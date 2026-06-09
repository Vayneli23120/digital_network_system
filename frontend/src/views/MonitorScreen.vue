<template>
  <div class="monitor-screen" :class="{ 'edit-mode': isEditMode }" data-screen-theme="dark">
    <!-- Header -->
    <header class="screen-header">
      <div class="header-left">
        <h1 class="screen-title">{{ t('monitorScreenTitle') }}</h1>
        <span class="live-badge">
          <span class="pulse"></span>
          {{ t('statusLive') }}
        </span>
        <!-- 紧凑平面图选择器（view/edit 都可用） -->
        <el-select v-model="selectedPlanId" :placeholder="t('monitorScreenSelectPlan')" @change="loadPlanNodes" size="small" style="width: 160px;">
          <el-option v-for="plan in floorPlans" :key="plan.id" :label="plan.name" :value="plan.id" />
        </el-select>
      </div>
      <div class="header-right">
        <!-- 筛选 popover（两态都可见） -->
        <el-popover placement="bottom" trigger="click" width="280">
          <template #reference>
            <button class="btn-filter-header">
              <el-icon><View /></el-icon>
              {{ t('monitorFilter') }}
            </button>
          </template>
          <div class="filter-popover-content">
            <el-select v-model="filterArea" :placeholder="t('monitorScreenFilterArea')" clearable size="small" style="width: 100%;">
              <el-option :label="t('monitorFilterAllAreas')" value="" />
              <el-option v-for="area in areaList" :key="area" :label="area" :value="area" />
            </el-select>
            <el-select v-model="filterDeviceType" :placeholder="t('monitorScreenFilterType')" clearable size="small" style="width: 100%; margin-top: 8px;">
              <el-option :label="t('monitorFilterAllTypes')" value="" />
              <el-option :label="t('deviceTypeUce')" value="uce" />
              <el-option :label="t('deviceTypeAp')" value="ap" />
              <el-option :label="t('deviceTypeSwitch')" value="switch" />
              <el-option :label="t('deviceTypeOfficeSwitch')" value="office_switch" />
              <el-option :label="t('deviceTypeCoreSwitch')" value="core_switch" />
            </el-select>
          </div>
        </el-popover>
        <span class="current-time">{{ currentTime }}</span>
        <!-- 编辑模式开关 -->
        <button class="btn-mode-switch" @click="isEditMode = !isEditMode" :class="{ active: isEditMode }">
          <el-icon><Edit /></el-icon>
          {{ isEditMode ? t('monitorModeEdit') : t('monitorModeView') }}
        </button>
        <button class="btn-refresh" @click="refreshData" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </header>

    <!-- Global Health Bar -->
    <div class="health-bar" v-if="globalSummary">
      <div class="health-score">
        <span class="health-label">{{ t('monitorHealthScore') }}</span>
        <span class="health-value">{{ globalSummary.health_score }}%</span>
      </div>
      <div class="health-divider"></div>
      <div class="health-stats">
        <span class="health-stat-item">
          <span class="stat-icon devices"></span>
          {{ t('monitorDevices') }} {{ globalSummary.total_devices }}
        </span>
        <span class="health-stat-item online">
          <span class="stat-icon online"></span>
          {{ t('statusReachable') }} {{ globalSummary.reachable }}
        </span>
        <span class="health-stat-item offline">
          <span class="stat-icon offline"></span>
          {{ t('statusUnreachable') }} {{ globalSummary.unreachable }}
        </span>
        <span class="health-stat-item switch">
          <span class="stat-icon switch"></span>
          {{ t('monitorScreenSwitches') }} {{ stats.switch_count }}
        </span>
        <span class="health-stat-item ap">
          <span class="stat-icon ap"></span>
          {{ t('monitorScreenAPs') }} {{ stats.ap_count }}
        </span>
        <!-- degraded_links 暂时恒为0，待 P2-3 接口级采集后启用 -->
        <span class="health-stat-item impacted" v-if="globalSummary.impacted_devices > 0">
          <span class="stat-icon impacted"></span>
          {{ t('monitorImpacted') }} {{ globalSummary.impacted_devices }}
        </span>
        <span class="health-stat-item alerts" v-if="globalSummary.active_alerts > 0">
          <span class="stat-icon alerts"></span>
          {{ t('dashAlerts') }} {{ globalSummary.active_alerts }}
        </span>
      </div>
    </div>

    <!-- Main Content -->
    <div class="screen-body">
      <!-- Floor Plan Area -->
      <div class="floor-plan-area">
        <!-- Edit Toolbar (仅编辑模式可见) -->
        <div class="edit-toolbar" v-if="isEditMode">
          <button class="btn-add-plan" @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            {{ t('monitorScreenUploadPlan') }}
          </button>
          <el-button type="danger" size="small" @click="deletePlan" v-if="selectedPlanId" :disabled="floorPlans.length <= 1">
            <el-icon><Delete /></el-icon>
            {{ t('actionDelete') }}
          </el-button>
          <button class="btn-add-node" @click="startCreateNode" v-if="selectedPlanId && !isCreatingNode">
            <el-icon><Plus /></el-icon>
            {{ t('monitorScreenCreateNode') }}
          </button>
          <button class="btn-cancel-node" @click="cancelCreateNode" v-if="isCreatingNode">
            <el-icon><Close /></el-icon>
            {{ t('actionCancel') }}
          </button>
          <button class="btn-draw-link" @click="startDrawLink" v-if="selectedPlanId && !linkDrawState?.active" :class="{ active: linkDrawState?.active }">
            <el-icon><Connection /></el-icon>
            {{ t('monitorDrawLink') }}
          </button>
          <button class="btn-cancel-link" @click="cancelDrawLink" v-if="linkDrawState?.active">
            <el-icon><Close /></el-icon>
            {{ t('actionCancel') }}
          </button>
        </div>

        <!-- Floor Plan Display -->
        <div class="plan-container" ref="planContainer">
          <!-- 缩放控制浮层（右下角半透明） -->
          <div class="zoom-float">
            <button class="zoom-btn" @click="zoomIn" title="放大">
              <el-icon><Plus /></el-icon>
            </button>
            <span class="zoom-value">{{ Math.round(zoomScale * 100) }}%</span>
            <button class="zoom-btn" @click="zoomOut" title="缩小">
              <el-icon><Minus /></el-icon>
            </button>
            <button class="zoom-btn" @click="resetZoom" title="重置">
              <el-icon><RefreshRight /></el-icon>
            </button>
          </div>
          <div
            class="plan-wrapper"
            ref="planWrapper"
            v-if="currentPlan"
            @click="handlePlanClick"
            @wheel="handleWheel"
            @mousedown="startPan"
            @mousemove="handlePan"
            @mouseup="endPan"
            @mouseleave="endPan"
            :style="planWrapperStyle"
          >
            <!-- Device Nodes Overlay -->
            <div class="nodes-overlay" v-if="imageLoaded">
              <!-- SVG Topology Links Layer -->
              <svg class="topo-layer" viewBox="0 0 100 100" preserveAspectRatio="none" v-if="links.length > 0">
                <!-- 链路路径 -->
                <path
                  v-for="link in logicalLinks"
                  :key="link.id"
                  :d="orthPath(link)"
                  :class="['topo-link', link.link_role, linkStatusClass(link), { selected: selectedLinkId === link.id }]"
                  fill="none"
                  @click.stop="onLinkClick(link)"
                  @dblclick.stop="onLinkPathClick(link, $event)"
                />
                <!-- 拐点手柄（编辑模式 + 有拐点的链路） -->
                <g v-if="isEditMode">
                  <template v-for="link in logicalLinks" :key="'wp-' + link.id">
                    <circle
                      v-for="(wp, idx) in getLinkWaypoints(link)"
                      :key="`${link.id}-${idx}`"
                      :cx="wp.x"
                      :cy="wp.y"
                      r="1.5"
                      class="waypoint-handle"
                      :class="{ dragging: waypointDragState?.linkId === link.id && waypointDragState?.waypointIndex === idx }"
                      @mousedown.stop="onWaypointMouseDown(link, idx, $event)"
                    />
                  </template>
                </g>
              </svg>
              <!-- Device Nodes -->
              <div
                v-for="node in filteredNodes"
                :key="node.id"
                :class="['device-node', node.status, node.device_type, {
                  flashing: node.status === 'offline',
                  highlighted: highlightedNodeId === node.id,
                  impacted: impactedNodeIds.includes(node.device_id),
                  dragging: dragState && dragState.nodeId === node.id,
                  resizing: resizeState && resizeState.nodeId === node.id,
                  'link-source': linkDrawState?.fromNodeId === node.id,
                  'link-target': linkDrawState?.active && linkDrawState?.fromNodeId !== node.id,
                }]"
                :style="{ left: node.x_percent + '%', top: node.y_percent + '%', transform: `translate(-50%, -50%) scale(${node.scale || 1})` }"
                @mousedown.stop="onNodeMouseDown($event, node)"
                @wheel.stop="onNodeWheel($event, node)"
              >
              <!-- Switch Icon -->
              <div class="node-icon switch-icon" v-if="node.device_type === 'switch'">
                <svg viewBox="0 0 24 24" width="20" height="20">
                  <rect x="2" y="6" width="20" height="12" rx="2" fill="currentColor"/>
                  <circle cx="6" cy="12" r="1.5" fill="#fff"/>
                  <circle cx="12" cy="12" r="1.5" fill="#fff"/>
                  <circle cx="18" cy="12" r="1.5" fill="#fff"/>
                </svg>
              </div>
              <!-- AP Icon -->
              <div class="node-icon ap-icon" v-if="node.device_type === 'ap'">
                <svg viewBox="0 0 24 24" width="20" height="20">
                  <circle cx="12" cy="12" r="4" fill="currentColor"/>
                  <path d="M12 2a10 10 0 0 1 0 4" stroke="currentColor" stroke-width="1.5" fill="none"/>
                  <path d="M12 2a10 10 0 0 0 0 4" stroke="currentColor" stroke-width="1.5" fill="none"/>
                </svg>
              </div>
              <!-- Default Icon -->
              <div class="node-icon default-icon" v-if="node.device_type !== 'switch' && node.device_type !== 'ap'">
                <svg viewBox="0 0 24 24" width="16" height="16">
                  <circle cx="12" cy="12" r="8" fill="currentColor"/>
                </svg>
              </div>
              <!-- Fault severity indicator dot -->
              <div
                v-if="node.active_fault_severity"
                :class="['fault-indicator', `fault-${node.active_fault_severity}`]"
                :title="`活跃故障: ${node.active_fault_severity}`"
              ></div>
              <span class="node-label">{{ node.device_name }}</span>
            </div>

            <!-- Create Node Marker -->
            <div v-if="isCreatingNode && tempPosition" class="temp-node-marker" :style="{ left: tempPosition.x + '%', top: tempPosition.y + '%' }">
              <div class="marker-icon">
                <svg viewBox="0 0 24 24" width="24" height="24">
                  <circle cx="12" cy="12" r="10" fill="#00d4aa" stroke="#fff" stroke-width="2"/>
                  <line x1="12" y1="7" x2="12" y2="17" stroke="#fff" stroke-width="2"/>
                  <line x1="7" y1="12" x2="17" y2="12" stroke="#fff" stroke-width="2"/>
                </svg>
              </div>
            </div>
          </div>
          </div>
          <div class="no-plan" v-if="!currentPlan">
            <el-icon><Picture /></el-icon>
            <span>{{ t('monitorScreenNoPlan') }}</span>
          </div>
        </div>
      </div>

      <!-- Alert Drawer (右侧可折叠) -->
      <div class="alert-drawer" :class="{ collapsed: !isAlertDrawerOpen }">
        <!-- 收起把手 -->
        <button class="drawer-toggle" @click="isAlertDrawerOpen = !isAlertDrawerOpen">
          <el-icon v-if="isAlertDrawerOpen"><Fold /></el-icon>
          <el-icon v-else><Expand /></el-icon>
          <span class="drawer-badge" v-if="offlineAlerts.length > 0 && !isAlertDrawerOpen">{{ offlineAlerts.length }}</span>
        </button>
        <!-- 展开内容 -->
        <div class="drawer-content" v-if="isAlertDrawerOpen">
          <div class="alert-header">
            <el-icon><Warning /></el-icon>
            <span>{{ t('monitorScreenOfflineAlerts') }}</span>
            <span class="alert-count" v-if="offlineAlerts.length">{{ offlineAlerts.length }}</span>
          </div>
          <div class="alert-list">
            <div
              v-for="alert in offlineAlerts"
              :key="alert.device_id"
              :class="['alert-item', { highlighted: highlightedNodeId && nodes.find(n => n.device_id === alert.device_id)?.id === highlightedNodeId }]"
              @click="highlightNode(alert.device_id)"
            >
              <div class="alert-icon">
                <svg viewBox="0 0 24 24" width="16" height="16">
                  <rect x="2" y="6" width="20" height="12" rx="2" fill="#ff4757"/>
                </svg>
              </div>
              <div class="alert-content">
                <span class="alert-name">{{ alert.device_name }}</span>
                <span class="alert-meta">{{ alert.ip }} · {{ alert.location }}</span>
              </div>
              <div class="alert-duration">
                <span class="duration-value">{{ alert.offline_str }}</span>
                <span class="duration-label">{{ t('monitorScreenOfflineTime') }}</span>
              </div>
            </div>
            <div class="no-alerts" v-if="offlineAlerts.length === 0">
              <el-icon><SuccessFilled /></el-icon>
              <span>{{ t('monitorScreenAllOnline') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Node Detail Popover -->
    <el-dialog
      v-model="showDetailDialog"
      :title="nodeDetail?.name"
      width="400px"
      class="node-detail-dialog"
      @close="highlightedNodeId = null"
    >
      <div class="detail-section" v-if="nodeDetail">
        <!-- Basic Info -->
        <div class="detail-block">
          <div class="block-title">{{ t('monitorScreenBasicInfo') }}</div>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">IP</span>
              <span class="info-value">{{ nodeDetail.ip }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('monitorScreenModel') }}</span>
              <span class="info-value">{{ nodeDetail.model || 'N/A' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('monitorScreenType') }}</span>
              <span class="info-value">{{ nodeDetail.device_type }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('monitorScreenStatus') }}</span>
              <span :class="['status-badge', nodeDetail.status]">{{ nodeDetail.status }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">{{ t('monitorScreenLocation') }}</span>
              <span class="info-value">{{ nodeDetail.location || 'N/A' }}</span>
            </div>
          </div>
        </div>

        <!-- Real-time Status -->
        <div class="detail-block">
          <div class="block-title">{{ t('monitorScreenRealTime') }}</div>
          <div class="status-grid">
            <div class="status-item">
              <span class="status-label">{{ t('monitorScreenUptime') }}</span>
              <span class="status-value">{{ nodeDetail.uptime_str }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">{{ t('monitorScreenPingLatency') }}</span>
              <span class="status-value">{{ nodeDetail.ping_latency || 'N/A' }}</span>
            </div>
          </div>
        </div>

        <!-- Lifespan -->
        <div class="detail-block">
          <div class="block-title">{{ t('monitorScreenLifespan') }}</div>
          <div class="lifespan-info">
            <div class="lifespan-item">
              <span class="lifespan-label">{{ t('monitorScreenInService') }}</span>
              <span class="lifespan-value">{{ nodeDetail.lifespan_str }}</span>
            </div>
            <div class="lifespan-item">
              <span class="lifespan-label">{{ t('monitorScreenPurchaseDate') }}</span>
              <span class="lifespan-value">{{ nodeDetail.purchase_date || 'N/A' }}</span>
            </div>
          </div>
        </div>

        <!-- Maintenance Records -->
        <div class="detail-block">
          <div class="block-title">{{ t('monitorScreenMaintenance') }}</div>
          <div class="maintenance-info">
            <div class="maintenance-item">
              <span class="maintenance-label">{{ t('monitorScreenLastBackup') }}</span>
              <span class="maintenance-value">{{ nodeDetail.last_backup }}</span>
            </div>
            <div class="maintenance-item fault" v-if="nodeDetail.last_fault">
              <span class="maintenance-label">{{ t('monitorScreenLastFault') }}</span>
              <span class="maintenance-value">{{ nodeDetail.last_fault.fault_no }} ({{ nodeDetail.last_fault.severity }})</span>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="detail-actions">
          <button class="btn-action" @click="goToDevice(nodeDetail.id)">
            <el-icon><View /></el-icon>
            {{ t('monitorScreenViewDevice') }}
          </button>
          <button class="btn-action danger" @click="deleteNodeFromPlan" v-if="currentPlan">
            <el-icon><Delete /></el-icon>
            {{ t('monitorScreenRemoveNode') }}
          </button>
        </div>
      </div>
    </el-dialog>

    <!-- Upload Floor Plan Dialog -->
    <el-dialog v-model="showUploadDialog" :title="t('monitorScreenUploadPlan')" width="400px" @close="resetUploadForm">
      <div class="upload-form">
        <div class="form-item">
          <label class="form-label">{{ t('monitorScreenPlanName') }}</label>
          <el-input v-model="newPlanName" :placeholder="t('monitorScreenPlanNamePlaceholder')" />
        </div>
        <div class="form-item">
          <label class="form-label">{{ t('monitorScreenPlanImage') }}</label>
          <div class="file-input-wrapper">
            <el-button @click="triggerFileInput">
              <el-icon><Upload /></el-icon>
              {{ t('monitorScreenSelectImage') }}
            </el-button>
            <input
              ref="fileInputRef"
              type="file"
              accept="image/*"
              @change="onFileSelect"
              style="display: none;"
            />
            <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="closeUploadDialog">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="uploadFloorPlan" :disabled="!newPlanName || !selectedFile || uploading" :loading="uploading">
          {{ uploading ? t('monitorScreenUploading') : t('actionConfirm') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- Select Device Dialog -->
    <el-dialog v-model="showSelectDeviceDialog" :title="t('monitorScreenSelectDevice')" width="500px">
      <div class="device-search">
        <el-input v-model="deviceSearchQuery" :placeholder="t('deviceSearchPlaceholder')" clearable />
      </div>
      <div class="device-list">
        <div
          v-for="device in filteredAvailableDevices"
          :key="device.id"
          :class="['device-option', { selected: selectedDeviceId === device.id }]"
          @click="selectedDeviceId = device.id"
        >
          <div class="device-icon">
            <svg viewBox="0 0 24 24" width="20" height="20" v-if="device.device_type === 'switch'">
              <rect x="2" y="6" width="20" height="12" rx="2" fill="currentColor"/>
            </svg>
            <svg viewBox="0 0 24 24" width="20" height="20" v-else-if="device.device_type === 'ap'">
              <circle cx="12" cy="12" r="4" fill="currentColor"/>
            </svg>
            <svg viewBox="0 0 24 24" width="16" height="16" v-else>
              <circle cx="12" cy="12" r="8" fill="currentColor"/>
            </svg>
          </div>
          <div class="device-info">
            <span class="device-name">{{ device.name }}</span>
            <span class="device-meta">{{ device.ip }} · {{ device.location }} · {{ device.status }}</span>
          </div>
        </div>
        <div class="no-devices" v-if="filteredAvailableDevices.length === 0">
          {{ t('monitorScreenNoAvailableDevices') }}
        </div>
      </div>
      <template #footer>
        <button class="btn-cancel" @click="cancelCreateNode">{{ t('actionCancel') }}</button>
        <button class="btn-confirm" @click="confirmCreateNode" :disabled="!selectedDeviceId || !tempPosition">
          {{ t('monitorScreenPlaceNode') }}
        </button>
      </template>
    </el-dialog>

    <!-- Link Role Select Dialog -->
    <el-dialog v-model="showLinkRoleDialog" :title="t('monitorSelectLinkRole')" width="350px">
      <div class="link-role-options">
        <div class="role-option" @click="createLink('uplink')">
          <div class="role-icon uplink"></div>
          <div class="role-info">
            <span class="role-name">{{ t('linkRoleUplink') }}</span>
            <span class="role-desc">{{ t('linkRoleUplinkDesc') }}</span>
          </div>
        </div>
        <div class="role-option" @click="createLink('svl')">
          <div class="role-icon svl"></div>
          <div class="role-info">
            <span class="role-name">{{ t('linkRoleSvl') }}</span>
            <span class="role-desc">{{ t('linkRoleSvlDesc') }}</span>
          </div>
        </div>
        <div class="role-option" @click="createLink('portchannel-member', null)">
          <div class="role-icon portchannel"></div>
          <div class="role-info">
            <span class="role-name">{{ t('linkRolePortchannel') }}</span>
            <span class="role-desc">{{ t('linkRolePortchannelDesc') }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showLinkRoleDialog = false; cancelDrawLink()">{{ t('actionCancel') }}</el-button>
      </template>
    </el-dialog>

    <!-- PortChannel Group Input Dialog -->
    <el-dialog v-model="showLinkGroupDialog" :title="t('monitorInputLinkGroup')" width="300px">
      <div class="link-group-input">
        <el-input v-model="pendingLinkGroup" :placeholder="t('monitorLinkGroupPlaceholder')" />
        <p class="group-hint">{{ t('monitorLinkGroupHint') }}</p>
      </div>
      <template #footer>
        <el-button @click="showLinkGroupDialog = false; cancelDrawLink()">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="confirmPortchannelLink">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- Link Edit/Delete Dialog (Edit Mode) -->
    <el-dialog v-model="showLinkEditDialog" :title="t('monitorEditLink')" width="300px" v-if="selectedLinkId && isEditMode">
      <div class="link-edit-content">
        <p>{{ t('monitorSelectedLink') }}: {{ selectedLinkId }}</p>
      </div>
      <template #footer>
        <el-button @click="showLinkEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="danger" @click="deleteSelectedLink(); showLinkEditDialog = false">
          <el-icon><Delete /></el-icon>
          {{ t('actionDelete') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- PortChannel Member Manage Dialog -->
    <el-dialog v-model="showLinkGroupManageDialog" :title="t('monitorManageLinkGroup')" width="400px">
      <div class="link-group-members" v-if="selectedLinkGroup">
        <p class="group-info">{{ t('monitorLinkGroupInfo', { group: selectedLinkGroup.link_group, count: selectedLinkGroup.memberCount }) }}</p>
        <div class="member-list">
          <div v-for="member in getLinkGroupMembers(selectedLinkGroup.link_group)" :key="member.id" class="member-item">
            <span class="member-name">{{ getMemberLabel(member) }}</span>
            <el-button size="small" type="danger" @click="deleteLinkMember(member.id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showLinkGroupManageDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="danger" @click="deleteLinkGroupAll()">
          <el-icon><Delete /></el-icon>
          {{ t('monitorDeleteGroupAll') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, Minus, Close, Picture, Warning, SuccessFilled, View, Delete, Upload, RefreshRight, Edit, Connection, Fold, Expand } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()

// State
const loading = ref(false)
const currentTime = ref(dayjs().format('HH:mm:ss'))
const selectedPlanId = ref(null)
const floorPlans = ref([])
const nodes = ref([])
const links = ref([])  // 拓扑链路列表
const linkGroups = ref([])  // 聚合组列表
const impactedNodeIds = ref([])  // 受影响节点 IDs
const globalSummary = ref(null)  // 全厂健康度汇总
const stats = ref({ total: 0, online: 0, offline: 0, switch_count: 0, ap_count: 0 })
const offlineAlerts = ref([])
const highlightedNodeId = ref(null)

// Edit Mode State
const isEditMode = ref(false)  // 编辑/监控模式切换
const isAlertDrawerOpen = ref(true)  // 告警抽屉展开状态

// Link Drawing State (Edit Mode)
const linkDrawState = ref(null)  // { active: boolean, fromNodeId: number, fromDeviceId: number }
const selectedLinkId = ref(null)  // 编辑模式下选中的链路 ID
const showLinkRoleDialog = ref(false)  // 链路角色选择弹窗
const pendingLinkTarget = ref(null)  // 待确认的目标节点 { nodeId, deviceId }
const showLinkEditDialog = ref(false)  // 链路编辑/删除弹窗
const showLinkGroupDialog = ref(false)  // PortChannel group 输入弹窗
const pendingLinkGroup = ref('')  // 待确认的 link_group
const showLinkGroupManageDialog = ref(false)  // PortChannel 成员管理弹窗
const selectedLinkGroup = ref(null)  // 选中的逻辑链路组信息

// Waypoint Drag State (Edit Mode)
const waypointDragState = ref(null)  // { linkId, waypointIndex, startX, startY }
const tempWaypoints = ref(null)  // 拖拽中的临时拐点位置

// Drag state (drag-to-reposition existing nodes)
const dragState = ref(null)

// Resize state (wheel-to-resize nodes)
const resizeState = ref(null)
let resizeSaveTimer = null

// WebSocket for real-time device status
let deviceStatusWs = null
let wsPingTimer = null

const connectDeviceStatusWs = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/device-status`
  try {
    deviceStatusWs = new WebSocket(wsUrl)

    deviceStatusWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.event === 'device_status_change') {
          handleDeviceStatusChange(msg)
        }
      } catch {}
    }

    deviceStatusWs.onclose = () => {
      if (wsPingTimer) clearInterval(wsPingTimer)
      // Reconnect after 5s
      setTimeout(connectDeviceStatusWs, 5000)
    }

    deviceStatusWs.onopen = () => {
      // Keep-alive ping every 30s
      wsPingTimer = setInterval(() => {
        if (deviceStatusWs && deviceStatusWs.readyState === WebSocket.OPEN) {
          deviceStatusWs.send('ping')
        }
      }, 30000)
    }
  } catch (e) {
    console.error('WebSocket connect failed:', e)
    setTimeout(connectDeviceStatusWs, 5000)
  }
}

const handleDeviceStatusChange = (msg) => {
  const { device_id, new_state, device_name, ip, location, device_type } = msg
  const newStatus = new_state === 'unreachable' ? 'offline' : 'online'

  // Update node status on map immediately
  const node = nodes.value.find(n => n.device_id === device_id)
  if (node) {
    node.status = newStatus
  }

  // Update stats counters
  if (new_state === 'unreachable') {
    stats.value.online = Math.max(0, (stats.value.online || 0) - 1)
    stats.value.offline = (stats.value.offline || 0) + 1
    // Add to offline alerts panel
    if (!offlineAlerts.value.find(a => a.device_id === device_id)) {
      offlineAlerts.value.unshift({
        device_id,
        device_name,
        ip,
        location,
        device_type,
        offline_hours: 0,
        offline_str: '刚刚',
        last_online: new Date().toISOString(),
      })
    }
  } else if (new_state === 'reachable') {
    stats.value.offline = Math.max(0, (stats.value.offline || 0) - 1)
    stats.value.online = (stats.value.online || 0) + 1
    // Remove from offline alerts panel
    offlineAlerts.value = offlineAlerts.value.filter(a => a.device_id !== device_id)
  }
}

// Filter State
const filterArea = ref('')
const filterDeviceType = ref('')

// 缩放和平移状态
const zoomScale = ref(1)
const panOffset = ref({ x: 0, y: 0 })
const isPanning = ref(false)
const panStart = ref({ x: 0, y: 0 })

// 计算平面图样式
const planWrapperStyle = computed(() => {
  return {
    backgroundImage: `url(${planImageUrl.value})`,
    transform: `scale(${zoomScale.value}) translate(${panOffset.value.x}px, ${panOffset.value.y}px)`,
    transformOrigin: 'center center',
    cursor: isPanning.value ? 'grabbing' : 'grab'
  }
})

// 缩放控制
const zoomIn = () => {
  if (zoomScale.value < 5) {
    zoomScale.value = Math.min(5, zoomScale.value + 0.25)
  }
}

const zoomOut = () => {
  if (zoomScale.value > 0.25) {
    zoomScale.value = Math.max(0.25, zoomScale.value - 0.25)
  }
}

const resetZoom = () => {
  zoomScale.value = 1
  panOffset.value = { x: 0, y: 0 }
}

// 鼠标滚轮缩放
const handleWheel = (e) => {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(0.25, Math.min(5, zoomScale.value + delta))
  zoomScale.value = newScale
}

// 拖拽平移
const startPan = (e) => {
  if (e.button === 0 && zoomScale.value > 1) {
    isPanning.value = true
    panStart.value = { x: e.clientX - panOffset.value.x, y: e.clientY - panOffset.value.y }
  }
}

const handlePan = (e) => {
  if (isPanning.value) {
    panOffset.value = {
      x: e.clientX - panStart.value.x,
      y: e.clientY - panStart.value.y
    }
  }
}

const endPan = () => {
  isPanning.value = false
}

// 车间列表（从节点中提取）
const areaList = computed(() => {
  const areas = new Set()
  nodes.value.forEach(n => {
    if (n.location) {
      areas.add(n.location)
    }
  })
  return Array.from(areas).sort()
})

// 过滤后的节点
const filteredNodes = computed(() => {
  return nodes.value.filter(n => {
    if (filterArea.value && n.location !== filterArea.value) return false
    if (filterDeviceType.value && n.device_type !== filterDeviceType.value) return false
    return true
  })
})

// Floor Plan display
const planContainer = ref(null)
const planWrapper = ref(null)
const imageLoaded = ref(false)
const currentPlan = computed(() => floorPlans.value.find(p => p.id === selectedPlanId.value))
const planImageUrl = computed(() => {
  if (!currentPlan.value) return ''
  // Convert local path to URL
  // Backend stores path like: assets/devices/floor_plans/xxx.jpg
  // Static mount: /photos -> ./assets/devices
  // So URL should be: /photos/floor_plans/xxx.jpg
  const path = currentPlan.value.image_path
  const filename = path.split('/').pop()
  // Encode filename to handle Chinese characters and spaces
  return '/photos/floor_plans/' + encodeURIComponent(filename)
})

// Watch planImageUrl to preload image and set loaded state
watch(planImageUrl, (newUrl) => {
  if (newUrl) {
    const img = new Image()
    img.onload = () => {
      imageLoaded.value = true
    }
    img.src = newUrl
  } else {
    imageLoaded.value = false
  }
}, { immediate: true })

// Node detail
const showDetailDialog = ref(false)
const nodeDetail = ref(null)

// Create node
const isCreatingNode = ref(false)
const tempPosition = ref(null)
const showSelectDeviceDialog = ref(false)
const availableDevices = ref([])
const deviceSearchQuery = ref('')
const selectedDeviceId = ref(null)
const filteredAvailableDevices = computed(() => {
  if (!deviceSearchQuery.value) return availableDevices.value
  const query = deviceSearchQuery.value.toLowerCase()
  return availableDevices.value.filter(d =>
    d.name.toLowerCase().includes(query) ||
    d.ip?.toLowerCase().includes(query) ||
    d.location?.toLowerCase().includes(query)
  )
})

// Upload floor plan
const showUploadDialog = ref(false)
const newPlanName = ref('')
const selectedFile = ref(null)
const uploading = ref(false)
const fileInputRef = ref(null)

const triggerFileInput = () => {
  if (fileInputRef.value) {
    fileInputRef.value.click()
  }
}

const resetUploadForm = () => {
  newPlanName.value = ''
  selectedFile.value = null
  uploading.value = false
}

const onFileSelect = (event) => {
  const file = event.target.files[0]
  console.log('File selected:', file)
  if (file) {
    selectedFile.value = file
    console.log('selectedFile set to:', selectedFile.value)
  }
}

const closeUploadDialog = () => {
  showUploadDialog.value = false
  resetUploadForm()
}

// Methods
// 内部加载函数（无 debounce，用于 refreshData 等需要立即执行的场景）
const _loadFloorPlans = async (force = false) => {
  try {
    const data = await cachedRequest(
      () => fetch('/api/floor-plans').then(r => r.json()),
      'monitor_floor_plans',
      {},
      { forceRefresh: force, ttl: 120 }
    )
    floorPlans.value = data.items || []
    // 如果没有选中平面图，选择第一个
    if (floorPlans.value.length > 0 && !selectedPlanId.value) {
      selectedPlanId.value = floorPlans.value[0].id
    }
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load floor plans:', err)
    }
  }
}

const _loadPlanNodes = async (planId, force = false) => {
  try {
    const data = await cachedRequest(
      () => fetch(`/api/floor-plans/${planId}/nodes`).then(r => r.json()),
      `monitor_nodes_${planId}`,
      { planId },
      { forceRefresh: force, ttl: 60 }
    )
    nodes.value = data.items || []
    // 加载拓扑链路
    await _loadPlanTopology(planId, force)
    // 不要重置 imageLoaded，保持图片加载状态
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load plan nodes:', err)
    }
  }
}

// 加载拓扑链路
const _loadPlanTopology = async (planId, force = false) => {
  try {
    const data = await cachedRequest(
      () => fetch(`/api/floor-plans/${planId}/topology`).then(r => r.json()),
      `monitor_topology_${planId}`,
      { planId },
      { forceRefresh: force, ttl: 60 }
    )
    links.value = data.links || []
    linkGroups.value = data.groups || []
    impactedNodeIds.value = data.impacted_node_ids || []
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load topology:', err)
    }
    links.value = []
    linkGroups.value = []
    impactedNodeIds.value = []
  }
}

// 计算正交折线路径（Manhattan routing）
const orthPath = (link) => {
  const fromNode = nodes.value.find(n => n.device_id === link.from)
  const toNode = nodes.value.find(n => n.device_id === link.to)
  if (!fromNode || !toNode) return ''

  // 转换百分比坐标到像素（相对于容器尺寸）
  // 由于容器尺寸动态，使用百分比直接计算
  const x1 = fromNode.x_percent
  const y1 = fromNode.y_percent
  const x2 = toNode.x_percent
  const y2 = toNode.y_percent

  // 使用 getLinkWaypoints 获取拐点（拖拽时返回 tempWaypoints）
  const waypoints = getLinkWaypoints(link)
  if (waypoints && waypoints.length > 0) {
    let path = `M ${x1},${y1}`
    for (const wp of waypoints) {
      path += ` L ${wp.x},${wp.y}`
    }
    path += ` L ${x2},${y2}`
    return path
  }

  // 默认：先横后竖（中点拐弯）
  const midX = (x1 + x2) / 2
  const midY = (y1 + y2) / 2

  // 选择拐弯方向：水平距离大 → 先横后竖；垂直距离大 → 先竖后横
  const dx = Math.abs(x2 - x1)
  const dy = Math.abs(y2 - y1)

  if (dx >= dy) {
    // 先横后竖
    return `M ${x1},${y1} L ${midX},${y1} L ${midX},${y2} L ${x2},${y2}`
  } else {
    // 先竖后横
    return `M ${x1},${y1} L ${x1},${midY} L ${x2},${midY} L ${x2},${y2}`
  }
}

// 计算链路状态样式类
const linkStatusClass = (link) => {
  // 对于 PortChannel 成员，使用组逻辑状态
  if (link.link_role === 'portchannel-member' && link.link_group) {
    const group = linkGroups.value.find(g => g.link_group === link.link_group)
    if (group) {
      return `link-${group.logical_status}`
    }
  }
  return `link-${link.status}`
}

// 计算逻辑链路列表（聚合显示）
const logicalLinks = computed(() => {
  // 对 PortChannel 成员按组聚合，只显示逻辑链路
  const result = []
  const processedGroups = new Set()

  for (const link of links.value) {
    if (link.link_role === 'portchannel-member' && link.link_group) {
      // 已处理的组跳过
      if (processedGroups.has(link.link_group)) continue
      processedGroups.add(link.link_group)

      // 使用第一个成员作为代表
      const group = linkGroups.value.find(g => g.link_group === link.link_group)
      if (group) {
        result.push({
          ...link,
          id: `logical-${link.link_group}`,
          status: group.logical_status,
          isLogical: true,
          memberCount: group.member_links.length,
        })
      }
    } else {
      // 非聚合链路直接添加
      result.push(link)
    }
  }

  return result
})

const refreshData = async () => {
  loading.value = true
  // 先加载平面图列表，确保 selectedPlanId 有值
  await _loadFloorPlans(true)
  // 再并行加载其他数据
  await Promise.all([loadStats(true), loadOfflineAlerts(true), loadGlobalSummary(true)])
  // 最后加载节点（依赖 selectedPlanId）
  if (selectedPlanId.value) {
    await _loadPlanNodes(selectedPlanId.value, true)
  }
  loading.value = false
  ElMessage.success(t('msgDataRefreshed'))
}

const deletePlan = async () => {
  if (!selectedPlanId.value) return

  try {
    await ElMessageBox.confirm(t('monitorScreenDeletePlanConfirm'), t('monitorScreenDeleteConfirmTitle'), { type: 'warning' })

    const res = await fetch(`/api/floor-plans/${selectedPlanId.value}`, { method: 'DELETE' })
    if (res.ok) {
      ElMessage.success(t('monitorScreenPlanDeleted'))
      // 重新加载列表并选择第一个
      await _loadFloorPlans(true)
      selectedPlanId.value = floorPlans.value[0]?.id || null
      if (selectedPlanId.value) {
        await _loadPlanNodes(selectedPlanId.value, true)
      }
    } else {
      const data = await res.json()
      ElMessage.error(data.detail || t('msgOpFailed'))
    }
  } catch {
    // 用户取消
  }
}

// Debounced 版本用于 el-select change 等需要防抖的场景
const loadFloorPlans = debounce((force = false) => _loadFloorPlans(force), 300)
const loadPlanNodes = debounce((planId, force = false) => {
  if (selectedPlanId.value === planId) {
    _loadPlanNodes(planId, force)
  }
}, 300)

const loadStats = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => fetch('/api/monitor-screen/stats').then(r => r.json()),
      'monitor_stats',
      {},
      { forceRefresh: force, ttl: 30 }
    )
    stats.value = data
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load stats:', err)
    }
  }
}, 300)

const loadOfflineAlerts = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => fetch('/api/monitor-screen/offline-alerts').then(r => r.json()),
      'monitor_offline_alerts',
      {},
      { forceRefresh: force, ttl: 60 }
    )
    offlineAlerts.value = data.items || []
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load offline alerts:', err)
    }
  }
}, 300)

const loadGlobalSummary = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => fetch('/api/monitor-screen/global-summary').then(r => r.json()),
      'monitor_global_summary',
      {},
      { forceRefresh: force, ttl: 30 }
    )
    globalSummary.value = data
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load global summary:', err)
    }
  }
}, 300)

const startCreateNode = async () => {
  if (!selectedPlanId.value) return
  isCreatingNode.value = true
  tempPosition.value = null
  selectedDeviceId.value = null

  // Load available devices
  try {
    const data = await cachedRequest(
      () => fetch(`/api/floor-plans/${selectedPlanId.value}/available-devices`).then(r => r.json()),
      `monitor_available_devices_${selectedPlanId.value}`,
      { planId: selectedPlanId.value },
      { ttl: 60 }
    )
    availableDevices.value = data.items || []
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load available devices:', err)
    }
  }
}

const cancelCreateNode = () => {
  isCreatingNode.value = false
  tempPosition.value = null
  showSelectDeviceDialog.value = false
  selectedDeviceId.value = null
}

const handlePlanClick = (e) => {
  if (!isCreatingNode.value) return

  // 使用 planWrapper 获取坐标（包含图片和节点层）
  const target = planWrapper.value
  if (!target) return

  const rect = target.getBoundingClientRect()
  const x = ((e.clientX - rect.left) / rect.width) * 100
  const y = ((e.clientY - rect.top) / rect.height) * 100

  tempPosition.value = { x: Math.round(x * 100) / 100, y: Math.round(y * 100) / 100 }
  showSelectDeviceDialog.value = true
}

const confirmCreateNode = async () => {
  if (!selectedDeviceId.value || !tempPosition.value || !selectedPlanId.value) return

  try {
    const res = await fetch(`/api/floor-plans/${selectedPlanId.value}/nodes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: selectedDeviceId.value,
        x_percent: tempPosition.value.x,
        y_percent: tempPosition.value.y,
      }),
    })
    const data = await res.json()
    if (res.ok) {
      ElMessage.success(data.message || t('msgSaveSuccess'))
      await _loadPlanNodes(selectedPlanId.value, true)
    } else {
      ElMessage.error(data.detail || 'Failed')
    }
  } catch (err) {
    ElMessage.error(t('msgLoadFailed'))
  }

  cancelCreateNode()
}

const showNodeDetail = async (node) => {
  highlightedNodeId.value = node.id
  try {
    const data = await cachedRequest(
      () => fetch(`/api/monitor-screen/device/${node.device_id}/detail`).then(r => r.json()),
      `monitor_device_detail_${node.device_id}`,
      { deviceId: node.device_id },
      { ttl: 30 }
    )
    nodeDetail.value = data
    showDetailDialog.value = true
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load device detail:', err)
    }
  }
}

const highlightNode = (deviceId) => {
  const node = nodes.value.find(n => n.device_id === deviceId)
  if (node) {
    highlightedNodeId.value = node.id
  }
}

// ===== Link Drawing Functions (Edit Mode) =====

const startDrawLink = () => {
  if (!isEditMode.value) return
  linkDrawState.value = { active: true, fromNodeId: null, fromDeviceId: null }
  ElMessage.info(t('monitorDrawLinkTip'))
}

const cancelDrawLink = () => {
  linkDrawState.value = null
  selectedLinkId.value = null
}

const onNodeClick = (node) => {
  if (!isEditMode.value) return

  // 连线绘制模式
  if (linkDrawState.value?.active) {
    if (!linkDrawState.value.fromNodeId) {
      // 选择源节点
      linkDrawState.value.fromNodeId = node.id
      linkDrawState.value.fromDeviceId = node.device_id
      ElMessage.info(t('monitorDrawLinkTarget'))
    } else if (linkDrawState.value.fromNodeId !== node.id) {
      // 选择目标节点，弹窗选择角色
      pendingLinkTarget.value = { nodeId: node.id, deviceId: node.device_id }
      showLinkRoleDialog.value = true
    }
    return
  }

  // 非连线模式：显示详情弹窗
  showNodeDetail(node)
}

const onLinkClick = (link) => {
  if (!isEditMode.value) return

  // 选中链路用于编辑/删除
  selectedLinkId.value = link.id

  // 如果是逻辑链路（PortChannel 聚合），打开成员管理弹窗
  if (link.isLogical) {
    // 从 id 中剥离 logical- 前缀获取 link_group
    const linkGroupId = link.id.toString().replace('logical-', '')
    selectedLinkGroup.value = {
      id: link.id,
      link_group: linkGroupId,
      memberCount: link.memberCount || 0,
    }
    showLinkGroupManageDialog.value = true
    return
  }

  // 显示编辑/删除弹窗
  showLinkEditDialog.value = true
}

// 创建链路（弹窗确认角色后）
const createLink = async (linkRole, linkGroup) => {
  if (!linkDrawState.value || !pendingLinkTarget.value) return

  // PortChannel 需要先输入 group id
  if (linkRole === 'portchannel-member' && linkGroup === null) {
    showLinkRoleDialog.value = false
    pendingLinkGroup.value = ''  // 清空上次输入
    showLinkGroupDialog.value = true
    return
  }

  try {
    const res = await fetch(`/api/floor-plans/${selectedPlanId.value}/links`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from_node_id: linkDrawState.value.fromNodeId,
        to_node_id: pendingLinkTarget.value.nodeId,
        link_role: linkRole,
        link_group: linkGroup || null,
        link_type: 'fiber',
      })
    })

    if (res.ok) {
      ElMessage.success(t('monitorLinkCreated'))
      await _loadPlanTopology(selectedPlanId.value, true)
    } else {
      const data = await res.json()
      ElMessage.error(data.detail || t('msgOpFailed'))
    }
  } catch (err) {
    ElMessage.error(t('msgOpFailed'))
  }

  // 重置状态
  showLinkRoleDialog.value = false
  showLinkGroupDialog.value = false
  linkDrawState.value = null
  pendingLinkTarget.value = null
}

