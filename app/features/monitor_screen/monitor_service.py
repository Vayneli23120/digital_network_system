"""
Monitor Screen 服务层

提供系统监控大屏相关的业务逻辑。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
import json

from app.shared.models import Device, FloorPlan, DeviceNode, BackupRecord, FaultRecord
from .topo_service import ensure_device_topo_ports, sync_device_port_node_positions


def get_floor_plans(db: Session) -> List[Dict[str, Any]]:
    """获取所有平面图列表"""
    plans = db.query(FloorPlan).order_by(FloorPlan.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "image_path": p.image_path,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "node_count": db.query(DeviceNode).filter(DeviceNode.floor_plan_id == p.id).count(),
        }
        for p in plans
    ]


def get_floor_plan(db: Session, plan_id: int) -> Optional[Dict[str, Any]]:
    """获取单个平面图详情"""
    plan = db.query(FloorPlan).filter(FloorPlan.id == plan_id).first()
    if not plan:
        return None
    return {
        "id": plan.id,
        "name": plan.name,
        "image_path": plan.image_path,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


def create_floor_plan(db: Session, name: str, image_path: str) -> Dict[str, Any]:
    """创建平面图"""
    plan = FloorPlan(name=name, image_path=image_path)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id,
        "name": plan.name,
        "image_path": plan.image_path,
        "message": "平面图创建成功",
    }


def update_floor_plan(db: Session, plan_id: int, name: Optional[str] = None, image_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """更新平面图"""
    plan = db.query(FloorPlan).filter(FloorPlan.id == plan_id).first()
    if not plan:
        return None
    if name:
        plan.name = name
    if image_path:
        plan.image_path = image_path
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return {
        "id": plan.id,
        "name": plan.name,
        "image_path": plan.image_path,
        "message": "平面图更新成功",
    }


def delete_floor_plan(db: Session, plan_id: int) -> bool:
    """删除平面图（同时删除相关节点）"""
    plan = db.query(FloorPlan).filter(FloorPlan.id == plan_id).first()
    if not plan:
        return False
    db.delete(plan)
    db.commit()
    return True


def get_floor_plan_nodes(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取平面图上的所有设备节点"""
    nodes = db.query(DeviceNode).filter(DeviceNode.floor_plan_id == plan_id).all()
    result = []
    for node in nodes:
        device = db.query(Device).filter(Device.id == node.device_id).first()
        if device:
            # 计算连续在线时长
            uptime_hours = 0
            if device.reachability == "reachable" and device.updated_at:
                uptime_hours = (datetime.utcnow() - device.updated_at).total_seconds() / 3600

            # 计算使用寿命（从 purchase_date 到现在）
            lifespan_days = 0
            if device.purchase_date:
                lifespan_days = (datetime.utcnow() - device.purchase_date).days

            # 最严重的活跃故障（critical > high > medium > low）
            active_fault = db.query(FaultRecord).filter(
                FaultRecord.device_id == device.id,
                FaultRecord.status.in_(['open', 'in_progress']),
            ).order_by(
                case(
                    (FaultRecord.severity == 'critical', 0),
                    (FaultRecord.severity == 'high', 1),
                    (FaultRecord.severity == 'medium', 2),
                    else_=3,
                )
            ).first()

            result.append({
                "id": node.id,
                "device_id": device.id,
                "device_name": device.name,
                "device_type": device.device_type or "switch",
                "ip": device.ip,
                "model": device.model,
                "status": device.status,
                "reachability": device.reachability,
                "latency_ms": device.reachability_latency_ms,
                "location": device.location,
                "x_percent": float(node.x_percent),
                "y_percent": float(node.y_percent),
                "scale": float(node.scale) if node.scale else 1.0,  # 缩放比例
                "uptime_hours": round(uptime_hours, 1),
                "lifespan_days": lifespan_days,
                "active_fault_severity": active_fault.severity if active_fault else None,
                "created_at": node.created_at.isoformat() if node.created_at else None,
            })
    return result


