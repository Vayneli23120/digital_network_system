"""
Monitor Screen 服务层

提供系统监控大屏相关的业务逻辑。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
import json

from app.shared.models import Device, FloorPlan, DeviceNode, DeviceLink, BackupRecord, FaultRecord


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
            if device.status == "online" and device.updated_at:
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
    """删除设备节点"""
    node = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id,
        DeviceNode.id == node_id
    ).first()
    if not node:
        return False
    db.delete(node)
    db.commit()
    return True


def list_device_links(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取平面图上的所有设备链路"""
    links = db.query(DeviceLink).filter(DeviceLink.floor_plan_id == plan_id).all()
    return [
        {
            "id": l.id,
            "floor_plan_id": l.floor_plan_id,
            "from_node_id": l.from_node_id,
            "to_node_id": l.to_node_id,
            "link_role": l.link_role,
            "link_group": l.link_group,
            "link_type": l.link_type,
            "waypoints": json.loads(l.waypoints) if l.waypoints else None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in links
    ]


def create_device_link(
    db: Session,
    plan_id: int,
    from_node_id: int,
    to_node_id: int,
    link_role: str = "uplink",
    link_group: Optional[str] = None,
    link_type: str = "fiber"
) -> Optional[Dict[str, Any]]:
    """创建设备链路

    校验规则：
    - 两端节点必须属于该平面图
    - 禁止自环（from_node_id != to_node_id）
    - link_role 必须在白名单内（uplink/svl/portchannel-member）
    - 防止重复链路（同方向同两端）
    """
    # 校验 link_role 白名单
    valid_roles = ["uplink", "svl", "portchannel-member"]
    if link_role not in valid_roles:
        return None

    # 校验自环
    if from_node_id == to_node_id:
        return None

    # 校验两端节点属于该平面图
    from_node = db.query(DeviceNode).filter(
        DeviceNode.id == from_node_id,
        DeviceNode.floor_plan_id == plan_id
    ).first()
    to_node = db.query(DeviceNode).filter(
        DeviceNode.id == to_node_id,
        DeviceNode.floor_plan_id == plan_id
    ).first()

    if not from_node or not to_node:
        return None

    # 校验重复链路（同方向）
    existing = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.from_node_id == from_node_id,
        DeviceLink.to_node_id == to_node_id,
    ).first()
    if existing:
        # 更新已有链路而非重复创建
        existing.link_role = link_role
        existing.link_group = link_group
        existing.link_type = link_type
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "from_node_id": from_node_id,
            "to_node_id": to_node_id,
            "link_role": link_role,
            "message": "链路已更新",
        }

    # 创建新链路
    link = DeviceLink(
        floor_plan_id=plan_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        link_role=link_role,
        link_group=link_group,
        link_type=link_type,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return {
        "id": link.id,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "link_role": link_role,
        "link_group": link_group,
        "message": "链路创建成功",
    }


def update_device_link(
    db: Session,
    plan_id: int,
    link_id: int,
    link_role: Optional[str] = None,
    link_group: Optional[str] = None,
    waypoints: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """更新设备链路"""
    link = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.id == link_id
    ).first()
    if not link:
        return None

    # 校验 link_role 白名单
    if link_role:
        valid_roles = ["uplink", "svl", "portchannel-member"]
        if link_role not in valid_roles:
            return None
        link.link_role = link_role

    if link_group:
        link.link_group = link_group

    # waypoints 允许为空（用户清空所有拐点）
    if waypoints is not None:
        link.waypoints = waypoints

    link.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(link)

    return {
        "id": link.id,
        "link_role": link.link_role,
        "link_group": link.link_group,
        "waypoints": link.waypoints,
        "message": "链路更新成功",
    }


def delete_device_link(db: Session, plan_id: int, link_id: int) -> bool:
    """删除设备链路"""
    link = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.id == link_id
    ).first()
    if not link:
        return False
    db.delete(link)
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
    if device.status == "online" and device.updated_at:
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
    """获取离线设备告警列表"""
    offline_devices = db.query(Device).filter(Device.status == "offline").all()
    alerts = []
    for device in offline_devices:
        # 计算离线时长
        offline_hours = 0
        offline_str = "N/A"
        if device.updated_at:
            offline_seconds = (datetime.utcnow() - device.updated_at).total_seconds()
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
            "last_online": device.updated_at.isoformat() if device.updated_at else None,
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
    """获取平面图拓扑数据 - 包含节点、链路、聚合组、影响传播

    返回用于前端渲染拓扑图的所有数据：
    - nodes: 节点列表（包含位置、状态）
    - links: 链路列表（包含角色、分组）
    - groups: PortChannel/SVL 聚合组（逻辑链路）
    - impacted_node_ids: 受影响节点 IDs（冗余感知）

    Args:
        db: 数据库会话
        plan_id: 平面图ID

    Returns:
        拓扑数据字典
    """
    # 获取所有节点
    nodes = get_floor_plan_nodes(db, plan_id)
    node_map = {n["device_id"]: n for n in nodes}

    # 获取所有链路
    links = db.query(DeviceLink).filter(DeviceLink.floor_plan_id == plan_id).all()

    # 获取该平面图的所有 DeviceNode，避免 N+1 查询
    device_nodes = db.query(DeviceNode).filter(DeviceNode.floor_plan_id == plan_id).all()
    device_node_map = {dn.id: dn for dn in device_nodes}

    # 构建链路列表
    link_list = []
    for link in links:
        # 从内存字典获取节点信息（避免 N+1）
        from_node = device_node_map.get(link.from_node_id)
        to_node = device_node_map.get(link.to_node_id)

        if not from_node or not to_node:
            continue

        # 获取设备状态
        from_device = node_map.get(from_node.device_id)
        to_device = node_map.get(to_node.device_id)

        link_list.append({
            "id": link.id,
            "from": from_node.device_id,
            "to": to_node.device_id,
            "from_node_id": from_node.id,
            "to_node_id": to_node.id,
            "link_role": link.link_role,
            "link_group": link.link_group,
            "link_type": link.link_type,
            "waypoints": json.loads(link.waypoints) if link.waypoints else None,
            "status": _calculate_link_status(from_device, to_device, link.link_role, link.link_group),
        })

    # 构建聚合组（PortChannel/SVL）
    groups = _build_link_groups(link_list)

    # 计算受影响节点（冗余感知）
    impacted_node_ids = _propagate_impact(nodes, link_list, groups)

    # 获取主干光缆数据
    fiber_trunks = _get_fiber_trunks(db, plan_id)

    # 获取分支点数据
    fiber_branch_points = _get_fiber_branch_points(db, plan_id)

    # 获取分支光缆数据
    fiber_branch_links = _get_fiber_branch_links(db, plan_id, device_node_map)

    return {
        "nodes": nodes,
        "links": link_list,
        "groups": groups,
        "impacted_node_ids": impacted_node_ids,
        "fiber_trunks": fiber_trunks,
        "fiber_branch_points": fiber_branch_points,
        "fiber_branch_links": fiber_branch_links,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _calculate_link_status(
    from_device: Optional[Dict],
    to_device: Optional[Dict],
    link_role: str,
    link_group: Optional[str]
) -> str:
    """计算单条链路状态

    ⚠️ 设计限制说明（诚实兜底）：
    当前使用"两端设备 ICMP 可达性"推导链路状态，这在双上联冗余场景有盲区：
    - PortChannel 单条成员物理断开时，两端设备仍 reachable（设备活着，只是某条链路 down）
    - 因此"链路降级(degraded)"状态目前无法真实检测

    真正的 PortChannel 成员状态需要接口级采集（SNMP/CLI show etherchannel summary），
    这属于 P2-3"实时指标叠加"的工作，届时会新增 DeviceLink.member_status 字段。

    当前策略：诚实兜底，只返回 normal/broken，不假装能检测 degraded。
    - normal: 两端设备都 reachable（设备级在线）
    - broken: 任一端 unreachable（设备级离线）

    Args:
        from_device: 下游设备信息
        to_device: 上游设备信息
        link_role: 链路角色
        link_group: 链路分组

    Returns:
        状态: normal / broken（诚实兜底，暂无 degraded）
    """
    if not from_device or not to_device:
        return "broken"

    from_status = from_device.get("reachability", "unknown")
    to_status = to_device.get("reachability", "unknown")

    # 任一端 unreachable 则链路断开（设备级离线）
    if from_status == "unreachable" or to_status == "unreachable":
        return "broken"

    # 两端都 reachable 则正常（设备级在线）
    # 注意：这里不检测 degraded，因为 ICMP 无法感知单链路物理断开
    if from_status == "reachable" and to_status == "reachable":
        return "normal"

    # unknown 状态暂时也返回 normal（保守策略，避免误报断链）
    return "normal"


def _build_link_groups(links: List[Dict]) -> List[Dict]:
    """构建链路聚合组

    ⚠️ 设计限制说明（诚实兜底）：
    真正的 PortChannel 成员状态（接口 up/down）需要 SNMP/CLI 采集（P2-3）。
    当前基于设备 ICMP 可达性推导，无法检测"单成员物理断开"的降级场景。
    因此聚合组只判定：
    - broken: 所有成员的端设备都 unreachable（设备级离线）
    - normal: 至少有一个成员两端设备都 reachable（设备级在线）

    将接口级采集列入 P2-3，届时可真正检测部分成员失效的 degraded 状态。

    Args:
        links: 链路列表

    Returns:
        聚合组列表
    """
    groups = {}

    for link in links:
        group_id = link.get("link_group")
        if not group_id:
            continue

        if group_id not in groups:
            groups[group_id] = {
                "link_group": group_id,
                "member_link_ids": [],
                "member_links": [],
                "link_role": link["link_role"],
            }

        groups[group_id]["member_link_ids"].append(link["id"])
        groups[group_id]["member_links"].append(link)

    # 计算每组逻辑状态（诚实兜底：暂无 degraded）
    result = []
    for group_id, group in groups.items():
        # 统计成员状态
        broken_count = sum(1 for l in group["member_links"] if l["status"] == "broken")
        total_count = len(group["member_links"])

        # 诚实判定：只有全部设备级离线才判 broken
        # 单成员物理断开（设备仍活着）目前无法检测，暂不判 degraded
        if broken_count == total_count and total_count > 0:
            group["logical_status"] = "broken"
        else:
            group["logical_status"] = "normal"

        result.append(group)

    return result


def _propagate_impact(
    nodes: List[Dict],
    links: List[Dict],
    groups: List[Dict]
) -> List[int]:
    """冗余感知的影响传播计算

    核心业务逻辑：
    - 接入单上联断: 链路降级(黄)，设备不报离线
    - 接入双上联全断: 接入失联(红)
    - SVL 单核心宕: 核心红，下游不连带
    - SVL 双核心全宕: 全厂中断(橙)

    Args:
        nodes: 节点列表
        links: 链路列表
        groups: 聚合组列表

    Returns:
        受影响节点 device_id 列表（橙色脉冲，区别于自身 unreachable）
    """
    # 构建上游依赖图
    # downstream_to_upstreams: {下游device_id: [上游device_id列表]}
    downstream_to_upstreams = {}

    # PortChannel 组状态映射
    group_status = {g["link_group"]: g["logical_status"] for g in groups}

    for link in links:
        if link["link_role"] == "svl":
            # SVL 链路特殊处理，不计入下游依赖
            continue

        from_id = link["from"]
        to_id = link["to"]

        if from_id not in downstream_to_upstreams:
            downstream_to_upstreams[from_id] = []

        # PortChannel 成员按组状态判定
        if link["link_role"] == "portchannel-member" and link["link_group"]:
            # 使用组逻辑状态而非单链路状态
            group_id = link["link_group"]
            effective_status = group_status.get(group_id, "normal")

            if effective_status == "broken":
                # 组完全断开，计入失效上游
                downstream_to_upstreams[from_id].append((to_id, "broken"))
            else:
                # 组正常（当前无 degraded，诚实兜底）
                downstream_to_upstreams[from_id].append((to_id, "normal"))
        else:
            # 普通 uplink
            downstream_to_upstreams[from_id].append((to_id, link["status"]))

    # 计算受影响节点
    impacted = set()
    node_status = {n["device_id"]: n.get("reachability", "unknown") for n in nodes}

    for downstream_id, upstreams in downstream_to_upstreams.items():
        # 自身 unreachable 的节点不算"受影响"，直接离线
        if node_status.get(downstream_id) == "unreachable":
            continue

        # 统计上游状态
        broken_upstreams = [u for u, s in upstreams if s == "broken"]

        if len(broken_upstreams) == len(upstreams) and len(upstreams) > 0:
            # 所有上游都失效 → 下游受影响（橙色）
            impacted.add(downstream_id)
        elif len(broken_upstreams) > 0:
            # 部分上游失效 → 链路降级，设备不受影响
            pass

    return list(impacted)


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

    # 统计受影响设备（聚合所有平面图）
    # 注意：degraded_links 暂时恒为0，因为 ICMP 无法检测 PortChannel 单成员断开
    # 待 P2-3 接口级采集后再启用
    impacted_devices = 0

    plans = db.query(FloorPlan).all()
    for plan in plans:
        topology = get_plan_topology(db, plan.id)
        # 统计受影响设备
        impacted_devices += len(topology.get("impacted_node_ids", []))

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


# ============ 预接式光纤主干+分支辅助函数 ============

def _get_fiber_trunks(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取主干光缆列表"""
    from app.shared.models import FiberTrunkLink
    import json

    trunks = db.query(FiberTrunkLink).filter(
        FiberTrunkLink.floor_plan_id == plan_id
    ).all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "start_x_percent": t.start_x_percent,
            "start_y_percent": t.start_y_percent,
            "start_device_id": t.start_device_id,
            "end_x_percent": t.end_x_percent,
            "end_y_percent": t.end_y_percent,
            "waypoints": json.loads(t.waypoints) if t.waypoints else None,
        }
        for t in trunks
    ]


def _get_fiber_branch_points(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取分支点列表"""
    from app.shared.models import FiberBranchPoint, FiberTrunkLink

    branch_points = db.query(FiberBranchPoint).join(FiberTrunkLink).filter(
        FiberTrunkLink.floor_plan_id == plan_id
    ).all()

    return [
        {
            "id": bp.id,
            "trunk_link_id": bp.trunk_link_id,
            "name": bp.name,
            "position_percent": bp.position_percent,
            "x_percent": bp.x_percent,
            "y_percent": bp.y_percent,
        }
        for bp in branch_points
    ]


def _get_fiber_branch_links(db: Session, plan_id: int, device_node_map: Dict) -> List[Dict[str, Any]]:
    """获取分支光缆列表"""
    branch_links = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.link_role == "fiber_branch"
    ).all()

    result = []
    for link in branch_links:
        to_node = device_node_map.get(link.to_node_id)
        result.append({
            "id": link.id,
            "branch_point_id": link.branch_point_id,
            "to_device_id": to_node.device_id if to_node else None,
            "to_node_id": link.to_node_id,
            "logical_uplink_device_id": link.logical_uplink_device_id,
            "waypoints": json.loads(link.waypoints) if link.waypoints else None,
        })

    return result