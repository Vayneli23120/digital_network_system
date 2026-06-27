# 下一阶段开发计划书：3D 监控大屏与智能故障闭环

版本：v1.0  
日期：2026-06-27  
适用项目：Network Automation System / digital_network_system  
目标阶段：下一阶段研发迭代

---

## 1. 背景与目标

当前系统已经完成一批关键监控能力：

- 3D Monitor 大屏可展示设备、光缆拓扑、数据链路线。
- 设备可达性监控已接入 WebSocket。
- SNMP 接口发现、上行口标记、接口轮询、流量样本落库已完成。
- HUD 已接入真实 SNMP 上行状态、流量和趋势图。
- SNMP Trap `linkDown/linkUp` 已可秒级接收，并触发前端自动聚焦与 HUD 弹出。
- CDP/LLDP 邻居发现已接入，可自动推断上行口、写入对端信息。
- 邻居关系已经合并进原有数据链路体系，统一沿光缆拓扑计算 Dijkstra 最短路径，不再单独画直连邻居线。
- UAT 手册已整理：`docs/UAT_SNMP_MONITORING_TOPOLOGY.md`。

下一阶段目标是把大屏从“监控展示”升级为“运维指挥与智能故障闭环平台”：

1. 告警能自动进入故障记录/工单流程。
2. 系统能自动判断故障类型、严重级别、影响范围与处理建议。
3. 系统能按规则自动指派负责人并发送邮件/系统通知。
4. 管理员收到通知后可复核、确认、转维修或关闭。
5. 3D 大屏成为故障指挥入口，而不只是状态可视化页面。
6. 数据链路、拓扑、Trap、SNMP、故障记录、维修记录、设备管理形成闭环。

---

## 2. 产品定位

下一阶段的大屏产品定位：

```text
3D 大屏 = 实时态势 + 故障发现 + 指挥入口
故障记录 FaultRecord = 告警确认、指派、诊断、处理闭环
维修记录 MaintenanceRecord = 现场维修、换件、验证、成本闭环
设备管理 Device = 单设备资产、状态、故障、维修、拓扑全生命周期视图
通知系统 Notification/Email = 负责人触达与复核入口
AI/规则引擎 = 故障分类、根因候选、处理建议与自动编排辅助
```

原则：

- 不新建孤立的“告警工单”模块。
- 复用现有 `FaultRecord` 作为 Incident / Work Order 主体。
- 复用现有 `MaintenanceRecord` 处理现场维修、换件、验证。
- 自动化先建议、再复核；重要操作不直接跳过管理员确认。
- 大屏所有“红色告警”都应能追溯到故障记录。

---

## 3. 当前基线能力

### 3.1 已完成后端能力

- SNMP 配置：`PUT /api/devices/{id}/snmp`
- 接口发现：`POST /api/devices/{id}/interfaces/discover`
- 接口列表：`GET /api/devices/{id}/interfaces`
- 接口流量：`GET /api/devices/{id}/interfaces/{if_index}/traffic`
- SNMP Trap 接收器：UDP `linkDown/linkUp`
- Trap 诊断：`GET /api/devices/monitor/trap-diagnostics`
- CDP/LLDP 邻居发现：`POST /api/devices/{id}/interfaces/discover-neighbors`
- 批量邻居发现：`POST /api/devices/monitor/discover-neighbors-all`
- 邻居链路查询：`GET /api/devices/monitor/neighbor-links`
- 数据链路路径：`GET /api/floor-plans/{plan_id}/device-paths`
- `device-paths` 已返回：
  - `paths`
  - `neighbor_paths`

### 3.2 已完成前端能力

- 3D 设备模型与光缆拓扑渲染。
- 数据链路路径统一渲染。
- HUD 显示：设备状态、延迟、上行状态、上行流量、趋势图、告警数量、对端信息。
- Trap 告警后自动聚焦设备。
- Trap 告警后自动弹出 HUD。
- 手动“邻居发现”按钮。

