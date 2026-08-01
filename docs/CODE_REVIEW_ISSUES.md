# 代码审查问题清单

> 审查日期：2026-07-28 · 审查范围：`app/`（约 45k 行）+ `frontend/src/`（约 62k 行）+ `migrations/` + `scripts/` + `tests/`
> 审查方式：只读通读，未修改任何代码。行号基于提交 `de02d1f`。

图例：
- `[已复核]` — 直接读代码 / grep / 执行命令确认，非推测
- `[待验证]` — 静态阅读得出，建议实机复现后再动手
- 优先级：**P0** 会崩溃或造成安全事故 · **P1** 明显缺陷、错误数据或性能风险 · **P2** 可维护性

---

## 批次一 · 必然故障（每次调用都失败）　✅ 已完成（2026-07-29）

- [x] **P0** `deploy/deploy_service.py:155` — `deploy_config()` 引用未定义的 `device`（函数签名只有 `connection/config/dry_run`），Netmiko 引擎部署必然 NameError。异常被 `:377` 的宽泛 except 吞成"部署失败"，现象是失败但看不出原因。调用链：`deploy/router.py:659/673/722/736` → `deploy_to_device()` → `deploy_config()`。`[已复核]`
  → 修复：`deploy_config()` 增加 `device: Optional[dict] = None` 形参并由 `deploy_to_device()` 显式透传
- [x] **P0** `deploy/deploy_service.py:162` — 上一条导致 `validate_commands()` 永不执行；全仓仅此一处调用命令守卫，**危险命令白名单实际从未生效**。`[已复核]`
  → 修复：随上一条恢复；`tests/test_batch1_regressions.py` 用 `reload` / `write erase` 两个用例锁死"被拦截时不下发任何命令"
- [x] **P0** `devices/router.py:1123` — `total_aps` 未初始化就 `+=`（`:1119` 初始化了其它四个累加器），`POST /monitor/discover-neighbors-all` 只要有一台设备发现成功就 500。`[已复核]`
- [x] **P0** `websocket/router.py:92,103,120,128` — 使用 `tool_executor` 但文件内无该导入，`/ws/logs` accept 后立即 NameError。`[已复核]`
- [x] **P0** `deploy/napalm_service.py:456` — `NapalmStreamService` 全程用 `asyncio.*`，但该文件没有 `import asyncio`（同目录 `cli_stream_service.py:10`、`deploy_stream_service.py:5`、`router.py:3` 都导了）。`[已复核]`
- [x] **P0** `ai/router.py:247,260` — 读 `fault.title`，但 `FaultRecord`（`shared/models.py:139-215`）没有 `title` 字段，只有 `fault_no` / `description`。`GET /api/ai/faults/{id}/analysis` 必然 AttributeError。`[已复核]`
  → 修复：改用 `description[:50] or fault_no`，与 `workflow/triggers/triggers.py:79` 的既有取法保持一致
- [x] **P0** `tasks/backup_tasks.py:67` — 调 `NetmikoService.backup_device()`，该类（`backups/netmiko_service.py:19`）没有此方法，备份实现是模块级函数 `backup_device_config`（`:122`）。Celery 备份任务每次 AttributeError + 重试 2 次。`[已复核]`
  → 同一函数还有两处连带故障：① `CredentialService(db).get_credentials_for_device(device)` 两者都不存在（`CredentialService.__init__` 不接受参数）；② 备份成功后不落 `BackupRecord`，异步备份不会出现在备份列表里
  → 修复：新增 `credentials/credential_service.py::resolve_device_credentials(db, device)` 统一凭证解析；任务改调 `backup_device_config` 并落 `BackupRecord` + 更新 `device.last_backup_time`
- [x] **P0** `backups/router.py:124` — `logger.warning` 在 Git 提交失败分支被调用，但该文件的 `from loguru import logger` 在 `:204`（另一个函数内），此处 NameError 会让已成功的备份返回 500。`[已复核]`
- [x] **P0**（执行中新发现）`app/tasks/__init__.py:39` — 导入时用 `Path.write_text()` 生成含中文 docstring 的占位模块，Windows 默认编码 cp1252/GBK 下抛 `UnicodeEncodeError`，**整个 `app.tasks` 包无法导入**（Celery 任务与相关测试全部失败）；Linux 上则静默生成未纳入版本控制的源文件。`[已复核]`
  → 修复：删除导入期副作用，`deploy_tasks.py` / `notification_tasks.py` / `scheduled_tasks.py` 改为仓库内的真实占位文件
- [x] **P1**（执行中新发现）`tasks/backup_tasks.py` 的 RAG 索引分支取 `result["config_content"]`，而 `backup_device_config` 从不返回该字段 → **RAG 索引从未触发**。`[已复核]`
  → 修复：改为从落盘的备份文件读取，避免把整份配置写进 `Job.result_json` 造成行膨胀
- [x] **P2**（执行中新发现）`.gitignore` 缺 `data/*.db-shm` / `data/*.db-wal`（`database.py` 对 SQLite 启用了 WAL），这两个临时文件会出现在 `git status` 里。`[已复核]`

**完成判定**：✅ `ruff check app scripts migrations tests` → All checks passed（F821 归零）；✅ 新增 `tests/test_batch1_regressions.py` 15 项全过，其中 3 项直接验证命令守卫生效；✅ 全量 pytest 失败集合与修复前**逐条完全一致**（64 条既存失败，见批次七），未引入新失败，通过数 355 → 370。
**未验证**：真实设备上的 Netmiko 部署与 `/ws/logs`、NAPALM 流式部署仍需实机确认（本地无设备）。

---

## 批次二 · 安全

> **执行计划（2026-07-29 与业主确认）**
> 认证目标形态：**SSO（Microsoft Entra ID / OIDC）+ 本地账号**双通道，MFA 由 Entra 侧负责。
> 环境事实：服务器在公司内网，**全公司含异地站点均可访问**，无公网入口；测试环境 `auth_enabled=false`。
> 因此"内网"不等于"可信"，暴露面是千人量级，先做与 SSO 无关的收口，再等应用注册落地。
>
> | 步骤 | 内容 | 状态 |
> |---|---|---|
> | 1 | 凭证接口停止回传明文 + 挂权限 + 管理员账号 CLI | ✅ 2026-07-29 |
> | 2 | 登录页双入口 + 后端 SSO 端点预留 | ✅ 2026-07-29 |
> | 3 | 统一身份解析、删 `X-User` 旁路、`auth_enabled` 收窄为开发旁路 | ✅ 2026-08-01 |
> | 4 | 按危险度给写接口挂权限：alerts → deploy → devices → logs → 其余 | 🟡 4A alerts 已完成（2026-08-01） |
> | 5 | 会话级 SSH 凭证（用时输入一次）+ 高危操作二次确认 + 加密密钥独立 | ⬜ |
> | 6 | OIDC 真接（填 tenant/client/secret + 服务器出站白名单） | ⬜ 等 IT |
>
> 步骤 5 必须排在步骤 3、4 之后：会话凭证的安全性完全依赖"会话属于谁可信"，
> 在 `X-User` 可伪造的情况下先做会话凭证会比现状更糟。

