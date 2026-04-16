"""
测试数据种子脚本
用于生成示例数据，方便演示和测试系统功能

使用方法:
    python scripts/seed_data.py
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import random

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db_manager, get_db
from app.models import (
    Device, BackupRecord, FaultRecord, MaintenanceRecord,
    ConfigTemplate, CredentialGroup, AuditLog, Base
)
from sqlalchemy.orm import Session


def clear_existing_data(db: Session):
    """清除现有数据"""
    print("清除现有测试数据...")

    # 按依赖顺序删除
    db.query(AuditLog).delete()
    db.query(BackupRecord).delete()
    db.query(FaultRecord).delete()
    db.query(MaintenanceRecord).delete()
    db.query(Device).delete()
    db.query(ConfigTemplate).delete()
    db.query(CredentialGroup).delete()

    db.commit()
    print("清除完成!")


def create_credential_groups(db: Session):
    """创建 SSH 凭证组"""
    print("\n创建凭证组...")

    groups = [
        CredentialGroup(
            name="default",
            description="默认凭证组 - 用于大多数设备",
            username="admin",
            password_encrypted="cGlAb3AxMjM=",  # 示例加密密码
            enable_password_encrypted="ZW5hYmxlMTIz"
        ),
        CredentialGroup(
            name="core-switches",
            description="核心交换机专用凭证",
            username="core_admin",
            password_encrypted="Y29yZUAxMjM=",
            enable_password_encrypted="Y29yZUVuMTIz"
        ),
        CredentialGroup(
            name="readonly",
            description="只读监控凭证",
            username="monitor",
            password_encrypted="bW9uaXRvckAxMjM=",
            enable_password_encrypted=None
        )
    ]

    db.add_all(groups)
    db.commit()
    print(f"  已创建 {len(groups)} 个凭证组")
    return {g.name: g.id for g in groups}


def create_devices(db: Session) -> dict:
    """创建示例设备"""
    print("\n创建设备...")

    now = datetime.utcnow()

    devices_data = [
        # 核心交换机
        {
            "name": "Core-SW-01",
            "ip": "192.168.1.1",
            "model": "Cisco Catalyst 9500-48Y4C",
            "serial_number": "CAT1234A001",
            "location": "主数据中心 - 机柜 A01",
            "role": "core",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("45000.00"),
            "purchase_date": now - timedelta(days=730),
            "credential_group": "core-switches"
        },
        {
            "name": "Core-SW-02",
            "ip": "192.168.1.2",
            "model": "Cisco Catalyst 9500-48Y4C",
            "serial_number": "CAT1234A002",
            "location": "主数据中心 - 机柜 A02",
            "role": "core",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("45000.00"),
            "purchase_date": now - timedelta(days=700),
            "credential_group": "core-switches"
        },
        # 汇聚交换机
        {
            "name": "Dist-SW-01",
            "ip": "192.168.2.1",
            "model": "Cisco Catalyst 9300-48P",
            "serial_number": "CAT9300B001",
            "location": "办公楼 1 楼 - 机房",
            "role": "distribution",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("18000.00"),
            "purchase_date": now - timedelta(days=500),
            "credential_group": "default"
        },
        {
            "name": "Dist-SW-02",
            "ip": "192.168.2.2",
            "model": "Cisco Catalyst 9300-48P",
            "serial_number": "CAT9300B002",
            "location": "办公楼 2 楼 - 机房",
            "role": "distribution",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("18000.00"),
            "purchase_date": now - timedelta(days=480),
            "credential_group": "default"
        },
        {
            "name": "Dist-SW-03",
            "ip": "192.168.3.1",
            "model": "Cisco Catalyst 9300-24P",
            "serial_number": "CAT9300C001",
            "location": "研发楼 1 楼 - 机房",
            "role": "distribution",
            "status": "maintenance",
            "vendor": "Cisco",
            "purchase_cost": Decimal("15000.00"),
            "purchase_date": now - timedelta(days=400),
            "credential_group": "default"
        },
        # 接入交换机
        {
            "name": "Access-SW-01",
            "ip": "192.168.10.1",
            "model": "Cisco Catalyst 2960X-48FPS-L",
            "serial_number": "CAT2960D001",
            "location": "办公楼 1 楼 - 配线间 101",
            "role": "access",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("8500.00"),
            "purchase_date": now - timedelta(days=600),
            "credential_group": "default"
        },
        {
            "name": "Access-SW-02",
            "ip": "192.168.10.2",
            "model": "Cisco Catalyst 2960X-48FPS-L",
            "serial_number": "CAT2960D002",
            "location": "办公楼 1 楼 - 配线间 102",
            "role": "access",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("8500.00"),
            "purchase_date": now - timedelta(days=590),
            "credential_group": "default"
        },
        {
            "name": "Access-SW-03",
            "ip": "192.168.11.1",
            "model": "Cisco Catalyst 2960X-24TS-L",
            "serial_number": "CAT2960E001",
            "location": "办公楼 2 楼 - 配线间 201",
            "role": "access",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("6500.00"),
            "purchase_date": now - timedelta(days=550),
            "credential_group": "default"
        },
        {
            "name": "Access-SW-04",
            "ip": "192.168.11.2",
            "model": "Cisco Catalyst 2960X-24TS-L",
            "serial_number": "CAT2960E002",
            "location": "办公楼 2 楼 - 配线间 202",
            "role": "access",
            "status": "offline",
            "vendor": "Cisco",
            "purchase_cost": Decimal("6500.00"),
            "purchase_date": now - timedelta(days=540),
            "credential_group": "default"
        },
        {
            "name": "Access-SW-05",
            "ip": "192.168.12.1",
            "model": "Cisco Catalyst 2960L-48PQ-LL",
            "serial_number": "CAT2960F001",
            "location": "研发楼 1 楼 - 配线间 101",
            "role": "access",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("7200.00"),
            "purchase_date": now - timedelta(days=300),
            "credential_group": "default"
        },
        {
            "name": "Access-SW-06",
            "ip": "192.168.12.2",
            "model": "Cisco Catalyst 2960L-48PQ-LL",
            "serial_number": "CAT2960F002",
            "location": "研发楼 1 楼 - 配线间 102",
            "role": "access",
            "status": "online",
            "vendor": "Cisco",
            "purchase_cost": Decimal("7200.00"),
            "purchase_date": now - timedelta(days=290),
            "credential_group": "default"
        },
        {
            "name": "Access-SW-07",
            "ip": "192.168.13.1",
            "model": "Cisco Catalyst 2960L-24Q-LL",
            "serial_number": "CAT2960F003",
            "location": "研发楼 2 楼 - 配线间 201",
            "role": "access",
            "status": "retired",
            "vendor": "Cisco",
            "purchase_cost": Decimal("5500.00"),
            "purchase_date": now - timedelta(days=800),
            "credential_group": "default"
        },
    ]

    devices = []
    for data in devices_data:
        device = Device(**data)
        devices.append(device)
        db.add(device)

    db.commit()

    device_map = {d.name: d.id for d in devices}
    print(f"  已创建 {len(devices)} 台设备")
    print(f"    - 核心交换机：2 台")
    print(f"    - 汇聚交换机：3 台")
    print(f"    - 接入交换机：7 台")

    return device_map


def create_backup_records(db: Session, device_map: dict):
    """创建备份记录"""
    print("\n创建备份记录...")

    now = datetime.utcnow()
    backups = []

    # 为每个在线设备创建最近的备份记录
    for device_name, device_id in device_map.items():
        device_status = "online" if "Core" in device_name or "Dist" in device_name or \
                        device_name in ["Access-SW-01", "Access-SW-02", "Access-SW-03",
                                       "Access-SW-05", "Access-SW-06"] else "offline"

        if device_status == "online":
            # 最近一次备份（今天）
            backups.append(BackupRecord(
                device_id=device_id,
                backup_file=f"backups/{device_name}/{device_name}_{now.strftime('%Y%m%d_%H%M%S')}.cfg",
                file_size=random.randint(5000, 50000),
                md5_hash=f"abc123{random.randint(1000, 9999)}def456",
                has_change=random.choice([True, False]),
                diff_file=None,
                backup_time=now - timedelta(hours=random.randint(1, 24)),
                operator="admin",
                device_name=device_name
            ))

            # 历史备份（过去 7 天）
            for i in range(random.randint(3, 7)):
                backup_time = now - timedelta(days=i+1, hours=random.randint(1, 23))
                backups.append(BackupRecord(
                    device_id=device_id,
                    backup_file=f"backups/{device_name}/{device_name}_{backup_time.strftime('%Y%m%d_%H%M%S')}.cfg",
                    file_size=random.randint(5000, 50000),
                    md5_hash=f"xyz789{random.randint(1000, 9999)}abc123",
                    has_change=random.choice([True, False, False]),
                    diff_file=None,
                    backup_time=backup_time,
                    operator=random.choice(["admin", "netop", "system"]),
                    device_name=device_name
                ))

    db.add_all(backups)
    db.commit()
    print(f"  已创建 {len(backups)} 条备份记录")


def create_fault_records(db: Session, device_map: dict):
    """创建故障记录"""
    print("\n创建故障记录...")

    now = datetime.utcnow()

    faults_data = [
        {
            "device_id": device_map["Access-SW-04"],
            "device_name": "Access-SW-04",
            "fault_no": "FLT-2026-0001",
            "fault_time": now - timedelta(days=2),
            "description": "设备无法 Ping 通，所有端口无响应",
            "severity": "critical",
            "downtime_minutes": 180,
            "impact": "办公楼 2 楼东侧全部网络中断，影响约 50 个用户",
            "resolution": "更换设备电源模块后恢复正常",
            "cost": Decimal("800.00"),
            "reporter": "监控中心",
            "status": "resolved"
        },
        {
            "device_id": device_map["Dist-SW-03"],
            "device_name": "Dist-SW-03",
            "fault_no": "FLT-2026-0002",
            "fault_time": now - timedelta(days=1),
            "description": "部分端口间歇性丢包",
            "severity": "major",
            "downtime_minutes": 0,
            "impact": "研发楼 1 楼部分用户网络不稳定",
            "resolution": "正在进行硬件诊断，等待备件",
            "cost": Decimal("0.00"),
            "reporter": "用户报修",
            "status": "investigating"
        },
        {
            "device_id": device_map["Access-SW-07"],
            "device_name": "Access-SW-07",
            "fault_no": "FLT-2025-0089",
            "fault_time": now - timedelta(days=45),
            "description": "设备老化，频繁出现 CRC 错误",
            "severity": "major",
            "downtime_minutes": 480,
            "impact": "研发楼 2 楼部分区域网络中断",
            "resolution": "已退役设备，更换新设备 Access-SW-08",
            "cost": Decimal("0.00"),
            "reporter": "网络运维组",
            "status": "closed"
        },
        {
            "device_id": device_map["Core-SW-01"],
            "device_name": "Core-SW-01",
            "fault_no": "FLT-2025-0075",
            "fault_time": now - timedelta(days=90),
            "description": "主备切换失败",
            "severity": "critical",
            "downtime_minutes": 15,
            "impact": "核心网络短暂中断 15 分钟",
            "resolution": "修复 ISSU 配置，更新备用引擎固件",
            "cost": Decimal("2000.00"),
            "reporter": "监控中心",
            "status": "closed"
        },
    ]

    faults = [FaultRecord(**data) for data in faults_data]
    db.add_all(faults)
    db.commit()
    print(f"  已创建 {len(faults)} 条故障记录")


def create_maintenance_records(db: Session, device_map: dict):
    """创建维修记录"""
    print("\n创建维修记录...")

    now = datetime.utcnow()

    maintenance_data = [
        {
            "device_id": device_map["Access-SW-04"],
            "device_name": "Access-SW-04",
            "maint_no": "MNT-2026-0001",
            "maint_type": "corrective",
            "maint_time": now - timedelta(days=2),
            "parts_replaced": "电源模块 PWR-C1-1100WAC",
            "parts_cost": Decimal("600.00"),
            "labor_hours": Decimal("2.0"),
            "labor_cost": Decimal("300.00"),
            "vendor": "Cisco TAC",
            "description": "更换故障电源模块",
            "post_status": "设备恢复正常，已重新上线",
            "operator": "李工"
        },
        {
            "device_id": device_map["Dist-SW-02"],
            "device_name": "Dist-SW-02",
            "maint_no": "MNT-2026-0002",
            "maint_type": "preventive",
            "maint_time": now - timedelta(days=15),
            "parts_replaced": "无",
            "parts_cost": Decimal("0.00"),
            "labor_hours": Decimal("1.5"),
            "labor_cost": Decimal("200.00"),
            "vendor": "内部维护",
            "description": "季度预防性维护：清洁风扇、检查日志、更新配置备份",
            "post_status": "维护完成，设备运行正常",
            "operator": "王工"
        },
        {
            "device_id": device_map["Core-SW-01"],
            "device_name": "Core-SW-01",
            "maint_no": "MNT-2025-0045",
            "maint_type": "upgrade",
            "maint_time": now - timedelta(days=100),
            "parts_replaced": "无",
            "parts_cost": Decimal("0.00"),
            "labor_hours": Decimal("4.0"),
            "labor_cost": Decimal("800.00"),
            "vendor": "Cisco 专业服务",
            "description": "IOS-XE 版本升级：17.3.4 -> 17.6.3",
            "post_status": "升级成功，运行稳定",
            "operator": "Cisco 工程师"
        },
        {
            "device_id": device_map["Access-SW-01"],
            "device_name": "Access-SW-01",
            "maint_no": "MNT-2025-0038",
            "maint_type": "corrective",
            "maint_time": now - timedelta(days=150),
            "parts_replaced": "风扇模块 FAN-2960X",
            "parts_cost": Decimal("250.00"),
            "labor_hours": Decimal("1.0"),
            "labor_cost": Decimal("150.00"),
            "vendor": "内部维护",
            "description": "更换故障风扇",
            "post_status": "风扇运转正常，温度恢复正常",
            "operator": "张工"
        },
    ]

    maintenances = [MaintenanceRecord(**data) for data in maintenance_data]
    db.add_all(maintenances)
    db.commit()
    print(f"  已创建 {len(maintenances)} 条维修记录")


def create_config_templates(db: Session):
    """创建配置模板"""
    print("\n创建配置模板...")

    templates = [
        ConfigTemplate(
            name="接入交换机标准配置",
            description="适用于所有接入层交换机的基础配置模板",
            template_content="""! 接入交换机标准配置