### 3.3 已有可复用业务模块

- 故障模块：`app/features/faults/router.py`
- 维修模块：`app/features/maintenance/router.py`
- 通知模块：`app/features/notifications/router.py`
- 邮件/企业微信/钉钉通知服务：`app/services/notification_service.py`
- AI 故障分析：`app/features/ai/router.py`
- 前端故障/维修/API：`frontend/src/api/index.js`

---

## 4. 下一阶段总体路线

建议分为 4 个阶段：

| 阶段 | 主题 | 目标 | 优先级 |
|---|---|---|---|
| Phase 1 | 告警转故障工单闭环 | 监控事件自动进入 FaultRecord，自动指派、通知、复核 | P0 |
| Phase 2 | 大屏指挥面板与故障时间线 | 大屏展示未确认故障、事件流、负责人、SLA、处理按钮 | P0 |
| Phase 3 | 影响范围与根因候选 | 基于光缆路径/上行口/Trap 时间线推断影响面和疑似根因 | P1 |
| Phase 4 | 国际化大屏亮点 | 流量热力、故障电影模式、Topology Diff、数字孪生层级视图 | P2 |

当前进度（2026-06-27）：

| 模块 | 状态 | 说明 |
|---|---|---|
| Phase 1 MVP | 已完成，待测试环境 UAT | 自动建单、去重、恢复关闭、复核、转维修、离线单元测试已完成 |
| Phase 2 指挥面板 | 已完成，待前端联调截图验证 | Command Summary、事件流、HUD 故障状态已完成 |
| Phase 3 初版洞察 | 已完成，待真实拓扑增强 | 根因候选、影响范围、受影响设备高亮、故障链路 Top 5 已完成 |
| Phase 3 拓扑推理 | 开发中 | 下一步接入 `device_paths` 共同边/共同光缆段分析 |

---

# Phase 1：告警转故障工单闭环

当前状态（2026-06-27）：MVP 代码已完成，后端静态编译与本地离线单元测试通过；测试环境离线，待环境恢复后执行真实 Trap/设备离线联调与 UAT。

已验证的离线路径：

1. `device_unreachable` 自动创建并指派 FaultRecord。
2. 重复 `device_unreachable` 不重复建单，递增 `event_count`。
3. `device_recovered` 自动将对应未关闭故障标记为 `resolved`。
4. 无未关闭故障时收到恢复事件不会创建新故障。

## 5. Phase 1 目标

实现：

```text
监控事件产生
  ↓
系统自动判断故障类型和严重级别
  ↓
自动创建或更新 FaultRecord
  ↓
自动指派负责人
  ↓
生成处理建议
  ↓
邮件 + 系统通知 + 大屏提示
  ↓
管理员复核
  ↓
确认 / 诊断 / 转维修 / 标记恢复 / 关闭
```

---

## 6. 事件来源范围

第一批接入以下事件：

1. SNMP Trap `linkDown`
2. SNMP Trap `linkUp`
3. 接口轮询发现上行口 down
4. 设备可达性变为 `unreachable`
5. CDP/LLDP 邻居关系变化
6. 数据链路路径不可达

第二批接入：

1. 接口错误包持续增长
2. 链路利用率持续超过阈值
3. 设备 CPU/内存/温度异常
4. 光功率异常

---

## 7. 新增后端服务：Incident Automation

新增文件建议：

```text
app/services/incident_automation.py
```

核心结构：

```python
class MonitorEvent(BaseModel):
    source_type: str          # trap / snmp_poll / reachability / topology / threshold
    event_type: str           # link_down / link_up / device_unreachable / neighbor_changed / path_unreachable
    device_id: int
    device_name: str | None
    ip: str | None
    if_index: int | None
    if_name: str | None
    peer_device_id: int | None
    peer_device_name: str | None
    severity_hint: str | None
    occurred_at: datetime
    raw: dict

class IncidentDecision(BaseModel):
    fault_type: str           # network / hardware / config / capacity / topology / other
    incident_type: str        # uplink_down / device_down / topology_changed / high_errors / high_utilization
    severity: str             # critical / major / warning / minor
    source_key: str           # 去重键
    title: str
    description: str
    impact: str | None
    recommendation: str
    owner: str | None
    owner_email: str | None
    should_create_maintenance: bool
    should_notify: bool
```