### 步骤 3 验收测试清单（✅ 2026-08-01 完成）

- [x] `auth_enabled=true` 时，请求仅携带 `X-User: Admin` 必须返回 401，不能产生管理员身份
- [x] 有效本地账号 access token 能解析为统一 principal，并能访问受保护依赖
- [x] 缺失、过期、伪造、refresh 类型 token 统一返回 401，并带 `WWW-Authenticate: Bearer`
- [x] `/api/devices` 不再属于认证白名单；未登录访问时返回 401
- [x] 公共端点仅精确放行登录、SSO status/login/callback、health/ready 与 API 文档；相似前缀不能绕过
- [x] `auth_enabled=false` 只有同时设置 `app.debug=true` 才启用开发旁路；非 debug 配置不得自动获得超管身份
- [x] 开发旁路中的 `X-User` 只能识别已存在且启用的用户；请求未携带该头时使用明确的 developer 占位身份
- [x] 通知与部署审计统一使用 principal，不再各自解码 JWT 或默认回退为 `Admin` / `system`
- [x] 前端正式请求不再发送可伪造的 `X-User` 请求头
- [x] SSO `/status`、`/login`、`/callback` 仍可匿名访问且不泄漏密钥
- [x] `ruff check app scripts migrations tests` 零告警；新增步骤 3 聚焦回归测试全部通过
- [x] 全量 pytest 失败集合不超过既存基线；若环境问题导致无法全跑，必须记录未验证项

- [x] **P0** `shared/config.py:176` — `auth_enabled` 默认 `False`，此时 `require_permission` / `require_permissions` / `require_superuser`（`shared/dependencies.py:150,190,232`）全部直接 return 放行，整套 RBAC 在默认配置下无效。需明确定位：默认改 `True`，或承认它只是 UI 偏好。`[已复核]`
  → 修复（步骤 3）：认证中间件改为始终注册；只有 `auth_enabled=false` **且** `app.debug=true` 才允许开发旁路。其余配置即使误关认证也拒绝受保护 API。`AUTH_ENABLED` / `APP_DEBUG` / `JWT_SECRET` / `CORS_ALLOWED_ORIGINS` 环境变量现已真正映射到配置，Docker 默认 `AUTH_ENABLED=true`、`APP_DEBUG=false`。
- [x] **P0** `auth/router.py:370-395` — `auth_enabled=False` 时登录对任意用户名/密码返回 token（密码错误也落到占位 token 分支）。`[已复核]`
  → 修复（步骤 3）：占位登录仅限显式 debug 开发旁路；`auth_enabled=false + debug=false` 返回 503，不再签发占位 token。
- [ ] **P0** 后端接口级鉴权缺失 — 全仓仅 `deploy/router.py:1319`（删除部署历史）与 `ai/router.py` 几个端点挂了权限依赖，其余上百个写操作接口无任何校验。`[已复核]`
- [ ] **P0** `logs/router.py:36` + `logs/log_service.py:47` — `filename` 直接拼进 `log_dir / filename`，`../../` 可读任意文件；同文件 `:74` 的 `clear_old_logs` 无鉴权可删文件。`[已复核]`
- [ ] **P0** `deploy/router.py:76,570`、`templates/template_service.py:171` — 裸 `jinja2.Template` 渲染用户可写模板与变量，无沙箱，等价 SSTI（可达 RCE）。`[待验证]` 需确认模板来源是否仅限管理员
- [ ] **P0** `devices/router.py:815` — 用未消毒的 `photo.filename` 拼写入路径（路径穿越写入），且无类型/大小限制、同步 `shutil.copyfileobj` 阻塞事件循环。`[已复核]`
- [x] **P1** `auth/router.py:102,110` — passlib 缺失时静默退化为明文存储 + 明文比较，无任何告警。建议缺失即启动失败。`[已复核]`
  → 部分缓解（步骤 1）：`nas user create-admin` / `reset-password` 会先检查 `PWD_CONTEXT_AVAILABLE`，
    缺失则拒绝创建并给出安装命令；`tests/test_credentials_no_plaintext.py::test_passlib_is_installed`
    把它变成测试门禁。运行期的 fail-fast 留到步骤 3 一起做。
  → 完成（步骤 3）：应用 startup 调用 `validate_auth_runtime_dependencies()`；缺 passlib 或 python-jose 直接拒绝启动。
- [x] **P0**（步骤 1 新增）没有创建本地管理员账号的手段 —— 收紧认证前无法确认"自己能登进去"。`[已复核]`
  → 新增 CLI：`nas user create-admin -u <用户名>`（交互式输入密码、强制 ≥8 位、自动关联 admin 角色）、
    `nas user reset-password`、`nas user list`
- [x] **P0**（步骤 2）登录入口只有本地账号一种，SSO 无处挂载。`[已复核]`
  → 新增 `app/shared/config.py::SSOConfig`（Entra ID / OIDC，默认关闭）与
    `app/features/auth/sso_router.py` 三个端点（`/status`、`/login`、`/callback`）；
    前端 `Login.vue` 改成两段式：先选登录方式（企业账号 / 本地账号），再进表单。
    未开通时 `/status` 返回 `enabled:false`，`/login` 返回 **501 + 缺失配置项清单**（不是 404/500），
    且 `/status` 绝不回传 client_id / client_secret。
    等应用注册批下来，只需在 config.yaml 填 tenant_id / client_id / client_secret / redirect_uri。
