<template>
  <div class="faults-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuFaults') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn" @click="openAddDialog">
          <el-icon><Plus /></el-icon>
          <span>{{ t('faultAdd') }}</span>
        </button>
        <button class="nav-action-btn secondary" @click="loadFaults" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-grid">
        <!-- 总故障 -->
        <div class="stat-card total" @click="filterByStatus('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.total }}</div>
              <div class="metric-label">{{ t('faultStatsTotal') }}</div>
            </div>
            <div class="card-trend stable">
              <span class="trend-icon">●</span>
            </div>
          </div>
        </div>
        <!-- 待处理 -->
        <div class="stat-card pending" @click="filterByStatusGroup('pending')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.pending }}</div>
              <div class="metric-label">{{ t('faultStatsPending') }}</div>
            </div>
            <div class="card-trend warning" v-if="stats.pending > 0">
              <el-icon><Warning /></el-icon>
            </div>
          </div>
        </div>
        <!-- 处理中 -->
        <div class="stat-card processing" @click="filterByStatusGroup('processing')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Setting /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.processing }}</div>
              <div class="metric-label">{{ t('faultStatsProcessing') }}</div>
            </div>
            <div class="card-progress">
              <div class="progress-ring" :style="{ '--percent': getProcessingPercent() }"></div>
            </div>
          </div>
        </div>
        <!-- 已解决 -->
        <div class="stat-card resolved" @click="filterByStatus('resolved')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.resolved }}</div>
              <div class="metric-label">{{ t('faultStatsResolved') }}</div>
            </div>
            <div class="card-trend success">
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
        <!-- 已关闭 -->
        <div class="stat-card closed" @click="filterByStatus('closed')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><SuccessFilled /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.closed }}</div>
              <div class="metric-label">{{ t('faultStatsClosed') }}</div>
            </div>
            <div class="card-trend done">
              <el-icon><SuccessFilled /></el-icon>
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
            :placeholder="t('faultSearchPlaceholder')"
            class="search-input"
            clearable
            @input="filterFaults"
          />
        </div>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <div
            :class="['status-chip', { active: filterStatus === '' }]"
            @click="filterByStatus('')"
          >
            <span class="chip-label">{{ t('faultFilterAll') }}</span>
            <span class="chip-count">{{ stats.total }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-open', { active: filterStatus === 'open' }]"
            @click="filterByStatus('open')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('faultStatusOpen') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-assigned', { active: filterStatus === 'assigned' }]"
            @click="filterByStatus('assigned')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('faultStatusAssigned') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-diagnosing', { active: filterStatus === 'diagnosing' }]"
            @click="filterByStatus('diagnosing')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('faultStatusDiagnosing') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-transferred', { active: filterStatus === 'transferred' }]"
            @click="filterByStatus('transferred')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('faultStatusTransferred') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-resolved', { active: filterStatus === 'resolved' }]"
            @click="filterByStatus('resolved')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('faultStatusResolved') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-closed', { active: filterStatus === 'closed' }]"
            @click="filterByStatus('closed')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('faultStatusClosed') }}</span>
          </div>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-select v-model="filterPriority" :placeholder="t('faultPriority')" clearable style="width: 90px" @change="filterFaults">
            <el-option label="P1" value="P1" />
            <el-option label="P2" value="P2" />
            <el-option label="P3" value="P3" />
            <el-option label="P4" value="P4" />
          </el-select>
          <el-select v-model="filterType" :placeholder="t('faultType')" clearable style="width: 120px" @change="filterFaults">
            <el-option :label="t('faultTypeHardware')" value="hardware" />
            <el-option :label="t('faultTypeSoftware')" value="software" />
            <el-option :label="t('faultTypeConfig')" value="config" />
            <el-option :label="t('faultTypeNetwork')" value="network" />
            <el-option :label="t('faultTypeOther')" value="other" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :range-separator="t('faultToDate')"
            :start-placeholder="t('faultStartDate')"
            :end-placeholder="t('faultEndDate')"
            value-format="YYYY-MM-DD"
            style="width: 220px"
            @change="filterFaults"
          />
        </div>
      </div>
    </section>

    <!-- 故障数据面板 -->
    <section class="data-section">
      <div class="table-header">
        <span class="table-title">Incident List</span>
        <span class="table-count">{{ filteredTotal }} records</span>
      </div>

      <el-table
        :data="paginatedFaults"
        class="enterprise-table"
        v-loading="loading"
        :row-class-name="tableRowClassName"
        :header-cell-style="{ background: 'transparent' }"
      >
        <!-- 故障单号 -->
        <el-table-column prop="fault_no" :label="t('faultNo')" width="220">
          <template #default="{ row }">
            <router-link :to="`/faults/${row.id}`" class="fault-no-link">
              <span class="fault-no-badge">{{ row.fault_no }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>

        <!-- 状态 -->
        <el-table-column prop="status" :label="t('faultStatusLabel')" width="100">
          <template #default="{ row }">
            <div :class="['status-badge', row.status]">
              <span class="status-dot"></span>
              <span class="status-text">{{ getStatusLabel(row.status) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 优先级 -->
        <el-table-column prop="priority" :label="t('faultPriority')" width="90">
          <template #default="{ row }">
            <div :class="['priority-badge', getPriorityFromSeverity(row.severity)]">
              <span class="priority-icon">
                <el-icon v-if="getPriorityFromSeverity(row.severity) === 'P1'"><Warning /></el-icon>
                <el-icon v-else-if="getPriorityFromSeverity(row.severity) === 'P2'"><InfoFilled /></el-icon>
              </span>
              <span class="priority-text">{{ getPriorityFromSeverity(row.severity) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 设备 -->
        <el-table-column prop="device_name" :label="t('faultDevice')" width="180">
          <template #default="{ row }">
            <div class="device-cell">
              <el-icon class="device-icon"><Connection /></el-icon>
              <span class="device-name">{{ row.device_name }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 负责人 -->
        <el-table-column prop="assigned_to" :label="t('faultOwner')" width="120">
          <template #default="{ row }">
            <div class="owner-cell">
              <div class="owner-avatar">{{ (row.assigned_to || '?')[0] }}</div>
              <span class="owner-name">{{ row.assigned_to || t('faultOwnerUnassigned') }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 类型 -->
        <el-table-column prop="fault_type" :label="t('faultType')" width="120">
          <template #default="{ row }">
            <div :class="['type-badge', row.fault_type]">
              <span class="type-text">{{ getFaultTypeLabel(row.fault_type) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 进度 -->
        <el-table-column prop="progress_percent" :label="t('faultProgress')" width="140">
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
        <el-table-column prop="sla_remaining" :label="t('faultSlaDeadline')" width="100">
          <template #default="{ row }">
            <div :class="['sla-cell', { overdue: isOverdue(row), critical: isSlaCritical(row) }]">
              <el-icon v-if="isOverdue(row)" class="sla-icon"><Warning /></el-icon>
              <span class="sla-text">{{ getSlaText(row.sla_remaining) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 关联维修成本 -->
        <el-table-column prop="maintenance_cost" :label="t('faultTotalCost')" width="120">
          <template #default="{ row }">
            <div class="cost-cell">
              <span class="cost-currency">¥</span>
              <span class="cost-value" v-if="row.maintenance_cost">{{ row.maintenance_cost.toFixed(2) }}</span>
              <span class="cost-value empty" v-else>--</span>
            </div>
          </template>
        </el-table-column>

        <!-- 时间 -->
        <el-table-column prop="created_at" :label="t('faultOccurTime')" width="180">
          <template #default="{ row }">
            <div class="time-cell">
              <el-icon class="time-icon"><Clock /></el-icon>
              <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column :label="t('faultAction')" width="160" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <button class="action-btn view" @click="viewDetail(row)" title="查看详情">
                <el-icon><View /></el-icon>
              </button>
              <button class="action-btn locate" @click="locateDevice(row)" v-if="row.device_id" title="定位设备">
                <el-icon><Aim /></el-icon>
              </button>
              <button class="action-btn edit" @click="editFault(row)" v-if="row.status !== 'closed'" title="编辑">
                <el-icon><Edit /></el-icon>
              </button>
              <button class="action-btn delete" @click="deleteFaultRecord(row)" v-if="row.status === 'open'" title="删除">
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

    <!-- 添加故障对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('faultEditRecord') : t('faultAddRecord')" width="650px" class="edit-fault-dialog">
      <div class="edit-dialog-content">
        <!-- 基础信息 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Warning /></el-icon>
            {{ t('faultBasicInfo') || '基础信息' }}
          </div>
          <el-form :model="faultForm" label-width="100px">
            <el-form-item :label="t('faultDeviceLabel')" required>
              <el-select v-model="faultForm.device_id" :placeholder="t('faultSelectDevice')" style="width: 100%" :disabled="editMode" filterable>
                <el-option
                  v-for="device in devices"
                  :key="device.id"
                  :label="device.name"
                  :value="device.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('faultAssignTo')">
              <el-select v-model="faultForm.assigned_to" :placeholder="t('faultAssignPlaceholder')" style="width: 100%" clearable>
                <el-option v-for="user in users" :key="user" :label="user" :value="user" />
              </el-select>
              <div class="assign-tip">{{ t('faultAssignTip') || '指派后将自动通知负责人' }}</div>
            </el-form-item>
            <el-form-item :label="t('faultType')">
              <el-select v-model="faultForm.fault_type" clearable style="width: 100%">
                <el-option :label="t('faultTypeHardware')" value="hardware" />
                <el-option :label="t('faultTypeSoftware')" value="software" />
                <el-option :label="t('faultTypeConfig')" value="config" />
                <el-option :label="t('faultTypeNetwork')" value="network" />
                <el-option :label="t('faultTypeOther')" value="other" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('faultPriority')" required>
              <el-select v-model="faultForm.severity" style="width: 100%">
                <el-option label="P1 - Critical" value="critical" />
                <el-option label="P2 - Major" value="major" />
                <el-option label="P3 - Minor" value="minor" />
                <el-option label="P4 - Warning" value="warning" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('faultStatus')" v-if="editMode">
              <el-select v-model="faultForm.status" style="width: 100%">
                <el-option :label="t('faultStatusOpen')" value="open" />
                <el-option :label="t('faultStatusAssigned')" value="assigned" />
                <el-option :label="t('faultStatusDiagnosing')" value="diagnosing" />
                <el-option :label="t('faultStatusTransferred')" value="transferred" />
                <el-option :label="t('faultStatusResolved')" value="resolved" />
                <el-option :label="t('faultStatusClosed')" value="closed" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('faultDowntimeMinutes')">
              <el-input-number v-model="faultForm.downtime_minutes" :min="0" style="width: 100%" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 影响与描述 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Document /></el-icon>
            {{ t('faultImpactDesc') || '影响与描述' }}
          </div>
          <el-form :model="faultForm" label-width="100px">
            <el-form-item :label="t('faultImpact')">
              <el-input v-model="faultForm.impact" type="textarea" :rows="2" :placeholder="t('faultImpactPlaceholder')" />
            </el-form-item>
            <el-form-item :label="t('faultDescription')" required>
              <el-input v-model="faultForm.description" type="textarea" :rows="4" :placeholder="t('faultDescPlaceholder')" />
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateFault() : addFault()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Refresh, Document, Clock, CircleCheck, SuccessFilled, ArrowRight, Edit, View, Delete, Setting, Warning, InfoFilled, Connection, Aim } from '@element-plus/icons-vue'
import { getFaults, getDevices, createFault, updateFault as updateFaultApi, deleteFault } from '@/api'
import { formatDateTime, dayjs } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const router = useRouter()

const faults = ref([])
const filteredFaults = ref([])
const devices = ref([])
const users = ref(['Vayne', '张工', '李工', '王工', '运维组'])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const editMode = ref(false)

const searchText = ref('')
const filterPriority = ref('')
const filterType = ref('')
const filterStatus = ref('')
const dateRange = ref([])

// 统计数据 - 按状态分组
const stats = computed(() => {
  const list = faults.value
  const totalCount = list.length
  const pendingCount = list.filter(f => ['open', 'assigned'].includes(f.status)).length
  const processingCount = list.filter(f => ['accepted', 'diagnosing', 'resolving', 'transferred'].includes(f.status)).length
  const resolvedCount = list.filter(f => f.status === 'resolved').length
  const closedCount = list.filter(f => f.status === 'closed').length
  return {
    total: totalCount,
    pending: pendingCount,
    processing: processingCount,
    resolved: resolvedCount,
    closed: closedCount
  }
})

const filteredTotal = computed(() => filteredFaults.value.length)

// 分页后的数据
const paginatedFaults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredFaults.value.slice(start, end)
})

// 处理中百分比
const getProcessingPercent = () => {
  if (stats.value.total === 0) return 0
  return Math.round((stats.value.processing / stats.value.total) * 100)
}

// 状态颜色映射
const STATUS_COLORS = {
  'open': 'info',
  'assigned': 'primary',
  'accepted': 'primary',
  'diagnosing': 'warning',
  'resolving': 'warning',
  'transferred': 'success',
  'resolved': 'success',
  'closed': 'info'
}

const STATUS_PERCENT = {
  'open': 10,
  'assigned': 20,
  'accepted': 30,
  'diagnosing': 50,
  'resolving': 60,
  'transferred': 70,
  'resolved': 90,
  'closed': 100
}

const getStatusColor = (status) => STATUS_COLORS[status] || 'info'
const getStatusLabel = (status) => {
  const keyMap = {
    'open': 'faultStatusOpen',
    'assigned': 'faultStatusAssigned',
    'accepted': 'faultStatusAccepted',
    'diagnosing': 'faultStatusDiagnosing',
    'resolving': 'faultStatusResolving',
    'transferred': 'faultStatusTransferred',
    'resolved': 'faultStatusResolved',
    'closed': 'faultStatusClosed'
  }
  const key = keyMap[status]
  return key ? t(key) : status
}
const getProgressPercent = (status) => STATUS_PERCENT[status] || 10

const getSlaText = (slaRemaining) => {
  if (!slaRemaining) return '--'
  if (slaRemaining === '已超期' || slaRemaining === 'Overdue') return t('faultSlaOverdue')
  return slaRemaining
}

// 优先级映射 (severity -> priority)
const SEVERITY_TO_PRIORITY = {
  'critical': 'P1',
  'major': 'P2',
  'minor': 'P3',
  'warning': 'P4'
}

const getPriorityFromSeverity = (severity) => SEVERITY_TO_PRIORITY[severity] || 'P3'

const getPriorityColor = (priority) => {
  const colors = { 'P1': 'danger', 'P2': 'warning', 'P3': 'info', 'P4': 'success' }
  return colors[priority] || 'info'
}

// 故障类型颜色和标签
const FAULT_TYPE_COLORS = {
  'hardware': 'danger',
  'software': 'warning',
  'config': 'info',
  'network': 'primary',
  'other': ''
}

const FAULT_TYPE_LABELS = {
  'hardware': '硬件',
  'software': '软件',
  'config': '配置',
  'network': '网络',
  'other': '其他'
}

const getFaultTypeColor = (type) => FAULT_TYPE_COLORS[type] || ''
const getFaultTypeLabel = (type) => FAULT_TYPE_LABELS[type] || type || '--'

// 超期判断
const isOverdue = (row) => {
  if (row.status === 'closed' || row.status === 'resolved') return false
  if (row.sla_remaining && (row.sla_remaining === '已超期' || row.sla_remaining === 'Overdue')) return true
  return false
}

// SLA紧急判断
const isSlaCritical = (row) => {
  if (row.status === 'closed' || row.status === 'resolved') return false
  if (row.sla_remaining) {
    const match = row.sla_remaining.match(/(\d+)h/)
    if (match && parseInt(match[1]) <= 4) return true
  }
  return false
}

// 表格行样式
const tableRowClassName = ({ row }) => {
  if (isOverdue(row)) return 'overdue-row'
  if (row.status === 'closed') return 'closed-row'
  return ''
}

// 状态筛选
const filterByStatus = (status) => {
  filterStatus.value = status
  currentPage.value = 1
  filterFaults()
}

// 状态组筛选
const filterByStatusGroup = (group) => {
  if (group === 'pending') {
    filterStatus.value = 'pending'
  } else if (group === 'processing') {
    filterStatus.value = 'processing'
  }
  currentPage.value = 1
  filterFaults()
}

const handlePageSizeChange = () => {
  currentPage.value = 1
}

const handlePageChange = () => {}

const faultForm = ref({
  id: null,
  device_id: null,
  device_name: '',
  severity: 'major',
  downtime_minutes: 0,
  impact: '',
  description: '',
  status: 'open',
  assigned_to: '',
  fault_type: ''
})

const filterFaults = () => {
  let result = [...faults.value]

  // 搜索文本过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(f =>
      f.device_name?.toLowerCase().includes(search) ||
      f.fault_no?.toLowerCase().includes(search) ||
      f.description?.toLowerCase().includes(search)
    )
  }

  // 优先级过滤
  if (filterPriority.value) {
    result = result.filter(f => getPriorityFromSeverity(f.severity) === filterPriority.value)
  }

  // 类型过滤
  if (filterType.value) {
    result = result.filter(f => f.fault_type === filterType.value)
  }

  // 状态过滤
  if (filterStatus.value) {
    if (filterStatus.value === 'pending') {
      result = result.filter(f => ['open', 'assigned'].includes(f.status))
    } else if (filterStatus.value === 'processing') {
      result = result.filter(f => ['accepted', 'diagnosing', 'resolving', 'transferred'].includes(f.status))
    } else {
      result = result.filter(f => f.status === filterStatus.value)
    }
  }

  // 日期范围过滤
  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0])
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(f => {
      const faultTime = dayjs(f.created_at)
      return faultTime.isAfter(startDate) && faultTime.isBefore(endDate)
    })
  }

  // 按创建时间降序排序
  result.sort((a, b) => dayjs(b.created_at) - dayjs(a.created_at))

  filteredFaults.value = result
}

const loadFaults = async () => {
  loading.value = true
  try {
    const data = await getFaults({ limit: 500 })
    faults.value = (data.items || [])
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

const openAddDialog = () => {
  editMode.value = false
  resetForm()
  showAddDialog.value = true
}

const addFault = async () => {
  try {
    const device = devices.value.find(d => d.id === faultForm.value.device_id)
    const data = {
      ...faultForm.value,
      device_name: device?.name,
      reporter: 'Web',
      status: faultForm.value.assigned_to ? 'assigned' : 'open'
    }
    await createFault(data)
    ElMessage.success(t('faultAddSuccess'))
    showAddDialog.value = false
    resetForm()
    loadFaults()
    window.dispatchEvent(new CustomEvent('fault-status-change'))
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
    status: row.status,
    assigned_to: row.assigned_to || '',
    fault_type: row.fault_type || ''
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
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    ElMessage.error(t('faultUpdateFailed'))
  }
}

const deleteFaultRecord = async (row) => {
  try {
    await ElMessageBox.confirm(
      `${t('faultDeleteConfirm')} "${row.fault_no}" ?`,
      t('faultDeleteTitle'),
      { type: 'warning' }
    )
    await deleteFault(row.id)
    ElMessage.success(t('faultDeleteSuccess'))
    loadFaults()
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('faultDeleteFailed'))
    }
  }
}

const viewDetail = (row) => {
  router.push(`/faults/${row.id}`)
}

const locateDevice = (row) => {
  router.push(`/monitor-screen?device_id=${row.device_id}`)
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
    status: 'open',
    assigned_to: '',
    fault_type: ''
  }
  editMode.value = false
}

onMounted(() => {
  loadFaults()
  loadDevices()
})
</script>

<style scoped>
/* 字体清晰度优化 - 所有等宽字体 */
.fault-no-badge,
.metric-value,
.chip-count,
.table-count,
.progress-percent,
.sla-text,
.cost-value,
.cost-currency,
.time-text,
.priority-text {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* ===== 页面整体背景 ===== */
.faults-page {
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
.stat-card.pending .card-icon {
  background: linear-gradient(135deg, rgba(116, 185, 255, 0.2) 0%, rgba(116, 185, 255, 0.1) 100%);
  color: #74b9ff;
}
.stat-card.processing .card-icon {
  background: linear-gradient(135deg, rgba(253, 121, 168, 0.2) 0%, rgba(253, 121, 168, 0.1) 100%);
  color: #fd79a8;
}
.stat-card.resolved .card-icon {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.2) 0%, rgba(0, 184, 148, 0.1) 100%);
  color: #00b894;
}
.stat-card.closed .card-icon {
  background: linear-gradient(135deg, rgba(99, 110, 114, 0.15) 0%, rgba(99, 110, 114, 0.08) 100%);
  color: #636e72;
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
.card-trend.warning { background: rgba(239, 68, 68, 0.1); color: #ef4444; }
.card-trend.success { background: rgba(0, 184, 148, 0.1); color: #00b894; }
.card-trend.done { background: rgba(99, 110, 114, 0.1); color: #636e72; }

.card-progress {
  width: 24px;
  height: 24px;
  position: relative;
}

.progress-ring {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: conic-gradient(#fd79a8 calc(var(--percent) * 1%), rgba(253, 121, 168, 0.2) 0);
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

.status-chip.chip-open .chip-dot { background: #74b9ff; }
.status-chip.chip-assigned .chip-dot { background: #0984e3; }
.status-chip.chip-diagnosing .chip-dot { background: #fd79a8; }
.status-chip.chip-transferred .chip-dot { background: #00b894; }
.status-chip.chip-resolved .chip-dot { background: #00b894; }
.status-chip.chip-closed .chip-dot { background: #636e72; }

.status-chip.chip-open:hover { background: rgba(116, 185, 255, 0.08); border-color: rgba(116, 185, 255, 0.3); }
.status-chip.chip-assigned:hover { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); }
.status-chip.chip-diagnosing:hover { background: rgba(253, 121, 168, 0.08); border-color: rgba(253, 121, 168, 0.3); }
.status-chip.chip-transferred:hover { background: rgba(0, 184, 148, 0.08); border-color: rgba(0, 184, 148, 0.3); }
.status-chip.chip-resolved:hover { background: rgba(0, 184, 148, 0.12); border-color: rgba(0, 184, 148, 0.4); }
.status-chip.chip-closed:hover { background: rgba(45, 52, 54, 0.08); border-color: rgba(45, 52, 54, 0.3); }

.more-filters {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.more-filters :deep(.el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  box-shadow: none;
}

.more-filters :deep(.el-date-editor) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  box-shadow: none;
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

.enterprise-table :deep(.overdue-row > td) {
  background: rgba(239, 68, 68, 0.04) !important;
}

.enterprise-table :deep(.closed-row) {
  opacity: 0.6;
}

/* 故障单号链接 */
.fault-no-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent-primary);
  text-decoration: none;
  transition: all 0.25s;
}

.fault-no-link:hover {
  color: var(--accent-secondary);
}

.fault-no-badge {
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

.fault-no-link:hover .fault-no-badge {
  background: rgba(9, 132, 227, 0.15);
}

.link-arrow {
  opacity: 0;
  font-size: 12px;
  transition: all 0.25s;
  color: var(--accent-primary);
}

.fault-no-link:hover .link-arrow {
  opacity: 1;
  transform: translateX(4px);
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

.status-badge.open {
  border-color: rgba(116, 185, 255, 0.3);
  color: #74b9ff;
}
.status-badge.open .status-dot { background: #74b9ff; }

.status-badge.assigned {
  border-color: rgba(9, 132, 227, 0.3);
  color: #0984e3;
}
.status-badge.assigned .status-dot { background: #0984e3; }

.status-badge.diagnosing {
  border-color: rgba(253, 121, 168, 0.3);
  color: #fd79a8;
}
.status-badge.diagnosing .status-dot { background: #fd79a8; }

.status-badge.transferred {
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}
.status-badge.transferred .status-dot { background: #00b894; }

.status-badge.resolved {
  border-color: rgba(0, 184, 148, 0.4);
  color: #00b894;
}
.status-badge.resolved .status-dot { background: #00b894; }

.status-badge.closed {
  border-color: rgba(45, 52, 54, 0.3);
  color: #636e72;
}
.status-badge.closed .status-dot { background: #636e72; }

/* 优先级徽章 */
.priority-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.priority-icon {
  font-size: 12px;
}

.priority-badge.P1 {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.08) 100%);
  border: 1px solid rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.priority-badge.P2 {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(251, 191, 36, 0.08) 100%);
  border: 1px solid rgba(251, 191, 36, 0.3);
  color: #f59e0b;
}

.priority-badge.P3 {
  background: linear-gradient(135deg, rgba(9, 132, 227, 0.12) 0%, rgba(9, 132, 227, 0.06) 100%);
  border: 1px solid rgba(9, 132, 227, 0.25);
  color: #0984e3;
}

.priority-badge.P4 {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.12) 0%, rgba(0, 184, 148, 0.06) 100%);
  border: 1px solid rgba(0, 184, 148, 0.25);
  color: #00b894;
}

/* 设备单元格 */
.device-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-icon {
  font-size: 14px;
  color: var(--text-tertiary);
}

.device-name {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 负责人单元格 */
.owner-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.owner-avatar {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: linear-gradient(135deg, #0984e3, #74b9ff);
  color: white;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.owner-name {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 类型徽章 */
.type-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
}

.type-badge.hardware {
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
}

.type-badge.software {
  background: rgba(251, 191, 36, 0.08);
  color: #f59e0b;
}

.type-badge.config {
  background: rgba(9, 132, 227, 0.08);
  color: #0984e3;
}

.type-badge.network {
  background: rgba(116, 185, 255, 0.08);
  color: #74b9ff;
}

.type-badge.other {
  background: rgba(45, 52, 54, 0.08);
  color: #636e72;
}

/* 进度条 */
.progress-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar-bg {
  width: 70px;
  height: 6px;
  background: rgba(0, 48, 135, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}

.progress-bar-fill.open { background: linear-gradient(90deg, #74b9ff, #a8d8ff); }
.progress-bar-fill.assigned { background: linear-gradient(90deg, #0984e3, #74b9ff); }
.progress-bar-fill.diagnosing { background: linear-gradient(90deg, #fd79a8, #ffb8c6); }
.progress-bar-fill.transferred { background: linear-gradient(90deg, #00b894, #55efc4); }
.progress-bar-fill.resolved { background: linear-gradient(90deg, #00b894, #55efc4); }
.progress-bar-fill.closed { background: linear-gradient(90deg, #636e72, #b2bec3); }

.progress-percent {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 500;
}

/* SLA单元格 */
.sla-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.sla-cell.overdue {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
  padding: 2px 8px;
  border-radius: 6px;
}

.sla-cell.critical {
  color: #f59e0b;
}

.sla-icon {
  font-size: 12px;
}

/* 成本单元格 */
.cost-cell {
  display: flex;
  align-items: center;
  gap: 2px;
}

.cost-currency {
  font-size: 11px;
  color: var(--text-tertiary);
}

.cost-value {
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

.cost-value.empty {
  color: var(--text-tertiary);
}

/* 时间单元格 */
.time-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-icon {
  font-size: 13px;
  color: var(--text-tertiary);
}

.time-text {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 操作按钮组 */
.action-group {
  display: flex;
  gap: 4px;
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

.action-btn.edit:hover {
  background: rgba(251, 191, 36, 0.08);
  border-color: rgba(251, 191, 36, 0.2);
  color: #f59e0b;
}

.action-btn.locate:hover {
  background: rgba(0, 212, 170, 0.08);
  border-color: rgba(0, 212, 170, 0.2);
  color: #00d4aa;
}

.action-btn.delete:hover {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.2);
  color: #ef4444;
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

.assign-tip {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 4px;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .status-chips {
    justify-content: center;
  }

  .more-filters {
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
.dark .faults-page {
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

.dark .metric-label {
  color: #8b949e;
}

.dark .card-trend.stable { background: rgba(9, 132, 227, 0.2); color: #58a6ff; }
.dark .card-trend.warning { background: rgba(239, 68, 68, 0.2); color: #f85149; }
.dark .card-trend.success { background: rgba(0, 184, 148, 0.2); color: #3fb950; }
.dark .card-trend.done { background: rgba(139, 148, 158, 0.2); color: #8b949e; }

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

.dark .more-filters :deep(.el-select .el-input__wrapper),
.dark .more-filters :deep(.el-date-editor) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

/* 状态徽章暗黑模式 */
.dark .status-badge {
  background: rgba(13, 17, 23, 0.9);
}

.dark .status-badge.open {
  border-color: rgba(116, 185, 255, 0.4);
  color: #74b9ff;
}
.dark .status-badge.open .status-dot { background: #74b9ff; }

.dark .status-badge.assigned {
  border-color: rgba(88, 166, 255, 0.4);
  color: #58a6ff;
}
.dark .status-badge.assigned .status-dot { background: #58a6ff; }

.dark .status-badge.diagnosing {
  border-color: rgba(253, 121, 168, 0.4);
  color: #fd79a8;
}
.dark .status-badge.diagnosing .status-dot { background: #fd79a8; }

.dark .status-badge.transferred {
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}
.dark .status-badge.transferred .status-dot { background: #3fb950; }

.dark .status-badge.resolved {
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}
.dark .status-badge.resolved .status-dot { background: #3fb950; }

.dark .status-badge.closed {
  border-color: rgba(139, 148, 158, 0.4);
  color: #8b949e;
}
.dark .status-badge.closed .status-dot { background: #8b949e; }

/* 优先级徽章暗黑模式 */
.dark .priority-badge.P1 {
  background: rgba(248, 81, 73, 0.15);
  border-color: rgba(248, 81, 73, 0.4);
  color: #f85149;
}

.dark .priority-badge.P2 {
  background: rgba(210, 153, 34, 0.15);
  border-color: rgba(210, 153, 34, 0.4);
  color: #d29922;
}

.dark .priority-badge.P3 {
  background: rgba(88, 166, 255, 0.15);
  border-color: rgba(88, 166, 255, 0.4);
  color: #58a6ff;
}

.dark .priority-badge.P4 {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}

/* 类型徽章暗黑模式 */
.dark .type-badge.hardware {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
}

.dark .type-badge.software {
  background: rgba(210, 153, 34, 0.15);
  color: #d29922;
}

.dark .type-badge.config {
  background: rgba(88, 166, 255, 0.15);
  color: #58a6ff;
}

.dark .type-badge.network {
  background: rgba(116, 185, 255, 0.15);
  color: #74b9ff;
}

.dark .type-badge.other {
  background: rgba(139, 148, 158, 0.15);
  color: #8b949e;
}

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

.dark .enterprise-table :deep(.overdue-row > td) {
  background: rgba(248, 81, 73, 0.08) !important;
}

.dark .fault-no-link {
  color: #58a6ff;
}

.dark .fault-no-badge {
  background: rgba(88, 166, 255, 0.15);
}

.dark .fault-no-link:hover .fault-no-badge {
  background: rgba(88, 166, 255, 0.25);
}

.dark .device-name {
  color: #c9d1d9;
}

.dark .owner-name {
  color: #8b949e;
}

.dark .owner-avatar {
  background: linear-gradient(135deg, #0984e3, #74b9ff);
}

.dark .progress-bar-bg {
  background: rgba(48, 54, 61, 0.5);
}

.dark .progress-percent {
  color: #8b949e;
}

.dark .sla-cell {
  color: #8b949e;
}

.dark .sla-cell.overdue {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
}

.dark .sla-cell.critical {
  color: #d29922;
}

.dark .cost-value {
  color: #8b949e;
}

.dark .cost-value.empty {
  color: #6e7681;
}

.dark .time-text {
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
</style>