# Network Automation System - 架构文档

**版本**: v1.2.0  
**最后更新**: 2026-04-21

> v1.2.0 重大变更：新增 3 个 Service 层模块（template_service/dashboard_service/spare_part_service），重构 6 个路由为纯路由层。新增前端页面：设备发现、工具日志。测试覆盖：196 个用例，100% 通过。

---

## 一、系统架构图

### 1.1 整体架构 (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Network Automation System                      │
│                                    v1.0                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐        ┌─────────────────────┐                    │
│  │    Vue 3 Frontend   │        │    CLI Tool (Python)│                    │
│  │  (Element Plus UI)  │        │    (Click + Rich)   │                    │
│  │                     │        │                     │                    │
│  │  • Dashboard        │        │  • Device Mgmt      │                    │
│  │  • Device List      │        │  • Backup Ops       │                    │
│  │  • Backup Manager   │        │  • Fault Reports    │                    │
│  │  • Fault Tracker    │        │  • Stats & Reports  │                    │
│  │  • Config Deploy    │        │                     │                    │
│  └──────────┬──────────┘        └──────────┬──────────┘                    │
│             │                              │                                │
│             │ HTTP/REST API                │ Direct DB Access               │
│             │                              │                                │
│             ▼                              ▼                                │
│  ┌─────────────────────────────────────────────────────┐                   │
│  │              FastAPI Backend Server                  │                   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │                   │
│  │  │   Routers   │  │  Services   │  │   Models    │  │                   │
│  │  │  (API Layer)│  │(Business)   │  │  (SQLAlch)  │  │                   │
│  │  ├─────────────┤  ├─────────────┤  ├─────────────┤  │                   │
│  │  │ • devices   │  │• netmiko    │  │• Device     │  │                   │
│  │  │ • backups   │  │• deploy     │  │• Backup     │  │                   │
│  │  │ • faults    │  │• console    │  │• Fault      │  │                   │
│  │  │ • templates │  │• credential │  │• Template   │  │                   │
│  │  │ • deploy    │  │• email      │  │• Audit      │  │                   │
│  │  │ • console   │  └─────────────┘  └──────┬──────┘  │                   │
│  │  │ • logs      │                           │         │                   │
│  │  │ • dashboard │                           │         │                   │
│  │  │ • creds     │                           │         │                   │
│  │  └──────┬──────┘                           │         │                   │
│  │         │                                  │         │                   │
│  │         └──────────────────────────────────┘         │                   │
│  │                        │                             │                   │
│  │                        ▼                             │                   │
│  │              ┌─────────────────────┐                 │                   │
│  │              │  Database (SQLite)  │                 │                   │
│  │              │  • nas.db           │                 │                   │
│  │              └─────────────────────┘                 │                   │
│  │                                                      │                   │
│  └─────────────────────────────────────────────────────┘                   │
│                              │                                              │
│                              │ SSH/Console                                  │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────┐                   │
│  │           Network Devices (Cisco IOS)                │                   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐  │                   │
│  │  │ Core    │  │ Distrib │  │ Access  │  │ WLC    │  │                   │
│  │  │ Switch  │  │ Switch  │  │ Switch  │  │        │  │                   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └───┬────┘  │                   │
│  │       └─────────────┴────────────┴──────────┘       │                   │
│  └─────────────────────────────────────────────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 部署架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      Production Environment                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐        ┌──────────────┐                     │
│   │   Nginx      │        │   Uvicorn    │                     │
│   │ (Static/Web) │───────▶│  (FastAPI)   │                     │
│   │              │        │  Workers     │                     │
│   └──────────────┘        └──────┬───────┘                     │
│                                  │                              │
│                                  ▼                              │
│                        ┌──────────────┐                        │
│                        │    SQLite    │                        │
│                        │    nas.db    │                        │
│                        └──────────────┘                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、模块依赖关系

### 2.1 依赖关系图

