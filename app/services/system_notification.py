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
        """获取用户通知

        严格按当前登录账号过滤：每个账号只接收发给自己的通知
        （大小写不敏感；admin 同样只收自己的，不再全量可见）。
        """
        query = self.db.query(Notification)

        # 大小写不敏感匹配
        query = query.filter(Notification.user.ilike(user))

        if unread_only:
            query = query.filter(Notification.read == False)

        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def get_user_notifications_total(self, user: str, unread_only: bool = False) -> int:
        """获取用户通知总数（不受 limit 截断，用于返回真实 total）"""
        query = self.db.query(Notification)

        query = query.filter(Notification.user.ilike(user))

        if unread_only:
            query = query.filter(Notification.read == False)

        return query.count()

    def get_unread_count(self, user: str) -> int:
        """获取未读通知数量

        严格按当前登录账号统计：只数发给自己的未读通知（大小写不敏感）。
        """
        query = self.db.query(Notification).filter(Notification.read == False)

        query = query.filter(Notification.user.ilike(user))

        return query.count()

    def get_broadcast_notifications(
        self,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Notification]:
        """获取广播通知（所有用户都能看到的）"""
        query = self.db.query(Notification).filter(
            Notification.user.in_(['all', 'Admin', 'admin', 'broadcast', 'default', '*'])
        )

        if unread_only:
            query = query.filter(Notification.read == False)

        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def get_broadcast_unread_count(self) -> int:
        """获取广播通知未读数量"""
        return self.db.query(Notification).filter(
            Notification.user.in_(['all', 'Admin', 'admin', 'broadcast', 'default', '*']),
            Notification.read == False
        ).count()

    def mark_as_read(self, notification_id: int, user: str) -> bool:
        """标记通知为已读（只能标记发给自己的通知）"""
        query = self.db.query(Notification).filter(Notification.id == notification_id)
        query = query.filter(Notification.user.ilike(user))
        notification = query.first()

        if notification:
            notification.read = True
            notification.read_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def mark_all_as_read(self, user: str) -> int:
        """标记所有通知为已读（只作用于发给自己的通知）"""
        query = self.db.query(Notification).filter(Notification.read == False)
        query = query.filter(Notification.user.ilike(user))
        count = query.update({"read": True, "read_at": datetime.utcnow()})
        self.db.commit()
        return count

    def delete_notification(self, notification_id: int, user: str) -> bool:
        """删除通知（只能删除发给自己的通知）"""
        query = self.db.query(Notification).filter(Notification.id == notification_id)
        query = query.filter(Notification.user.ilike(user))
        notification = query.first()

        if notification:
            self.db.delete(notification)
            self.db.commit()
            return True
        return False