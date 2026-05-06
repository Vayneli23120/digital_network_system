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
from app.shared.models import SparePart, SparePartInstance, SparePartMovement

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
    location: Optional[str] = None  # 存放位置


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


class ScanItemUpdate(BaseModel):
    """更新扫描项"""
    unit_price: Optional[float] = None


class ScanComplete(BaseModel):
    """完成扫码会话"""
    items: Optional[List[dict]] = None  # 可选传入包含单价等信息的 items
    reason: Optional[str] = None  # 入库/出库原因


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
        "location": data.location,  # 存放位置
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
    """扫码枪添加备件（扫码枪扫描序列号后调用）

    入库模式：session中已有part_id，直接记录序列号
    出库模式：查询已有备件实例匹配序列号
    """
    session = scan_sessions.get(data.session_code)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    if session["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="会话已过期")

    if not session["joined"]:
        raise HTTPException(status_code=400, detail="请先扫描会话码加入")

    # 入库模式：从session获取备件信息
    if session["session_type"] == "in" and session.get("part_id"):
        part = db.query(SparePart).filter(SparePart.id == session["part_id"]).first()
        if not part:
            raise HTTPException(status_code=404, detail="备件不存在")

        # 检查序列号是否已存在（防止重复入库）
        existing_instance = db.query(SparePartInstance).filter(
            SparePartInstance.serial_number == data.serial_number
        ).first()

        scan_item = {
            "serial_number": data.serial_number,
            "part_id": part.id,
            "part_number": part.part_number,
            "name": part.name,
            "quantity": 1,  # 每个序列号对应一个备件，数量固定为1
            "unit_price": float(part.unit_price) if part.unit_price else None,
            "po_number": session.get("po_number"),
            "scanned_at": datetime.utcnow()
        }

        # 检查session中是否已有该序列号（防止重复扫描）
        existing = None
        for item in session["items"]:
            if item["serial_number"] == data.serial_number:
                existing = item
                break

        if existing:
            # 已存在则提示重复，不重复添加
            return {
                "session_code": data.session_code,
                "item": existing,
                "total_items": len(session["items"]),
                "found_in_stock": existing_instance is not None and existing_instance.status == "in_stock",
                "is_duplicate": True,
                "is_session_duplicate": True,  # 会话中已存在
                "message": f"序列号 {data.serial_number} 已在本次扫描列表中"
            }
        else:
            session["items"].append(scan_item)

        return {
            "session_code": data.session_code,
            "item": scan_item,
            "total_items": len(session["items"]),
            "found_in_stock": existing_instance is not None and existing_instance.status == "in_stock",
            "is_duplicate": existing_instance is not None,
            "is_session_duplicate": False,
            "message": f"已添加: {part.name}" if not existing_instance else f"序列号已存在库存中（状态: {existing_instance.status})"
        }

    # 出库模式：查询已有备件实例
    instance = db.query(SparePartInstance).filter(
        SparePartInstance.serial_number == data.serial_number,
        SparePartInstance.status == "in_stock"
    ).first()

    part = None
    if instance:
        part = db.query(SparePart).filter(SparePart.id == instance.part_id).first()

    scan_item = {
        "serial_number": data.serial_number,
        "part_id": instance.part_id if instance else None,
        "instance_id": instance.id if instance else None,
        "part_number": part.part_number if part else None,
        "name": part.name if part else None,
        "quantity": data.quantity,
        "unit_price": float(part.unit_price) if part and part.unit_price else None,
        "scanned_at": datetime.utcnow()
    }

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
        "found_in_stock": instance is not None,
        "message": f"已添加: {part.name if part else data.serial_number}" if instance else f"序列号 {data.serial_number} 未找到或在库中不存在"
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
    data: Optional[ScanComplete] = None,
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

    # 如果前端传入了 items 数据（包含单价和备注），更新 session 中的 items
    if data and data.items:
        # 更新单价和备注信息
        for incoming_item in data.items:
            for session_item in session["items"]:
                if session_item["serial_number"] == incoming_item.get("serial_number"):
                    if incoming_item.get("unit_price"):
                        session_item["unit_price"] = incoming_item["unit_price"]
                    if incoming_item.get("notes"):
                        session_item["notes"] = incoming_item["notes"]
                    break

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
            unit_price = item.get("unit_price", 0)  # 获取单价
            notes = item.get("notes", "")  # 获取备注

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
                    existing.unit_price = unit_price
                    existing.notes = notes  # 更新备注
            else:
                # 创建新的备件实例
                instance = SparePartInstance(
                    part_id=part_id,
                    serial_number=serial_number,
                    po_number=po_number,
                    unit_price=unit_price,
                    status="in_stock",
                    location=session.get("location") or part.location,  # 优先使用用户输入的位置
                    notes=notes,  # 保存备注
                    in_stock_at=datetime.utcnow()
                )
                db.add(instance)

        # 先提交事务，让新实例写入数据库
        db.commit()

        # 然后基于实际实例数量同步库存
        actual_count = db.query(SparePartInstance).filter(
            SparePartInstance.part_id == part_id,
            SparePartInstance.status == "in_stock"
        ).count()
        part.quantity_in_stock = actual_count
        db.commit()

        # 创建出入库历史记录
        movement = SparePartMovement(
            part_id=part_id,
            movement_type="in",
            quantity=len(session["items"]),
            reason=data.reason if data else "",  # 入库原因
            operator="",  # 操作人可以从session获取
            reference=po_number,  # 使用PO号作为参考
            created_at=datetime.utcnow()
        )
        db.add(movement)
        db.commit()

        # 不删除会话，保留让扫码枪端能获取completed状态
        # 扫码枪端轮询检测到completed后会自动退出

        return {
            "session_code": session_code,
            "status": "completed",
            "items": session["items"],
            "part_id": part_id,
            "added_count": len(session["items"]),
            "new_stock": part.quantity_in_stock,
            "message": f"入库成功，新增 {len(session['items'])} 件，库存: {part.quantity_in_stock}"
        }

    # 出库处理：更新备件实例状态
    if session["session_type"] == "out":
        out_count = 0
        for item in session["items"]:
            serial_number = item["serial_number"]
            instance = db.query(SparePartInstance).filter(
                SparePartInstance.serial_number == serial_number,
                SparePartInstance.status == "in_stock"
            ).first()

            if instance:
                instance.status = "out"
                instance.out_at = datetime.utcnow()
                # 更新备注
                notes = item.get("notes", "")
                out_note = f"扫码出库"
                if data and data.reason:
                    out_note += f", 原因: {data.reason}"
                if notes:
                    out_note += f", 备注: {notes}"
                if instance.notes:
                    instance.notes = instance.notes + "\n" + out_note
                else:
                    instance.notes = out_note
                out_count += 1

                # 更新该备件的库存数量
                part = db.query(SparePart).filter(SparePart.id == instance.part_id).first()
                if part:
                    db.flush()  # 先让状态更新生效
                    actual_count = db.query(SparePartInstance).filter(
                        SparePartInstance.part_id == instance.part_id,
                        SparePartInstance.status == "in_stock"
                    ).count()
                    part.quantity_in_stock = actual_count

        db.commit()

        # 创建出入库历史记录（每个序列号单独记录）
        if out_count > 0:
            for item in session["items"]:
                if item.get("part_id"):
                    movement = SparePartMovement(
                        part_id=item["part_id"],
                        movement_type="out",
                        quantity=1,
                        serial_number=item.get("serial_number"),
                        reason=data.reason if data else "扫码出库",
                        operator="",
                        reference="",
                        created_at=datetime.utcnow()
                    )
                    db.add(movement)
            db.commit()

        # 不删除会话，保留让扫码枪端能获取completed状态
        return {
            "session_code": session_code,
            "status": "completed",
            "items": session["items"],
            "out_count": out_count,
            "message": f"出库成功，共 {out_count} 件"
        }

    # 删除会话（其他类型）
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