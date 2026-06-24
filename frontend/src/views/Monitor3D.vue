<template>
  <div class="monitor3d" :class="{ 'fullscreen-mode': isFullscreen, 'panel-hidden': hidePanel, 'edit-mode': isEditMode, 'dark-panel': isDark }">
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
        <el-button type="primary" :loading="bindSubmitting" @click="confirmBindDevice">{{ t('actionConfirm') }}</el-button>
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

    <!-- 主干光缆拐点编辑对话框 -->
    <el-dialog v-model="showTrunkWaypointDialog" :title="t('editWaypoints') + ' - ' + t('fiberTrunk')" width="500px">
      <p class="waypoint-hint">{{ t('waypointHint') }}</p>
      <div class="waypoint-list">
        <div v-for="(wp, idx) in editingTrunkWaypoints" :key="idx" class="waypoint-item">
          <span class="waypoint-index">{{ idx + 1 }}</span>
          <el-input-number v-model="wp.x" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointX')" />
          <el-input-number v-model="wp.y" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointY')" />
          <button class="icon-btn danger" :title="t('actionDelete')" @click="removeTrunkWaypoint(idx)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
        <div v-if="editingTrunkWaypoints.length === 0" class="no-data">
          {{ t('noWaypoints') }}
        </div>
      </div>
      <el-button type="primary" size="small" @click="addTrunkWaypoint">
        <el-icon><Plus /></el-icon>
        {{ t('addWaypoint') }}
      </el-button>
      <template #footer>
        <el-button @click="showTrunkWaypointDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="saveTrunkWaypoints">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 分支光缆拐点编辑对话框 -->
    <el-dialog v-model="showBranchLinkWaypointDialog" :title="t('editWaypoints') + ' - ' + t('fiberBranchLink')" width="500px">
      <p class="waypoint-hint">{{ t('waypointHint') }}</p>
      <div class="waypoint-list">
        <div v-for="(wp, idx) in editingBranchLinkWaypoints" :key="idx" class="waypoint-item">
          <span class="waypoint-index">{{ idx + 1 }}</span>
          <el-input-number v-model="wp.x" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointX')" />
          <el-input-number v-model="wp.y" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointY')" />
          <button class="icon-btn danger" :title="t('actionDelete')" @click="removeBranchLinkWaypoint(idx)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
        <div v-if="editingBranchLinkWaypoints.length === 0" class="no-data">
          {{ t('noWaypoints') }}
        </div>
      </div>
      <el-button type="primary" size="small" @click="addBranchLinkWaypoint">
        <el-icon><Plus /></el-icon>
        {{ t('addWaypoint') }}
      </el-button>
      <template #footer>
        <el-button @click="showBranchLinkWaypointDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="saveBranchLinkWaypoints">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- TopoEdge 拐点编辑对话框 -->
    <el-dialog v-model="showTopoEdgeWaypointDialog" :title="t('editWaypoints') + ' - TopoEdge'" width="500px">
      <p class="waypoint-hint">{{ t('waypointHint') }}</p>
      <div class="waypoint-list">
        <div v-for="(wp, idx) in editingTopoEdgeWaypoints" :key="idx" class="waypoint-item">
          <span class="waypoint-index">{{ idx + 1 }}</span>
          <el-input-number v-model="wp.x" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointX')" />
          <el-input-number v-model="wp.y" :min="0" :max="100" :step="1" size="small" :placeholder="t('waypointY')" />
          <button class="icon-btn danger" :title="t('actionDelete')" @click="removeTopoEdgeWaypoint(idx)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
        <div v-if="editingTopoEdgeWaypoints.length === 0" class="no-data">
          {{ t('noWaypoints') }}
        </div>
      </div>
      <el-button type="primary" size="small" @click="addTopoEdgeWaypoint">
        <el-icon><Plus /></el-icon>
        {{ t('addWaypoint') }}
      </el-button>
      <template #footer>
        <el-button @click="showTopoEdgeWaypointDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="saveTopoEdgeWaypoints">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 右：操作面板（玻璃质感） -->
    <aside class="side-panel" :class="{ dark: isDark }">
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

          <!-- 光纤主干操作（编辑模式下显示） -->
          <div class="fiber-section" v-if="isEditMode">
            <!-- 操作按钮区域 -->
            <div class="fiber-action-bar">
              <button class="panel-action-btn" @click="startAddTrunk">
                <el-icon><Plus /></el-icon>
                <span>{{ t('addFiberTrunk') }}</span>
              </button>
              <button class="panel-action-btn" @click="startAddBranchPoint" v-if="displayCables.length > 0">
                <el-icon><Position /></el-icon>
                <span>{{ t('addBranchPoint') }}</span>
              </button>
            </div>

            <!-- 主干树形列表 -->
            <div class="fiber-tree" v-if="displayCables.length > 0">
              <div v-for="cable in displayCables" :key="cable.cable_id" class="fiber-tree-node trunk-node">
                <!-- 主干节点 -->
                <div class="tree-node-header" @click="toggleTrunkExpand(cable.cable_id)">
                  <div class="tree-node-row">
                    <el-icon class="tree-expand-icon">
                      <ArrowDown v-if="expandedTrunks[cable.cable_id]" />
                      <ArrowRight v-else />
                    </el-icon>
                    <span class="trunk-name" :title="cable.cable_name || cable.cable_no">{{ cable.cable_name || cable.cable_no }}</span>
                  </div>
                  <div class="tree-node-actions">
                    <button class="icon-btn" @click.stop="editCableWaypoints(cable)" :title="t('editWaypoints')">
                      <el-icon><Connection /></el-icon>
                    </button>
                    <button class="icon-btn danger" @click.stop="deleteCable(cable.cable_id)" :title="t('actionDelete')">
                      <el-icon><Delete /></el-icon>
                    </button>
                  </div>
                </div>
                <!-- 主干展开内容 -->
                <div class="tree-node-children" v-if="expandedTrunks[cable.cable_id]">
                  <div v-for="bp in getBranchPointsForCable(cable.cable_id)" :key="bp.id" class="fiber-tree-node branch-point-node">
                    <div class="tree-node-header" @click="toggleBranchPointExpand(bp.id)">
                      <div class="tree-node-row">
                        <el-icon class="tree-expand-icon">
                          <ArrowDown v-if="expandedBranchPoints[bp.id]" />
                          <ArrowRight v-else />
                        </el-icon>
                        <span class="bp-name" :title="bp.label || `BP-${bp.id}`">{{ bp.label || `BP-${bp.id}` }}</span>
                      </div>
                      <div class="tree-node-actions">
                        <button class="icon-btn" @click.stop="startConnectFromTopoBranch(bp)" :title="t('connectDevice')">
                          <el-icon><Position /></el-icon>
                        </button>
                        <button class="icon-btn danger" @click.stop="deleteTopoBranchPoint(bp.id)" :title="t('actionDelete')">
                          <el-icon><Delete /></el-icon>
                        </button>
                      </div>
                    </div>
                    <div class="tree-node-children" v-if="expandedBranchPoints[bp.id]">
                      <div v-for="edge in getBranchLinksForTopoNode(bp.id)" :key="edge.id" class="fiber-tree-node branch-link-node">
                        <div class="tree-node-header">
                          <div class="tree-node-row">
                            <span class="link-name" :title="edge.cable_name || `Link-${edge.id}`">{{ edge.cable_name || `Link-${edge.id}` }}</span>
                          </div>
                          <div class="tree-node-actions">
                            <button class="icon-btn" @click.stop="openTopoEdgeWaypointDialog(edge)" :title="t('editWaypoints')">
                              <el-icon><Connection /></el-icon>
                            </button>
                            <button class="icon-btn danger" @click.stop="deleteTopoEdge(edge.id)" :title="t('actionDelete')">
                              <el-icon><Delete /></el-icon>
                            </button>
                          </div>
                        </div>
                      </div>
                      <div v-if="getBranchLinksForTopoNode(bp.id).length === 0" class="tree-empty-hint">
                        {{ t('noData') }}
                      </div>
                    </div>
                  </div>
                  <div v-if="getBranchPointsForCable(cable.cable_id).length === 0" class="tree-empty-hint">
                    {{ t('noData') }}
                  </div>
                </div>
              </div>
            </div>
            <div v-if="displayCables.length === 0" class="no-data">
              {{ t('noData') }}
            </div>
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
            <el-checkbox v-model="showPhysicalTopology">{{ t('showPhysicalTopology') }}</el-checkbox>
            <el-checkbox v-model="showDataLinks">{{ t('showDataLinks') }}</el-checkbox>
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
import { ref, reactive, onMounted, onBeforeUnmount, shallowRef, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js'
import { ElMessage } from 'element-plus'
import { Pointer, Warning, Upload, FullScreen, Close, ArrowLeft, ArrowRight, ArrowDown, Plus, Delete, Switch, Picture, Box, Position, Connection, Lock, Cpu } from '@element-plus/icons-vue'
import axios from 'axios'
import { useI18n } from '@/composables/useI18n'

const router = useRouter()
const canvasHost = ref(null)
const selectedDevice = ref(null)
const filterType = ref('')
const filterStatus = ref('')
const showLabels = ref(true)
const showLinks = ref(true)
const showPhysicalTopology = ref(true)  // 显示物理拓扑（光纤）
const showDataLinks = ref(true)         // 显示数据链路（设备间连接）
const floorTiltAngle = ref(0)  // 底图倾斜角度，0=水平，90=垂直
const isFullscreen = ref(false)  // 全屏模式
const { t } = useI18n()
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
        cable_id: edge.id,  // 用 edge.id 作为临时 cable_id
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

// 监听全局主题变化
window.addEventListener('theme-change', (e) => {
  isDark.value = e.detail.dark
})

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
    cancelWiring()
    // 清除端口锚点
    disposeGroup('port-anchors')
    // 重建 TopoEdge（去掉拐点球，保留边线）
    buildTopoEdges()
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

// 获取指定主干下的分支点（旧模型）
function getBranchPointsForTrunk(trunkId) {
  return fiberBranchPoints.value.filter(bp => bp.trunk_link_id === trunkId)
}

// 获取指定分支点下的分支光缆（旧模型）
function getBranchLinksForPoint(bpId) {
  return fiberBranchLinks.value.filter(link => link.branch_point_id === bpId)
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
  ElMessage.info(t('clickDeviceToConnect'))
}

// 从 topo 分支点连接设备
async function connectDeviceFromTopoBranch(deviceId) {
  if (!selectedTopoBranchPoint.value) return

  try {
    await axios.post(`/api/floor-plans/${currentPlanId.value}/topo/branch-cable`, {
      branch_point_id: selectedTopoBranchPoint.value.id,
      to_device_id: deviceId,
    })
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

// 开始从分支点连接设备
function startConnectFromBranch(bp) {
  connectFromBranchMode.value = true
  selectedBranchPoint.value = bp
  ElMessage.info(t('clickDeviceToConnect'))
}

// 创建主干光缆
async function createFiberTrunk() {
  if (!trunkStartPoint.value || !trunkEndPoint.value) return

  console.log('创建主干:', {
    planId: currentPlanId.value,
    start: trunkStartPoint.value,
    end: trunkEndPoint.value
  })

  try {
    // 使用新的 topo API 创建主干
    const res = await axios.post(`/api/floor-plans/${currentPlanId.value}/topo/trunk`, {
      name: `TRUNK-${fiberTrunks.value.length + 1}`,
      start_x: trunkStartPoint.value.x,
      start_y: trunkStartPoint.value.y,
      end_x: trunkEndPoint.value.x,
      end_y: trunkEndPoint.value.y,
    })
    console.log('创建主干成功:', res.data)
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
      devicePaths.value = topoPathsRes.data?.paths || {}
    } catch (e) {
      console.warn('加载 device-paths 失败:', e)
      devicePaths.value = {}
    }

    // 重建光纤渲染（优先使用新 topo 数据）
    disposeGroup('fiber-trunks')
    disposeGroup('branch-points')
    disposeGroup('branch-links')
    disposeGroup('topo-edges')
    disposeGroup('data-link-paths')

    // 使用新的图模型渲染
    buildTopoEdges()
    buildDataLinkPaths()
  } catch (e) {
    console.error('加载光纤数据失败:', e)
  }
}

// 删除主干光缆（旧 API）
async function deleteTrunk(trunkId) {
  try {
    await axios.delete(`/api/floor-plans/${currentPlanId.value}/fiber-trunks/${trunkId}`)
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('删除主干失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
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

// 删除分支点（旧 API）
async function deleteBranchPoint(bpId) {
  try {
    await axios.delete(`/api/floor-plans/${currentPlanId.value}/fiber-branch-points/${bpId}`)
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('删除分支点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
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

// 在主干上添加分支点（点击主干时）- 使用旧的 fiber API
async function addBranchPointOnTrunk(trunk, clickPos) {
  // 计算点击位置在主干上的百分比
  const positionPercent = calculatePositionPercentOnTrunk(trunk, clickPos)

  try {
    await axios.post(`/api/floor-plans/${currentPlanId.value}/fiber-branch-points`, {
      trunk_link_id: trunk.id,
      position_percent: positionPercent,
      name: `${fiberBranchPoints.value.length + 1}`,  // 只存储数字序号，显示时动态翻译
    })
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('添加分支点失败:', e)
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

// 计算点击位置在主干上的百分比
function calculatePositionPercentOnTrunk(trunk, clickPos) {
  const points = [{ x: trunk.start_x_percent, y: trunk.start_y_percent }]
  let waypoints = trunk.waypoints
  if (typeof waypoints === 'string') {
    try { waypoints = JSON.parse(waypoints) } catch (e) { waypoints = [] }
  }
  if (Array.isArray(waypoints)) points.push(...waypoints)
  points.push({ x: trunk.end_x_percent, y: trunk.end_y_percent })

  let totalLength = 0
  const segmentLengths = []
  for (let i = 1; i < points.length; i++) {
    const dx = points[i].x - points[i-1].x
    const dy = points[i].y - points[i-1].y
    const len = Math.sqrt(dx*dx + dy*dy)
    segmentLengths.push(len)
    totalLength += len
  }

  // 用向量投影精确计算最近点，替代暴力循环
  let minDist = Infinity
  let bestPercent = 0
  let accumulated = 0

  for (let i = 0; i < segmentLengths.length; i++) {
    const segLen = segmentLengths[i]
    const ax = points[i].x, ay = points[i].y
    const bx = points[i+1].x, by = points[i+1].y
    const dx = bx - ax, dy = by - ay

    if (segLen === 0) {
      const dist = Math.sqrt((ax - clickPos.x)**2 + (ay - clickPos.y)**2)
      if (dist < minDist) {
        minDist = dist
        bestPercent = accumulated / totalLength * 100
      }
      accumulated += segLen
      continue
    }

    // 向量投影: t = dot(P-A, B-A) / |B-A|^2
    const t = ((clickPos.x - ax) * dx + (clickPos.y - ay) * dy) / (segLen * segLen)
    const clampedT = Math.max(0, Math.min(1, t))
    const projX = ax + clampedT * dx
    const projY = ay + clampedT * dy
    const dist = Math.sqrt((projX - clickPos.x)**2 + (projY - clickPos.y)**2)

    if (dist < minDist) {
      minDist = dist
      bestPercent = (accumulated + clampedT * segLen) / totalLength * 100
    }
    accumulated += segLen
  }

  return bestPercent
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
  // waypoints 可能是字符串（旧数据）或已解析的数组（新接口）
  try {
    if (typeof link.waypoints === 'string') {
      editingWaypoints.value = JSON.parse(link.waypoints) || []
    } else if (Array.isArray(link.waypoints)) {
      editingWaypoints.value = link.waypoints
    } else {
      editingWaypoints.value = []
    }
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
      editingTrunkWaypoints.value = JSON.parse(trunk.waypoints) || []
    } else if (Array.isArray(trunk.waypoints)) {
      editingTrunkWaypoints.value = trunk.waypoints
    } else {
      editingTrunkWaypoints.value = []
    }
  } catch (e) {
    editingTrunkWaypoints.value = []
  }
  showTrunkWaypointDialog.value = true
}

// 添加主干拐点
function addTrunkWaypoint() {
  editingTrunkWaypoints.value.push({
    x: 50,
    y: 50
  })
}

// 删除主干拐点
function removeTrunkWaypoint(idx) {
  editingTrunkWaypoints.value.splice(idx, 1)
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
      editingBranchLinkWaypoints.value = JSON.parse(link.waypoints) || []
    } else if (Array.isArray(link.waypoints)) {
      editingBranchLinkWaypoints.value = link.waypoints
    } else {
      editingBranchLinkWaypoints.value = []
    }
  } catch (e) {
    editingBranchLinkWaypoints.value = []
  }
  showBranchLinkWaypointDialog.value = true
}

// 添加分支光缆拐点
function addBranchLinkWaypoint() {
  editingBranchLinkWaypoints.value.push({
    x: 50,
    y: 50
  })
}

// 删除分支光缆拐点
function removeBranchLinkWaypoint(idx) {
  editingBranchLinkWaypoints.value.splice(idx, 1)
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
      editingTopoEdgeWaypoints.value = JSON.parse(edge.waypoints) || []
    } else if (Array.isArray(edge.waypoints)) {
      editingTopoEdgeWaypoints.value = edge.waypoints
    } else {
      editingTopoEdgeWaypoints.value = []
    }
  } catch (e) {
    editingTopoEdgeWaypoints.value = []
  }
  showTopoEdgeWaypointDialog.value = true
}

// 添加 TopoEdge 拐点
function addTopoEdgeWaypoint() {
  editingTopoEdgeWaypoints.value.push({
    x: 50,
    y: 50
  })
}

// 删除 TopoEdge 拐点
function removeTopoEdgeWaypoint(idx) {
  editingTopoEdgeWaypoints.value.splice(idx, 1)
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
    buildTopoEdges()

    showTopoEdgeWaypointDialog.value = false
    editingTopoEdge.value = null
  } catch (e) {
    console.error('保存 TopoEdge 拐点失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }
}

// 构建 TopoEdge 渲染
function buildTopoEdges() {
  const { scene } = ctx.value
  if (!scene || topoEdges.value.length === 0) return

  // 清除旧渲染
  disposeGroup('topo-edges')

  const edgeGroup = new THREE.Group()
  edgeGroup.name = 'topo-edges'

  const edgeHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
  const edgeRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001
  const wpRadius = edgeRadius * 2.5  // 拐点球半径

  topoEdges.value.forEach(edge => {
    // 找两端节点坐标
    const aNode = topoNodes.value.find(n => n.id === edge.a_node_id)
    const bNode = topoNodes.value.find(n => n.id === edge.b_node_id)
    if (!aNode || !bNode) return

    const startX = parseFloat(aNode.x_percent)
    const startY = parseFloat(aNode.y_percent)
    const endX = parseFloat(bNode.x_percent)
    const endY = parseFloat(bNode.y_percent)

    // 解析拐点
    let waypoints = []
    try {
      if (typeof edge.waypoints === 'string') {
        waypoints = JSON.parse(edge.waypoints) || []
      } else if (Array.isArray(edge.waypoints)) {
        waypoints = edge.waypoints
      }
    } catch (e) {
      waypoints = []
    }

    // 构建所有点
    const points = [
      { x: startX, y: startY },
      ...waypoints,
      { x: endX, y: endY }
    ]

    // 颜色根据 cable_type
    let color = 0x22c55e  // 默认绿色（分支光缆）
    if (edge.cable_type === 'trunk') color = 0x3b82f6  // 主干蓝色
    if (edge.cable_type === 'trunk_to_core') color = 0xf59e0b  // 核心-主干橙色
    if (edge.cable_type === 'trunk_segment') color = 0x8b5cf6  // 主干段紫色
    if (edge.status === 'down') color = 0xff4d4f  // 断开红色

    const mat = new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity: 0.8,
    })

    // 绘制每段
    for (let i = 0; i < points.length - 1; i++) {
      const pt1 = points[i]
      const pt2 = points[i + 1]

      const start = percentToWorld(pt1.x, pt1.y, edgeHeight)
      const end = percentToWorld(pt2.x, pt2.y, edgeHeight)

      const direction = new THREE.Vector3().subVectors(end, start)
      const length = direction.length()

      if (length < 1e-6) continue

      const midPoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)

      const cylinderGeo = new THREE.CylinderGeometry(edgeRadius, edgeRadius, length, 8)
      const cylinder = new THREE.Mesh(cylinderGeo, mat)
      cylinder.position.copy(midPoint)

      const axis = new THREE.Vector3(0, 1, 0)
      const normalizedDir = direction.clone().normalize()
      if (normalizedDir.length() < 0.5) continue
      const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, normalizedDir)
      cylinder.quaternion.copy(quaternion)

      // 存储边信息用于点击选择
      cylinder.userData.topoEdge = {
        id: edge.id,
        aNodeId: edge.a_node_id,
        bNodeId: edge.b_node_id,
        cableType: edge.cable_type,
        cableId: edge.cable_id,
        cableNo: edge.cable_no,
        cableName: edge.cable_name,
        segmentIndex: i,
      }
      cylinder.name = `topo-edge-${edge.id}-seg-${i}`
      edgeGroup.add(cylinder)
    }

    // 添加拐点球（白色，可拖拽）
    if (waypoints.length > 0 && isEditMode.value) {
      waypoints.forEach((wp, idx) => {
        const wpWorld = percentToWorld(wp.x, wp.y, edgeHeight)
        const sphereGeo = new THREE.SphereGeometry(wpRadius, 16, 16)
        const sphereMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 1.0 })
        const sphere = new THREE.Mesh(sphereGeo, sphereMat)
        sphere.position.set(wpWorld.x, wpWorld.y, wpWorld.z)
        sphere.userData.topoEdgeWaypoint = {
          edgeId: edge.id,
          index: idx,
          x: wp.x,
          y: wp.y,
        }
        sphere.name = `topo-edge-waypoint-${edge.id}-${idx}`
        edgeGroup.add(sphere)
      })
    }
  })

  scene.add(edgeGroup)
  ctx.value.topoEdgesGroup = edgeGroup

  // 渲染 junction 节点球（分支点）
  const junctionNodes = topoNodes.value.filter(n => n.node_kind === 'junction' && n.junction_type === 'branch_point')
  if (junctionNodes.length > 0) {
    const bpHeight = edgeHeight + 1  // 分支点略高于边
    const bpRadius = edgeRadius * 3  // 分支点球比边粗

    junctionNodes.forEach(node => {
      const bpWorld = percentToWorld(node.x_percent, node.y_percent, bpHeight)
      const sphereGeo = new THREE.SphereGeometry(bpRadius, 16, 16)
      const sphereMat = new THREE.MeshBasicMaterial({
        color: 0xfbbf24,  // 黄色（分支点）
        transparent: true,
        opacity: 1.0,
      })
      const sphere = new THREE.Mesh(sphereGeo, sphereMat)
      sphere.position.set(bpWorld.x, bpWorld.y, bpWorld.z)
      sphere.userData.topoNode = node
      sphere.name = `junction-${node.id}`
      edgeGroup.add(sphere)

      // 添加分支点标签（CSS2D）
      if (node.label && isEditMode.value) {
        const labelEl = document.createElement('div')
        labelEl.className = 'topo-label junction-label'
        labelEl.textContent = node.label
        const labelObj = new CSS2DObject(labelEl)
        labelObj.position.set(bpWorld.x, bpWorld.y + bpRadius * 2, bpWorld.z)
        edgeGroup.add(labelObj)
      }
    })
  }

  // 渲染 trunk_endpoint（主干起点终点，编辑模式下可拖拽）
  if (isEditMode.value) {
    const trunkEndpoints = topoNodes.value.filter(n => n.node_kind === 'junction' && n.junction_type === 'trunk_endpoint')
    if (trunkEndpoints.length > 0) {
      const epHeight = edgeHeight + edgeRadius * 2
      const epRadius = edgeRadius * 4  // 起点终点球更大

      trunkEndpoints.forEach(node => {
        const epWorld = percentToWorld(node.x_percent, node.y_percent, epHeight)
        const sphereGeo = new THREE.SphereGeometry(epRadius, 16, 16)
        // 起点绿色，终点红色
        const isStart = node.label && node.label.includes('起点')
        const sphereMat = new THREE.MeshBasicMaterial({
          color: isStart ? 0x22c55e : 0xef4444,
          transparent: true,
          opacity: 1.0,
        })
        const sphere = new THREE.Mesh(sphereGeo, sphereMat)
        sphere.position.set(epWorld.x, epWorld.y, epWorld.z)
        sphere.userData.topoEndpoint = {
          nodeId: node.id,
          type: isStart ? 'start' : 'end',
          x: node.x_percent,
          y: node.y_percent,
        }
        sphere.name = `topo-endpoint-${node.id}`
        edgeGroup.add(sphere)
      })
    }
  }

  // 添加 cable_no 标签（只在编辑模式下显示）
  if (isEditMode.value) {
    // 按 cable_id 聚合，只在每条光缆的中点显示一个标签
    const cablesMap = new Map()
    topoEdges.value.forEach(edge => {
      if (edge.cable_id && edge.cable_no) {
        if (!cablesMap.has(edge.cable_id)) {
          cablesMap.set(edge.cable_id, { cable_no: edge.cable_no, cable_name: edge.cable_name, edges: [] })
        }
        cablesMap.get(edge.cable_id).edges.push(edge)
      }
    })

    cablesMap.forEach((cable, cableId) => {
      // 计算光缆中点位置
      const cableEdges = cable.edges
      if (cableEdges.length === 0) return

      // 取第一条边的起点作为标签位置
      const firstEdge = cableEdges[0]
      const aNode = topoNodes.value.find(n => n.id === firstEdge.a_node_id)
      if (!aNode) return

      const labelWorld = percentToWorld(aNode.x_percent, aNode.y_percent, edgeHeight + edgeRadius * 4)

      const labelEl = document.createElement('div')
      labelEl.className = 'topo-label cable-label'
      labelEl.textContent = cable.cable_no
      const labelObj = new CSS2DObject(labelEl)
      labelObj.position.set(labelWorld.x, labelWorld.y, labelWorld.z)
      edgeGroup.add(labelObj)
    })
  }
}