核心函数：

```python
def classify_event(db, event: MonitorEvent) -> IncidentDecision:
    ...

def upsert_fault_from_monitor_event(db, event: MonitorEvent) -> FaultRecord:
    ...

def assign_owner(db, decision: IncidentDecision, device: Device) -> tuple[str, str | None]:
    ...

def build_recommendation(db, event: MonitorEvent, decision: IncidentDecision) -> str:
    ...

def notify_incident(db, fault: FaultRecord, decision: IncidentDecision) -> None:
    ...
```

---

## 8. FaultRecord 字段扩展

为了支持去重、来源追踪、邮件复核与大屏展示，建议给 `fault_records` 增加字段：

```python
source_type = Column(String(30), index=True)      # trap / snmp_poll / reachability / topology / threshold / manual
source_key = Column(String(200), index=True)      # device:9:if:10148:link_down
source_event = Column(String(50), index=True)     # link_down / device_unreachable / neighbor_changed
if_index = Column(Integer)
if_name = Column(String(100))
peer_device_id = Column(Integer, nullable=True)
peer_if_name = Column(String(100))
event_count = Column(Integer, default=1)
last_event_at = Column(DateTime)
recommendation = Column(Text)
assigned_email = Column(String(200))
review_required = Column(Boolean, default=True)   # 管理员是否需要复核
reviewed_at = Column(DateTime)
reviewed_by = Column(String(100))
false_positive = Column(Boolean, default=False)
```

迁移建议：

```text
migrations/add_incident_automation_fields.py
```

幂等支持 SQLite/PostgreSQL。

---

## 9. 去重规则

同一类未关闭故障不重复创建。

示例 `source_key`：

| 场景 | source_key |
|---|---|
| 设备离线 | `device:{device_id}:unreachable` |
| 接口 linkDown | `device:{device_id}:if:{if_index}:link_down` |
| 链路路径不可达 | `path:{device_id}:{peer_device_id}:unreachable` |
| 邻居变化 | `device:{device_id}:if:{if_index}:neighbor_changed` |
| 高错误包 | `device:{device_id}:if:{if_index}:high_errors` |
| 高利用率 | `device:{device_id}:if:{if_index}:high_utilization` |

去重查询：

```python
FaultRecord.source_key == source_key
FaultRecord.status.notin_(['resolved', 'closed'])
```

若已存在：

- `event_count += 1`
- `last_event_at = now`
- 更新 `severity`（只升不降）
- 追加诊断日志/事件说明
- 不重复发高频邮件，需做通知节流

---

## 10. 故障分类与严重级别规则

### 10.1 初始规则

| 事件 | 条件 | fault_type | incident_type | severity |
|---|---|---|---|---|
| device_unreachable | core_switch / firewall | network | device_down | critical |
| device_unreachable | office_switch / server_switch / wlc | network | device_down | major |
| device_unreachable | ap / other | network | device_down | warning |
| link_down | is_uplink=true 且对端为核心/汇聚 | network | uplink_down | critical/major |
| link_down | is_uplink=true 普通上行 | network | uplink_down | major |
| link_down | 非上行口 | network | access_port_down | warning |
| link_up | 对应故障存在 | network | link_recovered | info/resolved |
| neighbor_changed | 对端设备/端口变化 | topology | topology_changed | major |
| path_unreachable | 数据链路无光缆路径 | topology | path_unreachable | warning/major |
| high_errors | CRC/errors 持续增长 | hardware/network | high_errors | major |
| high_utilization | >80% 持续 15min | capacity | high_utilization | warning/major |

