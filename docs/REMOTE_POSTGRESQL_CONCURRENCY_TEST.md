# 远程测试机 PostgreSQL 并发测试手册

版本：v1.6
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

from app.features.devices.snmp_service import get_snmp_service
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

---

## 15. Step 1.1：Prometheus 周期事实采集远程验证

### 15.1 验证目标

本切片不增加数据库迁移、不修改前端页面，验证以下行为：

1. 后端每次 Prometheus 轮询自动写入一条 `prometheus_snmp` 设备事实，
   不再依赖用户打开实时指标页面。
2. 接口 up/down/total、错误计数和 `sysUpTime` 从同一批 Prometheus 数据派生，
   不增加逐台设备 SNMP 请求。
3. 事实写入使用独立 savepoint；即使旁路写入失败，原接口状态更新仍可提交。
4. Alembic 版本保持 `b8c9d0e1f2a3`。

### 15.2 拉取代码并确认运行环境

```bash
cd /home/vayne/network-automation-system
git status --short
git pull --ff-only origin main
git rev-parse --short HEAD
.venv/bin/python - <<'PY'
import apscheduler
import httpx

print('python dependencies: OK')
print('httpx:', httpx.__version__, httpx.__file__)
print('apscheduler:', apscheduler.__version__, apscheduler.__file__)
PY
```

`git status --short` 必须无输出，两个模块路径必须位于项目 `.venv` 下。
如果模块缺失，停止验证并从测试环境批准的离线包源补齐依赖；不要切换公共镜像，
不要关闭 TLS 校验。

### 15.3 运行聚焦回归

```bash
unset TEST_DATABASE_URL
.venv/bin/python -m pytest -q \
  tests/test_device_metric_facts.py \
  tests/test_prometheus_metric_facts.py
```

预期：

```text
8 passed
```

其中必须包含 `test_metric_fact_failure_preserves_interface_updates` 通过。

### 15.4 验证 Prometheus 已提供批量指标

```bash
.venv/bin/python - <<'PY'
import httpx

base_url = 'http://127.0.0.1:9090'
for metric in ('sysUpTime', 'ifOperStatus', 'ifInErrors', 'ifOutErrors'):
  response = httpx.get(
    f'{base_url}/api/v1/query',
    params={'query': metric},
    timeout=30,
  )
  response.raise_for_status()
  body = response.json()
  results = body.get('data', {}).get('result', [])
  print(metric, 'series:', len(results))
  if body.get('status') != 'success' or not results:
    raise SystemExit(f'FAIL: Prometheus metric unavailable: {metric}')
PY
```

四项查询都必须成功且至少返回一个 series。`sysUpTime` 由 snmp_exporter
按秒暴露，连接器换算后写入 `uptime_days`。

### 15.5 记录基线并触发真实后台轮询

```bash
BEFORE_FACTS=$(sudo -u postgres psql -d nas -tAc \
  "SELECT COUNT(*) FROM device_metric_samples WHERE source='prometheus_snmp';")
BEFORE_LAST_CHECK=$(sudo -u postgres psql -d nas -tAc \
  "SELECT COALESCE(MAX(last_check)::text, '') FROM device_interfaces;")
echo "before facts: $BEFORE_FACTS"
echo "before interface last_check: $BEFORE_LAST_CHECK"

sudo systemctl restart nas-backend
sudo systemctl is-active --quiet nas-backend
curl -fsS http://127.0.0.1:8000/health

AFTER_FACTS=$(sudo -u postgres psql -d nas -tAc \
  "SELECT COUNT(*) FROM device_metric_samples WHERE source='prometheus_snmp';")
AFTER_LAST_CHECK=$(sudo -u postgres psql -d nas -tAc \
  "SELECT COALESCE(MAX(last_check)::text, '') FROM device_interfaces;")
echo "after facts: $AFTER_FACTS"
echo "after interface last_check: $AFTER_LAST_CHECK"

test "$AFTER_FACTS" -gt "$BEFORE_FACTS"
test -n "$AFTER_LAST_CHECK"
test "$AFTER_LAST_CHECK" != "$BEFORE_LAST_CHECK"
```

连接器在后端启动时立即执行一次，因此无需等待下一个 60 秒周期。通过标准：

- `AFTER_FACTS > BEFORE_FACTS`
- `AFTER_LAST_CHECK` 非空且发生变化
- 全程没有调用设备实时指标 API

### 15.6 检查周期事实内容

```bash
sudo -u postgres psql -d nas -x -c \
  "SELECT id, device_id, ts, source, collection_status,
          uptime_days, interfaces_up, interfaces_down,
          interfaces_total, total_errors
     FROM device_metric_samples
    WHERE source='prometheus_snmp'
    ORDER BY ts DESC, id DESC
    LIMIT 5;"
```

预期：

- `source` 全部为 `prometheus_snmp`
- `collection_status` 为 `partial`
- `uptime_days` 为非负整数
- `interfaces_up + interfaces_down <= interfaces_total`
- 支持 IF-MIB 错误计数时，`total_errors` 为非负整数

CPU、内存和温度在当前 exporter 配置中没有对应厂商 OID，保持 `NULL` 是预期行为；
本切片不得为填充这些字段改回逐台 SNMP 轮询。

### 15.7 检查版本、服务和日志

