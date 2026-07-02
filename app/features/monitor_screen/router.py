"""
Monitor Screen Router - 系统监控大屏 API

提供平面图管理、设备节点管理、设备详情、离线告警等 API。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
from pathlib import Path
import shutil
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.config import get_config
from app.shared.models import Device, DeviceInterface, DeviceNode, FaultRecord
from app.shared.time_utils import utc_iso
from app.services.incident_insights import build_hot_links, build_impact_scope, build_root_cause_candidates, build_shared_path_edges
from app.services.monitor3d_traffic_heat import build_traffic_heat_items
from .monitor_service import (
    get_floor_plans, get_floor_plan, create_floor_plan, update_floor_plan, delete_floor_plan,
    get_floor_plan_nodes, create_device_node, update_device_node, delete_device_node,
    get_device_detail, get_offline_alerts, get_available_devices, get_plan_snapshot, get_plan_topology, get_global_summary,
)

config = get_config()
router = APIRouter(prefix="/api", tags=["monitor-screen"])


# ============ Pydantic 模型 ============

class FloorPlanCreate(BaseModel):
    name: str


class FloorPlanUpdate(BaseModel):
    name: Optional[str] = None


class DeviceNodeCreate(BaseModel):
    device_id: int
    x_percent: float
    y_percent: float


class DeviceNodeUpdate(BaseModel):
    x_percent: Optional[float] = None
    y_percent: Optional[float] = None
    scale: Optional[float] = None  # 缩放比例 (0.5-3.0)


# ============ 平面图管理 API ============

@router.get("/floor-plans")
async def list_floor_plans(db: Session = Depends(get_db)):
    """获取平面图列表"""
    return {"items": get_floor_plans(db)}


@router.get("/floor-plans/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """获取单个平面图详情"""
    result = get_floor_plan(db, plan_id)
    if not result:
        raise HTTPException(status_code=404, detail="平面图不存在")
    return result


@router.post("/floor-plans")
async def create_plan(
    name: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传平面图"""
    # 确保上传目录存在
    upload_dir = Path(config.storage.photo_dir) / "floor_plans"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 生成安全的文件名
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    original_ext = Path(image.filename).suffix if image.filename else ".jpg"

    # 读取图片数据
    image_data = await image.read()

    # 处理图片
    if original_ext.lower() == '.svg':
        # SVG 矢量图直接保存
        filename = f"{timestamp}.svg"
        file_path = upload_dir / filename
        with open(file_path, "wb") as buffer:
            buffer.write(image_data)
    else:
        # 尝试使用 Pillow 处理
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            original_width, original_height = img.size

            # 保存原图（用于超高清需求）
            original_path = upload_dir / f"{timestamp}_original{original_ext}"

            # 生成预览版本：控制在 4096px
            preview_max = 4096
            if max(original_width, original_height) > preview_max:
                ratio = preview_max / max(original_width, original_height)
                preview_size = (int(original_width * ratio), int(original_height * ratio))
                preview_img = img.resize(preview_size, Image.LANCZOS)
            else:
                preview_img = img

            # 保存预览版本
            preview_path = upload_dir / f"{timestamp}{original_ext}"

            if original_ext.lower() in ['.jpg', '.jpeg']:
                preview_img.save(preview_path, 'JPEG', quality=95, optimize=True)
                img.save(original_path, 'JPEG', quality=95)
            elif original_ext.lower() == '.png':
                preview_img.save(preview_path, 'PNG', optimize=True)
                img.save(original_path, 'PNG', optimize=True)
            else:
                preview_img.save(preview_path, quality=95)
                img.save(original_path, quality=95)

            file_path = preview_path

        except ImportError:
            # Pillow 未安装，直接保存原图
            filename = f"{timestamp}{original_ext}"
            file_path = upload_dir / filename
            with open(file_path, "wb") as buffer:
                buffer.write(image_data)
        except Exception as e:
            # 处理失败，保存原图
            filename = f"{timestamp}{original_ext}"
            file_path = upload_dir / filename
            with open(file_path, "wb") as buffer:
                buffer.write(image_data)

    # 创建数据库记录
    result = create_floor_plan(db, name, str(file_path))
    return result


