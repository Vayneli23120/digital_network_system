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


# ========== 设备端口自动化（PNetLab 式图模型基础） ==========

# 设备图标占平面的百分比尺寸，用于把端口锚点换算成平面坐标偏移
PORT_ICON_SIZE = 3.0

# 每台设备默认创建的上行端口（预留扩展：后期可增删端口）
# anchor_x/anchor_y 为端口在设备图标上的相对位置（0-1，0.5=中心）
# 暂时统一为单个锚点，放在图标顶部居中，朝向核心方向
DEFAULT_UPLINK_PORTS = [
    {"name": "Uplink-1", "anchor_x": 0.5, "anchor_y": 0.0},
]


def resolve_port_node_position(device_node: DeviceNode, anchor_x: float, anchor_y: float) -> Tuple[float, float]:
    """根据设备节点坐标 + 端口锚点计算端口节点的平面坐标（单一真理源）。

    端口节点坐标永远由"设备坐标 + 锚点偏移"推导，设备一移动端口随之移动，
    避免端口坐标与设备坐标发散。
    """
    base_x = float(device_node.x_percent)
    base_y = float(device_node.y_percent)
    scale = float(device_node.scale) if device_node.scale else 1.0
    size = PORT_ICON_SIZE * scale
    return (
        base_x + (float(anchor_x) - 0.5) * size,
        base_y + (float(anchor_y) - 0.5) * size,
    )


def ensure_device_topo_ports(db: Session, plan_id: int, device_id: int) -> List[TopoNode]:
    """确保设备在该平面图上拥有端口及对应的端口 TopoNode。

    - 若设备尚无任何端口，按 DEFAULT_UPLINK_PORTS 创建默认上行端口。
    - 为每个端口确保存在一个 node_kind='port' 的 TopoNode（图寻路依赖它）。

    返回端口 TopoNode 列表。调用方负责 commit。
    """
    device_node = db.query(DeviceNode).filter(
        DeviceNode.device_id == device_id,
        DeviceNode.floor_plan_id == plan_id,
    ).first()
    if not device_node:
        return []

    # 1. 确保设备有端口（全局，不分平面图）
    ports = db.query(DevicePort).filter(DevicePort.device_id == device_id).all()
    if not ports:
        ports = []
        for spec in DEFAULT_UPLINK_PORTS:
            p = DevicePort(
                device_id=device_id,
                name=spec["name"],
                port_type="fiber",
                anchor_x=spec["anchor_x"],
                anchor_y=spec["anchor_y"],
                is_auto_created=True,
            )
            db.add(p)
            ports.append(p)
        db.flush()

    # 2. 为每个端口确保 TopoNode(port)（按平面图）
    port_nodes: List[TopoNode] = []
    for p in ports:
        node = db.query(TopoNode).filter(
            TopoNode.floor_plan_id == plan_id,
            TopoNode.node_kind == "port",
            TopoNode.port_id == p.id,
        ).first()
        if not node:
            x, y = resolve_port_node_position(device_node, p.anchor_x, p.anchor_y)
            node = TopoNode(
                floor_plan_id=plan_id,
                node_kind="port",
                port_id=p.id,
                x_percent=x,
                y_percent=y,
                label=p.name,
            )
            db.add(node)
        port_nodes.append(node)
    db.flush()
    return port_nodes


def sync_device_port_node_positions(db: Session, plan_id: int, device_id: int) -> None:
    """设备移动/缩放后，同步其所有端口 TopoNode 的坐标。调用方负责 commit。"""
    device_node = db.query(DeviceNode).filter(
        DeviceNode.device_id == device_id,
        DeviceNode.floor_plan_id == plan_id,
    ).first()
    if not device_node:
        return

    port_nodes = db.query(TopoNode).join(
        DevicePort, TopoNode.port_id == DevicePort.id
    ).filter(
        TopoNode.floor_plan_id == plan_id,
        TopoNode.node_kind == "port",
        DevicePort.device_id == device_id,
    ).all()

    for node in port_nodes:
        port = db.query(DevicePort).filter(DevicePort.id == node.port_id).first()
        if port:
            node.x_percent, node.y_percent = resolve_port_node_position(
                device_node, port.anchor_x, port.anchor_y
            )
    db.flush()


