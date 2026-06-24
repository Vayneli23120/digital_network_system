"""
Topology Router - PNetLab 式拓扑图 API

提供图寻路和拓扑管理的 API。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.shared.database import get_db
from .graph_path_service import calculate_path, calculate_all_device_paths


router = APIRouter(prefix="/api", tags=["topology-graph"])


# ============ Pydantic 模型 ============

class TopoNodeCreate(BaseModel):
    floor_plan_id: int
    node_kind: str  # 'port' | 'junction'
    port_id: Optional[int] = None
    x_percent: Optional[float] = None
    y_percent: Optional[float] = None
    label: Optional[str] = None
    junction_type: Optional[str] = None


class TopoNodeUpdate(BaseModel):
    x_percent: Optional[float] = None
    y_percent: Optional[float] = None
    label: Optional[str] = None


class TopoEdgeCreate(BaseModel):
    floor_plan_id: int
    a_node_id: int
    b_node_id: int
    cable_type: str = "fiber"
    waypoints: Optional[str] = None  # JSON string
    cable_name: Optional[str] = None
    status: str = "up"


class TopoEdgeUpdate(BaseModel):
    waypoints: Optional[str] = None  # JSON string
    status: Optional[str] = None
    cable_name: Optional[str] = None


class DevicePortCreate(BaseModel):
    device_id: int
    name: str
    port_type: str = "ethernet"
    anchor_x: float = 0.5
    anchor_y: float = 0.5
    is_auto_created: bool = False


# ============ 路径计算 API ============

@router.get("/floor-plans/{plan_id}/path")
async def get_path(
    plan_id: int,
    from_device: int,
    to_device: int,
    db: Session = Depends(get_db)
):
    """计算两个设备之间的路径（Dijkstra 最短路）

    Returns:
        {reachable, polyline, edges, hops, total_length}
    """
    result = calculate_path(db, plan_id, from_device, to_device)
    if result is None:
        raise HTTPException(status_code=404, detail="无法计算路径")
    return result


@router.get("/floor-plans/{plan_id}/device-paths")
async def get_device_paths(plan_id: int, db: Session = Depends(get_db)):
    """计算所有设备到最近核心交换机的路径

    Returns:
        {device_id: {reachable, polyline, ...}}
    """
    return calculate_all_device_paths(db, plan_id)


# ============ 设备端口管理 API ============

from app.shared.models import DevicePort, TopoNode, TopoEdge, Device, FloorPlan


@router.get("/devices/{device_id}/ports")
async def list_device_ports(device_id: int, db: Session = Depends(get_db)):
    """获取设备的端口列表"""
    ports = db.query(DevicePort).filter(DevicePort.device_id == device_id).all()
    return {"items": [
        {
            "id": p.id,
            "device_id": p.device_id,
            "name": p.name,
            "port_type": p.port_type,
            "anchor_x": p.anchor_x,
            "anchor_y": p.anchor_y,
            "is_auto_created": p.is_auto_created,
        }
        for p in ports
    ]}


@router.post("/devices/{device_id}/ports")
async def create_device_port(
    device_id: int,
    data: DevicePortCreate,
    db: Session = Depends(get_db)
):
    """创建设备端口"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    port = DevicePort(
        device_id=device_id,
        name=data.name,
        port_type=data.port_type,
        anchor_x=data.anchor_x,
        anchor_y=data.anchor_y,
        is_auto_created=data.is_auto_created,
    )
    db.add(port)
    db.commit()
    db.refresh(port)

    return {
        "id": port.id,
        "device_id": port.device_id,
        "name": port.name,
        "port_type": port.port_type,
        "anchor_x": port.anchor_x,
        "anchor_y": port.anchor_y,
    }


@router.delete("/devices/{device_id}/ports/{port_id}")
async def delete_device_port(
    device_id: int,
    port_id: int,
    db: Session = Depends(get_db)
):
    """删除设备端口（连带删除关联的 TopoNode 和 TopoEdge）"""
    port = db.query(DevicePort).filter(
        DevicePort.id == port_id,
        DevicePort.device_id == device_id
    ).first()
    if not port:
        raise HTTPException(status_code=404, detail="端口不存在")

    db.delete(port)
    db.commit()
    return {"message": "端口删除成功"}


@router.post("/floor-plans/{plan_id}/ensure-topo-ports")
async def ensure_plan_topo_ports(plan_id: int, db: Session = Depends(get_db)):
    """为平面图上所有已放置设备补建端口及端口 TopoNode（幂等）。

    用于回填在自动建端口逻辑之前放置的旧设备，确保端口到端口连线可用。
    """
    from app.shared.models import DeviceNode
    from .topo_service import ensure_device_topo_ports

    device_nodes = db.query(DeviceNode).filter(
        DeviceNode.floor_plan_id == plan_id
    ).all()

    created = 0
    for dn in device_nodes:
        nodes = ensure_device_topo_ports(db, plan_id, dn.device_id)
        created += len(nodes)
    db.commit()
    return {"message": "端口拓扑节点已补建", "device_count": len(device_nodes), "port_node_count": created}


# ============ 拓扑节点管理 API ============

