"""
数据库迁移：SNMP 接口监控

1. 给 devices 表添加 SNMP 采集配置列（snmp_enabled / snmp_version / snmp_community / snmp_port）
2. 创建 device_interfaces 表（接口状态/上行口标记/最近流量）
3. 创建 interface_traffic_samples 表（流量时序样本）

兼容 SQLite 与 PostgreSQL：使用应用配置的引擎 + SQLAlchemy Inspector 做幂等检查，
新表通过 Base.metadata.create_all 仅创建缺失表。

执行方式：
    cd <项目根目录> && source .venv/bin/activate && python migrations/add_snmp_interface_monitoring.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text
from app.shared.database import get_db_manager
from app.shared.models import Base, DeviceInterface, InterfaceTrafficSample  # noqa: F401


# devices 表要新增的列：列名 -> (sqlite 类型, postgres 类型, 默认值SQL)
DEVICE_SNMP_COLUMNS = {
    "snmp_enabled": ("BOOLEAN", "BOOLEAN", "0", "FALSE"),
    "snmp_version": ("VARCHAR(10)", "VARCHAR(10)", "'2c'", "'2c'"),
    "snmp_community": ("VARCHAR(200)", "VARCHAR(200)", None, None),
    "snmp_port": ("INTEGER", "INTEGER", "161", "161"),
}


def migrate():
    db_manager = get_db_manager()
    engine = db_manager.engine
    dialect = engine.dialect.name  # 'sqlite' / 'postgresql'
    print(f"数据库方言: {dialect}")

    inspector = inspect(engine)
    existing_cols = {c["name"] for c in inspector.get_columns("devices")}

    with engine.begin() as conn:
        for col, (sqlite_type, pg_type, sqlite_default, pg_default) in DEVICE_SNMP_COLUMNS.items():
            if col in existing_cols:
                print(f"  devices.{col} 已存在，跳过")
                continue
            if dialect == "postgresql":
                col_type = pg_type
                default = pg_default
            else:
                col_type = sqlite_type
                default = sqlite_default
            ddl = f"ALTER TABLE devices ADD COLUMN {col} {col_type}"
            if default is not None:
                ddl += f" DEFAULT {default}"
            print(f"  添加列 devices.{col} ...")
            conn.execute(text(ddl))

    # 创建新表（仅创建缺失的表，幂等）
    print("创建/校验 SNMP 接口监控表 ...")
    Base.metadata.create_all(
        bind=engine,
        tables=[DeviceInterface.__table__, InterfaceTrafficSample.__table__],
    )

    print("迁移完成")


if __name__ == "__main__":
    migrate()
