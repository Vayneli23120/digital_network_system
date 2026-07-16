# Test Results — 2026-07-15

**Overall: 291 passed, 60 failed** (2 test files skipped: console_service, redis_cache due to infrastructure dependencies)

## Failed Test Breakdown

### 1. Compliance Service (24 failed) — test-code mismatch
`ComplianceService` 已被重构，测试仍引用旧方法名 (`run_all_checks`, `_check_enable_secret` 等)。测试代码与服务代码不一致，需要同步更新。

### 2. Tool Executor (9 failed) — dependency not installed
netmiko / napalm / jira 库未安装，mock 未能正确覆盖。

### 3. Discovery Service (6 failed) — dependency not installed
netmiko 库未安装。

### 4. Git Config Service (5 failed) — git config issue
本地 git user.name/user.email 未配置导致部分提交相关测试失败。

### 5. Deploy Service (2 failed) — dependency not installed
netmiko 未安装。

### 6. Device Service (1 failed) — test assertion
`test_create_device_all_fields` — 断言字段值不匹配。

### 7. Vendor Adapter (2 failed) — netmiko not installed

### 8. Spare Part Service (3 failed) — Chinese vs English
备件分类返回中文 "模块" 而非 "module"。

### 9. Auth Service (2 failed) — function moved
`check_permission` 已从 `permissions.router` 移除。

### 10. Email Service (1 failed) — HTML encoding
Base64 编码导致 HTML body 断言失败。

### 11. Others (5 failed) — various

---

## PostgreSQL 并发测试结果（补充验证）

**执行日期**: 2026-07-15  
**测试机**: 192.168.4.37（k8s-worker）  
**测试文档**: `docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md`

### 步骤 8：本地逻辑回归（SQLite）

| 测试文件 | 结果 |
|---|---|
| `test_spare_part_service.py::TestCreateMovement` | 通过 |
| `test_fault_transfer_idempotency.py` (4 tests) | 通过 |
| `test_workflow_maintenance_idempotency.py` (1 test) | 通过 |

**13 passed** ✓

### 步骤 9：PostgreSQL 双连接并发测试

| 测试用例 | 结果 |
|---|---|
| `test_concurrent_outbound_movement_never_creates_negative_stock` | 通过 |
| `test_concurrent_fault_maintenance_creation_reuses_one_record` | 通过 |

**2 passed** ✓

### 步骤 10：临时数据清理检查

| 表 | 剩余记录 |
|---|---|
| `devices` (STEP0-PG-%) | 0 |
| `fault_records` (STEP0-PG-%) | 0 |
| `maintenance_records` (STEP0-PG-%) | 0 |
| `spare_parts` (STEP0-PG-%) | 0 |

**全部清理完成** ✓

### 步骤 12：部署冒烟检查

- `nas-backend` 状态: `active (running)` ✓
- `/health` 端点: 返回成功 ✓
- 日志: 无数据库连接失败或事务异常 ✓

**结论**: 事务隔离防护（Step 0）在真实 PostgreSQL 上验证通过，库存不会为负，并发维修单创建只保留一条记录。

---

## Step 1：设备指标事实层远程验证（补充验证）

**执行日期**: 2026-07-16
**测试机**: 192.168.4.37（k8s-worker）
**测试文档**: `docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md` §14
**Git 提交**: `3e282df`
**Alembic 版本**: `b8c9d0e1f2a3`

### 14.3 聚焦回归

| 测试文件 | 结果 |
|---|---|
| `test_device_metric_facts.py` (4 tests) | 通过 |

**4 passed** ✓
前端 Vite 构建成功 ✓

### 14.5 Alembic 迁移

`c30eb4f78004` → `b8c9d0e1f2a3`（add canonical device metric fact table）

### 14.6 PostgreSQL 表结构

- 主键 `device_metric_samples_pkey` ✓
- 外键 `device_id → devices.id ON DELETE CASCADE` ✓
- 索引 `idx_device_metric_device_ts` ✓
- 字段 `cpu_percent`, `memory_percent`, `temperature_c`, `collection_status` ✓

### 14.7 真实 SNMP 样本

| 项目 | 值 |
|---|---|
| 设备 | pnetlab-swr (192.168.4.1) |
| snmp_available | True |
| CPU | 37.0% (normal) |
| 样本计数 | 0 → 1 |

### 14.8 历史查询

