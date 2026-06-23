"""
Fiber Trunk Service - 预接式光纤主干+分支拓扑服务

提供主干光缆、分支点、分支光缆的 CRUD 操作。
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.shared.models import (
    FiberTrunkLink, FiberBranchPoint, DeviceLink, DeviceNode, Device, FloorPlan
)


# ============ 主干光缆 CRUD ============

def list_fiber_trunks(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取平面图上的所有主干光缆"""
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
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in trunks
    ]


def create_fiber_trunk(db: Session, plan_id: int, data) -> Dict[str, Any]:
    """创建主干光缆"""
    trunk = FiberTrunkLink(
        floor_plan_id=plan_id,
        name=data.name,
        start_x_percent=data.start_x_percent,
        start_y_percent=data.start_y_percent,
        start_device_id=data.start_device_id,
        end_x_percent=data.end_x_percent,
        end_y_percent=data.end_y_percent,
        waypoints=data.waypoints,
    )
    db.add(trunk)
    db.commit()
    db.refresh(trunk)
    return {
        "id": trunk.id,
        "name": trunk.name,
        "start_x_percent": trunk.start_x_percent,
        "start_y_percent": trunk.start_y_percent,
        "start_device_id": trunk.start_device_id,
        "end_x_percent": trunk.end_x_percent,
        "end_y_percent": trunk.end_y_percent,
        "waypoints": json.loads(trunk.waypoints) if trunk.waypoints else None,
    }


def update_fiber_trunk(db: Session, plan_id: int, trunk_id: int, data) -> Optional[Dict[str, Any]]:
    """更新主干光缆"""
    trunk = db.query(FiberTrunkLink).filter(
        FiberTrunkLink.id == trunk_id,
        FiberTrunkLink.floor_plan_id == plan_id
    ).first()
    if not trunk:
        return None

    if data.name is not None:
        trunk.name = data.name
    if data.waypoints is not None:
        trunk.waypoints = data.waypoints
    if data.start_x_percent is not None:
        trunk.start_x_percent = data.start_x_percent
    if data.start_y_percent is not None:
        trunk.start_y_percent = data.start_y_percent
    if data.start_device_id is not None:
        trunk.start_device_id = data.start_device_id
    if data.end_x_percent is not None:
        trunk.end_x_percent = data.end_x_percent
    if data.end_y_percent is not None:
        trunk.end_y_percent = data.end_y_percent

    trunk.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(trunk)
    return {
        "id": trunk.id,
        "name": trunk.name,
        "start_x_percent": trunk.start_x_percent,
        "start_y_percent": trunk.start_y_percent,
        "start_device_id": trunk.start_device_id,
        "end_x_percent": trunk.end_x_percent,
        "end_y_percent": trunk.end_y_percent,
        "waypoints": json.loads(trunk.waypoints) if trunk.waypoints else None,
    }


def delete_fiber_trunk(db: Session, plan_id: int, trunk_id: int) -> bool:
    """删除主干光缆（连带删除分支点和分支光缆）"""
    trunk = db.query(FiberTrunkLink).filter(
        FiberTrunkLink.id == trunk_id,
        FiberTrunkLink.floor_plan_id == plan_id
    ).first()
    if not trunk:
        return False

    # 删除关联的分支光缆（通过 branch_point_id）
    branch_points = db.query(FiberBranchPoint).filter(
        FiberBranchPoint.trunk_link_id == trunk_id
    ).all()
    for bp in branch_points:
        db.query(DeviceLink).filter(DeviceLink.branch_point_id == bp.id).delete()

    db.delete(trunk)
    db.commit()
    return True


# ============ 分支点 CRUD ============

