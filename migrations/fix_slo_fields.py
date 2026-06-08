"""
Migration: Fix SLO field precision and add device_types
Run from: cd /home/vayne/network-automation-system && python3 migrations/fix_slo_fields.py
"""
import sqlite3

DB_PATH = 'data/nas.db'

def run_migration():
    """Fix SLO precision and add device_types column"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='service_slo'")
    if not cursor.fetchone():
        print("service_slo table not found, creating...")
        cursor.execute("""
            CREATE TABLE service_slo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name VARCHAR(100) NOT NULL UNIQUE,
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
        print("Table created successfully")
        conn.close()
        return

    # 获取现有数据
    cursor.execute("SELECT * FROM service_slo")
    existing_rows = cursor.fetchall()
    print(f"Found {len(existing_rows)} existing records")

    # SQLite 不支持 ALTER COLUMN，需要重建表
    # 根据服务名称设置 device_types
    device_types_map = {
        '核心网络可达性': 'core_switch,router',
        '数据中心网络': 'server_switch',
        'WiFi 无线网络': 'ap,wlc',
        '园区接入网络': 'office_switch',
    }

    # 创建新表
    cursor.execute("""
        CREATE TABLE service_slo_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name VARCHAR(100) NOT NULL UNIQUE,
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
    print("New table structure created")

    # 复制数据
    for row in existing_rows:
        row_id = row[0]
        service_name = row[1]
        slo_target = row[2]
        # 处理精度问题：确保 slo_target 是百分数形式
        if slo_target < 10:  # 可能是小数形式 (如 0.999)
            slo_target = slo_target * 100  # 转为百分数
        device_types = device_types_map.get(service_name, '')
        window_days = row[3] if len(row) > 3 else 30
        description = row[4] if len(row) > 4 else None
        is_active = row[5] if len(row) > 5 else 1
        created_at = row[6] if len(row) > 6 else None
        updated_at = row[7] if len(row) > 7 else None

        cursor.execute("""
            INSERT INTO service_slo_new (id, service_name, slo_target, device_types, window_days, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (row_id, service_name, slo_target, device_types, window_days, description, is_active, created_at, updated_at))

    conn.commit()
    print(f"Migrated {len(existing_rows)} records")

    # 删除旧表
    cursor.execute("DROP TABLE service_slo")
    conn.commit()

    # 重命名新表
    cursor.execute("ALTER TABLE service_slo_new RENAME TO service_slo")
    conn.commit()
    print("Table renamed successfully")

    # 添加 WiFi SLO（如果不存在）
    cursor.execute("SELECT COUNT(*) FROM service_slo WHERE service_name = 'WiFi 无线网络'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO service_slo (service_name, slo_target, device_types, window_days, is_active)
            VALUES ('WiFi 无线网络', 99.0, 'ap,wlc', 30, 1)
        """)
        conn.commit()
        print("Added WiFi SLO")

    # 验证结果
    cursor.execute("PRAGMA table_info(service_slo)")
    columns = cursor.fetchall()
    print("\nTable structure after migration:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")

    cursor.execute("SELECT * FROM service_slo")
    rows = cursor.fetchall()
    print("\nData after migration:")
    for row in rows:
        print(f"  {row}")

    conn.close()
    print("\nMigration completed!")

if __name__ == "__main__":
    run_migration()