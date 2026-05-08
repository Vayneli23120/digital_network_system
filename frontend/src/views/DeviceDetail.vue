<template>
  <div class="device-detail">
    <el-row :gutter="20">
      <!-- 左侧：设备信息 -->
      <el-col :span="8">
        <el-card class="info-card" v-loading="loading">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>{{ t('deviceInfo') }}</span>
              <el-button type="primary" size="small" @click="testConnection" :disabled="!device">
                <el-icon><Connection /></el-icon> {{ t('deviceConnectTest') }}
              </el-button>
            </div>
          </template>

          <div v-if="device" class="device-info">
            <div class="device-avatar">
              <el-avatar :size="80" icon="Switch" />
              <h2>{{ device.name }}</h2>
              <el-tag :type="getStatusType(device.status)">
                {{ getStatusText(device.status) }}
              </el-tag>
              <el-tag v-if="device.vendor" type="info" size="small" style="margin-top: 8px">
                {{ getVendorText(device.vendor) }}
              </el-tag>
            </div>

            <el-descriptions :column="1" border>
              <el-descriptions-item :label="t('deviceVendor')">
                <el-tag size="small" :type="getVendorTagType(device.vendor)">{{ getVendorText(device.vendor) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item :label="t('deviceIp')">{{ device.ip || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item :label="t('deviceModel')">{{ device.model || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item :label="t('deviceSerialNumber')">{{ device.serial_number || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item :label="t('deviceLocation')">{{ device.location || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item :label="t('deviceRole')">{{ getRoleText(device.role) }}</el-descriptions-item>
              <el-descriptions-item :label="t('deviceSupplier')">{{ device.vendor || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item :label="t('devicePurchaseDate')">
                {{ device.purchase_date ? formatDate(device.purchase_date) : 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('devicePurchaseCost')">
                {{ device.purchase_cost ? '¥' + device.purchase_cost.toLocaleString() : 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('deviceLastBackup')">
                {{ device.last_backup_time ? formatDateTime(device.last_backup_time) : t('deviceNeverBackup') }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="actions">
              <el-button type="primary" @click="backupNow">
                <el-icon><Download /></el-icon>
                {{ t('deviceBackupNow') }}
              </el-button>
              <el-button type="warning" @click="openConsoleDeploy">
                <el-icon><Connection /></el-icon>
                {{ t('deviceConsoleDeploy') }}
              </el-button>
              <el-button type="success" @click="showEditDialog = true">{{ t('deviceEdit') }}</el-button>
            </div>
          </div>
        </el-card>

        <!-- 设备照片 -->
        <el-card class="photos-card" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>{{ t('devicePhotos') }}</span>
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
          </template>

          <div v-if="device?.photos?.length" class="photo-grid">
            <div v-for="photo in device.photos" :key="photo.id" class="photo-item">
              <el-image
                :src="`/assets${photo.photo_path}`"
                fit="cover"
                :preview-src-list="[`/assets${photo.photo_path}`]"
                class="photo-image"
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div class="photo-actions">
                <span class="photo-type">{{ getPhotoTypeText(photo.photo_type) }}</span>
                <el-button type="danger" size="small" @click="deletePhoto(photo.id)">{{ t('deviceDelete') }}</el-button>
              </div>
            </div>
          </div>
          <el-empty v-else :description="t('deviceNoPhotos')" />
        </el-card>
      </el-col>

      <!-- 右侧：记录标签页 -->
      <el-col :span="16">
        <el-card>
          <el-tabs v-model="activeTab">
            <el-tab-pane :label="t('tabBackupRecords')" name="backups">
              <el-table :data="device?.recent_backups || []" style="width: 100%">
                <el-table-column prop="backup_time" :label="t('backupTime')" width="180">
                  <template #default="{ row }">{{ formatDateTime(row.backup_time) }}</template>
                </el-table-column>
                <el-table-column prop="has_change" :label="t('backupConfigChange')" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.has_change ? 'warning' : 'success'" size="small">
                      {{ row.has_change ? t('statusYes') : t('statusNo') }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column :label="t('deviceAction')" width="150">
                  <template #default="{ row }">
                    <el-button size="small" @click="viewConfig(row.id)">{{ t('backupViewConfig') }}</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="t('tabFaultRecords')" name="faults">
              <el-table :data="device?.recent_faults || []" style="width: 100%">
                <el-table-column prop="fault_no" :label="t('faultNo')" width="180">
                  <template #default="{ row }">
                    <router-link :to="`/faults/${row.id}`" class="fault-link">
                      {{ row.fault_no }}
                    </router-link>
                  </template>
                </el-table-column>
                <el-table-column prop="severity" :label="t('faultLevel')" width="80">
                  <template #default="{ row }">
                    <el-tag :type="getSeverityType(row.severity)" size="small">
                      {{ getSeverityText(row.severity) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" :label="t('faultStatus')" width="80">
                  <template #default="{ row }">
                    <el-tag :type="getFaultStatusType(row.status)" size="small">
                      {{ getFaultStatusText(row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" :label="t('faultOccurTime')" width="160">
                  <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                </el-table-column>
                <el-table-column :label="t('deviceAction')" width="150" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" @click="editFaultInDetail(row)">{{ t('deviceEdit') }}</el-button>
                    <el-button
                      v-if="row.status !== 'closed'"
                      size="small"
                      type="success"
                      @click="closeFaultInDetail(row)"
                    >
                      {{ t('faultClose') }}
                    </el-button>
                    <el-button
                      v-else
                      size="small"
                      type="info"
                      plain
                      disabled
                    >
                      {{ t('faultClosed') }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-button type="primary" size="small" style="margin-top: 10px" @click="openFaultDialog">
                {{ t('faultAddRecord') }}
              </el-button>
            </el-tab-pane>

            <el-tab-pane :label="t('tabMaintenanceRecords')" name="maintenance">
              <el-table :data="device?.recent_maintenances || []" style="width: 100%">
                <el-table-column prop="maint_no" :label="t('maintNo')" width="180">
                  <template #default="{ row }">
                    <router-link :to="`/maintenance/${row.id}`" class="maint-link">
                      {{ row.maint_no }}
                    </router-link>
                  </template>
                </el-table-column>
                <el-table-column prop="maint_type" :label="t('maintType')" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getMaintTypeType(row.maint_type)" size="small">
                      {{ getMaintTypeText(row.maint_type) }}
                    </el-tag>
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
              <el-button type="primary" size="small" style="margin-top: 10px" @click="openMaintDialog">
                {{ t('maintAddRecord') }}
              </el-button>
            </el-tab-pane>

            <el-tab-pane :label="t('tabCostStats')" name="costs">
              <div class="cost-summary">
                <el-statistic :title="t('purchaseCost')" :value="device?.purchase_cost || 0" prefix="¥" />
                <el-statistic :title="t('maintCost')" :value="calculateMaintCost()" :precision="2" prefix="¥" />
                <el-statistic :title="t('maintTotalCost')" :value="(device?.purchase_cost || 0) + calculateMaintCost()" :precision="2" prefix="¥" />
              </div>
            </el-tab-pane>
            <el-tab-pane :label="t('tabDeviceInventory')" name="inventory">
              <!-- 概览（紧凑） -->
              <div v-if="deviceInventory.length > 0" class="compact-header">
                <span>{{ t('inventoryInstalledParts') }}: <strong class="text-success">{{ deviceInventory.length }}</strong> {{ t('inventoryParts') }}</span>
                <span>{{ t('inventoryTotalValue') }}: <strong class="text-success">¥{{ inventoryTotalValue.toFixed(2) }}</strong></span>
              </div>

              <!-- 备件清单表格 -->
              <el-table :data="deviceInventory" v-loading="inventoryLoading" stripe border size="small" style="margin-top: 8px">
                <el-table-column prop="serial_number" :label="t('spareSerialNumber')" width="120">
                  <template #default="{ row }">
                    <span class="text-primary">{{ row.serial_number || '-' }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="po_number" :label="t('inventoryPoNumber')" width="80">
                  <template #default="{ row }">{{ row.po_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" :label="t('sparePartNumber')" width="120" />
                <el-table-column prop="part_name" :label="t('spareName')" width="150" />
                <el-table-column prop="category" :label="t('spareCategory')" width="80" />
                <el-table-column prop="unit_price" :label="t('spareUnitPrice')" width="80">
                  <template #default="{ row }">
                    <span class="text-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="installed_at" :label="t('inventoryInstalledAt')" width="160">
                  <template #default="{ row }">{{ formatDateTime(row.installed_at) }}</template>
                </el-table-column>
                <el-table-column prop="installed_by" :label="t('inventoryInstalledBy')" width="80" />
                <el-table-column prop="notes" :label="t('spareNotes')" min-width="100" show-overflow-tooltip />
              </el-table>

              <el-empty v-if="deviceInventory.length === 0 && !inventoryLoading" :description="t('inventoryNoParts')" :image-size="60" />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑设备对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('editDeviceTitle')" width="600px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item :label="t('deviceName')">
          <el-input v-model="editForm.name" :disabled="true" />
        </el-form-item>
        <el-form-item :label="t('deviceIp')">
          <el-input v-model="editForm.ip" />
        </el-form-item>
        <el-form-item :label="t('deviceModel')">
          <el-input v-model="editForm.model" />
        </el-form-item>
        <el-form-item :label="t('deviceSerialNumber')">
          <el-input v-model="editForm.serial_number" />
        </el-form-item>
        <el-form-item :label="t('deviceLocation')">
          <el-input v-model="editForm.location" />
        </el-form-item>
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
      <el-card v-if="configContent">
        <pre class="config-content">{{ configContent }}</pre>
      </el-card>
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
        <el-form-item :label="t('faultDowntimeMinutes')">
          <el-input-number v-model="faultForm.downtime_minutes" :min="0" />
        </el-form-item>
        <el-form-item :label="t('faultDescription')" required>
          <el-input v-model="faultForm.description" type="textarea" :rows="4" />
        </el-form-item>
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
        <el-form-item :label="t('maintReplaceParts')">
          <el-input v-model="maintForm.parts_replaced" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('maintPartsCost')">
          <el-input-number v-model="maintForm.parts_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item :label="t('maintLaborHours')">
          <el-input-number v-model="maintForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item :label="t('maintLaborCost')">
          <el-input-number v-model="maintForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item :label="t('maintVendor')">
          <el-input v-model="maintForm.vendor" />
        </el-form-item>
        <el-form-item :label="t('maintDescription')" required>
          <el-input v-model="maintForm.description" type="textarea" :rows="4" />
        </el-form-item>
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
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Download, Upload, Picture } from '@element-plus/icons-vue'
import { getDeviceDetail, createFault, createMaintenance, updateMaintenance, deleteMaintenance, updateFault, updateDevice as updateDeviceApi, getDeviceInventory } from '@/api'
import { formatDateTime, formatDate } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import axios from 'axios'

const { t } = useI18n()
const route = useRoute()
const device = ref(null)
const loading = ref(false)
const activeTab = ref('backups')
const showFaultDialog = ref(false)
const showMaintDialog = ref(false)
const showEditDialog = ref(false)
const showConfigDialog = ref(false)
const editMode = ref(false)
const configContent = ref('')

// 设备资产相关
const deviceInventory = ref([])
const inventoryLoading = ref(false)

// 设备资产总价值计算
const inventoryTotalValue = computed(() => {
  return deviceInventory.value.reduce((sum, item) => sum + (item.unit_price || 0), 0)
})

const faultForm = ref({
  severity: 'major',
  downtime_minutes: 0,
  description: ''
})

const maintForm = ref({
  maint_type: 'corrective',
  parts_replaced: '',
  parts_cost: 0,
  labor_hours: 0,
  labor_cost: 0,
  vendor: '',
  description: ''
})

const editForm = ref({})

// 上传配置
const uploadUrl = computed(() => `/api/devices/${route.params.id}/photos`)
const uploadHeaders = computed(() => ({}))

const getStatusType = (status) => {
  const types = { online: 'success', offline: 'danger', maintenance: 'warning', retired: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { online: t('statusOnline'), offline: t('statusOffline'), maintenance: t('statusMaintenance'), retired: t('statusRetired') }
  return texts[status] || status
}

const getFaultStatusType = (status) => {
  const types = { open: 'info', investigating: 'warning', resolved: 'success', closed: 'info' }
  return types[status] || 'info'
}

const getFaultStatusText = (status) => {
  const texts = { open: t('faultStatusOpen'), investigating: t('faultStatusInvestigating'), resolved: t('faultStatusResolved'), closed: t('faultStatusClosed') }
  return texts[status] || status
}

const getRoleText = (role) => {
  const texts = { access: t('deviceRoleAccess'), distribution: t('deviceRoleDistribution'), core: t('deviceRoleCore') }
  return texts[role] || role
}

const getVendorText = (vendor) => {
  const map = { cisco: 'Cisco', huawei: t('vendorHuawei'), '华为': t('vendorHuawei'), h3c: 'H3C', '新华三': 'H3C', hp: 'H3C', juniper: 'Juniper', arista: 'Arista' }
  return map[vendor?.toLowerCase()] || vendor || 'Cisco'
}

const getVendorTagType = (vendor) => {
  const map = { cisco: '', huawei: 'success', '华为': 'success', h3c: 'warning', '新华三': 'warning', hp: 'warning', juniper: 'danger', arista: 'info' }
  return map[vendor?.toLowerCase()] || ''
}

const testConnection = async () => {
  try {
    ElMessage.info(t('msgTestConnecting'))
    // TODO: 实现连接测试 API
    ElMessage.success(t('msgTestWaitApi'))
  } catch (e) {
    ElMessage.error(t('msgTestFailed'))
  }
}

const getSeverityType = (severity) => {
  const types = { critical: 'danger', major: 'warning', minor: '', warning: 'info' }
  return types[severity] || 'info'
}

const getSeverityText = (severity) => {
  const texts = { critical: t('dashCritical'), major: t('dashMajor'), minor: t('dashMinor'), warning: t('dashWarning') }
  return texts[severity] || severity
}

const getPhotoTypeText = (type) => {
  const texts = { front: t('devicePhotoFront'), back: t('devicePhotoBack'), label: t('devicePhotoLabel'), rack: t('devicePhotoRack'), other: t('devicePhotoOther') }
  return texts[type] || type
}

const getMaintTypeText = (type) => {
  const texts = { preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }
  return texts[type] || type
}

const getMaintTypeType = (type) => {
  const types = { preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }
  return types[type] || ''
}

const calculateMaintCost = () => {
  if (!device.value?.recent_maintenances) return 0
  return device.value.recent_maintenances.reduce((sum, m) => {
    return sum + (parseFloat(m.parts_cost) || 0) + (parseFloat(m.labor_cost) || 0)
  }, 0)
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

// 加载设备资产
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

// 监听 Tab 切换，切换到资产 Tab 时加载资产数据
watch(activeTab, (newTab) => {
  if (newTab === 'inventory') {
    loadDeviceInventory()
  }
})

const backupNow = async () => {
  try {
    const { backupDevice } = await import('@/api')
    await backupDevice(route.params.id, 'Web')
    ElMessage.success(t('msgBackupSuccessShort'))
    loadDevice()
  } catch (error) {
    ElMessage.error(t('msgBackupFailed'))
  }
}

const openConsoleDeploy = () => {
  ElMessage.info(t('msgConsoleDev'))
}

const handlePhotoUploadSuccess = (response) => {
  ElMessage.success(t('msgPhotoUploadSuccess'))
  loadDevice()
}

const handlePhotoUploadError = (error) => {
  ElMessage.error(t('msgPhotoUploadFailed'))
}

const deletePhoto = async (photoId) => {
  try {
    await ElMessageBox.confirm(t('confirmDeletePhoto'), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    const api = await import('@/api')
    await api.deletePhoto(route.params.id, photoId)
    ElMessage.success(t('msgPhotoDeleteSuccess'))
    loadDevice()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgPhotoDeleteFailed'))
    }
  }
}

const viewConfig = async (backupId) => {
  try {
    const { getBackupContent } = await import('@/api')
    const data = await getBackupContent(backupId)
    configContent.value = data.content
    showConfigDialog.value = true
  } catch (error) {
    ElMessage.error(t('msgConfigLoadFailed'))
  }
}

const updateDevice = async () => {
  try {
    await updateDeviceApi(route.params.id, editForm.value)
    ElMessage.success(t('msgDeviceUpdateSuccess'))
    showEditDialog.value = false
    loadDevice()
  } catch (error) {
    ElMessage.error(t('msgDeviceUpdateFailed'))
  }
}

const addFault = async () => {
  try {
    console.log('Adding fault for device:', device.value)
    await createFault({
      device_id: device.value.id,
      device_name: device.value.name,
      ...faultForm.value,
      status: 'open'
    })
    ElMessage.success(t('msgFaultAddSuccess'))
    showFaultDialog.value = false
    resetFaultForm()
    loadDevice()
  } catch (error) {
    ElMessage.error(t('msgFaultAddFailed'))
    ElMessage.error(error.response?.data?.detail || t('msgFaultAddFailed'))
  }
}

const openFaultDialog = () => {
  editMode.value = false
  resetFaultForm()
  showFaultDialog.value = true
}

const editFaultInDetail = (row) => {
  editMode.value = true
  faultForm.value = {
    id: row.id,
    device_id: row.device_id,
    severity: row.severity,
    downtime_minutes: row.downtime_minutes || 0,
    impact: row.impact || '',
    description: row.description,
    status: row.status
  }
  showFaultDialog.value = true
}

const updateFaultInDetail = async () => {
  try {
    await updateFault(faultForm.value.id, faultForm.value)
    ElMessage.success(t('msgFaultUpdateSuccess'))
    showFaultDialog.value = false
    editMode.value = false
    resetFaultForm()
    loadDevice()
  } catch (error) {
    ElMessage.error(t('msgFaultUpdateFailed'))
  }
}

const closeFaultInDetail = async (row) => {
  try {
    await ElMessageBox.confirm(t('faultCloseConfirm', { id: row.fault_no }), t('faultCloseTitle'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await updateFault(row.id, { status: 'closed' })
    console.log('API 调用成功，row:', row)
    ElMessage.success(t('msgFaultCloseSuccess'))
    loadDevice()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgFaultCloseFailed'))
    }
  }
}

const resetFaultForm = () => {
  faultForm.value = {
    severity: 'major',
    downtime_minutes: 0,
    impact: '',
    description: ''
  }
}

const openMaintDialog = () => {
  editMode.value = false
  resetMaintForm()
  showMaintDialog.value = true
}

const addMaintenance = async () => {
  try {
    console.log('Adding maintenance for device:', device.value)
    await createMaintenance({
      device_id: device.value.id,
      device_name: device.value.name,
      ...maintForm.value
    })
    ElMessage.success(t('msgMaintAddSuccess'))
    showMaintDialog.value = false
    resetMaintForm()
    loadDevice()
  } catch (error) {
    ElMessage.error(t('msgMaintAddFailed'))
    ElMessage.error(error.response?.data?.detail || t('msgMaintAddFailed'))
  }
}

const editMaintInDetail = (row) => {
  editMode.value = true
  maintForm.value = {
    id: row.id,
    device_id: row.device_id,
    maint_type: row.maint_type,
    parts_replaced: row.parts_replaced || '',
    parts_cost: row.parts_cost || 0,
    labor_hours: row.labor_hours || 0,
    labor_cost: row.labor_cost || 0,
    vendor: row.vendor || '',
    description: row.description
  }
  showMaintDialog.value = true
}

const updateMaintInDetail = async () => {
  try {
    await updateMaintenance(maintForm.value.id, maintForm.value)
    ElMessage.success(t('msgMaintUpdateSuccess'))
    showMaintDialog.value = false
    editMode.value = false
    resetMaintForm()
    loadDevice()
  } catch (error) {
    ElMessage.error(t('msgMaintUpdateFailed'))
  }
}

const deleteMaintInDetail = async (maintId) => {
  try {
    await ElMessageBox.confirm(t('confirmDeleteMaint'), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteMaintenance(maintId)
    ElMessage.success(t('msgMaintDeleteSuccess'))
    loadDevice()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgMaintDeleteFailed'))
    }
  }
}

const resetMaintForm = () => {
  maintForm.value = {
    maint_type: 'corrective',
    parts_replaced: '',
    parts_cost: 0,
    labor_hours: 0,
    labor_cost: 0,
    vendor: '',
    description: ''
  }
}

onMounted(() => {
  loadDevice()
})
</script>

<style scoped>
.device-info {
  text-align: center;
}

.device-avatar {
  margin-bottom: 20px;
}

.device-avatar h2 {
  margin: 15px 0 10px;
  font-size: 20px;
}

.actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.photos-card {
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
  padding: 10px;
}

.photo-item {
  position: relative;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.photo-image {
  width: 100%;
  height: 120px;
}

.photo-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: #f5f7fa;
}

.photo-type {
  font-size: 12px;
  color: #606266;
}

.image-error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
  font-size: 20px;
}

.cost-summary {
  display: flex;
  justify-content: space-around;
  padding: 20px;
}

.config-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 500px;
  overflow-y: auto;
}

.fault-link,
.maint-link {
  color: #409EFF;
  text-decoration: none;
  font-weight: 500;
}

.fault-link:hover,
.maint-link:hover {
  text-decoration: underline;
  color: #66b1ff;
}

/* 紧凑头部样式 */
.compact-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 13px;
}
.compact-header strong {
  font-weight: 600;
}
.text-primary {
  color: var(--el-color-primary);
  font-weight: 500;
}
.text-success {
  color: var(--el-color-success);
  font-weight: 600;
}
</style>
