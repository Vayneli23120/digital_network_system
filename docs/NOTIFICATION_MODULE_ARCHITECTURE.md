# 通知管理 / 告警异常通知模块 · 架构设计方案（适配版）

> 版本：v1.1（2026-08）
> 依据：对 NAS 现状代码的完整盘点（告警闭环 MVP 已落地）＋ 通用告警通知蓝图
> 原则：**在现有技术栈上演进，不引入新语言/新中间件；复用优先，策略化补齐**

### 变更记录

| 版本 | 变更 |
|---|---|
| v1.0 | 首版：现状盘点 + 分层设计 + 数据模型 + 三期路线 |
| v1.1 | ① 确认**通知目标映射与升级链**组织决策（见 2.2）；② 通知铃铛按登录账号严格过滤（已完成上线，见 8.0）；③ 一期开发任务清单细化 |

### 已确认的组织决策（v1.1，开发基线）

1. **监控自动故障的通知目标**：统一发给 **admin + 运维组**（不再使用环境变量伪账号名）。
2. **升级链**：运维组**超时未处理** → 升级通知 **部门经理**（默认三级，时长可配，见 4.6）。
3. 站内通知必须发到**真实登录账号**；邮件/IM 渠道同步发组内成员邮箱。

---

## 1. 设计原则与范围

1. **复用优先，不另起炉灶**：现有 `MonitorEvent`（统一事件）、`FaultRecord`（故障单状态机）、
   `NotificationService`（多渠道发送）已经是蓝图里"接入层 + 故障单 + 渠道"的骨架，本方案是
   把它们从"硬编码 MVP"升级为"可配置、可追踪、可升级"的完整模块，而不是推倒重建。
2. **技术栈不变**：保持 FastAPI + Vue 3 + PostgreSQL + Redis + Celery。
   当前告警量级（SNMP Trap + ICMP 轮询 + 内部事件，每分钟个位数～两位数）远未到需要
   Kafka / Go 的水平；Celery 队列 + Redis 去重/频控足以覆盖并预留 10 倍余量。
3. **通知与分发解耦**：`notification_policy`（告知谁）与 `dispatch_rule`（派给谁）两套独立配置。
4. **全链路可追溯**：每一次"策略命中、渠道发送、重试、降级、升级"都落 `notification_log`。
5. **风暴治理先行**：去重、聚合、频控是信任根基；没有治理就上通知，邮箱会被打爆。

---

## 2. 现状盘点：蓝图 ↔ 现状映射

| 蓝图层次 | 蓝图能力 | NAS 现状实现 | 差距（本方案补齐项） |
|---|---|---|---|
| 告警接入层 | Prometheus/Zabbix/自定义接入、统一告警模型 | ✅ `MonitorEvent` dataclass（`app/services/incident_automation.py`）；内部源：`trap_receiver.py`（SNMP Trap linkDown/Up）、`reachability_monitor.py`（ICMP）、备份失败/库存/工作流事件 | ❌ 无**外部** HTTP 接入（webhook）与鉴权；事件模型缺 `labels/annotations` 通用承载 |
| 告警处理引擎 | 去重/聚合/抑制/静默/升级 | ✅ 去重（`source_key` upsert 进未关闭故障单，`event_count` 累计）；✅ 抖动抑制（`FLAP_SUPPRESS_SECONDS=90s` → `false_positive`）；✅ 恢复事件自动 resolve | ❌ 聚合（同类归并）；❌ 抑制（根因屏蔽衍生）；❌ 静默窗口（未联动 `planned_maintenance`）；❌ 频控（同故障 N 分钟最多 M 条） |
| 通知策略引擎 | 渠道管理/模板/多维路由/频控/重试降级 | 🟡 `notification_service.py`：email/企业微信/钉钉三渠道统一入口，`config.yaml` + `/api/alerts/settings` 管理；🟡 每个事件一个硬编码方法（`notify_backup_failure` 等），仅 try/except 无重试 | ❌ 无策略表（级别×对象×渠道不可配置）；❌ 无模板引擎（正文硬编码在代码里）；❌ 无重试/降级；❌ 无发送日志 |
| 组织与权限 | 用户/角色/分组/排班/RBAC | ✅ `User/Role/Permission` + RBAC（`require_permission`）；🟡 负责人指派靠环境变量 + `_owner_for()` 硬编码规则 | ❌ 无 `user_group`（运维组）；❌ 无 `oncall_schedule`（排班表） |
| 分发与任务 | 分发规则/故障单/任务派发认领 | ✅ `FaultRecord` 完整状态机（open→assigned→accepted→diagnosing→resolving→transferred→resolved→closed，各环节时间戳齐全）；✅ 复核字段（`review_required/false_positive`）；✅ 关联维修单 `maintenance_id` | ❌ 分发规则硬编码（env + `_owner_for`），不可 UI 配置；❌ 无升级（Escalation）；🟡 认领流程已有但无超时驱动 |
| 闭环与统计 | 确认→恢复→关闭、MTTA/MTTR/SLA 报表 | ✅ Dashboard 已有 MTTA/MTTR（`MttrFunnel.vue` 等）；✅ AI 预判（`ai_triage.py`）+ 复盘字段 | ❌ 通知侧无统计（送达率/渠道成功率）；❌ SLA 报表未与升级策略联动 |

