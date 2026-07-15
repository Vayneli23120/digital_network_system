# Test Results — 2026-07-15

**Overall: 289 passed, 60 failed** (3 test files skipped: console_service, postgresql_concurrency, redis_cache due to infrastructure dependencies)

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
