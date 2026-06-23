"""
Link Path Service - 数据链路路径计算服务

计算设备之间的数据链路路径（沿着光纤拓扑）。

路径计算逻辑：
1. 判断设备所在区域：
   - 分支节点区域：接入层交换机（office_switch, server_switch, uce）
   - 核心交换机区域：核心交换机（core_switch）

2. 源是分支交换机，目标是核心交换机：
   分支交换机 → 分支点 → 主干（沿主干）→ 主干起始点 → 核心交换机

3. 源是核心交换机，目标是分支交换机：
   核心交换机 → 主干起始点 → 主干（沿主干往分支方向）→ 分支点 → 分支交换机
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import json

from app.shared.models import (
    Device, DeviceNode, DeviceLink, FiberTrunkLink, FiberBranchPoint, FloorPlan
)


# 分支交换机类型（接入层）
BRANCH_SWITCH_TYPES = ["office_switch", "server_switch", "uce"]

# 核心交换机类型
CORE_SWITCH_TYPES = ["core_switch"]


def get_device_role(db: Session, device_id: int) -> str:
    """判断设备角色

    Returns:
        "core" - 核心交换机
        "branch" - 分支交换机（接入层）
        "other" - 其他设备类型
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        return "other"

    device_type = device.device_type or "switch"

    if device_type in CORE_SWITCH_TYPES:
        return "core"
    elif device_type in BRANCH_SWITCH_TYPES:
        return "branch"
    else:
        return "other"


def find_branch_point_for_device(db: Session, plan_id: int, device_id: int) -> Optional[FiberBranchPoint]:
    """查找设备连接的分支点

    Args:
        db: 数据库会话
        plan_id: 平面图ID
        device_id: 设备ID

    Returns:
        设备连接的分支点，如果没有则返回 None
    """
    # 查找设备的 DeviceNode
    device_node = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id,
        DeviceNode.device_id == device_id
    ).first()

    if not device_node:
        return None

    # 查找该设备的 fiber_branch_link（分支光缆）
    branch_link = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.to_node_id == device_node.id,
        DeviceLink.link_role == "fiber_branch"
    ).first()

    if not branch_link or not branch_link.branch_point_id:
        return None

    # 返回分支点
    return db.query(FiberBranchPoint).filter(
        FiberBranchPoint.id == branch_link.branch_point_id
    ).first()


def get_branch_link_for_device(db: Session, plan_id: int, device_id: int) -> Optional[Dict[str, Any]]:
    """获取设备连接的分支光缆完整信息（包括拐点）

    Args:
        db: 数据库会话
        plan_id: 平面图ID
        device_id: 设备ID

    Returns:
        分支光缆信息 {id, branch_point_id, waypoints}，如果没有则返回 None
    """
    # 查找设备的 DeviceNode
    device_node = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id,
        DeviceNode.device_id == device_id
    ).first()

    if not device_node:
        return None

    # 查找该设备的 fiber_branch_link（分支光缆）
    branch_link = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.to_node_id == device_node.id,
        DeviceLink.link_role == "fiber_branch"
    ).first()

    if not branch_link or not branch_link.branch_point_id:
        return None

    # 解析拐点
    waypoints = []
    if branch_link.waypoints:
        try:
            waypoints = json.loads(branch_link.waypoints)
        except:
            waypoints = []

    return {
        "id": branch_link.id,
        "branch_point_id": branch_link.branch_point_id,
        "waypoints": waypoints,
    }


def find_trunk_for_branch_point(db: Session, branch_point_id: int) -> Optional[FiberTrunkLink]:
    """查找分支点所属的主干

    Args:
        db: 数据库会话
        branch_point_id: 分支点ID

    Returns:
        分支点所属的主干光缆
    """
    branch_point = db.query(FiberBranchPoint).filter(
        FiberBranchPoint.id == branch_point_id
    ).first()

    if not branch_point:
        return None

    return db.query(FiberTrunkLink).filter(
        FiberTrunkLink.id == branch_point.trunk_link_id
    ).first()


