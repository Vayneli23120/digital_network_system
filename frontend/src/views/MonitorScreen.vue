<template>
  <div class="monitor-screen">
    <!-- Header -->
    <header class="screen-header">
      <div class="header-left">
        <h1 class="screen-title">{{ t('monitorScreenTitle') }}</h1>
        <span class="live-badge">
          <span class="pulse"></span>
          {{ t('statusLive') }}
        </span>
      </div>
      <div class="header-right">
        <span class="current-time">{{ currentTime }}</span>
        <button class="btn-refresh" @click="refreshData" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <div class="screen-body">
      <!-- Left: Floor Plan Area -->
      <div class="floor-plan-area">
        <!-- Floor Plan Selector -->
        <div class="plan-selector">
          <el-select v-model="selectedPlanId" :placeholder="t('monitorScreenSelectPlan')" @change="loadPlanNodes" style="width: 200px;">
            <el-option v-for="plan in floorPlans" :key="plan.id" :label="plan.name" :value="plan.id">
              <span>{{ plan.name }}</span>
              <span class="node-count">{{ t('monitorScreenNodeCount', { count: plan.node_count }) }}</span>
            </el-option>
          </el-select>
          <el-button type="danger" size="small" @click="deletePlan" v-if="selectedPlanId" :disabled="floorPlans.length <= 1">
            <el-icon><Delete /></el-icon>
            {{ t('actionDelete') }}
          </el-button>
          <button class="btn-add-plan" @click="showUploadDialog = true">
            <el-icon><Plus /></el-icon>
            {{ t('monitorScreenUploadPlan') }}
          </button>
          <button class="btn-add-node" @click="startCreateNode" v-if="selectedPlanId && !isCreatingNode">
            <el-icon><Plus /></el-icon>
            {{ t('monitorScreenCreateNode') }}
          </button>
          <button class="btn-cancel-node" @click="cancelCreateNode" v-if="isCreatingNode">
            <el-icon><Close /></el-icon>
            {{ t('actionCancel') }}
          </button>
        </div>

        <!-- Floor Plan Display -->
        <div class="plan-container" ref="planContainer">
          <div
            class="plan-wrapper"
            ref="planWrapper"
            v-if="currentPlan"
            @click="handlePlanClick"
            :style="{ backgroundImage: `url(${planImageUrl})` }"
          >
            <!-- Device Nodes Overlay -->
            <div class="nodes-overlay" v-if="imageLoaded">
              <div
                v-for="node in nodes"
                :key="node.id"
                :class="['device-node', node.status, node.device_type, { flashing: node.status === 'offline', highlighted: highlightedNodeId === node.id }]"
                :style="{ left: node.x_percent + '%', top: node.y_percent + '%' }"
                @click.stop="showNodeDetail(node)"
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

        <!-- Stats Panel -->
        <div class="stats-panel">
          <div class="stat-item">
            <span class="stat-value">{{ stats.total }}</span>
            <span class="stat-label">{{ t('monitorScreenTotalDevices') }}</span>
          </div>
          <div class="stat-item online">
            <span class="stat-value">{{ stats.online }}</span>
            <span class="stat-label">{{ t('dashOnline') }}</span>
          </div>
          <div class="stat-item offline">
            <span class="stat-value">{{ stats.offline }}</span>
            <span class="stat-label">{{ t('dashOffline') }}</span>
          </div>
          <div class="stat-item switch">
            <span class="stat-value">{{ stats.switch_count }}</span>
            <span class="stat-label">{{ t('monitorScreenSwitches') }}</span>
          </div>
          <div class="stat-item ap">
            <span class="stat-value">{{ stats.ap_count }}</span>
            <span class="stat-label">{{ t('monitorScreenAPs') }}</span>
          </div>
        </div>
      </div>

      <!-- Right: Alert Panel -->
      <div class="alert-panel">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Plus, Close, Picture, Warning, SuccessFilled, View, Delete, Upload } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'

const router = useRouter()
const { t } = useI18n()

// State
const loading = ref(false)
const currentTime = ref(dayjs().format('HH:mm:ss'))
const selectedPlanId = ref(null)
const floorPlans = ref([])
const nodes = ref([])
const stats = ref({ total: 0, online: 0, offline: 0, switch_count: 0, ap_count: 0 })
const offlineAlerts = ref([])
const highlightedNodeId = ref(null)

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
const refreshData = async () => {
  loading.value = true
  await Promise.all([loadFloorPlans(), loadStats(), loadOfflineAlerts()])
  if (selectedPlanId.value) {
    await loadPlanNodes(selectedPlanId.value)
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
      await loadFloorPlans()
      selectedPlanId.value = floorPlans.value[0]?.id || null
      if (selectedPlanId.value) {
        await loadPlanNodes(selectedPlanId.value)
      }
    } else {
      const data = await res.json()
      ElMessage.error(data.detail || t('msgOpFailed'))
    }
  } catch {
    // 用户取消
  }
}

