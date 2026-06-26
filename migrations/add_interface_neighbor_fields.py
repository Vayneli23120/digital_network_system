"""
数据库迁移：接口邻居发现（CDP/LLDP）字段

给 device_interfaces 表添加对端关联列：
    peer_device_id / peer_device_name / peer_ip / peer_if_name
    neighbor_source / neighbor_updated_at

兼容 SQLite 与 PostgreSQL：使用应用配置的引擎 + SQLAlchemy Inspector 做幂等检查。

执行方式：
    cd <项目根目录> && source .venv/bin/activate && python migrations/add_interface_neighbor_fields.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from app.shared.database import get_db_manager


# device_interfaces 新增列：列名 -> (sqlite 类型, postgres 类型)
IFACE_NEIGHBOR_COLUMNS = {
    "peer_device_id": ("INTEGER", "INTEGER"),
    "peer_device_name": ("VARCHAR(200)", "VARCHAR(200)"),
    "peer_ip": ("VARCHAR(64)", "VARCHAR(64)"),
    "peer_if_name": ("VARCHAR(100)", "VARCHAR(100)"),
    "neighbor_source": ("VARCHAR(20)", "VARCHAR(20)"),
    "neighbor_updated_at": ("DATETIME", "TIMESTAMP"),
}


def migrate():
    db_manager = get_db_manager()
    engine = db_manager.engine
    dialect = engine.dialect.name  # 'sqlite' / 'postgresql'
    print(f"数据库方言: {dialect}")

    inspector = inspect(engine)
    if "device_interfaces" not in inspector.get_table_names():
        print("device_interfaces 表不存在，请先运行 add_snmp_interface_monitoring.py")
        return

    existing_cols = {c["name"] for c in inspector.get_columns("device_interfaces")}

    with engine.begin() as conn:
        for col, (sqlite_type, pg_type) in IFACE_NEIGHBOR_COLUMNS.items():
            if col in existing_cols:
                print(f"  device_interfaces.{col} 已存在，跳过")
                continue
            col_type = pg_type if dialect == "postgresql" else sqlite_type
            ddl = f"ALTER TABLE device_interfaces ADD COLUMN {col} {col_type}"
            print(f"  添加列 device_interfaces.{col} ...")
            conn.execute(text(ddl))

        # peer_device_id 建索引（幂等）
        if dialect == "postgresql":
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_device_interfaces_peer_device_id "
                "ON device_interfaces (peer_device_id)"
            ))
        else:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_device_interfaces_peer_device_id "
                "ON device_interfaces (peer_device_id)"
            ))

    print("迁移完成")


if __name__ == "__main__":
    migrate()