// 确认 PortChannel 链路（带 group）
const confirmPortchannelLink = () => {
  const group = pendingLinkGroup.value.trim() || null
  createLink('portchannel-member', group)
}

// ===== Link Group Member Management =====

// 获取逻辑链路组的成员列表
const getLinkGroupMembers = (linkGroupId) => {
  return links.value.filter(l => l.link_group === linkGroupId)
}

// 获取成员链路的显示标签
const getMemberLabel = (member) => {
  const fromNode = nodes.value.find(n => n.device_id === member.from)
  const toNode = nodes.value.find(n => n.device_id === member.to)
  const fromName = fromNode?.device_name || '未知'
  const toName = toNode?.device_name || '未知'
  return `${fromName} → ${toName}`
}

// 删除单个成员链路
const deleteLinkMember = async (memberId) => {
  try {
    await ElMessageBox.confirm(t('monitorDeleteLinkConfirm'), t('monitorDeleteConfirmTitle'), { type: 'warning' })

    const res = await fetch(`/api/floor-plans/${selectedPlanId.value}/links/${memberId}`, { method: 'DELETE' })
    if (res.ok) {
      ElMessage.success(t('monitorLinkDeleted'))
      // 刷新拓扑
      await _loadPlanTopology(selectedPlanId.value, true)
      // 更新弹窗中的成员列表
      if (selectedLinkGroup.value) {
        const members = getLinkGroupMembers(selectedLinkGroup.value.link_group)
        if (members.length === 0) {
          // 无成员时关闭弹窗
          showLinkGroupManageDialog.value = false
        }
      }
    } else {
      ElMessage.error(t('msgOpFailed'))
    }
  } catch {
    // 用户取消
  }
}