```bash
.venv/bin/python -m alembic current
sudo systemctl --no-pager --full status nas-backend
journalctl -u nas-backend --since "10 minutes ago" --no-pager | \
  grep -E "Prometheus poll:|metric facts|Metric fact persist failed|Poll cycle failed"
```

通过标准：

- Alembic 当前版本仍为 `b8c9d0e1f2a3`
- 服务为 `active (running)`
- 日志包含 `Prometheus poll: ... metric facts`
- 日志没有持续出现 `Metric fact persist failed` 或 `Poll cycle failed`

### 15.8 Step 1.1 通过标准

必须同时满足：

- 聚焦测试 `8 passed`
- Prometheus 四项批量指标均有数据
- 后端启动轮询后 `prometheus_snmp` 样本数自动增加
- 原 `device_interfaces.last_check` 同时更新
- 周期事实字段满足 15.6 的约束
- Alembic 版本未变化，后端健康且日志无持续轮询错误

将提交号、测试数量、轮询前后样本数、最新事实字段和服务状态追加到测试报告；
不要记录 SNMP community、数据库密码或其他凭据。

---

## 16. Step 1.2：Prometheus uptime 双格式兼容验证

### 16.1 验证目标

Step 1.1 的真实报告中，同一设备实时 SNMP 返回 `uptime_days=19`，周期事实却为
`uptime_days=0`。本切片验证根因和修复结果：

1. snmp_exporter 将真实值放在 `sysUpTime` 同名标签时，优先读取标签。
2. 标准 Prometheus 格式仍从样本 `value[1]` 读取。
3. 周期事实与原始 Prometheus 值完全一致。
4. 周期事实与同一设备实时 SNMP uptime 的差值不超过 1 天。

本切片不增加数据库迁移，不修改前端页面，也不改变采集频率。

### 16.2 拉取代码并运行聚焦回归

```bash
cd /home/vayne/network-automation-system
git status --short
git pull --ff-only origin main
git rev-parse --short HEAD
unset TEST_DATABASE_URL
.venv/bin/python -m pytest -q \
  tests/test_device_metric_facts.py \
  tests/test_prometheus_metric_facts.py
```

`git status --short` 必须无输出，预期测试结果：

```text
8 passed
```

### 16.3 检查原始 Prometheus uptime 格式

```bash
.venv/bin/python - <<'PY'
import math

import httpx

response = httpx.get(
  'http://127.0.0.1:9090/api/v1/query',
  params={'query': 'sysUpTime'},
  timeout=30,
)
response.raise_for_status()
results = response.json().get('data', {}).get('result', [])
if not results:
  raise SystemExit('FAIL: sysUpTime has no Prometheus series')

for item in results:
  labels = item.get('metric') or {}
  sample = item.get('value') or []
  label_value = labels.get('sysUpTime')
  sample_value = sample[1] if len(sample) >= 2 else None
  selected = label_value if label_value not in (None, '') else sample_value
  try:
    seconds = float(selected)
  except (TypeError, ValueError):
    raise SystemExit(f"FAIL: invalid sysUpTime for {labels.get('instance')}")
  if seconds < 0 or not math.isfinite(seconds):
    raise SystemExit(f"FAIL: invalid sysUpTime for {labels.get('instance')}")
  print(
    'instance=', labels.get('instance'),
    'label=', label_value,
    'sample=', sample_value,
    'selected=', selected,
    'expected_days=', int(seconds // 86400),
  )
PY
```

记录输出中真实值位于 `label` 还是 `sample`。禁止只记录 `expected_days`，否则无法
证明测试覆盖了哪一种 exporter 格式。

### 16.4 触发新周期事实并逐设备对照原始值

```bash
BEFORE_ID=$(sudo -u postgres psql -d nas -tAc \
  "SELECT COALESCE(MAX(id), 0) FROM device_metric_samples;")
sudo systemctl restart nas-backend
sudo systemctl is-active --quiet nas-backend
curl -fsS http://127.0.0.1:8000/health
echo "before id: $BEFORE_ID"

BEFORE_ID="$BEFORE_ID" .venv/bin/python - <<'PY'
import os

import httpx

from app.shared.database import get_db_manager
from app.shared.models import Device, DeviceMetricSample

before_id = int(os.environ['BEFORE_ID'])
response = httpx.get(
  'http://127.0.0.1:9090/api/v1/query',
  params={'query': 'sysUpTime'},
  timeout=30,
)
response.raise_for_status()

expected_by_ip = {}
for item in response.json().get('data', {}).get('result', []):
  labels = item.get('metric') or {}
  sample = item.get('value') or []
  instance = labels.get('instance')
  if not instance:
    continue
  raw = labels.get('sysUpTime')
  if raw in (None, ''):
    raw = sample[1] if len(sample) >= 2 else None
  expected_by_ip[instance.rsplit(':', 1)[0]] = int(float(raw) // 86400)

db = get_db_manager().get_session()
try:
  rows = (
    db.query(Device.ip, DeviceMetricSample)
    .join(DeviceMetricSample, DeviceMetricSample.device_id == Device.id)
    .filter(
      DeviceMetricSample.id > before_id,
      DeviceMetricSample.source == 'prometheus_snmp',
    )
    .all()
  )
  if not rows:
    raise SystemExit('FAIL: restart did not create prometheus_snmp facts')

  checked = 0
  for ip, sample in rows:
    if ip not in expected_by_ip:
      continue
    expected = expected_by_ip[ip]
    print(ip, 'fact_days=', sample.uptime_days, 'expected_days=', expected)
    if sample.uptime_days != expected:
      raise SystemExit(f'FAIL: uptime mismatch for {ip}')
    checked += 1
  if checked == 0:
    raise SystemExit('FAIL: no fact could be matched to Prometheus instance')
  print('matched facts:', checked)
finally:
  db.close()
PY
```

