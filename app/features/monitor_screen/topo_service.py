"""
Topo Service - 基于图模型的光缆拓扑服务

设计决策：
- 图模型（topo_nodes + topo_edges）为唯一真理来源
- 一条主干 = 一个光缆编号（所有分段共享 cable_id）
- 分支光缆单独编号
- 分支点编号手填（存于 TopoNode.label）
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import math

from app.shared.models import (
    TopoNode, TopoEdge, DevicePort, Device, DeviceNode, FloorPlan
)


# ========== 光缆聚合查询 ==========

def get_cables(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取所有光缆（按 cable_id 聚合）

    每条光缆包含：
    - cable_id: 光缆编号
    - cable_no: 显示编号
    - cable_type: trunk/fiber
    - segments: 该光缆的所有边
    """
    edges = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.cable_id.isnot(None)
    ).order_by(TopoEdge.cable_id, TopoEdge.id).all()

    # 按 cable_id 分组
    cables_map = {}
    for e in edges:
        if e.cable_id not in cables_map:
            cables_map[e.cable_id] = {
                "cable_id": e.cable_id,
                "cable_no": e.cable_no,
                "cable_name": e.cable_name,
                "cable_type": e.cable_type,
                "status": e.status,
                "segments": [],
            }
        cables_map[e.cable_id]["segments"].append({
            "edge_id": e.id,
            "a_node_id": e.a_node_id,
            "b_node_id": e.b_node_id,
            "waypoints": json.loads(e.waypoints) if e.waypoints else [],
        })

    return list(cables_map.values())


