# 网络数字孪生监控大屏 — 完整技术方案 v2

> **架构基线(实际拓扑)**
> - 核心层:2× Cisco C9410,StackWise Virtual(SVL)堆叠 → 逻辑上是 1 台核心
> - 接入层:接入交换机双上行,2 条成员链路 PortChannel 捆绑,分别上联核心-A 与核心-B
> - 整体:星型拓扑,核心居中,接入辐射
>
> **核心目标**:全厂网络节点一眼可见 + 掉线亚分钟级告警 + 故障影响面可视(数字孪生)
>
> **现有地基(保留不重写)**:可达性监控 → WebSocket 推送 → 大屏实时渲染链路已打通
>
> **关键文件索引**
> - 后端监控:app/services/reachability_monitor.py
> - WebSocket:app/features/websocket/router.py
> - 大屏 API:app/features/monitor_screen/router.py、monitor_service.py
> - 数据模型:app/shared/models.py（Device L15、FloorPlan L646、DeviceNode L663）
> - 前端大屏:frontend/src/views/MonitorScreen.vue
> - 启动注册:app/main.py L274

---

## 〇、架构带来的 4 个关键设计决策

| 决策点 | 普通树状方案 | 本项目(SVL+双归属)正确做法 |
|---|---|---|
| 核心怎么画 | 两台独立节点 | 2 台物理核心 + 中间 1 条 SVL 链路,逻辑视为 1 个核心组;可折叠为一个"核心"图标,展开看两台物理机 |
| 接入怎么连父 | 单 parent_node_id | 不能用单父字段;接入有 2 条上联,必须用独立"边表",支持一个节点多条上联 |
| 链路怎么表达 | 一条线 | PortChannel 是逻辑链路,由 2 条成员线组成;画 1 条粗逻辑线,hover 展开看 2 条成员状态 |
| 何时判"掉线连带" | 父断 → 子全断 | 双上联冗余:断 1 条上联=链路降级(黄),2 条全断才=接入失联(红);SVL 单台核心宕 ≠ 全网断 |

> ⚠️ 关键修正:DeviceNode.parent_node_id 单父字段作废,改用独立 device_links 边表,否则无法表达双归属和 PortChannel。

---

## 一、交付优先级总览

| 阶段 | 目标 | 解决的硬伤 | 工作量 |
|---|---|---|---|
| P0-1 | 探测异步并发 + 周期分级 | 实时性假象、规模撑不住 | 中 |
| P0-2 | 拓扑边表 + SVL/PortChannel 建模 | 看不到影响面、单父模型不适配 | 大 |
| P0-3 | 正交折线连线 + 冗余感知影响传播 | 连线乱、误判掉线 | 中大 |
| P1-1 | WS 重连快照对账 | 计数漂移 | 小 |
| P1-2 | 深色 NOC 主题 + 全厂健康条 | 视觉档次 | 中 |
| P1-3 | 筛选框 i18n 清零 | 中文硬编码回潮 | 小 |
| P2-1 | 历史状态回放 | 无时间维度 | 大 |
| P2-2 | 自动拓扑发现(LLDP/CDP) | 手工布线漂移 | 大 |
| P2-3 | 实时指标叠加(利用率/CPU/光功率) | 孪生深度 | 中大 |

---

# P0-1:探测异步并发化 + 周期分级

## 问题
reachability_monitor.py L73 check_all_devices 串行循环,每台 subprocess 起 ping 进程(L188)。叠加 L33 check_interval=300 + L34 failure_threshold=3,最坏 15 分钟才告警。

## 1.1 探测分级字段
app/shared/models.py Device L15 新增:
```python
monitor_tier = Column(String(20), default="normal", index=True)  # critical/normal/low
```
迁移 + 回填规则:
```python
# core_switch (两台9410) → critical (15s)
# 接入交换机 / wlc → normal (60s)
# ap / 其余 → low (300s)
```

## 1.2 并发探测(重写 check_all_devices)
reachability_monitor.py L73:
```python
import asyncio

# __init__ 新增
self.max_concurrency = 50
self.tier_intervals = {"critical": 15, "normal": 60, "low": 300}

async def _check_tier(self, tier: str):
    devices = self._load_devices_by_tier(tier)   # 各自独立查询
    sem = asyncio.Semaphore(self.max_concurrency)

    async def _one(dev):
        async with sem:
            db = next(get_db())                  # ★ 每探测独立 Session,避免并发写冲突
            try:
                await asyncio.to_thread(self.check_device_reachability, db, dev)
            finally:
                db.close()

    await asyncio.gather(*[_one(d) for d in devices], return_exceptions=True)
    cache.invalidate_prefix("dashboard:")
```

