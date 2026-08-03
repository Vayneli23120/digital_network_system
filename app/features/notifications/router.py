"""系统通知路由"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.shared.database import get_db
from app.shared.models import Notification
from app.shared.time_utils import utc_iso
from app.features.auth.identity import Principal, get_current_principal
from app.services.system_notification import SystemNotificationService
from app.shared.dependencies import require_permission

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

require_notification_read = require_permission("notification:read")
require_notification_write = require_permission("notification:write")


@router.get("")
async def get_notifications(
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_notification_read),
    unread_only: bool = False,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """获取用户通知列表 - 内部系统返回所有通知"""
    user = principal.username
    service = SystemNotificationService(db)
    notifications = service.get_user_notifications(user, unread_only, limit)

    items = []
    for n in notifications:
        created_at_iso = utc_iso(n.created_at)
        read_at_iso = utc_iso(n.read_at)

        items.append({
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "content": n.content,
            "reference_type": n.reference_type,
            "reference_id": n.reference_id,
            "read": n.read,
            "read_at": read_at_iso,
            "created_at": created_at_iso
        })

    total = service.get_user_notifications_total(user, unread_only)
    unread_count = service.get_unread_count(user)

    return {
        "total": total,
        "unread_count": unread_count,
        "items": items
    }


@router.get("/unread-count")
async def get_unread_count(
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_notification_read),
    db: Session = Depends(get_db)
):
    """获取未读通知数量"""
    user = principal.username
    service = SystemNotificationService(db)
    count = service.get_unread_count(user)
    return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_notification_write),
    db: Session = Depends(get_db)
):
    """标记通知为已读"""
    user = principal.username
    service = SystemNotificationService(db)
    success = service.mark_as_read(notification_id, user)

    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")

    return {"message": "已标记为已读"}


@router.post("/read-all")
async def mark_all_as_read(
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_notification_write),
    db: Session = Depends(get_db)
):
    """标记所有通知为已读"""
    user = principal.username
    service = SystemNotificationService(db)
    count = service.mark_all_as_read(user)
    return {"message": f"已标记 {count} 条通知为已读"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    principal: Principal = Depends(get_current_principal),
    _: None = Depends(require_notification_write),
    db: Session = Depends(get_db)
):
    """删除通知"""
    user = principal.username
    service = SystemNotificationService(db)
    success = service.delete_notification(notification_id, user)

    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")

    return {"message": "通知已删除"}