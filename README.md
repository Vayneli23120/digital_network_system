# Network Automation System

Cisco IOS 交换机自动化备份与配置管理平台

**版本：1.3.0 | 最后更新：2026-04-22**

---

## 项目简介

Network Automation System 是一个基于 **FastAPI + Vue 3** 的网络设备自动化管理平台，面向 Cisco IOS 交换机运维场景，提供设备管理、配置备份、配置部署、故障管理、维修管理、备件管理、合规检查、设备发现等全链路运维能力。

### 核心指标

| 指标 | 数值 |
|------|------|
| 后端 API | 116 端点，19 个 feature 模块 |
| 服务层 | Feature-first 架构，19 个业务模块 |
| 前端页面 | 19 个 Vue 组件 |
| API 函数 | 80+ 前端 API 调用 |
| 测试用例 | **225 个**，100% 通过 |
| 数据库表 | 15 个模型 + Alembic 迁移 |
| DB 索引 | 14 个高频查询列索引 |

---

## 快速启动

```bash
# 方式一：使用启动脚本
python start.py

# 方式二：手动启动
# 1. 安装依赖
pip install -r requirements.txt

# 2. 准备配置
copy config.example.yaml config.yaml

# 3. 初始化数据库并导入测试数据
python init_db.py              # 初始化空数据库
python scripts/seed_data.py    # 导入测试数据（可选，用于演示）

# 4. 启动后端（终端 1）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. 启动前端（终端 2）
cd frontend && npm run dev
```

访问：
- 前端界面：http://localhost:3000
- API 文档：http://localhost:8000/docs

---

## 测试

```bash
# 运行所有测试
cd network-automation-system
.venv/bin/python -m pytest tests/ -v

# 当前状态：225 个测试用例，100% 通过
# 覆盖率：核心服务层 100% 覆盖
```

远程 PostgreSQL 双连接并发验证请严格按照
[远程测试机 PostgreSQL 并发测试手册](docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md)
执行。测试必须使用独立数据库 `nas_concurrency_test`，禁止连接业务库。

---

## 测试数据

项目包含测试数据生成脚本，可快速生成演示数据：

```bash
# 生成测试数据
python scripts/seed_data.py
```

**测试数据包含**：
- 12 台网络设备（2 核心 +3 汇聚 +7 接入）
- 60+ 条备份记录
- 4 条故障记录（含不同状态）
- 4 条维修记录（含不同类型）
- 3 个配置模板
- 审计日志若干

**注意**：`seed_data.py` 会清除现有数据后重新生成，生产环境请谨慎使用。

---

## 功能模块

| 功能 | 说明 |
|------|------|
| 设备管理 | 设备 CRUD、照片上传、批量导入导出 |
| 配置备份 | Netmiko SSH 自动备份、配置差异对比 |
| 配置部署 | Jinja2 模板渲染、批量部署到设备 |
| Console 自动化 | 串口连接、自动刷配置 |
| 故障管理 | 故障记录、停机统计、告警通知 |
| 维修管理 | 维修记录、成本统计 |
| Dashboard | ECharts 图表、运维指标展示 |
| 系统日志 | 实时日志查看、搜索过滤 |
| 配置模板 | Jinja2 模板管理 + 渲染 |
| 配置合规 | 10 项安全合规自动检查 |
| 设备发现 | Ping Sweep 网段扫描 + 自动识别 |
| 备件管理 | 备件 CRUD + 出入库 + 库存预警 + 统计 |
| 工具日志 | Netmiko/NAPALM/JIRA 执行日志追踪 |
| 用户认证 | JWT + RBAC 权限管理（可选启用） |
| 审计日志 | 操作审计追踪 |
| CLI 工具 | 命令行管理设备 |

---

## CLI 命令

```bash
# 设备管理
nas-cli device list
nas-cli device add -n SW-01 -i 192.168.1.1
nas-cli device show SW-01

# 备份管理
nas-cli backup run SW-01
nas-cli backup list

# 故障管理
nas-cli fault add -d SW-01 -s major -desc "端口故障"
nas-cli fault list

# 日志管理
nas-cli log list -l ERROR
nas-cli log search "backup"

# 统计信息
nas-cli stats
```

---

## 项目结构（Feature-first）