### 10.2 处理建议模板

示例：`uplink_down`

```text
建议处理：
1. 检查本端接口 admin/oper 状态。
2. 检查对端接口状态与最近 Trap。
3. 查看 CRC、input errors、output errors 是否增长。
4. 检查光模块、跳线、ODF/配线架。
5. 若持续 down 超过阈值，建议转维修单安排现场检查。
```

示例：`device_down`

```text
建议处理：
1. 检查设备电源、管理地址、网关和上联链路。
2. 查看其上游设备接口状态。
3. 若同路径多设备同时离线，优先检查共同上游链路。
4. 若设备为核心/防火墙，立即升级为 P1 并通知核心管理员。
```

示例：`topology_changed`

```text
建议处理：
1. 核对 CDP/LLDP 对端是否符合设计拓扑。
2. 检查是否有误插线、临时跳线或端口迁移。
3. 对比历史邻居关系与当前对端。
4. 若变化未备案，建议创建现场核查维修单。
```

---

## 11. 自动指派规则

### 11.1 第一版配置文件规则

先使用配置文件，后续再做前端配置页面。

建议配置：

```yaml
incident:
  enabled: true
  auto_create_fault: true
  auto_assign: true
  notify_email: true
  notify_system: true
  notification_cooldown_minutes: 10
  default_owner: "Network Admin"
  default_email: "network-admin@example.com"
  rules:
    - device_type: "core_switch"
      min_severity: "major"
      owner: "Core Network Admin"
      email: "core-admin@example.com"
    - device_type: "firewall"
      owner: "Security Admin"
      email: "security@example.com"
    - fault_type: "topology"
      owner: "Field Engineer"
      email: "field@example.com"
    - fault_type: "hardware"
      owner: "Maintenance Team"
      email: "maintenance@example.com"
    - incident_type: "high_utilization"
      owner: "Capacity Planner"
      email: "capacity@example.com"
```

### 11.2 后续表结构规则

第二版可新增：

```text
incident_assignment_rules
```

字段：

- id
- name
- enabled
- priority
- device_type
- fault_type
- incident_type
- severity_min
- location_pattern
- owner
- owner_email
- notify_channels
- created_at
- updated_at

---

## 12. 邮件与系统通知设计

### 12.1 邮件触发时机

- 新建 critical/major 故障。
- 未确认超过 SLA 阈值。
- 故障升级。
- 故障转维修。
- 故障恢复待关闭。

### 12.2 邮件内容模板

主题：

```text
[NAS P1] Core-01 Gi1/0/48 上行链路中断 - 工单 FLT-20260627-001
```

正文：

```text
故障单：FLT-20260627-001
状态：待复核
严重级别：critical
负责人：Core Network Admin
设备：Core-01 / 10.10.10.1
端口：Gi1/0/48
对端：Access-03 Gi1/0/48
来源：SNMP Trap linkDown
发生时间：2026-06-27 14:32:11

系统判断：
故障类型：network / uplink_down
影响范围：可能影响 Access-03 下联设备
疑似原因：
1. 光模块异常
2. 跳线松动或损坏
3. 对端端口 shutdown
4. 上联链路 flap

建议处理：
1. 检查 Core-01 Gi1/0/48 与对端端口状态。
2. 查看接口 errors / CRC / input drops。
3. 检查光功率和模块告警。
4. 如持续 down，安排现场检查跳线和模块。
5. 若需要换件，转维修单并预留 SFP 模块。

复核动作：
- 登录系统查看故障单
- 确认接单
- 开始诊断
- 转维修
- 标记误报
```

### 12.3 系统通知

通知应写入现有 `Notification`：

```text
type = incident / fault / maintenance
title = [P1] Core-01 上行链路中断
content = 简要建议 + 负责人 + SLA
reference_type = fault
reference_id = fault.id
```

---

