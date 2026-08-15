# Docker 全栈部署指南

将 Network Automation System 全栈（Postgres + Redis + 后端 + Celery worker/beat +
Vue 前端 + Prometheus + snmp_exporter + Grafana）用 Docker Compose 一键编排。

> 旧的「物理机后端 + Docker 采集器」混合模式见仓库根目录 `Makefile`；
> 本指南面向纯 Docker 部署（本地 Docker Desktop / Linux 服务器通用）。

## 一、前置条件

- Docker Engine 20.10+，Compose v2（`docker compose version`）
- 从仓库根目录执行所有命令

## 二、本地启动

```bash
# 1. 生成环境变量（含密码/密钥，.env 已被 gitignore）
cp .env.docker.example .env

# 2. 修改 .env：至少设置 DB_PASSWORD / JWT_SECRET / ADMIN_PASSWORD
#    JWT_SECRET 生成：python -c "import secrets; print(secrets.token_hex(32))"

# 3. 构建并启动全部服务（首次会执行迁移 + 创建初始管理员）
docker compose up -d --build

# 4. 查看状态
docker compose ps
docker compose logs -f backend
```

首次启动流程：`migrate` 服务会依次执行 `alembic upgrade head` →
初始化默认角色/配置模板 → 创建初始管理员（`ADMIN_USERNAME` / `ADMIN_PASSWORD`），
完成后 backend / worker / beat 才启动。

## 三、访问地址（默认端口）

| 服务 | 地址 |
| --- | --- |
| 前端（Vue，nginx） | http://localhost:3000 |
| 后端 API / Swagger | http://localhost:8000 / http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| snmp_exporter | http://localhost:9116 |
| Grafana | http://localhost:3001（匿名只读） |

初始管理员登录：用户名/密码见 `.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`。

## 四、常用命令

```bash
docker compose ps                       # 状态
docker compose logs -f <service>        # 日志（backend/worker/beat/frontend/...）
docker compose down                     # 停止（保留数据卷）
docker compose down -v                  # 停止并删除数据卷（重置数据库）
# 重新导入演示数据（会清空现有数据）
docker compose exec backend sh -c 'NAS_SEED_CONFIRM=1 python scripts/seed_data.py'
```

## 五、服务器部署注意事项

在服务器上跑之前，逐项核对：

1. **file_sd 目标文件写权限**：后端以 `appuser`（uid 1000）运行，会写入
   `./docker/prometheus/targets/snmp_devices.yml`。Linux 上需保证该目录对 uid 1000 可写：
   ```bash
   chown -R 1000:1000 docker/prometheus/targets
   ```

2. **SNMP community**：`docker/snmp_exporter/snmp.yml` 中的 `gyread` / `public` 必须与
   交换机侧一致，否则采集不到指标。

3. **SNMP Trap**：`.env` 中 `SNMP_TRAP_COMMUNITY` 留空 = fail-closed（拒绝所有 Trap）。
   要接收秒级 linkDown/linkUp，需设为与设备 trap community 一致，并确保
   服务器防火墙放行 `162/udp`（compose 已映射到后端容器）。

4. **域名/IP 替换**：
   - `.env` 的 `CORS_ALLOWED_ORIGINS` → 实际前端访问地址
   - `docker-compose.yml` 中 grafana 的 `GF_SERVER_ROOT_URL` → 服务器地址

5. **密钥**：生产必须设置强 `JWT_SECRET`（≥32 位）、`DB_PASSWORD`、`REDIS_PASSWORD`、
   `ADMIN_PASSWORD`，并妥善保管 `.env`。

6. **端口**：3000（前端）、8000（API）、162/udp（SNMP Trap）、9090（Prometheus）、
   3001（Grafana）按需在防火墙放行或通过反向代理收敛。

## 六、可选：把监控面板嵌入系统

Grafana 默认匿名只读、允许 iframe 嵌入。后端提供 `/grafana` 反向代理（在
「系统设置」里配置 `grafana_url` 指向 Grafana 地址即可在系统内嵌展示）。