必须至少匹配一台设备，且每台输出的 `fact_days == expected_days`。

### 16.5 与同一设备实时 SNMP uptime 对照

```bash
.venv/bin/python - <<'PY'
import asyncio

from app.features.devices.router import get_device_performance_metrics
from app.shared.database import get_db_manager
from app.shared.models import Device, DeviceMetricSample

db = get_db_manager().get_session()
try:
  periodic = (
    db.query(DeviceMetricSample)
    .join(Device, Device.id == DeviceMetricSample.device_id)
    .filter(
      DeviceMetricSample.source == 'prometheus_snmp',
      DeviceMetricSample.uptime_days.isnot(None),
      Device.snmp_enabled.is_(True),
      Device.snmp_community.isnot(None),
    )
    .order_by(DeviceMetricSample.ts.desc(), DeviceMetricSample.id.desc())
    .first()
  )
  if not periodic:
    raise SystemExit('FAIL: no comparable periodic fact found')

  device = db.query(Device).filter(Device.id == periodic.device_id).one()
  live = asyncio.run(get_device_performance_metrics(device.id, db))
  live_days = (live.get('uptime') or {}).get('uptime_days')
  print(
    'device=', device.id, device.name, device.ip,
    'periodic_days=', periodic.uptime_days,
    'live_days=', live_days,
  )
  if live.get('error'):
    raise SystemExit(f"FAIL: live SNMP query failed: {live['error']}")
  if live_days is None:
    raise SystemExit('FAIL: live SNMP uptime is unavailable')
  if abs(periodic.uptime_days - live_days) > 1:
    raise SystemExit('FAIL: periodic and live uptime differ by more than 1 day')
finally:
  db.close()
PY
```

只记录设备 ID、名称、IP 和两个天数；不要记录 SNMP community。允许最多 1 天差值，
用于覆盖采样时间跨日边界。

### 16.6 检查版本和日志

```bash
.venv/bin/python -m alembic current
sudo systemctl --no-pager --full status nas-backend
journalctl -u nas-backend --since "10 minutes ago" --no-pager | \
  grep -E "Prometheus poll:|Metric fact persist failed|Poll cycle failed"
```

通过标准：

- Alembic 仍为 `b8c9d0e1f2a3`
- 后端为 `active (running)`
- 日志包含成功轮询，且没有持续事实写入或轮询失败

### 16.7 Step 1.2 通过标准

必须同时满足：

- 聚焦测试 `8 passed`
- 原始输出明确记录 label/sample 两种位置中的实际值来源
- 新周期事实至少匹配一台设备，且 uptime 与 Prometheus 原始值换算结果一致
- 同一设备周期 uptime 与实时 SNMP uptime 差值不超过 1 天
- Alembic 版本未变化，后端健康且日志无持续错误

将原始值位置、对照设备、两个 uptime 天数、匹配事实数、提交号和服务状态追加到
测试报告；不要记录 SNMP community、数据库密码或其他凭据。

---

## 17. Step 1.3：Prometheus 周期 CPU 事实验证

### 17.1 验证目标

本切片在现有 `cisco_if` exporter 模块中增加 Cisco
`cpmCPUTotal5minRev`，每轮通过一次 Prometheus 全量查询写入设备事实：

1. 不增加逐台 SNMP 请求，轮询批量查询数从 8 次增加到 9 次。
2. 同一设备有多个 CPU series 时，采用有效值中的最大值，避免局部高负载被平均。
3. CPU 必须为有限的 `0–100` 数值；缺失、非法或越界时保持 `NULL`。
4. 新周期事实的 `cpu_percent` 与连接器从 Prometheus 解析出的值一致。
5. 与同一 OID 的实时 SNMP CPU 做合理性对照。

本切片不增加数据库迁移、不切换前端页面，也不采集尚未验证的内存或温度 OID。

### 17.2 备份 exporter 配置并拉取代码

```bash
cd /home/vayne/network-automation-system
git status --short
mkdir -p ~/nas-test-results
CPU_CONFIG_BACKUP=~/nas-test-results/snmp-before-step1.3-$(date +%Y%m%d-%H%M%S).yml
cp docker/snmp_exporter/snmp.yml "$CPU_CONFIG_BACKUP"
test -s "$CPU_CONFIG_BACKUP"

git pull --ff-only origin main
git rev-parse --short HEAD
```

拉取前 `git status --short` 必须无输出，备份文件必须存在且大小大于 `0`。

### 17.3 运行聚焦回归和静态配置检查

