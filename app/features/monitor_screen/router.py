"""
Monitor Screen Router - 系统监控大屏 API

提供平面图管理、设备节点管理、设备详情、离线告警等 API。
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
import shutil
from datetime import datetime
from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.config import get_config
from .monitor_service import (
    get_floor_plans, get_floor_plan, create_floor_plan, update_floor_plan, delete_floor_plan,
    get_floor_plan_nodes, create_device_node, update_device_node, delete_device_node,
    get_device_detail, get_offline_alerts, get_available_devices, get_plan_snapshot, get_plan_topology, get_global_summary,
    list_device_links, create_device_link, update_device_link, delete_device_link,
)

config = get_config()
router = APIRouter(prefix="/api", tags=["monitor-screen"])


# ============ Pydantic 模型 ============

class FloorPlanCreate(BaseModel):
    name: str


class FloorPlanUpdate(BaseModel):
    name: Optional[str] = None


class DeviceNodeCreate(BaseModel):
    device_id: int
    x_percent: float
    y_percent: float


class DeviceNodeUpdate(BaseModel):
    x_percent: Optional[float] = None
    y_percent: Optional[float] = None
    scale: Optional[float] = None  # 缩放比例 (0.5-3.0)


class DeviceLinkCreate(BaseModel):
    from_node_id: int
    to_node_id: int
    link_role: str = "uplink"  # uplink / svl / portchannel-member
    link_group: Optional[str] = None
    link_type: str = "fiber"


class DeviceLinkUpdate(BaseModel):
    link_role: Optional[str] = None
    link_group: Optional[str] = None
    waypoints: Optional[str] = None  # JSON string


# ============ 平面图管理 API ============

@router.get("/floor-plans")
async def list_floor_plans(db: Session = Depends(get_db)):
    """获取平面图列表"""
    return {"items": get_floor_plans(db)}


@router.get("/floor-plans/{plan_id}")
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """获取单个平面图详情"""
    result = get_floor_plan(db, plan_id)
    if not result:
        raise HTTPException(status_code=404, detail="平面图不存在")
    return result


@router.post("/floor-plans")
async def create_plan(
    name: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传平面图"""
    # 确保上传目录存在
    upload_dir = Path(config.storage.photo_dir) / "floor_plans"
    upload_dir.mkdir(parents=True, exist_ok=True)

    # 生成安全的文件名（处理中文和特殊字符）
    import re
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    # 获取原始扩展名
    original_ext = Path(image.filename).suffix if image.filename else ".jpg"
    # 使用时间戳作为文件名，避免中文/空格问题
    filename = f"{timestamp}{original_ext}"
    file_path = upload_dir / filename

    # 保存文件
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    # 创建数据库记录
    result = create_floor_plan(db, name, str(file_path))
    return result