// 删除整组
const deleteLinkGroupAll = async () => {
  if (!selectedLinkGroup.value) return

  try {
    await ElMessageBox.confirm(t('monitorDeleteGroupConfirm'), t('monitorDeleteConfirmTitle'), { type: 'warning' })

    const members = getLinkGroupMembers(selectedLinkGroup.value.link_group)
    for (const member of members) {
      await fetch(`/api/floor-plans/${selectedPlanId.value}/links/${member.id}`, { method: 'DELETE' })
    }

    ElMessage.success(t('monitorGroupDeleted'))
    showLinkGroupManageDialog.value = false
    await _loadPlanTopology(selectedPlanId.value, true)
  } catch {
    // 用户取消
  }
}

// ===== Waypoint Drag Functions =====

// 获取链路的拐点数组
const getLinkWaypoints = (link) => {
  // 使用临时拐点（拖拽中）或原始拐点
  if (waypointDragState.value?.linkId === link.id && tempWaypoints.value) {
    return tempWaypoints.value
  }
  return link.waypoints || []
}

// 拐点拖拽开始
const onWaypointMouseDown = (link, idx, event) => {
  if (!isEditMode.value) return

  const svg = event.target.closest('svg')
  const rect = svg.getBoundingClientRect()

  // 计算鼠标位置对应的百分比坐标
  const xPercent = (event.clientX - rect.left) / rect.width * 100
  const yPercent = (event.clientY - rect.top) / rect.height * 100

  waypointDragState.value = {
    linkId: link.id,
    waypointIndex: idx,
    startX: xPercent,
    startY: yPercent,
  }

  // 复制当前拐点数组作为临时状态
  tempWaypoints.value = [...(link.waypoints || [])]

  // 添加全局拖拽监听
  window.addEventListener('mousemove', onWaypointDrag)
  window.addEventListener('mouseup', onWaypointDragEnd)
}