const loadFloorPlans = async () => {
  try {
    const res = await fetch('/api/floor-plans')
    const data = await res.json()
    floorPlans.value = data.items || []
    if (floorPlans.value.length > 0 && !selectedPlanId.value) {
      selectedPlanId.value = floorPlans.value[0].id
      await loadPlanNodes(selectedPlanId.value)
    }
  } catch (err) {
    console.error('Failed to load floor plans:', err)
  }
}

const loadPlanNodes = async (planId) => {
  try {
    const res = await fetch(`/api/floor-plans/${planId}/nodes`)
    const data = await res.json()
    nodes.value = data.items || []
    imageLoaded.value = false
  } catch (err) {
    console.error('Failed to load nodes:', err)
  }
}

const loadStats = async () => {
  try {
    const res = await fetch('/api/monitor-screen/stats')
    stats.value = await res.json()
  } catch (err) {
    console.error('Failed to load stats:', err)
  }
}

const loadOfflineAlerts = async () => {
  try {
    const res = await fetch('/api/monitor-screen/offline-alerts')
    const data = await res.json()
    offlineAlerts.value = data.items || []
  } catch (err) {
    console.error('Failed to load offline alerts:', err)
  }
}

const startCreateNode = async () => {
  if (!selectedPlanId.value) return
  isCreatingNode.value = true
  tempPosition.value = null
  selectedDeviceId.value = null

  // Load available devices
  try {
    const res = await fetch(`/api/floor-plans/${selectedPlanId.value}/available-devices`)
    const data = await res.json()
    availableDevices.value = data.items || []
  } catch (err) {
    console.error('Failed to load available devices:', err)
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
      await loadPlanNodes(selectedPlanId.value)
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
    const res = await fetch(`/api/monitor-screen/device/${node.device_id}/detail`)
    nodeDetail.value = await res.json()
    showDetailDialog.value = true
  } catch (err) {
    console.error('Failed to load device detail:', err)
  }
}

const highlightNode = (deviceId) => {
  const node = nodes.value.find(n => n.device_id === deviceId)
  if (node) {
    highlightedNodeId.value = node.id
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
        await loadPlanNodes(selectedPlanId.value)
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
      await loadFloorPlans()
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

// Lifecycle
let refreshInterval = null

onMounted(() => {
  refreshData()

  // Update time every second
  setInterval(() => {
    currentTime.value = dayjs().format('HH:mm:ss')
  }, 1000)

  // Refresh data every 30 seconds
  refreshInterval = setInterval(() => {
    loadStats()
    loadOfflineAlerts()
    if (selectedPlanId.value) {
      loadPlanNodes(selectedPlanId.value)
    }
  }, 30000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.monitor-screen {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
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
  padding: 16px;
  gap: 16px;
  min-height: calc(100vh - 72px);
}

/* Floor Plan Area */
.floor-plan-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.plan-selector {
  display: flex;
  align-items: center;
  gap: 12px;
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
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-add-plan:hover, .btn-add-node:hover {
  background: var(--accent-primary);
  color: #fff;
  border-color: var(--accent-primary);
}

.btn-cancel-node {
  background: var(--accent-danger);
  color: #fff;
  border-color: var(--accent-danger);
}

.plan-container {
  position: relative;
  flex: 1;
  min-height: 500px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.plan-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-size: contain;
  background-position: center;
  background-repeat: no-repeat;
  background-color: var(--bg-tertiary);
}

.nodes-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
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
  transform: translate(-50%, -50%);
  cursor: pointer;
  transition: all 0.2s;
}

.device-node:hover {
  transform: translate(-50%, -50%) scale(1.2);
}

.device-node.highlighted {
  transform: translate(-50%, -50%) scale(1.3);
  z-index: 10;
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
  font-size: 24px;
  font-weight: 600;
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
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-action:hover {
  background: var(--accent-secondary);
  color: #fff;
  border-color: var(--accent-secondary);
}

.btn-action.danger:hover {
  background: var(--accent-danger);
  border-color: var(--accent-danger);
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
</style>