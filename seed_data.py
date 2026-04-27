"""
Seed test data for the dashboard
"""
import sys, os, uuid
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from app.shared.database import get_db_manager
from app.shared.models import (
    Device, BackupRecord, FaultRecord, MaintenanceRecord,
    ConfigTemplate, CredentialGroup, SparePart, SparePartMovement,
    LogEntry
)
from app.features.credentials.credential_service import encrypt_password

db_manager = get_db_manager()
db = db_manager.get_session()

devices_data = [
    {"name": "SW-Core-01", "ip": "10.0.0.1", "model": "Cisco Catalyst 9500-48Y4C", "serial_number": "FCW2345A6BC", "location": "机房 A-机柜 1", "role": "core", "status": "online", "vendor": "Cisco", "purchase_date": datetime(2024, 3, 15), "purchase_cost": 85000, "credential_group": "default"},
    {"name": "SW-Core-02", "ip": "10.0.0.2", "model": "Cisco Catalyst 9500-48Y4C", "serial_number": "FCW2345A6BD", "location": "机房 A-机柜 2", "role": "core", "status": "online", "vendor": "Cisco", "purchase_date": datetime(2024, 3, 15), "purchase_cost": 85000, "credential_group": "default"},
    {"name": "SW-AGG-01", "ip": "10.0.1.1", "model": "Cisco Catalyst 9300-48T", "serial_number": "FCW3456B7CD", "location": "机房 B-机柜 1", "role": "distribution", "status": "online", "vendor": "Cisco", "purchase_date": datetime(2024, 6, 1), "purchase_cost": 42000, "credential_group": "default"},
    {"name": "SW-AGG-02", "ip": "10.0.1.2", "model": "Cisco Catalyst 9300-48T", "serial_number": "FCW3456B7CE", "location": "机房 B-机柜 2", "role": "distribution", "status": "maintenance", "vendor": "Cisco", "purchase_date": datetime(2024, 6, 1), "purchase_cost": 42000, "credential_group": "default"},
    {"name": "SW-Access-01", "ip": "10.0.2.1", "model": "Cisco Catalyst 9200-24P", "serial_number": "FCW4567C8DE", "location": "办公楼 1F", "role": "access", "status": "online", "vendor": "Cisco", "purchase_date": datetime(2024, 9, 10), "purchase_cost": 18000, "credential_group": "default"},
    {"name": "SW-Access-02", "ip": "10.0.2.2", "model": "Cisco Catalyst 9200-24P", "serial_number": "FCW4567C8DF", "location": "办公楼 2F", "role": "access", "status": "online", "vendor": "Cisco", "purchase_date": datetime(2024, 9, 10), "purchase_cost": 18000, "credential_group": "default"},
    {"name": "SW-Access-03", "ip": "10.0.2.3", "model": "Cisco Catalyst 9200-24P", "serial_number": "FCW4567C8DG", "location": "办公楼 3F", "role": "access", "status": "offline", "vendor": "Cisco", "purchase_date": datetime(2024, 9, 10), "purchase_cost": 18000, "credential_group": "default"},
    {"name": "SW-WLC-01", "ip": "10.0.3.1", "model": "Cisco Catalyst 9800-L", "serial_number": "FCW5678D9EF", "location": "机房 A-机柜 3", "role": "core", "status": "online", "vendor": "Cisco", "purchase_date": datetime(2025, 1, 20), "purchase_cost": 55000, "credential_group": "default"},
]

print("Creating devices...")
for d in devices_data:
    existing = db.query(Device).filter(Device.name == d["name"]).first()
    if existing:
        continue
    dev = Device(**d)
    db.add(dev)
db.commit()

# Get device objects
device_map = {d.name: d for d in db.query(Device).all()}

# Backup records
print("Creating backup records...")
severities = ["critical", "major", "minor", "warning"]
for i, (name, dev) in enumerate(device_map.items()):
    for j in range(random.randint(2, 5)):
        days_ago = random.randint(1, 29)
        backup_time = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 12))
        has_change = random.choice([True, False])
        snapshot = f"!\nhostname {name}\ninterface GigabitEthernet0/1\n description Port {j+1}\n switchport mode access\n!\n"
        record = BackupRecord(
            device_id=dev.id,
            device_name=name,
            backup_file=f"./backups/{name}_{backup_time.strftime('%Y%m%d_%H%M%S')}.cfg",
            file_size=random.randint(2048, 15000),
            md5_hash=uuid.uuid4().hex[:32],
            has_change=has_change,
            config_snapshot=snapshot,
            backup_time=backup_time,
            operator=random.choice(["admin", "operator", "CLI"]),
        )
        db.add(record)
    # Update last_backup_time
    dev.last_backup_time = datetime.utcnow() - timedelta(hours=random.randint(1, 24))
db.commit()

# Fault records
print("Creating fault records...")
fault_descriptions = [
    "端口 GigabitEthernet0/24 频繁 up/down",
    "CPU 使用率持续超过 85%",
    "STP 拓扑变化频繁，网络震荡",
    "模块 X2 光衰过大，链路质量下降",
    "电源模块 PSU-2 故障告警",
    "OSPF 邻居关系频繁断开",
    "MAC 地址表溢出，部分端口不通",
    "NTP 时间同步异常，偏差超过 5 秒",
]
for i in range(12):
    dev_name = random.choice(list(device_map.keys()))
    dev = device_map[dev_name]
    days_ago = random.randint(1, 29)
    fault_time = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
    severity = random.choice(severities)
    status = random.choice(["open", "investigating", "resolved", "closed"])
    fault_no = f"FAULT-{fault_time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    fault = FaultRecord(
        device_id=dev.id,
        device_name=dev_name,
        fault_no=fault_no,
        fault_time=fault_time,
        description=random.choice(fault_descriptions),
        severity=severity,
        downtime_minutes=random.choice([0, 5, 15, 30, 60, 120]),
        reporter=random.choice(["admin", "monitor", "user_report"]),
        status=status,
        created_at=fault_time,
    )
    db.add(fault)