// 动态翻译主干名称
function getTrunkDisplayName(trunk) {
  if (!trunk.name) return `${t('fiberTrunk')} ${trunk.id}`
  // 如果名称是纯数字，添加翻译前缀
  if (/^\d+$/.test(trunk.name)) return `${t('fiberTrunk')} ${trunk.name}`
  // 如果名称包含中文或英文前缀，解析数字并重新翻译
  const match = trunk.name.match(/(?:光纤主干|Fiber\s*Trunk)\s*(\d+)/i)
  if (match) return `${t('fiberTrunk')} ${match[1]}`
  // 其他情况直接显示
  return trunk.name
}

// 动态翻译分支点名称
function getBranchPointDisplayName(bp) {
  if (!bp.name) return `${t('fiberBranchPoint')} ${bp.id}`
  // 如果名称是纯数字，添加翻译前缀
  if (/^\d+$/.test(bp.name)) return `${t('fiberBranchPoint')} ${bp.name}`
  // 如果名称包含中文或英文前缀，解析数字并重新翻译
  const match = bp.name.match(/(?:分支点|Branch\s*Point)\s*(\d+)/i)
  if (match) return `${t('fiberBranchPoint')} ${match[1]}`
  // 其他情况直接显示
  return bp.name
}

// 获取分支光缆名称（完整显示）
function getBranchLinkName(link) {
  const bp = fiberBranchPoints.value.find(bp => bp.id === link.branch_point_id)
  const device = devices.value.find(d => d.id === link.to_device_id)
  const bpName = bp ? getBranchPointDisplayName(bp) : `${t('fiberBranchPoint')} ${link.branch_point_id}`
  const deviceName = device ? device.name : `Device ${link.to_device_id}`
  return `${bpName} → ${deviceName}`
}