@router.put("/floor-plans/{plan_id}")
async def update_plan(
    plan_id: int,
    name: Optional[str] = None,
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """更新平面图（可更换图片）"""
    image_path = None
    if image:
        upload_dir = Path(config.storage.photo_dir) / "floor_plans"
        upload_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        original_ext = Path(image.filename).suffix if image.filename else ".jpg"

        image_data = await image.read()

        if original_ext.lower() == '.svg':
            filename = f"{timestamp}.svg"
            file_path = upload_dir / filename
            with open(file_path, "wb") as buffer:
                buffer.write(image_data)
        else:
            try:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(image_data))
                original_width, original_height = img.size

                original_path = upload_dir / f"{timestamp}_original{original_ext}"

                preview_max = 4096
                if max(original_width, original_height) > preview_max:
                    ratio = preview_max / max(original_width, original_height)
                    preview_size = (int(original_width * ratio), int(original_height * ratio))
                    preview_img = img.resize(preview_size, Image.LANCZOS)
                else:
                    preview_img = img

                preview_path = upload_dir / f"{timestamp}{original_ext}"

                if original_ext.lower() in ['.jpg', '.jpeg']:
                    preview_img.save(preview_path, 'JPEG', quality=95, optimize=True)
                    img.save(original_path, 'JPEG', quality=95)
                elif original_ext.lower() == '.png':
                    preview_img.save(preview_path, 'PNG', optimize=True)
                    img.save(original_path, 'PNG', optimize=True)
                else:
                    preview_img.save(preview_path, quality=95)
                    img.save(original_path, quality=95)

                file_path = preview_path
            except ImportError:
                filename = f"{timestamp}{original_ext}"
                file_path = upload_dir / filename
                with open(file_path, "wb") as buffer:
                    buffer.write(image_data)
            except Exception:
                filename = f"{timestamp}{original_ext}"
                file_path = upload_dir / filename
                with open(file_path, "wb") as buffer:
                    buffer.write(image_data)

        image_path = str(file_path)

    result = update_floor_plan(db, plan_id, name=name, image_path=image_path)
    if not result:
        raise HTTPException(status_code=404, detail="平面图不存在")
    return result


@router.delete("/floor-plans/{plan_id}")
async def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    """删除平面图"""
    success = delete_floor_plan(db, plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="平面图不存在")
    return {"message": "平面图删除成功"}


# ============ 设备节点管理 API ============