## 13. 自动创建 Work Order 的策略

### 13.1 定义

本系统中建议区分两类工单：

| 类型 | 对应表 | 创建时机 |
|---|---|---|
| Incident / Fault Work Order | FaultRecord | 所有监控告警事件进入这里 |
| Maintenance Work Order | MaintenanceRecord | 需要现场维修、换件、验证时创建 |

### 13.2 第一版策略

默认自动创建 `FaultRecord`，不直接自动创建 `MaintenanceRecord`。

自动生成“建议转维修”的条件：

- `link_down` 持续超过 N 分钟。
- `device_down` 持续超过 N 分钟。
- `high_errors` 持续增长。
- `fault_type=hardware`。
- AI/规则判断 `need_replace`。
- 管理员点击“转维修”。

管理员复核后调用现有接口：

```text
POST /api/faults/{fault_id}/transfer-to-maintenance
```

故障状态变更：

```text
open/assigned/diagnosing → transferred
```

维修单进入：

```text
created → repairing → verifying → completed
```

### 13.3 第二版策略

允许配置部分场景自动创建 `MaintenanceRecord`：

- 核心设备硬件故障高置信度。
- 同一接口 24 小时内 flap 超过阈值。
- 光模块错误包持续增长并且有备件库存。

但仍建议设置 `review_required=true`，管理员确认后执行现场动作。

---

# Phase 2：大屏指挥面板与故障时间线

当前状态（2026-06-27）：已实现 `GET /api/monitor3d/command-summary`、`GET /api/monitor3d/events`、大屏故障指挥面板、事件流、HUD 活跃故障状态、确认/误报/转维修入口；测试环境离线，待恢复后做截图验收和端到端 UAT。

## 14. NOC 指挥面板

在 Monitor3D 大屏右侧或底部新增高密度指挥面板：

内容：

- 当前 P1/P2 告警数
- 未确认故障数
- 处理中故障数
- 已转维修数
- 受影响设备数
- 疑似根因 Top 3
- 最近 5 条关键事件
- 最拥塞链路 Top 5
- 最高错误包接口 Top 5

数据 API 建议：

```text
GET /api/monitor3d/command-summary
```

返回：

```json
{
  "p1_count": 1,
  "p2_count": 3,
  "unacknowledged": 4,
  "in_progress": 2,
  "transferred": 1,
  "impacted_devices": 18,
  "recent_events": [],
  "root_cause_candidates": [],
  "hot_links": []
}
```

---

## 15. 告警时间线 / 事件流

新增右侧事件时间线：

事件类型：

- Trap linkDown/linkUp
- 设备离线/恢复
- 故障创建
- 故障确认
- 开始诊断
- 转维修
- 维修完成
- 拓扑邻居变化
- 路径不可达

要求：

- 支持最近 10 分钟/1 小时/24 小时。
- 点击事件自动聚焦设备。
- 点击故障事件打开故障详情。
- 重大故障事件可触发“故障电影模式”。

建议 API：

```text
GET /api/monitor3d/events?limit=100&severity=major
```

---

## 16. 大屏 HUD 故障状态扩展

HUD 增加：

- 当前故障单号
- 故障状态
- 严重级别
- 负责人
- SLA 剩余时间
- 推荐动作摘要
- 操作按钮：确认 / 诊断 / 转维修 / 关闭

示例：

```text
故障：FLT-20260627-001 P1
状态：待复核
负责人：Core Network Admin
建议：检查光模块、跳线、对端端口
操作：确认 | 转维修
```

---

## 17. 管理员复核流程

管理员收到邮件/系统通知后：

1. 打开故障单详情。
2. 查看系统判断与证据：
   - Trap 时间
   - SNMP 接口状态
   - 接口流量趋势
   - 错误包计数
   - CDP/LLDP 对端
   - 数据链路路径
   - 影响范围