```bash
unset TEST_DATABASE_URL
.venv/bin/python -m pytest -q \
  tests/test_device_metric_facts.py \
  tests/test_prometheus_metric_facts.py

.venv/bin/python - <<'PY'
import yaml

path = 'docker/snmp_exporter/snmp.yml'
with open(path, encoding='utf-8') as stream:
  config = yaml.safe_load(stream)
module = config['modules']['cisco_if']
metric = next(
  item for item in module['metrics']
  if item['name'] == 'cpmCPUTotal5minRev'
)
expected_oid = '1.3.6.1.4.1.9.9.109.1.1.1.1.8'
assert metric['oid'] == expected_oid
assert metric['type'] == 'Gauge32'
assert metric['indexes'] == [
  {'labelname': 'cpmCPUTotalIndex', 'type': 'Integer'}
]
assert expected_oid in module['walk']
print('snmp CPU config: OK')
PY
```

预期：

```text
9 passed
snmp CPU config: OK
```

### 17.4 重启 snmp_exporter 并确认 CPU series

```bash
sudo docker restart netsnmp
sudo docker inspect -f '{{.State.Status}}' netsnmp
sudo docker logs --since 2m netsnmp
```

容器状态必须为 `running`，日志不得包含配置解析错误。如果启动失败，立即恢复：

```bash
cp "$CPU_CONFIG_BACKUP" docker/snmp_exporter/snmp.yml
sudo docker restart netsnmp
sudo docker inspect -f '{{.State.Status}}' netsnmp
```

恢复后停止 Step 1.3，不得继续重启后端。

容器正常时，等待 Prometheus 下一次 scrape 并检查新指标：

```bash
.venv/bin/python - <<'PY'
import time

import httpx

url = 'http://127.0.0.1:9090/api/v1/query'
results = []
for _attempt in range(9):
  response = httpx.get(
    url,
    params={'query': 'cpmCPUTotal5minRev'},
    timeout=30,
  )
  response.raise_for_status()
  results = response.json().get('data', {}).get('result', [])
  if results:
    break
  time.sleep(10)

print('CPU series:', len(results))
if not results:
  raise SystemExit('FAIL: cpmCPUTotal5minRev has no Prometheus series')

instances = sorted({
  (item.get('metric') or {}).get('instance')
  for item in results
  if (item.get('metric') or {}).get('instance')
})
print('CPU instances:', instances)
PY
```

至少返回一个 CPU series。只记录 instance 和 series 数，不记录 auth/community 标签。
部分不支持 CISCO-PROCESS-MIB 的设备可以没有该指标。

### 17.5 触发周期事实并与 Prometheus 解析值对照

```bash
BEFORE_ID=$(sudo -u postgres psql -d nas -tAc \
  "SELECT COALESCE(MAX(id), 0) FROM device_metric_samples;")
sudo systemctl restart nas-backend
sudo systemctl is-active --quiet nas-backend
curl -fsS http://127.0.0.1:8000/health
echo "before id: $BEFORE_ID"

BEFORE_ID="$BEFORE_ID" .venv/bin/python - <<'PY'
import os

from app.services.prometheus_connector import PrometheusConnector
from app.shared.database import get_db_manager
from app.shared.models import Device, DeviceMetricSample

before_id = int(os.environ['BEFORE_ID'])
connector = PrometheusConnector()
try:
  cpu_by_instance = connector._fetch_device_cpu()
finally:
  connector._http.close()

expected_by_ip = {
  instance.rsplit(':', 1)[0]: value
  for instance, value in cpu_by_instance.items()
}
print('parsed CPU devices:', len(expected_by_ip))
if not expected_by_ip:
  raise SystemExit('FAIL: connector parsed no CPU values')

db = get_db_manager().get_session()
try:
  rows = (
    db.query(Device, DeviceMetricSample)
    .join(DeviceMetricSample, DeviceMetricSample.device_id == Device.id)
    .filter(
      DeviceMetricSample.id > before_id,
      DeviceMetricSample.source == 'prometheus_snmp',
      DeviceMetricSample.cpu_percent.isnot(None),
    )
    .all()
  )
  if not rows:
    raise SystemExit('FAIL: restart created no periodic CPU facts')

  checked = 0
  for device, sample in rows:
    expected = expected_by_ip.get(device.ip)
    if expected is None:
      continue
    print(
      device.id, device.name, device.ip,
      'fact_cpu=', sample.cpu_percent,
      'prometheus_cpu=', expected,
    )
    if sample.cpu_percent != expected:
      raise SystemExit(f'FAIL: CPU fact mismatch for {device.ip}')
    checked += 1
  if checked == 0:
    raise SystemExit('FAIL: no CPU fact matched a Prometheus instance')
  print('matched CPU facts:', checked)
finally:
  db.close()
PY
```

必须至少匹配一台设备，且每台输出的 `fact_cpu == prometheus_cpu`。

### 17.6 与同一设备实时 SNMP CPU 对照