def list_branch_points(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取平面图上的所有分支点"""
    # 通过 trunk 关联过滤 plan_id
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
            "created_at": bp.created_at.isoformat() if bp.created_at else None,
        }
        for bp in branch_points
    ]


def create_branch_point(db: Session, plan_id: int, data) -> Dict[str, Any]:
    """在主干上创建分支点"""
    # 验证主干存在
    trunk = db.query(FiberTrunkLink).filter(
        FiberTrunkLink.id == data.trunk_link_id,
        FiberTrunkLink.floor_plan_id == plan_id
    ).first()
    if not trunk:
        raise ValueError("主干光缆不存在")

    # 计算分支点坐标（如果未提供）
    x_percent = data.x_percent
    y_percent = data.y_percent

    if x_percent is None or y_percent is None:
        # 根据位置百分比计算坐标
        x_percent, y_percent = calculate_position_on_trunk(
            trunk, data.position_percent
        )

    bp = FiberBranchPoint(
        trunk_link_id=data.trunk_link_id,
        name=data.name,
        position_percent=data.position_percent,
        x_percent=x_percent,
        y_percent=y_percent,
    )
    db.add(bp)
    db.commit()
    db.refresh(bp)
    return {
        "id": bp.id,
        "trunk_link_id": bp.trunk_link_id,
        "name": bp.name,
        "position_percent": bp.position_percent,
        "x_percent": bp.x_percent,
        "y_percent": bp.y_percent,
    }


def update_branch_point(db: Session, plan_id: int, bp_id: int, data) -> Optional[Dict[str, Any]]:
    """更新分支点"""
    bp = db.query(FiberBranchPoint).join(FiberTrunkLink).filter(
        FiberBranchPoint.id == bp_id,
        FiberTrunkLink.floor_plan_id == plan_id
    ).first()
    if not bp:
        return None

    if data.name is not None:
        bp.name = data.name
    if data.position_percent is not None:
        bp.position_percent = data.position_percent
        # 重新计算坐标
        bp.x_percent, bp.y_percent = calculate_position_on_trunk(
            bp.trunk_link, data.position_percent
        )
    if data.x_percent is not None:
        bp.x_percent = data.x_percent
    if data.y_percent is not None:
        bp.y_percent = data.y_percent

    db.commit()
    db.refresh(bp)
    return {
        "id": bp.id,
        "name": bp.name,
        "position_percent": bp.position_percent,
        "x_percent": bp.x_percent,
        "y_percent": bp.y_percent,
    }


def delete_branch_point(db: Session, plan_id: int, bp_id: int) -> bool:
    """删除分支点（连带删除分支光缆）"""
    bp = db.query(FiberBranchPoint).join(FiberTrunkLink).filter(
        FiberBranchPoint.id == bp_id,
        FiberTrunkLink.floor_plan_id == plan_id
    ).first()
    if not bp:
        return False

    # 删除关联的分支光缆
    db.query(DeviceLink).filter(DeviceLink.branch_point_id == bp_id).delete()
    db.delete(bp)
    db.commit()
    return True


# ============ 分支光缆 CRUD ============

def create_branch_link(db: Session, plan_id: int, data) -> Dict[str, Any]:
    """创建分支光缆（从分支点到设备）"""
    # 验证分支点存在
    bp = db.query(FiberBranchPoint).join(FiberTrunkLink).filter(
        FiberBranchPoint.id == data.branch_point_id,
        FiberTrunkLink.floor_plan_id == plan_id
    ).first()
    if not bp:
        raise ValueError("分支点不存在")

    # 验证设备存在且有节点
    device = db.query(Device).filter(Device.id == data.to_device_id).first()
    if not device:
        raise ValueError("设备不存在")

    device_node = db.query(DeviceNode).filter(
        DeviceNode.device_id == data.to_device_id,
        DeviceNode.floor_plan_id == plan_id
    ).first()
    if not device_node:
        raise ValueError("设备节点不存在")

    # 创建分支光缆（使用 DeviceLink 表，link_role='fiber_branch'）
    # 分支光缆的 from_node_id 为 NULL（因为连接的是分支点，不是节点）
    link = DeviceLink(
        floor_plan_id=plan_id,
        from_node_id=None,  # NULL 表示从分支点连接（无源节点）
        to_node_id=device_node.id,
        link_role="fiber_branch",
        link_type="fiber",
        branch_point_id=data.branch_point_id,
        logical_uplink_device_id=data.logical_uplink_device_id,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return {
        "id": link.id,
        "branch_point_id": link.branch_point_id,
        "to_device_id": device_node.device_id,
        "to_node_id": link.to_node_id,
        "logical_uplink_device_id": link.logical_uplink_device_id,
        "waypoints": json.loads(link.waypoints) if link.waypoints else None,
    }


def update_branch_link(db: Session, plan_id: int, link_id: int, waypoints: str) -> Optional[Dict[str, Any]]:
    """更新分支光缆拐点"""
    link = db.query(DeviceLink).filter(
        DeviceLink.id == link_id,
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.link_role == "fiber_branch"
    ).first()
    if not link:
        return None

    link.waypoints = waypoints
    link.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(link)

    return {
        "id": link.id,
        "branch_point_id": link.branch_point_id,
        "waypoints": json.loads(link.waypoints) if link.waypoints else None,
    }


def delete_branch_link(db: Session, plan_id: int, link_id: int) -> bool:
    """删除分支光缆"""
    link = db.query(DeviceLink).filter(
        DeviceLink.id == link_id,
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.link_role == "fiber_branch"
    ).first()
    if not link:
        return False

    db.delete(link)
    db.commit()
    return True


# ============ 辅助函数 ============

def calculate_position_on_trunk(trunk: FiberTrunkLink, position_percent: float) -> tuple:
    """根据位置百分比计算主干上的坐标

    Args:
        trunk: 主干光缆对象
        position_percent: 位置百分比 (0-100)

    Returns:
        (x_percent, y_percent) 坐标百分比
    """
    # 获取主干路径点（起点、拐点、终点）
    points = [(trunk.start_x_percent, trunk.start_y_percent)]

    if trunk.waypoints:
        try:
            waypoints = json.loads(trunk.waypoints)
            for wp in waypoints:
                points.append((wp["x"], wp["y"]))
        except:
            pass

    points.append((trunk.end_x_percent, trunk.end_y_percent))

    # 计算总长度（百分比距离）
    total_length = 0
    segment_lengths = []
    for i in range(1, len(points)):
        dx = points[i][0] - points[i-1][0]
        dy = points[i][1] - points[i-1][1]
        length = (dx**2 + dy**2)**0.5
        segment_lengths.append(length)
        total_length += length

    # 根据位置百分比找到对应点
    target_length = total_length * position_percent / 100
    accumulated = 0

    for i, seg_len in enumerate(segment_lengths):
        if accumulated + seg_len >= target_length:
            # 在这个段上
            remaining = target_length - accumulated
            ratio = remaining / seg_len if seg_len > 0 else 0
            x = points[i][0] + ratio * (points[i+1][0] - points[i][0])
            y = points[i][1] + ratio * (points[i+1][1] - points[i][1])
            return x, y
        accumulated += seg_len

    # 如果超出范围，返回终点
    return trunk.end_x_percent, trunk.end_y_percent