def normalize_device_ports_to_single(db: Session, device_id: int) -> int:
    """将设备自动生成的上行端口规整为单个（顶部居中）。

    - 仅处理 is_auto_created 的 fiber 端口；手动添加的端口保持不变。
    - 保留 id 最小的自动端口并移到中心，删除其余自动端口及其
      端口 TopoNode（所有平面图）和相连的 TopoEdge。

    返回删除的端口数。调用方负责 commit。
    """
    auto_ports = db.query(DevicePort).filter(
        DevicePort.device_id == device_id,
        DevicePort.is_auto_created == True,  # noqa: E712
        DevicePort.port_type == "fiber",
    ).order_by(DevicePort.id).all()

    if not auto_ports:
        return 0

    # 保留第一个并移到中心
    keep = auto_ports[0]
    keep.anchor_x = DEFAULT_UPLINK_PORTS[0]["anchor_x"]
    keep.anchor_y = DEFAULT_UPLINK_PORTS[0]["anchor_y"]
    keep.name = DEFAULT_UPLINK_PORTS[0]["name"]

    removed = 0
    for p in auto_ports[1:]:
        # 删除该端口的所有端口 TopoNode（跨平面图）及相连边
        nodes = db.query(TopoNode).filter(TopoNode.port_id == p.id).all()
        for n in nodes:
            db.query(TopoEdge).filter(
                (TopoEdge.a_node_id == n.id) | (TopoEdge.b_node_id == n.id)
            ).delete(synchronize_session=False)
            db.delete(n)
        db.delete(p)
        removed += 1
    db.flush()
    return removed


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
    cable_name = data.name or unique_cable_name(db, plan_id, f"主干光缆-{cable_id}")

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

        if proj_dist < 10.0:  # 10% 容差（允许用户点击主干附近）
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
    cable_name = data.name or unique_cable_name(db, plan_id, f"分支光缆-{cable_id}")

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


def _oriented_waypoints_far_to_bp(edge, bp_id) -> list:
    """返回该边从『远端节点』指向分支点方向的拐点列表。

    边的拐点顺序固定为 a_node -> b_node。
    """
    wps = []
    if edge.waypoints:
        try:
            wps = json.loads(edge.waypoints) or []
        except Exception:
            wps = []
    if edge.a_node_id == bp_id:
        # a 是分支点：a->b 即 bp->far，反转得到 far->bp
        return list(reversed(wps))
    # b 是分支点：a->b 即 far->bp，保持原顺序
    return list(wps)


def delete_topo_node(db: Session, plan_id: int, node_id: int) -> bool:
    """删除拓扑节点。

    - 普通节点：删除节点及其所有关联边。
    - 分支点(branch_point)：删除挂在其上的分支光缆(fiber)，并把被它切断的两段主干
      重新合并成一条连续主干（保留主干 cable_id / 编号 / 名称，拐点串接并经过原分支点
      位置），避免删除分支点导致整条主干光缆消失、只剩孤立的主干端点。
    """
    node = db.query(TopoNode).filter(
        TopoNode.id == node_id,
        TopoNode.floor_plan_id == plan_id
    ).first()

    if not node:
        return False

    edges = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        (TopoEdge.a_node_id == node_id) | (TopoEdge.b_node_id == node_id)
    ).all()

    is_branch_point = node.node_kind == "junction" and node.junction_type == "branch_point"

    if is_branch_point:
        trunk_edges = [e for e in edges if e.cable_type in ("trunk", "trunk_segment")]
        other_edges = [e for e in edges if e.cable_type not in ("trunk", "trunk_segment")]

        # 删除挂在分支点上的分支光缆
        for e in other_edges:
            db.delete(e)

        if len(trunk_edges) == 2:
            e1, e2 = trunk_edges
            far1 = e1.a_node_id if e1.b_node_id == node_id else e1.b_node_id
            far2 = e2.a_node_id if e2.b_node_id == node_id else e2.b_node_id

            # far1 -> bp 的拐点 + 分支点坐标 + bp -> far2 的拐点
            wps1 = _oriented_waypoints_far_to_bp(e1, node_id)                 # far1 -> bp
            wps2 = list(reversed(_oriented_waypoints_far_to_bp(e2, node_id)))  # bp -> far2
            merged = list(wps1) + [{"x": node.x_percent, "y": node.y_percent}] + list(wps2)

            # 还原主干名称（去掉 “-段N” 后缀）
            base_name = e1.cable_name or e2.cable_name or ""
            if "-段" in base_name:
                base_name = base_name.rsplit("-段", 1)[0]

            # 若两端都是主干端点，则恢复为整条 trunk；否则仍是分段
            far1_node = db.query(TopoNode).filter(TopoNode.id == far1).first()
            far2_node = db.query(TopoNode).filter(TopoNode.id == far2).first()
            both_endpoints = (
                far1_node and far2_node
                and far1_node.junction_type == "trunk_endpoint"
                and far2_node.junction_type == "trunk_endpoint"
            )

            merged_edge = TopoEdge(
                floor_plan_id=plan_id,
                a_node_id=far1,
                b_node_id=far2,
                cable_type="trunk" if both_endpoints else "trunk_segment",
                cable_id=e1.cable_id,
                cable_no=e1.cable_no,
                cable_name=base_name or e1.cable_name,
                waypoints=json.dumps(merged) if merged else None,
                status="up",
            )
            db.add(merged_edge)
            db.delete(e1)
            db.delete(e2)
        else:
            # 非预期结构（分支点未正好切断两段主干），退化为直接删除避免悬挂边
            for e in trunk_edges:
                db.delete(e)

        db.delete(node)
        db.commit()
        return True

    # 普通节点：删除节点及其所有关联边
    for edge in edges:
        db.delete(edge)

    db.delete(node)
    db.commit()
    return True


