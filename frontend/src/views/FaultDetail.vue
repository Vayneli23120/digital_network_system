<template>
  <div class="fault-detail-page">
    <el-page-header @back="goBack" :title="t('faultDetailBack')">
      <template #content>
        <span class="page-title">{{ fault.fault_no || t('faultDetailTitle') }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：故障信息 -->
      <el-col :span="16">
        <el-card class="fault-info-card">
          <template #header>
            <span>{{ t('faultDetailInfo') }}</span>
          </template>

          <el-descriptions :column="2" border v-if="fault.id">
            <el-descriptions-item :label="t('faultNo')">{{ fault.fault_no }}</el-descriptions-item>
            <el-descriptions-item :label="t('faultDevice')">
              <router-link :to="`/devices/${fault.device_id}`">{{ fault.device_name }}</router-link>
            </el-descriptions-item>
            <el-descriptions-item :label="t('faultLevel')">
              <el-tag :type="getSeverityType(fault.severity)">
                {{ getSeverityText(fault.severity) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('faultDetailCurrentStatus')">
              <el-tag :type="getStatusType(fault.status)">
                {{ getStatusText(fault.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('faultDowntime')">{{ fault.downtime_minutes }} {{ t('faultMinutes') }}</el-descriptions-item>
            <el-descriptions-item :label="t('faultImpact')">{{ fault.impact || t('faultNoImpact') }}</el-descriptions-item>
            <el-descriptions-item :label="t('faultReporter')">{{ fault.reporter || 'Web' }}</el-descriptions-item>
            <el-descriptions-item :label="t('faultOccurTime')">{{ formatDateTime(fault.fault_time || fault.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <el-divider>{{ t('faultDescription') }}</el-divider>
          <p class="description">{{ fault.description || t('faultNoDescription') }}</p>

          <el-divider v-if="fault.resolution">{{ t('faultResolution') }}</el-divider>
          <p v-if="fault.resolution" class="description">{{ fault.resolution }}</p>
        </el-card>

        <!-- 操作按钮 -->
        <el-card style="margin-top: 20px">
          <el-space>
            <el-button type="primary" @click="showEditDialog = true">
              <el-icon><Edit /></el-icon>
              {{ t('actionEdit') }}
            </el-button>
            <!-- 转维修按钮：未关闭且未关联维修单 -->
            <el-button
              v-if="fault.status !== 'closed' && !fault.maintenance_id"
              type="warning"
              @click="convertToMaintenance"
            >
              <el-icon><Tools /></el-icon>
              {{ t('faultDetailConvertMaintenance') }}
            </el-button>
            <el-button
              v-if="fault.status !== 'closed'"
              type="success"
              @click="closeFault"
            >
              <el-icon><CircleCheck /></el-icon>
              {{ t('actionClose') }}
            </el-button>
            <el-button type="danger" @click="deleteFault">
              <el-icon><Delete /></el-icon>
              {{ t('actionDelete') }}
            </el-button>
          </el-space>
        </el-card>

        <!-- 关联的维修单信息 -->
        <el-card style="margin-top: 20px" v-if="maintenanceInfo">
          <template #header>
            <span>{{ t('maintTitle') }}</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item :label="t('maintNo')">
              <router-link :to="`/maintenance/${maintenanceInfo.id}`">
                {{ maintenanceInfo.maint_no }}
              </router-link>
            </el-descriptions-item>
            <el-descriptions-item :label="t('maintType')">
              <el-tag>{{ getMaintTypeText(maintenanceInfo.maint_type) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('maintPartsCost')">¥{{ maintenanceInfo.parts_cost }}</el-descriptions-item>
            <el-descriptions-item :label="t('maintLaborCost')">¥{{ maintenanceInfo.labor_cost }}</el-descriptions-item>
            <el-descriptions-item :label="t('maintTime')">{{ formatDateTime(maintenanceInfo.maint_time) }}</el-descriptions-item>
            <el-descriptions-item :label="t('maintTotalCost')">
              <span class="total-cost">¥{{ (maintenanceInfo.parts_cost + maintenanceInfo.labor_cost).toFixed(2) }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <el-divider>{{ t('maintDescription') }}</el-divider>
          <p class="description">{{ maintenanceInfo.description || t('faultNoDescription') }}</p>
        </el-card>
      </el-col>

      <!-- 右侧：时间线 -->
      <el-col :span="8">
        <el-card class="timeline-card">
          <template #header>
            <span>{{ t('faultDetailTimeline') }}</span>
          </template>

          <el-timeline>
            <el-timeline-item
              :timestamp="formatDateTime(fault.created_at)"
              placement="top"
              color="#409EFF"
            >
              <el-card>
                <h4>{{ t('faultDetailFaultOccur') }}</h4>
                <p>{{ t('faultReporter') }}：{{ fault.reporter || 'Web' }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.status === 'investigating'"
              :timestamp="t('faultStatusInvestigating')"
              placement="top"
              color="#E6A23C"
            >
              <el-card>
                <h4>{{ t('faultDetailStartInvestigate') }}</h4>
                <p>{{ t('faultDetailProcessing') }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.status === 'resolved'"
              :timestamp="t('faultStatusResolved')"
              placement="top"
              color="#67C23A"
            >
              <el-card>
                <h4>{{ t('faultDetailFaultResolved') }}</h4>
                <p>{{ t('faultDetailFaultResolved') }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.status === 'closed'"
              :timestamp="t('faultStatusClosed')"
              placement="top"
              color="#909399"
            >
              <el-card>
                <h4>{{ t('faultDetailFaultClosed') }}</h4>
                <p>{{ t('faultDetailRecordArchived') }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- 设备快速信息 -->
        <el-card class="device-quick-info" style="margin-top: 20px" v-if="device">
          <template #header>
            <span>{{ t('faultDetailDeviceInfo') }}</span>
          </template>
          <div class="device-summary">
            <el-avatar :size="60" icon="Switch" />
            <div class="device-info">
              <h4>{{ device.name }}</h4>
              <p>{{ device.ip }}</p>
              <el-tag :type="device.status === 'online' ? 'success' : 'info'" size="small">
                {{ device.status }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑故障对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('faultEditRecord')" width="600px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item :label="t('faultLevel')" required>
          <el-select v-model="editForm.severity">
            <el-option :label="`${t('dashCritical')} (Critical)`" value="critical" />
            <el-option :label="`${t('dashMajor')} (Major)`" value="major" />
            <el-option :label="`${t('dashMinor')} (Minor)`" value="minor" />
            <el-option :label="`${t('dashWarning')} (Warning)`" value="warning" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('faultStatus')" required>
          <el-select v-model="editForm.status">
            <el-option :label="t('faultStatusOpen')" value="open" />
            <el-option :label="t('faultStatusInvestigating')" value="investigating" />
            <el-option :label="t('faultStatusResolved')" value="resolved" />
            <el-option :label="t('faultStatusClosed')" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('faultDowntimeMinutes')">
          <el-input-number v-model="editForm.downtime_minutes" :min="0" />
        </el-form-item>
        <el-form-item :label="t('faultImpact')">
          <el-input v-model="editForm.impact" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('faultDescription')" required>
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item :label="t('faultResolution')">
          <el-input v-model="editForm.resolution" type="textarea" :rows="3" :placeholder="t('faultResolutionPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="updateFault">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tools } from '@element-plus/icons-vue'
import { getFaultDetail, updateFault as updateFaultApi, deleteFault as deleteFaultApi, getDevices, convertFaultToMaintenance, getFaultMaintenance } from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()

const fault = ref({})
const device = ref(null)
const loading = ref(false)
const showEditDialog = ref(false)
const maintenanceInfo = ref(null)

const editForm = ref({
  severity: 'major',
  status: 'open',
  downtime_minutes: 0,
  impact: '',
  description: '',
  resolution: ''
})

const getSeverityType = (severity) => {
  const types = { critical: 'danger', major: 'warning', minor: '', warning: 'info' }
  return types[severity] || 'info'
}

const getSeverityText = (severity) => {
  const keys = { critical: 'dashCritical', major: 'dashMajor', minor: 'dashMinor', warning: 'dashWarning' }
  return t(keys[severity]) || severity
}

const getStatusType = (status) => {
  const types = { open: 'info', investigating: 'warning', resolved: 'success', closed: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const keys = { open: 'faultStatusOpen', investigating: 'faultStatusInvestigating', resolved: 'faultStatusResolved', closed: 'faultStatusClosed' }
  return t(keys[status]) || status
}

const getMaintTypeText = (type) => {
  const keys = { preventive: 'maintTypePreventive', corrective: 'maintTypeCorrective', upgrade: 'maintTypeUpgrade', emergency: 'maintTypeEmergency' }
  return t(keys[type]) || type
}

const loadFault = async () => {
  try {
    const faultId = route.params.id
    // 获取故障详情
    const data = await getFaultDetail(faultId)
    fault.value = data
    editForm.value = {
      severity: data.severity,
      status: data.status,
      downtime_minutes: data.downtime_minutes || 0,
      impact: data.impact || '',
      description: data.description,
      resolution: data.resolution || ''
    }

    // 加载设备信息
    if (data.device_id) {
      const devices = await getDevices()
      device.value = (devices.items || []).find(d => d.id === data.device_id)
    }

    // 加载关联的维修单信息
    if (data.maintenance_id) {
      const maintData = await getFaultMaintenance(faultId)
      maintenanceInfo.value = maintData.maintenance
    }
  } catch (error) {
    ElMessage.error(t('faultDetailLoadFailed'))
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/faults')
}

const convertToMaintenance = async () => {
  try {
    await ElMessageBox.confirm(
      t('faultDetailConvertConfirm'),
      t('faultDetailConvertTitle'),
      {
        confirmButtonText: t('faultDetailConfirmConvert'),
        cancelButtonText: t('actionCancel'),
        type: 'warning'
      }
    )

    const result = await convertFaultToMaintenance(fault.value.id)
    ElMessage.success(`${t('faultDetailMaintenanceCreated')} ${result.maint_no}`)
    loadFault()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || t('faultDetailConvertFailed'))
    }
  }
}

const updateFault = async () => {
  try {
    await updateFaultApi(fault.value.id, editForm.value)
    ElMessage.success(t('faultUpdateSuccess'))
    showEditDialog.value = false
    loadFault()
  } catch (error) {
    ElMessage.error(t('faultUpdateFailed'))
  }
}

const closeFault = async () => {
  try {
    await ElMessageBox.confirm(t('faultDetailCloseConfirm'), t('faultCloseTitle'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await updateFaultApi(fault.value.id, { status: 'closed' })
    ElMessage.success(t('faultCloseSuccess'))
    loadFault()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('faultCloseFailed'))
    }
  }
}

const deleteFault = async () => {
  try {
    await ElMessageBox.confirm(t('faultDetailDeleteConfirm'), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteFaultApi(fault.value.id)
    ElMessage.success(t('faultDetailDeleteSuccess'))
    router.push('/faults')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('faultDetailDeleteFailed'))
    }
  }
}

onMounted(() => {
  loadFault()
})
</script>

<style scoped>
.fault-detail-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
}

.fault-info-card {
  min-height: 400px;
}

.description {
  line-height: 1.8;
  color: #606266;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.timeline-card {
  min-height: 300px;
}

.device-summary {
  display: flex;
  align-items: center;
  gap: 15px;
}

.device-info h4 {
  margin: 0 0 5px 0;
  font-size: 16px;
}

.device-info p {
  margin: 0 0 5px 0;
  color: #909399;
  font-size: 14px;
}

.total-cost {
  font-weight: 600;
  color: #E6A23C;
  font-size: 16px;
}
</style>