- [ ] **P1** `services/adk/config.py:118`、`compliance/router.py:521,564,618` — AI API Key 明文入库（字段名却叫 `api_key_encrypted`），并写进进程级 `os.environ`，跨请求污染。`[已复核]`
- [x] **P1** `credentials/router.py:104` — 通过 API 明文返回 SSH 密码；`:41,115` 请求体是裸 `dict`。`[已复核]`
  → 修复（步骤 1）：详情/列表接口一律不返回密码，只给 `has_password` / `has_enable_password` 标志；
    前端本来就没用那个字段（`Credentials.vue` 写的是 `password: ''`），所以零功能损失。
    同时该文件的另三个问题一并解决：四个接口挂上 `credential:*` 权限依赖、请求体换成
    Pydantic 模型、`db = next(get_db())` 换成 `Depends(get_db)`。
  → 连带修复：前端不回填密码后，"留空"必须等于"保持不变"，否则每次编辑都会静默清掉已存的
    enable 密码；清空改为显式 `clear_enable_password`（编辑框下新增勾选项）。
  → 连带修复：`app/cli.py` 的 `backup run` 命令此前硬编码 `admin/admin/admin`，改为走
    `resolve_device_credentials()`。
- [ ] **P1** `credentials/credential_service.py:24-38` — Fernet key 由 `jwt_secret` + 固定盐 `b"nas-salt"` 派生：轮换 JWT 密钥即全部设备凭证不可解密，且 `credentials/router.py:96` 已用 try/except 把解密失败兜成空密码。`[已复核]`
- [x] **P1** `alerts/router.py:36-56` — `GET /settings` 无鉴权返回 `dingtalk_secret` / webhook / SMTP 用户名。`[已复核]`
  → 修复（步骤 4A）：`GET/POST /settings` 与 `POST /test` 统一挂 `alert:manage`；读取接口仅返回 `has_*` 标志，绝不返回 SMTP 用户名/密码、Webhook 或钉钉 Secret；请求体换成 Pydantic 模型，空敏感字段表示保留，只有显式 `clear_*` 才清除；配置采用临时文件 + `os.replace` 原子写入并重置配置/通知服务缓存。前端同步改为“已配置，留空保留”与显式清除，并用 `alert:manage` 控制菜单入口。
- [x] **P1** `shared/middleware/auth_middleware.py:26` — `skip_paths` 含 `/api/devices`，前缀匹配放过整个设备域；`:57,62` 在中间件里 `raise HTTPException` 不会被 FastAPI 异常处理器接管，实际返回 500 而非 401。`[已复核]`
  → 修复（步骤 3）：删除设备域豁免，公共端点改精确匹配；中间件统一返回 JSON 401/403，并完整校验用户存在、启用状态与会话撤销状态。
- [ ] **P1** `services/trap_receiver.py:196` — SNMP Trap 的 community 校验默认关闭，任意主机可伪造 linkDown 改设备状态并自动开工单。`[待验证]`
- [x] **P1** `notifications/router.py:37` — 解析不出用户时默认返回 `"Admin"`，匿名请求可读/已读/删除 Admin 的通知。`[已复核]`
  → 修复（步骤 3）：通知接口依赖统一 `Principal`，删除手工 JWT 解码和 `Admin` 回退；部署审计同步改用该身份。
- [ ] **P1** `frontend/src/router/index.js:431` — 路由守卫只读 `localStorage.isLoggedIn === 'true'`，无权限判断，手改标志位即可进 `/users`、`/credentials`。`[已复核]`
- [ ] **P2** 多处 `detail=str(e)` 直接回显内部异常（`deploy/router.py:1160`、`devices/router.py:219` 等）。`[已复核]`

**完成判定**：`auth_enabled=true` 下跑一遍主要写操作，未授权账号应全部 403；日志文件接口对 `../` 返回 400。

**步骤 1 / 2 的验证结果（2026-07-29）**：✅ `ruff` 零告警；✅ 新增
`tests/test_credentials_no_plaintext.py`（10 项）与 `tests/test_sso_placeholder.py`（7 项）全过，
覆盖"接口不含明文""留空不误清空""错误密码返回 401""SSO 状态不泄漏密钥"；
✅ 全量 pytest 失败集合仍为基线 64 条，通过数 355 → 387。
**未验证**：前端页面实际渲染（npm 装不上依赖），登录页双入口需你在浏览器里看一眼；
真实 Entra ID 跳转需等应用注册。

**步骤 3 的验证结果（2026-08-01）**：✅ `tests/test_auth_step3.py` 20 项全过，覆盖
伪造 `X-User`、有效/伪造/过期/refresh/撤销 token、公共路径精确匹配、CORS 预检、
debug 双开关、管理员通过与普通用户 403、环境变量映射和认证依赖 fail-fast；
✅ `tests/test_credentials_no_plaintext.py` 10 项、`tests/test_sso_placeholder.py` 7 项、
`tests/test_batch1_regressions.py` 15 项全过；✅ `ruff` 零告警；
✅ 全量 pytest（跳过会挂起的 console）仍为既存基线 **54 failed / 10 errors**，
通过数增至 420，未新增失败。`tests/test_auth.py` 的 2 项旧 `check_permission` 导入失败仍在基线内。
**未验证**：真实浏览器登录/登出、生产反向代理下的 CORS、真实 Entra ID 回调；进入步骤 4 前应在测试服务器做一次本地管理员 smoke test。

**测试系统 AI 实测补充（2026-08-01，HEAD `e528c53`，真实服务器）**：在测试服务器上按「步骤 3 未完成测试」清单 A/B/C 执行，
结果见下方更新后的清单。要点：
- ✅ 门禁全过：ruff 零告警；`test_auth_step3.py` 20/20；credentials/sso/batch1 32/32；
  全量 pytest **53 failed / 424 passed / 4 skipped / 0 errors**（失败集合为基线子集，无新增失败，
  文档标注的 Windows-only `test_git_config.py` 11 项在 Linux 上不存在）。
- ✅ 服务器已切换 `auth_enabled=true` + 随机 JWT secret（≥32 位）+ testadmin 超管账号，认证保持开启。
- ✅ API smoke test（C 部分）通过：无凭据/伪造 `X-User`/伪造 token 均 401；本地管理员 200；
  viewer 访问 `/api/credentials` 403；SSO 端点匿名可达且不泄漏密钥。
- ⚠️ 遗留：`GET /api/alerts/settings` 匿名可读（dingtalk_secret 等）——文档 P1 已知项，属步骤 4；
  passlib 与新版 bcrypt 版本兼容警告（`bcrypt` 移除 `__about__`），功能正常，建议后续升级。
- 未执行：浏览器端（D）、Docker（E）、用户归属审计（F）——本服务器无 Docker/前端构建依赖，
  dry-run 部署审计需实验设备，留待步骤 4 前后环境补齐。

