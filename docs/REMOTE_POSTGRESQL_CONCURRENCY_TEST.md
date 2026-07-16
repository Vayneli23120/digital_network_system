# 远程测试机 PostgreSQL 并发测试手册

版本：v1.1
日期：2026-07-16
适用分支：`main`
Step 0 实现基线：`3e92d88`

本文件也是后续阶段的远程测试机验收记录入口。凡本地无法覆盖、必须在
PostgreSQL、真实 SNMP 或部署服务上验证的变更，继续按阶段追加到本文件，
不另建口径不同的临时步骤。

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
.venv/bin/python -c "import sqlalchemy, psycopg2, pytest, netmiko, napalm; print('test dependencies: OK'); print('netmiko:', netmiko.__file__); print('napalm:', napalm.__file__)"
```

预期输出：

```text
test dependencies: OK
netmiko: /home/vayne/network-automation-system/.venv/lib/python3.x/site-packages/netmiko/__init__.py
napalm: /home/vayne/network-automation-system/.venv/lib/python3.x/site-packages/napalm/__init__.py
```

所有测试命令必须使用 `.venv/bin/python -m pytest`。禁止直接执行裸 `pytest`
或系统 `python`，否则会误报 Netmiko、NAPALM 等依赖缺失。

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

---

## 14. Step 1：设备指标事实层远程验证

### 14.1 验证目标

本阶段只增加事实层，不切换 Dashboard、Operations 或 Monitor3D 页面口径：

1. 新表 `device_metric_samples` 可在 PostgreSQL 正确迁移。
2. 现有 `GET /api/devices/{id}/metrics` 响应保持兼容。
3. 每次成功执行设备指标查询后，CPU、内存、温度等字段旁路写入事实表。
4. 新接口 `GET /api/devices/{id}/metrics/history` 按时间升序返回历史样本。
5. 指标落库失败不得影响原实时指标响应。

### 14.2 拉取代码并确认 Python 环境

```bash
cd /home/vayne/network-automation-system
git status --short
git pull --ff-only origin main
git log -3 --oneline --decorate
.venv/bin/python -c "import sys, netmiko, napalm; print(sys.executable); print(netmiko.__file__); print(napalm.__file__)"
```

预期 Python 路径为：

```text
/home/vayne/network-automation-system/.venv/bin/python
```

若 `git status --short` 有输出，或模块路径不在项目 `.venv` 下，停止测试并先修正环境。

### 14.3 运行聚焦回归

```bash
unset TEST_DATABASE_URL
.venv/bin/python -m pytest -q tests/test_device_metric_facts.py
```

预期：

```text
4 passed
```

验证前端 API 导出可构建：

```bash
npm --prefix frontend run build
```

预期 Vite 构建成功。测试机是离线环境，应复用已经安装的 `node_modules`；
不要临时改 npm registry 或关闭 TLS 校验。

### 14.4 备份测试环境数据库

以下操作针对测试环境数据库 `nas`，不得在生产机执行：

```bash
mkdir -p ~/nas-test-results
BACKUP_FILE=~/nas-test-results/nas-before-step1-$(date +%Y%m%d-%H%M%S).dump
sudo -u postgres pg_dump -Fc nas > "$BACKUP_FILE"
test -s "$BACKUP_FILE"
ls -lh "$BACKUP_FILE"
```

备份文件必须存在且大小大于 `0`，否则停止迁移。

### 14.5 检查并执行 Alembic 迁移

```bash
.venv/bin/python -m alembic heads
.venv/bin/python -m alembic current
```

`heads` 必须包含：

```text
b8c9d0e1f2a3 (head)
```

如果 `current` 没有输出，说明该数据库未纳入 Alembic 版本管理。此时停止操作，
不要自行执行 `stamp`，也不要手工建表。

确认无误后执行：

```bash
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
```

预期当前版本为 `b8c9d0e1f2a3`。

### 14.6 检查 PostgreSQL 表结构

```bash
sudo -u postgres psql -d nas -c "\d+ device_metric_samples"
sudo -u postgres psql -d nas -tAc \
  "SELECT indexname FROM pg_indexes WHERE tablename='device_metric_samples' ORDER BY indexname;"