// 获取分支光缆设备名称（只显示设备名，用于树节点）
function getBranchLinkDeviceName(link) {
  const device = devices.value.find(d => d.id === link.to_device_id)
  return device ? device.name : `Device ${link.to_device_id}`
}

// 删除分支光缆
async function deleteBranchLink(linkId) {
  try {
    await axios.delete(`/api/floor-plans/${currentPlanId.value}/fiber-branch-links/${linkId}`)
    ElMessage.success(t('msgSaveSuccess'))
    await loadFiberData()
  } catch (e) {
    console.error('删除分支光缆失败:', e)
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
  fiberTrunkGroup: null,
  branchPointGroup: null,
  branchLinkGroup: null,
  dataLinkPaths: null,
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

// 设备发光颜色（让设备在暗背景下更醒目）
const STATUS_EMISSIVE = { online: 0x0a4a5e, offline: 0x5a1a1a, maintenance: 0x5a3a0a }

// 复用的 emissive 颜色常量（避免每次 new THREE.Color）
const EMISSIVE_ON = new THREE.Color(0x333333)
const EMISSIVE_OFF = new THREE.Color(0x000000)

// 创建立体设备模型（基于底图比例）
function createDeviceModel(deviceType, status = 'online') {
  const group = new THREE.Group()
  const base = getDeviceBaseSize(deviceType)
  const color = STATUS_COLOR[status] || STATUS_COLOR.online
  const emissive = STATUS_EMISSIVE[status] || STATUS_EMISSIVE.online
  const bodyMat = new THREE.MeshStandardMaterial({ color, metalness: 0.4, roughness: 0.5, emissive, emissiveIntensity: 0.3 })
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
    rebuildScene()
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
  if (!host) return
  // 清除可能残留的旧画布（HMR/重复挂载防护，避免画布堆叠导致设备等重影）
  while (host.firstChild) host.removeChild(host.firstChild)
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

  // 清除旧设备组（移除所有同名组，防止重复累积）
  disposeGroup('devices')

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
  if (!scene) return
  // 移除所有同名直接子组（防止同名组残留导致重复渲染）
  const groups = scene.children.filter(o => o.name === name)
  groups.forEach(g => {
    g.traverse(o => {
      // 清理 CSS2DObject 的 DOM 元素
      if (o.element && o.element.parentNode) {
        o.element.parentNode.removeChild(o.element)
      }
      o.geometry?.dispose?.()
      o.material?.dispose?.()
    })
    scene.remove(g)
  })
}

// 重建场景（底图切换或节点变化后）
function rebuildScene() {
  disposeGroup('devices')
  disposeGroup('links')
  disposeGroup('labels')
  disposeGroup('fiber-trunks')
  disposeGroup('branch-points')
  disposeGroup('branch-links')
  disposeGroup('data-link-paths')
  buildDeviceModels()
  buildLinks()
  buildTopoEdges()
  buildDataLinkPaths()
  buildLabels()
}

// 构建链路（支持 waypoints 正交折线）
function buildLinks() {
  const { scene } = ctx.value

  const linkGroup = new THREE.Group()
  linkGroup.name = 'links'

  // 链路高度：比主干光缆稍微高一点，避免重叠
  const trunkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
  const linkHeight = trunkHeight + 0.5  // 链路浮在主干上方
  // 链路圆柱半径：比主干细一点
  const linkRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001

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
        // waypoints 可能是字符串或已解析的数组
        const waypoints = typeof link.waypoints === 'string'
          ? JSON.parse(link.waypoints)
          : link.waypoints
        if (Array.isArray(waypoints)) {
          waypoints.forEach(wp => {
            const wpWorld = percentToWorld(wp.x, wp.y, linkHeight)
            points.push(new THREE.Vector3(wpWorld.x, wpWorld.y, wpWorld.z))
          })
        }
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

    // 链路状态颜色：正常绿色，异常红色
    const statusColor = link.status === 'broken' ? 0xff4d4f : 0x22c55e  // 红色/绿色
    const mat = new THREE.MeshBasicMaterial({
      color: statusColor,
      transparent: true,
      opacity: 0.8,
    })

    // 使用圆柱体绘制每段链路（更粗、更可见）
    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i]
      const end = points[i + 1]

      const direction = new THREE.Vector3().subVectors(end, start)
      const length = direction.length()
      const midPoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)

      const cylinderGeo = new THREE.CylinderGeometry(linkRadius, linkRadius, length, 8)
      const cylinder = new THREE.Mesh(cylinderGeo, mat)
      cylinder.position.copy(midPoint)

      const axis = new THREE.Vector3(0, 1, 0)
      const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, direction.clone().normalize())
      cylinder.quaternion.copy(quaternion)

      cylinder.userData.link = link
      cylinder.name = `link-${link.id}-seg-${i}`
      linkGroup.add(cylinder)
    }

    // 如果有拐点且在编辑模式，添加拐点标记球
    if (link.waypoints && isEditMode.value) {
      try {
        // waypoints 可能是字符串或已解析的数组
        const waypoints = typeof link.waypoints === 'string'
          ? JSON.parse(link.waypoints)
          : link.waypoints
        if (Array.isArray(waypoints)) {
          waypoints.forEach((wp, idx) => {
            const wpWorld = percentToWorld(wp.x, wp.y, linkHeight + linkRadius * 2)
            // 拐点球半径
            const wpRadius = linkRadius * 2.5
            const sphereGeo = new THREE.SphereGeometry(wpRadius, 16, 16)
            const sphereMat = new THREE.MeshBasicMaterial({ color: 0xffc107, transparent: true, opacity: 1.0 })  // 黄色
            const sphere = new THREE.Mesh(sphereGeo, sphereMat)
            sphere.position.set(wpWorld.x, wpWorld.y, wpWorld.z)
            sphere.userData.waypoint = { linkId: link.id, index: idx, x: wp.x, y: wp.y }
            sphere.name = `waypoint-${link.id}-${idx}`
            linkGroup.add(sphere)
          })
        }
      } catch (e) {}
    }
  })

  scene.add(linkGroup)
  ctx.value.linkLines = linkGroup
}

