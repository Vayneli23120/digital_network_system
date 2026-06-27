# UAT 测试手册：Monitor3D 智能故障闭环与指挥面板

版本：v1.0  
日期：2026-06-27  
适用分支：`main`  
关键提交范围：`6da7cf7` ~ `7faacf2`

---

## 1. 测试目标

验证 Monitor3D 从“监控展示”升级为“故障指挥与闭环处理入口”后的核心能力：

1. 监控事件可自动创建、更新、恢复 `FaultRecord`。
2. 自动故障单可去重、累计事件次数、自动指派负责人并生成处理建议。
3. 设备恢复或接口 `linkUp` 可自动把对应故障标记为 `resolved`。
4. Monitor3D 大屏可展示故障指挥面板、事件流、HUD 故障状态、根因候选、影响范围、故障链路 Top 5。
5. 管理员可在大屏执行确认、误报、转维修闭环操作。
6. 多设备离线时，大屏可显示受影响设备、共同路径/光缆段证据和疑似根因。

---

## 2. 测试范围

### 2.1 后端功能

- `app/services/incident_automation.py`
- `app/services/incident_insights.py`
- `migrations/add_incident_automation_fields.py`
- Trap `linkDown/linkUp` 自动故障处理
- Reachability `device_unreachable/device_recovered` 自动故障处理
- `GET /api/faults` 自动化字段返回
- `POST /api/faults/{fault_id}/review`
- `POST /api/faults/{fault_id}/transfer-to-maintenance`
- `GET /api/monitor3d/command-summary`
- `GET /api/monitor3d/events`
- `GET /api/floor-plans/{plan_id}/device-paths` 路径边元数据

### 2.2 前端功能

- Monitor3D 故障指挥面板
- Monitor3D 事件流
- 选中设备活跃故障卡片
- 设备 HUD 活跃故障状态
- 确认 / 误报 / 转维修按钮
- 疑似根因 Top 3
- 影响范围与受影响设备高亮
- 故障链路 Top 5
- 共同路径/共同光缆段证据显示

### 2.3 不在本轮 UAT 范围

- AI 大模型根因分析准确率评估
- 长周期告警风暴压测
- 邮件网关稳定性专项压测
- 多租户权限隔离
- 生产环境安全审计
- 真实大规模园区拓扑性能压测
- Phase 4 故障电影模式、Topology Diff、流量热力图

---

## 3. 测试环境要求

### 3.1 服务环境

- OS：Ubuntu 测试环境或等效 Linux 环境
- Python：项目当前兼容版本
- Node.js：前端构建所需版本
- 数据库：SQLite 或 PostgreSQL
- 后端：FastAPI `app.main:app`
- 前端：Vue 3 / Vite 构建产物

### 3.2 网络要求

- 后端服务器可访问测试设备管理地址。
- 设备可向后端发送 SNMP Trap UDP/162 或测试指定高端口。
- 后端 WebSocket 可被前端访问。
- 前端可访问后端 `/api`。

### 3.3 测试数据建议

至少准备：

1. 1 台核心交换机，`device_type=core_switch`。
2. 2 台接入/服务器交换机，`device_type=office_switch/server_switch`。
3. 1 条可操作测试上行口，例如 `Gi1/0/48`。
4. Monitor3D 平面图中已放置以上设备。
5. 若验证共同路径证据，需已配置光缆拓扑与设备路径，`device-paths` 可返回 `edges`。

---

## 4. 上线前准备

### 4.1 拉取最新代码

```bash
git pull origin main
git log --oneline -10
```

应至少看到：

```text
7faacf2 feat(monitor3d): infer shared topology impact paths
689b56c feat(monitor3d): surface hot incident links
ff6b9b0 feat(monitor3d): highlight impacted devices
627ac7e feat(monitor3d): add incident impact scope
8c7c05f feat(monitor3d): add root cause candidates
6da7cf7 feat(incidents): auto-create faults from monitor events
```

### 4.2 安装依赖

```bash
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
```

