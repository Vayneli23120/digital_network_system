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
  → 后续（批次二·步骤5 收尾）：legacy `/ws/cli/{session_id}` 无认证部署路径整块下线，`cli_stream_service.py` 与 `NapalmStreamService`/`get_napalm_stream_service` 一并删除，`napalm_service.py` 不再使用 `asyncio`/`datetime`（导入随之下移），本 P0 回归点由「删除代码」消解，`test_batch1_regressions.py` 对应用例移除。
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
> | 4 | 按危险度给写接口挂权限：alerts → deploy → devices → logs → 其余 | ✅ 高风险主线 4A–4E-B5B（2026-08-02）+ 长尾端点（2026-08-03 slice A）全部完成 |
> | 5 | 会话级 SSH 凭证（用时输入一次）+ 备份提醒（不再自动）+ 高危操作二次确认 | ✅ 2026-08-03（切片 A 备份会话凭证 + 需备份列表；切片 B 部署/回滚凭证 + 二次确认 + 下线异步） |
> | 6 | OIDC 真接（填 tenant/client/secret + 服务器出站白名单） | ⬜ 等 IT |
>
> 步骤 5 必须排在步骤 3、4 之后：会话凭证的安全性完全依赖"会话属于谁可信"，
> 在 `X-User` 可伪造的情况下先做会话凭证会比现状更糟。
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
- [x] **P0** 后端接口级鉴权缺失 — 全仓仅 `deploy/router.py:1319`（删除部署历史）与 `ai/router.py` 几个端点挂了权限依赖，其余上百个写操作接口无任何校验。`[已复核]`
  → 高风险主线已分切片完成 alerts、deploy、devices、logs、backups、templates、faults、maintenance、planned maintenance、workflows、users、system settings/SLO/system ops；Spare/Movements C1 已完成代码收口、待服务器验证，Notifications、Jobs、Compliance 与 Scan Sessions 等长尾端点仍待逐域复核。
  → 长尾收口（批次二 slice A，2026-08-03）：新增 `notification:*`、`job:*`、`compliance:read/write`、`discovery:*`、`scan:*` 10 个权限 code；notifications(5)、jobs(7)、compliance(20)、discovery(3)、scan(PC 侧 5) 全部挂上 `require_permission`（jobs/scan 原为全零 auth，一并补齐认证+授权）；`scan` 的 gun 侧端点（join/items/remove-item）因扫码枪无登录终端而按会话码凭据保持开放。同时修复两处 shadowed route：jobs `/stats`/`/types`/`/statuses` 与 scan `/sessions/active` 注册到通配路径之前（此前被 `/{job_id}`、`/sessions/{session_code}` 吞掉 → 404）。
- [x] **P0** `permissions/router.py` — 权限定义、角色与用户角色分配的九个写接口没有功能权限依赖，任意已登录用户可创建含 `admin:all` 的角色或直接给自己绑定管理员角色。`[已复核]`
  → 修复（步骤 4E-B0）：权限/角色创建更新克隆使用 `role:write`，删除使用 `role:delete`，用户角色覆盖/添加/移除使用 `user:write`；普通用户自提权三条路径均为 403，角色管理与用户管理职责不能互相替代。
- [x] **P0** `faults/router.py` — 23 条故障读写、删除、AI 与状态流转端点均无功能权限依赖，任意已登录用户可查看和修改全部故障。`[已复核]`
  → 修复（步骤 4E-B1）：全端点按 `fault:read/write/delete/analyze` 分层；创建者、复核人和转维修 operator 只取统一 Principal，旧客户端身份字段即使传入也不可信；工作日志改为严格限长模型。
- [x] **P0** `maintenance/router.py` — 13 条维修读写、删除与状态流转端点均无功能权限依赖，且 operator 由客户端 body 提供。`[已复核]`
  → 修复（步骤 4E-B2）：全端点按 `maintenance:read/write/delete/transition` 分层；创建、指派、日志、流转、验证事件的 operator 均取统一 Principal，body 中伪造 operator 直接 422。
- [x] **P0** `planned_maintenance/router.py` + `aop_router.py` — 旧任务流 17 条与 AOP 年度计划 13 条端点全部只有登录认证，无 `planned_task:*` 功能权限。`[已复核]`
  → 修复（步骤 4E-B3）：30 条端点按 `planned_task:read/write/delete/execute` 分层，覆盖计划、任务、统计、AI/预测生成、AOP 项目/窗口/日历与排程。
- [x] **P0** `workflows/router.py` — 规则 CRUD、初始化与四条触发路径共 14 条端点全部无功能权限；仅持登录身份即可配置和执行跨域自动化。`[已复核]`
  → 修复（步骤 4E-B4）：按 `workflow:read/write/delete/trigger` 分层；HTTP 触发在任何动作执行前还必须满足动作目标域权限（maintenance/planned_task/device write），缺失时整次 403 且零副作用。
- [x] **P0** `auth/router.py` — 用户列表/详情/创建/编辑/密码重置/停用/删除与角色目录只有登录认证，任意已登录用户可管理其他账号。`[已复核]`
  → 修复（步骤 4E-B5A）：按 `user:read/write/delete` 与 `role:read` 分层；委派角色同时要求 `role:write` 且只能授予自身权限子集，禁止 admin:all、重复/不存在角色和修改管理员目标。
- [x] **P0** `system_settings/router.py`、`dashboard/router.py::SLO` 与 `main.py` 系统运维端点仅有登录认证，任意登录用户可修改全局配置/SLO、清缓存、跑诊断或写 Grafana。`[已复核]`
  → 修复（步骤 4E-B5B）：新增 `system_config:read/write`、`slo:read/write`、`system_ops:read/write`；配置只允许 timezone/grafana_url 原子更新，SLO 严格校验，系统运维与 Grafana 按读写分权。
- [x] **P0** `logs/router.py:36` + `logs/log_service.py:47` — `filename` 直接拼进 `log_dir / filename`，`../../` 可读任意文件；同文件 `:74` 的 `clear_old_logs` 无鉴权可删文件。`[已复核]`
  → 修复（步骤 4D）：日志文件解析只接受根目录内的单层 `.log` 文件名，拒绝 `../`、子目录、绝对路径和符号链接逃逸；文件列表不再返回服务器绝对路径，读取/搜索/清理仅遍历安全路径且错误不回显路径。列表/读取/搜索与三条日志 WebSocket 统一使用 `log:read`，清理使用 `log:clear`；参数增加范围限制，HTTP 文件 IO 移入工作线程。
- [x] **P0** `deploy/router.py:76,570`、`templates/template_service.py:171` — 裸 `jinja2.Template` 渲染用户可写模板与变量，无沙箱，等价 SSTI（可达 RCE）。`[已验证]`
  → 修复（步骤 4B）：新增统一 `render_network_template()`，使用 `ImmutableSandboxedEnvironment`，清空默认 globals，阻断 `__class__` / `__globals__` / `cycler` / `lipsum` 逃逸；上下文仅允许 JSON 类型且不可覆盖 `now/now_str/device`，限制模板、上下文、输出大小并拦截超大乘法/指数。Deploy HTTP、DeployService、模板服务和 Deploy WebSocket 全部复用该入口，内置 4 个模板兼容测试通过。
- [x] **P0** `devices/router.py:815` — 用未消毒的 `photo.filename` 拼写入路径（路径穿越写入），且无类型/大小限制、同步 `shutil.copyfileobj` 阻塞事件循环。`[已复核]`
  → 修复（步骤 4C）：照片文件名由服务端 UUID 生成，客户端文件名完全忽略；仅允许 JPEG/PNG/WebP，验证文件魔数并限制 10 MB，分块写临时文件后原子落盘，文件 IO 放入工作线程；上传人固定取可信 Principal，数据库失败自动清理文件。读取/删除均校验路径位于 `storage.photo_dir`，设备照片改走 `device:read` 保护的内容 API，不再暴露真实路径；静态 `/photos` 整目录挂载已移除，floor plan 同步迁到受保护内容 API。
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
- [x] **P1** `services/adk/config.py:118`、`compliance/router.py:521,564,618` — AI API Key 明文入库（字段名却叫 `api_key_encrypted`），并写进进程级 `os.environ`，跨请求污染。`[已复核]`
  → 修复（批次二切片 B）：入库改用 `encrypt_text`（Fernet 加密）——`create_ai_config` 加密存储、`update_ai_config` 显式传 key 才覆盖（None=保留原值）；`test_ai_config` 不再写 `os.environ` 改为直传 `api_key=`；adk `get_model_config` 解密返回 api_key 且不再写进程级 `os.environ`，`create_litellm_model` 与 runner `acompletion` 均 `api_key=` 直传。历史明文 key 经 `decrypt_or_passthrough` 原样透传。`get_ai_config` 仍不回传 api_key。
- [x] **P1** `credentials/router.py:104` — 通过 API 明文返回 SSH 密码；`:41,115` 请求体是裸 `dict`。`[已复核]`
  → 修复（步骤 1）：详情/列表接口一律不返回密码，只给 `has_password` / `has_enable_password` 标志；
    前端本来就没用那个字段（`Credentials.vue` 写的是 `password: ''`），所以零功能损失。
    同时该文件的另三个问题一并解决：四个接口挂上 `credential:*` 权限依赖、请求体换成
    Pydantic 模型、`db = next(get_db())` 换成 `Depends(get_db)`。
  → 连带修复：前端不回填密码后，"留空"必须等于"保持不变"，否则每次编辑都会静默清掉已存的
    enable 密码；清空改为显式 `clear_enable_password`（编辑框下新增勾选项）。
  → 连带修复：`app/cli.py` 的 `backup run` 命令此前硬编码 `admin/admin/admin`，改为走
    `resolve_device_credentials()`。
- [x] **P1** `credentials/credential_service.py:24-38` — Fernet key 由 `jwt_secret` + 固定盐 `b"nas-salt"` 派生：轮换 JWT 密钥即全部设备凭证不可解密，且 `credentials/router.py:96` 已用 try/except 把解密失败兜成空密码。`[已复核]`
  → 修复（批次二切片 B）：新增 `app/shared/crypto.py` 统一入口——密钥材料 `security.encryption_key`（`ENCRYPTION_KEY` 环境变量）优先，未配置时回退 `jwt_secret`（PBKDF2HMAC 派生参数不变，旧密文仍可解）；decrypt 失败且配置了 encryption_key 时回退 legacy `jwt_secret` cipher，密钥轮换不丢数据。`credential_service` 改经 `get_cipher()` / `decrypt_text()`。从此轮换 `JWT_SECRET` 不再影响已存凭证/AI Key 密文。
- [x] **P1** `alerts/router.py:36-56` — `GET /settings` 无鉴权返回 `dingtalk_secret` / webhook / SMTP 用户名。`[已复核]`
  → 修复（步骤 4A）：`GET/POST /settings` 与 `POST /test` 统一挂 `alert:manage`；读取接口仅返回 `has_*` 标志，绝不返回 SMTP 用户名/密码、Webhook 或钉钉 Secret；请求体换成 Pydantic 模型，空敏感字段表示保留，只有显式 `clear_*` 才清除；配置采用临时文件 + `os.replace` 原子写入并重置配置/通知服务缓存。前端同步改为“已配置，留空保留”与显式清除，并用 `alert:manage` 控制菜单入口。
- [x] **P1** `shared/middleware/auth_middleware.py:26` — `skip_paths` 含 `/api/devices`，前缀匹配放过整个设备域；`:57,62` 在中间件里 `raise HTTPException` 不会被 FastAPI 异常处理器接管，实际返回 500 而非 401。`[已复核]`
  → 修复（步骤 3）：删除设备域豁免，公共端点改精确匹配；中间件统一返回 JSON 401/403，并完整校验用户存在、启用状态与会话撤销状态。
- [x] **P1** `services/trap_receiver.py:196` — SNMP Trap 的 community 校验默认关闭，任意主机可伪造 linkDown 改设备状态并自动开工单。`[已复核]`
  → 修复（批次二切片 C）：**fail-closed**——未配置 `SNMP_TRAP_COMMUNITY` 时 `_handle_packet` 直接 return 拒绝全部 Trap，启动时打 ERROR 告警（附交换机配置指引）；`_handle_packet` 改严格比对 `parsed.community == self.community`，配置错误/缺失一律拒绝。AP 监控不受影响：瘦 AP 不支持 SNMP，在线状态由所连交换机上联口 oper_status 派生（`ap_discovery.py`）。
- [x] **P1** `notifications/router.py:37` — 解析不出用户时默认返回 `"Admin"`，匿名请求可读/已读/删除 Admin 的通知。`[已复核]`
  → 修复（步骤 3）：通知接口依赖统一 `Principal`，删除手工 JWT 解码和 `Admin` 回退；部署审计同步改用该身份。
- [x] **P1** `frontend/src/router/index.js:431` — 路由守卫只读 `localStorage.isLoggedIn === 'true'`，无权限判断，手改标志位即可进 `/users`、`/credentials`。`[已复核]`
  → 修复（批次二切片 C）：auth store 增 `permissions` / `permissionsLoaded` 状态与 `fetchMyPermissions()` action（拉 `/permissions/my-permissions`，失败置空不抛）；路由守卫改 async——`admin:all` 短路放行、未加载先拉取、仅当明确持非空权限且缺所需权限时才重定向回首页（空/未加载 = 放行，体验层兜底，后端 `require_permission` 才是真拦截）；9 个敏感路由挂 `meta.permission`（users/credentials/system-settings/permissions/logs/alert-settings/notifications/discovery/compliance）。
- [x] **P2** 多处 `detail=str(e)` 直接回显内部异常（`deploy/router.py:1160`、`devices/router.py:219` 等）。`[已复核]` `[已修复]`（批次十一收尾）：5 个 router 共 12 处 catch-all 统一改「中文通用文案 + 服务端 `logger.error`」，`test_no_leak_detail.py` 7 项回归守卫。

**完成判定**：`auth_enabled=true` 下跑一遍主要写操作，未授权账号应全部 403；日志文件接口对 `../` 返回 400。

### 批次二·安全 · 切片 A · Linux 实测（2026-08-03，HEAD 前 `51ce7cc`）

> 对应 item 78（长尾 authz）。items 115/125 在切片 B，130/133 在切片 C，item 134 按约定延后。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest tests/test_batch2_authz_longtail.py` | ✅ 14 passed（新增） |
| `pytest tests/test_batch1_regressions.py` | ✅ 15 passed |
| 全量 pytest | ✅ 53 failed / 674 passed / 4 skipped —— 失败集合与基线**逐条一致**（24 compliance_service + 11 tool_executor + 8 discovery_service + 3 spare + 2 deploy + 2 auth + 1 email + 1 device + 1 dashboard），无新增失败（passed 660→674 = 新增 14） |
| `frontend validate:locales` + `npm run build` | ✅ 通过（零前端改动，验证性） |

**根因**：批次二步骤 4 高风险主线完成后，Notifications/Jobs/Compliance/Discovery/Scan 五组端点仍是长尾：jobs 与 scan 8+7 端点**全零认证**，compliance 20 端点中 17 个零认证，discovery 仅 `get_current_active_user`（认证无授权），notifications 仅认证。

**改动**：
- `permissions/router.py`：EXTENDED_PERMISSIONS 新增 10 个 code（`notification:read/write`、`job:read/cancel`、`compliance:read/write`、`discovery:read/scan`、`scan:read/write`），startup 增量补齐；PRESET_ROLES operator 追加全部长尾 + `ai:config`（保住 AI 配置入口），viewer 追加只读侧。
- 五组端点按 `require_permission` 挂依赖（`require_permission` 内部执行 `get_current_user_from_token`，**单个依赖同时完成 auth+authz**）：notifications 5（read/write）、jobs 7（read/cancel）、compliance 20（check/read/write/ai:config）、discovery 3（read/scan）、scan PC 侧 5（read/write）。
- **shadowed route 修复**：jobs `/stats`、`/types`、`/statuses` 与 scan `/sessions/active` 移到通配路径 `/{job_id}`、`/sessions/{session_code}` **之前**——此前 GET `/api/jobs/stats`、`/api/scan/sessions/active` 被通配吞掉恒 404。

**行为变化**：
- `auth_enabled=true` 下 jobs/scan/compliance 等端点从"裸奔"变为按权限 401/403；`operator`/`viewer` 预置角色已获对应授权，存量部署 startup 时自动补齐。
- `auth_enabled=false + debug=true` 开发旁路下所有端点行为不变（require_permission 返回 None 放行）。

**保留项 / 说明**：
- **scan gun 侧端点（`POST /sessions/join`、`POST /sessions/items`、`DELETE /sessions/{code}/items/{serial}`）保持开放**：/scanner 终端页是纯 HTML 无登录（兼容旧版 Chromium），扫码枪无法携带 token；这些端点只操作已存在会话，靠 6 位随机会话码 + 30 分钟有效期作凭据。电脑端创建/查询/完成/删除会话已上锁。
- compliance `/standards/upload` 未做移动：无同层 `POST /standards/{x}` 竞争（仅 `/generate-rules`、`/update-rules` 为三层路径），不存在 shadow。
- 既有失败基线中 compliance/discovery 相关失败均为**服务层**测试（test_compliance_service/test_discovery_service），与本次 router 改动无关，未新增。


### 批次二·安全 · 切片 B · Linux 实测（2026-08-03，HEAD 前 `51ce7cc`）

> 对应 item 125（凭证加密独立）+ item 115（AI key 加密）。items 130/133 在切片 C（下块），item 134 按约定延后。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest tests/test_crypto.py` | ✅ 4 passed（新增） |
| `pytest tests/test_ai_config_security.py` | ✅ 8 passed（新增） |
| `pytest tests/test_credential_service.py` | ✅ 12 passed（含回归 2 项：wrong_key 抛错、缺 key 抛 ValueError） |
| `pytest tests/test_batch1_regressions.py` | ✅ 15 passed |
| 全量 pytest | ✅ 53 failed / 686 passed / 4 skipped —— 失败集合与基线**逐条一致**（分布同切片 A 的 53，无新增失败；passed 674→686 = 新增 crypto/ai_config/credential 相关 12） |
| `frontend validate:locales` + `npm run build` | ✅ 通过（零前端改动，验证性） |

**根因**：
- **125**：Fernet key 由 `jwt_secret` + 固定盐派生 → 轮换 JWT 密钥即全部设备凭证/AI Key 不可解密（加密依赖被认证密钥耦合）。
- **115**：AI API Key 明文存 `api_key_encrypted` 字段，且 adk 侧写进程级 `os.environ` 供 LiteLLM 读取 → 明文落库 + 跨请求污染 + test 端点也污染环境。

**改动**：
- `shared/config.py`：`SecurityConfig` 新增 `encryption_key: Optional[str] = None`，`_apply_security_env_overrides` 读 `ENCRYPTION_KEY`（`.env.example:38` 声明的死变量正式生效）。
- `shared/crypto.py`（新）：`_derive_fernet`（PBKDF2HMAC SHA256/32/salt=b"nas-salt"/100000，与历史一致）；`get_cipher`（encryption_key 优先否则 jwt_secret）、`get_legacy_cipher`（恒 jwt_secret，供解密旧密文回退）、`encrypt_text`/`decrypt_text`（新 cipher 失败且配置了 encryption_key 时回退 legacy）、`decrypt_or_passthrough`（非 Fernet 明文原样返回，兼容历史明文 AI Key）。
- `credentials/credential_service.py`：cipher 改经 `get_cipher(self.config)`，`decrypt_password` 用 `decrypt_text(..., self.config)`——**保留 mock 能力**（crypto 函数支持显式传 config，既有测试的 `patch(get_config)` 依旧生效）。
- `compliance/router.py`：create 用 `encrypt_text(request.api_key) if request.api_key else None`；update 用 `if request.api_key is not None:` 显式覆盖（None=保留原值）；test_ai_config 删 `os.environ` 块、`litellm.completion` 直传 `api_key=request.api_key`；get_ai_config 仍不回传 api_key。
- `services/adk/config.py`：get_model_config 删 `os.environ` 写入，改 `result["api_key"] = decrypt_or_passthrough(config.api_key_encrypted)`；create_litellm_model 加 `api_key=config_dict.get("api_key")`。
- `services/adk/runner.py`：`acompletion(...)` 加 `api_key=model_config.get("api_key")`。

**行为变化**：
- AI Key 与设备密码密文现由独立 `encryption_key` 保护；未配置时行为与历史完全一致（回退 jwt_secret），存量密文零迁移即可解。
- `auth_enabled` 无关（纯数据层改动）；AI 调用链路不再依赖进程级 `os.environ`，避免并发请求 key 互相污染。

**保留项 / 说明**：
- `JWT_SECRET` 轮换流程不变；生产建议通过 `ENCRYPTION_KEY` 单独设置持久加密密钥后再轮换 JWT。
- `decrypt_or_passthrough` 仅用于 AI key 消费侧（兼容历史明文）；凭证侧仍严格要求 Fernet 密文，解密失败按既有逻辑兜底。
- 既有失败基线中 credential 相关 2 项（wrong_key / 缺 key）为**本次修复后回归通过**的项，不再属于基线。


### 批次二·安全 · 切片 C · Linux 实测（2026-08-03，HEAD `0d1b199`）

> 对应 item 130（trap fail-closed）+ item 133（前端守卫缺权限）。item 134 按约定延后。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest tests/test_lifecycle_batch3.py` | ✅ 全过（含新增 TestTrapCommunityFailClosed 2 项） |
| `pytest tests/test_batch2_frontend_guard.py` | ✅ 8 passed（新增） |
| `pytest tests/test_batch1_regressions.py` | ✅ 15 passed |
| 全量 pytest | ✅ 53 failed / 696 passed / 4 skipped —— 失败集合与基线**逐条一致**（分布同切片 A/B 的 53，无新增失败；passed 686→696 = 新增前端守卫 8 + trap 2） |
| `frontend validate:locales` + `npm run build` | ✅ 通过（本次有前端改动，真实构建） |

**根因**：
- **130**：Trap community 校验默认关闭（`if self.community and ...` 留空即放行），任意主机可伪造 linkDown/linkUp 改设备状态并自动开工单。
- **133**：前端路由守卫只读 `localStorage.isLoggedIn === 'true'`，无权限判断，手改标志位即可直达 `/users`、`/credentials` 等敏感页。

**改动**：
- `trap_receiver.py`：模块 docstring 补 fail-closed 说明；`start()` 在 community 为空时打 **ERROR 告警**（含交换机配置指引）；`_handle_packet` 改为**先判 `if not self.community:` 直接 return（拒绝全部）**，再严格比对 `parsed.get("community") != self.community`，配置缺失/错误一律拒绝。
- `stores/auth.js`：state 加 `permissions: []`、`permissionsLoaded: false`；action `async fetchMyPermissions()` 拉 `/permissions/my-permissions`（失败置空且仍置 loaded，不抛错）；`clearAuth()` 清 permissions。
- `router/index.js`：`beforeEach` 改 async——`meta.permission` 存在时：未加载先 `await fetchMyPermissions()`；**`permissions.includes('admin:all')` 短路放行**（`get_user_all_permissions` 对超管只回 `["admin:all"]` 不展开，不短路会锁死超管）；仅当权限非空且缺所需权限才 `next('/')`；空/未加载 = 放行。
- 9 个敏感路由挂 `meta.permission`：`/users→user:read`、`/credentials→credential:read`、`/system-settings→system_config:read`、`/permissions→role:read`、`/logs→log:read`、`/alert-settings→alert:manage`、`/notifications→notification:read`、`/discovery→discovery:read`、`/compliance→compliance:read`（codes 均已在批次二步骤 4 权限表内，startup 增量补齐）。

**行为变化**：
- 未配置 `SNMP_TRAP_COMMUNITY` 时 Trap 全部拒绝（fail-closed）并在启动日志打 ERROR；配置后仅接受匹配 community 的 Trap。
- 前端手改 `isLoggedIn` 无法再直达敏感页；超管/空权限/权限拉取失败均不受影响（体验层兜底，后端 `require_permission` 才是真拦截）。

**保留项 / 说明**：
- **AP 监控不受影响**：瘦 AP 不支持 SNMP，在线状态由所连交换机上联口 oper_status 派生（`ap_discovery.py:116-151`），与 Trap 接收器无关。
- 前端守卫是**体验层兜底**：`auth_enabled=false + debug=true` 开发旁路下守卫仍照常拉权限，但后端旁路放行；空/未加载放行约定与 `Layout.vue` nav 过滤一致（权限表未初始化/拉取失败不锁死 UI）。
- `/scanner` 终端页无 `meta.permission`（扫码枪无登录），不参与守卫。
- item 134（`detail=str(e)` 内部异常回显）已于批次十一修复（2026-08-04）。


### 批次二·步骤5 · 切片 A · Linux 实测（2026-08-03，HEAD 前 `465bd35`）

> 步骤 5 切片 A：备份会话级 SSH 凭证（操作者手输、密码不落服务器）+ 备份提醒（不再自动）+ 需备份统一列表。
> 切片 B（部署操作者凭证 + 二次确认 + 下线 celery 异步备份/定时部署）单独提交。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest tests/test_typed_credentials_security.py` | ✅ 10 passed（新增：无凭证 400 / 认证失败 401、批量 auth_failed 标记、needs-backup 两类原因、`credential_session_required=False` 降级回退、async 端点已移除） |
| `pytest tests/test_backups_templates_security_step4e.py` | ✅ 21 passed（权限矩阵含 needs-backup/mark-config-changed；redaction/batch 测试改操作者凭证 payload；`backup_uses_principal_as_operator` 补传凭证） |
| `pytest tests/test_batch1_regressions.py` | ✅ 15 passed |
| 全量 pytest | ✅ 53 failed / 706 passed / 4 skipped —— 失败集合与基线**逐条一致**（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1 = 53，零新增；passed 696→706 = 新增 10 项） |
| `frontend validate:locales` + `npm run build` | ✅ 通过（3237 zh/en 键一致，真实构建） |
| alembic | ✅ `heads` = `5e6a7b8c9d0e`（基于 `5d16fa030a9a`） |

**根因**：
- 备份接口此前直接解密服务器存储的 `CredentialGroup` 凭证 → 违背"操作者密码不落服务器"；且备份完全自动化，无"超期未备份 / 配置变更后需备份"的提醒通道。
- celery 异步备份 `backup_device` 无法携带浏览器会话凭证，与"密码不落服务器"互斥（切片 B 一并下线；本切片已删除 `POST /backup/{device_id}/async`）。

**改动**：
- **数据/配置**：`devices.config_changed_at` 迁移（`5e6a7b8c9d0e`）；`SecurityConfig` 增 `credential_session_required=True`（默认要求操作者凭证，False 才显式降级回退服务器凭证组）与 `backup_reminder_days=7`；env 覆盖 `CREDENTIAL_SESSION_REQUIRED` / `BACKUP_REMINDER_DAYS`。
- **备份 router**：单台/批量备份请求体改 `BackupRequest` / `BatchBackupRequest{device_ids, username?, password?, secret?}`；操作者凭证优先（仅请求内存），未提供且开关开 → 400；`NetmikoAuthenticationException` → 单台 401 / 批量 `auth_failed` 标记（不中断整批），响应与日志不含任何口令。
- **needs-backup**：`GET /api/backups/needs-backup`（`require_backup_read`）统一需备份列表——config_changed（部署成功/手动标记后未备份）或 backup_overdue（超 `backup_reminder_days` 未备份），仅统计 `deployment_status=='in-use'`；`POST /api/backups/mark-config-changed`（`require_backup_execute`）手动标记配置已变更。
- **部署 hook**：deploy_stream_service（WS 流）与 `create_deploy_history`（HTTP）在成功部署后置 `config_changed_at=now` → 设备自动进入需备份列表。
- **前端**：`useSessionCredentials.js`（sessionStorage 读写 `session_ssh_*`）+ `SSHCredentialDialog.vue`（form-section el-dialog，缺凭证弹一次存会话复用，明示密码不落服务器）；Backups.vue 新增「需备份」区（多选批量备份 / 标记配置已变更，认证失败设备可重试）；Devices.vue 单台/批量备份改走凭证对话框；i18n 全部进 locales。

**行为变化**：
- 默认配置下备份必须携带操作者 SSH 凭证，未提供返回 400；密码仅存于浏览器 sessionStorage / 请求内存，关闭标签页或登出即消失。
- 备份不再静默自动化：超期未备份或配置变更后设备进入「需备份」列表，由管理员统一批量备份。

**保留项 / 说明**：
- `CredentialGroup`（服务器存储凭证）保留但作为**显式降级回退**：仅 `credential_session_required=False` 时使用；默认 True 拒绝无操作者凭证的请求。
- sessionStorage 边界：刷新保留、关标签/登出清除——凭证会话边界即"浏览器会话"。


### 批次二·步骤5 · 切片 B · Linux 实测（2026-08-03，HEAD 前 `bea483d`）

> 步骤 5 切片 B：部署/回滚操作者会话级 SSH 凭证（单组 default 覆盖全部目标设备）+ 高危操作二次确认 + 下线 celery 异步备份/定时部署。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest tests/test_typed_credentials_security.py` | ✅ 21 passed（切片 A 10 + 切片 B 新增 11：build_operator_credential_groups 单 default 组 / 拒绝部分填写 / 空返 None；resolve_operator_credentials 开关开→400、关→None 降级、带凭证透传；回滚端点无凭证→400；/schedule 端点与 schema 已移除；celery 不再注册 backup/deploy_tasks） |
| `pytest tests/test_backups_templates_security_step4e.py` | ✅ 21 passed（异步 job 脱敏测试改写为同步 HTTP 路径等价覆盖：成功响应/LogEntry 不含绝对路径、失败归一封皮） |
| `pytest tests/test_batch1_regressions.py` | ✅ 15 passed（async `backup_device.apply` 改写为同步 `run_device_op(backup_device_config)` 等价覆盖，调用时经模块属性解析取到 monkeypatch 实现） |
| `pytest tests/test_deploy_security_step4b.py` | ✅ 通过（移除 ScheduleDeployRequest 测试与权限矩阵 `schedule_deploy` 项） |
| 全量 pytest | ✅ 53 failed / 716 passed / 4 skipped —— 失败集合与基线**逐条一致**（分布同切片 A 的 53，零新增；passed 706→716 = 新增切片 B 11 项 − 移除 schedule schema 测试 1 项） |
| `frontend validate:locales` + `npm run build` | ✅ 通过（3237 zh/en 键一致，真实构建，Deploy 路由产物正常） |

**改动**：
- **部署/回滚凭证**：`DeployRequest` / `RollbackRequest` / WS `start_deploy` 增加可选 `credentials{username?, password?, secret?}`；新 `app/features/deploy/operator_credentials.py` 的 `resolve_operator_credentials` 构建**单个 `name='default'` 操作者凭证组**覆盖全部目标设备（各 deploy 服务按 `device.credential_group` 名匹配并回退 `'default'`，单个 default 组即可覆盖全部设备）；`credential_session_required=True`（默认）未携带 → 400「请使用操作者 SSH 凭证（密码不存储在服务器上）」；`False` 才回退服务器存储 CredentialGroup 解密；部分填写（用户名/密码缺一）→ 400，不静默降级。凭证仅存于请求/WS 会话/线程内存，不落库、不入日志（部署日志仍只记用户名）。
- **二次确认**：前端执行部署/回滚前 `ElMessageBox.confirm` 明示「高危操作：即将使用当前操作者 SSH 凭证…（密码仅本次会话，不存储在服务器上）」；Deploy.vue 缺凭证先弹 `SSHCredentialDialog`（sessionStorage 复用），取消则中止；`useDeployExecution.executeDeploy/handleRollback` 经 `hooks.ensureCredentials` 收集并在 WS/回滚请求携带凭证。
- **下线异步/定时部署**：删除 `POST /api/deploy/schedule` 与 `ScheduleDeployRequest`（`POST /backup/{device_id}/async` 切片 A 已删）；`git rm app/tasks/backup_tasks.py` `app/tasks/deploy_tasks.py`；celery_app.py imports/task_routes 移除两条 `device_ops` 路由；tasks `__all__` 移除二者；前端移除 Deploy.vue 排程 UI（`DeployScheduleDialog.vue`、api `getMaintenanceWindows`/`scheduleDeploy`、DeployPreviewDialog Schedule 按钮）。

**行为变化**：
- 默认配置下部署/回滚/备份都必须携带操作者 SSH 凭证，未提供返回 400；凭证仅存于浏览器 sessionStorage / WS 会话 / 请求内存，关闭标签页或登出即消失。
- 备份与部署全部走同步端点，不再有 celery 异步设备操作；定时部署功能下线（异步 worker 无法携带操作者会话凭证，与"密码不落服务器"互斥）。

**保留项 / 说明**：
- `CredentialGroup` 保留但仅 `credential_session_required=False` 时显式降级使用（默认 True 拒绝无操作者凭证请求）。
- **残留风险（已解决）**：切片 B 曾 flag `websocket/router.py:253` 的 legacy `action == 'deploy'` WS handler 无认证（不校验 access_token / 权限），直接使用服务器存储 CredentialGroup，且前端未调用（死代码）。已于步骤 5 收尾切片整块下线（见下方实测）。
- WS `start_deploy` 凭证缺失时被外层 `except Exception` 归一封皮为通用错误消息「部署处理失败，请查看服务端日志」；前端总是先收集凭证再开 WS（`executeDeploy` 内 `ensureCredentials` 拦截），该路径为纵深防御，不影响正常流程。


### 批次二·步骤5 · legacy `/ws/cli` 下线 · Linux 实测（2026-08-04，HEAD 前 `54bbbb0`）

> 步骤 5 收尾：整块下线 legacy `/ws/cli/{session_id}` 无认证部署路径（方法 1，即切片 B 曾 flag 的残留风险）。前端从未接入该端点（自引入即死代码，部署进度走 `/ws/deploy/` 的 `start_deploy`），无前端改动。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest tests/test_batch1_regressions.py` | ✅ 14 passed（移除 `test_napalm_service_module_has_asyncio`——其守护对象 `NapalmStreamService` 已随本切片删除，P0-5 回归点由删码消解；15 → 14 为预期） |
| `pytest tests/test_typed_credentials_security.py` | ✅ 21 passed（不受影响） |
| `pytest tests/test_deploy_security_step4b.py` + `test_backups_templates_security_step4e.py` | ✅ 30 + 21 passed（WS 部署测试走 `/ws/deploy/`，与 `/ws/cli/` 零耦合） |
| 全量 pytest | ✅ **53 failed / 715 passed / 4 skipped** —— 失败集合与基线**逐条一致**（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1 = 53，零新增；passed 716→715 = 移除 batch1 asyncio 用例 1 项） |
| `frontend validate:locales` + `npm run build` | ✅ 通过（3237 zh/en 键一致，真实构建 13.86s） |
| 模块导入 | ✅ `websocket.router` / `napalm_service` 干净导入；WS 路由仅剩 `/ws/deploy/{session_id}`、`/ws/device-status`、`/ws/logs`、`/ws/logs/{operation}` |

