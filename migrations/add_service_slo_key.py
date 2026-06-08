"""
Migration: Add service_key field to ServiceSlo for i18n support
Run from: cd /home/vayne/network-automation-system && python3 migrations/add_service_slo_key.py

This migration adds a language-independent service_key field that can be used
for frontend i18n mapping, separating data storage from display translation.
"""
import sqlite3

DB_PATH = 'data/nas.db'

# 服务名称到 key 的映射
SERVICE_KEY_MAP = {
    '核心网络可达性': 'core_network',
    'Core Network Availability': 'core_network',
    '数据中心网络': 'datacenter_network',
    'Datacenter Network': 'datacenter_network',
    '园区接入网络': 'campus_access',
    'Campus Access Network': 'campus_access',
    'WiFi 无线网络': 'wifi_network',
    'WiFi Network': 'wifi_network',
}

def run_migration():
    """Add service_key field and migrate existing data"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='service_slo'")
    if not cursor.fetchone():
        print("service_slo table not found, skipping migration")
        conn.close()
        return

    # 检查 service_key 列是否已存在
    cursor.execute("PRAGMA table_info(service_slo)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'service_key' in columns:
        print("service_key column already exists, skipping migration")
        conn.close()
        return

    # 获取现有数据
    cursor.execute("SELECT id, service_name, slo_target, device_types, window_days, description, is_active, created_at, updated_at FROM service_slo")
    existing_rows = cursor.fetchall()
    print(f"Found {len(existing_rows)} existing records")

    # 创建新表结构
    cursor.execute("""
        CREATE TABLE service_slo_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_key VARCHAR(50) NOT NULL UNIQUE,
            service_name VARCHAR(100) NOT NULL,
            slo_target DECIMAL(7,4) NOT NULL,
            device_types VARCHAR(200),
            window_days INTEGER DEFAULT 30,
            description VARCHAR(200),
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    print("New table structure created with service_key")

    # 迁移数据：根据 service_name 映射到 service_key
    migrated_count = 0
    for row in existing_rows:
        row_id = row[0]
        service_name = row[1]
        slo_target = row[2]
        device_types = row[3] if len(row) > 3 else None
        window_days = row[4] if len(row) > 4 else 30
        description = row[5] if len(row) > 5 else None
        is_active = row[6] if len(row) > 6 else 1
        created_at = row[7] if len(row) > 7 else None
        updated_at = row[8] if len(row) > 8 else None

        # 映射 service_key
        service_key = SERVICE_KEY_MAP.get(service_name, service_name.lower().replace(' ', '_').replace('网络', 'network').replace('可达性', ''))
        if service_key in ['核心', 'core']:
            service_key = 'core_network'
        elif service_key in ['数据中心', 'datacenter']:
            service_key = 'datacenter_network'
        elif service_key in ['园区接入', 'campusaccess']:
            service_key = 'campus_access'
        elif service_key in ['wifi', '无线']:
            service_key = 'wifi_network'

        cursor.execute("""
            INSERT INTO service_slo_new (id, service_key, service_name, slo_target, device_types, window_days, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (row_id, service_key, service_name, slo_target, device_types, window_days, description, is_active, created_at, updated_at))
        migrated_count += 1
        print(f"  Migrated: {service_name} -> {service_key}")

    conn.commit()
    print(f"Migrated {migrated_count} records")

    # 删除旧表
    cursor.execute("DROP TABLE service_slo")
    conn.commit()

    # 重命名新表
    cursor.execute("ALTER TABLE service_slo_new RENAME TO service_slo")
    conn.commit()
    print("Table renamed successfully")

    # 验证结果
    cursor.execute("PRAGMA table_info(service_slo)")
    columns = cursor.fetchall()
    print("\nTable structure after migration:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")

    cursor.execute("SELECT service_key, service_name, slo_target, device_types FROM service_slo")
    rows = cursor.fetchall()
    print("\nData after migration:")
    for row in rows:
        print(f"  key={row[0]}, name={row[1]}, target={row[2]}%, types={row[3]}")

    conn.close()
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    run_migration()