// 根据位置百分比计算主干上的坐标
function calculatePositionOnTrunk(trunk, positionPercent) {
  // 获取主干路径点
  const points = [{ x: trunk.start_x_percent, y: trunk.start_y_percent }]

  if (trunk.waypoints && Array.isArray(trunk.waypoints)) {
    trunk.waypoints.forEach(wp => points.push({ x: wp.x, y: wp.y }))
  }

  points.push({ x: trunk.end_x_percent, y: trunk.end_y_percent })

  // 计算总长度
  let totalLength = 0
  const segmentLengths = []
  for (let i = 1; i < points.length; i++) {
    const dx = points[i].x - points[i-1].x
    const dy = points[i].y - points[i-1].y
    const len = Math.sqrt(dx*dx + dy*dy)
    segmentLengths.push(len)
    totalLength += len
  }

  // 根据位置百分比找到对应点
  const targetLength = totalLength * positionPercent / 100
  let accumulated = 0

  for (let i = 0; i < segmentLengths.length; i++) {
    if (accumulated + segmentLengths[i] >= targetLength) {
      const remaining = targetLength - accumulated
      const ratio = segmentLengths[i] > 0 ? remaining / segmentLengths[i] : 0
      const x = points[i].x + ratio * (points[i+1].x - points[i].x)
      const y = points[i].y + ratio * (points[i+1].y - points[i].y)
      return { x, y }
    }
    accumulated += segmentLengths[i]
  }

  // 超出范围返回终点
  return { x: trunk.end_x_percent, y: trunk.end_y_percent }
}

// 构建数据链路路径（沿着光纤拓扑）- 使用后端返回的 polyline
function buildDataLinkPaths() {
  const { scene } = ctx.value
  if (!scene || !devicePaths.value || Object.keys(devicePaths.value).length === 0) return

  const pathGroup = new THREE.Group()
  pathGroup.name = 'data-link-paths'

  // 路径高度：在物理拓扑上方
  const trunkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
  const pathHeight = trunkHeight + 0.8
  // 路径线半径（比链路稍细）
  const pathRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.0008

  Object.entries(devicePaths.value).forEach(([deviceId, pathData]) => {
    // 支持两种格式：
    // 旧格式：pathData 是数组 [{x_percent, y_percent}, ...]
    // 新格式：pathData 是对象 {reachable, polyline: [{x_percent, y_percent}, ...]}
    let polyline = pathData
    if (pathData && typeof pathData === 'object' && !Array.isArray(pathData)) {
      if (!pathData.reachable) return  // 不可达，跳过
      polyline = pathData.polyline || []
    }

    if (!Array.isArray(polyline) || polyline.length < 2) return

    // 获取设备状态
    const device = devices.value.find(d => d.id === parseInt(deviceId))
    const status = device ? device.status : 'unknown'
    const statusColor = status === 'online' ? 0x22c55e : 0xff4d4f  // 绿色/红色

    // 直接使用 polyline 的 x_percent, y_percent（后端已去重）
    const points = polyline.map(pt => {
      if (pt.x_percent != null && pt.y_percent != null) {
        const pos = percentToWorld(pt.x_percent, pt.y_percent, pathHeight)
        return new THREE.Vector3(pos.x, pos.y, pos.z)
      }
      return null
    }).filter(p => p !== null)

    // 如果点数少于2，无法绘制路径
    if (points.length < 2) return

    // 使用圆柱体绘制路径线
    const mat = new THREE.MeshBasicMaterial({
      color: statusColor,
      transparent: true,
      opacity: 0.7,
    })

    for (let i = 0; i < points.length - 1; i++) {
      const start = points[i]
      const end = points[i + 1]

      const direction = new THREE.Vector3().subVectors(end, start)
      const length = direction.length()

      // 零长度段防御：跳过长度过小的段
      if (length < 1e-6) continue

      const midPoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)

      const cylinderGeo = new THREE.CylinderGeometry(pathRadius, pathRadius, length, 8)
      const cylinder = new THREE.Mesh(cylinderGeo, mat)
      cylinder.position.copy(midPoint)

      const axis = new THREE.Vector3(0, 1, 0)
      const normalizedDir = direction.clone().normalize()
      // 防止 normalize 后仍然是零向量（虽然上面已检查，但双重保险）
      if (normalizedDir.length() < 0.5) continue
      const quaternion = new THREE.Quaternion().setFromUnitVectors(axis, normalizedDir)
      cylinder.quaternion.copy(quaternion)

      cylinder.userData.dataPath = { deviceId: parseInt(deviceId), segmentIndex: i }
      cylinder.name = `data-path-${deviceId}-seg-${i}`
      pathGroup.add(cylinder)
    }
  })

  scene.add(pathGroup)
  ctx.value.dataLinkPaths = pathGroup
}

// ========== PNetLab 式端口连线交互 ==========

// 连线状态
const wiringState = ref(null)  // { fromNodeId, fromWorldPos, rubberBandLine }
const devicePorts = ref([])    // 设备端口数据
const topoNodes = ref([])      // 拓扑节点数据
const topoEdges = ref([])      // 拓扑边数据

// 加载设备端口和拓扑数据
async function loadTopoData() {
  try {
    // 先幂等补建所有设备的端口及端口拓扑节点（兼容旧设备），确保连线可用
    await axios.post(`/api/floor-plans/${currentPlanId.value}/ensure-topo-ports`).catch(() => {})

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
    buildPortAnchors()
    // 构建 TopoEdge 渲染
    buildTopoEdges()
  } catch (e) {
    console.error('加载拓扑数据失败:', e)
  }
}