**改动**：
- **删除端点**：`websocket/router.py` 移除 `@router.websocket("/ws/cli/{session_id}")` 的 `websocket_cli_stream` 整个函数（含无认证的 `action == 'deploy'` 分支与 `action == 'ping'`）及仅该分支使用的 `parse_config_to_commands`；`datetime` 导入保留（`start_deploy` 仍用）。
- **删除服务**：`git rm app/features/deploy/cli_stream_service.py`（`stream_netmiko_deploy` / `get_cli_stream_service` 仅被该端点引用）；`napalm_service.py` 删除 `NapalmStreamService` 类与 `get_napalm_stream_service`（`stream_napalm_deploy` 仅被该端点引用），随之失用的 `import asyncio` / `from datetime import datetime` 一并移除（`time` / `Dict` 原本即未用，同块清理；`List` / `Optional` 仍被 `NapalmDeployService` 使用保留）。

**行为变化**：
- WebSocket 部署仅剩 `/ws/deploy/{session_id}` 一条路径，全部走鉴权（`authorize_deploy_token` 校验 access_token + `config:deploy` 权限）+ 操作者会话级 SSH 凭证；仓库内不再存在任何无认证、直接解密服务器 CredentialGroup 的部署入口。

**遗留说明**：
- `NapalmStreamService.driver_map` 早在批次六切片 C 已删，本次删除的是该类的剩余主体；`docs/CODE_REVIEW_ISSUES.md:21` 的 P0 项（napalm_service 缺 `import asyncio`）已追加"由删码消解"的跟进说明。


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

**步骤 4A 测试系统 Linux 实测补充（2026-08-01，HEAD `a9721ce`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_alert_settings_security.py` 17/17；相邻回归
  52/52（步骤 3 + 凭证/SSO/批次一）；全量 pytest **53 failed / 441 passed / 4 skipped / 0 errors**
  （失败集合与基线一致，无新增；通过数较上次 424 增 +17 = 新增 alerts 测试）。
- ✅ 真实 API smoke test：未认证 `GET /api/alerts/settings` 401；viewer（无 `alert:manage`）
  GET/POST 均 403；admin GET 200 且响应脱敏（SMTP/Webhook/钉钉仅返回 `has_*` 标志，绝不回传
  secret）；admin POST 最小改动 200 且空敏感字段保留；保存触发 config.yaml 原子重写后
  `auth_enabled`/`jwt_secret` 等安全配置保留、服务正常。
- 未执行：浏览器端（D）、Docker（E）、用户归属审计（F）同前。

**步骤 4B 验证结果（2026-08-01）**：✅ Deploy HTTP 权限矩阵完成：preview/variables/windows/history
使用 `config:read`，execute/schedule 使用 `config:deploy`，rollback 使用 `config:rollback`，删除历史保留
`deploy_history:delete`；✅ 主部署 WebSocket 在访问设备/凭证前校验 JWT + `config:deploy`，前端首条消息携带
access token，部署历史、审计与工具日志统一记录 token 用户名；✅ HTTP 与流式 Netmiko/NAPALM 均在设备连接前执行命令守卫；
✅ Deploy 请求改用 Pydantic 模型，限制 mode/engine/并发/设备数/维护窗口/额外字段；✅ 所有客户端和数据库来源的
备份路径均约束在 `storage.backup_dir`，拒绝 `../`、根目录外绝对路径与符号链接逃逸；
✅ `tests/test_deploy_security_step4b.py` + `tests/test_secure_template_renderer.py` 为 **44 passed / 1 skipped**
（Windows 无符号链接权限时跳过），相邻回归新增代码无失败，Ruff 与 `app.main` 导入通过；
✅ Windows 全量 pytest 为 **54 failed / 484 passed / 5 skipped / 10 errors**，失败集合仍为既存基线。
⚠️ 本机未安装 `frontend/node_modules`，Vite build 未执行；`tests/test_deploy_service.py` 仍有 2 个旧模块 patch 路径失败。

**步骤 4B 测试系统 Linux 实测补充（2026-08-01，HEAD `0de278c`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_deploy_security_step4b.py` + `test_secure_template_renderer.py`
  **48 passed**（Linux 全过无 skip，Windows 为 44 passed/1 skipped）；相邻回归 69 项全过
  （批次一/步骤3/凭证/SSO/alerts）；全量 pytest **53 failed / 489 passed / 4 skipped / 0 errors**，
  失败集合与 4A 基线逐项一致（compliance 24 / tool_executor 11 / discovery 8 / spare 3 /
  deploy 2（`tests/test_deploy_service.py` 旧模块 patch 路径）/ auth 2 / email 1 / device 1 /
  dashboard 1），无新增失败；通过数较 4A 增 +48 = 新增 4B 测试。
- ✅ 真实 API 权限矩阵：临时建 `smoke_reader`（仅 `config:read`）与 `smoke_deployer`（operator：
  `config:read`+`config:deploy`+`config:rollback`）。smoke_reader 对 preview/variables/windows/history
  均 200，execute/schedule/rollback 均 403；smoke_deployer 与 admin 越过权限后进入业务校验
  （execute 设备不存在 404「未找到指定的设备」）；schedule 200。
- ✅ WebSocket `/ws/deploy/{sid}`：无 token → `deploy_error` 401 并关闭 4401；伪造 token → 401/4401；
  仅 `config:read` 的 token → 403/4403；`config:deploy` token 通过鉴权后才进入设备/凭证流程（设备 999
  直接业务报错）。所有拒绝均发生在凭证读取与设备连接之前（`authorize_deploy_token` 位于凭证查询之前）。
- ✅ 实验设备 dry-run 身份归属：smoke_deployer 对实验设备 pnetlab-swr（192.168.4.1，SSH 22 可达）经 WebSocket
  dry-run 部署（业务结果因凭证不匹配失败），写入 `DeployHistory` id=52 `username='smoke_deployer'`、
  `user_id=7`，`LogEntry` id=115 `created_by='smoke_deployer'`，与 token 用户一致；旧记录中的
  `operator/created_by='Web'` 为修复前历史数据，源码级检查确认新写入不再产生。
- ✅ 路径穿越：HTTP `POST /api/deploy/preview` 合法备份文件 200；`../../../../etc/passwd` 与 `/etc/passwd`
  均 400「备份文件路径超出允许目录」；WebSocket `mode=backup` 相同两例均返回 `deploy_error`
  「备份文件路径超出允许目录」；符号链接逃逸由 `test_backup_path_rejects_symlink_escape_when_supported` 覆盖。
- ✅ SSTI：直接渲染 `render_network_template()` 与经 HTTP template-preview 双路径验证，
  `__class__.__mro__`、`__subclasses__`、`cycler`/`lipsum` 的 `os.popen`、`10 ** 100000`、
  `'A' * 100000000` 全部拒绝（「模板包含不安全表达式」/「模板语法或渲染无效」），未执行任何系统命令。
- ✅ 模板兼容：四个内置模板（id 1/3/4/5）以样例变量渲染全部 OK；循环遍历上下文变量、`if/elif` 条件、
  `default` 过滤器、`now()`/`now_str`、缺失变量留空均兼容。已知限制：沙箱清空 globals 后 `range()`
  不可用（内置模板不使用，单元测试亦按变量循环设计）。
- ✅ 前端构建：`npm run build` 成功（13.88s，仅既有 chunk 体积告警）。
- ⚠️ 浏览器 Deploy 页手动验证（D）未执行，需真实浏览器与前端交互。

**步骤 4B 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、两个 4B 测试文件、批次一及全量 pytest，失败集合不得新增
- [x] `config:read` 用户只能 preview/variables/windows/history，execute/schedule/rollback 均 403
- [x] `config:deploy` 用户可通过 WebSocket 连接并执行**实验设备 dry-run**，历史与 LogEntry 用户名必须等于 token 用户
- [x] 无 token、伪造 token、仅 `config:read` 的 WebSocket 部署分别被拒绝，且拒绝前不得读取凭证或连接设备
- [x] `../`、根目录外绝对路径、符号链接逃逸在 HTTP 与 WebSocket 均被拒绝
- [x] SSTI payload（`__class__`、`__globals__`、`cycler`、`lipsum`、超大乘法/指数）全部被拒绝且不执行系统命令
- [x] 四个内置模板与现有用户模板抽样渲染正常；循环、条件、default、`now()/now_str` 和缺失变量兼容
- [ ] 浏览器 Deploy 页 preview/历史/预约/回滚权限表现正确，WebSocket 断线与 401/403 提示可理解
- [x] 前端环境可用时执行 `npm ci && npm run build`

**步骤 4C 验证结果（2026-08-02）**：✅ Devices 的 34 个 HTTP 端点全部挂功能权限：
查询/指标/详情/接口/拓扑读使用 `device:read`，探测/监控触发/SNMP/接口发现与更新使用
`device:write`，删除/导入/导出/照片分别使用 `device:delete/import/export/photo`；
✅ `/ws/device-status` 使用首条消息 JWT + `device:read` 鉴权，无 token/无权限关闭 4401/4403；
✅ Element Plus 上传携带 Bearer、字段名固定为 photo，前端限制 MIME/10 MB；照片与 floor plan 使用认证 Axios Blob URL，
所有旧原生 Axios 设备调用切到统一认证客户端，静态 `/photos` 不再挂载；✅ Excel 导入限制 10 MB 并在线程中解析；
✅ `tests/test_device_security_step4c.py` 为 **29 passed / 1 skipped**（Windows 符号链接权限），
相邻绿色回归 **145 passed / 2 skipped**，Ruff 与 `app.main` 导入通过；
✅ Windows 全量 pytest 为 **54 failed / 516 passed / 6 skipped / 10 errors**，失败集合仍为既存基线。
⚠️ 本机无 `frontend/node_modules`，前端 build 交由测试系统执行。

**步骤 4C 测试系统 Linux 实测补充（2026-08-02，HEAD `fddd3cb`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_device_security_step4c.py` **30 passed**（Linux 全过无 skip，
  Windows 为 29 passed/1 skipped）；相邻回归 117 项全过（批次一/步骤3/凭证/SSO/alerts/4B）；
  全量 pytest **53 failed / 519 passed / 4 skipped / 0 errors**，失败集合与 4B 基线逐项
  diff 完全一致（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 /
  auth 2 / email 1 / device 1 / dashboard 1），无新增失败；通过数较 4B 增 +30 = 新增 4C 测试。
- ✅ 真实 API 权限矩阵：新建 dev_reader/…/dev_photographer 六种最小权限账号（各自仅持单一
  device:read/write/delete/import/export/photo）逐端点探测 14 个代表端点——全部 read 端点
  （列表/详情/vendors/统计/监控/照片列表）reader 200、writer 403；export 200/403；write 端点
  （test-reachability/check-reachability/interfaces discover/discover-neighbors）writer 200 或
  404（设备不存在，权限已过）、reader 403；import 400（文件解析，权限已过）/403；delete 404/403；
  photo 上传与删除 404/403；admin 全部放行。跨权限均 403，无一例外。
- ✅ 照片上传安全：恶意文件名 `../../../evil.jpg` + 伪造 `uploader=forged-admin` → 200，服务端
  生成 UUID 文件名 `3817f1350a2c41b89adcce4fba3a177e.jpg`（无穿越），DB 记录 `uploader=dev_photographer`
  （伪造名被忽略）；HTML 伪装 JPEG、空文件、>10 MB、错误 content-type 全部 400；被拒上传不落盘，
  上传/删除后 assets/devices 无孤儿文件。
- ✅ 内容访问与旧静态路径：reader 经内容 API 取照 200 `image/jpeg`，writer 403；删除照片 200 且文件与
  DB 记录同步清除；直接请求旧 `/photos/...` 经认证返回 404（静态挂载已移除，OpenAPI 无独立 /photos 路由）。
- ✅ `/ws/device-status`：无 token → `auth_error` 401 关闭 4401；伪造 token → 401/4401；仅
  device:write → 403/4403；device:read → `authenticated`（username=dev_reader）+ ping/pong 正常。
- ✅ floor plan 内容 API：`GET /api/floor-plans/10/content` 对 floor_plan:read 或 device:read 均 200
  `image/jpeg`；把 image_path 临时指向 `/etc/hostname`（存储根目录外）→ 400，还原后恢复 200。
- ✅ 前端构建：`npm run build` 成功（13.75s，仅既有 chunk 体积告警）。
- ⚠️ 浏览器端照片上传/预览/删除、接口流量图、批量邻居发现与 3D 底图 Bearer 行为（D）未执行，
  需真实浏览器与前端交互。

**步骤 4C 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_device_security_step4c.py`、批次一和全量 pytest，失败集合不得新增
- [x] 使用 read/write/delete/import/export/photo 六种最小权限账号验证 34 个端点矩阵，跨权限均应 403
- [x] 照片上传测试恶意文件名、伪造 uploader、错误 MIME/魔数、空文件、>10 MB、`../`/绝对路径/符号链接；不得产生孤儿文件
- [x] reader 能通过内容 API 查看照片，writer 不能；直接请求旧 `/photos/...` 必须 404，不能绕过 `device:read`
- [x] `/ws/device-status` 无 token、伪造 token、仅 device:write 分别拒绝；device:read 能认证并接收 ping/pong 与状态推送
- [ ] 浏览器验证照片上传/预览/删除、接口流量图、批量邻居发现和 3D 底图均携带 Bearer 且可用
- [x] floor plan 内容 API 对 `floor_plan:read` 或 `device:read` 可用，存储根目录外路径必须 400
- [x] 前端环境执行 `npm ci && npm run build`

**步骤 4D 验证结果（2026-08-02）**：✅ `tests/test_logs_security_step4d.py` + 既有
`tests/test_log_service.py` 为 **40 passed / 1 skipped**（Windows 符号链接权限）；
✅ `/api/logs` 列表/文件/读取/搜索使用 `log:read`，清理使用 `log:clear`，真实 HTTP 测试覆盖
未认证 401、跨权限 403、管理员 200 与参数 422；✅ `/api/logs/ws`、`/ws/logs`、
`/ws/logs/{operation}` 均以首条 JSON 消息校验 JWT + `log:read`，无 token/无权限关闭 4401/4403；
✅ 文件 tail 改为 `asyncio.to_thread` 增量轮询，移除事件循环中的 `time.sleep`；回调连接在所有退出路径清理；
✅ 相邻安全回归 **169 passed / 3 skipped**，Ruff 与 `app.main` 导入通过；
✅ Windows 全量 pytest 为 **54 failed / 537 passed / 7 skipped / 10 errors**，失败集合仍为既存基线。
⚠️ 本机无 `frontend/node_modules`，前端 build 交由测试系统执行。

**步骤 4D 测试系统 Linux 实测补充（2026-08-02，HEAD `b23db4e`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_logs_security_step4d.py` + `test_log_service.py` **42 passed**
  （Linux 全过无 skip）；批次一 147 项全过；全量 pytest **53 failed / 541 passed / 4 skipped / 0 errors**，
  失败集合与 4B/4C 基线逐项 diff 完全一致（compliance 24 / tool_executor 11 / discovery 8 / spare 3 /
  deploy 2 / auth 2 / email 1 / device 1 / dashboard 1），无新增失败；通过数较 4C 增 +22 = 新增 4D 测试。
- ✅ 真实 API 权限矩阵：新建 log_reader（仅 log:read）、log_clearer（仅 log:clear）两最小权限账号逐端点
  探测——GET /api/logs、/api/logs/files、/api/logs/files/{filename}、/api/logs/search 均 reader 200、
  clearer 403、admin 200；POST /api/logs/clear 为 clearer 200、reader 403、admin 200。跨权限一律 403。
- ✅ 路径穿越/文件名约束：`../backend.log`、URL 编码 `..%2Fbackend.log`、绝对路径 `%2Fetc%2Fhostname`、
  子目录 `sub%2Fbackend.log` 全部 404；`..%252Fbackend.log`（双重编码）按字面文件名解析、无逃逸、
  200 返回空列表；`api.txt` → 400 “仅允许读取 .log 文件”；合法 `api.log?lines=5` → 200。错误响应均为
  通用文案，不含服务器路径。符号链接逃逸由单测 `test_log_path_rejects_symlink_escape_when_supported` 覆盖通过。
- ✅ 文件列表不泄露路径：`GET /api/logs/files?days=365` 返回全部 4 个文件（uvicorn.log / backend.log /
  api.log / server.log），仅文件名+大小+修改时间，无绝对路径；默认 `days=7` 正确排除 17–82 天前的旧文件
  （符合 7 天窗口语义，非缺陷）。
- ✅ 三条日志 WebSocket（/api/logs/ws、/ws/logs、/ws/logs/{operation}）：无 token → `auth_error` 401
  关闭 4401；伪造 token → 401/4401；仅 log:clear → 403/4403；log:read → `authenticated`
  （username=log_reader）且 /api/logs/ws、/ws/logs 均 ping/pong 正常。
- ✅ 认证超时清理：/api/logs/ws 连接后不发首条消息，服务端 10 秒超时自动关闭 4401；多次连接/断开后
  事件循环保持响应，后续请求全部正常，manager 无残余连接干扰。
- ✅ 前端构建：`npm run build` 成功（14.05s，仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 Logs 页列表/搜索/文件查看/清理按钮交互未执行，需真实浏览器验证。

**步骤 4D 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_logs_security_step4d.py`、`test_log_service.py`、批次一和全量 pytest，失败集合不得新增
- [x] `log:read` 只能列表/读取/搜索，`log:clear` 只能清理；跨权限 403，管理员全部放行
- [x] HTTP 测试 `../`、URL 编码 traversal、绝对路径、子目录、非 `.log`、符号链接逃逸，均不得读取根目录外内容
- [x] 日志文件列表/错误响应/服务日志不得泄露绝对路径
- [x] 三条日志 WebSocket 分别验证无 token、伪造 token、仅 log:clear 为 401/403/4401/4403；log:read 可认证并 ping/pong
- [x] 连接断开、认证超时和异常时 callback/ConnectionManager 不留残余连接，事件循环保持响应
- [ ] 浏览器 Logs 页列表、搜索、文件查看、清理按钮权限与 401/403 提示正常
- [x] 前端环境执行 `npm ci && npm run build`

**步骤 4E-A 验证结果（2026-08-02）**：✅ Backups 的列表/内容/差异/下载使用 `backup:read`，
同步与异步执行使用 `backup:execute`，批量执行使用 `backup:batch`，删除使用 `backup:delete`；operator
只取可信 Principal，前端不再发送 `Web`；所有 Netmiko、通知、Git 提交和文件读取均移入工作线程；
✅ 新备份目录与文件名只使用服务端设备 ID，读/下载/差异/删除均约束在 `storage.backup_dir`，
拒绝 `../`、根目录外绝对路径与符号链接逃逸，并以 5 MB 上限读取；列表、diff、下载文件名、HTTP
错误和 Celery Job 结果不再泄露服务器绝对路径或底层异常；认证 Blob 下载替换原先不存在且不带 Bearer
的直接链接；✅ 批量请求限制 1–100 个正整数 ID，列表分页增加范围限制；✅ Templates 的读/写/删/渲染
分别使用 `template:read/write/delete/render`，Create/Update/Render 使用拒绝额外字段且有大小上限的 Pydantic
模型，服务层仅允许模型字段，继续复用 4B 不可变 Jinja 沙箱；✅ 菜单可见性改用功能 read 权限；
✅ `tests/test_backups_templates_security_step4e.py` 为 **20 passed / 1 skipped**（Windows 符号链接权限），
既有 Backups/Templates/Netmiko 与异步任务回归合计 **65 passed / 1 skipped**，全部安全切片
**117 passed / 4 skipped**；Ruff 与 `app.main` 导入通过；
✅ Windows 可比较全量 pytest（排除既有挂起的 `test_console_service.py`）为
**54 failed / 557 passed / 8 skipped / 10 errors**，相对 4D 恰好新增 20 passed / 1 skipped，
失败/错误集合不变。⚠️ 原始全量命令仍挂在既有 console 测试；本机 `frontend/node_modules` 不完整，
`npm run build` 因找不到 Vite 未执行成功，交由测试系统执行。

**步骤 4E-A 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_backups_templates_security_step4e.py` **21 passed**；批次一 15 项全过；
  全量 pytest **53 failed / 625 passed / 4 skipped**，失败集合与 4D 基线逐项 diff 完全一致
  （compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1），无新增失败。
- ✅ 真实 API 权限矩阵（`/tmp/smoke_4ea_backups_templates.py` 全过）：新建 backup read/execute/batch/delete 与
  template read/write/delete/render 最小权限账号逐端点探测——Backups 列表/内容/下载/差异=reader 200、
  同步与异步执行=executor、批量=batcher、删除=deleter；Templates 列表=reader、创建=writer、删除=deleter、
  渲染=renderer；跨权限一律 403、管理员全放行。
- ✅ 下载必须携带 Bearer 且返回 `backup-{id}.cfg`；`../`、根目录外绝对路径与符号链接逃逸由单测覆盖，
  HTTP 错误与 Job 结果均为通用文案，不含服务器路径；异步执行成功结果不含 `file_path`。
- ✅ operator 只取 token 用户，同步/批量/异步备份无伪造 operator 通道。
- ✅ 前端构建：`npm run build` 成功（13.94s，仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 Backups/Templates 页交互未执行，需真实浏览器验证。

**步骤 4E-A 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_backups_templates_security_step4e.py`、既有 backup/template/netmiko/批次一回归及全量 pytest，失败集合不得新增
- [x] 使用 backup read/execute/batch/delete 四种最小权限账号逐端点验证；跨权限 403，管理员全部放行，执行只允许实验设备
- [x] 使用 template read/write/delete/render 四种最小权限账号验证列表/详情/创建/更新/删除/渲染；跨权限 403
- [x] 备份列表、内容、diff、下载、错误响应和 Job 结果不得含服务器绝对路径；下载必须要求 Bearer 且返回 `backup-{id}.cfg`
- [x] 验证合法旧备份路径可读；`../`、根目录外绝对路径、符号链接逃逸及恶意设备名不得越过 `storage.backup_dir`
- [x] 同步/批量/异步备份的 operator 必须等于 token 用户，伪造 query/body operator 无效；异步 Job 成功结果不得含 `file_path`，失败信息必须脱敏
- [x] 模板 create/update 拒绝 `id/created_at` 等额外字段；对象、数组和字符串形式变量超过 100 KB 均 422；合法模板仍可经共享沙箱渲染
- [ ] 浏览器 Backups 页列表/查看/diff/认证下载/批量执行可用，菜单与按钮权限表现正确，401/403 提示可理解
- [x] 前端环境执行 `npm ci && npm run build`

**步骤 4E-B0 验证结果（2026-08-02）**：✅ 权限定义、角色 CRUD/clone 与用户角色分配九条写路由全部挂功能权限；
✅ `tests/test_permissions_security_step4e_b.py` 3 项真实 HTTP 回归覆盖普通用户创建权限、创建管理员角色、给自己绑定管理员角色均 403，
并验证 `role:write` 与 `user:write` 职责隔离；与统一认证回归合计 **23 passed**；全仓 Ruff、`app.main` 导入和编辑器诊断通过。
Linux 测试系统需重跑该测试，并以普通账号复核上述三条自提权路径 403、管理员仍可正常管理角色。

**步骤 4E-B0 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_permissions_security_step4e_b.py` **3 passed**，与统一认证回归合并全过；
  全量 pytest **53 failed / 625 passed / 4 skipped**，失败集合与 4D 基线完全一致，无新增失败。
- ✅ 真实 API 复核（`/tmp/smoke_4e_rest.py`）：role create 中仅 usr_writer（无 role:write）→ 403，
  role_writer / usr_role_writer / admin → 201；roles 列表无权限门槛（供角色分配下拉框）三类账号均 200；
  user create 仅 usr_writer → 201、usr_reader → 403；user delete 仅 usr_writer / role_writer → 403、admin → 404，
  证明 `role:write` 与 `user:write` 职责隔离且写路由均已挂功能权限。三条自提权路径 403 由上述 3 项自动测试覆盖。

**步骤 4E-B1 验证结果（2026-08-02）**：✅ Faults 23 条 HTTP 路由全部挂 `fault:read/write/delete/analyze`；
✅ reporter、reviewed_by 与转维修 operator 由 JWT Principal 覆盖，前端不再发送 `Web/Monitor3D/author` 审计身份；
✅ 工作日志拒绝空值、额外字段与 >10,000 字符，列表限制 `skip >= 0`、`1 <= limit <= 500`；
✅ 严重度改为显式 `critical > major > warning > minor` 排序，dashboard 统计完整状态机且除 closed 外均计为活跃；
✅ 转维修表单的维修描述与诊断文本不再被静默丢弃；五条后台工作流/AI/通知异常由 `print()` 改为结构化服务端异常日志；
Layout 故障角标改走认证 API 客户端并统计全部非 closed 状态，菜单使用 `fault:read`；
✅ `tests/test_faults_security_step4e_b.py` **7 passed**，故障相邻回归 **23 passed**，全部已完成安全切片
**152 passed / 4 skipped**；全仓 Ruff、`app.main` 导入和编辑器诊断通过；
✅ Windows 可比较全量 pytest（排除既有挂起 console）为 **54 failed / 567 passed / 8 skipped / 10 errors**，
相对 4E-A 恰好新增 B0+B1 的 10 passed，失败/错误集合不变。⚠️ 本机缺 Vite 可执行文件，前端构建留给 Linux。

**步骤 4E-B1 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_faults_security_step4e_b.py` **7 passed**，故障相邻回归全过；
  全量 pytest **53 failed / 625 passed / 4 skipped**，失败集合与 4D 基线完全一致，无新增失败。
- ✅ 真实 API 权限矩阵（`/tmp/smoke_4e_rest.py`）：fault list 与 incidents/dashboard=reader 200；
  create/get=writer；delete=deleter；analyze=analyzer；work-note=writer；跨权限一律 403、admin 全放行
  （bogus id 在权限门后解析为 404，证明权限先于资源解析）。
- ✅ 单测覆盖伪造 reporter/reviewed_by/operator 均取 Principal 落库、工作日志空白/额外字段/超长与
  分页越界均 422、列表 severity 业务排序、dashboard 全状态机分布之和等于 total。
- ✅ 前端构建：`npm run build` 成功（仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 Faults/FaultDetail/Monitor3D 交互未执行，需真实浏览器验证。

**步骤 4E-B1 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_permissions_security_step4e_b.py`、`test_faults_security_step4e_b.py`、故障幂等与全量 pytest，失败集合不得新增
- [x] 用 fault read/write/delete/analyze 四个最小权限账号验证 23 条端点代表路径；跨权限 403，未认证 401，管理员全部放行
- [x] 创建故障时伪造 reporter、复核时伪造 reviewed_by、转维修时伪造 operator 均不得落库，DB 必须记录 token 用户
- [x] 工作日志空白、额外 author/operator、>10,000 字符均 422；合法日志可保存；分页越界均 422
- [x] 实测列表严重度顺序与 dashboard 全状态总数/活跃数；状态分布之和必须等于 total
- [ ] 浏览器 Faults/FaultDetail/Monitor3D 创建、复核、日志、转维修可用，故障角标携带 Bearer；执行 `npm ci && npm run build`

**步骤 4E-B2 验证结果（2026-08-02）**：✅ Maintenance 13 条 HTTP 路由全部挂
`maintenance:read/write/delete/transition`，列表/详情/事件、CRUD、指派、日志、建议、流转与验证均覆盖；
✅ 删除全部 `next(get_db())` 与手工 close，改用 `Depends(get_db)` 管理会话；HTTP 400/404 保持原状态码，
未知异常只返回通用 500，服务端保留堆栈；✅ 九类裸 dict 请求改为拒绝额外字段且有枚举/长度/金额范围的
Pydantic 模型，禁止经 create/update 覆盖 id/status/operator；分页限制 `skip >= 0`、`1 <= limit <= 500`；
✅ 创建、指派、日志、状态流转、提交验证、验证通过与自动推进的事件 operator 固定为 token 用户；前端不再发送
Maintenance `operator: Web`，菜单使用 `maintenance:read`；✅ transition/verify-pass/auto-transition 三条完成路径
统一把关联 transferred 故障置为 resolved，列表快捷动作与四步状态机统一为 created/pending → repairing → verifying → completed；
✅ Fault 转维修的类型、优先级、负责人和文本均按数据库列约束，维修描述、诊断与预估备件均持久化；
✅ 移除 `""`/`"/"` 重复路由注册；`tests/test_maintenance_security_step4e_b.py` **7 passed**，
Faults/Maintenance 集成回归 **19 passed**，全部已完成安全切片 **159 passed / 4 skipped**；全仓 Ruff、
`app.main` 导入和编辑器诊断通过；✅ Windows 可比较全量 pytest（排除既有挂起 console）为
**54 failed / 574 passed / 8 skipped / 10 errors**，相对 B1 恰好新增 7 passed，失败/错误集合不变。
⚠️ 本机无 Vite 可执行文件，前端构建交给 Linux 测试系统。

**步骤 4E-B2 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_maintenance_security_step4e_b.py` **7 passed**，Faults/Maintenance 集成回归全过；
  全量 pytest **53 failed / 625 passed / 4 skipped**，失败集合与 4D 基线完全一致，无新增失败。