## 1.3 调度分级注册
reachability_monitor.py start() L44:
```python
for tier, interval in self.tier_intervals.items():
    self.scheduler.add_job(
        lambda t=tier: asyncio.run(self._check_tier(t)),
        trigger=IntervalTrigger(seconds=interval),
        id=f'reachability_check_{tier}', replace_existing=True,
    )
```

## 1.4 判定阈值分级
_determine_state L300:critical 用 failure_threshold=2(30s 内 2 次失败即告警),normal/low 保持 3。

验收:核心拔线 → 大屏闪红 ≤30s;500 台 critical 单轮 <10s;并发无 DB 报错。

---

# P0-2:拓扑边表 + SVL / PortChannel 建模

## 问题
DeviceNode L663 只有坐标,无连接关系;单父字段无法表达双上联。

## 2.1 废弃单父,改用独立边表
app/shared/models.py 新增:
```python
class DeviceLink(Base):
    """设备链路(边) - 支持双上联、PortChannel、SVL"""
    __tablename__ = "device_links"
    id = Column(Integer, primary_key=True)
    floor_plan_id = Column(Integer, ForeignKey("floor_plans.id", ondelete="CASCADE"), index=True)
    from_node_id = Column(Integer, ForeignKey("device_nodes.id", ondelete="CASCADE"), index=True)  # 下游(接入)
    to_node_id   = Column(Integer, ForeignKey("device_nodes.id", ondelete="CASCADE"), index=True)  # 上游(核心)
    link_role = Column(String(20), default="uplink")   # uplink / svl / portchannel-member
    link_group = Column(String(40), nullable=True)     # 同一 PortChannel 的成员共享一个 group id
    link_type = Column(String(20), default="fiber")    # fiber / ethernet / wireless
    waypoints = Column(Text, nullable=True)            # 正交折线人工拐点 '[{"x":30,"y":40},...]'
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 2.2 你的拓扑如何建模(关键)
- SVL 核心:核心-A、核心-B 两个 DeviceNode + 一条 DeviceLink(link_role='svl') 相连;渲染为"核心组"图标。
- 接入双上联 PortChannel:每台接入交换机建 2 条 DeviceLink:
  - link_role='portchannel-member',link_group='po-<接入设备id>',一条 to_node=核心-A,一条=核心-B;
  - 大屏把同 link_group 的 2 条成员画成 1 条逻辑粗线,hover 展开看 2 条成员状态。

## 2.3 后端拓扑接口
monitor_screen/router.py L133 同级新增:
```python
@router.get("/floor-plans/{plan_id}/topology")
async def get_topology(plan_id: int, db: Session = Depends(get_db)):
    return monitor_service.get_plan_topology(db, plan_id)
```
monitor_service.py 新增 get_plan_topology(),返回:
```json
{
  "nodes": [{ "id", "device_id", "status", "device_type", "x_percent", "y_percent" }],
  "links": [{ "id", "from", "to", "link_role", "link_group", "status" }],
  "groups": [{ "link_group", "member_link_ids", "logical_status" }],
  "impacted_node_ids": [ ... ]
}
```

验收:接口正确返回 SVL 边 + 每台接入的 2 条 PortChannel 成员边,同组聚合。

---

# P0-3:正交折线连线 + 冗余感知影响传播

## 3.1 连线渲染:正交折线(Manhattan),不用直线
规整厂区直线斜穿会乱,改走横平竖直折线,贴合星型布局。

MonitorScreen.vue 在 nodes-overlay(L94)下方叠 SVG 链路层(z-index 低于节点):
```html
<svg class="topo-layer" v-if="imageLoaded">
  <path v-for="link in logicalLinks" :key="link.id"
        :d="orthPath(link)"
        :class="['topo-link', link.link_role, statusClass(link)]" />
