"""
Migration: Add monitor_tier field to Device model for graded monitoring
Run from: cd /home/vayne/network-automation-system && python3 migrations/add_monitor_tier.py

This migration adds a monitor_tier field to classify devices by monitoring priority:
- critical: Core switches/routers (15s check interval, 2 failures threshold)
- normal: Access switches, WLCs (60s check interval, 3 failures threshold)
- low: APs and others (300s check interval, 3 failures threshold)
"""
import sqlite3

DB_PATH = 'data/nas.db'

# 设备类型到监控分级映射
DEVICE_TYPE_TIER_MAP = {
    'core_switch': 'critical',
    'server_switch': 'critical',
    'router': 'critical',
    'uce': 'normal',
    'office_switch': 'normal',
    'wlc': 'normal',
    'ap': 'low',
    'pa': 'normal',
    'ftd': 'normal',
    'other': 'low',
}

def run_migration():
    """Add monitor_tier field and backfill based on device_type"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
    if not cursor.fetchone():
        print("devices table not found, skipping migration")
        conn.close()
        return

    # 检查 monitor_tier 列是否已存在
    cursor.execute("PRAGMA table_info(devices)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'monitor_tier' in columns:
        print("monitor_tier column already exists, skipping migration")
        conn.close()
        return

    # 添加 monitor_tier 列
    cursor.execute("ALTER TABLE devices ADD COLUMN monitor_tier VARCHAR(20) DEFAULT 'normal'")
    conn.commit()
    print("Added monitor_tier column")

    # 创建索引
    try:
        cursor.execute("CREATE INDEX idx_devices_monitor_tier ON devices(monitor_tier)")
        conn.commit()
        print("Created monitor_tier index")
    except Exception as e:
        print(f"Index creation note: {e}")

    # 回填数据：根据 device_type 设置 monitor_tier
    cursor.execute("SELECT id, device_type FROM devices WHERE monitor_tier IS NULL OR monitor_tier = 'normal'")
    devices = cursor.fetchall()
    print(f"Found {len(devices)} devices to update")

    updated_count = 0
    for device_id, device_type in devices:
        tier = DEVICE_TYPE_TIER_MAP.get(device_type, 'normal')
        cursor.execute("UPDATE devices SET monitor_tier = ? WHERE id = ?", (tier, device_id))
        updated_count += 1

    conn.commit()
    print(f"Updated {updated_count} devices with monitor_tier")

    # 验证结果
    cursor.execute("SELECT monitor_tier, COUNT(*) FROM devices GROUP BY monitor_tier")
    tiers = cursor.fetchall()
    print("\nTier distribution after migration:")
    for tier, count in tiers:
        print(f"  {tier}: {count} devices")

    conn.close()
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    run_migration()