- ✅ 真实 API 权限矩阵（`/tmp/smoke_4e_rest.py`）：maint list=reader 200；create/get=writer；
  delete=deleter；transition=transition 权限；跨权限一律 403、admin 全放行
  （bogus id 在权限门后解析为 404，证明权限先于资源解析）。
- ✅ 单测覆盖三条完成路径（transition/verify-pass/auto-transition）关联 fault 置为 resolved 且 verify_passed、
  create/update 覆盖 id/status/operator、负金额、非法类型/优先级与超长文本均 422、内部异常 500 脱敏
  不含 SQL/路径、依赖会话管理无连接池泄漏。
- ✅ 前端构建：`npm run build` 成功（仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 Maintenance/FaultDetail 交互未执行，需真实浏览器验证。

**步骤 4E-B2 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_maintenance_security_step4e_b.py`、Faults/转维修幂等与全量 pytest，失败集合不得新增
- [x] 用 maintenance read/write/delete/transition 四个最小权限账号验证 13 条端点代表路径；跨权限 403、未认证 401、管理员全放行
- [x] create/transition/work-note/submit-verification/verify-pass/auto-transition 伪造 operator 均 422，事件表 operator 必须等于 token 用户
- [x] create/update 尝试覆盖 id/status/operator、负金额、非法维修类型/优先级、超长文本均 422；分页越界 422
- [x] 分别通过 transition、verify-pass、auto-transition 完成三张关联维修单，Maintenance 必须 completed 且关联 Fault 必须 resolved
- [x] 实测 created/pending 列表快捷动作进入 repairing；Fault 转维修的描述、诊断、预估备件与 owner 均正确落库
- [x] 制造数据库异常时 HTTP 只返回通用文案，不含 SQL、路径或连接信息；确认请求后连接池无泄漏
- [ ] 浏览器 Maintenance/FaultDetail 创建、编辑、指派、日志、状态流转与验证可用；执行 `npm ci && npm run build`

**步骤 4E-B3 验证结果（2026-08-02）**：✅ 旧计划/任务流 17 条与 AOP 年度规划 13 条端点全部按
`planned_task:read/write/delete/execute` 分层；✅ legacy plans 五条路由移除 `next(get_db())`，统一依赖会话；
列表、任务、历史、预测天数和 AI 扫描数量均有上限；✅ Plan/Task/AI/Complete 与全部 AOP 请求改为严格 Pydantic
模型，拒绝额外字段并按数据库列限制日期、枚举、文本、金额与 `DECIMAL(5,2)` 工时；前端旧计划与 AOP 项目/窗口
改为显式 payload，不再 spread 含 id/统计/只读关系的服务端对象；✅ plan/task/AOP project 在提供 device_id 时
由数据库覆盖 device_name；任务完成创建的维修单 operator 取 token Principal，伪造 operator 422；
✅ AOP 排程错误只返回通用业务文案，详细原因仅写服务端日志；菜单使用 `planned_task:read`；
✅ `tests/test_planned_maintenance_security_step4e_b.py` **5 passed**，与既有 AOP 测试合计
**16 passed**（PostgreSQL 并发测试本机 skip）；全部已完成安全切片 **175 passed / 4 skipped**；全仓 Ruff、
`app.main` 导入和编辑器诊断通过；✅ Windows 可比较全量 pytest（排除既有挂起 console）为
**54 failed / 579 passed / 8 skipped / 10 errors**，相对 B2 恰好新增 5 passed，失败/错误集合不变。
⚠️ 本机缺 Vite，前端构建与 PostgreSQL AOP 并发测试交 Linux 测试系统。

**步骤 4E-B3 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_planned_maintenance_security_step4e_b.py` **5 passed**、
  `test_aop_planning.py` **11 passed**；全量 pytest **53 failed / 625 passed / 4 skipped**，
  失败集合与 4D 基线完全一致，无新增失败。
- ✅ PostgreSQL 并发（scratch 库 `nas_test`，`TEST_DATABASE_URL`）：`test_postgresql_concurrency.py`
  **2 passed**（并发出库不产生负库存、并发 Fault→Maintenance 只复用一条记录）、
  `test_postgresql_aop_planning.py` **1 passed**（并发 AOP 生成只创建一条任务，排程幂等、
  approved/locked 更新约束不退化）。
- ✅ 真实 API 权限矩阵（`/tmp/smoke_4e_rest.py`）：plans/tasks 列表=reader 200；plan/task create=writer；
  task complete=executor；跨权限一律 403、admin 全放行（bogus id 在权限门后解析为 404）。
- ✅ 单测覆盖伪造 device_name 由数据库覆盖为 device_id 真实名称、任务完成伪造 operator 422、
  非法输入与分页/历史/预测天数/AI 扫描越界 422、排程错误脱敏不含 SQL/路径且依赖会话管理。
- ✅ 前端构建：`npm run build` 成功（仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 legacy/AOP 交互未执行，需真实浏览器验证。

**步骤 4E-B3 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_planned_maintenance_security_step4e_b.py`、`test_aop_planning.py`、PostgreSQL AOP 并发与全量 pytest，失败集合不得新增
- [x] 用 planned_task read/write/delete/execute 四个最小权限账号验证 legacy+AOP 30 条端点代表路径；跨权限 403、未认证 401、管理员全放行
- [x] 创建 legacy plan/task 与 AOP project 时伪造 device_name，数据库必须保存 device_id 对应真实名称；任务完成伪造 operator 必须 422
- [x] 测试非法 plan type/status/date、额外 id/created_by、负金额、超长文本、工时溢出、分页/历史/预测天数/AI 扫描越界均 422
- [x] AOP 排程失败响应不得含 SQL、路径或调度内部信息；计划请求后连接池不得泄漏
- [x] PostgreSQL 并发重复排程仍保持幂等，既有 approved/locked 更新约束不退化
- [ ] 浏览器 legacy 与 AOP 新建/编辑/批量窗口/排程/任务完成可用；执行 `npm ci && npm run build`

**步骤 4E-B4 验证结果（2026-08-02）**：✅ Workflows 14 条 HTTP 端点全部按
`workflow:read/write/delete/trigger` 分层；✅ trigger/action 类型限制为注册表中的 4/5 种，规则条件、动作配置和
event_data 拒绝额外字段、未知操作符、类型错配、超长/深层/过多节点及危险数值；规则列表增加真实 total 与
`skip/limit` 上限；✅ HTTP 手动 trigger 在匹配全部规则后、执行任何动作前，按动作要求
`maintenance:write` / `planned_task:write` / `device:write`，缺权限整次 403 且无部分副作用；
创建、更新、启停跨域写规则以及初始化默认规则时也必须先持有相同目标域权限，不能借 system 自动触发绕过；
用户发起的 Fault create/escalate 自动化同样检查目标域权限，系统内部自动触发保留 system 语义；
✅ maintenance operator、PM task generated_by 与健康分 AuditLog 均记录可信 actor；scheduled-check 改为数据库聚合，
最多返回 1000 个设备 ID 并标记截断；✅ 任一动作失败时整体 `success=false`，异常与维修抢占冲突不再回传内部细节；
前端 scheduled_check 测试补齐 check_type，菜单使用 `workflow:read`；
✅ `tests/test_workflows_security_step4e_b.py` **10 passed**，Workflow/Fault/Maintenance 相邻回归 **24 passed**，
全部已完成安全切片 **185 passed / 4 skipped**；全仓 Ruff、`app.main` 导入和编辑器诊断通过；
✅ Windows 可比较全量 pytest（排除既有挂起 console）为 **54 failed / 589 passed / 8 skipped / 10 errors**，
相对 B3 恰好新增 10 passed，失败/错误集合不变。⚠️ 本机缺 Vite，前端构建交 Linux 测试系统。

**步骤 4E-B4 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_workflows_security_step4e_b.py` **10 passed**，
  Workflow/Fault/Maintenance 相邻回归全过；全量 pytest **53 failed / 625 passed / 4 skipped**，
  失败集合与 4D 基线完全一致，无新增失败。
- ✅ 真实 API 权限矩阵（`/tmp/smoke_4e_rest.py`）：rules 列表/stats=reader 200；rule create/get=writer；
  trigger=trigger 权限（bogus device 未命中规则返回 200 “Trigger not activated”）；跨权限一律 403、admin 全放行。
- ✅ 单测覆盖跨域写权限：仅 workflow:trigger 命中 create_maintenance/update_health_score 缺目标域 write 时 403 且零副作用、
  创建/更新/启停跨域规则或初始化默认规则需先持目标域 write、Fault create/escalate 间接触发同样受限、
  动作失败整体 success=false 且异常脱敏不含 SQL/路径/堆栈、scheduled-check 大量设备只返回截断列表、规则分页 total 真实。
- ✅ 前端构建：`npm run build` 成功（仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 Workflows 交互未执行，需真实浏览器验证。

**步骤 4E-B4 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_workflows_security_step4e_b.py`、工作流维修幂等、Fault/Maintenance 相邻及全量 pytest，失败集合不得新增
- [x] 用 workflow read/write/delete/trigger 四个最小权限账号验证 14 条端点；跨权限 403、未认证 401、管理员全放行
- [x] 仅 workflow:trigger 命中 create_maintenance/create_pm_task/update_health_score 分别必须 403 且零副作用；补齐对应目标域 write 后才执行
- [x] 仅 workflow:write 创建/更新/启停上述跨域规则或初始化默认规则必须 403；补齐目标域 write 后才允许保存
- [x] 验证维修单 operator、PM task notes.generated_by、健康分 AuditLog.operator 均等于 token 用户；Fault create/escalate 间接触发同样遵守目标域权限
- [x] 未知 trigger/action、错配 event_data、未知条件操作符、超深/超大 JSON、非法 days_offset/adjustment 与额外字段均 422
- [x] 强制一个动作失败和一个动作抛内部异常：整体 success 必须 false，响应不得含 SQL、路径、堆栈或内部异常文本
- [x] scheduled-check 在大量设备下只返回最多 1000 个 ID、计数正确且有截断标志；规则分页 total 不等于当前页长度
- [ ] 浏览器 Workflows 列表/创建/编辑/启停/删除/默认规则/四类测试触发可用；执行 `npm ci && npm run build`

**步骤 4E-B5A 验证结果（2026-08-02）**：✅ Auth Users 的列表/详情、创建/编辑、删除与角色目录分别使用
`user:read/write/delete`、`role:read`；用户列表分页限制 `skip >= 0`、`1 <= limit <= 500`；
✅ UserCreate/UserUpdate/PasswordChange 严格拒绝额外字段，验证 Email、正整数角色 ID、最多 50 个角色及 8–128 位密码，
前端校验与中英文文案同步；✅ Auth 与 Permissions 两套角色分配 API 共用同一委派安全策略：必须同时持有
`user:write + role:write`，只能授予自身权限子集，禁止 admin:all、重复/不存在 ID，并阻止委派管理员修改或删除
superuser/admin:all 目标；✅ 管理员密码重置、停用账号和用户自改密码都会撤销该用户全部活动会话；删除用户前
显式清理 Session 与角色关联；✅ 统一 current-user 兼容依赖移入 identity，消除 Auth↔Dependencies 导入循环且保持
既有 FastAPI dependency override 函数对象不变；Users 菜单使用 `user:read`；
✅ `tests/test_auth_users_security_step4e_b.py` **7 passed**，与 permissions/auth/workflow/alerts 相邻回归
**57 passed**，全部安全切片 **192 passed / 4 skipped**；全仓 Ruff、`app.main` 导入和编辑器诊断通过；
✅ Windows 可比较全量 pytest（排除既有挂起 console）为 **54 failed / 596 passed / 8 skipped / 10 errors**，
相对 B4 恰好新增 7 passed，失败/错误集合不变。

**步骤 4E-B5A 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_auth_users_security_step4e_b.py` **7 passed**，
  permissions/auth/workflow/alerts 相邻回归全过；全量 pytest **53 failed / 625 passed / 4 skipped**，
  失败集合与 4D 基线完全一致，无新增失败。
- ✅ 真实 API 权限矩阵（`/tmp/smoke_4e_rest.py`）：users 列表=reader 200；user create 仅 usr_writer → 201、
  usr_reader → 403；role create 仅 usr_writer（无 role:write）→ 403、role_writer/usr_role_writer → 201；
  user delete 仅 usr_writer/role_writer → 403、admin → 404；roles 目录无权限门槛三类账号均 200。
- ✅ 单测覆盖委派安全策略：仅 user:write 分配/清空角色 403、增加 role:write 后只能授予自身权限子集且
  admin:all/越权/重复/不存在角色均拒绝、委派管理员不得修改/删除 superuser 或 admin:all 账号、
  密码重置/停用/自改密码后旧 token 401、删除带活动 Session/角色用户不 500。
- ✅ 前端构建：`npm run build` 成功（仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 Users 交互未执行，需真实浏览器验证。

**步骤 4E-B5A 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_auth_users_security_step4e_b.py`、permissions/auth/workflow 相邻及全量 pytest，失败集合不得新增
- [x] 用 user read/write/delete 与 role read/write 最小权限组合验证用户 CRUD、角色目录和两套角色分配 API；跨权限 403、未认证 401
- [x] 仅 user:write 分配/清空角色必须 403；增加 role:write 后只能授予自身权限子集，admin:all、越权、重复/不存在角色均拒绝
- [x] 委派管理员不得更新/删除 superuser 或持 admin:all 的账号；超级管理员仍可正常管理
- [x] 管理员重置密码、停用账号、用户自改密码后复用旧 access token 必须 401；删除带活动 Session/角色的用户不得 500
- [ ] 浏览器 Users 列表、创建、编辑、角色分配、密码重置、停用和删除可用；执行 `npm ci && npm run build`

**步骤 4E-B5B 验证结果（2026-08-02）**：✅ SystemConfig GET/PUT 使用 `system_config:read/write`，
仅返回并允许修改 timezone/grafana_url，数据库未知 key 不再回传；时区通过 ZoneInfo 校验，Grafana URL 仅允许
无凭据/片段的 HTTP(S)，两项在单个事务中原子更新并记录 Principal `updated_by`；✅ 前端 SystemSettings
全部迁到统一认证 API 客户端，配置一次 PUT 保存，不再产生半写状态；菜单使用 `system_config:read`；
✅ SLO 使用 `slo:read/write`，service key/name/目标 90–100/窗口 1–365/设备类型/文本与额外字段均严格验证；
✅ cache/rate-limit/diagnostics/Grafana 按 `system_ops:read/write` 分层，diagnostics 使用依赖会话且异常脱敏；
readiness 返回真实 200/503 JSONResponse，不再把 `(body, status)` 序列化为 200 数组；✅ Grafana GET 与写方法分权，
限制路径/查询/5 MB body，拒绝非法 Content-Length，不向上游转发 NAS Authorization/Cookie，过滤 hop-by-hop 头，
StreamingResponse 完成后关闭上游 response/client，连接失败只返回通用 502；✅ operator 预置角色不再携带失效的
system settings 导航权限，新权限默认仅由 admin:all 放行；
✅ `tests/test_system_settings_security_step4e_b.py` **6 passed**，与 users/permissions/alerts/auth 相邻回归
**53 passed**，全部安全切片 **198 passed / 4 skipped**；全仓 Ruff、`app.main` 导入和编辑器诊断通过；
✅ Windows 可比较全量 pytest（排除既有挂起 console）为 **54 failed / 602 passed / 8 skipped / 10 errors**，
相对 B5A 恰好新增 6 passed，失败/错误集合不变。⚠️ 本机缺 Vite，前端构建交 Linux 测试系统。

**步骤 4E-B5B 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_system_settings_security_step4e_b.py` **6 passed**，
  users/permissions/alerts/auth 相邻回归全过；全量 pytest **53 failed / 625 passed / 4 skipped**，
  失败集合与 4D 基线完全一致，无新增失败。
- ✅ 真实 API 权限矩阵（`/tmp/smoke_4e_rest.py`）：system config 读=sc_reader、写=sc_writer；
  SLO 列表=slo_reader；diagnostics=so_reader；跨权限一律 403、admin 全放行。
- ✅ 单测覆盖配置白名单与原子更新（未知 key 拒绝、timezone/URL 非法与额外字段 422、updated_by 取 token 用户）、
  SLO 目标 90–100/窗口 1–365/重复超长设备类型/额外 operator 校验、system_ops 分层与请求边界、
  Grafana 代理不向上游转发 NAS Authorization/Cookie 且流关闭、readiness 真实 503 且错误脱敏不含 SQL/路径、
  前端一次 PUT 保存无半写。
- ✅ 前端构建：`npm run build` 成功（仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 SystemSettings 交互未执行，需真实浏览器验证。

**步骤 4E-B5B 测试系统 AI 接手清单**：
- [x] Linux 跑 Ruff、`test_system_settings_security_step4e_b.py`、users/permissions/alerts/auth 相邻及全量 pytest，失败集合不得新增
- [x] 用 system_config/slo/system_ops read/write 六个最小权限账号验证配置、SLO、cache、diagnostics、Grafana；跨权限 403、未认证 401
- [x] SystemConfig 尝试读/写未知 key、JWT/数据库/密钥字段必须拒绝或隐藏；timezone/URL 非法、null、额外字段均 422；合法两项一次提交且 updated_by=token 用户
- [x] SLO 非法 key、目标 <90 或 >100、窗口越界、重复/超长设备类型、额外 operator 均 422；合法 CRUD 可用
- [x] readiness 在数据库/Prometheus 失败时真实返回 503，响应不得含 SQL、路径、连接串或异常文本；diagnostics 同样脱敏且连接池无泄漏
- [x] Grafana GET 只需 system_ops:read，POST/PUT/DELETE/PATCH 需 write；超长路径/查询、>5 MB/非法 Content-Length 被拒且不上游
- [x] 抓取上游请求确认不含 NAS Authorization/Cookie；流结束、上游失败和客户端断开后 response/client 均关闭
- [ ] 浏览器 SystemSettings 配置与 SLO CRUD 均携带 Bearer、一次保存无半写；执行 `npm ci && npm run build`

**步骤 4E-C1 Spare Parts / Movements 代码收口（2026-08-02，服务器已验证）**：
✅ Spare Parts 11 条端点按 `spare_part:read/write/delete` 分层，Movements 5 条端点按
`spare_movement:read/write` 分层；新增 read 权限并同步 operator/viewer 预置角色；✅ Create/Update/Manual
Stock/Movement 请求改为拒绝额外字段且有枚举、长度、金额、数量和查询参数边界的 Pydantic 模型；所有写入
operator 固定取 JWT Principal，前端不再发送 `operator: Web`；✅ serial 查询与状态变更同时约束 `part_id`，
带 serial 的操作强制 quantity=1，跨型号 serial 在库存扣减前拒绝；实例状态按
`in_stock → out/inuse → in_stock` 与 `inuse → pending_scrap → scrapped` 流转，聚合库存按实例状态重算；
存在实例的备件禁止无 serial 出入库，无实例的旧聚合库存仍保留按数量操作；✅ 扫码新建备件目录初始库存设为 0，
再由 manual-in 唯一创建实例与增加库存，避免初始数量 + movement 双计数；ScanInput 快速出入库携带 serial；
✅ Movement 历史改为不可物理删除，报废库存页面“删除”改为创建 `scrap_out` 反向业务记录，不再删除
`pending_scrap` 实例和审计轨迹；✅ Task/Planned/Maintenance/Fault 页面在提交主记录前拦截缺 serial 或
serialized quantity != 1 的必失败库存动作，避免已知校验错误发生在主记录提交之后；菜单使用功能 read 权限。

**本地仅执行最低静态门禁（按业主要求暂停测试）**：
- ✅ 受影响 Python 文件 `py_compile` 通过
- ✅ `ruff check app/features/spare_parts app/features/spare_movements app/features/permissions/router.py` 通过
- ✅ `import app.main` 通过，应用路由可装配
- ✅ `git diff --check` 与 VS Code 受影响文件诊断通过
- ⚠️ **未执行任何 pytest、PostgreSQL/并发测试、真实数据库写入、前端 Vite build 或浏览器操作**；以下全部由服务器端 AI 接手，不能把静态门禁当成行为验收

**步骤 4E-C1 测试系统 Linux 实测补充（2026-08-02，HEAD `2d6552a`，真实服务器）**：
- ✅ 门禁全过：ruff 零告警；`test_spare_security_step4e_c1.py` **7 passed**、`test_spare_atomic_step4e_c1.py`
  **11 passed**；批次一 15 项全过；全量 pytest **53 failed / 625 passed / 4 skipped**，失败集合与 4D 基线
  逐项 diff 完全一致，无新增失败。`tests/test_spare_part_service.py` 既有 3 个分类/估值失败
  （`test_get_part_success`、`test_stats_basic`、`test_stats_by_category`，类别中英文/估值旧契约差异）
  在 HEAD `2d6552a` 基线同样失败，与本次安全逻辑改动无关，未改测试或基线掩盖。
- ✅ 真实 API 权限矩阵（`/tmp/smoke_4e_rest.py`）：spare-parts 列表=sp_reader、创建=sp_writer、删除=sp_deleter；
  spare-movements 列表=mv_reader、创建=mv_writer；跨权限一律 403、admin 全放行（bogus id 权限门后 404）。
- ✅ 行为验收（`/tmp/smoke_4ec1_behavior.py` **41/41 PASS**，真实 PostgreSQL）：serial 属于同一/另一 part_id、
  serial 不存在、quantity != 1、serialized 备件无 serial 出入库、重复 manual-in 等拒绝路径库存/实例/movement
  均不变；状态机 `in_stock→out/inuse→in_stock` 与 `inuse→pending_scrap→scrapped`、聚合不变量
  `quantity_in_stock == count(in_stock)`；manual-in 新建/重新入库、manual-out、扫码快速出入库、跨型号 serial、
  PO/单价/安装与拆卸设备、审计 operator=token 用户；Movement PUT 仅 reason/reference/单价可改且 part_id+serial
  绑定、DELETE 一律 409 并保留审计轨迹；并发同一 serial 双出库一次成功一次 4xx 且库存 0、
  并发聚合出库不产生负库存（真实 PostgreSQL `with_for_update`）。
- ✅ PostgreSQL 并发单测（scratch 库 `nas_test`，`TEST_DATABASE_URL`）：`test_postgresql_concurrency.py`
  **2 passed**、`test_postgresql_aop_planning.py` **1 passed**。
- ✅ **跨 API 原子事务（docs 清单第 9 项非原子流程修复）**：新增服务端单事务端点 `POST /api/spare-movements/batch`，
  并把 spare movements 折入 `complete_task`/`update_maintenance` 主记录事务，全程一个 commit，缺
  `spare_movement:write` 整次 403 零副作用。`/tmp/smoke_4ec1_atomic.py` **22/22 PASS**：(a) 完成任务带 2 条
  movement、第 2 条故意失败（序列号属于他型号）→ 400、任务仍 in_progress、0 条落库（整批回滚）；
  (b) 全部合法 → completed + 2 条落库 + 实例 out + operator=admin；(c) 缺 spare_movement:write 的账号提交
  带 movement 的完成 → 403 且零副作用；(d) batch 合法/非法/权限；(e) update_maintenance 失败回滚 + 成功落库。
  前端四个视图（TaskDetail/PlannedMaintenance/MaintenanceDetail/FaultDetail）改为单次请求携带 `spare_movements`，
  删除逐条 createMovement 循环。
- ✅ 前端构建：`npm run build` 成功（13.94s，仅既有 chunk 体积告警）。
- ⚠️ 浏览器端 PartsTable/ScanInput/FaultDetail/MaintenanceDetail/PlannedMaintenance/TaskDetail/ScrapInventory
  交互未执行，需真实浏览器验证。

**步骤 4E-C1 服务器端 AI 必做清单**：
- [x] 拉取本提交，记录 SHA/环境；运行全仓 Ruff、`test_spare_part_service.py`、`test_spare_part_service.py` 的既有基线对比及全量 pytest（仍忽略已知挂起 console 时须注明）
- [x] 新增 `tests/test_spare_security_step4e_c1.py`，对 Parts 11 条 + Movements 5 条路由做依赖矩阵、未认证 401、跨权限 403、admin 放行和 Principal operator 落库测试
- [x] PostgreSQL 分别验证 serial 属于同一/另一 `part_id`、serial 不存在、重复 out/in/scrap_in/scrap_out、quantity != 1；所有拒绝路径库存、实例和 movement 数量均不得变化
- [x] 验证实例状态机和聚合不变量：每次成功/失败后 `SparePart.quantity_in_stock == count(instance.status == 'in_stock')`；旧无实例聚合备件仍可按数量 in/out，有实例备件无 serial 必须拒绝
- [x] 并发两次对同一 serial 出库只能成功一次；并发聚合出库不得负库存；SQLite 与 PostgreSQL 的 `with_for_update` 差异必须记录
- [x] 验证 manual-in 新建/重新入库、manual-out、扫码快速入/出、跨型号 serial、PO/单价/安装设备/拆卸设备与审计 operator 全生命周期
- [x] 验证 Movement PUT 只能改 reason/reference/实例单价且 part_id+serial 绑定；DELETE 一律 409，ScrapInventory 通过 scrap_out 移除报废库存并保留 scrap_in/out 历史与实例记录
- [ ] 浏览器验证 PartsTable、ScanInput、FaultDetail、MaintenanceDetail、PlannedMaintenance、TaskDetail、ScrapInventory 全流程并执行 `npm ci && npm run build`
- [x] **重点复现既存非原子流程**：任务/维修记录更新与后续多条 spare movement 仍是跨 API 多事务；在第 N 条 movement 故障时记录半提交结果。服务器 AI 应设计并实现单个服务端事务端点或明确补偿机制后再判定该项完成
- [x] 核对 `tests/test_spare_part_service.py` 既有 3 个分类/估值失败，确认仍为旧契约差异，禁止通过修改新安全逻辑或更新基线掩盖

**下一切片**：服务器端 AI 先完成 C1 行为验收与跨 API 原子事务，再继续 Scan Sessions、Notifications、Jobs、Compliance 与权限读取面；
完成长尾写接口后再进入步骤 5 的会话级 SSH 凭证、二次确认和独立加密密钥。

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

- [x] **P1** `backups/router.py:69,319` — async def 内直接调同步 netmiko SSH（超时 30/60s），`/batch` 还串行遍历全部设备。`[已复核]`
  → 修复（批次三 3.1+3.2）：同步与批量路径的 Netmiko 调用改为经统一设备操作执行器 `run_device_op`（`app/shared/device_ops.py`），不再阻塞事件循环；批量保持串行遍历（并发收敛留待后续）。
- [x] **P1** `deploy/router.py:971` — `rollback_deploy` 在 async def 内逐台同步调 `napalm_service.rollback_device`（同文件 `execute_deploy` 已正确用线程池，属遗漏）。`[已复核]`
  → 修复（批次三）：改为 `await run_device_op(napalm_service.rollback_device, ..., timeout=180)` 逐台串行；`execute_deploy` 与 `rollback_deploy` 共用统一执行器。
- [x] **P1** `logs/router.py:66` — WebSocket 迭代同步阻塞生成器 `stream_logs`（内部 `time.sleep(0.5)` 死循环），一条连接占死事件循环。`[已复核]`
  → 修复（步骤 4D）：改为每 0.5 秒异步等待客户端消息，文件读取通过 `asyncio.to_thread` 执行无等待增量轮询；连接断开可及时取消，不再占死事件循环。
- [x] **P1** `discovery/router.py:93` — 同步 `ping_sweep`（50 线程 + 阻塞 socket）在 async 内执行；`subnet` 无 CIDR 校验，`/8` 会构造 1600 万 future。`[已复核]`
  → 修复（批次三）：`ping_sweep` 经 `await run_device_op(...)` 移出事件循环；`discovery_service.ping_sweep` 增加 CIDR 守卫 `num_addresses > 65536`（> /16）抛 `ValueError`，`ping-sweep`/`discover` 端点将其映射为 HTTP 400（顺带把非法 CIDR 从 500 修正为 400）。
- [x] **P1** `tool_logs/tool_executor.py:101-112` — 协程内直接同步 `ConnectHandler/send_command`，无 `run_in_executor`。`[已复核]`
  → 修复（批次三）：netmiko `ConnectHandler/send_command/disconnect`、napalm `open/方法调用/close`、jira `JIRA/issue/update/close` 全部经 `run_device_op` 在线程池执行。
- [x] **P1** `alerts/router.py:131` — `_send_email` 同步 SMTP 在 async 内调用。`[已复核]`
  → 修复（批次三）：`test_alert_channel` 的 SMTP 发送改为 `await asyncio.to_thread(service._send_email, ...)`（与 backups 既有模式一致）。
- [x] **P1** `console/console_service.py` 全量、`devices/router.py:815` 文件 IO — 同类问题。`[已复核]`
  → 修复（批次三）：`console/router.py` 的 `list_ports` / `find_console_port` 经 `run_device_op`；`devices/router.py` 探测端点 `test_ssh_connection` / `fetch_device_info`（netmiko SSH）改 `asyncio.to_thread`（文件 IO 已于步骤 4C 线程化）。
- [x] **P1** 统一方案：建立唯一的「设备操作执行器」——强制线程池 + 强制过命令守卫 + `finally` 关连接，把 netmiko / napalm / serial / subprocess 四条路径全部收进去。
  → 修复（批次三）：新增 `app/shared/device_ops.py` —— `get_device_executor()`（懒加载全局 ThreadPoolExecutor）+ `run_device_op()`（`loop.run_in_executor` + 可选超时）+ `get_device_executor_pool()`（受控临时池）。netmiko / napalm / serial / subprocess（deploy 回滚、discovery ping-sweep、console 串口、tool_executor 三条路径）均已接入；命令守卫由 deploy 引擎既有 `CommandGuard` 承担；`finally` 关连接由各工具自身 `disconnect/close` 保证。

### 3.2 数据库会话与事务

- [x] **P0** `db = next(get_db())` 绕过依赖注入共 9+ 处：`main.py:277`、`services/reachability_monitor.py:194,248,436,497`、`services/snmp_discovery.py:139,197`、`services/trap_receiver.py:264`、`shared/db_init.py:14,49`、`tool_logs/tool_executor.py:99`、`devices/router.py:800,835,857`。`get_db`（`shared/database.py:135`）是包了 `session_scope` 的生成器，`next()` 后 commit/rollback/close 永不执行，连接靠 GC 归还，`pool_size=10` 在后台线程长跑下会耗尽。`[已复核]`
  → 修复（批次三 3.2）：`main.py` 已先期解决；后台服务 `reachability_monitor`（4 处）、`snmp_discovery`（2 处）、`trap_receiver`（1 处）、`db_init`（2 处）、`tool_logs/tool_executor`（3 处）全部改为 `with get_db_manager().session_scope() as db:`（成功提交/异常回滚/始终 close），异常路径显式 `db.rollback()` 后 return；`devices/router.py` 6 个端点（`test_device_connection`/`fetch_device_info`/`export_devices`/`import_devices`/`manual_check_reachability`/`get_reachability_stats`）改为 `db: Session = Depends(get_db)` 并删除手工 close。`adk/`、`compliance/`、`deploy` 其余 `next(get_db())` 属后续统一项。
- [x] **P0** `maintenance/router.py` 13 条路由全部使用 `db = next(get_db())`，请求完成前的异常路径可能跳过生成器清理并耗尽连接池。`[已复核]`
  → 修复（步骤 4E-B2）：全部改为 `db: Session = Depends(get_db)`，移除手工 close；业务异常保留状态码，未知异常统一回滚/脱敏。
- [x] **P0** `planned_maintenance/router.py` 的 legacy plans 五条路由使用 `next(get_db())`，与同文件其余依赖注入路径并存。`[已复核]`
  → 修复（步骤 4E-B3）：全部改为 `Depends(get_db)`，移除手工 close，创建异常改为通用 500 并在服务端记录堆栈。
- [x] **P1** `devices/device_service.py:118` — `_sync_modules_to_inventory` 内部自行 commit，与调用方形成嵌套提交，中途失败留半份库存实例。`[已复核]`
  → 修复（批次三）：`_sync_modules_to_inventory` 移除内部 commit（保留 `db.flush()` 拿 part_id），`create_device`/`update_device` 改为 flush → sync → 统一 commit，设备行 + 模块资产实例单事务提交，中途失败整批回滚。