// 拐点拖拽中
const onWaypointDrag = (event) => {
  if (!waypointDragState.value) return

  // 找到 SVG 容器
  const planWrapper = document.querySelector('.plan-wrapper')
  if (!planWrapper) return

  const svg = planWrapper.querySelector('.topo-layer')
  if (!svg) return

  const rect = svg.getBoundingClientRect()

  // 计算新位置（百分比）
  const xPercent = Math.max(0, Math.min(100, (event.clientX - rect.left) / rect.width * 100))
  const yPercent = Math.max(0, Math.min(100, (event.clientY - rect.top) / rect.height * 100))

  // 替换整个数组确保 Vue 触发重渲染（而非直接修改 wp.x/wp.y）
  const idx = waypointDragState.value.waypointIndex
  const newWaypoints = tempWaypoints.value.map((wp, i) =>
    i === idx ? { x: xPercent, y: yPercent } : { ...wp }
  )
  tempWaypoints.value = newWaypoints
}

// 拐点拖拽结束
const onWaypointDragEnd = async () => {
  if (!waypointDragState.value) return

  // 移除全局监听
  window.removeEventListener('mousemove', onWaypointDrag)
  window.removeEventListener('mouseup', onWaypointDragEnd)

  // 保存拐点
  await saveWaypoints(waypointDragState.value.linkId, tempWaypoints.value)

  // 重置状态
  waypointDragState.value = null
  tempWaypoints.value = null
}

