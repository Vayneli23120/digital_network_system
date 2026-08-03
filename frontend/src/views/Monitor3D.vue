<template>
  <div class="monitor3d" :class="{ 'fullscreen-mode': isFullscreen, 'panel-hidden': hidePanel, 'edit-mode': isEditMode, 'dark-panel': isDark }">
    <!-- 左：3D 画布 -->
    <div ref="canvasHost" class="canvas-host"
         @dragover.prevent="onCanvasDragOver"
         @drop.prevent="onCanvasDrop"></div>

    <!-- 覆盖层：流量热力图例 / SNMP 采集健康 / 画布右下操作按钮（item 946 切片 7 拆组件） -->
    <HeatLegendPanel :pos="heatPos" :collapsed="!showHeatLegend" :dark="isDark"
      :summary="trafficHeatSummary"
      @start-drag="e => startDrag(e, heatPos, HEAT_PANEL_W)" @toggle="toggleHeatLegend" />
    <SnmpHealthPanel :pos="snmpPos" :collapsed="!showSnmpHealth" :dark="isDark"
      :summary="snmpHealthSummary" :items="snmpHealthItems" :now="snmpHealthNow"
      @start-drag="e => startDrag(e, snmpPos, SNMP_PANEL_W)" @toggle="toggleSnmpHealth"
      @refresh="refreshTrafficHeatLayer" />
    <CanvasToolbar :is-edit-mode="isEditMode" :is-fullscreen="isFullscreen"
      :discovering-neighbors="discoveringNeighbors"
      @toggle-edit-mode="toggleEditMode" @reset-view="resetView" @top-view="topView"
      @discover-neighbors="discoverNeighbors" @upload="showUploadDialog = true"
      @toggle-fullscreen="toggleFullscreen" />

    <!-- 右侧面板展开/收起按钮 -->
    <div class="panel-toggle" @click="hidePanel = !hidePanel">
      <el-icon><ArrowRight v-if="!hidePanel" /><ArrowLeft v-else /></el-icon>
    </div>

    <!-- 上传底图对话框 -->
    <UploadFloorPlanDialog
      v-model="showUploadDialog"
      v-model:plan-name="uploadPlanName"
      :file-name="uploadFileName"
      :uploading="uploading"
      @file-change="handleFileChange"
      @confirm="uploadFloorPlan"
    />

    <!-- 绑定设备对话框 -->
    <BindDeviceDialog
      v-model="showBindDialog"
      v-model:device-id="bindDeviceId"
      :candidates="bindCandidates"
      :submitting="bindSubmitting"
      @cancel="cancelBind"
      @confirm="confirmBindDevice"
    />

    <!-- 链路拐点编辑对话框 -->
    <WaypointEditorDialog
      v-model="showWaypointDialog"
      :title="t('editWaypoints')"
      v-model:waypoints="editingWaypoints"
      @save="saveWaypoints"
    />

    <!-- 主干光缆拐点编辑对话框 -->
    <WaypointEditorDialog
      v-model="showTrunkWaypointDialog"
      :title="t('editWaypoints') + ' - ' + t('fiberTrunk')"
      v-model:waypoints="editingTrunkWaypoints"
      @save="saveTrunkWaypoints"
    />

    <!-- 分支光缆拐点编辑对话框 -->
    <WaypointEditorDialog
      v-model="showBranchLinkWaypointDialog"
      :title="t('editWaypoints') + ' - ' + t('fiberBranchLink')"
      v-model:waypoints="editingBranchLinkWaypoints"
      @save="saveBranchLinkWaypoints"
    />

    <!-- TopoEdge 拐点编辑对话框 -->
    <WaypointEditorDialog
      v-model="showTopoEdgeWaypointDialog"
      :title="t('editWaypoints') + ' - TopoEdge'"
      v-model:waypoints="editingTopoEdgeWaypoints"
      @save="saveTopoEdgeWaypoints"
    />

    <!-- 右：操作面板（玻璃质感）（item 946 切片 8 拆 SidePanel） -->
    <SidePanel
      :dark="isDark"
      :stats="stats"
      :command-summary="commandSummary"
      :monitor-events="monitorEvents"
      :event-window="eventWindow"
      :is-edit-mode="isEditMode"
      :display-cables="displayCables"
      :expanded-trunks="expandedTrunks"
      :expanded-branch-points="expandedBranchPoints"
      :get-branch-points-for-cable="getBranchPointsForCable"
      :get-branch-links-for-topo-node="getBranchLinksForTopoNode"
      :selected-device="selectedDevice"
      :selected-active-fault="selectedActiveFault"
      :selected-fault-needs-review="selectedFaultNeedsReview"
      :fault-action-loading="faultActionLoading"
      :ai-diagnosing="aiDiagnosing"
      :selected-node="selectedNode"
      :offline-devices="offlineDevices"
      :floor-plans="floorPlans"
      :current-plan-id="currentPlanId"
      v-model:filter-type="filterType"
      v-model:filter-status="filterStatus"
      v-model:device-scale="deviceScale"
      v-model:show-physical-topology="showPhysicalTopology"
      v-model:show-data-links="showDataLinks"
      v-model:show-labels="showLabels"
      v-model:floor-tilt-angle="floorTiltAngle"
      v-model:auto-focus-offline="autoFocusOffline"
      @refresh="loadCommandPanelData"
      @focus-incident="focusIncidentEvent"
      @set-event-window="setEventWindow"
      @start-add-trunk="startAddTrunk"
      @start-add-branch-point="startAddBranchPoint"
      @toggle-trunk-expand="toggleTrunkExpand"
      @rename-cable="renameCable"
      @edit-cable-waypoints="editCableWaypoints"
      @delete-cable="deleteCable"
      @toggle-branch-point-expand="toggleBranchPointExpand"
      @rename-branch-point="renameBranchPoint"
      @connect-from-topo-branch="startConnectFromTopoBranch"
      @delete-topo-branch-point="deleteTopoBranchPoint"
      @rename-branch-link="renameBranchLink"
      @open-topo-edge-waypoint="openTopoEdgeWaypointDialog"
      @delete-topo-edge="deleteTopoEdge"
      @review-fault="reviewSelectedFault"
      @open-fault-detail="openSelectedFaultDetail"
      @transfer-fault="transferSelectedFaultToMaintenance"
      @ai-prediagnose="runIncidentAiPrediagnose"
      @update-device-scale="updateDeviceScale"
      @go-to-device-detail="goToDeviceDetail"
      @delete-node="deleteNode"
      @switch-plan="switchPlan"
      @delete-plan="deletePlan"
      @upload="showUploadDialog = true"
      @focus-device="focusDevice"
      @palette-drag-start="onPaletteDragStart"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { authenticatedAxios as axios } from '@/api/request.js'
import { reviewFault, transferFaultToMaintenance, aiPreDiagnoseFault } from '@/api'
import { stampUid } from '@/utils/uid.js'
import { useI18n } from '@/composables/useI18n'
import { useAuthStore } from '@/stores/auth'
import UploadFloorPlanDialog from '@/components/UploadFloorPlanDialog.vue'
import BindDeviceDialog from '@/components/BindDeviceDialog.vue'
import WaypointEditorDialog from '@/components/WaypointEditorDialog.vue'
import HeatLegendPanel from '@/components/HeatLegendPanel.vue'
import SnmpHealthPanel from '@/components/SnmpHealthPanel.vue'
import CanvasToolbar from '@/components/CanvasToolbar.vue'
import SidePanel from '@/components/SidePanel.vue'
import { useOverlayPanels } from '@/composables/useOverlayPanels'
import { useCommandPanel } from '@/composables/useCommandPanel'
import { useDeviceMappings } from '@/composables/useDeviceMappings'
import { useThreeScene } from '@/composables/useThreeScene'
import { useSceneBuilders } from '@/composables/useSceneBuilders'
import { useCanvasInteraction } from '@/composables/useCanvasInteraction'

const router = useRouter()
const authStore = useAuthStore()
const canvasHost = ref(null)
const selectedDevice = ref(null)
const filterType = ref('')
const filterStatus = ref('')
const showLabels = ref(true)
const showPhysicalTopology = ref(true)  // 显示物理拓扑（光纤）
const showDataLinks = ref(true)         // 显示数据链路（设备间连接）
const autoFocusOffline = ref(true)      // 设备离线时自动锁定镜头（默认开）
const floorTiltAngle = ref(0)  // 底图倾斜角度，0=水平，90=垂直
const isFullscreen = ref(false)  // 全屏模式
const { t, currentLang } = useI18n()
const hidePanel = ref(false)  // 隐藏侧边栏
// 覆盖层拖拽/展开收起状态（item 946 切片 7，单实例：reset_panels=1 由首个实例清参）
const { snmpPos, heatPos, showSnmpHealth, showHeatLegend, startDrag, toggleSnmpHealth, toggleHeatLegend, SNMP_PANEL_W, HEAT_PANEL_W } = useOverlayPanels()
// 指挥面板状态（item 946 切片 8，父侧单实例：commandSummary 被场景 buildImpactGlow 共享；getPlanId 惰性取 currentPlanId）
const { commandSummary, monitorEvents, eventWindow, loadCommandSummary, loadMonitorEvents, setEventWindow } = useCommandPanel(() => currentPlanId.value)
// 设备类型/状态标签映射（item 946 切片 8，纯函数：父侧场景 HUD/标签与 SidePanel 模板各调用一次均安全）
const { getDeviceTypeLabelI18n, getStatusLabelI18n, deviceStatus, isDeviceOnline, isDeviceOffline } = useDeviceMappings()