def get_trunk_path_points(trunk: FiberTrunkLink, reverse: bool = False) -> List[Dict[str, Any]]:
    """获取主干路径点列表

    Args:
        trunk: 主干光缆对象
        reverse: 是否反向（从终点到起点）

    Returns:
        路径点列表 [{x_percent, y_percent}, ...]
    """
    points = []

    # 起点
    points.append({
        "x_percent": trunk.start_x_percent,
        "y_percent": trunk.start_y_percent,
        "type": "trunk_start_point"
    })

    # 拐点
    if trunk.waypoints:
        try:
            waypoints = json.loads(trunk.waypoints)
            for wp in waypoints:
                if wp.get("x") is not None and wp.get("y") is not None:
                    points.append({
                        "x_percent": wp["x"],
                        "y_percent": wp["y"],
                        "type": "trunk_waypoint"
                    })
        except:
            pass

    # 终点
    points.append({
        "x_percent": trunk.end_x_percent,
        "y_percent": trunk.end_y_percent,
        "type": "trunk_end_point"
    })

    # 如果需要反向，反转列表
    if reverse:
        points = points[::-1]
        # 反转后重新标记类型
        for i, p in enumerate(points):
            if i == 0:
                p["type"] = "trunk_end_point"
            elif i == len(points) - 1:
                p["type"] = "trunk_start_point"
            else:
                p["type"] = "trunk_waypoint"

    return points


