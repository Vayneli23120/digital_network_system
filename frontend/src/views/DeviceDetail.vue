<template>
  <div class="device-detail-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">{{ device?.name || t('deviceDetail') }}</h1>
        <el-tag v-if="device" :type="getStatusType(device.status)" size="large">
          {{ getStatusText(device.status) }}
        </el-tag>
      </div>
      <div class="page-actions">
        <el-button type="success" @click="backupNow">
          <el-icon><Download /></el-icon>
          {{ t('deviceBackupNow') }}
        </el-button>
        <el-button type="warning" @click="openConsoleDeploy">
          <el-icon><Connection /></el-icon>
          Console
        </el-button>
        <el-button type="primary" @click="showEditDialog = true">{{ t('deviceEdit') }}</el-button>
      </div>
    </div>

    <!-- 主体：左右布局 -->
    <div class="detail-header">
      <!-- 左侧：主信息卡片 -->
      <div class="detail-main-card" v-loading="loading">
        <div class="detail-title">{{ t('deviceInfo') }}</div>
        <div class="detail-meta" v-if="device">
          <span>IP: {{ device.ip || 'N/A' }}</span>
          <span>型号: {{ device.model || 'N/A' }}</span>
          <span>位置: {{ device.location || 'N/A' }}</span>
          <el-tag :type="getVendorTagType(device.vendor)" size="small">{{ getVendorText(device.vendor) }}</el-tag>
        </div>

        <!-- 信息列表 -->
        <div class="info-list" v-if="device">
          <div class="info-item">
            <span class="info-label">{{ t('deviceSerialNumber') }}</span>
            <span class="info-value">{{ device.serial_number || 'N/A' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('deviceRole') }}</span>
            <span class="info-value">{{ getRoleText(device.role) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('deviceCredentialGroup') }}</span>
            <span class="info-value">{{ device.credential_group || 'default' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('devicePurchaseDate') }}</span>
            <span class="info-value">{{ device.purchase_date ? formatDate(device.purchase_date) : 'N/A' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('deviceLifeSpan') }}</span>
            <span class="info-value">{{ calculateLifeSpan() }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('devicePurchaseCost') }}</span>
            <span class="info-value">{{ device.purchase_cost ? '¥' + device.purchase_cost.toLocaleString() : 'N/A' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('deviceLastBackup') }}</span>
            <span class="info-value">{{ device.last_backup_time ? formatDateTime(device.last_backup_time) : t('deviceNeverBackup') }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('deviceSupplier') }}</span>
            <span class="info-value">{{ device.vendor || 'N/A' }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧：快速操作卡片 -->
      <div class="detail-side-card">
        <div class="card-title">{{ t('deviceQuickActions') }}</div>
        <div class="action-list">
          <el-button type="primary" class="action-btn" @click="backupNow">{{ t('deviceBackupNow') }}</el-button>
          <el-button type="default" class="action-btn" @click="viewLatestConfig">{{ t('backupViewConfig') }}</el-button>
          <el-button type="default" class="action-btn" @click="openConsoleDeploy">Console {{ t('deviceConsoleDeploy') }}</el-button>
          <el-button type="default" class="action-btn" @click="testConnection">{{ t('deviceConnectTest') }}</el-button>
          <el-button type="default" class="action-btn" @click="openMaintDialog">{{ t('maintAddRecord') }}</el-button>
          <el-button type="danger" class="action-btn" @click="confirmDeleteDevice" v-if="device">{{ t('deviceDelete') }}</el-button>
        </div>
      </div>
    </div>

    <!-- Tabs 区域 -->
    <div class="tabs-wrapper">
      <el-tabs v-model="activeTab">
        <el-tab-pane :label="t('tabBackupRecords')" name="backups">
          <el-table :data="device?.recent_backups || []" style="width: 100%">
            <el-table-column prop="backup_time" :label="t('backupTime')" width="180">
              <template #default="{ row }">{{ formatDateTime(row.backup_time) }}</template>
            </el-table-column>
            <el-table-column prop="has_change" :label="t('backupConfigChange')" width="100">
              <template #default="{ row }">
                <el-tag :type="row.has_change ? 'warning' : 'success'" size="small">
                  {{ row.has_change ? t('dashModified') : t('dashClean') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="triggered_by" :label="t('backupTriggeredBy')" width="100">
              <template #default="{ row }">{{ row.triggered_by || 'Auto' }}</template>
            </el-table-column>
            <el-table-column :label="t('deviceAction')" width="150">
              <template #default="{ row }">
                <el-button type="primary" link @click="viewConfig(row.id)">{{ t('backupViewConfig') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="t('tabFaultRecords')" name="faults">
          <el-table :data="device?.recent_faults || []" style="width: 100%">
            <el-table-column prop="fault_no" :label="t('faultNo')" width="180">
              <template #default="{ row }">
                <router-link :to="`/faults/${row.id}`" class="fault-link">{{ row.fault_no }}</router-link>
              </template>
            </el-table-column>
            <el-table-column prop="severity" :label="t('faultLevel')" width="80">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)" size="small">{{ getSeverityText(row.severity) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" :label="t('faultStatus')" width="80">
              <template #default="{ row }">
                <el-tag :type="getFaultStatusType(row.status)" size="small">{{ getFaultStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" :label="t('faultOccurTime')" width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column :label="t('deviceAction')" width="150" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="editFaultInDetail(row)">{{ t('deviceEdit') }}</el-button>
                <el-button v-if="row.status !== 'closed'" size="small" type="success" @click="closeFaultInDetail(row)">{{ t('faultClose') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" size="small" style="margin-top: 10px" @click="openFaultDialog">{{ t('faultAddRecord') }}</el-button>
        </el-tab-pane>

        <el-tab-pane :label="t('tabMaintenanceRecords')" name="maintenance">
          <el-table :data="device?.recent_maintenances || []" style="width: 100%">
            <el-table-column prop="maint_no" :label="t('maintNo')" width="180">
              <template #default="{ row }">
                <router-link :to="`/maintenance/${row.id}`" class="maint-link">{{ row.maint_no }}</router-link>
              </template>
            </el-table-column>
            <el-table-column prop="maint_type" :label="t('maintType')" width="100">
              <template #default="{ row }">
                <el-tag :type="getMaintTypeType(row.maint_type)" size="small">{{ getMaintTypeText(row.maint_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="maint_time" :label="t('maintTime')" width="160">
              <template #default="{ row }">{{ formatDateTime(row.maint_time || row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="description" :label="t('maintDescription')" min-width="200" />
            <el-table-column :label="t('deviceAction')" width="150" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="editMaintInDetail(row)">{{ t('deviceEdit') }}</el-button>
                <el-button type="danger" size="small" @click="deleteMaintInDetail(row.id)">{{ t('deviceDelete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" size="small" style="margin-top: 10px" @click="openMaintDialog">{{ t('maintAddRecord') }}</el-button>
        </el-tab-pane>

        <el-tab-pane :label="t('tabDeviceInventory')" name="inventory">
          <div v-if="deviceInventory.length > 0" class="compact-header">
            <span>{{ t('inventoryInstalledParts') }}: <strong class="text-success">{{ deviceInventory.length }}</strong> {{ t('inventoryParts') }}</span>
            <span>{{ t('inventoryTotalValue') }}: <strong class="text-success">¥{{ inventoryTotalValue.toFixed(2) }}</strong></span>
          </div>
          <el-table :data="deviceInventory" v-loading="inventoryLoading" stripe border size="small" style="margin-top: 8px">
            <el-table-column prop="serial_number" :label="t('spareSerialNumber')" width="120">
              <template #default="{ row }"><span class="text-primary">{{ row.serial_number || '-' }}</span></template>
            </el-table-column>
            <el-table-column prop="part_number" :label="t('sparePartNumber')" width="120" />
            <el-table-column prop="part_name" :label="t('spareName')" width="150" />
            <el-table-column prop="category" :label="t('spareCategory')" width="80" />
            <el-table-column prop="unit_price" :label="t('spareUnitPrice')" width="80">
              <template #default="{ row }"><span class="text-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span></template>
            </el-table-column>
            <el-table-column prop="installed_at" :label="t('inventoryInstalledAt')" width="160">
              <template #default="{ row }">{{ formatDateTime(row.installed_at) }}</template>
            </el-table-column>
            <el-table-column prop="installed_by" :label="t('inventoryInstalledBy')" width="80" />
          </el-table>
          <el-empty v-if="deviceInventory.length === 0 && !inventoryLoading" :description="t('inventoryNoParts')" :image-size="60" />
        </el-tab-pane>

        <el-tab-pane :label="t('tabCostStats')" name="costs">
          <div class="cost-summary">
            <el-statistic :title="t('purchaseCost')" :value="device?.purchase_cost || 0" prefix="¥" />
            <el-statistic :title="t('maintCost')" :value="calculateMaintCost()" :precision="2" prefix="¥" />
            <el-statistic :title="t('maintTotalCost')" :value="(device?.purchase_cost || 0) + calculateMaintCost()" :precision="2" prefix="¥" />
          </div>
        </el-tab-pane>

        <el-tab-pane :label="t('devicePhotos')" name="photos">
          <div class="photo-toolbar">
            <el-upload
              :action="uploadUrl"
              :headers="uploadHeaders"
              :data="{ photo_type: 'other' }"
              :on-success="handlePhotoUploadSuccess"
              :on-error="handlePhotoUploadError"
              show-upload
            >
              <el-button type="primary" size="small">
                <el-icon><Upload /></el-icon>
                {{ t('deviceUploadPhoto') }}
              </el-button>
            </el-upload>
          </div>
          <div v-if="device?.photos?.length" class="photo-grid">
            <div v-for="photo in device.photos" :key="photo.id" class="photo-item">
              <el-image :src="`/assets${photo.photo_path}`" fit="cover" :preview-src-list="[`/assets${photo.photo_path}`]" class="photo-image">
                <template #error>
                  <div class="image-error"><el-icon><Picture /></el-icon></div>
                </template>
              </el-image>
              <div class="photo-actions">
                <span class="photo-type">{{ getPhotoTypeText(photo.photo_type) }}</span>
                <el-button type="danger" size="small" @click="deletePhoto(photo.id)">{{ t('deviceDelete') }}</el-button>
              </div>
            </div>
          </div>
          <el-empty v-else :description="t('deviceNoPhotos')" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 编辑设备对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('editDeviceTitle')" width="600px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item :label="t('deviceName')"><el-input v-model="editForm.name" :disabled="true" /></el-form-item>
        <el-form-item :label="t('deviceIp')"><el-input v-model="editForm.ip" /></el-form-item>
        <el-form-item :label="t('deviceModel')"><el-input v-model="editForm.model" /></el-form-item>
        <el-form-item :label="t('deviceSerialNumber')"><el-input v-model="editForm.serial_number" /></el-form-item>
        <el-form-item :label="t('deviceLocation')"><el-input v-model="editForm.location" /></el-form-item>
        <el-form-item :label="t('deviceRole')">
          <el-select v-model="editForm.role">
            <el-option :label="t('deviceRoleAccess')" value="access" />
            <el-option :label="t('deviceRoleDistribution')" value="distribution" />
            <el-option :label="t('deviceRoleCore')" value="core" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('deviceStatus')">
          <el-select v-model="editForm.status">
            <el-option :label="t('statusOnline')" value="online" />
            <el-option :label="t('statusOffline')" value="offline" />
            <el-option :label="t('statusMaintenance')" value="maintenance" />
            <el-option :label="t('statusRetired')" value="retired" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="updateDevice">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 查看配置对话框 -->
    <el-dialog v-model="showConfigDialog" :title="t('backupConfigContent')" width="800px">
      <el-card v-if="configContent"><pre class="config-content">{{ configContent }}</pre></el-card>
      <el-empty v-else :description="t('backupNoConfig')" />
    </el-dialog>

    <!-- 添加故障记录对话框 -->
    <el-dialog v-model="showFaultDialog" :title="editMode ? t('faultEditRecord') : t('faultAddRecord')" width="500px">
      <el-form :model="faultForm" label-width="100px">
        <el-form-item :label="t('faultSeverity')" required>
          <el-select v-model="faultForm.severity">
            <el-option :label="t('faultSeverityCritical')" value="critical" />
            <el-option :label="t('faultSeverityMajor')" value="major" />
            <el-option :label="t('faultSeverityMinor')" value="minor" />
            <el-option :label="t('faultSeverityWarning')" value="warning" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('faultDowntimeMinutes')"><el-input-number v-model="faultForm.downtime_minutes" :min="0" /></el-form-item>
        <el-form-item :label="t('faultDescription')" required><el-input v-model="faultForm.description" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFaultDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateFaultInDetail() : addFault()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 添加维修记录对话框 -->
    <el-dialog v-model="showMaintDialog" :title="editMode ? t('maintEditRecord') : t('maintAddRecord')" width="600px">
      <el-form :model="maintForm" label-width="120px">
        <el-form-item :label="t('maintType')" required>
          <el-select v-model="maintForm.maint_type">
            <el-option :label="t('maintTypePreventiveFull')" value="preventive" />
            <el-option :label="t('maintTypeCorrectiveFull')" value="corrective" />
            <el-option :label="t('maintTypeUpgradeFull')" value="upgrade" />
            <el-option :label="t('maintTypeEmergencyFull')" value="emergency" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('maintReplaceParts')"><el-input v-model="maintForm.parts_replaced" type="textarea" :rows="2" /></el-form-item>
        <el-form-item :label="t('maintPartsCost')"><el-input-number v-model="maintForm.parts_cost" :min="0" :precision="2" /></el-form-item>
        <el-form-item :label="t('maintLaborHours')"><el-input-number v-model="maintForm.labor_hours" :min="0" :precision="1" /></el-form-item>
        <el-form-item :label="t('maintLaborCost')"><el-input-number v-model="maintForm.labor_cost" :min="0" :precision="2" /></el-form-item>
        <el-form-item :label="t('maintVendor')"><el-input v-model="maintForm.vendor" /></el-form-item>
        <el-form-item :label="t('maintDescription')" required><el-input v-model="maintForm.description" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMaintDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateMaintInDetail() : addMaintenance()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Download, Upload, Picture } from '@element-plus/icons-vue'
import { getDeviceDetail, createFault, createMaintenance, updateMaintenance, deleteMaintenance, updateFault, updateDevice as updateDeviceApi, getDeviceInventory, deleteDevice } from '@/api'
import { formatDateTime, formatDate } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const device = ref(null)
const loading = ref(false)
const activeTab = ref('backups')
const showFaultDialog = ref(false)
const showMaintDialog = ref(false)
const showEditDialog = ref(false)
const showConfigDialog = ref(false)
const editMode = ref(false)
const configContent = ref('')

// 设备资产
const deviceInventory = ref([])
const inventoryLoading = ref(false)
const inventoryTotalValue = computed(() => deviceInventory.value.reduce((sum, item) => sum + (item.unit_price || 0), 0))

const faultForm = ref({ severity: 'major', downtime_minutes: 0, description: '' })
const maintForm = ref({ maint_type: 'corrective', parts_replaced: '', parts_cost: 0, labor_hours: 0, labor_cost: 0, vendor: '', description: '' })
const editForm = ref({})

const uploadUrl = computed(() => `/api/devices/${route.params.id}/photos`)
const uploadHeaders = computed(() => ({}))

const getStatusType = (status) => ({ online: 'success', offline: 'danger', maintenance: 'warning', retired: 'info' }[status] || 'info')
const getStatusText = (status) => ({ online: t('statusOnline'), offline: t('statusOffline'), maintenance: t('statusMaintenance'), retired: t('statusRetired') }[status] || status)
const getFaultStatusType = (status) => ({ open: 'info', investigating: 'warning', resolved: 'success', closed: 'info' }[status] || 'info')
const getFaultStatusText = (status) => ({ open: t('faultStatusOpen'), investigating: t('faultStatusInvestigating'), resolved: t('faultStatusResolved'), closed: t('faultStatusClosed') }[status] || status)
const getRoleText = (role) => ({ access: t('deviceRoleAccess'), distribution: t('deviceRoleDistribution'), core: t('deviceRoleCore') }[role] || role)
const getVendorText = (vendor) => ({ cisco: 'Cisco', huawei: t('vendorHuawei'), '华为': t('vendorHuawei'), h3c: 'H3C', juniper: 'Juniper' }[vendor?.toLowerCase()] || vendor || 'Cisco')
const getVendorTagType = (vendor) => ({ cisco: '', huawei: 'success', h3c: 'warning', juniper: 'danger' }[vendor?.toLowerCase()] || '')
const getSeverityType = (severity) => ({ critical: 'danger', major: 'warning', minor: '', warning: 'info' }[severity] || 'info')
const getSeverityText = (severity) => ({ critical: t('dashCritical'), major: t('dashMajor'), minor: t('dashMinor'), warning: t('dashWarning') }[severity] || severity)
const getPhotoTypeText = (type) => ({ front: t('devicePhotoFront'), back: t('devicePhotoBack'), label: t('devicePhotoLabel'), rack: t('devicePhotoRack'), other: t('devicePhotoOther') }[type] || type)
const getMaintTypeText = (type) => ({ preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }[type] || type)
const getMaintTypeType = (type) => ({ preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }[type] || '')

const calculateLifeSpan = () => {
  if (!device.value?.purchase_date) return 'N/A'
  const purchase = new Date(device.value.purchase_date)
  const now = new Date()
  const years = Math.floor((now - purchase) / (365 * 24 * 60 * 60 * 1000))
  const months = Math.floor(((now - purchase) % (365 * 24 * 60 * 60 * 1000)) / (30 * 24 * 60 * 60 * 1000))
  return `${years}年 ${months}月`
}

const calculateMaintCost = () => {
  if (!device.value?.recent_maintenances) return 0
  return device.value.recent_maintenances.reduce((sum, m) => sum + (parseFloat(m.parts_cost) || 0) + (parseFloat(m.labor_cost) || 0), 0)
}

const loadDevice = async () => {
  loading.value = true
  try {
    const data = await getDeviceDetail(route.params.id)
    device.value = data
    editForm.value = { ...data }
  } catch (error) {
    ElMessage.error(t('msgDeviceDetailFailed'))
  } finally {
    loading.value = false
  }
}

const loadDeviceInventory = async () => {
  if (!route.params.id) return
  inventoryLoading.value = true
  try {
    const data = await getDeviceInventory(route.params.id)
    deviceInventory.value = data.items || []
  } catch (error) {
    ElMessage.error(t('msgDeviceInventoryFailed'))
  } finally {
    inventoryLoading.value = false
  }
}

watch(activeTab, (newTab) => { if (newTab === 'inventory') loadDeviceInventory() })

const testConnection = async () => { ElMessage.info(t('msgTestWaitApi')) }
const backupNow = async () => {
  try {
    const { backupDevice } = await import('@/api')
    await backupDevice(route.params.id, 'Web')
    ElMessage.success(t('msgBackupSuccessShort'))
    loadDevice()
  } catch (error) { ElMessage.error(t('msgBackupFailed')) }
}
const openConsoleDeploy = () => { ElMessage.info(t('msgConsoleDev')) }
const viewLatestConfig = async () => {
  if (!device.value?.recent_backups?.length) { ElMessage.warning(t('backupNoConfig')); return }
  viewConfig(device.value.recent_backups[0].id)
}
const viewConfig = async (backupId) => {
  try {
    const { getBackupContent } = await import('@/api')
    const data = await getBackupContent(backupId)
    configContent.value = data.content
    showConfigDialog.value = true
  } catch (error) { ElMessage.error(t('msgConfigLoadFailed')) }
}

const handlePhotoUploadSuccess = () => { ElMessage.success(t('msgPhotoUploadSuccess')); loadDevice() }
const handlePhotoUploadError = () => { ElMessage.error(t('msgPhotoUploadFailed')) }
const deletePhoto = async (photoId) => {
  try {
    await ElMessageBox.confirm(t('confirmDeletePhoto'), t('msgConfirmDelete'), { type: 'warning' })
    const api = await import('@/api')
    await api.deletePhoto(route.params.id, photoId)
    ElMessage.success(t('msgPhotoDeleteSuccess'))
    loadDevice()
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('msgPhotoDeleteFailed')) }
}

const updateDevice = async () => {
  try {
    await updateDeviceApi(route.params.id, editForm.value)
    ElMessage.success(t('msgDeviceUpdateSuccess'))
    showEditDialog.value = false
    loadDevice()
  } catch (error) { ElMessage.error(t('msgDeviceUpdateFailed')) }
}

const confirmDeleteDevice = async () => {
  try {
    await ElMessageBox.confirm(t('confirmDeleteDevice'), t('msgConfirmDelete'), { type: 'warning' })
    await deleteDevice(route.params.id)
    ElMessage.success(t('msgDeviceDeleteSuccess'))
    router.push('/devices')
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('msgDeviceDeleteFailed')) }
}

const openFaultDialog = () => { editMode.value = false; faultForm.value = { severity: 'major', downtime_minutes: 0, description: '' }; showFaultDialog.value = true }
const addFault = async () => {
  try {
    await createFault({ device_id: device.value.id, device_name: device.value.name, ...faultForm.value, status: 'open' })
    ElMessage.success(t('msgFaultAddSuccess'))
    showFaultDialog.value = false
    loadDevice()
  } catch (error) { ElMessage.error(t('msgFaultAddFailed')) }
}
const editFaultInDetail = (row) => {
  editMode.value = true
  faultForm.value = { id: row.id, severity: row.severity, downtime_minutes: row.downtime_minutes || 0, description: row.description }
  showFaultDialog.value = true
}
const updateFaultInDetail = async () => {
  try {
    await updateFault(faultForm.value.id, faultForm.value)
    ElMessage.success(t('msgFaultUpdateSuccess'))
    showFaultDialog.value = false
    editMode.value = false
    loadDevice()
  } catch (error) { ElMessage.error(t('msgFaultUpdateFailed')) }
}
const closeFaultInDetail = async (row) => {
  try {
    await ElMessageBox.confirm(t('faultCloseConfirm', { id: row.fault_no }), t('faultCloseTitle'), { type: 'warning' })
    await updateFault(row.id, { status: 'closed' })
    ElMessage.success(t('msgFaultCloseSuccess'))
    loadDevice()
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('msgFaultCloseFailed')) }
}

const openMaintDialog = () => { editMode.value = false; maintForm.value = { maint_type: 'corrective', parts_replaced: '', parts_cost: 0, labor_hours: 0, labor_cost: 0, vendor: '', description: '' }; showMaintDialog.value = true }
const addMaintenance = async () => {
  try {
    await createMaintenance({ device_id: device.value.id, device_name: device.value.name, ...maintForm.value })
    ElMessage.success(t('msgMaintAddSuccess'))
    showMaintDialog.value = false
    loadDevice()
  } catch (error) { ElMessage.error(t('msgMaintAddFailed')) }
}
const editMaintInDetail = (row) => {
  editMode.value = true
  maintForm.value = { id: row.id, maint_type: row.maint_type, parts_replaced: row.parts_replaced || '', parts_cost: row.parts_cost || 0, labor_hours: row.labor_hours || 0, labor_cost: row.labor_cost || 0, vendor: row.vendor || '', description: row.description }
  showMaintDialog.value = true
}
const updateMaintInDetail = async () => {
  try {
    await updateMaintenance(maintForm.value.id, maintForm.value)
    ElMessage.success(t('msgMaintUpdateSuccess'))
    showMaintDialog.value = false
    editMode.value = false
    loadDevice()
  } catch (error) { ElMessage.error(t('msgMaintUpdateFailed')) }
}
const deleteMaintInDetail = async (maintId) => {
  try {
    await ElMessageBox.confirm(t('confirmDeleteMaint'), t('msgConfirmDelete'), { type: 'warning' })
    await deleteMaintenance(maintId)
    ElMessage.success(t('msgMaintDeleteSuccess'))
    loadDevice()
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('msgMaintDeleteFailed')) }
}

onMounted(() => { loadDevice() })
</script>

<style scoped>
.device-detail-page {
  max-width: 1400px;
  margin: 0 auto;
}

/* 页面头部 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-default);
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-actions {
  display: flex;
  gap: 8px;
}

/* 主体布局 */
.detail-header {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
}

.detail-main-card {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 24px;
  box-shadow: var(--shadow-card);
}

.detail-side-card {
  width: 300px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-card);
}

.detail-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.detail-meta {
  display: flex;
  gap: 16px;
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

/* 信息列表 */
.info-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.info-item {
  display: flex;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.info-label {
  width: 100px;
  font-size: 13px;
  color: var(--text-muted);
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
  font-weight: 500;
}

/* 操作列表 */
.action-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  width: 100%;
  justify-content: center;
}

/* Tabs */
.tabs-wrapper {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-card);
}

/* 配置内容 */
.config-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  max-height: 500px;
  overflow-y: auto;
}

/* 链接 */
.fault-link, .maint-link {
  color: var(--accent-secondary);
  text-decoration: none;
  font-weight: 500;
}
.fault-link:hover, .maint-link:hover { text-decoration: underline; }

/* 成本统计 */
.cost-summary {
  display: flex;
  justify-content: space-around;
  padding: 20px;
}

/* 照片网格 */
.photo-toolbar { margin-bottom: 16px; }
.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
}
.photo-item { position: relative; border-radius: 4px; overflow: hidden; }
.photo-image { width: 100%; height: 120px; }
.photo-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: var(--bg-tertiary);
}
.photo-type { font-size: 12px; color: var(--text-secondary); }
.image-error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

/* 紧凑头部 */
.compact-header {
  display: flex;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  font-size: 13px;
}
.text-primary { color: var(--accent-secondary); font-weight: 500; }
.text-success { color: var(--accent-success); font-weight: 600; }

/* 响应式 */
@media (max-width: 1024px) {
  .detail-header { flex-direction: column; }
  .detail-side-card { width: 100%; }
  .info-list { grid-template-columns: 1fr; }
}

@media (max-width: 768px) {
  .page-header { flex-direction: column; gap: 12px; align-items: flex-start; }
  .page-actions { width: 100%; flex-wrap: wrap; }
}
</style>