**结论**：蓝图六层中，"故障单闭环"和"内部告警接入"已经相当成熟（见
`docs/NEXT_PHASE_MONITOR3D_INCIDENT_AUTOMATION_PLAN.md` 的 Phase 1 已落地）；
**本方案的主战场是：外部接入、聚合/静默/频控、通知策略化、排班与升级、通知审计**。

### 2.1 故障与维修单的创建/派发路径（现状全景，通知改造必须全覆盖）

系统里"生成故障单 / 维修单并派发"有 **6 条独立路径**，任何一条都不能在通知改造中遗漏
（维修单是故障单的下游：故障转维修后会**再产生一次"维修单派发"**，它有自己的负责人、SLA 和通知链）：

| # | 路径 | 代码入口 | 自动派发方式 | 当前通知行为 | 缺口 |
|---|---|---|---|---|---|
| 1 | **监控自动生成故障**（3D 数字孪生大屏展示的活跃故障） | `trap_receiver.py` / `reachability_monitor.py` → `upsert_fault_from_monitor_event()` | `_owner_for()`：按设备类型×级别×故障类型 → 负责人 + 邮箱（**环境变量配置的伪账号**） | `notify_incident()`：站内通知 + **邮件**（critical/major 及恢复时，发 `assigned_email`） | 派发目标是**环境变量伪账号**（Core Network Admin 等非真实登录账号），站内通知无人可见；无 IM；无组级派发；无频控/升级/发送日志 |
| 2 | **手动创建故障单** | `POST /api/faults` → `create_fault()` | 可选 `assigned_to` | `send_fault_assigned_notification()`：**仅站内通知**；另触发工作流 + AI 预判 | 无邮件/IM；无策略路由；无发送日志 |
| 3 | **手动指派故障** | `POST /api/faults/{id}/assign` → `assign_fault()` | `assigned_to` | `send_fault_assigned_notification()`：**仅站内通知** | 同路径 2 |
| 4 | **3D 大屏复核 / 转维修** | `POST /api/faults/{id}/review`、`transfer-to-maintenance` | 转维修建维修单：`current_owner = maintenance_owner 或继承 fault.assigned_to` | `send_maintenance_assigned_notification()`：**仅站内通知**给维修负责人 | 与故障单通知未串联；无组级派发；无邮件/IM |
| 5 | **维修单指派 / AI·工作流自动建维修单** | `PUT /api/maintenance/{id}/assign`；`auto-create-maintenance`；工作流 `create_maintenance` 动作 | 手动指定 `current_owner`；AI/工作流建单时**不指派**（owner 为空） | `assign_maintenance`：**零通知**；`auto_create_maintenance`：**零指派 + 零通知** | 手动指派无任何通知；自动建单无人认领、无 SLA 驱动 |
| 6 | **维修完成 → 故障负责人确认** | `send_maintenance_completed_notification()` | — | 站内通知故障负责人 | 无邮件/IM；无发送日志 |

**设计红线**：这 6 条路径 + 工作流 `SendAlertAction`（现有 TODO 未接通知服务）必须全部收敛到
本方案的统一通知出口 `dispatch()`（见 4.3），否则会出现"有的故障有邮件、有的只有站内通知、
维修单指派甚至完全没通知"的不一致体验。路径 1 与路径 4/5 的派发还要从
"环境变量/继承负责人指定个人"升级为"`dispatch_rule` 路由到运维组 → `oncall_schedule`
解析值班人"（见 4.4/4.5）。

### 2.2 通知目标映射与升级链（v1.1 确认的组织决策）

**现状问题**：`_owner_for()` 生成的是伪账号名（`Core Network Admin` / `Security Admin` /
`Field Engineer` / `Capacity Planner` / `Network Admin`），不是真实登录账号——
修复通知铃铛严格按账号过滤后（见 8.0），这类站内通知将无人可见。

**目标映射规则（开发基线）**：

```text
监控自动故障（Trap/可达性）─→ 通知目标 = { admin } ∪ { 运维组 }     （站内 + 邮件 + IM）
       │
       ├─ 运维组值班人在岗 → assigned_to = 值班人（真实账号）
       ├─ 无排班表        → assigned_to = 组名回退 admin 认领
       └─ 旧 env 伪账号   → 废弃（不再写 assigned_to；邮件 env 仅作组邮箱兜底，后续并入组配置）
```