def create_device_node(db: Session, plan_id: int, device_id: int, x_percent: float, y_percent: float) -> Optional[Dict[str, Any]]:
    """创建设备节点"""
    # 检查平面图是否存在
    plan = db.query(FloorPlan).filter(FloorPlan.id == plan_id).first()
    if not plan:
        return None

    # 检查设备是否存在
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return None

    # 检查是否已存在节点
    existing = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id,
        DeviceNode.device_id == device_id
    ).first()
    if existing:
        # 更新位置
        existing.x_percent = x_percent
        existing.y_percent = y_percent
        existing.updated_at = datetime.utcnow()
        # 确保端口节点存在并同步到新位置（图寻路基础）
        ensure_device_topo_ports(db, plan_id, device_id)
        sync_device_port_node_positions(db, plan_id, device_id)
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "device_id": device_id,
            "device_name": device.name,
            "x_percent": x_percent,
            "y_percent": y_percent,
            "message": "节点位置已更新",
        }

    # 创建新节点
    node = DeviceNode(
        floor_plan_id=plan_id,
        device_id=device_id,
        x_percent=x_percent,
        y_percent=y_percent,
    )
    db.add(node)
    db.flush()
    # 自动为设备创建默认上行端口 + 端口拓扑节点（PNetLab 式图模型基础）
    ensure_device_topo_ports(db, plan_id, device_id)
    db.commit()
    db.refresh(node)
    return {
        "id": node.id,
        "device_id": device_id,
        "device_name": device.name,
        "x_percent": x_percent,
        "y_percent": y_percent,
        "message": "节点创建成功",
    }


def update_device_node(db: Session, plan_id: int, node_id: int, x_percent: float = None, y_percent: float = None, scale: float = None) -> Optional[Dict[str, Any]]:
    """更新设备节点位置和大小"""
    node = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id,
        DeviceNode.id == node_id
    ).first()
    if not node:
        return None

    # 只更新提供的字段
    if x_percent is not None:
        node.x_percent = x_percent
    if y_percent is not None:
        node.y_percent = y_percent
    if scale is not None:
        # 限制缩放范围 0.5-3.0
        node.scale = max(0.5, min(3.0, scale))

    node.updated_at = datetime.utcnow()
    # 设备移动/缩放后同步端口拓扑节点坐标，链路端点随之联动
    sync_device_port_node_positions(db, plan_id, node.device_id)
    db.commit()
    db.refresh(node)
    return {
        "id": node.id,
        "x_percent": float(node.x_percent),
        "y_percent": float(node.y_percent),
        "scale": float(node.scale) if node.scale else 1.0,
        "message": "节点更新成功",
    }


def delete_device_node(db: Session, plan_id: int, node_id: int) -> bool:
    """删除设备节点（连带清理该平面图上的端口拓扑节点及相连的边）"""
    from app.shared.models import TopoNode, TopoEdge, DevicePort

    node = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id,
        DeviceNode.id == node_id
    ).first()
    if not node:
        return False

    # 找出该设备在本平面图上的端口拓扑节点
    port_nodes = db.query(TopoNode).join(
        DevicePort, TopoNode.port_id == DevicePort.id
    ).filter(
        TopoNode.floor_plan_id == plan_id,
        TopoNode.node_kind == "port",
        DevicePort.device_id == node.device_id,
    ).all()
    port_node_ids = [n.id for n in port_nodes]

    if port_node_ids:
        # 删除连接到这些端口节点的边
        db.query(TopoEdge).filter(
            TopoEdge.floor_plan_id == plan_id,
            (TopoEdge.a_node_id.in_(port_node_ids)) | (TopoEdge.b_node_id.in_(port_node_ids)),
        ).delete(synchronize_session=False)
        # 删除端口拓扑节点
        for n in port_nodes:
            db.delete(n)

    db.delete(node)
    db.commit()
    return True


