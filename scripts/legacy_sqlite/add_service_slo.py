"""
Migration: Add ServiceSlo table and seed initial SLO configurations
Run from: cd /home/vayne/network-automation-system && python3 migrations/add_service_slo.py
"""
import sys
sys.path.insert(0, '/home/vayne/network-automation-system/backend')

from sqlalchemy import text
from app.core.database import engine

def run_migration():
    """Create service_slo table and seed initial data"""

    # Create table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS service_slo (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name VARCHAR(100) NOT NULL UNIQUE,
        slo_target DECIMAL(5,4) NOT NULL,
        window_days INTEGER DEFAULT 30,
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """

    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
        print("service_slo table created successfully")

        # Check if data exists
        result = conn.execute(text("SELECT COUNT(*) FROM service_slo"))
        count = result.scalar()

        if count == 0:
            # Seed initial SLO configurations
            seed_sql = """
            INSERT INTO service_slo (service_name, slo_target, window_days, is_active) VALUES
                ('核心网络可达性', 99.9, 30, 1),
                ('数据中心网络', 99.5, 30, 1),
                ('园区接入网络', 99.0, 30, 1);
            """
            conn.execute(text(seed_sql))
            conn.commit()
            print("Initial SLO data seeded successfully")
        else:
            print(f"service_slo already has {count} records, skipping seed")

if __name__ == "__main__":
    run_migration()