@router.get("/floor-plans/{plan_id}/topo-nodes")
async def list_topo_nodes(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图的拓扑节点列表"""
    nodes = db.query(TopoNode).filter(TopoNode.floor_plan_id == plan_id).all()
    return {"items": [
        {
            "id": n.id,
            "node_kind": n.node_kind,
            "port_id": n.port_id,
            "x_percent": n.x_percent,
            "y_percent": n.y_percent,
            "label": n.label,
            "junction_type": n.junction_type,
        }
        for n in nodes
    ]}


@router.post("/floor-plans/{plan_id}/topo-nodes")
async def create_topo_node(
    plan_id: int,
    data: TopoNodeCreate,
    db: Session = Depends(get_db)
):
    """创建拓扑节点（junction 类型，用于分支点/熔接点等）"""
    plan = db.query(FloorPlan).filter(FloorPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="平面图不存在")

    if data.node_kind == "port" and not data.port_id:
        raise HTTPException(status_code=400, detail="port 类型节点必须指定 port_id")

    node = TopoNode(
        floor_plan_id=plan_id,
        node_kind=data.node_kind,
        port_id=data.port_id,
        x_percent=data.x_percent,
        y_percent=data.y_percent,
        label=data.label,
        junction_type=data.junction_type,
    )
    db.add(node)
    db.commit()
    db.refresh(node)

    return {
        "id": node.id,
        "node_kind": node.node_kind,
        "x_percent": node.x_percent,
        "y_percent": node.y_percent,
        "label": node.label,
    }


@router.put("/floor-plans/{plan_id}/topo-nodes/{node_id}")
async def update_topo_node(
    plan_id: int,
    node_id: int,
    data: TopoNodeUpdate,
    db: Session = Depends(get_db)
):
    """更新拓扑节点位置"""
    node = db.query(TopoNode).filter(
        TopoNode.id == node_id,
        TopoNode.floor_plan_id == plan_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    if data.x_percent is not None:
        node.x_percent = data.x_percent
    if data.y_percent is not None:
        node.y_percent = data.y_percent
    if data.label is not None:
        node.label = data.label

    db.commit()
    return {
        "id": node.id,
        "x_percent": node.x_percent,
        "y_percent": node.y_percent,
        "label": node.label,
    }


@router.delete("/floor-plans/{plan_id}/topo-nodes/{node_id}")
async def delete_topo_node(
    plan_id: int,
    node_id: int,
    db: Session = Depends(get_db)
):
    """删除拓扑节点（连带删除关联的边）"""
    node = db.query(TopoNode).filter(
        TopoNode.id == node_id,
        TopoNode.floor_plan_id == plan_id
    ).first()
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    db.delete(node)
    db.commit()
    return {"message": "节点删除成功"}


# ============ 拓扑边管理 API ============

@router.get("/floor-plans/{plan_id}/topo-edges")
async def list_topo_edges(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图的拓扑边列表"""
    edges = db.query(TopoEdge).filter(TopoEdge.floor_plan_id == plan_id).all()
    return {"items": [
        {
            "id": e.id,
            "a_node_id": e.a_node_id,
            "b_node_id": e.b_node_id,
            "cable_type": e.cable_type,
            "waypoints": e.waypoints,
            "cable_name": e.cable_name,
            "status": e.status,
        }
        for e in edges
    ]}


@router.post("/floor-plans/{plan_id}/topo-edges")
async def create_topo_edge(
    plan_id: int,
    data: TopoEdgeCreate,
    db: Session = Depends(get_db)
):
    """创建拓扑边（连接两个节点）"""
    # 验证节点存在
    a_node = db.query(TopoNode).filter(
        TopoNode.id == data.a_node_id,
        TopoNode.floor_plan_id == plan_id
    ).first()
    b_node = db.query(TopoNode).filter(
        TopoNode.id == data.b_node_id,
        TopoNode.floor_plan_id == plan_id
    ).first()

    if not a_node or not b_node:
        raise HTTPException(status_code=400, detail="节点不存在")

    edge = TopoEdge(
        floor_plan_id=plan_id,
        a_node_id=data.a_node_id,
        b_node_id=data.b_node_id,
        cable_type=data.cable_type,
        waypoints=data.waypoints,
        cable_name=data.cable_name,
        status=data.status,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)

    return {
        "id": edge.id,
        "a_node_id": edge.a_node_id,
        "b_node_id": edge.b_node_id,
        "cable_type": edge.cable_type,
        "waypoints": edge.waypoints,
        "cable_name": edge.cable_name,
        "status": edge.status,
    }


@router.put("/floor-plans/{plan_id}/topo-edges/{edge_id}")
async def update_topo_edge(
    plan_id: int,
    edge_id: int,
    data: TopoEdgeUpdate,
    db: Session = Depends(get_db)
):
    """更新拓扑边（拐点、状态等）"""
    edge = db.query(TopoEdge).filter(
        TopoEdge.id == edge_id,
        TopoEdge.floor_plan_id == plan_id
    ).first()
    if not edge:
        raise HTTPException(status_code=404, detail="边不存在")

    if data.waypoints is not None:
        edge.waypoints = data.waypoints
    if data.status is not None:
        edge.status = data.status
    if data.cable_name is not None:
        edge.cable_name = data.cable_name

    db.commit()
    return {
        "id": edge.id,
        "waypoints": edge.waypoints,
        "status": edge.status,
        "cable_name": edge.cable_name,
    }


@router.delete("/floor-plans/{plan_id}/topo-edges/{edge_id}")
async def delete_topo_edge(
    plan_id: int,
    edge_id: int,
    db: Session = Depends(get_db)
):
    """删除拓扑边"""
    edge = db.query(TopoEdge).filter(
        TopoEdge.id == edge_id,
        TopoEdge.floor_plan_id == plan_id
    ).first()
    if not edge:
        raise HTTPException(status_code=404, detail="边不存在")

    db.delete(edge)
    db.commit()
    return {"message": "边删除成功"}