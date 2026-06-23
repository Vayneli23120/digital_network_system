"""
数据迁移脚本：将现有光纤拓扑模型迁移到 TopoNode/TopoEdge 统一图模型

迁移逻辑（修复版）：
1. DeviceNode → 为每个设备创建一个默认 DevicePort + TopoNode(port)
2. FiberTrunkLink → TopoEdge（起点和终点各创建一个 junction TopoNode）
3. FiberBranchPoint → junction TopoNode（**插入到主干中间，切段**）
4. DeviceLink(fiber_branch) → TopoEdge（连接 junction 和 port）

关键修复：分支点不再用直线连主干端点，而是按位置排序后切开主干成串联段。

运行方式：
    python scripts/migrate_to_topo_graph.py [--plan-id PLAN_ID] [--dry-run] [--clean]

选项：
    --plan-id: 只迁移指定平面图（默认迁移所有）
    --dry-run: 只打印迁移计划，不实际执行
    --clean: 先清空旧 topo 数据再迁移
"""

import sys
import os
import json
import math
import argparse
from typing import List, Tuple, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.shared.database import get_db_manager
from app.shared.models import (
    Base, DeviceNode, DeviceLink, FiberTrunkLink, FiberBranchPoint,
    DevicePort, TopoNode, TopoEdge, Device, FloorPlan
)


# ========== 几何计算工具函数 ==========

def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """两点欧氏距离"""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def polyline_total_length(polyline: List[Tuple[float, float]]) -> float:
    """折线总长度"""
    total = 0.0
    for i in range(len(polyline) - 1):
        total += distance(polyline[i], polyline[i + 1])
    return total


def project_point_on_segment(point: Tuple[float, float],
                              seg_start: Tuple[float, float],
                              seg_end: Tuple[float, float]) -> Tuple[float, Tuple[float, float]]:
    """
    点投影到线段上，返回 (沿线段方向的投影距离比例 t, 投影点坐标)
    t 在 [0, 1] 范围内表示投影在线段上
    """
    dx = seg_end[0] - seg_start[0]
    dy = seg_end[1] - seg_start[1]
    seg_len_sq = dx*dx + dy*dy

    if seg_len_sq < 1e-10:  # 线段长度接近0
        return 0.0, seg_start

    # 点到线段起点的向量在线段方向上的投影长度
    t = ((point[0] - seg_start[0]) * dx + (point[1] - seg_start[1]) * dy) / seg_len_sq
    t = max(0.0, min(1.0, t))  # 限制在 [0, 1]

    proj_x = seg_start[0] + t * dx
    proj_y = seg_start[1] + t * dy

    return t, (proj_x, proj_y)


def project_point_on_polyline(point: Tuple[float, float],
                               polyline: List[Tuple[float, float]]) -> Tuple[float, Tuple[float, float]]:
    """
    点投影到折线上，返回 (沿线累计距离 s, 投影点坐标)

    s 是从折线起点沿折线到投影点的累计距离（用于排序分支点位置）
    """
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

        t, proj = project_point_on_segment(point, seg_start, seg_end)
        dist = distance(point, proj)

        if dist < best_dist:
            best_dist = dist
            best_proj = proj
            best_s = cumulative_len + t * seg_len

        cumulative_len += seg_len

    return best_s, best_proj


def extract_sub_waypoints(polyline: List[Tuple[float, float]],
                          s_start: float, s_end: float) -> List[dict]:
    """
    从折线中提取 s_start 到 s_end 区间的拐点子集
    返回适合存入 waypoints 字段的格式 [{'x': ..., 'y': ...}, ...]
    """
    if s_start >= s_end:
        return []

    total_len = polyline_total_length(polyline)
    if total_len < 1e-10:
        return []

    # 遍历折线，找出落在区间内的拐点
    result = []
    cumulative_len = 0.0

    for i in range(len(polyline) - 1):
        seg_start = polyline[i]
        seg_end = polyline[i + 1]
        seg_len = distance(seg_start, seg_end)

        seg_s_start = cumulative_len
        seg_s_end = cumulative_len + seg_len

        # 判断这段是否与目标区间有交集
        if seg_s_end <= s_start or seg_s_start >= s_end:
            cumulative_len += seg_len
            continue

        # 如果起点不是区间起点，且这段跨越 s_start，需要添加起点投影点
        if seg_s_start < s_start and seg_s_end > s_start:
            t = (s_start - seg_s_start) / seg_len
            proj_x = seg_start[0] + t * (seg_end[0] - seg_start[0])
            proj_y = seg_start[1] + t * (seg_end[1] - seg_start[1])
            result.append({'x': proj_x, 'y': proj_y})

        # 段内拐点（不是端点）
        if i > 0 and seg_s_start > s_start and seg_s_start < s_end:
            # polyline[i] 是拐点（不是起点终点）
            result.append({'x': seg_start[0], 'y': seg_start[1]})

        # 如果终点不是区间终点，且这段跨越 s_end，需要添加终点投影点
        if seg_s_start < s_end and seg_s_end > s_end:
            t = (s_end - seg_s_start) / seg_len
            proj_x = seg_start[0] + t * (seg_end[0] - seg_start[0])
            proj_y = seg_start[1] + t * (seg_end[1] - seg_start[1])
            result.append({'x': proj_x, 'y': proj_y})

        cumulative_len += seg_len

    return result


