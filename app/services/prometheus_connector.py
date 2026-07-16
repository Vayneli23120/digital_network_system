"""
Prometheus 连接器 — 替代自定义 SNMP 轮询

从 Prometheus 查询 SNMP 指标（由 snmp_exporter 采集），
写入 device_interfaces（实时值）+ interface_traffic_samples（时序），
与现有前端 API 兼容，无需修改前端代码。

启动方式：在 main.py startup_event 中调用 start_connector()。
"""

import logging
import math
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import httpx
import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.device_metric_facts import record_device_metric_sample
from app.shared.database import get_db_manager
from app.shared.models import Device, DeviceInterface, InterfaceTrafficSample

logger = logging.getLogger(__name__)

COUNTER64_MAX = 2**64

# Prometheus 直连地址（Python 应用与 Prometheus 同机部署；Prometheus 在 Docker，端口发布到宓主机）
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
POLL_INTERVAL = int(os.environ.get("PROMETHEUS_POLL_INTERVAL", "60"))  # 秒，与 Prometheus scrape_interval 对齐

# Prometheus file_sd 目标文件：由本连接器根据数据库自动生成。
# 可用环境变量 PROMETHEUS_TARGETS_FILE 覆盖（例如容器挂载路径）。
_DEFAULT_TARGETS_FILE = str(
    Path(__file__).resolve().parents[2] / "docker" / "prometheus" / "targets" / "snmp_devices.yml"
)
TARGETS_FILE = os.environ.get("PROMETHEUS_TARGETS_FILE", _DEFAULT_TARGETS_FILE)


