"""
Prometheus 连接器 — 替代自定义 SNMP 轮询

从 Prometheus 查询 SNMP 指标（由 snmp_exporter 采集），
写入 device_interfaces（实时值）+ interface_traffic_samples（时序），
与现有前端 API 兼容，无需修改前端代码。

启动方式：在 main.py startup_event 中调用 start_connector()。
"""

import logging
from datetime import datetime
from typing import Dict, Optional

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.shared.database import get_db
from app.shared.models import Device, DeviceInterface, InterfaceTrafficSample

logger = logging.getLogger(__name__)

COUNTER64_MAX = 2**64

# Prometheus 直连地址（Python 应用与 Prometheus 同机部署）
PROMETHEUS_URL = "http://localhost:9090"
POLL_INTERVAL = 60  # 秒，与 Prometheus scrape_interval 对齐


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

    def _fetch_device_interfaces(self, instance: str) -> Dict[int, dict]:
        """查询一台设备全部接口的 Prometheus 指标，按 ifIndex 索引。"""
        ifaces: Dict[int, dict] = {}
        metrics = [
            "ifHCInOctets", "ifHCOutOctets", "ifOperStatus",
            "ifAdminStatus", "ifHighSpeed", "ifInErrors", "ifOutErrors",
        ]
        for metric in metrics:
            try:
                results = self._query(f'{metric}{{instance="{instance}"}}')
                for item in results:
                    if_idx = int(item["metric"]["ifIndex"])
                    entry = ifaces.get(if_idx)
                    if entry is None:
                        entry = {
                            "ifIndex": if_idx,
                            "ifName": item["metric"].get("ifName", ""),
                        }
                        ifaces[if_idx] = entry
                    # snmp_exporter 将所有指标真实值存储在标签中，Prometheus value 始终为 1
                    entry[metric] = int(item["metric"].get(metric, item["value"][1]))
            except Exception as exc:
                logger.warning("Prometheus query %s failed for %s: %s", metric, instance, exc)
        return ifaces

    # ── 持久化 ──

    def _persist(self, db, device: Device, ifaces: Dict[int, dict], now: datetime):
        """将 Prometheus 查询结果写入 device_interfaces / interface_traffic_samples。"""
        device_key = device.ip

        for if_idx, data in ifaces.items():
            iface: Optional[DeviceInterface] = (
                db.query(DeviceInterface)
                .filter(
                    DeviceInterface.device_id == device.id,
                    DeviceInterface.if_index == if_idx,
                )
                .first()
            )
            if iface is None:
                continue

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

    # ── 轮询入口 ──

    def poll_once(self):
        """单次轮询周期：查询 Prometheus → 写入数据库。"""
        db = next(get_db())
        try:
            devices = (
                db.query(Device)
                .filter(
                    Device.ip.isnot(None),
                )
                .all()
            )
            if not devices:
                return

            now = datetime.utcnow()
            for device in devices:
                try:
                    ifaces = self._fetch_device_interfaces(device.ip)
                    if ifaces:
                        self._persist(db, device, ifaces, now)
                except Exception as exc:
                    logger.error("Prometheus poll failed for %s: %s", device.ip, exc)

            db.commit()
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

def _counter_delta(prev: Optional[int], curr: Optional[int]) -> int:
    """处理 64 位计数器翻转。"""
    if prev is None or curr is None:
        return 0
    if curr >= prev:
        return curr - prev
    return (COUNTER64_MAX - prev) + curr
