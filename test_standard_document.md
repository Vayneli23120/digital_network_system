# Cisco 交换机安全配置基线标准

## 文档信息
- **标准名称**: Cisco Switch Security Baseline
- **版本**: v2.0
- **发布日期**: 2024-01-15
- **适用范围**: Cisco Catalyst 系列交换机

---

## 1. 访问控制安全配置

### 1.1 特权模式密码保护
**要求等级**: 关键 (Critical)

所有网络设备必须配置特权模式密码保护。使用 enable secret 命令配置加密存储的特权密码，禁止使用 enable password 明文存储。

**检查要点**:
- 配置文件中必须存在 `enable secret` 配置项
- 密码长度不少于 8 位
- 密码应包含大小写字母、数字和特殊字符

**推荐配置**:
```
enable secret <strong-password>
```

**不符合时的风险**: 未配置特权密码时，任何用户可进入特权模式查看和修改配置。

---

### 1.2 SSH 远程访问配置
**要求等级**: 高 (High)

远程管理必须使用 SSH 协议，禁止使用 Telnet 等明文传输协议。SSH 版本必须设置为 Version 2。

**检查要点**:
- 配置中必须存在 `ip ssh version 2` 命令
- 禁止存在 `telnet` 相关配置
- SSH 访问端口建议修改为非默认端口

**推荐配置**:
```
ip domain-name company.local
crypto key generate rsa modulus 2048
ip ssh version 2
ip ssh port 2222
line vty 0 4
 transport input ssh
```

---

### 1.3 管理平面访问控制
**要求等级**: 高 (High)

必须配置 ACL 限制管理平面（VTY、SNMP、HTTP）的访问来源 IP 地址，仅允许授权管理网段访问。

**检查要点**:
- VTY 端口配置 access-class ACL
- SNMP 配置 ACL 限制访问来源
- 仅允许指定管理 IP 网段访问

**推荐配置**:
```
ip access-list standard MGMT-ACL
 permit 10.10.100.0 0.0.0.255
 deny any log
line vty 0 4
 access-class MGMT-ACL in
```

---

## 2. 密码与认证安全

### 2.1 密码加密服务
**要求等级**: 高 (High)

所有密码必须在配置文件中加密存储，启用密码加密服务。

**检查要点**:
- 配置中必须存在 `service password-encryption` 命令
- 所有用户密码和 enable 密码必须加密

**推荐配置**:
```
service password-encryption
```

---

### 2.2 本地用户认证
**要求等级**: 中 (Medium)

设备应配置本地用户账号进行认证，用户密码强度符合企业密码策略。

**检查要点**:
- 配置至少一个本地管理员账号
- 用户密码加密存储
- 建议配置密码强度策略

**推荐配置**:
```
username admin privilege 15 secret <strong-password>
aaa new-model
aaa authentication login default local
```

---

### 2.3 AAA 认证配置
**要求等级**: 中 (Medium)

企业网络设备应配置 AAA 认证，对接企业认证服务器（如 TACACS+ 或 RADIUS）。

**检查要点**:
- 配置 TACACS+ 或 RADIUS 服务器地址
- AAA 登录认证启用
- 配置 AAA 记录操作日志

**推荐配置**:
```
aaa new-model
tacacs-server host 10.10.100.10
tacacs-server key <shared-key>
aaa authentication login default group tacacs+ local
aaa authorization exec default group tacacs+ local
aaa accounting exec default start-stop group tacacs+
```

---

## 3. 端口安全配置

### 3.1 未使用端口管理
**要求等级**: 中 (Medium)

所有未使用的物理端口必须处于 shutdown 状态，防止未经授权的设备接入。

**检查要点**:
- 未使用的端口配置 shutdown
- 未使用端口应划入隔离 VLAN

**推荐配置**:
```
interface range GigabitEthernet 1/0/10 - 24
 shutdown
 switchport access vlan 999
 description UNUSED_PORT
```

---

### 3.2 端口安全配置
**要求等级**: 高 (High)

接入端口应启用端口安全功能，限制 MAC 地址学习数量，防止 MAC 泛洪攻击。

**检查要点**:
- 接入端口启用 port-security
- 设置最大 MAC 地址数量（建议 1-2）
- 配置违规处理方式（shutdown 或 restrict）

**推荐配置**:
```
interface GigabitEthernet 1/0/5
 switchport mode access
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation shutdown
```

---

### 3.3 DHCP Snooping 配置
**要求等级**: 高 (High)

接入交换机必须启用 DHCP Snooping，防止非法 DHCP 服务器攻击。

**检查要点**:
- 全局启用 DHCP Snooping
- 配置信任端口（上联端口）
- 非信任端口启用 DHCP Snooping

**推荐配置**:
```
ip dhcp snooping
ip dhcp snooping vlan 10,20,30
interface GigabitEthernet 1/0/1
 ip dhcp snooping trust
```

---

## 4. VLAN 安全配置

### 4.1 Native VLAN 安全
**要求等级**: 中 (Medium)

Trunk 端口的 Native VLAN 必须修改为非默认值（非 VLAN 1），防止 VLAN Hopping 攻击。

**检查要点**:
- Trunk 端口 Native VLAN 不等于 1
- Native VLAN 不应承载用户数据

**推荐配置**:
```
interface GigabitEthernet 1/0/1
 switchport trunk native vlan 999
```

---

### 4.2 VLAN 跳跃防护
**要求等级**: 中 (Medium)

启用 VLAN 跳跃防护功能，防止 DTP 攻击导致端口变为 Trunk。