def get_topo_nodes(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取所有拓扑节点"""
    nodes = db.query(TopoNode).filter(TopoNode.floor_plan_id == plan_id).all()

    result = []
    for n in nodes:
        node_data = {
            "id": n.id,
            "node_kind": n.node_kind,
            "x_percent": n.x_percent,
            "y_percent": n.y_percent,
            "label": n.label,
        }
        if n.node_kind == "junction":
            node_data["junction_type"] = n.junction_type
        elif n.node_kind == "port" and n.port_id:
            port = db.query(DevicePort).filter(DevicePort.id == n.port_id).first()
            if port:
                node_data["port_id"] = n.port_id
                node_data["device_id"] = port.device_id
                device = db.query(Device).filter(Device.id == port.device_id).first()
                if device:
                    node_data["device_name"] = device.name
                    node_data["device_type"] = device.device_type
        result.append(node_data)

    return result


def get_topo_edges(db: Session, plan_id: int) -> List[Dict[str, Any]]:
    """获取所有拓扑边"""
    edges = db.query(TopoEdge).filter(TopoEdge.floor_plan_id == plan_id).all()

    return [
        {
            "id": e.id,
            "a_node_id": e.a_node_id,
            "b_node_id": e.b_node_id,
            "cable_type": e.cable_type,
            "cable_id": e.cable_id,
            "cable_no": e.cable_no,
            "cable_name": e.cable_name,
            "waypoints": json.loads(e.waypoints) if e.waypoints else [],
            "status": e.status,
        }
        for e in edges
    ]


# ========== 主干光缆创建 ==========

def create_trunk(db: Session, plan_id: int, data) -> Dict[str, Any]:
    """创建主干光缆

    输入：
    - name: 光缆名称（可选）
    - start_x, start_y: 起点坐标
    - start_device_id: 起点关联核心设备（可选）
    - end_x, end_y: 终点坐标
    - waypoints: 拐点列表 [{'x': ..., 'y': ...}, ...]

    输出：
    - cable_id: 分配的光缆编号
    - cable_no: 显示编号
    - nodes: 创建的节点列表
    - edges: 创建的边列表
    """
    # 分配 cable_id
    max_cable_id = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.cable_id.isnot(None)
    ).order_by(TopoEdge.cable_id.desc()).first()

    cable_id = (max_cable_id.cable_id + 1) if max_cable_id else 1
    cable_no = data.cable_no or f"TRUNK-{cable_id}"
    cable_name = data.name or f"主干光缆-{cable_id}"

    # 创建起点 junction
    start_node = TopoNode(
        floor_plan_id=plan_id,
        node_kind="junction",
        junction_type="trunk_endpoint",
        x_percent=data.start_x,
        y_percent=data.start_y,
        label=f"{cable_no}-起点",
    )
    db.add(start_node)
    db.flush()

    # 创建终点 junction
    end_node = TopoNode(
        floor_plan_id=plan_id,
        node_kind="junction",
        junction_type="trunk_endpoint",
        x_percent=data.end_x,
        y_percent=data.end_y,
        label=f"{cable_no}-终点",
    )
    db.add(end_node)
    db.flush()

    # 创建主干边
    waypoints_json = json.dumps(data.waypoints) if data.waypoints else None
    trunk_edge = TopoEdge(
        floor_plan_id=plan_id,
        a_node_id=start_node.id,
        b_node_id=end_node.id,
        cable_type="trunk",
        cable_id=cable_id,
        cable_no=cable_no,
        cable_name=cable_name,
        waypoints=waypoints_json,
        status="up",
    )
    db.add(trunk_edge)
    db.flush()

    created_nodes = [start_node, end_node]
    created_edges = [trunk_edge]

    # 如果起点关联核心设备，创建连接边
    if data.start_device_id:
        # 找设备的 port TopoNode
        device_port_node = db.query(TopoNode).join(DevicePort).filter(
            TopoNode.floor_plan_id == plan_id,
            TopoNode.node_kind == "port",
            DevicePort.device_id == data.start_device_id
        ).first()

        if device_port_node:
            connect_edge = TopoEdge(
                floor_plan_id=plan_id,
                a_node_id=start_node.id,
                b_node_id=device_port_node.id,
                cable_type="trunk_to_core",
                cable_id=cable_id,
                cable_no=cable_no,
                cable_name=f"{cable_name}-核心连接",
                status="up",
            )
            db.add(connect_edge)
            db.flush()
            created_edges.append(connect_edge)

    db.commit()

    return {
        "cable_id": cable_id,
        "cable_no": cable_no,
        "cable_name": cable_name,
        "nodes": [
            {"id": n.id, "node_kind": n.node_kind, "x_percent": n.x_percent, "y_percent": n.y_percent, "label": n.label}
            for n in created_nodes
        ],
        "edges": [
            {"id": e.id, "a_node_id": e.a_node_id, "b_node_id": e.b_node_id, "cable_type": e.cable_type}
            for e in created_edges
        ],
    }


# ========== 分支点创建 ==========

def create_branch_point(db: Session, plan_id: int, data) -> Dict[str, Any]:
    """在主干上创建分支点（切段主干）

    输入：
    - trunk_cable_id: 主干光缆编号
    - x, y: 分支点坐标
    - label: 分支点编号（手填）

    处理逻辑：
    1. 找到主干的当前边
    2. 计算分支点投影位置
    3. 切断主干成多段
    4. 创建分支点 junction

    输出：
    - node: 创建的分支点节点
    - affected_edges: 受影响的边列表
    """
    # 获取主干所有边
    trunk_edges = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.cable_id == data.trunk_cable_id,
        TopoEdge.cable_type.in_(["trunk", "trunk_segment"]),
    ).all()

    if not trunk_edges:
        raise ValueError("主干光缆不存在")

    # 找到分支点落在哪条边上
    bp_coord = (data.x, data.y)
    best_edge = None
    best_s = None
    best_proj = None

    for edge in trunk_edges:
        a_node = db.query(TopoNode).filter(TopoNode.id == edge.a_node_id).first()
        b_node = db.query(TopoNode).filter(TopoNode.id == edge.b_node_id).first()

        if not a_node or not b_node:
            continue

        polyline = [(a_node.x_percent, a_node.y_percent)]
        if edge.waypoints:
            try:
                for wp in json.loads(edge.waypoints):
                    polyline.append((wp['x'], wp['y']))
            except:
                pass
        polyline.append((b_node.x_percent, b_node.y_percent))

        s, proj = project_point_on_polyline(bp_coord, polyline)
        proj_dist = math.sqrt((bp_coord[0] - proj[0])**2 + (bp_coord[1] - proj[1])**2)

        if proj_dist < 5.0:  # 5% 容差
            if best_edge is None or proj_dist < math.sqrt((bp_coord[0] - best_proj[0])**2 + (bp_coord[1] - best_proj[1])**2):
                best_edge = edge
                best_s = s
                best_proj = proj

    if not best_edge:
        raise ValueError("分支点不在主干线路上")

    # 创建分支点 junction（使用投影坐标）
    bp_node = TopoNode(
        floor_plan_id=plan_id,
        node_kind="junction",
        junction_type="branch_point",
        x_percent=best_proj[0],
        y_percent=best_proj[1],
        label=data.label or f"BP-{best_edge.cable_no}",
    )
    db.add(bp_node)
    db.flush()

    # 切断主干边
    a_node = db.query(TopoNode).filter(TopoNode.id == best_edge.a_node_id).first()
    b_node = db.query(TopoNode).filter(TopoNode.id == best_edge.b_node_id).first()

    polyline = [(a_node.x_percent, a_node.y_percent)]
    if best_edge.waypoints:
        try:
            for wp in json.loads(best_edge.waypoints):
                polyline.append((wp['x'], wp['y']))
        except:
            pass
    polyline.append((b_node.x_percent, b_node.y_percent))

    total_len = polyline_total_length(polyline)

    # 提取两段的拐点
    wps_before = extract_waypoints_in_range(polyline, 0.0, best_s)
    wps_after = extract_waypoints_in_range(polyline, best_s, total_len)

    # 创建两段新边
    edge1 = TopoEdge(
        floor_plan_id=plan_id,
        a_node_id=a_node.id,
        b_node_id=bp_node.id,
        cable_type="trunk_segment",
        cable_id=best_edge.cable_id,
        cable_no=best_edge.cable_no,
        cable_name=f"{best_edge.cable_name}-段1",
        waypoints=json.dumps(wps_before) if wps_before else None,
        status="up",
    )
    db.add(edge1)
    db.flush()

    edge2 = TopoEdge(
        floor_plan_id=plan_id,
        a_node_id=bp_node.id,
        b_node_id=b_node.id,
        cable_type="trunk_segment",
        cable_id=best_edge.cable_id,
        cable_no=best_edge.cable_no,
        cable_name=f"{best_edge.cable_name}-段2",
        waypoints=json.dumps(wps_after) if wps_after else None,
        status="up",
    )
    db.add(edge2)
    db.flush()

    # 删除原边
    db.delete(best_edge)

    db.commit()

    return {
        "node": {
            "id": bp_node.id,
            "node_kind": "junction",
            "junction_type": "branch_point",
            "x_percent": bp_node.x_percent,
            "y_percent": bp_node.y_percent,
            "label": bp_node.label,
        },
        "affected_edges": [
            {"id": edge1.id, "a_node_id": edge1.a_node_id, "b_node_id": edge1.b_node_id},
            {"id": edge2.id, "a_node_id": edge2.a_node_id, "b_node_id": edge2.b_node_id},
        ],
        "deleted_edges": [best_edge.id],
    }


# ========== 分支光缆创建 ==========

def create_branch_cable(db: Session, plan_id: int, data) -> Dict[str, Any]:
    """创建分支光缆（从分支点到设备）

    输入：
    - branch_point_id: 分支点节点 ID
    - to_device_id: 目标设备 ID
    - waypoints: 拐点列表（可选）

    输出：
    - cable_id: 分配的独立光缆编号
    - cable_no: 显示编号
    - edge: 创建的边
    """
    # 验证分支点存在
    bp_node = db.query(TopoNode).filter(
        TopoNode.id == data.branch_point_id,
        TopoNode.floor_plan_id == plan_id,
        TopoNode.node_kind == "junction",
        TopoNode.junction_type == "branch_point",
    ).first()

    if not bp_node:
        raise ValueError("分支点不存在")

    # 找设备的 port TopoNode
    device_port_node = db.query(TopoNode).join(DevicePort).filter(
        TopoNode.floor_plan_id == plan_id,
        TopoNode.node_kind == "port",
        DevicePort.device_id == data.to_device_id
    ).first()

    if not device_port_node:
        # 如果设备没有 port node，创建一个
        device_node = db.query(DeviceNode).filter(
            DeviceNode.device_id == data.to_device_id,
            DeviceNode.floor_plan_id == plan_id
        ).first()

        if not device_node:
            raise ValueError("设备节点不存在")

        # 创建默认 port
        port = DevicePort(
            device_id=data.to_device_id,
            name=f"auto-{device_node.id}",
            port_type="ethernet",
            anchor_x=0.5,
            anchor_y=0.5,
            is_auto_created=True,
        )
        db.add(port)
        db.flush()

        # 创建 TopoNode
        device_port_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="port",
            port_id=port.id,
            x_percent=device_node.x_percent,
            y_percent=device_node.y_percent,
        )
        db.add(device_port_node)
        db.flush()

    # 分配独立的 cable_id
    max_cable_id = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.cable_id.isnot(None)
    ).order_by(TopoEdge.cable_id.desc()).first()

    cable_id = (max_cable_id.cable_id + 1) if max_cable_id else 1
    cable_no = data.cable_no or f"BR-{cable_id}"
    cable_name = data.name or f"分支光缆-{cable_id}"

    # 创建分支光缆边
    waypoints_json = json.dumps(data.waypoints) if data.waypoints else None
    branch_edge = TopoEdge(
        floor_plan_id=plan_id,
        a_node_id=bp_node.id,
        b_node_id=device_port_node.id,
        cable_type="fiber",
        cable_id=cable_id,
        cable_no=cable_no,
        cable_name=cable_name,
        waypoints=waypoints_json,
        status="up",
    )
    db.add(branch_edge)
    db.commit()

    return {
        "cable_id": cable_id,
        "cable_no": cable_no,
        "cable_name": cable_name,
        "edge": {
            "id": branch_edge.id,
            "a_node_id": branch_edge.a_node_id,
            "b_node_id": branch_edge.b_node_id,
            "waypoints": json.loads(branch_edge.waypoints) if branch_edge.waypoints else [],
        },
    }


# ========== 边更新 ==========

def update_topo_edge(db: Session, plan_id: int, edge_id: int, data) -> Optional[Dict[str, Any]]:
    """更新拓扑边（拐点、名称等）"""
    edge = db.query(TopoEdge).filter(
        TopoEdge.id == edge_id,
        TopoEdge.floor_plan_id == plan_id
    ).first()

    if not edge:
        return None

    if data.waypoints is not None:
        edge.waypoints = json.dumps(data.waypoints) if data.waypoints else None
    if data.cable_name is not None:
        edge.cable_name = data.cable_name
    if data.cable_no is not None:
        edge.cable_no = data.cable_no
    if data.status is not None:
        edge.status = data.status

    edge.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(edge)

    return {
        "id": edge.id,
        "a_node_id": edge.a_node_id,
        "b_node_id": edge.b_node_id,
        "cable_type": edge.cable_type,
        "cable_id": edge.cable_id,
        "cable_no": edge.cable_no,
        "cable_name": edge.cable_name,
        "waypoints": json.loads(edge.waypoints) if edge.waypoints else [],
        "status": edge.status,
    }


def delete_topo_edge(db: Session, plan_id: int, edge_id: int) -> bool:
    """删除拓扑边"""
    edge = db.query(TopoEdge).filter(
        TopoEdge.id == edge_id,
        TopoEdge.floor_plan_id == plan_id
    ).first()

    if not edge:
        return False

    db.delete(edge)
    db.commit()
    return True


def delete_topo_node(db: Session, plan_id: int, node_id: int) -> bool:
    """删除拓扑节点（连同关联的边）"""
    node = db.query(TopoNode).filter(
        TopoNode.id == node_id,
        TopoNode.floor_plan_id == plan_id
    ).first()

    if not node:
        return False

    # 删除连接到该节点的所有边
    edges = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        (TopoEdge.a_node_id == node_id) | (TopoEdge.b_node_id == node_id)
    ).all()

    for edge in edges:
        db.delete(edge)

    db.delete(node)
    db.commit()
    return True


def delete_cable(db: Session, plan_id: int, cable_id: int) -> bool:
    """删除整条光缆（所有 cable_id 相同的边）"""
    edges = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.cable_id == cable_id
    ).all()

    if not edges:
        return False

    # 删除所有边
    for edge in edges:
        db.delete(edge)

    # 删除关联的 junction 节点（如果没有其他边连接）
    for edge in edges:
        for node_id in [edge.a_node_id, edge.b_node_id]:
            node = db.query(TopoNode).filter(TopoNode.id == node_id).first()
            if node and node.node_kind == "junction":
                # 检查是否有其他边连接
                other_edges = db.query(TopoEdge).filter(
                    TopoEdge.floor_plan_id == plan_id,
                    TopoEdge.id != edge.id,
                    (TopoEdge.a_node_id == node_id) | (TopoEdge.b_node_id == node_id)
                ).count()
                if other_edges == 0:
                    db.delete(node)

    db.commit()
    return True


# ========== 几何计算辅助函数 ==========

def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def polyline_total_length(polyline: List[Tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(polyline) - 1):
        total += distance(polyline[i], polyline[i + 1])
    return total


def project_point_on_polyline(point: Tuple[float, float],
                               polyline: List[Tuple[float, float]]) -> Tuple[float, Tuple[float, float]]:
    """点到折线的投影，返回 (沿线累计距离 s, 投影坐标)"""
    if len(polyline) < 2:
        return 0.0, polyline[0] if polyline else point

    best_s = 0.0
    best_proj = polyline[0]
    best_dist = distance(point, polyline[0])
    cumulative_len = 0.0

    for i in range(len(polyline) - 1):
        seg_start = polyline[i]
        seg_end = polyline[i + 1]
        seg_len = distance(seg_start, seg_end)

        dx = seg_end[0] - seg_start[0]
        dy = seg_end[1] - seg_start[1]
        seg_len_sq = dx*dx + dy*dy

        if seg_len_sq < 1e-10:
            cumulative_len += seg_len
            continue

        t = ((point[0] - seg_start[0]) * dx + (point[1] - seg_start[1]) * dy) / seg_len_sq
        t = max(0.0, min(1.0, t))

        proj_x = seg_start[0] + t * dx
        proj_y = seg_start[1] + t * dy
        proj = (proj_x, proj_y)
        dist = distance(point, proj)

        if dist < best_dist:
            best_dist = dist
            best_proj = proj
            best_s = cumulative_len + t * seg_len

        cumulative_len += seg_len

    return best_s, best_proj


def extract_waypoints_in_range(polyline: List[Tuple[float, float]],
                               s_start: float, s_end: float) -> List[dict]:
    """提取区间内的真实拐点"""
    if s_start >= s_end:
        return []

    result = []
    cumulative_len = 0.0

    for i in range(len(polyline) - 1):
        seg_len = distance(polyline[i], polyline[i + 1])
        seg_s_start = cumulative_len
        seg_s_end = cumulative_len + seg_len

        if i > 0 and seg_s_start > s_start and seg_s_start < s_end:
            result.append({'x': polyline[i][0], 'y': polyline[i][1]})

        cumulative_len += seg_len

    return result