**步骤 4A 验证结果（2026-08-01）**：✅ `tests/test_alert_settings_security.py` 17 项全过，覆盖
真实 FastAPI 路由的未认证 401、无权限 403、管理员 200 与响应脱敏，以及空值保留、显式清除、
新秘密替换、请求模型拒绝非法 channel/端口/额外字段、原子写入和服务缓存失效；
✅ 与步骤 3/凭证/SSO/批次一相邻回归合计 69 项全过；✅ Ruff 零告警；✅ `app.main` 完整导入通过；
✅ Windows 全量 pytest（跳过 console）为 **54 failed / 440 passed / 4 skipped / 10 errors**，
失败集合仍为既存基线，无新增失败。⚠️ 本机未安装 `frontend/node_modules`，Vite build 留给测试系统执行。
**下一切片**：步骤 4B deploy——`preview/history` 挂 `config:read`，`execute/schedule` 挂
`config:deploy`，`rollback` 挂 `config:rollback`，并把用户模板渲染从裸 `jinja2.Template`
迁到沙箱环境；真实设备只做实验设备 dry-run 与审计 operator 验证。

### 步骤 3 未完成测试：测试系统 AI 接手清单

> 目标：以下项目因本机缺 Docker、前端依赖或真实身份/设备环境而未执行。
> 测试系统只处理验证和测试修复，不应顺带进入安全步骤 4 的接口权限改造。

#### A. 测试环境准备

1. 拉取 `origin/main`，确认工作区干净，并记录 `git rev-parse HEAD`。
2. 后端生产式配置必须满足：`AUTH_ENABLED=true`、`APP_DEBUG=false`、
   `JWT_SECRET` 为至少 32 位随机值、`CORS_ALLOWED_ORIGINS` 为测试前端的精确 Origin。
3. 执行 `nas user list`；没有管理员时执行 `nas user create-admin -u testadmin`。
4. 准备一个无 `admin:all`、无 `credential:read`、无 `config:deploy` 的普通测试账号。
5. 不得使用生产设备凭证；部署审计测试只能选择实验设备并使用 dry-run。

#### B. 自动化门禁（应全部满足）

```powershell
.\.venv\Scripts\python.exe -m ruff check app scripts migrations tests
.\.venv\Scripts\python.exe -m pytest tests\test_auth_step3.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_credentials_no_plaintext.py tests\test_sso_placeholder.py tests\test_batch1_regressions.py -q
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests\test_console_service.py
```

预期：步骤 3 为 **20 passed**；凭证/SSO/批次一为 **32 passed**；Ruff 零告警。
全量测试允许的既存基线为 **54 failed / 420 passed / 4 skipped / 10 errors**，失败集合必须与
本文件“批次七”一致。任何新增失败都算本次回归，不能通过更新基线掩盖。

#### C. API 认证 smoke test（2026-08-01 AI 已执行大部分）

- [x] 不带任何凭据访问 `GET /api/devices`：返回 401（实测 HTTP 401）✅
- [x] 只带 `X-User: Admin` 访问同一接口：仍返回 401（实测 `X-User: admin` 401）✅
- [x] 错误 Bearer、过期 token、refresh token：均返回 401，不能变成 500（实测伪造 token 401）✅
- [x] 本地管理员登录成功后访问 `/api/auth/me`、`/api/devices`、`/api/notifications`：返回 200
  （实测 testadmin 登录后 `/api/devices`、`/api/dashboard/summary` 均 200；`/api/auth/me` 端点已由
  `/api/permissions/my-permissions` 覆盖，返回 admin:all）✅
- [x] 普通账号访问已挂权限的 `/api/credentials`：返回 403；管理员访问返回 200
  （实测 viewer test01 访问 403，admin 访问 200）✅
- [ ] 调用 `/api/auth/logout` 后复用旧 token：返回 401（验证撤销会话）—— 未测，服务端会话撤销逻辑待确认
- [ ] 停用账号现有 token：返回 403；不能继续访问业务 API —— 未测，需要停用账号操作
- [x] `/api/auth/login`、`/api/auth/status`、三个 `/api/auth/sso/*` 公共端点、`/health`、
  `/ready`、`/docs`、`/openapi.json` 可匿名访问；`/api/auth/login-evil`、
  `/health/private` 不得因前缀相似而放行 —— 实测 health/ready/SSO status 匿名 200，
  SSO login/callback 501，前缀精确匹配生效；`/docs`、`/health/private` 未单独实测 ✅（部分）

#### D. 浏览器与前端（未执行）

- [ ] 在企业 CA/内网 npm 镜像可用的环境执行 `npm ci && npm run build`，构建必须成功
- [ ] 本地账号登录后刷新页面，登录态保持；登出后回到登录页且旧 token 不可再用
- [ ] 浏览器 Network 面板确认请求只有 `Authorization: Bearer ...`，不再发送 `X-User`
- [ ] 顶部全局搜索能返回设备、模板、备份结果；401 时统一跳回登录页
- [ ] 普通账号不能通过修改 `localStorage.isLoggedIn` 获得受保护 API 数据
  （菜单级权限隐藏属于步骤 4/前端权限治理，API 拒绝必须现在成立）

#### E. 反向代理、CORS 与容器（未执行）

- [ ] `docker compose config` 成功，backend 生效值为 `AUTH_ENABLED=true`、`APP_DEBUG=false`
- [ ] `docker compose up` 后 `/health` 与 `/ready` 正常，缺失/弱 `JWT_SECRET` 时 backend 必须拒绝启动
- [ ] 合法 Origin 的 OPTIONS 预检成功；非法 Origin 不返回允许跨域头
- [ ] HTTPS 反向代理下登录、Bearer 转发、401/403 响应和 `WWW-Authenticate` 头不被 Nginx 改写

#### F. 用户归属与审计（未执行）

- [ ] 建立用户 A/B 各自通知，A 只能读取、标记、删除 A 的通知，不能操作 B 的通知
- [ ] 使用实验设备执行一次 dry-run 部署，部署历史/审计 operator 必须等于 token 用户名，
  伪造 `X-User` 不能改变 operator
- [ ] 多并发请求使用不同 token 时身份不得串线，日志中不得出现 token、密码或 JWT secret

#### G. 明确暂缓项

- 真实 Entra ID 授权跳转/回调仍等待 IT 应用注册，步骤 3 只要求占位端点匿名可达且不泄密。
- WebSocket `/ws/logs` 不经过 HTTP middleware；其 token 协议与日志权限归入安全步骤 4 的 logs 切片，
  测试系统应记录为待办，不应误判为步骤 3 已覆盖。
- 真实 Netmiko/NAPALM 部署不在本轮执行；只允许实验设备 dry-run 验证身份归属。

#### H. 测试回传格式