// 上传底图相关
const showUploadDialog = ref(false)
const uploadPlanName = ref('')
const uploadFile = ref(null)
const uploadFileName = ref('')
const uploading = ref(false)

// 绑定设备对话框相关
const showBindDialog = ref(false)
const bindCandidates = ref([])
const bindDeviceId = ref(null)
const bindSubmitting = ref(false)
let pendingPlacement = null  // { deviceType, x_percent, y_percent }

// 链路拐点编辑相关
const showWaypointDialog = ref(false)
const editingLink = ref(null)
const editingWaypoints = ref([])

// 选中节点（用于删除）
const selectedNode = ref(null)

// 设备缩放值（与选中节点同步）
const deviceScale = ref(1)

// 设备数据
const devices = ref([])
const nodes = ref([])
const links = ref([])
const fiberTrunks = ref([])  // 主干光缆（旧数据，面板备用）
const fiberBranchPoints = ref([])  // 分支点（旧数据，面板备用）
const fiberBranchLinks = ref([])  // 分支光缆（旧数据，面板备用）
const devicePaths = ref({})  // 设备路径（沿着光纤拓扑）
const discoveringNeighbors = ref(false)  // 邻居发现进行中
const activeFaults = ref([])  // 监控自动创建的活跃故障
const trafficHeatItems = ref([])
const trafficHeatByDevice = ref(new Map())
const trafficHeatSummary = ref({})
let trafficHeatPollTimer = null
const snmpHealthItems = ref([])
const snmpHealthSummary = ref({})
const snmpHealthNow = ref(null)
const faultActionLoading = ref(false)
const aiDiagnosing = ref(false)

const floorPlans = ref([])
const currentPlan = ref(null)
const currentPlanId = ref(null)

// 从 topoEdges 派生的光缆列表（用于面板显示）
const topoCables = computed(() => {
  // 分支点 junction 节点 id 集合
  const branchPointIds = new Set(
    topoNodes.value
      .filter(n => n.node_kind === 'junction' && n.junction_type === 'branch_point')
      .map(n => n.id)
  )
  const cablesMap = new Map()
  topoEdges.value.forEach(edge => {
    // 跳过 trunk_to_core 类型（这是主干到核心的连接线，不作为独立光缆显示）
    if (edge.cable_type === 'trunk_to_core') return

    // 跳过分支光缆（连接到分支点的 fiber 边）——它们在分支点节点下嵌套显示，不作为顶层光缆，避免重复
    if (edge.cable_type === 'fiber' && (branchPointIds.has(edge.a_node_id) || branchPointIds.has(edge.b_node_id))) return

    // 如果有 cable_id，按 cable_id 聚合
    if (edge.cable_id) {
      if (!cablesMap.has(edge.cable_id)) {
        cablesMap.set(edge.cable_id, {
          cable_id: edge.cable_id,
          cable_no: edge.cable_no || `Cable-${edge.cable_id}`,
          cable_name: edge.cable_name,
          cable_type: edge.cable_type,
          edges: [],
        })
      }
      cablesMap.get(edge.cable_id).edges.push(edge)
    } else {
      // 没有 cable_id 时，按边单独显示（临时方案）
      cablesMap.set(`edge-${edge.id}`, {
        cable_id: `edge-${edge.id}`,  // 用 "edge-{id}" 作为临时 cable_id，保证删除走 topo-edges 接口
        cable_no: edge.cable_name || edge.cable_type,
        cable_name: edge.cable_name,
        cable_type: edge.cable_type,
        edges: [edge],
      })
    }
  })
  return Array.from(cablesMap.values())
})

// 从 topoNodes 派生的分支点列表（用于面板显示）
const topoBranchPoints = computed(() => {
  return topoNodes.value.filter(n => n.node_kind === 'junction' && n.junction_type === 'branch_point')
})

// 优先使用 topo 数据，如果没有则使用旧数据
const displayCables = computed(() => {
  if (topoEdges.value.length > 0) return topoCables.value
  return fiberTrunks.value.map(t => ({
    cable_id: t.id,
    cable_no: t.name || `TRUNK-${t.id}`,
    cable_name: t.name,
    cable_type: 'trunk',
    edges: [],
  }))
})

const displayBranchPoints = computed(() => {
  if (topoNodes.value.length > 0) return topoBranchPoints.value
  return fiberBranchPoints.value
})

// 统计数据
const stats = computed(() => {
  const filtered = filteredDevices.value
  return {
    total: filtered.length,
    online: filtered.filter(isDeviceOnline).length,
    offline: filtered.filter(isDeviceOffline).length,
  }
})

// 离线设备列表
const offlineDevices = computed(() => {
  return devices.value.filter(isDeviceOffline).slice(0, 10)
})

const selectedActiveFault = computed(() => {
  if (!selectedDevice.value) return null
  return getActiveFaultForDevice(selectedDevice.value)
})

// 是否仍需复核：自动创建、尚未被确认/误报的故障才显示确认/误报按钮
const selectedFaultNeedsReview = computed(() => {
  return selectedActiveFault.value?.review_required === true
})

function getActiveFaultForDevice(device) {
  if (!device) return null
  return activeFaults.value.find(f => f.device_id === device.id) || null
}

// 筛选后的设备
const filteredDevices = computed(() => {
  let result = devices.value
  if (filterType.value) {
    if (filterType.value === 'switch') {
      // "交换机"排除核心交换机，避免与"核心交换机"选项重叠
      result = result.filter(d => ['office_switch', 'server_switch', 'uce'].includes(d.device_type))
    } else {
      result = result.filter(d => d.device_type === filterType.value)
    }
  }
  if (filterStatus.value) {
    if (filterStatus.value === 'online') result = result.filter(isDeviceOnline)
    else if (filterStatus.value === 'offline') result = result.filter(isDeviceOffline)
    else result = result.filter(d => deviceStatus(d) === filterStatus.value)
  }
  return result
})

// 标签页和编辑模式
const isEditMode = ref(false)
const selectedTopoEdgeId = ref(null)  // 当前选中的拓扑线（仅其拐点手柄可见）
const isDark = ref(document.documentElement.classList.contains('dark'))

// 光纤主干交互状态
const trunkCreateMode = ref(false)  // 正在创建主干
const trunkStartPoint = ref(null)   // 主干起点
const trunkEndPoint = ref(null)     // 主干终点
const branchPointCreateMode = ref(false)  // 正在添加分支点
const connectFromBranchMode = ref(false)  // 从分支点连接设备模式
const selectedBranchPoint = ref(null)     // 选中的分支点（旧模型）
const selectedTopoBranchPoint = ref(null) // 选中的分支点（新 topo 模型）

// 树形展开状态
const expandedTrunks = reactive({})
const expandedBranchPoints = reactive({})

// 监听全局主题变化（named handler 以便卸载时移除）
const handleThemeChange = (e) => {
  isDark.value = e.detail.dark
}
window.addEventListener('theme-change', handleThemeChange)

// 编辑模式切换时自动禁用/启用轨道控制 + 显示/隐藏拐点
watch(isEditMode, (editMode) => {
  if (ctx.value.controls) {
    ctx.value.controls.enabled = !editMode
  }
  // 重建链路以显示/隐藏拐点球
  if (ctx.value.scene) {
    builders.disposeGroup('links')
    builders.buildLinks()
  }
})

// 新增链路对话框
const showAddLinkDialog = ref(false)
const newLinkSource = ref(null)
const newLinkTarget = ref(null)
const newLinkRole = ref('uplink')
const newLinkType = ref('fiber')

// 编辑模式切换
function toggleEditMode() {
  isEditMode.value = !isEditMode.value
  selectedTopoEdgeId.value = null  // 切换模式时清除拓扑线选中
  if (isEditMode.value) {
    ElMessage.info(t('monitorEditMode') + ' - ' + t('clickDeviceHint'))
    // 进入编辑模式时加载拓扑数据并显示端口锚点
    loadTopoData()
  } else {
    ElMessage.info(t('monitorViewMode'))
    // 退出编辑模式时清除交互状态
    trunkCreateMode.value = false
    trunkStartPoint.value = null
    trunkEndPoint.value = null
    branchPointCreateMode.value = false
    connectFromBranchMode.value = false
    selectedBranchPoint.value = null
    // 取消连线态
    interaction.cancelWiring()
    // 清除端口锚点
    builders.disposeGroup('port-anchors')
    // 重建 TopoEdge（去掉拐点球，保留边线）
    builders.buildTopoEdges()
  }
}

// ============ 光纤主干交互函数 ============

// 开始添加主干
function startAddTrunk() {
  trunkCreateMode.value = true
  trunkStartPoint.value = null
  trunkEndPoint.value = null
  ElMessage.info(t('clickTrunkStart'))
}

// 开始添加分支点
function startAddBranchPoint() {
  branchPointCreateMode.value = true
  ElMessage.info(t('clickTrunkToAddBranch'))
}

// 切换主干展开/收起
function toggleTrunkExpand(trunkId) {
  expandedTrunks[trunkId] = !expandedTrunks[trunkId]
}

// 切换分支点展开/收起
function toggleBranchPointExpand(bpId) {
  expandedBranchPoints[bpId] = !expandedBranchPoints[bpId]
}