- 返回 1 条记录，按时间升序 ✓
- source: `snmp_live` ✓
- collection_status: `partial`（SNMP 不支持 temperature 等字段）
- 附加字段: uptime_days=19, interfaces_up=17, interfaces_down=102, total_errors=0

### 14.9 后端重启

- `nas-backend` 状态: `active (running)` ✓
- `/health`: `{"status":"healthy","version":"2.0.0"}` ✓
- 日志: 无 `device_metric_samples` 异常或迁移错误 ✓

**结论**: Step 1 设备指标事实层在真实 PostgreSQL + SNMP 设备上验证通过，事实表写入和历史查询均正常，不影响原实时指标接口。

---

## Step 1.1：Prometheus 周期事实采集远程验证（补充验证）

**执行日期**: 2026-07-16
**测试机**: 192.168.4.37（k8s-worker）
**测试文档**: `docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md` §15
**Git 提交**: `9af3cfc`
**Alembic 版本**: `b8c9d0e1f2a3`（无变化）

### 15.3 聚焦回归

| 测试文件 | 结果 |
|---|---|
| `test_device_metric_facts.py` (4 tests) | 通过 |
| `test_prometheus_metric_facts.py` (4 tests) | 通过 |
| 其中 `test_metric_fact_failure_preserves_interface_updates` | 通过 |

**8 passed** ✓

### 15.4 Prometheus 批量指标

| 指标 | Series 数 |
|---|---|
| `sysUpTime` | 6 |
| `ifOperStatus` | 165 |
| `ifInErrors` | 161 |
| `ifOutErrors` | 161 |

### 15.5 轮询基线 → 触发后对比

| 项目 | 轮询前 | 轮询后 |
|---|---|---|
| `prometheus_snmp` 样本数 | 0 | 6 |
| `device_interfaces.last_check` | 02:01:12 | 02:03:33 |

样本数自动增加 ✓，last_check 更新 ✓

### 15.6 周期事实内容示例

| 字段 | 示例值 |
|---|---|
| source | `prometheus_snmp` |
| collection_status | `partial` |
| uptime_days | 0 |
| interfaces_up + down ≤ total | 17+102=119 ≤ 119 ✓ |
| total_errors | 0 |

CPU/温度保持 NULL（对应厂商 OID 不支持）— 预期行为 ✓

### 15.7 版本、服务、日志

- Alembic 版本：`b8c9d0e1f2a3` ✓
- `nas-backend` 状态：`active (running)` ✓
- `/health`：`{"status":"healthy","version":"2.0.0"}` ✓
- 日志：今日无 `error`/`failed`/`poll` 相关异常 ✓

**结论**: Step 1.1 Prometheus 周期事实采集在真实 PostgreSQL + snmp_exporter 上验证通过，后端启动后自动写入 6 条 `prometheus_snmp` 事实，`device_interfaces.last_check` 同步更新，无任何错误。

---

## Step 1.2：Prometheus uptime 双格式兼容验证（补充验证）

**执行日期**: 2026-07-16
**测试机**: 192.168.4.37（k8s-worker）
**测试文档**: `docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md` §16
**Git 提交**: `36a4c60`
**Alembic 版本**: `b8c9d0e1f2a3`（无变化）

### 发现并修复的 Bug

根因：snmp_exporter 将 `sysUpTime` 放在 metric label 时是 SNMP 原始厘秒值（hundredths of a second），而标准 Prometheus 格式的样本值已经是秒。上游代码仅从 label 取值后直接 `// 86400`，导致 `uptime_days` 膨胀 100 倍（如 19 天 → 1962 天）。

修复：`_prometheus_metric_raw_value()` 改为返回 `(value, from_label)` 二元组，`_fetch_device_uptimes()` 对 label 来源的值先 `/ 100` 再换算天数。

### 16.3 原始 Prometheus uptime 格式

| 实例 | 来源位置 | 原始值 | 正确天数 |
|---|---|---|---|
| 10.121.2.2 | **label** | 500214737 厘秒 | 57 |
| 10.121.2.3 | **label** | 490453026 厘秒 | 56 |
| 10.121.1.1 | **label** | 508073863 厘秒 | 58 |
| 10.121.2.254 | **label** | 488300953 厘秒 | 56 |
| 192.168.4.1 | **label** | 169565060 厘秒 | 19 |
| 10.121.2.1 | **label** | 488086217 厘秒 | 56 |

