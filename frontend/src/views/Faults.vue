<template>
  <div class="faults-page">
    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-header">
        <span class="stats-title">{{ t('faultStatsTitle') }}</span>
        <button class="refresh-btn" @click="loadFaults" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
      <div class="stats-grid">
        <!-- 总故障 -->
        <div class="stat-card total" @click="filterByStatus('')">
          <div class="card-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.total }}</div>
            <div class="metric-label">{{ t('faultStatsTotal') }}</div>
          </div>
        </div>
        <!-- 待处理 -->
        <div class="stat-card pending" @click="filterByStatus('open')">
          <div class="card-icon">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.open }}</div>
            <div class="metric-label">{{ t('faultStatsOpen') }}</div>
          </div>
        </div>
        <!-- 调查中 -->
        <div class="stat-card investigating" @click="filterByStatus('investigating')">
          <div class="card-icon">
            <el-icon><Search /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.investigating }}</div>
            <div class="metric-label">{{ t('faultStatsInvestigating') }}</div>
          </div>
        </div>
        <!-- 已解决 -->
        <div class="stat-card resolved" @click="filterByStatus('resolved')">
          <div class="card-icon">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.resolved }}</div>
            <div class="metric-label">{{ t('faultStatsResolved') }}</div>
          </div>
        </div>
        <!-- 已关闭 -->
        <div class="stat-card closed" @click="filterByStatus('closed')">
          <div class="card-icon">
            <el-icon><SuccessFilled /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.closed }}</div>
            <div class="metric-label">{{ t('faultStatsClosed') }}</div>
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
          :placeholder="t('faultSearchPlaceholder')"
          class="search-input"
          clearable
          @input="filterFaults"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <el-tag
            :class="['status-chip', { active: filterStatus === '' }]"
            @click="filterByStatus('')"
          >{{ t('faultFilterAll') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-open', { active: filterStatus === 'open' }]"
            @click="filterByStatus('open')"
          >{{ t('faultStatusOpen') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-investigating', { active: filterStatus === 'investigating' }]"
            @click="filterByStatus('investigating')"
          >{{ t('faultStatusInvestigating') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-resolved', { active: filterStatus === 'resolved' }]"
            @click="filterByStatus('resolved')"
          >{{ t('faultStatusResolved') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-closed', { active: filterStatus === 'closed' }]"
            @click="filterByStatus('closed')"
          >{{ t('faultStatusClosed') }}</el-tag>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-select v-model="filterSeverity" :placeholder="t('faultLevel')" clearable style="width: 100px" @change="filterFaults">
            <el-option :label="t('dashCritical')" value="critical" />
            <el-option :label="t('dashMajor')" value="major" />
            <el-option :label="t('dashMinor')" value="minor" />
            <el-option :label="t('dashWarning')" value="warning" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :range-separator="t('faultToDate')"
            :start-placeholder="t('faultStartDate')"
            :end-placeholder="t('faultEndDate')"
            value-format="YYYY-MM-DD"
            style="width: 200px"
            @change="filterFaults"
          />
          <el-select v-model="sortBy" :placeholder="t('faultSort')" style="width: 140px" @change="filterFaults">
            <el-option :label="t('faultSortTimeDesc')" value="created_at_desc" />
            <el-option :label="t('faultSortTimeAsc')" value="created_at_asc" />
            <el-option :label="t('faultSortDowntimeDesc')" value="downtime_desc" />
            <el-option :label="t('faultSortDowntimeAsc')" value="downtime_asc" />
          </el-select>
        </div>

        <!-- 新增按钮 -->
        <el-button type="primary" class="add-btn" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          {{ t('faultAdd') }}
        </el-button>
      </div>
    </section>

    <!-- 故障数据面板 -->
    <section class="data-section">
      <el-table :data="filteredFaults" class="modern-table" v-loading="loading">
        <el-table-column prop="fault_no" :label="t('faultNo')" width="180">
          <template #default="{ row }">
            <router-link :to="`/faults/${row.id}`" class="fault-link">
              <span class="fault-no-text">{{ row.fault_no }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" :label="t('faultDevice')" width="140" />
        <el-table-column prop="severity" :label="t('faultSeverity')" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small" class="severity-tag">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" :label="t('faultStatus')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small" class="status-tag">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="downtime_minutes" :label="t('faultDowntime')" width="100">
          <template #default="{ row }">
            <span class="downtime-value">{{ row.downtime_minutes }} {{ t('faultMinutes') }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" :label="t('faultDescription')" />
        <el-table-column prop="created_at" :label="t('faultOccurTime')" width="140">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('faultAction')" width="180" fixed="right">
          <template #default="{ row }">
            <div class="action-icons">
              <el-button size="small" link @click="editFault(row)" class="action-icon">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button
                v-if="row.status === 'open'"
                size="small"
                type="warning"
                link
                @click="changeStatus(row, 'investigating')"
                class="action-icon action-main"
              >
                <el-icon><Search /></el-icon>
              </el-button>
              <el-button
                v-if="row.status === 'investigating'"
                size="small"
                type="success"
                link
                @click="changeStatus(row, 'resolved')"
                class="action-icon action-main"
              >
                <el-icon><CircleCheck /></el-icon>
              </el-button>
              <el-button
                v-if="row.status === 'resolved'"
                size="small"
                type="info"
                link
                @click="changeStatus(row, 'closed')"
                class="action-icon action-main"
              >
                <el-icon><SuccessFilled /></el-icon>
              </el-button>
              <el-button
                v-if="row.status === 'closed'"
                size="small"
                type="primary"
                link
                @click="changeStatus(row, 'open')"
                class="action-icon"
              >
                <el-icon><RefreshRight /></el-icon>
              </el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoFaults')" :image-size="80">
            <el-button type="primary" size="small" @click="showAddDialog = true">{{ t('faultAdd') }}</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="filteredTotal" @size-change="handlePageSizeChange" @current-change="handlePageChange" />
      </div>
    </section>

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
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Refresh, Document, Clock, CircleCheck, SuccessFilled, ArrowRight, Edit, RefreshRight } from '@element-plus/icons-vue'
import { getFaults, getDevices, createFault, updateFault as updateFaultApi, deleteFault } from '@/api'
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

// 统计数据
const stats = computed(() => {
  const list = faults.value
  const totalCount = list.length
  const openCount = list.filter(f => f.status === 'open').length
  const investigatingCount = list.filter(f => f.status === 'investigating').length
  const resolvedCount = list.filter(f => f.status === 'resolved').length
  const closedCount = list.filter(f => f.status === 'closed').length
  return {
    total: totalCount,
    open: openCount,
    investigating: investigatingCount,
    resolved: resolvedCount,
    closed: closedCount
  }
})

// 分页后的总数
const filteredTotal = computed(() => filteredFaults.value.length)

// 状态筛选
const filterByStatus = (status) => {
  filterStatus.value = status
  currentPage.value = 1
  filterFaults()
}

// 分页处理
const handlePageSizeChange = () => {
  currentPage.value = 1
}

const handlePageChange = () => {
  // 分页切换
}

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
  editMode.value = false
}

onMounted(() => {
  loadFaults()
  loadDevices()
})
</script>

<style scoped>
.faults-page {
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

.stat-card.pending .card-icon {
  background: rgba(116, 185, 255, 0.15);
  color: #74b9ff;
}

.stat-card.investigating .card-icon {
  background: rgba(225, 112, 85, 0.15);
  color: #e17055;
}

.stat-card.resolved .card-icon {
  background: rgba(0, 184, 148, 0.15);
  color: #00b894;
}

.stat-card.closed .card-icon {
  background: rgba(45, 52, 54, 0.15);
  color: #2d3436;
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

.status-chip.chip-open { background: rgba(116, 185, 255, 0.1); border-color: rgba(116, 185, 255, 0.3); color: #74b9ff; }
.status-chip.chip-investigating { background: rgba(225, 112, 85, 0.1); border-color: rgba(225, 112, 85, 0.3); color: #e17055; }
.status-chip.chip-resolved { background: rgba(0, 184, 148, 0.1); border-color: rgba(0, 184, 148, 0.3); color: #00b894; }
.status-chip.chip-closed { background: rgba(45, 52, 54, 0.1); border-color: rgba(45, 52, 54, 0.3); color: #2d3436; }

.more-filters {
  display: flex;
  gap: 8px;
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

/* 故障单号链接 */
.fault-link {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--accent-primary);
  text-decoration: none;
  font-family: 'JetBrains Mono', 'Geist Mono', monospace;
  font-weight: 500;
  font-size: 13px;
  transition: all 0.2s;
}

.fault-link:hover {
  color: var(--accent-secondary);
}

.fault-link:hover .link-arrow {
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

/* 严重等级标签 */
.severity-tag {
  font-weight: 500;
}

/* 停机时间 */
.downtime-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--text-secondary);
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

.action-main {
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

  .add-btn {
    width: 100%;
    margin-left: 0;
  }
}

/* ===== 暗色模式 ===== */
.dark .stat-card:hover {
  box-shadow: 0 4px 12px rgba(0, 184, 148, 0.1);
}

.dark .stat-card.total .card-icon { background: rgba(9, 132, 227, 0.2); }
.dark .stat-card.pending .card-icon { background: rgba(116, 185, 255, 0.2); }
.dark .stat-card.investigating .card-icon { background: rgba(225, 112, 85, 0.2); }
.dark .stat-card.resolved .card-icon { background: rgba(0, 184, 148, 0.2); }
.dark .stat-card.closed .card-icon { background: rgba(45, 52, 54, 0.2); }

.dark .status-chip.chip-open { background: rgba(116, 185, 255, 0.15); }
.dark .status-chip.chip-investigating { background: rgba(225, 112, 85, 0.15); }
.dark .status-chip.chip-resolved { background: rgba(0, 184, 148, 0.15); }
.dark .status-chip.chip-closed { background: rgba(45, 52, 54, 0.15); }
</style>