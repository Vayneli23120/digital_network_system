"""
数据库迁移：添加备件实例表

备件管理重新设计：
- spare_parts：存储备件型号基础信息（型号、名称、厂商、单价等）
- spare_part_instances：存储每个备件个体的序列号、PO号、状态等

执行方式：
    python migrations/add_spare_part_instances.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.shared.database import get_db_manager
from app.shared.models import Base, SparePart, SparePartInstance, SparePartMovement
from loguru import logger


def migrate():
    """执行迁移"""
    db = get_db_manager()

    logger.info("开始迁移：添加备件实例表...")

    # 检查表是否已存在
    with db.engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='spare_part_instances'"
        ))
        if result.fetchone():
            logger.info("spare_part_instances 表已存在，跳过创建")
            return

    # 创建新表
    SparePartInstance.__table__.create(db.engine, checkfirst=True)
    logger.info("spare_part_instances 表创建成功")

    # 从现有 spare_parts 表迁移数据（如果有序列号的备件）
    with Session(db.engine) as session:
        # 查询所有有序列号的备件（旧结构）
        parts_with_sn = session.execute(text(
            "SELECT id, serial_number, po_number, location, created_at FROM spare_parts WHERE serial_number IS NOT NULL AND serial_number != ''"
        )).fetchall()

        if parts_with_sn:
            logger.info(f"发现 {len(parts_with_sn)} 个有序列号的备件，开始迁移...")

            for part in parts_with_sn:
                # 创建备件实例记录
                session.execute(text(
                    """
                    INSERT INTO spare_part_instances
                    (part_id, serial_number, po_number, status, location, in_stock_at, created_at)
                    VALUES (:part_id, :serial_number, :po_number, 'in_stock', :location, :created_at, :created_at)
                    """
                ), {
                    'part_id': part[0],
                    'serial_number': part[1],
                    'po_number': part[2] or '',
                    'location': part[3] or '',
                    'created_at': part[4]
                })

            session.commit()
            logger.info(f"已迁移 {len(parts_with_sn)} 个备件实例")

    logger.info("迁移完成！")

    # 显示表结构
    with db.engine.connect() as conn:
        result = conn.execute(text(
            "PRAGMA table_info(spare_part_instances)"
        ))
        logger.info("spare_part_instances 表结构：")
        for row in result.fetchall():
            logger.info(f"  {row}")


if __name__ == "__main__":
    migrate()