"""
初始化内置合规规则

将硬编码的内置规则转换为数据库规则，支持开关控制
"""
from datetime import datetime
from loguru import logger
from app.shared.database import get_db
from app.shared.models import ComplianceRule, ComplianceStandard


# 内置规则定义
BUILTIN_RULES = [
    {
        "rule_id": "SEC-001",
        "name": "特权模式密码保护",
        "category": "security",
        "severity": "critical",
        "pattern": "enable secret",
        "check_logic": "检查配置文件中是否存在 enable secret 命令，验证是否使用加密存储的特权密码",
        "recommendation": "enable secret <strong-password>",
        "description": "所有网络设备必须配置特权模式密码保护，使用 enable secret 命令配置加密存储的特权密码，禁止使用 enable password 明文存储"
    },
    {
        "rule_id": "SEC-002",
        "name": "SSH Version 2 配置",
        "category": "security",
        "severity": "high",
        "pattern": "ip ssh version 2",
        "check_logic": "检查配置中是否存在 ip ssh version 2 命令，确保SSH使用Version 2",
        "recommendation": "ip ssh version 2",
        "description": "远程管理必须使用 SSH 协议，SSH 版本必须设置为 Version 2"
    },
    {
        "rule_id": "SEC-003",
        "name": "密码加密服务",
        "category": "security",
        "severity": "high",
        "pattern": "service password-encryption",
        "check_logic": "检查配置中是否存在 service password-encryption 命令",
        "recommendation": "service password-encryption",
        "description": "所有密码必须在配置文件中加密存储，启用密码加密服务"
    },
    {
        "rule_id": "SEC-004",
        "name": "管理平面访问控制",
        "category": "security",
        "severity": "high",
        "pattern": "access-class",
        "check_logic": "检查VTY端口是否配置 access-class ACL限制访问来源",
        "recommendation": "ip access-list standard MGMT-ACL\n permit 10.10.100.0 0.0.0.255\n deny any log\nline vty 0 4\n access-class MGMT-ACL in",
        "description": "必须配置 ACL 限制管理平面（VTY、SNMP、HTTP）的访问来源 IP 地址"
    },
    {
        "rule_id": "SEC-005",
        "name": "未使用端口管理",
        "category": "security",
        "severity": "medium",
        "pattern": "shutdown",
        "check_logic": "检查未使用的物理端口是否配置 shutdown 状态",
        "recommendation": "interface range GigabitEthernet 1/0/10 - 24\n shutdown\n switchport access vlan 999\n description UNUSED_PORT",
        "description": "所有未使用的物理端口必须处于 shutdown 状态，防止未经授权的设备接入"
    },
    {
        "rule_id": "SEC-006",
        "name": "Native VLAN 安全",
        "category": "security",
        "severity": "medium",
        "pattern": "switchport trunk native vlan",
        "check_logic": "检查Trunk端口的Native VLAN是否修改为非默认值（非VLAN 1）",
        "recommendation": "interface GigabitEthernet 1/0/1\n switchport trunk native vlan 999",
        "description": "Trunk 端口的 Native VLAN 必须修改为非默认值（非 VLAN 1），防止 VLAN Hopping 攻击"
    },
    {
        "rule_id": "SEC-007",
        "name": "Syslog 日志配置",
        "category": "security",
        "severity": "medium",
        "pattern": "logging",
        "check_logic": "检查是否配置远程Syslog服务器IP地址",
        "recommendation": "logging buffered 10000 informational\nlogging 10.10.100.20\nservice timestamps log datetime msec localtime",
        "description": "设备必须配置远程 Syslog 服务器，将操作日志和事件日志发送至日志服务器集中存储"
    },
    {
        "rule_id": "SEC-008",
        "name": "NTP 时间同步",
        "category": "availability",
        "severity": "medium",
        "pattern": "ntp server",
        "check_logic": "检查是否配置至少一个NTP服务器",
        "recommendation": "ntp server 10.10.100.30 prefer\nntp server 10.10.100.31",
        "description": "所有网络设备必须配置 NTP 时间同步，确保日志时间准确性"
    },
    {
        "rule_id": "SEC-009",
        "name": "登录警告横幅",
        "category": "compliance",
        "severity": "low",
        "pattern": "banner motd",
        "check_logic": "检查是否配置登录警告横幅（Banner）",
        "recommendation": "banner motd #\n*******************************************************************\n* WARNING: This device is the property of Company Name.          *\n* Unauthorized access is prohibited and will be prosecuted.      *\n*******************************************************************\n#",
        "description": "设备应配置登录警告横幅（Banner），声明设备归属和访问授权"
    },
    {
        "rule_id": "SEC-010",
        "name": "SNMP Community 安全",
        "category": "security",
        "severity": "critical",
        "pattern": "snmp-server community",
        "check_logic": "检查SNMP Community是否为默认值(public/private)",
        "recommendation": "ip access-list standard SNMP-ACL\n permit 10.10.100.20\n deny any\nsnmp-server community <secure-string> RO SNMP-ACL",
        "description": "SNMP 必须配置安全的 Community 字符串，禁止使用默认 Community（public/private）"
    },
]


def init_builtin_rules():
    """初始化内置规则到数据库"""
    db = next(get_db())
    try:
        # 检查是否已存在内置规则
        existing = db.query(ComplianceRule).filter(
            ComplianceRule.source_type == "builtin"
        ).first()

        if existing:
            logger.info("内置规则已存在，跳过初始化")
            return

        # 创建一个内置标准文档
        standard = ComplianceStandard(
            name="网络设备安全基线",
            version="1.0",
            description="内置的安全配置基线标准",
            content="内置标准，包含核心安全检查规则",
            is_active=True,
            created_by="system",
            created_at=datetime.utcnow()
        )
        db.add(standard)
        db.flush()

        # 添加内置规则
        for rule_data in BUILTIN_RULES:
            rule = ComplianceRule(
                standard_id=standard.id,
                rule_id=rule_data["rule_id"],
                name=rule_data["name"],
                category=rule_data["category"],
                severity=rule_data["severity"],
                pattern=rule_data["pattern"],
                check_logic=rule_data["check_logic"],
                recommendation=rule_data["recommendation"],
                source_type="builtin",
                is_active=True,
                created_at=datetime.utcnow()
            )
            db.add(rule)

        db.commit()
        logger.info(f"初始化内置规则完成，共 {len(BUILTIN_RULES)} 条规则")

    except Exception as e:
        db.rollback()
        logger.error(f"初始化内置规则失败: {e}")
        raise
    finally:
        db.close()


def get_all_rules_for_audit():
    """获取所有激活的规则用于AI审核"""
    db = next(get_db())
    try:
        rules = db.query(ComplianceRule).filter(
            ComplianceRule.is_active == True
        ).order_by(ComplianceRule.severity, ComplianceRule.rule_id).all()

        return [
            {
                "id": r.id,
                "rule_id": r.rule_id,
                "name": r.name,
                "category": r.category,
                "severity": r.severity,
                "pattern": r.pattern,
                "check_logic": r.check_logic,
                "recommendation": r.recommendation,
                "source_type": r.source_type,
                "description": getattr(r, 'description', '')  # 内置规则有描述字段
            }
            for r in rules
        ]
    finally:
        db.close()