```

必须存在：

- 主键 `device_metric_samples_pkey`
- 外键 `device_id -> devices.id`，删除设备时级联删除样本
- 索引 `idx_device_metric_device_ts`
- 字段 `cpu_percent`、`memory_percent`、`temperature_c`、`collection_status`

### 14.7 用真实 SNMP 设备生成一个事实样本

以下脚本使用应用自身配置选择一台已启用 SNMP 的设备，并调用与 API 相同的函数：

```bash
.venv/bin/python - <<'PY'
import asyncio

from app.features.devices.router import get_device_performance_metrics
from app.shared.database import get_db_manager
from app.shared.models import Device, DeviceMetricSample

manager = get_db_manager()
db = manager.get_session()
try:
  device = db.query(Device).filter(
    Device.snmp_enabled.is_(True),
    Device.snmp_community.isnot(None),
    Device.ip.isnot(None),
  ).order_by(Device.id).first()
  if not device:
    raise SystemExit('FAIL: no SNMP-enabled test device found')

  before = db.query(DeviceMetricSample).filter(
    DeviceMetricSample.device_id == device.id
  ).count()
  result = asyncio.run(get_device_performance_metrics(device.id, db))
  after = db.query(DeviceMetricSample).filter(
    DeviceMetricSample.device_id == device.id
  ).count()

  print('device:', device.id, device.name, device.ip)
  print('snmp_available:', result.get('snmp_available'))
  print('cpu:', result.get('cpu'))
  print('memory:', result.get('memory'))
  print('temperature:', result.get('temperature'))
  print('sample_count:', before, '->', after)

  if result.get('error'):
    raise SystemExit(f"FAIL: metric query returned error: {result['error']}")
  if after != before + 1:
    raise SystemExit('FAIL: metric fact row was not persisted')
finally:
  db.close()
PY
```

通过标准：

- `snmp_available: True`
- 没有 `FAIL`
- `sample_count` 增加 `1`
- CPU、内存或温度至少一个包含真实数值；不支持的厂商 OID 可以为 `None`

### 14.8 验证历史查询服务

```bash
.venv/bin/python - <<'PY'
from app.services.device_metric_facts import get_device_metric_samples, device_metric_sample_to_dict
from app.shared.database import get_db_manager
from app.shared.models import Device

manager = get_db_manager()
db = manager.get_session()
try:
  device = db.query(Device).filter(Device.snmp_enabled.is_(True)).order_by(Device.id).first()
  samples = get_device_metric_samples(db, device.id, limit=5)
  print([device_metric_sample_to_dict(sample) for sample in samples])
  if not samples:
    raise SystemExit('FAIL: no metric history returned')
  if samples != sorted(samples, key=lambda sample: (sample.ts, sample.id)):
    raise SystemExit('FAIL: metric history is not chronological')
finally:
  db.close()
PY
```

预期至少返回一条记录，`source` 为 `snmp_live`，时间顺序从旧到新。

### 14.9 重启后端并检查日志

```bash
sudo systemctl restart nas-backend
sudo systemctl --no-pager --full status nas-backend
curl -fsS http://127.0.0.1:8000/health
journalctl -u nas-backend --since "5 minutes ago" --no-pager | tail -n 100
```

通过标准：服务为 `active (running)`、健康检查成功，日志无
`device_metric_samples`、迁移或持续数据库写入异常。

### 14.10 Step 1 当前切片通过标准

必须同时满足：

- 聚焦测试 `4 passed`
- Vue 前端构建成功
- Alembic 当前版本为 `b8c9d0e1f2a3`
- PostgreSQL 表与索引存在
- 真实 SNMP 查询后样本数增加 `1`
- 历史样本按时间升序返回
- 后端重启及健康检查正常

将结果追加到测试报告，记录提交号、迁移版本、测试数量和真实样本字段；
不要记录 SNMP community、数据库密码或其他凭据。
