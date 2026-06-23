"""
初始化图模型数据脚本（按设计决策重构）

设计决策：
- 图模型（topo_nodes+topo_edges）为唯一真理来源
- 一条主干 = 一个光缆编号（所有分段共享 cable_id）
- 分支光缆单独编号
- 分支点编号手填（存于 TopoNode.label）
- 数据链路状态只看设备 online/offline
- 旧数据可丢

运行方式：
    python scripts/init_topo_graph.py [--plan-id PLAN_ID]

清理并重建图模型数据，分配 cable_id/cable_no。
"""

import sys
import os
import json
import math
import argparse
from typing import List, Tuple, Optional, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.shared.database import get_db_manager
from app.shared.models import (
    TopoNode, TopoEdge, DevicePort, Device, DeviceNode, FloorPlan
)


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
    """提取区间内的真实拐点（不插入投影点）"""
    if s_start >= s_end:
        return []

    result = []
    cumulative_len = 0.0

    for i in range(len(polyline) - 1):
        seg_len = distance(polyline[i], polyline[i + 1])
        seg_s_start = cumulative_len
        seg_s_end = cumulative_len + seg_len

        # 只提取真实的拐点（polyline[i]，当 i > 0 时）
        if i > 0 and seg_s_start > s_start and seg_s_start < s_end:
            result.append({'x': polyline[i][0], 'y': polyline[i][1]})

        cumulative_len += seg_len

    return result


def clear_topo_data(db: Session, plan_id: int = None):
    """清空图模型数据"""
    if plan_id:
        db.query(TopoEdge).filter(TopoEdge.floor_plan_id == plan_id).delete()
        db.query(TopoNode).filter(TopoNode.floor_plan_id == plan_id).delete()
        db.query(DevicePort).filter(DevicePort.is_auto_created == True).delete()
    else:
        db.query(TopoEdge).delete()
        db.query(TopoNode).delete()
        db.query(DevicePort).filter(DevicePort.is_auto_created == True).delete()
    db.commit()