```
main.py
│
├── config.py ◄──────┐
│       ▲            │
│       │            │
├── database.py ─────┤
│       │            │
│       ▼            │
├── models.py ───────┤ (所有模块都依赖配置)
│       │            │
│       ▼            │
├── exceptions.py    │
│                    │
├── db_init.py ──────┘
│
├── routers/
│   ├── devices.py ◄────┬──┐
│   ├── backups.py  ◄───┤  │
│   ├── faults.py   ◄───┤  │
│   ├── maintenance.py ◄┤  │
│   ├── deploy.py   ◄───┼──┼──┐
│   ├── console.py  ◄───┤  │  │
│   ├── templates.py    │  │  │
│   ├── credentials.py  │  │  │
│   └── logs.py         │  │  │
│                       │  │  │
└── services/           │  │  │
    ├── netmiko_service ◄──┘  │
    ├── deploy_service  ◄─────┤
    ├── console_service ◄─────┤
    ├── credential_service    │
    ├── email_service         │
    └── log_service           │
```

### 2.2 依赖矩阵

| 模块 | models | database | config | services | 外部库 |
|------|--------|----------|--------|----------|--------|
| routers/devices.py | ✓ | ✓ | ✓ | - | fastapi |
| routers/backups.py | ✓ | ✓ | ✓ | netmiko_service, credential_service | fastapi |
| routers/deploy.py | ✓ | ✓ | - | deploy_service, credential_service | fastapi, jinja2 |
| routers/faults.py | ✓ | ✓ | - | email_service | fastapi |
| services/netmiko_service.py | ✓ | ✓ | ✓ | - | netmiko, loguru |
| services/deploy_service.py | - | - | - | - | netmiko, jinja2, loguru |
| services/credential_service.py | - | - | ✓ | - | cryptography |
| services/email_service.py | - | - | ✓ | - | smtplib, loguru |

---

## 三、数据流图

### 3.1 设备备份流程

```
┌──────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   User   │────▶│   Backup    │────▶│ Netmiko Service │────▶│   Device    │
│ (Web/CLI)│     │    API      │     │                 │     │  (SSH)      │
└──────────┘     └─────────────┘     └────────┬────────┘     └──────┬──────┘
                                              │                      │
                                              ▼                      │
                                       ┌──────────────┐             │
                                       │ Get Running  │◄────────────┘
                                       │   Config     │
                                       └──────┬───────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │ Save to File │
                                       │ (MD5 Hash)   │
                                       └──────┬───────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │   SQLite     │
                                       │ BackupRecord │
                                       └──────────────┘
```

### 3.2 配置部署流程

```
┌──────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   User   │────▶│   Deploy    │────▶│ Template Render │────▶│   Device    │
│   (Web)  │     │    API      │     │   (Jinja2)      │     │  (SSH)      │
└──────────┘     └─────────────┘     └─────────────────┘     └──────┬──────┘
        │                                                           │
        │                    ┌──────────────┐                       │
        └───────────────────▶│   Preview    │                       │
                             │  (Dry Run)   │                       │
                             └──────────────┘                       │
                                                                    │
                              ┌─────────────────────────────┐       │
                              │ Config Diff (Current vs New)│◄──────┘
                              └─────────────────────────────┘
```

### 3.3 故障上报流程

```
┌──────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   User   │────▶│   Fault     │────▶│   Create Fault  │────▶│   SQLite    │
│   (Web)  │     │    API      │     │    Record       │     │ FaultRecord │
└──────────┘     └─────────────┘     └────────┬────────┘     └─────────────┘
                                              │
                                              ▼
                                       ┌──────────────┐
                                       │ Email Alert  │
                                       │  (Optional)  │
                                       └──────────────┘
```

---

## 四、API 路由清单

### 4.1 RESTful API 列表

