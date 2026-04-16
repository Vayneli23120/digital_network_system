# Changelog

## v1.1.0 (2026-04-14)

### 代码审查
- ✅ 完成完整代码审查报告 (`CODE_REVIEW.md`)
- 识别 15+ 个安全/质量问题
- 提供优先级排序的改进建议

### 架构文档
- ✅ 新增 `docs/ARCHITECTURE.md` — 系统架构、模块依赖、数据流、API 清单、数据库表结构

### 用户认证与权限管理 (预留)
- ✅ 新增 `User`, `Role`, `Permission`, `UserSession` 模型
- ✅ 新增 `app/routers/auth.py` — 登录/登出/用户 CRUD API
- ✅ 新增 `app/routers/permissions.py` — 角色和权限管理 API
- ✅ 新增 `app/middleware/auth_middleware.py` — JWT 认证中间件 + `require_auth` 装饰器
- ✅ 认证功能默认关闭，通过 `config.yaml` 的 `auth_enabled: true` 开启

### 工具执行日志系统
- ✅ 新增 `app/services/tool_executor.py` — 统一工具执行器
  - Netmiko SSH 命令执行（带实时日志）
  - NAPALM 网络设备操作
  - JIRA 工单创建/更新
- ✅ 新增 `app/routers/websocket.py` — WebSocket 实时日志推送
  - `/ws/logs` — 全部日志
  - `/ws/logs/{operation}` — 按操作订阅
- ✅ 新增 `app/routers/tool_logs.py` — 日志查询/搜索/统计 API
- ✅ 新增 `LogEntry` 模型 — 持久化存储
- ✅ `requirements.txt` 新增: napalm, jira

### 备件资产管理
- ✅ 新增 `SparePart`, `SparePartMovement` 模型
- ✅ 新增 `app/routers/spare_parts.py` — 备件 CRUD + 统计 API
- ✅ 新增 `app/routers/spare_movements.py` — 出入库操作 API
- ✅ 新增 `frontend/src/views/SpareParts.vue` — 备件管理前端页面
- ✅ 入库/出库操作 + 库存不足预警

### 配置合规检查 (Roadmap P0)
- ✅ 新增 `app/services/compliance_service.py` — 10 项合规检查
  - SEC-001: Enable Secret 密码
  - SEC-002: SSH 版本
  - SEC-003: 密码加密服务
  - SEC-004: 管理平面 ACL
  - SEC-005: 未使用端口处理
  - SEC-006: Native VLAN 配置
  - SEC-007: 日志服务器配置
  - SEC-008: NTP 时间同步
  - SEC-009: 登录警告横幅
  - SEC-010: SNMP Community 安全
- ✅ 新增 `app/routers/compliance.py` — 合规检查 API
- ✅ 新增 `frontend/src/views/Compliance.vue` — 合规检查前端页面

### Docker 容器化 (Roadmap P0)
- ✅ 新增 `Dockerfile` — 多阶段构建后端镜像
- ✅ 新增 `docker-compose.yml` — 一键部署后端 + 前端 + 数据卷

### 路由注册
- ✅ 更新 `app/main.py` — 注册所有新增路由
- ✅ 更新 `app/routers/__init__.py` — 导出新 router
- ✅ 更新 `frontend/src/router/index.js` — 注册新页面路由

### 新增依赖
```
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
napalm==4.1.0
jira==3.5.2
```

---

## v1.0.0 (初始版本)

- FastAPI + Vue 3 + SQLite 基础架构
- 设备管理、配置备份、故障管理、维修管理
- Dashboard、Console 自动化、配置部署
- CLI 工具 (nas-cli)
- 系统日志
