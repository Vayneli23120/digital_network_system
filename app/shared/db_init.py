"""
数据库初始化模块

负责数据库表初始化和默认数据 seeding
"""

from loguru import logger
from app.shared.database import get_db
from app.shared.models import ConfigTemplate, Role


def init_default_roles():
    """初始化默认角色"""
    db = next(get_db())

    try:
        # 检查是否已有角色
        existing = db.query(Role).first()
        if existing:
            logger.info("默认角色已存在，跳过初始化")
            return

        # 默认角色列表
        default_roles = [
            {"name": "admin", "description": "系统管理员 - 拥有所有权限", "is_system": True},
            {"name": "operator", "description": "运维人员 - 可管理设备和配置", "is_system": True},
            {"name": "viewer", "description": "观察者 - 仅可查看数据", "is_system": True},
        ]

        for role_data in default_roles:
            role = Role(**role_data)
            db.add(role)
            logger.info(f"创建默认角色：{role_data['name']}")

        db.commit()
        logger.info("默认角色初始化完成")

    except Exception as e:
        db.rollback()
        logger.error(f"初始化默认角色失败：{e}")
    finally:
        db.close()


def init_default_templates():
    """初始化默认配置模板"""
    import json

    db = next(get_db())

    try:
        # 检查是否已有模板
        existing = db.query(ConfigTemplate).first()
        if existing:
            logger.info("默认模板已存在，跳过初始化")
            return  # 已有模板，跳过初始化

        # 默认模板列表
        default_templates = [
            {
                "name": "标准接入交换机配置",
                "description": "适用于接入层交换机的标准配置模板，包含基础网络配置、VLAN、端口安全等",
                "template_content": """!
! 配置模板：标准接入交换机配置
! 适用于：Cisco IOS 接入层交换机
! 创建时间：{{ now_str }}
!
version 15.2
service timestamps debug datetime msec
service timestamps log datetime msec
service password-encryption
!
hostname {{ HOSTNAME | default('SW-Access') }}
!
! AAA 认证
aaa new-model
aaa authentication login default local
aaa authentication enable default enable
aaa authorization exec default local
!
! 启用密码
enable secret {{ ENABLE_SECRET | default('YourEnablePassword') }}
!
! 本地用户
username {{ ADMIN_USERNAME | default('admin') }} privilege 15 secret {{ ADMIN_PASSWORD | default('YourAdminPassword') }}
username {{ OPERATOR_USERNAME | default('operator') }} privilege 5 secret {{ OPERATOR_PASSWORD | default('YourOperatorPassword') }}
!
! VTY 线路配置
line vty 0 15
 transport input ssh
 login authentication default
!
! SSH 配置
ip domain-name {{ DOMAIN_NAME | default('company.local') }}
crypto key generate rsa modulus 2048
ip ssh version 2
ip ssh time-out 60
ip ssh authentication-retries 2
!
! 管理 VLAN
vlan {{ MGMT_VLAN_ID | default('100') }}
 name Management
!
! 业务 VLAN 列表
{% for vlan in BUSINESS_VLANS | default([]) %}
vlan {{ vlan.id }}
 name {{ vlan.name }}
{% endfor %}
!
! 管理接口
interface Vlan{{ MGMT_VLAN_ID | default('100') }}
 description Management Interface
 ip address {{ MGMT_IP }} {{ MGMT_NETMASK | default('255.255.255.0') }}
 no shut
!
! 默认网关
ip default-gateway {{ DEFAULT_GATEWAY }}
!
! SNMP 配置
snmp-server community {{ SNMP_COMMUNITY | default('YourSNMPCommunity') }} RO
snmp-server location {{ LOCATION | default('Not Set') }}
snmp-server contact {{ CONTACT | default('network-admin@company.com') }}
!
! NTP 配置
ntp server {{ NTP_SERVER | default('10.0.0.1') }}
!
! Syslog 配置
logging host {{ SYSLOG_SERVER | default('10.0.0.2') }}
logging trap {{ LOGGING_LEVEL | default('warnings') }}
!
! STP 配置
spanning-tree mode rapid-pvst
spanning-tree extend system-id
!
! 端口安全（应用于接入端口）
interface range {{ ACCESS_PORT_RANGE | default('GigabitEthernet1/0/1-48') }}
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
 switchport port-security aging time 60
 spanning-tree portfast
 spanning-tree bpduguard enable
 no cdp enable
!
! 上联端口配置
interface {{ UPLINK_PORT | default('GigabitEthernet1/0/49') }}
 description Uplink to Distribution
 switchport mode trunk
 switchport trunk allowed vlan add {{ MGMT_VLAN_ID | default('100') }},{{ BUSINESS_VLAN_LIST | default('10,20,30') }}
 spanning-tree guard root
!
end""",
                "variables": json.dumps([
                    {"key": "HOSTNAME", "description": "设备主机名", "default": "SW-Access-01"},
                    {"key": "ENABLE_SECRET", "description": "Enable 密码", "default": ""},
                    {"key": "ADMIN_USERNAME", "description": "管理员用户名", "default": "admin"},
                    {"key": "ADMIN_PASSWORD", "description": "管理员密码", "default": ""},
                    {"key": "OPERATOR_USERNAME", "description": "操作员用户名", "default": "operator"},
                    {"key": "OPERATOR_PASSWORD", "description": "操作员密码", "default": ""},
                    {"key": "DOMAIN_NAME", "description": "域名", "default": "company.local"},
                    {"key": "MGMT_VLAN_ID", "description": "管理 VLAN ID", "default": "100"},
                    {"key": "MGMT_IP", "description": "管理 IP 地址", "default": ""},
                    {"key": "MGMT_NETMASK", "description": "管理子网掩码", "default": "255.255.255.0"},
                    {"key": "DEFAULT_GATEWAY", "description": "默认网关", "default": ""},
                    {"key": "SNMP_COMMUNITY", "description": "SNMP 只读团体名", "default": ""},
                    {"key": "LOCATION", "description": "设备位置", "default": ""},
                    {"key": "CONTACT", "description": "联系人邮箱", "default": "network-admin@company.com"},
                    {"key": "NTP_SERVER", "description": "NTP 服务器", "default": "10.0.0.1"},
                    {"key": "SYSLOG_SERVER", "description": "Syslog 服务器", "default": "10.0.0.2"},
                    {"key": "LOGGING_LEVEL", "description": "日志级别", "default": "warnings"},
                    {"key": "ACCESS_PORT_RANGE", "description": "接入端口范围", "default": "GigabitEthernet1/0/1-48"},
                    {"key": "UPLINK_PORT", "description": "上联端口", "default": "GigabitEthernet1/0/49"},
                    {"key": "BUSINESS_VLAN_LIST", "description": "业务 VLAN 列表（逗号分隔）", "default": "10,20,30"}
                ])
            },
            {
                "name": "汇聚交换机配置",
                "description": "适用于汇聚层交换机的配置模板，包含三层路由、VLAN 间路由等功能",
                "template_content": """!
! 配置模板：汇聚交换机配置
! 适用于：Cisco IOS 汇聚层交换机
! 创建时间：{{ now_str }}
!
version 15.2
service timestamps debug datetime msec
service timestamps log datetime msec
service password-encryption
!
hostname {{ HOSTNAME | default('SW-Distribution') }}
!
! AAA 认证
aaa new-model
aaa authentication login default local
aaa authentication enable default enable
aaa authorization exec default local
!
enable secret {{ ENABLE_SECRET | default('YourEnablePassword') }}
!
username {{ ADMIN_USERNAME | default('admin') }} privilege 15 secret {{ ADMIN_PASSWORD | default('YourAdminPassword') }}
!
line vty 0 15
 transport input ssh
 login authentication default
!
ip domain-name {{ DOMAIN_NAME | default('company.local') }}
crypto key generate rsa modulus 2048
ip ssh version 2
!
! VLAN 配置
{% for vlan in VLANS | default([]) %}
vlan {{ vlan.id }}
 name {{ vlan.name }}
{% endfor %}
!
! VLAN 接口（SVI）
{% for vlan in VLANS | default([]) %}
interface Vlan{{ vlan.id }}
 description {{ vlan.description | default('VLAN ' + vlan.id | string) }}
{% if vlan.ip and vlan.netmask %}
 ip address {{ vlan.ip }} {{ vlan.netmask }}
{% endif %}
{% if vlan.hsrp_group %}
 standby {{ vlan.hsrp_group }} ip {{ vlan.hsrp_virtual_ip }}
 standby {{ vlan.hsrp_group }} priority {{ vlan.hsrp_priority | default('100') }}
 standby {{ vlan.hsrp_group }} preempt
{% endif %}
 no shut
{% endfor %}
!
! 默认网关
ip routing
ip route 0.0.0.0 0.0.0.0 {{ DEFAULT_ROUTE | default('10.0.0.1') }}
!
! OSPF 配置（可选）
{% if ENABLE_OSPF | default('false') | lower == 'true' %}
router ospf 1
 router-id {{ OSPF_ROUTER_ID }}
{% for network in OSPF_NETWORKS | default([]) %}
 network {{ network.network }} {{ network.wildcard }} area {{ network.area | default('0') }}
{% endfor %}
{% endif %}
!
! SNMP 配置
snmp-server community {{ SNMP_COMMUNITY | default('YourSNMPCommunity') }} RO
snmp-server location {{ LOCATION | default('Not Set') }}
snmp-server contact {{ CONTACT | default('network-admin@company.com') }}
!
! NTP 配置
ntp server {{ NTP_SERVER | default('10.0.0.1') }}
!
! 与核心交换机互联端口
interface {{ CORE_UPLINK_PORT | default('TenGigabitEthernet1/1/1') }}
 description Uplink to Core
 switchport trunk allowed vlan {{ TRUNK_VLANS | default('10,20,30,100') }}
 switchport mode trunk
 no shut
!
! 与接入交换机互联端口
interface range {{ ACCESS_DOWNLINK_PORTS | default('GigabitEthernet1/0/1-48') }}
 switchport trunk allowed vlan {{ TRUNK_VLANS | default('10,20,30,100') }}
 switchport mode trunk
 spanning-tree guard root
 no shut
!
end""",
                "variables": json.dumps([
                    {"key": "HOSTNAME", "description": "设备主机名", "default": "SW-Distribution-01"},
                    {"key": "ENABLE_SECRET", "description": "Enable 密码", "default": ""},
                    {"key": "ADMIN_USERNAME", "description": "管理员用户名", "default": "admin"},
                    {"key": "ADMIN_PASSWORD", "description": "管理员密码", "default": ""},
                    {"key": "DOMAIN_NAME", "description": "域名", "default": "company.local"},
                    {"key": "DEFAULT_ROUTE", "description": "默认路由下一跳", "default": ""},
                    {"key": "ENABLE_OSPF", "description": "是否启用 OSPF", "default": "false"},
                    {"key": "OSPF_ROUTER_ID", "description": "OSPF Router ID", "default": ""},
                    {"key": "SNMP_COMMUNITY", "description": "SNMP 团体名", "default": ""},
                    {"key": "LOCATION", "description": "设备位置", "default": ""},
                    {"key": "CONTACT", "description": "联系人", "default": "network-admin@company.com"},
                    {"key": "NTP_SERVER", "description": "NTP 服务器", "default": "10.0.0.1"},
                    {"key": "CORE_UPLINK_PORT", "description": "上联核心端口", "default": "TenGigabitEthernet1/1/1"},
                    {"key": "ACCESS_DOWNLINK_PORTS", "description": "下联接入口范围", "default": "GigabitEthernet1/0/1-48"},
                    {"key": "TRUNK_VLANS", "description": "Trunk 允许的 VLAN", "default": "10,20,30,100"}
                ])
            },
            {
                "name": "核心交换机配置",
                "description": "适用于核心层交换机的配置模板，包含高级路由、冗余协议等",
                "template_content": """!
! 配置模板：核心交换机配置
! 适用于：Cisco IOS 核心层交换机
! 创建时间：{{ now_str }}
!
version 15.2
service timestamps debug datetime msec
service timestamps log datetime msec
service password-encryption
!
hostname {{ HOSTNAME | default('SW-Core') }}
!
aaa new-model
aaa authentication login default local
aaa authentication enable default enable
!
enable secret {{ ENABLE_SECRET | default('YourEnablePassword') }}
!
username {{ ADMIN_USERNAME | default('admin') }} privilege 15 secret {{ ADMIN_PASSWORD | default('YourAdminPassword') }}
!
line vty 0 15
 transport input ssh
 login authentication default
!
ip domain-name {{ DOMAIN_NAME | default('company.local') }}
crypto key generate rsa modulus 4096
ip ssh version 2
!
! VLAN 配置
{% for vlan in VLANS | default([]) %}
vlan {{ vlan.id }}
 name {{ vlan.name }}
{% endfor %}
!
! 三层 VLAN 接口
{% for vlan in VLANS | default([]) %}
interface Vlan{{ vlan.id }}
 description {{ vlan.description | default('VLAN ' + vlan.id | string) }}
{% if vlan.ip and vlan.netmask %}
 ip address {{ vlan.ip }} {{ vlan.netmask }}
{% endif %}
{% if vlan.hsrp_group %}
 standby {{ vlan.hsrp_group }} ip {{ vlan.hsrp_virtual_ip }}
 standby {{ vlan.hsrp_group }} priority {{ vlan.hsrp_priority | default('150') }}
 standby {{ vlan.hsrp_group }} preempt
{% endif %}
 no shut
{% endfor %}
!
! 默认路由
ip routing
ip route 0.0.0.0 0.0.0.0 {{ DEFAULT_ROUTE | default('10.0.0.1') }}
!
! OSPF 配置
router ospf 1
 router-id {{ OSPF_ROUTER_ID }}
 log-adjacency-changes
{% for network in OSPF_NETWORKS | default([]) %}
 network {{ network.network }} {{ network.wildcard }} area {{ network.area | default('0') }}
{% endfor %}
!
! SNMP 配置
snmp-server community {{ SNMP_COMMUNITY | default('YourSNMPCommunity') }} RO
snmp-server location {{ LOCATION | default('Data Center') }}
snmp-server contact {{ CONTACT | default('noc@company.com') }}
!
! NTP 配置
ntp master {{ NTP_STRATUM | default('3') }}
ntp server {{ NTP_SERVER | default('10.0.0.1') }}
!
! 与汇聚层互联端口
interface {{ DISTRIBUTION_PORT | default('TenGigabitEthernet1/1/1') }}
 description Downlink to Distribution
 switchport trunk allowed vlan {{ TRUNK_VLANS | default('all') }}
 switchport mode trunk
 no shut
!
end""",
                "variables": json.dumps([
                    {"key": "HOSTNAME", "description": "设备主机名", "default": "SW-Core-01"},
                    {"key": "ENABLE_SECRET", "description": "Enable 密码", "default": ""},
                    {"key": "ADMIN_USERNAME", "description": "管理员用户名", "default": "admin"},
                    {"key": "ADMIN_PASSWORD", "description": "管理员密码", "default": ""},
                    {"key": "DOMAIN_NAME", "description": "域名", "default": "company.local"},
                    {"key": "DEFAULT_ROUTE", "description": "默认路由下一跳", "default": ""},
                    {"key": "OSPF_ROUTER_ID", "description": "OSPF Router ID", "default": ""},
                    {"key": "SNMP_COMMUNITY", "description": "SNMP 团体名", "default": ""},
                    {"key": "LOCATION", "description": "设备位置", "default": "Data Center"},
                    {"key": "CONTACT", "description": "联系人", "default": "noc@company.com"},
                    {"key": "NTP_SERVER", "description": "主 NTP 服务器", "default": "10.0.0.1"},
                    {"key": "NTP_STRATUM", "description": "NTP 层级", "default": "3"},
                    {"key": "DISTRIBUTION_PORT", "description": "下联汇聚层端口", "default": "TenGigabitEthernet1/1/1"},
                    {"key": "TRUNK_VLANS", "description": "Trunk VLAN 范围", "default": "all"}
                ])
            },
            {
                "name": "无线控制器配置",
                "description": "适用于 Cisco 无线控制器 (WLC) 的基础配置模板",
                "template_content": """!
! 配置模板：无线控制器配置
! 适用于：Cisco Wireless LAN Controller
! 创建时间：{{ now_str }}
!
config system hostname {{ HOSTNAME | default('WLC-01') }}
!
! 管理接口
config interface address management {{ MGMT_IP }} {{ MGMT_NETMASK | default('255.255.255.0') }} {{ DEFAULT_GATEWAY }} {{ PHYSICAL_PORT | default('1') }}
!
! AP 管理器接口
config interface address ap-manager {{ AP_MGR_IP }} {{ MGMT_NETMASK | default('255.255.255.0') }} {{ PHYSICAL_PORT | default('1') }}
!
! VLAN 接口（用于不同 SSID）
{% for wlan_vlan in WLAN_VLANS | default([]) %}
config interface create {{ wlan_vlan.name }} {{ wlan_vlan.id }}
config interface address {{ wlan_vlan.name }} {{ wlan_vlan.ip }} {{ wlan_vlan.netmask }} {{ PHYSICAL_PORT | default('1') }}
{% endfor %}
!
! 默认路由
config network add default-gateway {{ DEFAULT_GATEWAY }}
!
! 认证服务器配置
config radius add {{ RADIUS_SERVER | default('10.0.0.10') }} {{ RADIUS_SECRET | default('radius_secret') }} 1812 0 {{ RADIUS_SERVER_INDEX | default('1') }}
!
! SNMP 配置
config snmp community read-only {{ SNMP_RO_COMMUNITY | default('public') }}
config snmp community read-write {{ SNMP_RW_COMMUNITY | default('private') }}
config snmp trap receiver add {{ SNMP_TRAP_SERVER | default('10.0.0.2') }} 162 version 2c {{ SNMP_COMMUNITY | default('public') }}
!
! NTP 配置
config time ntp interval {{ NTP_INTERVAL | default('1440') }}
config time ntp server add {{ NTP_SERVER | default('10.0.0.1') }}
!
! AP 组配置
{% for ap_group in AP_GROUPS | default([]) %}
config ap group add {{ ap_group.name }}
{% endfor %}
!
! SSID/WLAN 配置
{% for wlan in WLANS | default([]) %}
config wlan create {{ wlan.ssid }} {{ wlan.id }} {{ wlan.interface | default('management') }}
config wlan ssid {{ wlan.ssid }} {{ wlan.id }} {{ wlan.ssid_name }}
{% if wlan.security %}
config wlan security wpa {{ wlan.id }} {{ wlan.security }}
{% endif %}
config wlan enable {{ wlan.id }}
{% endfor %}
!
! 保存配置
save config
!
end""",
                "variables": json.dumps([
                    {"key": "HOSTNAME", "description": "控制器主机名", "default": "WLC-01"},
                    {"key": "MGMT_IP", "description": "管理接口 IP", "default": ""},
                    {"key": "MGMT_NETMASK", "description": "管理子网掩码", "default": "255.255.255.0"},
                    {"key": "DEFAULT_GATEWAY", "description": "默认网关", "default": ""},
                    {"key": "AP_MGR_IP", "description": "AP 管理器 IP", "default": ""},
                    {"key": "PHYSICAL_PORT", "description": "物理端口号", "default": "1"},
                    {"key": "RADIUS_SERVER", "description": "RADIUS 服务器 IP", "default": ""},
                    {"key": "RADIUS_SECRET", "description": "RADIUS 密钥", "default": ""},
                    {"key": "SNMP_RO_COMMUNITY", "description": "SNMP 只读团体名", "default": "public"},
                    {"key": "SNMP_RW_COMMUNITY", "description": "SNMP 读写团体名", "default": "private"},
                    {"key": "NTP_SERVER", "description": "NTP 服务器", "default": "10.0.0.1"}
                ])
            }
        ]

        # 批量创建模板
        for tmpl_data in default_templates:
            template = ConfigTemplate(**tmpl_data)
            db.add(template)
            logger.info(f"创建默认模板：{tmpl_data['name']}")

        db.commit()
        logger.info("默认配置模板初始化完成")

    except Exception as e:
        db.rollback()
        logger.error(f"初始化默认模板失败：{e}")
    finally:
        db.close()
