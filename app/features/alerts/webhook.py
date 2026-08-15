"""告警 Webhook 接入（二期/三期）：Alertmanager / Zabbix / 通用 → MonitorEvent → 故障单闭环

鉴权：Header X-Alert-Token 必须等于环境变量 ALERT_WEBHOOK_TOKEN（fail-closed：
未配置 token 时接口直接 503，参考 trap_receiver 的做法）。
幂等：fingerprint × status → dedup_key 唯一约束，重复投递跳过。
设备解析：labels.device_id → labels.instance(ip) → labels.device/device_name（Zabbix 用 host）；
找不到系统设备时仅落 alert_event，不建故障单。
"""

import hmac
import json
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.shared.models import AlertEvent, Device

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts/webhook", tags=["告警Webhook"])

SEVERITY_MAP = {"critical": "critical", "warning": "major", "info": "minor"}
ZABBIX_SEVERITY_MAP = {
    "disaster": "critical", "critical": "critical", "high": "major",
    "average": "warning", "warning": "minor", "information": "minor",
    "not classified": "warning",
}


def _check_token(x_alert_token: Optional[str]) -> None:
    token = os.environ.get("ALERT_WEBHOOK_TOKEN") or None
    if not token:
        raise HTTPException(status_code=503, detail="告警 Webhook 未启用：未配置 ALERT_WEBHOOK_TOKEN")
    if not x_alert_token or not hmac.compare_digest(x_alert_token, token):
        raise HTTPException(status_code=401, detail="无效的告警 Token")


def _resolve_device(db: Session, *, device_id: Any = None, host: Any = None,
                    name: Any = None) -> Optional[Device]:
    if device_id:
        try:
            device = db.query(Device).filter(Device.id == int(device_id)).first()
            if device:
                return device
        except (TypeError, ValueError):
            pass
    if host:
        host_str = str(host).split(":")[0]
        device = db.query(Device).filter(Device.ip == host_str).first()
        if device:
            return device
    for value in (name, host):
        if value:
            device = db.query(Device).filter(Device.name == str(value)).first()
            if device:
                return device
    return None


def _handle_alert(db: Session, *, source_type: str, event_type: str, fingerprint: str,
                  status: str, severity: str, labels: Dict[str, Any],
                  annotations: Dict[str, Any], device: Optional[Device],
                  description_hint: str = "") -> str:
    """落 alert_event + 进入故障闭环。返回处理结果：created/resolved/duplicate/no_device。"""
    dedup_key = f"{source_type}:{fingerprint}:{status}"
    existing = db.query(AlertEvent).filter(AlertEvent.dedup_key == dedup_key).first()
    if existing:
        return "duplicate"

    fault_id = None
    result = "created"
    if device is None:
        result = "no_device"
    else:
        from app.services.incident_automation import MonitorEvent, upsert_fault_from_monitor_event
        try:
            fault = upsert_fault_from_monitor_event(db, MonitorEvent(
                source_type=source_type,
                event_type=event_type,
                device_id=device.id,
                device_name=device.name,
                ip=device.ip,
                severity_hint=severity,
                is_recovery=(status in ("resolved", "OK")),
                raw={"summary": (annotations.get("summary") or annotations.get("description")
                                 or description_hint or "")},
            ))
            fault_id = fault.id if fault else None
            if status in ("resolved", "OK"):
                result = "resolved"
        except Exception:
            db.rollback()
            logger.exception("Webhook 建单失败 source=%s fingerprint=%s", source_type, fingerprint)
            result = "error"

    db.add(AlertEvent(
        source_type=source_type,
        event_type=event_type,
        fingerprint=fingerprint,
        dedup_key=dedup_key,
        severity=severity,
        labels_json=json.dumps(labels, ensure_ascii=False),
        annotations_json=json.dumps(annotations, ensure_ascii=False),
        fault_id=fault_id,
    ))
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("alert_event 落库失败 fingerprint=%s", fingerprint)
    return result