3. 点击确认接单：`assign/accept`。
4. 开始诊断：`diagnose`。
5. 决定是否转维修：`transfer-to-maintenance`。
6. 故障恢复后标记 resolved。
7. 人工确认后 closed。

---

# Phase 3：影响范围与根因候选

当前状态（2026-06-27）：已实现基于活跃 FaultRecord 的根因候选、影响范围摘要、受影响设备高亮、故障链路 Top 5。下一步增强为基于 `device_paths` / `neighbor_paths` 的共同路径边与共同光缆段分析。

## 18. 影响范围分析

基于现有 `device_paths` 和 `neighbor_paths`：

当某条链路/接口/设备故障时：

1. 找到经过该路径的设备。
2. 区分“直接故障设备”和“受影响设备”。
3. 大屏显示影响区域和受影响数量。
4. 写入 FaultRecord.impact。

示例：

```text
影响范围：
- Access-03 下联 AP：12 台
- 办公区 3F：18 个终端可能受影响
- 经过路径：Core-01 Gi1/0/48 → ODF-A → Access-03 Gi1/0/48
```

---

## 19. Root Cause 候选排序

根因候选输入：

- Trap 先后时间
- 多设备离线时间聚合
- 数据链路路径共同边
- 上游接口状态
- CDP/LLDP 邻居关系
- SNMP 错误计数

候选规则：

| 现象 | 根因候选 |
|---|---|
| 多台接入同时离线且路径经过同一上游链路 | 上游链路故障 |
| linkDown Trap 早于设备离线 | 链路故障为主因 |
| 单设备离线但上游链路正常 | 设备自身/电源/管理网络问题 |
| CDP/LLDP 对端突然变化 | 误接线或临时跳线 |
| 错误包先增长后 linkDown | 光模块/跳线质量问题 |

输出：

```json
{
  "candidate": "Core-01 Gi1/0/48 uplink_down",
  "confidence": 0.82,
  "evidence": ["linkDown trap", "downstream devices unreachable", "shared path edge"]
}
```

---

## 20. 拓扑变更检测

CDP/LLDP 每次发现后，对比上次邻居关系：

- 新邻居
- 邻居消失
- 对端设备变化
- 对端端口变化
- 本地端口 peer_ip 变化

触发：

- 自动创建 topology 类型 FaultRecord。
- 大屏标记“拓扑异常”。
- 邮件发送现场核查建议。

---

# Phase 4：旗舰级大屏亮点

## 21. 流量热力层

数据链路线按链路健康状态动态表达：

- 线条粗细：带宽利用率
- 颜色：健康评分
- 粒子速度：流量速率
- 粒子方向：主要流向
- 红色断点：链路中断

建议先做简版：

- `<20%`：细绿线
- `20%~60%`：普通绿/青线
- `60%~80%`：黄色加粗
- `>80%`：橙红加粗 + 动画

---

## 22. 故障电影模式

重大故障发生后自动播放故障演进：

```text
14:32:11 Trap linkDown
14:32:12 上行链路变红
14:32:20 下游设备不可达
14:32:30 影响范围计算完成
14:32:31 疑似根因标注
```

表现：

- 镜头自动聚焦根因候选。
- 按时间顺序高亮链路和设备。
- 受影响区域逐步扩散。
- 播放完成后停留在故障指挥面板。

---

## 23. Topology Diff 视图

对比：

```text
设计拓扑 / 光缆拓扑 / 手工拓扑
vs
CDP/LLDP 自动发现拓扑
```

显示：

- 多出来的连接
- 缺失的连接
- 对端不一致
- 端口不一致
- 低置信度匹配

用途：

- 发现误接线。
- 发现文档拓扑过期。
- 发现临时跳线未登记。

---

## 24. 拓扑置信度

每条自动发现关系记录置信度：

| 来源 | 置信度 |
|---|---|
| CDP 双向一致 + IP 匹配 | 高 |
| CDP 单向 + IP 匹配 | 高 |
| LLDP 单向 + 主机名匹配 | 中 |
| 仅端口名/主机名模糊匹配 | 低 |
| 手工确认 | 人工确认 |

