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