本地 Windows 如遇 `requirements.txt` 编码问题，可使用：

```powershell
$env:PYTHONUTF8='1'
python -m pip install -r requirements.txt
```

### 4.3 执行数据库迁移

```bash
python migrations/add_incident_automation_fields.py
```

验收点：`fault_records` 表存在以下字段：

```text
source_type
source_key
source_event
if_index
if_name
peer_device_id
peer_if_name
event_count
last_event_at
recommendation
assigned_email
review_required
reviewed_at
reviewed_by
false_positive
```

### 4.4 可选负责人环境变量

```bash
export INCIDENT_DEFAULT_OWNER="Network Admin"
export INCIDENT_DEFAULT_EMAIL="network-admin@example.com"
export INCIDENT_CORE_OWNER="Core Network Admin"
export INCIDENT_CORE_EMAIL="core-admin@example.com"
export INCIDENT_FIELD_OWNER="Field Engineer"
export INCIDENT_FIELD_EMAIL="field@example.com"
```

未设置时系统会使用内置默认负责人。

### 4.5 启动后端

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

若需要 Trap：

```bash
export SNMP_TRAP_BIND=0.0.0.0
export SNMP_TRAP_PORT=162
export SNMP_TRAP_COMMUNITY=
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

无权限绑定 162 时使用高端口：

```bash
export SNMP_TRAP_PORT=1162
```

---

## 5. 本地离线测试

测试环境未恢复时，先跑离线单元测试：

```bash
python -m pytest tests/test_incident_automation.py tests/test_monitor3d_command_summary.py -q
```

预期：

```text
13 passed
```

覆盖范围：

1. 设备离线自动建单。
2. 重复离线事件去重并累计 `event_count`。
3. 设备恢复自动标记 `resolved`。
4. 无未关闭故障时恢复事件不误建单。
5. 根因候选排序。
6. 影响范围摘要。
7. 故障链路 Top 5。
8. 共同路径/共同光缆段分析。

---

## 6. API 验证

### 6.1 查询活跃故障

```bash
curl "http://127.0.0.1:8000/api/faults?status=open,assigned,accepted,diagnosing,resolving,transferred"
```

验收点：

- 返回 `source_type/source_event/source_key`。
- 返回 `event_count/last_event_at`。
- 返回 `recommendation`。
- 返回 `review_required`。

### 6.2 查询指挥面板汇总

无平面图上下文：

```bash
curl "http://127.0.0.1:8000/api/monitor3d/command-summary"
```

带平面图上下文：

```bash
curl "http://127.0.0.1:8000/api/monitor3d/command-summary?plan_id=<plan_id>"
```

验收点：

- `p1_count`
- `p2_count`
- `unacknowledged`
- `in_progress`
- `transferred`
- `impacted_devices`
- `recent_events`
- `root_cause_candidates`
- `impact_scope`
- `hot_links`

带 `plan_id` 且存在共同路径时，`impact_scope.shared_path_edges` 应包含共同边/光缆段。

### 6.3 查询事件流

```bash
curl "http://127.0.0.1:8000/api/monitor3d/events?window=1h&limit=100"
```

可选窗口：

```text
10m
1h
24h
```

验收点：事件包括：

- `fault_created`
- `monitor_event/link_down/device_unreachable`
- `fault_reviewed`
- `maintenance_transferred`
- `fault_resolved`
- `fault_closed`

---

## 7. 测试用例

### TC-01：设备不可达自动创建故障单

步骤：

1. 选择一台测试设备。
2. 使设备管理地址不可达，或临时停止测试网络连通。
3. 等待 reachability monitor 检测状态变化。
4. 查询 `/api/faults?status=open,assigned,accepted,diagnosing,resolving,transferred`。

预期：

- 自动创建一条 `FaultRecord`。
- `source_type=reachability`。
- `source_event=device_unreachable`。
- `source_key=device:{device_id}:unreachable`。
- `incident_type=device_down`。
- `review_required=true`。
- 大屏指挥面板 `未确认` 数量增加。
- 事件流出现故障创建/设备离线事件。

### TC-02：重复设备不可达不重复建单

步骤：

1. 保持同一设备不可达。
2. 等待多次监控事件。
3. 查询该设备活跃故障。

预期：

- 不重复创建新故障单。
- 原故障 `event_count` 增加。
- `last_event_at` 更新。

### TC-03：设备恢复自动 resolved

步骤：

1. 恢复设备网络连通。
2. 等待 reachability monitor 检测恢复。
3. 查询原故障详情。

预期：

- 原故障状态变为 `resolved`。
- `resolved_at` 有值。
- `resolution` 包含恢复事件说明。
- 事件流出现 `fault_resolved`。

### TC-04：Trap linkDown 自动创建接口故障

步骤：

1. 确认设备 SNMP Trap 已配置。
2. 对测试接口执行 shutdown 或拔插测试链路。
3. 后端日志确认收到 linkDown。
4. 查询故障列表。

预期：

- 自动创建接口故障。
- `source_type=trap`。
- `source_event=link_down`。
- `source_key=device:{device_id}:if:{if_index}:link_down`。
- `if_index/if_name` 正确。
- 若接口为上行口，`incident_type=uplink_down`。
- Monitor3D “故障链路 Top 5”显示该链路。

### TC-05：Trap linkUp 自动恢复接口故障

步骤：

1. 对 TC-04 的接口执行 no shutdown 或恢复链路。
2. 后端日志确认收到 linkUp。
3. 查询原故障详情。

预期：

- 原故障状态变为 `resolved`。
- 事件流出现恢复事件。
- 大屏活跃故障数下降。

### TC-06：大屏确认故障

步骤：

1. 打开 Monitor3D。
2. 点击有活跃故障的设备。
3. 在右侧设备卡片点击“确认”。
4. 查询故障详情。

预期：

- `review_required=false`。
- `reviewed_at` 有值。
- `reviewed_by=Monitor3D`。
- 指挥面板未确认数量减少。

### TC-07：大屏标记误报

步骤：

1. 点击有活跃故障的设备。
2. 点击“误报”。
3. 查询故障详情。

预期：

- `false_positive=true`。
- `status=closed`。
- `closed_at` 有值。
- 活跃故障列表不再显示该故障。

### TC-08：大屏转维修

步骤：

1. 点击有活跃故障的设备。
2. 点击“转维修”。
3. 查询故障详情和维修单。

预期：

- 故障状态变为 `transferred`。
- `maintenance_id` 有值。
- 生成 `MaintenanceRecord`。
- 指挥面板 `转维修` 数量增加。

### TC-09：指挥面板完整展示

步骤：

1. 打开 Monitor3D。
2. 确认右侧“故障指挥”面板。

预期展示：

- P1 数量。
- P2 数量。
- 未确认数量。
- 处理中数量。
- 转维修数量。
- 影响设备数量。
- 最近活跃故障。
- 疑似根因 Top 3。
- 影响范围。
- 故障链路 Top 5。
- 事件流。

### TC-10：设备 HUD 显示故障状态

步骤：

1. 鼠标悬浮有活跃故障的设备。
2. 查看 HUD。

预期：

- 显示故障单号。
- 显示严重级别。
- 显示状态。
- 显示负责人。
- 显示建议摘要。

### TC-11：影响范围与受影响设备高亮

步骤：

1. 制造多个设备离线或多个活跃故障。
2. 打开 Monitor3D。
3. 查看“影响范围”和场景设备光晕。

预期：

- `impact_scope.level` 合理。
- `impact_scope.summary` 描述受影响数量。
- 受影响但未离线设备显示琥珀色光晕。
- 离线设备显示红色光晕。
- 点击影响设备可聚焦。

### TC-12：共同路径/共同光缆段证据

前置条件：

- 平面图已配置拓扑端口和光缆边。
- `/api/floor-plans/{plan_id}/device-paths` 返回每台设备路径和 `edges`。
- 多个故障设备路径经过同一条 `TopoEdge`。

步骤：

1. 让多个路径相关设备同时离线。
2. 调用：

```bash
curl "http://127.0.0.1:8000/api/monitor3d/command-summary?plan_id=<plan_id>"
```

3. 查看 Monitor3D 影响范围面板。

预期：

- `impact_scope.shared_path_edges` 非空。
- 显示共同 `cable_name` 或 `Edge-{id}`。
- 根因候选包含 “共同路径 ... 疑似上游链路异常”。
- 影响范围摘要包含共同光缆/边名称。

---

## 8. 验收标准

本轮 UAT 通过条件：

1. 数据库迁移成功，后端启动无新增字段错误。
2. 离线单元测试通过。
3. 设备不可达可自动创建故障单。
4. 重复事件不重复建单。
5. 恢复事件可自动 resolved。
6. Trap linkDown/linkUp 可创建/恢复接口故障。
7. Monitor3D 指挥面板数据正确刷新。
8. HUD 能显示活跃故障信息。
9. 确认/误报/转维修动作可完成。
10. 根因候选、影响范围、故障链路 Top 5 可展示。
11. 带 `plan_id` 时共同路径/共同光缆段证据可展示。

---

## 9. 常见问题排查

### 9.1 自动建单时报数据库缺列

原因：未执行迁移。

处理：

```bash
python migrations/add_incident_automation_fields.py
```

### 9.2 大屏没有活跃故障

检查：

```bash
curl "http://127.0.0.1:8000/api/faults?status=open,assigned,accepted,diagnosing,resolving,transferred"
```

若为空，说明当前没有活跃 FaultRecord，需先触发设备离线或 linkDown。

### 9.3 指挥面板没有共同路径证据

检查：

1. 前端是否传了 `plan_id`。
2. 后端接口是否使用 `/api/monitor3d/command-summary?plan_id=<plan_id>`。
3. `device-paths` 是否返回 `edges`。
4. 多个故障设备路径是否真的经过同一 `edge_id`。

### 9.4 Trap 收不到

检查：

- 设备 Trap 目标 IP 是否为后端服务器。
- Trap 端口是否与 `SNMP_TRAP_PORT` 一致。
- 防火墙是否放行 UDP/162 或测试端口。
- Trap 源 IP 是否能匹配系统内 `Device.ip`。

### 9.5 转维修失败

检查故障状态是否为：

```text
assigned / accepted / diagnosing
```

其他状态不允许转维修。

### 9.6 前端没有受影响设备光晕

检查：

1. `command-summary` 是否返回 `impact_scope.impacted_devices`。
2. 设备是否已放置在当前平面图节点中。
3. 离线设备会显示红色光晕，受影响但未离线设备显示琥珀色光晕。

---

## 10. UAT 记录模板

| 用例 | 结果 | 备注 |
|---|---|---|
| TC-01 设备不可达自动建单 | 通过 / 失败 |  |
| TC-02 重复事件去重 | 通过 / 失败 |  |
| TC-03 设备恢复 resolved | 通过 / 失败 |  |
| TC-04 Trap linkDown 建单 | 通过 / 失败 |  |
| TC-05 Trap linkUp 恢复 | 通过 / 失败 |  |
| TC-06 大屏确认 | 通过 / 失败 |  |
| TC-07 大屏误报 | 通过 / 失败 |  |
| TC-08 大屏转维修 | 通过 / 失败 |  |
| TC-09 指挥面板展示 | 通过 / 失败 |  |
| TC-10 HUD 故障状态 | 通过 / 失败 |  |
| TC-11 影响范围高亮 | 通过 / 失败 |  |
| TC-12 共同路径证据 | 通过 / 失败 |  |

---

## 11. UAT 结论

```text
测试环境：
测试日期：
测试人员：
后端版本：
前端版本：
数据库：

结论：通过 / 有条件通过 / 不通过

遗留问题：
1.
2.
3.

下一步：
```
