"""
数据迁移脚本：将现有光纤拓扑模型迁移到 TopoNode/TopoEdge 统一图模型

迁移逻辑：
1. DeviceNode → 为每个设备创建一个默认 DevicePort + TopoNode(port)
2. FiberTrunkLink → TopoEdge（起点和终点各创建一个 junction TopoNode）
3. FiberBranchPoint → junction TopoNode（使用 x_percent/y_percent 坐标）
4. DeviceLink(fiber_branch) → TopoEdge（连接 junction 和 port）

运行方式：
    python scripts/migrate_to_topo_graph.py [--plan-id PLAN_ID] [--dry-run]

选项：
    --plan-id: 只迁移指定平面图（默认迁移所有）
    --dry-run: 只打印迁移计划，不实际执行
"""

import sys
import os
import json
import argparse

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.shared.database import get_db_manager
from app.shared.models import (
    Base, DeviceNode, DeviceLink, FiberTrunkLink, FiberBranchPoint,
    DevicePort, TopoNode, TopoEdge, Device, FloorPlan
)


def migrate_plan(db: Session, plan_id: int, dry_run: bool = False) -> dict:
    """迁移单个平面图的拓扑数据

    Returns:
        迁移统计信息
    """
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
            db.flush()  # 获取 ID

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

    # 2. FiberTrunkLink → TopoEdge（创建 junction 端点）
    fiber_trunks = db.query(FiberTrunkLink).filter(FiberTrunkLink.floor_plan_id == plan_id).all()
    trunk_to_nodes = {}  # trunk_id -> (start_node, end_node)

    print(f"  FiberTrunkLinks: {len(fiber_trunks)}")

    for trunk in fiber_trunks:
        # 创建起点 junction（可能关联核心设备）
        start_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="junction",
            port_id=None,
            x_percent=trunk.start_x_percent,
            y_percent=trunk.start_y_percent,
            label=f"trunk-{trunk.id}-start",
            junction_type="trunk_endpoint",
        )
        if not dry_run:
            db.add(start_node)
            db.flush()

        # 如果起点关联核心设备，也可以创建 port 连接
        # 这里暂时用 junction，后续用户可以手动连接

        stats["nodes_created"] += 1

        # 创建终点 junction
        end_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="junction",
            port_id=None,
            x_percent=trunk.end_x_percent,
            y_percent=trunk.end_y_percent,
            label=f"trunk-{trunk.id}-end",
            junction_type="trunk_endpoint",
        )
        if not dry_run:
            db.add(end_node)
            db.flush()

        stats["nodes_created"] += 1

        trunk_to_nodes[trunk.id] = (start_node, end_node)

        # 创建 TopoEdge（主干）
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

    # 3. FiberBranchPoint → junction TopoNode
    branch_points = db.query(FiberBranchPoint).filter(
        FiberBranchPoint.trunk_link_id.in_([t.id for t in fiber_trunks])
    ).all()
    bp_to_node = {}  # branch_point_id -> TopoNode

    print(f"  FiberBranchPoints: {len(branch_points)}")

    for bp in branch_points:
        # 使用真实坐标（不再是 position_percent 投影）
        bp_node = TopoNode(
            floor_plan_id=plan_id,
            node_kind="junction",
            port_id=None,
            x_percent=bp.x_percent,
            y_percent=bp.y_percent,
            label=bp.name or f"分支点-{bp.id}",
            junction_type="branch_point",
        )
        if not dry_run:
            db.add(bp_node)
            db.flush()

        stats["nodes_created"] += 1
        bp_to_node[bp.id] = bp_node

        # 在分支点和主干之间创建连接边
        trunk = next((t for t in fiber_trunks if t.id == bp.trunk_link_id), None)
        if trunk and trunk.id in trunk_to_nodes:
            # 分支点连接到主干（这里需要判断分支点在哪一侧）
            # 简化处理：分支点连接到主干两端
            start_node, end_node = trunk_to_nodes[trunk.id]

            # 选择最近的端点
            bp_dist_start = (bp.x_percent - trunk.start_x_percent)**2 + (bp.y_percent - trunk.start_y_percent)**2
            bp_dist_end = (bp.x_percent - trunk.end_x_percent)**2 + (bp.y_percent - trunk.end_y_percent)**2

            # 分支点应该连接到主干本身，这里简化处理
            # 实际上分支点是主干的"分叉点"，应该直接在主干边上
            # 这里暂时创建一条从分支点到主干端点的连接边
            # 后续用户可能需要调整

    # 4. DeviceLink(fiber_branch) → TopoEdge
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
    parser = argparse.ArgumentParser(description="迁移光纤拓扑到统一图模型")
    parser.add_argument("--plan-id", type=int, help="只迁移指定平面图")
    parser.add_argument("--dry-run", action="store_true", help="只打印迁移计划")
    args = parser.parse_args()

    db_manager = get_db_manager()
    db = next(db_manager.get_db())

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