def get_device_detail(db: Session, device_id: int) -> Optional[Dict[str, Any]]:
    """获取设备详情（用于弹窗显示）"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return None

    # 计算连续在线时长
    uptime_hours = 0
    uptime_str = "N/A"
    if device.reachability == "reachable" and device.updated_at:
        uptime_seconds = (datetime.utcnow() - device.updated_at).total_seconds()
        uptime_hours = uptime_seconds / 3600
        # 格式化为天/小时
        days = int(uptime_hours / 24)
        hours = int(uptime_hours % 24)
        if days > 0:
            uptime_str = f"{days}天{hours}小时"
        else:
            uptime_str = f"{hours}小时"

    # 计算使用寿命（从 purchase_date 到现在）
    lifespan_days = 0
    lifespan_str = "N/A"
    if device.purchase_date:
        lifespan_days = (datetime.utcnow() - device.purchase_date).days
        years = lifespan_days // 365
        days = lifespan_days % 365
        if years > 0:
            lifespan_str = f"{years}年{days}天"
        else:
            lifespan_str = f"{days}天"

    # 最近备份
    last_backup = db.query(BackupRecord).filter(
        BackupRecord.device_id == device_id
    ).order_by(BackupRecord.backup_time.desc()).first()
    last_backup_str = "N/A"
    if last_backup and last_backup.backup_time:
        last_backup_str = last_backup.backup_time.strftime("%Y-%m-%d %H:%M")

    # 最近故障
    last_fault = db.query(FaultRecord).filter(
        FaultRecord.device_id == device_id,
        FaultRecord.status != "closed"
    ).order_by(FaultRecord.created_at.desc()).first()
    last_fault_info = None
    if last_fault:
        last_fault_info = {
            "fault_no": last_fault.fault_no,
            "severity": last_fault.severity,
            "description": last_fault.description[:50] if last_fault.description else "",
            "status": last_fault.status,
            "created_at": last_fault.created_at.strftime("%Y-%m-%d") if last_fault.created_at else None,
        }

    return {
        # 基础信息
        "id": device.id,
        "name": device.name,
        "ip": device.ip,
        "model": device.model,
        "device_type": device.device_type or "switch",
        "status": device.status,
        "location": device.location,
        "vendor": device.vendor,
        # 实时状态
        "uptime_hours": round(uptime_hours, 1),
        "uptime_str": uptime_str,
        "ping_latency": f"{device.reachability_latency_ms}ms" if device.reachability_latency_ms else None,
        # 使用寿命
        "lifespan_days": lifespan_days,
        "lifespan_str": lifespan_str,
        "purchase_date": device.purchase_date.strftime("%Y-%m-%d") if device.purchase_date else None,
        # 运维记录
        "last_backup": last_backup_str,
        "last_fault": last_fault_info,
    }


def get_offline_alerts(db: Session) -> List[Dict[str, Any]]:
    """获取离线设备告警列表（基于 reachability）"""
    # Phase2: 统一以 reachability 驱动设备状态
    offline_devices = db.query(Device).filter(Device.reachability == "unreachable").all()
    alerts = []
    for device in offline_devices:
        # 计算离线时长
        offline_hours = 0
        offline_str = "N/A"
        if device.last_reachability_check:
            offline_seconds = (datetime.utcnow() - device.last_reachability_check).total_seconds()
            offline_hours = offline_seconds / 3600
            days = int(offline_hours / 24)
            hours = int(offline_hours % 24)
            if days > 0:
                offline_str = f"{days}天{hours}小时"
            else:
                offline_str = f"{hours}小时"

        alerts.append({
            "device_id": device.id,
            "device_name": device.name,
            "ip": device.ip,
            "location": device.location,
            "device_type": device.device_type or "switch",
            "offline_hours": round(offline_hours, 1),
            "offline_str": offline_str,
            "last_online": device.last_reachability_check.isoformat() if device.last_reachability_check else None,
            "reachability": device.reachability,
        })
    return alerts


def get_available_devices(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取可用于创建节点的设备列表（排除已在该平面图上的设备）"""
    # 获取已在该平面图上的设备ID
    existing_device_ids = [
        n.device_id for n in db.query(DeviceNode).filter(DeviceNode.floor_plan_id == plan_id).all()
    ]

    # 获取所有不在该平面图上的设备
    devices = db.query(Device).filter(Device.id.notin_(existing_device_ids)).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "ip": d.ip,
            "device_type": d.device_type or "switch",
            "status": d.status,
            "location": d.location,
        }
        for d in devices
    ]