def calculate_link_path(db: Session, plan_id: int, source_device_id: int, target_device_id: int) -> Optional[List[Dict[str, Any]]]:
    """计算数据链路路径

    根据源设备和目标设备的角色，计算沿着光纤拓扑的路径：

    - 源是分支交换机，目标是核心交换机：
      分支交换机 → 分支点 → 主干（从分支点位置沿主干到起点）→ 主干起始点 → 核心交换机

    - 源是核心交换机，目标是分支交换机：
      核心交换机 → 主干起始点 → 主干（从起点沿主干到分支点位置）→ 分支点 → 分支交换机

    Args:
        db: 数据库会话
        plan_id: 平面图ID
        source_device_id: 源设备ID
        target_device_id: 目标设备ID

    Returns:
        路径点列表，每个点包含 type, device_id/branch_point_id/x_percent/y_percent 等
    """
    # 判断设备角色
    source_role = get_device_role(db, source_device_id)
    target_role = get_device_role(db, target_device_id)

    # 获取设备节点位置
    source_node = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id,
        DeviceNode.device_id == source_device_id
    ).first()

    target_node = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id,
        DeviceNode.device_id == target_device_id
    ).first()

    if not source_node or not target_node:
        return None

    path = []

    # 场景1：源是分支交换机，目标是核心交换机
    if source_role == "branch" and target_role == "core":
        # 1. 源设备位置
        path.append({
            "type": "device",
            "role": "source",
            "device_id": source_device_id,
            "x_percent": float(source_node.x_percent),
            "y_percent": float(source_node.y_percent),
        })

        # 2. 获取分支光缆信息（包括拐点）
        branch_link_info = get_branch_link_for_device(db, plan_id, source_device_id)
        if not branch_link_info:
            return None  # 没有光纤拓扑，无法计算路径

        # 3. 添加分支光缆的拐点（按顺序）
        if branch_link_info.get("waypoints") and len(branch_link_info["waypoints"]) > 0:
            for wp in branch_link_info["waypoints"]:
                if wp.get("x") is not None and wp.get("y") is not None:
                    path.append({
                        "type": "branch_link_waypoint",
                        "x_percent": wp["x"],
                        "y_percent": wp["y"],
                    })

        # 4. 查找源设备连接的分支点
        branch_point = db.query(FiberBranchPoint).filter(
            FiberBranchPoint.id == branch_link_info["branch_point_id"]
        ).first()

        if not branch_point:
            return None

        # 分支点位置
        path.append({
            "type": "branch_point",
            "id": branch_point.id,
            "x_percent": branch_point.x_percent,
            "y_percent": branch_point.y_percent,
        })

        # 5. 查找分支点所属的主干
        trunk = find_trunk_for_branch_point(db, branch_point.id)
        if not trunk:
            return None

        # 6. 计算分支点在主干上的位置百分比
        bp_position = branch_point.position_percent

        # 7. 添加主干路径（从分支点沿主干到起点）
        trunk_waypoints = get_trunk_waypoints_between(trunk, bp_position, 0)
        if trunk_waypoints:
            # 反转waypoints，因为是从分支点往起点走
            trunk_waypoints = trunk_waypoints[::-1]
            # 跳过第一个点（接近分支点）和最后一个点（接近主干起点），避免重复
            for i, wp in enumerate(trunk_waypoints):
                if i == 0 or i == len(trunk_waypoints) - 1:
                    continue  # 跳过首尾点
                path.append({
                    "type": "trunk_waypoint",
                    "x_percent": wp["x_percent"],
                    "y_percent": wp["y_percent"],
                })

        # 8. 主干起始点位置
        if trunk.start_device_id == target_device_id:
            # 主干起点正好连接目标核心交换机
            path.append({
                "type": "trunk_start",
                "device_id": trunk.start_device_id,
                "x_percent": trunk.start_x_percent,
                "y_percent": trunk.start_y_percent,
            })
        else:
            # 主干起点位置
            path.append({
                "type": "trunk_start_point",
                "x_percent": trunk.start_x_percent,
                "y_percent": trunk.start_y_percent,
            })

        # 9. 目标核心交换机位置
        path.append({
            "type": "device",
            "role": "target",
            "device_id": target_device_id,
            "x_percent": float(target_node.x_percent),
            "y_percent": float(target_node.y_percent),
        })

        return path

    # 场景2：源是核心交换机，目标是分支交换机
    elif source_role == "core" and target_role == "branch":
        # 1. 源核心交换机位置
        path.append({
            "type": "device",
            "role": "source",
            "device_id": source_device_id,
            "x_percent": float(source_node.x_percent),
            "y_percent": float(source_node.y_percent),
        })

        # 2. 获取目标设备连接的分支光缆信息
        branch_link_info = get_branch_link_for_device(db, plan_id, target_device_id)
        if not branch_link_info:
            return None

        # 3. 查找分支点
        branch_point = db.query(FiberBranchPoint).filter(
            FiberBranchPoint.id == branch_link_info["branch_point_id"]
        ).first()
        if not branch_point:
            return None

        # 4. 查找分支点所属的主干
        trunk = find_trunk_for_branch_point(db, branch_point.id)
        if not trunk:
            return None

        # 5. 主干起始点位置（从核心出发）
        if trunk.start_device_id == source_device_id:
            path.append({
                "type": "trunk_start",
                "device_id": trunk.start_device_id,
                "x_percent": trunk.start_x_percent,
                "y_percent": trunk.start_y_percent,
            })
        else:
            path.append({
                "type": "trunk_start_point",
                "x_percent": trunk.start_x_percent,
                "y_percent": trunk.start_y_percent,
            })

        # 6. 沿主干到分支点位置
        bp_position = branch_point.position_percent
        trunk_waypoints = get_trunk_waypoints_between(trunk, 0, bp_position)
        if trunk_waypoints:
            # 跳过第一个点（接近主干起点）和最后一个点（接近分支点），避免重复
            for i, wp in enumerate(trunk_waypoints):
                if i == 0 or i == len(trunk_waypoints) - 1:
                    continue  # 跳过首尾点
                path.append({
                    "type": "trunk_waypoint",
                    "x_percent": wp["x_percent"],
                    "y_percent": wp["y_percent"],
                })

        # 7. 分支点位置
        path.append({
            "type": "branch_point",
            "id": branch_point.id,
            "x_percent": branch_point.x_percent,
            "y_percent": branch_point.y_percent,
        })

        # 8. 分支光缆拐点（如果有）- 从分支点到设备
        if branch_link_info.get("waypoints") and len(branch_link_info["waypoints"]) > 0:
            for wp in branch_link_info["waypoints"]:
                if wp.get("x") is not None and wp.get("y") is not None:
                    path.append({
                        "type": "branch_link_waypoint",
                        "x_percent": wp["x"],
                        "y_percent": wp["y"],
                    })

        # 9. 目标分支交换机位置
        path.append({
            "type": "device",
            "role": "target",
            "device_id": target_device_id,
            "x_percent": float(target_node.x_percent),
            "y_percent": float(target_node.y_percent),
        })

        return path

    # 场景3：源是分支交换机，目标是分支交换机（同一主干）
    elif source_role == "branch" and target_role == "branch":
        # 1. 获取两个设备的分支光缆信息
        source_branch_link = get_branch_link_for_device(db, plan_id, source_device_id)
        target_branch_link = get_branch_link_for_device(db, plan_id, target_device_id)

        if not source_branch_link or not target_branch_link:
            return None

        # 2. 查找两个设备各自的分支点
        source_branch_point = db.query(FiberBranchPoint).filter(
            FiberBranchPoint.id == source_branch_link["branch_point_id"]
        ).first()
        target_branch_point = db.query(FiberBranchPoint).filter(
            FiberBranchPoint.id == target_branch_link["branch_point_id"]
        ).first()

        if not source_branch_point or not target_branch_point:
            return None

        # 3. 查找各自的主干
        source_trunk = find_trunk_for_branch_point(db, source_branch_point.id)
        target_trunk = find_trunk_for_branch_point(db, target_branch_point.id)

        if not source_trunk or not target_trunk:
            return None

        # 4. 源设备位置
        path.append({
            "type": "device",
            "role": "source",
            "device_id": source_device_id,
            "x_percent": float(source_node.x_percent),
            "y_percent": float(source_node.y_percent),
        })

        # 5. 源分支光缆拐点（如果有）
        if source_branch_link.get("waypoints") and len(source_branch_link["waypoints"]) > 0:
            for wp in source_branch_link["waypoints"]:
                if wp.get("x") is not None and wp.get("y") is not None:
                    path.append({
                        "type": "branch_link_waypoint",
                        "x_percent": wp["x"],
                        "y_percent": wp["y"],
                    })

        # 6. 源分支点位置
        path.append({
            "type": "branch_point",
            "id": source_branch_point.id,
            "x_percent": source_branch_point.x_percent,
            "y_percent": source_branch_point.y_percent,
        })

        # 7. 检查是否在同一主干上
        if source_trunk.id == target_trunk.id:
            # 同一主干：沿主干从源分支点到目标分支点
            source_bp_pos = source_branch_point.position_percent
            target_bp_pos = target_branch_point.position_percent

            trunk_waypoints = get_trunk_waypoints_between(source_trunk, source_bp_pos, target_bp_pos)
            if trunk_waypoints:
                # 跳过第一个点（接近源分支点）和最后一个点（接近目标分支点），避免重复
                for i, wp in enumerate(trunk_waypoints):
                    if i == 0 or i == len(trunk_waypoints) - 1:
                        continue
                    path.append({
                        "type": "trunk_waypoint",
                        "x_percent": wp["x_percent"],
                        "y_percent": wp["y_percent"],
                    })
        else:
            # 不同主干：需要经过核心
            # 源主干 → 核心 → 目标主干
            source_trunk_waypoints = get_trunk_waypoints_between(source_trunk, source_branch_point.position_percent, 0)
            if source_trunk_waypoints:
                source_trunk_waypoints = source_trunk_waypoints[::-1]  # 反转，往起点走
                # 跳过第一个点（接近源分支点）和最后一个点（接近主干起点）
                for i, wp in enumerate(source_trunk_waypoints):
                    if i == 0 or i == len(source_trunk_waypoints) - 1:
                        continue
                    path.append({
                        "type": "trunk_waypoint",
                        "x_percent": wp["x_percent"],
                        "y_percent": wp["y_percent"],
                    })

            # 源主干起点
            path.append({
                "type": "trunk_start_point",
                "x_percent": source_trunk.start_x_percent,
                "y_percent": source_trunk.start_y_percent,
            })

            # 目标主干起点
            path.append({
                "type": "trunk_start_point",
                "x_percent": target_trunk.start_x_percent,
                "y_percent": target_trunk.start_y_percent,
            })

            target_trunk_waypoints = get_trunk_waypoints_between(target_trunk, 0, target_branch_point.position_percent)
            if target_trunk_waypoints:
                # 跳过第一个点（接近主干起点）和最后一个点（接近目标分支点）
                for i, wp in enumerate(target_trunk_waypoints):
                    if i == 0 or i == len(target_trunk_waypoints) - 1:
                        continue
                    path.append({
                        "type": "trunk_waypoint",
                        "x_percent": wp["x_percent"],
                        "y_percent": wp["y_percent"],
                    })

        # 8. 目标分支点位置
        path.append({
            "type": "branch_point",
            "id": target_branch_point.id,
            "x_percent": target_branch_point.x_percent,
            "y_percent": target_branch_point.y_percent,
        })

        # 9. 目标分支光缆拐点（如果有）
        if target_branch_link.get("waypoints") and len(target_branch_link["waypoints"]) > 0:
            for wp in target_branch_link["waypoints"]:
                if wp.get("x") is not None and wp.get("y") is not None:
                    path.append({
                        "type": "branch_link_waypoint",
                        "x_percent": wp["x"],
                        "y_percent": wp["y"],
                    })

        # 10. 目标设备位置
        path.append({
            "type": "device",
            "role": "target",
            "device_id": target_device_id,
            "x_percent": float(target_node.x_percent),
            "y_percent": float(target_node.y_percent),
        })

        return path

    # 其他场景：直接连接
    else:
        # 返回简单的直接连接路径
        return [
            {
                "type": "device",
                "role": "source",
                "device_id": source_device_id,
                "x_percent": float(source_node.x_percent),
                "y_percent": float(source_node.y_percent),
            },
            {
                "type": "device",
                "role": "target",
                "device_id": target_device_id,
                "x_percent": float(target_node.x_percent),
                "y_percent": float(target_node.y_percent),
            }
        ]


