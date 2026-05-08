<template>
  <div class="devices-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('deviceList') }}</span>
          <div class="actions">
            <el-checkbox v-model="selectMode" style="margin-right: 10px">{{ t('deviceBatchSelect') }}</el-checkbox>
            <el-button type="success" @click="batchBackup" :disabled="selectedDevices.length === 0">
              <el-icon><Download /></el-icon>
              {{ t('deviceBatchBackup') }} ({{ selectedDevices.length }})
            </el-button>
            <el-button type="primary" @click="showAddDialog = true">
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
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          :placeholder="t('deviceSearchPlaceholder')"
          style="width: 250px"
          clearable
        />
        <el-select v-model="filterStatus" :placeholder="t('deviceFilterStatus')" clearable style="width: 120px">
          <el-option :label="t('statusOnline')" value="online" />
          <el-option :label="t('statusOffline')" value="offline" />
          <el-option :label="t('statusMaintenance')" value="maintenance" />
          <el-option :label="t('statusRetired')" value="retired" />
        </el-select>
        <el-select v-model="filterRole" :placeholder="t('deviceFilterRole')" clearable style="width: 120px">
          <el-option :label="t('deviceRoleAccess')" value="access" />
          <el-option :label="t('deviceRoleDistribution')" value="distribution" />
          <el-option :label="t('deviceRoleCore')" value="core" />
        </el-select>
      </div>

      <!-- 设备表格 -->
      <el-table
        :data="filteredDevices"
        style="width: 100%"
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column v-if="selectMode" type="selection" width="55" />
        <el-table-column prop="name" :label="t('deviceName')" width="180" />
        <el-table-column prop="ip" :label="t('deviceIp')" width="140" />
        <el-table-column prop="model" :label="t('deviceModel')" width="200" />
        <el-table-column prop="serial_number" :label="t('deviceSerialNumber')" width="160" />
        <el-table-column prop="location" :label="t('deviceLocation')" />
        <el-table-column prop="credential_group" :label="t('deviceCredentialGroup')" width="120" />
        <el-table-column prop="status" :label="t('deviceStatus')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
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
            <div class="table-actions">
              <el-button type="primary" size="small" @click="viewDevice(row.id)">{{ t('deviceDetail') }}</el-button>
              <el-button type="success" size="small" @click="backupDevice(row)">{{ t('deviceBackup') }}</el-button>
              <el-button type="warning" size="small" @click="editDevice(row)">{{ t('deviceEdit') }}</el-button>
              <el-button type="danger" size="small" @click="deleteDevice(row)">{{ t('deviceDelete') }}</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoDevices')" :image-size="80">
            <el-button type="primary" size="small" @click="showAddDialog = true">{{ t('deviceAdd') }}</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          :total="total"
          @size-change="loadDevices"
          @current-change="loadDevices"
        />
      </div>
    </el-card>

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
import { Download, Plus, Upload, UploadFilled } from '@element-plus/icons-vue'
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

const filteredDevices = computed(() => {
  return devices.value.filter(d => {
    const matchSearch = !searchText.value ||
      d.name.toLowerCase().includes(searchText.value.toLowerCase()) ||
      d.ip?.includes(searchText.value)

    const matchStatus = !filterStatus.value || d.status === filterStatus.value
    const matchRole = !filterRole.value || d.role === filterRole.value

    return matchSearch && matchStatus && matchRole
  })
})

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
    const params = { status: filterStatus.value || undefined, role: filterRole.value || undefined, skip: (currentPage.value - 1) * pageSize.value, limit: pageSize.value }
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
    // 只传递需要更新的字段
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
}

.filter-bar {
  display: flex;
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
  flex-wrap: wrap;
}

.filter-bar .el-input {
  width: 250px;
}

.filter-bar .el-select {
  width: 120px;
}
</style>