```
network-automation-system/
├── app/
│   ├── main.py                 # FastAPI 主程序
│   ├── cli.py                  # CLI 工具
│   ├── shared/                 # 公共基础设施
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── exceptions.py
│   │   ├── db_init.py
│   │   ├── cache.py
│   │   └── middleware/
│   ├── features/               # 19 个业务模块
│   │   ├── devices/            # router.py + device_service.py
│   │   ├── backups/            # router.py + backup/netmiko_service.py
│   │   ├── faults/             # router.py
│   │   ├── maintenance/        # router.py
│   │   ├── templates/          # router.py + template_service.py
│   │   ├── credentials/        # router.py + credential_service.py
│   │   ├── deploy/             # router.py + deploy_service.py
│   │   ├── console/            # router.py + console_service.py
│   │   ├── dashboard/          # router.py + dashboard_service.py
│   │   ├── logs/               # router.py + log_service.py
│   │   ├── auth/               # router.py
│   │   ├── permissions/        # router.py
│   │   ├── tool_logs/          # router.py + tool_executor.py
│   │   ├── spare_parts/        # router.py + spare_part_service.py
│   │   ├── spare_movements/    # router.py
│   │   ├── discovery/          # router.py + discovery_service.py
│   │   ├── alerts/             # router.py
│   │   ├── compliance/         # router.py + compliance_service.py
│   │   └── websocket/          # router.py
│   └── services/               # 跨领域服务
│       ├── email_service.py
│       ├── notification_service.py
│       ├── wechat_work_service.py
│       └── dingtalk_service.py
│
├── frontend/                   # Vue 3 前端 (19 页面 + 80+ API)
│   └── src/
│       ├── views/
│       ├── router/
│       └── api/
│
├── tests/                      # 225 个测试
├── migrations/                 # Alembic 数据库迁移
├── backups/ / logs/ / data/
│
├── config.yaml                 # 应用配置
├── .env.example                # 环境变量文档
├── requirements.txt            # Python 依赖
├── docker-compose.yml          # Docker 编排
├── Dockerfile                  # Docker 镜像
├── alembic.ini                 # Alembic 配置
├── CHANGELOG.md                # 变更日志
├── DEV_PLAN.md                 # 开发计划
└── README.md                   # 本文档
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| 前端框架 | Vue 3 + Element Plus |
| 数据库 | SQLite |
| ORM | SQLAlchemy |
| 数据库迁移 | Alembic |
| 网络设备连接 | Netmiko |
| 串口通信 | pyserial |
| 配置模板 | Jinja2 |
| 图表 | ECharts |
| 日志 | Loguru |
| 测试 | pytest + pytest-asyncio |
| 容器化 | Docker + Docker Compose |

---

## 系统要求

- Python 3.9+
- Node.js 16+
- Windows 10/11 或 Windows Server

---

## 文档说明

**保留的文档**：
- `README.md` - 项目说明（本文档）
- `CLI_USAGE.md` - CLI 工具详细使用指南
- `CHANGELOG.md` - 变更日志
- `DEV_PLAN.md` - 开发计划
- `CODE_REVIEW.md` - 代码审查报告

**其他历史文档**（BRD.md、CODEX_*.md 等）为项目开发过程中的过程文档，已归档至 `.docs-archive/` 目录。

---

## 开发路线 (Roadmap)

### v1.3.0 已完成 ✅

| 功能 | 说明 |
|------|------|
| Feature-first 架构 | 19 个业务模块 + shared 基础设施 |
| 测试覆盖 | 225 个测试，100% 通过 |
| 前端 | 19 页面 + 暗色主题 + 响应式 + Auth 拦截器 |
| 告警通知 | 企业微信/钉钉/邮件 |
| 性能优化 | 14 DB 索引 + API 分页 + 内存缓存 |
| 安全 | 限流中间件 + 安全头 + Request ID |
| 数据库 | Alembic 迁移 + 优雅关闭 |
| 开发规范 | .env.example + Pydantic 验证 |

### 短期目标 (v1.3+)

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 告警通知 | 企业微信/钉钉/邮件告警 | P1 |
| API 文档 | OpenAPI/Swagger 完善 | P2 |
| 前端优化 | 响应式布局/暗色主题 | P2 |
| 性能优化 | 查询优化/缓存/分页 | P2 |

### 中期目标 (v1.3 - v2.0)

| 功能 | 说明 |
|------|------|
| 多租户支持 | 多项目/多团队隔离 |
| PostgreSQL 支持 | 替代 SQLite，支持更大规模部署 |
| 配置版本控制 | Git 后端存储配置历史 |
| 可视化拓扑 | 网络拓扑自动发现与展示 |
| API Rate Limiting | API 限流与配额管理 |
| OAuth2 认证 | 对接企业 SSO |

### 长期规划 (v2.0+)

- **AI 运维助手**：基于 LLM 的故障诊断与配置建议
- **意图驱动网络**：自然语言描述需求，自动生成配置
- **多厂商支持**：扩展支持 Huawei、H3C、Juniper 等设备
- **云原生支持**：Kubernetes 部署、自动扩缩容
- **可观测性集成**：Prometheus + Grafana 监控集成

---

*版本：1.2.0 | 最后更新：2026-04-21*
sk-kimi-ECotntEbT5fel3ZOWlGZQMIDZgscAic7CzqRjImIgSI5Le063CE5yLJdd2nKnZt5