所有设备 `sysUpTime` 值均位于 **label** 位（snmp_exporter 格式），sample 值始终为 `1`。

### 16.4 周期事实与 Prometheus 原始值对照

6/6 台设备 `fact_days == expected_days`，全部一致 ✓

### 16.5 周期与实时 SNMP uptime 对照

| 设备 | 周期事实 | 实时 SNMP | 差值 |
|---|---|---|---|
| pnetlab-swr (192.168.4.1) | 19 天 | 19 天 | 0 天 ✓ |

### 16.6 版本、服务、日志

- Alembic 版本：`b8c9d0e1f2a3` ✓
- `nas-backend` 状态：`active (running)` ✓
- `/health`：`{"status":"healthy","version":"2.0.0"}` ✓
- Prometheus 连接器日志：正常 ✅

**结论**: Step 1.2 验证通过。修复后周期事实 `uptime_days` 与 Prometheus 原始值完全一致，与实时 SNMP 差值 0 天。代码已提交 (`36a4c60`)，聚焦测试 8/8 通过。

---

## Step 1.3：Prometheus 周期 CPU 事实验证（补充验证）

**执行日期**: 2026-07-16
**测试机**: 192.168.4.37（k8s-worker）
**测试文档**: `docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md` §17
**Git 提交**: `0aacc30`
**Alembic 版本**: `b8c9d0e1f2a3`（无变化）

### 17.3 聚焦回归 + 配置检查

| 项目 | 结果 |
|---|---|
| `test_device_metric_facts.py` + `test_prometheus_metric_facts.py` | **9 passed** |
| snmp.yml `cpmCPUTotal5minRev` OID 检查 (`1.3.6.1.4.1.9.9.109.1.1.1.1.8`) | OK |

### 17.4 snmp_exporter + Prometheus CPU series

`cpmCPUTotal5minRev` 在 Prometheus 中返回 **1 series**，实例：`192.168.4.1`

### 17.5 周期 CPU 事实对照

| 设备 | 周期 CPU | Prometheus 解析值 | 匹配 |
|---|---|---|---|
| cn-pulandian1-rtr (10.121.1.1) | 0.0% | 0.0% | ✓ |
| pnetlab-swr (192.168.4.1) | 37.0% | 37.0% | ✓ |

**2 台设备全部匹配** ✓

### 17.6 周期 vs 实时 SNMP CPU

| 设备 | 周期 CPU | 实时 CPU | 差值 |
|---|---|---|---|
| pnetlab-swr (192.168.4.1) | 37.0% | 37.0% | 0.0 |

差值 0.0（允许 20 个百分点） ✓

### 17.7 事实完整度、服务、日志

- CPU 值均在 0–100 范围内 ✓
- `collection_status`: `partial` ✓
- `uptime_days`、接口聚合字段正常 ✓
- Alembic 版本：`b8c9d0e1f2a3` ✓
- `nas-backend`：`active (running)` ✓
- 日志：无 exporter、事实写入或轮询错误 ✓

**结论**: Step 1.3 验证通过。Prometheus 周期 CPU 事实采集正常，值与 Prometheus 解析值完全一致，与实时 SNMP CPU 差值 0 点。Cisco CPU OID 已正确配置到 snmp_exporter。

---

## Step 1.4：指标保留、节流与查询性能门禁（验证）

**执行日期**: 2026-07-16
**测试机**: 192.168.4.37（k8s-worker）
**测试文档**: `docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md` §18
**Git 提交**: `b1e24c6`
**Alembic 版本**: `b8c9d0e1f2a3` → `d0e1f2a3b4c5`

### 18.2 本地逻辑测试

| 测试文件 | 结果 |
|---|---|
| `test_device_metric_facts.py` (4) + `test_prometheus_metric_facts.py` (6) + `test_metric_retention.py` (4) | **14 passed** |

### 18.3 真实 PostgreSQL 事务语义测试

| 测试 | 结果 |
|---|---|
| `test_postgresql_metric_retention.py` | **1 passed** |
| 临时数据清理 (METRIC-RETENTION-PG-%) | 0 |

### 18.5 迁移版本

`b8c9d0e1f2a3` → `d0e1f2a3b4c5` (add device metric retention index)

### 18.6 查询计划索引验证

