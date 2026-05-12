<template>
  <div class="devices-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuDevices') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          <span>{{ t('deviceAdd') }}</span>
        </button>
        <el-dropdown split-button class="nav-action-btn export" @click="exportDevices">
          <el-icon><Upload /></el-icon>
          <span>{{ t('actionExport') }}</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="exportDevices">{{ t('deviceExcelExport') }}</el-dropdown-item>
              <el-dropdown-item @click="showImportDialog = true">{{ t('deviceExcelImport') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <button class="nav-action-btn secondary" @click="loadDevices" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-grid">
        <!-- 总设备 -->
        <div class="stat-card total" @click="filterByStatus('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Monitor /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.total }}</div>
              <div class="metric-label">{{ t('deviceStatsTotal') }}</div>
            </div>
            <div class="card-trend stable">
              <span class="trend-icon">●</span>
            </div>
          </div>
        </div>
        <!-- 在线设备 -->
        <div class="stat-card online" @click="filterByStatus('online')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.online }}</div>
              <div class="metric-label">{{ t('deviceStatsOnline') }}</div>
            </div>
            <div class="card-trend success" v-if="stats.online > 0">
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
        <!-- 离线设备 -->
        <div class="stat-card offline" @click="filterByStatus('offline')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><CircleClose /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value danger">{{ stats.offline }}</div>
              <div class="metric-label">{{ t('deviceStatsOffline') }}</div>
            </div>
            <div class="card-trend warning" v-if="stats.offline > 0">
              <el-icon><Warning /></el-icon>
            </div>
          </div>
        </div>
        <!-- 维护中 -->
        <div class="stat-card maintenance" @click="filterByStatus('maintenance')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Setting /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.maintenance }}</div>
              <div class="metric-label">{{ t('deviceStatsMaintenance') }}</div>
            </div>
            <div class="card-progress" v-if="stats.maintenance > 0">
              <div class="progress-ring" :style="{ '--percent': getMaintenancePercent() }"></div>
            </div>
          </div>
        </div>
        <!-- 已退役 -->
        <div class="stat-card retired" @click="filterByStatus('retired')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><WarningFilled /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.retired }}</div>
              <div class="metric-label">{{ t('deviceStatsRetired') }}</div>
            </div>
            <div class="card-trend done" v-if="stats.retired > 0">
              <el-icon><WarningFilled /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 高级筛选工具栏 -->
    <section class="filter-section">
      <div class="filter-toolbar">
        <!-- 搜索框 -->
        <div class="search-box">
          <el-icon class="search-icon"><Search /></el-icon>
          <el-input
            v-model="searchText"
            :placeholder="t('deviceSearchPlaceholder')"
            class="search-input"
            clearable
            @input="applyFilters"
          />
        </div>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <div
            :class="['status-chip', { active: filterStatus === '' }]"
            @click="filterByStatus('')"
          >
            <span class="chip-label">{{ t('deviceFilterAll') }}</span>
            <span class="chip-count">{{ stats.total }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-online', { active: filterStatus === 'online' }]"
            @click="filterByStatus('online')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('statusOnline') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-offline', { active: filterStatus === 'offline' }]"
            @click="filterByStatus('offline')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('statusOffline') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-maintenance', { active: filterStatus === 'maintenance' }]"
            @click="filterByStatus('maintenance')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('statusMaintenance') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-retired', { active: filterStatus === 'retired' }]"
            @click="filterByStatus('retired')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('statusRetired') }}</span>
          </div>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-select v-model="filterRole" :placeholder="t('deviceFilterRole')" clearable style="width: 100px" @change="applyFilters">
            <el-option :label="t('deviceRoleAccess')" value="access" />
            <el-option :label="t('deviceRoleDistribution')" value="distribution" />
            <el-option :label="t('deviceRoleCore')" value="core" />
          </el-select>
        </div>

        <!-- 批量操作 -->
        <div class="batch-actions">
          <el-checkbox v-model="selectMode">{{ t('deviceBatchSelect') }}</el-checkbox>
          <el-button type="success" size="small" @click="batchBackup" :disabled="selectedDevices.length === 0">
            <el-icon><Download /></el-icon>
            {{ t('deviceBatchBackup') }} ({{ selectedDevices.length }})
          </el-button>
        </div>
      </div>
    </section>

    <!-- 设备数据面板 -->
    <section class="data-section">
      <div class="table-header">
        <span class="table-title">Device List</span>
        <span class="table-count">{{ filteredTotal }} records</span>
      </div>

      <el-table
        :data="filteredDevices"
        class="enterprise-table"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        :row-class-name="tableRowClassName"
        :header-cell-style="{ background: 'transparent' }"
      >
        <el-table-column v-if="selectMode" type="selection" width="48" />
        <el-table-column prop="name" :label="t('deviceName')" min-width="140">
          <template #default="{ row }">
            <router-link :to="`/devices/${row.id}`" class="device-link">
              <span class="device-no-badge">{{ row.name }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="ip" :label="t('deviceIp')" min-width="130">
          <template #default="{ row }">
            <div class="ip-cell">
              <el-icon class="ip-icon"><Connection /></el-icon>
              <span class="ip-text">{{ row.ip }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('deviceStatus')" min-width="120" align="center">
          <template #default="{ row }">
            <div :class="['status-badge', row.status]">
              <span class="status-dot"></span>
              <span class="status-text">{{ getStatusText(row.status) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="location" :label="t('deviceLocation')" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="location-cell">
              <el-icon class="location-icon"><Location /></el-icon>
              <span class="location-text">{{ row.location || '--' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="model" :label="t('deviceModel')" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="model-cell">
              <span class="model-text">{{ row.model || '--' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column :label="t('deviceAction')" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-group">
              <button class="action-btn view" @click="viewDevice(row.id)" title="查看详情">
                <el-icon><View /></el-icon>
              </button>
              <button class="action-btn backup" @click="backupDevice(row)" title="备份配置">
                <el-icon><Download /></el-icon>
              </button>
              <button class="action-btn edit" @click="editDevice(row)" title="编辑">
                <el-icon><Edit /></el-icon>
              </button>
              <button class="action-btn delete" @click="deleteDevice(row)" title="删除">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoDevices')" :image-size="80">
            <el-button type="primary" size="small" @click="showAddDialog = true">{{ t('deviceAdd') }}</el-button>
          </el-empty>
        </template>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="filteredTotal"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </section>

    <!-- 添加/编辑设备对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('editDeviceTitle') : t('addDeviceTitle')" width="600px" class="edit-device-dialog">
      <div class="edit-dialog-content">
        <!-- 基础信息 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Monitor /></el-icon>
            {{ t('deviceBasicInfo') || '基础信息' }}
          </div>
          <el-form :model="newDevice" label-width="100px">
            <el-form-item :label="t('deviceName')" required>
              <el-input v-model="newDevice.name" :placeholder="t('editDeviceNamePlaceholder')" :disabled="editMode" />
            </el-form-item>
            <el-form-item :label="t('deviceIp')" required>
              <el-input v-model="newDevice.ip" :placeholder="t('editDeviceIpPlaceholder')" />
            </el-form-item>
            <el-form-item :label="t('deviceModel')">
              <el-input v-model="newDevice.model" :placeholder="t('editDeviceModelPlaceholder')" />
            </el-form-item>
            <el-form-item :label="t('deviceSerialNumber')">
              <el-input v-model="newDevice.serial_number" />
            </el-form-item>
            <el-form-item :label="t('deviceLocation')">
              <el-input v-model="newDevice.location" :placeholder="t('editDeviceLocationPlaceholder')" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 分类与状态 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Setting /></el-icon>
            {{ t('deviceCategoryStatus') || '分类与状态' }}
          </div>
          <el-form :model="newDevice" label-width="100px">
            <el-form-item :label="t('deviceVendor')">
              <el-select v-model="newDevice.vendor">
                <el-option v-for="v in vendors" :key="v.key" :label="v.name" :value="v.key" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceRole')">
              <el-select v-model="newDevice.role">
                <el-option :label="t('deviceRoleAccess')" value="access" />
                <el-option :label="t('deviceRoleDistribution')" value="distribution" />
                <el-option :label="t('deviceRoleCore')" value="core" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceStatus')">
              <el-select v-model="newDevice.status">
                <el-option :label="t('statusOnline')" value="online" />
                <el-option :label="t('statusOffline')" value="offline" />
                <el-option :label="t('statusMaintenance')" value="maintenance" />
                <el-option :label="t('statusRetired')" value="retired" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('deviceCredentialGroup')">
              <el-select v-model="newDevice.credential_group" :placeholder="t('deviceSelectCredential')">
                <el-option label="default" value="default" />
                <el-option v-for="cred in credentialGroups" :key="cred.id" :label="cred.name" :value="cred.name" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateDevice() : addDevice()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 导入设备对话框 -->
    <el-dialog v-model="showImportDialog" :title="t('deviceImportTitle')" width="600px">
      <el-alert
        :title="t('deviceImportDesc')"
        type="info"
        :closable="false"
        style="margin-bottom: 15px"
      >
        <p>{{ t('deviceImportTip') }}</p>
        <ul style="margin: 10px 0; padding-left: 20px">
          <li>{{ t('deviceImportName') }}</li>
          <li>{{ t('deviceImportIp') }}</li>
          <li>{{ t('deviceImportModel') }}</li>
          <li>{{ t('deviceImportSerial') }}</li>
          <li>{{ t('deviceImportLocation') }}</li>
          <li>{{ t('deviceImportRole') }}</li>
          <li>{{ t('deviceImportStatus') }}</li>
          <li>{{ t('deviceImportCredGroup') }}</li>
        </ul>
      </el-alert>
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".xlsx,.csv"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          {{ t('deviceUploadDrag') }}
        </div>
        <template #tip>
          <div class="el-upload__tip">
            {{ t('deviceUploadTip') }}
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showImportDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="importDevices" :disabled="!selectedFile">{{ t('deviceConfirmImport') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Plus, Upload, UploadFilled, Monitor, CircleCheck, CircleClose, Setting, WarningFilled, Refresh, Search, View, Edit, Delete, ArrowRight, Connection, Location, Warning } from '@element-plus/icons-vue'
import { getDevices, createDevice, updateDevice as updateDeviceApi, deleteDevice as deleteDeviceApi, backupDevice as backupDeviceApi, batchBackup as batchBackupApi, getCredentials, exportDevices as exportDevicesApi, importDevices as importDevicesApi, getVendors } from '@/api'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const router = useRouter()

const loading = ref(false)
const devices = ref([])
const searchText = ref('')
const filterStatus = ref('')
const filterRole = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const editMode = ref(false)
const selectMode = ref(false)
const selectedDevices = ref([])
const credentialGroups = ref([])
const selectedFile = ref(null)
const vendors = ref([])

const newDevice = ref({
  name: '',
  ip: '',
  model: '',
  serial_number: '',
  location: '',
  role: 'access',
  status: 'online',
  vendor: 'cisco',
  credential_group: 'default'
})

// 统计数据
const stats = computed(() => {
  const list = devices.value
  const totalCount = list.length
  const onlineCount = list.filter(d => d.status === 'online').length
  const offlineCount = list.filter(d => d.status === 'offline').length
  const maintenanceCount = list.filter(d => d.status === 'maintenance').length
  const retiredCount = list.filter(d => d.status === 'retired').length
  return {
    total: totalCount,
    online: onlineCount,
    offline: offlineCount,
    maintenance: maintenanceCount,
    retired: retiredCount
  }
})

// 分页后的总数
const filteredTotal = computed(() => filteredDevices.value.length)

// 筛选后的设备列表
const filteredDevices = computed(() => {
  let result = [...devices.value]

  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(d =>
      d.name.toLowerCase().includes(search) ||
      d.ip?.includes(search)
    )
  }

  if (filterStatus.value) {
    result = result.filter(d => d.status === filterStatus.value)
  }

  if (filterRole.value) {
    result = result.filter(d => d.role === filterRole.value)
  }

  return result
})

// 维护中百分比
const getMaintenancePercent = () => {
  if (stats.value.total === 0) return 0
  return Math.round((stats.value.maintenance / stats.value.total) * 100)
}

// 状态筛选
const filterByStatus = (status) => {
  filterStatus.value = status
  currentPage.value = 1
}

// 应用筛选
const applyFilters = () => {
  currentPage.value = 1
}

// 分页处理
const handlePageSizeChange = () => {
  currentPage.value = 1
}

const handlePageChange = () => {
  // 分页切换
}

// 表格行样式
const tableRowClassName = ({ row, rowIndex }) => {
  if (row.status === 'offline') return 'offline-row'
  if (row.status === 'retired') return 'retired-row'
  return ''
}

const getStatusType = (status) => {
  const types = { online: 'success', offline: 'danger', maintenance: 'warning', retired: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { online: t('statusOnline'), offline: t('statusOffline'), maintenance: t('statusMaintenance'), retired: t('statusRetired') }
  return texts[status] || status
}

const getRoleType = (role) => {
  const types = { access: '', distribution: 'warning', core: 'danger' }
  return types[role] || ''
}

const getRoleText = (role) => {
  const texts = { access: t('deviceRoleAccess'), distribution: t('deviceRoleDistribution'), core: t('deviceRoleCore') }
  return texts[role] || role
}

const handleSelectionChange = (selection) => {
  selectedDevices.value = selection.map(d => d.id)
}

const loadDevices = async () => {
  loading.value = true
  try {
    const params = { skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value }
    const data = await getDevices(params)
    devices.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    ElMessage.error(t('msgDeviceListFailed'))
  } finally {
    loading.value = false
  }
}

const loadCredentialGroups = async () => {
  try {
    const data = await getCredentials()
    credentialGroups.value = data.items || data || []
  } catch (error) {
    ElMessage.error(t('msgCredentialListFailed'))
  }
}

const viewDevice = (id) => {
  router.push(`/devices/${id}`)
}

const backupDevice = async (row) => {
  try {
    await backupDeviceApi(row.id, 'Web')
    ElMessage.success(t('msgBackupSuccess', { name: row.name }))
    loadDevices()
  } catch (error) {
    ElMessage.error(t('msgBackupFailed'))
  }
}

const batchBackup = async () => {
  if (selectedDevices.value.length === 0) return

  try {
    await ElMessageBox.confirm(t('confirmBackupSelected', { count: selectedDevices.value.length }), t('confirmBatchBackup'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await batchBackupApi(selectedDevices.value, 'Web')
    ElMessage.success(t('msgBatchBackupSuccess'))
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgBatchBackupFailed'))
    }
  }
}

const editDevice = (row) => {
  editMode.value = true
  newDevice.value = { ...row }
  showAddDialog.value = true
}

const updateDevice = async () => {
  try {
    const updateData = {
      id: newDevice.value.id,
      name: newDevice.value.name,
      ip: newDevice.value.ip,
      model: newDevice.value.model,
      serial_number: newDevice.value.serial_number,
      location: newDevice.value.location,
      role: newDevice.value.role,
      status: newDevice.value.status,
      credential_group: newDevice.value.credential_group
    }
    await updateDeviceApi(newDevice.value.id, updateData)
    ElMessage.success(t('msgDeviceUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    loadDevices()
  } catch (error) {
    ElMessage.error(t('msgDeviceUpdateFailed'))
    ElMessage.error(error.response?.data?.detail || t('msgDeviceUpdateFailed'))
  }
}

const deleteDevice = async (row) => {
  try {
    await ElMessageBox.confirm(t('confirmDeleteDevice', { name: row.name }), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteDeviceApi(row.id)
    ElMessage.success(t('msgDeviceDeleteSuccess'))
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgDeviceDeleteFailed'))
    }
  }
}

const addDevice = async () => {
  try {
    await createDevice(newDevice.value)
    ElMessage.success(t('msgDeviceAddSuccess'))
    showAddDialog.value = false
    loadDevices()
  } catch (error) {
    ElMessage.error(t('msgDeviceAddFailed'))
  }
}

const exportDevices = async () => {
  try {
    const blob = await exportDevicesApi()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `devices-${new Date().toISOString().split('T')[0]}.xlsx`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success(t('msgExportSuccess'))
  } catch (error) {
    ElMessage.error(t('msgExportFailed'))
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const importDevices = async () => {
  if (!selectedFile.value) {
    ElMessage.warning(t('msgImportSelectFile'))
    return
  }

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const result = await importDevicesApi(formData)
    ElMessage.success(t('msgImportSuccess', { success: result.success, failed: result.failed }))
    showImportDialog.value = false
    selectedFile.value = null
    loadDevices()
    loadCredentialGroups()
  } catch (error) {
    ElMessage.error(t('msgImportFailed'))
    ElMessage.error(error.response?.data?.detail || t('msgImportFailed'))
  }
}

const loadVendors = async () => {
  try {
    const res = await getVendors()
    vendors.value = res.vendors || []
  } catch (e) {
    console.error(t('msgVendorListFailed'), e)
  }
}

onMounted(() => {
  loadDevices()
  loadCredentialGroups()
  loadVendors()
})
</script>

<style scoped>
/* 字体清晰度优化 - 所有等宽字体 */
.device-no-badge,
.metric-value,
.chip-count,
.table-count,
.ip-text,
.status-text {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* ===== 页面整体背景 ===== */
.devices-page {
  padding: 0;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f8fafc 0%, #e8f4fc 50%, #f0f7ff 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 页面顶部导航条 ===== */
.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.06);
  position: relative;
  overflow: hidden;
}

.page-nav-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894);
}

.nav-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.nav-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.nav-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
  color: white;
  border: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(9, 132, 227, 0.25);
}

.nav-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(9, 132, 227, 0.35);
}

.nav-action-btn.secondary {
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  box-shadow: none;
  padding: 8px 12px;
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.nav-action-btn.export {
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  box-shadow: none;
}

.nav-action-btn.export:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.nav-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ===== 统计 Dashboard ===== */
.stats-dashboard {
  padding: 16px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(16px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(9, 132, 227, 0.05) 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.stat-card:hover::before {
  opacity: 1;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 48, 135, 0.12);
}

.card-content {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
}

.card-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: transform 0.3s;
}

.stat-card:hover .card-icon {
  transform: scale(1.05);
}

.stat-card.total .card-icon {
  background: linear-gradient(135deg, rgba(9, 132, 227, 0.15) 0%, rgba(9, 132, 227, 0.08) 100%);
  color: #0984e3;
}
.stat-card.online .card-icon {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.2) 0%, rgba(0, 184, 148, 0.1) 100%);
  color: #00b894;
}
.stat-card.offline .card-icon {
  background: linear-gradient(135deg, rgba(214, 48, 49, 0.2) 0%, rgba(214, 48, 49, 0.1) 100%);
  color: #d63031;
}
.stat-card.maintenance .card-icon {
  background: linear-gradient(135deg, rgba(225, 112, 85, 0.2) 0%, rgba(225, 112, 85, 0.1) 100%);
  color: #e17055;
}
.stat-card.retired .card-icon {
  background: linear-gradient(135deg, rgba(116, 185, 255, 0.2) 0%, rgba(116, 185, 255, 0.1) 100%);
  color: #74b9ff;
}

.card-body { flex: 1; }

.metric-value {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
  letter-spacing: -0.02em;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.metric-value.danger {
  color: #d63031;
}

.metric-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 6px;
  font-weight: 500;
}

.card-trend {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.card-trend.stable { background: rgba(9, 132, 227, 0.1); color: #0984e3; }
.card-trend.warning { background: rgba(214, 48, 49, 0.1); color: #d63031; }
.card-trend.success { background: rgba(0, 184, 148, 0.1); color: #00b894; }
.card-trend.done { background: rgba(116, 185, 255, 0.1); color: #74b9ff; }

.card-progress {
  width: 24px;
  height: 24px;
  position: relative;
}

.progress-ring {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: conic-gradient(#e17055 calc(var(--percent) * 1%), rgba(225, 112, 85, 0.2) 0);
  display: flex;
  align-items: center;
  justify-content: center;
}

.progress-ring::after {
  content: '';
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: white;
}

/* ===== 筛选工具栏 ===== */
.filter-section {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 12px rgba(0, 48, 135, 0.06);
}

.filter-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--text-tertiary);
  font-size: 14px;
  z-index: 1;
}

.search-input {
  width: 240px;
}

.search-input :deep(.el-input__wrapper) {
  padding-left: 36px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  box-shadow: none;
  transition: all 0.25s;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(9, 132, 227, 0.15);
}

/* Status Chips */
.status-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.status-chip::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  right: 50%;
  height: 2px;
  background: currentColor;
  transition: all 0.25s ease;
}

.status-chip:hover::before,
.status-chip.active::before {
  left: 0;
  right: 0;
}

.status-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.1);
}

.status-chip.active {
  background: rgba(9, 132, 227, 0.08);
  border-color: rgba(9, 132, 227, 0.3);
  color: #0984e3;
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.chip-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.status-chip.active .chip-label {
  color: #0984e3;
}

.chip-count {
  font-size: 11px;
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--text-tertiary);
  padding: 2px 6px;
  background: rgba(0, 48, 135, 0.05);
  border-radius: 4px;
}

.status-chip.chip-online .chip-dot { background: #00b894; }
.status-chip.chip-offline .chip-dot { background: #d63031; }
.status-chip.chip-maintenance .chip-dot { background: #e17055; }
.status-chip.chip-retired .chip-dot { background: #74b9ff; }

.status-chip.chip-online:hover { background: rgba(0, 184, 148, 0.08); border-color: rgba(0, 184, 148, 0.3); }
.status-chip.chip-offline:hover { background: rgba(214, 48, 49, 0.08); border-color: rgba(214, 48, 49, 0.3); }
.status-chip.chip-maintenance:hover { background: rgba(225, 112, 85, 0.08); border-color: rgba(225, 112, 85, 0.3); }
.status-chip.chip-retired:hover { background: rgba(116, 185, 255, 0.08); border-color: rgba(116, 185, 255, 0.3); }

.more-filters {
  display: flex;
  gap: 8px;
}

.more-filters :deep(.el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  box-shadow: none;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

/* ===== 数据面板 ===== */
.data-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.08);
}

.table-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.03em;
}

.table-count {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.enterprise-table { width: 100%; }

.enterprise-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.enterprise-table :deep(.el-table__header-wrapper) {
  border-bottom: 2px solid rgba(0, 48, 135, 0.1);
}

.enterprise-table :deep(th.el-table__cell) {
  background: transparent;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
  padding: 12px 0;
  border-bottom: none;
}

.enterprise-table :deep(td.el-table__cell) {
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
  padding: 10px 0;
  background: transparent;
}

.enterprise-table :deep(.el-table__row) {
  transition: all 0.25s ease;
  background: transparent;
}

.enterprise-table :deep(.el-table__row:hover > td) {
  background: rgba(9, 132, 227, 0.04) !important;
}

.enterprise-table :deep(.offline-row > td) {
  background: rgba(214, 48, 49, 0.04) !important;
}

.enterprise-table :deep(.retired-row) {
  opacity: 0.6;
}

/* 设备链接 */
.device-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent-primary);
  text-decoration: none;
  transition: all 0.25s;
}

.device-link:hover {
  color: var(--accent-secondary);
}

.device-no-badge {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
  font-size: 13px;
  padding: 4px 8px;
  background: rgba(9, 132, 227, 0.08);
  border-radius: 6px;
  transition: all 0.25s;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  letter-spacing: 0.02em;
}

.device-link:hover .device-no-badge {
  background: rgba(9, 132, 227, 0.15);
}

.link-arrow {
  opacity: 0;
  font-size: 12px;
  transition: all 0.25s;
  color: var(--accent-primary);
}

.device-link:hover .link-arrow {
  opacity: 1;
  transform: translateX(4px);
}

/* IP单元格 */
.ip-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ip-icon {
  font-size: 14px;
  color: var(--text-tertiary);
}

.ip-text {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-text {
  letter-spacing: 0.02em;
}

.status-badge.online {
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}
.status-badge.online .status-dot { background: #00b894; }

.status-badge.offline {
  border-color: rgba(214, 48, 49, 0.3);
  color: #d63031;
}
.status-badge.offline .status-dot { background: #d63031; }

.status-badge.maintenance {
  border-color: rgba(225, 112, 85, 0.3);
  color: #e17055;
}
.status-badge.maintenance .status-dot { background: #e17055; }

.status-badge.retired {
  border-color: rgba(116, 185, 255, 0.3);
  color: #74b9ff;
}
.status-badge.retired .status-dot { background: #74b9ff; }

/* 位置单元格 */
.location-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.location-icon {
  font-size: 14px;
  color: var(--text-tertiary);
}

.location-text {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 型号单元格 */
.model-cell {
  display: flex;
  align-items: center;
}

.model-text {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 操作按钮组 */
.action-group {
  display: flex;
  gap: 4px;
  justify-content: center;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.15);
}

.action-btn.view:hover {
  background: rgba(9, 132, 227, 0.08);
  border-color: rgba(9, 132, 227, 0.2);
  color: #0984e3;
}

.action-btn.backup:hover {
  background: rgba(0, 184, 148, 0.08);
  border-color: rgba(0, 184, 148, 0.2);
  color: #00b894;
}

.action-btn.edit:hover {
  background: rgba(251, 191, 36, 0.08);
  border-color: rgba(251, 191, 36, 0.2);
  color: #f59e0b;
}

.action-btn.delete:hover {
  background: rgba(214, 48, 49, 0.08);
  border-color: rgba(214, 48, 49, 0.2);
  color: #d63031;
}

/* 分页 */
.pagination-bar {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 48, 135, 0.06);
  display: flex;
  justify-content: flex-end;
}

.pagination-bar :deep(.el-pagination) {
  gap: 8px;
}

.pagination-bar :deep(.el-pagination button),
.pagination-bar :deep(.el-pager li) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 6px;
  border: 1px solid var(--border-default);
  font-size: 12px;
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.pagination-bar :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #0984e3, #74b9ff);
  border-color: transparent;
  color: white;
}

/* ===== 编辑对话框 ===== */
.edit-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input {
    width: 100%;
  }

  .status-chips {
    justify-content: center;
  }

  .more-filters {
    justify-content: center;
  }

  .batch-actions {
    justify-content: center;
    margin-left: 0;
  }

  .page-nav-bar {
    flex-direction: column;
    gap: 12px;
  }

  .nav-right {
    width: 100%;
    justify-content: center;
  }
}

/* ===== 暗黑模式 ===== */
.dark .devices-page {
  background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #161b22 100%);
}

.dark .page-nav-bar {
  background: rgba(22, 27, 34, 0.9);
  border-color: rgba(48, 54, 61, 0.8);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .page-nav-bar::before {
  background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894);
}

.dark .page-title {
  color: #f0f6fc;
}

.dark .nav-action-btn {
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
}

.dark .nav-action-btn.secondary {
  background: rgba(48, 54, 61, 0.8);
  color: #8b949e;
  border-color: #30363d;
}

.dark .nav-action-btn.secondary:hover {
  background: rgba(9, 132, 227, 0.15);
  border-color: #0984e3;
  color: #58a6ff;
}

.dark .nav-action-btn.export {
  background: rgba(48, 54, 61, 0.8);
  color: #8b949e;
  border-color: #30363d;
}

.dark .nav-action-btn.export:hover {
  background: rgba(9, 132, 227, 0.15);
  border-color: #0984e3;
  color: #58a6ff;
}

.dark .stats-dashboard {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

.dark .stat-card {
  background: rgba(13, 17, 23, 0.95);
  border-color: rgba(48, 54, 61, 0.6);
}

.dark .stat-card:hover {
  background: rgba(22, 27, 34, 0.95);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.dark .metric-value {
  color: #f0f6fc;
}

.dark .metric-value.danger {
  color: #f85149;
}

.dark .metric-label {
  color: #8b949e;
}

.dark .card-trend.stable { background: rgba(9, 132, 227, 0.2); color: #58a6ff; }
.dark .card-trend.warning { background: rgba(248, 81, 73, 0.2); color: #f85149; }
.dark .card-trend.success { background: rgba(63, 185, 80, 0.2); color: #3fb950; }
.dark .card-trend.done { background: rgba(116, 185, 255, 0.2); color: #74b9ff; }

.dark .progress-ring {
  background: conic-gradient(#e17055 calc(var(--percent) * 1%), rgba(225, 112, 85, 0.3) 0);
}

.dark .progress-ring::after {
  background: #0d1117;
}

.dark .filter-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.dark .search-input :deep(.el-input__wrapper) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

.dark .search-input :deep(.el-input__wrapper:hover),
.dark .search-input :deep(.el-input__wrapper.is-focus) {
  border-color: #58a6ff;
  box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
}

.dark .search-icon {
  color: #8b949e;
}

.dark .status-chip {
  background: rgba(13, 17, 23, 0.9);
  border-color: #30363d;
}

.dark .status-chip:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .chip-label {
  color: #8b949e;
}

.dark .status-chip.active {
  background: rgba(88, 166, 255, 0.15);
  border-color: rgba(88, 166, 255, 0.4);
  color: #58a6ff;
}

.dark .status-chip.active .chip-label {
  color: #58a6ff;
}

.dark .chip-count {
  background: rgba(48, 54, 61, 0.3);
  color: #8b949e;
}

.dark .more-filters :deep(.el-select .el-input__wrapper) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

/* 状态徽章暗黑模式 */
.dark .status-badge {
  background: rgba(13, 17, 23, 0.9);
}

.dark .status-badge.online {
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}
.dark .status-badge.online .status-dot { background: #3fb950; }

.dark .status-badge.offline {
  border-color: rgba(248, 81, 73, 0.4);
  color: #f85149;
}
.dark .status-badge.offline .status-dot { background: #f85149; }

.dark .status-badge.maintenance {
  border-color: rgba(225, 112, 85, 0.4);
  color: #e17055;
}
.dark .status-badge.maintenance .status-dot { background: #e17055; }

.dark .status-badge.retired {
  border-color: rgba(116, 185, 255, 0.4);
  color: #74b9ff;
}
.dark .status-badge.retired .status-dot { background: #74b9ff; }

.dark .data-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

.dark .table-header {
  border-bottom-color: rgba(48, 54, 61, 0.6);
}

.dark .table-title {
  color: #8b949e;
}

.dark .table-count {
  color: #6e7681;
}

.dark .enterprise-table :deep(.el-table__header-wrapper) {
  border-bottom-color: rgba(48, 54, 61, 0.6);
}

.dark .enterprise-table :deep(th.el-table__cell) {
  color: #8b949e;
}

.dark .enterprise-table :deep(td.el-table__cell) {
  border-bottom-color: rgba(48, 54, 61, 0.3);
}

.dark .enterprise-table :deep(.el-table__row:hover > td) {
  background: rgba(88, 166, 255, 0.08) !important;
}

.dark .enterprise-table :deep(.offline-row > td) {
  background: rgba(248, 81, 73, 0.08) !important;
}

.dark .device-link {
  color: #58a6ff;
}

.dark .device-no-badge {
  background: rgba(88, 166, 255, 0.15);
}

.dark .device-link:hover .device-no-badge {
  background: rgba(88, 166, 255, 0.25);
}

.dark .ip-text {
  color: #8b949e;
}

.dark .location-text {
  color: #8b949e;
}

.dark .model-text {
  color: #8b949e;
}

.dark .pagination-bar {
  border-top-color: rgba(48, 54, 61, 0.3);
}

.dark .pagination-bar :deep(.el-pagination button),
.dark .pagination-bar :deep(.el-pager li) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
  color: #8b949e;
}

.dark .pagination-bar :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #0984e3, #74b9ff);
  color: white;
}

.dark .action-btn {
  background: rgba(13, 17, 23, 0.9);
  color: #8b949e;
  border-color: transparent;
}

.dark .action-btn:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.dark .action-btn.view:hover {
  background: rgba(88, 166, 255, 0.15);
  border-color: rgba(88, 166, 255, 0.3);
  color: #58a6ff;
}

.dark .action-btn.backup:hover {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.3);
  color: #3fb950;
}

.dark .action-btn.edit:hover {
  background: rgba(210, 153, 34, 0.15);
  border-color: rgba(210, 153, 34, 0.3);
  color: #d29922;
}

.dark .action-btn.delete:hover {
  background: rgba(248, 81, 73, 0.15);
  border-color: rgba(248, 81, 73, 0.3);
  color: #f85149;
}

.dark .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .form-section-title {
  color: #8b949e;
}
</style>