```bash
.venv/bin/python - <<'PY'
import asyncio

from app.features.devices.router import get_device_performance_metrics
from app.shared.database import get_db_manager
from app.shared.models import Device, DeviceMetricSample

db = get_db_manager().get_session()
try:
  periodic = (
    db.query(DeviceMetricSample)
    .join(Device, Device.id == DeviceMetricSample.device_id)
    .filter(
      DeviceMetricSample.source == 'prometheus_snmp',
      DeviceMetricSample.cpu_percent.isnot(None),
      Device.snmp_enabled.is_(True),
      Device.snmp_community.isnot(None),
    )
    .order_by(DeviceMetricSample.ts.desc(), DeviceMetricSample.id.desc())
    .first()
  )
  if not periodic:
    raise SystemExit('FAIL: no comparable periodic CPU fact found')

  device = db.query(Device).filter(Device.id == periodic.device_id).one()
  service = get_snmp_service()
  if not service.is_available():
    raise SystemExit('FAIL: live SNMP service is unavailable')
  cpu_oid = service.get_oid_set(device.vendor or 'cisco').get('cpu_5min')
  values = asyncio.run(
    service.snmp_walk_async(
      device.ip,
      device.snmp_community,
      cpu_oid,
      timeout=3,
    )
  )
  valid = [
    float(value)
    for value in values.values()
    if isinstance(value, (int, float)) and 0 <= float(value) <= 100
  ]
  live_cpu = max(valid) if valid else None
  print(
    'device=', device.id, device.name, device.ip,
    'periodic_cpu=', periodic.cpu_percent,
    'live_cpu=', live_cpu,
  )
  if live_cpu is None:
    raise SystemExit('FAIL: live SNMP CPU is unavailable')
  if abs(periodic.cpu_percent - live_cpu) > 20:
    raise SystemExit('FAIL: periodic and live CPU differ by more than 20 points')
finally:
  db.close()
PY
```

周期和实时 SNMP 都对同一 OID 的有效 series 取最大值。CPU 是动态值，因此允许
20 个百分点差值。
只记录设备 ID、名称、IP 和两个 CPU 数值，不记录 SNMP community。

### 17.7 检查事实完整度、服务和日志

```bash
sudo -u postgres psql -d nas -x -c \
  "SELECT id, device_id, ts, source, collection_status,
          cpu_percent, uptime_days, interfaces_up,
          interfaces_down, interfaces_total, total_errors
     FROM device_metric_samples
    WHERE source='prometheus_snmp' AND cpu_percent IS NOT NULL
    ORDER BY ts DESC, id DESC
    LIMIT 5;"

.venv/bin/python -m alembic current
sudo systemctl --no-pager --full status nas-backend
journalctl -u nas-backend --since "10 minutes ago" --no-pager | \
  grep -E "Prometheus poll:|cpmCPUTotal5minRev|Metric fact persist failed|Poll cycle failed"
```

通过标准：

- 周期事实 CPU 均在 `0–100`
- `collection_status` 为 `partial`
- uptime 和接口聚合字段仍正常存在
- Alembic 仍为 `b8c9d0e1f2a3`
- 后端为 `active (running)`，连接器日志无持续错误

### 17.8 Step 1.3 通过标准

必须同时满足：

- 聚焦测试 `9 passed`，静态 exporter 配置检查通过
- snmp_exporter 重启成功，Prometheus 至少返回一个 CPU series
- 新周期事实至少有一条非空 CPU，且与连接器 Prometheus 解析值一致
- 同一设备周期 CPU 与实时 SNMP CPU 差值不超过 20 个百分点
- uptime、接口聚合未回归，Alembic 版本未变化
- 后端健康且日志无持续 exporter、事实写入或轮询错误

将提交号、CPU series 数、匹配事实数、对照设备与两个 CPU 数值、服务状态追加到
测试报告；不要记录 SNMP community、数据库密码或其他凭据。

---

## 18. Step 1.4：指标保留、节流与查询性能门禁

### 18.1 验证目标

这是进入计划维护/AOP 等大模块改造前的最后一项指标基础门禁：

1. Prometheus 接口状态仍每 60 秒刷新，设备事实默认每 300 秒最多写一条。
2. 设备事实和接口流量样本默认保留 90 天，每 24 小时执行一次清理。
3. 清理按每表最多 5000 行一批提交，避免长事务持续锁表。
4. cutoff 使用严格小于号：恰好位于 cutoff 的记录必须保留。
5. `device_metric_samples.ts` 和 `interface_traffic_samples.ts` 均有可用索引。

默认值可由以下环境变量覆盖：

```text
DEVICE_METRIC_SAMPLE_INTERVAL=300
DEVICE_METRIC_RETENTION_DAYS=90
DEVICE_METRIC_CLEANUP_INTERVAL=86400
DEVICE_METRIC_CLEANUP_BATCH_SIZE=5000
```

生产调整前必须在测试机重新执行本节。不得把采样间隔降到 60 秒后直接上线。

### 18.2 拉取代码并运行本地逻辑测试

```bash
cd /home/vayne/network-automation-system
git status --short
git pull --ff-only origin main
git rev-parse --short HEAD

unset TEST_DATABASE_URL
.venv/bin/python -m pytest -q \
  tests/test_device_metric_facts.py \
  tests/test_prometheus_metric_facts.py \
  tests/test_metric_retention.py
```

拉取前 `git status --short` 必须无输出。预期：

```text
14 passed
```

必须包含以下边界通过：

- 连续两次轮询只写一批设备事实
- 299 秒不写、300 秒允许写
- cutoff 时刻记录保留
- 多批清理可完整排空
- 时间索引存在

### 18.3 真实 PostgreSQL 事务语义测试

