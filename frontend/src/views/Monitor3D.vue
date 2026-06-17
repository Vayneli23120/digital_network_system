<template>
  <div class="monitor3d" :class="{ 'fullscreen-mode': isFullscreen, 'panel-hidden': hidePanel, 'edit-mode': isEditMode }">
    <!-- 左：3D 画布 -->
    <div ref="canvasHost" class="canvas-host"
         @dragover.prevent="onCanvasDragOver"
         @drop.prevent="onCanvasDrop"></div>

    <!-- 画布右下角操作按钮 -->
    <div class="canvas-tools">
      <!-- 编辑模式状态提示 -->
      <div v-if="isEditMode" class="edit-mode-indicator">
        <el-tag type="warning" size="small">{{ t('monitorEditMode') }}</el-tag>
      </div>
      <!-- 编辑/查看模式切换 -->
      <el-button size="small" :type="isEditMode ? 'warning' : 'primary'" @click="toggleEditMode">
        {{ isEditMode ? t('monitorViewMode') : t('monitorEditMode') }}
      </el-button>
      <el-button size="small" @click="resetView">{{ t('viewReset') }}</el-button>
      <el-button size="small" @click="topView">{{ t('viewTop') }}</el-button>
      <el-button size="small" type="primary" @click="showUploadDialog = true">
        {{ t('uploadFloorPlan') }}
      </el-button>
      <el-button size="small" :type="isFullscreen ? 'warning' : 'default'" @click="toggleFullscreen">
        {{ isFullscreen ? t('exitFullscreen') : t('enterFullscreen') }}
      </el-button>
    </div>

    <!-- 右侧面板展开/收起按钮 -->
    <div class="panel-toggle" @click="hidePanel = !hidePanel">
      <el-icon><ArrowRight v-if="!hidePanel" /><ArrowLeft v-else /></el-icon>
    </div>

    <!-- 新增链路对话框 -->
    <el-dialog v-model="showAddLinkDialog" :title="t('actionAddLink')" width="400px">
      <el-form>
        <el-form-item :label="t('linkSource')">
          <el-select v-model="newLinkSource" :placeholder="t('actionSelect')" size="small" popper-class="dark-select-popper">
            <el-option v-for="node in nodes" :key="node.id" :label="getNodeName(node)" :value="node.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('linkTarget')">
          <el-select v-model="newLinkTarget" :placeholder="t('actionSelect')" size="small" popper-class="dark-select-popper">
            <el-option v-for="node in nodes" :key="node.id" :label="getNodeName(node)" :value="node.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('linkRole')">
          <el-select v-model="newLinkRole" size="small" popper-class="dark-select-popper">
            <el-option :label="t('linkRoleUplink')" value="uplink" />
            <el-option :label="t('linkRoleSvl')" value="svl" />
            <el-option :label="t('linkRolePortchannel')" value="portchannel-member" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('linkType')">
          <el-select v-model="newLinkType" size="small" popper-class="dark-select-popper">
            <el-option :label="t('linkTypeFiber')" value="fiber" />
            <el-option :label="t('linkTypeEthernet')" value="ethernet" />
            <el-option :label="t('linkTypeWireless')" value="wireless" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddLinkDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="addLink">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 上传底图对话框 -->
    <el-dialog v-model="showUploadDialog" :title="t('uploadFloorPlan')" width="400px">
      <el-form>
        <el-form-item :label="t('monitorScreenPlanName')">
          <el-input v-model="uploadPlanName" :placeholder="t('monitorScreenPlanNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('monitorScreenPlanImage')">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*"
            :on-change="handleFileChange"
          >
            <el-button type="primary">{{ t('monitorScreenSelectImage') }}</el-button>
            <template #tip>
              <div class="upload-tip">{{ uploadFileName || t('monitorScreenSelectImage') }}</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="uploadFloorPlan" :loading="uploading">
          {{ t('actionUpload') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 绑定设备对话框 -->
    <el-dialog v-model="showBindDialog" :title="t('bindDeviceTitle')" width="400px">
      <el-select v-model="bindDeviceId" :placeholder="t('monitorScreenSelectDevice')" filterable style="width:100%" popper-class="dark-select-popper">
        <el-option v-for="d in bindCandidates" :key="d.id"
                   :label="`${d.name} (${d.ip || ''})`" :value="d.id" />
      </el-select>
      <template #footer>
        <el-button @click="cancelBind">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="confirmBindDevice">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 链路拐点编辑对话框 -->
    <el-dialog v-model="showWaypointDialog" :title="t('editWaypoints')" width="500px">
      <p class="waypoint-hint">{{ t('waypointHint') }}</p>
      <div class="waypoint-list">
        <div v-for="(wp, idx) in editingWaypoints" :key="idx" class="waypoint-item">
          <span class="waypoint-index">{{ idx + 1 }}</span>
          <el-input-number v-model="wp.x" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointX')" />
          <el-input-number v-model="wp.y" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointY')" />
          <button class="icon-btn danger" :title="t('actionDelete')" @click="removeWaypoint(idx)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
        <div v-if="editingWaypoints.length === 0" class="no-data">
          {{ t('noWaypoints') }}
        </div>
      </div>
      <el-button type="primary" size="small" @click="addWaypoint">
        <el-icon><Plus /></el-icon>
        {{ t('addWaypoint') }}
      </el-button>
      <template #footer>
        <el-button @click="showWaypointDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="saveWaypoints">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 右：操作面板（玻璃质感） -->
    <aside class="side-panel">
      <div class="panel-header">
        <h3>{{ t('monitor3dTitle') }}</h3>
      </div>
      <div class="kpi-row">
        <div class="kpi">
          <span>{{ t('statusOnline') }}</span>
          <b class="online">{{ stats.online }}</b>
        </div>
        <div class="kpi danger">
          <span>{{ t('statusOffline') }}</span>
          <b class="offline">{{ stats.offline }}</b>
        </div>
        <div class="kpi">
          <span>{{ t('deviceTotal') }}</span>
          <b>{{ stats.total }}</b>
        </div>
      </div>

      <!-- 标签页：拓扑/链路/底图 -->
      <el-tabs v-model="sidebarTab" type="border-card" size="small">
        <!-- 拓扑标签页 -->
        <el-tab-pane :label="t('monitorTopology')" name="topology">
          <!-- 设备筛选 -->
          <div class="filter-section">
            <el-select v-model="filterType" :placeholder="t('filterDeviceType')" size="small" clearable popper-class="dark-select-popper">
              <el-option :label="t('monitorFilterAllTypes')" value="" />
              <el-option :label="t('deviceTypeSwitch')" value="switch" />
              <el-option :label="t('deviceTypeCoreSwitch')" value="core_switch" />
              <el-option :label="t('deviceTypeAP')" value="ap" />
            </el-select>
            <el-select v-model="filterStatus" :placeholder="t('filterDeviceStatus')" size="small" clearable popper-class="dark-select-popper">
              <el-option :label="t('filterAllStatus')" value="" />
              <el-option :label="t('statusOnline')" value="online" />
              <el-option :label="t('statusOffline')" value="offline" />
            </el-select>
          </div>

          <!-- 选中设备详情 -->
          <div class="selected-box" v-if="selectedDevice">
            <h4>{{ selectedDevice.name }}</h4>
            <p><strong>IP:</strong> {{ selectedDevice.ip }}</p>
            <p><strong>{{ t('deviceType') }}:</strong> {{ getDeviceTypeLabel(selectedDevice.device_type) }}</p>
            <p><strong>{{ t('deviceStatus') }}:</strong>
              <el-tag :type="selectedDevice.status === 'online' ? 'success' : 'danger'" size="small">
                {{ getStatusLabel(selectedDevice.status) }}
              </el-tag>
            </p>
            <!-- 设备缩放调节 -->
            <div class="scale-control" v-if="selectedNode">
              <span>{{ t('deviceScale') }}:</span>
              <el-slider
                v-model="deviceScale"
                :min="0.2"
                :max="3"
                :step="0.1"
                :show-tooltip="true"
                size="small"
                @change="updateDeviceScale"
              />
              <span class="scale-value">{{ deviceScale.toFixed(1) }}x</span>
            </div>
            <div class="selected-actions">
              <el-button type="primary" size="small" @click="goToDeviceDetail(selectedDevice.id)">
                {{ t('viewDetail') }}
              </el-button>
              <el-button type="danger" size="small" v-if="selectedNode" @click="deleteNode(selectedNode.id)">
                {{ t('actionDelete') }}
              </el-button>
            </div>
          </div>
          <div v-else class="hint">
            <el-icon><Pointer /></el-icon>
            <span>{{ t('clickDeviceHint') }}</span>
          </div>

          <!-- 图层控制 -->
          <div class="layer-control">
            <h4>{{ t('layerControl') }}</h4>
            <el-checkbox v-model="showLabels">{{ t('showLabels') }}</el-checkbox>
            <el-checkbox v-model="showLinks">{{ t('showLinks') }}</el-checkbox>
            <div class="tilt-control">
              <span>{{ t('floorPlanTilt') }}:</span>
              <el-slider v-model="floorTiltAngle" :min="0" :max="90" :step="5" :show-tooltip="true" size="small" />
              <span class="tilt-value">{{ floorTiltAngle }}°</span>
            </div>
          </div>

          <!-- 告警列表 -->
          <div class="alert-section">
            <h4>{{ t('alertList') }}</h4>
            <div class="alert-list">
              <div
                v-for="alert in offlineDevices"
                :key="alert.id"
                class="alert-item"
                @click="focusDevice(alert)"
              >
                <el-icon class="alert-icon"><Warning /></el-icon>
                <span class="alert-name">{{ alert.name }}</span>
              </div>
              <div v-if="offlineDevices.length === 0" class="no-alert">
                {{ t('noOfflineDevices') }}
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 链路标签页 -->
        <el-tab-pane :label="t('deviceLinks')" name="links">
          <button class="panel-action-btn" @click="showAddLinkDialog = true">
            <el-icon><Plus /></el-icon>
            <span>{{ t('actionAddLink') }}</span>
          </button>
          <div class="link-list">
            <div v-for="link in links" :key="link.id" class="link-item">
              <span class="link-info">{{ getLinkLabel(link) }}</span>
              <span class="link-role-badge" :data-role="link.link_role">{{ link.link_role }}</span>
              <div class="link-actions">
                <button class="icon-btn" :title="t('editWaypoints')" @click="openWaypointDialog(link)">
                  <el-icon><Connection /></el-icon>
                </button>
                <button class="icon-btn danger" :title="t('actionDelete')" @click="deleteLink(link.id)">
                  <el-icon><Delete /></el-icon>
                </button>
              </div>
            </div>
            <div v-if="links.length === 0" class="no-data">
              {{ t('noData') }}
            </div>
          </div>
        </el-tab-pane>

        <!-- 底图标签页 -->
        <el-tab-pane :label="t('floorPlans')" name="plans">
          <button class="panel-action-btn" @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            <span>{{ t('uploadFloorPlan') }}</span>
          </button>
          <div class="plan-list">
            <div v-for="plan in floorPlans" :key="plan.id" class="plan-item" :class="{ active: plan.id === currentPlanId }">
              <el-icon class="plan-icon"><Picture /></el-icon>
              <span class="plan-name">{{ plan.name }}</span>
              <span v-if="plan.id === currentPlanId" class="plan-badge">{{ t('statusLive') }}</span>
              <div class="plan-actions">
                <button v-if="plan.id !== currentPlanId" class="icon-btn" :title="t('actionSwitchPlan')" @click="switchPlan(plan.id)">
                  <el-icon><Switch /></el-icon>
                </button>
                <button class="icon-btn danger" :title="t('actionDeletePlan')" @click="deletePlan(plan.id)">
                  <el-icon><Delete /></el-icon>
                </button>
              </div>
            </div>
            <div v-if="floorPlans.length === 0" class="no-data">
              {{ t('noData') }}
            </div>
          </div>
        </el-tab-pane>

        <!-- 设备库标签页 -->
        <el-tab-pane :label="t('deviceLibrary')" name="devices">
          <div class="hint">
            <span>{{ t('dragDeviceHint') }}</span>
          </div>
          <div class="device-palette">
            <div class="palette-item" draggable="true"
                 v-for="item in deviceTemplates" :key="item.type"
                 @dragstart="onPaletteDragStart($event, item.type)">
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ t(item.labelKey) }}</span>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </aside>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, shallowRef, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { ElMessage } from 'element-plus'
import { Pointer, Warning, Upload, FullScreen, Close, ArrowLeft, ArrowRight, Plus, Delete, Switch, Picture, Box, Position, Connection, Lock, Cpu } from '@element-plus/icons-vue'
import axios from 'axios'
import { t } from '@/locales'