@router.post("/prometheus")
async def prometheus_webhook(request: Request,
                             x_alert_token: Optional[str] = Header(default=None),
                             db: Session = Depends(get_db)):
    """接收 Alertmanager Webhook v4。"""
    _check_token(x_alert_token)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体不是合法 JSON")

    alerts: List[Dict[str, Any]] = payload.get("alerts", []) if isinstance(payload, dict) else []
    counters = {"created": 0, "resolved": 0, "duplicate": 0, "no_device": 0, "error": 0}
    for alert in alerts:
        fingerprint = str(alert.get("fingerprint") or alert.get("generatorURL") or "")
        if not fingerprint:
            continue
        labels = alert.get("labels") or {}
        annotations = alert.get("annotations") or {}
        status = str(alert.get("status") or "firing")
        severity = SEVERITY_MAP.get(str(labels.get("severity", "warning")).lower(), "warning")
        device = _resolve_device(db, device_id=labels.get("device_id"),
                                 host=labels.get("instance"),
                                 name=labels.get("device") or labels.get("device_name"))
        result = _handle_alert(db, source_type="prometheus", event_type="prometheus_alert",
                               fingerprint=fingerprint, status=status, severity=severity,
                               labels=labels, annotations=annotations, device=device)
        counters[result] = counters.get(result, 0) + 1
    return {"accepted": True, **counters}


@router.post("/zabbix")
async def zabbix_webhook(request: Request,
                         x_alert_token: Optional[str] = Header(default=None),
                         db: Session = Depends(get_db)):
    """接收 Zabbix 告警（5.4+ 格式：host/name/severity/status/value）。"""
    _check_token(x_alert_token)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体不是合法 JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Zabbix 负载必须是 JSON 对象")

    name = str(payload.get("name") or payload.get("key") or "zabbix_problem")
    status = "resolved" if str(payload.get("status", "PROBLEM")).upper() == "OK" else "firing"
    severity = ZABBIX_SEVERITY_MAP.get(str(payload.get("severity", "warning")).lower(), "warning")
    host = payload.get("host")
    fingerprint = str(payload.get("itemid") or f"{host}:{name}")
    device = _resolve_device(db, host=host, name=host)
    result = _handle_alert(db, source_type="zabbix", event_type="zabbix_alert",
                           fingerprint=fingerprint, status=status, severity=severity,
                           labels={"host": host, "key": name},
                           annotations={"summary": str(payload.get("value") or "")},
                           device=device)
    return {"accepted": True, "result": result}


@router.post("/generic")
async def generic_webhook(request: Request,
                          x_alert_token: Optional[str] = Header(default=None),
                          db: Session = Depends(get_db)):
    """接收通用自定义告警：{device_id|device_name|ip, event_type, severity, title, description, status, fingerprint}。"""
    _check_token(x_alert_token)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体不是合法 JSON")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="通用告警负载必须是 JSON 对象")

    device = _resolve_device(db, device_id=payload.get("device_id"),
                             host=payload.get("ip"),
                             name=payload.get("device_name") or payload.get("device"))
    event_type = str(payload.get("event_type") or "generic_alert")
    status = "resolved" if str(payload.get("status", "firing")).lower() in ("resolved", "ok") else "firing"
    severity = SEVERITY_MAP.get(str(payload.get("severity", "warning")).lower(), "warning")
    fingerprint = str(payload.get("fingerprint")
                      or (f"{getattr(device, 'id', 'none')}:{event_type}" if device else f"none:{event_type}"))
    result = _handle_alert(db, source_type="generic", event_type=event_type,
                           fingerprint=fingerprint, status=status, severity=severity,
                           labels={"device_name": payload.get("device_name"), "ip": payload.get("ip")},
                           annotations={"summary": str(payload.get("title") or ""),
                                        "description": str(payload.get("description") or "")},
                           device=device,
                           description_hint=str(payload.get("description") or ""))
    return {"accepted": True, "result": result}