使用第 7 节已经配置的隔离数据库 `TEST_DATABASE_URL`，不得使用系统 Python：

```bash
.venv/bin/python -m pytest -q tests/test_postgresql_metric_retention.py
```

预期：

```text
1 passed
```

测试在同一事务内创建 1899/1900 年边界记录，验证后执行 rollback，不留下设备、
接口或指标样本。随后检查临时前缀：

```bash
psql "$TEST_DATABASE_URL" -tAc \
  "SELECT COUNT(*) FROM devices WHERE name LIKE 'METRIC-RETENTION-PG-%';"
```

预期为 `0`。

### 18.4 备份应用测试数据库

以下操作只允许在测试环境数据库 `nas` 执行：

```bash
mkdir -p ~/nas-test-results
BACKUP_FILE=~/nas-test-results/nas-before-step1.4-$(date +%Y%m%d-%H%M%S).dump
sudo -u postgres pg_dump -Fc nas > "$BACKUP_FILE"
test -s "$BACKUP_FILE"
ls -lh "$BACKUP_FILE"
```

备份为空时停止，不得执行迁移或清理。

### 18.5 执行 retention 索引迁移

```bash
.venv/bin/python -m alembic heads
.venv/bin/python -m alembic current
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
```

预期迁移：

```text
b8c9d0e1f2a3 -> d0e1f2a3b4c5
```

检查索引：

```bash
sudo -u postgres psql -d nas -tAc \
  "SELECT indexname || ' | ' || indexdef
     FROM pg_indexes
    WHERE tablename IN ('device_metric_samples', 'interface_traffic_samples')
      AND indexname IN ('idx_device_metric_ts', 'ix_interface_traffic_samples_ts')
    ORDER BY indexname;"
```

必须同时存在：

```text
idx_device_metric_ts
ix_interface_traffic_samples_ts
```

若接口时间索引不存在，停止清理，不得用全表扫描继续测试。

### 18.6 验证 PostgreSQL 清理查询计划

测试库数据量较小时 PostgreSQL 可能合理选择顺序扫描，因此只在本会话关闭顺序扫描，
用于证明两个索引可以支撑生产 cutoff 查询：

```bash
sudo -u postgres psql -d nas <<'SQL'
BEGIN;
SET LOCAL enable_seqscan = off;
EXPLAIN (COSTS OFF)
SELECT id
  FROM device_metric_samples
 WHERE ts < NOW() - INTERVAL '90 days'
 ORDER BY ts, id
 LIMIT 5000;

EXPLAIN (COSTS OFF)
SELECT id
  FROM interface_traffic_samples
 WHERE ts < NOW() - INTERVAL '90 days'
 ORDER BY ts, id
 LIMIT 5000;
ROLLBACK;
SQL
```

第一份计划必须包含 `idx_device_metric_ts`，第二份必须包含
`ix_interface_traffic_samples_ts`。允许出现 `Incremental Sort`。

### 18.7 记录当前容量与 90 天预测

```bash
sudo -u postgres psql -d nas <<'SQL'
SELECT
  (SELECT COUNT(*) FROM devices WHERE snmp_enabled IS TRUE) AS snmp_devices,
  (SELECT COUNT(*) FROM device_interfaces WHERE monitored IS TRUE) AS monitored_interfaces,
  (SELECT COUNT(*) FROM device_metric_samples) AS device_fact_rows,
  (SELECT COUNT(*) FROM interface_traffic_samples) AS interface_sample_rows,
  (SELECT pg_size_pretty(pg_total_relation_size('device_metric_samples'))) AS device_fact_size,
  (SELECT pg_size_pretty(pg_total_relation_size('interface_traffic_samples'))) AS interface_sample_size;

SELECT
  (SELECT COUNT(*) FROM devices WHERE snmp_enabled IS TRUE) * 25920
    AS projected_device_fact_rows_90d,
  (SELECT COUNT(*) FROM device_interfaces WHERE monitored IS TRUE) * 129600
    AS projected_interface_sample_rows_90d;
SQL
```

预测公式：

- 每台 SNMP 设备：`90 × 24 × 12 = 25,920` 条设备事实
- 每个 monitored 接口：`90 × 24 × 60 = 129,600` 条流量样本

将实际数量、表大小和预测行数写入报告。若接口预测超过 5000 万行，记录为生产上线前
必须增加降采样/分区的容量风险，但不阻塞业务模块在测试环境继续开发。

### 18.8 验证 5 分钟事实节流

重启会清空进程内节流状态，因此第一次轮询应写事实；约一分钟后的第二次轮询仍刷新
接口，但设备事实数应为 `0`：

```bash
CHECK_STARTED=$(date --iso-8601=seconds)
sudo systemctl restart nas-backend
sudo systemctl is-active --quiet nas-backend
curl -fsS http://127.0.0.1:8000/health
sleep 75
journalctl -u nas-backend --since "$CHECK_STARTED" --no-pager -o cat | \
  grep "Prometheus poll:"
```

至少看到两条轮询日志。通过标准：

- 第一条包含大于 `0` 的 `metric facts`
- 下一分钟轮询包含 `0 metric facts`
- 两条日志的接口数量均正常，说明只节流事实落库，没有停止接口刷新

### 18.9 执行一次真实保留清理

先记录 90 天前数据量：