hostname {{ hostname }}

! NTP 配置
ntp server {{ ntp_primary }}
ntp server {{ ntp_secondary }}

! SNMP 配置
snmp-server community {{ snmp_community }} RO
snmp-server location {{ location }}
snmp-server contact {{ contact }}

! 端口配置
{% for port in ports %}
interface GigabitEthernet{{ port }}
 description User Access Port
 switchport mode access
 switchport access vlan {{ access_vlan }}
 spanning-tree portfast
 spanning-tree bpduguard enable
!
{% endfor %}

! 管理 VLAN
interface Vlan{{ management_vlan }}
 description Management VLAN
 ip address {{ management_ip }} {{ subnet_mask }}
 no shutdown
!
! 默认路由
ip default-gateway {{ gateway }}
""",
            variables='{"hostname": "交换机名", "ntp_primary": "主 NTP 服务器", "access_vlan": "接入 VLAN ID", "management_vlan": "管理 VLAN", "ports": ["1/0/1", "1/0/2", "..."]}'
        ),
        ConfigTemplate(
            name="汇聚交换机 OSPF 配置",
            description="汇聚交换机 OSPF 路由配置模板",
            template_content="""! 汇聚交换机 OSPF 配置
router ospf {{ process_id }}
 router-id {{ router_id }}
 log-adjacency-changes

