# UAT 测试手册：SNMP 接口监控、Trap 告警、HUD、流量趋势、CDP/LLDP 拓扑

版本：v1.0  
日期：2026-06-26  
适用分支：`main`  
关键提交范围：`20623cc` ~ `9bbef73`

---

## 1. 测试目标

验证本轮网络监控增强功能在测试环境中是否达到可验收状态：

1. 设备 SNMP 配置可保存，接口可通过 SNMP 自动发现。
2. 上行口可被监控，接口状态、流量、错误计数可周期采集并落库。
3. 大屏 HUD 可显示真实 SNMP 上行状态、流量和趋势。
4. SNMP Trap `linkDown/linkUp` 可秒级接收并驱动前端告警、自动聚焦和 HUD 弹出。
5. CDP/LLDP 可自动发现邻居，自动推断上行口，并把邻居关系合并进原有数据链路体系。
6. 数据链路线仍然遵循光缆拓扑 Dijkstra 最短路径，不出现单独的邻居直连线图层。

---

## 2. 测试范围

### 2.1 后端功能

- SNMP 设备配置 API
- 接口发现 API
- 接口列表、接口更新、流量样本 API
- 接口轮询后台任务
- SNMP Trap UDP 接收器
- Trap 诊断 API
- CDP/LLDP 邻居发现 API
- 批量邻居发现 API
- 数据链路路径计算 API（含 `neighbor_paths`）

### 2.2 前端功能

- Monitor3D 大屏 HUD
- 上行口状态展示
- 上行口实时流量展示
- 上行流量趋势 sparkline
- Trap 告警后自动聚焦设备 + 自动显示 HUD
- 手动触发“邻居发现”按钮
- 统一数据链路线渲染（含 CDP/LLDP 发现的邻居路径）

### 2.3 不在本轮 UAT 范围

- 生产环境安全加固
- 多租户权限细粒度隔离
- LLDP 多厂商字段全兼容性矩阵
- 长周期容量压测
- 大规模拓扑性能测试（可作为后续专项）

---

## 3. 测试环境要求

### 3.1 服务环境

- OS：Ubuntu 测试环境
- Python：项目当前兼容版本
- Node.js：前端构建所需版本
- 数据库：当前测试环境数据库（SQLite 或 PostgreSQL 均可）
- 后端：FastAPI `app.main:app`
- 前端：Vue 3 / Vite 构建产物

### 3.2 网络要求

- 后端服务器可访问测试交换机 SNMP UDP/161。
- 交换机可向后端服务器发送 Trap UDP/162。
- 若后端非 root 运行且无法绑定 162，可临时使用高端口，并在设备端指定对应 Trap 端口。
- 防火墙放行：
  - 后端出站到设备：UDP/161
  - 设备入站到后端：UDP/162 或测试指定端口
  - 前端访问后端：TCP/8000

### 3.3 测试设备建议

至少准备：

- 1 台 Cisco 接入或汇聚交换机，启用 SNMP、CDP、Trap。
- 1 台上级核心/汇聚设备，系统内存在对应 `Device` 记录，且 `Device.ip` 与 CDP/LLDP 上报的管理 IP 一致。
- 1 条可操作的测试上行口，例如 `Gi1/0/48`。

推荐测试样例：

- 设备 ID：`9`
- 端口：`Gi1/0/48`
- ifIndex：`10148`
- 端口角色：上行口

---

## 4. 上线前准备

### 4.1 拉取最新代码

```bash
git pull origin main
```

确认至少包含以下提交：

```bash
git log --oneline -10
```

应看到：

- `9bbef73 feat(topology): merge discovered neighbors into data-link paths`
- `ba9a120 feat(monitor3d): manual discover-neighbors button + redraw topology`
- `0723b13 feat(topology): CDP-based neighbor discovery + auto uplink inference`
- `d1e7cce feat(snmp): receive link up/down traps`

### 4.2 安装依赖

```bash
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
```

重点确认 Python 依赖包含：

```bash
python - <<'PY'
import puresnmp
print('puresnmp ok')
PY
```

### 4.3 执行数据库迁移

按顺序执行：

```bash
python migrations/add_snmp_interface_monitoring.py
python migrations/add_interface_neighbor_fields.py
```

验收点：

- `devices` 表存在 `snmp_enabled/snmp_version/snmp_community/snmp_port`。
- `device_interfaces` 表存在接口监控字段。
- `device_interfaces` 表存在：
  - `peer_device_id`
  - `peer_device_name`
  - `peer_ip`
  - `peer_if_name`
  - `neighbor_source`
  - `neighbor_updated_at`
- `interface_traffic_samples` 表存在。

### 4.4 后端启动环境变量