</svg>
```
orthPath(link) 生成正交折线:
- 无人工拐点 → 默认"先横后竖"或中点拐弯:M x1,y1 L x1,my L x2,my L x2,y2(my=中点);
- 有 waypoints → 按存储拐点连线,支持人工避障(编辑态拖拽拐点写回 DeviceLink.waypoints)。

降噪三原则(贴合星型,避免毛线感):
1. 正常链路 opacity: 0.2 近乎隐形,只有降级/断链才高亮(黄/红变粗);
2. 连线从节点边缘锚点出线,不穿图标;
3. 同一接入的 2 条 PortChannel 成员默认合并为 1 条逻辑线,只在 hover 展开。

## 3.2 冗余感知的影响传播(最关键的业务逻辑)
不能简单"父断子全断"——存在双上联和 SVL 冗余。_propagate_impact() 规则:

| 故障场景 | 判定结果 | 大屏表现 |
|---|---|---|
| 接入的 1 条上联断(另一条还在) | 链路降级,接入设备不算掉线 | 该 PortChannel 逻辑线变黄,接入节点正常绿 |
| 接入的 2 条上联全断 | 接入设备失联 | 逻辑线变红,接入节点红色闪烁 |
| SVL 单台核心(9410-A)宕 | 全网不中断(SVL 冗余) | 核心-A 节点红,SVL 线红,但下游不连带告警 |
| SVL 两台核心全宕 | 全厂中断 | 核心组红 + 全部下游橙色"影响"脉冲 |
| 设备自身 ICMP 不可达 | 该设备掉线 | 节点红闪 |

前端节点 class(L98)新增 impacted(橙色脉冲,区别于自身 offline 的红闪);WS 事件(handleDeviceStatusChange L455)后重算 impactedNodeIds 与各 link_group 的 logical_status。

验收:断单上联 → 黄降级、设备不报离线;断双上联 → 红、设备失联;单核心宕 → 核心红但下游不连带;双核心宕 → 全网橙。

---

# P1-1:WebSocket 重连快照对账

## 问题
前端 stats 乐观增减(L460-480),断线漏事件 → 漂移。

## 落地
- monitor_screen/router.py 新增 GET /floor-plans/{plan_id}/snapshot,以 Device.reachability(models.py L38)为准返回全量状态;
- MonitorScreen.vue onopen(L441)追加 reconcileSnapshot(),整体覆盖 nodes/stats/offlineAlerts;onMounted 复用同函数初始化。

验收:断网 5 分钟后重连,大屏计数与后端一致;online+offline == 在管总数。

---

# P1-2:深色 NOC 主题 + 全厂健康条

## 问题
当前浅色主题 + 渐变卡片(L1243),挂墙对比不足。

## 落地
- MonitorScreen.vue <style> L1111:根容器加 data-screen-theme="dark",定义大屏专用变量(深底 #0a0e17、在线 #10d98a、离线 #ff3b5b、影响 #ffa116、降级 #ffd60a),KPI 数字 ≥36px;
- screen-header(L4)下方加常驻全厂健康条(跨所有平面图聚合):全厂健康度 98.2% | 设备1240 在线1218 离线22 降级8 影响35 告警14;数据源新增 GET /monitor-screen/global-summary。

验收:切深色高对比,挂墙清晰;健康条跨厂区实时更新。

---

# P1-3:筛选框 i18n 清零

## 问题
MonitorScreen.vue L53-63 硬编码"全部车间/全部类型/交换机"等。

## 落地
逐条改 t(),locales/index.js 加 zh/en:
```js
monitorFilterAllAreas / monitorFilterAllTypes /
deviceTypeSwitch / deviceTypeOfficeSwitch / deviceTypeCoreSwitch / deviceTypeAp / deviceTypeWlc / deviceTypeRouter ...
```
建议统一 deviceTypeLabel(type) 映射,覆盖 models.py L50 全部类型。

验收:切英文无残留;所有 device_type 有译。

---

# P2-1:历史状态回放(time-travel)

- models.py 新增 DeviceStatusEvent(device_id/old_state/new_state/latency_ms/created_at);写入点 reachability_monitor.py _trigger_state_change_alert L340(推 WS 同时落库);
- GET /monitor-screen/floor-plans/{plan_id}/replay?at=<ISO> 重建该时刻状态;
- 大屏底部时间滑块,拖动回放(只读,停 WS 覆盖)。

验收:拖到历史时刻 → 还原当时离线分布。

---

# P2-2:自动拓扑发现(LLDP/CDP)

- 新增 app/services/topology_discovery.py,经 NAPALM/Netmiko(参考 tests/test_netmiko_service.py)采集 LLDP/CDP 邻居,得 (本端,邻居,接口);
- 特别适配本架构:自动识别 PortChannel 成员(同 Po 接口归一组)、识别 SVL 对;自动写入 DeviceLink(P0-2 边表);
- POST /monitor-screen/discover-topology 一键发现;定期对比实测 vs 图上,漂移标黄。

验收:一键发现自动生成 SVL + 双上联连线;改接线后提示漂移。

---

# P2-3:实时指标叠加

- 扩展监控或新增 metrics_collector.py,对 critical 设备 SNMP 采 CPU/接口利用率/光功率,写 device_metrics(初期 SQLite 表,后续接 TSDB);
- 大屏:节点由二态升级为健康度渐变着色;PortChannel 逻辑线粗细/颜色反映聚合利用率;hover 弹 mini 指标卡。

验收:节点按综合健康着色;链路利用率以连线视觉强弱体现。

---

# P2-4:模型尺寸跟随底图等比缩放

## 问题
当前 Monitor3D.vue 中模型尺寸是固定米数（交换机 25m、AP 18m），换不同尺寸底图时比例失调：
- 大底图（1000m）上模型显得很小
- 小底图（100m）上模型显得巨大

相机滚轮缩放（透视投影）下模型与底图同步变化是自动的，真正要改的是：让模型尺寸基于底图尺寸的百分比，而非固定米数。

## 2.1 核心改法：基准尺寸 = 底图尺寸 × 比例系数

```javascript
// 设备基准尺寸 = 底图较小边的百分比
// 例如 1.5% → 1000×562 的底图上，基准约 8.4m；换 200×112 的底图上，基准约 1.7m，比例一致
const DEVICE_SIZE_RATIO = {
  switch: 0.015,      // 占底图短边 1.5%
  core_switch: 0.020, // 核心稍大 2%
  ap: 0.010,          // AP 小一点 1%
  router: 0.014,
  firewall: 0.016,
}