{% for network in networks %}
 network {{ network.ip }} {{ network.wildcard }} area {{ network.area }}
{% endfor %}

! BFD for OSPF
{% for interface in bfd_interfaces %}
interface {{ interface }}
 ip ospf bfd
!
{% endfor %}
""",
            variables='{"process_id": "OSPF 进程 ID", "router_id": "路由器 ID", "networks": "OSPF 网络列表", "bfd_interfaces": "启用 BFD 的接口"}'
        ),
        ConfigTemplate(
            name="端口安全配置",
            description="交换机端口安全配置模板",
            template_content="""! 端口安全配置
interface {{ interface }}
 switchport mode access
 switchport port-security
 switchport port-security maximum {{ max_mac_count }}
 switchport port-security violation {{ violation_mode }}
 switchport port-security aging time {{ aging_time }}
 switchport port-security aging type inactivity
!
""",
            variables='{"interface": "接口名称", "max_mac_count": "最大 MAC 地址数", "violation_mode": "违规处理方式 (protect/restrict/shutdown)", "aging_time": "老化时间 (分钟)"}'
        )
    ]

    db.add_all(templates)
    db.commit()
    print(f"  已创建 {len(templates)} 个配置模板")


def create_audit_logs(db: Session, device_map: dict):
    """创建审计日志"""
    print("\n创建审计日志...")

    now = datetime.utcnow()

    logs = [
        AuditLog(
            operator="admin",
            action="device.create",
            target_type="device",
            target_id=device_map.get("Core-SW-01"),
            details="创建核心交换机 Core-SW-01",
            ip_address="192.168.100.10",
            created_at=now - timedelta(hours=1)
        ),
        AuditLog(
            operator="netop",
            action="backup.execute",
            target_type="backup",
            target_id=None,
            details="执行批量配置备份，成功 10 台，失败 0 台",
            ip_address="192.168.100.15",
            created_at=now - timedelta(hours=2)
        ),
        AuditLog(
            operator="admin",
            action="fault.resolve",
            target_type="fault",
            target_id=None,
            details="解决故障 FLT-2026-0001 (Access-SW-04)",
            ip_address="192.168.100.10",
            created_at=now - timedelta(days=2)
        ),
        AuditLog(
            operator="system",
            action="maintenance.create",
            target_type="maintenance",
            target_id=None,
            details="创建预防性维护记录 MNT-2026-0002",
            ip_address="127.0.0.1",
            created_at=now - timedelta(days=15)
        ),
    ]

    db.add_all(logs)
    db.commit()
    print(f"  已创建 {len(logs)} 条审计日志")


def print_summary():
    """打印摘要信息"""
    print("\n" + "=" * 50)
    print("测试数据生成完成!")
    print("=" * 50)
    print("""