**升级链（默认三级，时长可配）**：

```text
L1 告警产生      → 立即通知 admin + 运维组（值班人）
L2 超时未认领    → 通知运维组全员 + admin
L3 再超时未处理  → 升级通知部门经理（运维组组长）+ 生成复盘任务
```

- 部门经理 = `user_group_member.is_leader=true` 的组员（或 escalation_policy 单独配置目标角色/用户）。
- 维修单（SLA 超时）走同一套升级链，仅时间基准换成 `sla_deadline`。
- 伪账号 → 真实账号的映射不需要额外的映射表：**通知目标直接由 dispatch_rule/组解析产生**，
  伪账号概念随 `_owner_for` 一起下线。

---

## 3. 适配后总体架构

```
             内部源（现状已接入）              外部源（一期新增）
  ┌──────────────┬──────────────┬──────────┐   ┌─────────────┬─────────────┐
  │ SNMP Trap    │ ICMP 轮询    │ 备份/部署 │   │ Prometheus  │ Zabbix/     │
  │ trap_receiver│ reachability │ 库存/工作流│   │ Alertmanager│ 自定义     │
  └──────┬───────┴──────┬───────┴─────┬────┘   └──────┬──────┴──────┬──────┘
         └──────────────┼─────────────┘               │             │
                        ▼                             ▼             ▼
        ┌──────────────────────────────────────────────────────────────┐
        │ 告警接入层（app/features/alerts 扩展）                          │
        │  · MonitorEvent 扩展 labels/annotations/指纹                     │
        │  · POST /api/alerts/webhook/{source}（签名鉴权 + 适配器）        │
        └─────────────────────────────┬────────────────────────────────┘
                                      ▼
        ┌──────────────────────────────────────────────────────────────┐
        │ 告警处理引擎（incident_automation.py 演进）                     │
        │  去重(source_key) → 抖动抑制(已有) → 聚合(新) →                 │
        │  抑制(根因/拓扑,新) → 静默窗口(联动 planned_maintenance,新) →   │
        │  频控(Redis 计数,新) → 生成 AlertEvent 待分发                   │
        └─────────────────────────────┬────────────────────────────────┘
                                      ▼
        ┌──────────────────────────────────────────────────────────────┐
        │ 策略引擎（新模块 app/features/notifications 扩展）              │
        │  notification_policy：级别 × 对象(组/值班人) × 渠道 × 模板       │
        │  dispatch_rule：条件(业务线/标签/来源) → 运维组                 │
        │  oncall_schedule：排班解析当前值班人                             │
        └───────────────┬──────────────────────────────┬───────────────┘
                        ▼                              ▼
        ┌────────────────────────┐      ┌───────────────────────────────┐
        │ 通知渠道（已有，DB 化） │      │ 故障/任务（已有）               │
        │ email/wechat/dingtalk  │      │ FaultRecord 状态机 + 维修单     │
        │ + 模板引擎(Jinja2)     │      │ + escalation_policy 升级        │
        │ + 重试/降级(Celery)    │      │ + 认领/转派/超时驱动             │
        └────────────┬───────────┘      └───────────────┬───────────────┘
                     └──────────────┬───────────────────┘
                                    ▼
        ┌──────────────────────────────────────────────────────────────┐
        │ 审计与统计：notification_log / 操作审计 / MTTA·MTTR·SLA 报表    │
        └──────────────────────────────────────────────────────────────┘
```

架构决策对照（蓝图 → 现状落地）：

| 蓝图选型 | NAS 实际决策 | 理由 |
|---|---|---|
| Go/Java 后端 | **保持 FastAPI** | 告警洪峰量级小；现有代码/人员栈一致，改造成本最低 |
| Kafka | **Celery + Redis** | 已有 worker/beat 与 Redis；`task_acks_late + 幂等 source_key` 等效"至少一次" |
| MySQL | **PostgreSQL** | 现状已是 PG（含 pgvector），不引入第二套关系库 |
| Redis 去重/频控 | ✅ 复用现有 Redis | 新增告警去重键/频控计数，与现有 cache 共用 |
| XXL-Job/Quartz | **Celery beat** | 已有 beat（escalation 扫描、排班切换、重试调度） |
| 模板引擎 | **Jinja2**（Python 原生） | 邮件正文/IM 卡片统一模板，无新依赖 |
| 时序存储 | 暂不引入 ClickHouse | 告警历史量级用 PG 分区表即可，后续需要再演进 |

---

## 4. 分层设计

### 4.1 告警接入层（内部已通，补外部）

- **统一事件模型扩展**：`MonitorEvent` 增加
  `labels: Dict[str,str]`（业务线/机房/系统标签）、`annotations: Dict[str,str]`（详情/建议）、
  `fingerprint: str`（外部源自带指纹，缺省由 `source_type+source_key` 派生）。