| 表 | 索引 | 可用 |
|---|---|---|
| `device_metric_samples` | `idx_device_metric_ts` | Index Scan ✓ |
| `interface_traffic_samples` | `ix_interface_traffic_samples_ts` | Index Scan ✓ |

### 18.7 容量与 90 天预测

| 指标 | 当前 | 90 天预测 |
|---|---|---|
| SNMP 设备数 | 6 | — |
| monitored 接口数 | 10 | — |
| 设备事实行数 | 1,182 (384 kB) | 155,520 |
| 接口样本行数 | 76,377 (15 MB) | 1,296,000 |

预测未超过 5000 万行，无容量风险。

### 18.8 5 分钟节流验证

- 第一分钟轮询：写入设备事实 ✓
- 下一分钟轮询：0 设备事实（节流生效）✓
- 接口 `last_check` 持续更新 ✓

### 18.9 保留清理

90 天前过期数据为 0（测试数据库近期建立），清理返回零删除 — 预期行为 ✓

### 18.10 服务与日志

- Alembic 版本：`d0e1f2a3b4c5` ✓
- `nas-backend`：`active (running)` ✓
- `/health`：`{"status":"healthy","version":"2.0.0"}` ✓
- 日志：Prometheus 连接器正常，无错误 ✓

**结论**: Step 1.4 验证通过。时间索引可用，5 分钟事实节流有效（接口刷新不受影响），清理入口可正常调用。Alembic 迁移已应用到 `d0e1f2a3b4c5`。

---

## Step 1.5：AOP 年度计划 — 迁移、并发排程与前端门禁（验证）

**执行日期**: 2026-07-16
**测试机**: 192.168.4.37（k8s-worker）
**测试文档**: `docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md` §19
**Git 提交**: `f27c220`
**Alembic 版本**: `d0e1f2a3b4c5` → `e1f2a3b4c5d6` → `f2a3b4c5d6e7`

### 19.2 聚焦回归

| 测试 | 结果 |
|---|---|
| `test_aop_planning.py` | **11 passed** |

### 19.4 结构检查

| 项目 | 状态 |
|---|---|
| 3 张 AOP 表 (`aop_programs`, `aop_projects`, `aop_maintenance_windows`) | ✓ |
| 5 个任务列 (`aop_project_id`, `maintenance_window_id`, `scheduled_end`, `estimated_hours`, `schedule_source`) | ✓ |
| 5 个执行结果列 (`actual_hours`, `actual_cost`, `completion_result`, `completion_notes`, `completed_at`) | ✓ |
| 3 个索引 (`ix_maintenance_tasks_aop_project_id`, `ix_maintenance_tasks_maintenance_window_id`, `ix_maintenance_tasks_schedule_source`) | ✓ |
| 4 个约束 (`fk_maintenance_task_aop_project`, `fk_maintenance_task_aop_window`, `uq_aop_program_year_version`, `uq_aop_project_program_code`) | ✓ |

### 19.5 并发幂等测试

| 测试 | 结果 |
|---|---|
| `test_postgresql_aop_planning.py` (隔离库) | **1 passed** |
| 临时数据 `AOP-PG-%` | 0 |

### 19.6 AOP API 冒烟

| 端点 | 状态 |
|---|---|
| `GET /api/planned-maintenance/aop/programs?year=2099` | `{"total":0,"items":[]}` (200) ✓ |

### 19.7 Vue 生产构建

| 步骤 | 结果 |
|---|---|
| `npm ci` | 成功 (98 packages) |
| `npm run build` | 成功 |
| `frontend/dist/index.html` | 存在 ✓ |

### 19.8 旧功能回归

| 端点 | 状态 |
|---|---|
| `GET /api/planned-maintenance/plans?limit=1` | 返回 5 条计划 (200) ✓ |
| `GET /api/planned-maintenance/tasks?limit=1` | 返回 8 条任务 (200) ✓ |
| `/health` | `{"status":"healthy","version":"2.0.0"}` ✓ |

### 服务与日志

- `nas-backend`：`active (running)` ✓
- 日志：无 Traceback、IntegrityError 或持续错误 ✓

**结论**: AOP 年度计划功能验证通过。迁移到 `f2a3b4c5d6e7`（含执行结果列），表结构完整，并发幂等测试通过，AOP API 正常，Vue 构建成功，旧功能无回归。25/25 全量聚焦测试通过。