- [x] **P1** `deploy/router.py:1006-1035` — `create_deploy_history` 内部已 commit（`:1449`），之后再更新 `rollback_status` 二次 commit，中途失败留半状态。`[已复核]`
  → 修复（批次三）：`create_deploy_history` 删除内部 `db.commit()`（保留两处 `db.flush()`），由调用方 `execute_deploy`/`rollback_deploy` 各自保持最终一次 commit，消除同一 session 二次提交。
- [x] **P1** `backups/router.py:154,163` — 通用 except 里引用可能未绑定的 `device`；且在 `db.commit()` 之后才 `db.rollback()`，顺序无效。`[已复核]`
  → 修复（步骤 4E-A）：进入 try 前初始化 `device`，异常路径先 rollback，再写通用失败日志；HTTP 响应不回显底层异常。
- [x] **P1** `deploy/router.py:907` — `except: pass` 吞掉 rollback/close 阶段全部异常。`[已复核]`
  → 修复（批次三）：改 `except Exception as e:` + `logger.warning(f"清理部署会话异常: {e}")`，不再吞异常。

**批次三 3.1+3.2 Linux 实测（2026-08-02，HEAD 提交前，真实服务器）**：
- ✅ 静态：`ruff check app/ tests/` → All checks passed。
- ✅ 回归（SQLite 默认）：`tests/test_batch1_regressions.py` 15 项全过；discovery/devices/deploy/tool_executor/alerts/backups 相关单测通过；全量 pytest（跳过既有挂起 `test_console_service.py`）为 **53 failed / 625 passed / 4 skipped**，失败集合与 4E 基线逐项 diff 完全一致（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1），无新增失败。`tests/test_backups_templates_security_step4e.py` 与 `tests/test_secure_template_renderer.py` 的 2 个源码断言随实现更新（`asyncio.to_thread`→统一执行器、db_init 的 `get_db`→`get_db_manager`）。
- ✅ 真实服务器（systemd `nas-backend`，PG，`auth_enabled=true`）`/tmp/smoke_3_arch.py` 全过（9/9）：ping-sweep `127.0.0.1/30`→200；ping-sweep `10.0.0.0/8`→400（CIDR 守卫，返回「子网过大，最多允许 65536 个地址（/16）」）；设备导出→200（Excel，5480B）；reachability-stats→200；单设备 check-reachability→200（顺带修复 `manual_check_reachability` 调用不存在的 `check_device_reachability` 的既存 500 错误，改走 `_detect_reachability`+`_update_device_status` 经 `asyncio.to_thread`）；console /ports→200；rollback 空设备列表→400（不 500）；alert /test（SMTP 未启用→`"未启用"`）；连续 30 次请求无连接池报错。
- ✅ 重启后既有 4E 冒烟无回归：`smoke_4ea_backups_templates.py`（4E-A 权限矩阵）、`smoke_4e_rest.py`（4E-B/C 矩阵）、`smoke_4ec1_atomic.py`（PASS=22）、`smoke_4ec1_behavior.py`（PASS=41）全部通过。

### 3.3 Schema 权威源

- [x] **P0** `main.py:353` + `shared/database.py:95` — 启动时 `init_db()` 调 `Base.metadata.create_all`，与 alembic 双轨；`models.py` 45 张表中 alembic 仅覆盖约 28 张（`spare_part_instances`、`device_interfaces`、`interface_traffic_samples`、`notifications`、`deploy_history`、`compliance_*`、`ai_configs`、`system_config`、`service_slo`、`jobs` 等全靠 create_all 兜底）→ **全新 PG 库执行 `alembic upgrade head` 得不到完整 schema**。`[已复核]` `[已修复]`：基线迁移 `ed628a533673`（autogenerate 补齐 17 张缺失表 + 缺失列/索引）+ 修复迁移 `5d16fa030a9a`（FK ondelete / 索引 / server_default）；PG 启动 create_all 已移除，改 fail-fast 校验 alembic head。
- [x] **P0** 8 个"迁移"脚本硬编码 `sqlite3` + `data/nas.db`：`migrations/add_monitor_tier.py:12`、`add_service_slo_key.py:10`、`add_spare_part_fields.py:10`、`add_service_slo.py:17`、`create_device_links.py:14`、`fix_slo_fields.py:7`、`scripts/migrate_device_reachability.py:17`。在 PG 生产上执行会静默创建/修改一个空 SQLite 文件，改错库且不报错。建议删除或移入 `scripts/legacy_sqlite/`。`[已复核]` `[已修复]`：8 个脚本 + 3 个 .sql（`006_asset_tracking.sql` 等）已 `git mv` 至 `scripts/legacy_sqlite/`；`migrations/` 下保留 3 个 dialect-safe 脚本（`add_incident_automation_fields.py`/`add_interface_neighbor_fields.py`/`add_snmp_interface_monitoring.py`）。
- [x] **P1** `migrations/versions/b7a8c9d0e1f2_*.py:16` 与 `c1d2e3f4g5h6_*.py:16` 都是 `down_revision = None`，存在多个 base 根，分支执行顺序不确定。`[已复核]` `[已修复]`：全新 PG 库实测 `alembic upgrade head` 按确定顺序跑完整个链（3 根在 `383cadd7b057` 合并为单 head `5d16fa030a9a`），`alembic check` 无漂移，顺序风险实测消除。
- [x] **P1** `migrations/env.py:13` — 只 import `app.shared.models`，`models_jobs.Job` 未注册进 `target_metadata`，autogenerate 会生成 `drop_table('jobs')`。`[已复核]` `[已修复]`：`env.py` 与 `app/shared/database.py` 均 import `models_jobs.Job`，autogenerate/create_all 与运行期 metadata 一致。
- [x] **P1** `migrations/versions/f3a4b5c6d7e8_*.py:41` — 对 `topo_edges/topo_nodes/device_ports` 只有 `DELETE FROM`，这三张表从未被任何 `create_table` 创建。`[已复核]` `[已修复]`：基线迁移 `ed628a533673` 创建全部 17 张链外缺失表（含 `topo_nodes`/`topo_edges`/`device_ports`/`device_interfaces`/`interface_traffic_samples`/`jobs` 等）。
- [x] **P1** `models.py:32,38,62,67,72` — `deployment_status/reachability/monitor_tier/risk_level/lifecycle_stage` 声明 `index=True`，但列是通过裸 ALTER 加的，PG 上索引实际不存在。`[待验证]` 用 `\d devices` 确认 `[已修复]`：修复迁移 `5d16fa030a9a` 以 `CREATE INDEX IF NOT EXISTS` 建 5 个 device 列索引 + `ix_devices_serial_number` + `ix_audit_logs_created_at` + `ix_audit_logs_operator`；真实 PG `pg_indexes` 实测：5 个 device 列索引已存在（无新增），serial_number 与 audit_logs 2 索引缺失已补齐。
- [x] **P1** `models.py:154,237,771,1153` — `fault_records.maintenance_id` 等 4 处 FK 无 `ondelete`，且 fault↔maintenance 构成环形 FK，删设备时会被 FK 违例挡住。`[已复核]` `[已修复]`：4 处 FK 均改 `ondelete="SET NULL"`；真实 PG 已落地（含历史孤儿数据清理：2 条 `maintenance_tasks` 引用不存在父行 → 置 NULL 后重建约束）。
- [x] **P1** `models.py:23` — `devices.serial_number` 既无唯一约束也无索引；`models.py:332` — `audit_logs` 除主键外零索引。`[已复核]` `[已修复]`：`serial_number` 改 `index=True`（不 unique，避免既有重复数据迁移失败）；`audit_logs` 加 `ix_audit_logs_created_at`/`ix_audit_logs_operator`；真实 PG `pg_indexes` 实测 3 索引均在。
- [x] **P2** `models.py` 全文 0 处 `server_default`，默认值只在 Python 侧；raw SQL 路径写 NULL 而 `filter(x == False)` 在 PG 下不匹配 NULL。`[已复核]` `[已修复]`（有界子集）：`review_required→true`、`snmp_enabled/is_uplink/monitored/false_positive/auto_created/ai_recommended/verify_passed/notifications.read→false` 补 `server_default` + 迁移回填既有 NULL；其余 True 默认列（`is_active`/`is_auto_created`/`auto_generate` 等）留待 797 后续批次。
- [x] **P2** `models.py:187,1011,1050,1239,1374`、`models_jobs.py:34` — 裸 Integer 伪外键，会产生孤儿数据。`[已复核]` `[已修复]`（批次十收尾）：6 处转真 FK（`fault_records.peer_device_id`/`device_interfaces.peer_device_id`/`ai_knowledge_documents.device_id`/`jobs.device_id` → `SET NULL`，`interface_traffic_samples.device_id`/`deploy_device_results.device_id` → `CASCADE`），幂等迁移 `f0a1b2c3d4e5`（建约束前清孤儿）+ `test_fk_integrity.py` 覆盖三类 ondelete；`fault_records.if_index` 为复合键引用（device_id+if_index → device_interfaces）判为误报不建简单 FK，`jobs.change_request_id` 无 `change_requests` 表记观察；既有 `Device.faults`/`DeviceInterface.device` 关系因新增第二个 devices FK 加 `foreign_keys` 消歧（仅 ORM）。
- [x] **P2** `shared/config.py:137` — `pool_timeout` 配置项从未传入 `create_engine`（`database.py:73-78`），无效配置。`[已复核]` `[已修复]`：`DatabaseManager.__init__` 增加 `pool_timeout` 参数并传入 PG `create_engine`，`get_db_manager()` 从 `config.database.pool_timeout` 取值。
- [x] **P2** `models.py:1207` — `deploy_history.children` 的 `remote_side=[id]` + `backref="parent"` 自引用方向反了。`[待验证]` `[已核实为误报]`：这是 SQLAlchemy 标准 adjacency-list 写法（children 以 id 为 remote_side），无需修改。
- [x] **P2** `interface_traffic_samples` / `device_metric_samples` 无分区、无保留策略，单表无限增长。`[已复核]` `[已修复]`（批次十收尾）：经核实**保留机制已存在**（`metric_retention.py` + `prometheus_connector.cleanup_old_metric_samples` + APScheduler 每日任务，默认 90 天，`test_metric_retention.py` 全绿），批次十补齐可运维性——保留参数经 `Config.metrics`（`retention_days`/`cleanup_interval_seconds`/`cleanup_batch_size`）+ config.yaml `metrics:` 块 + env（`DEVICE_METRIC_*`）下发；**PG 分区列遗留不动**（单表分区为独立工作项）。
- [x] **P2** 目标动作：以当前 PG 实际结构 autogenerate 一个基线迁移并 `alembic stamp`，然后移除启动期 `create_all`。`[已修复]`：基线 `ed628a533673`（autogenerate）+ 修复迁移 `5d16fa030a9a`；真实 nas 库 `stamp ed628a533673` → `upgrade head`（仅跑 5d16fa030a9a）；PG `init_db()` 移除 create_all 改 head 校验 fail-fast；重启后冒烟全过（见下方实测）。

**批次三 3.3 Linux 实测（2026-08-02，HEAD 后，真实服务器 systemd nas-backend / PG / auth_enabled=true）**：
- 全新 scratch PG `nas_scratch`：`alembic upgrade head` 从空库一步到位（修复链上 `e2f3g4h5i6j7`/`c30eb4f78004` 对链外表的裸 ALTER、`c1d2e3f4g5h6`/`d1e2f3g4h5i6` 对 `spare_part_instances`/`device_links` 的裸引用 → `_has_table` 守卫）；`alembic check` 无漂移；Inspector vs `Base.metadata` 差异脚本零 diff（仅 `alembic_version`）。
- 真实 `nas` 库：diff 脚本仅见预期差异（3 缺失索引 + 4 处 FK 无 ondelete + 3 张遗留 Gen2 拓扑表）→ `alembic stamp ed628a533673` → `upgrade head` 跑 `5d16fa030a9a`；`pg_indexes`/`pg_constraint`/`information_schema` 实测：3 索引补齐、4 处 FK 均 `ON DELETE SET NULL`、`review_required=true` 等 server_default 落地、NULL 回填清零、孤儿 `maintenance_tasks` 2 条清理为 0。
- `init_db()` 三条路径实测：真实 nas（head）启动通过；空库 → `RuntimeError`（缺少 alembic_version）；stamp 回旧版 → `RuntimeError`（未到达期望 head）。
- 重启 nas-backend 后冒烟：`/tmp/smoke_3_arch.py` **9/9**；`smoke_4ea_backups_templates.py` **ALL PASS**；`smoke_4e_rest.py` **4E-B/C ALL PASS**；`smoke_4ec1_behavior.py` **41 PASS / 0 FAIL**；`smoke_4ec1_atomic.py` **22 PASS / 0 FAIL**。
- ruff `app/ tests/ migrations/` 全绿；`pytest --ignore=tests/test_console_service.py` **53 failed / 625 passed / 4 skipped**（与 4D 基线完全一致，无新增）。

### 3.4 缓存

- [x] **P1** `services/reachability_monitor.py:339` — 探测历史存进 `max_size=256` 的全局 `SimpleCache`（与 dashboard 共用），被 LRU 淘汰即丢失连续失败计数 → **漏告警**。`[已复核]` `[已修复]`：探测历史迁到独立 `_history_cache = HybridCache(max_size=1024, default_ttl=3600)`（不与 dashboard 256 竞争 LRU），Redis 兜底支持未来多 worker 共享历史。
- [x] **P1** `services/ai_triage.py:377,398` — AI 后台结果只写进程内存缓存，多 worker 下前端轮询永不命中。`[已复核]` `[已修复]`：全局 `cache` 升级为 `HybridCache`（内存 LRU + Redis 兜底），set 双写、get 内存 miss 回查 Redis 保持原始 TTL 回填，ai_triage/dashboard 在 `config.cache.enabled=true` 时自动多 worker 共享。
- [x] **P1** `shared/cache.py:117` — `cached` 装饰器用 `hash(str(args))` 作键（含对象 repr 地址、受 PYTHONHASHSEED 影响），多进程键不一致；`_cache_key` 只取 md5 前 8 位。`[已复核]` `[已修复]`：`_cache_key` 用完整 md5；`cached` 改 `inspect.signature(func).bind(*args, **kwargs)` + `apply_defaults()` 生成确定性键。
- [x] **P1** `shared/cache.py:96` / `shared/redis_cache.py:107` — 内存与 Redis 两套实现互不失效；前者全扫描 + 全局锁，后者用 `KEYS prefix*`。`[已复核]` `[已修复]`：`HybridCache` 统一两层——`invalidate_prefix/clear/delete` 级联内存 + Redis，一处清空两套一致。
- [x] **P2** `shared/middleware/rate_limiter_v2.py:16` — `TieredRateLimiter` 定义后完全未使用；限流为进程内内存态，多 worker 下额度按进程翻倍。`[待验证]` `[已修复]`：删除零引用的 `TieredRateLimiter`；`RateLimiter` 加 Redis 固定窗口后端（`rl:{prefix}:{identity}:{窗口}` INCR/EXPIRE），三套限流器独立 key_prefix；`/api/rate-limit/status` 改读 v2。固定窗口边界 2 倍突发为可接受近似。

### 批次三 3.4 · 切片一 · Linux 实测（2026-08-03）

验证（HEAD `c1ee7ae` → 切片一后）：

| 检查点 | 结果 |
| --- | --- |
| `ruff check app tests` | ✅ All checks passed |
| `pytest tests/test_batch1_regressions.py -q` | ✅ 15 passed |
| 新增测试 `tests/test_cache.py` / `tests/test_redis_cache.py` | ✅ 56 passed（TestHybridCache 5 例 + Redis enabled=False/ttl/incr/get_config 用例） |
| 全量 `pytest -q -rf` | ✅ **53 failed / 651 passed / 4 skipped**，失败集合与基线**逐条一致**（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1 = 53），零新增；passed +9 为新增用例 |
| `frontend/npm run validate:locales` | ✅ 3212 zh / 3212 en，0 违规 |
| `frontend/npm run build` | ✅ 构建成功（chunk 体积告警为既有，非错误） |

修复说明：
- **813 探测历史独立缓存**：`_history_cache = HybridCache(max_size=1024, default_ttl=3600)`，与全局 dashboard 缓存（max_size=256）隔离，消除 LRU 竞争漏告警；Redis 兜底支持未来多 worker 共享历史。
- **814 AI 结果多 worker 共享**：全局 `cache` 由 `SimpleCache` 升级为 `HybridCache`；`config.cache.enabled=true`（config.yaml 配独立 db，默认 db=0 vs broker db=1 天然隔离）时 ai_triage/dashboard set 双写 Redis，内存 miss 回查 Redis 并保持原始 TTL 回填。
- **815 key 确定性**：`_cache_key` 去 `[:8]` 用完整 md5；`cached` 装饰器 `inspect.signature().bind()` + `apply_defaults()`（零调用方，仅修陷阱）。
- **816 两套缓存统一失效**：`HybridCache.invalidate_prefix/clear/delete` 级联内存 + Redis，一处清空两套一致。
- **817 限流 Redis 化 + 删死码**：删零引用的 `TieredRateLimiter`；`RateLimiter` 加 Redis 固定窗口后端（pipeline INCR + EXPIRE nx），三套限流器独立 key_prefix（`rl:get`/`rl:write`/`rl:auth`），Redis 不可用/未启用自动降级纯内存滑动窗口；`/api/rate-limit/status` 改读 v2。固定窗口边界 2 倍突发为可接受近似（限流是保护非精确计量）。按用户限流属 3.5-3（切片二）范围，本切片保留按 IP。

### 3.5 启动与关闭

- [x] **P1** `main.py:217-221` — `return {...}, status_code` 被序列化成数组且状态码恒 200，`/ready` 永远"健康"。`[已复核]`
  → 修复（步骤 4E-B5B）：改为显式 JSONResponse，依赖失败真实返回 503；检查异常仅写服务端日志，响应不泄露细节。
- [x] **P1** `main.py:434-435` — 导入期注册 SIGTERM/SIGINT，会被 uvicorn 自身 handler 覆盖，且无 `@app.on_event("shutdown")` → Trap 接收器 / APScheduler / 连接池清理实际不执行。`[已复核]` `[已修复]`：新增 `@app.on_event("shutdown") async def shutdown_event()`（迁入原 handle_shutdown 五段 try/except：停三服务 + engine.dispose + cache.clear），删除模块级 `signal.signal`（被 uvicorn handler 覆盖，属无效注册）与 `import signal`；uvicorn 收到 SIGTERM/SIGINT 均触发 lifespan shutdown，覆盖 `python app/main.py` 与 `python -m uvicorn` 两路径。
- [x] **P1** `services/prometheus_connector.py:505` — `start()` 内先阻塞跑一次完整 `poll_once()`；`:507` 的轮询任务未设 `max_instances/coalesce`（清理任务设了），60s 周期可重叠，`_last_counters` 多线程读写导致速率算错。`[已复核]` `[已修复]`：删同步阻塞 `poll_once()`，轮询 job 加 `max_instances=1, coalesce=True, next_run_time=datetime.now()`（立即首跑不阻塞启动，与清理 job 一致）；`_last_counters` 读写加 `threading.Lock`。
- [x] **P1** `main.py:262-283` — `async with AsyncClient` 内 `send(stream=True)`，返回 StreamingResponse 前 client 已关闭。`[已验证]`
  → 修复（步骤 4E-B5B）：client 生命周期延长到 StreamingResponse background close；同步关闭上游 response/client，并过滤凭据与 hop-by-hop 头。
- [x] **P1** `main.py:76-80` — 限流中间件注册在 auth 之后，实际先于认证执行，无法按用户限流。`[已复核]` `[已修复]`：`RateLimitMiddleware` 注册移到 auth_middleware 之前 → 入站 security→auth→RateLimit→CORS，认证先执行；`RateLimitMiddleware` 读 `scope["state"].get("user_id")`（auth 已写 `request.state.user_id`），有则按用户限流、无则回退 IP。行为变化：无效 token 请求先被 auth 拒绝（401，不再计入限流额度），恶意 token 洪泛打 DB 由 `/auth/`、`/login` 公开路径的 AUTH_LIMITER IP 限流缓解。
- [x] **P2** `services/trap_receiver.py:243` — `stop()` 只关 socket 不 join 线程；全局 `_db_lock` 串行处理所有 Trap，风暴时丢包。`[待验证]` `[已修复]`（join 部分）：`stop()` 关 socket 后 `join(timeout=2.0)`（`_serve` 在 sock=None 时自然退出）。`_db_lock` 串行处理 Trap 属性能设计，非本项缺陷，保留。

### 批次三 3.5 · 切片二 · Linux 实测（2026-08-03）

验证（HEAD `c8e5ba9` → 切片二后）：

| 检查点 | 结果 |
| --- | --- |
| `ruff check app tests` | ✅ All checks passed |
| `pytest tests/test_lifecycle_batch3.py` + `test_batch1_regressions.py` | ✅ 24 passed（9 静态断言 + 15 回归） |
| 全量 `pytest -q -rf` | ✅ **53 failed / 660 passed / 4 skipped**，失败集合与基线**逐条一致**（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1 = 53），零新增；passed +9 为新增生命周期用例 |
| `frontend/npm run validate:locales` | ✅ 3212 zh / 3212 en，0 违规 |
| `frontend/npm run build` | ✅ 构建成功（chunk 体积告警为既有，非错误） |

修复说明：
- **823 shutdown 事件**：`@app.on_event("shutdown")` 迁入原 handle_shutdown 五段 try/except；删模块级 `signal.signal` + `import signal`。静态断言：`signal.signal(` 与 `import signal` 均不在 main.py。
- **824 prometheus 轮询**：删启动期同步阻塞 `poll_once()`；轮询 job `max_instances=1/coalesce=True/next_run_time=datetime.now()`；`_last_counters` 两处访问（:244 读 / :279 写）加 `threading.Lock`。静态断言覆盖 job 参数与锁。
- **827 中间件顺序 + 按用户限流**：注册序改 CORS→RateLimit→auth→security（入站 security→auth→RateLimit→CORS）；`RateLimitMiddleware` 读 `scope["state"]["user_id"]` 优先按用户限流（public 路径无 user_id 回退 IP + AUTH_LIMITER）。
- **828 trap join**：`stop()` 关 socket 后 `join(timeout=2.0)`（`self._thread` 初始化 None，安全）。

---

## 批次四 · 数据正确性（页面数字目前不可信）

- [x] **P1** `compliance/compliance_service.py:341` — `max([severity 字符串])` 按字典序，结果 `medium > low > high > critical`，行级严重度标注全错。`[已复核]`
  → 修复（批次四）：新增 `SEVERITY_RANK = {"critical":5,"high":4,"medium":3,"low":2,"info":1,"ok":0}`，行级严重度取最高等级、默认 `"ok"`。
- [x] **P1** `faults/router.py:210` — `order_by(severity.desc())` 是字符串倒序（`warning > minor > major > critical`），与注释声称的 critical 优先相反。`[已复核]`
  → 修复（步骤 4E-B1）：使用 SQLAlchemy `case` 显式映射业务优先级，SQLite/PostgreSQL 均按 critical、major、warning、minor 排序。
- [x] **P1** `faults/router.py:938-955` — 统计只覆盖 `open/investigating/resolved/closed`，实际状态机含 `assigned/accepted/diagnosing/resolving/transferred`（`models.py:154` 注释），活跃数低估、分布不等于总数。`[已复核]`
  → 修复（步骤 4E-B1）：状态分布覆盖完整 `FAULT_STATUS_LABELS`，除 closed 外全部计为活跃，严重度与最近事件使用同一活跃集合。
- [x] **P1** `compliance/compliance_service.py:421` vs `compliance/router.py:283` — service 返回 `results`，router 读 `security_issues/compliance_issues/config_errors/recommendations`，`/quick-check` 永远返回空数组。`[已复核]`
  → 修复（批次四）：router 改读真实键 `{"success","score","results"}`；`quick_audit` 兼容 AI 返回裸 JSON 数组（`parse_json_response` 可能返回 list），不再 `list.get` 崩溃。
- [x] **P1** `dashboard/dashboard_service.py:51-78` — 按 10 种设备类型循环执行约 8 条 COUNT，单次 summary 近 80 次查询。`[已复核]`
  → 修复（批次四）：1 次 `db.query(Device.device_type, Device.deployment_status, Device.reachability).all()` + Python 聚合，输出形状完全不变（total/reachable/unreachable/unknown、in_use/un_used/maintenance/retired、by_type 每类型含 online/offline）。
- [x] **P1** `dashboard/dashboard_service.py:1057,1103` — 变更-故障关联在循环内逐条 COUNT（N+1），且同条件 count 与 all 重复查两次；`:948,962` SLO 计算逐个查设备与故障全集。`[已复核]`
  → 修复（批次四）：变更-故障关联改为按 `device_id` 批量拉取后 `bisect` 计 72h 窗口；上周期对比去掉 count+all 重复查询；SLO 提升设备类型→id 解析到循环外 1 次查询、故障按最大窗口批量拉取后在内存按窗口切分。
- [x] **P1** `faults/router.py:217,222` — 列表接口每条故障各查一次 Device 和 MaintenanceRecord（limit=100 → 约 200 次额外查询）。`[已复核]`
  → 修复（批次四）：列表查询加 `selectinload(FaultRecord.device), selectinload(FaultRecord.maintenance)`，循环内改读 `f.device` / `f.maintenance`。
- [x] **P1** `spare_parts/router.py:334`（出库）/ `:258`（入库）— 仅按 `serial_number` 定位实例，未约束 `part_id`，可把 B 备件实例按 A 备件出库，两个 `quantity_in_stock` 同时写错。`[代码已修复，待服务器验证]`
  → 修复（步骤 4E-C1）：所有实例查询同时约束 part_id+serial 并在库存变更前校验归属/状态；serial 操作强制 quantity=1，聚合库存与实例状态同步。未跑行为/并发测试，验收见 C1 服务器清单。
- [x] **P1** `planned_maintenance` 任务完成与备件出入库由浏览器分成多次请求：后端先 commit completed，前端再逐条调用 spare movement；中途失败会留下“任务已完成但库存只更新一部分”。`[已复核]`
  → 修复（步骤 4E-C1）：spare movements 折入 `complete_task`/`update_maintenance` 主记录单事务，新增
  `POST /api/spare-movements/batch`，任一条失败整批回滚；前端四个视图改为单次请求携带 `spare_movements`，
  不再由前端逐条编排。真实服务器 22/22 PASS，见 4E-C1 清单第 9 项。
- [x] **P1** `deploy/router.py:1143` — `window_id.split('_')[1]` 缺参数即异常；该接口返回 success 但**不创建任何定时任务**（注释自承"简化处理"）。`[已复核]`
  → 修复（批次四，完整实现定时）：抽出 `_run_deploy_impl(deploy_data, current_username)` 复用 `execute_deploy` 主体；`schedule_deploy` 落库 `Job(job_type=deploy)` + `deploy_scheduled.apply_async(eta=本地墙钟→UTC aware)`（celery timezone=UTC），返回真实 `job_id`/`task_id`。执行需常驻 celery worker：`celery -A app.core.celery_app worker -Q device_ops`（`celery_app` 已加 `imports` 让 worker 注册任务模块；未运行 worker 时 Job 停在 pending/queued，不再假装已执行）。
- [x] **P1** `tasks/backup_tasks.py:139` — 批量任务伪造子 Job ID `f"{job_id}-{i}"`，Job 表无对应记录 → 子任务全部 "Job not found"。`[已复核]`
  → 修复（批次四）：删除死代码 `backup_devices_batch`（无任何调用方）。
- [x] **P1** `backups/router.py:78,328` — `status=result["success"] if ... else "failed"` 把布尔 `True` 写进 String 状态列。`[已复核]`
  → 修复（步骤 4E-A）：同步与批量日志状态均显式写入 `success` / `failed` 字符串。
- [x] **P1** 分页参数普遍无 `ge/le` 约束：`devices/router.py:155`、`devices/device_service.py:150`、`backups/backup_service.py:16`、`faults/router.py:170`、`maintenance/router.py:744`、`deploy/router.py:1205`（`spare_parts/router.py:59` 用了 `Query(ge/le)`，风格不统一）。`[已复核]`
  → Backups HTTP 路由已在步骤 4E-A、Faults 在 4E-B1、Maintenance 在 4E-B2、Planned Maintenance 在 4E-B3 增加范围限制；批次四补齐剩余：`devices/router.py` `limit=Query(200,ge=1,le=200)`/`skip=Query(0,ge=0)`、`deploy/router.py` `limit=Query(50,ge=1,le=200)`/`offset=Query(0,ge=0)`，并给 `device_service.list_devices`、`backup_service.list_backups` 服务层加 `skip>=0, 1<=limit<=200` clamp 防直调越界。
- [x] **P1** 高危写操作请求体为裸 `dict`：`deploy/router.py:40,482,915,1134`、`credentials/router.py:41,115`、`templates/router.py:28,42`（后者还 `ConfigTemplate(**data)` 批量赋值）。`[已复核]`
  → 修复：Deploy 在 4B、Credentials 在步骤 1、Templates 在 4E-A 全部迁到 Pydantic 模型；模板服务额外使用字段白名单，禁止覆盖 id/时间戳等内部字段。
- [x] **P1** `maintenance/router.py` 九类写/建议请求使用裸 `dict`，客户端可提交 operator/status/id 等内部字段，文本、金额与枚举没有边界。`[已复核]`
  → 修复（步骤 4E-B2）：全部迁到 `maintenance/schemas.py` 的严格 Pydantic 模型，额外字段 422，并按数据库列限制枚举、长度和非负金额。
- [x] **P1** `planned_maintenance/router.py::complete_task` 使用 `Optional[dict]`，成本、结果和文本无权威模型；AOP 模型默认忽略额外字段。`[已复核]`
  → 修复（步骤 4E-B3）：legacy 与 AOP 请求全部 `extra=forbid` 并加边界；前端改显式 payload，避免把服务端只读字段回传导致 422。
- [x] **P1** `workflows/router.py` 的 trigger_conditions/action_config/event_data 为任意字典，未知 trigger/action 与未知条件操作符可进入执行层；动作失败后 Executor 仍返回整体 success。`[已复核]`
  → 修复（步骤 4E-B4）：严格限制注册类型、JSON 大小/深度/节点与动作字段；任一动作失败则整体 false，内部异常统一脱敏。
- [x] **P2** `templates/template_service.py:20`、`notifications/router.py:78` — 把页大小当 `total`，分页总数失真。`[待验证]`
  → Workflows 已在步骤 4E-B4 改为 count + offset/limit，响应同时返回真实 total、skip、limit。批次四补齐：`template_service.list_templates` 的 `total` 改 `db.query(ConfigTemplate).count()`；notifications 新增 `SystemNotificationService.get_user_notifications_total(user, unread_only)` 返回真实总数。
- [x] **P2** 时间字段两套写法：devices/backups 走 `utc_iso()`（带 Z），`faults/router.py:288`、`deploy/router.py:1237`、`credentials/router.py:30` 直接 `isoformat()`（无 Z），`notifications/router.py:57` 手工拼 Z，`deploy/router.py:1105` 用本地 `datetime.now()`。`[已复核]`
  → 批次四统一：faults 列表、deploy history、credentials、notifications 全部改 `utc_iso()`（带 Z）。`get_maintenance_windows` 的 `datetime.now()` **保留本地墙钟语义**（复核结论：改 `utcnow` 会在非 UTC 服务器把窗口日期偏移一天，窗口选择是纯本地日期概念，不应变 UTC）；`schedule_deploy` 的 `scheduled_at` 入参保持本地 naive ISO，仅 `eta` 做本地→UTC aware 转换交给 celery（timezone=UTC）。
- [x] **P2** `discovery/discovery_service.py:245` — 单例缓存首次的 `timeout/workers`，后续请求传参被静默忽略。`[待验证]`
  → 修复（批次四）：`get_discovery_service` 每次返回前把传入 `timeout/workers` 同步到缓存实例。