测试系统需回传：commit SHA、环境变量（密钥脱敏）、命令与退出码、失败测试完整 nodeid、
HTTP 状态码/关键响应头、浏览器截图或 HAR、是否属于既存基线，以及可复现的最小步骤。

---

## 批次三 · 架构一致性（比单个 bug 影响更大）

### 3.1 阻塞事件循环

- [ ] **P1** `backups/router.py:69,319` — async def 内直接调同步 netmiko SSH（超时 30/60s），`/batch` 还串行遍历全部设备。`[已复核]`
- [ ] **P1** `deploy/router.py:971` — `rollback_deploy` 在 async def 内逐台同步调 `napalm_service.rollback_device`（同文件 `execute_deploy` 已正确用线程池，属遗漏）。`[已复核]`
- [ ] **P1** `logs/router.py:66` — WebSocket 迭代同步阻塞生成器 `stream_logs`（内部 `time.sleep(0.5)` 死循环），一条连接占死事件循环。`[已复核]`
- [ ] **P1** `discovery/router.py:93` — 同步 `ping_sweep`（50 线程 + 阻塞 socket）在 async 内执行；`subnet` 无 CIDR 校验，`/8` 会构造 1600 万 future。`[已复核]`
- [ ] **P1** `tool_logs/tool_executor.py:101-112` — 协程内直接同步 `ConnectHandler/send_command`，无 `run_in_executor`。`[已复核]`
- [ ] **P1** `alerts/router.py:131` — `_send_email` 同步 SMTP 在 async 内调用。`[待验证]`
- [ ] **P1** `console/console_service.py` 全量、`devices/router.py:815` 文件 IO — 同类问题。`[待验证]`
- [ ] **P1** 统一方案：建立唯一的「设备操作执行器」——强制线程池 + 强制过命令守卫 + `finally` 关连接，把 netmiko / napalm / serial / subprocess 四条路径全部收进去。

### 3.2 数据库会话与事务

- [ ] **P0** `db = next(get_db())` 绕过依赖注入共 9+ 处：`main.py:277`、`services/reachability_monitor.py:194,248,436,497`、`services/snmp_discovery.py:139,197`、`services/trap_receiver.py:264`、`shared/db_init.py:14,49`、`tool_logs/tool_executor.py:99`、`devices/router.py:800,835,857`、`backups/router.py:231,255`。`get_db`（`shared/database.py:135`）是包了 `session_scope` 的生成器，`next()` 后 commit/rollback/close 永不执行，连接靠 GC 归还，`pool_size=10` 在后台线程长跑下会耗尽。`[已复核]`
- [ ] **P1** `devices/device_service.py:118` — `_sync_modules_to_inventory` 内部自行 commit，与调用方形成嵌套提交，中途失败留半份库存实例。`[已复核]`
- [ ] **P1** `deploy/router.py:1006-1035` — `create_deploy_history` 内部已 commit（`:1449`），之后再更新 `rollback_status` 二次 commit，中途失败留半状态。`[待验证]`
- [ ] **P1** `backups/router.py:154,163` — 通用 except 里引用可能未绑定的 `device`；且在 `db.commit()` 之后才 `db.rollback()`，顺序无效。`[已复核]`
- [ ] **P1** `deploy/router.py:907` — `except: pass` 吞掉 rollback/close 阶段全部异常。`[已复核]`

### 3.3 Schema 权威源

- [ ] **P0** `main.py:353` + `shared/database.py:95` — 启动时 `init_db()` 调 `Base.metadata.create_all`，与 alembic 双轨；`models.py` 45 张表中 alembic 仅覆盖约 28 张（`spare_part_instances`、`device_interfaces`、`interface_traffic_samples`、`notifications`、`deploy_history`、`compliance_*`、`ai_configs`、`system_config`、`service_slo`、`jobs` 等全靠 create_all 兜底）→ **全新 PG 库执行 `alembic upgrade head` 得不到完整 schema**。`[已复核]`
- [ ] **P0** 8 个"迁移"脚本硬编码 `sqlite3` + `data/nas.db`：`migrations/add_monitor_tier.py:12`、`add_service_slo_key.py:10`、`add_spare_part_fields.py:10`、`add_service_slo.py:17`、`create_device_links.py:14`、`fix_slo_fields.py:7`、`scripts/migrate_device_reachability.py:17`。在 PG 生产上执行会静默创建/修改一个空 SQLite 文件，改错库且不报错。建议删除或移入 `scripts/legacy_sqlite/`。`[已复核]`
- [ ] **P1** `migrations/versions/b7a8c9d0e1f2_*.py:16` 与 `c1d2e3f4g5h6_*.py:16` 都是 `down_revision = None`，存在多个 base 根，分支执行顺序不确定。`[已复核]`
- [ ] **P1** `migrations/env.py:13` — 只 import `app.shared.models`，`models_jobs.Job` 未注册进 `target_metadata`，autogenerate 会生成 `drop_table('jobs')`。`[已复核]`
- [ ] **P1** `migrations/versions/f3a4b5c6d7e8_*.py:41` — 对 `topo_edges/topo_nodes/device_ports` 只有 `DELETE FROM`，这三张表从未被任何 `create_table` 创建。`[已复核]`
- [ ] **P1** `models.py:32,38,62,67,72` — `deployment_status/reachability/monitor_tier/risk_level/lifecycle_stage` 声明 `index=True`，但列是通过裸 ALTER 加的，PG 上索引实际不存在。`[待验证]` 用 `\d devices` 确认
- [ ] **P1** `models.py:154,237,771,1153` — `fault_records.maintenance_id` 等 4 处 FK 无 `ondelete`，且 fault↔maintenance 构成环形 FK，删设备时会被 FK 违例挡住。`[已复核]`
- [ ] **P1** `models.py:23` — `devices.serial_number` 既无唯一约束也无索引；`models.py:332` — `audit_logs` 除主键外零索引。`[已复核]`
- [ ] **P2** `models.py` 全文 0 处 `server_default`，默认值只在 Python 侧；raw SQL 路径写 NULL 而 `filter(x == False)` 在 PG 下不匹配 NULL。`[已复核]`
- [ ] **P2** `models.py:187,1011,1050,1239,1374`、`models_jobs.py:34` — 裸 Integer 伪外键，会产生孤儿数据。`[已复核]`
- [ ] **P2** `shared/config.py:137` — `pool_timeout` 配置项从未传入 `create_engine`（`database.py:73-78`），无效配置。`[已复核]`
- [ ] **P2** `models.py:1207` — `deploy_history.children` 的 `remote_side=[id]` + `backref="parent"` 自引用方向反了。`[待验证]`
- [ ] **P2** `interface_traffic_samples` / `device_metric_samples` 无分区、无保留策略，单表无限增长。`[已复核]`
- [ ] **P2** 目标动作：以当前 PG 实际结构 autogenerate 一个基线迁移并 `alembic stamp`，然后移除启动期 `create_all`。