- **外部 webhook 接收**（一期）：
  - `POST /api/alerts/webhook/prometheus`：接收 Alertmanager Webhook v4 JSON，
    适配器转 `MonitorEvent(source_type="prometheus", event_type=..., severity 映射)`。
  - `POST /api/alerts/webhook/zabbix`、`POST /api/alerts/webhook/generic`（自定义 JSON 模板）。
  - 鉴权：每个 source 独立密钥（Header `X-Alert-Token`，HMAC 校验），沿用现有
    `require_permission` 之外的独立签名中间件；IP 白名单可选。
- **兼容性红线**：外部源先转 `MonitorEvent` 再进引擎，**禁止**任何渠道/策略直接消费原始格式
  （否则策略层要写 N 套适配，必然失控）。

### 4.2 告警处理引擎（在 incident_automation.py 上叠加）

保留现有 `upsert_fault_from_monitor_event` 的去重/抖动抑制/自动恢复语义，新增四道工序
（全部做成可开关的独立函数，默认不改变现有行为）：

1. **聚合（Aggregation）**：按 `(source_key 前缀, severity, 时间窗)` 归并同类事件，
   如"同一上联链路下 8 台接入交换机同时 unreachable"聚合为 1 条根因候选，避免 8 张工单 + 8 封邮件。
2. **抑制（Suppression）**：拓扑感知——上游设备 down 时，抑制其下游设备的衍生告警
   （现状已有 `peer_device_id/is_uplink` 拓扑字段可直接利用）；根因单未关闭前衍生单标 `suppressed_by=<fault_no>`。
3. **静默（Silence）**：联动 `planned_maintenance`——维护窗口内的设备告警标
   `silenced=true`，只落库不通知；窗口结束自动解除。这是现成数据，不需要新建维护日历。
4. **频控（Rate Limit）**：Redis 计数——同一 `source_key` 在 5 分钟窗内最多 N 条
   外部通知（N 按级别可配，默认 critical 不限、major 3、其余 1），超出的只更新故障单不重复轰炸。

### 4.3 通知策略引擎（本次核心新增）

- **渠道 DB 化**：新增 `notification_channel` 表，把 `config.yaml` 里的
  email/wechat/dingtalk 配置迁移入库（加密存密钥），保留 `/api/alerts/settings`
  为兼容入口，底层改读 DB；渠道增删改支持热生效（现状已有 `reset_notification_service()` 缓存失效机制可复用）。
- **策略路由**：`notification_policy` 表定义
  `级别 × 事件类型 × 对象(组/角色/用户) × 渠道 × 模板 × 频控窗口` 的多维路由。
  默认策略（安装时 seed）：critical/major → 值班组全员（email+IM）；minor/warning → 仅站内通知。
- **模板引擎**：通知正文全部迁到 Jinja2 模板（邮件 HTML/纯文本、IM 卡片各一套），
  模板变量 = MonitorEvent + FaultRecord 字段 + AI 研判摘要；支持恢复通知独立模板。
  现状硬编码在 `build_incident_email_body` 等位置的文案全部迁移为模板文件。
- **发送管线**：`NotificationService` 的硬编码方法（`notify_backup_failure` 等）统一改为
  `dispatch(event, policy)` 单入口。**事件类型枚举必须覆盖全部故障/维修来源**：
  `fault_auto_created / fault_recovered / fault_assigned / fault_reviewed / fault_transferred /
  maintenance_assigned / maintenance_auto_created / maintenance_reassigned /
  maintenance_completed / maintenance_sla_escalated / backup_failed / device_unreachable /
  device_recovered / low_stock / workflow_alert`，对应现状 2.1 节的 6 条路径 +
  工作流动作 + 运维事件；每条路径的调用点（`notify_incident`、`send_fault_assigned_notification`、
  `send_maintenance_assigned_notification`、`send_maintenance_completed_notification`、
  `assign_maintenance`（现状零通知，需新增）、`auto_create_maintenance`（现状零通知，需新增）、
  `SendAlertAction`）全部改为调用 `dispatch()`。
  每次发送写 `notification_log`（who/when/channel/status/retry）。
- **可靠性**：发送改 Celery 异步任务（新队列 `alerts`，与 device_ops 隔离）；失败指数退避
  重试（1/2/4 分钟 ×3），仍失败按策略降级（email→IM→站内通知）；`SendAlertAction`
  （workflow）里的 TODO 顺势接上 `dispatch()`。

### 4.4 组织与排班

- 新增 `user_group`（运维组/值班组）+ `user_group_member`（多对多，含 `is_leader` 组长标记），
  复用现有 RBAC 权限体系（`notification:manage` / `dispatch:manage` 新权限点）。