- [x] **P2** `compliance/router.py:26` — 模块导入期实例化 `ComplianceService()`，其 `__init__` 会访问数据库。`[已复核]`
  → 修复（批次四）：改为懒加载 `get_compliance_service()` 单例，4 处调用点全部替换。
- [x] **P2** `deploy/router.py:815,985` — 审计日志 `operator` 硬编码 `"Web"`，同函数内已解析出 `current_username`，审计不可追溯。`[已复核]`
  → **纠偏**：docs 行号过期——deploy 早已修复（`router.py` 用 `current_username`，`test_deploy_security_step4b.py` 断言无 `"Web"`）。真正残留为 compliance：`compliance_service._save_audit_log`（`created_by="Web"`）与 `compliance/router.py` `/standards/upload`。批次四修复：`audit_config`/`_save_audit_log` 透传 `operator`（默认 system），`/check`、`/upload`、`/standards/upload` 加 `Depends(get_current_principal)`，按 `_actor_username` 范式取 `principal.username`。
- [x] **P2** `faults/router.py:1015,1042,1069,1096,1125` — 五个后台任务用 `print()` 吞异常，工作流/AI/通知失败完全不可见。`[已复核]`
  → 修复（步骤 4E-B1）：全部改为 Loguru `logger.exception`，保留 fault/maintenance ID 并记录堆栈。

### 批次四 · Linux 实测（2026-08-02，PostgreSQL + 严格认证）

静态：`ruff check app/ tests/` 全绿。回归：`pytest tests/test_batch1_regressions.py` 15 passed；全量 `pytest --ignore=tests/test_console_service.py` 53 failed / 625 passed，与基线**失败集合完全一致**（无新增无收敛）。

真实服务器冒烟（systemd `nas-backend.service`，uvicorn :8000，PostgreSQL，`auth_enabled=true`）：

| 检查点 | 结果 |
| --- | --- |
| dashboard summary 形状 | ✅ 输出形状不变：deployment in_use/un_used/maintenance/retired、reachable/unreachable/unknown/online/offline、`by_type` 每设备类型含 total/in_use/un_used/maintenance/retired/reachable/unreachable/unknown/online/offline |
| faults 列表时间戳 | ✅ `last_event_at/fault_time/created_at/updated_at` 全部带 `Z` |
| compliance `/check` 审计操作人 | ✅ `ComplianceAuditLog.created_by = 'admin'`（真实登录用户名），旧数据 `'Web'` 不再产生 |
| `/api/deploy/schedule` 真实调度 | ✅ 返回真实 `job_id`(UUID)+`task_id`(celery UUID)；Job 落库 status=pending、operator=admin、parameters 含 window_id/scheduled_at/deploy_data |
| celery worker 实际执行 | ✅ `celery -A app.core.celery_app worker -Q device_ops --pool=solo` 注册 `deploy_scheduled`；用 eta=过去 + 不存在的 device_id(999999) 调度 → Job `failed`、error=`404: 未找到指定的设备`、started_at/completed_at 落库（证明任务真实执行）；验后已停 worker |
| 分页越界 | ✅ `/api/devices?limit=201`、`limit=-1` 被拒绝（`less_than_equal`/`greater_than_equal` 校验详情，应用统一 400 校验体；`limit=50` 200） |
| 真实 total | ✅ notifications `total=69`（limit=3 仅返回 3 条）、templates `total=15` |
| quick-check 契约 | ✅ 返回 `{"success":true,"score":50,"results":[...]}`（AI 返回裸 JSON 数组时也正常） |

部署说明（批次四 item 6 新增）：`POST /api/deploy/schedule` 返回真实 Job+task_id 并在到点后**真正执行**，前提是常驻 celery worker 运行 `celery -A app.core.celery_app worker -Q device_ops`。`celery_app` 已加 `imports` 使 worker 启动即注册任务模块（此前 `KeyError: unknown task`）。未运行 worker 时 Job 停留在 pending/queued，不再假装已执行。

---

## 批次五 · 前端

- [x] **P0** `views/Deploy.vue`（3631 行）— 无任何卸载钩子，部署中切路由后 `setInterval`(`:1737,:2078`) 与 WebSocket(`:1747`) 全部残留；且两处 `setInterval` 复用同一 `timer` 变量，`stopTimer()` 只清得掉最后一个。`[已复核]`
  → 修复（批次五卸载清理）：文件实际 4146 行（docs 行号过期）。抽 `startElapsedTicker()` 先清旧计时器再启动，替换两处内联 `setInterval`（消除孤儿计时器）；新增 `onBeforeUnmount`：`stopTimer()` + 关闭 `deployWebSocket` 并置空。
- [x] **P0** `utils/requestManager.js:22-30` + `api/request.js:78-83` — 所有 GET 按 `method:url:params:data` 自动 abort 同键旧请求，两个组件轮询同一端点会互相取消，表现为随机空数据，且调用方无法关闭该行为。`[已复核]`
  → 修复（批次五请求层切片）：auto-abort 加逃生口——调用方传 `config.noAutoCancel: true` 关闭；已自带 `config.signal` 时不再覆盖（默认同键在途 GET 自动取消行为保留）。
- [x] **P0** `api/request.js:130-165` — `apiWithRetry` 对 post/put/patch/delete 默认重试，非幂等写操作（部署、入库）可能重复下发。`[已复核]`
  → 修复（批次五请求层切片）：`withRetry` catch 分支补 `if (shouldRetry(error) === false) throw error`（此前从未咨询调用方策略）；`apiWithRetry` 的 post/put/patch/delete 默认 `retries: 0`（写操作不重试），get 保留重试（幂等读，network/5xx 才重）。注：`apiWithRetry` 为死代码（全项目零调用方），保留但收敛默认行为。
- [x] **P0** `views/layout/SearchDropdown.vue:174-198` — 用原生 `fetch('/api/...')` 绕过 axios 实例，不带 Authorization、不过 401 拦截器。`[已复核]`
  → 修复（安全步骤 3）：设备、模板、备份搜索全部改走统一 Axios 客户端并使用结构化 `params`，自动携带 JWT 与复用 401 处理。
- [x] **P1** `views/Layout.vue:96` — 故障角标仍用原生 `fetch('/api/faults?...')`，绕过统一 Bearer/401 客户端；严格认证下角标会静默失效或保持旧值。`[已复核]`
  → 修复（步骤 4E-B1）：改用统一 `getFaults()` Axios 客户端，自动附加 Bearer 并复用 401 处理。
- [x] **P1** `views/Compliance.vue:696,1504` — `v-html` 渲染自写 markdown 转换结果，`renderSectionContent` 只做正则替换不转义 HTML。`[待验证]`
  → 修复（批次五剩余小项切片）：全项目唯一 `v-html` 点。`renderSectionContent` 开头先 `escapeHtml`（转义 `& < > " '`）再跑正则，白名单标签只来自替换字符串，捕获内容均为惰性化文本；内容来自用户可创建/编辑的标准文档 API，存储型 XSS 路径已堵。node 复核：`<script>`/`<img onerror>` 全部惰性化、无残留原始危险 token，粗体/行内代码 markdown 语义不变。
- [x] **P1** `utils/cache.js:121-130` — localStorage 回填内存缓存时重算 `Date.now()+ttl`，等于每次读取都续期，数据可无限存活。`[已复核]`
  → 修复（批次五请求层切片）：`readFromStorage` 改返回完整记录 `{ value, expires }`，`getCache` 回填内存时保留原 expires，读取不再续期。
- [x] **P1** `utils/cache.js:26-31` — 缓存键把 `JSON.stringify(params)` 非字母数字全替换为 `_`，不同参数可产出同键，且键顺序敏感。`[已复核]`
  → 修复（批次五请求层切片）：`generateCacheKey` 改为「稳定序列化（递归排序键）→ djb2 哈希 → `STORAGE_PREFIX + resource + '_' + hash36`」，确定性、键序无关、无 `_` 替换碰撞。
- [x] **P1** `utils/cache.js:218-246` — `cachedRequest` 声称去重但无 in-flight Map，并发同键全部打到后端。`[已复核]`
  → 修复（批次五请求层切片）：`cachedRequest` 新增 `inFlight` Map（按 cache key），同键请求在途时复用其 Promise，`finally` 清理。另修探索发现的 `ttl`/`customTtl` 分裂：`cachedRequest` 改读 `ttl`（毫秒，与 `DEFAULT_TTL` 一致），`Layout.vue`/`SearchDropdown.vue` 传秒的 5 处改毫秒。
- [x] **P1** `views/DeviceHealth.vue:334,365,391` — 3 个 `echarts.init` 无 dispose 且组件无卸载钩子。`[待验证]`
  → 修复（批次五卸载清理）：新增 `chartInstances` 数组 + `disposeCharts()`，`initCharts` 开头先 dispose 旧实例（mount 与每次刷新重跑不再泄漏）、三个实例 push 跟踪；新增 `onBeforeUnmount(() => disposeCharts())`。
- [x] **P1** `views/Monitor3D.vue:1060` — 匿名 `theme-change` 监听从不移除，闭包持有旧 Three.js 场景阻止 GC；`:6231` 对数组材质 dispose 无效、纹理未 dispose。`[待验证]`
  → 修复（批次五卸载清理）：`theme-change` 改 named `handleThemeChange`，`onBeforeUnmount` 移除；连线 `window` 监听（mousemove/mouseup）在 `onBeforeUnmount` 直接移除（连线中卸载不再泄漏）；`scene.traverse` 改数组材质逐个 dispose + `material.map` 纹理 dispose（覆盖底图）；模块级 `offlineGlowTexture`/`impactGlowTexture` dispose 并置空（重挂载时重建）。
- [x] **P1** `composables/useLoadControl.js:142,159,165` — `online`/`visibilitychange` 监听从不移除，也不返回清理函数。`[已复核]`
  → 修复（批次五卸载清理）：`useSmartRefresh` 改 named `handleOnline`/`handleVisibility`，新增 `dispose()`（清 interval + 移除两个监听）并返回。注：该 composable 全项目零消费者，改返回形状安全。
- [x] **P1** `main.js:16` 装了 Pinia 但全项目 `defineStore` 数为 0；登录态/用户/主题在 12 个文件裸读 localStorage（`views/Layout.vue:78,81`、`api/request.js:68,74` 等），无单一数据源。`[已复核]`
  → 修复（批次五 Pinia 状态集中切片）：新建 `stores/auth.js`（`useAuthStore`：accessToken / isLoggedIn / currentUser + `setAuth`/`clearAuth`）与 `stores/theme.js`（`useThemeStore`：darkMode + `apply`/`toggle`，toggle 保留 `theme-change` dispatch）。localStorage 键名全部不变（`accessToken`/`isLoggedIn`/`currentUser`/`darkMode`），零迁移。9 处改造 + 探索补 1 处：`request.js` attachAuthToken/401 清 store、`router` 守卫读 store、`Login.vue` `setAuth`、`Layout.vue` storeToRefs/`toggle`/`apply`、`UserMenu.vue` 登出 `clearAuth`、`DeviceDetail.vue` 上传头、`Deploy.vue`/`Monitor3D.vue` deploy/WS body、`FaultDetail.vue` author、`main.js` 暗色初始化 `apply()`。`theme-change` 消费者（ParetoChart/Operations/Monitor3D）与 `isRedirectingToLogin` 401 硬跳转行为不变。
- [x] **P1** `api/request.js:49` 读 `'language'`，`locales/index.js:6797,6802` 写 `'lang'`，键不一致导致英文界面仍被汉化。`[已复核]`
  → 修复（批次五请求层切片）：`translateSSHError` 改读 `localStorage.getItem('lang')`，与 `locales/index.js:7022` 统一。
- [x] **P1** `locales/index.js` — 190 组重复键（`zh:dashDevices` L230/L288、`zh:uploadFailed` L742/L1349 等）后者静默覆盖；zh 3065 / en 3015 键，52 键缺英文、2 键缺中文。`[已复核]`
  → 修复（批次五 i18n 重建切片）：实测 183 组重复（191 冗余行，docs 190 接近）+ 43 键缺英、2 键缺中（docs 52 已过期）——同值组 keep-first、异值组 keep-last（行为保持）去重；修正 en 块 4 处漏进中文（如 `commonRefresh` '刷新'→'Refresh'）；补 42 en + 2 zh 译文。新增 `frontend/scripts/validate-locales.mjs`（ESM 逐行解析，无重复键/无缺键，违规 exit 1）+ package.json `validate:locales`。现 zh/en 各 3212 键，`npm run validate:locales` 0 违规。
- [x] **P1** 硬编码中文与 `useI18n` 混用：`Monitor3D.vue` 825 处、`Deploy.vue` 245 处、`Compliance.vue` 189 处，英文模式大面积失效。`[已复核]`
  → 修复（批次五 i18n 重建切片）：docs 计数含注释/模板含中文行，真实用户可见硬编码 ~140 处且全在 script（Monitor3D ~19、Deploy ~15、Compliance ~11 条提示 + 模板 provider 下拉）——迁移为 `t()` 调用（复用 `faultTransferFailed`/`faultTransferSuccess`/`deviceUplinkPort`/`hudStatus`/`faultOwner`/`complianceRecommendation`/`complianceAIProvider*` 等现成键；新增 `monitor3d*`/`deploy*`/`compliance*` 键含 `{param}` 占位）。排除项：后端存储值（复核 notes '大屏确认：…'、转维修 description）、逻辑/存储匹配串（`'起点'`、provider map 键）、zh 回退 map（deviceTypeMap/statusMap）、console 日志。英文模式失效修复。
- [x] **P1** `vite.config.js:18` — target `chrome60` 与 router 全量动态 `import()`（需 Chrome 63+）自相矛盾；`format:'es'` 写在 `build` 下属无效键。`[已复核]`
  → 修复（批次五请求层切片）：删无效 `build.format`；`target` 改 `['es2018','chrome63']`，注释同步（router 已用动态 import，≥63 才真实）。
- [x] **P1** `vite.config.js` — 无 `manualChunks`，three@0.184 + echarts + element-plus 同一 vendor chunk，首屏体积过大。`[已复核]`
  → 修复（批次五请求层切片）：`build.rollupOptions.output.manualChunks` 按 `node_modules` 切 three/echarts(+zrender)/element-plus/vue-vendor(vue,@vue,vue-router,pinia)/axios；实测主 index chunk 1.5MB→295kB，vendor 独立成 chunk 可长缓存。
- [x] **P1** `vite.config.js:27-30` — `server.https` 无条件 `readFileSync` 证书，缺证书连 `vite build` 都崩。`[已复核]`
  → 修复（批次五请求层切片）：`fs.existsSync(key/cert)` 后才注入 `https`，缺证书时 `vite build`/`vite dev` 不再崩溃（本机证书在位，HTTPS 冒烟 200）。
- [x] **P2** `api/request.js:107-113` — 401 用 `window.location.href` 整页刷新，多并发请求连弹错误，无 refresh token 流程。`[已复核]`
  → 修复（批次五请求层切片）：`handleAuthFailure` 加模块级 `isRedirectingToLogin` 守卫，并发多个 401 只弹一次 toast、只触发一次跳转（`api` 与 `authenticatedAxios` 共用该函数，一处守卫覆盖两条拦截链）。refresh token 流程超出本切片范围，仍缺。
- [x] **P2** 巨型视图：`Monitor3D.vue` 7119 行、`Deploy.vue` 3631、`Compliance.vue` 2948，渲染与请求耦合，无法单测。`[已复核]`
  → 切片 1（Compliance，2026-08-03）：`utils/compliance.js` + UploadStandard/CreateStandard/Rules/StandardDetail 四对话框拆子组件，Compliance 3377→2753 行。＋切片 2（2026-08-03）：Audit/AI 配置/规则详情/Config 高亮四对话框拆子组件 + `useComplianceStandards` composable 收拢 standards 状态，Compliance 2753→934 行。＋切片 3（2026-08-03）：Deploy Preview/Schedule/VariableHelp 三对话框拆子组件 + `utils/deploy.js` 纯函数收拢 + 死代码清理（approval/getVariableDescription/Promotion/warning CSS），Deploy 4146→3654 行。＋切片 4（2026-08-03）：Deploy 配置表单拆 `DeployFormPanel.vue` + `useDeployForm` composable（deployForm/executionMode/parallelLimit/数据 refs/canDeploy/5 loaders/mode→netmiko watch 收拢），Deploy 3654→2696 行。＋切片 5（2026-08-03）：Deploy 执行/历史簇拆 `useDeployExecution` + `useDeployHistory` + `DeployExecutionPanel`/`DeployHistoryPanel`（deployForm↔deviceExecutions 晚绑定 hooks 解耦），Deploy 2696→709 行。＋切片 6（2026-08-03）：Monitor3D 6 对话框参数化拆 `WaypointEditorDialog`（4 近克隆拐点对话框合一）+ `UploadFloorPlanDialog` + `BindDeviceDialog`，8184→8000 行。＋切片 7（2026-08-03）：Monitor3D 覆盖层拆 `HeatLegendPanel` + `SnmpHealthPanel` + `CanvasToolbar` + `useOverlayPanels`（拖拽/展开收起状态收敛 composable，父侧单实例避免 reset_panels=1 清参竞态），8000→7536 行。＋切片 8（2026-08-03）：Monitor3D 侧栏拆 `SidePanel.vue` + `useCommandPanel`/`useDeviceMappings`（指挥面板状态/设备映射收拢 composable，死代码清理 getDeviceTypeLabel/getStatusLabel/plan-switch/link-*），7536→5688 行。＋切片 9a（2026-08-03）：Monitor3D 场景拆 `useThreeScene`（sceneState 共享对象 + frameUpdate 逐帧组合 + 别名策略 + 事件接线归属演进，死代码清理 COLORS/getTrunkDisplayName/deleteBranchLink/openWaypointDialog/getLinkLabel/startConnectFromBranch/deleteTrunk/deleteBranchPoint/addBranchPointOnTrunk/calculatePositionPercentOnTrunk/getNodeName/getBranchPointsForTrunk/getBranchLinksForPoint/deleteBranchPoint/faultSeverityTag），5687→4981 行。＋切片 9b（2026-08-03）：Monitor3D 场景构建拆 `useSceneBuilders`（全部 build*/glow/pulse/label + disposeGroup + rebuildScene + refreshDeviceVisuals + getTrafficHeatForPath 逐字搬迁，deps 渐进加 builders 字段 + 拓扑 refs 晚声明追加 TDZ 安全，死代码清理 calculatePositionOnTrunk/reusedColor），4981→3971 行。＋切片 9c（2026-08-03）：Monitor3D 画布交互拆 `useCanvasInteraction`（全部鼠标/拖拽/拐点/连线/HUD 逻辑 + screenToPercent/updateDeviceScale/handleWheel + attach/detachSceneListeners/dispose；sceneState.snmpIfaceCache/snmpTrafficCache 共享，WS handler/语言切换经 interaction 暴露的 fetchDeviceInterfaces/fetchUplinkTrafficSamples/showHudForDevice/refreshHudForDevice/refreshCurrentHud 复用，onMounted/onBeforeUnmount 演进至终态，父侧死别名行清理），3971→2117 行；946 全部完成。
- [x] **P2** `:key="index"` 广泛存在（`Operations.vue:18,272,298,388,417,439`、`Compliance.vue:669,688,754`、`Devices.vue:340`）；`views/Logs.vue:286` 每 3 秒全量重载日志；全项目无虚拟滚动。`[已复核]`
  → 修复（批次五 :key-Logs 切片）：新增 `utils/uid.js`（`stampUid` 用 `Object.defineProperty` 定义**不可枚举** `_uid`，JSON 序列化不携带，避免泄漏进 payload / 被后端 `json.dumps` 落地 DB）。表单行改 `:key="xxx._uid"`：Devices:340/DeviceDetail:464 模块行、Deploy:285 变量行，stamp 覆盖初始/reset/add/probe/populate 全部分配点；展示列表改天然稳定键：Operations faultDeviceList→`device_id`、recentBackups→`device_name+backup_time`、alerts→`alert_key` 回退复合、activityFeed→`type+text`，Compliance configLineAnalysis→`lineNum`。探索按 `:key="idx"` 补出 4 处同病 Monitor3D 拐点行（`editingWaypoints`/Trunk/BranchLink/TopoEdge，均 v-model input-number + add/remove），一并 `_uid` 化。Logs 实时 interval 改 `loadLogs(true)`（原不 force 命中 30s 缓存，实际每 30s 才真刷新）；主表改 `el-table-v2` + `el-auto-resizer` 虚拟滚动（仅渲染可视行），列定义 `computed` 随语言响应式，message 列 ellipsis + 原生 title 替代 overflow tooltip。保留 `:key="index"`：Operations:18/24（字符串数组）、Operations:272（并行数组 index 承载）、Compliance:667/686（toc/content 的 active/scroll/ref 全靠 index 且静态）、Deploy:508（cliLogs append-only）、FaultDetail:129（字符串数组）。
- [x] **P2** `Monitor3D.vue` 53 处、`Deploy.vue` 10 处 `console.log`（含 WS 报文）未在生产剥离。`[待验证]`
  → 修复（批次五剩余小项切片）：剥离纯调试 `console.log` 7 处——Monitor3D 1227/1244/3308/3368（创建主干、拓扑缺节点调试）、Deploy 1749/1767/1781（含逐条 WS 报文日志）；保留 catch 内 `console.error`/`console.warn` 错误日志（其余 ~56 处）。`ToolLogs.vue:244` 为 catch 内错误日志但误用 `console.log`，不在本项范围，保留。
- [x] **P2** `utils/requestManager.js:11,155` — `requestCache` 从未写入，配套 10s 清理定时器为空转死代码；`utils/cache.js:253` 同样是模块级常驻定时器。`[已复核]`
  → 修复（批次五请求层切片）：删 `requestCache` Map 与 10s 空转 `setInterval`（`generateRequestKey` 仍被 cancel/create/remove 使用，保留）；删 `cache.js` 模块级 300s `setInterval`（过期条目读时已清、写满时 `writeToStorage` 兜底触发）。
- [x] **P2** `.env.example` 的 `VITE_WS_URL` 源码零引用（WS 地址按 `window.location.host` 拼），配置已失效。`[待验证]`
  → 修复（批次五剩余小项切片）：两处 WS 地址构造改读 `import.meta.env.VITE_WS_URL` 为可选覆盖、缺省回退 `location.host`——Monitor3D（`/ws/device-status`）、Deploy（`/ws/deploy/${sessionId}`）；`.env.example` 注释同步为「可选覆盖」语义。缺省行为不变。

### 批次五 · 请求层切片 · Linux 实测（2026-08-02）

前端改动（仅 `frontend/`），无 vitest，验证靠构建 + 冒烟：

| 检查点 | 结果 |
| --- | --- |
| `npm run build` | ✅ 13.64s 构建成功；`manualChunks` 生效——主 index chunk 1.5MB→295kB（gzip 99.66kB），three/echarts/element-plus/vue-vendor/axios 拆为独立 vendor chunk |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/`、`/login` 均 200（证书在位，`server.https` 守卫正常注入） |
| 后端门禁 | ✅ `ruff check app/ tests/` 全绿；`pytest tests/test_batch1_regressions.py` 15 passed；全量 `pytest --ignore=tests/test_console_service.py` 53 failed / 625 passed / 4 skipped，与批次四基线**失败集合完全一致** |

修复说明：auto-abort 逃生口 `config.noAutoCancel`；`withRetry` 咨询 `shouldRetry`（`apiWithRetry` 写操作 `retries:0`，该导出为死代码）；`cachedRequest` 统一 `ttl` 单位毫秒（Layout/SearchDropdown 秒→毫秒共 5 处）；SSH 翻译键统一 `'lang'`；401 并发去重守卫；`generateCacheKey` 稳定序列化+djb2 哈希。

### 批次五 · 卸载清理切片 · Linux 实测（2026-08-02）

| 检查点 | 结果 |
| --- | --- |
| `npm run build` | ✅ 13.84s 构建成功；Monitor3D chunk 重建（107.44kB），其余 vendor/主 chunk 体积与请求层切片一致 |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/`、`/login` 均 200（仅按精确 PID 启停自起实例，未触碰用户 3001 dev server） |
| 后端门禁 | ✅ `ruff check app/ tests/` 全绿；`pytest tests/test_batch1_regressions.py` 15 passed（前端改动不涉 app/，失败基线不变） |

修复说明：Deploy.vue 实际 4146 行，`startElapsedTicker` 清旧再启消除孤儿计时器，`onBeforeUnmount` 停计时器 + 关 WS；DeviceHealth `chartInstances`/`disposeCharts` 覆盖刷新与卸载两路径；Monitor3D named `handleThemeChange` + 连线监听卸载时直接移除 + 数组材质与纹理 dispose + glow 纹理置空；`useSmartRefresh` 返回 `dispose`（该 composable 零消费者）。

### 批次五 · 剩余小项切片 · Linux 实测（2026-08-02）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + XSS 逻辑复核：

| 检查点 | 结果 |
| --- | --- |
| `npm run build` | ✅ 13.77s 构建成功；主 index 295kB / Monitor3D 107kB，chunk 体积与卸载清理切片一致（500kB 警告为 echarts/element-plus/three 既有大 chunk，非新增） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（自起实例精确 PID 启停，未触碰用户 3001 dev server） |
| XSS 逻辑复核（node 复刻 escape+正则管线） | ✅ `<script>alert(1)</script>`、`<img onerror>` 全部惰性化、无原始危险 token 残留；`**粗体**`/`` `行内` `` markdown 语义不变 |
| 后端门禁 | ✅ `ruff check app/ tests/` 全绿；`pytest tests/test_batch1_regressions.py` 15 passed（前端改动不涉 app/，失败基线不变） |

修复说明：916 唯一 `v-html` 点 escape-first（先转义再正则，白名单标签仅来自替换字符串）；944 剥离纯调试 `console.log` 7 处（含逐条 WS 报文日志），保留 catch 内错误日志；947 两处 WS 构造改 `import.meta.env.VITE_WS_URL` 可选覆盖、缺省 `location.host`。另清单外小项：`main.js` ElementPlus locale 由硬编码 `zhCn` 改为按 `localStorage('lang')` 选 `en`/`zhCn`（挂载时一次，运行中切换不实时更新，超出小项范围）。

### 批次五 · i18n 重建切片 · Linux 实测（2026-08-02）

前端改动（仅 `frontend/`），验证靠 `validate:locales` + 构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（新增校验脚本，无重复键/无缺键；现 zh/en 各 3212 键） |
| `npm run build` | ✅ 13.77s 构建成功；chunk 体积与剩余小项切片一致（500kB 警告为既有大 chunk） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（自起实例精确 PID 启停，未触碰用户 3001 dev server） |
| 后端门禁 | ✅ `ruff check app/ tests/` 全绿；`pytest tests/test_batch1_regressions.py` 15 passed；全量 `pytest --ignore=tests/test_console_service.py` **53 failed / 625 passed / 4 skipped**，失败集合与基线逐项一致（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1），无新增失败 |

修复说明（932/933，i18n 表重建）：去重 183 组重复键（191 冗余行，同值 keep-first、异值 keep-last 行为保持）+ 修正 en 块 4 处漏进中文 + 补 42 en / 2 zh 缺键，新增 `scripts/validate-locales.mjs` 脚本化校验（`package.json` `validate:locales`）；硬编码中文真实 ~140 处（docs 计数含注释行），全在 script 与 Compliance provider 下拉——Monitor3D ~19 / Deploy ~15 / Compliance ~11 条提示 + 模板下拉，逐处换 `t()`（复用 `faultTransferFailed` 等现成键，新增 `monitor3d*`/`deploy*`/`compliance*` 键含 `{param}` 占位）。排除：后端存储值（复核 notes、转维修 description）、逻辑/存储匹配串（`'起点'`、provider map 键）、zh 回退 map（deviceTypeMap/statusMap）、console 日志。

### 批次五 · Pinia 状态集中切片 · Linux 实测（2026-08-02）

前端改动（仅 `frontend/` + 2 个源码断言测试），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键） |
| `npm run build` | ✅ 13.92s 构建成功；chunk 体积与前序切片一致（500kB 警告为既有大 chunk） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（自起实例精确 PID 启停，未触碰用户 3001 dev server） |
| 后端门禁 | ✅ `ruff check app/ tests/` 全绿（venv 内 ruff 0.16.0）；`pytest tests/test_batch1_regressions.py` 15 passed；全量 `pytest --ignore=tests/test_console_service.py` **53 failed / 625 passed / 4 skipped**，失败集合与基线逐项一致（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1），无新增失败 |

修复说明（930，Pinia 状态集中）：新增 `stores/auth.js` + `stores/theme.js`，localStorage 键名不变、零迁移。2 个源码断言测试随实现更新（`tests/test_deploy_security_step4b.py::test_stream_history_uses_authenticated_username_source`、`tests/test_device_security_step4c.py::test_device_status_frontend_sends_access_token` 原断言 `access_token: localStorage.getItem('accessToken')` → `access_token: authStore.accessToken`，安全意图「前端带 token」不变）；`tests/test_faults_security_step4e_b.py:381` 为否定断言（断言旧 `author: localStorage.getItem('currentUser')` 不存在）仍在 FaultDetail.vue 成立，无需改。注意：全量测试须用 venv 解释器（`.venv/bin/python -m pytest`），系统 python 无 ruff 会误报 `test_ruff_static_analysis_is_clean`/`test_git_config.py` 等环境失败。

### 批次五 · :key-Logs 切片 · Linux 实测（2026-08-02）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键） |
| `npm run build` | ✅ 13.85s 构建成功（el-table-v2 / el-auto-resizer / ElTag cellRenderer 编译通过）；chunk 体积与前序切片一致（500kB 警告为既有大 chunk） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（自起实例精确 PID 启停，未触碰用户 3001 dev server） |
| 代码审查 | ✅ 全项目 `:key="index"` 只剩保留清单 4 处（Compliance 669/688 toc-content、Deploy 508 cliLogs；Operations 18/24/272 与 FaultDetail 129 为 `:key="i"/"idx"` 同保留）；`el-table-v2`/`el-auto-resizer` 仅在 Logs.vue；`_uid` 不可枚举（`Object.defineProperty enumerable:false`） |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed；全量 `pytest --ignore=tests/test_console_service.py` **53 failed / 625 passed / 4 skipped**，失败集合与基线逐项一致，无新增失败 |

修复说明（947，:key 稳定化 + Logs 虚拟滚动）：新增 `utils/uid.js` `stampUid`（不可枚举 `_uid`），3 处表单行 + 探索补出的 4 处 Monitor3D 拐点行全部 `_uid` 键；5 处展示列表改天然稳定键；Logs 实时 interval `loadLogs(true)` 修复「读 30s 缓存不真刷新」bug + 主表改 `el-table-v2` 虚拟滚动（message 列 ellipsis + 原生 title 替代 overflow tooltip）。

### 批次五 · 946 Compliance 拆分切片 1 · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新组件只用既有 `t()` 键，无硬编码文本 |
| `npm run build` | ✅ 13.86s 构建成功（`utils/compliance.js` + 4 子组件 import / `defineModel` / props-emits 编译通过） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server，精确 PID 2283407） |
| 代码审查 | ✅ `escapeHtml`/`renderSectionContent`/`parseDocumentSections` 定义仅在 `utils/compliance.js`、调用仅在 `StandardDetailDialog.vue`；已迁走项（`standardUploadRef`/`uploadStandardDocument`/`standardForm`/`currentStandardDetail` 等）在父组件零残留；4 子组件无裸中文（仅注释/`t()`）；`renderSectionContent` 正则顺序与源文件逐字一致 |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 1，Compliance 拆分）：抽 `utils/compliance.js` 纯函数（escape-first markdown 渲染 + 章节解析 + category/severity 映射，无 vue 依赖可单测）；上传标准/Create 标准/规则列表/标准详情 4 个低耦合对话框拆子组件，props/emits 通信（详情对话框 `v-model:generating-rules` 用 `defineModel` 与父共享禁用态）；Compliance.vue 3377→2753 行。Audit/AI 配置/规则详情/Config 高亮 4 对话框与 composable 收拢留待切片 2。