class PrometheusConnector:
    """查询 Prometheus → 写入 PostgreSQL"""

    def __init__(self, prometheus_url: str = PROMETHEUS_URL):
        self._http = httpx.Client(timeout=30)
        self._prometheus_url = prometheus_url.rstrip("/")
        self._running = False
        self._scheduler = BackgroundScheduler()
        self._last_counters: Dict[str, Dict[int, Dict[str, int | float]]] = {}
        # {device_ip: {ifIndex: {"in": octets, "out": octets, "ts": timestamp}}}

    # ── Prometheus 查询 ──

    def _query(self, promql: str) -> list:
        """执行 PromQL 即时查询，返回结果列表。"""
        resp = self._http.get(
            f"{self._prometheus_url}/api/v1/query",
            params={"query": promql},
        )
        resp.raise_for_status()
        body = resp.json()
        if body["status"] != "success":
            raise RuntimeError(f"Prometheus query error: {body.get('error', 'unknown')}")
        return body["data"]["result"]

    def _fetch_all_interfaces(self) -> Dict[str, Dict[int, dict]]:
        """一次性查询全部设备全部接口指标（每个指标一次全量 PromQL）。

        旧实现是“每台设备 × 7 个查询”（1000 台 = 7000 次串行查询），
        改为“每个指标一次全量”共 7 次查询，按 instance 标签在内存中聚合。

        返回 {instance: {ifIndex: {metric: value, ifName: ...}}}。
        """
        metrics = [
            "ifHCInOctets", "ifHCOutOctets", "ifOperStatus",
            "ifAdminStatus", "ifHighSpeed", "ifInErrors", "ifOutErrors",
        ]
        by_instance: Dict[str, Dict[int, dict]] = {}
        for metric in metrics:
            try:
                results = self._query(metric)
            except Exception as exc:
                logger.warning("Prometheus batch query %s failed: %s", metric, exc)
                continue
            for item in results:
                m = item["metric"]
                instance = m.get("instance")
                if not instance or "ifIndex" not in m:
                    continue
                try:
                    if_idx = int(m["ifIndex"])
                except (ValueError, TypeError):
                    continue
                dev_map = by_instance.setdefault(instance, {})
                entry = dev_map.get(if_idx)
                if entry is None:
                    entry = {"ifIndex": if_idx, "ifName": m.get("ifName", "")}
                    dev_map[if_idx] = entry
                elif not entry.get("ifName") and m.get("ifName"):
                    entry["ifName"] = m.get("ifName")
                raw_value = _prometheus_metric_raw_value(item, metric)
                try:
                    entry[metric] = int(raw_value)
                except (ValueError, TypeError):
                    pass
        return by_instance

    def _fetch_device_uptimes(self) -> Dict[str, int]:
        """Fetch device uptime from snmp_exporter, keyed by target instance."""
        uptimes: Dict[str, int] = {}
        try:
            results = self._query("sysUpTime")
        except Exception as exc:
            logger.warning("Prometheus batch query sysUpTime failed: %s", exc)
            return uptimes

        for item in results:
            instance = (item.get("metric") or {}).get("instance")
            if not instance:
                continue
            try:
                uptime_seconds = float(
                    _prometheus_metric_raw_value(item, "sysUpTime")
                )
            except (TypeError, ValueError):
                continue
            if uptime_seconds < 0 or not math.isfinite(uptime_seconds):
                continue
            uptimes[instance] = int(uptime_seconds // 86400)
        return uptimes

    # ── 持久化 ──

    def _persist_device(self, db, device: Device, ifaces: Dict[int, dict], now: datetime) -> int:
        """写入单台设备接口数据；一次性批量加载该设备接口，消除 N+1。返回写入接口数。"""
        if not ifaces:
            return 0
        rows = (
            db.query(DeviceInterface)
            .filter(
                DeviceInterface.device_id == device.id,
                DeviceInterface.if_index.in_(list(ifaces.keys())),
            )
            .all()
        )
        iface_by_idx = {r.if_index: r for r in rows}
        device_key = device.ip
        written = 0

        for if_idx, data in ifaces.items():
            iface = iface_by_idx.get(if_idx)
            if iface is None:
                continue
            written += 1

            old_oper = iface.oper_status
            new_oper = "up" if data.get("ifOperStatus", 0) == 1 else "down"

            # 更新实时状态
            iface.oper_status = new_oper
            iface.admin_status = "up" if data.get("ifAdminStatus", 0) == 1 else "down"
            if "ifHighSpeed" in data:
                iface.speed_mbps = data["ifHighSpeed"]
            iface.last_check = now
            iface.last_in_errors = data.get("ifInErrors", 0)
            iface.last_out_errors = data.get("ifOutErrors", 0)

            # 速率计算：两次采集间的计数器差值 / 时间 × 8
            has_hc = "ifHCInOctets" in data and "ifHCOutOctets" in data
            if has_hc:
                curr_in = data["ifHCInOctets"]
                curr_out = data["ifHCOutOctets"]
                iface.last_in_octets = curr_in
                iface.last_out_octets = curr_out
                iface.last_sample_at = now

                prev = self._last_counters.get(device_key, {}).get(if_idx)
                if prev is not None:
                    dt = now.timestamp() - prev["ts"]
                    if dt > 0:
                        in_delta = _counter_delta(prev["in"], curr_in)
                        out_delta = _counter_delta(prev["out"], curr_out)
                        in_bps = int(in_delta * 8 / dt)
                        out_bps = int(out_delta * 8 / dt)

                        if in_bps <= 400_000_000_000 and out_bps <= 400_000_000_000:
                            iface.last_in_bps = in_bps
                            iface.last_out_bps = out_bps

                            speed = data.get("ifHighSpeed") or iface.speed_mbps
                            if speed and speed > 0:
                                cap = speed * 1_000_000
                                iface.last_in_util = round(min(in_bps / cap * 100, 100), 2)
                                iface.last_out_util = round(min(out_bps / cap * 100, 100), 2)

                            # 仅 monitored 接口写入时序样本
                            if iface.monitored:
                                db.add(InterfaceTrafficSample(
                                    interface_id=iface.id,
                                    device_id=device.id,
                                    ts=now,
                                    in_bps=in_bps,
                                    out_bps=out_bps,
                                    in_util=iface.last_in_util,
                                    out_util=iface.last_out_util,
                                    in_errors=data.get("ifInErrors", 0),
                                    out_errors=data.get("ifOutErrors", 0),
                                    oper_status=new_oper,
                                ))

                # 保存当前计数器供下次计算
                self._last_counters.setdefault(device_key, {})[if_idx] = {
                    "in": curr_in,
                    "out": curr_out,
                    "ts": now.timestamp(),
                }

            # oper_status 变化记录（TODO: 后续可接入 WebSocket 推送 / 故障工单）
            if old_oper and old_oper != new_oper and new_oper in ("up", "down"):
                logger.info(
                    "Interface %s ifIndex %d (%s): %s → %s",
                    device.ip, if_idx, data.get("ifName", "?"),
                    old_oper, new_oper,
                )

        return written

    # ── Prometheus 目标清单自动生成 ──

    def sync_targets(self, db) -> bool:
        """根据数据库中启用 SNMP 的设备生成 Prometheus file_sd 目标文件。

        按 snmp_community 分组（对应 snmp_exporter 的 auth 名），仅在内容变化时写入，
        避免无谓写盘。新增设备后下一个周期即可自动进入 Prometheus 采集。

        返回 True 表示文件发生了变更。
        """
        devices = (
            db.query(Device)
            .filter(
                Device.snmp_enabled == True,  # noqa: E712
                Device.ip.isnot(None),
                Device.snmp_community.isnot(None),
            )
            .order_by(Device.snmp_community, Device.ip)
            .all()
        )

        # 按 auth（社区名）分组，可选端口不为 161 时附在目标后
        groups: Dict[str, list] = {}
        for dev in devices:
            auth = dev.snmp_community
            port = getattr(dev, "snmp_port", None)
            target = dev.ip if not port or port == 161 else f"{dev.ip}:{port}"
            groups.setdefault(auth, []).append(target)

        target_groups = [
            {
                "targets": sorted(set(targets)),
                "labels": {"job": "snmp_cisco", "auth": auth},
            }
            for auth, targets in sorted(groups.items())
        ]

        header = "# SNMP 设备目标列表 — 由 prometheus_connector.sync_targets() 自动生成，请勿手动编辑。\n"
        body = yaml.safe_dump(target_groups, allow_unicode=True, sort_keys=False, default_flow_style=False)
        content = header + (body if target_groups else "[]\n")

        try:
            existing = None
            if os.path.exists(TARGETS_FILE):
                with open(TARGETS_FILE, "r", encoding="utf-8") as fh:
                    existing = fh.read()
            if existing == content:
                return False
            os.makedirs(os.path.dirname(TARGETS_FILE), exist_ok=True)
            with open(TARGETS_FILE, "w", encoding="utf-8") as fh:
                fh.write(content)
            logger.info(
                "Prometheus targets synced: %d device(s), %d auth group(s) → %s",
                len(devices), len(target_groups), TARGETS_FILE,
            )
            return True
        except OSError as exc:
            logger.warning("Failed to write Prometheus targets file %s: %s", TARGETS_FILE, exc)
            return False

    # ── 轮询入口 ──

    def poll_once(self):
        """单次轮询周期：同步目标清单 → 查询 Prometheus → 写入数据库。"""
        started = time.monotonic()
        db = get_db_manager().get_session()
        try:
            # 先同步目标文件，让新增/变更的 SNMP 设备自动进入采集
            try:
                self.sync_targets(db)
            except Exception as exc:
                logger.warning("sync_targets failed: %s", exc)

            devices = (
                db.query(Device)
                .filter(
                    Device.ip.isnot(None),
                )
                .all()
            )
            if not devices:
                return
            devices_by_ip = {d.ip: d for d in devices}

            now = datetime.utcnow()

            # 一次性批量查询所有指标（8 次查询，而非逐台设备查询）
            q_started = time.monotonic()
            by_instance = self._fetch_all_interfaces()
            uptimes_by_instance = self._fetch_device_uptimes()
            query_ms = int((time.monotonic() - q_started) * 1000)

            persist_started = time.monotonic()
            device_count = 0
            iface_count = 0
            fact_count = 0
            instances = sorted(set(by_instance) | set(uptimes_by_instance))
            processed_device_ids = set()
            for instance in instances:
                device = devices_by_ip.get(instance)
                # 端口非 161 时 instance 形如 ip:port，回退按 IP 匹配
                if device is None and ":" in instance:
                    device = devices_by_ip.get(instance.rsplit(":", 1)[0])
                if device is None or device.id in processed_device_ids:
                    continue
                processed_device_ids.add(device.id)
                ifaces = by_instance.get(instance, {})
                try:
                    iface_count += self._persist_device(db, device, ifaces, now)
                    device_count += 1
                except Exception as exc:
                    logger.error("Persist failed for %s: %s", instance, exc)

                try:
                    with db.begin_nested():
                        record_device_metric_sample(
                            db,
                            device.id,
                            _build_device_metric_payload(
                                ifaces,
                                uptimes_by_instance.get(instance),
                            ),
                            source="prometheus_snmp",
                            ts=now,
                        )
                    fact_count += 1
                except Exception as exc:
                    logger.warning("Metric fact persist failed for %s: %s", instance, exc)

            db.commit()
            persist_ms = int((time.monotonic() - persist_started) * 1000)

            # 根据交换机端口 oper_status 刷新 AP 在线状态（AP 不 ping，靠 CDP + 端口）
            try:
                from app.services.ap_discovery import sync_ap_online_status
                ap_updated = sync_ap_online_status(db)
                if ap_updated:
                    db.commit()
            except Exception as exc:
                logger.warning("sync_ap_online_status failed: %s", exc)

            total_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "Prometheus poll: %d devices, %d interfaces, %d metric facts, query=%dms persist=%dms total=%dms",
                device_count, iface_count, fact_count, query_ms, persist_ms, total_ms,
            )
        except Exception as exc:
            logger.error("Poll cycle failed: %s", exc)
            db.rollback()
        finally:
            db.close()

    # ── 生命周期 ──

    def start(self):
        if self._running:
            return
        # 启动后立即执行一次，避免等到下一个调度周期
        self.poll_once()
        self._scheduler.add_job(
            self.poll_once,
            trigger=IntervalTrigger(seconds=POLL_INTERVAL),
            id="prometheus_connector_poll",
            name="Prometheus SNMP connector",
            replace_existing=True,
        )
        self._scheduler.start()
        self._running = True
        logger.info("Prometheus connector started (interval=%ds)", POLL_INTERVAL)

    def stop(self):
        self._running = False
        self._scheduler.shutdown(wait=False)
        self._http.close()
        logger.info("Prometheus connector stopped")


