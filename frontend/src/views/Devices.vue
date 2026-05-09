<template>
  <div class="devices-page">
    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-header">
        <span class="stats-title">{{ t('deviceStatsTitle') }}</span>
        <button class="refresh-btn" @click="loadDevices" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
      <div class="stats-grid">
        <!-- 总设备 -->
        <div class="stat-card total" @click="filterByStatus('')">
          <div class="card-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.total }}</div>
            <div class="metric-label">{{ t('deviceStatsTotal') }}</div>
          </div>
        </div>
        <!-- 在线设备 -->
        <div class="stat-card online" @click="filterByStatus('online')">
          <div class="card-icon">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.online }}</div>
            <div class="metric-label">{{ t('deviceStatsOnline') }}</div>
          </div>
        </div>
        <!-- 离线设备 -->
        <div class="stat-card offline" @click="filterByStatus('offline')">
          <div class="card-icon">
            <el-icon><CircleClose /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value danger">{{ stats.offline }}</div>
            <div class="metric-label">{{ t('deviceStatsOffline') }}</div>
          </div>
        </div>
        <!-- 维护中 -->
        <div class="stat-card maintenance" @click="filterByStatus('maintenance')">
          <div class="card-icon">
            <el-icon><Setting /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.maintenance }}</div>
            <div class="metric-label">{{ t('deviceStatsMaintenance') }}</div>
          </div>
        </div>
        <!-- 已退役 -->
        <div class="stat-card retired" @click="filterByStatus('retired')">
          <div class="card-icon">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.retired }}</div>
            <div class="metric-label">{{ t('deviceStatsRetired') }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- 高级筛选工具栏 -->
    <section class="filter-section">
      <div class="filter-toolbar">
        <!-- 搜索框 -->
        <el-input
          v-model="searchText"
          :placeholder="t('deviceSearchPlaceholder')"
          class="search-input"
          clearable
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <el-tag
            :class="['status-chip', { active: filterStatus === '' }]"
            @click="filterByStatus('')"
          >{{ t('deviceFilterAll') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-online', { active: filterStatus === 'online' }]"
            @click="filterByStatus('online')"
          >{{ t('statusOnline') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-offline', { active: filterStatus === 'offline' }]"
            type="danger"
            @click="filterByStatus('offline')"
          >{{ t('statusOffline') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-maintenance', { active: filterStatus === 'maintenance' }]"
            @click="filterByStatus('maintenance')"
          >{{ t('statusMaintenance') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-retired', { active: filterStatus === 'retired' }]"
            @click="filterByStatus('retired')"
          >{{ t('statusRetired') }}</el-tag>
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

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button type="primary" class="add-btn" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            {{ t('deviceAdd') }}
          </el-button>
          <el-dropdown split-button @click="exportDevices">
            <el-icon><Upload /></el-icon>
            {{ t('actionExport') }}
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="exportDevices">{{ t('deviceExcelExport') }}</el-dropdown-item>
                <el-dropdown-item @click="showImportDialog = true">{{ t('deviceExcelImport') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </section>

    <!-- 设备数据面板 -->
    <section class="data-section">
      <el-table
        :data="filteredDevices"
        class="modern-table"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        :row-class-name="tableRowClassName"
      >
        <el-table-column v-if="selectMode" type="selection" width="55" />
        <el-table-column prop="name" :label="t('deviceName')" width="180">
          <template #default="{ row }">
            <router-link :to="`/devices/${row.id}`" class="device-name-link">
              <span class="device-name-text">{{ row.name }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="ip" :label="t('deviceIp')" width="140" />
        <el-table-column prop="model" :label="t('deviceModel')" width="200" />
        <el-table-column prop="serial_number" :label="t('deviceSerialNumber')" width="160" />
        <el-table-column prop="location" :label="t('deviceLocation')" />
        <el-table-column prop="credential_group" :label="t('deviceCredentialGroup')" width="120" />
        <el-table-column prop="status" :label="t('deviceStatus')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small" class="status-tag">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vendor" :label="t('deviceVendor')" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.vendor || 'Cisco' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="role" :label="t('deviceRole')" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)" size="small">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('deviceAction')" width="280" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-icons">
              <el-tooltip content="详情" placement="top">
                <el-button type="primary" link @click="viewDevice(row.id)" class="action-icon">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="备份" placement="top">
                <el-button type="success" link @click="backupDevice(row)" class="action-icon">
                  <el-icon><Download /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="编辑" placement="top">
                <el-button type="warning" link @click="editDevice(row)" class="action-icon">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button type="danger" link @click="deleteDevice(row)" class="action-icon">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
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
    <el-dialog v-model="showAddDialog" :title="editMode ? t('editDeviceTitle') : t('addDeviceTitle')" width="600px">
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
import { Download, Plus, Upload, UploadFilled, Monitor, CircleCheck, CircleClose, Setting, WarningFilled, Refresh, Search, View, Edit, Delete, ArrowRight } from '@element-plus/icons-vue'
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
.devices-page {
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 统计 Dashboard ===== */
.stats-dashboard {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.stats-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stats-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.refresh-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.2s;
}

.stat-card:hover {
  background: var(--bg-hover);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 48, 135, 0.08);
}

.card-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.stat-card.total .card-icon {
  background: rgba(9, 132, 227, 0.15);
  color: #0984e3;
}

.stat-card.online .card-icon {
  background: rgba(0, 184, 148, 0.15);
  color: #00b894;
}

.stat-card.offline .card-icon {
  background: rgba(214, 48, 49, 0.15);
  color: #d63031;
}

.stat-card.maintenance .card-icon {
  background: rgba(225, 112, 85, 0.15);
  color: #e17055;
}

.stat-card.retired .card-icon {
  background: rgba(116, 185, 255, 0.15);
  color: #74b9ff;
}

.card-body {
  flex: 1;
}

.metric-value {
  font-family: 'JetBrains Mono', 'Geist Mono', monospace;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1;
}

.metric-value.danger {
  color: #d63031;
}

.metric-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

/* ===== 筛选工具栏 ===== */
.filter-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 12px 16px;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input {
  width: 220px;
}

.status-chips {
  display: flex;
  gap: 8px;
}

.status-chip {
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 6px;
}

.status-chip.active {
  box-shadow: 0 0 0 2px var(--accent-primary);
}

.status-chip.chip-online { background: rgba(0, 184, 148, 0.1); border-color: rgba(0, 184, 148, 0.3); color: #00b894; }
.status-chip.chip-offline { background: rgba(214, 48, 49, 0.1); border-color: rgba(214, 48, 49, 0.3); color: #d63031; }
.status-chip.chip-maintenance { background: rgba(225, 112, 85, 0.1); border-color: rgba(225, 112, 85, 0.3); color: #e17055; }
.status-chip.chip-retired { background: rgba(116, 185, 255, 0.1); border-color: rgba(116, 185, 255, 0.3); color: #74b9ff; }

.more-filters {
  display: flex;
  gap: 8px;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.add-btn {
  margin-left: auto;
}

/* ===== 数据面板 ===== */
.data-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

/* 现代化表格 */
.modern-table {
  width: 100%;
}

.modern-table :deep(.el-table__header-wrapper) {
  border-bottom: 2px solid var(--border-default);
}

.modern-table :deep(th.el-table__cell) {
  background: var(--bg-tertiary);
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.modern-table :deep(td.el-table__cell) {
  border-bottom: 1px solid var(--border-subtle);
}

.modern-table :deep(.el-table__row) {
  transition: all 0.2s;
}

.modern-table :deep(.el-table__row:hover > td) {
  background: var(--bg-hover) !important;
}

.modern-table :deep(.offline-row) {
  background: rgba(214, 48, 49, 0.05);
}

.modern-table :deep(.retired-row) {
  opacity: 0.6;
}

/* 设备名称链接 */
.device-name-link {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--accent-primary);
  text-decoration: none;
  font-weight: 500;
  font-size: 13px;
  transition: all 0.2s;
}

.device-name-link:hover {
  color: var(--accent-secondary);
}

.device-name-link:hover .link-arrow {
  opacity: 1;
  transform: translateX(4px);
}

.link-arrow {
  opacity: 0;
  transition: all 0.2s;
}

/* 状态标签 */
.status-tag {
  font-weight: 500;
}

/* 操作图标 */
.action-icons {
  display: flex;
  gap: 4px;
}

.action-icon {
  padding: 4px;
}

.action-icon:hover {
  background: var(--bg-tertiary);
  border-radius: 6px;
}

/* 分页 */
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
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
    flex-wrap: wrap;
  }

  .more-filters {
    flex-wrap: wrap;
  }

  .batch-actions {
    justify-content: flex-start;
  }

  .action-buttons {
    margin-left: 0;
    justify-content: flex-start;
  }
}

/* ===== 暗色模式 ===== */
.dark .stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 184, 148, 0.1);
}

.dark .stat-card.total .card-icon { background: rgba(9, 132, 227, 0.2); }
.dark .stat-card.online .card-icon { background: rgba(0, 184, 148, 0.2); }
.dark .stat-card.offline .card-icon { background: rgba(214, 48, 49, 0.2); }
.dark .stat-card.maintenance .card-icon { background: rgba(225, 112, 85, 0.2); }
.dark .stat-card.retired .card-icon { background: rgba(116, 185, 255, 0.2); }

.dark .status-chip.chip-online { background: rgba(0, 184, 148, 0.15); }
.dark .status-chip.chip-offline { background: rgba(214, 48, 49, 0.15); }
.dark .status-chip.chip-maintenance { background: rgba(225, 112, 85, 0.15); }
.dark .status-chip.chip-retired { background: rgba(116, 185, 255, 0.15); }

.dark .modern-table :deep(.offline-row) {
  background: rgba(214, 48, 49, 0.1);
}
</style>