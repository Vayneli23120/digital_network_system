"""
Graph Path Service - PNetLab 式图寻路服务

核心思想：
- 物理拓扑 = 图（Graph），节点是端点，边是线缆
- 自动寻路 = Dijkstra 图最短路
- 渲染 = 把路径经过的边的拐点折线首尾拼起来

这解决了当前方案的问题：
1. 用"角色规则"代替"真实连接" → 任意拓扑都支持
2. 用几何投影推算路径 → 路径沿真实边走
3. 拓扑和几何没分离 → 边自带拐点，直接拼接
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import heapq
import json
import math

from app.shared.models import TopoNode, TopoEdge, DevicePort, Device, DeviceNode


def edge_geometry_length(edge: TopoEdge, node_positions: Dict[int, Tuple[float, float]]) -> float:
    """计算边的几何长度（含拐点）

    Args:
        edge: 边对象
        node_positions: 节点位置字典 {node_id: (x, y)}

    Returns:
        边的总几何长度
    """
    a_pos = node_positions.get(edge.a_node_id)
    b_pos = node_positions.get(edge.b_node_id)

    if not a_pos or not b_pos:
        return 1.0  # 默认权重

    total = 0.0
    prev = a_pos

    # 拐点
    if edge.waypoints:
        try:
            waypoints = json.loads(edge.waypoints)
            for wp in waypoints:
                if wp.get("x") is not None and wp.get("y") is not None:
                    curr = (wp["x"], wp["y"])
                    total += math.sqrt((curr[0] - prev[0])**2 + (curr[1] - prev[1])**2)
                    prev = curr
        except:
            pass

    # 终点
    total += math.sqrt((b_pos[0] - prev[0])**2 + (b_pos[1] - prev[1])**2)

    return total if total > 0 else 1.0


def build_graph(db: Session, plan_id: int) -> Tuple[List[TopoNode], Dict[int, List[Tuple[int, TopoEdge, float, bool]]]]:
    """构建邻接表

    Args:
        db: 数据库会话
        plan_id: 平面图ID

    Returns:
        (nodes, adj) 节点列表和邻接表
        adj: {node_id: [(neighbor_id, edge, weight, reversed), ...]}
    """
    nodes = db.query(TopoNode).filter(TopoNode.floor_plan_id == plan_id).all()
    edges = db.query(TopoEdge).filter(
        TopoEdge.floor_plan_id == plan_id,
        TopoEdge.status == "up"
    ).all()

    # 计算节点位置
    node_positions = get_node_positions(db, nodes)

    # 构建邻接表
    adj = defaultdict(list)
    for e in edges:
        w = e.length_weight if e.length_weight else edge_geometry_length(e, node_positions)
        adj[e.a_node_id].append((e.b_node_id, e, w, False))
        adj[e.b_node_id].append((e.a_node_id, e, w, True))

    return nodes, dict(adj)


def get_node_positions(db: Session, nodes: List[TopoNode]) -> Dict[int, Tuple[float, float]]:
    """获取所有节点的位置坐标

    port 类型节点：从设备坐标 + 端口锚点偏移计算
    junction 类型节点：使用自己的坐标
    """
    positions = {}

    for node in nodes:
        if node.node_kind == "junction":
            if node.x_percent is not None and node.y_percent is not None:
                positions[node.id] = (node.x_percent, node.y_percent)
        elif node.node_kind == "port" and node.port_id:
            # 查找端口关联的设备
            port = db.query(DevicePort).filter(DevicePort.id == node.port_id).first()
            if port:
                # 查找设备在平面图上的位置
                device_node = db.query(DeviceNode).filter(
                    DeviceNode.device_id == port.device_id,
                    DeviceNode.floor_plan_id == node.floor_plan_id
                ).first()
                if device_node:
                    # 设备坐标 + 端口锚点偏移
                    base_x = float(device_node.x_percent)
                    base_y = float(device_node.y_percent)
                    # 锚点偏移（假设设备图标大小约 3% 平面）
                    icon_size = 3.0
                    offset_x = (port.anchor_x - 0.5) * icon_size
                    offset_y = (port.anchor_y - 0.5) * icon_size
                    positions[node.id] = (base_x + offset_x, base_y + offset_y)

    return positions


def shortest_path(
    adj: Dict[int, List[Tuple[int, TopoEdge, float, bool]]],
    start_node_id: int,
    end_node_id: int
) -> Optional[List[Tuple[TopoEdge, bool]]]:
    """Dijkstra 最短路算法

    Args:
        adj: 邻接表
        start_node_id: 起点
        end_node_id: 终点

    Returns:
        边序列 [(edge, reversed), ...] 或 None（不可达）
    """
    if start_node_id == end_node_id:
        return []

    # Dijkstra
    dist = {start_node_id: 0.0}
    prev = {}  # node_id -> (prev_node_id, edge, reversed)
    pq = [(0.0, start_node_id)]

    while pq:
        d, u = heapq.heappop(pq)

        if u == end_node_id:
            break

        if d > dist.get(u, 1e18):
            continue

        for v, edge, w, rev in adj.get(u, []):
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = (u, edge, rev)
                heapq.heappush(pq, (nd, v))

    # 回溯边序列
    if end_node_id not in prev:
        return None

    edge_seq = []
    cur = end_node_id
    while cur != start_node_id:
        pu, edge, rev = prev[cur]
        edge_seq.append((edge, rev))
        cur = pu
    edge_seq.reverse()

    return edge_seq


def path_to_polyline(
    edge_seq: List[Tuple[TopoEdge, bool]],
    node_positions: Dict[int, Tuple[float, float]]
) -> List[Dict[str, float]]:
    """沿路径把每条边的折线拼起来

    Args:
        edge_seq: 边序列 [(edge, reversed), ...]
        node_positions: 节点位置字典

    Returns:
        polyline: [{"x_percent": x, "y_percent": y}, ...]
    """
    if not edge_seq:
        return []

    poly = []

    for edge, rev in edge_seq:
        a_pos = node_positions.get(edge.a_node_id)
        b_pos = node_positions.get(edge.b_node_id)

        if not a_pos or not b_pos:
            continue

        # 构建点序列：起点 → 拐点 → 终点
        pts = [a_pos]

        if edge.waypoints:
            try:
                waypoints = json.loads(edge.waypoints)
                for wp in waypoints:
                    if wp.get("x") is not None and wp.get("y") is not None:
                        pts.append((wp["x"], wp["y"]))
            except:
                pass

        pts.append(b_pos)

        # 如果边是反向的，反转点序列
        if rev:
            pts = pts[::-1]

        # 去重拼接
        for p in pts:
            if not poly:
                poly.append(p)
            else:
                # 距离阈值
                last = poly[-1]
                d = math.sqrt((p[0] - last[0])**2 + (p[1] - last[1])**2)
                if d > 0.01:  # 0.01% 坐标差值阈值
                    poly.append(p)

    return [{"x_percent": x, "y_percent": y} for x, y in poly]


def calculate_path(
    db: Session,
    plan_id: int,
    from_device_id: int,
    to_device_id: int
) -> Optional[Dict[str, Any]]:
    """计算两个设备之间的路径

    Args:
        db: 数据库会话
        plan_id: 平面图ID
        from_device_id: 源设备ID
        to_device_id: 目标设备ID

    Returns:
        {reachable, polyline, edges, hops} 或 None
    """
    # 建图
    nodes, adj = build_graph(db, plan_id)
    node_positions = get_node_positions(db, nodes)

    # 找源设备和目标设备的端口节点
    from_port_nodes = [n for n in nodes if n.node_kind == "port" and n.port_id]
    from_nodes = []
    to_nodes = []

    for n in from_port_nodes:
        port = db.query(DevicePort).filter(DevicePort.id == n.port_id).first()
        if port:
            if port.device_id == from_device_id:
                from_nodes.append(n.id)
            elif port.device_id == to_device_id:
                to_nodes.append(n.id)

    if not from_nodes or not to_nodes:
        return {"reachable": False, "reason": "设备无拓扑连接"}

    # 多起点 → 多终点 Dijkstra（找最近的）
    best_path = None
    best_dist = float("inf")

    for start in from_nodes:
        for end in to_nodes:
            if start == end:
                continue
            edge_seq = shortest_path(adj, start, end)
            if edge_seq:
                # 计算路径长度
                total_w = sum(
                    e.length_weight if e.length_weight else edge_geometry_length(e, node_positions)
                    for e, _ in edge_seq
                )
                if total_w < best_dist:
                    best_dist = total_w
                    best_path = edge_seq

    if not best_path:
        return {"reachable": False, "reason": "无连通路径"}

    # 拼折线
    polyline = path_to_polyline(best_path, node_positions)

    # 构建跳信息
    hops = []
    for edge, rev in best_path:
        a_node = next((n for n in nodes if n.id == edge.a_node_id), None)
        b_node = next((n for n in nodes if n.id == edge.b_node_id), None)
        hop = {
            "edge_id": edge.id,
            "cable_type": edge.cable_type,
            "cable_name": edge.cable_name,
            "a_node_kind": a_node.node_kind if a_node else None,
            "b_node_kind": b_node.node_kind if b_node else None,
        }
        if a_node and a_node.port_id:
            port = db.query(DevicePort).filter(DevicePort.id == a_node.port_id).first()
            if port:
                hop["a_device_id"] = port.device_id
        if b_node and b_node.port_id:
            port = db.query(DevicePort).filter(DevicePort.id == b_node.port_id).first()
            if port:
                hop["b_device_id"] = port.device_id
        hops.append(hop)

    return {
        "reachable": True,
        "polyline": polyline,
        "edges": [{"id": e.id, "reversed": r} for e, r in best_path],
        "hops": hops,
        "total_length": best_dist,
    }


def calculate_all_device_paths(db: Session, plan_id: int) -> Dict[int, Dict[str, Any]]:
    """计算所有设备到最近核心交换机的路径

    Args:
        db: 数据库会话
        plan_id: 平面图ID

    Returns:
        {device_id: {reachable, polyline, ...}} 字典
    """
    # 建图
    nodes, adj = build_graph(db, plan_id)
    node_positions = get_node_positions(db, nodes)

    # 找所有核心交换机的端口节点（作为终点）
    core_devices = db.query(Device).filter(Device.device_type == "core_switch").all()
    core_device_ids = [d.id for d in core_devices]

    core_port_nodes = []
    for n in nodes:
        if n.node_kind == "port" and n.port_id:
            port = db.query(DevicePort).filter(DevicePort.id == n.port_id).first()
            if port and port.device_id in core_device_ids:
                core_port_nodes.append(n.id)

    if not core_port_nodes:
        return {}

    # 找所有非核心设备的端口节点（作为起点）
    all_port_nodes = []
    device_to_nodes = {}  # device_id -> [node_ids]

    for n in nodes:
        if n.node_kind == "port" and n.port_id:
            port = db.query(DevicePort).filter(DevicePort.id == n.port_id).first()
            if port:
                all_port_nodes.append((n.id, port.device_id))
                if port.device_id not in device_to_nodes:
                    device_to_nodes[port.device_id] = []
                device_to_nodes[port.device_id].append(n.id)

    # 排除核心设备
    non_core_devices = [d for d in device_to_nodes.keys() if d not in core_device_ids]

    device_paths = {}

    for device_id in non_core_devices:
        start_nodes = device_to_nodes.get(device_id, [])

        # 多起点 → 多终点 Dijkstra
        best_path = None
        best_dist = float("inf")
        best_end = None

        for start in start_nodes:
            # 从起点跑 Dijkstra，到任意核心
            edge_seq = shortest_path_multi_target(adj, start, core_port_nodes)
            if edge_seq:
                total_w = sum(
                    e.length_weight if e.length_weight else edge_geometry_length(e, node_positions)
                    for e, _ in edge_seq
                )
                if total_w < best_dist:
                    best_dist = total_w
                    best_path = edge_seq

        if best_path:
            polyline = path_to_polyline(best_path, node_positions)
            device_paths[device_id] = {
                "reachable": True,
                "polyline": polyline,
                "total_length": best_dist,
            }
        else:
            device_paths[device_id] = {
                "reachable": False,
                "reason": "无连通路径",
            }

    return device_paths


def shortest_path_multi_target(
    adj: Dict[int, List[Tuple[int, TopoEdge, float, bool]]],
    start_node_id: int,
    target_node_ids: List[int]
) -> Optional[List[Tuple[TopoEdge, bool]]]:
    """Dijkstra 多终点（到任意一个终点即停）

    Args:
        adj: 邻接表
        start_node_id: 起点
        target_node_ids: 终点列表

    Returns:
        边序列 [(edge, reversed), ...] 或 None
    """
    if start_node_id in target_node_ids:
        return []

    dist = {start_node_id: 0.0}
    prev = {}
    pq = [(0.0, start_node_id)]
    reached_target = None

    while pq:
        d, u = heapq.heappop(pq)

        # 到达任意终点
        if u in target_node_ids:
            reached_target = u
            break

        if d > dist.get(u, 1e18):
            continue

        for v, edge, w, rev in adj.get(u, []):
            nd = d + w
            if nd < dist.get(v, 1e18):
                dist[v] = nd
                prev[v] = (u, edge, rev)
                heapq.heappush(pq, (nd, v))

    if not reached_target:
        return None

    # 回溯
    edge_seq = []
    cur = reached_target
    while cur != start_node_id:
        pu, edge, rev = prev[cur]
        edge_seq.append((edge, rev))
        cur = pu
    edge_seq.reverse()

    return edge_seq