function getDeviceBaseSize(deviceType) {
  const ref = Math.min(plan.real_width_m, plan.real_depth_m)  // 用短边做基准
  const ratio = DEVICE_SIZE_RATIO[deviceType] ?? 0.015
  return ref * ratio
}
```

## 2.2 InstancedMesh 改用基准尺寸构建

Monitor3D.vue `buildDeviceInstances()` 中，把写死的 BoxGeometry 改为 base × 系数：

```javascript
function buildDeviceInstances() {
  const { scene } = ctx.value

  // 按类型分组，每组用各自的 base
  const switches = filteredDevices.value.filter(d =>
    ['office_switch', 'core_switch', 'server_switch', 'uce'].includes(d.device_type)
  )

  if (switches.length > 0) {
    // 交换机基准尺寸
    const base = getDeviceBaseSize('switch')
    const geo = new THREE.BoxGeometry(base * 1.6, base * 0.5, base * 1.1)  // 长×高×宽
    const mat = new THREE.MeshStandardMaterial({ ... })
    const mesh = new THREE.InstancedMesh(geo, mat, switches.length)

    // 离地高度也用 base
    const elevation = base * 0.8

    switches.forEach((d, i) => {
      const node = nodes.value.find(n => n.device_id === d.id)
      if (!node) return
      const w = percentToWorld(node.x_percent, node.y_percent, elevation)
      dummy.position.set(w.x, w.y, w.z)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      // 颜色同前...
    })
    // ...
  }

  // AP 用自己的 base
  const aps = filteredDevices.value.filter(d => d.device_type === 'ap')
  if (aps.length > 0) {
    const base = getDeviceBaseSize('ap')
    const geo = new THREE.BoxGeometry(base * 1.2, base * 0.4, base * 0.8)
    // ...
  }
}
```

这样无论底图真实尺寸是 1000m 还是 100m，模型相对底图始终是同样大小比例。

## 2.3 node.scale 用户个性化缩放叠加

如果 DeviceNode 表有 `scale` 字段（用户在 2D 里设的 0.5–3.0），作为叠加倍数：

```javascript
// 最终尺寸 = 底图比例基准 × 用户缩放
const userScale = Number(node.scale) || 1
// 在 InstancedMesh 的 matrix 里额外乘 scale
dummy.scale.setScalar(userScale)
dummy.updateMatrix()
```

## 2.4 底图切换时重建模型

模型基准依赖 `plan.real_width_m / real_depth_m`，底图切换后必须重建：

```javascript
async function switchPlan(planId) {
  // ...加载新底图数据...

  // 清除旧设备模型
  Object.values(ctx.value.deviceMeshes || {}).forEach(mesh => {
    scene.remove(mesh)
    mesh.geometry?.dispose()
    mesh.material?.dispose()
  })
  ctx.value.deviceMeshes = null

  // 重建（用新底图尺寸重新算 base）
  buildDeviceInstances()
  buildLinks()
  buildLabels()
  fitView()
}
```

## 2.5 可选：远距离最小可见性兜底

纯比例缩放下，相机拉极远时模型可能变成 1–2 像素看不清。若希望"既跟比例、又不消失"，可加屏幕像素下限：

```javascript
const MIN_PX = 18  // 最小 18 像素

