# SQLite → PostgreSQL 迁移记录

> 执行日期：2026-06-10
> 目标环境：Ubuntu VM（hostname `k8s-worker`，IP `192.168.4.37`，部署路径 `/home/vayne/network-automation-system`）
> 结果：✅ 成功，38 张表全部迁移，行数逐表核对一致，后端已在 PostgreSQL 上稳定运行。

---

## 1. 背景与动机

项目原使用 SQLite（`data/nas.db`）作为数据库。为支撑生产环境的并发访问、连接池、MVCC 以及后续向量检索能力（pgvector），将数据库迁移到 **PostgreSQL 17.6**。

代码层早已支持双数据库：[app/shared/database.py](../app/shared/database.py) 中的 `DatabaseManager` 通过 URL 前缀自动切换 SQLite（`StaticPool` + WAL）/ PostgreSQL（`QueuePool` 连接池）。本次迁移**无需改动业务代码**，仅迁移数据 + 切换配置。

---

## 2. 迁移前环境事实

| 项目 | 值 |
|---|---|
| 部署方式 | 裸机（非 Docker），无 systemd/tmux，原后端为孤儿进程 |
| Python 运行时 | 项目 `.venv`（`/home/vayne/network-automation-system/.venv`），已含 `psycopg2 2.9.12`、`asyncpg 0.31.0`、`pgvector`、`fastapi`、`sqlalchemy 2.0.25` |
| 系统 Python | `python3.12` 缺驱动且受 PEP 668 限制 → **本次全程使用 `.venv`，不动系统 Python** |
| PostgreSQL | 17.6（pgdg），运行于 `127.0.0.1:5432`，`scram-sha-256` 认证 |
| 配置加载 | 应用读取**工作目录下的 `config.yaml`**（非 `DATABASE_URL` 环境变量） |
| 数据规模 | 小型，38 张表，数百行级别（迁移耗时秒级） |
| ORM 类型 | 全部为 `String/Text/Integer/DateTime/Boolean/DECIMAL` 等原始类型，**无 SQLAlchemy Enum、无 JSON 列类型、无 Vector 列**（[app/shared/models.py](../app/shared/models.py) L1052 `Vector` 列已注释），因此 `create_all` 不依赖 pgvector |

---

## 3. 执行步骤

### 阶段 1：驱动与扩展
- `.venv` 已自带全部 PG 驱动，无需安装。
- 安装 `pgvector` apt 包（0.8.2），在 `nas` 库中 `CREATE EXTENSION vector`（为后续向量能力预留，当前 ORM 未使用）。

### 阶段 2：创建 PG 库 / 角色 / 授权
1. **双重备份 SQLite**：`data/nas.db.bak_*` 与 `data/nas.db.safebak_*`（均经 `sqlite .backup` 校验）。
2. 生成 **24 位纯字母数字随机密码**，写入 `/home/vayne/.nas_pg_pw`（`chmod 600`，全程不经过日志/聊天）。
3. 创建角色 `nasuser`（普通登录角色）、数据库 `nas`（owner=`nasuser`）。
4. `CREATE EXTENSION vector` + `GRANT ALL ON SCHEMA public TO nasuser`。
5. **`pg_hba.conf`**：追加 `host nas nasuser 127.0.0.1/32 scram-sha-256` 与 `::1/128` 规则，备份原文件后 `pg_reload_conf()`。
6. **连接容量**：原 `max_connections=20` 被 Zabbix 的 17 个常驻连接占满，导致 `nasuser` 无可用槽。
   - 应用户决定：**停用 `zabbix-server.service`** 释放连接。
   - `max_connections` 20 → **100**（备份 `postgresql.conf` 后修改并重启 `postgresql@17-main`）。
   - ⚠️ **Zabbix 当前为停用状态**。如需恢复：`sudo systemctl start zabbix-server`（容量已扩，不会再抢槽）。

### 阶段 3：停后端 → 建表 → 迁数据 → 改配置
1. **停后端**：原孤儿 worker（持有 port 8000 与 `nas.db` fd）以 SIGTERM→SIGKILL 停止，释放端口与文件锁。
2. **建表**：用项目 ORM 的 `Base.metadata.create_all()` 在 PG 建表，**保证 schema 与代码完全一致**。
3. **迁数据**：[scripts/_migrate_sqlite_to_pg.py](../scripts/_migrate_sqlite_to_pg.py) 用同一份 `Base.metadata` 读 SQLite、写 PG，`DateTime/Boolean/DECIMAL` 等类型由 SQLAlchemy 自动转换；按 `sorted_tables` 顺序迁移；结束后 `setval` 重置所有自增序列。
4. **切换配置**：[config.yaml](../config.yaml) 的 `database` 段由 SQLite 改为 PostgreSQL（密码从 `~/.nas_pg_pw` 注入），并将连接池调小（`pool_size=5`、`max_overflow=10`）以对共享 PG 友好。原配置备份为 `config.yaml.sqlitebak_*`。

### 阶段 4：启动后端 + 验证
- 启动：`.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`（日志写 `~/nas-backend.log`）。
- 验证：
  - 启动日志 `数据库引擎初始化完成: PostgreSQL`
  - `/health` → `{"status":"healthy"}`，`/docs` → 200
  - `内置规则/默认模板/默认角色 已存在，跳过初始化` → 证明读取的是迁移过来的真实数据
  - `/api/devices` → `total:6` 真实数据；`/api/floor-plans` → 2
  - **行数逐表核对：38 张表全部 SQLite == PG**

---

## 4. 迁移过程中解决的 3 个技术障碍

