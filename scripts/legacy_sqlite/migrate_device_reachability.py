"""
数据库迁移脚本 - 添加设备可达性字段

运行方式：python3 scripts/migrate_device_reachability.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import sqlite3

# 数据库路径
DB_PATH = Path(__file__).parent.parent / "data" / "nas.db"

def migrate():
    """添加设备可达性相关字段"""

    print(f"数据库路径: {DB_PATH}")

    if not DB_PATH.exists():
        print("数据库文件不存在，将由 SQLAlchemy 自动创建")
        return

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 检查现有列
    cursor.execute("PRAGMA table_info(devices)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    print(f"现有列: {existing_columns}")

    # 需要添加的新列
    new_columns = [
        ("deployment_status", "VARCHAR(50) DEFAULT 'un-used'"),
        ("reachability", "VARCHAR(50) DEFAULT 'unknown'"),
        ("last_reachability_check", "DATETIME"),
        ("reachability_latency_ms", "INTEGER"),
        ("reachability_method", "VARCHAR(20)"),
    ]

    # 添加缺失的列
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE devices ADD COLUMN {col_name} {col_type}"
                cursor.execute(sql)
                print(f"添加列: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"添加列 {col_name} 失败: {e}")

    # 更新现有数据：将旧的 status 字段映射到 deployment_status
    cursor.execute("SELECT id, status FROM devices WHERE deployment_status IS NULL OR deployment_status = 'online'")
    devices_to_update = cursor.fetchall()

    status_map = {
        'online': 'in-use',
        'offline': 'un-used',
        'maintenance': 'maintenance',
        'retired': 'retired'
    }

    for device_id, old_status in devices_to_update:
        new_deployment = status_map.get(old_status, 'un-used')
        cursor.execute(
            "UPDATE devices SET deployment_status = ?, reachability = ? WHERE id = ?",
            (new_deployment, 'unknown', device_id)
        )
        print(f"更新设备 {device_id}: status={old_status} -> deployment_status={new_deployment}")

    # 创建索引
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_deployment_status ON devices(deployment_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_devices_reachability ON devices(reachability)")
        print("创建索引成功")
    except sqlite3.OperationalError as e:
        print(f"创建索引失败: {e}")

    conn.commit()
    conn.close()

    print("迁移完成!")


if __name__ == "__main__":
    migrate()