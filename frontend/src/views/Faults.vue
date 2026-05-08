<template>
  <div class="faults-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('faultTitle') }}</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            {{ t('faultAdd') }}
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          :placeholder="t('faultSearchPlaceholder')"
          style="width: 220px"
          clearable
          @input="filterFaults"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterSeverity" :placeholder="t('faultLevel')" clearable style="width: 140px" @change="filterFaults">
          <el-option :label="t('dashCritical')" value="critical" />
          <el-option :label="t('dashMajor')" value="major" />
          <el-option :label="t('dashMinor')" value="minor" />
          <el-option :label="t('dashWarning')" value="warning" />
        </el-select>
        <el-select v-model="filterStatus" :placeholder="t('faultStatus')" clearable style="width: 120px" @change="filterFaults">
          <el-option :label="t('faultStatusOpen')" value="open" />
          <el-option :label="t('faultStatusInvestigating')" value="investigating" />
          <el-option :label="t('faultStatusResolved')" value="resolved" />
          <el-option :label="t('faultStatusClosed')" value="closed" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          :range-separator="t('faultToDate')"
          :start-placeholder="t('faultStartDate')"
          :end-placeholder="t('faultEndDate')"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="filterFaults"
        />
        <el-select v-model="sortBy" :placeholder="t('faultSort')" style="width: 150px" @change="filterFaults">
          <el-option :label="t('faultSortTimeDesc')" value="created_at_desc" />
          <el-option :label="t('faultSortTimeAsc')" value="created_at_asc" />
          <el-option :label="t('faultSortDowntimeDesc')" value="downtime_desc" />
          <el-option :label="t('faultSortDowntimeAsc')" value="downtime_asc" />
        </el-select>
      </div>

      <el-table :data="filteredFaults" style="width: 100%" v-loading="loading">
        <el-table-column prop="fault_no" :label="t('faultNo')" width="200">
          <template #default="{ row }">
            <router-link :to="`/faults/${row.id}`" class="fault-link">
              {{ row.fault_no }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" :label="t('faultDevice')" width="180" />
        <el-table-column prop="severity" :label="t('faultSeverity')" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('faultStatus')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="downtime_minutes" :label="t('faultDowntime')" width="100">
          <template #default="{ row }">{{ row.downtime_minutes }} {{ t('faultMinutes') }}</template>
        </el-table-column>
        <el-table-column prop="description" :label="t('faultDescription')" />
        <el-table-column prop="created_at" :label="t('faultOccurTime')" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('faultAction')" width="240" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editFault(row)">{{ t('actionEdit') }}</el-button>
            <el-button
              v-if="row.status === 'open'"
              size="small"
              type="warning"
              @click="changeStatus(row, 'investigating')"
            >
              {{ t('faultProcess') }}
            </el-button>
            <el-button
              v-if="row.status === 'investigating'"
              size="small"
              type="success"
              @click="changeStatus(row, 'resolved')"
            >
              {{ t('faultResolve') }}
            </el-button>
            <el-button
              v-if="row.status === 'resolved'"
              size="small"
              type="info"
              @click="changeStatus(row, 'closed')"
            >
              {{ t('actionClose') }}
            </el-button>
            <el-button
              v-if="row.status === 'closed'"
              size="small"
              type="primary"
              plain
              @click="changeStatus(row, 'open')"
            >
              {{ t('faultReopen') }}
            </el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoFaults')" :image-size="80">
            <el-button type="primary" size="small" @click="showAddDialog = true">{{ t('faultAdd') }}</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadFaults" @current-change="loadFaults" />
      </div>
    </el-card>

    <!-- 添加故障对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('faultEditRecord') : t('faultAddRecord')" width="600px">
      <el-form :model="faultForm" label-width="120px">
        <el-form-item :label="t('faultDeviceLabel')" required>
          <el-select v-model="faultForm.device_id" :placeholder="t('faultSelectDevice')" style="width: 100%" :disabled="editMode">
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('faultLevel')" required>
          <el-select v-model="faultForm.severity">
            <el-option :label="`${t('dashCritical')} (Critical)`" value="critical" />
            <el-option :label="`${t('dashMajor')} (Major)`" value="major" />
            <el-option :label="`${t('dashMinor')} (Minor)`" value="minor" />
            <el-option :label="`${t('dashWarning')} (Warning)`" value="warning" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('faultStatus')" v-if="editMode">
          <el-select v-model="faultForm.status">
            <el-option :label="t('faultStatusOpen')" value="open" />
            <el-option :label="t('faultStatusInvestigating')" value="investigating" />
            <el-option :label="t('faultStatusResolved')" value="resolved" />
            <el-option :label="t('faultStatusClosed')" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('faultDowntimeMinutes')">
          <el-input-number v-model="faultForm.downtime_minutes" :min="0" />
        </el-form-item>
        <el-form-item :label="t('faultImpact')">
          <el-input v-model="faultForm.impact" type="textarea" :rows="2" :placeholder="t('faultImpactPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('faultDescription')" required>
          <el-input v-model="faultForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateFault() : addFault()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFaults, getDevices, createFault, updateFault as updateFaultApi, deleteFault } from '@/api'
import { Search } from '@element-plus/icons-vue'
import { formatDateTime, toLocalDayjs, dayjs } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const faults = ref([])
const filteredFaults = ref([])
const devices = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const editMode = ref(false)

const searchText = ref('')
const filterSeverity = ref('')
const filterStatus = ref('')
const dateRange = ref([])
const sortBy = ref('created_at_desc')

const faultForm = ref({
  id: null,
  device_id: null,
  device_name: '',
  severity: 'major',
  downtime_minutes: 0,
  impact: '',
  description: '',
  status: 'open'
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

const filterFaults = () => {
  let result = [...faults.value]

  // 按搜索文本过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(f =>
      f.device_name?.toLowerCase().includes(search) ||
      f.fault_no?.toLowerCase().includes(search)
    )
  }

  // 按故障级别过滤
  if (filterSeverity.value) {
    result = result.filter(f => f.severity === filterSeverity.value)
  }

  // 按状态过滤
  if (filterStatus.value) {
    result = result.filter(f => f.status === filterStatus.value)
  }

  // 按日期范围过滤
  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0])
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(f => {
      const faultTime = dayjs(f.created_at)
      return faultTime.isAfter(startDate) && faultTime.isBefore(endDate)
    })
  }

  // 排序
  if (sortBy.value) {
    switch (sortBy.value) {
      case 'created_at_desc':
        result.sort((a, b) => dayjs(b.created_at) - dayjs(a.created_at))
        break
      case 'created_at_asc':
        result.sort((a, b) => dayjs(a.created_at) - dayjs(b.created_at))
        break
      case 'downtime_desc':
        result.sort((a, b) => (b.downtime_minutes || 0) - (a.downtime_minutes || 0))
        break
      case 'downtime_asc':
        result.sort((a, b) => (a.downtime_minutes || 0) - (b.downtime_minutes || 0))
        break
    }
  }

  filteredFaults.value = result
}

