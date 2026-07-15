# 远程测试机 PostgreSQL 并发测试手册

版本：v1.0
日期：2026-07-15
适用分支：`main`
Step 0 实现基线：`3e92d88`

---

## 1. 测试目标

在远程 Linux 测试机的真实 PostgreSQL 上验证 Step 0 事务防护：

1. 两个独立数据库连接同时出库时，库存不会为负。
2. 库存只有一个成功请求，且只生成一条出库流水。
3. 两个独立数据库连接同时为同一故障创建维修单时，只保留一张维修单。
4. 竞争失败事务会复用胜出维修单，不留下孤立记录。

测试文件：`tests/test_postgresql_concurrency.py`。

## 2. 强制安全规则

- 只能使用独立数据库 `nas_concurrency_test`。
- 禁止把 `TEST_DATABASE_URL` 指向业务库 `nas` 或其他已有数据库。
- 禁止在仓库、聊天、工单或命令历史中保存数据库密码。
- 不运行 `seed_data.py`，不需要启动后端、前端、Redis 或 Celery。
- 测试使用 `STEP0-PG-` 前缀创建临时数据，并在每个用例结束时清理。
- 建库、删库命令必须先确认当前主机是测试机。

## 3. 测试前检查

按现有部署记录，测试机为 `192.168.4.37`，项目目录为
`/home/vayne/network-automation-system`。直接执行：

```bash
ssh vayne@192.168.4.37
cd /home/vayne/network-automation-system
hostname
pwd
```

如果测试机地址、SSH 用户或部署目录已经调整，只替换上面对应值，其余步骤不变。
后续命令要求使用 Bash。

确认工作区没有未提交修改：

```bash
git status --short
```

预期：无输出。若有输出，停止操作并先确认这些修改的归属，不要执行 `git reset --hard`。

确认 PostgreSQL 正常：

```bash
sudo systemctl is-active postgresql
sudo -u postgres psql -tAc "SELECT version();"
```

预期：服务状态为 `active`，并显示 PostgreSQL 版本。

## 4. 拉取远程代码

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git log -3 --oneline --decorate
```

确认以下文件存在：

```bash
test -f app/services/fault_maintenance.py
test -f tests/test_postgresql_concurrency.py
test -f docs/REMOTE_POSTGRESQL_CONCURRENCY_TEST.md
```

以上三条命令均应无输出且退出码为 `0`。

## 5. 准备 Python 环境

优先复用项目现有 `.venv`：

```bash
test -x .venv/bin/python
.venv/bin/python --version
.venv/bin/python -m pip check
```

若 `.venv` 不存在，再创建并安装依赖：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

确认关键依赖：

```bash
.venv/bin/python -c "import sqlalchemy, psycopg2, pytest; print('test dependencies: OK')"
```

预期输出：

```text
test dependencies: OK
```

## 6. 创建独立测试角色和数据库

首次执行时创建专用角色，命令会安全提示输入密码：

```bash
sudo -u postgres createuser --login --pwprompt nas_test_runner
sudo -u postgres createdb --owner=nas_test_runner nas_concurrency_test
```

如果角色或数据库已经存在，不要重复创建，改为检查：

```bash
sudo -u postgres psql -tAc "SELECT rolname FROM pg_roles WHERE rolname='nas_test_runner';"
sudo -u postgres psql -tAc "SELECT datname FROM pg_database WHERE datname='nas_concurrency_test';"
sudo -u postgres psql -d nas_concurrency_test -tAc "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database();"
```

预期依次看到：

```text
nas_test_runner
nas_concurrency_test
nas_test_runner
```

该测试角色不需要超级用户、建库或创建角色权限。

## 7. 安全配置测试连接

使用临时 `PGPASSFILE`，密码不会进入 shell 历史或 Git：

```bash
read -rsp "PostgreSQL test password: " TEST_DB_PASSWORD; echo
export PGPASSFILE="$(mktemp)"
chmod 600 "$PGPASSFILE"
printf '127.0.0.1:5432:nas_concurrency_test:nas_test_runner:%s\n' "$TEST_DB_PASSWORD" > "$PGPASSFILE"
unset TEST_DB_PASSWORD
export TEST_DATABASE_URL='postgresql+psycopg2://nas_test_runner@127.0.0.1:5432/nas_concurrency_test'
```

确认连接目标。这里必须显示 `nas_concurrency_test`，否则立即停止：

```bash
psql -h 127.0.0.1 -U nas_test_runner -d nas_concurrency_test \
  -tAc "SELECT current_database(), current_user;"