前端表达：

- 高：实线
- 中：半透明实线
- 低：虚线
- 人工确认：带确认标记

---

## 25. 数字孪生分层视图

未来方向：

1. 园区视图
2. 建筑视图
3. 楼层视图
4. 机柜/弱电间视图
5. 设备视图
6. 端口视图

下钻逻辑：

```text
全厂态势 → 楼栋 → 楼层 → 弱电间 → 交换机 → 端口 → 对端链路
```

---

## 26. 数据新鲜度 Stale 标记

每类数据都显示 freshness：

- reachability last_check
- SNMP last_check
- Trap last_event_at
- CDP/LLDP neighbor_updated_at
- traffic sample last_sample_at

规则：

| 数据 | 超时阈值 | 表现 |
|---|---|---|
| SNMP 接口 | > 3 个轮询周期 | stale 黄色时钟 |
| reachability | > 2 个周期 | stale |
| CDP/LLDP | > 24 小时 | topology stale |
| 流量样本 | > 5 分钟 | trend stale |

---

## 27. 维护窗口模式

维护窗口内：

- 告警不自动升级。
- 大屏显示“维护中”。
- 自动建 FaultRecord 可降级为 warning 或仅记录事件。
- 仍然保留日志与审计。

适用：

- 设备升级
- 光缆割接
- 计划停机
- 机房巡检

---

## 28. 容量趋势预警

基于 `interface_traffic_samples`：

- 最近 24 小时 / 7 天利用率趋势。
- 上行链路超过 80% 的持续时间。
- 错误包增长趋势。
- Top N 拥塞链路。

第一版无需复杂 AI，可先做：

- 阈值统计
- 线性趋势
- 移动平均

---

# 29. API 规划

## 29.1 Incident Automation API

```text
POST /api/incidents/from-monitor-event
GET  /api/incidents/active
GET  /api/incidents/summary
POST /api/incidents/{fault_id}/ack
POST /api/incidents/{fault_id}/mark-false-positive
POST /api/incidents/{fault_id}/review
```

说明：

- 也可全部挂到 `/api/faults` 下，保持模块集中。
- 第一版建议新增 service，少新增 API，优先复用已有 faults API。

## 29.2 Monitor3D 指挥 API

```text
GET /api/monitor3d/command-summary
GET /api/monitor3d/events
GET /api/monitor3d/device/{device_id}/active-incident
GET /api/monitor3d/impact/{fault_id}
GET /api/monitor3d/root-cause-candidates/{fault_id}
```

## 29.3 通知测试 API

复用现有 alerts/notifications/email 能力，必要时新增：

```text
POST /api/incidents/{fault_id}/send-review-email
```

---

# 30. 数据模型规划

## 30.1 FaultRecord 扩展

见第 8 节。

## 30.2 可选：IncidentEvent 表

如果要构建完整事件时间线，建议新增：