db.commit()

# Maintenance records
print("Creating maintenance records...")
maint_types = ["preventive", "corrective", "upgrade", "emergency"]
maint_descriptions = [
    "更换故障电源模块",
    "例行巡检，清洁风扇",
    "升级 IOS 至 17.6.5",
    "更换 SFP+ 光模块",
    "重新布线机柜跳线",
    "更换故障风扇模块",
]
for i in range(8):
    dev_name = random.choice(list(device_map.keys()))
    dev = device_map[dev_name]
    days_ago = random.randint(1, 29)
    maint_time = datetime.utcnow() - timedelta(days=days_ago)
    maint_no = f"MNT-{maint_time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    parts_cost = random.choice([0, 500, 1200, 2500, 3800, 8500])
    labor_cost = random.choice([0, 300, 600, 1000, 1500])
    maint = MaintenanceRecord(
        device_id=dev.id,
        device_name=dev_name,
        maint_no=maint_no,
        maint_type=random.choice(maint_types),
        maint_time=maint_time,
        parts_cost=parts_cost,
        labor_cost=labor_cost,
        labor_hours=random.choice([1, 2, 3, 4, 8]),
        description=random.choice(maint_descriptions),
        operator=random.choice(["admin", "vendor_support", "team_a"]),
        created_at=maint_time,
    )
    db.add(maint)
db.commit()

# Credential group
print("Creating credential group...")
existing = db.query(CredentialGroup).filter(CredentialGroup.name == "default").first()
if not existing:
    cred = CredentialGroup(
        name="default",
        description="默认设备凭证组",
        username="admin",
        password_encrypted=encrypt_password("admin123"),
        enable_password_encrypted=encrypt_password("cisco123"),
    )
    db.add(cred)
db.commit()

# Spare parts
print("Creating spare parts...")
parts_data = [
    {"name": "SFP+ 10G 光模块", "part_number": "SFP-10G-SR", "category": "模块", "manufacturer": "Cisco", "description": "10GBASE-SR SFP+ 模块", "quantity_in_stock": 12, "min_quantity": 5, "unit_price": 850, "location": "备件柜 A1"},
    {"name": "千兆 SFP 光模块", "part_number": "GLC-SX-MMD", "category": "模块", "manufacturer": "Cisco", "description": "1000BASE-SX SFP 模块", "quantity_in_stock": 20, "min_quantity": 10, "unit_price": 320, "location": "备件柜 A2"},
    {"name": "Catalyst 9300 电源模块", "part_number": "PWR-C1-715WAC", "category": "电源", "manufacturer": "Cisco", "description": "715W AC 电源", "quantity_in_stock": 3, "min_quantity": 2, "unit_price": 2500, "location": "备件柜 B1"},
    {"name": "Catalyst 9300 风扇模块", "part_number": "C9300-FAN-1R", "category": "其他", "manufacturer": "Cisco", "description": "冗余风扇模块", "quantity_in_stock": 2, "min_quantity": 1, "unit_price": 1200, "location": "备件柜 B2"},
    {"name": "Cat6 网线 (箱)", "part_number": "CAT6-BOX", "category": "线缆", "manufacturer": "CommScope", "description": "305 米/箱 Cat6 网线", "quantity_in_stock": 5, "min_quantity": 2, "unit_price": 450, "location": "备件柜 C1"},
]
for p in parts_data:
    existing = db.query(SparePart).filter(SparePart.part_number == p["part_number"]).first()
    if existing:
        continue
    part = SparePart(**p)
    db.add(part)
db.commit()

# Spare part movements
print("Creating spare part movements...")
movement_reasons = ["设备故障更换", "备件入库", "项目领用", "定期补充库存"]
part_ids = [p.id for p in db.query(SparePart).all()]
for i in range(6):
    mv = SparePartMovement(
        part_id=random.choice(part_ids),
        movement_type=random.choice(["in", "out"]),
        quantity=random.randint(1, 5),
        reason=random.choice(movement_reasons),
        operator=random.choice(["admin", "warehouse"]),
        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 20)),
    )
    db.add(mv)
db.commit()

# Log entries
print("Creating log entries...")
tool_types = ["netmiko", "napalm", "jira"]
operations = ["backup config", "show running-config", "deploy config", "check OSPF neighbors", "create JIRA ticket"]
for i in range(10):
    entry = LogEntry(
        tool_type=random.choice(tool_types),
        operation=random.choice(operations),
        target=random.choice(list(device_map.keys())),
        status=random.choice(["success", "success", "success", "failed"]),
        duration_ms=random.randint(500, 15000),
        created_by="admin",
        timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 72)),
    )
    db.add(entry)
db.commit()

print(f"\nDone! Created:")
print(f"  Devices:          {db.query(Device).count()}")
print(f"  Backup records:   {db.query(BackupRecord).count()}")
print(f"  Fault records:    {db.query(FaultRecord).count()}")
print(f"  Maintenance:      {db.query(MaintenanceRecord).count()}")
print(f"  Credential groups:{db.query(CredentialGroup).count()}")
print(f"  Spare parts:      {db.query(SparePart).count()}")
print(f"  Part movements:   {db.query(SparePartMovement).count()}")
print(f"  Log entries:      {db.query(LogEntry).count()}")

db.close()