// 点击链路中段插入新拐点
const onLinkPathClick = (link, event) => {
  if (!isEditMode.value) return

  // 逻辑链路不允许加拐点（聚合代表，拐点应加在具体成员上）
  if (link.isLogical) {
    ElMessage.warning(t('monitorLogicalLinkNoWaypoint'))
    return
  }

  // 获取 SVG 坐标
  const svg = event.target.closest('svg')
  const rect = svg.getBoundingClientRect()
  const xPercent = (event.clientX - rect.left) / rect.width * 100
  const yPercent = (event.clientY - rect.top) / rect.height * 100

  ElMessage.success(t('monitorWaypointAdded'))

  // 计算插入位置（在哪个拐点之间）
  const existingWaypoints = link.waypoints || []
  const fromNode = nodes.value.find(n => n.device_id === link.from)
  const toNode = nodes.value.find(n => n.device_id === link.to)

  if (!fromNode || !toNode) return

  // 构建完整路径点列表（起点 → 拐点 → 终点）
  const allPoints = [
    { x: fromNode.x_percent, y: fromNode.y_percent },
    ...existingWaypoints,
    { x: toNode.x_percent, y: toNode.y_percent },
  ]

  // 找到最近的两点之间插入
  let insertIndex = existingWaypoints.length // 默认插在最后一个拐点后
  let minDist = Infinity

  for (let i = 0; i < allPoints.length - 1; i++) {
    const p1 = allPoints[i]
    const p2 = allPoints[i + 1]
    // 计算点到线段的距离
    const dist = pointToSegmentDistance(xPercent, yPercent, p1.x, p1.y, p2.x, p2.y)
    if (dist < minDist) {
      minDist = dist
      insertIndex = i // 插在 p1 后（即 existingWaypoints 的 i-1 后）
    }
  }

  // 调整插入索引（考虑起点不算拐点）
  const waypointInsertIndex = Math.max(0, Math.min(existingWaypoints.length, insertIndex))

  // 创建新拐点数组
  const newWaypoints = [
    ...existingWaypoints.slice(0, waypointInsertIndex),
    { x: xPercent, y: yPercent },
    ...existingWaypoints.slice(waypointInsertIndex),
  ]

  // 保存
  saveWaypoints(link.id, newWaypoints)
}