// 获取指定光缆关联的分支点（新 topo 模型）
function getBranchPointsForCable(cableId) {
  // 找到该光缆的所有边（兼容没有 cable_id 的情况）
  let cableEdges
  if (typeof cableId === 'number' && !cableId.toString().startsWith('edge-')) {
    // 正常的 cable_id
    cableEdges = topoEdges.value.filter(e => e.cable_id === cableId)
  } else {
    // 临时生成的 cable_id（来自 edge.id）
    const edgeId = parseInt(cableId.toString().replace('edge-', '')) || cableId
    cableEdges = topoEdges.value.filter(e => e.id === edgeId || e.cable_id === cableId)
  }

  // 找到这些边连接的 junction 节点（branch_point 类型）
  const nodeIds = new Set()
  cableEdges.forEach(e => {
    nodeIds.add(e.a_node_id)
    nodeIds.add(e.b_node_id)
  })
  return topoNodes.value.filter(n =>
    n.node_kind === 'junction' &&
    n.junction_type === 'branch_point' &&
    nodeIds.has(n.id)
  )
}

// 获取指定分支点连接的分支光缆（新 topo 模型）
function getBranchLinksForTopoNode(nodeId) {
  return topoEdges.value.filter(e =>
    e.cable_type === 'fiber' &&
    (e.a_node_id === nodeId || e.b_node_id === nodeId)
  )
}

// 开始从分支点连接设备（新 topo 模型）
function startConnectFromTopoBranch(bp) {
  connectFromBranchMode.value = true
  selectedTopoBranchPoint.value = bp
  ElMessage.info(t('clickAnchorToConnect'))
}

