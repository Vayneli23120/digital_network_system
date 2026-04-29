<template>
  <div class="devices-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>设备列表</span>
          <div class="actions">
            <el-checkbox v-model="selectMode" style="margin-right: 10px">批量选择</el-checkbox>
            <el-button type="success" @click="batchBackup" :disabled="selectedDevices.length === 0">
              <el-icon><Download /></el-icon>
              批量备份 ({{ selectedDevices.length }})
            </el-button>
            <el-button type="primary" @click="showAddDialog = true">
              <el-icon><Plus /></el-icon>
              添加设备
            </el-button>
            <el-dropdown split-button @click="exportDevices">
              <el-icon><Upload /></el-icon>
              导出
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="exportDevices">Excel 导出</el-dropdown-item>
                  <el-dropdown-item @click="showImportDialog = true">Excel 导入</el-dropdown-item>
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
          placeholder="搜索设备名称或 IP"
          style="width: 250px"
          clearable
        />
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px">
          <el-option label="在线" value="online" />
          <el-option label="离线" value="offline" />
          <el-option label="维护中" value="maintenance" />
          <el-option label="已退役" value="retired" />
        </el-select>
        <el-select v-model="filterRole" placeholder="角色" clearable style="width: 120px">
          <el-option label="接入层" value="access" />
          <el-option label="汇聚层" value="distribution" />
          <el-option label="核心层" value="core" />
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
        <el-table-column prop="name" label="设备名称" width="180" />
        <el-table-column prop="ip" label="IP 地址" width="140" />
        <el-table-column prop="model" label="型号" width="200" />
        <el-table-column prop="serial_number" label="序列号" width="160" />
        <el-table-column prop="location" label="位置" />
        <el-table-column prop="credential_group" label="账号组" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vendor" label="厂商" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.vendor || 'Cisco' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)" size="small">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button type="primary" size="small" @click="viewDevice(row.id)">详情</el-button>
              <el-button type="success" size="small" @click="backupDevice(row)">备份</el-button>
              <el-button type="warning" size="small" @click="editDevice(row)">编辑</el-button>
              <el-button type="danger" size="small" @click="deleteDevice(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
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
    <el-dialog v-model="showAddDialog" :title="editMode ? '编辑设备' : '添加设备'" width="600px">
      <el-form :model="newDevice" label-width="100px">
        <el-form-item label="设备名称" required>
          <el-input v-model="newDevice.name" placeholder="如 SW-ACCESS-01" :disabled="editMode" />
        </el-form-item>
        <el-form-item label="IP 地址" required>
          <el-input v-model="newDevice.ip" placeholder="192.168.x.x" />
        </el-form-item>
        <el-form-item label="设备型号">
          <el-input v-model="newDevice.model" placeholder="如 WS-C2960X-24TS-L" />
        </el-form-item>
        <el-form-item label="序列号">
          <el-input v-model="newDevice.serial_number" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="newDevice.location" placeholder="如 Building-A / Floor1 / Rack-03" />
        </el-form-item>
        <el-form-item label="厂商">
          <el-select v-model="newDevice.vendor">
            <el-option v-for="v in vendors" :key="v.key" :label="v.name" :value="v.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="newDevice.role">
            <el-option label="接入层" value="access" />
            <el-option label="汇聚层" value="distribution" />
            <el-option label="核心层" value="core" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="newDevice.status">
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="维护中" value="maintenance" />
            <el-option label="已退役" value="retired" />
          </el-select>
        </el-form-item>
        <el-form-item label="账号组">
          <el-select v-model="newDevice.credential_group" placeholder="选择 SSH 账号组">
            <el-option label="default" value="default" />
            <el-option v-for="cred in credentialGroups" :key="cred.id" :label="cred.name" :value="cred.name" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="editMode ? updateDevice() : addDevice()">确定</el-button>
      </template>
    </el-dialog>

    <!-- 导入设备对话框 -->
    <el-dialog v-model="showImportDialog" title="导入设备信息" width="600px">
      <el-alert
        title="导入说明"
        type="info"
        :closable="false"
        style="margin-bottom: 15px"
      >
        <p>请上传 Excel (.xlsx) 或 CSV 格式的设备文件，文件应包含以下列：</p>
        <ul style="margin: 10px 0; padding-left: 20px">
          <li>name (设备名称，必填)</li>
          <li>ip (IP 地址，必填)</li>
          <li>model (设备型号)</li>
          <li>serial_number (序列号)</li>
          <li>location (位置)</li>
          <li>role (角色：access/distribution/core)</li>
          <li>status (状态：online/offline/maintenance/retired)</li>
          <li>credential_group (账号组名称)</li>
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
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            只能上传 xlsx / csv 文件
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="importDevices" :disabled="!selectedFile">确定导入</el-button>
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
  const texts = { online: '在线', offline: '离线', maintenance: '维护中', retired: '已退役' }
  return texts[status] || status
}

