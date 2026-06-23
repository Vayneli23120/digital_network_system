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


# ============ 预接式光纤主干+分支 Pydantic 模型 ============

class FiberTrunkCreate(BaseModel):
    name: Optional[str] = None
    start_x_percent: float
    start_y_percent: float
    start_device_id: Optional[int] = None
    end_x_percent: float
    end_y_percent: float
    waypoints: Optional[str] = None  # JSON string


class FiberTrunkUpdate(BaseModel):
    name: Optional[str] = None
    waypoints: Optional[str] = None  # JSON string
    start_x_percent: Optional[float] = None  # 起点X坐标百分比
    start_y_percent: Optional[float] = None  # 起点Y坐标百分比
    start_device_id: Optional[int] = None  # 起点关联设备ID（核心交换机）
    end_x_percent: Optional[float] = None  # 终点X坐标百分比
    end_y_percent: Optional[float] = None  # 终点Y坐标百分比


class FiberBranchPointCreate(BaseModel):
    trunk_link_id: int
    name: Optional[str] = None
    position_percent: float  # 0-100
    x_percent: Optional[float] = None  # 用户微调坐标
    y_percent: Optional[float] = None


class FiberBranchPointUpdate(BaseModel):
    name: Optional[str] = None
    position_percent: Optional[float] = None
    x_percent: Optional[float] = None
    y_percent: Optional[float] = None


class FiberBranchLinkCreate(BaseModel):
    branch_point_id: int
    to_device_id: int
    logical_uplink_device_id: Optional[int] = None  # 逻辑上联设备


class FiberBranchLinkUpdate(BaseModel):
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

    # 生成安全的文件名
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    original_ext = Path(image.filename).suffix if image.filename else ".jpg"

    # 读取图片数据
    image_data = await image.read()

    # 处理图片
    if original_ext.lower() == '.svg':
        # SVG 矢量图直接保存
        filename = f"{timestamp}.svg"
        file_path = upload_dir / filename
        with open(file_path, "wb") as buffer:
            buffer.write(image_data)
    else:
        # 尝试使用 Pillow 处理
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            original_width, original_height = img.size

            # 保存原图（用于超高清需求）
            original_path = upload_dir / f"{timestamp}_original{original_ext}"

            # 生成预览版本：控制在 4096px
            preview_max = 4096
            if max(original_width, original_height) > preview_max:
                ratio = preview_max / max(original_width, original_height)
                preview_size = (int(original_width * ratio), int(original_height * ratio))
                preview_img = img.resize(preview_size, Image.LANCZOS)
            else:
                preview_img = img

            # 保存预览版本
            preview_path = upload_dir / f"{timestamp}{original_ext}"

            if original_ext.lower() in ['.jpg', '.jpeg']:
                preview_img.save(preview_path, 'JPEG', quality=95, optimize=True)
                img.save(original_path, 'JPEG', quality=95)
            elif original_ext.lower() == '.png':
                preview_img.save(preview_path, 'PNG', optimize=True)
                img.save(original_path, 'PNG', optimize=True)
            else:
                preview_img.save(preview_path, quality=95)
                img.save(original_path, quality=95)

            file_path = preview_path

        except ImportError:
            # Pillow 未安装，直接保存原图
            filename = f"{timestamp}{original_ext}"
            file_path = upload_dir / filename
            with open(file_path, "wb") as buffer:
                buffer.write(image_data)
        except Exception as e:
            # 处理失败，保存原图
            filename = f"{timestamp}{original_ext}"
            file_path = upload_dir / filename
            with open(file_path, "wb") as buffer:
                buffer.write(image_data)

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
        original_ext = Path(image.filename).suffix if image.filename else ".jpg"

        image_data = await image.read()

        if original_ext.lower() == '.svg':
            filename = f"{timestamp}.svg"
            file_path = upload_dir / filename
            with open(file_path, "wb") as buffer:
                buffer.write(image_data)
        else:
            try:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(image_data))
                original_width, original_height = img.size

                original_path = upload_dir / f"{timestamp}_original{original_ext}"

                preview_max = 4096
                if max(original_width, original_height) > preview_max:
                    ratio = preview_max / max(original_width, original_height)
                    preview_size = (int(original_width * ratio), int(original_height * ratio))
                    preview_img = img.resize(preview_size, Image.LANCZOS)
                else:
                    preview_img = img

                preview_path = upload_dir / f"{timestamp}{original_ext}"

                if original_ext.lower() in ['.jpg', '.jpeg']:
                    preview_img.save(preview_path, 'JPEG', quality=95, optimize=True)
                    img.save(original_path, 'JPEG', quality=95)
                elif original_ext.lower() == '.png':
                    preview_img.save(preview_path, 'PNG', optimize=True)
                    img.save(original_path, 'PNG', optimize=True)
                else:
                    preview_img.save(preview_path, quality=95)
                    img.save(original_path, quality=95)

                file_path = preview_path
            except ImportError:
                filename = f"{timestamp}{original_ext}"
                file_path = upload_dir / filename
                with open(file_path, "wb") as buffer:
                    buffer.write(image_data)
            except Exception:
                filename = f"{timestamp}{original_ext}"
                file_path = upload_dir / filename
                with open(file_path, "wb") as buffer:
                    buffer.write(image_data)

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