// 构建端口锚点（设备上的小圆点）
function buildPortAnchors() {
  const { scene } = ctx.value
  if (!scene) return

  // 清除旧锚点
  disposeGroup('port-anchors')

  if (!isEditMode.value) return  // 只在编辑模式显示

  const anchorGroup = new THREE.Group()
  anchorGroup.name = 'port-anchors'

  const refDim = Math.min(plan.real_width_m, plan.real_depth_m)
  const anchorRadius = refDim * 0.004   // 放大，编辑模式下清晰可见
  const anchorHeight = refDim * 0.006   // 抬高，浮在设备模型上方

  // 遍历设备节点，显示端口锚点
  nodes.value.forEach(node => {
    const device = devices.value.find(d => d.id === node.device_id)
    if (!device) return

    // 获取该设备的端口
    const ports = devicePorts.value.filter(p => p.device_id === device.id)
    if (ports.length === 0) {
      // 如果没有端口数据，显示默认中心锚点
      ports.push({
        id: `auto-${node.id}`,
        device_id: device.id,
        name: 'auto',
        anchor_x: 0.5,
        anchor_y: 0.5,
        is_auto_created: true,
      })
    }

    ports.forEach(port => {
      // 计算锚点位置（设备坐标 + 锚点偏移）
      const baseX = parseFloat(node.x_percent)
      const baseY = parseFloat(node.y_percent)
      const iconSize = 3.0  // 设备图标大小约 3%
      const offsetX = (port.anchor_x - 0.5) * iconSize
      const offsetY = (port.anchor_y - 0.5) * iconSize

      const worldPos = percentToWorld(baseX + offsetX, baseY + offsetY, anchorHeight)

      const anchorColor = port.is_auto_created ? 0x22c55e : 0x3b82f6  // 自动=绿色 手动=蓝色

      // 创建锚点球（核心，不透明、鲜亮）
      const sphereGeo = new THREE.SphereGeometry(anchorRadius, 16, 16)
      const sphereMat = new THREE.MeshBasicMaterial({
        color: anchorColor,
        transparent: false,
      })
      const sphere = new THREE.Mesh(sphereGeo, sphereMat)
      sphere.position.set(worldPos.x, worldPos.y, worldPos.z)
      sphere.userData.portAnchor = {
        portId: port.id,
        deviceId: device.id,
        deviceName: device.name,
        anchorX: baseX + offsetX,
        anchorY: baseY + offsetY,
      }
      sphere.name = `port-anchor-${device.id}-${port.id}`
      anchorGroup.add(sphere)

      // 外层发光光环（半透明，不参与射线拾取，避免遮挡核心球）
      const haloGeo = new THREE.SphereGeometry(anchorRadius * 1.9, 16, 16)
      const haloMat = new THREE.MeshBasicMaterial({
        color: anchorColor,
        transparent: true,
        opacity: 0.22,
        depthWrite: false,
      })
      const halo = new THREE.Mesh(haloGeo, haloMat)
      halo.position.set(worldPos.x, worldPos.y, worldPos.z)
      halo.raycast = () => {}
      anchorGroup.add(halo)
    })
  })

  scene.add(anchorGroup)
  ctx.value.portAnchors = anchorGroup
}

// 处理端口锚点点击（开始连线）
function onPortAnchorMouseDown(anchorData) {
  if (!isEditMode.value) return

  // 查找该端口对应的 topoNode（直接用锚点的 portId 精确匹配）
  const topoNode = topoNodes.value.find(n =>
    n.node_kind === 'port' && n.port_id === anchorData.portId
  )

  if (!topoNode) {
    // 没有拓扑节点，需要先创建
    console.log('需要先创建拓扑节点')
    ElMessage.warning(t('msgUpdateFailed'))
    return
  }

  // 进入连线态
  const worldPos = percentToWorld(anchorData.anchorX, anchorData.anchorY, Math.min(plan.real_width_m, plan.real_depth_m) * 0.003)

  wiringState.value = {
    fromNodeId: topoNode.id,
    fromDeviceId: anchorData.deviceId,
    fromWorldPos: worldPos,
    fromAnchorX: anchorData.anchorX,
    fromAnchorY: anchorData.anchorY,
    rubberBandLine: null,
  }

  // 创建橡皮筋线
  const { scene, renderer } = ctx.value
  if (scene) {
    const lineMat = new THREE.LineBasicMaterial({ color: 0x22c55e, linewidth: 2 })
    const lineGeo = new THREE.BufferGeometry()
    lineGeo.setFromPoints([
      new THREE.Vector3(worldPos.x, worldPos.y, worldPos.z),
      new THREE.Vector3(worldPos.x, worldPos.y, worldPos.z),
    ])
    const line = new THREE.Line(lineGeo, lineMat)
    line.name = 'rubber-band'
    scene.add(line)
    wiringState.value.rubberBandLine = line
  }

  // 添加鼠标移动和释放监听器
  renderer?.domElement?.addEventListener('mousemove', onWiringMouseMove)
  renderer?.domElement?.addEventListener('mouseup', onWiringMouseUp)
}

// 更新橡皮筋线位置
function updateRubberBandLine(mouseWorldPos) {
  if (!wiringState.value || !wiringState.value.rubberBandLine) return

  const line = wiringState.value.rubberBandLine
  const positions = line.geometry.attributes.position.array
  positions[3] = mouseWorldPos.x
  positions[4] = mouseWorldPos.y
  positions[5] = mouseWorldPos.z
  line.geometry.attributes.position.needsUpdate = true
}

// 结束连线（创建 TopoEdge）
async function finishWiring(targetAnchorData) {
  if (!wiringState.value) return

  // 查找目标 topoNode（直接用锚点的 portId 精确匹配）
  const targetTopoNode = topoNodes.value.find(n =>
    n.node_kind === 'port' && n.port_id === targetAnchorData.portId
  )

  if (!targetTopoNode) {
    console.log('目标设备没有拓扑节点')
    cancelWiring()
    return
  }

  // 不能连接到自己
  if (wiringState.value.fromDeviceId === targetAnchorData.deviceId) {
    cancelWiring()
    return
  }

  // 创建 TopoEdge
  try {
    await axios.post(`/api/floor-plans/${currentPlanId.value}/topo-edges`, {
      floor_plan_id: currentPlanId.value,
      a_node_id: wiringState.value.fromNodeId,
      b_node_id: targetTopoNode.id,
      cable_type: 'fiber',
      cable_name: `${devices.value.find(d => d.id === wiringState.value.fromDeviceId)?.name || 'A'} - ${devices.value.find(d => d.id === targetAnchorData.deviceId)?.name || 'B'}`,
      status: 'up',
    })

    ElMessage.success(t('msgSaveSuccess'))

    // 重新加载拓扑数据
    await loadTopoData()
    await loadFiberData()
  } catch (e) {
    console.error('创建连接失败:', e)
    ElMessage.error(t('msgUpdateFailed'))
  }

  cancelWiring()
}