const getRoleType = (role) => {
  const types = { access: '', distribution: 'warning', core: 'danger' }
  return types[role] || ''
}

const getRoleText = (role) => {
  const texts = { access: '接入层', distribution: '汇聚层', core: '核心层' }
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
    ElMessage.error('加载设备列表失败')
  } finally {
    loading.value = false
  }
}

const loadCredentialGroups = async () => {
  try {
    const data = await getCredentials()
    credentialGroups.value = data.items || data || []
  } catch (error) {
    ElMessage.error('加载账号组列表失败')
  }
}

const viewDevice = (id) => {
  router.push(`/devices/${id}`)
}

const backupDevice = async (row) => {
  try {
    await backupDeviceApi(row.id, 'Web')
    ElMessage.success(`设备 ${row.name} 备份成功`)
    loadDevices()
  } catch (error) {
    ElMessage.error('备份失败')
    ElMessage.error('备份失败')
  }
}

const batchBackup = async () => {
  if (selectedDevices.value.length === 0) return

  try {
    await ElMessageBox.confirm(`确定要备份选中的 ${selectedDevices.value.length} 台设备吗？`, '确认批量备份', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await batchBackupApi(selectedDevices.value, 'Web')
    ElMessage.success('批量备份完成')
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量备份失败')
      ElMessage.error('批量备份失败')
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
    ElMessage.success('设备更新成功')
    showAddDialog.value = false
    editMode.value = false
    loadDevices()
  } catch (error) {
    ElMessage.error('更新设备失败')
    ElMessage.error(error.response?.data?.detail || '更新设备失败')
  }
}

const deleteDevice = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除设备 "${row.name}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteDeviceApi(row.id)
    ElMessage.success('设备删除成功')
    loadDevices()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除设备失败')
      ElMessage.error('删除设备失败')
    }
  }
}

const addDevice = async () => {
  try {
    await createDevice(newDevice.value)
    ElMessage.success('设备添加成功')
    showAddDialog.value = false
    loadDevices()
  } catch (error) {
    ElMessage.error('添加设备失败')
    ElMessage.error('添加设备失败')
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
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
    ElMessage.error('导出失败')
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const importDevices = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择要导入的文件')
    return
  }

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    const result = await importDevicesApi(formData)
    ElMessage.success(`导入成功：${result.success}台设备，失败：${result.failed}台`)
    showImportDialog.value = false
    selectedFile.value = null
    loadDevices()
    loadCredentialGroups()
  } catch (error) {
    ElMessage.error('导入失败')
    ElMessage.error(error.response?.data?.detail || '导入失败')
  }
}

const loadVendors = async () => {
  try {
    const res = await getVendors()
    vendors.value = res.vendors || []
  } catch (e) {
    console.error('加载厂商列表失败', e)
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-buttons {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
  justify-content: center;
  align-items: center;
}

.action-buttons .el-button {
  padding: 5px 8px;
  font-size: 12px;
  min-width: auto;
}
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
@media (max-width: 768px) {
  .filter-bar { flex-wrap: wrap; }
  .filter-bar .el-input, .filter-bar .el-select { width: 100% !important; }
  .action-buttons .el-button { margin-bottom: 4px; }
}
</style>
