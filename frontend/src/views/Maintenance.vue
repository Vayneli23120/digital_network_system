<template>
  <div class="maintenance-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuMaintenance') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn" @click="openAddDialog">
          <el-icon><Plus /></el-icon>
          <span>{{ t('maintAddRecord') }}</span>
        </button>
        <button class="nav-action-btn secondary" @click="loadMaintenances" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-grid">
        <!-- 总维修单 -->
        <div class="stat-card total" @click="filterByStatus('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.total }}</div>
              <div class="metric-label">{{ t('maintStatsTotal') }}</div>
            </div>
            <div class="card-trend stable">
              <span class="trend-icon">&#9679;</span>
            </div>
          </div>
        </div>
        <!-- 维修中 -->
        <div class="stat-card repairing" @click="filterByStatus('repairing')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Setting /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.repairing }}</div>
              <div class="metric-label">{{ t('maintStatsRepairing') }}</div>
            </div>
            <div class="card-progress">
              <div class="progress-ring" :style="{ '--percent': getRepairingPercent() }"></div>
            </div>
          </div>
        </div>
        <!-- 待验证 -->
        <div class="stat-card verifying" @click="filterByStatus('verifying')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.verifying }}</div>
              <div class="metric-label">{{ t('maintStatsVerifying') }}</div>
            </div>
            <div class="card-trend info">
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
        <!-- 已完成 -->
        <div class="stat-card completed" @click="filterByStatus('completed')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><SuccessFilled /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.completed }}</div>
              <div class="metric-label">{{ t('maintStatsCompleted') }}</div>
            </div>
            <div class="card-trend success">
              <el-icon><SuccessFilled /></el-icon>
            </div>
          </div>
        </div>
        <!-- 超时工单 -->
        <div class="stat-card overdue" @click="filterByStatus('overdue')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><WarningFilled /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.overdue }}</div>
              <div class="metric-label">{{ t('maintStatsOverdue') }}</div>
            </div>
            <div class="card-trend warning" v-if="stats.overdue > 0">
              <el-icon><Warning /></el-icon>
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
            :placeholder="t('maintSearchPlaceholder')"
            class="search-input"
            clearable
            @input="filterMaintenances"
          />
        </div>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <div
            :class="['status-chip', { active: filterStatus === '' }]"
            @click="filterByStatus('')"
          >
            <span class="chip-label">{{ t('maintFilterAll') }}</span>
            <span class="chip-count">{{ stats.total }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-created', { active: filterStatus === 'created' }]"
            @click="filterByStatus('created')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelCreated') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-diagnosing', { active: filterStatus === 'diagnosing' }]"
            @click="filterByStatus('diagnosing')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelDiagnosing') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-repairing', { active: filterStatus === 'repairing' }]"
            @click="filterByStatus('repairing')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelRepairing') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-verifying', { active: filterStatus === 'verifying' }]"
            @click="filterByStatus('verifying')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelVerifying') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-completed', { active: filterStatus === 'completed' }]"
            @click="filterByStatus('completed')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintStatusLabelCompleted') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-overdue', { active: filterStatus === 'overdue' }]"
            @click="filterByStatus('overdue')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('maintFilterOverdue') }}</span>
          </div>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-select v-model="filterPriority" :placeholder="t('maintPriority')" clearable style="width: 90px" @change="filterMaintenances">
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
            <el-option label="P4" value="P4" />
          </el-select>
          <el-select v-model="filterMaintType" :placeholder="t('maintType')" clearable style="width: 120px" @change="filterMaintenances">
            <el-option :label="t('maintTypePreventive')" value="preventive" />
            <el-option :label="t('maintTypeCorrective')" value="corrective" />
            <el-option :label="t('maintTypeUpgrade')" value="upgrade" />
            <el-option :label="t('maintTypeEmergency')" value="emergency" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :range-separator="t('maintDateTo')"
            :start-placeholder="t('maintDateStart')"
            :end-placeholder="t('maintDateEnd')"
            value-format="YYYY-MM-DD"
            style="width: 220px"
            @change="filterMaintenances"
          />
        </div>
      </div>
    </section>

    <!-- 维修单数据面板 -->
    <section class="data-section">
      <div class="table-header">
        <span class="table-title">Work Order List</span>
        <span class="table-count">{{ filteredTotal }} records</span>
      </div>

      <el-table
        :data="paginatedMaintenances"
        class="enterprise-table"
        v-loading="loading"
        :row-class-name="tableRowClassName"
        :header-cell-style="{ background: 'transparent' }"
      >
        <!-- 维修单号 -->
        <el-table-column prop="maint_no" :label="t('maintColNo')" width="220">
          <template #default="{ row }">
            <router-link :to="`/maintenance/${row.id}`" class="maint-no-link">
              <span class="maint-no-badge">{{ row.maint_no }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>

        <!-- 状态 -->
        <el-table-column prop="status" :label="t('maintStatusLabel')" width="100">
          <template #default="{ row }">
            <div :class="['status-badge', row.status]">
              <span class="status-dot"></span>
              <span class="status-text">{{ getStatusLabel(row.status) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 优先级 -->
        <el-table-column prop="priority" :label="t('maintPriority')" width="90">
          <template #default="{ row }">
            <div :class="['priority-badge', getPriorityBadgeClass(row.priority)]">
              <span class="priority-icon">
                <el-icon v-if="getPriorityBadgeClass(row.priority) === 'P1'"><Warning /></el-icon>
                <el-icon v-else-if="getPriorityBadgeClass(row.priority) === 'P2'"><InfoFilled /></el-icon>
              </span>
              <span class="priority-text">{{ row.priority || 'P3' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 设备 -->
        <el-table-column prop="device_name" :label="t('maintColDevice')" width="180">
          <template #default="{ row }">
            <div class="device-cell">
              <el-icon class="device-icon"><Connection /></el-icon>
              <span class="device-name">{{ row.device_name || '--' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 负责人 -->
        <el-table-column prop="current_owner" :label="t('maintOwner')" width="120">
          <template #default="{ row }">
            <div class="owner-cell">
              <div class="owner-avatar">{{ (row.current_owner || '?')[0] }}</div>
              <span class="owner-name">{{ row.current_owner || t('maintOwnerUnassigned') }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 类型 -->
        <el-table-column prop="maint_type" :label="t('maintColType')" width="120">
          <template #default="{ row }">
            <div :class="['type-badge', row.maint_type || 'other']">
              <span class="type-text">{{ getMaintTypeText(row.maint_type) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 进度 -->
        <el-table-column prop="progress_percent" :label="t('maintProgress')" width="140">
          <template #default="{ row }">
            <div class="progress-cell">
              <div class="progress-bar-bg">
                <div class="progress-bar-fill" :style="{ width: getProgressPercent(row.status) + '%' }" :class="row.status"></div>
              </div>
              <span class="progress-percent">{{ getProgressPercent(row.status) }}%</span>
            </div>
          </template>
        </el-table-column>

        <!-- SLA -->
        <el-table-column prop="sla_remaining" :label="t('maintSlaDeadline')" width="100">
          <template #default="{ row }">
            <div :class="['sla-cell', { overdue: isOverdue(row), critical: isSlaCritical(row) }]">
              <el-icon v-if="isOverdue(row)" class="sla-icon"><Warning /></el-icon>
              <span class="sla-text">{{ getSlaText(row.sla_remaining) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 成本 -->
        <el-table-column prop="total_cost" :label="t('maintColTotalCost')" width="120">
          <template #default="{ row }">
            <div class="cost-cell">
              <span class="cost-currency">&#165;</span>
              <span class="cost-value">{{ ((row.parts_cost || 0) + (row.labor_cost || 0)).toFixed(2) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 时间 -->
        <el-table-column prop="maint_time" :label="t('maintColTime')" width="180">
          <template #default="{ row }">
            <div class="time-cell">
              <el-icon class="time-icon"><Clock /></el-icon>
              <span class="time-text">{{ formatDateTime(row.maint_time || row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column :label="t('colOperation')" width="120" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <button class="action-btn advance" @click="handleStatusAction(row)" v-if="getNextAction(row.status)" :title="getActionTooltip(row.status)">
                <el-icon><component :is="getActionIcon(row.status)" /></el-icon>
              </button>
              <button class="action-btn view" @click="viewDetail(row)" title="查看详情">
                <el-icon><View /></el-icon>
              </button>
              <button class="action-btn delete" @click="deleteMaintenance(row)" v-if="row.status !== 'completed'" title="删除">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </template>
        </el-table-column>
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

    <!-- 添加/编辑维修记录对话框（使用共享组件） -->
    <MaintenanceFormDialog
      v-model="showAddDialog"
      :editData="editMaintData"
      :showScanButton="true"
      :showReturnParts="true"
      @success="handleMaintSuccess"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, InfoFilled, Setting, Edit, Delete, View, ArrowRight, Refresh, CircleCheck, SuccessFilled, WarningFilled, Warning, Connection } from '@element-plus/icons-vue'
import { getMaintenances, getDevices, deleteMaintenance as deleteMaintenanceApi, transitionMaintenanceStatus } from '@/api'
import api from '@/api/request'
import MaintenanceFormDialog from '@/components/MaintenanceFormDialog.vue'
import { formatDateTime, dayjs } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { debounce } from '@/utils/requestManager.js'
import { cachedRequest, clearCache } from '@/utils/cache.js'

const router = useRouter()
const { t } = useI18n()

const maintenances = ref([])
const filteredMaintenances = ref([])
const devices = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const editMaintData = ref(null)  // 维修编辑数据

const searchText = ref('')
const filterStatus = ref('')
const filterPriority = ref('')
const filterMaintType = ref('')
const dateRange = ref([])
const sortBy = ref('maint_time_desc')

const stats = computed(() => {
  const list = maintenances.value
  const totalCount = list.length
  const repairingCount = list.filter(m => m.status === 'repairing').length
  const verifyingCount = list.filter(m => m.status === 'verifying').length
  const completedCount = list.filter(m => m.status === 'completed').length
  const overdueCount = list.filter(m => {
    if (m.status === 'completed' || m.status === 'cancelled') return false
    if (m.sla_remaining && (m.sla_remaining === '已超期' || m.sla_remaining === 'Overdue')) return true
    if (m.sla_deadline) {
      return new Date(m.sla_deadline) < new Date()
    }
    return false
  }).length
  return {
    total: totalCount,
    repairing: repairingCount,
    verifying: verifyingCount,
    completed: completedCount,
    overdue: overdueCount
  }
})

const filteredTotal = computed(() => filteredMaintenances.value.length)

const paginatedMaintenances = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredMaintenances.value.slice(start, end)
})

const getRepairingPercent = () => {
  if (stats.value.total === 0) return 0
  return Math.round((stats.value.repairing / stats.value.total) * 100)
}

const STATUS_COLORS = {
  'created': 'info',
  'diagnosing': 'primary',
  'repairing': 'warning',
  'verifying': '',
  'completed': 'success',
  'cancelled': 'danger'
}

const getStatusColor = (status) => STATUS_COLORS[status] || 'info'
const getStatusLabel = (status) => {
  const keyMap = {
    'created': 'maintStatusLabelCreated',
    'diagnosing': 'maintStatusLabelDiagnosing',
    'repairing': 'maintStatusLabelRepairing',
    'verifying': 'maintStatusLabelVerifying',
    'completed': 'maintStatusLabelCompleted',
    'cancelled': 'maintStatusLabelCancelled'
  }
  const key = keyMap[status]
  return key ? t(key) : status
}

const STATUS_PERCENT = {
  'created': 20,
  'diagnosing': 40,
  'repairing': 60,
  'verifying': 80,
  'completed': 100,
  'cancelled': 0
}

const getProgressPercent = (status) => STATUS_PERCENT[status] || 20

const getSlaText = (slaRemaining) => {
  if (!slaRemaining) return '--'
  if (slaRemaining === '已超期' || slaRemaining === 'Overdue') return t('maintSlaOverdue')
  return slaRemaining
}

const getPriorityBadgeClass = (priority) => priority || 'P3'

const isOverdue = (row) => {
  if (row.status === 'completed' || row.status === 'cancelled') return false
  if (row.sla_remaining && (row.sla_remaining === '已超期' || row.sla_remaining === 'Overdue')) return true
  if (row.sla_deadline) return new Date(row.sla_deadline) < new Date()
  return false
}

const isSlaCritical = (row) => {
  if (row.status === 'completed' || row.status === 'cancelled') return false
  if (row.sla_remaining) {
    const match = row.sla_remaining.match(/(\d+)h/)
    if (match && parseInt(match[1]) <= 4) return true
  }
  return false
}

const filterByStatus = (status) => {
  filterStatus.value = status
  currentPage.value = 1
  filterMaintenances()
}

const handlePageSizeChange = () => { currentPage.value = 1 }
const handlePageChange = () => {}

const tableRowClassName = ({ row }) => {
  if (row.status === 'cancelled') return 'cancelled-row'
  if (isOverdue(row)) return 'overdue-row'
  return ''
}

const viewDetail = (row) => { router.push(`/maintenance/${row.id}`) }

const ACTION_BUTTONS = {
  'created': { action: 'diagnosing', label: '开始诊断', icon: 'Search' },
  'diagnosing': { action: 'repairing', label: '开始维修', icon: 'Setting' },
  'repairing': { action: 'verifying', label: '提交验证', icon: 'CircleCheck' },
  'verifying': { action: 'completed', label: '完成维修', icon: 'SuccessFilled' },
  'completed': { action: null, label: '查看详情', icon: 'View' },
  'cancelled': { action: null, label: '查看详情', icon: 'View' }
}

const getNextAction = (status) => ACTION_BUTTONS[status]?.action || null
const getActionTooltip = (status) => ACTION_BUTTONS[status]?.label
const getActionIcon = (status) => ACTION_BUTTONS[status]?.icon || 'View'

const handleStatusAction = async (row) => {
  const nextAction = getNextAction(row.status)
  if (!nextAction) { viewDetail(row); return }
  const actionLabel = ACTION_BUTTONS[row.status]?.label
  try {
    const suggestResult = await api.post(`/maintenance/${row.id}/suggest-status`, {})
    await ElMessageBox.confirm(
      `是否执行「${actionLabel}」操作？\n状态将从「${suggestResult.current_status_label}」变为「${suggestResult.suggested_status_label || getNextStatusLabel(nextAction)}」`,
      '状态流转确认',
      { confirmButtonText: '确认', cancelButtonText: '取消', type: 'info' }
    )
    const result = await api.post(`/maintenance/${row.id}/auto-transition`, { status: nextAction, operator: 'Web' })
    ElMessage.success(result.message || `状态已更新为 ${result.status_label}`)
    await loadMaintenances()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || e.message)
  }
}

const getNextStatusLabel = (status) => {
  const labels = { 'diagnosing': '诊断', 'repairing': '维修', 'verifying': '验证', 'completed': '完成', 'cancelled': '取消' }
  return labels[status] || status
}

const openAddDialog = () => {
  editMaintData.value = null
  showAddDialog.value = true
}

const handleMaintSuccess = () => {
  clearCache('maintenance')
  loadMaintenances(true)
}

const getMaintTypeText = (type) => {
  const texts = { preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }
  return texts[type] || type || '--'
}

const filterMaintenances = () => {
  let result = [...maintenances.value]
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(m => m.device_name?.toLowerCase().includes(search) || m.maint_no?.toLowerCase().includes(search) || m.description?.toLowerCase().includes(search))
  }
  if (filterStatus.value) {
    if (filterStatus.value === 'overdue') result = result.filter(m => isOverdue(m))
    else result = result.filter(m => m.status === filterStatus.value)
  }
  if (filterPriority.value) result = result.filter(m => (m.priority || 'P3') === filterPriority.value)
  if (filterMaintType.value) result = result.filter(m => m.maint_type === filterMaintType.value)
  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0]), endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(m => { const mt = dayjs(m.maint_time || m.created_at); return mt.isAfter(startDate) && mt.isBefore(endDate) })
  }
  if (sortBy.value) {
    switch (sortBy.value) {
      case 'maint_time_desc': result.sort((a, b) => dayjs(b.maint_time || b.created_at) - dayjs(a.maint_time || a.created_at)); break
      case 'maint_time_asc': result.sort((a, b) => dayjs(a.maint_time || a.created_at) - dayjs(b.maint_time || b.created_at)); break
      case 'total_cost_desc': result.sort((a, b) => ((b.parts_cost || 0) + (b.labor_cost || 0)) - ((a.parts_cost || 0) + (a.labor_cost || 0))); break
      case 'total_cost_asc': result.sort((a, b) => ((a.parts_cost || 0) + (a.labor_cost || 0)) - ((b.parts_cost || 0) + (b.labor_cost || 0))); break
    }
  }
  filteredMaintenances.value = result
}

const loadMaintenances = debounce(async (force = false) => {
  loading.value = true
  try {
    const params = { limit: 500 }
    const data = await cachedRequest(
      () => getMaintenances(params),
      'maintenance',
      params,
      { forceRefresh: force }
    )
    maintenances.value = data.items || []; total.value = data.total || maintenances.value.length
    filterMaintenances()
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('maintLoadFailed'))
    }
  }
  finally { loading.value = false }
}, 300)

const loadDevices = async () => {
  try { const data = await getDevices(); devices.value = data.items || [] }
  catch (error) { ElMessage.error(t('maintDeviceLoadFailed')) }
}

const editMaintenance = (row) => {
  editMaintData.value = {
    id: row.id,
    device_id: row.device_id,
    maint_type: row.maint_type || 'corrective',
    spare_parts: row.spare_parts || [],
    parts_cost: row.parts_cost || 0,
    labor_hours: row.labor_hours || 0,
    labor_cost: row.labor_cost || 0,
    vendor: row.vendor || '',
    description: row.description || ''
  }
  showAddDialog.value = true
}

const deleteMaintenance = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('maintConfirmDeletePrompt')} "${row.maint_no}"?`, t('msgConfirmDelete'), { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' })
    await deleteMaintenanceApi(row.id); clearCache('maintenance'); ElMessage.success(t('maintDeleteSuccess')); loadMaintenances(true)
  } catch (error) { if (error !== 'cancel') ElMessage.error(t('maintDeleteFailed')) }
}

onMounted(() => { loadMaintenances(); loadDevices() })
</script>

<style scoped>
.maint-no-badge, .metric-value, .chip-count, .table-count, .progress-percent, .sla-text, .cost-value, .cost-currency, .time-text, .priority-text {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

.maintenance-page {
  padding: 0;
  background: linear-gradient(135deg, #f8fafc 0%, #e8f4fc 50%, #f0f7ff 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

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
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894);
}

.nav-left { display: flex; align-items: baseline; gap: 12px; }
.page-title { font-size: 20px; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em; }
.nav-right { display: flex; gap: 8px; }

.nav-action-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 8px;
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
  color: white; border: none; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(9, 132, 227, 0.25);
}
.nav-action-btn:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(9, 132, 227, 0.35); }
.nav-action-btn.secondary {
  background: rgba(255, 255, 255, 0.9); color: var(--text-secondary);
  border: 1px solid var(--border-default); box-shadow: none; padding: 8px 12px;
}
.nav-action-btn.secondary:hover { background: var(--bg-hover); color: var(--accent-primary); border-color: var(--accent-primary); }

.stats-dashboard {
  padding: 16px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(16px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.stats-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }

.stat-card {
  position: relative; display: flex; align-items: center; gap: 12px;
  padding: 18px; background: rgba(255, 255, 255, 0.95);
  border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.8);
  cursor: pointer; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); overflow: hidden;
}
.stat-card::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(9, 132, 227, 0.05) 100%);
  opacity: 0; transition: opacity 0.3s;
}
.stat-card:hover::before { opacity: 1; }
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 8px 32px rgba(0, 48, 135, 0.12); }

.card-content { display: flex; align-items: center; gap: 14px; width: 100%; }
.card-icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; transition: transform 0.3s;
}
.stat-card:hover .card-icon { transform: scale(1.05); }

.stat-card.total .card-icon { background: linear-gradient(135deg, rgba(9, 132, 227, 0.15) 0%, rgba(9, 132, 227, 0.08) 100%); color: #0984e3; }
.stat-card.repairing .card-icon { background: linear-gradient(135deg, rgba(225, 112, 85, 0.2) 0%, rgba(225, 112, 85, 0.1) 100%); color: #e17055; }
.stat-card.verifying .card-icon { background: linear-gradient(135deg, rgba(116, 185, 255, 0.2) 0%, rgba(116, 185, 255, 0.1) 100%); color: #74b9ff; }
.stat-card.completed .card-icon { background: linear-gradient(135deg, rgba(0, 184, 148, 0.2) 0%, rgba(0, 184, 148, 0.1) 100%); color: #00b894; }
.stat-card.overdue .card-icon { background: linear-gradient(135deg, rgba(214, 48, 49, 0.2) 0%, rgba(214, 48, 49, 0.1) 100%); color: #d63031; }

.card-body { flex: 1; }
.metric-value {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 28px; font-weight: 700; color: var(--text-primary);
  line-height: 1; letter-spacing: -0.02em;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
}
.metric-label { font-size: 12px; color: var(--text-tertiary); margin-top: 6px; font-weight: 500; }

.card-trend { width: 24px; height: 24px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 12px; }
.card-trend.stable { background: rgba(9, 132, 227, 0.1); color: #0984e3; }
.card-trend.warning { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.card-trend.success { background: rgba(0, 184, 148, 0.1); color: #00b894; }
.card-trend.info { background: rgba(116, 185, 255, 0.1); color: #74b9ff; }

.card-progress { width: 24px; height: 24px; position: relative; }
.progress-ring {
  width: 24px; height: 24px; border-radius: 50%;
  background: conic-gradient(#e17055 calc(var(--percent) * 1%), rgba(225, 112, 85, 0.2) 0);
}
.progress-ring::after { content: ''; width: 16px; height: 16px; border-radius: 50%; background: white; }

.filter-section {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 12px rgba(0, 48, 135, 0.06);
}

.filter-toolbar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.search-box { position: relative; display: flex; align-items: center; }
.search-icon { position: absolute; left: 12px; color: var(--text-tertiary); font-size: 14px; z-index: 1; }
.search-input { width: 240px; }
.search-input :deep(.el-input__wrapper) {
  padding-left: 36px; background: rgba(255, 255, 255, 0.95);
  border-radius: 8px; border: 1px solid var(--border-default); box-shadow: none; transition: all 0.25s;
}
.search-input :deep(.el-input__wrapper:hover) { border-color: var(--accent-primary); }
.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary); box-shadow: 0 0 0 3px rgba(9, 132, 227, 0.15);
}

.status-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.status-chip {
  display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  background: rgba(255, 255, 255, 0.9); border-radius: 8px;
  border: 1px solid var(--border-default); cursor: pointer;
  transition: all 0.25s ease; position: relative; overflow: hidden;
}
.status-chip::before {
  content: ''; position: absolute; bottom: 0; left: 50%; right: 50%;
  height: 2px; background: currentColor; transition: all 0.25s ease;
}
.status-chip:hover::before, .status-chip.active::before { left: 0; right: 0; }
.status-chip:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0, 48, 135, 0.1); }
.status-chip.active { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); color: #0984e3; }

.chip-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.chip-label { font-size: 12px; font-weight: 500; color: var(--text-secondary); }
.status-chip.active .chip-label { color: #0984e3; }
.chip-count {
  font-size: 11px; font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--text-tertiary); padding: 2px 6px; background: rgba(0, 48, 135, 0.05); border-radius: 4px;
}

.status-chip.chip-created .chip-dot { background: #0984e3; }
.status-chip.chip-diagnosing .chip-dot { background: #0984e3; }
.status-chip.chip-repairing .chip-dot { background: #e17055; }
.status-chip.chip-verifying .chip-dot { background: #74b9ff; }
.status-chip.chip-completed .chip-dot { background: #00b894; }
.status-chip.chip-overdue .chip-dot { background: #d63031; }
.status-chip.chip-created:hover { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); }
.status-chip.chip-diagnosing:hover { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); }
.status-chip.chip-repairing:hover { background: rgba(225, 112, 85, 0.08); border-color: rgba(225, 112, 85, 0.3); }
.status-chip.chip-verifying:hover { background: rgba(116, 185, 255, 0.08); border-color: rgba(116, 185, 255, 0.3); }
.status-chip.chip-completed:hover { background: rgba(0, 184, 148, 0.12); border-color: rgba(0, 184, 148, 0.4); }
.status-chip.chip-overdue:hover { background: rgba(214, 48, 49, 0.08); border-color: rgba(214, 48, 49, 0.3); }

.more-filters { display: flex; gap: 8px; margin-left: auto; }
.more-filters :deep(.el-select .el-input__wrapper) { background: rgba(255, 255, 255, 0.95); border-radius: 8px; border: 1px solid var(--border-default); box-shadow: none; }
.more-filters :deep(.el-date-editor) { background: rgba(255, 255, 255, 0.95); border-radius: 8px; border: 1px solid var(--border-default); box-shadow: none; }

.data-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.table-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid rgba(0, 48, 135, 0.08); }
.table-title { font-size: 13px; font-weight: 600; color: var(--text-secondary); letter-spacing: 0.03em; }
.table-count { font-size: 12px; color: var(--text-tertiary); font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

.enterprise-table { width: 100%; }
.enterprise-table :deep(.el-table__inner-wrapper::before) { display: none; }
.enterprise-table :deep(.el-table__header-wrapper) { border-bottom: 2px solid rgba(0, 48, 135, 0.1); }
.enterprise-table :deep(th.el-table__cell) {
  background: transparent; font-size: 11px; font-weight: 600; color: var(--text-tertiary);
  letter-spacing: 0.03em; padding: 12px 0; border-bottom: none;
}
.enterprise-table :deep(td.el-table__cell) { border-bottom: 1px solid rgba(0, 48, 135, 0.06); padding: 10px 0; background: transparent; }
.enterprise-table :deep(.el-table__row) { transition: all 0.25s ease; background: transparent; }
.enterprise-table :deep(.el-table__row:hover > td) { background: rgba(9, 132, 227, 0.04) !important; }
.enterprise-table :deep(.overdue-row > td) { background: rgba(239, 68, 68, 0.04) !important; }
.enterprise-table :deep(.cancelled-row) { opacity: 0.6; }

.maint-no-link { display: flex; align-items: center; gap: 8px; color: var(--accent-primary); text-decoration: none; transition: all 0.25s; }
.maint-no-link:hover { color: var(--accent-secondary); }
.maint-no-badge {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600; font-size: 13px; padding: 4px 8px; background: rgba(9, 132, 227, 0.08);
  border-radius: 6px; transition: all 0.25s;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; letter-spacing: 0.02em;
}
.maint-no-link:hover .maint-no-badge { background: rgba(9, 132, 227, 0.15); }
.link-arrow { opacity: 0; font-size: 12px; transition: all 0.25s; color: var(--accent-primary); }
.maint-no-link:hover .link-arrow { opacity: 1; transform: translateX(4px); }

.status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500; background: rgba(255, 255, 255, 0.95); border: 1px solid; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.status-text { letter-spacing: 0.02em; }
.status-badge.created { border-color: rgba(9, 132, 227, 0.3); color: #0984e3; }
.status-badge.created .status-dot { background: #0984e3; }
.status-badge.diagnosing { border-color: rgba(9, 132, 227, 0.3); color: #0984e3; }
.status-badge.diagnosing .status-dot { background: #0984e3; }
.status-badge.repairing { border-color: rgba(225, 112, 85, 0.3); color: #e17055; }
.status-badge.repairing .status-dot { background: #e17055; }
.status-badge.verifying { border-color: rgba(116, 185, 255, 0.3); color: #74b9ff; }
.status-badge.verifying .status-dot { background: #74b9ff; }
.status-badge.completed { border-color: rgba(0, 184, 148, 0.4); color: #00b894; }
.status-badge.completed .status-dot { background: #00b894; }
.status-badge.cancelled { border-color: rgba(45, 52, 54, 0.3); color: #636e72; }
.status-badge.cancelled .status-dot { background: #636e72; }

.priority-badge { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.priority-icon { font-size: 12px; }
.priority-badge.P1 { background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.08) 100%); border: 1px solid rgba(239, 68, 68, 0.3); color: #ef4444; }
.priority-badge.P2 { background: linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(251, 191, 36, 0.08) 100%); border: 1px solid rgba(251, 191, 36, 0.3); color: #f59e0b; }
.priority-badge.P3 { background: linear-gradient(135deg, rgba(9, 132, 227, 0.12) 0%, rgba(9, 132, 227, 0.06) 100%); border: 1px solid rgba(9, 132, 227, 0.25); color: #0984e3; }
.priority-badge.P4 { background: linear-gradient(135deg, rgba(0, 184, 148, 0.12) 0%, rgba(0, 184, 148, 0.06) 100%); border: 1px solid rgba(0, 184, 148, 0.25); color: #00b894; }

.device-cell { display: flex; align-items: center; gap: 8px; }
.device-icon { font-size: 14px; color: var(--text-tertiary); }
.device-name { font-size: 13px; color: var(--text-secondary); }

.owner-cell { display: flex; align-items: center; gap: 8px; }
.owner-avatar {
  width: 24px; height: 24px; border-radius: 6px;
  background: linear-gradient(135deg, #0984e3, #74b9ff); color: white;
  font-size: 11px; font-weight: 600; display: flex; align-items: center; justify-content: center;
}
.owner-name { font-size: 13px; color: var(--text-secondary); }

.type-badge { display: inline-flex; align-items: center; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 500; }
.type-badge.preventive { background: rgba(0, 184, 148, 0.08); color: #00b894; }
.type-badge.corrective { background: rgba(225, 112, 85, 0.08); color: #e17055; }
.type-badge.upgrade { background: rgba(9, 132, 227, 0.08); color: #0984e3; }
.type-badge.emergency { background: rgba(239, 68, 68, 0.08); color: #ef4444; }
.type-badge.other { background: rgba(45, 52, 54, 0.08); color: #636e72; }

.progress-cell { display: flex; align-items: center; gap: 10px; }
.progress-bar-bg { width: 70px; height: 6px; background: rgba(0, 48, 135, 0.08); border-radius: 3px; overflow: hidden; }
.progress-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s ease; }
.progress-bar-fill.created { background: linear-gradient(90deg, #74b9ff, #a8d8ff); }
.progress-bar-fill.diagnosing { background: linear-gradient(90deg, #0984e3, #74b9ff); }
.progress-bar-fill.repairing { background: linear-gradient(90deg, #e17055, #fab1a0); }
.progress-bar-fill.verifying { background: linear-gradient(90deg, #74b9ff, #a8d8ff); }
.progress-bar-fill.completed { background: linear-gradient(90deg, #00b894, #55efc4); }
.progress-bar-fill.cancelled { background: linear-gradient(90deg, #636e72, #b2bec3); }
.progress-percent { font-size: 11px; color: var(--text-tertiary); font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-weight: 500; }

.sla-cell { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-secondary); font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.sla-cell.overdue { color: #ef4444; background: rgba(239, 68, 68, 0.08); padding: 2px 8px; border-radius: 6px; }
.sla-cell.critical { color: #f59e0b; }
.sla-icon { font-size: 12px; }

.cost-cell { display: flex; align-items: center; gap: 2px; }
.cost-currency { font-size: 11px; color: var(--text-tertiary); }
.cost-value { font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 13px; color: var(--text-secondary); font-weight: 500; }

.time-cell { display: flex; align-items: center; gap: 8px; }
.time-icon { font-size: 13px; color: var(--text-tertiary); }
.time-text { font-size: 12px; color: var(--text-secondary); font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

.action-group { display: flex; gap: 4px; }
.action-btn {
  width: 28px; height: 28px; border-radius: 6px; border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.9); color: var(--text-tertiary);
  cursor: pointer; transition: all 0.25s ease; display: flex; align-items: center; justify-content: center;
}
.action-btn:hover { transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0, 48, 135, 0.15); }
.action-btn.view:hover { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.2); color: #0984e3; }
.action-btn.advance:hover { background: rgba(225, 112, 85, 0.08); border-color: rgba(225, 112, 85, 0.2); color: #e17055; }
.action-btn.delete:hover { background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.2); color: #ef4444; }

.pagination-bar { margin-top: 16px; padding-top: 12px; border-top: 1px solid rgba(0, 48, 135, 0.06); display: flex; justify-content: flex-end; }
.pagination-bar :deep(.el-pagination) { gap: 8px; }
.pagination-bar :deep(.el-pagination button), .pagination-bar :deep(.el-pager li) {
  background: rgba(255, 255, 255, 0.95); border-radius: 6px; border: 1px solid var(--border-default);
  font-size: 12px; font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.pagination-bar :deep(.el-pager li.is-active) { background: linear-gradient(135deg, #0984e3, #74b9ff); border-color: transparent; color: white; }

.edit-dialog-content { display: flex; flex-direction: column; gap: 16px; }
.form-section { background: rgba(0, 48, 135, 0.04); border-radius: 10px; padding: 16px; border: 1px solid rgba(0, 48, 135, 0.08); }
.form-section-title { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 12px; }

.spare-parts-section { width: 100%; }
.spare-search { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.spare-tip { font-size: 12px; color: var(--el-text-color-secondary); padding: 4px 8px; background: var(--el-fill-color-light); border-radius: 4px; }
.selected-parts { margin-top: 12px; }
.no-parts-tip { display: flex; align-items: center; gap: 8px; padding: 12px 16px; background: #f5f7fa; border-radius: 4px; color: #909399; font-size: 13px; margin-top: 12px; }
.parts-summary { margin-top: 10px; padding: 8px 12px; background: #f5f7fa; border-radius: 4px; text-align: right; }
.total-cost { font-weight: 600; color: #409EFF; font-size: 16px; }
.spare-option { display: flex; align-items: center; gap: 12px; }
.spare-number { font-weight: 500; color: #409EFF; }
.spare-name { color: #606266; }
.spare-stock { font-size: 12px; color: #909399; }
.spare-stock.low { color: #F56C6C; font-weight: 500; }

.return-parts-section { width: 100%; }
.return-found-info { margin-bottom: 16px; }
.found-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.found-actions { display: flex; align-items: center; gap: 10px; margin-top: 12px; }
.return-manual-area { margin-bottom: 12px; }
.return-manual-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.return-manual-tip { font-size: 12px; color: var(--el-text-color-secondary); padding: 4px 8px; background: var(--el-fill-color-light); border-radius: 4px; }
.return-parts-table { margin-top: 8px; }
.scrap-label { margin-left: 8px; font-size: 12px; color: #909399; }
.scrap-label.no-id { color: #E6A23C; }
.return-tip { margin-top: 10px; padding: 8px 12px; background: #fdf6ec; border-radius: 4px; color: #909399; font-size: 12px; }
.no-return-tip { margin-top: 8px; }

.scan-action-bar {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  background: linear-gradient(135deg, var(--color-gb) 0%, var(--color-gb-mid) 100%);
  border-radius: var(--radius-md); margin-bottom: 16px;
}
.scan-action-bar.return { background: linear-gradient(135deg, #636e72 0%, #4a5455 100%); }
.scan-action-bar .scan-btn {
  background: rgba(255,255,255,0.15); border-color: rgba(255,255,255,0.3);
  color: #fff; font-weight: 600; height: 36px; border-radius: 8px; transition: all 0.2s;
}
.scan-action-bar .scan-btn:hover { background: rgba(255,255,255,0.25); transform: translateY(-1px); }
.scan-tip-badge { display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: rgba(255,255,255,0.1); border-radius: 4px; color: rgba(255,255,255,0.9); font-size: 12px; }

@media (max-width: 1200px) { .stats-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .filter-toolbar { flex-direction: column; align-items: stretch; }
  .status-chips { justify-content: center; }
  .more-filters { justify-content: center; margin-left: 0; }
  .page-nav-bar { flex-direction: column; gap: 12px; }
  .nav-right { width: 100%; justify-content: center; }
}

.dark .maintenance-page { background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #161b22 100%); }
.dark .page-nav-bar { background: rgba(22, 27, 34, 0.9); border-color: rgba(48, 54, 61, 0.8); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); }
.dark .page-nav-bar::before { background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894); }
.dark .page-title { color: #f0f6fc; }
.dark .nav-action-btn { background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%); }
.dark .nav-action-btn.secondary { background: rgba(48, 54, 61, 0.8); color: #8b949e; border-color: #30363d; }
.dark .nav-action-btn.secondary:hover { background: rgba(9, 132, 227, 0.15); border-color: #0984e3; color: #58a6ff; }
.dark .stats-dashboard { background: rgba(22, 27, 34, 0.85); border-color: rgba(48, 54, 61, 0.6); box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4); }
.dark .stat-card { background: rgba(13, 17, 23, 0.95); border-color: rgba(48, 54, 61, 0.6); }
.dark .stat-card:hover { background: rgba(22, 27, 34, 0.95); box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5); }
.dark .metric-value { color: #f0f6fc; }
.dark .metric-label { color: #8b949e; }
.dark .card-trend.stable { background: rgba(9, 132, 227, 0.2); color: #58a6ff; }
.dark .card-trend.warning { background: rgba(239, 68, 68, 0.2); color: #f85149; }
.dark .card-trend.success { background: rgba(0, 184, 148, 0.2); color: #3fb950; }
.dark .card-trend.info { background: rgba(116, 185, 255, 0.2); color: #74b9ff; }
.dark .progress-ring { background: conic-gradient(#e17055 calc(var(--percent) * 1%), rgba(225, 112, 85, 0.3) 0); }
.dark .progress-ring::after { background: #0d1117; }
.dark .filter-section { background: rgba(22, 27, 34, 0.85); border-color: rgba(48, 54, 61, 0.6); box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3); }
.dark .search-input :deep(.el-input__wrapper) { background: rgba(13, 17, 23, 0.95); border-color: #30363d; }
.dark .search-input :deep(.el-input__wrapper:hover), .dark .search-input :deep(.el-input__wrapper.is-focus) { border-color: #58a6ff; box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15); }
.dark .search-icon { color: #8b949e; }
.dark .status-chip { background: rgba(13, 17, 23, 0.9); border-color: #30363d; }
.dark .status-chip:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3); }
.dark .chip-label { color: #8b949e; }
.dark .status-chip.active { background: rgba(88, 166, 255, 0.15); border-color: rgba(88, 166, 255, 0.4); color: #58a6ff; }
.dark .status-chip.active .chip-label { color: #58a6ff; }
.dark .chip-count { background: rgba(48, 54, 61, 0.3); color: #8b949e; }
.dark .more-filters :deep(.el-select .el-input__wrapper), .dark .more-filters :deep(.el-date-editor) { background: rgba(13, 17, 23, 0.95); border-color: #30363d; }
.dark .status-badge { background: rgba(13, 17, 23, 0.9); }
.dark .status-badge.created { border-color: rgba(88, 166, 255, 0.4); color: #58a6ff; }
.dark .status-badge.created .status-dot { background: #58a6ff; }
.dark .status-badge.diagnosing { border-color: rgba(88, 166, 255, 0.4); color: #58a6ff; }
.dark .status-badge.diagnosing .status-dot { background: #58a6ff; }
.dark .status-badge.repairing { border-color: rgba(225, 112, 85, 0.4); color: #e17055; }
.dark .status-badge.repairing .status-dot { background: #e17055; }
.dark .status-badge.verifying { border-color: rgba(116, 185, 255, 0.4); color: #74b9ff; }
.dark .status-badge.verifying .status-dot { background: #74b9ff; }
.dark .status-badge.completed { border-color: rgba(63, 185, 80, 0.4); color: #3fb950; }
.dark .status-badge.completed .status-dot { background: #3fb950; }
.dark .status-badge.cancelled { border-color: rgba(139, 148, 158, 0.4); color: #8b949e; }
.dark .status-badge.cancelled .status-dot { background: #8b949e; }
.dark .priority-badge.P1 { background: rgba(248, 81, 73, 0.15); border-color: rgba(248, 81, 73, 0.4); color: #f85149; }
.dark .priority-badge.P2 { background: rgba(210, 153, 34, 0.15); border-color: rgba(210, 153, 34, 0.4); color: #d29922; }
.dark .priority-badge.P3 { background: rgba(88, 166, 255, 0.15); border-color: rgba(88, 166, 255, 0.4); color: #58a6ff; }
.dark .priority-badge.P4 { background: rgba(63, 185, 80, 0.15); border-color: rgba(63, 185, 80, 0.4); color: #3fb950; }
.dark .type-badge.preventive { background: rgba(63, 185, 80, 0.15); color: #3fb950; }
.dark .type-badge.corrective { background: rgba(225, 112, 85, 0.15); color: #e17055; }
.dark .type-badge.upgrade { background: rgba(88, 166, 255, 0.15); color: #58a6ff; }
.dark .type-badge.emergency { background: rgba(248, 81, 73, 0.15); color: #f85149; }
.dark .type-badge.other { background: rgba(139, 148, 158, 0.15); color: #8b949e; }
.dark .data-section { background: rgba(22, 27, 34, 0.85); border-color: rgba(48, 54, 61, 0.6); box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4); }
.dark .table-header { border-bottom-color: rgba(48, 54, 61, 0.6); }
.dark .table-title { color: #8b949e; }
.dark .table-count { color: #6e7681; }
.dark .enterprise-table :deep(.el-table__header-wrapper) { border-bottom-color: rgba(48, 54, 61, 0.6); }
.dark .enterprise-table :deep(th.el-table__cell) { color: #8b949e; }
.dark .enterprise-table :deep(td.el-table__cell) { border-bottom-color: rgba(48, 54, 61, 0.3); }
.dark .enterprise-table :deep(.el-table__row:hover > td) { background: rgba(88, 166, 255, 0.08) !important; }
.dark .enterprise-table :deep(.overdue-row > td) { background: rgba(248, 81, 73, 0.08) !important; }
.dark .maint-no-link { color: #58a6ff; }
.dark .maint-no-badge { background: rgba(88, 166, 255, 0.15); }
.dark .maint-no-link:hover .maint-no-badge { background: rgba(88, 166, 255, 0.25); }
.dark .device-name { color: #c9d1d9; }
.dark .owner-name { color: #8b949e; }
.dark .owner-avatar { background: linear-gradient(135deg, #0984e3, #74b9ff); }
.dark .progress-bar-bg { background: rgba(48, 54, 61, 0.5); }
.dark .progress-percent { color: #8b949e; }
.dark .sla-cell { color: #8b949e; }
.dark .sla-cell.overdue { background: rgba(248, 81, 73, 0.15); color: #f85149; }
.dark .sla-cell.critical { color: #d29922; }
.dark .cost-value { color: #8b949e; }
.dark .cost-currency { color: #6e7681; }
.dark .time-text { color: #8b949e; }
.dark .pagination-bar { border-top-color: rgba(48, 54, 61, 0.3); }
.dark .pagination-bar :deep(.el-pagination button), .dark .pagination-bar :deep(.el-pager li) { background: rgba(13, 17, 23, 0.95); border-color: #30363d; color: #8b949e; }
.dark .pagination-bar :deep(.el-pager li.is-active) { background: linear-gradient(135deg, #0984e3, #74b9ff); color: white; }
.dark .action-btn { background: rgba(13, 17, 23, 0.9); color: #8b949e; border-color: transparent; }
.dark .action-btn:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4); }
.dark .action-btn.view:hover { background: rgba(88, 166, 255, 0.15); border-color: rgba(88, 166, 255, 0.3); color: #58a6ff; }
.dark .action-btn.advance:hover { background: rgba(225, 112, 85, 0.15); border-color: rgba(225, 112, 85, 0.3); color: #e17055; }
.dark .action-btn.delete:hover { background: rgba(248, 81, 73, 0.15); border-color: rgba(248, 81, 73, 0.3); color: #f85149; }
.dark .form-section { background: rgba(13, 17, 23, 0.6); border-color: rgba(48, 54, 61, 0.4); }
.dark .form-section-title { color: #8b949e; }
.dark .no-parts-tip { background: rgba(13, 17, 23, 0.6); color: #8b949e; }
.dark .parts-summary { background: rgba(13, 17, 23, 0.6); }
.dark .spare-tip { background: rgba(13, 17, 23, 0.6); color: #8b949e; }
.dark .return-manual-tip { background: rgba(13, 17, 23, 0.6); color: #8b949e; }
.dark .return-tip { background: rgba(13, 17, 23, 0.6); color: #8b949e; }

/* 添加维修记录对话框样式 */
.maint-add-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}
.maint-add-dialog .section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
}
.maint-add-dialog .section-header .el-icon {
  color: var(--accent-primary);
}
.maint-add-dialog .section-action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.maint-add-dialog .unit-text {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: 4px;
}
.maint-add-dialog .el-form-item {
  margin-bottom: 10px;
}
.maint-add-dialog .el-form-item__label {
  font-size: 13px;
}

/* 紧凑对话框样式 */
.compact-dialog .el-form-item {
  margin-bottom: 12px;
}
.compact-dialog .el-divider {
  margin: 16px 0 12px;
}
.compact-dialog .spare-row,
.compact-dialog .return-row {
  display: flex;
  gap: 8px;
  align-items: center;
}
.compact-dialog .el-table {
  margin-top: 8px;
}
.compact-dialog .el-checkbox {
  margin-right: 8px;
}
</style>