```bash
sudo -u postgres psql -d nas -c \
  "SELECT
     (SELECT COUNT(*) FROM device_metric_samples
       WHERE ts < NOW() - INTERVAL '90 days') AS expired_device_facts,
     (SELECT COUNT(*) FROM interface_traffic_samples
       WHERE ts < NOW() - INTERVAL '90 days') AS expired_interface_samples;"
```

确认 18.4 备份有效后执行应用清理入口：

```bash
.venv/bin/python - <<'PY'
from app.services.prometheus_connector import PrometheusConnector

connector = PrometheusConnector()
try:
  print(connector.cleanup_old_metric_samples())
finally:
  connector._http.close()
PY
```

再次查询 90 天前数据量，两项都必须为 `0`。日志中的删除数量应与执行前统计一致；
如果执行前为 `0`，返回零删除是正常结果。

### 18.10 检查服务、调度和错误日志

```bash
.venv/bin/python -m alembic current
sudo systemctl --no-pager --full status nas-backend
curl -fsS http://127.0.0.1:8000/health
journalctl -u nas-backend --since "$CHECK_STARTED" --no-pager | \
  grep -E "Prometheus poll:|Metric retention cleanup:|Metric fact persist failed|Poll cycle failed"
```

通过标准：

- Alembic 当前版本为 `d0e1f2a3b4c5`
- 后端为 `active (running)`，健康检查成功
- 没有持续 `Metric fact persist failed` 或 `Poll cycle failed`
- 原 CPU、uptime、接口聚合样本继续生成

### 18.11 Step 1.4 通过标准

必须同时满足：

- 本地逻辑测试 `14 passed`
- 真实 PostgreSQL 保留语义测试 `1 passed`，临时数据为 `0`
- 迁移版本为 `d0e1f2a3b4c5`，两个时间索引存在且执行计划可使用
- 第一分钟写设备事实、下一分钟事实为 `0`，接口刷新未停止
- 真实清理后 90 天前记录为 `0`
- 容量预测已记录，超过 5000 万行时已登记生产容量风险
- 后端健康，CPU、uptime、接口聚合无回归

将提交号、测试数量、迁移版本、执行计划索引名、轮询日志、清理前后数量、容量预测和
服务状态追加到测试报告；不要记录 SNMP community、数据库密码或其他凭据。

---

## 19. AOP 年度计划：迁移、并发排程与前端门禁

### 19.1 验证目标

本节验证计划性运维从周期模板扩展为年度 AOP 后的关键边界：

1. 旧 `maintenance_plans` 数据和 API 保持可用。
2. AOP 项目、维护窗口和任务关联结构正确迁移到 PostgreSQL。
3. 两个独立连接同时生成同一 AOP 时只创建一条任务，后到请求复用该任务。
4. AOP API 可由真实后端访问，Vue 生产构建成功。
5. 迁移和后端重启不影响 Step 1.4 指标采集与保留策略。

### 19.2 拉取代码并运行聚焦回归

```bash
cd /home/vayne/network-automation-system
git status --short
git pull --ff-only origin main
git rev-parse --short HEAD

env -u TEST_DATABASE_URL .venv/bin/python -m pytest -q tests/test_aop_planning.py
.venv/bin/python -m alembic heads
```

拉取前工作区必须干净。预期聚焦测试为 `11 passed`，唯一 Alembic head 为：

```text
f2a3b4c5d6e7 (head)
```

### 19.3 备份应用测试数据库

以下操作只允许在测试环境数据库 `nas` 执行：

```bash
mkdir -p ~/nas-test-results
BACKUP_FILE=~/nas-test-results/nas-before-aop-$(date +%Y%m%d-%H%M%S).dump
sudo -u postgres pg_dump -Fc nas > "$BACKUP_FILE"
test -s "$BACKUP_FILE"
ls -lh "$BACKUP_FILE"
```

备份为空时停止。不得跳过备份直接迁移，也不得把备份提交到 Git。

### 19.4 执行并检查 AOP 迁移

```bash
.venv/bin/python -m alembic current
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
```

预期迁移：

```text
d0e1f2a3b4c5 -> e1f2a3b4c5d6
e1f2a3b4c5d6 -> f2a3b4c5d6e7
```

`f2a3b4c5d6e7` 向 `aop_projects` 增加执行结果列 `actual_hours`、`actual_cost`、
`completion_result`、`completion_notes`、`completed_at`，用于完工后回填实际工时/成本。

检查表、任务列、唯一索引和外键：

```bash
sudo -u postgres psql -d nas <<'SQL'
SELECT table_name
  FROM information_schema.tables
 WHERE table_schema = 'public'
   AND table_name IN ('aop_programs', 'aop_projects', 'aop_maintenance_windows')
 ORDER BY table_name;

SELECT column_name
  FROM information_schema.columns
 WHERE table_schema = 'public'
   AND table_name = 'maintenance_tasks'
   AND column_name IN (
     'aop_project_id', 'maintenance_window_id', 'scheduled_end',
     'estimated_hours', 'schedule_source'
   )
 ORDER BY column_name;

SELECT indexname
  FROM pg_indexes
 WHERE tablename = 'maintenance_tasks'
   AND indexname IN (
     'ix_maintenance_tasks_aop_project_id',
     'ix_maintenance_tasks_maintenance_window_id',
     'ix_maintenance_tasks_schedule_source'
   )
 ORDER BY indexname;

SELECT conname
  FROM pg_constraint
 WHERE conname IN (
   'fk_maintenance_task_aop_project',
   'fk_maintenance_task_aop_window',
   'uq_aop_program_year_version',
   'uq_aop_project_program_code'
 )
 ORDER BY conname;
SQL
```