```python
class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True)
    fault_id = Column(Integer, ForeignKey("fault_records.id"), index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), index=True)
    event_type = Column(String(50), index=True)
    source_type = Column(String(30), index=True)
    severity = Column(String(20), index=True)
    message = Column(Text)
    raw_payload = Column(Text)
    occurred_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

用途：

- 告警时间线
- 故障电影模式
- 根因分析证据
- 通知审计

## 30.3 可选：IncidentAssignmentRule 表

见第 11.2 节。

---

# 31. 前端规划

## 31.1 Monitor3D 大屏

新增：

- 指挥面板
- 事件时间线
- 当前故障卡片
- HUD 故障状态行
- HUD 操作按钮
- 影响范围高亮
- 根因候选卡片
- 数据新鲜度标记
- 流量热力线

## 31.2 故障详情页

增强：

- 监控事件证据区
- 系统判断区
- AI/规则建议区
- 影响范围区
- 拓扑路径区
- 操作按钮区
- 维修单关联区

## 31.3 设备详情页

增强：

- 当前未关闭故障
- 最近 30 天故障统计
- 最近一次 Trap
- 上行口列表
- 对端邻居
- 关联维修记录
- 健康趋势

---

# 32. 验收标准

## 32.1 Phase 1 验收

- linkDown Trap 自动创建 FaultRecord。
- 同一接口重复 linkDown 不重复创建故障，只更新 event_count。
- 故障自动指派负责人。
- 故障生成处理建议。
- 邮件发送给对应负责人。
- 系统通知可见。
- 管理员可确认接单。
- 管理员可转维修单。
- 维修单完成后可回写故障状态。

## 32.2 Phase 2 验收

- 大屏显示当前 P1/P2、未确认、处理中、转维修数量。
- 大屏事件时间线按时间更新。
- 点击事件可聚焦设备。
- HUD 显示当前故障单号、状态、负责人、建议。
- 大屏可执行确认/转维修操作。

## 32.3 Phase 3 验收

- 上游链路故障可计算受影响设备。
- 多设备同时离线可给出根因候选。
- 拓扑变化可生成 topology 故障。
- FaultRecord.impact 写入影响范围。

## 32.4 Phase 4 验收

- 数据链路线可按流量利用率变色/变粗。
- 重大故障可播放故障演进。
- Topology Diff 可展示设计拓扑与 CDP/LLDP 发现差异。
- stale 数据可被识别并在 UI 显示。

---

# 33. 开发建议顺序

建议实际开发顺序：

1. `incident_automation_service.py`
2. FaultRecord 字段迁移
3. Trap/linkDown 接入自动故障创建
4. 设备离线接入自动故障创建
5. 自动指派规则配置
6. 邮件与系统通知发送
7. HUD 显示故障单状态
8. 大屏一键确认故障
9. 转维修闭环接入
10. 指挥面板
11. 事件时间线
12. 影响范围分析
13. Root Cause 候选
14. 流量热力层
15. Topology Diff
16. 故障电影模式

---

# 34. 风险与控制

| 风险 | 控制方式 |
|---|---|
| 自动创建过多故障 | source_key 去重 + 通知节流 + 阈值过滤 |
| AI 判断不稳定 | 规则优先，AI 作为建议，管理员复核 |
| 误报影响信任 | 支持 false_positive 标记，优化规则 |
| 邮件轰炸 | cooldown + severity 过滤 + 合并通知 |
| 维修单污染 | 默认只自动创建 FaultRecord，维修单需复核 |
| 拓扑不完整导致影响范围不准 | 标记置信度与路径不可达原因 |
| 前端信息过载 | 指挥面板高密度但分层展示，重大告警优先 |

---

# 35. 第一阶段最小可交付版本（MVP）

MVP 范围：

1. 新增 FaultRecord 监控来源字段。
2. 新增 `incident_automation_service.py`。
3. Trap `linkDown` 自动创建/更新 FaultRecord。
4. 设备离线自动创建/更新 FaultRecord。
5. 自动生成故障类型、严重级别、处理建议。
6. 自动指派默认负责人。
7. 发送系统通知和邮件。
8. HUD 显示当前故障单号和状态。
9. 大屏支持确认故障。
10. 支持人工转维修单。

MVP 不包含：

- 完整 AI 自动根因分析
- Topology Diff
- 故障电影模式
- 多级数字孪生视图
- 复杂容量预测

---

# 36. 结论

下一阶段应优先打通“监控事件 → 故障工单 → 指派通知 → 管理员复核 → 维修闭环”的主链路。

这条主链路完成后，3D 监控大屏将从“可视化监控页面”升级为“网络运维指挥台”。后续再叠加影响范围分析、根因候选、流量热力、Topology Diff 和故障电影模式，系统会逐步接近国际一线 NOC / DCIM / AIOps 大屏的体验。