def update_topo_node(db: Session, plan_id: int, node_id: int, data) -> Optional[Dict[str, Any]]:
    """更新拓扑节点位置"""
    node = db.query(TopoNode).filter(
        TopoNode.id == node_id,
        TopoNode.floor_plan_id == plan_id
    ).first()

    if not node:
        return None

    if data.x_percent is not None:
        node.x_percent = data.x_percent
    if data.y_percent is not None:
        node.y_percent = data.y_percent
    if data.label is not None:
        node.label = data.label

    node.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(node)

    result = {
        "id": node.id,
        "node_kind": node.node_kind,
        "x_percent": node.x_percent,
        "y_percent": node.y_percent,
        "label": node.label,
    }
    if node.node_kind == "junction":
        result["junction_type"] = node.junction_type

    return result


def rename_cable(db: Session, plan_id: int, cable_id: int, new_name: str) -> bool:
    """重命名整条光缆（更新所有 cable_id 相同的边的 cable_name）。

    返回是否成功。调用方负责 commit。
    """
    edges = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.cable_id == cable_id,
    ).all()
    if not edges:
        return False
    for e in edges:
        e.cable_name = new_name
    db.flush()
    return True


def is_cable_name_duplicated(db: Session, plan_id: int, new_name: str, exclude_cable_id: Optional[int] = None) -> bool:
    """检查光缆名是否与同平面图其他光缆重复（按 cable_id 区分）。"""
    q = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.cable_name == new_name,
    )
    edges = q.all()
    for e in edges:
        if exclude_cable_id is not None and e.cable_id == exclude_cable_id:
            continue
        return True
    return False


def unique_cable_name(db: Session, plan_id: int, base_name: str) -> str:
    """若 base_name 已被占用，追加 -2/-3... 直到唯一。"""
    if not is_cable_name_duplicated(db, plan_id, base_name):
        return base_name
    i = 2
    while True:
        candidate = f"{base_name}-{i}"
        if not is_cable_name_duplicated(db, plan_id, candidate):
            return candidate
        i += 1


def delete_cable(db: Session, plan_id: int, cable_id: int) -> bool:
    """删除整条光缆（所有 cable_id 相同的边）"""
    edges = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.cable_id == cable_id
    ).all()

    if not edges:
        return False

    # 主干类光缆删除时，需要级联删除挂载在该主干上的分支点与分支光缆
    is_trunk_cable = any(e.cable_type in ["trunk", "trunk_segment", "trunk_to_core"] for e in edges)

    edge_ids_to_delete = {e.id for e in edges}

    # 收集本次删除光缆关联的 junction 节点候选
    candidate_junction_node_ids = set()
    for edge in edges:
        candidate_junction_node_ids.add(edge.a_node_id)
        candidate_junction_node_ids.add(edge.b_node_id)

    if is_trunk_cable:
        # 找到挂在该主干上的分支点
        branch_point_node_ids = set()
        for node_id in list(candidate_junction_node_ids):
            node = db.query(TopoNode).filter(
                TopoNode.id == node_id,
                TopoNode.floor_plan_id == plan_id,
            ).first()
            if node and node.node_kind == "junction" and node.junction_type == "branch_point":
                branch_point_node_ids.add(node_id)

        # 级联删除分支点连接的边（通常是分支光缆）
        if branch_point_node_ids:
            branch_edges = db.query(TopoEdge).filter(
                TopoEdge.floor_plan_id == plan_id,
                (TopoEdge.a_node_id.in_(branch_point_node_ids)) | (TopoEdge.b_node_id.in_(branch_point_node_ids))
            ).all()

            for edge in branch_edges:
                edge_ids_to_delete.add(edge.id)
                candidate_junction_node_ids.add(edge.a_node_id)
                candidate_junction_node_ids.add(edge.b_node_id)

    # 删除所有需要删除的边（主干 + 其挂载分支）
    edges_to_delete = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.id.in_(edge_ids_to_delete)
    ).all()
    for edge in edges_to_delete:
        db.delete(edge)

    # 删除关联的 junction 节点（排除本次整缆删除中的所有边后，若无剩余连接则删除）
    for node_id in candidate_junction_node_ids:
        node = db.query(TopoNode).filter(
            TopoNode.id == node_id,
            TopoNode.floor_plan_id == plan_id,
        ).first()
        if not node or node.node_kind != "junction":
            continue

        remaining_edges = db.query(TopoEdge).filter(
            TopoEdge.floor_plan_id == plan_id,
            ~TopoEdge.id.in_(edge_ids_to_delete),
            (TopoEdge.a_node_id == node_id) | (TopoEdge.b_node_id == node_id)
        ).count()

        if remaining_edges == 0:
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