**检查要点**:
- 接入端口禁止 DTP 协议
- 配置 switchport nonegotiate

**推荐配置**:
```
interface range GigabitEthernet 1/0/2 - 10
 switchport mode access
 switchport nonegotiate
```

---

## 5. 日志与监控配置

### 5.1 Syslog 日志配置
**要求等级**: 中 (Medium)

设备必须配置远程 Syslog 服务器，将操作日志和事件日志发送至日志服务器集中存储。

**检查要点**:
- 配置远程 Syslog 服务器 IP 地址
- 设置日志级别（建议 informational）
- 启用日志时间戳

**推荐配置**:
```
logging buffered 10000 informational
logging 10.10.100.20
logging source-interface Vlan100
service timestamps log datetime msec localtime
```

---

### 5.2 NTP 时间同步
**要求等级**: 中 (Medium)

所有网络设备必须配置 NTP 时间同步，确保日志时间准确性，便于事件追溯。

**检查要点**:
- 配置至少一个 NTP 服务器
- NTP 服务器应为企业内部 NTP 服务器

**推荐配置**:
```
ntp server 10.10.100.30 prefer
ntp server 10.10.100.31
```

---

### 5.3 SNMP 安全配置
**要求等级**: 高 (High)

SNMP 必须配置安全的 Community 字符串，禁止使用默认 Community（public/private），并配置 ACL 限制访问来源。

**检查要点**:
- SNMP Community 不能为 public 或 private
- 配置 SNMP ACL 限制访问来源
- 建议使用 SNMPv3 认证加密

**推荐配置**:
```
ip access-list standard SNMP-ACL
 permit 10.10.100.20
 deny any
snmp-server community <secure-string> RO SNMP-ACL
snmp-server location DataCenter-Rack-A1
```

---

## 6. 控制平面安全

### 6.1 控制平面保护
**要求等级**: 高 (High)

设备应配置 Control Plane Policing (CoPP)，限制控制平面的流量，防止控制平面泛洪攻击。

**检查要点**:
- 配置 CoPP 策略
- 限制 ICMP、SNMP、SSH 等管理流量速率

**推荐配置**:
```
class-map COPP-MANAGEMENT
 match access-group name MGMT-ACL
policy-map COPP-POLICY
 class COPP-MANAGEMENT
  police 10000 1000 conform-action transmit exceed-action drop
control-plane
 service-policy input COPP-POLICY
```

---

### 6.2 登录警告横幅
**要求等级**: 低 (Low)

设备应配置登录警告横幅（Banner），声明设备归属和访问授权。

**检查要点**:
- 配置 banner motd 警告信息
- 警告信息应包含授权声明

**推荐配置**:
```
banner motd #
*******************************************************************
* WARNING: This device is the property of Company Name.          *
* Unauthorized access is prohibited and will be prosecuted.      *
* All activities are logged and monitored.                       *
*******************************************************************
#
```

---

## 7. 交换机特定安全配置

### 7.1 BPDU Guard 配置
**要求等级**: 高 (High)

所有接入端口必须启用 BPDU Guard，防止非法交换机接入导致网络拓扑变更。

**检查要点**:
- PortFast 端口启用 BPDU Guard
- BPDU Guard 违规处理为 err-disable

**推荐配置**:
```
interface range GigabitEthernet 1/0/2 - 10
 spanning-tree portfast
 spanning-tree bpduguard enable
```

---

### 7.2 Root Guard 配置
**要求等级**: 中 (Medium)

关键网络位置端口应启用 Root Guard，防止非法交换机抢占 Root Bridge。

**检查要点**:
- 下联端口启用 Root Guard
- Root Guard 违规处理为 root-inconsistent

**推荐配置**:
```
interface GigabitEthernet 1/0/1
 spanning-tree guard root
```

---

### 7.3 动态 ARP 检测
**要求等级**: 高 (High)

接入交换机应启用 Dynamic ARP Inspection (DAI)，防止 ARP 欺骗攻击。

**检查要点**:
- VLAN 启用 DAI
- 配置信任端口
- 配置 ARP 检查验证

**推荐配置**:
```
ip arp inspection vlan 10,20
interface GigabitEthernet 1/0/1
 ip arp inspection trust
```

---

## 8. 合规性检查清单汇总

| 规则编号 | 规则名称 | 类别 | 严重程度 |
|---------|---------|------|---------|
| SEC-001 | 特权模式密码保护 | security | critical |
| SEC-002 | SSH Version 2 配置 | security | high |
| SEC-003 | 密码加密服务 | security | high |
| SEC-004 | 管理平面 ACL | security | high |
| SEC-005 | 未使用端口管理 | security | medium |
| SEC-006 | Native VLAN 安全 | security | medium |
| SEC-007 | Syslog 日志配置 | security | medium |
| SEC-008 | NTP 时间同步 | availability | medium |
| SEC-009 | 登录警告横幅 | compliance | low |
| SEC-010 | SNMP Community 安全 | security | critical |
| SEC-011 | 端口安全配置 | security | high |
| SEC-012 | DHCP Snooping | security | high |
| SEC-013 | BPDU Guard | security | high |
| SEC-014 | Dynamic ARP Inspection | security | high |
| SEC-015 | 控制平面保护 | security | high |

---

## 9. 参考标准

本配置基线参照以下行业标准制定：
- CIS Cisco IOS Benchmark
- NIST SP 800-53 Security Controls
- ISO/IEC 27001 Information Security Management
- PCI DSS Network Security Requirements