const router = useRouter()
const canvasHost = ref(null)
const selectedDevice = ref(null)
const filterType = ref('')
const filterStatus = ref('')
const showLabels = ref(true)
const showLinks = ref(true)
const floorTiltAngle = ref(0)  // 底图倾斜角度，0=水平，90=垂直
const isFullscreen = ref(false)  // 全屏模式
const hidePanel = ref(false)  // 隐藏侧边栏

// 上传底图相关
const showUploadDialog = ref(false)
const uploadPlanName = ref('')
const uploadFile = ref(null)
const uploadFileName = ref('')
const uploading = ref(false)

// 设备库模板
const deviceTemplates = [
  { type: 'switch',   icon: Box,        labelKey: 'deviceTypeSwitch' },
  { type: 'ap',       icon: Position,   labelKey: 'deviceTypeAP' },
  { type: 'router',   icon: Connection, labelKey: 'deviceTypeRouter' },
  { type: 'firewall', icon: Lock,       labelKey: 'deviceTypeFirewall' },
]

// 绑定设备对话框相关
const showBindDialog = ref(false)
const bindCandidates = ref([])
const bindDeviceId = ref(null)
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
const floorPlans = ref([])
const currentPlan = ref(null)
const currentPlanId = ref(null)

// 统计数据
const stats = computed(() => {
  const filtered = filteredDevices.value
  return {
    total: filtered.length,
    online: filtered.filter(d => d.status === 'online').length,
    offline: filtered.filter(d => d.status === 'offline').length,
  }
})

// 离线设备列表
const offlineDevices = computed(() => {
  return devices.value.filter(d => d.status === 'offline').slice(0, 10)
})

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
    result = result.filter(d => d.status === filterStatus.value)
  }
  return result
})

// 设备类型/状态中文映射
const deviceTypeMap = {
  'office_switch': '办公交换机',
  'core_switch': '核心交换机',
  'server_switch': '服务器交换机',
  'uce': 'UCE',
  'ap': 'AP',
  'wlc': '无线控制器',
  'router': '路由器',
  'firewall': '防火墙',
}

const statusMap = {
  'online': '在线',
  'offline': '离线',
  'maintenance': '维护中',
}

function getDeviceTypeLabel(type) {
  return deviceTypeMap[type] || type
}

function getStatusLabel(status) {
  return statusMap[status] || status
}

// 标签页和编辑模式
const sidebarTab = ref('topology')
const isEditMode = ref(false)