### 批次五 · 946 Compliance 拆分切片 2 · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新组件只用既有 `t()` 键，无硬编码文本 |
| `npm run build` | ✅ 13.86s 构建成功（4 子组件 + `defineModel` + composable + props-emits 编译通过） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server，精确 PID 2283407） |
| 代码审查 | ✅ 已迁走项（`auditForm`/`runAudit`/`ruleEditForm`/`aiConfigForm`/`configLineAnalysis`/`analyzeConfigLines`/`selectConfigLine`/`highlightIssueLines`/`testAIConfig`/`saveAIConfig` 等）在父组件零残留；`analyzeConfigLines`/`getLineClass`/`severityTagType`/`categoryTagType`/`capitalize` 定义仅在 `utils/compliance.js`；4 子组件无裸中文（仅注释/`t()`）；父 `.section-title`（两处）与 `.action-btn.small.primary`/`.table-action-btn.primary`/`.standard-name.clickable` 保留，页面 section 标题样式不变 |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 2，Compliance 拆分）：Audit/AI 配置/规则详情/Config 高亮 4 个高耦合对话框拆子组件——`AuditDialog`（`defineModel('configText')` 与父共享手动审核配置文本，`@completed` 回调写父 `report`，打开重置对齐原 `showAuditDialog`）、`AIConfigDialog`（`watch(() => props.aiConfig, ..., { immediate: true })` 只填表单不含 api_key，保存 `@saved` → 父 `loadAIConfig()` 刷新 status bar）、`RuleDetailDialog`（父 `currentRule` 与 `rules` 表格行是同一对象引用，保存用 `Object.assign(props.currentRule, data.rule)` 原位更新父子同时生效、回滚传播一致）、`ConfigDetailDialog`（分析构建移入子 `watch(modelValue→true)`，`auditForm.config_text` → 父 `auditConfigText` ref）；`utils/compliance.js` 追加 5 个纯函数；新增 `useComplianceStandards` composable 收拢 standards 列表请求与状态（`loadStandards` 保留 debounce 300）；Compliance.vue 2753→934 行。`getDefaultUrl`（全文零引用死代码）与 `configDetailConfigText`（未使用 ref）一并丢弃。

### 批次五 · 946 Deploy 拆分切片 3 · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新组件只用既有 `t()` 键，无硬编码文本 |
| `npm run build` | ✅ 13.82s 构建成功（3 子组件 + `defineModel` + props-emits 编译通过） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server，精确 PID 2283407） |
| 代码审查 | ✅ 已迁走/死代码项（`approvalStatus`/`showApprovalDialog`/`handleApprovalSubmit`/`handleRejectionSubmit`/`startApprovedDeployment`/`getVariableDescription`/`getRiskLevelType`/`getRiskLevelText`/`getWindowLabel`）在父组件零残留；`approveDeployment`/`rejectDeployment` 仅 `api/index.js` 导出、views/ 零引用；7 个纯函数定义仅在 `utils/deploy.js`；父 `.device-info`/`.device-ip` 保留（device-card 样式不变）；3 子组件无裸中文（仅注释/`t()`） |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 3，Deploy 拆分）：Preview/Schedule/VariableHelp 3 对话框拆子组件——`DeployPreviewDialog`（props 收 loading/results/impact/isDark，`defineModel('selectedPreviewDevice')` 与父共享选中设备、收拢 `DiffViewer` 与 `getRiskLevelType`，footer `@schedule`/`@deploy` 回调父 `openScheduleDialog`/`confirmDeployFromPreview`）、`DeployScheduleDialog`（`defineModel('selectedWindow')` 与父共享、`isScheduled`/`scheduledTime` 只读 props、`getWindowLabel` 保留组件内）、`DeployVariableHelpDialog`（纯 el-table，无自定义 CSS）；`utils/deploy.js` 收拢 7 个纯函数（`getDeviceStatusType`/`getDeviceProgressStatus`/`formatDuration`/`formatTime`/`hasBeenRolledBack`/`canRollback`/`getRiskLevelType`，t() 依赖的 `getDeviceStatusText`/`getRiskLevelText`/`getWindowLabel` 留组件内）；死代码清理：approval 状态+3 处理器+`approveDeployment`/`rejectDeployment` 导入、`getVariableDescription`、`Promotion`/`Calendar` 图标、`DiffViewer` 导入、`.warning-*`/`.execution-mode-hint` 死 CSS；共享 `.device-info`/`.device-ip`/`.dialog-footer` 拷贝进子组件、页面级保留父视图；Deploy.vue 4146→3654 行。

### 批次五 · 946 Deploy 拆分切片 4 · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新组件/新 composable 只用既有 `t()` 键，无硬编码文本 |
| `npm run build` | ✅ 13.96s 构建成功（`DeployFormPanel` + `defineModel` 三元组 + `useDeployForm` composable 编译通过） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server，精确 PID 2283407） |
| 代码审查 | ✅ 配置表单脚本在父零残留（`const loadDevices`/`const loadTemplateVariables`/`const addVariable`/`const removeVariable`/`const getVariablePlaceholder`/`const deployForm = ref`/`const executionMode = ref`/`const parallelLimit = ref`/`const canDeploy` 均仅 composable/面板）；`getVariablePlaceholder`/`addVariable`/`removeVariable` 定义仅 `DeployFormPanel.vue`、`loadDevices`/`loadTemplateVariables`/`canDeploy` 定义仅 `useDeployForm.js`（父仅调用）；`handleDeviceChange` 仍在父（写 deviceExecutions）；父模板零配置图标（`Document/Files/Edit/Shield/Connection/Plus/View/Upload/WarningFilled/InfoFilled` 无命中）；`.config-form` 选择器在父 CSS 零残留（仅面板），父 `.nav-action-btn` 全族保留（nav 栏仍用）；新组件/composable 无裸中文（仅注释/`t()`）；7 个纯函数仍仅 `utils/deploy.js` |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 4，Deploy 拆分）：配置表单（模板 48-356）拆 `DeployFormPanel.vue`——`defineModel` 三元组共享可写态：`deploy-form`（与父同一对象引用，表单 v-model 写嵌套属性、redeploy 恢复配置也写同一对象 → UI 响应式一致）、`execution-mode`/`parallel-limit`（子写 radio/input-number、父 confirmDeploy 读 payload）；只读 props 收 `loading/devices/backups/templates/availableVariables/allVariables/canDeploy`；emits `template-change`/`device-change`/`preview`/`deploy` 回调父 `loadTemplateVariables`/`handleDeviceChange`/`previewDeploy`/`confirmDeploy`；变量操作 `getVariablePlaceholder`/`addVariable`/`removeVariable` 面板本地；`useDeployForm` composable 收拢 deployForm/executionMode/parallelLimit/数据 refs/canDeploy/5 个 loader（3 个 `debounce`+`cachedRequest`）/mode→netmiko `watch`，父单次解构、`onMounted` 顺序不变；配置表单 scoped CSS 全量拷入面板（含 `.nav-action-btn` 全族副本），页面级 `.config-column`/`.main-content-area`/`.nav-action-btn`/执行历史/动画/非 scoped 全局块留父；父 import 删 `getDevices/getBackups/getTemplates/getTemplate/getCompatibleVariables`/`debounce`/`watch` 与配置图标、保留 `cachedRequest`（previewDeploy 用）/`clearCache`/`stampUid`（redeploy 用）；注：`Shield` 非 element-plus 图标包导出、原实现即未解析空渲染，面板保留 `<Shield />` 且不导入以保持行为逐字一致；Deploy.vue 3654→2696 行（+`DeployFormPanel.vue` 972 行 +`useDeployForm.js` 196 行）。

### 批次五 · 946 Deploy 拆分切片 5 · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新组件/新 composable 只用既有 `t()` 键，无硬编码文本 |
| `npm run build` | ✅ 13.96s 构建成功（`useDeployExecution`/`useDeployHistory` + `DeployExecutionPanel`/`DeployHistoryPanel` + 晚绑定 hooks 编译通过；唯一修复为 `rollbackDeploy as rollbackDeployApi` 别名） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server，精确 PID 2283407） |
| 代码审查 | ✅ 执行/历史函数在父零残留（`const loadHistory`/`const executeDeploy`/`const handleRollback`/`const loadHistoryRecord`/`const handleRedeploy`/`const handleDeleteHistory`/`const groupedHistory`/`const expandedGroups`/`const handleDeployMessage`/`const scrollToBottom`/`const stopTimer`/`let deployWebSocket`/`let timer` 均仅 composable）；`executeDeployApi`/`taskId` 死代码全仓零残留；`useDeployExecution`/`useDeployHistory` 定义仅各自 `.js`；父模板零执行/历史图标残留（仅 nav 保留 `Loading` 执行标签/`CircleCheckFilled` 完成标签/`CircleCloseFilled`/`QuestionFilled`/`CircleClose`）；`.execution-panel`/`.cli-section-parallel`/`.history-panel`/`.deploy-card`/`.device-card`/`.group-actions` 选择器在父 CSS 零残留，`.deploy-page`/`.execution-column`/`.config-column`/`.nav-action-btn` 保留；新组件/composable 无裸中文（仅注释/HTML 注释/逐字拷入的 `console.error` 调试串）；7 个纯函数仍仅 `utils/deploy.js`，`formatDateTime` 仅 `utils/time` |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 5，Deploy 拆分）：执行/历史簇（模板 67-418）拆 `useDeployExecution` + `useDeployHistory` 双 composable + `DeployExecutionPanel`/`DeployHistoryPanel` 双面板——`useDeployExecution` 收拢 executionStatus/elapsedTime/deviceExecutions/selectedDevice/aborting + 全部执行 computed + WebSocket/timer/handleRollback/abort/scrollToBottom，CLI DOM 改非响应式 `cliOutputEl` 经 `register-cli-output` prop 由面板 onMounted 注入（保留显式 scrollToBottom 语义）；`useDeployHistory` 收拢 deployHistory/groupedHistory/expandedGroups/loadHistoryRecord/handleRedeploy/handleHistoryRollback/handleDeleteHistory + redeployParentId；deployForm↔deviceExecutions 交叉耦合（handleDeviceChange/executeDeploy/handleDeployMessage/handleRollback ↔ loadHistoryRecord/handleRedeploy/handleDeleteHistory 互调）通过晚绑定 hooks/deps 解耦——父构造后接线（`execHooks.reloadHistory=()=>history.loadHistory()` 等 6 个 + `historyDeps.executeDeploy/handleRollback/setDeviceExecutions/setSelectedDevice` 等 4 个），调用处 `?.()` 守卫，避免循环构造；面板 props 收数据/computed、emits `select-device`/`clear-cli`/`rollback`（执行）、`select-record`/`toggle-group`/`rollback-record`/`redeploy-record`/`delete-record`（历史），历史面板 `is-group-expanded` 走谓词 prop；`DeployExecutionPanel` root 为 `.execution-panel`、`.cli-section-parallel` 第二格用 `#history` 插槽注入历史面板（grid 布局不变）；执行/历史 scoped CSS 全量逐字拷入双面板（含 `.nav-action-btn` 副本/`.dark .mini-badge`/`.dark .card-meta`/`expand-*`/动画 keyframes），父只留页面级 + 新增 nav `.is-loading` 旋转（导航状态标签用）；死代码清理：`executeDeployApi`（仅 import 未用）、`taskId`（仅声明）删除；`handleDeviceChange` 简化委托 `initDeviceExecutions(deployForm.target_devices)`（与 executeDeploy 共用 buildDeviceExecutions）；`getDeviceStatusText` 迁执行面板本地（用 t()）；父 import 删 `Loading` 以外的执行/历史图标、`rollbackDeploy`/`getDeployHistory`/`getDeployHistoryDetail`/`deleteDeployHistory`、`formatDateTime`、`useAuthStore`、`clearCache`、`stampUid`、`nextTick`/`onBeforeUnmount`、utils/deploy.js 整段；`onBeforeUnmount`（stopTimer + WebSocket 关闭）迁入执行 composable 内部；preview/schedule 逻辑与 3 对话框留父，`onMounted` loader 顺序不变；Deploy.vue 2696→709 行（+`DeployExecutionPanel.vue` 888 行 +`DeployHistoryPanel.vue` 757 行 +`useDeployExecution.js` 469 行 +`useDeployHistory.js` 285 行）。

### 批次五 · 946 Monitor3D 拆分切片 6 · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新组件只用既有 `t()` 键，无硬编码文本 |
| `npm run build` | ✅ 13.87s 构建成功（3 新组件 + `defineModel` 双向绑定 + 4× 复用 `WaypointEditorDialog` 编译通过） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server，PID 2283407） |
| 代码审查 | ✅ 8 个 add/remove 拐点函数在父零残留（`addWaypoint`/`removeWaypoint`/`addTrunkWaypoint`/`removeTrunkWaypoint`/`addBranchLinkWaypoint`/`removeBranchLinkWaypoint`/`addTopoEdgeWaypoint`/`removeTopoEdgeWaypoint`）；父模板零 `el-dialog` 残留；父 CSS 零 `.waypoint-` 残留，`.no-data`/`.icon-btn`/`.side-panel:not(.dark) .no-data` 保留（侧面板仍用）；`WaypointEditorDialog`/`UploadFloorPlanDialog`/`BindDeviceDialog` 定义仅各自 `.vue`（父仅标签 + import 引用）；新组件无裸中文（仅 HTML/CSS 注释）；`stampUid` 父保留（open 函数仍用）；`Delete`/`Plus` 图标父保留（侧面板仍用） |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 6，Monitor3D 对话框参数化）：模板 101-242 的 6 个 el-dialog 拆 3 个组件——4 个近克隆拐点对话框合一 `WaypointEditorDialog`（props `modelValue`/`title` + `defineModel('waypoints')` 双向绑定父 `editingXWaypoints`，`addWaypoint`/`removeWaypoint` 组件内直接改共享响应式数组，`emit('save')` 由父接管 4 个 save 函数）；`UploadFloorPlanDialog`（`defineModel('planName')` + `fileName`/`uploading` props，`file-change` 转发 + `confirm` 由父 `uploadFloorPlan` 接管，表单状态全留父，行为不变）；`BindDeviceDialog`（`defineModel('deviceId')` + `candidates`/`submitting` props，`cancel`/`confirm` 转发父的 `cancelBind`/`confirmBindDevice`，父保留 `pendingPlacement` 与 API + rebuildScene）；父脚本删 8 个 add/remove 拐点函数（无其他调用点），保留 4 个 open 函数（仍 `.map(stampUid)` 解析，`stampUid` import 保留）与 4 个 save 函数（资源 URL/序列化/局部数组/重建各不同）；父模板改 6 个组件标签（`v-model` 可见 + `v-model:waypoints`/`v-model:plan-name`/`v-model:device-id` + `@save`/`@confirm`/`@file-change`/`@cancel`）；scoped CSS 逐字拷入 `WaypointEditorDialog`（`.waypoint-hint`/`.waypoint-list`/`.waypoint-item`/`.waypoint-index`/`.waypoint-item .el-input-number` + `.no-data` + `.icon-btn` 全族，对话框 teleport 到 body 父 scoped 够不到）；父 CSS 删 `.waypoint-*`（8015-8046）与 `.side-panel:not(.dark) .waypoint-*`（6251-6263 死代码）；父保留 `.no-data`/`.icon-btn`/`.side-panel:not(.dark) .no-data`（侧面板 fiber 树/plans 仍用）；Monitor3D.vue 8184→8000 行（+`WaypointEditorDialog.vue` 139 行 +`UploadFloorPlanDialog.vue` 58 行 +`BindDeviceDialog.vue` 38 行）。

### 批次五 · 946 Monitor3D 拆分切片 7 · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新组件只用既有 `t()` 键，无硬编码文本 |
| `npm run build` | ✅ 13.79s 构建成功（3 新组件 + `useOverlayPanels` composable 编译通过） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server，PID 2283407） |
| 代码审查 | ✅ 父拖拽/可见性状态零残留（仅 useOverlayPanels 解构行：`showHeatLegend`/`showSnmpHealth`/`snmpPos`/`heatPos`/`startDrag`/`toggleSnmpHealth`/`toggleHeatLegend`/`SNMP_PANEL_W`/`HEAT_PANEL_W`/`clampPanelPos`/`resetPanelIfOob`/`loadPanelPos`/`savePanelPos`/`panelDragState`）；父零 `heatLegendLevels`；父零 5 格式化函数（`snmpHealthStatusLabel`/`collectorStatusLabel`/`formatSnmpAge`/`formatDurationMs`/`formatSnmpServerTime`）；父 CSS 零 `.heat-legend`/`.snmp-health-`/`.edit-mode-indicator`/`.canvas-tools`，仅保留 `.monitor3d.panel-hidden .canvas-tools`（跨组件祖先选择器，子根元素带父 scope id 仍命中）；`HeatLegendPanel`/`SnmpHealthPanel`/`CanvasToolbar` 定义仅各自 `.vue`（父仅标签 + import 引用）；`useOverlayPanels` 定义仅在 composables 且父单次调用；icon import 无 `Rank`/`ArrowUp`，`ArrowDown`/`ArrowLeft`/`ArrowRight`/`reactive` 父保留（侧栏/展开树仍用）；新组件无裸中文（仅 HTML/CSS 注释 + 既有英文 'ifIndex '） |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 7，Monitor3D 覆盖层拆组件）：模板 8-93 的 3 个覆盖层块拆 3 个纯展示组件 + 1 个状态 composable——`HeatLegendPanel`（props `pos`/`collapsed`/`dark`/`summary`，emits `start-drag`/`toggle`，`heatLegendLevels` computed 迁入组件内依赖 `t`，scoped CSS 拷 `.heat-legend` 族 6312-6383 + `.drag-handle` + `.heat-legend-head:hover .drag-handle` 半边）；`SnmpHealthPanel`（props `pos`/`collapsed`/`dark`/`summary`/`items`/`now`，emits `start-drag`/`toggle`/`refresh`，5 个格式化函数迁入组件内依赖 `t`，scoped CSS 拷 `.snmp-health-panel` 族 6385-6526 + `.drag-handle` + `.snmp-health-head:hover .drag-handle` 半边）；`CanvasToolbar`（props `isEditMode`/`isFullscreen`/`discoveringNeighbors`，emits 6 个动作转发父的 `toggleEditMode`/`resetView`/`topView`/`discoverNeighbors`/打开上传对话框/`toggleFullscreen`，scoped CSS 拷 `.canvas-tools` 6297-6305 + `.edit-mode-indicator` 7557-7568）；`useOverlayPanels`（从 667-766 拖拽块收敛：loadPanelPos/savePanelPos/clampPanelPos/resetPanelIfOob/SNMP_PANEL_W/HEAT_PANEL_W/PANEL_MARGIN/两面板 reactive 位置/reset_panels=1 处理/panelDragState/startDrag/onPanelDragMove/onPanelDragEnd/两 toggle，`HEADER_H` 死代码丢弃；必须父侧单实例——reset_panels=1 处理会 replaceState 清参，多实例第二个找不到参数不重置）；父模板 8-93 改 3 个组件标签，`@start-drag` 转发 `startDrag(e, heatPos, HEAT_PANEL_W)` 等（父仍持有 pos ref）；父脚本删 heatLegendLevels(656-663)、拖拽块(667-766)、5 格式化函数(5456-5499)，icon import 删 `Rank`/`ArrowUp`，加 3 组件 import + `useOverlayPanels` 解构；父 CSS 删 `.canvas-tools`(6297-6305)/`.heat-legend` 族(6312-6383)/`.snmp-health-panel` 族(6385-6526)/`.edit-mode-indicator`(7557-7568)，保留 `.monitor3d.panel-hidden .canvas-tools`(6307-6309) + `.panel-toggle` 族(6264-6295，耦合 hidePanel/侧栏留切片 8)；数据 refs/加载器/轮询/`getTrafficHeatForPath` 全留父（scene buildDataLinkPaths 2918 仍用 trafficHeat*）；Monitor3D.vue 8000→7536 行（+`HeatLegendPanel.vue` 141 行 +`SnmpHealthPanel.vue` 258 行 +`CanvasToolbar.vue` 68 行 +`useOverlayPanels.js` 122 行）。

### 批次五 · 946 Monitor3D 拆分切片 8 · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新组件/新 composable 只用既有 `t()` 键，无硬编码文本 |
| `npm run build` | ✅ 13.87s 构建成功（`SidePanel.vue` + 2 composables + `defineModel` 8 个双向绑定编译通过；Monitor3D chunk 109.06→116.07 kB，新文件同属懒路由 chunk 属预期） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server，PID 2283407） |
| 代码审查 | ✅ 父模板零 `<aside`/`class="command-`/`class="fiber-`/`class="plan-`/`class="kpi`/`class="palette` 残留（全迁 `SidePanel.vue`）；父脚本零残留（除解构行）`commandSummary`/`monitorEvents`/`eventWindow`/`loadCommandSummary`/`loadMonitorEvents`/`setEventWindow`/`formatEventTime`/`deviceTemplates`/`getDeviceTypeLabelI18n`/`getStatusLabelI18n`/`deviceStatus`/`isDeviceOnline`/`isDeviceOffline`/`faultSeverityTag`/`sidebarTab`/`getDeviceTypeLabel`/`getStatusLabel`；父 CSS 仅保留 `.monitor3d.panel-hidden .side-panel`/`.monitor3d.fullscreen-mode .side-panel` 两祖先规则（子根元素带父 scope id 仍命中，切片 7 同款）；`SidePanel` 定义仅在 `SidePanel.vue`、`useCommandPanel`/`useDeviceMappings` 定义仅在 composables；父 icon import 仅 `ArrowLeft, ArrowRight`；新文件无裸中文（仅 HTML/CSS 注释 + 既有英文 'BP-'/'Link-'/'Edge-'/'ifIndex ' + verbatim map 中文回退） |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 8，Monitor3D 侧栏拆组件）：模板 80-491 的整个 `<aside class="side-panel">` 拆 `SidePanel.vue` 单一展示组件 + 2 个 composable——`useCommandPanel`（指挥面板状态：`commandSummary`/`monitorEvents`/`eventWindow` + `loadCommandSummary`/`loadMonitorEvents`/`setEventWindow`，**父侧单实例**：`commandSummary` 被场景 `buildImpactGlow`(2800) 共享；设计为 `useCommandPanel(() => currentPlanId.value)` 惰性 getter——箭头闭包只创建不执行，TDZ 安全，加载器运行晚于 setup）；`useDeviceMappings`（纯映射函数无共享可变状态，父场景 HUD/标签与 SidePanel 模板**双实例调用均安全**：deviceTemplates/statusI18nKey/getStatusLabelI18n/deviceTypeI18nKey/getDeviceTypeLabelI18n（函数体内调 `t()` 保语言切换响应式）/deviceStatus/isDeviceOffline/isDeviceOnline/faultSeverityTag，`getDeviceTypeLabel`/`getStatusLabel` 死代码丢弃）；`SidePanel.vue`（props 20 + emits 28 + `defineModel` 8 个与父 ref 初值一致的默认值，`sidebarTab`/`formatEventTime` 迁组件内，模板交互全部 `emit` 转发父，`@upload="showUploadDialog = true"`；scoped CSS 按 6 块逐字搬迁，删 `.plan-switch`/`.no-plan-hint`/`.link-list`/`.link-item`/`.link-info`/`.link-actions` 死代码）；父模板 80-491 改 `<SidePanel>` 标签，`@refresh="loadCommandPanelData"`/`@focus-incident="focusIncidentEvent"` 等；父脚本删 refs 块/mapping 块/sidebarTab/4 个加载器与格式化函数，保留 `loadCommandPanelData`/`focusIncidentEvent`/`getBranchPointsForCable`/`getBranchLinksForTopoNode`/全部场景/树/故障函数（场景耦合），icon import 精简为 `ArrowLeft, ArrowRight`（`Cpu`/`Close`/`FullScreen` 无用法一并删）；父 CSS 删 6 块，保留 `.panel-toggle` 族 + `.monitor3d.edit-mode .canvas-host` + 全部 HUD CSS（`:deep(.device-label)`/`:deep(.device-hud)`/`:deep(.topo-label)`/`@keyframes pulse`）；发现 `.hud-incident` 规则编译为 `.incident-meta .hud-incident[data-v]` 匹配任何节点（innerHTML 3D HUD 无 data-v），父内本就是死代码，逐字搬迁行为完全不变；Monitor3D.vue 7536→5688 行（+`SidePanel.vue` ~1050 行 +`useCommandPanel.js` 41 行 +`useDeviceMappings.js` 80 行）。

### 批次五 · 946 Monitor3D 拆分切片 9a · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新 composable 只用既有 `t()` 键与注释，无硬编码文本 |
| `npm run build` | ✅ 13.74s 构建成功（`useThreeScene.js` 编译通过，Monitor3D 模板 `resetView`/`topView`/`toggleFullscreen`/`focusDevice` 绑定经 `const { ... } = three` 解构解析） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server） |
| 代码审查 | ✅ 父零 `initScene(`/`fitView(`/`topView(`/`resetView(`/`toggleFullscreen(`/`loadFloorPlanTexture(`/`animateCameraTo(`/`scheduleAutoFocusOffline(`/`onFullscreenChange`（全部改 `three.xxx`）；父零 `const ctx = shallowRef`/`const plan = {`/`const raycaster =`/`const pointer =`/`let offlineGlowTexture`/`let impactGlowTexture`/`const snmpIfaceCache`/`const snmpTrafficCache`（全收 sceneState）；父零死代码 COLORS/getTrunkDisplayName/deleteBranchLink/openWaypointDialog/getLinkLabel/startConnectFromBranch/deleteTrunk/deleteBranchPoint/addBranchPointOnTrunk/calculatePositionPercentOnTrunk/getNodeName/getBranchPointsForTrunk/getBranchLinksForPoint/faultSeverityTag；父仅经别名引用 `ctx`/`plan`/`percentToWorld`/`getDeviceBaseSize`/`raycaster`/`pointer`/`EMISSIVE_*`/`STATUS_COLOR`/`STATUS_EMISSIVE`；`useThreeScene` 定义仅在 composable；新 composable 无裸中文（仅注释 + console.error + 既有英文 'BP-' 等） |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 9a，Monitor3D 场景核拆 `useThreeScene`）：从 1478-1538 常量块 + 1540 前部 + initScene/onResize/resetView/topView/fitView/toggleFullscreen/onFullscreenChange/loadFloorPlanTexture + focusDevice/animateCameraTo/focusOfflineCluster/resetViewAnimated/scheduleAutoFocusOffline + dispose 逐字搬迁；`sceneState` 普通对象（**不可 reactive/ref 包裹**，deep-proxy 破坏 three 对象）承载 `ctx`（shallowRef）`/plan`/`raf`/`raycaster`/`pointer`/`DEVICE_SIZE_RATIO`/`STATUS_COLOR`/`STATUS_EMISSIVE`/`EMISSIVE_ON`/`EMISSIVE_OFF`/`getDeviceBaseSize`/`percentToWorld`（两方法三 composable 共用必须放 sceneState）/`floorPlanLoadId`/`offlineGlowTexture`/`impactGlowTexture`/`focusAnimationId`/`autoFocusDebounceTimer`/`snmpIfaceCache`/`snmpTrafficCache`/`frameUpdate`；父 setup 在 mode refs 后建 `deps`（9a 仅 useThreeScene 消费字段：canvasHost/isFullscreen/floorTiltAngle/autoFocusOffline/filteredDevices/nodes/selectedDevice/currentPlan/deviceMappings.isDeviceOffline），`const three = useThreeScene(deps)` 后**别名策略**：`const ctx = sceneState.ctx`/`const plan = sceneState.plan`/解构 `percentToWorld`/`getDeviceBaseSize`/`raycaster`/`pointer`/`EMISSIVE_*`/`STATUS_*`——对象引用共享，父剩余 builder/interaction 代码零改名；**frameUpdate 组合**父 setup 顶层赋值（`pulseOfflineDevices`/`updateOfflineGlow`/`updateImpactGlow`/`pulseOfflineLinks`/`refreshHoveredHud`/`updateLabelVisibility`，均父 hoisted 函数声明）——initScene 首帧同步执行，必须在 onMounted 前就位；**事件接线归属演进**：initScene 不再接 wheel/click/mousedown/mousemove 4 个 domElement 监听，父 onMounted 在 `three.initScene()` 后手动接（`handleWheel` 保持 `{ passive: false }`），onBeforeUnmount 手动移，window resize 始终由 initScene 接/dispose 移；**onMounted/onBeforeUnmount 演进**：onMounted = `three.initScene()` + 父接 4 监听 + `await loadData()` + `three.loadFloorPlanTexture()` + 父 build*/buildOfflineGlow + `requestAnimationFrame(() => three.fitView())` + WS/轮询 + `three.onFullscreenChange` 挂 document；onBeforeUnmount = `three.dispose()`（rAF cancel × 2 + window resize 移除 + autoFocusDebounceTimer 清理 + controls/renderer dispose + scene traverse 全量 dispose（数组材质 + mat.map）+ glow 纹理 dispose 置空 + host 移除 renderer/labelRenderer DOM）+ 父 theme/WS/轮询/fullscreenchange 清理 + 中间态父保留的 HUD/wiring/4 domElement/onDragMove/onDragEnd 清理；不可别名（被重赋值）字段：`raf`/`offlineGlowTexture`/`impactGlowTexture`/`snmpIfaceCache`/`snmpTrafficCache`/`floorPlanLoadId`/`focusAnimationId`/`autoFocusDebounceTimer` → 父侧剩余引用改 `sceneState.*`（glow 纹理 ~8 处、snmp 缓存 ~14 处、WS handler 4 处）；死代码清理：COLORS + 9a 表内 15 个函数（含 `faultSeverityTag` 从 useDeviceMappings 解构中删，SidePanel.vue 直接 import 不受影响）；发现父侧 `ctx`/`plan`/`percentToWorld` 旧声明与别名重声明冲突（`shallowRef`/`plan` 字面量 + `function percentToWorld` 各一处）——一次全删，构建即过；Monitor3D.vue 5687→4981 行（+`useThreeScene.js` 535 行）。