@router.put("/floor-plans/{plan_id}")
async def update_plan(
    plan_id: int,
    name: Optional[str] = None,
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """更新平面图（可更换图片）"""
    image_path = None
    if image:
        upload_dir = Path(config.storage.photo_dir) / "floor_plans"
        upload_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        # 获取原始扩展名，使用时间戳作为文件名
        original_ext = Path(image.filename).suffix if image.filename else ".jpg"
        filename = f"{timestamp}{original_ext}"
        file_path = upload_dir / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_path = str(file_path)

    result = update_floor_plan(db, plan_id, name=name, image_path=image_path)
    if not result:
        raise HTTPException(status_code=404, detail="平面图不存在")
    return result


@router.delete("/floor-plans/{plan_id}")
async def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    """删除平面图"""
    success = delete_floor_plan(db, plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="平面图不存在")
    return {"message": "平面图删除成功"}


# ============ 设备节点管理 API ============

@router.get("/floor-plans/{plan_id}/nodes")
async def list_nodes(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图上的设备节点"""
    nodes = get_floor_plan_nodes(db, plan_id)
    return {"items": nodes}


@router.get("/floor-plans/{plan_id}/snapshot")
async def get_snapshot(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图全量快照 - 用于 WebSocket 重连对账

    返回所有节点完整状态 + 统计数据，前端重连时直接覆盖本地状态，
    防止乐观增减导致的计数漂移。
    """
    result = get_plan_snapshot(db, plan_id)
    return result


@router.get("/floor-plans/{plan_id}/topology")
async def get_topology(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图拓扑数据 - 用于数字孪生渲染

    返回：
    - nodes: 节点列表（包含位置、状态）
    - links: 链路列表（包含角色、分组）
    - groups: PortChannel/SVL 聚合组（逻辑链路）
    - impacted_node_ids: 受影响节点 IDs（冗余感知）
    """
    result = get_plan_topology(db, plan_id)
    return result


@router.get("/floor-plans/{plan_id}/available-devices")
async def list_available_devices(plan_id: int, db: Session = Depends(get_db)):
    """获取可添加到平面图的设备列表"""
    devices = get_available_devices(db, plan_id)
    return {"items": devices}


@router.post("/floor-plans/{plan_id}/nodes")
async def create_node(plan_id: int, node_data: DeviceNodeCreate, db: Session = Depends(get_db)):
    """创建设备节点"""
    result = create_device_node(db, plan_id, node_data.device_id, node_data.x_percent, node_data.y_percent)
    if not result:
        raise HTTPException(status_code=404, detail="平面图或设备不存在")
    return result


@router.put("/floor-plans/{plan_id}/nodes/{node_id}")
async def update_node(plan_id: int, node_id: int, node_data: DeviceNodeUpdate, db: Session = Depends(get_db)):
    """更新设备节点位置和大小"""
    result = update_device_node(db, plan_id, node_id, node_data.x_percent, node_data.y_percent, node_data.scale)
    if not result:
        raise HTTPException(status_code=404, detail="节点不存在")
    return result


@router.delete("/floor-plans/{plan_id}/nodes/{node_id}")
async def delete_node(plan_id: int, node_id: int, db: Session = Depends(get_db)):
    """删除设备节点"""
    success = delete_device_node(db, plan_id, node_id)
    if not success:
        raise HTTPException(status_code=404, detail="节点不存在")
    return {"message": "节点删除成功"}


# ============ 设备链路管理 API ============

@router.get("/floor-plans/{plan_id}/links")
async def list_links(plan_id: int, db: Session = Depends(get_db)):
    """获取平面图上的设备链路列表"""
    links = list_device_links(db, plan_id)
    return {"items": links}


@router.post("/floor-plans/{plan_id}/links")
async def create_link(plan_id: int, link_data: DeviceLinkCreate, db: Session = Depends(get_db)):
    """创建设备链路"""
    result = create_device_link(db, plan_id, link_data.from_node_id, link_data.to_node_id,
                                link_data.link_role, link_data.link_group, link_data.link_type)
    if not result:
        raise HTTPException(status_code=400, detail="链路创建失败：节点不存在或不属于该平面图")
    return result


@router.put("/floor-plans/{plan_id}/links/{link_id}")
async def update_link(plan_id: int, link_id: int, link_data: DeviceLinkUpdate, db: Session = Depends(get_db)):
    """更新设备链路"""
    result = update_device_link(db, plan_id, link_id, link_data.link_role, link_data.link_group, link_data.waypoints)
    if not result:
        raise HTTPException(status_code=404, detail="链路不存在")
    return result


@router.delete("/floor-plans/{plan_id}/links/{link_id}")
async def delete_link(plan_id: int, link_id: int, db: Session = Depends(get_db)):
    """删除设备链路"""
    success = delete_device_link(db, plan_id, link_id)
    if not success:
        raise HTTPException(status_code=404, detail="链路不存在")
    return {"message": "链路删除成功"}


# ============ 设备详情 & 告警 API ============

@router.get("/monitor-screen/device/{device_id}/detail")
async def get_device_info(device_id: int, db: Session = Depends(get_db)):
    """获取设备详情（用于大屏弹窗）"""
    result = get_device_detail(db, device_id)
    if not result:
        raise HTTPException(status_code=404, detail="设备不存在")
    return result


@router.get("/monitor-screen/offline-alerts")
async def get_alerts(db: Session = Depends(get_db)):
    """获取离线设备告警列表"""
    alerts = get_offline_alerts(db)
    return {"items": alerts}


@router.get("/monitor-screen/stats")
async def get_stats(db: Session = Depends(get_db)):
    """获取大屏统计数据"""
    from app.shared.models import Device
    from sqlalchemy import or_

    total_devices = db.query(Device).count()
    online_devices = db.query(Device).filter(Device.status == "online").count()
    offline_devices = db.query(Device).filter(Device.status == "offline").count()
    maintenance_devices = db.query(Device).filter(Device.status == "maintenance").count()

    # 交换机：包括 office_switch、core_switch、server_switch（项目实际枚举值）
    switch_count = db.query(Device).filter(
        Device.device_type.in_(["office_switch", "core_switch", "server_switch"])
    ).count()
    ap_count = db.query(Device).filter(Device.device_type == "ap").count()

    return {
        "total": total_devices,
        "online": online_devices,
        "offline": offline_devices,
        "maintenance": maintenance_devices,
        "switch_count": switch_count,
        "ap_count": ap_count,
    }


@router.get("/monitor-screen/global-summary")
async def get_global_summary_endpoint(db: Session = Depends(get_db)):
    """获取全厂健康度汇总 - 用于大屏顶部健康条

    聚合所有平面图数据，返回全厂整体健康状态。
    """
    return get_global_summary(db)