必须看到 3 张表、5 个任务列、3 个任务索引和 4 个命名约束。任何一组缺失都应停止
后续排程测试并保留日志，不要手工补列或补索引。

### 19.5 在隔离数据库验证并发幂等

继续使用第 7 节的 `PGPASSFILE` 和 `TEST_DATABASE_URL`。先确认目标数据库，输出必须是
`nas_concurrency_test`：

```bash
psql "$TEST_DATABASE_URL" -tAc "SELECT current_database(), current_user;"
DATABASE_URL="$TEST_DATABASE_URL" .venv/bin/python -m alembic upgrade head
DATABASE_URL="$TEST_DATABASE_URL" .venv/bin/python -m alembic current
.venv/bin/python -m pytest -q tests/test_postgresql_aop_planning.py
```

预期迁移版本为 `e1f2a3b4c5d6`，测试为：

```text
1 passed
```

该测试使用两个独立 SQLAlchemy Session 同时调用真实生成入口。通过标准是一方返回一个
`generated_task_id`，另一方返回同一个 `existing_task_id`，数据库最终只有一条任务。
测试结束后检查临时数据：

```bash
psql "$TEST_DATABASE_URL" -tAc \
  "SELECT COUNT(*) FROM aop_programs WHERE name LIKE 'AOP-PG-%';"
```

预期为 `0`。非零表示测试清理失败，必须先清理隔离库，不能删除业务库中的同名数据。

### 19.6 AOP API 冒烟测试

重启后端并检查只读 AOP 列表接口：

```bash
CHECK_STARTED=$(date --iso-8601=seconds)
sudo systemctl restart nas-backend
sudo systemctl is-active --quiet nas-backend
curl -fsS http://127.0.0.1:8000/health
curl -fsS "http://127.0.0.1:8000/api/planned-maintenance/aop/programs?year=2099" | \
  .venv/bin/python -m json.tool
```

接口必须返回 JSON 且无 `500`。这里只执行只读请求，不在业务测试库创建占位 AOP。

维护窗口批量导入（节假日/停产日历）和成本汇总仅需以聚焦测试
`test_batch_window_import_creates_all_windows` 和 `test_aop_completion_rolls_up_execution_results`
为准（已含在 19.2 的 `11 passed` 中），Vue 端在 19.7 构建中一并验证。

### 19.7 Vue 生产构建

本地 Windows 环境的 npm 镜像证书无法可靠安装依赖，因此以测试机生产构建为准：

```bash
node --version
npm --version
npm --prefix frontend ci
npm --prefix frontend run build
test -f frontend/dist/index.html
```

不得使用 `strict-ssl=false`、`NODE_TLS_REJECT_UNAUTHORIZED=0` 或其他方式关闭 TLS 校验。
若 `npm ci` 因测试机证书链失败，记录完整错误并修复系统/企业 CA，不得把它记为 Vue
代码缺陷；依赖可用后必须重新执行构建。

### 19.8 服务与旧功能回归

```bash
.venv/bin/python -m alembic current
curl -fsS "http://127.0.0.1:8000/api/planned-maintenance/plans?limit=1"
curl -fsS "http://127.0.0.1:8000/api/planned-maintenance/tasks?limit=1"
curl -fsS http://127.0.0.1:8000/health
sudo systemctl --no-pager --full status nas-backend
journalctl -u nas-backend --since "$CHECK_STARTED" --no-pager | \
  grep -E "Traceback|IntegrityError|AOP|Prometheus poll:|Metric retention cleanup:"
```

旧接口若需要认证，应使用测试账号按现有登录流程获取凭据，不要把 token 写入手册、报告
或 shell 脚本。后端必须保持 `active (running)`，且日志中不得有持续数据库、排程或指标
轮询错误。

### 19.9 AOP 通过标准

必须同时满足：

- AOP 聚焦测试 `11 passed`，覆盖反序依赖、峰值并行容量、窗口时区、已排程写保护、执行结果回填和窗口批量导入
- 应用数据库和隔离数据库均为 `f2a3b4c5d6e7`
- 3 张 AOP 表、5 个任务列、3 个任务索引和 4 个命名约束齐全
- `aop_projects` 含 `actual_hours`、`actual_cost`、`completion_result`、`completion_notes`、`completed_at` 五个执行结果列
- PostgreSQL 并发测试 `1 passed`，`AOP-PG-` 临时数据为 `0`
- AOP 只读 API 返回有效 JSON，旧计划和任务接口无回归
- `npm --prefix frontend run build` 成功并生成 `frontend/dist/index.html`
- 后端健康，Step 1.4 指标轮询与保留日志无持续错误

将提交号、测试数量、两个数据库的迁移版本、结构检查结果、并发结果、API 状态、前端
构建结果和服务状态追加到测试报告；不要记录数据库密码、认证 token 或其他凭据。