// 编辑模式切换时自动禁用/启用轨道控制 + 显示/隐藏拐点
watch(isEditMode, (editMode) => {
  if (ctx.value.controls) {
    ctx.value.controls.enabled = !editMode
  }
  // 重建链路以显示/隐藏拐点球
  if (ctx.value.scene) {
    disposeGroup('links')
    buildLinks()
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
  if (isEditMode.value) {
    ElMessage.info(t('monitorEditMode') + ' - ' + t('clickDeviceHint'))
  } else {
    ElMessage.info(t('monitorViewMode'))
  }
}

// 获取节点名称
function getNodeName(node) {
  const device = devices.value.find(d => d.id === node.device_id)
  return device ? device.name : `Node ${node.id}`
}

// 获取链路标签
function getLinkLabel(link) {
  const fromNode = nodes.value.find(n => n.id === link.from_node_id)
  const toNode = nodes.value.find(n => n.id === link.to_node_id)
  const fromName = fromNode ? getNodeName(fromNode) : '?'
  const toName = toNode ? getNodeName(toNode) : '?'
  return `${fromName} → ${toName}`
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
    buildLinks()
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
    disposeGroup('links')
    buildLinks()
  } catch (e) {
    console.error('删除链路失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 打开拐点编辑对话框
function openWaypointDialog(link) {
  editingLink.value = link
  try {
    editingWaypoints.value = link.waypoints ? JSON.parse(link.waypoints) : []
  } catch (e) {
    editingWaypoints.value = []
  }
  showWaypointDialog.value = true
}

// 添加拐点
function addWaypoint() {
  editingWaypoints.value.push({ x: 50, y: 50 })
}

// 移除拐点
function removeWaypoint(idx) {
  editingWaypoints.value.splice(idx, 1)
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
    disposeGroup('links')
    buildLinks()

    showWaypointDialog.value = false
    editingLink.value = null
  } catch (e) {
    console.error('保存拐点失败:', e)
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

// 用 shallowRef 持有 three 对象，避免 Vue 深度响应式代理
const ctx = shallowRef({
  scene: null,
  camera: null,
  renderer: null,
  labelRenderer: null,
  controls: null,
  deviceGroup: null,
  linkLines: null,
  labels: null,
})

// 厂区真实尺寸（米）
const plan = {
  real_width_m: 1000,
  real_depth_m: 562.5,
  wall_height_m: 3
}

let raf = 0
const raycaster = new THREE.Raycaster()
const pointer = new THREE.Vector2()

// 颜色映射
const COLORS = {
  online: new THREE.Color(0x22d3ee),    // 青色
  offline: new THREE.Color(0xff4d4f),   // 红色
  maintenance: new THREE.Color(0xffa116), // 橙色
}

// 设备尺寸比例系数 - 基于底图短边的百分比（调小以适应放大底图）
const DEVICE_SIZE_RATIO = {
  switch: 0.008,       // 交换机占底图短边 0.8%
  core_switch: 0.010,  // 核心交换机 1%
  ap: 0.005,           // AP 0.5%
  server_switch: 0.008,
  uce: 0.008,
  router: 0.007,
  firewall: 0.008,
  wlc: 0.010,
}

// 计算设备基准尺寸（基于底图尺寸）
function getDeviceBaseSize(deviceType) {
  const ref = Math.min(plan.real_width_m, plan.real_depth_m)  // 用短边做基准
  const ratio = DEVICE_SIZE_RATIO[deviceType] ?? 0.015
  return ref * ratio
}

// 状态颜色映射
const STATUS_COLOR = { online: 0x22d3ee, offline: 0xff4d4f, maintenance: 0xffa116 }

// 复用的 emissive 颜色常量（避免每次 new THREE.Color）
const EMISSIVE_ON = new THREE.Color(0x333333)
const EMISSIVE_OFF = new THREE.Color(0x000000)

// 创建立体设备模型（基于底图比例）
function createDeviceModel(deviceType, status = 'online') {
  const group = new THREE.Group()
  const base = getDeviceBaseSize(deviceType)
  const color = STATUS_COLOR[status] || STATUS_COLOR.online
  const bodyMat = new THREE.MeshStandardMaterial({ color, metalness: 0.4, roughness: 0.5 })
  const accentMat = new THREE.MeshStandardMaterial({ color: 0x1a2230, metalness: 0.6, roughness: 0.4 })

  switch (deviceType) {
    case 'ap': {
      const r = base * 0.6
      const baseMesh = new THREE.Mesh(new THREE.CylinderGeometry(r, r, base * 0.25, 24), bodyMat)
      const dome = new THREE.Mesh(
        new THREE.SphereGeometry(r * 0.7, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), bodyMat)
      dome.position.y = base * 0.15
      group.add(baseMesh, dome)
      break
    }
    case 'router': {
      const body = new THREE.Mesh(new THREE.BoxGeometry(base * 1.4, base * 0.4, base * 1.0), bodyMat)
      group.add(body)
      for (let i = -1; i <= 1; i++) {
        const ant = new THREE.Mesh(new THREE.CylinderGeometry(base * 0.04, base * 0.04, base * 0.8), accentMat)
        ant.position.set(i * base * 0.4, base * 0.6, -base * 0.4)
        group.add(ant)
      }
      break
    }
    case 'firewall': {
      const body = new THREE.Mesh(new THREE.BoxGeometry(base * 1.4, base * 0.8, base * 1.0),
        new THREE.MeshStandardMaterial({ color: 0xff4d4f, metalness: 0.4, roughness: 0.5 }))
      const panel = new THREE.Mesh(new THREE.BoxGeometry(base * 1.42, base * 0.15, base * 0.03), accentMat)
      panel.position.set(0, base * 0.1, base * 0.5)
      group.add(body, panel)
      break
    }
    default: { // switch / core_switch / server_switch / uce
      const body = new THREE.Mesh(new THREE.BoxGeometry(base * 1.6, base * 0.5, base * 1.1), bodyMat)
      const ports = new THREE.Mesh(new THREE.BoxGeometry(base * 1.4, base * 0.12, base * 0.03), accentMat)
      ports.position.set(0, -base * 0.05, base * 0.56)
      group.add(body, ports)
    }
  }

  group.userData.deviceType = deviceType
  return group
}

// 屏幕坐标 → 百分比坐标（射线求交）
function screenToPercent(e) {
  const { camera, renderer } = ctx.value
  const rect = renderer.domElement.getBoundingClientRect()
  const ndc = new THREE.Vector2(
    ((e.clientX - rect.left) / rect.width) * 2 - 1,
    -((e.clientY - rect.top) / rect.height) * 2 + 1
  )
  const ray = new THREE.Raycaster()
  ray.setFromCamera(ndc, camera)
  const ground = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
  const hit = new THREE.Vector3()
  if (!ray.ray.intersectPlane(ground, hit)) return null
  return {
    x_percent: Math.max(0, Math.min(100, (hit.x / plan.real_width_m) * 100)),
    y_percent: Math.max(0, Math.min(100, (hit.z / plan.real_depth_m) * 100)),
  }
}

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

  const pos = screenToPercent(e)
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
    rebuildScene()
  } catch (e) {
    ElMessage.error(t('msgUpdateFailed'))
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
    rebuildScene()
  } catch (e) {
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 更新设备缩放
async function updateDeviceScale(newScale) {
  if (!selectedNode.value) return

  try {
    await axios.put(`/api/floor-plans/${currentPlanId.value}/nodes/${selectedNode.value.id}`, {
      scale: Number(newScale.toFixed(2)),
    })
    ElMessage.success(t('msgSaveSuccess'))

    // 更新本地 nodes 数据
    const node = nodes.value.find(n => n.id === selectedNode.value.id)
    if (node) {
      node.scale = newScale
      selectedNode.value = { ...node }
    }

    // 更新模型缩放
    if (selectedModel) {
      selectedModel.scale.setScalar(newScale)
    }
  } catch (e) {
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 坐标转换：百分比 → 世界坐标（米）
function percentToWorld(xPercent, yPercent, elevation = 0) {
  const x = (Number(xPercent) / 100) * plan.real_width_m
  const z = (Number(yPercent) / 100) * plan.real_depth_m
  return { x, y: elevation, z }
}

// 自定义滚轮缩放处理函数（需要保存引用以便清理）
function handleWheel(e) {
  e.preventDefault()

  // 编辑模式下禁用滚轮缩放，防止视角乱动
  if (isEditMode.value) return

  const { camera, controls } = ctx.value

  // 计算鼠标在场景中的位置
  const rect = ctx.value.renderer.domElement.getBoundingClientRect()
  const mouseX = ((e.clientX - rect.left) / rect.width) * 2 - 1
  const mouseY = -((e.clientY - rect.top) / rect.height) * 2 + 1

  // 射线投射到地面（y=0）
  const raycasterLocal = new THREE.Raycaster()
  raycasterLocal.setFromCamera({ x: mouseX, y: mouseY }, camera)

  // 创建一个水平面用于计算交点
  const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0)
  const intersectPoint = new THREE.Vector3()
  raycasterLocal.ray.intersectPlane(groundPlane, intersectPoint)

  if (intersectPoint) {
    // 缩放因子
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    const minDist = 30
    const maxDist = 3000

    // 当前相机到target的距离
    const currentDist = camera.position.distanceTo(controls.target)
    const newDist = Math.max(minDist, Math.min(maxDist, currentDist * (1 / delta)))

    // 以鼠标位置为中心缩放
    const direction = camera.position.clone().sub(controls.target).normalize()
    const offset = intersectPoint.clone().sub(controls.target)

    // 新的target位置（向鼠标位置移动）
    const factor = (newDist - currentDist) / currentDist
    controls.target.add(offset.multiplyScalar(factor * 0.5))

    // 新的相机位置
    camera.position.copy(controls.target).add(direction.multiplyScalar(newDist))
  }
}

// 初始化场景
function initScene() {
  const host = canvasHost.value
  const W = host.clientWidth
  const H = host.clientHeight

  // 场景
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x0a0e16)

  // 相机
  const camera = new THREE.PerspectiveCamera(50, W / H, 0.1, 8000)
  camera.position.set(plan.real_width_m / 2, 700, plan.real_depth_m + 700)

  // WebGL 渲染器
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(W, H)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  host.appendChild(renderer.domElement)

  // CSS2D 标签渲染器
  const labelRenderer = new CSS2DRenderer()
  labelRenderer.setSize(W, H)
  labelRenderer.domElement.style.position = 'absolute'
  labelRenderer.domElement.style.top = '0'
  labelRenderer.domElement.style.pointerEvents = 'none'
  host.appendChild(labelRenderer.domElement)

  // 轨道控制
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
  controls.maxPolarAngle = Math.PI / 2.05
  controls.minDistance = 30
  controls.maxDistance = 3000
  controls.enablePan = true  // 允许平移
  controls.panSpeed = 1.5    // 平移速度
  controls.zoomSpeed = 1.2   // 缩放速度
  controls.enableZoom = false // 禁用默认滚轮缩放，使用自定义的
  controls.mouseButtons = {
    LEFT: THREE.MOUSE.PAN,     // 左键平移
    MIDDLE: THREE.MOUSE.DOLLY, // 中键缩放
    RIGHT: THREE.MOUSE.ROTATE  // 右键旋转
  }

  // 灯光
  scene.add(new THREE.AmbientLight(0xffffff, 0.7))
  const dir = new THREE.DirectionalLight(0xffffff, 0.8)
  dir.position.set(100, 200, 100)
  scene.add(dir)

  // 地面网格（已隐藏）
  // const gridHelper = new THREE.GridHelper(plan.real_width_m, 50, 0x1a2230, 0x1a2230)
  // gridHelper.position.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
  // scene.add(gridHelper)

  // 保存上下文
  Object.assign(ctx.value, { scene, camera, renderer, labelRenderer, controls, host })

  // 注册滚轮事件（使用提取的函数以便清理）
  renderer.domElement.addEventListener('wheel', handleWheel, { passive: false })

  // 动画循环
  const animate = () => {
    raf = requestAnimationFrame(animate)
    controls.update()

    // 离线设备呼吸动画
    pulseOfflineDevices()

    // 根据相机距离更新标签可见性
    updateLabelVisibility()

    renderer.render(scene, camera)
    labelRenderer.render(scene, camera)
  }
  animate()

  // 点击事件（查看模式选中）
  renderer.domElement.addEventListener('click', onCanvasClick)

  // 鼠标按下事件（编辑模式拖动起点）
  renderer.domElement.addEventListener('mousedown', onCanvasMouseDown)

  // 窗口大小变化
  window.addEventListener('resize', onResize)
}

// 窗口大小变化处理
function onResize() {
  const { camera, renderer, labelRenderer, host } = ctx.value
  if (!host) return
  const W = host.clientWidth
  const H = host.clientHeight
  camera.aspect = W / H
  camera.updateProjectionMatrix()
  renderer.setSize(W, H)
  labelRenderer.setSize(W, H)
}

// 视角复位
function resetView() {
  fitView()
}

// 俯视图
function topView() {
  const { camera, controls } = ctx.value
  camera.position.set(plan.real_width_m / 2, 500, plan.real_depth_m / 2 + 0.1)
  controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
}

// 自动框景 - 根据底图尺寸和画布宽高比计算合适的相机距离
function fitView() {
  const { camera, controls } = ctx.value
  if (!camera) return

  const fovV = THREE.MathUtils.degToRad(camera.fov)            // 垂直 FOV
  const aspect = camera.aspect || 1

  // 垂直方向需要的距离（按底图"深度"）
  const distV = (plan.real_depth_m / 2) / Math.tan(fovV / 2)
  // 水平方向需要的距离（按底图"宽度"，换算水平 FOV）
  const fovH = 2 * Math.atan(Math.tan(fovV / 2) * aspect)
  const distH = (plan.real_width_m / 2) / Math.tan(fovH / 2)

  const dist = Math.max(distV, distH) * 1.05  // 取大者保证完整可见，1.05 微留边

  // 略微俯视角度（0.6 越小越接近俯视）
  camera.position.set(plan.real_width_m / 2, dist * 0.6, plan.real_depth_m / 2 + dist * 0.8)
  controls.target.set(plan.real_width_m / 2, 0, plan.real_depth_m / 2)
}

// 全屏切换
function toggleFullscreen() {
  if (!isFullscreen.value) {
    // 进入全屏
    const elem = document.querySelector('.monitor3d')
    if (elem.requestFullscreen) {
      elem.requestFullscreen()
    } else if (elem.webkitRequestFullscreen) {
      elem.webkitRequestFullscreen()
    } else if (elem.msRequestFullscreen) {
      elem.msRequestFullscreen()
    }
    isFullscreen.value = true
  } else {
    // 退出全屏
    if (document.exitFullscreen) {
      document.exitFullscreen()
    } else if (document.webkitExitFullscreen) {
      document.webkitExitFullscreen()
    } else if (document.msExitFullscreen) {
      document.msExitFullscreen()
    }
    isFullscreen.value = false
  }
}

// 监听全屏变化
function onFullscreenChange() {
  isFullscreen.value = document.fullscreenElement !== null
}

// 底图加载并发控制
let floorPlanLoadId = 0

// 加载底图纹理
async function loadFloorPlanTexture() {
  const { scene, renderer } = ctx.value
  if (!currentPlan.value) return

  // 生成新的加载ID，用于并发控制
  const currentLoadId = ++floorPlanLoadId

  // 清除旧底图
  const oldGround = scene?.getObjectByName('ground')
  if (oldGround) {
    scene.remove(oldGround)
    oldGround.geometry?.dispose()
    oldGround.material?.dispose()
  }

  // 转换本地路径到 HTTP URL
  const path = currentPlan.value.image_path
  const filename = path.split('/').pop()
  const imageUrl = '/photos/floor_plans/' + encodeURIComponent(filename)

  const loader = new THREE.TextureLoader()

  try {
    const tex = await loader.loadAsync(imageUrl)

    // 并发检查：如果这不是最新的加载请求，则放弃
    if (currentLoadId !== floorPlanLoadId) {
      tex.dispose()
      return
    }

    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = renderer.capabilities.getMaxAnisotropy()

    const geo = new THREE.PlaneGeometry(plan.real_width_m, plan.real_depth_m)
    // 使用带亮度的材质，降低底图亮度
    const mat = new THREE.MeshBasicMaterial({
      map: tex,
      opacity: 0.85,  // 略微降低亮度
      transparent: true
    })
    const ground = new THREE.Mesh(geo, mat)

    // 根据倾斜角度设置旋转和位置
    // 0度 = 水平躺地 (-Math.PI/2)，90度 = 垂直站立 (0)
    const tiltRad = (floorTiltAngle.value / 90) * (Math.PI / 2)
    ground.rotation.x = -Math.PI / 2 + tiltRad

    // 垂直时底图立在场景后方
    const tiltFactor = floorTiltAngle.value / 90
    const yPos = tiltFactor * plan.real_depth_m / 2  // 垂直时提升到底图高度的一半
    const zPos = plan.real_depth_m / 2 - tiltFactor * plan.real_depth_m / 2  // 垂直时移到后方

    ground.position.set(plan.real_width_m / 2, yPos, zPos)
    ground.name = 'ground'
    scene.add(ground)
  } catch (e) {
    console.error('加载底图失败:', e)
  }
}

// 构建设备模型（独立 Group，便于单独操作）
function buildDeviceModels() {
  const { scene } = ctx.value

  // 清除旧设备组
  const oldGroup = scene?.getObjectByName('devices')
  if (oldGroup) {
    oldGroup.traverse(o => { o.geometry?.dispose?.(); o.material?.dispose?.() })
    scene.remove(oldGroup)
  }

  const group = new THREE.Group()
  group.name = 'devices'

  filteredDevices.value.forEach(d => {
    const node = nodes.value.find(n => n.device_id === d.id)
    if (!node) return

    const model = createDeviceModel(d.device_type, d.status)
    const elevation = getDeviceBaseSize(d.device_type) * 0.5
    const w = percentToWorld(node.x_percent, node.y_percent, elevation)
    model.position.set(w.x, w.y, w.z)
    const userScale = Number(node.scale) || 1
    model.scale.setScalar(userScale)
    model.userData = { device: d, node, base: getDeviceBaseSize(d.device_type) }
    group.add(model)
  })

  scene.add(group)
  ctx.value.deviceGroup = group
}

// 清理组资源
function disposeGroup(name) {
  const { scene } = ctx.value
  const g = scene?.getObjectByName(name)
  if (!g) return
  g.traverse(o => { o.geometry?.dispose?.(); o.material?.dispose?.() })
  scene.remove(g)
}

// 重建场景（底图切换或节点变化后）
function rebuildScene() {
  disposeGroup('devices')
  disposeGroup('links')
  disposeGroup('labels')
  buildDeviceModels()
  buildLinks()
  buildLabels()
}

// 构建链路（支持 waypoints 正交折线）
function buildLinks() {
  const { scene } = ctx.value

  const linkGroup = new THREE.Group()
  linkGroup.name = 'links'

  // 链路高度：贴近地面，底图短边的 0.2%
  const linkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002

  links.value.forEach(link => {
    const fromNode = nodes.value.find(n => n.id === link.from_node_id || n.device_id === link.from)
    const toNode = nodes.value.find(n => n.id === link.to_node_id || n.device_id === link.to)

    if (!fromNode || !toNode) return

    const a = percentToWorld(fromNode.x_percent, fromNode.y_percent, linkHeight)
    const b = percentToWorld(toNode.x_percent, toNode.y_percent, linkHeight)

    // 构建折线点（支持 waypoints）
    const points = []
    points.push(new THREE.Vector3(a.x, a.y, a.z))

    // 如果有拐点，按拐点绘制折线
    if (link.waypoints) {
      try {
        const waypoints = JSON.parse(link.waypoints)
        waypoints.forEach(wp => {
          const wpWorld = percentToWorld(wp.x, wp.y, linkHeight)
          points.push(new THREE.Vector3(wpWorld.x, wpWorld.y, wpWorld.z))
        })
      } catch (e) {
        console.error('解析 waypoints 失败:', e)
      }
    } else if (!link.waypoints) {
      // 无拐点时，生成默认正交折线（先横后竖）
      const midX = (a.x + b.x) / 2
      const midZ = (a.z + b.z) / 2
      // 根据起点终点方向决定折线方向
      if (Math.abs(a.x - b.x) > Math.abs(a.z - b.z)) {
        // 横向为主：先横向到中点，再竖向
        points.push(new THREE.Vector3(midX, a.y, a.z))
        points.push(new THREE.Vector3(midX, a.y, b.z))
      } else {
        // 竖向为主：先竖向到中点，再横向
        points.push(new THREE.Vector3(a.x, a.y, midZ))
        points.push(new THREE.Vector3(b.x, a.y, midZ))
      }
    }

    points.push(new THREE.Vector3(b.x, b.y, b.z))

    const geo = new THREE.BufferGeometry().setFromPoints(points)
    const mat = new THREE.LineBasicMaterial({
      color: link.status === 'broken' ? 0xff4d4f : 0x22d3ee,
      transparent: true,
      opacity: 0.6,
      linewidth: 2
    })

    const line = new THREE.Line(geo, mat)
    line.userData.link = link
    linkGroup.add(line)

    // 如果有拐点且在编辑模式，添加拐点标记球
    if (link.waypoints && isEditMode.value) {
      try {
        const waypoints = JSON.parse(link.waypoints)
        waypoints.forEach((wp, idx) => {
          const wpWorld = percentToWorld(wp.x, wp.y, linkHeight + 2)
          const sphereGeo = new THREE.SphereGeometry(3, 16, 16)
          const sphereMat = new THREE.MeshBasicMaterial({ color: 0xffa116, transparent: true, opacity: 0.8 })
          const sphere = new THREE.Mesh(sphereGeo, sphereMat)
          sphere.position.set(wpWorld.x, wpWorld.y, wpWorld.z)
          sphere.userData.waypoint = { linkId: link.id, index: idx, x: wp.x, y: wp.y }
          sphere.name = `waypoint-${link.id}-${idx}`
          linkGroup.add(sphere)
        })
      } catch (e) {}
    }
  })

  scene.add(linkGroup)
  ctx.value.linkLines = linkGroup
}

// 构建设备标签（显示在设备上方）
function buildLabels() {
  const { scene, deviceGroup } = ctx.value

  const labelGroup = new THREE.Group()
  labelGroup.name = 'labels'

  // 显示所有筛选后的设备标签
  filteredDevices.value.forEach(d => {
    const node = nodes.value.find(n => n.device_id === d.id)
    if (!node) return

    // 获取设备模型位置和高度
    const base = getDeviceBaseSize(d.device_type)
    const elevation = base * 0.5  // 设备离地高度
    const modelHeight = base * 0.8  // 设备模型高度估算
    const labelHeight = elevation + modelHeight + base * 0.3  // 标签在设备上方

    const w = percentToWorld(node.x_percent, node.y_percent, labelHeight)

    const el = document.createElement('div')
    el.className = `device-label ${d.status}`
    el.textContent = d.name
    el.style.opacity = '0'

    const label = new CSS2DObject(el)
    label.position.set(w.x, w.y, w.z)
    label.userData.deviceId = d.id
    label.userData.deviceStatus = d.status
    label.visible = false
    labelGroup.add(label)
  })

  scene.add(labelGroup)
  ctx.value.labels = labelGroup
}

// 离线设备呼吸动画（独立 Group 版本）
let pulseTime = 0
const reusedColor = new THREE.Color()
let lastPulseUpdate = 0
const PULSE_UPDATE_INTERVAL = 50

function pulseOfflineDevices() {
  const { deviceGroup } = ctx.value
  if (!deviceGroup) return

  const now = performance.now()
  if (now - lastPulseUpdate < PULSE_UPDATE_INTERVAL) return
  lastPulseUpdate = now

  pulseTime += 0.1
  const pulse = Math.sin(pulseTime) * 0.3 + 0.7

  deviceGroup.children.forEach(model => {
    const device = model.userData.device
    if (device && device.status === 'offline') {
      model.traverse(child => {
        if (child.material && child.material.color) {
          const baseColor = STATUS_COLOR.offline
          child.material.color.set(baseColor)
          child.material.color.multiplyScalar(pulse)
        }
      })
    }
  })
}

// 根据相机距离更新标签可见性
const LABEL_SHOW_DISTANCE = 200 // 相机距离小于200米时显示标签
function updateLabelVisibility() {
  const { camera, labels } = ctx.value
  if (!labels || !showLabels.value) return

  const cameraPos = camera.position
  const cameraHeight = cameraPos.y

  // 标签可见性：相机高度低于阈值时显示
  const shouldShowLabels = cameraHeight < LABEL_SHOW_DISTANCE

  labels.children.forEach(label => {
    // 计算标签与相机的距离
    const labelPos = label.position
    const dist = cameraPos.distanceTo(labelPos)

    // 近距离显示，远距离隐藏
    label.visible = shouldShowLabels && dist < LABEL_SHOW_DISTANCE * 2

    // 更新标签样式（近处更清晰）
    if (label.element) {
      const opacity = dist < LABEL_SHOW_DISTANCE ? 1 : 0.5
      label.element.style.opacity = opacity
    }
  })
}

// 点击拾取（独立 Group）
let selectedModel = null

// 拖动状态
const dragState = ref(null)
let isDragging = false

// 拐点拖动状态
let waypointDragState = null
let selectedWaypointSphere = null

// 编辑模式鼠标按下 - 拖动起点（支持拐点和设备拖动）
function onCanvasMouseDown(e) {
  if (!isEditMode.value) return

  const { camera, renderer, deviceGroup, linkLines, controls } = ctx.value

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  // 先检查是否点击了拐点球
  if (linkLines) {
    const waypointSpheres = linkLines.children.filter(c => c.userData.waypoint)
    const waypointHits = raycaster.intersectObjects(waypointSpheres, false)

    if (waypointHits.length > 0) {
      const sphere = waypointHits[0].object
      const wp = sphere.userData.waypoint

      waypointDragState = {
        linkId: wp.linkId,
        index: wp.index,
        startX: wp.x,
        startY: wp.y,
      }
      selectedWaypointSphere = sphere

      // 高亮拐点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onWaypointDragMove)
      renderer.domElement.addEventListener('mouseup', onWaypointDragEnd)
      return
    }
  }

  // 检查设备点击
  const hits = raycaster.intersectObjects(deviceGroup?.children || [], true)

  if (hits.length > 0) {
    // 找到带 userData.device 的父级 Group
    let model = hits[0].object
    while (model && !model.userData.device) {
      model = model.parent
    }

    if (model && model.userData.device) {
      const device = model.userData.device
      const node = model.userData.node

      selectedDevice.value = device
      selectedNode.value = node
      selectedModel = model

      // 高亮选中设备
      model.traverse(child => {
        if (child.material) {
          child.material.emissive = EMISSIVE_ON
        }
      })

      // 设置拖动状态
      dragState.value = {
        nodeId: node.id,
        deviceId: device.id,
        deviceType: device.device_type,
        startClientX: e.clientX,
        startClientY: e.clientY,
      }

      // 暂停轨道控制（编辑模式下完全禁用）
      controls.enabled = false
      isDragging = false

      // 监听拖动
      renderer.domElement.addEventListener('mousemove', onDragMove)
      renderer.domElement.addEventListener('mouseup', onDragEnd)
    }
  }
}

// 拐点拖动处理
function onWaypointDragMove(e) {
  if (!waypointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  waypointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  waypointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新拐点球位置
  if (selectedWaypointSphere) {
    const linkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002 + 2
    const w = percentToWorld(waypointDragState._lastX, waypointDragState._lastY, linkHeight)
    selectedWaypointSphere.position.set(w.x, w.y, w.z)
  }
}

// 拐点拖动结束
async function onWaypointDragEnd(e) {
  if (!waypointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onWaypointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onWaypointDragEnd)
  ctx.value.controls.enabled = true

  const { linkId, index, _lastX, _lastY } = waypointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 更新拐点数据
      const link = links.value.find(l => l.id === linkId)
      if (link) {
        let waypoints = []
        try {
          waypoints = link.waypoints ? JSON.parse(link.waypoints) : []
        } catch (e) {}

        // 更新指定索引的拐点
        if (index < waypoints.length) {
          waypoints[index] = { x: Number(_lastX.toFixed(2)), y: Number(_lastY.toFixed(2)) }
        }

        const waypointsJson = JSON.stringify(waypoints)
        await axios.put(`/api/floor-plans/${currentPlanId.value}/links/${linkId}`, {
          waypoints: waypointsJson
        })

        // 更新本地数据
        link.waypoints = waypointsJson

        // 更新 userData
        if (selectedWaypointSphere) {
          selectedWaypointSphere.userData.waypoint.x = _lastX
          selectedWaypointSphere.userData.waypoint.y = _lastY
        }

        // 重建链路
        disposeGroup('links')
        buildLinks()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新拐点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复拐点球颜色
  if (selectedWaypointSphere) {
    selectedWaypointSphere.material.color.set(0xffa116)
  }

  waypointDragState = null
  selectedWaypointSphere = null
  isDragging = false
}

// 查看模式点击选中
function onCanvasClick(e) {
  // 如果刚完成拖动，不处理点击
  if (isDragging) return
  if (isEditMode.value) return

  const { camera, renderer, deviceGroup } = ctx.value

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  const hits = raycaster.intersectObjects(deviceGroup?.children || [], true)

  // 清除之前的高亮
  if (selectedModel) {
    selectedModel.traverse(child => {
      if (child.material) {
        child.material.emissive = EMISSIVE_OFF
      }
    })
  }

  if (hits.length > 0) {
    // 找到带 userData.device 的父级 Group
    let model = hits[0].object
    while (model && !model.userData.device) {
      model = model.parent
    }

    if (model && model.userData.device) {
      const device = model.userData.device
      const node = model.userData.node

      selectedDevice.value = device
      selectedNode.value = node
      selectedModel = model

      // 高亮选中设备
      model.traverse(child => {
        if (child.material) {
          child.material.emissive = EMISSIVE_ON
        }
      })

      ElMessage.success(`${t('selected')}: ${device.name}`)

      // 相机聚焦到设备
      if (node) {
        const w = percentToWorld(node.x_percent, node.y_percent, 0)
        const ref = Math.min(plan.real_width_m, plan.real_depth_m)
        const lookAtHeight = ref * 0.03
        ctx.value.controls.target.set(w.x, lookAtHeight, w.z)
      }
    }
  } else {
    selectedDevice.value = null
    selectedNode.value = null
    selectedModel = null
  }
}

// 拖动处理（独立 Group 版本）
function onDragMove(e) {
  if (!dragState.value) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  dragState.value._lastX = pos.x_percent
  dragState.value._lastY = pos.y_percent

  // 计算基于底图尺寸的高度
  const deviceType = dragState.value.deviceType || 'switch'
  const base = getDeviceBaseSize(deviceType)
  const elevation = base * 0.5  // 设备离地高度
  const labelHeight = elevation + base * 1.1  // 标签在设备上方

  // 实时更新标签位置（在设备上方）
  const label = ctx.value.labels?.children.find(l => l.userData.deviceId === dragState.value.deviceId)
  if (label) {
    const w = percentToWorld(pos.x_percent, pos.y_percent, labelHeight)
    label.position.set(w.x, w.y, w.z)
  }

  // 实时更新设备模型位置
  if (selectedModel) {
    const w = percentToWorld(pos.x_percent, pos.y_percent, elevation)
    selectedModel.position.set(w.x, w.y, w.z)
  }
}

async function onDragEnd(e) {
  if (!dragState.value) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onDragEnd)
  ctx.value.controls.enabled = true

  const { nodeId, _lastX, _lastY } = dragState.value

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      await axios.put(`/api/floor-plans/${currentPlanId.value}/nodes/${nodeId}`, {
        x_percent: Number(_lastX.toFixed(2)),
        y_percent: Number(_lastY.toFixed(2)),
      })
      ElMessage.success(t('msgSaveSuccess'))

      // 更新本地nodes数据（不重建场景，保持选中状态）
      const node = nodes.value.find(n => n.id === nodeId)
      if (node) {
        node.x_percent = _lastX.toFixed(2)
        node.y_percent = _lastY.toFixed(2)
        // 同步 userData
        if (selectedModel && selectedModel.userData.node) {
          selectedModel.userData.node = { ...node }
        }
      }

      // 只重建链路（不重建设备模型和标签）
      disposeGroup('links')
      buildLinks()

      // 清除高亮
      if (selectedModel) {
        selectedModel.traverse(child => {
          if (child.material) {
            child.material.emissive = EMISSIVE_OFF
          }
        })
      }

    } catch (err) {
      console.error('更新节点位置失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  dragState.value = null
  isDragging = false
}
      
// 聚焦到设备（带平滑动画）- 使用基于底图尺寸的距离
let focusAnimationId = null
function focusDevice(device) {
  const { camera, controls, deviceGroup } = ctx.value

  const node = nodes.value.find(n => n.device_id === device.id)
  if (!node) return

  const w = percentToWorld(node.x_percent, node.y_percent, 0)

  // 取消之前的动画
  if (focusAnimationId) {
    cancelAnimationFrame(focusAnimationId)
  }

  // 基于底图尺寸计算聚焦距离
  const ref = Math.min(plan.real_width_m, plan.real_depth_m)
  const focusDist = ref * 0.08
  const focusHeight = ref * 0.05
  const lookAtHeight = ref * 0.03

  // 目标位置
  const targetPos = { x: w.x + focusDist, y: focusHeight, z: w.z + focusDist }
  const targetLookAt = { x: w.x, y: lookAtHeight, z: w.z }

  // 当前位置
  const startPos = { x: camera.position.x, y: camera.position.y, z: camera.position.z }
  const startLookAt = { x: controls.target.x, y: controls.target.y, z: controls.target.z }

  // 动画参数
  const duration = 60
  let frame = 0

  const animate = () => {
    frame++
    const progress = Math.min(frame / duration, 1)
    const ease = 1 - Math.pow(1 - progress, 3)

    camera.position.x = startPos.x + (targetPos.x - startPos.x) * ease
    camera.position.y = startPos.y + (targetPos.y - startPos.y) * ease
    camera.position.z = startPos.z + (targetPos.z - startPos.z) * ease

    controls.target.x = startLookAt.x + (targetLookAt.x - startLookAt.x) * ease
    controls.target.y = startLookAt.y + (targetLookAt.y - startLookAt.y) * ease
    controls.target.z = startLookAt.z + (targetLookAt.z - startLookAt.z) * ease

    if (progress < 1) {
      focusAnimationId = requestAnimationFrame(animate)
    } else {
      focusAnimationId = null
    }
  }
  animate()

  selectedDevice.value = device

  // 高亮该设备（独立 Group）
  if (deviceGroup) {
    deviceGroup.children.forEach(model => {
      const d = model.userData.device
      if (d && d.id === device.id) {
        model.traverse(child => {
          if (child.material) {
            child.material.emissive = EMISSIVE_ON
          }
        })
      }
    })
  }
}

// 跳转设备详情
function goToDeviceDetail(deviceId) {
  router.push(`/devices/${deviceId}`)
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

  // 重新加载节点和链路
  try {
    const nodesRes = await axios.get(`/api/floor-plans/${planId}/nodes`)
    nodes.value = nodesRes.data.items || []

    const linksRes = await axios.get(`/api/floor-plans/${planId}/links`)
    links.value = linksRes.data.items || []

    const topoRes = await axios.get(`/api/floor-plans/${planId}/topology`)
    if (topoRes.data.nodes) nodes.value = topoRes.data.nodes
    if (topoRes.data.links) links.value = topoRes.data.links

    // 重建场景
    loadFloorPlanTexture()
    rebuildScene()

    // 重置视角
    resetView()

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
      loadFloorPlanTexture()
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

    // 加载节点
    if (currentPlan.value) {
      const nodesRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/nodes`)
      nodes.value = nodesRes.data.items || []

      const linksRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/links`)
      links.value = linksRes.data.items || []

      const topoRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/topology`)
      if (topoRes.data.nodes) nodes.value = topoRes.data.nodes
      if (topoRes.data.links) links.value = topoRes.data.links
    }

  } catch (e) {
    console.error('加载数据失败:', e)
    ElMessage.error(t('loadDataFailed'))
  }
}

// 监听筛选变化，重建设备和标签
watch([filterType, filterStatus], () => {
  if (ctx.value.scene) {
    rebuildScene()
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

// 监听图层控制
watch(showLinks, (val) => {
  if (ctx.value.linkLines) {
    ctx.value.linkLines.visible = val
  }
})

watch(showLabels, (val) => {
  if (ctx.value.labels) {
    ctx.value.labels.visible = val
  }
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

onMounted(async () => {
  initScene()
  await loadData()
  loadFloorPlanTexture()
  buildDeviceModels()
  buildLinks()
  buildLabels()

  // 自动框景 - 延迟执行确保布局稳定
  requestAnimationFrame(() => fitView())

  // 全屏事件监听
  document.addEventListener('fullscreenchange', onFullscreenChange)
  document.addEventListener('webkitfullscreenchange', onFullscreenChange)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', onResize)

  // 移除全屏事件监听
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  document.removeEventListener('webkitfullscreenchange', onFullscreenChange)

  // 移除滚轮事件监听
  if (ctx.value.renderer?.domElement) {
    ctx.value.renderer.domElement.removeEventListener('wheel', handleWheel)
  }

  const { renderer, controls, host, labelRenderer, scene } = ctx.value

  // 清除事件
  renderer?.domElement?.removeEventListener('click', onCanvasClick)
  renderer?.domElement?.removeEventListener('mousedown', onCanvasMouseDown)
  renderer?.domElement?.removeEventListener('mousemove', onDragMove)
  renderer?.domElement?.removeEventListener('mouseup', onDragEnd)

  // 释放资源
  controls?.dispose()
  renderer?.dispose()

  // 清除场景
  scene?.traverse(obj => {
    obj.geometry?.dispose()
    obj.material?.dispose()
  })

  // 移除 DOM
  if (renderer?.domElement) host?.removeChild(renderer.domElement)
  if (labelRenderer?.domElement) host?.removeChild(labelRenderer.domElement)
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

/* 玻璃质感侧边栏（浮动覆盖） */
.side-panel {
  position: absolute;
  top: 0;
  right: 0;
  width: 200px;
  height: 100%;
  padding: 12px;
  background: rgba(17, 22, 31, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: #e5e7eb;
  overflow-y: auto;
  border-left: 1px solid rgba(34, 211, 238, 0.2);
  transition: transform 0.3s ease, opacity 0.3s ease;
  z-index: 10;
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
  right: 200px;
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

/* 画布右下角工具按钮（避开侧边栏） */
.canvas-tools {
  position: absolute;
  right: 216px;
  bottom: 16px;
  display: flex;
  gap: 8px;
  z-index: 5;
  transition: right 0.3s ease;
}

.monitor3d.panel-hidden .canvas-tools {
  right: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 14px;
  color: #22d3ee;
}

.plan-switch {
  margin-top: 8px;
}

.plan-switch .el-select {
  width: 100%;
}

.no-plan-hint {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #6b7280;
  font-size: 12px;
}

.kpi-row {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.kpi {
  flex: 1;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 6px;
  padding: 8px 4px;
  text-align: center;
}

.kpi span {
  font-size: 10px;
  color: #6b7280;
}

.kpi b {
  display: block;
  font-size: 16px;
  margin-top: 2px;
}

.kpi b.online {
  color: #22d3ee;
}

.kpi b.offline {
  color: #ff4d4f;
}

.filter-section {
  display: flex;
  flex-direction: row;  /* 横向排列 */
  gap: 8px;
}

.filter-section .el-select {
  flex: 1;  /* 等宽 */
}

.selected-box {
  background: rgba(26, 34, 48, 0.5);
  border-radius: 6px;
  padding: 8px;
}

.selected-box h4 {
  margin: 0 0 6px;
  color: #22d3ee;
  font-size: 12px;
}

.selected-box p {
  margin: 2px 0;
  font-size: 11px;
}

.hint {
  color: #6b7280;
  font-size: 11px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.layer-control h4 {
  margin: 0 0 6px;
  font-size: 12px;
}

.tilt-control {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tilt-control span {
  font-size: 12px;
  color: #6b7280;
}

.tilt-control .el-slider {
  width: 80px;
}

.tilt-value {
  color: #22d3ee;
  font-weight: 500;
  font-size: 11px;
}

.alert-section h4 {
  margin: 0 0 6px;
  font-size: 12px;
}

.alert-list {
  max-height: 150px;
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 4px;
  margin-bottom: 4px;
  cursor: pointer;
}

.alert-item:hover {
  background: rgba(36, 48, 64, 0.6);
}

.alert-icon {
  color: #ff4d4f;
}

.alert-name {
  color: #e5e7eb;
  font-size: 11px;
}

.no-alert {
  color: #6b7280;
  font-size: 11px;
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

.edit-mode-indicator {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  background: rgba(255, 161, 22, 0.9);
  padding: 8px 16px;
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
}

/* 标签页样式 - 暗色玻璃质感风格 */
:deep(.el-tabs) {
  margin-top: 8px;
}

/* 整个 tabs 作为一张连续卡片 */
:deep(.el-tabs--border-card) {
  background: rgba(17, 22, 31, 0.45);
  border: 1px solid rgba(34, 211, 238, 0.18);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
}

/* 头部去掉独立底色，改为轻微区分 + 底部细分隔线 */
:deep(.el-tabs__header) {
  background: rgba(26, 34, 48, 0.35);
  border: none;
  border-bottom: 1px solid rgba(34, 211, 238, 0.12);
  border-radius: 0;
  margin: 0;
}

:deep(.el-tabs__nav-wrap) {
  background: transparent;
}

:deep(.el-tabs__item) {
  color: #e5e7eb !important;
  background: transparent;
  border: none;
  padding: 8px 12px;
  font-size: 12px;
  border-left: none !important;
  border-right: none !important;
}

:deep(.el-tabs__item:hover) {
  color: #22d3ee !important;
}

/* 选中项改为底部高亮条，而非整块色块 */
:deep(.el-tabs__item.is-active) {
  color: #22d3ee !important;
  background: transparent;
  position: relative;
}
:deep(.el-tabs__item.is-active)::after {
  content: '';
  position: absolute;
  left: 12px; right: 12px; bottom: 0;
  height: 2px;
  background: #22d3ee;
  border-radius: 2px;
}

/* 内容区透明、无独立圆角（圆角交给外层） */
:deep(.el-tabs__content) {
  padding: 10px;
  background: transparent;
  border-radius: 0;
}

:deep(.el-tab-pane) {
  font-size: 12px;
}

:deep(.el-tabs__nav) {
  border: none;
}

/* ===== 下拉框暗色化 ===== */
/* 覆盖 el-select 的输入框底色（暗色玻璃质感） */
:deep(.el-select__wrapper),
:deep(.el-input__wrapper) {
  background: rgba(26, 34, 48, 0.6) !important;
  box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.25) inset !important;
  border-radius: 6px;
}
:deep(.el-select__wrapper:hover),
:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.5) inset !important;
}
:deep(.el-select__wrapper.is-focused),
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #22d3ee inset !important;
}
/* 选中文字 / 占位符颜色 */
:deep(.el-select__placeholder),
:deep(.el-input__inner) {
  color: #e5e7eb !important;
}
:deep(.el-select__placeholder.is-transparent) {
  color: #6b7280 !important;
}
/* 下拉箭头 / 清除图标 */
:deep(.el-select__caret),
:deep(.el-input__icon) {
  color: #9ca3af !important;
}

/* 链路列表 */
.link-list {
  max-height: 300px;
  overflow-y: auto;
}

.link-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 4px;
  margin-bottom: 4px;
}

.link-info {
  color: #e5e7eb;
  font-size: 11px;
}

/* 底图列表 */
.plan-list {
  max-height: 300px;
  overflow-y: auto;
}

.plan-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 4px;
  margin-bottom: 4px;
}

.plan-item.active {
  background: rgba(34, 211, 238, 0.2);
  border: 1px solid rgba(34, 211, 238, 0.3);
}

.plan-name {
  color: #e5e7eb;
  font-size: 12px;
}

.plan-actions {
  display: flex;
  gap: 4px;
}

.no-data {
  color: #6b7280;
  font-size: 12px;
  text-align: center;
  padding: 12px;
}

/* 功能按钮 */
.panel-action-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 12px;
  margin-bottom: 10px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.18), rgba(34, 211, 238, 0.08));
  border: 1px solid rgba(34, 211, 238, 0.35);
  border-radius: 6px;
  color: #22d3ee;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.panel-action-btn:hover {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.25), rgba(34, 211, 238, 0.15));
  border-color: rgba(34, 211, 238, 0.5);
  transform: translateY(-1px);
}

.panel-action-btn .el-icon {
  font-size: 14px;
}

/* 图标按钮 */
.icon-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(26, 34, 48, 0.6);
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 4px;
  color: #22d3ee;
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 0;
}

.icon-btn:hover {
  background: rgba(34, 211, 238, 0.2);
  border-color: rgba(34, 211, 238, 0.4);
  transform: scale(1.05);
}

.icon-btn.danger {
  color: #ff4d4f;
  border-color: rgba(255, 77, 79, 0.3);
}

.icon-btn.danger:hover {
  background: rgba(255, 77, 79, 0.15);
  border-color: rgba(255, 77, 79, 0.5);
}

.icon-btn .el-icon {
  font-size: 12px;
}

/* 链路角色标签 */
.link-role-badge {
  padding: 2px 6px;
  font-size: 10px;
  background: rgba(26, 34, 48, 0.6);
  border-radius: 3px;
  color: #6b7280;
}

.link-role-badge[data-role="uplink"] {
  background: rgba(34, 211, 238, 0.15);
  color: #22d3ee;
}

.link-role-badge[data-role="svl"] {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}

.link-role-badge[data-role="portchannel-member"] {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

/* 增强底图列表项 */
.plan-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 4px;
  margin-bottom: 6px;
  transition: all 0.2s ease;
}

.plan-item:hover {
  background: rgba(36, 48, 64, 0.6);
}

.plan-item.active {
  background: rgba(34, 211, 238, 0.15);
  border: 1px solid rgba(34, 211, 238, 0.35);
}

.plan-icon {
  color: #6b7280;
  font-size: 14px;
}

.plan-item.active .plan-icon {
  color: #22d3ee;
}

.plan-name {
  flex: 1;
  color: #e5e7eb;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-badge {
  padding: 2px 6px;
  font-size: 10px;
  background: rgba(34, 211, 238, 0.2);
  border-radius: 3px;
  color: #22d3ee;
}

.plan-actions {
  display: flex;
  gap: 4px;
}

/* 设备库面板 */
.device-palette {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.palette-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: rgba(26, 34, 48, 0.5);
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 6px;
  color: #e5e7eb;
  font-size: 12px;
  cursor: grab;
  transition: all 0.2s ease;
}

.palette-item:hover {
  background: rgba(34, 211, 238, 0.12);
  border-color: rgba(34, 211, 238, 0.45);
}

.palette-item:active {
  cursor: grabbing;
}

.palette-item .el-icon {
  color: #22d3ee;
  font-size: 14px;
}

/* 选中设备操作按钮 */
.selected-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

/* 设备缩放控制 */
.scale-control {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.scale-control span {
  font-size: 12px;
  color: #6b7280;
}

.scale-control .el-slider {
  flex: 1;
}

.scale-value {
  color: #22d3ee;
  font-weight: 500;
  font-size: 11px;
}

/* 链路操作按钮 */
.link-actions {
  display: flex;
  gap: 4px;
}

/* 拐点编辑样式 */
.waypoint-hint {
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 12px;
}

.waypoint-list {
  max-height: 200px;
  overflow-y: auto;
}

.waypoint-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 4px;
  margin-bottom: 4px;
}

.waypoint-index {
  color: #22d3ee;
  font-size: 12px;
  font-weight: 500;
  min-width: 20px;
}

.waypoint-item .el-input-number {
  width: 80px;
}
</style>