const loadFaults = async () => {
  loading.value = true
  try {
    const data = await getFaults({ limit: 500 })
    faults.value = data.items || []
    total.value = data.total || faults.value.length
    filterFaults()
  } catch (error) {
    ElMessage.error(t('faultLoadFailed'))
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (error) {
    ElMessage.error(t('faultDeviceLoadFailed'))
  }
}

const addFault = async () => {
  try {
    const device = devices.value.find(d => d.id === faultForm.value.device_id)
    await createFault({
      ...faultForm.value,
      device_name: device?.name,
      reporter: 'Web',
      status: 'open'
    })
    ElMessage.success(t('faultAddSuccess'))
    showAddDialog.value = false
    resetForm()
    loadFaults()
  } catch (error) {
    ElMessage.error(t('faultAddFailed'))
  }
}

const editFault = (row) => {
  editMode.value = true
  faultForm.value = {
    id: row.id,
    device_id: row.device_id,
    device_name: row.device_name,
    severity: row.severity,
    downtime_minutes: row.downtime_minutes || 0,
    impact: row.impact || '',
    description: row.description,
    status: row.status
  }
  showAddDialog.value = true
}

const updateFault = async () => {
  try {
    const device = devices.value.find(d => d.id === faultForm.value.device_id)
    await updateFaultApi(faultForm.value.id, {
      ...faultForm.value,
      device_name: device?.name
    })
    ElMessage.success(t('faultUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    resetForm()
    loadFaults()
    // 触发事件更新导航栏badge
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    ElMessage.error(t('faultUpdateFailed'))
  }
}

const closeFault = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('faultCloseConfirm')} "${row.fault_no}" ?`, t('faultCloseTitle'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await updateFaultApi(row.id, { status: 'closed' })
    ElMessage.success(t('faultCloseSuccess'))
    loadFaults()
    // 触发事件更新导航栏badge
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('faultCloseFailed'))
    }
  }
}

const changeStatus = async (row, newStatus) => {
  try {
    const statusKeys = {
      open: 'faultStatusOpen',
      investigating: 'faultStatusInvestigating',
      resolved: 'faultStatusResolved',
      closed: 'faultStatusClosed'
    }
    const statusText = t(statusKeys[newStatus])

    await ElMessageBox.confirm(
      `${t('faultStatusChangeConfirm')} "${row.fault_no}" ${t('faultStatusChangeTo')} "${statusText}" ?`,
      t('faultStatusChangeTitle'),
      {
        confirmButtonText: t('actionConfirm'),
        cancelButtonText: t('actionCancel'),
        type: 'info'
      }
    )

    await updateFaultApi(row.id, { status: newStatus })
    ElMessage.success(`${t('faultStatusUpdated')} ${statusText}`)
    loadFaults()
    // 触发事件更新导航栏badge
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('faultStatusUpdateFailed'))
    }
  }
}

const resetForm = () => {
  faultForm.value = {
    id: null,
    device_id: null,
    device_name: '',
    severity: 'major',
    downtime_minutes: 0,
    impact: '',
    description: '',
    status: 'open'
  }
}

onMounted(() => {
  loadFaults()
  loadDevices()
})
</script>

<style scoped>
.faults-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
  flex-wrap: wrap;
}

.fault-link {
  color: var(--accent-secondary);
  text-decoration: none;
  font-weight: 500;
}

.fault-link:hover {
  text-decoration: underline;
}
</style>