如使用默认 162 端口：

```bash
export SNMP_TRAP_BIND=0.0.0.0
export SNMP_TRAP_PORT=162
export SNMP_TRAP_COMMUNITY=
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

如无权限绑定 162，可测试高端口：

```bash
export SNMP_TRAP_PORT=1162
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 5. 设备侧配置参考

### 5.1 Cisco IOS SNMP 基础配置

示例，请按现场网段替换：

```text
conf t
snmp-server community <community> RO
snmp-server ifindex persist
snmp-server enable traps snmp linkdown linkup
snmp-server host <backend_ip> version 2c <community>
end
wr mem
```

如后端使用高端口：

```text
snmp-server host <backend_ip> version 2c <community> udp-port 1162
```

建议指定 Trap 源接口，确保 Trap 源 IP 与系统内 `Device.ip` 一致：

```text
conf t
snmp-server source-interface traps <management_or_vlan_interface>
end
wr mem
```

### 5.2 Cisco CDP

```text
conf t
cdp run
interface <test_uplink_interface>
 cdp enable
end
wr mem
```

### 5.3 LLDP 设备

不同厂商命令不同，原则是：

- 全局启用 LLDP。
- 测试接口启用 LLDP transmit/receive。
- SNMP 可 walk 标准 LLDP-MIB。

---

## 6. API 快速检查

以下命令中的 `9` 替换为实际设备 ID。

### 6.1 配置设备 SNMP

```bash
curl -X PUT http://<backend>:8000/api/devices/9/snmp \
  -H 'Content-Type: application/json' \
  -d '{"snmp_enabled":true,"snmp_version":"2c","snmp_community":"<community>","snmp_port":161}'
```

期望：

- HTTP 200
- 返回 `snmp_enabled: true`
- `snmp_community_set: true`

### 6.2 发现接口

```bash
curl -X POST http://<backend>:8000/api/devices/9/interfaces/discover
```

期望：

- HTTP 200
- `ok: true`
- `discovered > 0`
- 接口列表中存在测试端口。

### 6.3 标记上行口/监控

```bash
curl -X PUT http://<backend>:8000/api/devices/9/interfaces/10148 \
  -H 'Content-Type: application/json' \
  -d '{"is_uplink":true,"monitored":true}'
```

期望：

- HTTP 200
- `is_uplink: true`
- `monitored: true`

### 6.4 查询接口列表

```bash
curl 'http://<backend>:8000/api/devices/9/interfaces?monitored_only=true'
```

期望：

- 返回被监控接口。
- 字段包含 `last_in_bps/last_out_bps/oper_status/is_uplink`。
- 邻居发现后应包含 `peer_device_id/peer_device_name/peer_if_name/neighbor_source`。

### 6.5 查询流量样本

```bash
curl 'http://<backend>:8000/api/devices/9/interfaces/10148/traffic?limit=24'
```

期望：

- `samples` 按时间升序返回。
- 至少轮询 2 次后，样本中出现 `in_bps/out_bps`。

### 6.6 Trap 诊断

```bash
curl http://<backend>:8000/api/devices/monitor/trap-diagnostics
```

期望：

- `running: true`
- `bind` 为实际监听地址。
- 触发 Trap 后 `received` 增加。
- 成功匹配设备和端口后 `applied` 增加。

### 6.7 单设备邻居发现

```bash
curl -X POST http://<backend>:8000/api/devices/9/interfaces/discover-neighbors
```

期望：

- HTTP 200
- `ok: true`
- `found > 0`
- 若对端设备已录入且 IP/主机名匹配，`matched > 0`
- 上联到更高层级设备时，`uplinks_marked > 0` 或接口已保持 `is_uplink=true`

### 6.8 批量邻居发现

```bash
curl -X POST http://<backend>:8000/api/devices/monitor/discover-neighbors-all
```

期望：

- HTTP 200
- `devices > 0`
- `total_found >= 0`
- 每台设备返回发现结果。

### 6.9 数据链路路径（含邻居路径）

```bash
curl http://<backend>:8000/api/floor-plans/<plan_id>/device-paths
```

期望：

- 返回 `paths`：原有设备到核心的数据链路路径。
- 返回 `neighbor_paths`：CDP/LLDP 发现的邻居关系对应的光缆最短路径。
- `neighbor_paths.*.reachable=true` 时包含 `polyline`。
- `neighbor_paths.*.path_source=neighbor`。
- 不可达时返回 `reachable=false` 和 `reason`，前端不应画直线兜底。

---

## 7. 前端 UAT 用例

### TC-FE-001 大屏正常加载

步骤：

1. 打开 Monitor3D 大屏页面。
2. 选择测试楼层/平面图。
3. 等待设备、标签、光缆拓扑加载完成。