def init_plan(db: Session, plan_id: int) -> dict:
    """初始化单个平面图的图模型数据"""

    stats = {"nodes": 0, "edges": 0, "ports": 0}
    print(f"\n=== 初始化平面图 {plan_id} ===")

    # 获取设备节点
    device_nodes = db.query(DeviceNode).filter(DeviceNode.floor_plan_id == plan_id).all()
    print(f"  DeviceNodes: {len(device_nodes)}")

    # 为每个设备创建端口 + TopoNode(port)
    device_to_port = {}
    device_to_topo_node = {}
    next_cable_id = 1

    for dn in device_nodes:
        port = DevicePort(
            device_id=dn.device_id,
            name=f"auto-{dn.id}",
            port_type="ethernet",
            anchor_x=0.5,
            anchor_y=0.5,
            is_auto_created=True,
        )
        db.add(port)
        db.flush()
        stats["ports"] += 1
        device_to_port[dn.device_id] = port

        topo_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="port",
            port_id=port.id,
            x_percent=float(dn.x_percent),
            y_percent=float(dn.y_percent),
        )
        db.add(topo_node)
        db.flush()
        stats["nodes"] += 1
        device_to_topo_node[dn.device_id] = topo_node

    # 获取旧系统的主干和分支数据
    from app.shared.models import FiberTrunkLink, FiberBranchPoint, DeviceLink

    fiber_trunks = db.query(FiberTrunkLink).filter(FiberTrunkLink.floor_plan_id == plan_id).all()
    print(f"  FiberTrunks: {len(fiber_trunks)}")

    trunk_to_endpoints = {}
    trunk_to_polyline = {}

    # 创建主干端点 junction
    for trunk in fiber_trunks:
        start_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="junction",
            junction_type="trunk_endpoint",
            x_percent=float(trunk.start_x_percent),
            y_percent=float(trunk.start_y_percent),
            label=f"trunk-{trunk.id}-start",
        )
        db.add(start_node)
        db.flush()
        stats["nodes"] += 1

        end_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="junction",
            junction_type="trunk_endpoint",
            x_percent=float(trunk.end_x_percent),
            y_percent=float(trunk.end_y_percent),
            label=f"trunk-{trunk.id}-end",
        )
        db.add(end_node)
        db.flush()
        stats["nodes"] += 1

        trunk_to_endpoints[trunk.id] = (start_node, end_node)

        # 构建主干折线
        polyline = [(float(trunk.start_x_percent), float(trunk.start_y_percent))]
        if trunk.waypoints:
            try:
                for wp in json.loads(trunk.waypoints):
                    polyline.append((float(wp['x']), float(wp['y']))
            except:
                pass
        polyline.append((float(trunk.end_x_percent), float(trunk.end_y_percent)))
        trunk_to_polyline[trunk.id] = polyline

    # 分支点切段主干
    branch_points = db.query(FiberBranchPoint).filter(
        FiberBranchPoint.trunk_link_id.in_([t.id for t in fiber_trunks])
    ).all()
    print(f"  BranchPoints: {len(branch_points)}")

    bp_to_node = {}
    trunk_cable_ids = {}  # trunk_id -> cable_id

    for trunk in fiber_trunks:
        trunk_id = trunk.id
        start_node, end_node = trunk_to_endpoints[trunk_id]
        polyline = trunk_to_polyline[trunk_id]
        total_len = polyline_total_length(polyline)

        # 分配 cable_id 和 cable_no
        cable_id = next_cable_id
        next_cable_id += 1
        cable_no = f"TRUNK-{trunk.id}"
        trunk_cable_ids[trunk_id] = cable_id

        # 获取该主干上的分支点
        bps_on_trunk = [bp for bp in branch_points if bp.trunk_link_id == trunk_id]

        if not bps_on_trunk:
            # 无分支点：整条主干一条边
            edge = TopoEdge(
                floor_plan_id=plan_id,
                a_node_id=start_node.id,
                b_node_id=end_node.id,
                cable_type="trunk",
                waypoints=trunk.waypoints,
                cable_name=f"主干-{trunk.id}",
                cable_id=cable_id,
                cable_no=cable_no,
                status="up",
            )
            db.add(edge)
            stats["edges"] += 1

            # 关联核心设备
            if trunk.start_device_id:
                core_node = device_to_topo_node.get(trunk.start_device_id)
                if core_node:
                    connect_edge = TopoEdge(
                        floor_plan_id=plan_id,
                        a_node_id=start_node.id,
                        b_node_id=core_node.id,
                        cable_type="trunk_to_core",
                        cable_id=cable_id,
                        cable_no=cable_no,
                        cable_name=f"主干-{trunk.id}-核心-{trunk.start_device_id}",
                        status="up",
                    )
                    db.add(connect_edge)
                    stats["edges"] += 1
            continue

        # 有分支点：切段
        bp_projections = []
        for bp in bps_on_trunk:
            bp_coord = (float(bp.x_percent), float(bp.y_percent))
            s, proj = project_point_on_polyline(bp_coord, polyline)

            bp_node = TopoNode(
                floor_plan_id=plan_id,
                node_kind="junction",
                junction_type="branch_point",
                x_percent=float(proj[0]),
                y_percent=float(proj[1]),
                label=bp.name or f"BP-{bp.id}",  # 手填编号
            )
            db.add(bp_node)
            db.flush()
            stats["nodes"] += 1
            bp_to_node[bp.id] = bp_node
            bp_projections.append((s, proj, bp, bp_node))

        # 按 s 排序
        bp_projections.sort(key=lambda t: t[0])

        # 切点序列
        cut_points = [(0.0, start_node)]
        for s, proj, bp, bp_node in bp_projections:
            cut_points.append((s, bp_node))
        cut_points.append((total_len, end_node))

        # 创建每段边
        for i in range(len(cut_points) - 1):
            s_start, node_a = cut_points[i]
            s_end, node_b = cut_points[i + 1]

            # 提取真实拐点
            sub_wps = extract_waypoints_in_range(polyline, s_start, s_end)
            waypoints_json = json.dumps(sub_wps) if sub_wps else None

            edge = TopoEdge(
                floor_plan_id=plan_id,
                a_node_id=node_a.id,
                b_node_id=node_b.id,
                cable_type="trunk_segment",
                waypoints=waypoints_json,
                cable_name=f"主干-{trunk.id}-段{i+1}",
                cable_id=cable_id,  # 所有段共享同一 cable_id
                cable_no=cable_no,
                status="up",
            )
            db.add(edge)
            stats["edges"] += 1

        # 关联核心设备
        if trunk.start_device_id:
            core_node = device_to_topo_node.get(trunk.start_device_id)
            if core_node:
                connect_edge = TopoEdge(
                    floor_plan_id=plan_id,
                    a_node_id=start_node.id,
                    b_node_id=core_node.id,
                    cable_type="trunk_to_core",
                    cable_id=cable_id,
                    cable_no=cable_no,
                    cable_name=f"主干-{trunk.id}-核心-{trunk.start_device_id}",
                    status="up",
                )
                db.add(connect_edge)
                stats["edges"] += 1

    # 分支光缆（junction → port）
    fiber_branch_links = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.link_role == "fiber_branch"
    ).all()
    print(f"  FiberBranchLinks: {len(fiber_branch_links)}")

    for link in fiber_branch_links:
        if not link.branch_point_id:
            continue

        bp_node = bp_to_node.get(link.branch_point_id)
        if not bp_node:
            continue

        to_dn = db.query(DeviceNode).filter(DeviceNode.id == link.to_node_id).first()
        if not to_dn:
            continue

        device_node = device_to_topo_node.get(to_dn.device_id)
        if not device_node:
            continue

        # 分配独立的 cable_id 和 cable_no
        cable_id = next_cable_id
        next_cable_id += 1
        cable_no = f"BR-{link.id}"

        edge = TopoEdge(
            floor_plan_id=plan_id,
            a_node_id=bp_node.id,
            b_node_id=device_node.id,
            cable_type="fiber",
            waypoints=link.waypoints,
            cable_name=f"分支光缆-{link.id}",
            cable_id=cable_id,
            cable_no=cable_no,
            status="up",
        )
        db.add(edge)
        stats["edges"] += 1

    db.commit()

    print(f"  统计: ports={stats['ports']}, nodes={stats['nodes']}, edges={stats['edges']}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="初始化图模型数据")
    parser.add_argument("--plan-id", type=int, help="只初始化指定平面图")
    args = parser.parse_args()

    db = get_db_manager().get_session()

    if args.plan_id:
        plan_ids = [args.plan_id]
    else:
        plans = db.query(FloorPlan).all()
        plan_ids = [p.id for p in plans]

    total = {"nodes": 0, "edges": 0, "ports": 0}

    for plan_id in plan_ids:
        clear_topo_data(db, plan_id)
        stats = init_plan(db, plan_id)
        total["nodes"] += stats["nodes"]
        total["edges"] += stats["edges"]
        total["ports"] += stats["ports"]

    print("\n=== 总计 ===")
    print(f"Ports: {total['ports']}")
    print(f"Nodes: {total['nodes']}")
    print(f"Edges: {total['edges']}")


if __name__ == "__main__":
    main()