- **种子数据（默认组织形态，按 v1.1 决策）**：
  - `运维组`（name=运维组）：成员含 `admin` + 各运维值班账号；其中 1 人标记 `is_leader=true`（**部门经理**）。
  - `escalation_policy` 默认策略的 L3 目标 = 运维组组长（部门经理）。
  - 用户账号创建复用现有 `/api/auth/users` 与 Users 页面，不新做用户管理。
- 新增 `oncall_schedule`：组 × 时间段 × 值班人，支持循环排班与临时替班；
  解析函数 `resolve_oncall(group_id, at_time) -> user`；未配置排班时回退"组内全员"（assign_to 组名 + 通知全员）。
- `dispatch_rule`：条件（来源/业务线/标签/设备类型）→ 目标组；把 `_owner_for()`
  的环境变量硬编码迁成规则表。**默认规则（seed）**：监控自动故障 → 运维组；通知目标 = {admin} ∪ 运维组。

### 4.5 分发与故障单（复用 FaultRecord）

- 故障单继续用 `FaultRecord` 状态机（**不新建 incident 表**），关联字段已具备
  （`source_key/source_type/event_count/assigned_to/assigned_at/...`）。
- 派发语义：**4 条创建路径（监控自动生成 / 手动创建 / 手动指派 / 3D 大屏复核转维修）
  统一走 `dispatch_rule`**：命中规则 → 写 `assigned_to=值班人`（真实账号）→ 站内通知 + 值班人渠道通知
  （email/IM）。
- **监控自动故障（路径 1）的目标映射（v1.1 基线）**：
  - 通知目标 = `{admin} ∪ 运维组成员`（站内 + 邮件 + IM），替代 `_owner_for` 伪账号；
  - `assigned_to` = 运维组值班人（真实账号）；无排班时 = 组名，由组内认领；
  - 旧 env 伪账号（`INCIDENT_*_OWNER`）**废弃**，不再写入 `assigned_to`；其 email 值并入运维组配置作为组邮箱兜底。
- 3D 大屏的"自动派发给组别/个人"能力迁移为 `dispatch_rule + user_group + oncall_schedule`，
  派发目标从"环境变量写死的伪账号"升级为"按业务线/设备类型路由到组 → 组内值班人"。
- 值班人**认领（accepted）**→ 处理 → resolved → closed（现有接口已覆盖，仅补超时驱动）。
- 无人认领时走 `escalation_policy`（见 4.6），不再出现"全组轰炸 + 无人负责"。
- **维修单是故障单的下游派发链**：`transfer_to_maintenance` / `auto_create_maintenance` /
  工作流 `create_maintenance` 建单后，`MaintenanceRecord.current_owner` 的指派同样走
  `dispatch_rule`（可路由到维修组/个人，替换现状"继承故障负责人 / 手动指定 / 无人认领"三态），
  并触发 `maintenance_assigned` 通知；`sla_deadline` 字段（现状已有、无人消费）作为维修单
  升级驱动的超时基准。维修完成时 `maintenance_completed` 通知故障负责人确认闭环
  （现状 `send_maintenance_completed_notification` 已有站内版，升级为全渠道）。

### 4.6 升级策略（Escalation）

- 新增 `escalation_policy` 表：`{级别, 超时时长, 目标(值班人/组全员/组长(部门经理)), 动作(通知/再加派人/生成复盘任务)}`。
- **默认三级（v1.1 组织决策，时长可配）**：
  - L1：告警产生 → 立即通知 admin + 运维组（值班人）
  - L2：15 分钟未认领 → 通知运维组全员 + admin
  - L3：30 分钟未处理（或 1 小时未恢复，取先到者）→ **升级通知部门经理（运维组组长）** + 生成复盘任务（落 `MaintenanceTask`）
- 驱动：Celery beat 每分钟扫描未关闭的 critical/major 单，按 `accepted_at/resolved_at`
  空值与超时阈值推进升级层级，每次升级写 `notification_log`（可追溯"谁在几点被升级通知"）。
- **维修单同套升级机制**：扫描未完成的维修单（`MaintenanceRecord.status not in
  (completed, cancelled)`），以 `sla_deadline`（现状已有字段）为超时基准，
  超时/临期触发 `maintenance_sla_escalated`（同样升级到部门经理、必要时加派人手），
  与故障单升级共用一张 `escalation_policy` 表、仅目标对象与时间基准不同。

### 4.7 闭环与统计

- 全流程事件链：`AlertEvent(标准化) → FaultRecord(故障单) → notification_log(通知) → 状态机时间戳(闭环)`。
- 新增统计：渠道送达率/失败率、升级触发次数、按组的 MTTA/MTTR、SLA 达成率，
  复用 dashboard 现有 MttrFunnel/ErrorBudget 组件出报表。

---

## 5. 数据模型（新增表 + 现有表扩展）

### 5.1 新增表（均为 SQLAlchemy 模型，落 `app/shared/models.py`，随 alembic 迁移）