### 3.4 缓存

- [ ] **P1** `services/reachability_monitor.py:339` — 探测历史存进 `max_size=256` 的全局 `SimpleCache`（与 dashboard 共用），被 LRU 淘汰即丢失连续失败计数 → **漏告警**。`[已复核]`
- [ ] **P1** `services/ai_triage.py:377,398` — AI 后台结果只写进程内存缓存，多 worker 下前端轮询永不命中。`[已复核]`
- [ ] **P1** `shared/cache.py:117` — `cached` 装饰器用 `hash(str(args))` 作键（含对象 repr 地址、受 PYTHONHASHSEED 影响），多进程键不一致；`_cache_key` 只取 md5 前 8 位。`[已复核]`
- [ ] **P1** `shared/cache.py:96` / `shared/redis_cache.py:107` — 内存与 Redis 两套实现互不失效；前者全扫描 + 全局锁，后者用 `KEYS prefix*`。`[已复核]`
- [ ] **P2** `shared/middleware/rate_limiter_v2.py:16` — `TieredRateLimiter` 定义后完全未使用；限流为进程内内存态，多 worker 下额度按进程翻倍。`[待验证]`

### 3.5 启动与关闭

- [ ] **P1** `main.py:217-221` — `return {...}, status_code` 被序列化成数组且状态码恒 200，`/ready` 永远"健康"。`[已复核]`
- [ ] **P1** `main.py:434-435` — 导入期注册 SIGTERM/SIGINT，会被 uvicorn 自身 handler 覆盖，且无 `@app.on_event("shutdown")` → Trap 接收器 / APScheduler / 连接池清理实际不执行。`[已复核]`
- [ ] **P1** `services/prometheus_connector.py:505` — `start()` 内先阻塞跑一次完整 `poll_once()`；`:507` 的轮询任务未设 `max_instances/coalesce`（清理任务设了），60s 周期可重叠，`_last_counters` 多线程读写导致速率算错。`[已复核]`
- [ ] **P1** `main.py:262-283` — `async with AsyncClient` 内 `send(stream=True)`，返回 StreamingResponse 前 client 已关闭。`[待验证]`
- [ ] **P1** `main.py:76-80` — 限流中间件注册在 auth 之后，实际先于认证执行，无法按用户限流。`[已复核]`
- [ ] **P2** `services/trap_receiver.py:243` — `stop()` 只关 socket 不 join 线程；全局 `_db_lock` 串行处理所有 Trap，风暴时丢包。`[待验证]`

---

## 批次四 · 数据正确性（页面数字目前不可信）

- [ ] **P1** `compliance/compliance_service.py:341` — `max([severity 字符串])` 按字典序，结果 `medium > low > high > critical`，行级严重度标注全错。`[已复核]`
- [ ] **P1** `faults/router.py:210` — `order_by(severity.desc())` 是字符串倒序（`warning > minor > major > critical`），与注释声称的 critical 优先相反。`[已复核]`
- [ ] **P1** `faults/router.py:938-955` — 统计只覆盖 `open/investigating/resolved/closed`，实际状态机含 `assigned/accepted/diagnosing/resolving/transferred`（`models.py:154` 注释），活跃数低估、分布不等于总数。`[已复核]`
- [ ] **P1** `compliance/compliance_service.py:421` vs `compliance/router.py:283` — service 返回 `results`，router 读 `security_issues/compliance_issues/config_errors/recommendations`，`/quick-check` 永远返回空数组。`[已复核]`
- [ ] **P1** `dashboard/dashboard_service.py:51-78` — 按 10 种设备类型循环执行约 8 条 COUNT，单次 summary 近 80 次查询。`[已复核]`
- [ ] **P1** `dashboard/dashboard_service.py:1057,1103` — 变更-故障关联在循环内逐条 COUNT（N+1），且同条件 count 与 all 重复查两次；`:948,962` SLO 计算逐个查设备与故障全集。`[已复核]`
- [ ] **P1** `faults/router.py:217,222` — 列表接口每条故障各查一次 Device 和 MaintenanceRecord（limit=100 → 约 200 次额外查询）。`[已复核]`
- [ ] **P1** `spare_parts/router.py:334`（出库）/ `:258`（入库）— 仅按 `serial_number` 定位实例，未约束 `part_id`，可把 B 备件实例按 A 备件出库，两个 `quantity_in_stock` 同时写错。`[已复核]`
- [ ] **P1** `deploy/router.py:1143` — `window_id.split('_')[1]` 缺参数即异常；该接口返回 success 但**不创建任何定时任务**（注释自承"简化处理"）。`[已复核]`
- [ ] **P1** `tasks/backup_tasks.py:139` — 批量任务伪造子 Job ID `f"{job_id}-{i}"`，Job 表无对应记录 → 子任务全部 "Job not found"。`[已复核]`
- [ ] **P1** `backups/router.py:78,328` — `status=result["success"] if ... else "failed"` 把布尔 `True` 写进 String 状态列。`[已复核]`
- [ ] **P1** 分页参数普遍无 `ge/le` 约束：`devices/router.py:155`、`devices/device_service.py:150`、`backups/backup_service.py:16`、`faults/router.py:170`、`maintenance/router.py:744`、`deploy/router.py:1205`（`spare_parts/router.py:59` 用了 `Query(ge/le)`，风格不统一）。`[已复核]`
- [ ] **P1** 高危写操作请求体为裸 `dict`：`deploy/router.py:40,482,915,1134`、`credentials/router.py:41,115`、`templates/router.py:28,42`（后者还 `ConfigTemplate(**data)` 批量赋值）。`[已复核]`
- [ ] **P2** `templates/template_service.py:20`、`workflows/router.py:104`、`notifications/router.py:78` — 把页大小当 `total`，分页总数失真。`[待验证]`
- [ ] **P2** 时间字段两套写法：devices/backups 走 `utc_iso()`（带 Z），`faults/router.py:288`、`deploy/router.py:1237`、`credentials/router.py:30` 直接 `isoformat()`（无 Z），`notifications/router.py:57` 手工拼 Z，`deploy/router.py:1105` 用本地 `datetime.now()`。`[已复核]`
- [ ] **P2** `discovery/discovery_service.py:245` — 单例缓存首次的 `timeout/workers`，后续请求传参被静默忽略。`[待验证]`
- [ ] **P2** `compliance/router.py:26` — 模块导入期实例化 `ComplianceService()`，其 `__init__` 会访问数据库。`[已复核]`
- [ ] **P2** `deploy/router.py:815,985` — 审计日志 `operator` 硬编码 `"Web"`，同函数内已解析出 `current_username`，审计不可追溯。`[已复核]`
- [ ] **P2** `faults/router.py:1015,1042,1069,1096,1125` — 五个后台任务用 `print()` 吞异常，工作流/AI/通知失败完全不可见。`[已复核]`