数据摘要:
  - 凭证组：3 个 (default, core-switches, readonly)
  - 设备：12 台
    * 核心交换机：2 台 (online)
    * 汇聚交换机：3 台 (2 online, 1 maintenance)
    * 接入交换机：7 台 (5 online, 1 offline, 1 retired)

  - 备份记录：约 50+ 条
  - 故障记录：4 条 (含不同状态)
  - 维修记录：4 条 (含不同类型)
  - 配置模板：3 个
  - 审计日志：4 条

登录信息:
  API 文档：http://localhost:8000/docs
  前端界面：http://localhost:3000

设备状态分布:
  - online: 7 台
  - offline: 1 台
  - maintenance: 1 台
  - retired: 1 台

下一步:
  1. 启动后端：python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
  2. 启动前端：cd frontend && npm run dev
  3. 访问 http://localhost:3000 查看效果
""")


def main():
    """主函数"""
    print("=" * 50)
    print("Network Automation System - 测试数据生成器")
    print("=" * 50)

    # 获取数据库管理器
    db_manager = get_db_manager()

    # 初始化数据库
    db_manager.init_db()

    db = db_manager.get_session()

    try:
        # 清除现有数据
        clear_existing_data(db)

        # 创建数据
        create_credential_groups(db)
        device_map = create_devices(db)
        create_backup_records(db, device_map)
        create_fault_records(db, device_map)
        create_maintenance_records(db, device_map)
        create_config_templates(db)
        create_audit_logs(db, device_map)

        # 打印摘要
        print_summary()

    except Exception as e:
        db.rollback()
        print(f"\n错误：{e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    exit(main())