```text
user_group(id, name, description, is_oncall)          # 运维组/值班组
user_group_member(id, group_id, user_id, is_leader)   # 成员（含组长标记）

oncall_schedule(id, group_id, user_id,
                start_at, end_at,                     # 排班时间段
                repeat_rule)                          # 循环规则（weekly/daily/自定义）

notification_channel(id, type[email|wechat_work|dingtalk|webhook],
                     name, enabled, config_encrypted) # SMTP/Webhook 配置（密钥加密）

notification_policy(id, name, enabled, priority,
                    severity[], event_types[],         # 级别×事件类型
                    target_type[group|role|user|all], target_id,
                    channels[], template_id,
                    rate_limit_window_s, rate_limit_max)

notification_template(id, name, channel_type,
                      subject_tpl, body_tpl)          # Jinja2 模板

notification_log(id, fault_id, alert_event_id, channel, recipient,
                 subject, status[sent|failed|degraded|suppressed],
                 retry_count, error, created_at)      # 全链路审计

dispatch_rule(id, name, enabled, priority,
              condition_json,                         # 来源/标签/业务线/设备类型
              target_group_id, escalation_policy_id)

escalation_policy(id, name, levels_json)              # [{level, timeout_s, targets, actions}]

alert_event(id, source_type, event_type, fingerprint,  # 标准化告警事件（外部源进来必落）
            severity, labels_json, annotations_json,
            dedup_key, aggregated_count, suppressed_by, silenced,
            fault_id, created_at)                     # 与 FaultRecord 一对多/多对一
```

### 5.2 现有表扩展（最小侵入）

| 表 | 扩展 | 说明 |
|---|---|---|
| `fault_records` | + `escalation_level`(默认0) + `escalated_at` + `silenced` + `suppressed_by` + `group_id` | 升级进度与抑制链；其余字段已完备，**不动** |
| `maintenance_records` | + `group_id` + `escalation_level` + `escalated_at` | 维修单派发到组 + SLA 升级进度；`current_owner/sla_deadline` 现状已有，直接消费 |
| `notifications` | + `alert_event_id` + `dedup_key` | 站内通知与告警事件对齐，去重可查 |
| `users` | 不动 | 组关系走 `user_group_member` |

---

## 6. 关键流程设计

### 6.1 告警通知主流程

```
告警产生(内部源/外部 webhook)
 → 适配器转 MonitorEvent（内部源直发）
 → classify_event() 分类分级（现状，规则优先 + AI 增强可选）
 → 引擎四道工序：去重(现状) → 聚合/抑制/静默/频控(新增)
 → upsert FaultRecord（现状）
 → 策略引擎：命中 notification_policy（级别×事件×组×渠道×模板）
 → 模板渲染 → Celery 队列发送(email/IM) + 站内通知(现状)
 → notification_log 落审计；失败→重试→降级(新增)
```

### 6.2 故障分发流程（核心）

```
告警 → 引擎 → FaultRecord(open)
 → 命中 dispatch_rule（业务线/标签/来源 → 运维组）
 → oncall_schedule 解析当前值班人 → assigned_to=值班人（assigned 态）
 → 按 notification_policy 通知值班人（email + IM + 站内）
 → 值班人认领(accepted) → 诊断(diagnosing) → 恢复(resolved) → 关闭(closed)
  → 超时未认领/未处理 → escalation_policy 逐级升级（运维组全员 → 部门经理 + 复盘任务）
```

### 6.3 升级流程（v1.1 默认三级）

```
Celery beat 每分钟扫描（只扫 critical/major、status in OPEN）
  L1(0min)   告警产生      → 通知 admin + 运维组（值班人）
  L2(15min)  accepted_at 为空 → 运维组全员 + admin
  L3(30min)  resolved_at 为空（超时未处理）→ 部门经理（运维组组长）+ 生成复盘任务(MaintenanceTask)
  维修单同套：以 sla_deadline 为基准，超时升级部门经理
  每次升级：escalation_level+1、escalated_at 更新、notification_log 记录
```

### 6.4 故障/维修单创建与派发路径全景（六条入口 → 一个通知出口）

```
┌─① 监控自动生成（Trap/可达性）──→ upsert_fault_from_monitor_event
│      └─ _owner_for 伪账号废弃 → dispatch_rule（admin + 运维组）
├─② 手动创建（POST /api/faults）──→ create_fault（可选 assigned_to）
├─③ 手动指派（POST /{id}/assign）─→ assign_fault
└─④ 3D 大屏复核/转维修 ──→ review / transfer-to-maintenance
         │                          │
         │              ┌───────────▼───────────┐
         │              │ 维修单创建与派发（下游链）│
         │              │ transfer / auto-create │
         │              │ workflow create_maint  │
         │              │ assign_maintenance     │
         │              │ → current_owner 指派   │
         │              └───────────┬───────────┘
         │                          ▼
        （工作流 SendAlertAction、备份失败、低库存等运维事件同样汇入 ↓）
                                 ▼
                    dispatch(event, policy)  统一通知出口
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                  ▼
        notification_policy  dispatch_rule    oncall_schedule
        （级别×事件×组×渠道）  （条件→组）      （组→值班人）
              │                  │
              ▼                  ▼
       渠道发送(邮件/IM/站内)   FaultRecord 状态机 + escalation_policy
              │                MaintenanceRecord + sla_deadline 升级
              ▼
        notification_log（全链路审计，含重试/降级/升级动作）
```