| 方法 | 路径 | 描述 | 请求参数 | 响应 |
|------|------|------|----------|------|
| GET | /health | 健康检查 | - | status, version |
| | | | | |
| **设备管理** | | | | |
| GET | /api/devices | 设备列表 | status, role | items[] |
| POST | /api/devices | 创建设备 | {name, ip, ...} | id, message |
| GET | /api/devices/{id} | 设备详情 | - | device details |
| PUT | /api/devices/{id} | 更新设备 | {field: value} | message |
| DELETE | /api/devices/{id} | 删除设备 | - | message |
| GET | /api/devices/export | 导出设备 | - | Excel file |
| POST | /api/devices/import | 导入设备 | file | stats |
| | | | | |
| **备份管理** | | | | |
| POST | /api/backups/backup/{id} | 备份设备 | operator | success, backup_id |
| POST | /api/backups/batch | 批量备份 | device_ids[] | results[] |
| GET | /api/backups | 备份列表 | device_id, limit | items[] |
| GET | /api/backups/{id}/content | 备份内容 | - | content |
| GET | /api/backups/{id}/diff | 配置差异 | - | diff |
| | | | | |
| **故障管理** | | | | |
| GET | /api/faults | 故障列表 | device_id, status | items[] |
| POST | /api/faults | 创建故障 | {device_id, severity, ...} | id, fault_no |
| GET | /api/faults/{id} | 故障详情 | - | fault details |
| PUT | /api/faults/{id} | 更新故障 | {field: value} | message |
| DELETE | /api/faults/{id} | 删除故障 | - | message |
| | | | | |
| **维修管理** | | | | |
| GET | /api/maintenance | 维修列表 | device_id | items[] |
| POST | /api/maintenance | 创建维修 | {device_id, type, ...} | id, maint_no |
| GET | /api/maintenance/{id} | 维修详情 | - | maintenance details |
| PUT | /api/maintenance/{id} | 更新维修 | {field: value} | message |
| DELETE | /api/maintenance/{id} | 删除维修 | - | message |
| | | | | |
| **配置模板** | | | | |
| GET | /api/templates | 模板列表 | - | items[] |
| POST | /api/templates | 创建模板 | {name, content, ...} | id, message |
| GET | /api/templates/{id} | 模板详情 | - | template details |
| PUT | /api/templates/{id} | 更新模板 | {field: value} | message |
| DELETE | /api/templates/{id} | 删除模板 | - | message |
| POST | /api/templates/{id}/render | 渲染模板 | variables | content |
| | | | | |
| **配置部署** | | | | |
| POST | /api/deploy/preview | 预览部署 | {mode, target_devices, ...} | results[] |
| POST | /api/deploy/execute | 执行部署 | {mode, target_devices, ...} | results[] |
| GET | /api/deploy/compatible-variables | 兼容变量 | - | variables[] |
| | | | | |
| **凭证管理** | | | | |
| GET | /api/credentials | 凭证列表 | - | items[] |
| POST | /api/credentials | 创建凭证 | {name, username, password, ...} | id |
| GET | /api/credentials/{id} | 凭证详情 | - | credential details (decrypted) |
| PUT | /api/credentials/{id} | 更新凭证 | {field: value} | message |
| DELETE | /api/credentials/{id} | 删除凭证 | - | message |
| | | | | |
| **Console** | | | | |
| GET | /api/console/ports | 串口列表 | - | ports[] |
| POST | /api/console/auto-detect | 自动检测 | - | port or null |
| | | | | |
| **Dashboard** | | | | |
| GET | /api/dashboard/summary | 摘要数据 | - | devices, backups, faults, costs |
| GET | /api/dashboard/fault-trend | 故障趋势 | time_range, start_date, end_date | labels, values, by_severity |
| | | | | |
| **日志管理** | | | | |
| GET | /api/logs | 日志列表 | days, level, limit | items[] |
| GET | /api/logs/files | 日志文件 | days | files[] |
| GET | /api/logs/files/{name} | 文件内容 | lines, level | items[] |
| GET | /api/logs/search | 搜索日志 | keyword, days, level | items[] |
| WS | /api/logs/ws | 实时日志 | - | stream |
| POST | /api/logs/clear | 清理日志 | days | cleared count |

### 4.2 WebSocket 端点

| 端点 | 描述 | 消息格式 |
|------|------|----------|
| /api/logs/ws | 实时日志流 | JSON {timestamp, level, module, message} |

---

## 五、数据库表结构

### 5.1 ER 图 (ASCII)