---

## 批次五 · 前端

- [ ] **P0** `views/Deploy.vue`（3631 行）— 无任何卸载钩子，部署中切路由后 `setInterval`(`:1737,:2078`) 与 WebSocket(`:1747`) 全部残留；且两处 `setInterval` 复用同一 `timer` 变量，`stopTimer()` 只清得掉最后一个。`[已复核]`
- [ ] **P0** `utils/requestManager.js:22-30` + `api/request.js:78-83` — 所有 GET 按 `method:url:params:data` 自动 abort 同键旧请求，两个组件轮询同一端点会互相取消，表现为随机空数据，且调用方无法关闭该行为。`[已复核]`
- [ ] **P0** `api/request.js:130-165` — `apiWithRetry` 对 post/put/patch/delete 默认重试，非幂等写操作（部署、入库）可能重复下发。`[已复核]`
- [x] **P0** `views/layout/SearchDropdown.vue:174-198` — 用原生 `fetch('/api/...')` 绕过 axios 实例，不带 Authorization、不过 401 拦截器。`[已复核]`
  → 修复（安全步骤 3）：设备、模板、备份搜索全部改走统一 Axios 客户端并使用结构化 `params`，自动携带 JWT 与复用 401 处理。
- [ ] **P1** `views/Compliance.vue:696,1504` — `v-html` 渲染自写 markdown 转换结果，`renderSectionContent` 只做正则替换不转义 HTML。`[待验证]`
- [ ] **P1** `utils/cache.js:121-130` — localStorage 回填内存缓存时重算 `Date.now()+ttl`，等于每次读取都续期，数据可无限存活。`[已复核]`
- [ ] **P1** `utils/cache.js:26-31` — 缓存键把 `JSON.stringify(params)` 非字母数字全替换为 `_`，不同参数可产出同键，且键顺序敏感。`[已复核]`
- [ ] **P1** `utils/cache.js:218-246` — `cachedRequest` 声称去重但无 in-flight Map，并发同键全部打到后端。`[已复核]`
- [ ] **P1** `views/DeviceHealth.vue:334,365,391` — 3 个 `echarts.init` 无 dispose 且组件无卸载钩子。`[待验证]`
- [ ] **P1** `views/Monitor3D.vue:1060` — 匿名 `theme-change` 监听从不移除，闭包持有旧 Three.js 场景阻止 GC；`:6231` 对数组材质 dispose 无效、纹理未 dispose。`[待验证]`
- [ ] **P1** `composables/useLoadControl.js:142,159,165` — `online`/`visibilitychange` 监听从不移除，也不返回清理函数。`[已复核]`
- [ ] **P1** `main.js:16` 装了 Pinia 但全项目 `defineStore` 数为 0；登录态/用户/主题在 12 个文件裸读 localStorage（`views/Layout.vue:78,81`、`api/request.js:68,74` 等），无单一数据源。`[已复核]`
- [ ] **P1** `api/request.js:49` 读 `'language'`，`locales/index.js:6797,6802` 写 `'lang'`，键不一致导致英文界面仍被汉化。`[已复核]`
- [ ] **P1** `locales/index.js` — 190 组重复键（`zh:dashDevices` L230/L288、`zh:uploadFailed` L742/L1349 等）后者静默覆盖；zh 3065 / en 3015 键，52 键缺英文、2 键缺中文。`[待验证]` 建议脚本化校验
- [ ] **P1** 硬编码中文与 `useI18n` 混用：`Monitor3D.vue` 825 处、`Deploy.vue` 245 处、`Compliance.vue` 189 处，英文模式大面积失效。`[待验证]`
- [ ] **P1** `vite.config.js:18` — target `chrome60` 与 router 全量动态 `import()`（需 Chrome 63+）自相矛盾；`format:'es'` 写在 `build` 下属无效键。`[已复核]`
- [ ] **P1** `vite.config.js` — 无 `manualChunks`，three@0.184 + echarts + element-plus 同一 vendor chunk，首屏体积过大。`[已复核]`
- [ ] **P1** `vite.config.js:27-30` — `server.https` 无条件 `readFileSync` 证书，缺证书连 `vite build` 都崩。`[已复核]`
- [ ] **P2** `api/request.js:107-113` — 401 用 `window.location.href` 整页刷新，多并发请求连弹错误，无 refresh token 流程。`[已复核]`
- [ ] **P2** 巨型视图：`Monitor3D.vue` 7119 行、`Deploy.vue` 3631、`Compliance.vue` 2948，渲染与请求耦合，无法单测。`[已复核]`
- [ ] **P2** `:key="index"` 广泛存在（`Operations.vue:18,272,298,388,417,439`、`Compliance.vue:669,688,754`、`Devices.vue:340`）；`views/Logs.vue:286` 每 3 秒全量重载日志；全项目无虚拟滚动。`[待验证]`
- [ ] **P2** `Monitor3D.vue` 53 处、`Deploy.vue` 10 处 `console.log`（含 WS 报文）未在生产剥离。`[待验证]`
- [ ] **P2** `utils/requestManager.js:11,155` — `requestCache` 从未写入，配套 10s 清理定时器为空转死代码；`utils/cache.js:253` 同样是模块级常驻定时器。`[已复核]`
- [ ] **P2** `.env.example` 的 `VITE_WS_URL` 源码零引用（WS 地址按 `window.location.host` 拼），配置已失效。`[待验证]`

---

## 批次六 · 工程与清理

- [x] **P0** venv 内无任何 linter（pyflakes / ruff / flake8 全部未安装）——批次一里 4 个 undefined-name 都能被 `ruff F821` 一次抓出。接入 ruff 是本清单投入产出比最高的一项。`[已复核]`
  → 已完成：新增 `ruff.toml`（门禁规则 F821/F822/F823/F811/F632/E9，刻意不启用 E712 因为 SQLAlchemy 的 `filter(Column == True)` 是必要写法），`requirements.txt` 钉 `ruff==0.16.0`，并用 `tests/test_batch1_regressions.py::test_ruff_static_analysis_is_clean` 把门禁接进测试
  → 未纳入门禁的技术债：F401 未使用导入约 200 处、F841 未使用局部变量约 20 处（其中少数指向真实死逻辑，如 `deploy/router.py:1140` 的 `deploy_data`）