def calculate_position_on_trunk_from_percent(trunk: FiberTrunkLink, position_percent: float) -> Dict[str, float]:
    """根据位置百分比计算主干上的坐标

    Args:
        trunk: 主干光缆对象
        position_percent: 位置百分比 (0-100)

    Returns:
        {x_percent, y_percent} 坐标百分比
    """
    # 获取主干路径点（起点、拐点、终点）
    points = [(trunk.start_x_percent, trunk.start_y_percent)]

    if trunk.waypoints:
        try:
            waypoints = json.loads(trunk.waypoints)
            for wp in waypoints:
                if wp.get("x") is not None and wp.get("y") is not None:
                    points.append((wp["x"], wp["y"]))
        except:
            pass

    points.append((trunk.end_x_percent, trunk.end_y_percent))

    # 计算总长度
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
            return {"x_percent": x, "y_percent": y}
        accumulated += seg_len

    # 超出范围，返回终点
    return {"x_percent": trunk.end_x_percent, "y_percent": trunk.end_y_percent}


def get_trunk_waypoints_between(trunk: FiberTrunkLink, from_percent: float, to_percent: float) -> List[Dict[str, float]]:
    """获取主干在两个百分比之间的路径点

    Args:
        trunk: 主干光缆对象
        from_percent: 起始位置百分比
        to_percent: 结束位置百分比

    Returns:
        路径点列表 [{x_percent, y_percent}, ...]
    """
    # 确保 from < to（如果需要反向，前端处理）
    if from_percent > to_percent:
        from_percent, to_percent = to_percent, from_percent

    # 获取主干路径点
    all_points = get_trunk_path_points(trunk, reverse=False)

    # 计算总长度
    total_length = 0
    segment_lengths = []
    for i in range(1, len(all_points)):
        dx = all_points[i]["x_percent"] - all_points[i-1]["x_percent"]
        dy = all_points[i]["y_percent"] - all_points[i-1]["y_percent"]
        length = (dx**2 + dy**2)**0.5
        segment_lengths.append(length)
        total_length += length

    # 找到两个百分比之间的点
    from_length = total_length * from_percent / 100
    to_length = total_length * to_percent / 100

    result_points = []

    # 起始点
    start_pos = calculate_position_on_trunk_from_percent(trunk, from_percent)
    result_points.append(start_pos)

    # 添加中间的拐点（如果在范围内）
    accumulated = 0
    for i, seg_len in enumerate(segment_lengths):
        seg_start_percent = accumulated / total_length * 100
        seg_end_percent = (accumulated + seg_len) / total_length * 100

        # 如果这个段在范围内，添加段的起点（如果不是第一个）
        if seg_start_percent >= from_percent and seg_start_percent <= to_percent:
            if i > 0:  # 不是主干起点
                result_points.append({
                    "x_percent": all_points[i]["x_percent"],
                    "y_percent": all_points[i]["y_percent"],
                })

        accumulated += seg_len

    # 结束点
    end_pos = calculate_position_on_trunk_from_percent(trunk, to_percent)
    result_points.append(end_pos)

    return result_points