> 现状六条路径的通知调用点分别为：`notify_incident()`（路径①）、
> `send_fault_assigned_notification()`（路径②③）、`send_maintenance_assigned_notification()`
> / `send_maintenance_completed_notification()`（路径④⑥）、`assign_maintenance()` 与
> `auto_create_maintenance()`（路径⑤，现状零通知）；改造后全部替换为 `dispatch()`，
> 仅传不同的事件类型与上下文。

---

## 7. 健壮性与告警风暴防护（适配现状部署）

| 蓝图要求 | NAS 落地方式 |
|---|---|
| 消息不丢失 | Celery `task_acks_late=True` + 消费端幂等（`dedup_key/fingerprint` 唯一约束，重复投递直接丢弃） |
| 通知可靠性 | 发送任务指数退避重试 ×3 → 按策略降级（email→IM→站内）；渠道健康检查（/api/alerts/status 已有，加自动熔断：连续失败 N 次暂停该渠道 5 分钟） |
| 告警风暴防护 | 聚合 + 抑制 + 频控（Redis 滑动窗口）+ 现有抖动抑制（90s）四层叠加；外部源限流（每 source 每秒上限） |
| 水平扩展 | 告警处理与发送全部进 Celery 队列，worker 可加实例（现状 worker `-c 4` 可调）；引擎无状态（状态全在 PG/Redis） |
| 配置热更新 | 策略/规则表改动即时生效（查询层加 60s Redis 缓存 + 失效广播）；渠道配置沿用 `reset_notification_service()` 机制 |
| 单点防护 | 现有物理机部署单进程 FastAPI：所有重活（发送/扫描）都异步化，进程崩溃由 systemd 拉起；关键状态先写 PG 再发送 |

---

## 8. 分阶段实施路线（映射现有代码改造点）

### 8.0 已完成（v1.1 之前）

| 项 | 内容 | 状态 |
|---|---|---|
| 通知铃铛按账号过滤 | 后端 `system_notification.py` 六个方法去掉 admin 全量可见特权，严格 `user ILIKE <当前登录账号>`；前端三处（铃铛下拉 / 通知中心 / 未读角标）缓存键加用户名 | ✅ 已上线（docker 环境已实测验证） |

### 一期（本次开发，v1.1 组织决策落地）：目标映射 + 组/排班 + 升级到部门经理

> 范围优先级：先把"监控自动故障 → admin + 运维组，超时升级部门经理"这条链跑通，
> 策略表/模板/渠道 DB 化等通用化能力放二期，避免一期范围失控。

| # | 改造点 | 交付物 |
|---|---|---|
| 1 | `app/shared/models.py` + alembic | 新增 `user_group` / `user_group_member`(含 `is_leader`) / `oncall_schedule` / `dispatch_rule` / `escalation_policy` / `notification_log`；`fault_records` + `escalation_level/escalated_at/group_id`；`maintenance_records` + `escalation_level/escalated_at/group_id` |
| 2 | 新 `app/features/groups`（或并入 notifications） | 组 CRUD + 成员管理 API；**seed：运维组 = {admin, 部门经理(is_leader=true)}**；`resolve_oncall(group, at)` 解析器（无排班回退组全员） |
| 3 | `incident_automation.py` | **废弃 `_owner_for` 伪账号**：监控自动故障 `assigned_to` = 运维组值班人（真实账号，无排班时写组名）；`notify_incident()` 目标 = `{admin} ∪ 运维组成员`，站内 + 邮件 + IM 三渠道 |
| 4 | 新 `escalation_service.py` + Celery beat | 每分钟扫描未关闭 critical/major 单：L2 15min 未认领 → 运维组全员 + admin；L3 30min 未处理 → **部门经理** + 生成复盘任务；每次升级写 `notification_log`；维修单以 `sla_deadline` 同套驱动 |
| 5 | `notification_service.py` | `dispatch()` 统一出口（本次内置默认策略：目标集合 × 渠道，策略表二期再接）+ `notification_log` 审计；**六条路径调用点全部切换**（`notify_incident` / `send_fault_assigned_notification` / `send_maintenance_assigned_notification` / `send_maintenance_completed_notification` / `assign_maintenance` / `auto_create_maintenance`）+ `SendAlertAction` 接上通知服务 |
| 6 | `frontend` | 组管理页（运维组 CRUD + 成员/组长）+ 排班视图（最简：手工维护）+ 升级策略配置页（默认三级时长可调）；复用 Users 页面建真实账号 |
| **验收** | ① 触发一个监控自动故障 → admin 与运维组成员（站内+邮件+IM）都收到，`assigned_to` 为真实账号；② 不处理 → 15min 组全员、30min 部门经理，升级链路有 `notification_log` 可查；③ 六条路径通知全部有日志 |