- [ ] **P1** 测试覆盖结构性偏斜：38 个测试文件 / 430 个用例，`pytest --collect-only` 干净通过，但全部集中在 service 层；router、streaming service、celery task 三条链路零覆盖，正是批次一全部故障的所在。`[已复核]`
- [ ] **P0**（执行中新发现）`tests/test_console_service.py` 会**挂起**（collect 17 项后无进展，>45s 无输出），导致 `pytest` 全量跑不完 —— 该文件之后的用例长期从未执行过。原因指向 console 服务的同步串口 IO（批次三 3.1）。当前 CI 需先 `--ignore=tests/test_console_service.py` 才能拿到完整结果。`[已复核]`
- [ ] **P1** `core/celery_app.py:36-48` + `tasks/__init__.py:30` — 任务路由指向三个空占位模块，全局无 `beat_schedule`；`tasks/__init__.py` 在导入时写磁盘生成占位文件。`[已复核]`
- [ ] **P1** `frontend/npm ci` 在当前网络下失败（`SELF_SIGNED_CERT_IN_CHAIN`，registry 指向 npmmirror）→ 前端无法构建验证。需决定：配置企业 CA 证书，或改用内网镜像。`[已复核]`
- [ ] **P2** `frontend-react/`（17 文件、5 个页面骨架、独立 vite/tsconfig）是停滞的并行重写，构成第二套事实标准，建议归档或删除。`[已复核]`
- [ ] **P2** `backend/`（22 文件）已在 `README_ARCHIVED.md` 中标注"自 2026-06-05 废弃、不可运行"，但仍在仓库内，建议删除或移出。`[已复核]`
- [ ] **P2** `frontend/src/locales/index.js.backup`（2277 行）留在 `src/` 内，会被 vite 扫描。`[已复核]`
- [ ] **P2** `data/nas.db`（663 KB，2026-07-16）是迁 PG 前的遗留库，缺 `config.yaml` 时任何脚本都会默认打开它。建议改名为 `nas.db.legacy-20260716`。`[已复核]`
- [ ] **P2** `scripts/seed_data.py:35-41` 用 `query().delete()` 批量清表并在 `:640` 调 `init_db()`，误在生产执行即清库，建议加环境确认。`[已复核]`
- [ ] **P2** `scripts/migrate_features.py` 是代码搬迁 codemod（会覆盖 `app/shared/*.py`）而非 DB 迁移，放在 scripts 里有误执行风险。`[已复核]`
- [ ] **P2** 异常体系混用：`shared/exceptions.py` 有完整 `AppException` 体系，devices/templates 用它，faults/maintenance/deploy 全用 `HTTPException`。`[已复核]`
- [ ] **P2** 三处重复的 vendor→driver 映射：`deploy/napalm_service.py:33`、`deploy/deploy_stream_service.py:300`、`devices/drivers/registry.py`。`[已复核]`
- [ ] **P2** 裸 `except:` 静默降级：`compliance/compliance_service.py:279`、`faults/router.py:335`、`discovery/discovery_service.py:130`、`shared/models.py:207`、`deploy/router.py:907`。`[已复核]`
- [ ] **P2** `maintenance/router.py:735,807` — `""` 与 `"/"` 双装饰器重复注册同一处理器。`[待验证]`

---

## 批次七 · 既存测试失败基线（批次一执行时测得，与本次改动无关）

`pytest -q --ignore=tests/test_console_service.py` 的结果是 **54 failed / 370 passed / 4 skipped / 10 errors**。
下面 64 条失败在修复前后**逐条完全一致**，属于早于本轮审查就存在的债务，需要单独一批处理：

- [ ] **P1** `tests/test_compliance_service.py` 24 项失败 —— 与批次四"`/quick-check` 字段名对不上"、"`max([severity])` 字典序"两条同源，建议连带修
- [ ] **P1** `tests/test_tool_executor.py` 11 项失败 —— 与批次三 3.1（协程内同步 SSH）、`next(get_db())` 未关闭同源
- [ ] **P1** `tests/test_git_config.py` 11 项失败/错误 —— PermissionError，疑似 Windows 上临时 Git 仓库清理失败，需确认是否仅本地环境问题
- [ ] **P1** `tests/test_discovery_service.py` 8 项失败 —— 与批次四"单例缓存首次 timeout/workers"同源
- [ ] **P1** `tests/test_spare_part_service.py` 3 项、`tests/test_deploy_service.py` 2 项、`tests/test_auth.py` 2 项、`test_device_service.py` / `test_dashboard_service.py` / `test_email_service.py` 各 1 项
- [ ] **P1** 恢复"绿色基线"后再把 `pytest` 接入提交前门禁；在此之前只能靠"失败集合不变"来判断是否引入回归

## 建议执行顺序

1. ~~**批次一**（硬故障）+ **批次六第 1 项**（接 ruff）~~ —— ✅ 2026-07-29 完成
2. **批次二**（安全）—— 需先确认 `auth_enabled` 的目标状态，再决定是收紧默认值还是重新定位 RBAC
3. **批次三 3.2**（DB 会话统一）+ **3.1**（设备操作执行器）—— 这两项一起做，收益最大
4. **批次三 3.3**（schema 基线）—— 独立于代码，可并行推进
5. **批次四**（数据正确性）—— 页面数字可信之后再谈优化
6. **批次五**（前端）—— 先收请求层默认行为，再补卸载清理，最后拆巨型组件与重建 i18n 表
7. **批次三 3.4/3.5** 与 **批次六剩余项**

## 附注

- 未做的验证：前端 `vite build` 未跑过（npm 装不上依赖），所有前端结论均为静态阅读；`[待验证]` 项建议实机复现后再改。
- 本清单未包含纯风格问题（命名、注释、格式），只保留会影响正确性、安全、性能或可维护性的条目。

## 日常校验命令

```powershell
# 静态门禁（必须零告警）
.\.venv\Scripts\python.exe -m ruff check app scripts migrations tests

# 批次一回归用例
.\.venv\Scripts\python.exe -m pytest tests/test_batch1_regressions.py -q

# 全量测试（必须跳过会挂起的 console 用例，见批次六）
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_console_service.py
```
