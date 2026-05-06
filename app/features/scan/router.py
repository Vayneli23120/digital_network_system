"""扫描会话管理 - Scan Session Service

用于建立扫码枪与电脑端操作的关联：
1. 电脑端创建扫码会话，显示会话码（二维码）
2. 扫码枪扫描会话码，建立关联
3. 扫码枪扫描序列号，数据推送到电脑端
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import json

from app.shared.database import get_db
from app.shared.models import SparePart, SparePartInstance

router = APIRouter(prefix="/api/scan", tags=["scan-session"])


# ============ 内存存储（可改为 Redis） ============
# 存储活跃的扫码会话
scan_sessions = {}  # {session_code: {type, created_at, items, status}}


# ============ Pydantic 模型 ============

class ScanSessionCreate(BaseModel):
    """创建扫码会话"""
    session_type: str  # in, out, maintenance, task
    reference: Optional[str] = None  # 关联工单/任务ID
    device_id: Optional[int] = None
    part_id: Optional[int] = None  # 入库时选择的备件ID
    po_number: Optional[str] = None  # 入库时的PO号


class ScanSessionJoin(BaseModel):
    """扫码枪加入会话"""
    session_code: str


class ScanItemAdd(BaseModel):
    """扫码枪添加备件"""
    session_code: str
    serial_number: str
    quantity: int = 1


class ScanItem(BaseModel):
    """扫描的备件项"""
    serial_number: str
    part_id: Optional[int] = None
    part_number: Optional[str] = None
    name: Optional[str] = None
    quantity: int = 1
    unit_price: Optional[float] = None
    scanned_at: datetime


class ScanSession(BaseModel):
    """扫码会话"""
    session_code: str
    session_type: str
    reference: Optional[str] = None
    device_id: Optional[int] = None
    created_at: datetime
    expires_at: datetime
    status: str  # pending, active, completed, expired
    items: List[ScanItem] = []


# ============ API ============

@router.post("/sessions")
async def create_scan_session(
    data: ScanSessionCreate,
    db: Session = Depends(get_db)
):
    """创建扫码会话（电脑端调用）

    返回会话码，用于生成二维码供扫码枪扫描
    """
    # 生成唯一会话码（6位字母数字，方便扫码）
    session_code = uuid.uuid4().hex[:6].upper()

    # 创建会话（有效期30分钟）
    now = datetime.utcnow()
    session = {
        "session_code": session_code,
        "session_type": data.session_type,
        "reference": data.reference,
        "device_id": data.device_id,
        "part_id": data.part_id,  # 入库备件ID
        "po_number": data.po_number,  # PO号
        "created_at": now,
        "expires_at": now + timedelta(minutes=30),
        "status": "pending",
        "items": [],
        "joined": False
    }

    scan_sessions[session_code] = session

    # 查询备件信息（如果有）
    part_info = None
    if data.part_id:
        part = db.query(SparePart).filter(SparePart.id == data.part_id).first()
        if part:
            part_info = {
                "id": part.id,
                "name": part.name,
                "part_number": part.part_number,
                "category": part.category,
                "manufacturer": part.manufacturer,
                "unit_price": float(part.unit_price) if part.unit_price else 0
            }

    return {
        "session_code": session_code,
        "session_type": data.session_type,
        "expires_at": session["expires_at"].isoformat(),
        "qr_content": f"NAS-SCAN:{session_code}",
        "part_info": part_info,
        "po_number": data.po_number,
        "message": "请用扫码枪扫描条形码加入会话"
    }


@router.post("/sessions/join")
async def join_scan_session(
    data: ScanSessionJoin,
    db: Session = Depends(get_db)
):
    """扫码枪加入会话（扫码枪扫描会话码后调用）"""
    session = scan_sessions.get(data.session_code)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    if session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="会话已过期")

    session["joined"] = True
    session["status"] = "active"

    return {
        "session_code": data.session_code,
        "session_type": session["session_type"],
        "status": "active",
        "message": "已加入扫码会话，请扫描备件序列号"
    }


@router.post("/sessions/items")
async def add_scan_item(
    data: ScanItemAdd,
    db: Session = Depends(get_db)
):
    """扫码枪添加备件（扫码枪扫描序列号后调用）"""
    session = scan_sessions.get(data.session_code)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    if session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="会话已过期")

    if not session["joined"]:
        raise HTTPException(status_code=400, detail="请先扫描会话码加入")

    # 查询备件信息
    part = db.query(SparePart).filter(
        SparePart.serial_number == data.serial_number
    ).first()

    # 创建扫描项
    scan_item = {
        "serial_number": data.serial_number,
        "part_id": part.id if part else None,
        "part_number": part.part_number if part else None,
        "name": part.name if part else None,
        "quantity": data.quantity,
        "unit_price": float(part.unit_price) if part and part.unit_price else None,
        "scanned_at": datetime.utcnow()
    }

    # 如果已存在相同序列号，增加数量
    existing = None
    for item in session["items"]:
        if item["serial_number"] == data.serial_number:
            existing = item
            break

    if existing:
        existing["quantity"] += data.quantity
    else:
        session["items"].append(scan_item)

    return {
        "session_code": data.session_code,
        "item": scan_item,
        "total_items": len(session["items"]),
        "found_in_stock": part is not None,
        "message": f"已添加: {part.name if part else data.serial_number}"
    }


@router.delete("/sessions/{session_code}/items/{serial_number}")
async def remove_scan_item(session_code: str, serial_number: str):
    """移除扫描项（扫码枪或PC端调用）"""
    session = scan_sessions.get(session_code)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    if session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="会话已过期")

    # 找到并移除该项
    for i, item in enumerate(session["items"]):
        if item["serial_number"] == serial_number:
            session["items"].pop(i)
            return {
                "session_code": session_code,
                "removed_serial": serial_number,
                "total_items": len(session["items"]),
                "message": f"已移除: {serial_number}"
            }

    raise HTTPException(status_code=404, detail="未找到该序列号")


@router.get("/sessions/{session_code}")
async def get_scan_session(
    session_code: str,
    db: Session = Depends(get_db)
):
    """获取扫码会话状态（电脑端轮询获取扫描结果）"""
    session = scan_sessions.get(session_code)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    if session["expires_at"] < datetime.utcnow():
        session["status"] = "expired"
        raise HTTPException(status_code=400, detail="会话已过期")

    return {
        "session_code": session_code,
        "session_type": session["session_type"],
        "reference": session["reference"],
        "device_id": session["device_id"],
        "part_id": session.get("part_id"),  # 入库备件ID
        "po_number": session.get("po_number"),  # PO号
        "status": session["status"],
        "joined": session["joined"],
        "items": session["items"],
        "total_items": len(session["items"]),
        "expires_at": session["expires_at"].isoformat()
    }


@router.post("/sessions/{session_code}/complete")
async def complete_scan_session(
    session_code: str,
    db: Session = Depends(get_db)
):
    """完成扫码会话（电脑端确认提交后调用）

    入库时：创建备件实例记录，更新库存
    出库时：更新备件实例状态为out
    """
    session = scan_sessions.get(session_code)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="会话已过期")

    session["status"] = "completed"

    # 处理入库：创建备件实例记录
    if session["session_type"] == "in" and session.get("part_id"):
        part_id = session["part_id"]
        po_number = session.get("po_number", "")
        part = db.query(SparePart).filter(SparePart.id == part_id).first()

        if not part:
            raise HTTPException(status_code=404, detail="备件不存在")

        # 为每个扫描的序列号创建备件实例
        for item in session["items"]:
            serial_number = item["serial_number"]

            # 检查序列号是否已存在
            existing = db.query(SparePartInstance).filter(
                SparePartInstance.serial_number == serial_number
            ).first()

            if existing:
                # 如果已存在但状态不是in_stock，更新状态
                if existing.status != "in_stock":
                    existing.status = "in_stock"
                    existing.in_stock_at = datetime.utcnow()
                    existing.out_at = None
                    existing.po_number = po_number
            else:
                # 创建新的备件实例
                instance = SparePartInstance(
                    part_id=part_id,
                    serial_number=serial_number,
                    po_number=po_number,
                    status="in_stock",
                    location=part.location,
                    in_stock_at=datetime.utcnow()
                )
                db.add(instance)

        # 更新备件库存数量
        part.quantity_in_stock += len(session["items"])
        db.commit()

        # 删除会话
        if session_code in scan_sessions:
            del scan_sessions[session_code]

        return {
            "session_code": session_code,
            "status": "completed",
            "items": session["items"],
            "part_id": part_id,
            "added_count": len(session["items"]),
            "new_stock": part.quantity_in_stock,
            "message": f"入库成功，新增 {len(session['items'])} 件，库存: {part.quantity_in_stock}"
        }

    # 出库处理（暂不实现复杂逻辑）
    if session["session_type"] == "out":
        # TODO: 更新备件实例状态为out
        pass

    # 删除会话
    if session_code in scan_sessions:
        del scan_sessions[session_code]

    return {
        "session_code": session_code,
        "status": "completed",
        "items": session["items"],
        "message": "扫码会话已完成"
    }


@router.delete("/sessions/{session_code}")
async def delete_scan_session(session_code: str):
    """删除/取消扫码会话"""
    if session_code in scan_sessions:
        del scan_sessions[session_code]
        return {"message": "会话已删除"}
    raise HTTPException(status_code=404, detail="会话不存在")


@router.get("/sessions/active")
async def list_active_sessions():
    """列出所有活跃会话（调试用）"""
    now = datetime.utcnow()
    active = []
    for code, session in scan_sessions.items():
        if session["expires_at"] > now and session["status"] not in ["completed", "expired"]:
            active.append({
                "session_code": code,
                "type": session["session_type"],
                "status": session["status"],
                "items_count": len(session["items"])
            })
    return {"active_sessions": active, "total": len(active)}