| # | 问题 | 解决方案 |
|---|---|---|
| 1 | **连接槽耗尽**：`max_connections=20` 被 Zabbix 17 个常驻连接占满，`nasuser` 拿不到槽 | 停用 `zabbix-server` + `max_connections` 调到 100 + 重启 PG |
| 2 | **循环外键**：`fault_records ↔ maintenance_records` 互相引用，`sorted_tables` 无法拓扑排序，按错误顺序插入触发 `ForeignKeyViolation` | 复制期间设 `session_replication_role = 'replica'` 跳过 FK 触发器检查（pg_dump 同款做法）。需 superuser 会话：**临时授予 `nasuser` SUPERUSER，迁移完立即 `NOSUPERUSER` 撤销**（当前 `rolsuper=f`） |
| 3 | **VARCHAR 超长**：SQLite 不强制 `VARCHAR(n)` 长度，`maintenance_events.event_type` 实际存了 22 字符但 ORM 声明 `VARCHAR(20)`，PG 强制长度触发 `StringDataRightTruncation` | 迁移前增加预处理：扫描所有 `String(n)` 列，凡 SQLite 实际最大长度超过声明长度的，`ALTER COLUMN ... TYPE VARCHAR(实际长度)` 加宽（不丢数据） |

---

## 5. 最终配置变更

[config.yaml](../config.yaml) `database` 段（密码以 `***` 脱敏）：

```yaml
database:
  # PostgreSQL 配置（生产环境）— 已从 SQLite 迁移
  type: postgresql
  url: "postgresql+asyncpg://nasuser:***@127.0.0.1:5432/nas"
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
  pool_recycle: 1800
  # SQLite 配置（开发环境，保留备查 / 回滚用）
  # type: sqlite
  # sqlite_path: "./data/nas.db"
  # url: "sqlite+aiosqlite:///./data/nas.db"
  echo: false
```

> 说明：启动横幅日志中的 `数据库路径：./data/nas.db` 是 [app/main.py](../app/main.py) 中写死的文案，**不影响实际引擎**（实际已是 PostgreSQL，以 `数据库引擎初始化完成: PostgreSQL` 为准）。

---

## 6. 安全要点

- PG 密码 24 位随机，存于 VM 上 `~/.nas_pg_pw`（`chmod 600`），**从未在日志/聊天/命令行明文出现**，连接串中亦不入版本库（`config.yaml` 已 gitignore）。
- `nasuser` 迁移后为**普通登录角色**（`rolsuper=f, rolcreatedb=f, rolcanlogin=t`），临时 SUPERUSER 已撤销。
- 应用连接池上限 `5+10=15`，远低于 `max_connections=100`，不会压垮共享 PG。
- 密码为纯字母数字，URL 安全，连接串无需百分号编码。

---

## 7. 回滚方案

若需回退到 SQLite：

1. 还原配置：
   ```bash
   cd /home/vayne/network-automation-system
   cp config.yaml.sqlitebak_<时间戳> config.yaml
   ```
2. 重启后端：
   ```bash
   pkill -f 'uvicorn app.main:app'
   nohup .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > ~/nas-backend.log 2>&1 &
   ```
3. 原始数据完好：`data/nas.db` 及两份备份 `data/nas.db.bak_*`、`data/nas.db.safebak_*` 均未被改动。

保留的回滚资产清单：

| 资产 | 路径 |
|---|---|
| 原 SQLite 配置 | `config.yaml.sqlitebak_*` |
| 原 SQLite 数据库 | `data/nas.db` + `data/nas.db.bak_*` + `data/nas.db.safebak_*` |
| 原 PG 配置 | `/etc/postgresql/17/main/postgresql.conf.bak_*` |
| 原 pg_hba | `/etc/postgresql/17/main/pg_hba.conf`（已备份原文件） |
| 迁移脚本 | [scripts/_migrate_sqlite_to_pg.py](../scripts/_migrate_sqlite_to_pg.py) |

---

## 8. 启动 / 运维速查（systemd 服务化）

> ✅ **已完成**：后端已配置为 systemd 服务，实现开机自启 + 崩溃重启。

```bash
# 服务管理
sudo systemctl start nas-backend    # 启动
sudo systemctl stop nas-backend     # 停止
sudo systemctl restart nas-backend  # 重启
sudo systemctl status nas-backend   # 查看状态

# 健康检查
curl -s http://127.0.0.1:8000/health

# 查看后端日志
tail -f ~/nas-backend.log
journalctl -u nas-backend -f        # systemd 日志（实时）

# 查看 PG 连接占用
sudo -u postgres psql -tAc "SELECT usename, count(*) FROM pg_stat_activity WHERE datname='nas' GROUP BY usename;"

# 恢复 Zabbix（如需）
sudo systemctl start zabbix-server
```

### systemd 服务文件

服务文件路径：`/etc/systemd/system/nas-backend.service`

```ini
[Unit]
Description=Network Automation System Backend
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=vayne
Group=vayne
WorkingDirectory=/home/vayne/network-automation-system
Environment="PATH=/home/vayne/network-automation-system/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/vayne/network-automation-system/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=append:/home/vayne/nas-backend.log
StandardError=append:/home/vayne/nas-backend.log
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

---

## 9. 验证结果摘要（38 张表行数核对，全部一致）

部分关键表（SQLite == PG）：

| 表 | 行数 |
|---|---|
| devices | 6 |
| device_links | 2 |
| floor_plans | 2 |
| users | 2 |
| audit_logs | 196 |
| spare_parts | 12 |
| spare_part_movements | 135 |
| spare_part_instances | 56 |
| deploy_history | 43 |
| maintenance_events | 53 |
| user_sessions | 60 |
| permissions | 57 |
| role_permissions | 96 |

完整核对输出为脚本运行时的 `[VERIFY]` 段，结果为 `[DONE]`（exit 0），无任何 MISMATCH。