期望：

- 页面无白屏。
- 控制台无关键报错。
- 设备模型位置正确。
- 光缆拓扑可见。
- 数据链路图层可通过“显示数据链路”开关控制显隐。

### TC-FE-002 HUD 显示上行状态和流量

步骤：

1. 鼠标悬浮到测试设备。
2. 查看 HUD 内容。
3. 等待至少 2 次刷新周期。

期望：

- HUD 显示设备名、类型、IP、状态、延迟。
- HUD 显示上行状态：正常/中断/降级/无上行。
- HUD 显示上行流量：`↓ in` / `↑ out`。
- HUD 显示趋势 sparkline。
- 若无 `is_uplink=true` 接口，不显示流量趋势。

### TC-FE-003 Trap linkDown 告警联动

步骤：

1. 保持大屏打开。
2. 在测试交换机上 shutdown 测试上行口。
3. 观察大屏。

期望：

- 后端 Trap 诊断 `received/applied` 增加。
- 前端收到 WebSocket `interface_status_change`。
- 设备镜头自动聚焦。
- HUD 自动弹出约 6 秒。
- 页面出现中断告警提示。
- HUD 上行状态变为中断或降级。

### TC-FE-004 Trap linkUp 恢复联动

步骤：

1. 在测试交换机上 no shutdown 测试上行口。
2. 观察大屏。

期望：

- 前端收到恢复消息。
- 页面出现恢复提示。
- HUD 自动弹出。
- 上行状态恢复正常。

### TC-FE-005 手动邻居发现按钮

步骤：

1. 点击顶部“邻居发现”按钮。
2. 等待按钮 loading 结束。
3. 查看弹窗提示。
4. 查看数据链路图层。

期望：

- 按钮触发 `POST /api/devices/monitor/discover-neighbors-all`。
- 成功提示显示设备数、邻居数、上行口数。
- 前端随后重新拉取 `/device-paths`。
- CDP/LLDP 邻居路径显示在同一套“数据链路”图层中。
- 不存在单独“邻居拓扑”开关。
- 不出现设备 A 到设备 B 的直线兜底；路径应沿光缆拓扑 polyline。

### TC-FE-006 HUD 显示对端信息

步骤：

1. 执行邻居发现。
2. 悬浮测试设备。
3. 查看 HUD。

期望：

- HUD 出现“对端/Peer”行。
- 显示对端主机名或 IP。
- 显示对端端口名。
- 显示 `CDP` 或 `LLDP` 来源。

---

## 8. 后端 UAT 用例

### TC-BE-001 接口轮询落库

步骤：

1. 启动后端。
2. 确认接口被标记为 `monitored=true`。
3. 等待至少 2 个轮询周期。
4. 查询接口列表和流量样本。

期望：

- `device_interfaces.last_check` 更新。
- `last_in_bps/last_out_bps` 有值。
- `interface_traffic_samples` 有新增记录。
- counter wrap 不导致负速率。

### TC-BE-002 接口状态变化广播

步骤：

1. 保持 WebSocket 连接。
2. shutdown/no shutdown 测试接口。
3. 观察后端日志和前端变化。

期望：

- 后端发送 `interface_status_change`。
- 消息包含：`device_id/if_index/if_name/old_status/new_status/is_uplink/source`。
- Trap 场景下 `source=trap`。

### TC-BE-003 Trap 接收与匹配

步骤：

1. 查询 Trap 诊断初始值。
2. 触发 linkDown/linkUp。
3. 再次查询 Trap 诊断。

期望：

- `received` 增加。
- 如果 Trap 源 IP 与 `Device.ip` 匹配，`applied` 增加。
- 对应 `DeviceInterface.oper_status` 被更新。

### TC-BE-004 CDP 邻居发现

步骤：

1. 确认 Cisco 设备 CDP 开启。
2. 调用单设备邻居发现 API。
3. 查询接口列表。

期望：

- 返回邻居包含：
  - `local_if_index`
  - `remote_ip`
  - `remote_host`
  - `remote_port`
  - `remote_platform`
  - `source=cdp`
- `device_interfaces` 对应行写入：
  - `peer_ip`
  - `peer_device_name`
  - `peer_if_name`
  - `neighbor_source=cdp`
- 对端匹配成功时写入 `peer_device_id`。

### TC-BE-005 LLDP 邻居发现

步骤：

1. 准备支持 LLDP 的设备。
2. 启用 LLDP。
3. 调用邻居发现 API。
4. 查询接口列表。

期望：

- 返回 `source=lldp` 的邻居。
- 可通过本地端口名匹配到 `DeviceInterface`。
- 可通过对端主机名匹配系统内设备。