// 计算点到线段距离
const pointToSegmentDistance = (px, py, x1, y1, x2, y2) => {
  const dx = x2 - x1
  const dy = y2 - y1
  const lenSq = dx * dx + dy * dy

  if (lenSq === 0) {
    // 线段是点
    return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
  }

  // 计算投影参数 t
  let t = ((px - x1) * dx + (py - y1) * dy) / lenSq
  t = Math.max(0, Math.min(1, t))

  // 投影点坐标
  const projX = x1 + t * dx
  const projY = y1 + t * dy

  return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2)
}

// 保存拐点到后端
const saveWaypoints = async (linkId, waypoints) => {
  try {
    const res = await fetch(`/api/floor-plans/${selectedPlanId.value}/links/${linkId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        waypoints: waypoints.length > 0 ? JSON.stringify(waypoints) : null,
      })
    })

    if (res.ok) {
      // 刷新拓扑数据
      await _loadPlanTopology(selectedPlanId.value, true)
    } else {
      ElMessage.error(t('msgOpFailed'))
    }
  } catch (err) {
    ElMessage.error(t('msgOpFailed'))
  }
}

// 删除选中链路
const deleteSelectedLink = async () => {
  if (!selectedLinkId.value) return

  try {
    await ElMessageBox.confirm(t('monitorDeleteLinkConfirm'), t('monitorDeleteConfirmTitle'), { type: 'warning' })

    // 如果是逻辑链路 ID（以 'logical-' 开头），需要删除所有成员
    const isLogical = selectedLinkId.value.toString().startsWith('logical-')
    if (isLogical) {
      const linkGroupId = selectedLinkId.value.toString().replace('logical-', '')
      // 删除所有该组的成员链路
      const groupLinks = links.value.filter(l => l.link_group === linkGroupId)
      for (const l of groupLinks) {
        await fetch(`/api/floor-plans/${selectedPlanId.value}/links/${l.id}`, { method: 'DELETE' })
      }
    } else {
      await fetch(`/api/floor-plans/${selectedPlanId.value}/links/${selectedLinkId.value}`, { method: 'DELETE' })
    }

    ElMessage.success(t('monitorLinkDeleted'))
    selectedLinkId.value = null
    await _loadPlanTopology(selectedPlanId.value, true)
  } catch {
    // 用户取消
  }
}

const goToDevice = (deviceId) => {
  showDetailDialog.value = false
  router.push(`/devices/${deviceId}`)
}

const deleteNodeFromPlan = async () => {
  if (!nodeDetail.value || !selectedPlanId.value) return

  try {
    await ElMessageBox.confirm(t('msgDeleteConfirm'), t('actionConfirm'), { type: 'warning' })
    const node = nodes.value.find(n => n.device_id === nodeDetail.value.id)
    if (node) {
      const res = await fetch(`/api/floor-plans/${selectedPlanId.value}/nodes/${node.id}`, { method: 'DELETE' })
      if (res.ok) {
        ElMessage.success(t('msgSaveSuccess'))
        showDetailDialog.value = false
        await _loadPlanNodes(selectedPlanId.value, true)
      }
    }
  } catch {
    // Cancelled
  }
}

const uploadFloorPlan = async () => {
  console.log('uploadFloorPlan called:', {
    name: newPlanName.value,
    file: selectedFile.value,
    uploading: uploading.value
  })

  if (!newPlanName.value || !selectedFile.value) {
    console.log('Missing data, returning early')
    return
  }

  uploading.value = true
  const formData = new FormData()
  formData.append('name', newPlanName.value)
  formData.append('image', selectedFile.value)

  try {
    const res = await fetch('/api/floor-plans', {
      method: 'POST',
      body: formData,
    })
    const data = await res.json()
    if (res.ok) {
      ElMessage.success(data.message || t('msgSaveSuccess'))
      closeUploadDialog()
      await _loadFloorPlans(true)
    } else {
      ElMessage.error(data.detail || t('monitorScreenUploadFailed'))
    }
  } catch (err) {
    console.error('Upload failed:', err)
    ElMessage.error(t('msgLoadFailed'))
  } finally {
    uploading.value = false
  }
}

// Node drag-to-reposition
const onNodeMouseDown = (e, node) => {
  if (e.button !== 0) return
  dragState.value = {
    nodeId: node.id,
    deviceId: node.device_id,
    startClientX: e.clientX,
    startClientY: e.clientY,
    startXPercent: node.x_percent,
    startYPercent: node.y_percent,
    moved: false,
  }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragEnd)
}

const onDragMove = (e) => {
  if (!dragState.value) return
  const dx = e.clientX - dragState.value.startClientX
  const dy = e.clientY - dragState.value.startClientY
  if (!dragState.value.moved && (Math.abs(dx) > 4 || Math.abs(dy) > 4)) {
    dragState.value.moved = true
  }
  if (dragState.value.moved && planWrapper.value) {
    const rect = planWrapper.value.getBoundingClientRect()
    const x = Math.max(0, Math.min(100, (e.clientX - rect.left) / rect.width * 100))
    const y = Math.max(0, Math.min(100, (e.clientY - rect.top) / rect.height * 100))
    const node = nodes.value.find(n => n.id === dragState.value.nodeId)
    if (node) {
      node.x_percent = Math.round(x * 100) / 100
      node.y_percent = Math.round(y * 100) / 100
    }
  }
}

const onDragEnd = async (e) => {
  if (!dragState.value) return
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
  const state = { ...dragState.value }
  dragState.value = null

  if (!state.moved) {
    const node = nodes.value.find(n => n.id === state.nodeId)
    if (!node) return

    // 连线模式：短按 = 选源/选目标节点
    if (linkDrawState.value?.active) {
      onNodeClick(node)
      return
    }

    // 普通模式：短按 = 弹设备详情
    showNodeDetail(node)
    return
  }

  // Save new position to backend
  const node = nodes.value.find(n => n.id === state.nodeId)
  if (!node || !selectedPlanId.value) return
  try {
    const res = await fetch(`/api/floor-plans/${selectedPlanId.value}/nodes/${state.nodeId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ x_percent: node.x_percent, y_percent: node.y_percent }),
    })
    if (!res.ok) {
      node.x_percent = state.startXPercent
      node.y_percent = state.startYPercent
      ElMessage.error('保存节点位置失败')
    }
  } catch {
    node.x_percent = state.startXPercent
    node.y_percent = state.startYPercent
    ElMessage.error('保存节点位置失败')
  }
}

