"""
数据库迁移：添加序列号和PO号字段到备件表

执行方式：cd /home/vayne/network-automation-system && source .venv/bin/activate && python migrations/add_spare_part_fields.py
"""

import sqlite3
import os

DB_PATH = "data/nas.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查列是否已存在
    cursor.execute("PRAGMA table_info(spare_parts)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'serial_number' not in columns:
        print("添加 serial_number 列...")
        cursor.execute("ALTER TABLE spare_parts ADD COLUMN serial_number VARCHAR(100)")
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spare_parts_serial_number ON spare_parts(serial_number)")
        print("✓ serial_number 列已添加")
    else:
        print("serial_number 列已存在，跳过")

    if 'po_number' not in columns:
        print("添加 po_number 列...")
        cursor.execute("ALTER TABLE spare_parts ADD COLUMN po_number VARCHAR(100)")
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_spare_parts_po_number ON spare_parts(po_number)")
        print("✓ po_number 列已添加")
    else:
        print("po_number 列已存在，跳过")

    conn.commit()
    conn.close()
    print("迁移完成")

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在：{DB_PATH}")
        exit(1)
    migrate()