### TC-BE-006 邻居路径合并到数据链路

步骤：

1. 确认存在已匹配的 `peer_device_id`。
2. 调用 `/api/floor-plans/<plan_id>/device-paths`。
3. 查看 `neighbor_paths`。

期望：

- `neighbor_paths` 存在。
- 每条 key 格式为 `neighbor:<device_id>:<peer_device_id>`。
- 可达时：`reachable=true`，包含 `polyline`、`path_source=neighbor`、`neighbor_source=cdp/lldp`。
- 不可达时：`reachable=false`，包含 `reason`。

---

## 9. 验收标准

### 9.1 必须通过

- SNMP 接口发现可用。
- 上行口监控可用。
- 流量样本可持续写入。
- HUD 显示上行状态、流量和趋势。
- Trap linkDown/linkUp 可触发前端自动聚焦和 HUD。
- CDP 至少在 Cisco 测试设备上可发现邻居。
- 邻居发现结果可写入 peer 字段。
- 邻居关系合并到原有数据链路路径，不再单独画直线图层。
- `/device-paths` 返回 `neighbor_paths` 且前端能渲染可达路径。

### 9.2 可接受但需记录

- LLDP 某些厂商字段不完整，导致只能发现主机名或端口名。
- CDP/LLDP 能发现邻居，但因系统内 `Device.ip/name` 不一致无法匹配 `peer_device_id`。
- 光缆拓扑未建完整，导致 `neighbor_paths` 不可达。
- 流量初次采样无速率，需要第二次采样后才有 bps。

### 9.3 不可接受

- 后端启动失败。
- 数据库迁移失败。
- Trap 接收导致服务崩溃。
- 大屏白屏或关键 JS 错误。
- 邻居关系又被画成独立直线而不走光缆路径。
- 接口状态变化无法传播到前端。

---

## 10. 常见问题排查

### 10.1 Trap 后端收不到

检查：

```bash
sudo ss -lunp | grep ':162'
sudo tcpdump -ni any udp port 162
curl http://<backend>:8000/api/devices/monitor/trap-diagnostics
```

重点确认：

- 进程是否监听正确端口。
- 防火墙是否放行。
- 交换机 `snmp-server host` 端口是否正确。
- Trap 源 IP 是否等于系统内 `Device.ip`。

### 10.2 接口发现为空

检查：

- SNMP community 是否正确。
- ACL 是否允许后端访问设备 UDP/161。
- 设备是否支持 IF-MIB。
- 后端是否安装 `puresnmp`。

### 10.3 CDP 发现不到

检查：

```text
show cdp neighbors detail
show snmp mib walk 1.3.6.1.4.1.9.9.23.1.2.1.1
```

重点确认：

- `cdp run` 已开启。
- 接口 `cdp enable`。
- CDP 表中有 `cdpCacheAddress`。

### 10.4 LLDP 发现不到

检查：

- 全局 LLDP 是否开启。
- 接口 LLDP transmit/receive 是否开启。
- 设备是否通过 SNMP 暴露 LLDP-MIB。

### 10.5 邻居发现有结果但大屏不画线

检查：

1. 对端是否匹配到系统内 `Device`：接口记录是否有 `peer_device_id`。
2. 光缆拓扑是否存在两端设备的端口节点。
3. `/device-paths` 的 `neighbor_paths` 是否为 `reachable=true`。
4. 若 `reachable=false`，查看 `reason`：常见为“设备无拓扑连接”或“无连通路径”。

---

## 11. UAT 记录模板

| 用例编号 | 测试人 | 测试时间 | 结果 | 备注/缺陷编号 |
|---|---|---|---|---|
| TC-FE-001 |  |  | Pass / Fail |  |
| TC-FE-002 |  |  | Pass / Fail |  |
| TC-FE-003 |  |  | Pass / Fail |  |
| TC-FE-004 |  |  | Pass / Fail |  |
| TC-FE-005 |  |  | Pass / Fail |  |
| TC-FE-006 |  |  | Pass / Fail |  |
| TC-BE-001 |  |  | Pass / Fail |  |
| TC-BE-002 |  |  | Pass / Fail |  |
| TC-BE-003 |  |  | Pass / Fail |  |
| TC-BE-004 |  |  | Pass / Fail |  |
| TC-BE-005 |  |  | Pass / Fail |  |
| TC-BE-006 |  |  | Pass / Fail |  |

---

## 12. 测试结论模板

```text
UAT 结论：通过 / 有条件通过 / 不通过

测试环境：
后端版本：
前端版本：
数据库：
测试设备：
测试端口：

通过项：
1.
2.
3.

遗留问题：
1.
2.

上线建议：
```