// 从 topo 分支点连接设备
async function connectDeviceFromTopoBranch(deviceId, portId = null) {
  if (!selectedTopoBranchPoint.value) return

  try {
    const payload = {
      branch_point_id: selectedTopoBranchPoint.value.id,
      to_device_id: deviceId,
    }
    // 端口锚点 id 可能是字符串占位符（auto-*），仅传递真实数字端口 id
    if (typeof portId === 'number') {
      payload.to_port_id = portId
    }
    await axios.post(`/api/floor-plans/${currentPlanId.value}/topo/branch-cable`, payload)
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()

    // 重置状态
    connectFromBranchMode.value = false
    selectedTopoBranchPoint.value = null
  } catch (e) {
    console.error('连接设备失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 创建主干光缆
async function createFiberTrunk() {
  if (!trunkStartPoint.value || !trunkEndPoint.value) return

  // 起点靠近核心交换机时，自动把主干起点关联到核心设备（后端会生成 trunk_to_core 边）
  const nearbyCore = interaction.findNearbyCoreDevice(trunkStartPoint.value.x, trunkStartPoint.value.y, 5)

  try {
    // 使用新的 topo API 创建主干
    const res = await axios.post(`/api/floor-plans/${currentPlanId.value}/topo/trunk`, {
      name: `TRUNK-${fiberTrunks.value.length + 1}`,
      start_x: trunkStartPoint.value.x,
      start_y: trunkStartPoint.value.y,
      start_device_id: nearbyCore?.device_id,
      end_x: trunkEndPoint.value.x,
      end_y: trunkEndPoint.value.y,
    })
    ElMessage.success(t('msgSaveSuccess'))

    // 重新加载数据
    await loadFiberData()

    // 重置状态
    trunkCreateMode.value = false
    trunkStartPoint.value = null
    trunkEndPoint.value = null
  } catch (e) {
    console.error('创建主干失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 加载光纤数据
async function loadFiberData() {
  try {
    // 加载图模型拓扑数据（Gen3）
    try {
      const nodesRes = await axios.get(`/api/floor-plans/${currentPlanId.value}/topo-nodes`)
      topoNodes.value = nodesRes.data.items || []
      const edgesRes = await axios.get(`/api/floor-plans/${currentPlanId.value}/topo-edges`)
      topoEdges.value = edgesRes.data.items || []
    } catch (e) {
      console.warn('加载 topo-nodes/edges 失败:', e)
    }

    // 设备图寻路路径（Gen3）
    try {
      const topoPathsRes = await axios.get(`/api/floor-plans/${currentPlanId.value}/device-paths`)
      devicePaths.value = {
        ...(topoPathsRes.data?.paths || {}),
        ...(topoPathsRes.data?.neighbor_paths || {}),
      }
      // 诊断：如果后端有诊断信息，优先显示；否则显示通用提示
      if (!devicePaths.value || Object.keys(devicePaths.value).length === 0) {
        const diagnostic = topoPathsRes.data?.diagnostic
        if (diagnostic) {
          ElMessage.info(t('monitor3dLinkDiagnostic', { msg: diagnostic }))
        } else {
          ElMessage.info(t('monitor3dLinkNoData'))
        }
      }
    } catch (e) {
      console.warn('加载 device-paths 失败:', e)
      ElMessage.warning(t('monitor3dLinkLoadFailed'))
      devicePaths.value = {}
    }
    await loadTrafficHeat()

    // 重建光纤渲染（优先使用新 topo 数据）
    builders.disposeGroup('fiber-trunks')
    builders.disposeGroup('branch-points')
    builders.disposeGroup('branch-links')
    builders.disposeGroup('topo-edges')
    builders.disposeGroup('data-link-paths')

    // 使用新的图模型渲染
    builders.buildTopoEdges()
    builders.buildDataLinkPaths()
  } catch (e) {
    console.error('加载光纤数据失败:', e)
  }
}

// 删除光缆（新 topo API）
async function deleteCable(cableId) {
  try {
    // 如果 cable_id 是临时生成的（以 "edge-" 开头），直接删除那条边
    if (typeof cableId === 'string' && cableId.startsWith('edge-')) {
      const edgeId = parseInt(cableId.replace('edge-', ''))
      await axios.delete(`/api/floor-plans/${currentPlanId.value}/topo-edges/${edgeId}`)
    } else {
      await axios.delete(`/api/floor-plans/${currentPlanId.value}/cables/${cableId}`)
    }
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('删除光缆失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 重命名主干光缆（按 cable_id 更新所有分段；edge-xxx 形式更新单条边）
async function renameCable(cable) {
  const current = cable.cable_name || cable.cable_no || ''
  let value
  try {
    const res = await ElMessageBox.prompt(t('renameCablePrompt'), t('actionRename'), {
      confirmButtonText: t('confirm'),
      cancelButtonText: t('cancel'),
      inputValue: current,
      inputValidator: (v) => (v && v.trim() ? true : t('nameRequired')),
    })
    value = res.value.trim()
  } catch {
    return  // 用户取消
  }

  const cableId = cable.cable_id
  try {
    if (typeof cableId === 'string' && cableId.startsWith('edge-')) {
      const edgeId = parseInt(cableId.replace('edge-', ''))
      await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-edges/${edgeId}`, { cable_name: value })
    } else {
      try {
        await axios.put(`/api/floor-plans/${currentPlanId.value}/cables/${cableId}/rename`, { name: value })
      } catch (err) {
        if (err?.response?.status === 409) {
          // 重名，确认后强制
          await ElMessageBox.confirm(t('cableNameDuplicateConfirm'), t('nameDuplicate'), {
            type: 'warning',
            confirmButtonText: t('confirm'),
            cancelButtonText: t('cancel'),
          })
          await axios.put(`/api/floor-plans/${currentPlanId.value}/cables/${cableId}/rename`, { name: value, force: true })
        } else {
          throw err
        }
      }
    }
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    if (e === 'cancel' || e === 'close') return
    console.error('重命名光缆失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 重命名分支点（更新 TopoNode.label）
async function renameBranchPoint(bp) {
  const current = bp.label || `BP-${bp.id}`
  let value
  try {
    const res = await ElMessageBox.prompt(t('renameBranchPointPrompt'), t('actionRename'), {
      confirmButtonText: t('confirm'),
      cancelButtonText: t('cancel'),
      inputValue: current,
      inputValidator: (v) => (v && v.trim() ? true : t('nameRequired')),
    })
    value = res.value.trim()
  } catch {
    return
  }
  try {
    await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-nodes/${bp.id}`, { label: value })
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('重命名分支点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 重命名分支光缆（更新 TopoEdge.cable_name）
async function renameBranchLink(edge) {
  const current = edge.cable_name || `Link-${edge.id}`
  let value
  try {
    const res = await ElMessageBox.prompt(t('renameBranchLinkPrompt'), t('actionRename'), {
      confirmButtonText: t('confirm'),
      cancelButtonText: t('cancel'),
      inputValue: current,
      inputValidator: (v) => (v && v.trim() ? true : t('nameRequired')),
    })
    value = res.value.trim()
  } catch {
    return
  }
  try {
    await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-edges/${edge.id}`, { cable_name: value })
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('重命名分支光缆失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 编辑光缆拐点
function editCableWaypoints(cable) {
  // 找到主干类型的边（trunk 或 trunk_segment）
  const trunkEdge = cable.edges.find(e => e.cable_type === 'trunk' || e.cable_type === 'trunk_segment')
  if (trunkEdge) {
    openTopoEdgeWaypointDialog(trunkEdge)
  } else if (cable.edges.length > 0) {
    // 如果没有 trunk 类型边，编辑第一条边
    openTopoEdgeWaypointDialog(cable.edges[0])
  }
}

// 删除拓扑边（新 topo API）
async function deleteTopoEdge(edgeId) {
  try {
    await axios.delete(`/api/floor-plans/${currentPlanId.value}/topo-edges/${edgeId}`)
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('删除边失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 删除 topo 分支点（连同关联的分支光缆）
async function deleteTopoBranchPoint(nodeId) {
  try {
    await axios.delete(`/api/floor-plans/${currentPlanId.value}/topo-nodes/${nodeId}`)
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('删除分支点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 从分支点连接设备
async function connectDeviceFromBranch(deviceId) {
  if (!selectedBranchPoint.value) return

  try {
    await axios.post(`/api/floor-plans/${currentPlanId.value}/fiber-branch-links`, {
      branch_point_id: selectedBranchPoint.value.id,
      to_device_id: deviceId,
    })
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()

    // 重置状态
    connectFromBranchMode.value = false
    selectedBranchPoint.value = null
  } catch (e) {
    console.error('连接设备失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 在主干上添加分支点（点击 TopoEdge 时）- 使用新的 topo API
async function addBranchPointOnTopoEdge(cableId, clickPos) {
  try {
    await axios.post(`/api/floor-plans/${currentPlanId.value}/topo/branch-point`, {
      trunk_cable_id: cableId,
      x: clickPos.x,
      y: clickPos.y,
      label: `BP-${topoNodes.value.filter(n => n.junction_type === 'branch_point').length + 1}`,
    })
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('添加分支点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 新增链路
async function addLink() {
  if (!newLinkSource.value || !newLinkTarget.value) {
    ElMessage.warning(t('pleaseFillAllFields'))
    return
  }
  try {
    await axios.post(`/api/floor-plans/${currentPlanId.value}/links`, {
      from_node_id: newLinkSource.value,
      to_node_id: newLinkTarget.value,
      link_role: newLinkRole.value,
      link_type: newLinkType.value,
    })
    ElMessage.success(t('msgSaveSuccess'))
    showAddLinkDialog.value = false
    newLinkSource.value = null
    newLinkTarget.value = null
    // 重新加载链路
    const linksRes = await axios.get(`/api/floor-plans/${currentPlanId.value}/links`)
    links.value = linksRes.data.items || []
    // 重建链路
    if (ctx.value.linkLines) {
      ctx.value.scene.remove(ctx.value.linkLines)
      ctx.value.linkLines = null
    }
    builders.buildLinks()
  } catch (e) {
    console.error('新增链路失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 删除链路
async function deleteLink(linkId) {
  try {
    await axios.delete(`/api/floor-plans/${currentPlanId.value}/links/${linkId}`)
    ElMessage.success(t('msgSaveSuccess'))
    links.value = links.value.filter(l => l.id !== linkId)
    // 重建链路
    builders.disposeGroup('links')
    builders.buildLinks()
  } catch (e) {
    console.error('删除链路失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 保存拐点
async function saveWaypoints() {
  if (!editingLink.value) return

  try {
    const waypointsJson = JSON.stringify(editingWaypoints.value)
    await axios.put(`/api/floor-plans/${currentPlanId.value}/links/${editingLink.value.id}`, {
      waypoints: waypointsJson
    })
    ElMessage.success(t('msgSaveSuccess'))

    // 更新本地数据
    const link = links.value.find(l => l.id === editingLink.value.id)
    if (link) {
      link.waypoints = waypointsJson
    }

    // 重建链路
    builders.disposeGroup('links')
    builders.buildLinks()

    showWaypointDialog.value = false
    editingLink.value = null
  } catch (e) {
    console.error('保存拐点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// ============ 主干光缆拐点编辑 ============

const showTrunkWaypointDialog = ref(false)
const editingTrunk = ref(null)
const editingTrunkWaypoints = ref([])

// 分支光缆拐点编辑
const showBranchLinkWaypointDialog = ref(false)
const editingBranchLink = ref(null)
const editingBranchLinkWaypoints = ref([])

// 打开主干拐点编辑对话框
function openTrunkWaypointDialog(trunk) {
  editingTrunk.value = trunk
  try {
    if (typeof trunk.waypoints === 'string') {
      editingTrunkWaypoints.value = (JSON.parse(trunk.waypoints) || []).map(stampUid)
    } else if (Array.isArray(trunk.waypoints)) {
      editingTrunkWaypoints.value = trunk.waypoints.map(stampUid)
    } else {
      editingTrunkWaypoints.value = []
    }
  } catch (e) {
    editingTrunkWaypoints.value = []
  }
  showTrunkWaypointDialog.value = true
}

// 保存主干拐点
async function saveTrunkWaypoints() {
  if (!editingTrunk.value) return

  try {
    const waypointsJson = JSON.stringify(editingTrunkWaypoints.value)
    await axios.put(`/api/floor-plans/${currentPlanId.value}/fiber-trunks/${editingTrunk.value.id}`, {
      waypoints: waypointsJson
    })
    ElMessage.success(t('msgSaveSuccess'))

    // 更新本地数据
    const trunk = fiberTrunks.value.find(t => t.id === editingTrunk.value.id)
    if (trunk) {
      trunk.waypoints = editingTrunkWaypoints.value
    }

    // 重新加载 topo 数据并重建渲染
    await loadTopoData()

    showTrunkWaypointDialog.value = false
    editingTrunk.value = null
  } catch (e) {
    console.error('保存主干拐点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 打开分支光缆拐点编辑对话框
function openBranchLinkWaypointDialog(link) {
  editingBranchLink.value = link
  try {
    if (typeof link.waypoints === 'string') {
      editingBranchLinkWaypoints.value = (JSON.parse(link.waypoints) || []).map(stampUid)
    } else if (Array.isArray(link.waypoints)) {
      editingBranchLinkWaypoints.value = link.waypoints.map(stampUid)
    } else {
      editingBranchLinkWaypoints.value = []
    }
  } catch (e) {
    editingBranchLinkWaypoints.value = []
  }
  showBranchLinkWaypointDialog.value = true
}

// 保存分支光缆拐点
async function saveBranchLinkWaypoints() {
  if (!editingBranchLink.value) return

  try {
    const waypointsJson = JSON.stringify(editingBranchLinkWaypoints.value)
    await axios.put(`/api/floor-plans/${currentPlanId.value}/fiber-branch-links/${editingBranchLink.value.id}`, {
      waypoints: waypointsJson
    })
    ElMessage.success(t('msgSaveSuccess'))

    // 更新本地数据
    const link = fiberBranchLinks.value.find(l => l.id === editingBranchLink.value.id)
    if (link) {
      link.waypoints = waypointsJson
    }

    // 重新加载 topo 数据并重建渲染
    await loadTopoData()

    showBranchLinkWaypointDialog.value = false
    editingBranchLink.value = null
  } catch (e) {
    console.error('保存分支光缆拐点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// ========== TopoEdge 拐点编辑 ==========

const showTopoEdgeWaypointDialog = ref(false)
const editingTopoEdge = ref(null)
const editingTopoEdgeWaypoints = ref([])

// 打开 TopoEdge 拐点编辑对话框
function openTopoEdgeWaypointDialog(edge) {
  editingTopoEdge.value = edge
  try {
    if (typeof edge.waypoints === 'string') {
      editingTopoEdgeWaypoints.value = (JSON.parse(edge.waypoints) || []).map(stampUid)
    } else if (Array.isArray(edge.waypoints)) {
      editingTopoEdgeWaypoints.value = edge.waypoints.map(stampUid)
    } else {
      editingTopoEdgeWaypoints.value = []
    }
  } catch (e) {
    editingTopoEdgeWaypoints.value = []
  }
  showTopoEdgeWaypointDialog.value = true
}

// 保存 TopoEdge 拐点
async function saveTopoEdgeWaypoints() {
  if (!editingTopoEdge.value) return

  try {
    // 后端期望 waypoints 是数组，不是 JSON 字符串
    await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-edges/${editingTopoEdge.value.id}`, {
      waypoints: editingTopoEdgeWaypoints.value
    })
    ElMessage.success(t('msgSaveSuccess'))

    // 更新本地数据
    const edge = topoEdges.value.find(e => e.id === editingTopoEdge.value.id)
    if (edge) {
      edge.waypoints = editingTopoEdgeWaypoints.value
    }

    // 重建拓扑边渲染
    builders.buildTopoEdges()

    showTopoEdgeWaypointDialog.value = false
    editingTopoEdge.value = null
  } catch (e) {
    console.error('保存 TopoEdge 拐点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}
// 删除底图
async function deletePlan(planId) {
  try {
    await axios.delete(`/api/floor-plans/${planId}`)
    ElMessage.success(t('msgSaveSuccess'))
    floorPlans.value = floorPlans.value.filter(p => p.id !== planId)
    if (currentPlanId.value === planId) {
      if (floorPlans.value.length > 0) {
        switchPlan(floorPlans.value[0].id)
      } else {
        currentPlanId.value = null
        currentPlan.value = null
      }
    }
  } catch (e) {
    console.error('删除底图失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 场景状态共享（item 946 切片 9a）：sceneState 由 useThreeScene 创建，供 useSceneBuilders/useCanvasInteraction 共享
const deps = {
  canvasHost, isFullscreen, floorTiltAngle, autoFocusOffline,
  filteredDevices, nodes, selectedDevice, currentPlan,
  devices, links, devicePaths, trafficHeatItems, trafficHeatByDevice,
  commandSummary, showLabels, showDataLinks, isEditMode, selectedTopoEdgeId,
  // 9c：画布交互消费字段（refs + t + deviceMappings + 父回调函数声明，函数 hoisted 无 TDZ）
  selectedNode, currentPlanId,
  trunkCreateMode, trunkStartPoint, trunkEndPoint, branchPointCreateMode,
  connectFromBranchMode, selectedBranchPoint, selectedTopoBranchPoint,
  fiberTrunks, fiberBranchLinks, t,
  deviceMappings: { isDeviceOffline, deviceStatus, getStatusLabelI18n, getDeviceTypeLabelI18n },
  createFiberTrunk, connectDeviceFromTopoBranch, connectDeviceFromBranch,
  addBranchPointOnTopoEdge, openTopoEdgeWaypointDialog,
  loadTopoData, loadFiberData, getActiveFaultForDevice,
}
const three = useThreeScene(deps)
const { sceneState } = three
// 别名：父侧剩余代码照旧引用（对象引用共享，非拷贝；builder/interaction 用到的别名已随 composable 迁走）
const ctx = sceneState.ctx
const plan = sceneState.plan
// 渲染循环逐帧函数组合（必须在 initScene 前赋值：首帧同步执行；builders/interaction 于 setup 后段实例化，箭头闭包运行晚于 setup 无 TDZ）
three.sceneState.frameUpdate = () => {
  builders.pulseOfflineDevices()
  builders.updateOfflineGlow()
  builders.updateImpactGlow()
  builders.pulseOfflineLinks()
  interaction.refreshHoveredHud()
  builders.updateLabelVisibility()
}
// 模板绑定：场景相机/聚焦方法（CanvasToolbar 与 SidePanel 引用）
const { resetView, topView, toggleFullscreen, focusDevice } = three

// 设备库拖拽开始
function onPaletteDragStart(e, type) {
  e.dataTransfer.setData('device-type', type)
  e.dataTransfer.effectAllowed = 'copy'
}

// 画布接收拖拽
function onCanvasDragOver(e) {
  e.dataTransfer.dropEffect = 'copy'
}

// 画布拖放处理
function onCanvasDrop(e) {
  const deviceType = e.dataTransfer.getData('device-type')
  if (!deviceType) return

  const pos = interaction.screenToPercent(e)
  if (!pos) return

  pendingPlacement = { deviceType, ...pos }
  openBindDeviceDialog(deviceType)
}

// 匹配设备类型
function matchType(devType, paletteType) {
  if (paletteType === 'switch')
    return ['switch', 'office_switch', 'server_switch', 'core_switch', 'uce'].includes(devType)
  return devType === paletteType
}

// 打开绑定设备对话框
async function openBindDeviceDialog(deviceType) {
  try {
    const res = await axios.get(`/api/floor-plans/${currentPlanId.value}/available-devices`)
    const items = res.data.items || []
    bindCandidates.value = items.filter(d => !deviceType || matchType(d.device_type, deviceType))
    if (bindCandidates.value.length === 0) {
      ElMessage.warning(t('noAvailableDevices'))
      pendingPlacement = null
      return
    }
    bindDeviceId.value = null
    showBindDialog.value = true
  } catch (e) {
    ElMessage.error(t('loadDataFailed'))
    pendingPlacement = null
  }
}

// 取消绑定
function cancelBind() {
  showBindDialog.value = false
  pendingPlacement = null
}

// 确认绑定设备
async function confirmBindDevice() {
  if (!bindDeviceId.value || !pendingPlacement) return
  if (bindSubmitting.value) return  // 防止双击重复提交
  bindSubmitting.value = true
  try {
    await axios.post(`/api/floor-plans/${currentPlanId.value}/nodes`, {
      device_id: bindDeviceId.value,
      x_percent: Number(pendingPlacement.x_percent.toFixed(2)),
      y_percent: Number(pendingPlacement.y_percent.toFixed(2)),
    })
    ElMessage.success(t('msgSaveSuccess'))
    showBindDialog.value = false
    pendingPlacement = null
    await loadData()
    builders.rebuildScene()
  } catch (e) {
    ElMessage.error(t('msgUpdateFailed'))
  } finally {
    bindSubmitting.value = false
  }
}

// 删除节点
async function deleteNode(nodeId) {
  try {
    await axios.delete(`/api/floor-plans/${currentPlanId.value}/nodes/${nodeId}`)
    ElMessage.success(t('msgSaveSuccess'))
    selectedDevice.value = null
    selectedNode.value = null
    deviceScale.value = 1
    await loadData()
    builders.rebuildScene()
  } catch (e) {
    ElMessage.error(t('msgUpdateFailed'))
  }
}



// 手动触发：对所有启用 SNMP 的设备执行 CDP/LLDP 邻居发现，并重绘拓扑线
async function discoverNeighbors() {
  if (discoveringNeighbors.value) return
  discoveringNeighbors.value = true
  try {
    const res = await axios.post('/api/devices/monitor/discover-neighbors-all')
    const d = res.data || {}
    if (currentPlanId.value) {
      const topoPathsRes = await axios.get(`/api/floor-plans/${currentPlanId.value}/device-paths`)
      devicePaths.value = {
        ...(topoPathsRes.data?.paths || {}),
        ...(topoPathsRes.data?.neighbor_paths || {}),
      }
      await loadTrafficHeat()
      builders.disposeGroup('data-link-paths')
      builders.buildDataLinkPaths()
    }
    ElMessage.success(
      `${t('discoverNeighbors')}: ${d.devices || 0} ${t('hudCheck')} · ` +
      `${t('hudPeer')} ${d.total_found || 0} · ${t('hudUplink')} ${d.total_uplinks_marked || 0}`
    )
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || t('loadDataFailed'))
  } finally {
    discoveringNeighbors.value = false
  }
}

const devicePorts = ref([])    // 设备端口数据
const topoNodes = ref([])      // 拓扑节点数据
const topoEdges = ref([])      // 拓扑边数据

// 9b：拓扑数据 refs 晚声明，追加进共享 deps 供 useSceneBuilders 消费（TDZ 安全）
deps.devicePorts = devicePorts
deps.topoNodes = topoNodes
deps.topoEdges = topoEdges
const builders = useSceneBuilders(sceneState, deps)
// 9c：画布交互 composable（builders 之后实例化；frameUpdate 箭头闭包运行晚于 setup 无 TDZ）
const interaction = useCanvasInteraction(sceneState, deps, builders)
// 模板绑定：设备缩放滑杆（SidePanel emit update-device-scale）
const { updateDeviceScale } = interaction

// 加载设备端口和拓扑数据
async function loadTopoData() {
  try {
    // 先幂等补建所有设备的端口及端口拓扑节点（兼容旧设备），确保连线可用
    await axios.post(`/api/floor-plans/${currentPlanId.value}/ensure-topo-ports`).catch(() => {})
    // 再把自动端口统一为单个锚点（删除旧设备多余的自动端口，手动端口不动）
    await axios.post(`/api/floor-plans/${currentPlanId.value}/normalize-topo-ports`).catch(() => {})

    // 加载设备端口（每个设备一个默认端口）。在客户端为每个端口注入 device_id，
    // 不依赖后端返回该字段，保证端口与设备关联可靠。
    const portsResults = await Promise.all(
      devices.value.map(async d => {
        const r = await axios.get(`/api/devices/${d.id}/ports`).catch(() => ({ data: { items: [] } }))
        return (r.data.items || []).map(p => ({ ...p, device_id: d.id }))
      })
    )
    devicePorts.value = portsResults.flat()

    // 加载拓扑节点和边
    const nodesRes = await axios.get(`/api/floor-plans/${currentPlanId.value}/topo-nodes`)
    topoNodes.value = nodesRes.data.items || []

    const edgesRes = await axios.get(`/api/floor-plans/${currentPlanId.value}/topo-edges`)
    topoEdges.value = edgesRes.data.items || []

    // 构建端口锚点
    builders.buildPortAnchors()
    // 构建 TopoEdge 渲染
    builders.buildTopoEdges()
  } catch (e) {
    console.error('加载拓扑数据失败:', e)
  }
}
// 处理端口锚点点击（开始连线）

// 更新橡皮筋线位置

// 结束连线（创建 TopoEdge）

// 取消连线














// 跳转设备详情
function goToDeviceDetail(deviceId) {
  router.push(`/devices/${deviceId}`)
}

async function loadActiveFaults() {
  try {
    const res = await axios.get('/api/faults', {
      params: {
        status: 'open,assigned,accepted,diagnosing,resolving,transferred',
        limit: 200,
      },
    })
    activeFaults.value = res.data.items || []
  } catch (e) {
    console.warn('加载活跃故障失败:', e)
  }
}

async function loadCommandPanelData() {
  await Promise.all([loadCommandSummary(), loadMonitorEvents()])
  if (ctx.value.scene && nodes.value.length > 0) builders.buildImpactGlow()
}

async function loadTrafficHeat() {
  try {
    const res = await axios.get('/api/monitor3d/traffic-heat', {
      params: currentPlanId.value ? { plan_id: currentPlanId.value } : {},
    })
    const items = res.data?.items || []
    const byDevice = new Map()
    items.forEach(item => {
      if (!item.is_uplink) return
      if (!byDevice.has(item.device_id)) byDevice.set(item.device_id, item)
    })
    trafficHeatItems.value = items
    trafficHeatByDevice.value = byDevice
    trafficHeatSummary.value = res.data?.summary || {}
  } catch (e) {
    console.warn('加载流量热力层失败:', e)
    trafficHeatItems.value = []
    trafficHeatByDevice.value = new Map()
    trafficHeatSummary.value = {}
  }
}

async function loadSnmpHealth() {
  try {
    const res = await axios.get('/api/monitor3d/snmp-health', {
      params: currentPlanId.value ? { plan_id: currentPlanId.value } : {},
    })
    snmpHealthItems.value = res.data?.items || []
    snmpHealthSummary.value = res.data?.summary || {}
    snmpHealthNow.value = res.data?.now || null
  } catch (e) {
    console.warn('加载 SNMP 采集健康失败:', e)
    snmpHealthItems.value = []
    snmpHealthSummary.value = {}
    snmpHealthNow.value = null
  }
}

async function refreshTrafficHeatLayer() {
  await Promise.all([loadTrafficHeat(), loadSnmpHealth()])
  if (!ctx.value.scene || !devicePaths.value || Object.keys(devicePaths.value).length === 0) return
  builders.disposeGroup('data-link-paths')
  builders.buildDataLinkPaths()
}

function startTrafficHeatPoll() {
  stopTrafficHeatPoll()
  trafficHeatPollTimer = setInterval(refreshTrafficHeatLayer, 30_000)
}

function stopTrafficHeatPoll() {
  if (trafficHeatPollTimer) {
    clearInterval(trafficHeatPollTimer)
    trafficHeatPollTimer = null
  }
}
function focusIncidentEvent(event) {
  if (!event?.device_id) return
  const device = devices.value.find(d => d.id === event.device_id)
  if (!device) return
  three.focusDevice(device)
  selectedDevice.value = device
}

async function reviewSelectedFault(falsePositive = false) {
  if (!selectedActiveFault.value) return
  faultActionLoading.value = true
  try {
    await reviewFault(selectedActiveFault.value.id, {
      false_positive: falsePositive,
      notes: falsePositive ? '大屏确认：误报' : '大屏确认：故障已复核',
    })
    ElMessage.success(falsePositive ? t('monitor3dFaultMarkedMisreport') : t('monitor3dFaultConfirmed'))
    await loadActiveFaults()
  } catch (e) {
    console.error('故障复核失败:', e)
    ElMessage.error(t('monitor3dFaultReviewFailed'))
  } finally {
    faultActionLoading.value = false
  }
}

function openSelectedFaultDetail() {
  if (!selectedActiveFault.value?.id) return
  router.push(`/faults/${selectedActiveFault.value.id}`)
}

async function runIncidentAiPrediagnose() {
  if (!selectedActiveFault.value?.id) return
  aiDiagnosing.value = true
  try {
    const res = await aiPreDiagnoseFault(selectedActiveFault.value.id)
    if (res.available) {
      ElMessage.success(t('faultAiDiagnoseDone'))
      await loadActiveFaults()
    } else {
      ElMessage.warning(res.reason || t('faultAiUnavailable'))
    }
  } catch (e) {
    ElMessage.error(t('faultAiDiagnoseFailed'))
  } finally {
    aiDiagnosing.value = false
  }
}

async function transferSelectedFaultToMaintenance() {
  if (!selectedActiveFault.value) return
  faultActionLoading.value = true
  try {
    await transferFaultToMaintenance(selectedActiveFault.value.id, {
      maintenance_type: selectedActiveFault.value.severity === 'critical' ? 'emergency' : 'corrective',
      priority: selectedActiveFault.value.severity === 'critical' ? 'P1' : 'P2',
      description: selectedActiveFault.value.recommendation || selectedActiveFault.value.description || '监控大屏转维修',
      maintenance_owner: selectedActiveFault.value.assigned_to || 'Field Engineer',
    })
    ElMessage.success(t('faultTransferSuccess'))
    await loadActiveFaults()
  } catch (e) {
    console.error('转维修失败:', e)
    ElMessage.error(t('faultTransferFailed'))
  } finally {
    faultActionLoading.value = false
  }
}

// 切换平面图
async function switchPlan(planId) {
  if (!planId) return

  const plan = floorPlans.value.find(p => p.id === planId)
  if (!plan) return

  currentPlan.value = plan

  // 清除旧底图
  const { scene } = ctx.value
  const oldGround = scene?.getObjectByName('ground')
  if (oldGround) {
    scene.remove(oldGround)
    oldGround.geometry?.dispose()
    oldGround.material?.dispose()
  }

  // 重新加载节点（Gen3：链路由 topo-edges 提供）
  try {
    const nodesRes = await axios.get(`/api/floor-plans/${planId}/nodes`)
    nodes.value = nodesRes.data.items || []
    links.value = []

    const topoRes = await axios.get(`/api/floor-plans/${planId}/topology`)
    if (topoRes.data.nodes) nodes.value = topoRes.data.nodes

    // 设备图寻路路径（Gen3）
    try {
      const topoPathsRes = await axios.get(`/api/floor-plans/${planId}/device-paths`)
      devicePaths.value = topoPathsRes.data?.paths || {}
    } catch (e) {
      console.warn('加载 device-paths 失败:', e)
      devicePaths.value = {}
    }
    await loadTrafficHeat()

    // 重建场景
    three.loadFloorPlanTexture()
    builders.rebuildScene()

    // 重置视角
    three.resetView()

    ElMessage.success(`${t('monitorScreenPlanSwitched')}: ${plan.name}`)
  } catch (e) {
    console.error('切换平面图失败:', e)
    ElMessage.error(t('loadDataFailed'))
  }
}

// 文件选择
function handleFileChange(file) {
  uploadFile.value = file.raw
  uploadFileName.value = file.name
}

// 上传底图
async function uploadFloorPlan() {
  if (!uploadPlanName.value || !uploadFile.value) {
    ElMessage.warning(t('pleaseFillAllFields'))
    return
  }

  uploading.value = true

  try {
    const formData = new FormData()
    formData.append('name', uploadPlanName.value)
    formData.append('image', uploadFile.value)

    const res = await axios.post('/api/floor-plans', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    ElMessage.success(t('uploadSuccess'))

    // 清除旧底图
    const { scene } = ctx.value
    const oldGround = scene?.getObjectByName('ground')
    if (oldGround) {
      scene.remove(oldGround)
      oldGround.geometry?.dispose()
      oldGround.material?.dispose()
    }

    // 重新加载平面图列表
    const plansRes = await axios.get('/api/floor-plans')
    floorPlans.value = plansRes.data.items || []

    // 设置当前平面图为新上传的
    const newPlan = floorPlans.value.find(p => p.id === res.data.id) || floorPlans.value[floorPlans.value.length - 1]
    if (newPlan) {
      currentPlan.value = newPlan
      currentPlanId.value = newPlan.id

      // 加载新底图纹理
      three.loadFloorPlanTexture()
    }

    // 关闭对话框
    showUploadDialog.value = false
    uploadPlanName.value = ''
    uploadFile.value = null
    uploadFileName.value = ''

  } catch (e) {
    console.error('上传失败:', e)
    ElMessage.error(t('uploadFailed'))
  } finally {
    uploading.value = false
  }
}

// 加载数据
async function loadData() {
  try {
    // 加载平面图
    const plansRes = await axios.get('/api/floor-plans')
    floorPlans.value = plansRes.data.items || []
    if (floorPlans.value.length > 0) {
      currentPlan.value = floorPlans.value[0]
      currentPlanId.value = floorPlans.value[0].id
    }

    // 加载设备
    const devicesRes = await axios.get('/api/devices')
    devices.value = devicesRes.data.items || devicesRes.data || []
    await loadActiveFaults()
    await loadCommandPanelData()

    // 加载节点
    if (currentPlan.value) {
      const nodesRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/nodes`)
      nodes.value = nodesRes.data.items || []
      links.value = []

      const topoRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/topology`)
      if (topoRes.data.nodes) nodes.value = topoRes.data.nodes

      // 加载图模型拓扑数据（Gen3）
      try {
        const topoNodesRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/topo-nodes`)
        topoNodes.value = topoNodesRes.data.items || []
        const topoEdgesRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/topo-edges`)
        topoEdges.value = topoEdgesRes.data.items || []

        // 加载设备图寻路路径（Gen3）
        const topoPathsRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/device-paths`)
        devicePaths.value = topoPathsRes.data?.paths || {}
        await loadTrafficHeat()
      } catch (e) {
        console.warn('加载 topo-nodes/edges/device-paths 失败:', e)
        devicePaths.value = {}
      }
    }

  } catch (e) {
    console.error('加载数据失败:', e)
    ElMessage.error(t('loadDataFailed'))
  }
}

// 监听筛选变化，重建设备和标签
watch([filterType, filterStatus], () => {
  if (ctx.value.scene) {
    builders.rebuildScene()
  }
})

// 监听编辑模式变化，重建拓扑渲染（显示/隐藏控制点）
watch(isEditMode, () => {
  if (ctx.value.scene) {
    builders.buildTopoEdges()
  }
})

// 监听选中节点变化，同步缩放值
watch(selectedNode, (node) => {
  if (node) {
    deviceScale.value = Number(node.scale) || 1
  } else {
    deviceScale.value = 1
  }
})

// 监听显示控制开关变化，重建拓扑图层
watch([showPhysicalTopology, showDataLinks], () => {
  if (!ctx.value.scene) return

  // 使用 visible 属性控制显隐，不再 dispose+rebuild
  // 物理拓扑
  if (ctx.value.fiberTrunkGroup) {
    ctx.value.fiberTrunkGroup.visible = showPhysicalTopology.value
  }
  if (ctx.value.branchPointGroup) {
    ctx.value.branchPointGroup.visible = showPhysicalTopology.value
  }
  if (ctx.value.branchLinkGroup) {
    ctx.value.branchLinkGroup.visible = showPhysicalTopology.value
  }
  if (ctx.value.topoEdgesGroup) {
    ctx.value.topoEdgesGroup.visible = showPhysicalTopology.value
  }

  // 数据链路（诊断：若用户打开但无数据则提示）
  if (ctx.value.linkLines) {
    ctx.value.linkLines.visible = showDataLinks.value
  }
  if (ctx.value.dataLinkPaths) {
    ctx.value.dataLinkPaths.visible = showDataLinks.value
  }
})

watch(showLabels, (val) => {
  if (ctx.value.labels) {
    ctx.value.labels.visible = val
  }
})

// 语言切换时刷新当前悬浮的 HUD 文案
watch(currentLang, () => {
  interaction.refreshCurrentHud()
})

// 监听底图倾斜角度变化
watch(floorTiltAngle, () => {
  const { scene } = ctx.value
  const ground = scene?.getObjectByName('ground')
  if (ground) {
    // 更新旋转和位置
    const tiltRad = (floorTiltAngle.value / 90) * (Math.PI / 2)
    ground.rotation.x = -Math.PI / 2 + tiltRad

    const tiltFactor = floorTiltAngle.value / 90
    const yPos = tiltFactor * plan.real_depth_m / 2
    const zPos = plan.real_depth_m / 2 - tiltFactor * plan.real_depth_m / 2

    ground.position.set(plan.real_width_m / 2, yPos, zPos)
  }
})
// ===== 设备可达性实时推送（WebSocket /ws/device-status）=====
let deviceStatusWs = null
let deviceStatusWsReconnectTimer = null
let deviceStatusWsClosed = false
let reachabilityPollTimer = null
const REACHABILITY_POLL_INTERVAL = 20000  // 对账轮询间隔（毫秒）

// SNMP 接口状态变化（上行口 up/down）：失效缓存并刷新 HUD/告警
function handleInterfaceStatusChange(msg) {
  if (msg.device_id == null) return
  // 失效该设备的接口缓存，强制下次拉取最新
  sceneState.snmpIfaceCache.delete(msg.device_id)
  for (const key of Array.from(sceneState.snmpTrafficCache.keys())) {
    if (String(key).startsWith(`${msg.device_id}:`)) sceneState.snmpTrafficCache.delete(key)
  }
  // 立即重新拉取（若正悬浮该设备会自动刷新 HUD）
  interaction.fetchDeviceInterfaces(msg.device_id, true)
  interaction.fetchUplinkTrafficSamples(msg.device_id, true)

  const device = devices.value.find(d => d.id === msg.device_id)
  const dName = msg.device_name || device?.name || `#${msg.device_id}`
  const ifName = msg.if_name || `if${msg.if_index}`
  const uplinkTag = msg.is_uplink ? t('monitor3dUplinkTag') : ''
  if (device && (msg.is_uplink || msg.source === 'trap')) {
    three.focusDevice(device)
    interaction.showHudForDevice(device, 6000)
  }
  if (msg.new_status === 'down') {
    ElMessage.error({ message: t('monitor3dIfDown', { tag: uplinkTag, iface: ifName, device: dName }), duration: 5000 })
  } else if (msg.new_status === 'up' && msg.old_status === 'down') {
    ElMessage.success({ message: t('monitor3dIfUp', { tag: uplinkTag, iface: ifName, device: dName }), duration: 4000 })
  }
  loadActiveFaults()
  loadCommandPanelData()
}

function handleDeviceStatusChange(msg) {
  const device = devices.value.find(d => d.id === msg.device_id)
  if (!device) return
  device.reachability = msg.new_state
  device.reachability_latency_ms = msg.latency_ms ?? null
  if (msg.timestamp) device.last_reachability_check = msg.timestamp

  // 刷新 3D 可视化（颜色/标签/链路随可达性变化）
  builders.refreshDeviceVisuals()

  // 若正悬浮该设备，实时刷新 HUD 内容
  interaction.refreshHudForDevice(device)

  // 离线/恢复告警提示
  const label = `${msg.device_name || device.name}（${msg.ip || device.ip}）`
  if (msg.new_state === 'unreachable') {
    ElMessage.error({ message: t('monitor3dDeviceOffline', { label }), duration: 5000 })
    // 自动锁定镜头（去抖：多台同时掉线会合并为框住整片区域，避免镜头乱跳）
    three.scheduleAutoFocusOffline()
  } else if (msg.new_state === 'reachable' && msg.old_state === 'unreachable') {
    ElMessage.success({ message: t('monitor3dDeviceRecovered', { label }), duration: 4000 })
    // 逐台恢复时重新框定剩余离线区域；全部恢复则视角复位
    three.scheduleAutoFocusOffline()
  }
  loadActiveFaults()
  loadCommandPanelData()
}

function connectDeviceStatusWs() {
  try {
    // WebSocket 连接地址：
    // 开发环境：通过 vite 代理（wss://），代理会转发到后端 ws://
    // 生产环境：使用当前 host（前端与后端同域部署）
    // VITE_WS_URL 为可选覆盖（远程访问或后端不同域时设置），缺省按 location.host 拼
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    const base = import.meta.env.VITE_WS_URL || `${proto}://${location.host}`
    const wsUrl = `${base}/ws/device-status`
    deviceStatusWs = new WebSocket(wsUrl)
    deviceStatusWs.onopen = () => {
      deviceStatusWs.send(JSON.stringify({
        action: 'authenticate',
        access_token: authStore.accessToken || undefined
      }))
    }
    deviceStatusWs.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg && msg.event === 'device_status_change') {
          handleDeviceStatusChange(msg)
        } else if (msg && msg.event === 'interface_status_change') {
          handleInterfaceStatusChange(msg)
        }
      } catch (e) { /* 忽略非 JSON 消息 */ }
    }
    deviceStatusWs.onclose = () => {
      if (deviceStatusWsClosed) return
      // 断线自动重连
      deviceStatusWsReconnectTimer = setTimeout(connectDeviceStatusWs, 5000)
    }
    deviceStatusWs.onerror = () => {
      try { deviceStatusWs && deviceStatusWs.close() } catch (e) { /* noop */ }
    }
  } catch (e) {
    console.warn('设备状态 WebSocket 连接失败:', e)
  }
}

function disconnectDeviceStatusWs() {
  deviceStatusWsClosed = true
  if (deviceStatusWsReconnectTimer) {
    clearTimeout(deviceStatusWsReconnectTimer)
    deviceStatusWsReconnectTimer = null
  }
  if (deviceStatusWs) {
    try { deviceStatusWs.close() } catch (e) { /* noop */ }
    deviceStatusWs = null
  }
}

// ===== 可达性对账轮询（WS 安全网：即使漏掉事件，也能在数十秒内自愈）=====
// 解决"设备已恢复但大屏报警未消失"——后端状态切换已完成、不会再发新 WS 事件的情况
async function reconcileDeviceReachability() {
  try {
    const res = await axios.get('/api/devices')
    const items = res.data.items || res.data || []
    const latest = new Map(items.map(d => [d.id, d]))

    let changed = false
    let newlyOffline = false
    let recovered = false
    devices.value.forEach(d => {
      const fresh = latest.get(d.id)
      if (!fresh) return
      if (fresh.reachability !== d.reachability) {
        if (fresh.reachability === 'unreachable' && d.reachability !== 'unreachable') {
          newlyOffline = true
        } else if (d.reachability === 'unreachable' && fresh.reachability !== 'unreachable') {
          recovered = true
        }
        d.reachability = fresh.reachability
        changed = true
      }
      // 同步延迟/检测时间（不触发重建）
      d.reachability_latency_ms = fresh.reachability_latency_ms
      d.last_reachability_check = fresh.last_reachability_check
    })

    if (changed) {
      // 仅在状态真正变化时重建可视化，避免无谓开销
      builders.refreshDeviceVisuals()
      // 新离线或有设备恢复时重新取景（WS 未连通时的兜底）
      // 恢复会重新框定剩余离线区域，全部恢复则复位
      if (newlyOffline || recovered) three.scheduleAutoFocusOffline()
    }
  } catch (e) {
    // 轮询失败静默处理，下个周期重试
  }
}

function startReachabilityPoll() {
  stopReachabilityPoll()
  reachabilityPollTimer = setInterval(reconcileDeviceReachability, REACHABILITY_POLL_INTERVAL)
}

function stopReachabilityPoll() {
  if (reachabilityPollTimer) {
    clearInterval(reachabilityPollTimer)
    reachabilityPollTimer = null
  }
}

onMounted(async () => {
  three.initScene()

  // 场景交互监听（9c：attachSceneListeners 统一接线 wheel/click/mousemove/mousedown）
  interaction.attachSceneListeners(three.sceneState.ctx.value.renderer?.domElement)

  await loadData()
  three.loadFloorPlanTexture()
  builders.buildDeviceModels()
  builders.buildLinks()
  builders.buildLabels()

  // 使用新 topo 数据渲染光纤拓扑
  builders.buildTopoEdges()
  builders.buildDataLinkPaths()
  loadSnmpHealth()

  // 离线设备红色光晕
  builders.buildOfflineGlow()

  // 自动框景 - 延迟执行确保布局稳定
  requestAnimationFrame(() => three.fitView())

  // 订阅设备实时可达性状态变化
  connectDeviceStatusWs()

  // 启动对账轮询（WS 安全网，自愈）
  startReachabilityPoll()

  // 定时刷新流量热力图，避免画布保留旧的高负载颜色/线宽
  startTrafficHeatPoll()

  // 全屏事件监听
  document.addEventListener('fullscreenchange', three.onFullscreenChange)
  document.addEventListener('webkitfullscreenchange', three.onFullscreenChange)
})

onBeforeUnmount(() => {
  // 场景资源释放（rAF/resize/autoFocusDebounceTimer/controls/renderer/scene traverse/glow 纹理/DOM 移交 three.dispose）
  three.dispose()
  // 交互资源释放（画布监听/连线 window 监听/HUD 面板 移交 interaction.dispose；置于 three.dispose 之后 ctx 仍可访问）
  interaction.dispose()
  window.removeEventListener('theme-change', handleThemeChange)

  // 停止对账轮询
  stopReachabilityPoll()

  // 停止流量热力图刷新
  stopTrafficHeatPoll()

  // 断开设备状态 WebSocket
  disconnectDeviceStatusWs()

  // 移除全屏事件监听
  document.removeEventListener('fullscreenchange', three.onFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', three.onFullscreenChange)
})
</script>

<style scoped>
.monitor3d {
  position: relative;
  width: 100%;
  height: 100%;  /* 使用父容器约束，不溢出 */
  background: #0a0e16;
  overflow: hidden;
}

.canvas-host {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  width: 100%;
  height: 100%;
}

.monitor3d.panel-hidden .side-panel {
  transform: translateX(100%);
}

.monitor3d.fullscreen-mode .side-panel {
  display: none;
}

.monitor3d.fullscreen-mode .panel-toggle {
  display: none;
}

/* 侧边栏展开/收起按钮 */
.panel-toggle {
  position: absolute;
  right: 260px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 48px;
  background: rgba(17, 22, 31, 0.65);
  backdrop-filter: blur(12px);
  border-radius: 4px 0 0 4px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-right: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 11;
  transition: right 0.3s ease;
  color: #22d3ee;
}

.monitor3d.panel-hidden .panel-toggle {
  right: 0;
}

/* 明亮模式：panel-toggle 适配 */
.monitor3d:not(.dark-panel) .panel-toggle {
  background: rgba(255, 255, 255, 0.85);
  border-color: rgba(0, 120, 212, 0.2);
  color: #0078d4;
}

.monitor3d.panel-hidden .canvas-tools {
  right: 16px;
}

/* 设备标签样式（CSS2D）- 显示在设备上方 */
:deep(.device-label) {
  padding: 2px 6px;
  background: rgba(26, 34, 48, 0.85);
  border-radius: 3px;
  color: #e5e7eb;
  font-size: 10px;
  white-space: nowrap;
  transition: opacity 0.3s;
  pointer-events: none;
}

:deep(.device-label.online) {
  background: rgba(34, 211, 238, 0.9);
  color: #fff;
}

:deep(.device-label.offline) {
  background: rgba(255, 77, 79, 0.9);
  color: #fff;
  animation: pulse 1s infinite;
}

:deep(.device-label.maintenance) {
  background: rgba(255, 161, 22, 0.9);
  color: #fff;
}

/* ===== 悬浮 HUD 全息玻璃面板 ===== */
:deep(.device-hud) {
  position: relative;
  min-width: 188px;
  padding: 12px 14px 12px;
  transform: translateY(-12px);
  background: linear-gradient(160deg, rgba(8, 22, 36, 0.82), rgba(10, 30, 48, 0.66));
  border: 1px solid rgba(34, 211, 238, 0.55);
  border-radius: 10px;
  box-shadow: 0 0 18px rgba(34, 211, 238, 0.35), inset 0 0 22px rgba(34, 211, 238, 0.08);
  backdrop-filter: blur(8px) saturate(140%);
  -webkit-backdrop-filter: blur(8px) saturate(140%);
  color: #e6f6ff;
  font-size: 11px;
  line-height: 1.5;
  pointer-events: none;
  overflow: hidden;
  /* 默认隐藏，通过 class 控制显示，避免闪烁 */
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.15s ease-out, visibility 0s linear 0.15s;
}
:deep(.device-hud.visible) {
  opacity: 1 !important;
  visibility: visible !important;
  transition: opacity 0.15s ease-out, visibility 0s linear 0s;
}
/* 顶部高亮描边 */
:deep(.device-hud::before) {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 10px;
  padding: 1px;
  background: linear-gradient(120deg, rgba(34, 211, 238, 0.8), rgba(34, 211, 238, 0) 40%, rgba(34, 211, 238, 0) 60%, rgba(34, 211, 238, 0.6));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}
/* 扫描线 */
:deep(.device-hud .hud-scan) {
  position: absolute;
  left: 0; right: 0;
  height: 28px;
  top: -28px;
  background: linear-gradient(180deg, rgba(34, 211, 238, 0) 0%, rgba(34, 211, 238, 0.18) 50%, rgba(34, 211, 238, 0) 100%);
  animation: hudScan 2.6s linear infinite;
  pointer-events: none;
}
:deep(.device-hud .hud-head) {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
:deep(.device-hud .hud-name) {
  color: #ffffff;
  text-shadow: 0 0 8px rgba(34, 211, 238, 0.6);
}
:deep(.device-hud .hud-dot) {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #94a3b8;
  box-shadow: 0 0 8px currentColor;
}
:deep(.device-hud .hud-dot.online) { background: #22d3ee; color: #22d3ee; }
:deep(.device-hud .hud-dot.offline) { background: #ff4d4f; color: #ff4d4f; animation: pulse 1s infinite; }
:deep(.device-hud .hud-dot.unknown) { background: #94a3b8; color: #94a3b8; }
:deep(.device-hud .hud-sub) {
  margin: 2px 0 8px;
  color: #8fd6ee;
  font-size: 10px;
  opacity: 0.85;
}
:deep(.device-hud .hud-grid) {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3px 12px;
  border-top: 1px solid rgba(34, 211, 238, 0.2);
  padding-top: 7px;
}
:deep(.device-hud .hud-k) { color: #7fa8bd; }
:deep(.device-hud .hud-v) { color: #e6f6ff; text-align: right; font-variant-numeric: tabular-nums; }
:deep(.device-hud .hud-v.online) { color: #22d3ee; }
:deep(.device-hud .hud-v.offline) { color: #ff6b6d; }
:deep(.device-hud .hud-v.maintenance) { color: #ffb454; }
:deep(.device-hud .hud-v.unknown) { color: #94a3b8; }
:deep(.device-hud .hud-time) { font-size: 10px; opacity: 0.9; }
:deep(.device-hud .hud-traffic) { font-size: 10px; color: #7dd3fc; letter-spacing: 0.2px; white-space: nowrap; }
:deep(.device-hud .hud-peer) { font-size: 10px; letter-spacing: 0.2px; white-space: nowrap; }
:deep(.device-hud .hud-peer-port) { opacity: 0.7; font-size: 9px; }
:deep(.device-hud .hud-peer-src) { font-size: 8px; opacity: 0.6; border: 1px solid rgba(148,163,184,0.4); border-radius: 3px; padding: 0 3px; margin-left: 2px; }
:deep(.device-hud .hud-v-trend) { padding-top: 2px; }
:deep(.device-hud .hud-trend-wrap) { display: flex; flex-direction: column; gap: 3px; }
:deep(.device-hud .hud-spark) { width: 100%; height: 36px; display: block; overflow: visible; }
:deep(.device-hud .hud-spark .grid) { fill: none; stroke: rgba(148, 163, 184, 0.25); stroke-width: 1; stroke-dasharray: 3 3; }
:deep(.device-hud .hud-spark .in) { fill: none; stroke: #22d3ee; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; filter: drop-shadow(0 0 2px rgba(34, 211, 238, 0.45)); }
:deep(.device-hud .hud-spark .out) { fill: none; stroke: #60a5fa; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; filter: drop-shadow(0 0 2px rgba(96, 165, 250, 0.35)); }
:deep(.device-hud .hud-trend-legend) { display: flex; justify-content: space-between; font-size: 9px; line-height: 1; opacity: 0.85; }
:deep(.device-hud .hud-trend-legend .in) { color: #22d3ee; }
:deep(.device-hud .hud-trend-legend .out) { color: #60a5fa; }

@keyframes hudIn {
  from { opacity: 0; transform: translateY(-4px) scale(0.96); }
  to   { opacity: 1; transform: translateY(-12px) scale(1); }
}
@keyframes hudScan {
  0%   { top: -28px; }
  100% { top: 100%; }
}

/* 拓扑标签样式（CSS2D）- cable_no 和 junction label */
:deep(.topo-label) {
  padding: 2px 8px;
  background: rgba(15, 23, 42, 0.9);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  pointer-events: none;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

:deep(.cable-label) {
  color: #22c55e;
  background: rgba(22, 163, 74, 0.15);
  border-color: rgba(34, 197, 94, 0.5);
}

:deep(.junction-label) {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.5);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* 编辑模式样式 */
.monitor3d.edit-mode .canvas-host {
  cursor: grab;
}

.monitor3d.edit-mode .canvas-host:active {
  cursor: grabbing;
}

</style>