### 批次五 · 946 Monitor3D 拆分切片 9b · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新 composable 只用既有 `t()` 键与注释，无硬编码文本 |
| `npm run build` | ✅ 13.87s 构建成功（`useSceneBuilders.js` 1009 行编译通过；Monitor3D 模板与 `builders.xxx` 调用点全部解析） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server） |
| 代码审查 | ✅ 父零 9b 函数定义（createDeviceModel/buildDeviceModels/buildLinks/buildTopoEdges/buildDataLinkPaths/buildLabels/buildPortAnchors/buildOfflineGlow/updateOfflineGlow/buildImpactGlow/updateImpactGlow/pulseOfflineDevices/pulseOfflineLinks/updateLabelVisibility/disposeGroup/rebuildScene/getTrafficHeatForPath/refreshDeviceVisuals/getTopoNodeRenderPos），仅 `builders.xxx` 调用（~38 处）+ 注释 1 处；父零 `calculatePositionOnTrunk`/`reusedColor` 死代码；`useSceneBuilders` 定义仅在 composable（父仅 import + 调用）；新 composable 无裸中文（仅注释 + console.error + 既有功能判断 `label.includes('起点')`） |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 9b，Monitor3D 场景构建拆 `useSceneBuilders`）：从父逐字搬迁 19 个构建函数 + 相关常量——`getTopoNodeRenderPos`(1011-1027)/`buildTopoEdges`(1029-1253)/`createDeviceModel`(1299-1346)/`buildDeviceModels`(1551-1577)/`disposeGroup`(1579-1596)/`rebuildScene`(1598-1615)/`buildLinks`(1617-1743)/`buildDataLinkPaths`(1786-1890)/`buildPortAnchors`(1962-2047)/`buildLabels`(2194-2229)/pulse/glow 块(2231-2426，`reusedColor` 死代码删)/`LABEL_SHOW_DISTANCE`+`updateLabelVisibility`(2428-2454)/`getTrafficHeatForPath`(4132-4148)/`refreshDeviceVisuals`(4464-4475)，Python 脚本带边界断言提取+删除（防止转录偏差）；**composable 单例**：`useSceneBuilders(sceneState, deps)` 内部别名 `ctx`/`plan` + 解构 `percentToWorld`/`getDeviceBaseSize`/`STATUS_COLOR`/`STATUS_EMISSIVE`，再解构 deps 的 refs（nodes/devices/links/filteredDevices/devicePaths/devicePorts/topoNodes/topoEdges/isEditMode/selectedTopoEdgeId/showLabels/showDataLinks/trafficHeatItems/trafficHeatByDevice/commandSummary/deviceMappings→deviceStatus+isDeviceOffline）——函数体逐字不改，依赖同源对象引用共享；**deps 渐进加字段**：9a 的 deps 追加 builders 消费的 refs（devices/links/devicePaths/trafficHeatItems/trafficHeatByDevice/commandSummary/showLabels/showDataLinks/isEditMode/selectedTopoEdgeId，deviceMappings 补 deviceStatus）；**拓扑 refs 晚声明 TDZ 安全**：`devicePorts`/`topoNodes`/`topoEdges` 声明在 deps 创建点（1031）之后（1290 前），不能进 deps 字面量——在声明后 `deps.devicePorts = devicePorts` 追加 + `const builders = useSceneBuilders(sceneState, deps)`，父同点实例化，frameUpdate 箭头闭包（1046）引用 `builders` 运行晚于 setup 无 TDZ；**frameUpdate 演进**：前 3 + 末 1 改 `builders.xxx`（pulseOfflineDevices/updateOfflineGlow/updateImpactGlow/pulseOfflineLinks/updateLabelVisibility），`refreshHoveredHud()` 仍父（9c 移交 interaction）；**调用点改 `builders.xxx`**（~38 处）：watch(isEditMode)/toggleEditMode/loadFiberData(disposeGroup 5 组 + buildTopoEdges + buildDataLinkPaths)/addLink/deleteLink/saveWaypoints/saveTopoEdgeWaypoints/confirmBindDevice/deleteNode/updateDeviceScale/watch([filterType,filterStatus])→rebuildScene/watch(isEditMode)→buildTopoEdges/discoverNeighbors/loadTopoData/onCanvasMouseDown(选中 TopoEdge)/onWaypointDragMove/onTrunkWaypointDragMove/onTopoEdgeWaypointDragMove/onTopoEndpointDragMove/onDragEnd/loadCommandPanelData→buildImpactGlow/refreshTrafficHeatLayer/goToDeviceDetail 尾部/switchPlan/uploadFloorPlan/watch 重建/WS handleInterfaceStatusChange+reconcileDeviceReachability→refreshDeviceVisuals/onMounted build* 全部；父 CSS 不动，`CSS2DObject`/`* as THREE` 父仍用（HUD 2683 处 new CSS2DObject），import 保留；onMounted/onBeforeUnmount 结构不变（9b 无新 teardown 移交）；Monitor3D.vue 4981→3971 行（+`useSceneBuilders.js` 1009 行）。

### 批次五 · 946 Monitor3D 拆分切片 9c · Linux 实测（2026-08-03）

前端改动（仅 `frontend/`），验证靠构建 + HTTPS 冒烟 + 代码审查：

| 检查点 | 结果 |
| --- | --- |
| `npm run validate:locales` | ✅ 0 违规（无 locales 改动，zh/en 各 3212 键）；新 composable 只用既有 `t()` 键与注释，无硬编码文本 |
| `npm run build` | ✅ 13.82s 构建成功（`useCanvasInteraction.js` 1937 行编译通过；Monitor3D 模板 `updateDeviceScale` 别名 + 全部 `interaction.*` 调用点解析） |
| `npm run dev` HTTPS 冒烟 | ✅ `curl -k https://localhost:3000/login`、`/` 均 200（复用既有 dev server） |
| 代码审查 | ✅ 父零 9c 函数定义（onCanvasMouseDown/onCanvasMouseMove/onCanvasClick/onDragMove/onDragEnd/handleWheel/updateDeviceScale/screenToPercent/findNearbyDevice/findNearbyCoreDevice/onPortAnchorMouseDown/finishWiring/cancelWiring/onWiringMouseMove/onWiringMouseUp/全部 drag move/end + 全部 HUD 函数 + ensureHudPanel/showHudForDevice/updateHudContent/refreshHoveredHud/refreshCurrentHud/attach/detachSceneListeners），仅 `interaction.*` 调用 + 模板别名 1 处；父零 `THREE.`/`CSS2DObject`/`formatDateTime`（import 已删）；父死别名解构行删除（percentToWorld/getDeviceBaseSize/raycaster/pointer/EMISSIVE_*/STATUS_* 父零使用）；`useCanvasInteraction` 定义仅在 composable；新 composable 无裸中文（仅注释 + console.error） |
| 后端门禁 | ✅ `pytest tests/test_batch1_regressions.py` 15 passed（改动仅 frontend/） |

修复说明（946 切片 9c，Monitor3D 画布交互拆 `useCanvasInteraction`）：从父逐字搬迁 22 个交互块——`screenToPercent`/`updateDeviceScale`/`handleWheel`/`onPortAnchorMouseDown`/`updateRubberBandLine`/`finishWiring`/`cancelWiring`/drag 状态变量/`onCanvasMouseDown`/全部 7 组 DragMove+DragEnd（waypoint/trunkWaypoint/topoEdgeWaypoint/topoEndpoint/trunkEndpoint/branchPoint/branchLinkWaypoint）/`findNearbyDevice`+`findNearbyCoreDevice`/HUD 块（hudObj/hudEl/hudDeviceId/hudPinnedDeviceId/hudAutoHideTimer + SNMP TTL 常量 + fetchDeviceInterfaces/fetchUplinkTrafficSamples/getUplinkInterfaces/getPrimaryTrafficInterface/getPeerInfo/getUplinkTraffic/getUplinkTrafficSamples/getUplinkTrendSvg/getUplinkStatus/getDeviceAlarmCount/formatCheckTime/formatBps/buildSparklinePath/getRecommendationSummary/ensureHudPanel/hideHudPanel/positionHudForDevice/showHudForDevice/updateHudContent）/`lastHoverCheck`+`lastHudRefresh`+`refreshHoveredHud`+`onCanvasMouseMove`+`onCanvasClick`/`onDragMove`+`onDragEnd`/`onWiringMouseMove`+`onWiringMouseUp`，Python 脚本带边界断言提取+删除（防止转录偏差）；**composable 单例**：`useCanvasInteraction(sceneState, deps, builders)` 内部别名 `ctx`/`plan` + 解构 `percentToWorld`/`getDeviceBaseSize`/`raycaster`/`pointer`/`EMISSIVE_ON`/`EMISSIVE_OFF`，再解构 deps 的 refs（isEditMode/selectedDevice/selectedNode/selectedTopoEdgeId/trunkCreateMode/trunkStartPoint/trunkEndPoint/branchPointCreateMode/connectFromBranchMode/selectedBranchPoint/selectedTopoBranchPoint/devices/nodes/links/fiberTrunks/fiberBranchLinks/devicePaths/topoNodes/topoEdges/currentPlanId）+ `t` + deviceMappings（deviceStatus/isDeviceOffline/getStatusLabelI18n/getDeviceTypeLabelI18n）+ 父回调函数声明（createFiberTrunk/connectDeviceFromTopoBranch/connectDeviceFromBranch/addBranchPointOnTopoEdge/openTopoEdgeWaypointDialog/loadTopoData/loadFiberData/getActiveFaultForDevice，函数声明 hoisted 进 deps 字面量无 TDZ）——函数体逐字不改，依赖同源对象引用共享；**deps 渐进加字段**：9b 的 deps 追加 interaction 消费字段（selectedNode/currentPlanId/trunk/branch 模式 refs/fiberTrunks/fiberBranchLinks/t，deviceMappings 补 getStatusLabelI18n/getDeviceTypeLabelI18n，回调 8 个），拓扑 refs 仍走晚声明追加；**interaction 实例化在 builders 之后**（1195），frameUpdate 箭头闭包（1051）引用 `interaction` 运行晚于 setup 无 TDZ，`refreshHoveredHud()` → `interaction.refreshHoveredHud()`；**HUD 状态闭包 + 复用桥**：hudObj/hudEl/hudDeviceId/hudAutoHideTimer 等 HUD 状态留在 interaction 闭包，父 WS handler/语言切换不直读——新增 `refreshCurrentHud()`（语言切换，封装 hudDeviceId/hudEl/hudObj.visible 检查后 updateHudContent）与 `refreshHudForDevice(device)`（设备可达性变化，`hudDeviceId === device.id` 才刷新），WS `handleInterfaceStatusChange` 改 `interaction.fetchDeviceInterfaces`/`fetchUplinkTrafficSamples`/`showHudForDevice(device,6000)`，`handleDeviceStatusChange` 改 `interaction.refreshHudForDevice(device)`；`sceneState.snmpIfaceCache`/`snmpTrafficCache` 保持 sceneState 共享（WS 失效 + interaction 读写）；**事件接线终态**：父 onMounted 的 4 个 domElement 监听改 `interaction.attachSceneListeners(domElement)`（wheel `{ passive: false }` + click/mousemove/mousedown），onBeforeUnmount 中 wiring window 监听/hudAutoHideTimer/4 domElement 移除/onDragMove+onDragEnd/释放 HUD 全部移交 `interaction.dispose()`（内部先清 hudAutoHideTimer + 移 wiring window 监听 + detachSceneListeners + scene.remove(hudObj)）；`wiringState` ref 迁入 interaction 闭包（父零引用），`devicePorts`/`topoNodes`/`topoEdges` refs 留父经 deps 共享；**模板/父调用点改 `interaction.xxx`**：toggleEditMode→cancelWiring、startConnectFromTopoBranch→findNearbyCoreDevice、onCanvasDrop→screenToPercent、模板 `@update-device-scale` 用 `const { updateDeviceScale } = interaction` 别名；**父 import 清理**：`* as THREE`/`CSS2DObject`/`formatDateTime` 父零使用删除，加 `useCanvasInteraction`；父死别名解构行（percentToWorld/getDeviceBaseSize/raycaster/pointer/EMISSIVE_*/STATUS_*）全部随代码迁走父零使用，删除；Monitor3D.vue 3971→2117 行（+`useCanvasInteraction.js` 1937 行），946 全部打勾。

---

## 批次六 · 工程与清理

- [x] **P0** venv 内无任何 linter（pyflakes / ruff / flake8 全部未安装）——批次一里 4 个 undefined-name 都能被 `ruff F821` 一次抓出。接入 ruff 是本清单投入产出比最高的一项。`[已复核]`
  → 已完成：新增 `ruff.toml`（门禁规则 F821/F822/F823/F811/F632/E9，刻意不启用 E712 因为 SQLAlchemy 的 `filter(Column == True)` 是必要写法），`requirements.txt` 钉 `ruff==0.16.0`，并用 `tests/test_batch1_regressions.py::test_ruff_static_analysis_is_clean` 把门禁接进测试
  → 未纳入门禁的技术债：F401 未使用导入约 200 处、F841 未使用局部变量约 20 处（其中少数指向真实死逻辑，如 `deploy/router.py:1140` 的 `deploy_data`）
- [x] **P1** 测试覆盖结构性偏斜：38 个测试文件 / 430 个用例，`pytest --collect-only` 干净通过，但全部集中在 service 层；router、streaming service、celery task 三条链路零覆盖，正是批次一全部故障的所在。`[已复核]`（批次八全部完成 ✅ 2026-08-04：切片 A router 层 26 项、切片 B streaming 层 4 项、切片 C celery 层 4 项，共 +34 → 788 passed / 4 skipped；**切片 C 顺带暴露 analyze_fault_task 真实缺陷，见下方新 P1 项**）
- [x] **P0**（执行中新发现）`tests/test_console_service.py` 会**挂起**（collect 17 项后无进展，>45s 无输出），导致 `pytest` 全量跑不完 —— 该文件之后的用例长期从未执行过。原因指向 console 服务的同步串口 IO（批次三 3.1）。当前 CI 需先 `--ignore=tests/test_console_service.py` 才能拿到完整结果。`[已复核]` `[已修复]`
  → 修复（批次六切片 A）：真因不在 service 而在测试自身——① 9 处 `patch` 目标仍是旧路径 `app.services.console_service`（`app/services/console_service.py` 已删，代码在 `app/features/console/console_service.py`），4 个用例 fast-fail（AttributeError）；② `test_send_command_success` 把 `mock_serial.in_waiting = 20` 设为常量，`send_command` 的 `while in_waiting:` 读循环永不耗尽 → 死循环挂死（非 collect 挂起）。修复：9 处 patch 路径改 `app.features.console.console_service`；`in_waiting` 改 `type(mock_serial).in_waiting = PropertyMock(side_effect=[20, 20, 0])` 模拟耗尽。17/17 通过，全量 pytest 不再需要 `--ignore`。
- [x] **P1** `core/celery_app.py:36-48` + `tasks/__init__.py:30` — 任务路由指向三个空占位模块，全局无 `beat_schedule`；`tasks/__init__.py` 在导入时写磁盘生成占位文件。`[已复核]` `[已修复]`
  → 修复（批次六切片 A）：`tasks/__init__.py` 导入期写占位文件的副作用已先期消除（当前为纯 docstring + `__all__`，占位模块是仓库真实文件）。本切片清掉残留悬挂 route `"app.tasks.discovery_tasks.*": {"queue": "device_ops"}`（`app/tasks/discovery_tasks.py` 不存在，路由永不命中属死配置）；`celery_app` 导入验证通过、routes 归一为 5 个真实模块。`notification_tasks`/`scheduled_tasks` 空占位与全局无 `beat_schedule` 保留——属「功能未实现」而非缺陷，见下方实测。
- [x] **P1** `frontend/npm ci` 在当前网络下失败（`SELF_SIGNED_CERT_IN_CHAIN`，registry 指向 npmmirror）→ 前端无法构建验证。需决定：配置企业 CA 证书，或改用内网镜像。`[已复核]` `[已验证]`
  → 已随网络/镜像状态变化解决（批次六切片 A）：真实 `npm ci` 98 包 6s 成功（`--dry-run` 3s 先行确认 registry 可达），随后 `npm run build` 18.54s、`validate:locales` 3212/3212 全过，前端构建验证链恢复。无需再配置企业 CA 或改镜像。
- [x] **P2** `frontend-react/`（17 文件、5 个页面骨架、独立 vite/tsconfig）是停滞的并行重写，构成第二套事实标准，建议归档或删除。`[已复核]` `[已修复]`
  → 修复（批次六切片 B）：`git rm -r frontend-react/` 删除 17 文件停滞重写（git 历史可恢复）；连带清掉 `docker-compose.yml` 的 `frontend-react:` 服务（build context 指向已删目录）与 `ruff.toml` 中对应 exclude 项。
- [x] **P2** `backend/`（22 文件）已在 `README_ARCHIVED.md` 中标注"自 2026-06-05 废弃、不可运行"，但仍在仓库内，建议删除或移出。`[已复核]` `[已修复]`
  → 修复（批次六切片 B）：`git rm -r backend/` 删除 22 文件废弃后端（README_ARCHIVED.md 2026-06-05 已标注不可运行）。
- [x] **P2** `frontend/src/locales/index.js.backup`（2277 行）留在 `src/` 内，会被 vite 扫描。`[已复核]` `[已修复]`
  → 修复（批次六切片 B）：`git rm frontend/src/locales/index.js.backup`，全仓库无引用。
- [x] **P2** `data/nas.db`（663 KB，2026-07-16）是迁 PG 前的遗留库，缺 `config.yaml` 时任何脚本都会默认打开它。建议改名为 `nas.db.legacy-20260716`。`[已复核]` `[已修复]`
  → 修复（批次六切片 B）：`mv data/nas.db data/nas.db.legacy-20260716`（`data/` 未纳入 git，纯文件系统操作）。`scripts/legacy_sqlite/*` 与 `_migrate_sqlite_to_pg.py` 的默认路径仍指向 `data/nas.db`，改名后这些一次性脚本会报「文件不存在」而非静默打开遗留库，符合改名初衷。
- [x] **P2** `scripts/seed_data.py:35-41` 用 `query().delete()` 批量清表并在 `:640` 调 `init_db()`，误在生产执行即清库，建议加环境确认。`[已复核]` `[已修复]`
  → 修复（批次六切片 B）：`main()` 顶部加环境守卫——`os.environ.get("NAS_SEED_CONFIRM") != "1"` 时打印拒绝说明并 `return 1`，发生在任何 DB 连接/初始化之前（误执行零副作用）。实测无环境变量即 exit=1 拒绝。README 三处用法同步为 `NAS_SEED_CONFIRM=1 python scripts/seed_data.py`。
- [x] **P2** `scripts/migrate_features.py` 是代码搬迁 codemod（会覆盖 `app/shared/*.py`）而非 DB 迁移，放在 scripts 里有误执行风险。`[已复核]` `[已修复]`
  → 修复（批次六切片 B）：`git mv` 至 `scripts/devtools/migrate_features.py`，移出 scripts 命名空间、明确为一次性 codemod 工具（git 历史保留 move）。`app/services/` 仍有活跃模块故不删。
- [x] **P2** 异常体系混用：`shared/exceptions.py` 有完整 `AppException` 体系，devices/templates 用它，faults/maintenance/deploy 全用 `HTTPException`。`[已复核]` `[已记录]`
  → 保留现状（批次六切片 C）：`AppException` 体系已注册全局 handler（`app/main.py:109` `register_exception_handlers`），与 `HTTPException` 两套共存由框架分别处理，行为安全；统一迁移风险 > 收益（会扰动批次七 53 失败基线），留待后续。
- [x] **P2** 三处重复的 vendor→driver 映射：`deploy/napalm_service.py:33`、`deploy/deploy_stream_service.py:300`、`devices/drivers/registry.py`。`[已复核]` `[已修复]`
  → 修复（批次六切片 C，安全子集）：`napalm_service.py` 的 `NapalmDeployService.driver_map`+`get_driver_name`（原 :31/:75）与 `NapalmStreamService.driver_map`（原 :361）是**死代码**（app 层零调用，grep 确认仅定义处）→ 删除；`connect_device`/`_connect_device` 早已用 `DriverRegistry.get(vendor).NAPALM_DRIVER`。`registry.py` 是 canonical 源不动。`deploy_stream_service.py:272` 内联 `vendor_driver_map`（`juniper→junos`/`arista→eos`/`h3c→huawei`）是**活代码**且与 registry 分歧（registry 缺 juniper/arista 驱动、`h3c_comware` NAPALM_DRIVER=None）——直换会改变这三类设备部署行为，属需真机验证的行为性统一，**保留**并记录。
- [x] **P2** 裸 `except:` 静默降级：`compliance/compliance_service.py:279`、`faults/router.py:335`、`discovery/discovery_service.py:130`、`shared/models.py:207`、`deploy/router.py:907`。`[已复核]` `[已修复]`
  → 修复（批次六切片 C）：docs 所列 5 处 + `models.py` 全部 10 处裸 `except:`（实际 101/211/976/986/1125/1135/1222/1232/1427/1437，全为 JSON/解析 fallback）→ `except Exception:`（裸 except 误捕 KeyboardInterrupt/SystemExit 是真正缺陷）。`compliance_service.py:285` 与 `faults/router.py:381` 加 `logger.warning`（`as e`）；`discovery_service.py:132` 端口探测失败回退 False 属常规路径不加日志。`deploy/router.py:907` 复核为批次三 3.2 已修（现文件零裸 except）。其余 ~15 处（snmp/websocket/deploy_service 等）超出 docs 范围保留。
- [x] **P2** `maintenance/router.py:735,807` — `""` 与 `"/"` 双装饰器重复注册同一处理器。`[已复核]`
  → 修复（步骤 4E-B2）：仅保留 canonical collection 路由，回归测试确认 GET/POST 各注册一次。

### 批次六 · 切片 A · Linux 实测（2026-08-03）

验证（HEAD `b57da61` → 切片 A 后）：

| 检查点 | 结果 |
| --- | --- |
| `pytest tests/test_console_service.py -q` | ✅ **17 passed**（0.83s，不再挂起） |
| `pytest tests/test_batch1_regressions.py -q` | ✅ 15 passed |
| 全量 `pytest -q`（**不再 --ignore**） | ✅ **53 failed / 642 passed / 4 skipped / 0 errors**，失败集合与批次七基线逐条一致 |
| `ruff check app tests scripts migrations` | ✅ All checks passed |
| `frontend/npm ci` | ✅ 98 包 6s（真实安装），1196 已随网络状态解决 |
| `frontend/npm run build` | ✅ 18.54s |
| `frontend/npm run validate:locales` | ✅ 3212 zh / 3212 en，0 违规 |
| `celery_app` 导入 | ✅ routes 归一为 5 个真实模块，无悬挂 |

修复说明：
- **1194 真因**：非 console service 阻塞（批次三 3.1 已线程化），而是测试自身两处缺陷——9 处 `patch` 旧路径 `app.services.console_service`（`app/services/console_service.py` 已删）→ 4 个用例 AttributeError fast-fail；`test_send_command_success` 的 `mock_serial.in_waiting` 常量 20 使 `send_command` 的 `while in_waiting:` 读循环永不耗尽 → 死循环。修 `app.features.console.console_service` 路径 + `PropertyMock(side_effect=[20, 20, 0])`。
- **1195**：导入期写盘副作用先期已除；本切片清掉 `discovery_tasks` 悬挂 route（模块不存在）。`notification_tasks`/`scheduled_tasks` 空占位与无 `beat_schedule` 是「功能未实现」现状（定时任务未接入），非缺陷，保留。
- **1196**：`npm ci --dry-run` 3s 确认 registry 可达 → 真实 `npm ci` 98 包 6s → build + validate 全过，前端构建验证链恢复，无需 CA/镜像决策。
- **批次五遗留修复**：全量 pytest 暴出 2 个过期前端源码断言——`test_deploy_security_step4b.py::test_stream_history_uses_authenticated_username_source` 扫描 `Deploy.vue` 的 `access_token: authStore.accessToken`（946 切片 5 后迁入 `useDeployExecution.js`）；`test_device_security_step4c.py::test_photo_static_mount_...` 扫描 `Monitor3D.vue` 的 `getFloorPlanContent(currentPlan.value.id)`（946 切片 9a 后迁入 `useThreeScene.js`，变 `deps.currentPlan.value.id`）。按「源码断言随实现更新」先例（批次三 3.1）改扫描新位置，2 项通过。全量失败集合回到 53 基线（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1）。
- docs「日常校验命令」全量测试命令已去掉 `--ignore=tests/test_console_service.py`。

### 批次六 · 切片 B · Linux 实测（2026-08-03）

验证（HEAD `a7edffc` → 切片 B 后）：

| 检查点 | 结果 |
| --- | --- |
| `ruff check app tests scripts migrations` | ✅ All checks passed |
| `pytest tests/test_batch1_regressions.py -q` | ✅ 15 passed |
| 全量 `pytest -q` | ✅ **53 failed / 642 passed / 4 skipped**，失败集合与切片 A 基线逐条一致，无新增 |
| `frontend/npm run validate:locales` | ✅ 3212 zh / 3212 en，0 违规 |
| `frontend/npm run build` | ✅ 13.89s（chunk 体积告警为既有，非错误） |
| `python scripts/seed_data.py`（无 NAS_SEED_CONFIRM） | ✅ 打印拒绝说明 exit=1，发生在任何 DB 连接之前 |
| 仓库清理落点 | ✅ `frontend-react/`、`backend/`、`locales/index.js.backup` 已 git rm；`nas.db`→`nas.db.legacy-20260716`；`migrate_features.py`→`scripts/devtools/` |

修复说明：
- **1200/1201/1202**：`git rm -r frontend-react/`（17 文件）、`git rm -r backend/`（22 文件）、`git rm frontend/src/locales/index.js.backup`。连带清理两处引用：`docker-compose.yml` 的 `frontend-react:` 服务（build context 指向已删目录，不删则 `docker compose up` 会失败）、`ruff.toml` 的 `backend`/`frontend-react` 两条死 exclude。
- **1203**：`data/nas.db` → `data/nas.db.legacy-20260716`。遗留一次性迁移脚本（`scripts/legacy_sqlite/*`、`_migrate_sqlite_to_pg.py`）默认路径仍指旧名，改名后报「文件不存在」而非静默打开遗留库，符合「防默认打开」初衷，故不改其路径。
- **1204**：`seed_data.py` `main()` 顶部环境守卫置于任何 DB 连接/初始化之前（比原计划「clear_existing_data 调用前」更早），误执行零副作用；实测拒绝路径 exit=1。README 三处用法同步。
- **1205**：`git mv scripts/migrate_features.py scripts/devtools/migrate_features.py`，git 历史保留 move。

### 批次六 · 切片 C · Linux 实测（2026-08-03）

验证（HEAD `85540a6` → 切片 C 后）：

| 检查点 | 结果 |
| --- | --- |
| `ruff check app tests` | ✅ All checks passed |
| `pytest tests/test_batch1_regressions.py -q` | ✅ 15 passed |
| 全量 `pytest -q -rf` | ✅ **53 failed / 642 passed / 4 skipped**，失败集合与基线**逐条一致**（compliance 24 / tool_executor 11 / discovery 8 / spare 3 / deploy 2 / auth 2 / email 1 / device 1 / dashboard 1 = 53），零新增 |
| `frontend/npm run build` + `validate:locales` | ✅ 13.82s / 3212 zh + 3212 en |
| `napalm_service` 导入 | ✅ 死代码删除后干净导入 |

修复说明：
- **1208 裸 `except:`**：5 处 + `models.py` 全部 10 处 → `except Exception:`（裸 except 会误捕 `KeyboardInterrupt`/`SystemExit`，这是真正缺陷，非纯风格）。compliance/faults 两处加 `logger.warning`；discovery 端口探测失败属常规路径只改 `except Exception:`。`deploy/router.py:907` 复核为零裸 except（批次三 3.2 已修）。
- **1207 vendor→driver**：删除 `napalm_service.py` 三处死代码（`NapalmDeployService.driver_map`+`get_driver_name`、`NapalmStreamService.driver_map`，app 层零调用）；`registry.py` canonical 不动；`deploy_stream_service.py:272` 内联 map 是活代码且与 registry 分歧，**保留**——直换会改变 juniper/arista/h3c 三类设备行为，属需真机验证的行为性统一，延后。
- **1206 异常体系**：仅记录——`AppException` 已注册全局 handler（`app/main.py:109`），与 `HTTPException` 两套共存由框架分别处理；统一迁移风险 > 收益，留待后续。

---

## 批次七 · 既存测试失败基线（批次一执行时测得，与本次改动无关）

`pytest -q --ignore=tests/test_console_service.py` 的结果是 **54 failed / 370 passed / 4 skipped / 10 errors**。
下面 64 条失败在修复前后**逐条完全一致**，属于早于本轮审查就存在的债务，需要单独一批处理：

- [x] ~~**P1** `tests/test_tool_executor.py` 11 项失败~~ —— ✅ 2026-08-04 批次七切片 A 已修复（陈旧 `app.services.*` patch 全部失效；改用 `database._db_manager` 单例替换 + 保留 netmiko/napalm/jira 补丁）
- [ ] **P1** `tests/test_git_config.py` 11 项失败/错误 —— PermissionError，疑似 Windows 上临时 Git 仓库清理失败，需确认是否仅本地环境问题（Linux 上不存在）
- [x] ~~**P1** `tests/test_discovery_service.py` 8 项失败~~ —— ✅ 2026-08-04 批次七切片 A 已修复（patch/别名模块名 retarget 到 `app.features.discovery.*`）
- [x] ~~**P1** `tests/test_compliance_service.py` 24 项失败~~ —— ✅ 2026-08-04 批次七切片 C 已修复（按新 ADK 架构重写：`audit_config(use_ai=False)` 基础审核 + `_parse_ai_result` + `_generate_config_analysis`，不调用真实 AI/ADK）
- [x] ~~**P1** `tests/test_spare_part_service.py` 3 项、`tests/test_auth.py` 2 项、`test_device_service.py` / `test_dashboard_service.py` / `test_email_service.py` 各 1 项~~ —— ✅ 2026-08-04 批次七切片 B 已修复（断言对齐语义变更：分类中文归一化、库存实例 total_value、dashboard deployment_status/reachability 口径、MIME base64 解码；`check_permission`→`check_user_permission` 改 import）
- [x] ~~**P1** 把 `pytest` 接入提交前门禁~~ —— ✅ 2026-08-04 已完成（`.githooks/pre-commit` 仓库内脚本 + `git config core.hooksPath .githooks`；.venv 解释器跑 ruff + 全量 pytest，失败即中止提交，见下方实测）

### 批次七 · 恢复绿色基线 · 切片 A · Linux 实测（2026-08-04，HEAD 前 `32391c5`）

> 切片 A 只处理**陈旧 patch 路径**一类（21 项），全部为测试侧问题，未改任何应用代码。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest tests/test_discovery_service.py` + `test_deploy_service.py` + `test_tool_executor.py` | ✅ 22 + 14 + 14 passed |
| 全量 pytest | ✅ **32 failed / 736 passed / 4 skipped** —— 失败集合从 53 收敛到 32，剩余恰为切片 B（auth 2 / spare 3 / device 1 / email 1 / dashboard 1 = 8）+ 切片 C（compliance 24），零新增 |

**改动**：
- `test_discovery_service.py`：8 处 `patch("app.services.discovery_service.NETMIKO_AVAILABLE" / "netmiko.ConnectHandler")` 与 2 处 `import app.services.discovery_service as mod` retarget 到 `app.features.discovery.discovery_service`（顶部 import 已是新路径）。
- `test_deploy_service.py`：`app.services.deploy_service.ConnectHandler` / `.NETMIKO_AVAILABLE` 同理 retarget。
- `test_tool_executor.py`（重写）：批次三后新实现无模块级 `get_db`/`LogEntry`（改用 `get_db_manager().session_scope()`），旧的两层 patch 必然 `AttributeError`。改为沿用 `test_batch1_regressions` 模式：`monkeypatch.setattr("app.shared.database._db_manager", db_manager)` 让 `get_db_manager()` 命中测试库、`LogEntry` 真实落库；`netmiko.ConnectHandler` / `napalm.get_network_driver` / `jira.JIRA` / `app.config.settings` 补丁目标在新实现内仍有效，原样保留。`napalm`/`jira` not_installed 两个空壳用例补为真实覆盖（`patch("builtins.__import__")` 抛 ImportError）。napalm mock 链修正：执行器是 `get_network_driver("ios")` → driver 类 → `driver(**device)` → 实例，需 `mock_driver_cls.return_value = instance`；method-not-found 需真实 stub（MagicMock 的 `getattr` 会为任意属性自动生成子 mock，导致 `getattr(instance, method, None)` 永不为 None）。

**遗留**：切片 C 24 项（compliance 重写）待后续切片。

### 批次七 · 恢复绿色基线 · 切片 B · Linux 实测（2026-08-04，HEAD 前 `e9158ab`）

> 切片 B 只处理**断言对齐语义变更**一类（8 项），全部为测试侧问题，未改任何应用代码。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest test_auth` + `test_spare_part_service` + `test_device_service` + `test_email_service` + `test_dashboard_service` | ✅ 97 passed |
| 全量 pytest | ✅ **24 failed / 744 passed / 4 skipped** —— 失败集合从 32 收敛到 24，剩余恰为切片 C（compliance），零新增 |

**改动**：
- `test_auth.py`：`check_permission` → `app.shared.dependencies.check_user_permission`（签名 `(user_id, permission_name, db)` 一致，仅 import/调用更名）。
- `test_spare_part_service.py`：分类经 `normalize_category` 归一化为中文（`module`→`模块`、`cable`→`线缆`），断言改中文键；`total_value` 语义为「库存实例 in_stock 单价求和」（`spare_part_service.py:266-270`），改为构造 `SparePartInstance` 后断言 100+200=300，保留覆盖意图。
- `test_device_service.py`：`create_device`/`get_device` 返回摘要均不含 `serial_number`（仅 `update_device`/`list_devices` 含），改为直接查库断言已落库。
- `test_email_service.py`：HTML 正文经 MIME base64 编码在 multipart 中，`email.message_from_string` 解码后断言 `<h1>HTML</h1>` 在内。
- `test_dashboard_service.py`：设备统计口径改为 `deployment_status`/`reachability`（`dashboard_service.py:31-46`，total 只统计 in-use），构造改用 `deployment_status`+`reachability`，断言 `total==3`、`online==2`、`offline==1`、`devices.deployment.maintenance==1`（无顶层 `maintenance` 键）。