```
┌─────────────────┐       ┌──────────────────┐
│     Device      │       │ CredentialGroup  │
├─────────────────┤       ├──────────────────┤
│ PK id           │       │ PK id            │
│    name         │       │    name          │
│    ip           │       │    description   │
│    model        │       │    username      │
│    serial_number│       │    password_enc  │
│    location     │       │    enable_passwd │
│    role         │       └──────────────────┘
│    status       │
│    credential_g │
│ FK credential_g │───────┐
│    created_at   │       │
└─────────────────┘       │
         │                │
         │ 1:N            │
         ▼                │
┌─────────────────┐       │
│  BackupRecord   │       │
├─────────────────┤       │
│ PK id           │       │
│ FK device_id    │───────┤
│    device_name  │       │
│    backup_file  │       │
│    md5_hash     │       │
│    has_change   │       │
│    operator     │       │
└─────────────────┘       │
                          │
         ┌────────────────┴────────┐
         │                         │
         ▼ 1:N                     ▼ 1:N
┌─────────────────┐       ┌──────────────────┐
│  FaultRecord    │       │ MaintenanceRecord│
├─────────────────┤       ├──────────────────┤
│ PK id           │       │ PK id            │
│ FK device_id    │       │ FK device_id     │
│    fault_no     │       │    maint_no      │
│    severity     │       │    maint_type    │
│    status       │       │    parts_cost    │
│    description  │       │    labor_cost    │
│    reporter     │       │    labor_hours   │
│    downtime_min │       │    vendor        │
└─────────────────┘       └──────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│  DevicePhoto    │
├─────────────────┤
│ PK id           │
│ FK device_id    │
│    photo_path   │
│    photo_type   │
│    uploader     │
└─────────────────┘

┌─────────────────┐
│ ConfigTemplate  │
├─────────────────┤
│ PK id           │
│    name         │
│    description  │
│    content      │
│    variables    │
│    created_at   │
└─────────────────┘

┌─────────────────┐
│    AuditLog     │
├─────────────────┤
│ PK id           │
│    operator     │
│    action       │
│    target_type  │
│    target_id    │
│    details      │
│    ip_address   │
└─────────────────┘
```

### 5.2 表结构详情

#### Device (设备表)
```sql
CREATE TABLE devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    ip VARCHAR(50),
    model VARCHAR(100),
    serial_number VARCHAR(100),
    location VARCHAR(200),
    role VARCHAR(50),  -- access/distribution/core
    status VARCHAR(50) DEFAULT 'online',
    purchase_date DATETIME,
    vendor VARCHAR(200),
    purchase_cost DECIMAL(10,2) DEFAULT 0,
    photo_dir VARCHAR(500),
    credential_group VARCHAR(50) DEFAULT 'default',
    last_backup_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### BackupRecord (备份记录表)
```sql
CREATE TABLE backup_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    backup_file VARCHAR(500) NOT NULL,
    file_size INTEGER,
    md5_hash VARCHAR(64),
    has_change BOOLEAN DEFAULT FALSE,
    backup_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    operator VARCHAR(100),
    device_name VARCHAR(100)
);
```

#### FaultRecord (故障记录表)
```sql
CREATE TABLE fault_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    fault_no VARCHAR(50) UNIQUE NOT NULL,
    fault_time DATETIME,
    description TEXT,
    severity VARCHAR(20),  -- critical/major/minor/warning
    downtime_minutes INTEGER DEFAULT 0,
    impact TEXT,
    resolution TEXT,
    cost DECIMAL(10,2) DEFAULT 0,
    reporter VARCHAR(100),
    status VARCHAR(20) DEFAULT 'open',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    device_name VARCHAR(100)
);
```

#### CredentialGroup (凭证组表)
```sql
CREATE TABLE credential_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(500),
    username VARCHAR(100) NOT NULL,
    password_encrypted VARCHAR(500) NOT NULL,
    enable_password_encrypted VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 六、关键技术决策说明

### 6.1 技术选型决策