def calculate_all_link_paths(db: Session, plan_id: int) -> Dict[str, List[Dict[str, Any]]]:
    """计算平面图上所有数据链路的路径

    对于每条链路（DeviceLink），根据源设备和目标设备计算路径

    Args:
        db: 数据库会话
        plan_id: 平面图ID

    Returns:
        { link_id: path } 字典
    """
    # 获取所有链路（排除 fiber_branch 类型，因为那是物理拓扑）
    links = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.link_role != "fiber_branch"
    ).all()

    link_paths = {}
    for link in links:
        # 获取源和目标设备
        from_node = db.query(DeviceNode).filter(
            DeviceNode.id == link.from_node_id
        ).first()

        to_node = db.query(DeviceNode).filter(
            DeviceNode.id == link.to_node_id
        ).first()

        if not from_node or not to_node:
            continue

        # 计算路径
        path = calculate_link_path(db, plan_id, from_node.device_id, to_node.device_id)

        if path:
            link_paths[link.id] = {
                "link_id": link.id,
                "source_device_id": from_node.device_id,
                "target_device_id": to_node.device_id,
                "link_role": link.link_role,
                "path": path,
            }

    return link_paths


def calculate_device_paths_to_core(db: Session, plan_id: int) -> Dict[int, List[Dict[str, Any]]]:
    """计算所有分支设备到核心交换机的路径（用于渲染）

    Args:
        db: 数据库会话
        plan_id: 平面图ID

    Returns:
        { device_id: path } 字典
    """
    # 获取所有设备节点
    device_nodes = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id
    ).all()

    device_paths = {}

    # 找到核心交换机（目标）
    core_devices = db.query(Device).filter(
        Device.device_type == "core_switch"
    ).all()

    if not core_devices:
        return device_paths

    # 使用第一个核心交换机作为默认目标
    target_core_id = core_devices[0].id

    for node in device_nodes:
        device_role = get_device_role(db, node.device_id)

        # 只计算分支设备到核心的路径
        if device_role == "branch":
            path = calculate_link_path(db, plan_id, node.device_id, target_core_id)
            if path:
                device_paths[node.device_id] = path

    return device_paths