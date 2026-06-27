"""
数据库迁移：监控事件自动化 / 故障工单闭环字段

给 fault_records 表添加监控来源、去重、复核、建议处理方案、自动指派邮箱等字段。
兼容 SQLite 与 PostgreSQL，使用 SQLAlchemy Inspector 做幂等检查。

执行方式：
    cd <项目根目录> && source .venv/bin/activate && python migrations/add_incident_automation_fields.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from app.shared.database import get_db_manager


FAULT_INCIDENT_COLUMNS = {
    "source_type": ("VARCHAR(30)", "VARCHAR(30)"),
    "source_key": ("VARCHAR(200)", "VARCHAR(200)"),
    "source_event": ("VARCHAR(50)", "VARCHAR(50)"),
    "if_index": ("INTEGER", "INTEGER"),
    "if_name": ("VARCHAR(100)", "VARCHAR(100)"),
    "peer_device_id": ("INTEGER", "INTEGER"),
    "peer_if_name": ("VARCHAR(100)", "VARCHAR(100)"),
    "event_count": ("INTEGER DEFAULT 1", "INTEGER DEFAULT 1"),
    "last_event_at": ("DATETIME", "TIMESTAMP"),
    "recommendation": ("TEXT", "TEXT"),
    "assigned_email": ("VARCHAR(200)", "VARCHAR(200)"),
    "review_required": ("BOOLEAN DEFAULT 1", "BOOLEAN DEFAULT TRUE"),
    "reviewed_at": ("DATETIME", "TIMESTAMP"),
    "reviewed_by": ("VARCHAR(100)", "VARCHAR(100)"),
    "false_positive": ("BOOLEAN DEFAULT 0", "BOOLEAN DEFAULT FALSE"),
}

INDEXES = {
    "ix_fault_records_source_type": "source_type",
    "ix_fault_records_source_key": "source_key",
    "ix_fault_records_source_event": "source_event",
}


def migrate():
    db_manager = get_db_manager()
    engine = db_manager.engine
    dialect = engine.dialect.name
    print(f"数据库方言: {dialect}")

    inspector = inspect(engine)
    if "fault_records" not in inspector.get_table_names():
        print("fault_records 表不存在，跳过")
        return

    existing_cols = {c["name"] for c in inspector.get_columns("fault_records")}

    with engine.begin() as conn:
        for col, (sqlite_type, pg_type) in FAULT_INCIDENT_COLUMNS.items():
            if col in existing_cols:
                print(f"  fault_records.{col} 已存在，跳过")
                continue
            col_type = pg_type if dialect == "postgresql" else sqlite_type
            print(f"  添加列 fault_records.{col} ...")
            conn.execute(text(f"ALTER TABLE fault_records ADD COLUMN {col} {col_type}"))

        for index_name, col in INDEXES.items():
            print(f"  创建索引 {index_name}（如不存在）...")
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS {index_name} ON fault_records ({col})"
            ))

    print("迁移完成")


if __name__ == "__main__":
    migrate()
