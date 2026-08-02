"""
Migration: Create device_links table for topology edge modeling

This migration creates the device_links table to support:
- Dual uplink connections (PortChannel members)
- SVL (StackWise Virtual) core switch stacking
- Arbitrary topology edge relationships

Run from: cd /home/vayne/network-automation-system && python3 migrations/create_device_links.py
"""
import sqlite3
import json

DB_PATH = 'data/nas.db'

def run_migration():
    """Create device_links table and indexes"""

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='device_links'")
    if cursor.fetchone():
        print("device_links table already exists, skipping migration")
        conn.close()
        return

    # Create device_links table
    cursor.execute("""
        CREATE TABLE device_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            floor_plan_id INTEGER NOT NULL,
            from_node_id INTEGER NOT NULL,
            to_node_id INTEGER NOT NULL,
            link_role VARCHAR(20) NOT NULL DEFAULT 'uplink',
            link_group VARCHAR(40),
            link_type VARCHAR(20) NOT NULL DEFAULT 'fiber',
            waypoints TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (floor_plan_id) REFERENCES floor_plans(id) ON DELETE CASCADE,
            FOREIGN KEY (from_node_id) REFERENCES device_nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (to_node_id) REFERENCES device_nodes(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    print("Created device_links table")

    # Create indexes
    indexes = [
        ("idx_device_links_floor_plan", "floor_plan_id"),
        ("idx_device_links_from_node", "from_node_id"),
        ("idx_device_links_to_node", "to_node_id"),
        ("idx_device_links_link_group", "link_group"),
        ("idx_device_links_link_role", "link_role"),
    ]

    for idx_name, idx_col in indexes:
        try:
            cursor.execute(f"CREATE INDEX {idx_name} ON device_links({idx_col})")
            conn.commit()
            print(f"Created index {idx_name}")
        except Exception as e:
            print(f"Index {idx_name} note: {e}")

    # Verify table structure
    cursor.execute("PRAGMA table_info(device_links)")
    columns = cursor.fetchall()
    print("\nTable structure:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")

    conn.close()
    print("\nMigration completed successfully!")


if __name__ == "__main__":
    run_migration()