| 决策项 | 选择 | 原因 | 权衡 |
|--------|------|------|------|
| **Web 框架** | FastAPI | 高性能、自动生成文档、类型提示 | 比 Flask/Django 新，生态较小 |
| **前端框架** | Vue 3 + Element Plus | 易学、组件丰富、中文文档好 | React 生态更大 |
| **数据库** | SQLite | 零配置、单文件、适合中小规模 | 不支持高并发、无用户权限 |
| **ORM** | SQLAlchemy 2.0 | 功能全面、支持异步 | 学习曲线较陡 |
| **设备连接** | Netmiko | Cisco 设备支持好、维护活跃 | 对非 Cisco 设备支持有限 |
| **模板引擎** | Jinja2 | 标准选择、功能强大 | - |
| **加密** | Fernet (cryptography) | AES-128-CBC、安全 | 需要密钥管理 |
| **日志** | Loguru | 比 logging 易用、功能丰富 | 额外依赖 |

### 6.2 架构设计决策

#### 1. 为什么选择 SQLite 而非 PostgreSQL/MySQL？

**原因**:
- 项目定位为中小规模网络环境 (< 1000 台设备)
- 零配置部署，单文件备份方便
- 开发运维简单，无需额外数据库服务器

**未来演进**:
- v1.3 计划支持 PostgreSQL 作为可选后端
- 通过 SQLAlchemy 抽象层，切换成本低

#### 2. 为什么使用同步数据库而非异步？

**原因**:
- SQLAlchemy 2.0 的异步支持相对较新
- 当前场景 I/O 等待主要在 SSH 操作
- 保持代码简单，避免复杂的异步上下文

**权衡**:
- 高并发场景可能受限
- 备份操作使用后台任务队列更合理

#### 3. 为什么密码使用应用层加密而非数据库层？

**原因**:
- SQLite 不支持原生加密字段
- 应用层加密更灵活，可切换算法
- 密钥可与数据库分离存储

**安全考虑**:
- 密钥不应存储在代码或版本控制中
- 生产环境建议使用密钥管理服务

#### 4. 前端为什么选择 Vue Options API 而非 Composition API？

**现状**:
- 当前代码混合使用两种风格
- Dashboard.vue 等组件使用 Composition API

**决策**:
- 新项目统一使用 Composition API
- 保持代码风格一致性

#### 5. 为什么 CLI 和 Web 服务共享数据库？

**原因**:
- CLI 工具是管理员的补充工具
- 共享数据库实现数据一致性
- 避免重复实现业务逻辑

**安全考虑**:
- CLI 应使用数据库级别的只读账号
- 敏感操作需要额外确认

### 6.3 安全设计决策

| 决策 | 实现 | 说明 |
|------|------|------|
| 密码加密 | Fernet (AES-128-CBC) | 对称加密，密钥需妥善保管 |
| CORS 配置 | 当前宽松 | 开发便利，生产需限制 |
| API 认证 | 未实现 | v1.1 计划添加 JWT |
| 会话管理 | 无状态 | 当前无需用户会话 |
| 输入验证 | 部分实现 | 使用 Pydantic 模型验证 |

### 6.4 扩展性设计

```
当前架构限制              扩展路径
─────────────────────────────────────────────────────
SQLite 并发限制    ──▶   PostgreSQL + 连接池

单进程部署         ──▶   Gunicorn/Uvicorn Workers

同步备份阻塞       ──▶   Celery + Redis 任务队列

单节点           ──▶    Docker + K8s 多副本

硬编码厂商支持    ──▶    Netmiko 驱动扩展
```

---

## 七、运行环境要求

### 7.1 后端依赖

```
Python >= 3.9
├── FastAPI >= 0.109.0
├── Uvicorn >= 0.27.0
├── SQLAlchemy >= 2.0.25
├── Netmiko >= 4.3.0
├── Pydantic >= 2.5.3
├── Cryptography >= 42.0.0
└── Loguru >= 0.7.2
```

### 7.2 前端依赖

```
Node.js >= 16
├── Vue 3 >= 3.4.0
├── Element Plus >= 2.5.4
├── Vue Router >= 4.2.5
├── Axios >= 1.6.5
└── ECharts >= 5.4.3
```

### 7.3 系统要求

| 资源 | 最小配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 50 GB | 100 GB |
| 网络 | 内网访问 | 公网访问需 HTTPS |

---

## 八、参考文档

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/)
- [Netmiko 文档](https://github.com/ktbyers/netmiko)
- [Vue 3 文档](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)

---

*文档版本: 1.0*  
*最后更新: 2026-04-14*