@router.get("/floor-plans/{plan_id}/nodes")
async def list_nodes(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图上的设备节点"""
    nodes = get_floor_plan_nodes(db, plan_id)
    return {"items": nodes}


@router.get("/floor-plans/{plan_id}/snapshot")
async def get_snapshot(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图全量快照 - 用于 WebSocket 重连对账

    返回所有节点完整状态 + 统计数据，前端重连时直接覆盖本地状态，
    防止乐观增减导致的计数漂移。
    """
    result = get_plan_snapshot(db, plan_id)
    return result


@router.get("/floor-plans/{plan_id}/topology")
async def get_topology(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图拓扑数据 - 用于数字孪生渲染

    返回（Gen3 图模型）：
    - nodes: 设备节点列表（位置 + 可达性状态）
    - topo_nodes: 拓扑节点（设备端口 + 接头/分支点 junction）
    - topo_edges: 拓扑边（线缆，自带拐点）
    - cables: 按 cable_id 聚合的光缆
    - device_paths: 各设备到核心的图寻路折线
    """
    result = get_plan_topology(db, plan_id)
    return result


@router.get("/floor-plans/{plan_id}/available-devices")
async def list_available_devices(plan_id: int, db: Session = Depends(get_db)):
    """获取可添加到平面图的设备列表"""
    devices = get_available_devices(db, plan_id)
    return {"items": devices}


@router.post("/floor-plans/{plan_id}/nodes")
async def create_node(plan_id: int, node_data: DeviceNodeCreate, db: Session = Depends(get_db)):
    """创建设备节点"""
    result = create_device_node(db, plan_id, node_data.device_id, node_data.x_percent, node_data.y_percent)
    if not result:
        raise HTTPException(status_code=404, detail="平面图或设备不存在")
    return result


@router.put("/floor-plans/{plan_id}/nodes/{node_id}")
async def update_node(plan_id: int, node_id: int, node_data: DeviceNodeUpdate, db: Session = Depends(get_db)):
    """更新设备节点位置和大小"""
    result = update_device_node(db, plan_id, node_id, node_data.x_percent, node_data.y_percent, node_data.scale)
    if not result:
        raise HTTPException(status_code=404, detail="节点不存在")
    return result


@router.delete("/floor-plans/{plan_id}/nodes/{node_id}")
async def delete_node(plan_id: int, node_id: int, db: Session = Depends(get_db)):
    """删除设备节点"""
    success = delete_device_node(db, plan_id, node_id)
    if not success:
        raise HTTPException(status_code=404, detail="节点不存在")
    return {"message": "节点删除成功"}


# ============ 设备详情 & 告警 API ============

@router.get("/monitor-screen/device/{device_id}/detail")
async def get_device_info(device_id: int, db: Session = Depends(get_db)):
    """获取设备详情（用于大屏弹窗）"""
    result = get_device_detail(db, device_id)
    if not result:
        raise HTTPException(status_code=404, detail="设备不存在")
    return result


@router.get("/monitor-screen/offline-alerts")
async def get_alerts(db: Session = Depends(get_db)):
    """获取离线设备告警列表"""
    alerts = get_offline_alerts(db)
    return {"items": alerts}


@router.get("/monitor-screen/stats")
async def get_stats(db: Session = Depends(get_db)):
    """获取大屏统计数据"""
    from app.shared.models import Device
    from sqlalchemy import or_

    total_devices = db.query(Device).count()
    # Phase2: 统一以 reachability 驱动在线/离线统计
    online_devices = db.query(Device).filter(Device.reachability == "reachable").count()
    offline_devices = db.query(Device).filter(Device.reachability == "unreachable").count()
    maintenance_devices = db.query(Device).filter(Device.deployment_status == "maintenance").count()

    # 交换机：包括 office_switch、core_switch、server_switch（项目实际枚举值）
    switch_count = db.query(Device).filter(
        Device.device_type.in_(["office_switch", "core_switch", "server_switch"])
    ).count()
    ap_count = db.query(Device).filter(Device.device_type == "ap").count()

    return {
        "total": total_devices,
        "online": online_devices,
        "offline": offline_devices,
        "maintenance": maintenance_devices,
        "switch_count": switch_count,
        "ap_count": ap_count,
    }


@router.get("/monitor-screen/global-summary")
async def get_global_summary_endpoint(db: Session = Depends(get_db)):
    """获取全厂健康度汇总 - 用于大屏顶部健康条

    聚合所有平面图数据，返回全厂整体健康状态。
    """
    return get_global_summary(db)


@router.get("/monitor3d/command-summary")
async def get_monitor3d_command_summary(plan_id: Optional[int] = None, db: Session = Depends(get_db)):
    """获取 3D 大屏故障指挥面板汇总"""
    active_statuses = ["open", "assigned", "accepted", "diagnosing", "resolving", "transferred"]
    active_query = db.query(FaultRecord).filter(FaultRecord.status.in_(active_statuses))

    p1_count = active_query.filter(FaultRecord.severity == "critical").count()
    p2_count = active_query.filter(FaultRecord.severity == "major").count()
    unacknowledged = active_query.filter(FaultRecord.review_required == True).count()
    in_progress = active_query.filter(FaultRecord.status.in_(["accepted", "diagnosing", "resolving"])).count()
    transferred = active_query.filter(FaultRecord.status == "transferred").count()
    impacted_devices = active_query.filter(FaultRecord.device_id.isnot(None)).with_entities(
        func.count(func.distinct(FaultRecord.device_id))
    ).scalar() or 0

    recent_faults = active_query.order_by(
        FaultRecord.last_event_at.desc().nullslast(),
        FaultRecord.created_at.desc(),
    ).limit(5).all()
    active_faults = active_query.order_by(
        FaultRecord.severity.desc(),
        FaultRecord.last_event_at.desc().nullslast(),
        FaultRecord.created_at.desc(),
    ).limit(200).all()
    device_paths = None
    if plan_id:
        try:
            from .graph_path_service import calculate_all_device_paths
            device_paths = calculate_all_device_paths(db, plan_id)
        except Exception:
            device_paths = None

    root_cause_candidates = build_root_cause_candidates(active_faults)
    shared_path_edges = build_shared_path_edges(active_faults, device_paths)
    if shared_path_edges:
        top_edge = shared_path_edges[0]
        root_cause_candidates.insert(0, {
            "candidate": f"共同路径 {top_edge['cable_name']} 疑似上游链路异常",
            "confidence": min(0.92, 0.52 + top_edge["affected_devices"] * 0.1),
            "impacted_devices": top_edge["affected_devices"],
            "fault_id": None,
            "device_id": top_edge["device_ids"][0] if top_edge["device_ids"] else None,
            "severity": "major",
            "evidence": ["shared path edge", top_edge["cable_name"], f"{top_edge['affected_devices']} affected devices"],
        })
        root_cause_candidates = root_cause_candidates[:3]

    return {
        "p1_count": p1_count,
        "p2_count": p2_count,
        "unacknowledged": unacknowledged,
        "in_progress": in_progress,
        "transferred": transferred,
        "impacted_devices": impacted_devices,
        "recent_events": [
            {
                "id": fault.id,
                "fault_no": fault.fault_no,
                "device_id": fault.device_id,
                "device_name": fault.device_name,
                "severity": fault.severity,
                "status": fault.status,
                "source_type": fault.source_type,
                "source_event": fault.source_event,
                "incident_type": fault.incident_type,
                "if_name": fault.if_name,
                "review_required": bool(fault.review_required) if fault.review_required is not None else False,
                "event_count": fault.event_count or 1,
                "last_event_at": fault.last_event_at.isoformat() if fault.last_event_at else None,
                "created_at": fault.created_at.isoformat() if fault.created_at else None,
            }
            for fault in recent_faults
        ],
        "root_cause_candidates": root_cause_candidates,
        "impact_scope": build_impact_scope(active_faults, device_paths),
        "hot_links": build_hot_links(active_faults),
    }


def _monitor_event_item(fault: FaultRecord, event_type: str, event_time: datetime, title: str) -> Dict:
    return {
        "id": f"fault:{fault.id}:{event_type}:{event_time.isoformat()}",
        "fault_id": fault.id,
        "fault_no": fault.fault_no,
        "device_id": fault.device_id,
        "device_name": fault.device_name,
        "severity": fault.severity,
        "status": fault.status,
        "event_type": event_type,
        "title": title,
        "source_type": fault.source_type,
        "source_event": fault.source_event,
        "incident_type": fault.incident_type,
        "if_name": fault.if_name,
        "review_required": bool(fault.review_required) if fault.review_required is not None else False,
        "event_count": fault.event_count or 1,
        "occurred_at": event_time.isoformat(),
    }


@router.get("/monitor3d/events")
async def get_monitor3d_events(
    window: str = Query("1h", pattern="^(10m|1h|24h)$"),
    severity: Optional[str] = None,
    limit: int = Query(100, ge=1, le=300),
    db: Session = Depends(get_db),
):
    """获取 3D 大屏故障事件时间线（MVP：由 FaultRecord 生命周期派生）"""
    window_delta = {
        "10m": timedelta(minutes=10),
        "1h": timedelta(hours=1),
        "24h": timedelta(hours=24),
    }[window]
    since = datetime.utcnow() - window_delta

    query = db.query(FaultRecord).filter(
        (FaultRecord.created_at >= since)
        | (FaultRecord.last_event_at >= since)
        | (FaultRecord.reviewed_at >= since)
        | (FaultRecord.transferred_at >= since)
        | (FaultRecord.resolved_at >= since)
        | (FaultRecord.closed_at >= since)
    )
    if severity:
        severities = [item.strip() for item in severity.split(",") if item.strip()]
        query = query.filter(FaultRecord.severity.in_(severities))

    faults = query.order_by(
        FaultRecord.updated_at.desc().nullslast(),
        FaultRecord.created_at.desc(),
    ).limit(limit * 2).all()

    events = []
    for fault in faults:
        if fault.created_at and fault.created_at >= since:
            events.append(_monitor_event_item(fault, "fault_created", fault.created_at, "故障创建"))
        if fault.last_event_at and fault.last_event_at >= since and fault.last_event_at != fault.created_at:
            events.append(_monitor_event_item(fault, fault.source_event or "monitor_event", fault.last_event_at, "监控事件"))
        if fault.reviewed_at and fault.reviewed_at >= since:
            title = "标记误报" if fault.false_positive else "管理员复核"
            events.append(_monitor_event_item(fault, "fault_reviewed", fault.reviewed_at, title))
        if fault.transferred_at and fault.transferred_at >= since:
            events.append(_monitor_event_item(fault, "maintenance_transferred", fault.transferred_at, "转维修"))
        if fault.resolved_at and fault.resolved_at >= since:
            events.append(_monitor_event_item(fault, "fault_resolved", fault.resolved_at, "故障恢复"))
        if fault.closed_at and fault.closed_at >= since:
            events.append(_monitor_event_item(fault, "fault_closed", fault.closed_at, "故障关闭"))

    events.sort(key=lambda item: item["occurred_at"], reverse=True)
    return {"items": events[:limit], "window": window, "since": since.isoformat()}


@router.get("/monitor3d/traffic-heat")
async def get_monitor3d_traffic_heat(plan_id: Optional[int] = None, db: Session = Depends(get_db)):
    """获取 3D 大屏流量热力层数据（基于接口最新采样）。"""
    plan_device_ids = None
    if plan_id:
        plan_device_ids = [
            row[0]
            for row in db.query(DeviceNode.device_id).filter(DeviceNode.floor_plan_id == plan_id).all()
        ]

    items = build_traffic_heat_items(db, plan_device_ids)
    summary = {
        "critical": 0,
        "high": 0,
        "normal": 0,
        "low": 0,
        "down": 0,
        "stale": 0,
    }
    for item in items:
        if item["level"] in summary:
            summary[item["level"]] += 1

    return {"items": items, "summary": summary, "plan_id": plan_id}


@router.get("/monitor3d/snmp-health")
async def get_monitor3d_snmp_health(plan_id: Optional[int] = None, db: Session = Depends(get_db)):
    """获取 3D 大屏 SNMP 采集健康状态（仅 monitored 接口）。"""
    plan_device_ids = None
    if plan_id:
        plan_device_ids = [
            row[0]
            for row in db.query(DeviceNode.device_id).filter(DeviceNode.floor_plan_id == plan_id).all()
        ]

    query = db.query(DeviceInterface, Device).join(Device, Device.id == DeviceInterface.device_id).filter(
        DeviceInterface.monitored == True,  # noqa: E712
    )
    if plan_device_ids is not None:
        if not plan_device_ids:
            return {"items": [], "summary": {}, "plan_id": plan_id}
        query = query.filter(DeviceInterface.device_id.in_(plan_device_ids))

    now = datetime.utcnow()
    summary = {"fresh": 0, "lagging": 0, "stale": 0, "missing": 0, "down": 0, "total": 0}
    collector_state = {}
    try:
        from app.services.interface_monitor import get_interface_monitor
        collector_state = get_interface_monitor().get_poll_state_snapshot()
    except Exception:
        collector_state = {}
    items = []
    for iface, device in query.all():
        collector = collector_state.get(iface.device_id, {})
        check_age_seconds = int((now - iface.last_check).total_seconds()) if iface.last_check else None
        sample_age_seconds = int((now - iface.last_sample_at).total_seconds()) if iface.last_sample_at else None
        if iface.oper_status == "down":
            status = "down"
        elif iface.last_check is None:
            status = "missing"
        else:
            if check_age_seconds > 600:
                status = "stale"
            elif check_age_seconds > 90:
                status = "lagging"
            else:
                status = "fresh"

        summary[status] += 1
        summary["total"] += 1
        items.append({
            "device_id": iface.device_id,
            "device_name": device.name,
            "device_ip": device.ip,
            "if_index": iface.if_index,
            "if_name": iface.if_name,
            "is_uplink": bool(iface.is_uplink),
            "oper_status": iface.oper_status,
            "admin_status": iface.admin_status,
            "last_sample_at": utc_iso(iface.last_sample_at),
            "last_check": utc_iso(iface.last_check),
            "age_seconds": check_age_seconds,
            "check_age_seconds": check_age_seconds,
            "sample_age_seconds": sample_age_seconds,
            "has_counter_sample": iface.last_in_octets is not None and iface.last_out_octets is not None,
            "collector_status": collector.get("status"),
            "collector_ok": collector.get("ok"),
            "collector_duration_ms": collector.get("duration_ms"),
            "collector_poll_mode": collector.get("poll_mode"),
            "collector_readings_count": collector.get("readings_count"),
            "collector_monitored_count": collector.get("monitored_count"),
            "collector_missing_counter_count": collector.get("missing_counter_count"),
            "collector_fallback_count": collector.get("fallback_count"),
            "collector_next_poll_in_seconds": collector.get("next_poll_in_seconds"),
            "collector_inflight_seconds": collector.get("inflight_seconds"),
            "collector_error": collector.get("last_error"),
            "status": status,
            "in_util": iface.last_in_util,
            "out_util": iface.last_out_util,
            "peer_device_name": iface.peer_device_name,
            "peer_if_name": iface.peer_if_name,
        })

    status_order = {"stale": 0, "missing": 1, "lagging": 2, "down": 3, "fresh": 4}
    items.sort(key=lambda item: (status_order.get(item["status"], 9), -(item["age_seconds"] or 0)))
    return {"items": items, "summary": summary, "plan_id": plan_id, "now": utc_iso(now)}


# ============ 图模型拓扑 API（新设计） ============

from .topo_service import (
    get_cables, get_topo_nodes, get_topo_edges,
    create_trunk, create_branch_point, create_branch_cable,
    update_topo_edge, update_topo_node, delete_topo_edge, delete_topo_node, delete_cable,
    rename_cable, is_cable_name_duplicated,
)


class TrunkCreate(BaseModel):
    """创建主干光缆"""
    name: Optional[str] = None
    cable_no: Optional[str] = None
    start_x: float
    start_y: float
    start_device_id: Optional[int] = None
    end_x: float
    end_y: float
    waypoints: Optional[List[Dict[str, float]]] = None


class BranchPointCreate(BaseModel):
    """创建分支点"""
    trunk_cable_id: int
    x: float
    y: float
    label: Optional[str] = None


class BranchCableCreate(BaseModel):
    """创建分支光缆"""
    branch_point_id: int
    to_device_id: int
    to_port_id: Optional[int] = None  # 指定连接的端口锚点，避免链路与光缆分叉
    name: Optional[str] = None
    cable_no: Optional[str] = None
    waypoints: Optional[List[Dict[str, float]]] = None


class TopoEdgeUpdate(BaseModel):
    """更新拓扑边"""
    waypoints: Optional[List[Dict[str, float]]] = None
    cable_name: Optional[str] = None
    cable_no: Optional[str] = None
    status: Optional[str] = None


class TopoNodeUpdate(BaseModel):
    """更新拓扑节点"""
    x_percent: Optional[float] = None
    y_percent: Optional[float] = None
    label: Optional[str] = None


@router.get("/floor-plans/{plan_id}/cables")
async def list_cables(plan_id: int, db: Session = Depends(get_db)):
    """获取所有光缆（按 cable_id 聚合）"""
    return {"items": get_cables(db, plan_id)}


@router.get("/floor-plans/{plan_id}/topo-nodes")
async def list_topo_nodes(plan_id: int, db: Session = Depends(get_db)):
    """获取所有拓扑节点"""
    return {"items": get_topo_nodes(db, plan_id)}


@router.get("/floor-plans/{plan_id}/topo-edges")
async def list_topo_edges(plan_id: int, db: Session = Depends(get_db)):
    """获取所有拓扑边"""
    return {"items": get_topo_edges(db, plan_id)}


@router.post("/floor-plans/{plan_id}/topo/trunk")
async def create_topo_trunk(plan_id: int, data: TrunkCreate, db: Session = Depends(get_db)):
    """创建主干光缆（图模型）"""
    try:
        result = create_trunk(db, plan_id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/floor-plans/{plan_id}/topo/branch-point")
async def create_topo_branch_point(plan_id: int, data: BranchPointCreate, db: Session = Depends(get_db)):
    """在主干上创建分支点（切段主干）"""
    try:
        result = create_branch_point(db, plan_id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/floor-plans/{plan_id}/topo/branch-cable")
async def create_topo_branch_cable(plan_id: int, data: BranchCableCreate, db: Session = Depends(get_db)):
    """创建分支光缆（从分支点到设备）"""
    try:
        result = create_branch_cable(db, plan_id, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/floor-plans/{plan_id}/topo-edges/{edge_id}")
async def update_topo_edge_endpoint(plan_id: int, edge_id: int, data: TopoEdgeUpdate, db: Session = Depends(get_db)):
    """更新拓扑边（拐点、名称等）"""
    result = update_topo_edge(db, plan_id, edge_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="边不存在")
    return result


@router.delete("/floor-plans/{plan_id}/topo-edges/{edge_id}")
async def delete_topo_edge_endpoint(plan_id: int, edge_id: int, db: Session = Depends(get_db)):
    """删除拓扑边"""
    success = delete_topo_edge(db, plan_id, edge_id)
    if not success:
        raise HTTPException(status_code=404, detail="边不存在")
    return {"message": "边删除成功"}


@router.put("/floor-plans/{plan_id}/topo-nodes/{node_id}")
async def update_topo_node_endpoint(plan_id: int, node_id: int, data: TopoNodeUpdate, db: Session = Depends(get_db)):
    """更新拓扑节点位置"""
    result = update_topo_node(db, plan_id, node_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="节点不存在")
    return result


@router.delete("/floor-plans/{plan_id}/topo-nodes/{node_id}")
async def delete_topo_node_endpoint(plan_id: int, node_id: int, db: Session = Depends(get_db)):
    """删除拓扑节点（连同关联的边）"""
    success = delete_topo_node(db, plan_id, node_id)
    if not success:
        raise HTTPException(status_code=404, detail="节点不存在")
    return {"message": "节点删除成功"}


@router.delete("/floor-plans/{plan_id}/cables/{cable_id}")
async def delete_cable_endpoint(plan_id: int, cable_id: int, db: Session = Depends(get_db)):
    """删除整条光缆（所有 cable_id 相同的边）"""
    success = delete_cable(db, plan_id, cable_id)
    if not success:
        raise HTTPException(status_code=404, detail="光缆不存在")
    return {"message": "光缆删除成功"}


class CableRenameBody(BaseModel):
    name: str
    force: bool = False


@router.put("/floor-plans/{plan_id}/cables/{cable_id}/rename")
async def rename_cable_endpoint(
    plan_id: int,
    cable_id: int,
    body: CableRenameBody,
    db: Session = Depends(get_db),
):
    """重命名整条光缆（更新所有分段）。重名时返回 409，除非 force=True。"""
    new_name = (body.name or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    if not body.force and is_cable_name_duplicated(db, plan_id, new_name, exclude_cable_id=cable_id):
        raise HTTPException(status_code=409, detail="光缆名称已存在")
    success = rename_cable(db, plan_id, cable_id, new_name)
    if not success:
        raise HTTPException(status_code=404, detail="光缆不存在")
    db.commit()
    return {"message": "光缆已重命名", "cable_id": cable_id, "name": new_name}


# ============ 数据链路路径 API ============

from .graph_path_service import calculate_path, calculate_all_device_paths


@router.get("/floor-plans/{plan_id}/device-path")
async def get_device_path(
    plan_id: int,
    from_device_id: int,
    to_device_id: int,
    db: Session = Depends(get_db)
):
    """计算两个设备之间的数据链路路径（基于图模型寻路）

    返回：
    - reachable: 是否可达
    - polyline: 路径折线坐标
    - hops: 路径跳信息
    - total_length: 总长度
    """
    result = calculate_path(db, plan_id, from_device_id, to_device_id)
    return result


@router.get("/floor-plans/{plan_id}/device-paths")
async def get_all_device_paths(plan_id: int, db: Session = Depends(get_db)):
    """计算所有设备到核心交换机的数据链路路径

    返回：
    {paths: {device_id: {reachable, polyline, total_length}}, diagnostic: "error message or null"}
    """
    result = calculate_all_device_paths(db, plan_id)
    return result