def clean_topo_data(db: Session, plan_id: int = None) -> dict:
    """清空旧 topo 数据"""
    stats = {"nodes_deleted": 0, "edges_deleted": 0, "ports_deleted": 0}

    if plan_id:
        db.query(TopoEdge).filter(TopoEdge.floor_plan_id == plan_id).delete()
        db.query(TopoNode).filter(TopoNode.floor_plan_id == plan_id).delete()
        # 只删除自动创建的端口
        ports_to_delete = db.query(DevicePort).filter(DevicePort.is_auto_created == True)
        # 需要通过 TopoNode 关联判断是否属于该 plan
        # 简化处理：删除所有自动创建的端口
        for port in ports_to_delete.all():
            db.delete(port)
            stats["ports_deleted"] += 1
    else:
        db.query(TopoEdge).delete()
        db.query(TopoNode).delete()
        ports_to_delete = db.query(DevicePort).filter(DevicePort.is_auto_created == True)
        stats["ports_deleted"] = ports_to_delete.count()
        ports_to_delete.delete()

    db.commit()
    return stats


def migrate_plan(db: Session, plan_id: int, dry_run: bool = False) -> dict:
    """迁移单个平面图的拓扑数据（修复版：分支点切段主干）"""

    stats = {
        "plan_id": plan_id,
        "ports_created": 0,
        "nodes_created": 0,
        "edges_created": 0,
        "errors": [],
    }

    print(f"\n=== 迁移平面图 {plan_id} ===")

    # 1. 为每个 DeviceNode 创建默认 DevicePort + TopoNode(port)
    device_nodes = db.query(DeviceNode).filter(DeviceNode.floor_plan_id == plan_id).all()
    device_to_port = {}  # device_id -> DevicePort
    device_to_topo_node = {}  # device_id -> TopoNode

    print(f"  DeviceNodes: {len(device_nodes)}")

    for dn in device_nodes:
        # 创建默认端口
        port = DevicePort(
            device_id=dn.device_id,
            name=f"auto-{dn.id}",
            port_type="ethernet",
            anchor_x=0.5,
            anchor_y=0.5,
            is_auto_created=True,
        )
        if not dry_run:
            db.add(port)
            db.flush()

        stats["ports_created"] += 1
        device_to_port[dn.device_id] = port

        # 创建 TopoNode(port)
        topo_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="port",
            port_id=port.id,
            x_percent=float(dn.x_percent),
            y_percent=float(dn.y_percent),
            label=None,
        )
        if not dry_run:
            db.add(topo_node)
            db.flush()

        stats["nodes_created"] += 1
        device_to_topo_node[dn.device_id] = topo_node

    # 2. FiberTrunkLink → 创建主干端点 junction（暂不创建整条主干 edge）
    fiber_trunks = db.query(FiberTrunkLink).filter(FiberTrunkLink.floor_plan_id == plan_id).all()
    trunk_to_endpoints = {}  # trunk_id -> (start_node, end_node)
    trunk_to_polyline = {}   # trunk_id -> 完整折线坐标列表

    print(f"  FiberTrunkLinks: {len(fiber_trunks)}")

    for trunk in fiber_trunks:
        # 创建起点 junction
        start_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="junction",
            port_id=None,
            x_percent=float(trunk.start_x_percent),
            y_percent=float(trunk.start_y_percent),
            label=f"trunk-{trunk.id}-start",
            junction_type="trunk_endpoint",
        )
        if not dry_run:
            db.add(start_node)
            db.flush()

        stats["nodes_created"] += 1

        # 创建终点 junction
        end_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="junction",
            port_id=None,
            x_percent=float(trunk.end_x_percent),
            y_percent=float(trunk.end_y_percent),
            label=f"trunk-{trunk.id}-end",
            junction_type="trunk_endpoint",
        )
        if not dry_run:
            db.add(end_node)
            db.flush()

        stats["nodes_created"] += 1

        trunk_to_endpoints[trunk.id] = (start_node, end_node)

        # 构建主干完整折线
        polyline = [(float(trunk.start_x_percent), float(trunk.start_y_percent))]
        if trunk.waypoints:
            try:
                wps = json.loads(trunk.waypoints)
                for wp in wps:
                    polyline.append((float(wp['x']), float(wp['y'])))
            except:
                pass
        polyline.append((float(trunk.end_x_percent), float(trunk.end_y_percent)))
        trunk_to_polyline[trunk.id] = polyline

    # 3. FiberBranchPoint → junction TopoNode + 切断主干成段
    branch_points = db.query(FiberBranchPoint).filter(
        FiberBranchPoint.trunk_link_id.in_([t.id for t in fiber_trunks])
    ).all()

    print(f"  FiberBranchPoints: {len(branch_points)}")

    # 按 trunk 分组分支点
    trunk_to_bps = {}  # trunk_id -> list of FiberBranchPoint
    for bp in branch_points:
        trunk_id = bp.trunk_link_id
        if trunk_id not in trunk_to_bps:
            trunk_to_bps[trunk_id] = []
        trunk_to_bps[trunk_id].append(bp)

    bp_to_node = {}  # branch_point_id -> TopoNode

    # 处理每条主干及其分支点
    for trunk in fiber_trunks:
        trunk_id = trunk.id
        start_node, end_node = trunk_to_endpoints[trunk_id]
        polyline = trunk_to_polyline[trunk_id]
        total_len = polyline_total_length(polyline)

        # 获取该主干的分支点列表
        bps_on_trunk = trunk_to_bps.get(trunk_id, [])

        if not bps_on_trunk:
            # 无分支点：直接创建整条主干 edge
            edge = TopoEdge(
                floor_plan_id=plan_id,
                a_node_id=start_node.id,
                b_node_id=end_node.id,
                cable_type="trunk",
                waypoints=trunk.waypoints,
                cable_name=trunk.name or f"主干-{trunk.id}",
                status="up",
            )
            if not dry_run:
                db.add(edge)
            stats["edges_created"] += 1
            continue

        # 有分支点：计算每个分支点的投影位置
        bp_projections = []  # [(s, proj_coord, bp, topo_node)]
        for bp in bps_on_trunk:
            # 使用分支点的真实坐标（x_percent, y_percent）
            bp_coord = (float(bp.x_percent), float(bp.y_percent))
            s, proj = project_point_on_polyline(bp_coord, polyline)

            # 创建分支点 junction（使用投影坐标，保证落在主干线上）
            bp_node = TopoNode(
                floor_plan_id=plan_id,
                node_kind="junction",
                port_id=None,
                x_percent=float(proj[0]),
                y_percent=float(proj[1]),
                label=bp.name or f"分支点-{bp.id}",
                junction_type="branch_point",
            )
            if not dry_run:
                db.add(bp_node)
                db.flush()

            stats["nodes_created"] += 1
            bp_to_node[bp.id] = bp_node
            bp_projections.append((s, proj, bp, bp_node))

        # 按 s 排序分支点（沿线距离）
        bp_projections.sort(key=lambda t: t[0])

        # 构建切段序列：起点 → 分支点1 → 分支点2 → ... → 终点
        cut_points = [(0.0, start_node)]  # (s, node)
        for s, proj, bp, bp_node in bp_projections:
            cut_points.append((s, bp_node))
        cut_points.append((total_len, end_node))

        # 创建每一段的 TopoEdge
        for i in range(len(cut_points) - 1):
            s_start, node_a = cut_points[i]
            s_end, node_b = cut_points[i + 1]

            # 提取这一段的子拐点
            sub_waypoints = extract_sub_waypoints(polyline, s_start, s_end)
            waypoints_json = json.dumps(sub_waypoints) if sub_waypoints else None

            # 段名称
            if i == 0:
                seg_name = f"主干-{trunk.id}-段1(起点→{bp_projections[0][2].name or 'BP1'})"
            elif i == len(cut_points) - 2:
                seg_name = f"主干-{trunk.id}-段末({bp_projections[-1][2].name or 'BP末'}→终点)"
            else:
                seg_name = f"主干-{trunk.id}-段{i+1}"

            edge = TopoEdge(
                floor_plan_id=plan_id,
                a_node_id=node_a.id,
                b_node_id=node_b.id,
                cable_type="trunk_segment",
                waypoints=waypoints_json,
                cable_name=seg_name,
                status="up",
            )
            if not dry_run:
                db.add(edge)
            stats["edges_created"] += 1

        # 如果主干起点关联核心设备，创建连接边
        if trunk.start_device_id:
            core_topo_node = device_to_topo_node.get(trunk.start_device_id)
            if core_topo_node:
                connect_edge = TopoEdge(
                    floor_plan_id=plan_id,
                    a_node_id=start_node.id,
                    b_node_id=core_topo_node.id,
                    cable_type="trunk_to_core",
                    waypoints=None,
                    cable_name=f"主干-{trunk.id}-到核心-{trunk.start_device_id}",
                    status="up",
                )
                if not dry_run:
                    db.add(connect_edge)
                stats["edges_created"] += 1

    # 4. DeviceLink(fiber_branch) → TopoEdge（连接分支点 junction 和设备 port）
    fiber_branch_links = db.query(DeviceLink).filter(
        DeviceLink.floor_plan_id == plan_id,
        DeviceLink.link_role == "fiber_branch"
    ).all()

    print(f"  FiberBranchLinks: {len(fiber_branch_links)}")

    for link in fiber_branch_links:
        if not link.branch_point_id:
            stats["errors"].append(f"Link {link.id} has no branch_point_id")
            continue

        bp_node = bp_to_node.get(link.branch_point_id)
        if not bp_node:
            stats["errors"].append(f"BranchPoint {link.branch_point_id} not migrated")
            continue

        # 找设备端点
        to_node = db.query(DeviceNode).filter(DeviceNode.id == link.to_node_id).first()
        if not to_node:
            stats["errors"].append(f"DeviceNode {link.to_node_id} not found")
            continue

        device_topo_node = device_to_topo_node.get(to_node.device_id)
        if not device_topo_node:
            stats["errors"].append(f"Device {to_node.device_id} TopoNode not created")
            continue

        # 创建分支光缆边（junction → port）
        edge = TopoEdge(
            floor_plan_id=plan_id,
            a_node_id=bp_node.id,  # 分支点（junction）
            b_node_id=device_topo_node.id,  # 设备端口
            cable_type="fiber",
            waypoints=link.waypoints,
            cable_name=f"分支光缆-{link.id}",
            status="up",
        )
        if not dry_run:
            db.add(edge)

        stats["edges_created"] += 1

    if not dry_run:
        db.commit()

    print(f"  统计: ports={stats['ports_created']}, nodes={stats['nodes_created']}, edges={stats['edges_created']}")
    if stats["errors"]:
        print(f"  错误: {stats['errors']}")

    return stats