# ── 单例 ──

_connector: Optional[PrometheusConnector] = None


def get_connector() -> PrometheusConnector:
    global _connector
    if _connector is None:
        _connector = PrometheusConnector()
    return _connector


def start_connector():
    c = get_connector()
    c.start()
    return c


def stop_connector():
    global _connector
    if _connector:
        _connector.stop()
        _connector = None


# ── 工具函数 ──

def _prometheus_metric_raw_value(item: dict, metric_name: str):
    """Read exporter label-style values with standard samples as fallback."""
    metric = item.get("metric") or {}
    label_value = metric.get(metric_name)
    if label_value not in (None, ""):
        return label_value

    sample = item.get("value") or []
    return sample[1] if len(sample) >= 2 else None


def _counter_delta(prev: Optional[int], curr: Optional[int]) -> int:
    """处理 64 位计数器翻转。"""
    if prev is None or curr is None:
        return 0
    if curr >= prev:
        return curr - prev
    return (COUNTER64_MAX - prev) + curr


def _build_device_metric_payload(
    ifaces: Dict[int, dict],
    uptime_days: Optional[int],
) -> dict:
    """Aggregate one Prometheus target into the canonical collector shape."""
    oper_statuses = [
        data["ifOperStatus"]
        for data in ifaces.values()
        if "ifOperStatus" in data
    ]
    error_values = [
        data[metric]
        for data in ifaces.values()
        for metric in ("ifInErrors", "ifOutErrors")
        if isinstance(data.get(metric), (int, float))
    ]
    total_errors = int(sum(error_values)) if error_values else None
    if oper_statuses:
        interface_metrics = {
            "up": sum(1 for status in oper_statuses if status == 1),
            "down": sum(1 for status in oper_statuses if status == 2),
            "total": len(oper_statuses),
        }
    else:
        interface_metrics = {"up": None, "down": None, "total": None}

    return {
        "cpu": {"value": None, "status": "unknown"},
        "memory": {"used_percent": None, "status": "unknown"},
        "temperature": {"value": None, "status": "unknown"},
        "uptime": {"uptime_days": uptime_days},
        "interfaces": interface_metrics,
        "errors": {
            "total_errors": total_errors,
            "has_errors": bool(total_errors),
        },
    }