**遗留**：切片 C 24 项（compliance 测试重写）待后续切片。

### 批次七 · 恢复绿色基线 · 切片 C · Linux 实测（2026-08-04，HEAD 前 `eda08fc`）

> 切片 C 只处理 **compliance 测试重写**一类（24 项），全部为测试侧问题，未改任何应用代码。全量 pytest 由此恢复绿色。

| 项 | 结果 |
|---|---|
| `ruff check app tests` | ✅ 零告警 |
| `pytest tests/test_compliance_service.py` | ✅ 15 passed |
| 全量 pytest | ✅ **0 failed / 754 passed / 4 skipped** —— 失败集合从 24 收敛到 0，绿色基线恢复（无新增失败、无新增跳过） |

**改动**：批次四把 `ComplianceService` 重写为「规则库 + ADK AI」架构，删除 `run_all_checks` / `_check_*` / `service.checks`，旧测试全部调用已删除 API。按新架构的确定性部分重写（不调用真实 AI/ADK）：
- **基础审核（`use_ai=False`）**：沿用 `database._db_manager` 单例替换模式，构造 `ComplianceService()`（`__init__` 经 `init_builtin_rules()` 种子 10 条内置规则），`await audit_config(GOOD_CONFIG / BAD_CONFIG, use_ai=False)`。GOOD_CONFIG → `total_checks==10`、`passed==9`、`score==90.0`（SEC-004 `access-class` 缺失）；BAD_CONFIG → `failed==8`、`score==20.0`。**已知基础审核误判**（写注释说明）：BAD_CONFIG 的 `no ip ssh version 2` 含子串 `ip ssh version 2`、`snmp-server community public` 含 `snmp-server community` → SEC-002 / SEC-010 误判为通过；真实 AI 路径不受影响。
- **单规则断言**：从 `report.results` 按 `check_id` 逐条断言 GOOD/BAD 各 10 条规则的 `passed`/`severity`（替代原 18 个 `_check_*` 粒度用例）。
- **AI 结果解析**：直接调 `_parse_ai_result(report, 假 AI 字典, rules)` 断言 results/passed/failed/score/line_numbers 填充正确。
- **配置行分析**：调 `_generate_config_analysis` 断言 `config_analysis` 含行号与 issues。
- **edge cases**：空配置 → `passed==0`；无 shutdown 配置的 SEC-005 失败（新架构无法区分「无接口」与「接口未 shutdown」，注释说明）；`get_all_rules_for_audit()` 需先构造 service 触发种子。

**遗留**：绿色基线已恢复；下一步把 `pytest` 接入提交前门禁。

### 批次七 · 把 pytest 接入提交前门禁 · Linux 实测（2026-08-04）

> 门禁选型经用户确认：**仓库内 git hook 脚本**（自包含、无外部框架依赖、.venv 解释器）。

| 项 | 结果 |
|---|---|
| 新增 `.githooks/pre-commit` | ✅ 仓库内跟踪，`chmod +x`，`git config core.hooksPath .githooks`（仓库本地，不随克隆传播） |
| 通过路径 | ✅ ruff + 全量 pytest 通过，`exit=0`，打印「门禁通过（ruff 零告警 + 全量 pytest 绿色）」 |
| ruff 失败路径 | ✅ 临时 probe 文件触发 F821 → `exit=1`「ruff 未通过，已中止提交」 |
| 缺 .venv 路径 | ✅ 从无 `.venv` 目录运行 → `exit=1` 提示需先建虚拟环境（拒绝静默降级到系统 python3，避免环境类假失败） |
| 绕过 | git 内置 `--no-verify`（一次性显式逃逸） |

**设计要点**：
- 强制 `.venv/bin/python`：系统 python3 无 ruff/pytest 依赖，退回只会产生环境类假失败（批次一已踩过 4 个 F821 全被吞的坑），门禁直接失败并提示而非降级。
- ruff 覆盖 `app scripts migrations tests`（与 `ruff.toml` 用法注释一致）。
- 全量 pytest 每个提交约 37s，作为回归门禁可接受；文档改动同样触发，保证任何变更都不能绕过回归验证。
- 恢复绿色基线（0 failed）是该门禁能落地的前提——在 53 失败基线接入只会让每次提交都失败。

### 批次八 · 切片 A · router 层首测 · Linux 实测（2026-08-04）

> 目标：给 router、streaming service、celery task 三条零覆盖链路补第一批真实测试，建立可复用模式。**只改测试 + conftest，不动应用代码**。

| 项 | 结果 |
|---|---|
| conftest `router_client_factory` | ✅ 新增 fixture：mini FastAPI + TestClient，override `get_current_user_from_token` / `get_current_principal` / `get_db`，默认 transient superuser（`config.app.debug` 默认 False，非 superuser 会让 `require_permission` 拒绝） |
| `tests/test_router_devices.py`（11 项） | ✅ CRUD + 列表过滤（status/role）+ 404/422 + 批次一 bug 现场回归：POST `/monitor/discover-neighbors-all`（patch `snmp_discovery.discover_neighbors` + `database._db_manager`，断言聚合 `total_aps_synced`） |
| `tests/test_router_spare_parts.py`（10 项） | ✅ 零外部依赖，CRUD + stats + 手动出入库 + 分类中文归一化，最快证明 mini-app 模式 |
| `tests/test_router_compliance.py`（5 项） | ✅ `/rules` 内置规则列表（`init_builtin_rules` 播种）、`/check` `use_ai=False` 基础审核（双 patch：`database._db_manager` + `_compliance_service=None` 强制重建单例播种）、空配置 400 |
| 全量回归 | ✅ `pytest -q`：**780 passed / 4 skipped / 0 failed**（基线 754 → +26） |
| ruff | ✅ 新/改文件零告警（门禁自动跑） |

**关键模式**（后续 slices B/C 复用）：服务内部 `next(get_db())` 经 `database._db_manager` 全局 → `monkeypatch.setattr(database, "_db_manager", db_manager)` 路由到测试库；SQLite 用 StaticPool，所有 session 共享同一内存库，`db_session` 与 service 内建 session 可见同一数据。

### 批次八 · 切片 B · streaming 层首测 · Linux 实测（2026-08-04）

| 项 | 结果 |
|---|---|
| `tests/test_deploy_stream_service.py`（3 项） | ✅ `asyncio.run(service.stream_batch_deploy(...))` 直测：fake websocket 收集 send_json 消息；`_deploy_single_device_netmiko` 实例属性覆盖作 seam（`:497` 经 `loop.run_in_executor` 调用）。断言消息序列 `deploy_started→device_started→device_progress→deploy_complete`、DeployHistory/DeployDeviceResult/Device.config_changed_at 落库、dry_run 透传、设备抛异常 → `success False` + `执行异常` |
| `tests/test_deploy_ws_endpoint.py`（1 项） | ✅ `/ws/deploy/{session_id}` 错误路径：发缺 `target_devices` 畸形请求 → `ValidationError` 分支先发 `deploy_error` 再发 `deploy_complete(success=False)`，零 DB/auth 依赖 |
| 成功路径 WS | 不做（需 `authorize_deploy_token` + 凭证解密，成本高）；业务流由 stream 直测覆盖 |
| 全量回归 | ✅ `pytest -q`：**784 passed / 4 skipped / 0 failed**（780 → +4） |
| ruff | ✅ 新文件零告警（门禁自动跑） |

### 批次八 · 切片 C · celery 层首测 · Linux 实测（2026-08-04）

| 项 | 结果 |
|---|---|
| `tests/test_celery_ai_tasks.py`（4 项） | ✅ 无 broker 直调 `@celery_app.task` 装饰函数：patch `app.services.rag.rag_engine` 模块属性 + `sys.modules['litellm']` stub + `database._db_manager`。`index_device_config_task` 成功/不可用两路径；`analyze_fault_task` 按当前行为断言（见下） |
| `index_device_config_task` | ✅ 成功路径 AIKnowledgeDocument 落库 + 返回 dict；RAG 不可用 → `{"success": False, "error": "RAG not available"}` |
| `analyze_fault_task` | ⚠️ 按当前行为断言：**每次运行必失败**（见下方新 P1 项）；litellm 异常 → 返回 `success False` |
| 全量回归 | ✅ `pytest -q`：**788 passed / 4 skipped / 0 failed**（784 → +4） |
| ruff | ✅ 新文件零告警（门禁自动跑） |

**新发现 P1（批次八切片 C 实测暴露）**：`app/tasks/ai_tasks.py:93 analyze_fault_task` 写 `AIAnalysisRecord` 时传入 `prompt` / `response` / `input_tokens` / `output_tokens` / `success`，但 `models.py:1400 AIAnalysisRecord` 实际列是 `input_data` / `output_result` / `tokens_used` / `status` —— 五个参数全部不匹配，构造时即 `TypeError: 'prompt' is an invalid keyword argument`，被函数内 `except Exception` 吞掉 → **恒返回 `success=False`，AI 故障分析结果永不落库**。且该任务为死代码：app 内无 `.delay()`/`.apply_async()` 调用（活跃的 `POST /faults/{id}/analyze` 走 ADK agent，`faults/router.py:605`）。修复需先定 schema 口径（改任务对齐模型列，或改模型对齐任务），且属「功能未实现」任务接入点问题，超出本批次「只改测试」范围，**已排入批次九**（2026-08-04）。`[已修复]`（批次九 ✅ 2026-08-04）：按方案 A 改任务对齐 canonical 模型列（依据：活跃的 `app/services/adk/audit.py:35` 正是用 `input_data`/`output_result`/`tokens_used`/`status` 且不传 id 自增）——去掉 `id=str(uuid)`、`prompt`→`input_data`(JSON)、`response`→`output_result`、`input/output_tokens`→`tokens_used`(求和)、`success`→`status="completed"`。批次八切片 C 的 `test_record_write_fails_on_schema_mismatch` 已翻转为 `test_success_records_analysis`（成功落库断言）。任务经核实为死代码（app 内无 `.delay()`/`.apply_async()` 调用）且与活跃 ADK 链路冗余（ADK 已落 `analysis_type='fault'` 记录，死任务写 `'fault_analysis'` 不会被 `GET /api/ai/faults/{id}/analysis` 读取）——2026-08-04 按用户决定直接删除，见下方「批次九 · 遗留清理」。

### 批次九 · 修复 analyze_fault_task P1 · Linux 实测（2026-08-04）

> schema 口径决策：改任务对齐模型（方案 A），不动 schema、无 alembic 迁移。依据：`AIAnalysisRecord` 的唯一活跃写入方 `app/services/adk/audit.py:35` 即用 `input_data`/`output_result`/`tokens_used`/`status` 且不传 id 走自增——模型列是 canonical，死任务假设是孤例。

| 项 | 结果 |
|---|---|
| `app/tasks/ai_tasks.py:93 analyze_fault_task` | ✅ 去掉 `id=str(uuid)`（改自增，顺带清未用 `import uuid`）、`prompt`→`input_data`(JSON)、`response`→`output_result`(截 5000)、`input/output_tokens`→`tokens_used`(求和)、`success`→`status="completed"`；模块级补 `import json` |
| `tests/test_celery_ai_tasks.py` | ✅ `test_record_write_fails_on_schema_mismatch` 翻转为 `test_success_records_analysis`：`record_id` 为 int、落库 `status=completed` / `output_result` / `tokens_used=30` / `target_id`；litellm 异常路径测试保留不变 |
| 全量回归 | ✅ `pytest -q`：**788 passed / 4 skipped / 0 failed**（测试数不变，翻转断言） |
| ruff | ✅ 修改文件零告警（门禁自动跑） |

**遗留处理（2026-08-04）**：① `analyze_fault_task` —— 经核实为死代码（app 内无 `.delay()`/`.apply_async()` 调用），且与活跃 ADK 链路冗余（`POST /faults/{id}/analyze` → `adk_runner.run_agent` → `ai_audit.record(analysis_type='fault')` 已把分析落 `AIAnalysisRecord`，`GET /api/ai/faults/{id}/analysis` 按 `analysis_type == 'fault'` 读取；死任务写 `'fault_analysis'` 不会出现）→ 接回无意义，**按用户决定删除**（见下方实测）；② `models.py:1442` 不可达残句 —— 已删（`get_output_dict` 的 `return {}` 后一行 `self.success` `__repr__` 碎片，永不执行）。

### 批次九 · 遗留清理 · Linux 实测（2026-08-04）

| 项 | 结果 |
|---|---|
| `app/tasks/ai_tasks.py` | ✅ 删除死任务 `analyze_fault_task`（`@celery_app.task name="app.tasks.ai_tasks.analyze_fault"`）+ 其专属辅助 `format_knowledge`；清未用 `import json`；模块 docstring 移除「AI 分析任务」项；`index_device_config_task`（RAG 索引）保留 |
| `tests/test_celery_ai_tasks.py` | ✅ 删除 `TestAnalyzeFaultTask` 两个用例 + 未用 helper（`_make_litellm_response`/`_inject_litellm`）与导入（`sys`/`SimpleNamespace`/`mock`）；docstring 改写；仅留 `index_device_config_task` 两用例 |
| 删除依据 | 死代码：app 内无 `.delay()`/`.apply_async()` 调用；与活跃 ADK 链路冗余（`faults/router.py:605` → `adk_runner.run_agent` → `ai_audit.record` 已落库，死任务写 `'fault_analysis'` 不会被 `GET /api/ai/faults/{id}/analysis` 读取）；批次九修复的列对齐方案 A 随删除作废（模型列仍是 canonical，依据活跃 audit.py） |
| celery route 配置 | ✅ `app/core/celery_app.py:45` 通配路由 `"app.tasks.ai_tasks.*": {"queue": "ai_tasks"}` 对剩余 `index_device_config` 仍命中，无需改动 |
| `models.py:1442` 残句 | ✅ 已删：`get_output_dict` 的 `return {}` 后一行不可达 `self.success` `__repr__` 碎片（永不执行）；合法 `__repr__` 保留 |
| 全量回归 | ✅ `pytest -q`：**786 passed / 4 skipped / 0 failed**（788 → -2，随删除的 2 个 analyze 用例） |
| ruff | ✅ 修改文件零告警（门禁自动跑） |

### 批次十 · 数据层 P2 遗留 · Linux 实测（2026-08-04）

收尾批次三 3.3 两项 P2（伪外键 + 保留策略），只动数据层，不动页面逻辑。

| 项 | 结果 |
|---|---|
| 伪外键 6 处 | ✅ `fault_records.peer_device_id`、`device_interfaces.peer_device_id`、`ai_knowledge_documents.device_id`、`jobs.device_id` → `ForeignKey("devices.id", ondelete="SET NULL")`（可空/审计引用，删设备保留父行）；`interface_traffic_samples.device_id`、`deploy_device_results.device_id` → `ondelete="CASCADE"`（冗余副本 / NOT NULL 子行） |
| 关系消歧 | ✅ `fault_records`、`device_interfaces` 因新增第二个 devices FK，既有 `Device.faults` / `DeviceInterface.device` 关系报 `AmbiguousForeignKeysError` → 加 `foreign_keys=[device_id]`（仅 ORM，无 schema 影响）；其余 4 表无 Device 关系不需处理 |
| 迁移 | ✅ 新增幂等迁移 `f0a1b2c3d4e5_add_device_fks.py`（down=`5e6a7b8c9d0e`）：`_existing_fk` 探测约束，ondelete 一致跳过、不符则 drop 重建；建约束前清孤儿（SET NULL → 置 NULL 保留行，CASCADE → 删行）；约束名 `{table}_{col}_fkey` 匹配 PG autogen 命名，`alembic check` 零漂移 |
| `EXPECTED_ALEMBIC_HEAD` | ✅ `database.py:145` 由过期 `'5d16fa030a9a'` 修正为 `'f0a1b2c3d4e5'`（真实链头原为 `5e6a7b8c9d0e`，既存不一致顺带修复） |
| FK 测试 | ✅ 新增 `tests/test_fk_integrity.py`（SQLite `foreign_keys=ON` 真实生效）：孤儿 `interface_traffic_samples.device_id` 写入拒绝（`IntegrityError`）；SET NULL 两例（删对端设备 fault 保留置 NULL、删设备 RAG 文档保留置 NULL）；CASCADE 一例（删设备 deploy 结果行消失）。`test_celery_ai_tasks.py::test_success_indexes_document` 补 seed Device 以符合新 FK |
| 保留策略 | ✅ 机制已存在（`metric_retention.py` + `cleanup_old_metric_samples` + APScheduler 每日任务，默认 90 天，`test_metric_retention.py` 全绿）；批次十 config 化：新增 `MetricsConfig`（`retention_days`/`cleanup_interval_seconds`/`cleanup_batch_size`）挂 `Config.metrics`，config.yaml `metrics:` 块 + env（`DEVICE_METRIC_RETENTION_DAYS`/`DEVICE_METRIC_CLEANUP_INTERVAL`/`DEVICE_METRIC_CLEANUP_BATCH_SIZE`，保留既有变量名）经 `_apply_security_env_overrides` 覆盖 |
| Connector 取参 | ✅ `prometheus_connector.__init__` 三保留参数默认 `None` → 落 `get_config().metrics`（try/except 兜底 90/86400/5000）；新增 `metric_cleanup_interval` 实例属性，`start()` 改用 `self._metric_cleanup_interval`；删除随之无用的模块常量 `METRIC_RETENTION_DAYS`/`METRIC_CLEANUP_INTERVAL`/`METRIC_CLEANUP_BATCH_SIZE`（`PROMETHEUS_URL`/`POLL_INTERVAL`/`METRIC_SAMPLE_INTERVAL` 保留） |
| 保留配置测试 | ✅ 新增 `tests/test_retention_config.py`（6 项）：默认值 / YAML 块生效 / env 覆盖优先 / 非法 env 报错 / Connector 未传参读 config / 显式传参优先 |
| 遗留记录 | ⏸ PG 分区列遗留不动（单表分区为独立工作项）；`fault_records.if_index` 复合键引用判误报不建简单 FK；`jobs.change_request_id` 无 `change_requests` 表记观察 |
| 全量回归 | ✅ `pytest -q`：**796 passed / 4 skipped / 0 failed**（786 → +10：FK 4 项 + 保留配置 6 项） |
| ruff | ✅ 修改文件零告警（门禁自动跑） |

### 批次十一 · 异常泄漏修复（item 134）· Linux 实测（2026-08-04）

收尾批次二安全遗留 item 134：catch-all 处理器不再向客户端回显内部异常文本。

| 项 | 结果 |
|---|---|
| 范围 | ✅ 5 个 router 12 处 `except Exception as e: raise HTTPException(detail=str(e) / detail=f"...{e}")`：compliance（创建/更新 AI 配置）、discovery（Ping Sweep/综合发现）、deploy（预览/部署/回滚/历史列表/历史详情/删除历史 ×6）、permissions（权限系统初始化）、devices（Excel 导入） |
| 处理方式 | ✅ 全部改「面向用户的中文通用文案（…请查看服务端日志 / 检查 Excel 格式）+ 服务端 `logger.error` 落原始异常」；deploy 保留既有 traceback 日志，devices 导入保留 400 状态码 |
| 保留的安全回显 | ✅ 区分「领域异常 / ValueError 校验」仍回显设计好的用户文案（ConflictException、UnsafeBackupPathError、NetworkTemplateRenderError、FaultMaintenanceConflictError、DevicePhotoValidationError、UnsafeLogPathError、UnsafeBackupRecordPathError、compliance LLM 连接测试、devices 逐行导入错误、SNMP 诊断探针、jobs 吞异常）；全局 `generic_exception_handler`（`exceptions.py:119`）本就返回固定 `Internal server error` 不回显，绕过的正是这批本地 catch-all |
| 回归测试 | ✅ 新增 `tests/test_no_leak_detail.py`（7 项）：对 5 个 router 各取一条最易触发的 catch-all 路径，monkeypatch 内部函数抛 `RuntimeError("LEAK-MARKER-...")`，断言响应 detail 为通用文案且不含 marker（防回显回归） |
| 全量回归 | ✅ `pytest -q`：**803 passed / 4 skipped / 0 failed**（796 → +7：泄漏回归 7 项） |
| ruff | ✅ 修改文件零告警（门禁自动跑） |

## 建议执行顺序

1. ~~**批次一**（硬故障）+ **批次六第 1 项**（接 ruff）~~ —— ✅ 2026-07-29 完成
2. **批次二**（安全）—— 需先确认 `auth_enabled` 的目标状态，再决定是收紧默认值还是重新定位 RBAC。**进行中**：步骤 3（统一身份）✅、步骤 4（写接口权限，含长尾 slice A）✅ 2026-08-03、加密密钥独立 + AI key 加密（slice B，items 125/115）✅ 2026-08-03、trap fail-closed + 前端守卫（slice C，items 130/133）✅ 2026-08-03、步骤 5 会话级 SSH 凭证 + 备份提醒 + 二次确认（✅ 2026-08-03：切片 A 备份会话凭证 + 需备份列表，切片 B 部署/回滚凭证 + 二次确认 + 下线异步；✅ 2026-08-04 步骤 5 收尾：legacy `/ws/cli` 无认证部署路径整块下线）、item 134（error leakage）✅ 2026-08-04 批次十一修复、**步骤 6 OIDC 真接仍 pending（⬜ 等 IT）**
3. ~~**批次三 3.2**（DB 会话统一）+ **3.1**（设备操作执行器）~~ —— ✅ 2026-08-02 完成（统一执行器 `app/shared/device_ops.py`，详见批次三 3.1/3.2 打勾项与下方实测）
4. ~~**批次三 3.3**（schema 基线）~~ —— ✅ 2026-08-02 完成（alembic 成为唯一 schema 权威源：基线 `ed628a533673` + 修复迁移 `5d16fa030a9a`，PG 启动 create_all 移除改 head 校验 fail-fast，详见 3.3 打勾项与下方实测）
5. **批次四**（数据正确性）—— 页面数字可信之后再谈优化
6. **批次五**（前端）—— 先收请求层默认行为，再补卸载清理，最后拆巨型组件与重建 i18n 表
7. **批次三 3.4/3.5** 与 **批次六剩余项** —— 批次六切片 A（console 挂起 / celery route / npm ci）✅ 2026-08-03、切片 B（仓库清理 6 项）✅ 2026-08-03、切片 C（异常体系记录 / vendor→driver 死码删 / 裸 except）✅ 2026-08-03 全部完成；批次六收官。批次三 3.4（缓存 5 项）切片一 ✅ 2026-08-03（见上方 3.4 实测）、3.5（启动与关闭 4 项：shutdown 事件 / prometheus 轮询 / 中间件顺序+按用户限流 / trap join）切片二 ✅ 2026-08-03（见上方 3.5 实测），批次三 3.4/3.5 全部完成
8. ~~**批次七**（恢复绿色基线 + 提交前门禁）~~ —— ✅ 2026-08-04 全部完成：53 项既存失败全部为测试侧问题（陈旧 patch 路径 / 未跟上批次二~四语义变更），未改应用代码。切片 A（陈旧路径 retarget 21 项）、切片 B（断言对齐 8 项）、切片 C（compliance 重写 24 项）均 ✅ 2026-08-04（见上方批次七实测）；**全量 pytest 恢复绿色（0 failed / 754 passed / 4 skipped）**；随后经用户确认选型，`.githooks/pre-commit` + `core.hooksPath` 把 ruff + 全量 pytest 接入提交前门禁 ✅（见上方实测）
9. ~~**批次八**（补测试覆盖偏斜：router / streaming / celery 三层首测）~~ —— ✅ 2026-08-04 全部完成：切片 A router 层（26 项，`router_client_factory` mini-app 模式）、切片 B streaming 层（4 项，stream 直测 + WS 错误路径）、切片 C celery 层（4 项，无 broker 直调 + litellm stub）均 ✅ 2026-08-04（见上方批次八实测）；**全量 pytest 788 passed / 4 skipped / 0 failed**。三层零覆盖链路已全部建立第一批真实测试，模式可复用。
10. ~~**批次九**（修复 `analyze_fault_task` P1，用户已排期 2026-08-04）~~ —— ✅ 2026-08-04 完成：按方案 A 改任务对齐 canonical 模型列（依据：活跃的 `app/services/adk/audit.py:35` 即用 `input_data`/`output_result`/`tokens_used`/`status` 且不传 id 自增，模型列是权威）。修复 `ai_tasks.py:93` 写 `AIAnalysisRecord` 列名不匹配恒失败；同步翻转 `test_celery_ai_tasks.py` 测试为成功落库断言。**全量 pytest 788 passed / 4 skipped / 0 failed**（见上方批次九实测）。**遗留已清**（2026-08-04）：`analyze_fault_task` 核实为死代码且与活跃 ADK 链路冗余 → 按用户决定整体删除（任务 + `format_knowledge`）；`models.py` 不可达 `self.success` 残句已删。全量 pytest **786 passed / 4 skipped / 0 failed**（见上方「批次九 · 遗留清理」实测）
11. ~~**批次十**（数据层 P2 遗留：批次三 3.3 两项 P2 收尾）~~ —— ✅ 2026-08-04 完成：**① 裸 Integer 伪外键 → 真 FK**（6 处，SET NULL ×4 / CASCADE ×2，幂等迁移 `f0a1b2c3d4e5` + 清孤儿 + 关系 `foreign_keys` 消歧 + `EXPECTED_ALEMBIC_HEAD` 修正）；**② 保留策略 config 化**（机制已存在，`Config.metrics` + config.yaml + env 下发，Connector 改读 config）。全量 pytest **796 passed / 4 skipped / 0 failed**（见上方「批次十」实测）；PG 分区列遗留记录在案
12. **批次十一**（item 134：catch-all 异常泄漏修复）—— ✅ 2026-08-04 完成：5 个 router 12 处 `detail=str(e)` 统一改中文通用文案 + 服务端 `logger.error`，`test_no_leak_detail.py` 7 项回归守卫。全量 pytest **803 passed / 4 skipped / 0 failed**（见上方「批次十一」实测）

## 遗留与待办（截至 2026-08-04，批次十一后）

批次一至十一已收尾全部**代码级**条目（item 1–134），全量 pytest **803 passed / 4 skipped**。
以下剩余工作全部受**外部资源**阻塞，按阻塞源分类记录，方便日后接续处理。

### 一、等 IT（OIDC 真接）

- [ ] **OIDC 真接**（批次二 step 6）—— 需 IT 填 tenant/client/secret + 服务器出站白名单。`SSOConfig`（`app/shared/config.py`，默认关闭）与 SSO 端点已预留，`test_sso_placeholder.py` 7 项为占位断言。落地后：真实 Entra 跳转/回调 + 占位测试替换为真接断言。无前置代码项。

### 二、需浏览器 + npm 构建环境（前端 QA 清单）

> 本机 `npm ci && npm run build` 装不上依赖，以下均为静态阅读后待实机验证项。

- [ ] 浏览器 Deploy 页 preview/历史/预约/回滚权限表现正确，WS 断线与 401/403 提示可理解
- [ ] 浏览器照片上传/预览/删除、接口流量图、批量邻居发现和 3D 底图均携带 Bearer 且可用
- [ ] 浏览器 Logs 页列表、搜索、文件查看、清理按钮权限与 401/403 提示正常
- [ ] 浏览器 Backups 页列表/查看/diff/认证下载/批量执行可用，菜单与按钮权限表现正确
- [ ] 浏览器 Faults/FaultDetail/Monitor3D 创建、复核、日志、转维修可用，故障角标携带 Bearer；执行 `npm ci && npm run build`
- [ ] 浏览器 Maintenance/FaultDetail 创建、编辑、指派、日志、状态流转与验证可用；执行 `npm ci && npm run build`
- [ ] 浏览器 legacy 与 AOP 新建/编辑/批量窗口/排程/任务完成可用；执行 `npm ci && npm run build`
- [ ] 浏览器 Workflows 列表/创建/编辑/启停/删除/默认规则/四类测试触发可用；执行 `npm ci && npm run build`
- [ ] 浏览器 Users 列表、创建、编辑、角色分配、密码重置、停用和删除可用；执行 `npm ci && npm run build`
- [ ] 浏览器 SystemSettings 配置与 SLO CRUD 均携带 Bearer、一次保存无半写；执行 `npm ci && npm run build`
- [ ] 浏览器验证 PartsTable、ScanInput、FaultDetail、MaintenanceDetail、PlannedMaintenance、TaskDetail、ScrapInventory 全流程并执行 `npm ci && npm run build`
- [ ] 本地账号登录后刷新登录态保持；登出后回登录页且旧 token 不可用
- [ ] Network 面板确认请求只有 `Authorization: Bearer ...`，不再发送 `X-User`；全局搜索能返回设备/模板/备份
- [ ] 普通账号不能通过修改 `localStorage.isLoggedIn` 获得受保护 API 数据
- [ ] 在企业 CA/内网 npm 镜像可用的环境执行 `npm ci && npm run build`，构建必须成功

### 三、需 docker + HTTPS 反向代理环境（部署验证）

- [ ] `docker compose config` 成功，backend 生效值 `AUTH_ENABLED=true`、`APP_DEBUG=false`
- [ ] `docker compose up` 后 `/health` 与 `/ready` 正常；缺失/弱 `JWT_SECRET` 时 backend 必须拒绝启动
- [ ] 合法 Origin 的 OPTIONS 预检成功；非法 Origin 不返回允许跨域头
- [ ] HTTPS 反向代理下登录、Bearer 转发、401/403 响应和 `WWW-Authenticate` 头不被 Nginx 改写

### 四、需真实账号 / 实验设备（集成验证）

- [ ] 调用 `/api/auth/logout` 后复用旧 token：返回 401（验证撤销会话）—— 未测，服务端会话撤销逻辑待确认
- [ ] 停用账号现有 token：返回 403；不能继续访问业务 API —— 未测，需要停用账号操作
- [ ] 建立用户 A/B 各自通知，A 只能读取、标记、删除 A 的通知，不能操作 B 的通知
- [ ] 使用实验设备执行一次 dry-run 部署，部署历史/审计 operator 必须等于 token 用户名
- [ ] 多并发请求使用不同 token 时身份不得串线，日志中不得出现 token、密码或 JWT secret

### 五、记录在案的观察 / 可选升级（无当前代码动作）

- PG 分区列（batch 10 记为独立工作项：`interface_traffic_samples` / `device_metric_samples` 单表分区）
- passlib 与新版 bcrypt 兼容警告（`bcrypt` 移除 `__about__`）升级，功能正常
- `jobs.change_request_id` 无 `change_requests` 表（观察，无修复）
- `fault_records.if_index` 为复合键引用（device_id+if_index → device_interfaces），判误报不建简单 FK
- `tests/test_git_config.py` 11 项 Windows PermissionError（Linux 上不存在，无需处理）

### 六、可选 ops（需真实 PostgreSQL）

- batch 10 FK 迁移在真实 PG 落地验证：`alembic upgrade head` + `alembic check` 零漂移（同 batch 3.3 方式，不进门禁）

## 附注

- 未做的验证：前端 `vite build` 未跑过（npm 装不上依赖），所有前端结论均为静态阅读；`[待验证]` 项建议实机复现后再改。
- 本清单未包含纯风格问题（命名、注释、格式），只保留会影响正确性、安全、性能或可维护性的条目。

## 日常校验命令

```powershell
# 静态门禁（必须零告警）
.\.venv\Scripts\python.exe -m ruff check app scripts migrations tests

# 批次一回归用例
.\.venv\Scripts\python.exe -m pytest tests/test_batch1_regressions.py -q

# 全量测试
.\.venv\Scripts\python.exe -m pytest -q
```