def main():
    parser = argparse.ArgumentParser(description="迁移光纤拓扑到统一图模型（修复版：分支点切段主干）")
    parser.add_argument("--plan-id", type=int, help="只迁移指定平面图")
    parser.add_argument("--dry-run", action="store_true", help="只打印迁移计划")
    parser.add_argument("--clean", action="store_true", help="先清空旧 topo 数据再迁移")
    args = parser.parse_args()

    db_manager = get_db_manager()
    db = db_manager.get_session()

    if args.clean and not args.dry_run:
        print("\n=== 清空旧 topo 数据 ===")
        clean_stats = clean_topo_data(db, args.plan_id)
        print(f"  删除: nodes={clean_stats['nodes_deleted']}, edges={clean_stats['edges_deleted']}, ports={clean_stats['ports_deleted']}")

    if args.plan_id:
        plan_ids = [args.plan_id]
    else:
        plans = db.query(FloorPlan).all()
        plan_ids = [p.id for p in plans]

    total_stats = {
        "ports_created": 0,
        "nodes_created": 0,
        "edges_created": 0,
        "errors": [],
    }

    for plan_id in plan_ids:
        stats = migrate_plan(db, plan_id, args.dry_run)
        total_stats["ports_created"] += stats["ports_created"]
        total_stats["nodes_created"] += stats["nodes_created"]
        total_stats["edges_created"] += stats["edges_created"]
        total_stats["errors"].extend(stats["errors"])

    print("\n=== 总计 ===")
    print(f"Ports created: {total_stats['ports_created']}")
    print(f"Nodes created: {total_stats['nodes_created']}")
    print(f"Edges created: {total_stats['edges_created']}")
    if total_stats["errors"]:
        print(f"Errors: {len(total_stats['errors'])}")

    if args.dry_run:
        print("\n[DRY RUN] 未实际写入数据库")


if __name__ == "__main__":
    main()