function applyMinScreenSize() {
  const { camera, deviceMeshes, host } = ctx.value
  if (!deviceMeshes) return

  Object.values(deviceMeshes).forEach(mesh => {
    mesh.userData.devices?.forEach((d, i) => {
      const dist = camera.position.distanceTo(/* 该实例的世界坐标 */)
      const base = getDeviceBaseSize(d.device_type)
      const userScale = 1  // 或从 node 取
      // 屏幕高度方向每像素对应的世界尺寸
      const worldPerPixel = (dist * Math.tan(THREE.MathUtils.degToRad(camera.fov/2))) / (host.clientHeight/2)
      const minWorld = worldPerPixel * MIN_PX
      const desired = base * userScale
      const finalScale = Math.max(desired, minWorld) / base
      // InstancedMesh 无法逐实例调 scale，只能调整体 mesh 或改用独立 Object3D
    })
  })
}
```

> 建议：默认严格按比例（满足当前需求）；把兜底做成开关，后续需要时再开。InstancedMesh 逐实例缩放受限，若需此功能应改用独立 Object3D 或在 shader 层处理。

## 验收点
| 验收项 | 验证方法 |
|---|---|
| 模型比例一致 | 换一张真实尺寸不同的底图，模型相对底图大小视觉一致 |
| 缩放同步 | 滚轮放大/缩小，模型与底图同步缩放、不脱节 |
| 用户缩放生效 | 调 node.scale（0.5/2.0）模型按倍数变化，仍保持底图比例基准 |
| 远距离可见 | （若开启兜底）拉到最远，模型不消失、仍可点选 |

---

# 实施顺序与风险

## 推荐落地批次
1. P0-1 + P1-1:先把实时性做真 + 计数对账,立刻兑现"掉线即报警"。
   风险:并发探测必须每探测独立 Session(P0-1 已强调),否则并发写报错。
2. P0-2 + P0-3:边表建模 + 折线 + 冗余传播,完成"点位图 → 数字孪生"质变。
   风险:① 影响传播 BFS 防环(SVL 双核心互连本身成环,加 visited 集);② 冗余判定别写成"父断子断",务必按 3.2 表区分降级/失联。
3. P1-2 / P1-3:视觉与 i18n 收尾,可并入任意批次。
4. P2-*:路线图,按资源推进。

## 全局规范(沿用本项目既有约定)
- i18n:新增用户可见文案一律 t() + zh/en 双语,禁止中文硬编码(沿用 useI18n 具名插值 {x})。
- WS 鉴权:/ws/device-status(websocket/router.py L131)当前无认证,P1 补 token 校验。
- 跨线程推送:APScheduler 后台线程必须走 broadcast_device_status_sync L67(主循环已在 main.py L274 注册),并发改造后保持该桥接。
- 迁移:每个加字段配 Alembic 脚本(参考 migrations/versions/)+ 存量回填。
- 数据隔离:设备名/IP/位置是真实业务数据,原样渲染,不翻译。

## 架构特别提示(给开发的话)
> 本网络是 SVL 堆叠核心 + 接入双上联 PortChannel 的冗余星型。整套大屏的价值核心在于正确表达冗余:断一条上联是"降级"不是"故障",单台核心宕是"冗余生效"不是"全网瘫"。故障传播逻辑(P0-3 §3.2)是本方案的灵魂,务必按冗余语义实现,否则会满屏误报,反而比没有拓扑更糟。