```

预期：

```text
nas_concurrency_test|nas_test_runner
```

## 8. 先运行本地逻辑回归

这组测试使用 SQLite，不接触 PostgreSQL：

```bash
unset TEST_DATABASE_URL
.venv/bin/python -m pytest -q \
  tests/test_spare_part_service.py::TestCreateMovement \
  tests/test_fault_transfer_idempotency.py \
  tests/test_workflow_maintenance_idempotency.py
```

预期结果：

```text
13 passed
```

重新设置 PostgreSQL 测试连接：

```bash
export TEST_DATABASE_URL='postgresql+psycopg2://nas_test_runner@127.0.0.1:5432/nas_concurrency_test'
```

## 9. 执行 PostgreSQL 双连接并发测试

```bash
mkdir -p ~/nas-test-results
TEST_LOG=~/nas-test-results/step0-postgresql-$(date +%Y%m%d-%H%M%S).log
.venv/bin/python -m pytest -q -rA -m postgresql \
  tests/test_postgresql_concurrency.py 2>&1 | tee "$TEST_LOG"
test "${PIPESTATUS[0]}" -eq 0
```

预期结果：

```text
2 passed
```

通过标准：

- 命令退出码为 `0`。
- 两个用例全部通过，无 `FAILED`、死锁或超时。
- 库存用例最终数量为 `0`，只有一条出库流水。
- 维修用例两个线程得到相同 `maintenance_id`，数据库只有一条维修记录。

日志位置会保存在 `$TEST_LOG`。提交测试结果时只提供日志，不提供密码或连接串。

## 10. 检查临时数据是否清理

```bash
psql -h 127.0.0.1 -U nas_test_runner -d nas_concurrency_test <<'SQL'
SELECT count(*) AS remaining_devices
FROM devices WHERE name LIKE 'STEP0-PG-%';

SELECT count(*) AS remaining_faults
FROM fault_records WHERE fault_no LIKE 'STEP0-PG-%';

SELECT count(*) AS remaining_maintenance
FROM maintenance_records WHERE maint_no LIKE 'STEP0-PG-%';

SELECT count(*) AS remaining_parts
FROM spare_parts WHERE part_number LIKE 'STEP0-PG-%';
SQL
```

四个计数都必须为 `0`。

## 11. 清理连接凭据

```bash
unset TEST_DATABASE_URL
rm -f "$PGPASSFILE"
unset PGPASSFILE
```

独立测试库可以保留用于后续回归。若确认不再需要，可删除：

```bash
sudo -u postgres dropdb --if-exists nas_concurrency_test
sudo -u postgres dropuser --if-exists nas_test_runner
```

## 12. 测试通过后的部署冒烟检查

只有第 8、9、10 节全部通过后，才重启测试环境后端：

```bash
sudo systemctl restart nas-backend
sudo systemctl --no-pager --full status nas-backend
curl -fsS http://127.0.0.1:8000/health
journalctl -u nas-backend --since "5 minutes ago" --no-pager | tail -n 100
```

验收要求：

- `nas-backend` 状态为 `active (running)`。
- `/health` 返回成功。
- 最近日志无数据库连接失败、事务异常或持续 500 错误。
- 不需要执行数据库迁移，本轮没有 schema 变更。

## 13. 失败时如何处理

任何一步失败都不要继续部署。保存以下信息：

```bash
git rev-parse HEAD
.venv/bin/python --version
.venv/bin/python -m pip show SQLAlchemy psycopg2-binary pytest
sudo -u postgres psql -tAc "SELECT version();"
cat "$TEST_LOG"
```

不要发送：

- `PGPASSFILE` 内容。
- 数据库密码。
- 带密码的数据库 URL。
- `.env`、`config.yaml` 或私钥。

常见问题：

| 现象 | 处理 |
|---|---|
| PostgreSQL 用例显示 `SKIPPED` | `TEST_DATABASE_URL` 未设置或 URL 不含 `postgresql` |
| `password authentication failed` | 重新执行第 7 节，确认测试角色密码 |
| `permission denied for schema public` | 确认数据库 owner 是 `nas_test_runner` |
| `database does not exist` | 重新执行第 6 节创建独立测试库 |
| `ModuleNotFoundError: psycopg2` | 在 `.venv` 中安装 `psycopg2-binary==2.9.9` |
| 测试超时 | 保存日志，检查 PG 锁等待，不要改用业务库重试 |

检查锁等待：

```bash
sudo -u postgres psql -d nas_concurrency_test -c \
  "SELECT pid, wait_event_type, wait_event, state, query FROM pg_stat_activity WHERE datname='nas_concurrency_test';"
```