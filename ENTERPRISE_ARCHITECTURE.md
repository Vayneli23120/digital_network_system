# 企业级网络自动化平台 — 目标架构设计文档

**版本**: 2.0 目标架构  
**制定日期**: 2026-06-05  
**状态**: 指导性设计文档，供重构执行参考  
**当前版本现状分级**: L2.5（部门级可用，距企业级平台尚需系统性重构）

> 本文档描述目标状态（Target State）。所有架构决策均以企业级 Network Operations Center（NOC）+
> Network Configuration Management（NCM）+ AI-Ops 平台为目标，支持多厂商、多区域、多团队运营场景。

---

## 目录

1. [平台定位与约束](#1-平台定位与约束)
2. [技术栈决策](#2-技术栈决策)
3. [系统上下文图](#3-系统上下文图)
4. [容器架构图](#4-容器架构图)
5. [后端分层设计](#5-后端分层设计)
6. [数据库架构设计](#6-数据库架构设计)
7. [网络自动化引擎架构](#7-网络自动化引擎架构)
8. [安全架构](#8-安全架构)
9. [AI Assistant 架构](#9-ai-assistant-架构)
10. [前端架构](#10-前端架构)
11. [部署与基础设施](#11-部署与基础设施)
12. [可观测性设计](#12-可观测性设计)
13. [多厂商支持规范](#13-多厂商支持规范)
14. [关键非功能要求](#14-关键非功能要求)

---

## 1. 平台定位与约束

### 1.1 平台目标

| 核心能力 | 描述 |
|---|---|
| Network Device Management | 设备 CMDB、生命周期、资产台账、拓扑感知 |
| Configuration Backup | 多厂商自动化备份、版本对比、基线快照 |
| Configuration Compliance | 规则引擎、基线对比、合规评分、报告 |
| Configuration Deployment | 模板化、变更审批、灰度、回滚、审计 |
| Network Change Management | 变更工单、风险评估、变更窗口、审批链 |
| Fault Management | 事件采集、告警聚合、根因分析、ITSM 联动 |
| Device Inventory | 资产属性、备件管理、保修、生命周期 |
| AI-Assisted Troubleshooting | 故障根因分析、配置异常检测、操作建议 |
| AI-Assisted Config Analysis | 合规建议、安全风险、配置优化 |
| Network Operations Automation | 工作流引擎、定时任务、事件驱动自动化 |

### 1.2 目标设备支持

| 厂商 | OS | Netmiko driver | NAPALM driver |
|---|---|---|---|
| Cisco | IOS | cisco_ios | ios |
| Cisco | IOS-XE | cisco_ios | ios |
| Cisco | NX-OS | cisco_nxos | nxos_ssh |
| Aruba | ArubaOS-Switch | aruba_os | ❌ 使用 Netmiko |
| Aruba | ArubaOS-CX | aruba_aoscx | ❌ 使用 Netmiko |
| Huawei | VRP | huawei | huawei（社区版） |
| H3C | Comware | hp_comware | ❌ 使用 Netmiko |
| Fortinet | FortiOS | fortinet | ❌ 使用 Netmiko |

### 1.3 架构约束

- 后端 Python 3.11+，FastAPI 0.111+，SQLAlchemy 2.x，Alembic
- 数据库 PostgreSQL 15+（主存储），Redis 7+（缓存/任务队列）
- 前端 React 18+，TypeScript 5+，Ant Design 5+（目标，当前阶段保持 Vue 3 过渡）
- 认证 JWT（RS256 非对称算法），RBAC + ABAC 权限模型
- 所有设备操作异步化，禁止在 API 请求线程中同步执行设备命令
- 所有变更操作必须有审计记录，不可删除的 append-only 审计日志

---

## 2. 技术栈决策

### 2.1 完整技术栈

| 层 | 组件 | 版本 | 决策理由 |
|---|---|---|---|
| **前端** | React | 18+ | 企业级生态、TypeScript 原生、社区最大 |
| | TypeScript | 5+ | 类型安全、重构安全网、IDE 支持 |
| | Ant Design | 5+ | 企业 B 端设计体系，组件最完整 |
| | Zustand | 4+ | 状态管理，轻量 |
| | React Query | 5+ | 服务端状态、缓存、同步 |
| | Vite | 5+ | 构建工具 |
| | Vitest | 1+ | 单元测试 |
| **API 网关** | Nginx | 1.26+ | 反向代理、SSL 终止、静态文件 |
| **后端** | FastAPI | 0.111+ | 异步、自动 OpenAPI、类型驱动 |
| | Python | 3.11+ | asyncio 成熟、生态完整 |
| | Pydantic | 2.x | 数据验证、序列化 |
| | SQLAlchemy | 2.x | ORM，异步支持 |
| | Alembic | 1.13+ | 数据库迁移 |
| **任务队列** | Celery | 5.3+ | 分布式任务、重试、优先级队列 |
| | Redis | 7+ | Celery broker + result backend + 缓存 |
| **数据库** | PostgreSQL | 15+ | 并发、JSON、全文检索、pgvector |
| | pgvector | 0.7+ | AI 向量检索 |
| **网络自动化** | Netmiko | 4.3+ | SSH 连接多厂商 |
| | NAPALM | 4.1+ | 标准化接口（支持厂商） |
| | Paramiko | 3.4+ | 低层 SSH |
| | TextFSM + NTC-Templates | 最新 | 输出结构化解析 |
| **AI** | LiteLLM | 最新 | 统一 LLM API 代理，OpenAI Compatible |
| | LangChain | 0.2+ | RAG 流程编排 |
| | pgvector | 0.7+ | 向量存储后端 |
| | Google ADK | 最新 | Agent 执行框架（已有，保留） |
| **通知** | 企业微信/钉钉/邮件 | 已有，保留 |
| **可观测性** | Structlog | 24+ | 结构化日志 |
| | OpenTelemetry | 1.x | Trace/Metric 标准 |
| | Prometheus + Grafana | 最新 | 指标采集与可视化 |
| **容器** | Docker | 26+ | 镜像标准 |
| | Docker Compose | v2 | 本地/中小规模部署 |

### 2.2 前端迁移策略

> 当前前端为 Vue 3 + Element Plus + JavaScript，目标为 React + TypeScript + Ant Design。  
> **迁移策略：新旧并行，模块级迁移**。短期保持 Vue 3 运行，按业务模块逐步迁移到 React+TS。
> 迁移顺序建议：AI 分析中心 → 设备管理 → 变更管理 → 其余模块。

---

## 3. 系统上下文图

```mermaid
C4Context
    title Network Automation Platform — System Context

    Person(netops, "NetOps Engineer", "日常运维、配置变更、故障处理")
    Person(netarch, "Network Architect", "合规策略制定、AI 分析审阅")
    Person(itmanager, "IT Manager", "报表查看、审批")

    System(nas, "NAS Platform", "企业级网络自动化平台")

    System_Ext(cisco, "Cisco Devices", "IOS/IOS-XE/NX-OS")
    System_Ext(aruba, "Aruba Devices", "ArubaOS-Switch/CX")
    System_Ext(huawei, "Huawei Devices", "VRP")
    System_Ext(h3c, "H3C Devices", "Comware")
    System_Ext(fortinet, "Fortinet", "FortiOS")
    System_Ext(itsm, "ITSM/Jira", "工单系统")
    System_Ext(ldap, "LDAP/AD", "企业目录")
    System_Ext(llm, "LLM APIs", "OpenAI/DeepSeek/Anthropic")
    System_Ext(smtp, "SMTP/WeChat/DingTalk", "通知渠道")

    Rel(netops, nas, "使用 Web UI / CLI")
    Rel(netarch, nas, "使用 Web UI")
    Rel(itmanager, nas, "使用 Web UI（只读）")
    Rel(nas, cisco, "SSH/NETCONF")
    Rel(nas, aruba, "SSH")
    Rel(nas, huawei, "SSH/NETCONF")
    Rel(nas, h3c, "SSH")
    Rel(nas, fortinet, "SSH/REST API")
    Rel(nas, itsm, "API 集成")
    Rel(nas, ldap, "LDAP 认证（可选）")
    Rel(nas, llm, "AI API 调用")
    Rel(nas, smtp, "告警通知")
```

---

## 4. 容器架构图

```mermaid
C4Container
    title NAS Platform — Container Diagram

    Person(user, "用户", "Web/CLI")

    Container(nginx, "Nginx", "反向代理", "SSL 终止 / 静态文件 / 路由")
    Container(frontend, "Frontend", "React+TS+Ant Design", "SPA 应用")
    Container(api, "API Server", "FastAPI", "REST API / WebSocket / BFF")
    Container(worker, "Celery Worker", "Python", "设备操作异步任务执行")
    Container(beat, "Celery Beat", "Python", "定时任务调度")
    ContainerDb(pg, "PostgreSQL", "主数据库", "业务数据 + pgvector")
    ContainerDb(redis, "Redis", "缓存 + 队列", "Celery broker / 结果 / 缓存")
    Container(ai_svc, "AI Service", "LiteLLM + LangChain", "RAG + Agent + Tool 调用")

    Rel(user, nginx, "HTTPS")
    Rel(nginx, frontend, "静态文件")
    Rel(nginx, api, "HTTP 反代 /api /ws")
    Rel(api, pg, "SQLAlchemy")
    Rel(api, redis, "任务提交 / 缓存读写")
    Rel(api, ai_svc, "AI 分析请求")
    Rel(worker, pg, "SQLAlchemy")
    Rel(worker, redis, "任务接收 / 结果写回")
    Rel(beat, redis, "定时任务触发")
    Rel(ai_svc, pg, "pgvector 向量检索")
    Rel(ai_svc, redis, "会话缓存")
```

---

## 5. 后端分层设计

### 5.1 目标分层模型

```
app/
├── api/                        # API 层（路由、请求/响应序列化、依赖注入）
│   ├── v1/                     # 版本化路由
│   │   ├── devices.py
│   │   ├── backups.py
│   │   ├── changes.py          # 变更管理（新）
│   │   ├── compliance.py
│   │   ├── faults.py
│   │   ├── inventory.py
│   │   ├── ai.py
│   │   ├── jobs.py             # 作业监控（新）
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── settings.py
│   │   └── websocket.py
│   └── deps.py                 # 共用 Depends 函数
│
├── domain/                     # 领域层（业务规则，不依赖 HTTP/DB）
│   ├── devices/
│   │   ├── models.py           # 领域对象（dataclass / Pydantic）
│   │   ├── services.py         # 业务服务
│   │   └── events.py           # 领域事件
│   ├── changes/
│   ├── compliance/
│   ├── faults/
│   ├── inventory/
│   └── ai/
│
├── application/                # 应用层（用例编排，协调 domain + infra）
│   ├── backup_usecase.py
│   ├── deploy_usecase.py
│   ├── compliance_usecase.py
│   ├── fault_usecase.py
│   └── ai_usecase.py
│
├── infrastructure/             # 基础设施层
│   ├── db/
│   │   ├── connection.py       # 连接池管理
│   │   ├── models.py           # SQLAlchemy ORM 模型
│   │   ├── repositories/       # 数据访问对象（Repository Pattern）
│   │   │   ├── device_repo.py
│   │   │   ├── backup_repo.py
│   │   │   ├── fault_repo.py
│   │   │   └── ...
│   │   └── migrations/         # Alembic 迁移
│   ├── cache/
│   │   └── redis_client.py
│   ├── automation/             # 设备自动化驱动
│   │   ├── driver_registry.py  # 统一驱动注册表
│   │   ├── drivers/
│   │   │   ├── base.py         # 抽象基类
│   │   │   ├── cisco_ios.py
│   │   │   ├── cisco_nxos.py
│   │   │   ├── huawei_vrp.py
│   │   │   ├── h3c_comware.py
│   │   │   ├── aruba_os.py     # 新增
│   │   │   └── fortinet_os.py  # 新增
│   │   └── connection_pool.py  # SSH 连接池
│   ├── ai/
│   │   ├── llm_client.py       # LiteLLM 封装
│   │   ├── rag_engine.py       # RAG 检索引擎
│   │   ├── vector_store.py     # pgvector 操作
│   │   ├── tool_registry.py    # AI 工具注册表
│   │   └── agents/             # Agent 实现
│   ├── notifications/          # 通知渠道
│   └── itsm/                   # JIRA/ITSM 集成
│
├── tasks/                      # Celery 任务定义
│   ├── backup_tasks.py
│   ├── deploy_tasks.py
│   ├── compliance_tasks.py
│   ├── discovery_tasks.py
│   ├── health_tasks.py
│   └── scheduled_tasks.py      # Beat 定时任务
│
├── core/                       # 核心基础设施（无业务逻辑）
│   ├── config.py               # 应用配置
│   ├── security.py             # 认证/加密工具
│   ├── exceptions.py           # 异常体系
│   ├── logging.py              # 结构化日志
│   ├── middleware/
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   ├── correlation.py      # Request ID / Trace ID
│   │   └── audit.py            # 审计中间件
│   └── celery_app.py           # Celery 实例
│
└── main.py                     # FastAPI 应用入口
```

### 5.2 作业（Job）统一模型

**所有设备操作必须通过统一 Job 模型执行，禁止 API 请求线程直接执行设备命令。**

```python
# 作业类型枚举
class JobType(str, Enum):
    BACKUP = "backup"
    DEPLOY = "deploy"
    COMPLIANCE_SCAN = "compliance_scan"
    DISCOVERY = "discovery"
    HEALTH_CHECK = "health_check"
    COMMAND_EXEC = "command_exec"
    CONFIG_COLLECT = "config_collect"

# 作业状态枚举
class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    PARTIAL = "partial"  # 批量作业部分成功
```

---

## 6. 数据库架构设计

### 6.1 迁移到 PostgreSQL 的核心变更

| 变更点 | SQLite 现状 | PostgreSQL 目标 |
|---|---|---|
| 连接字符串 | `sqlite:///./data/nas.db` | `postgresql+asyncpg://user:pass@host:5432/nas` |
| 连接池 | `StaticPool`（单文件） | `AsyncAdaptedQueuePool`（连接池） |
| 迁移配置 | `render_as_batch=True` | 删除此配置，原生 DDL |
| JSON 列 | `Text`（手动序列化） | `JSONB`（原生，可查询） |
| 枚举类型 | `String` + 应用层校验 | `ENUM` 类型 |
| 时间戳 | `DateTime`（无时区） | `TIMESTAMP WITH TIME ZONE` |
| 全文检索 | 不支持 | `tsvector` + GIN 索引 |
| 向量检索 | 不支持 | `pgvector` extension |
| 并发写入 | WAL 模式，单写锁 | 行级锁，MVCC |

### 6.2 核心数据模型设计

```mermaid
erDiagram
    DEVICES {
        serial id PK
        varchar(100) name UK
        inet ip
        varchar(50) vendor
        varchar(50) os_type
        varchar(100) model
        varchar(100) serial_number
        varchar(200) location
        varchar(50) role
        varchar(50) device_type
        integer ssh_port
        varchar(50) credential_group_id FK
        varchar(50) deployment_status
        varchar(50) reachability
        timestamp last_reachability_check
        integer reachability_latency_ms
        integer health_score
        varchar(20) risk_level
        varchar(20) lifecycle_stage
        timestamp warranty_expire
        jsonb modules
        jsonb custom_attributes
        timestamp created_at
        timestamp updated_at
        tsvector search_vector
    }

    CREDENTIAL_GROUPS {
        serial id PK
        varchar(100) name UK
        varchar(500) description
        varchar(100) username
        text password_encrypted
        text enable_password_encrypted
        text ssh_key_encrypted
        varchar(20) auth_method
        timestamp created_at
        timestamp updated_at
    }

    BACKUP_RECORDS {
        serial id PK
        integer device_id FK
        varchar(500) backup_file
        bigint file_size
        varchar(64) md5_hash
        boolean has_change
        varchar(500) diff_file
        timestamp backup_time
        varchar(100) operator
        varchar(20) backup_type
        varchar(20) status
        text error_message
        timestamp created_at
    }

    JOBS {
        uuid id PK
        varchar(50) job_type
        varchar(50) status
        integer device_id FK
        integer[] device_ids
        jsonb parameters
        jsonb result
        varchar(100) operator
        varchar(100) celery_task_id
        integer progress_percent
        text log_output
        varchar(200) error_message
        timestamp started_at
        timestamp completed_at
        timestamp created_at
        timestamp updated_at
    }

    CHANGE_REQUESTS {
        serial id PK
        varchar(50) change_no UK
        varchar(200) title
        text description
        varchar(20) change_type
        varchar(20) status
        varchar(20) risk_level
        integer[] affected_device_ids
        jsonb config_payload
        integer template_id FK
        jsonb variables
        varchar(100) requestor
        varchar(100) approver
        timestamp scheduled_window_start
        timestamp scheduled_window_end
        timestamp approved_at
        timestamp executed_at
        uuid job_id FK
        text rollback_config
        timestamp created_at
        timestamp updated_at
    }

    FAULT_RECORDS {
        serial id PK
        varchar(50) fault_no UK
        integer device_id FK
        varchar(20) severity
        varchar(20) status
        varchar(50) fault_type
        varchar(200) title
        text description
        text impact
        text resolution
        varchar(100) assigned_to
        integer maintenance_id FK
        text ai_root_cause
        text ai_recommendation
        decimal ai_confidence
        timestamp fault_time
        timestamp resolved_at
        timestamp closed_at
        timestamp created_at
        timestamp updated_at
    }

    COMPLIANCE_POLICIES {
        serial id PK
        varchar(100) name UK
        text description
        varchar(50) policy_type
        varchar(50) severity
        jsonb rules
        varchar(50)[] applicable_vendors
        boolean is_active
        timestamp created_at
        timestamp updated_at
    }

    COMPLIANCE_RESULTS {
        serial id PK
        integer device_id FK
        integer policy_id FK
        varchar(20) result_status
        text evidence
        text remediation
        uuid job_id FK
        timestamp checked_at
        timestamp created_at
    }

    AI_KNOWLEDGE_DOCUMENTS {
        uuid id PK
        varchar(100) doc_type
        varchar(200) title
        text content
        jsonb metadata
        vector(1536) embedding
        integer device_id FK
        timestamp indexed_at
        timestamp created_at
    }

    AI_ANALYSIS_RECORDS {
        uuid id PK
        varchar(50) analysis_type
        varchar(50) target_type
        integer target_id
        text prompt
        text response
        jsonb parsed_result
        varchar(100) model_name
        varchar(50) ai_provider
        integer input_tokens
        integer output_tokens
        decimal cost_usd
        integer processing_time_ms
        boolean success
        text error_message
        varchar(100) operator
        timestamp created_at
    }

    AUDIT_LOGS {
        bigserial id PK
        varchar(100) operator
        varchar(50) action
        varchar(50) resource_type
        integer resource_id
        jsonb before_state
        jsonb after_state
        inet ip_address
        varchar(100) user_agent
        varchar(36) request_id
        boolean success
        text error_message
        timestamp created_at
    }

    DEVICES ||--o{ BACKUP_RECORDS : "has"
    DEVICES ||--o{ JOBS : "targets"
    DEVICES ||--o{ FAULT_RECORDS : "has"
    DEVICES ||--o{ COMPLIANCE_RESULTS : "evaluated by"
    DEVICES ||--o{ AI_KNOWLEDGE_DOCUMENTS : "indexed as"
    JOBS ||--o{ CHANGE_REQUESTS : "executes"
    FAULT_RECORDS ||--o{ AI_ANALYSIS_RECORDS : "analyzed"
    COMPLIANCE_POLICIES ||--o{ COMPLIANCE_RESULTS : "applies"
```

### 6.3 关键索引策略

```sql
-- 设备全文检索
CREATE INDEX idx_devices_search_vector ON devices USING GIN(search_vector);

-- 设备名称/IP 快速查找
CREATE INDEX idx_devices_ip ON devices (ip);
CREATE INDEX idx_devices_vendor_role ON devices (vendor, role);
CREATE INDEX idx_devices_reachability ON devices (reachability, last_reachability_check);

-- 备份记录时间序列
CREATE INDEX idx_backup_records_device_time ON backup_records (device_id, backup_time DESC);
CREATE INDEX idx_backup_records_time ON backup_records (backup_time DESC);

-- 作业查询
CREATE INDEX idx_jobs_status_type ON jobs (status, job_type);
CREATE INDEX idx_jobs_device_id ON jobs (device_id);
CREATE INDEX idx_jobs_created_at ON jobs (created_at DESC);

-- 故障管理
CREATE INDEX idx_fault_records_status ON fault_records (status, severity, fault_time DESC);
CREATE INDEX idx_fault_records_device ON fault_records (device_id, created_at DESC);

-- 合规结果
CREATE INDEX idx_compliance_results_device ON compliance_results (device_id, checked_at DESC);

-- 审计日志（按月分区）
CREATE TABLE audit_logs_y2026m06 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');

-- AI 向量检索
CREATE INDEX idx_ai_knowledge_embedding ON ai_knowledge_documents 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_ai_knowledge_type ON ai_knowledge_documents (doc_type, device_id);
```

### 6.4 数据库连接池配置

```python
# infrastructure/db/connection.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool

engine = create_async_engine(
    settings.database.url,                    # postgresql+asyncpg://...
    poolclass=AsyncAdaptedQueuePool,
    pool_size=10,                             # 基础连接数
    max_overflow=20,                          # 溢出连接数
    pool_timeout=30,                          # 获取连接超时
    pool_recycle=1800,                        # 30 分钟回收连接
    pool_pre_ping=True,                       # 连接健康检查
    connect_args={
        "server_settings": {"application_name": "nas-api"},
        "command_timeout": 30,
    },
    echo=settings.app.debug,
)
```

---

## 7. 网络自动化引擎架构

### 7.1 统一驱动契约

所有厂商驱动必须实现以下抽象基类：

```python
# infrastructure/automation/drivers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class DeviceConnectionParams:
    host: str
    username: str
    password: str
    enable_password: Optional[str] = None
    ssh_port: int = 22
    timeout: int = 30
    session_timeout: int = 60

@dataclass
class CommandResult:
    command: str
    output: str
    success: bool
    error: Optional[str] = None
    parsed: Optional[Dict] = None  # TextFSM/NTC 解析结果

@dataclass
class ConfigDiff:
    added_lines: List[str]
    removed_lines: List[str]
    raw_diff: str
    has_changes: bool

class BaseDeviceDriver(ABC):
    """所有厂商驱动的抽象基类。实现此接口可自动注册到驱动注册表。"""
    
    VENDOR: str            # 厂商标识，如 "cisco", "huawei"
    OS_TYPES: List[str]    # 支持的 OS 类型列表
    NETMIKO_DRIVER: str    # Netmiko device_type
    NAPALM_DRIVER: Optional[str] = None  # NAPALM driver，None 表示仅用 Netmiko
    SUPPORTS_ENABLE_MODE: bool = True
    SHOW_RUN_COMMAND: str = "show running-config"
    SAVE_CONFIG_COMMAND: str = "write memory"
    CONFIG_MODE_COMMAND: str = "configure terminal"
    EXIT_CONFIG_MODE: str = "end"

    @abstractmethod
    def get_running_config(self, connection) -> str: ...

    @abstractmethod
    def get_device_facts(self, connection) -> Dict: ...

    @abstractmethod
    def deploy_config_lines(self, connection, commands: List[str], dry_run: bool = False) -> Dict: ...

    @abstractmethod
    def save_config(self, connection) -> bool: ...

    @abstractmethod
    def get_interfaces(self, connection) -> List[Dict]: ...

    def parse_output(self, command: str, output: str) -> Optional[Dict]:
        """默认使用 NTC-Templates 解析，子类可重写"""
        ...
```

### 7.2 驱动注册表

```python
# infrastructure/automation/driver_registry.py
# 所有 BaseDeviceDriver 子类自动注册，无需手动维护映射表
from infrastructure.automation.drivers.base import BaseDeviceDriver
from typing import Type, Dict

class DriverRegistry:
    _registry: Dict[str, Type[BaseDeviceDriver]] = {}
    
    @classmethod
    def register(cls, driver_class: Type[BaseDeviceDriver]):
        cls._registry[driver_class.VENDOR] = driver_class
        for os_type in driver_class.OS_TYPES:
            cls._registry[os_type] = driver_class
    
    @classmethod
    def get(cls, vendor: str) -> Type[BaseDeviceDriver]:
        return cls._registry.get(vendor.lower(), CiscoIOSDriver)  # 默认 Cisco
    
    @classmethod
    def list_vendors(cls) -> Dict[str, str]:
        return {k: v.VENDOR for k, v in cls._registry.items()}
```

### 7.3 作业执行流程

```mermaid
sequenceDiagram
    participant API as API Server
    participant Redis as Redis Queue
    participant Worker as Celery Worker
    participant Driver as Device Driver
    participant Device as Network Device
    participant DB as PostgreSQL

    API->>DB: 创建 Job 记录（status=pending）
    API->>Redis: 提交 Celery 任务（job_id）
    API-->>Client: 返回 job_id（202 Accepted）

    Redis->>Worker: 分发任务
    Worker->>DB: 更新 Job status=running
    Worker->>DB: 读取设备信息、凭证
    Worker->>Driver: 获取厂商驱动实例
    Driver->>Device: SSH 连接
    Device-->>Driver: 连接成功
    Driver->>Device: 执行命令
    Device-->>Driver: 命令输出
    Driver->>Driver: TextFSM 解析
    Driver-->>Worker: 执行结果
    Worker->>DB: 写入执行结果
    Worker->>DB: 更新 Job status=success/failed
    Worker->>Redis: 推送 WebSocket 事件

    Client->>API: GET /api/v1/jobs/{job_id} 轮询
    API-->>Client: Job 状态与结果
```

---

## 8. 安全架构

### 8.1 认证与授权

```mermaid
flowchart TD
    REQ[HTTP 请求] --> CORS[CORS 校验\nallowlist 配置]
    CORS --> RATELIMIT[限流中间件\n每分钟/每小时]
    RATELIMIT --> AUTHMW[Auth 中间件]
    AUTHMW --> WHITELIST{公开路径?\n/health /docs /login}
    WHITELIST -->|是| HANDLER[业务处理]
    WHITELIST -->|否| JWTVERIFY[JWT 验证\nRS256 算法]
    JWTVERIFY --> JWTVALID{Token 有效?}
    JWTVALID -->|否| 401[401 Unauthorized]
    JWTVALID -->|是| TOKENREVOKE{Token 已撤销?\nRedis 黑名单}
    TOKENREVOKE -->|已撤销| 401
    TOKENREVOKE -->|未撤销| RBAC[RBAC 角色检查]
    RBAC --> ABAC[ABAC 属性检查\n如 only own devices]
    ABAC --> HANDLER
    HANDLER --> AUDIT[审计中间件\n记录 AuditLog]
    AUDIT --> RESP[HTTP 响应]
```

### 8.2 安全配置基线（必须符合）

| 项目 | 要求 | 当前现状 | 修复优先级 |
|---|---|---|---|
| CORS | 仅允许白名单 origin | `allow_origins=["*"]` ❌ | P0 |
| JWT 算法 | RS256（非对称） | HS256 ⚠️ | P1 |
| JWT 默认 Secret | 启动时校验，生产禁止默认值 | 默认值无强制校验 ⚠️ | P0 |
| 认证默认状态 | 生产强制开启 | `auth_enabled: False` ❌ | P0 |
| Token 前端存储 | httpOnly Cookie 或内存 | localStorage ❌ | P1 |
| 密码哈希 | bcrypt/argon2，rounds≥12 | bcrypt（已有，保留） ✅ | - |
| 设备凭证存储 | AES-256-GCM + 应用层密钥 | Fernet 加密（已有）✅ | - |
| HTTPS | 生产强制 TLS 1.2+ | 未强制 ⚠️ | P0 |
| Security Headers | X-Frame、HSTS 等 | 已有 ✅ | - |
| 命令黑名单 | 高危命令阻止（reload/erase） | 无 ❌ | P1 |
| 审计日志 | 不可删除，至少保留 1 年 | 可删除 ❌ | P1 |
| 设备密码日志 | 日志中不可出现明文凭证 | 未校验 ⚠️ | P1 |

### 8.3 设备操作安全策略

```python
# 高危命令黑名单（所有设备操作前必须校验）
DANGEROUS_COMMANDS = {
    "reload", "erase startup-config", "format", "write erase",
    "delete", "factory-reset", "restore factory", "reset",
    "crypto key zeroize", "no service password-encryption",
    "no ip ssh", "no aaa", "shutdown" # interface shutdown 除外需特殊处理
}

# 变更前必须通过 AI 风险评估（当 AI 服务可用时）
# 评估维度：影响范围、配置合规性、回滚可行性
```

---

## 9. AI Assistant 架构

### 9.1 AI 平台分层

```mermaid
flowchart TB
    subgraph "AI Assistant 工作台 (前端)"
        CHAT[对话式运维助手]
        CFG_ANALYZE[配置分析面板]
        FAULT_AI[故障 AI 分析]
        CHANGE_AI[变更风险评估]
    end

    subgraph "AI Service 层"
        API[AI API Handler]
        AGENT[Agent Executor\nGoogle ADK]
        RAG[RAG Engine\nLangChain]
        TOOL_REG[Tool Registry\nMCP 工具注册表]
    end

    subgraph "知识层"
        VEC_DB[(pgvector\n向量索引)]
        CFG_IDX[设备配置索引]
        FAULT_IDX[历史故障知识库]
        SOP_IDX[SOP / 最佳实践]
        VENDOR_IDX[厂商设备手册]
    end

    subgraph "工具执行层"
        T1[get_device_config\n获取实时配置]
        T2[run_compliance_check\n执行合规检查]
        T3[get_fault_history\n查询故障历史]
        T4[simulate_config_change\n变更仿真]
        T5[get_interface_status\n接口状态]
        T6[search_knowledge_base\n知识库检索]
    end

    subgraph "LLM 层"
        LITELLM[LiteLLM 代理]
        GPT4O[OpenAI GPT-4o]
        DS[DeepSeek]
        CLAUDE[Anthropic Claude]
    end

    CHAT --> API
    CFG_ANALYZE --> API
    FAULT_AI --> API
    CHANGE_AI --> API
    API --> AGENT
    AGENT --> RAG
    AGENT --> TOOL_REG
    RAG --> VEC_DB
    VEC_DB --> CFG_IDX
    VEC_DB --> FAULT_IDX
    VEC_DB --> SOP_IDX
    VEC_DB --> VENDOR_IDX
    TOOL_REG --> T1
    TOOL_REG --> T2
    TOOL_REG --> T3
    TOOL_REG --> T4
    TOOL_REG --> T5
    TOOL_REG --> T6
    AGENT --> LITELLM
    LITELLM --> GPT4O
    LITELLM --> DS
    LITELLM --> CLAUDE
```

### 9.2 RAG 知识库体系

| 知识类型 | 内容 | 更新策略 | 向量维度 |
|---|---|---|---|
| 设备配置快照 | 最近 N 次备份配置文本 | 每次备份触发 | 1536 |
| 历史故障记录 | 故障描述 + 根因 + 解决方案 | 故障关闭时 | 1536 |
| 运维 SOP | 标准操作手册 | 人工上传 | 1536 |
| 厂商文档 | 命令参考、限制说明 | 人工上传/爬取 | 1536 |
| 合规规则库 | 配置检查规则说明 | 策略变更时 | 1536 |
| 变更记录 | 历史变更内容 + 效果 | 变更完成时 | 1536 |

### 9.3 AI 工具治理规范

```python
# 每个 AI Tool 必须声明以下属性
@dataclass
class AITool:
    name: str               # tool 唯一名称
    description: str        # 供 LLM 理解的描述
    parameters: dict        # JSON Schema 参数定义
    requires_permission: str  # 执行需要的权限（如 "device:read"）
    is_readonly: bool       # 是否为只读操作（只读不需审批）
    is_destructive: bool    # 是否为高危操作（需双人确认）
    timeout_seconds: int    # 执行超时
    rate_limit: int         # 每分钟最大调用次数
```

### 9.4 AI 分析质量保证

- 所有 AI 分析结果必须附带置信度分数（0.0-1.0）
- 高危建议（如 shutdown 接口、删除配置）必须经人工确认才可执行
- AI 工具调用结果必须记录在 `ai_analysis_records` 中，包含输入/输出/耗时/成本
- 提供"无 AI 降级模式"，当 LLM 不可用时平台功能不受影响

---

## 10. 前端架构

### 10.1 目标前端结构（React + TypeScript + Ant Design）

```
frontend/
├── src/
│   ├── app/                    # 应用全局
│   │   ├── App.tsx
│   │   ├── router.tsx          # React Router 路由配置
│   │   ├── store/              # Zustand 全局状态
│   │   │   ├── auth.ts
│   │   │   ├── notifications.ts
│   │   │   └── ui.ts
│   │   └── providers.tsx       # React Query, Theme, Auth Provider
│   │
│   ├── api/                    # API 层（React Query hooks）
│   │   ├── client.ts           # Axios 实例 + 拦截器
│   │   ├── devices.ts          # useDevices, useDevice, useMutateDevice
│   │   ├── backups.ts
│   │   ├── changes.ts
│   │   ├── compliance.ts
│   │   ├── faults.ts
│   │   ├── jobs.ts
│   │   └── ai.ts
│   │
│   ├── pages/                  # 页面（按业务域）
│   │   ├── dashboard/
│   │   ├── inventory/          # 设备管理 + 资产台账
│   │   │   ├── DeviceList.tsx
│   │   │   ├── DeviceDetail.tsx
│   │   │   └── DeviceDiscovery.tsx
│   │   ├── changes/            # 变更管理
│   │   │   ├── ChangeList.tsx
│   │   │   ├── ChangeCreate.tsx
│   │   │   └── ChangeDetail.tsx
│   │   ├── compliance/
│   │   ├── faults/
│   │   ├── backup/
│   │   ├── deploy/
│   │   ├── ai/                 # AI 工作台
│   │   │   ├── AICopilot.tsx   # 对话式助手
│   │   │   ├── FaultAnalysis.tsx
│   │   │   └── ConfigAnalysis.tsx
│   │   ├── settings/
│   │   └── auth/
│   │
│   ├── components/             # 通用组件
│   │   ├── layout/
│   │   ├── device/
│   │   ├── diff/               # 配置差异对比
│   │   ├── job-monitor/        # 作业监控面板
│   │   └── ai/                 # AI 专用组件
│   │
│   ├── hooks/                  # 通用 hooks
│   ├── utils/                  # 工具函数
│   └── types/                  # TypeScript 类型定义
│       ├── device.ts
│       ├── job.ts
│       ├── change.ts
│       └── api.ts
```

### 10.2 认证 Token 存储策略

生产环境使用 **httpOnly Cookie** 存储 accessToken，避免 XSS 泄漏：

```typescript
// 不应该: localStorage.setItem('accessToken', token)
// 应该: 服务端 Set-Cookie: accessToken=...; HttpOnly; Secure; SameSite=Strict
// 前端只需发送请求时自动携带 Cookie，无需手动管理 token

// refreshToken 同样使用 httpOnly Cookie
// 前端通过 /api/v1/auth/me 接口判断是否已登录
```

---

## 11. 部署与基础设施

### 11.1 生产部署架构

```mermaid
flowchart LR
    subgraph "DMZ / 入口层"
        LB[负载均衡器\nNginx/HAProxy]
    end

    subgraph "应用层"
        API1[API Server 1\nFastAPI + Uvicorn]
        API2[API Server 2\nFastAPI + Uvicorn]
        W1[Celery Worker 1\n设备操作]
        W2[Celery Worker 2\n备份任务]
        W3[Celery Worker 3\nAI 分析]
        BEAT[Celery Beat\n定时调度]
    end

    subgraph "数据层"
        PG_MASTER[(PostgreSQL\nMaster)]
        PG_REPLICA[(PostgreSQL\nReplica - 只读)]
        REDIS_C[(Redis Cluster\nBroker + Cache)]
        MINIO[(MinIO\n备份文件存储)]
    end

    LB --> API1
    LB --> API2
    API1 --> PG_MASTER
    API2 --> PG_MASTER
    API1 --> PG_REPLICA
    API2 --> PG_REPLICA
    API1 --> REDIS_C
    W1 --> PG_MASTER
    W1 --> REDIS_C
    W1 --> MINIO
    W2 --> MINIO
    BEAT --> REDIS_C
```

### 11.2 docker-compose.yml 目标结构

```yaml
version: '3.9'

services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: nas
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d nas"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/nas
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SECRET_KEY_RS256_PRIVATE: ${SECRET_KEY_RS256_PRIVATE}
      AUTH_ENABLED: "true"
      CORS_ALLOWED_ORIGINS: ${CORS_ALLOWED_ORIGINS}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build: .
    command: celery -A app.core.celery_app worker -Q device_ops,backups,ai_tasks -c 4
    depends_on:
      - api
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/nas
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0

  beat:
    build: .
    command: celery -A app.core.celery_app beat --scheduler redbeat.RedBeatScheduler
    depends_on:
      - redis

  frontend:
    build: ./frontend
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      api:
        condition: service_healthy

volumes:
  pg_data:
  redis_data:
```

---

## 12. 可观测性设计

### 12.1 日志规范

所有日志必须为 JSON 结构化格式：

```json
{
  "timestamp": "2026-06-05T12:00:00.000Z",
  "level": "INFO",
  "service": "nas-api",
  "version": "2.0.0",
  "trace_id": "abc123",
  "request_id": "req-xyz",
  "operator": "admin",
  "message": "Device backup completed",
  "device_id": 42,
  "device_name": "SW-CORE-01",
  "job_id": "uuid-...",
  "duration_ms": 1234
}
```

**严禁出现在日志中**：密码、SSH 密钥、API Key、Token、完整配置文件中的 enable secret。

### 12.2 核心 Metrics

| 指标 | 类型 | 标签 |
|---|---|---|
| `nas_job_total` | Counter | job_type, status |
| `nas_job_duration_seconds` | Histogram | job_type |
| `nas_device_reachable_total` | Gauge | vendor, role |
| `nas_backup_success_rate` | Gauge | vendor |
| `nas_ai_request_total` | Counter | provider, model, analysis_type |
| `nas_ai_cost_usd_total` | Counter | provider, model |
| `nas_api_request_duration_seconds` | Histogram | method, endpoint, status_code |

---

## 13. 多厂商支持规范

### 13.1 每个厂商驱动必须实现的功能矩阵

| 功能 | Cisco IOS/XE | Cisco NX-OS | Aruba OS | Huawei VRP | H3C Comware | Fortinet |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 获取 running-config | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 获取设备 facts | ✅(NAPALM) | ✅(NAPALM) | ✅(Netmiko+TextFSM) | ✅(Netmiko+TextFSM) | ✅(Netmiko+TextFSM) | ✅(Netmiko+TextFSM) |
| 部署配置（行级） | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 部署配置（NAPALM） | ✅ | ✅ | ❌ | ⚠️ 社区 | ❌ | ❌ |
| 配置回滚 | ✅(NAPALM) | ✅(NAPALM) | ❌ 快照还原 | ❌ 手动 | ❌ 手动 | ❌ 手动 |
| 接口状态 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ARP 表 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 路由表 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 日志收集 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 合规检查 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 13.2 Aruba 驱动实现要点

```python
class ArubaOSDriver(BaseDeviceDriver):
    VENDOR = "aruba"
    OS_TYPES = ["aruba", "aruba_os", "aruba-os"]
    NETMIKO_DRIVER = "aruba_os"
    NAPALM_DRIVER = None  # NAPALM 不支持 Aruba
    SUPPORTS_ENABLE_MODE = True
    SHOW_RUN_COMMAND = "show running-config"
    SAVE_CONFIG_COMMAND = "write memory"
    CONFIG_MODE_COMMAND = "configure terminal"
    # ArubaOS-Switch 特定：部署时需要处理 "no aaa port-access" 等命令顺序依赖
```

### 13.3 Fortinet 驱动实现要点

```python
class FortinetDriver(BaseDeviceDriver):
    VENDOR = "fortinet"
    OS_TYPES = ["fortinet", "fortigate", "fortios"]
    NETMIKO_DRIVER = "fortinet"
    NAPALM_DRIVER = None
    SUPPORTS_ENABLE_MODE = False  # FortiOS 无 enable 模式
    SHOW_RUN_COMMAND = "show full-configuration"  # 或 "show"
    SAVE_CONFIG_COMMAND = "execute cfg save"
    CONFIG_MODE_COMMAND = "config system global"  # FortiOS 配置模式按资源
    # 注意：Fortinet 使用层级式配置，不同于 Cisco 的平面式
    # 部署时需要解析配置层级，逐段 config ... end
```

---

## 14. 关键非功能要求

| 指标 | 要求 |
|---|---|
| API 响应时间（P95） | < 200ms（非设备操作） |
| 单次备份作业超时 | 120 秒 |
| 批量备份并发设备数 | 可配置，默认 10，最大 50 |
| 批量部署并发设备数 | 可配置，默认 5，最大 20 |
| 作业结果保留时间 | 90 天 |
| 审计日志保留时间 | 365 天，不可删除 |
| 配置备份文件保留 | 每设备最多 30 个版本，最长 365 天 |
| JWT 访问令牌有效期 | 8 小时 |
| JWT 刷新令牌有效期 | 7 天 |
| 系统可用性目标 | 99.5%（单节点），99.9%（双节点） |
| 设备规模支持 | 单实例支持 500+ 设备，水平扩展支持 5000+ |
| AI 分析超时 | 120 秒，超时返回降级响应而非报错 |

---

*本文档是架构评审输出，由 GitHub Copilot (Claude Sonnet 4.6) 生成于 2026-06-05。*  
*配套文档：REFACTORING_PLAN.md（分阶段重构执行计划）*