### 二期（策略化通知 + 外部接入）

| 改造点 | 交付物 |
|---|---|
| `app/shared/models.py` | 新增 `notification_channel/notification_policy/notification_template`，渠道配置从 config.yaml 迁 DB（密钥加密）+ alembic |
| `notification_service.py` | `dispatch()` 挂接策略表（级别×事件×组×渠道×模板），替换一期内置默认策略 |
| `app/features/alerts/router.py` | + `POST /api/alerts/webhook/prometheus`（签名鉴权），适配器转 MonitorEvent |
| `app/core/celery_app.py` | + `alerts` 队列 + 重试任务 + beat 渠道健康巡检 |
| `frontend` | AlertSettings 扩展：渠道管理（DB）+ 策略列表/编辑 + 发送日志查询 |
| **验收** | 通知策略可配置、按级别×渠道送达；Alertmanager webhook 进系统自动建故障单 |

### 三期（增强）：治理 + 静默 + 报表

| 改造点 | 交付物 |
|---|---|
| 告警治理 | 聚合 + 抑制（拓扑联动）+ 频控（Redis 滑动窗口），叠加现有去重/抖动抑制 |
| 静默窗口 | 联动 `planned_maintenance` 自动静默/解除 |
| 统计 | 渠道成功率、升级触发次数、组 MTTA/MTTR、SLA 报表（复用 dashboard 组件） |
| 外部源扩展 | zabbix/generic webhook 适配器 |
| **验收** | 维护窗口零误报通知；管理层可看告警治理报表 |

---

## 9. 架构决策要点（避坑清单，结合现状）

1. **统一事件模型是地基，且已经存在**：所有源（含外部）必须转 `MonitorEvent` 再进引擎，
   绝不允许策略层直接消费 Prometheus/Zabbix 原始格式。扩展 `labels/annotations/fingerprint`
   即可，不要新造第二个模型。
2. **通知与分发必须解耦**：现状 `notify_incident()` 已把"站内通知 + 邮件"和"指派给谁"写在一起，
   这是拆分点——通知走 `notification_policy`，指派走 `dispatch_rule`，否则将来改排班/改组会连环爆炸。
3. **排班表是分发的地基**：没有 `oncall_schedule`，分发只能"全组轰炸"，值班体验差且责任不清。
   一期就把表建好，哪怕先人工维护排班。
4. **闭环比通知更重要**：邮件发出只是开始。`FaultRecord` 状态机 + 时间戳 + 复核字段已经很好，
   本方案只补"超时驱动"（escalation），不重复造工单系统。
5. **先做风暴治理再放量通知**：现状已有去重 + 抖动抑制，上线外部源前必须补聚合/频控，
   否则一个交换机组故障就会打爆邮箱，系统立刻失去信任。
6. **渠道配置集中且可审计**：密钥加密入库（`config_encrypted`），发送行为全量落 `notification_log`；
   现状 config.yaml 里的渠道配置保留为 bootstrap 种子，避免敏感信息散落。
7. **升级用超时驱动而非事件驱动**：以 `accepted_at/resolved_at` 的空值 + 阈值判定升级，
   依赖现有状态机时间戳即可，不需要额外的定时事件表。
8. **六条入口必须一个出口**：故障链（监控自动生成（含 3D 大屏展示的活跃故障）、手动创建、
   手动指派、3D 大屏复核/转维修）＋ 维修单链（转维修/AI/工作流建单后的指派、
   手动 assign、维修完成确认）——这六条路径现状各自独立、且缺失严重
   （维修单手动指派和 AI 自动建单目前**零通知**），改造时**必须一次性全部收敛到 `dispatch()`**；
   只改其中几条，必然造成"同一系统里故障/维修通知体验不一致"，且后续排班、
   SLA 升级策略无法全局生效。
9. **站内通知必须指向真实账号（v1.1 已决策）**：环境变量伪账号（`Core Network Admin` 等）
   不是登录账号，铃铛按账号过滤后这类消息无人可见。目标一律由组/排班解析为真实账号：
   监控自动故障 = **admin + 运维组**，超时未处理升级 **部门经理（运维组组长）**；
   伪账号随 `_owner_for` 一起下线，不再进入 `assigned_to`。