// 取消连线
function cancelWiring() {
  // 移除事件监听器
  ctx.value.renderer?.domElement?.removeEventListener('mousemove', onWiringMouseMove)
  ctx.value.renderer?.domElement?.removeEventListener('mouseup', onWiringMouseUp)

  // 清除橡皮筋线
  if (wiringState.value && wiringState.value.rubberBandLine) {
    const { scene } = ctx.value
    if (scene) {
      scene.remove(wiringState.value.rubberBandLine)
      wiringState.value.rubberBandLine.geometry.dispose()
      wiringState.value.rubberBandLine.material.dispose()
    }
  }

  // 恢复控制器
  if (ctx.value.controls) {
    ctx.value.controls.enabled = true
  }

  wiringState.value = null
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

// 主干拐点拖动状态
let trunkWaypointDragState = null
let selectedTrunkWaypointSphere = null

// 主干端点拖拽状态
let trunkEndpointDragState = null
let selectedTrunkEndpointSphere = null

// 分支点拖拽状态
let branchPointDragState = null
let selectedBranchPointSphere = null

// 分支光缆拐点拖拽状态
let branchLinkWaypointDragState = null
let selectedBranchLinkWaypointSphere = null

// 编辑模式鼠标按下 - 拖动起点（支持拐点和设备拖动）
function onCanvasMouseDown(e) {
  if (!isEditMode.value) return

  const { camera, renderer, deviceGroup, linkLines, controls, fiberTrunkGroup, branchPointGroup, branchLinkGroup } = ctx.value

  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  // ========== 光纤主干交互 ==========

  // 处理主干创建模式的点击
  if (trunkCreateMode.value) {
    const pos = screenToPercent(e)
    if (!pos) return

    if (!trunkStartPoint.value) {
      trunkStartPoint.value = { x: pos.x_percent, y: pos.y_percent }
      ElMessage.info(t('clickTrunkEnd'))
    } else {
      trunkEndPoint.value = { x: pos.x_percent, y: pos.y_percent }
      createFiberTrunk()
    }
    return
  }

  // 处理从分支点连接设备模式
  if (connectFromBranchMode.value) {
    const hits = raycaster.intersectObjects(deviceGroup?.children || [], true)
    if (hits.length > 0) {
      let model = hits[0].object
      while (model && !model.userData.device) {
        model = model.parent
      }
      if (model && model.userData.device) {
        // 根据选中的分支点类型使用不同的连接函数
        if (selectedTopoBranchPoint.value) {
          connectDeviceFromTopoBranch(model.userData.device.id)
        } else if (selectedBranchPoint.value) {
          connectDeviceFromBranch(model.userData.device.id)
        }
      }
    }
    return
  }

  // ========== PNetLab 式端口连线交互 ==========

  // 检查是否处于连线态（更新橡皮筋）
  if (wiringState.value) {
    // 这是 mouseup 应该在另一个处理器中处理
    return
  }

  // 检查是否点击了端口锚点（开始连线）
  if (ctx.value.portAnchors) {
    const anchorHits = raycaster.intersectObjects(ctx.value.portAnchors.children, false)
    if (anchorHits.length > 0) {
      const sphere = anchorHits[0].object
      if (sphere.userData.portAnchor) {
        onPortAnchorMouseDown(sphere.userData.portAnchor)
        controls.enabled = false
        return
      }
    }
  }

  // ========== 光纤主干交互 ==========
  if (fiberTrunkGroup) {
    const endpointSpheres = fiberTrunkGroup.children.filter(c => c.userData.trunkEndpoint)
    const epHits = raycaster.intersectObjects(endpointSpheres, false)

    if (epHits.length > 0) {
      const sphere = epHits[0].object
      const ep = sphere.userData.trunkEndpoint

      trunkEndpointDragState = {
        trunkId: ep.trunkId,
        type: ep.type,  // 'start' or 'end'
        startX: ep.x,
        startY: ep.y,
      }
      selectedTrunkEndpointSphere = sphere

      // 高亮端点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onTrunkEndpointDragMove)
      renderer.domElement.addEventListener('mouseup', onTrunkEndpointDragEnd)
      return
    }
  }

  // 检查是否点击了分支点球（可拖动调整位置）- 新 topo 模型
  if (ctx.value.topoEdgesGroup) {
    const bpSpheres = ctx.value.topoEdgesGroup.children.filter(c => c.userData.topoNode && c.userData.topoNode.junction_type === 'branch_point')
    if (bpSpheres.length > 0) {
      const bpHits = raycaster.intersectObjects(bpSpheres, false)
      if (bpHits.length > 0) {
        const sphere = bpHits[0].object
        const node = sphere.userData.topoNode

        branchPointDragState = {
          nodeId: node.id,
          startX: node.x_percent,
          startY: node.y_percent,
        }
        selectedBranchPointSphere = sphere

        // 高亮分支点球
        sphere.material.color.set(0x22d3ee)

        controls.enabled = false
        isDragging = false

        renderer.domElement.addEventListener('mousemove', onBranchPointDragMove)
        renderer.domElement.addEventListener('mouseup', onBranchPointDragEnd)
        return
      }
    }
  }

  // 检查是否点击了分支光缆拐点球
  if (branchLinkGroup) {
    const waypointSpheres = branchLinkGroup.children.filter(c => c.userData.branchLinkWaypoint)
    const wpHits = raycaster.intersectObjects(waypointSpheres, false)

    if (wpHits.length > 0) {
      const sphere = wpHits[0].object
      const wp = sphere.userData.branchLinkWaypoint

      branchLinkWaypointDragState = {
        linkId: wp.linkId,
        index: wp.index,
        startX: wp.x,
        startY: wp.y,
      }
      selectedBranchLinkWaypointSphere = sphere

      // 高亮拐点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onBranchLinkWaypointDragMove)
      renderer.domElement.addEventListener('mouseup', onBranchLinkWaypointDragEnd)
      return
    }
  }

  // 检查是否点击了 TopoEndpoint（主干起点终点）
  if (isEditMode.value && !branchPointCreateMode.value && ctx.value.topoEdgesGroup) {
    const endpointSpheres = ctx.value.topoEdgesGroup.children.filter(c => c.userData.topoEndpoint)
    const epHits = raycaster.intersectObjects(endpointSpheres, false)

    if (epHits.length > 0) {
      const sphere = epHits[0].object
      const ep = sphere.userData.topoEndpoint

      topoEndpointDragState = {
        nodeId: ep.nodeId,
        type: ep.type,
        startX: ep.x,
        startY: ep.y,
      }
      selectedTopoEndpointSphere = sphere

      // 高亮端点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onTopoEndpointDragMove)
      renderer.domElement.addEventListener('mouseup', onTopoEndpointDragEnd)
      return
    }
  }

  // 检查是否点击了 TopoEdge 拐点球（优先于边管体）
  if (isEditMode.value && !branchPointCreateMode.value && ctx.value.topoEdgesGroup) {
    const waypointSpheres = ctx.value.topoEdgesGroup.children.filter(c => c.userData.topoEdgeWaypoint)
    const wpHits = raycaster.intersectObjects(waypointSpheres, false)

    if (wpHits.length > 0) {
      const sphere = wpHits[0].object
      const wp = sphere.userData.topoEdgeWaypoint

      topoEdgeWaypointDragState = {
        edgeId: wp.edgeId,
        index: wp.index,
        startX: wp.x,
        startY: wp.y,
      }
      selectedTopoEdgeWaypointSphere = sphere

      // 高亮拐点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onTopoEdgeWaypointDragMove)
      renderer.domElement.addEventListener('mouseup', onTopoEdgeWaypointDragEnd)
      return
    }
  }

  // 检查是否点击了 TopoEdge（编辑模式下点击打开拐点对话框）
  if (isEditMode.value && !branchPointCreateMode.value && ctx.value.topoEdgesGroup) {
    const edgeHits = raycaster.intersectObjects(ctx.value.topoEdgesGroup.children, false)
    if (edgeHits.length > 0) {
      const cylinder = edgeHits[0].object
      if (cylinder.userData.topoEdge) {
        // 找到对应的 TopoEdge 数据
        const edgeData = cylinder.userData.topoEdge
        const edge = topoEdges.value.find(e => e.id === edgeData.id)
        if (edge) {
          // 双击打开拐点编辑对话框
          if (isEditMode.value) {
            openTopoEdgeWaypointDialog(edge)
            return
          }
        }
      }
    }
  }

  // 检查是否点击了主干拐点球（优先于主干管体）
  if (fiberTrunkGroup) {
    const trunkWaypointSpheres = fiberTrunkGroup.children.filter(c => c.userData.trunkWaypoint)
    const wpHits = raycaster.intersectObjects(trunkWaypointSpheres, false)

    if (wpHits.length > 0) {
      const sphere = wpHits[0].object
      const wp = sphere.userData.trunkWaypoint

      trunkWaypointDragState = {
        trunkId: wp.trunkId,
        index: wp.index,
        startX: wp.x,
        startY: wp.y,
      }
      selectedTrunkWaypointSphere = sphere

      // 高亮拐点球
      sphere.material.color.set(0x22d3ee)

      controls.enabled = false
      isDragging = false

      renderer.domElement.addEventListener('mousemove', onTrunkWaypointDragMove)
      renderer.domElement.addEventListener('mouseup', onTrunkWaypointDragEnd)
      return
    }
  }

  // 检查是否点击了主干光缆管体（添加分支点）- 需要进入分支点创建模式
  if (branchPointCreateMode.value && ctx.value.topoEdgesGroup) {
    const topoEdgeHits = raycaster.intersectObjects(ctx.value.topoEdgesGroup.children.filter(c => c.userData.topoEdge), false)
    if (topoEdgeHits.length > 0) {
      const hit = topoEdgeHits[0]
      const tube = hit.object
      const edgeData = tube.userData.topoEdge
      if (edgeData && edgeData.cableId) {
        // 直接使用射线与管体的交点坐标，而不是地面平面交点
        const worldPos = hit.point
        const x_percent = Math.max(0, Math.min(100, (worldPos.x / plan.real_width_m) * 100))
        const y_percent = Math.max(0, Math.min(100, (worldPos.z / plan.real_depth_m) * 100))
        // 使用新的 topo API 创建分支点
        addBranchPointOnTopoEdge(edgeData.cableId, { x: x_percent, y: y_percent })
        branchPointCreateMode.value = false  // 添加完成后退出模式
      }
      return
    }
  }

  // ========== 原有编辑交互 ==========

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
        // waypoints 可能是字符串或已解析的数组
        let waypoints = []
        if (typeof link.waypoints === 'string') {
          waypoints = JSON.parse(link.waypoints) || []
        } else if (Array.isArray(link.waypoints)) {
          waypoints = link.waypoints
        }

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

// 主干拐点拖动处理
function onTrunkWaypointDragMove(e) {
  if (!trunkWaypointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  trunkWaypointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  trunkWaypointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新主干拐点球位置
  if (selectedTrunkWaypointSphere) {
    const trunkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
    const trunkRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.0015
    const w = percentToWorld(trunkWaypointDragState._lastX, trunkWaypointDragState._lastY, trunkHeight + trunkRadius * 3)
    selectedTrunkWaypointSphere.position.set(w.x, w.y, w.z)
  }
}

// 主干拐点拖动结束
async function onTrunkWaypointDragEnd(e) {
  if (!trunkWaypointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onTrunkWaypointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onTrunkWaypointDragEnd)
  ctx.value.controls.enabled = true

  const { trunkId, index, _lastX, _lastY } = trunkWaypointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 更新主干拐点数据
      const trunk = fiberTrunks.value.find(t => t.id === trunkId)
      if (trunk) {
        // waypoints 可能是字符串或已解析的数组
        let waypoints = []
        if (typeof trunk.waypoints === 'string') {
          waypoints = JSON.parse(trunk.waypoints) || []
        } else if (Array.isArray(trunk.waypoints)) {
          waypoints = trunk.waypoints
        }

        // 更新指定索引的拐点
        if (index < waypoints.length) {
          waypoints[index] = { x: Number(_lastX.toFixed(2)), y: Number(_lastY.toFixed(2)) }
        }

        const waypointsJson = JSON.stringify(waypoints)
        await axios.put(`/api/floor-plans/${currentPlanId.value}/fiber-trunks/${trunkId}`, {
          waypoints: waypointsJson
        })

        // 更新本地数据
        trunk.waypoints = waypointsJson

        // 重新加载 topo 数据并重建渲染
        await loadTopoData()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新主干拐点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复拐点球颜色
  if (selectedTrunkWaypointSphere) {
    selectedTrunkWaypointSphere.material.color.set(0xffffff)
  }

  trunkWaypointDragState = null
  selectedTrunkWaypointSphere = null
  isDragging = false
}

// ========== TopoEdge 拐点球拖拽处理 ==========

let topoEdgeWaypointDragState = null
let selectedTopoEdgeWaypointSphere = null

// TopoEndpoint 拖拽状态
let topoEndpointDragState = null
let selectedTopoEndpointSphere = null

function onTopoEdgeWaypointDragMove(e) {
  if (!topoEdgeWaypointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  topoEdgeWaypointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  topoEdgeWaypointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新拐点球位置
  if (selectedTopoEdgeWaypointSphere) {
    const edgeHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
    const w = percentToWorld(topoEdgeWaypointDragState._lastX, topoEdgeWaypointDragState._lastY, edgeHeight)
    selectedTopoEdgeWaypointSphere.position.set(w.x, w.y, w.z)
  }
}

async function onTopoEdgeWaypointDragEnd(e) {
  if (!topoEdgeWaypointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onTopoEdgeWaypointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onTopoEdgeWaypointDragEnd)
  ctx.value.controls.enabled = true

  const { edgeId, index, _lastX, _lastY } = topoEdgeWaypointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 更新 TopoEdge 拐点数据
      const edge = topoEdges.value.find(e => e.id === edgeId)
      if (edge) {
        let waypoints = []
        if (typeof edge.waypoints === 'string') {
          waypoints = JSON.parse(edge.waypoints) || []
        } else if (Array.isArray(edge.waypoints)) {
          waypoints = [...edge.waypoints]  // 复制数组
        }

        // 更新指定索引的拐点
        if (index < waypoints.length) {
          waypoints[index] = { x: Number(_lastX.toFixed(2)), y: Number(_lastY.toFixed(2)) }
        }

        // 发送数组，不是 JSON 字符串
        await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-edges/${edgeId}`, {
          waypoints: waypoints
        })

        // 更新本地数据
        edge.waypoints = waypoints

        // 重建拓扑边
        buildTopoEdges()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新 TopoEdge 拐点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复拐点球颜色
  if (selectedTopoEdgeWaypointSphere) {
    selectedTopoEdgeWaypointSphere.material.color.set(0xffffff)
  }

  topoEdgeWaypointDragState = null
  selectedTopoEdgeWaypointSphere = null
  isDragging = false
}

// ========== TopoEndpoint（主干起点终点）拖拽处理 ==========

function onTopoEndpointDragMove(e) {
  if (!topoEndpointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  topoEndpointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  topoEndpointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新端点球位置
  if (selectedTopoEndpointSphere) {
    const edgeHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
    const edgeRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001
    const epHeight = edgeHeight + edgeRadius * 2
    const w = percentToWorld(topoEndpointDragState._lastX, topoEndpointDragState._lastY, epHeight)
    selectedTopoEndpointSphere.position.set(w.x, w.y, w.z)
  }
}

async function onTopoEndpointDragEnd(e) {
  if (!topoEndpointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onTopoEndpointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onTopoEndpointDragEnd)
  ctx.value.controls.enabled = true

  const { nodeId, type, _lastX, _lastY } = topoEndpointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 更新 TopoNode 位置
      await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-nodes/${nodeId}`, {
        x_percent: _lastX,
        y_percent: _lastY,
      })

      // 更新本地数据
      const node = topoNodes.value.find(n => n.id === nodeId)
      if (node) {
        node.x_percent = _lastX
        node.y_percent = _lastY
      }

      // 重建拓扑边渲染
      buildTopoEdges()

      ElMessage.success(t('msgSaveSuccess'))
    } catch (err) {
      console.error('更新 TopoEndpoint 位置失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复端点球颜色
  if (selectedTopoEndpointSphere) {
    const isStart = selectedTopoEndpointSphere.userData.topoEndpoint.type === 'start'
    selectedTopoEndpointSphere.material.color.set(isStart ? 0x22c55e : 0xef4444)
  }

  topoEndpointDragState = null
  selectedTopoEndpointSphere = null
  isDragging = false
}

// ========== 主干端点拖动处理（旧系统） ==========
function onTrunkEndpointDragMove(e) {
  if (!trunkEndpointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  trunkEndpointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  trunkEndpointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新端点球位置
  if (selectedTrunkEndpointSphere) {
    const trunkHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002
    const trunkRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.0015
    const w = percentToWorld(trunkEndpointDragState._lastX, trunkEndpointDragState._lastY, trunkHeight + trunkRadius * 2)
    selectedTrunkEndpointSphere.position.set(w.x, w.y, w.z)
  }
}

// 主干端点拖动结束
async function onTrunkEndpointDragEnd(e) {
  if (!trunkEndpointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onTrunkEndpointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onTrunkEndpointDragEnd)
  ctx.value.controls.enabled = true

  const { trunkId, type, _lastX, _lastY } = trunkEndpointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      const trunk = fiberTrunks.value.find(t => t.id === trunkId)
      if (trunk) {
        // 更新起点或终点坐标
        const updateData = {}
        if (type === 'start') {
          updateData.start_x_percent = Number(_lastX.toFixed(2))
          updateData.start_y_percent = Number(_lastY.toFixed(2))

          // 检查是否靠近某个设备（起点可以关联核心交换机）
          const nearbyNode = findNearbyDevice(_lastX, _lastY, 5)  // 5% 范围内
          if (nearbyNode) {
            updateData.start_device_id = nearbyNode.device_id
            ElMessage.success(`${t('connectedToDevice')}: ${nearbyNode.device_name || nearbyNode.name}`)
          }
        } else {
          updateData.end_x_percent = Number(_lastX.toFixed(2))
          updateData.end_y_percent = Number(_lastY.toFixed(2))
        }

        await axios.put(`/api/floor-plans/${currentPlanId.value}/fiber-trunks/${trunkId}`, updateData)

        // 更新本地数据
        if (type === 'start') {
          trunk.start_x_percent = Number(_lastX.toFixed(2))
          trunk.start_y_percent = Number(_lastY.toFixed(2))
          if (updateData.start_device_id) {
            trunk.start_device_id = updateData.start_device_id
          }
        } else {
          trunk.end_x_percent = Number(_lastX.toFixed(2))
          trunk.end_y_percent = Number(_lastY.toFixed(2))
        }

        // 重新加载 topo 数据并重建渲染
        await loadTopoData()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新主干端点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复端点球颜色
  if (selectedTrunkEndpointSphere) {
    const ep = selectedTrunkEndpointSphere.userData.trunkEndpoint
    selectedTrunkEndpointSphere.material.color.set(ep.type === 'start' ? 0x22c55e : 0xef4444)
  }

  trunkEndpointDragState = null
  selectedTrunkEndpointSphere = null
  isDragging = false
}

// 分支点拖动处理
function onBranchPointDragMove(e) {
  if (!branchPointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  branchPointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  branchPointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新分支点球位置
  if (selectedBranchPointSphere) {
    const bpHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.002 + 1
    const w = percentToWorld(branchPointDragState._lastX, branchPointDragState._lastY, bpHeight)
    selectedBranchPointSphere.position.set(w.x, w.y, w.z)
  }
}

// 分支点拖动结束
async function onBranchPointDragEnd(e) {
  if (!branchPointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onBranchPointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onBranchPointDragEnd)
  ctx.value.controls.enabled = true

  const { nodeId, _lastX, _lastY } = branchPointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      // 使用新的 topo API 更新节点位置
      await axios.put(`/api/floor-plans/${currentPlanId.value}/topo-nodes/${nodeId}`, {
        x_percent: Number(_lastX.toFixed(2)),
        y_percent: Number(_lastY.toFixed(2)),
      })

      // 重新加载 topo 数据并重建渲染
      await loadFiberData()

      ElMessage.success(t('msgSaveSuccess'))
    } catch (err) {
      console.error('更新分支点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复分支点球颜色
  if (selectedBranchPointSphere) {
    selectedBranchPointSphere.material.color.set(0xfbbf24)  // 黄色
  }

  branchPointDragState = null
  selectedBranchPointSphere = null
  isDragging = false
}

// 分支光缆拐点拖动处理
function onBranchLinkWaypointDragMove(e) {
  if (!branchLinkWaypointDragState) return
  isDragging = true

  const pos = screenToPercent(e)
  if (!pos) return

  branchLinkWaypointDragState._lastX = Math.max(0, Math.min(100, pos.x_percent))
  branchLinkWaypointDragState._lastY = Math.max(0, Math.min(100, pos.y_percent))

  // 实时更新拐点球位置
  if (selectedBranchLinkWaypointSphere) {
    const branchHeight = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001
    const branchRadius = Math.min(plan.real_width_m, plan.real_depth_m) * 0.001
    const w = percentToWorld(branchLinkWaypointDragState._lastX, branchLinkWaypointDragState._lastY, branchHeight + branchRadius * 3)
    selectedBranchLinkWaypointSphere.position.set(w.x, w.y, w.z)
  }
}

// 分支光缆拐点拖动结束
async function onBranchLinkWaypointDragEnd(e) {
  if (!branchLinkWaypointDragState) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onBranchLinkWaypointDragMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onBranchLinkWaypointDragEnd)
  ctx.value.controls.enabled = true

  const { linkId, index, _lastX, _lastY } = branchLinkWaypointDragState

  if (isDragging && _lastX != null && _lastY != null) {
    try {
      const link = fiberBranchLinks.value.find(l => l.id === linkId)
      if (link) {
        // 解析拐点
        let waypoints = []
        if (typeof link.waypoints === 'string') {
          waypoints = JSON.parse(link.waypoints) || []
        } else if (Array.isArray(link.waypoints)) {
          waypoints = link.waypoints
        }

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
        // 重新加载 topo 数据并重建渲染
        await loadTopoData()

        ElMessage.success(t('msgSaveSuccess'))
      }
    } catch (err) {
      console.error('更新分支光缆拐点失败:', err)
      ElMessage.error(t('msgUpdateFailed'))
    }
  }

  // 恢复拐点球颜色
  if (selectedBranchLinkWaypointSphere) {
    selectedBranchLinkWaypointSphere.material.color.set(0xffffff)
  }

  branchLinkWaypointDragState = null
  selectedBranchLinkWaypointSphere = null
  isDragging = false
}

// 查找附近的设备节点
function findNearbyDevice(x_percent, y_percent, threshold) {
  for (const node of nodes.value) {
    const dx = Math.abs(node.x_percent - x_percent)
    const dy = Math.abs(node.y_percent - y_percent)
    if (dx < threshold && dy < threshold) {
      // 找到对应的设备
      const device = devices.value.find(d => d.id === node.device_id)
      return {
        device_id: node.device_id,
        device_name: device ? device.name : null,
        name: device ? device.name : `设备 ${node.device_id}`
      }
    }
  }
  return null
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
        node.x_percent = Number(_lastX.toFixed(2))
        node.y_percent = Number(_lastY.toFixed(2))
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

// ========== PNetLab 连线态鼠标处理器 ==========

function onWiringMouseMove(e) {
  if (!wiringState.value) return

  const { camera, renderer } = ctx.value
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  // 计算鼠标在世界坐标中的位置（投射到平面）
  const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -Math.min(plan.real_width_m, plan.real_depth_m) * 0.003)
  const mouseWorld = new THREE.Vector3()
  raycaster.ray.intersectPlane(plane, mouseWorld)

  updateRubberBandLine(mouseWorld)
}

function onWiringMouseUp(e) {
  if (!wiringState.value) return

  ctx.value.renderer.domElement.removeEventListener('mousemove', onWiringMouseMove)
  ctx.value.renderer.domElement.removeEventListener('mouseup', onWiringMouseUp)
  ctx.value.controls.enabled = true

  const { camera, renderer } = ctx.value
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1

  raycaster.setFromCamera(pointer, camera)

  // 检查是否点击了另一个端口锚点
  if (ctx.value.portAnchors) {
    const anchorHits = raycaster.intersectObjects(ctx.value.portAnchors.children, false)
    if (anchorHits.length > 0) {
      const sphere = anchorHits[0].object
      if (sphere.userData.portAnchor && sphere.userData.portAnchor.deviceId !== wiringState.value.fromDeviceId) {
        finishWiring(sphere.userData.portAnchor)
        return
      }
    }
  }

  // 没有点击到目标锚点，取消连线
  cancelWiring()
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
      links.value = []

      const topoRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/topology`)
      if (topoRes.data.nodes) nodes.value = topoRes.data.nodes

      // 加载图模型拓扑数据（Gen3）
      try {
        const topoNodesRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/topo-nodes`)
        topoNodes.value = topoNodesRes.data.items || []
        const topoEdgesRes = await axios.get(`/api/floor-plans/${currentPlan.value.id}/topo-edges`)
        topoEdges.value = topoEdgesRes.data.items || []
      } catch (e) {
        console.warn('加载 topo-nodes/edges 失败:', e)
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
    rebuildScene()
  }
})

// 监听编辑模式变化，重建拓扑渲染（显示/隐藏控制点）
watch(isEditMode, () => {
  if (ctx.value.scene) {
    buildTopoEdges()
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

  // 数据链路
  if (ctx.value.linkLines) {
    ctx.value.linkLines.visible = showDataLinks.value && showLinks.value
  }
  if (ctx.value.dataLinkPaths) {
    ctx.value.dataLinkPaths.visible = showDataLinks.value
  }
})

// 监听图层控制 - 只控制 links 组（直接链路线）
// 注意：当 showDataLinks 为 false 时，links 组已被 dispose，此 watch 无效
watch(showLinks, (val) => {
  if (ctx.value.linkLines && ctx.value.linkLines.parent) {
    // 只有当 group 还在 scene 中时才设置 visible
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

  // 使用新 topo 数据渲染光纤拓扑
  buildTopoEdges()
  buildDataLinkPaths()

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
  width: 260px;
  height: 100%;
  padding: 12px;
  background: rgba(17, 22, 31, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backpoint-filter: blur(12px);
  color: #e5e7eb;
  overflow-y: auto;
  border-left: 1px solid rgba(34, 211, 238, 0.2);
  transition: transform 0.3s ease, opacity 0.3s ease;
  z-index: 10;
}

/* 明亮模式适配 */
.side-panel:not(.dark) {
  background: rgba(255, 255, 255, 0.85);
  color: #374151;
  border-left: 1px solid rgba(0, 120, 212, 0.2);
}

.side-panel:not(.dark) .panel-header h3 {
  color: #0078d4;
}

.side-panel:not(.dark) .kpi b.online {
  color: #10b981;
}

.side-panel:not(.dark) .kpi b.offline {
  color: #ef4444;
}

.side-panel:not(.dark) .link-item,
.side-panel:not(.dark) .plan-item {
  background: rgba(0, 0, 0, 0.05);
  color: #374151;
}

.side-panel:not(.dark) .plan-item.active {
  background: rgba(0, 120, 212, 0.1);
  border-color: rgba(0, 120, 212, 0.3);
}

.side-panel:not(.dark) .link-info {
  color: #374151;
}

.side-panel:not(.dark) .plan-name {
  color: #374151;
}

.side-panel:not(.dark) .panel-action-btn {
  background: linear-gradient(135deg, rgba(0, 120, 212, 0.08), rgba(0, 120, 212, 0.02));
  border-color: rgba(0, 120, 212, 0.25);
  color: #0078d4;
}

.side-panel:not(.dark) .panel-action-btn:hover {
  background: linear-gradient(135deg, rgba(0, 120, 212, 0.15), rgba(0, 120, 212, 0.08));
  border-color: rgba(0, 120, 212, 0.4);
}

/* 明亮模式：KPI 区域适配 */
.side-panel:not(.dark) .kpi {
  background: rgba(0, 0, 0, 0.06);
}

.side-panel:not(.dark) .kpi span {
  color: #374151;
}

.side-panel:not(.dark) .kpi b {
  color: #374151;
}

.side-panel:not(.dark) .kpi b.online {
  color: #10b981;
}

.side-panel:not(.dark) .kpi b.offline {
  color: #ef4444;
}

/* 明亮模式：selected-box 适配 */
.side-panel:not(.dark) .selected-box {
  background: rgba(0, 0, 0, 0.04);
  border-color: rgba(0, 0, 0, 0.1);
}

.side-panel:not(.dark) .selected-box h4 {
  color: #1f2937;
}

.side-panel:not(.dark) .selected-box p {
  color: #4b5563;
}

/* 明亮模式：no-data 适配 */
.side-panel:not(.dark) .no-data {
  color: #6b7280;
}

/* 明亮模式：waypoint-hint 和 waypoint-item 适配 */
.side-panel:not(.dark) .waypoint-hint {
  color: #6b7280;
}

.side-panel:not(.dark) .waypoint-item {
  background: rgba(0, 0, 0, 0.04);
}

.side-panel:not(.dark) .waypoint-index {
  background: rgba(0, 120, 212, 0.1);
  color: #0078d4;
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

/* 画布右下角工具按钮（避开侧边栏） */
.canvas-tools {
  position: absolute;
  right: 276px;
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

/* 光纤主干区域 */
.fiber-section {
  margin-top: 10px;
}

.section-header {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 6px;
  margin-top: 10px;
}

/* 操作按钮区域：上下堆叠，200px面板并排太窄 */
.fiber-action-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 8px;
}

.fiber-action-bar .panel-action-btn {
  width: 100%;
  margin-bottom: 0;
}

/* 树形光纤列表 */
.fiber-tree {
  max-height: 400px;
  overflow-y: auto;
}

.fiber-tree-node {
  margin-bottom: 2px;
}

.tree-node-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px 8px;
  background: rgba(26, 34, 48, 0.5);
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.15s;
}

/* 第一行：展开图标 + 名称 */
.tree-node-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tree-node-header:hover {
  background: rgba(36, 48, 64, 0.6);
}

.tree-expand-icon {
  font-size: 12px;
  color: #6b7280;
  transition: transform 0.15s;
}

.trunk-node > .tree-node-header .tree-expand-icon {
  color: #a855f7;
}

.branch-point-node > .tree-node-header .tree-expand-icon {
  color: #fbbf24;
}

.trunk-name, .bp-name {
  font-size: 11px;
  color: #e5e7eb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.link-name {
  font-size: 11px;
  color: #06b6d4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.tree-node-actions {
  display: flex;
  gap: 4px;
  padding-left: 18px;
}

.tree-node-children {
  padding-left: 16px;
  border-left: 1px solid rgba(34, 211, 238, 0.12);
  margin-left: 10px;
}

.branch-link-node > .tree-node-header {
  background: rgba(6, 182, 212, 0.08);
  padding: 4px 6px;
}

.tree-empty-hint {
  color: #6b7280;
  font-size: 11px;
  padding: 6px 8px;
  text-align: center;
}

/* 明亮模式：树形光纤列表 */
.side-panel:not(.dark) .tree-node-header {
  background: rgba(0, 0, 0, 0.04);
}

.side-panel:not(.dark) .tree-node-header:hover {
  background: rgba(0, 0, 0, 0.08);
}

.side-panel:not(.dark) .trunk-node > .tree-node-header .tree-expand-icon {
  color: #7c3aed;
}

.side-panel:not(.dark) .branch-point-node > .tree-node-header .tree-expand-icon {
  color: #d97706;
}

.side-panel:not(.dark) .trunk-name,
.side-panel:not(.dark) .bp-name {
  color: #374151;
}

.side-panel:not(.dark) .link-name {
  color: #0891b2;
}

.side-panel:not(.dark) .tree-node-children {
  border-left: 1px solid rgba(0, 0, 0, 0.08);
}

.side-panel:not(.dark) .branch-link-node > .tree-node-header {
  background: rgba(0, 120, 212, 0.06);
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

/* ===== 明亮模式：el-tabs 样式覆盖 ===== */
.side-panel:not(.dark) :deep(.el-tabs--border-card) {
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.side-panel:not(.dark) :deep(.el-tabs__header) {
  background: rgba(0, 0, 0, 0.03);
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}

.side-panel:not(.dark) :deep(.el-tabs__item) {
  color: #6b7280 !important;
}

.side-panel:not(.dark) :deep(.el-tabs__item:hover) {
  color: #0078d4 !important;
}

.side-panel:not(.dark) :deep(.el-tabs__item.is-active) {
  color: #0078d4 !important;
}

.side-panel:not(.dark) :deep(.el-tabs__item.is-active)::after {
  background: #0078d4;
}

/* ===== 明亮模式：el-select 样式覆盖 ===== */
.side-panel:not(.dark) :deep(.el-select__wrapper),
.side-panel:not(.dark) :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.8) !important;
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.15) inset !important;
}

.side-panel:not(.dark) :deep(.el-select__wrapper:hover),
.side-panel:not(.dark) :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(0, 120, 212, 0.4) inset !important;
}

.side-panel:not(.dark) :deep(.el-select__wrapper.is-focused),
.side-panel:not(.dark) :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #0078d4 inset !important;
}

.side-panel:not(.dark) :deep(.el-select__placeholder),
.side-panel:not(.dark) :deep(.el-input__inner) {
  color: #374151 !important;
}

.side-panel:not(.dark) :deep(.el-select__placeholder.is-transparent) {
  color: #9ca3af !important;
}

.side-panel:not(.dark) :deep(.el-select__caret),
.side-panel:not(.dark) :deep(.el-input__icon) {
  color: #6b7280 !important;
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