# ============ 预接式光纤主干+分支 API ============

from .fiber_service import (
    list_fiber_trunks, create_fiber_trunk, update_fiber_trunk, delete_fiber_trunk,
    list_branch_points, create_branch_point, update_branch_point, delete_branch_point,
    create_branch_link, update_branch_link, delete_branch_link,
)


@router.get("/floor-plans/{plan_id}/fiber-trunks")
async def get_fiber_trunks(plan_id: int, db: Session = Depends(get_db)):
    """获取主干光缆列表"""
    return {"items": list_fiber_trunks(db, plan_id)}


@router.post("/floor-plans/{plan_id}/fiber-trunks")
async def add_fiber_trunk(plan_id: int, data: FiberTrunkCreate, db: Session = Depends(get_db)):
    """创建主干光缆"""
    result = create_fiber_trunk(db, plan_id, data)
    return result


@router.put("/floor-plans/{plan_id}/fiber-trunks/{trunk_id}")
async def modify_fiber_trunk(plan_id: int, trunk_id: int, data: FiberTrunkUpdate, db: Session = Depends(get_db)):
    """更新主干光缆"""
    result = update_fiber_trunk(db, plan_id, trunk_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="主干光缆不存在")
    return result


@router.delete("/floor-plans/{plan_id}/fiber-trunks/{trunk_id}")
async def remove_fiber_trunk(plan_id: int, trunk_id: int, db: Session = Depends(get_db)):
    """删除主干光缆（连带删除分支点和分支光缆）"""
    success = delete_fiber_trunk(db, plan_id, trunk_id)
    if not success:
        raise HTTPException(status_code=404, detail="主干光缆不存在")
    return {"message": "主干光缆删除成功"}


@router.get("/floor-plans/{plan_id}/fiber-branch-points")
async def get_branch_points(plan_id: int, db: Session = Depends(get_db)):
    """获取分支点列表"""
    return {"items": list_branch_points(db, plan_id)}


@router.post("/floor-plans/{plan_id}/fiber-branch-points")
async def add_branch_point(plan_id: int, data: FiberBranchPointCreate, db: Session = Depends(get_db)):
    """在主干上创建分支点"""
    result = create_branch_point(db, plan_id, data)
    return result


@router.put("/floor-plans/{plan_id}/fiber-branch-points/{bp_id}")
async def modify_branch_point(plan_id: int, bp_id: int, data: FiberBranchPointUpdate, db: Session = Depends(get_db)):
    """更新分支点"""
    result = update_branch_point(db, plan_id, bp_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="分支点不存在")
    return result


@router.delete("/floor-plans/{plan_id}/fiber-branch-points/{bp_id}")
async def remove_branch_point(plan_id: int, bp_id: int, db: Session = Depends(get_db)):
    """删除分支点（连带删除分支光缆）"""
    success = delete_branch_point(db, plan_id, bp_id)
    if not success:
        raise HTTPException(status_code=404, detail="分支点不存在")
    return {"message": "分支点删除成功"}


@router.post("/floor-plans/{plan_id}/fiber-branch-links")
async def add_branch_link(plan_id: int, data: FiberBranchLinkCreate, db: Session = Depends(get_db)):
    """创建分支光缆（从分支点到设备）"""
    result = create_branch_link(db, plan_id, data)
    return result


@router.put("/floor-plans/{plan_id}/fiber-branch-links/{link_id}")
async def modify_branch_link(plan_id: int, link_id: int, data: FiberBranchLinkUpdate, db: Session = Depends(get_db)):
    """更新分支光缆拐点"""
    result = update_branch_link(db, plan_id, link_id, data.waypoints)
    if not result:
        raise HTTPException(status_code=404, detail="分支光缆不存在")
    return result


@router.delete("/floor-plans/{plan_id}/fiber-branch-links/{link_id}")
async def remove_branch_link(plan_id: int, link_id: int, db: Session = Depends(get_db)):
    """删除分支光缆"""
    success = delete_branch_link(db, plan_id, link_id)
    if not success:
        raise HTTPException(status_code=404, detail="分支光缆不存在")
    return {"message": "分支光缆删除成功"}


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