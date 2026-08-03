<!-- Monitor3D 右侧操作面板（item 946 切片 8）
从 frontend/src/views/Monitor3D.vue 拆分（模板 80-491），行为与原实现完全一致。
展示组件：数据经 props、动作经 emit 转发给父（父持全部场景状态）；sidebarTab/formatEventTime 为内部；
useDeviceMappings 组件内调用供模板用；filterType 等 8 个共享可写状态用 defineModel 双向绑定父 ref。 -->
<template>
  <aside class="side-panel" :class="{ dark }">
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

    <div class="command-panel">
      <div class="command-head">
        <h4>{{ t('monitorCommandPanel') }}</h4>
        <button class="panel-mini-btn" @click="emit('refresh')">{{ t('monitorFaultRefresh') }}</button>
      </div>
      <div class="command-grid">
        <div class="command-card danger">
          <span>P1</span>
          <b>{{ commandSummary.p1_count || 0 }}</b>
        </div>
        <div class="command-card warning">
          <span>P2</span>
          <b>{{ commandSummary.p2_count || 0 }}</b>
        </div>
        <div class="command-card">
          <span>{{ t('monitorUnacknowledged') }}</span>
          <b>{{ commandSummary.unacknowledged || 0 }}</b>
        </div>
        <div class="command-card">
          <span>{{ t('monitorInProgress') }}</span>
          <b>{{ commandSummary.in_progress || 0 }}</b>
        </div>
      </div>
      <div class="command-substats">
        <span>{{ t('monitorTransferMaintenance') }} {{ commandSummary.transferred || 0 }}</span>
        <span>{{ t('monitorImpactedDevices') }} {{ commandSummary.impacted_devices || 0 }}</span>
      </div>
      <div class="command-events" v-if="commandSummary.recent_events?.length">
        <button
          v-for="event in commandSummary.recent_events"
          :key="event.id"
          class="command-event"
          @click="emit('focus-incident', event)"
        >
          <span class="event-main">
            <b :class="`sev-${event.severity || 'minor'}`">{{ event.severity || '-' }}</b>
            {{ event.device_name || event.fault_no }}
          </span>
          <span class="event-sub">
            {{ event.source_event || event.incident_type || event.status }}<span v-if="event.if_name"> · {{ event.if_name }}</span>
          </span>
        </button>
      </div>
      <div class="command-empty" v-else>{{ t('monitorNoActiveFaults') }}</div>

      <div class="root-cause-block" v-if="commandSummary.root_cause_candidates?.length">
        <div class="root-cause-title">{{ t('monitorRootCauseTop3') }}</div>
        <button
          v-for="candidate in commandSummary.root_cause_candidates"
          :key="candidate.candidate"
          class="root-cause-item"
          @click="emit('focus-incident', candidate)"
        >
          <span class="root-main">
            <b :class="`sev-${candidate.severity || 'minor'}`">{{ Math.round((candidate.confidence || 0) * 100) }}%</b>
            {{ candidate.candidate }}
          </span>
          <span class="root-sub">
            {{ t('monitorImpactedCount', { count: candidate.impacted_devices || 0 }) }} · {{ (candidate.evidence || []).slice(0, 2).join(' / ') }}
          </span>
        </button>
      </div>

      <div class="impact-scope" v-if="commandSummary.impact_scope && commandSummary.impact_scope.level !== 'none'">
        <div class="impact-head">
          <span>{{ t('monitorImpactScope') }}</span>
          <b :class="`sev-${commandSummary.impact_scope.level || 'minor'}`">{{ commandSummary.impact_scope.level }}</b>
        </div>
        <div class="impact-summary">{{ commandSummary.impact_scope.summary }}</div>
        <div class="impact-devices" v-if="commandSummary.impact_scope.impacted_devices?.length">
          <button
            v-for="device in commandSummary.impact_scope.impacted_devices.slice(0, 5)"
            :key="device.device_id"
            class="impact-device"
            @click="emit('focus-incident', device)"
          >
            <span>{{ device.device_name || device.fault_no }}</span>
            <b :class="`sev-${device.severity || 'minor'}`">{{ device.severity || '-' }}</b>
          </button>
        </div>
        <div class="shared-paths" v-if="commandSummary.impact_scope.shared_path_edges?.length">
          <div
            v-for="edge in commandSummary.impact_scope.shared_path_edges.slice(0, 3)"
            :key="edge.edge_id"
            class="shared-path-item"
          >
            <span>{{ edge.cable_name || ('Edge-' + edge.edge_id) }}</span>
            <b>{{ t('monitorAffectedCount', { count: edge.affected_devices }) }}</b>
          </div>
        </div>
      </div>

      <div class="hot-links" v-if="commandSummary.hot_links?.length">
        <div class="hot-links-title">{{ t('monitorHotLinksTitle') }}</div>
        <button
          v-for="link in commandSummary.hot_links"
          :key="link.fault_id"
          class="hot-link-item"
          @click="emit('focus-incident', link)"
        >
          <span class="hot-link-main">
            <b :class="`sev-${link.severity || 'minor'}`">{{ link.severity || '-' }}</b>
            {{ link.device_name || link.fault_no }}<span v-if="link.if_name"> · {{ link.if_name }}</span>
          </span>
          <span class="hot-link-sub">
            {{ link.incident_type || link.source_event }} · {{ t('monitorEventCount', { count: link.event_count || 1 }) }}<span v-if="link.peer_if_name"> · {{ t('monitorPeerPrefix') }} {{ link.peer_if_name }}</span>
          </span>
        </button>
      </div>

      <div class="timeline-head">
        <span>{{ t('monitorEventStream') }}</span>
        <div class="timeline-window">
          <button :class="{ active: eventWindow === '10m' }" @click="emit('set-event-window', '10m')">{{ t('monitor10min') }}</button>
          <button :class="{ active: eventWindow === '1h' }" @click="emit('set-event-window', '1h')">{{ t('monitor1hour') }}</button>
          <button :class="{ active: eventWindow === '24h' }" @click="emit('set-event-window', '24h')">{{ t('monitor24hours') }}</button>
        </div>
      </div>
      <div class="timeline-list" v-if="monitorEvents.length">
        <button
          v-for="event in monitorEvents"
          :key="event.id"
          class="timeline-item"
          @click="emit('focus-incident', event)"
        >
          <span class="timeline-dot" :class="`sev-bg-${event.severity || 'minor'}`"></span>
          <span class="timeline-body">
            <span class="timeline-title">{{ event.title }} · {{ event.device_name || event.fault_no }}</span>
            <span class="timeline-meta">{{ formatEventTime(event.occurred_at) }} · {{ event.event_type }}<span v-if="event.if_name"> · {{ event.if_name }}</span></span>
          </span>
        </button>
      </div>
      <div class="command-empty" v-else>{{ t('monitorNoEvents') }}</div>
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
            <button class="panel-action-btn" @click="emit('start-add-trunk')">
              <el-icon><Plus /></el-icon>
              <span>{{ t('addFiberTrunk') }}</span>
            </button>
            <button class="panel-action-btn" @click="emit('start-add-branch-point')" v-if="displayCables.length > 0">
              <el-icon><Position /></el-icon>
              <span>{{ t('addBranchPoint') }}</span>
            </button>
          </div>

          <!-- 主干树形列表 -->
          <div class="fiber-tree" v-if="displayCables.length > 0">
            <div v-for="cable in displayCables" :key="cable.cable_id" class="fiber-tree-node trunk-node">
              <!-- 主干节点 -->
              <div class="tree-node-header" @click="emit('toggle-trunk-expand', cable.cable_id)">
                <div class="tree-node-row">
                  <el-icon class="tree-expand-icon">
                    <ArrowDown v-if="expandedTrunks[cable.cable_id]" />
                    <ArrowRight v-else />
                  </el-icon>
                  <span class="trunk-name" :title="cable.cable_name || cable.cable_no">{{ cable.cable_name || cable.cable_no }}</span>
                </div>
                <div class="tree-node-actions">
                  <button class="icon-btn" @click.stop="emit('rename-cable', cable)" :title="t('actionRename')">
                    <el-icon><Edit /></el-icon>
                  </button>
                  <button class="icon-btn" @click.stop="emit('edit-cable-waypoints', cable)" :title="t('editWaypoints')">
                    <el-icon><Connection /></el-icon>
                  </button>
                  <button class="icon-btn danger" @click.stop="emit('delete-cable', cable.cable_id)" :title="t('actionDelete')">
                    <el-icon><Delete /></el-icon>
                  </button>
                </div>
              </div>
              <!-- 主干展开内容 -->
              <div class="tree-node-children" v-if="expandedTrunks[cable.cable_id]">
                <div v-for="bp in getBranchPointsForCable(cable.cable_id)" :key="bp.id" class="fiber-tree-node branch-point-node">
                  <div class="tree-node-header" @click="emit('toggle-branch-point-expand', bp.id)">
                    <div class="tree-node-row">
                      <el-icon class="tree-expand-icon">
                        <ArrowDown v-if="expandedBranchPoints[bp.id]" />
                        <ArrowRight v-else />
                      </el-icon>
                      <span class="bp-name" :title="bp.label || `BP-${bp.id}`">{{ bp.label || `BP-${bp.id}` }}</span>
                    </div>
                    <div class="tree-node-actions">
                      <button class="icon-btn" @click.stop="emit('rename-branch-point', bp)" :title="t('actionRename')">
                        <el-icon><Edit /></el-icon>
                      </button>
                      <button class="icon-btn" @click.stop="emit('connect-from-topo-branch', bp)" :title="t('connectDevice')">
                        <el-icon><Position /></el-icon>
                      </button>
                      <button class="icon-btn danger" @click.stop="emit('delete-topo-branch-point', bp.id)" :title="t('actionDelete')">
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
                          <button class="icon-btn" @click.stop="emit('rename-branch-link', edge)" :title="t('actionRename')">
                            <el-icon><Edit /></el-icon>
                          </button>
                          <button class="icon-btn" @click.stop="emit('open-topo-edge-waypoint', edge)" :title="t('editWaypoints')">
                            <el-icon><Connection /></el-icon>
                          </button>
                          <button class="icon-btn danger" @click.stop="emit('delete-topo-edge', edge.id)" :title="t('actionDelete')">
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
          <p><strong>{{ t('deviceType') }}:</strong> {{ getDeviceTypeLabelI18n(selectedDevice.device_type) }}</p>
          <p><strong>{{ t('deviceStatus') }}:</strong>
            <el-tag :type="isDeviceOnline(selectedDevice) ? 'success' : (isDeviceOffline(selectedDevice) ? 'danger' : 'info')" size="small">
              {{ getStatusLabelI18n(deviceStatus(selectedDevice)) }}
            </el-tag>
          </p>
          <div class="incident-panel" v-if="selectedActiveFault">
            <div class="incident-title">
              <span>{{ selectedActiveFault.fault_no }}</span>
              <el-tag :type="faultSeverityTag(selectedActiveFault.severity)" size="small">
                {{ selectedActiveFault.severity }}
              </el-tag>
            </div>
            <div class="incident-meta">
              {{ selectedActiveFault.status_label || selectedActiveFault.status }} · {{ selectedActiveFault.source_event || selectedActiveFault.incident_type || '-' }}
            </div>
            <div class="incident-meta" v-if="selectedActiveFault.if_name">
              {{ selectedActiveFault.if_name }}<span v-if="selectedActiveFault.event_count"> · {{ t('monitorEventCount', { count: selectedActiveFault.event_count }) }}</span>
            </div>
            <div class="incident-ai" v-if="selectedActiveFault.ai_root_cause">
              <span class="incident-ai-label">{{ t('faultAiProbableCause') }}</span>
              <span class="incident-ai-text">{{ selectedActiveFault.ai_root_cause }}</span>
            </div>
            <div class="incident-actions">
              <template v-if="selectedFaultNeedsReview">
                <el-button type="primary" size="small" :loading="faultActionLoading" @click="emit('review-fault', false)">{{ t('monitorFaultConfirm') }}</el-button>
                <el-button type="warning" size="small" :loading="faultActionLoading" @click="emit('review-fault', true)">{{ t('monitorFaultFalseAlarm') }}</el-button>
              </template>
              <el-button v-else type="primary" size="small" @click="emit('open-fault-detail')">{{ t('monitorFaultDetail') }}</el-button>
              <el-button type="danger" size="small" :loading="faultActionLoading" @click="emit('transfer-fault')">{{ t('monitorTransferMaintenance') }}</el-button>
              <el-button size="small" :loading="aiDiagnosing" @click="emit('ai-prediagnose')">{{ t('faultAiRunPrediagnose') }}</el-button>
            </div>
          </div>
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
              @change="emit('update-device-scale', $event)"
            />
            <span class="scale-value">{{ deviceScale.toFixed(1) }}x</span>
          </div>
          <div class="selected-actions">
            <el-button type="primary" size="small" @click="emit('go-to-device-detail', selectedDevice.id)">
              {{ t('viewDetail') }}
            </el-button>
            <el-button type="danger" size="small" v-if="selectedNode" @click="emit('delete-node', selectedNode.id)">
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
          <div class="tilt-control">
            <span>{{ t('floorPlanTilt') }}:</span>
            <el-slider v-model="floorTiltAngle" :min="0" :max="90" :step="5" :show-tooltip="true" size="small" />
            <span class="tilt-value">{{ floorTiltAngle }}°</span>
          </div>
        </div>

        <!-- 告警列表 -->
        <div class="alert-section">
          <div class="alert-header">
            <h4>{{ t('alertList') }}<span v-if="offlineDevices.length" class="alert-badge">{{ offlineDevices.length }}</span></h4>
            <el-checkbox v-model="autoFocusOffline" size="small">{{ t('autoFocusOffline') }}</el-checkbox>
          </div>
          <div class="alert-list">
            <div
              v-for="alert in offlineDevices"
              :key="alert.id"
              class="alert-item"
              @click="emit('focus-device', alert)"
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
        <button class="panel-action-btn" @click="emit('upload')">
          <el-icon><Upload /></el-icon>
          <span>{{ t('uploadFloorPlan') }}</span>
        </button>
        <div class="plan-list">
          <div v-for="plan in floorPlans" :key="plan.id" class="plan-item" :class="{ active: plan.id === currentPlanId }">
            <el-icon class="plan-icon"><Picture /></el-icon>
            <span class="plan-name">{{ plan.name }}</span>
            <span v-if="plan.id === currentPlanId" class="plan-badge">{{ t('statusLive') }}</span>
            <div class="plan-actions">
              <button v-if="plan.id !== currentPlanId" class="icon-btn" :title="t('actionSwitchPlan')" @click="emit('switch-plan', plan.id)">
                <el-icon><Switch /></el-icon>
              </button>
              <button class="icon-btn danger" :title="t('actionDeletePlan')" @click="emit('delete-plan', plan.id)">
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
               @dragstart="emit('palette-drag-start', $event, item.type)">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ t(item.labelKey) }}</span>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import { Plus, Position, Edit, Connection, Delete, Pointer, Warning, Upload, Picture, Switch, ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { useDeviceMappings } from '@/composables/useDeviceMappings'

defineProps({
  dark: { type: Boolean, default: false },
  stats: { type: Object, default: () => ({}) },
  commandSummary: { type: Object, default: () => ({ recent_events: [] }) },
  monitorEvents: { type: Array, default: () => [] },
  eventWindow: { type: String, default: '1h' },
  isEditMode: { type: Boolean, default: false },
  displayCables: { type: Array, default: () => [] },
  expandedTrunks: { type: Object, default: () => ({}) },
  expandedBranchPoints: { type: Object, default: () => ({}) },
  getBranchPointsForCable: { type: Function, required: true },
  getBranchLinksForTopoNode: { type: Function, required: true },
  selectedDevice: { type: Object, default: null },
  selectedActiveFault: { type: Object, default: null },
  selectedFaultNeedsReview: { type: Boolean, default: false },
  faultActionLoading: { type: Boolean, default: false },
  aiDiagnosing: { type: Boolean, default: false },
  selectedNode: { type: Object, default: null },
  offlineDevices: { type: Array, default: () => [] },
  floorPlans: { type: Array, default: () => [] },
  currentPlanId: { type: [String, Number], default: null },
})

const emit = defineEmits([
  'refresh',
  'focus-incident',
  'set-event-window',
  'start-add-trunk',
  'start-add-branch-point',
  'toggle-trunk-expand',
  'rename-cable',
  'edit-cable-waypoints',
  'delete-cable',
  'toggle-branch-point-expand',
  'rename-branch-point',
  'connect-from-topo-branch',
  'delete-topo-branch-point',
  'rename-branch-link',
  'open-topo-edge-waypoint',
  'delete-topo-edge',
  'review-fault',
  'open-fault-detail',
  'transfer-fault',
  'ai-prediagnose',
  'update-device-scale',
  'go-to-device-detail',
  'delete-node',
  'switch-plan',
  'delete-plan',
  'upload',
  'focus-device',
  'palette-drag-start',
])

// 共享可写状态（双向绑定父 ref，默认值与父原 ref 初始值一致）
const filterType = defineModel('filterType', { default: '' })
const filterStatus = defineModel('filterStatus', { default: '' })
const deviceScale = defineModel('deviceScale', { default: 1 })
const showPhysicalTopology = defineModel('showPhysicalTopology', { default: true })
const showDataLinks = defineModel('showDataLinks', { default: true })
const showLabels = defineModel('showLabels', { default: true })
const floorTiltAngle = defineModel('floorTiltAngle', { default: 0 })
const autoFocusOffline = defineModel('autoFocusOffline', { default: true })

const { t } = useI18n()
const { deviceTemplates, getDeviceTypeLabelI18n, getStatusLabelI18n, deviceStatus, isDeviceOnline, isDeviceOffline, faultSeverityTag } = useDeviceMappings()

const sidebarTab = ref('topology')

function formatEventTime(value) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
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

.side-panel:not(.dark) .plan-item {
  background: rgba(0, 0, 0, 0.05);
  color: #374151;
}

.side-panel:not(.dark) .plan-item.active {
  background: rgba(0, 120, 212, 0.1);
  border-color: rgba(0, 120, 212, 0.3);
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

.panel-header h3 {
  margin: 0;
  font-size: 14px;
  color: #22d3ee;
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

.command-panel {
  margin: 10px 0;
  padding: 10px;
  border: 1px solid rgba(34, 211, 238, 0.18);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.46);
}

.command-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.command-head h4 {
  margin: 0;
  color: #a5f3fc;
  font-size: 12px;
}

.panel-mini-btn {
  border: 1px solid rgba(34, 211, 238, 0.28);
  border-radius: 4px;
  background: rgba(8, 145, 178, 0.14);
  color: #67e8f9;
  cursor: pointer;
  font-size: 10px;
  line-height: 20px;
  padding: 0 8px;
}

.command-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.command-card {
  min-width: 0;
  padding: 6px 4px;
  border-radius: 5px;
  background: rgba(30, 41, 59, 0.7);
  text-align: center;
}

.command-card span {
  display: block;
  color: #94a3b8;
  font-size: 9px;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.command-card b {
  color: #e2e8f0;
  font-size: 16px;
  line-height: 1.4;
}

.command-card.danger b {
  color: #fb7185;
}

.command-card.warning b {
  color: #fbbf24;
}

.command-substats {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  color: #94a3b8;
  font-size: 10px;
}

.command-events {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 8px;
}

.command-event {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 5px;
  background: rgba(15, 23, 42, 0.58);
  cursor: pointer;
  padding: 6px;
  text-align: left;
}

.command-event:hover {
  border-color: rgba(34, 211, 238, 0.45);
  background: rgba(8, 145, 178, 0.14);
}

.event-main,
.event-sub {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-main {
  color: #e2e8f0;
  font-size: 11px;
}

.event-main b {
  margin-right: 5px;
  text-transform: uppercase;
}

.event-sub,
.command-empty {
  color: #94a3b8;
  font-size: 10px;
}

.command-empty {
  margin-top: 8px;
}

.root-cause-block {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(34, 211, 238, 0.14);
}

.root-cause-title {
  color: #a5f3fc;
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
}

.root-cause-item {
  display: block;
  width: 100%;
  border: 1px solid rgba(34, 211, 238, 0.18);
  border-radius: 5px;
  background: rgba(8, 145, 178, 0.1);
  cursor: pointer;
  margin-top: 5px;
  padding: 6px;
  text-align: left;
}

.root-cause-item:hover {
  border-color: rgba(34, 211, 238, 0.48);
  background: rgba(8, 145, 178, 0.18);
}

.root-main,
.root-sub {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.root-main {
  color: #e2e8f0;
  font-size: 11px;
}

.root-main b {
  margin-right: 6px;
}

.root-sub {
  margin-top: 3px;
  color: #94a3b8;
  font-size: 10px;
}

.impact-scope {
  margin-top: 10px;
  padding: 8px;
  border: 1px solid rgba(248, 113, 113, 0.18);
  border-radius: 6px;
  background: rgba(127, 29, 29, 0.1);
}

.impact-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #fecaca;
  font-size: 11px;
  font-weight: 700;
}

.impact-head b {
  text-transform: uppercase;
}

.impact-summary {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 4px;
  color: #fca5a5;
  font-size: 10px;
}

.impact-devices {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 7px;
}

.impact-device {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  border: 0;
  border-radius: 4px;
  background: rgba(15, 23, 42, 0.42);
  color: #e2e8f0;
  cursor: pointer;
  font-size: 10px;
  padding: 5px 6px;
  text-align: left;
}

.impact-device:hover {
  background: rgba(8, 145, 178, 0.16);
}

.impact-device span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.impact-device b {
  flex: none;
  text-transform: uppercase;
}

.shared-paths {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 7px;
  padding-top: 6px;
  border-top: 1px solid rgba(251, 191, 36, 0.16);
}

.shared-path-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #fde68a;
  font-size: 10px;
}

.shared-path-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shared-path-item b {
  flex: none;
  color: #fbbf24;
}

.hot-links {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(251, 191, 36, 0.16);
}

.hot-links-title {
  color: #fde68a;
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
}

.hot-link-item {
  display: block;
  width: 100%;
  border: 1px solid rgba(251, 191, 36, 0.18);
  border-radius: 5px;
  background: rgba(120, 53, 15, 0.12);
  cursor: pointer;
  margin-top: 5px;
  padding: 6px;
  text-align: left;
}

.hot-link-item:hover {
  border-color: rgba(251, 191, 36, 0.48);
  background: rgba(120, 53, 15, 0.2);
}

.hot-link-main,
.hot-link-sub {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hot-link-main {
  color: #e2e8f0;
  font-size: 11px;
}

.hot-link-main b {
  margin-right: 6px;
  text-transform: uppercase;
}

.hot-link-sub {
  margin-top: 3px;
  color: #fbbf24;
  font-size: 10px;
}

.timeline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 10px;
  color: #a5f3fc;
  font-size: 11px;
  font-weight: 600;
}

.timeline-window {
  display: flex;
  gap: 4px;
}

.timeline-window button {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 4px;
  background: rgba(15, 23, 42, 0.58);
  color: #94a3b8;
  cursor: pointer;
  font-size: 10px;
  line-height: 18px;
  padding: 0 5px;
}

.timeline-window button.active {
  border-color: rgba(34, 211, 238, 0.5);
  background: rgba(8, 145, 178, 0.22);
  color: #67e8f9;
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-top: 8px;
  max-height: 168px;
  overflow: auto;
}

.timeline-item {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr);
  gap: 7px;
  width: 100%;
  border: 0;
  border-radius: 5px;
  background: rgba(15, 23, 42, 0.34);
  cursor: pointer;
  padding: 6px;
  text-align: left;
}

.timeline-item:hover {
  background: rgba(8, 145, 178, 0.14);
}

.timeline-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-top: 4px;
}

.timeline-body,
.timeline-title,
.timeline-meta {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-title {
  color: #e2e8f0;
  font-size: 11px;
}

.timeline-meta {
  margin-top: 2px;
  color: #94a3b8;
  font-size: 10px;
}

.sev-critical { color: #fb7185; }
.sev-major { color: #fbbf24; }
.sev-warning { color: #fde68a; }
.sev-minor { color: #94a3b8; }
.sev-bg-critical { background: #fb7185; }
.sev-bg-major { background: #fbbf24; }
.sev-bg-warning { background: #fde68a; }
.sev-bg-minor { background: #94a3b8; }

.incident-panel {
  margin-top: 8px;
  padding: 8px;
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 6px;
  background: rgba(127, 29, 29, 0.16);
}

.incident-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #fecaca;
  font-size: 11px;
  font-weight: 600;
}

.incident-meta {
  margin-top: 4px;
  color: #fca5a5;

.hud-incident {
  margin-top: 8px;
  padding-top: 7px;
  border-top: 1px solid rgba(248, 113, 113, 0.28);
}

.hud-incident-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: #fecaca;
  font-size: 11px;
  font-weight: 700;
}

.hud-incident-head b {
  text-transform: uppercase;
}

.hud-incident-row {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 3px;
  color: #fca5a5;
  font-size: 10px;
}
  font-size: 10px;
  line-height: 1.35;
}

.incident-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.incident-ai {
  margin-top: 6px;
  padding: 6px 8px;
  border-radius: 6px;
  background: rgba(99, 102, 241, 0.14);
  border: 1px solid rgba(99, 102, 241, 0.32);
}

.incident-ai-label {
  display: block;
  margin-bottom: 2px;
  color: #c7d2fe;
  font-size: 10px;
  font-weight: 700;
}

.incident-ai-text {
  color: #e0e7ff;
  font-size: 11px;
  line-height: 1.4;
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

.alert-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.alert-header h4 {
  margin: 0;
}

.alert-badge {
  display: inline-block;
  min-width: 16px;
  padding: 0 5px;
  margin-left: 6px;
  border-radius: 8px;
  background: #ff4d4f;
  color: #fff;
  font-size: 10px;
  line-height: 16px;
  text-align: center;
  animation: alert-badge-pulse 1.4s ease-in-out infinite;
}

@keyframes alert-badge-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.6); }
  50% { box-shadow: 0 0 6px 3px rgba(255, 77, 79, 0.45); }
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
</style>