// 滚轮调整节点大小
const onNodeWheel = (e, node) => {
  e.preventDefault()
  const delta = e.deltaY > 0 ? -0.1 : 0.1  // 向上放大，向下缩小
  const currentScale = node.scale || 1
  const newScale = Math.max(0.5, Math.min(3, currentScale + delta))

  // 更新节点缩放
  node.scale = Math.round(newScale * 10) / 10  // 保留一位小数

  // 显示调整状态
  resizeState.value = { nodeId: node.id, scale: node.scale }

  // 延迟保存（避免频繁请求）
  if (resizeSaveTimer) clearTimeout(resizeSaveTimer)
  resizeSaveTimer = setTimeout(async () => {
    resizeState.value = null
    if (!selectedPlanId.value) return
    try {
      await fetch(`/api/floor-plans/${selectedPlanId.value}/nodes/${node.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scale: node.scale }),
      })
    } catch (err) {
      console.error('Failed to save node scale:', err)
    }
  }, 500)
}

// Lifecycle
let refreshInterval = null
let timeTimerId = null

// 处理路由参数（故障工单联动）
const handleRouteParams = async () => {
  const deviceId = route.query.device_id
  if (deviceId) {
    // 等待数据加载
    await _loadFloorPlans(true)
    await loadStats(true)
    await loadOfflineAlerts(true)
    if (selectedPlanId.value) {
      await _loadPlanNodes(selectedPlanId.value, true)
    }

    // 找到对应的节点并高亮
    const node = nodes.value.find(n => n.device_id === parseInt(deviceId))
    if (node) {
      highlightedNodeId.value = node.id
      // 打开设备详情
      await showNodeDetail(node)
    }

    // 清除路由参数
    router.replace({ query: {} })
  }
}

// 监听路由参数变化
watch(route, (newRoute) => {
  if (newRoute.query.device_id) {
    handleRouteParams()
  }
}, { immediate: true })

onMounted(() => {
  refreshData()
  connectDeviceStatusWs()

  // Update time every second
  timeTimerId = setInterval(() => {
    currentTime.value = dayjs().format('HH:mm:ss')
  }, 1000)

  // Refresh data every 30 seconds (fallback when WebSocket is unavailable)
  refreshInterval = setInterval(() => {
    loadStats()
    loadOfflineAlerts()
    loadGlobalSummary()
    if (selectedPlanId.value) {
      _loadPlanNodes(selectedPlanId.value)
    }
  }, 30000)
})

onUnmounted(() => {
  if (timeTimerId) {
    clearInterval(timeTimerId)
  }
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (wsPingTimer) {
    clearInterval(wsPingTimer)
  }
  if (deviceStatusWs) {
    deviceStatusWs.onclose = null // prevent reconnect on intentional close
    deviceStatusWs.close()
  }
  // Cleanup drag handlers if any
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragEnd)
})
</script>

<style scoped>
.monitor-screen {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-primary);
  color: var(--text-primary);
}

/* 深色 NOC 主题覆盖 */
.monitor-screen[data-screen-theme="dark"] {
  --bg-primary: #0a0e17;
  --bg-secondary: #121826;
  --bg-tertiary: #1a2132;
  --text-primary: #e4e7eb;
  --text-secondary: #8b95a5;
  --text-tertiary: #6b7280;
  --border-default: #2a3441;

  /* 状态色高对比度 */
  --status-online: #10d98a;
  --status-offline: #ff3b5b;
  --status-impacted: #ffa116;
  --status-degraded: #ffd60a;
  --accent-primary: #10d98a;
  --accent-danger: #ff3b5b;
  --accent-warning: #ffa116;
}

/* Header */
.screen-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-default);
}

/* Global Health Bar */
.health-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 12px 24px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-default);
}

.monitor-screen[data-screen-theme="dark"] .health-bar {
  background: linear-gradient(90deg, #121826 0%, #1a2132 100%);
}

.health-score {
  display: flex;
  align-items: center;
  gap: 8px;
}

.health-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.health-value {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--accent-primary);
}

.monitor-screen[data-screen-theme="dark"] .health-value {
  color: #10d98a;
  text-shadow: 0 0 12px rgba(16, 217, 138, 0.4);
}

.health-divider {
  width: 1px;
  height: 32px;
  background: var(--border-default);
}

.health-stats {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.health-stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.stat-icon {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.stat-icon.devices { background: var(--text-tertiary); }
.stat-icon.online { background: #10d98a; }
.stat-icon.offline { background: #ff3b5b; }
.stat-icon.degraded { background: #ffd60a; }
.stat-icon.impacted { background: #ffa116; }
.stat-icon.alerts { background: #ff3b5b; }

.health-stat-item.online { color: #10d98a; }
.health-stat-item.offline { color: #ff3b5b; }
.health-stat-item.degraded { color: #ffd60a; }
.health-stat-item.impacted { color: #ffa116; }

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.screen-title {
  font-size: 20px;
  font-weight: 600;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: var(--success-bg);
  border: 1px solid var(--accent-primary);
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-primary);
}

.live-badge .pulse {
  width: 8px;
  height: 8px;
  background: var(--accent-primary);
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(0.8); }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.current-time {
  font-family: var(--font-display);
  font-size: 16px;
  color: var(--text-secondary);
}

.btn-refresh {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-refresh:hover:not(:disabled) {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.btn-refresh:disabled {
  opacity: 0.5;
}

/* Main Body */
.screen-body {
  display: flex;
  flex: 1;
  padding: 16px;
  gap: 16px;
  overflow: hidden;
  min-height: 0;
}

/* Floor Plan Area */
.floor-plan-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: hidden;
}

.plan-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.node-count {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-left: 8px;
}

.btn-add-plan, .btn-add-node, .btn-cancel-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.25s;
  box-shadow: 0 2px 4px rgba(0, 48, 135, 0.08);
}

.btn-add-plan:hover, .btn-add-node:hover {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.9) 0%, rgba(85, 239, 196, 0.9) 100%);
  color: #fff;
  border-color: transparent;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 184, 148, 0.2);
}

.btn-cancel-node {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.9) 0%, rgba(255, 71, 87, 0.9) 100%);
  color: #fff;
  border: none;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
}

.plan-container {
  position: relative;
  flex: 1;
  min-height: 0;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.zoom-controls {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.zoom-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.zoom-btn:hover {
  background: var(--accent-primary);
  color: #fff;
  border-color: var(--accent-primary);
}

.zoom-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-primary);
  min-width: 50px;
  text-align: center;
}

.plan-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  background-color: var(--bg-tertiary);
  transition: transform 0.1s ease-out;
  will-change: transform;
}

.nodes-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

/* Topology Links Layer - SVG */
.topo-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 1;  /* 低于节点层 */
  pointer-events: none;  /* 不阻碍节点交互 */
}

.topo-link {
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: stroke 0.3s, stroke-width 0.3s, opacity 0.3s;
}

/* 正常链路 - 近乎隐形 */
.topo-link.link-normal {
  stroke: var(--accent-primary);
  opacity: 0.15;
}

/* SVL 链路 - 核心堆叠 */
.topo-link.svl {
  stroke: #6366f1;  /* 靛蓝色 */
  stroke-width: 3;
  opacity: 0.3;
}

/* 降级链路 - 黄色警告（P2-3 预留：接口级采集后启用）
 * 当前 ICMP 无法检测 PortChannel 单成员物理断开，暂不触发此状态 */
.topo-link.link-degraded {
  stroke: #ffa116;
  stroke-width: 3;
  opacity: 0.8;
}

/* 断开链路 - 红色高亮 */
.topo-link.link-broken {
  stroke: #ff3b5b;
  stroke-width: 4;
  opacity: 1;
  animation: link-pulse 1.5s infinite;
}

@keyframes link-pulse {
  0%, 100% { opacity: 1; stroke-width: 4; }
  50% { opacity: 0.6; stroke-width: 3; }
}

/* PortChannel 逻辑链路 - 加粗 */
.topo-link.portchannel-member {
  stroke-width: 4;
}

.no-plan {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--text-tertiary);
}

.no-plan .el-icon {
  font-size: 48px;
}

/* Nodes Overlay */
.device-node {
  position: absolute;
  transform-origin: center center;
  cursor: pointer;
  transition: filter 0.2s;
}

.device-node:hover {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}

.device-node.highlighted {
  z-index: 10;
  filter: drop-shadow(0 3px 6px rgba(255, 193, 7, 0.4));
}

.device-node.dragging {
  z-index: 20;
  cursor: grabbing;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
  transition: none;
}

.device-node.resizing {
  z-index: 25;
  cursor: ns-resize;
  filter: drop-shadow(0 2px 6px rgba(0, 150, 255, 0.4));
}

.node-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.device-node.online .node-icon {
  color: var(--accent-primary);
}

.device-node.offline .node-icon {
  color: var(--accent-danger);
  animation: flash 1s infinite;
}

.device-node.maintenance .node-icon {
  color: var(--accent-warning);
}

/* 受影响节点 - 橙色脉冲（区别于自身 offline 的红色）*/
.device-node.impacted .node-icon {
  color: #ffa116;
  animation: impacted-pulse 2s infinite;
}

@keyframes impacted-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.node-label {
  position: absolute;
  bottom: -18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: var(--text-secondary);
  background: var(--bg-card);
  padding: 2px 6px;
  border-radius: 3px;
  white-space: nowrap;
}

/* Fault severity indicator dot */
.fault-indicator {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid var(--bg-secondary);
  z-index: 10;
  pointer-events: none;
}

.fault-critical {
  background: #ff4757;
  animation: fault-pulse 1s infinite;
}

.fault-high {
  background: #ff6b35;
}

.fault-medium {
  background: #ffd32a;
}

.fault-low {
  background: #7efff5;
}

@keyframes fault-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 71, 87, 0.5); }
  50% { box-shadow: 0 0 0 5px rgba(255, 71, 87, 0); }
}

.temp-node-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  z-index: 100;
}

.marker-icon {
  animation: pulse 1s infinite;
}

/* Stats Panel */
.stats-panel {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.stat-value {
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 700;
}

/* 深色主题增强 */
.monitor-screen[data-screen-theme="dark"] .stat-value {
  font-size: 42px;
  letter-spacing: -1px;
}

.monitor-screen[data-screen-theme="dark"] .stat-item.online .stat-value {
  color: #10d98a;
  text-shadow: 0 0 10px rgba(16, 217, 138, 0.3);
}

.monitor-screen[data-screen-theme="dark"] .stat-item.offline .stat-value {
  color: #ff3b5b;
  text-shadow: 0 0 10px rgba(255, 59, 91, 0.3);
}

.stat-item.online .stat-value { color: var(--accent-primary); }
.stat-item.offline .stat-value { color: var(--accent-danger); }
.stat-item.switch .stat-value { color: var(--accent-secondary); }
.stat-item.ap .stat-value { color: var(--accent-warning); }

.stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

/* Alert Panel */
.alert-panel {
  width: 280px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-default);
}

.alert-header .el-icon {
  color: var(--accent-danger);
}

.alert-count {
  padding: 2px 8px;
  background: var(--accent-danger);
  color: #fff;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
}

.alert-list {
  padding: 8px;
  max-height: calc(100vh - 200px);
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: var(--bg-card);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.alert-item:hover, .alert-item.highlighted {
  background: rgba(255, 71, 87, 0.1);
  border: 1px solid rgba(255, 71, 87, 0.3);
}

.alert-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.alert-name {
  font-size: 13px;
  font-weight: 500;
}

.alert-meta {
  font-size: 11px;
  color: var(--text-tertiary);
}

.alert-duration {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.duration-value {
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
  color: var(--accent-danger);
}

.duration-label {
  font-size: 10px;
  color: var(--text-tertiary);
}

.no-alerts {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px;
  color: var(--accent-primary);
}

.no-alerts .el-icon {
  font-size: 32px;
}

/* Node Detail Dialog */
.node-detail-dialog .detail-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-block {
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.block-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 8px;
}

.info-grid, .status-grid, .lifespan-info, .maintenance-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.info-item, .status-item, .lifespan-item, .maintenance-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-label, .status-label, .lifespan-label, .maintenance-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.info-value, .status-value, .lifespan-value, .maintenance-value {
  font-size: 13px;
  color: var(--text-primary);
}

.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.online {
  background: rgba(0, 212, 170, 0.15);
  color: var(--accent-primary);
}

.status-badge.offline {
  background: rgba(255, 71, 87, 0.15);
  color: var(--accent-danger);
}

.status-badge.maintenance {
  background: rgba(255, 184, 0, 0.15);
  color: var(--accent-warning);
}

.maintenance-item.fault .maintenance-value {
  color: var(--accent-danger);
}

.detail-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-action {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9) 0%, rgba(248, 250, 252, 0.9) 100%);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.25s;
  box-shadow: 0 2px 4px rgba(0, 48, 135, 0.08);
}

.btn-action:hover {
  background: linear-gradient(135deg, rgba(9, 132, 227, 0.9) 0%, rgba(116, 185, 255, 0.9) 100%);
  color: #fff;
  border-color: transparent;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(9, 132, 227, 0.2);
}

.btn-action.danger:hover {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.9) 0%, rgba(255, 71, 87, 0.9) 100%);
  border-color: transparent;
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.2);
}

/* Element Plus danger button 玻璃渐变 */
.plan-selector :deep(.el-button--danger) {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.9) 0%, rgba(255, 71, 87, 0.9) 100%);
  border: none;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);
}

.plan-selector :deep(.el-button--danger:hover) {
  background: linear-gradient(135deg, rgba(220, 53, 69, 0.95) 0%, rgba(255, 71, 87, 0.95) 100%);
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
}

/* Upload Dialog */
.upload-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.file-input-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-choose-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-choose-file:hover {
  background: var(--accent-primary);
  color: #fff;
  border-color: var(--accent-primary);
}

.file-name {
  font-size: 13px;
  color: var(--accent-primary);
}

.btn-upload {
  padding: 8px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
}

.btn-cancel, .btn-confirm {
  padding: 8px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  border: 1px solid transparent;
}

.btn-cancel {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
  color: var(--text-secondary);
}

.btn-cancel:hover {
  background: var(--bg-hover);
}

.btn-confirm {
  background: var(--accent-primary);
  color: #fff;
}

.btn-confirm:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Device Select Dialog */
.device-search {
  margin-bottom: 12px;
}

.device-list {
  max-height: 300px;
  overflow-y: auto;
}

.device-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.device-option:hover {
  background: var(--bg-hover);
}

.device-option.selected {
  border-color: var(--accent-primary);
  background: rgba(0, 212, 170, 0.1);
}

.device-option .device-icon {
  color: var(--accent-secondary);
}

.device-option .device-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.device-option .device-name {
  font-size: 13px;
  font-weight: 500;
}

.device-option .device-meta {
  font-size: 11px;
  color: var(--text-tertiary);
}

.no-devices {
  padding: 24px;
  text-align: center;
  color: var(--text-tertiary);
}

/* 暗黑模式 */
.dark .zoom-controls {
  background: rgba(22, 27, 34, 0.95);
  border: 1px solid rgba(48, 54, 61, 0.8);
}

.dark .zoom-btn {
  background: rgba(48, 54, 61, 0.8);
  border-color: #30363d;
  color: #8b949e;
}

.dark .zoom-btn:hover {
  background: var(--accent-primary);
  color: #fff;
}

.dark .zoom-value {
  color: #f0f6fc;
}

/* 暗黑模式按钮玻璃质感 */
.dark .btn-add-plan, .dark .btn-add-node {
  background: linear-gradient(135deg, rgba(48, 54, 61, 0.9) 0%, rgba(22, 27, 34, 0.9) 100%);
  border-color: #30363d;
  color: #8b949e;
}

.dark .btn-add-plan:hover, .dark .btn-add-node:hover {
  background: linear-gradient(135deg, rgba(63, 185, 80, 0.9) 0%, rgba(85, 239, 196, 0.9) 100%);
  color: #fff;
}

.dark .btn-cancel-node {
  background: linear-gradient(135deg, rgba(248, 81, 73, 0.9) 0%, rgba(255, 71, 87, 0.9) 100%);
}

.dark .btn-action {
  background: linear-gradient(135deg, rgba(48, 54, 61, 0.9) 0%, rgba(22, 27, 34, 0.9) 100%);
  border-color: #30363d;
  color: #8b949e;
}

.dark .btn-action:hover {
  background: linear-gradient(135deg, rgba(88, 166, 255, 0.9) 0%, rgba(116, 185, 255, 0.9) 100%);
}

.dark .btn-action.danger:hover {
  background: linear-gradient(135deg, rgba(248, 81, 73, 0.9) 0%, rgba(255, 71, 87, 0.9) 100%);
}

.dark .plan-selector :deep(.el-button--danger) {
  background: linear-gradient(135deg, rgba(248, 81, 73, 0.9) 0%, rgba(255, 71, 87, 0.9) 100%);
}

/* ===== Edit Mode ===== */
.btn-mode-switch {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-mode-switch:hover {
  background: var(--accent-primary);
  color: #fff;
  border-color: var(--accent-primary);
}

.btn-mode-switch.active {
  background: #6366f1;
  color: #fff;
  border-color: #6366f1;
}

.btn-filter-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-filter-header:hover {
  background: var(--bg-secondary);
  color: var(--accent-primary);
}

.monitor-screen.edit-mode {
  --accent-primary: #6366f1;
}

/* ===== Edit Toolbar ===== */
.edit-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  margin-bottom: 8px;
}

.btn-draw-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  border: none;
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-draw-link:hover, .btn-draw-link.active {
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
  transform: translateY(-1px);
}

.btn-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
}

.btn-filter:hover {
  background: var(--bg-tertiary);
}

.filter-popover-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ===== Zoom Float ===== */
.zoom-float {
  position: absolute;
  bottom: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(26, 33, 50, 0.6);
  border-radius: 8px;
  z-index: 50;
  opacity: 0.5;
  transition: opacity 0.3s;
}

.zoom-float:hover {
  opacity: 1;
}

/* ===== Alert Drawer ===== */
.alert-drawer {
  position: relative;
  min-width: 280px;
  max-width: 320px;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-default);
  transition: all 0.3s;
}

.alert-drawer.collapsed {
  min-width: 48px;
  max-width: 48px;
}

.drawer-toggle {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: none;
  border-right: 1px solid var(--border-default);
  color: var(--text-secondary);
  cursor: pointer;
  z-index: 10;
}

.drawer-toggle:hover {
  color: var(--accent-primary);
}

.drawer-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  background: #ff3b5b;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drawer-content {
  padding: 16px;
  margin-left: 48px;
}

.alert-drawer.collapsed .drawer-content {
  display: none;
}

/* ===== Link Drawing States ===== */
.device-node.link-source {
  box-shadow: 0 0 0 3px #6366f1, 0 0 12px rgba(99, 102, 241, 0.4);
}

.device-node.link-target {
  cursor: crosshair;
}

.device-node.link-target:hover {
  box-shadow: 0 0 0 2px #10d98a;
}

/* ===== Link Selection ===== */
.topo-link.selected {
  stroke-width: 5;
  filter: drop-shadow(0 0 4px rgba(99, 102, 241, 0.6));
}

/* ===== Link Role Dialog ===== */
.link-role-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.role-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.role-option:hover {
  background: var(--bg-secondary);
  transform: translateX(4px);
}

.role-icon {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.role-icon.uplink { background: #10d98a; }
.role-icon.svl { background: #6366f1; }
.role-icon.portchannel { background: #ffa116; }

.role-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.role-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.role-desc {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* ===== Switch/AP Stat Icons ===== */
.stat-icon.switch { background: #6366f1; }
.stat-icon.ap { background: #ffa116; }

.health-stat-item.switch { color: #6366f1; }
.health-stat-item.ap { color: #ffa116; }

/* Link Group Input Dialog */
.link-group-input {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* Waypoint Handle */
.waypoint-handle {
  fill: #6366f1;
  stroke: #fff;
  stroke-width: 0.3;
  cursor: grab;
  transition: r 0.2s;
}

.waypoint-handle:hover {
  r: 2;
  fill: #8b5cf6;
}

.waypoint-handle.dragging {
  r: 2.5;
  fill: #4f46e5;
  cursor: grabbing;
}

/* Link Group Member Management */
.link-group-members {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.group-info {
  font-size: 14px;
  color: var(--text-secondary);
}

.member-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.member-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: 6px;
}

.member-name {
  font-size: 13px;
  color: var(--text-primary);
}
</style>