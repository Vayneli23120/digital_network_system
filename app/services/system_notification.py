"""系统内部通知服务

用于系统内部的通知（导航栏通知图标、通知中心）"""

from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List

from app.shared.models import Notification


class SystemNotificationService:
    """系统内部通知服务"""

    def __init__(self, db: Session):
        self.db = db

    def send_notification(
        self,
        user: str,
        type: str,
        title: str,
        content: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None
    ) -> Notification:
        """发送通知"""
        notification = Notification(
            user=user,
            type=type,
            title=title,
            content=content,
            reference_type=reference_type,
            reference_id=reference_id,
            read=False,
            created_at=datetime.utcnow()
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_user_notifications(
        self,
        user: str,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Notification]:
        """获取用户通知"""
        query = self.db.query(Notification).filter(Notification.user == user)

        if unread_only:
            query = query.filter(Notification.read == False)

        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def get_unread_count(self, user: str) -> int:
        """获取未读通知数量"""
        return self.db.query(Notification).filter(
            Notification.user == user,
            Notification.read == False
        ).count()

    def mark_as_read(self, notification_id: int, user: str) -> bool:
        """标记通知为已读"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user == user
        ).first()

        if notification:
            notification.read = True
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def mark_all_as_read(self, user: str) -> int:
        """标记所有通知为已读"""
        count = self.db.query(Notification).filter(
            Notification.user == user,
            Notification.read == False
        ).update({"read": True, "read_at": datetime.utcnow()})
        self.db.commit()
        return count

    def delete_notification(self, notification_id: int, user: str) -> bool:
        """删除通知"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user == user
        ).first()

        if notification:
            self.db.delete(notification)
            self.db.commit()
            return True
        return False