def get_plan_snapshot(db: Session, plan_id: int) -> Dict[str, Any]:
    """获取平面图全量快照 - 用于 WebSocket 重连对账

    返回所有节点完整状态 + 统计数据，前端重连时直接覆盖本地状态，
    防止乐观增减导致的计数漂移。

    Args:
        db: 数据库会话
        plan_id: 平面图ID

    Returns:
        {
            "nodes": [{...}],  # 全量节点状态
            "stats": {         # 统计数据（以 reachability 为准）
                "total": N,
                "reachable": N,
                "unreachable": N,
                "unknown": N
            },
            "timestamp": "ISO时间"
        }
    """
    # 获取所有节点
    nodes = get_floor_plan_nodes(db, plan_id)

    # 按 reachability 统计（这是可达性监控的真实状态）
    stats = {
        "total": len(nodes),
        "reachable": 0,
        "unreachable": 0,
        "unknown": 0,
    }

    for node in nodes:
        reachability = node.get("reachability", "unknown")
        if reachability == "reachable":
            stats["reachable"] += 1
        elif reachability == "unreachable":
            stats["unreachable"] += 1
        else:
            stats["unknown"] += 1

    return {
        "nodes": nodes,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_plan_topology(db: Session, plan_id: int) -> Dict[str, Any]:
    """获取平面图拓扑数据（Gen3 图模型）

    返回用于前端渲染数字孪生拓扑的所有数据：
    - nodes: 设备节点（位置 + 可达性状态）
    - topo_nodes: 拓扑节点（设备端口 port + 接头/分支点 junction）
    - topo_edges: 拓扑边（线缆，自带拐点 waypoints）
    - cables: 按 cable_id 聚合的光缆（主干/分支）
    - device_paths: 各设备沿真实 TopoEdge 拓扑到核心的图寻路折线

    Args:
        db: 数据库会话
        plan_id: 平面图ID

    Returns:
        拓扑数据字典
    """
    from .topo_service import get_topo_nodes, get_topo_edges, get_cables
    from .graph_path_service import calculate_all_device_paths

    nodes = get_floor_plan_nodes(db, plan_id)
    topo_nodes = get_topo_nodes(db, plan_id)
    topo_edges = get_topo_edges(db, plan_id)
    cables = get_cables(db, plan_id)
    device_paths = calculate_all_device_paths(db, plan_id)

    return {
        "nodes": nodes,
        "topo_nodes": topo_nodes,
        "topo_edges": topo_edges,
        "cables": cables,
        "device_paths": device_paths,
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_global_summary(db: Session) -> Dict[str, Any]:
    """获取全厂健康度汇总 - 用于大屏顶部健康条

    聚合所有平面图数据，返回全厂整体健康状态。

    Args:
        db: 数据库会话

    Returns:
        {
            "health_score": 98.2,  # 健康度百分比
            "total_devices": 1240,
            "reachable": 1218,
            "unreachable": 22,
            "unknown": 0,
            "degraded_links": 8,   # 降级链路数
            "impacted_devices": 35, # 受影响设备数
            "active_alerts": 14,   # 活跃告警数
        }
    """
    # 统计所有在管设备（deployment_status='in-use'）
    from sqlalchemy import func

    devices = db.query(Device).filter(Device.deployment_status == 'in-use').all()

    total = len(devices)
    reachable = sum(1 for d in devices if d.reachability == 'reachable')
    unreachable = sum(1 for d in devices if d.reachability == 'unreachable')
    unknown = total - reachable - unreachable

    # 计算健康度（reachable / total）
    health_score = round((reachable / total * 100) if total > 0 else 100, 1)

    # 受影响设备：接口级采集（P2-3）落地前暂恒 0
    # Gen3 图模型下，"受影响"应由图寻路连通性推导，待实时指标叠加阶段启用
    impacted_devices = 0

    # 活跃告警数（未关闭的告警）
    # 注意：项目使用 FaultRecord 存储故障，AlertRecord 不存在
    try:
        from app.shared.models import FaultRecord
        active_alerts = db.query(FaultRecord).filter(
            FaultRecord.status.in_(['open', 'in_progress'])
        ).count()
    except Exception:
        # FaultRecord 表可能不存在或查询失败
        active_alerts = 0

    return {
        "health_score": health_score,
        "total_devices": total,
        "reachable": reachable,
        "unreachable": unreachable,
        "unknown": unknown,
        "degraded_links": 0,  # 暂时恒0，待 P2-3 接口级采集后启用
        "impacted_devices": impacted_devices,
        "active_alerts": active_alerts,
        "timestamp": datetime.utcnow().isoformat(),
    }
