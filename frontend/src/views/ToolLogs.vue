<template>
  <div class="tool-logs-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="page-title">
        <h1>{{ t('toolTitle') }}</h1>
        <span class="page-subtitle">{{ t('toolSubtitle') }}</span>
      </div>
      <div class="btn-row">
        <button class="btn btn-ghost" @click="loadLogs">
          <el-icon><Refresh /></el-icon>
          {{ t('toolRefresh') }}
        </button>
        <button class="btn btn-danger" @click="cleanupLogs">
          <el-icon><Delete /></el-icon>
          {{ t('toolCleanup') }}
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="kpi-grid">
      <div class="kpi kpi-blue">
        <div class="kpi-top"></div>
        <div class="kpi-body">
          <div class="kpi-value">{{ stats.total }}</div>
          <div class="kpi-label">{{ t('toolTotalRuns') }}</div>
        </div>
      </div>
      <div class="kpi kpi-green">
        <div class="kpi-top"></div>
        <div class="kpi-body">
          <div class="kpi-value">{{ stats.success }}</div>
          <div class="kpi-label">{{ t('toolSuccess') }}</div>
        </div>
      </div>
      <div class="kpi kpi-red">
        <div class="kpi-top"></div>
        <div class="kpi-body">
          <div class="kpi-value">{{ stats.failed }}</div>
          <div class="kpi-label">{{ t('toolFailed') }}</div>
        </div>
      </div>
      <div class="kpi kpi-yellow">
        <div class="kpi-top"></div>
        <div class="kpi-body">
          <div class="kpi-value">{{ stats.avgDuration || 0 }}</div>
          <div class="kpi-label">{{ t('toolAvgTime') }}</div>
        </div>
      </div>
    </div>

    <!-- Filter Panel -->
    <div class="panel">
      <div class="panel-body">
        <div class="filter-bar">
          <select class="fselect" v-model="filterToolType" @change="loadLogs">
            <option value="">{{ t('toolAllTools') }}</option>
            <option value="netmiko">Netmiko</option>
            <option value="napalm">NAPALM</option>
            <option value="jira">JIRA</option>
          </select>
          <select class="fselect" v-model="filterStatus" @change="loadLogs">
            <option value="">{{ t('toolAllStatus') }}</option>
            <option value="success">{{ t('toolSuccess') }}</option>
            <option value="failed">{{ t('toolFailed') }}</option>
            <option value="running">{{ t('toolStatusRunning') }}</option>
          </select>
          <input
            class="finput"
            v-model="searchKeyword"
            :placeholder="t('toolSearchPlaceholder')"
            @keyup.enter="loadLogs"
          />
          <button class="btn btn-primary btn-sm" @click="loadLogs">
            <el-icon><Search /></el-icon>
            {{ t('actionSearch') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Logs Table -->
    <div class="panel">
      <div class="panel-hd">
        <span class="panel-title">{{ t('toolRecords') }}</span>
        <span class="panel-meta">{{ t('dashTotal') }} {{ total }} {{ t('dashAction') }}</span>
      </div>
      <div class="panel-body">
        <table class="tbl" v-loading="loading">
          <thead>
            <tr>
              <th>{{ t('toolColTime') }}</th>
              <th>{{ t('toolColTool') }}</th>
              <th>{{ t('toolColAction') }}</th>
              <th>{{ t('toolColTarget') }}</th>
              <th>{{ t('toolColStatus') }}</th>
              <th>{{ t('toolColDuration') }}</th>
              <th>{{ t('toolColOperator') }}</th>
              <th>{{ t('toolColDetail') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logList" :key="log.id" @click="showDetail(log)">
              <td class="td-mono">{{ formatDateTime(log.timestamp) }}</td>
              <td><span class="tag tag-blue">{{ log.tool_type }}</span></td>
              <td>{{ log.operation }}</td>
              <td class="td-mono">{{ log.target || '-' }}</td>
              <td>
                <span :class="['tag', getStatusTag(log.status)]">{{ log.status }}</span>
              </td>
              <td class="td-mono">{{ log.duration_ms ? log.duration_ms + 'ms' : '-' }}</td>
              <td>{{ log.created_by || '-' }}</td>
              <td><a class="td-action">{{ t('actionView') }}</a></td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div class="pagination-bar">
          <span class="page-info">{{ t('toolPageInfo', { page: currentPage, size: pageSize }) }}</span>
          <div class="page-btns">
            <button class="btn btn-tiny btn-ghost" @click="currentPage--; loadLogs()" :disabled="currentPage <= 1">{{ t('toolPrevPage') }}</button>
            <button class="btn btn-tiny btn-ghost" @click="currentPage++; loadLogs()" :disabled="currentPage * pageSize >= total">{{ t('toolNextPage') }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Detail Modal -->
    <div class="modal-overlay" v-if="showDetailDialog" @click="showDetailDialog = false">
      <div class="modal modal-lg" @click.stop>
        <div class="modal-hd">
          <span class="modal-title">{{ t('toolDetailTitle') }}</span>
          <button class="modal-close" @click="showDetailDialog = false">×</button>
        </div>
        <div class="modal-body" v-loading="detailLoading">
          <div class="detail-grid">
            <div class="detail-row">
              <label>{{ t('toolDetailToolType') }}</label>
              <span class="tag tag-blue">{{ selectedLog?.tool_type }}</span>
            </div>
            <div class="detail-row">
              <label>{{ t('toolDetailStatus') }}</label>
              <span :class="['tag', getStatusTag(selectedLog?.status)]">{{ selectedLog?.status }}</span>
            </div>
            <div class="detail-row">
              <label>{{ t('toolDetailTime') }}</label>
              <span class="mono">{{ formatDateTime(selectedLog?.timestamp) }}</span>
            </div>
            <div class="detail-row">
              <label>{{ t('toolDetailDuration') }}</label>
              <span class="mono">{{ selectedLog?.duration_ms ? selectedLog.duration_ms + 'ms' : '-' }}</span>
            </div>
            <div class="detail-row full">
              <label>{{ t('toolDetailAction') }}</label>
              <span>{{ selectedLog?.operation }}</span>
            </div>
            <div class="detail-row">
              <label>{{ t('toolDetailTarget') }}</label>
              <span class="mono">{{ selectedLog?.target || '-' }}</span>
            </div>
            <div class="detail-row">
              <label>{{ t('toolDetailOperator') }}</label>
              <span>{{ selectedLog?.created_by || '-' }}</span>
            </div>
          </div>

          <!-- Log Content -->
          <div class="section-title" v-if="selectedLog?.log_content">
            <span class="section-marker"></span>
            {{ t('toolDetailContent') }}
          </div>
          <div class="log-content" v-if="selectedLog?.log_content">
            <pre>{{ selectedLog.log_content }}</pre>
          </div>
          <div class="log-empty" v-else>
            <el-icon><Document /></el-icon>
            <span>{{ t('toolNoContent') }}</span>
          </div>
        </div>
        <div class="modal-ft">
          <button class="btn btn-ghost" @click="showDetailDialog = false">{{ t('actionClose') }}</button>
          <button class="btn btn-primary" @click="copyLogContent" v-if="selectedLog?.log_content">
            <el-icon><CopyDocument /></el-icon>
            {{ t('toolCopyLog') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Delete, Search, Document, CopyDocument } from '@element-plus/icons-vue'
import { getToolLogs, getToolLogStats, cleanupToolLogs, getToolLogDetail } from '@/api'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const loading = ref(false)
const detailLoading = ref(false)
const logList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const showDetailDialog = ref(false)
const selectedLog = ref(null)

const filterToolType = ref('')
const filterStatus = ref('')
const searchKeyword = ref('')

const stats = reactive({ total: 0, success: 0, failed: 0, avgDuration: 0 })

const loadStats = async () => {
  try {
    const res = await getToolLogStats()
    Object.assign(stats, res)
  } catch (error) {
    console.log('Stats load failed:', error)
  }
}

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      tool_type: filterToolType.value || undefined,
      status: filterStatus.value || undefined,
      keyword: searchKeyword.value || undefined,
    }
    const res = await getToolLogs(params)
    logList.value = res.items || res || []
    total.value = res.total || logList.value.length
  } catch (error) {
    ElMessage.error(t('msgLoadFailed') + '：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const showDetail = async (row) => {
  showDetailDialog.value = true
  detailLoading.value = true
  selectedLog.value = row

  try {
    const detail = await getToolLogDetail(row.id)
    selectedLog.value = detail
  } catch (error) {
    ElMessage.warning(t('msgLoadDetailFailed'))
  } finally {
    detailLoading.value = false
  }
}

const getStatusTag = (status) => {
  const map = { success: 'tag-green', failed: 'tag-red', running: 'tag-yellow' }
  return map[status] || 'tag-gray'
}

const formatDateTime = (datetimeStr) => {
  if (!datetimeStr) return ''
  try {
    return new Date(datetimeStr).toLocaleString('zh-CN', { hour12: false })
  } catch { return datetimeStr }
}

const cleanupLogs = async () => {
  try {
    await ElMessageBox.confirm(t('msgCleanupConfirm'), t('msgConfirmDelete'), { type: 'warning' })
    await cleanupToolLogs(30)
    ElMessage.success(t('msgCleanupComplete'))
    loadLogs()
    loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('msgCleanupFailed') + '：' + error.message)
    }
  }
}

const copyLogContent = async () => {
  if (!selectedLog.value?.log_content) return
  try {
    await navigator.clipboard.writeText(selectedLog.value.log_content)
    ElMessage.success(t('msgCopied'))
  } catch {
    ElMessage.error(t('msgOpFailed'))
  }
}

onMounted(() => {
  loadLogs()
  loadStats()
})
</script>

<style scoped>
.tool-logs-page {
  max-width: 1200px;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--gap-lg);
}

.page-title h1 {
  font-size: 20px;
  font-weight: 500;
  color: var(--ink);
  margin: 0;
}

.page-subtitle {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--ink3);
}

.btn-row {
  display: flex;
  gap: var(--gap-sm);
}

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
}

.kpi {
  background: var(--surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border);
  overflow: hidden;
}

.kpi-top {
  height: 4px;
}

.kpi-blue .kpi-top { background: var(--color-gb); }
.kpi-green .kpi-top { background: var(--success); }
.kpi-red .kpi-top { background: var(--danger); }
.kpi-yellow .kpi-top { background: var(--color-gy); }

.kpi-body {
  padding: 18px 20px;
}

.kpi-value {
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 300;
  color: var(--ink);
  line-height: 1;
}

.kpi-label {
  font-size: 12px;
  font-weight: 400;
  color: var(--ink3);
  margin-top: 6px;
}

/* Panel */
.panel {
  background: var(--surface);
  border-radius: var(--radius-panel);
  border: 1px solid var(--border);
  margin-bottom: var(--gap-md);
}

.panel-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}

.panel-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
}

.panel-meta {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--ink3);
}

.panel-body {
  padding: 18px 20px;
}

/* Filter Bar */
.filter-bar {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
}

.fselect {
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--ink);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  min-width: 120px;
}

.finput {
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--ink);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  width: 200px;
}

.finput:focus {
  border-color: var(--color-gb);
  outline: none;
}

.btn-sm {
  padding: 8px 12px;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 400;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.btn-primary {
  background: var(--color-gb);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-gb-mid);
}

.btn-danger {
  background: var(--danger);
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #991b1b;
}

.btn-ghost {
  background: var(--surface);
  color: var(--ink2);
  border-color: var(--border);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--color-gb-ghost);
}

.btn-tiny {
  padding: 4px 8px;
  font-size: 11px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Table */
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
}

.tbl th {
  padding: 10px 8px;
  font-size: 11px;
  font-weight: 500;
  color: var(--ink3);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 1px solid var(--border);
}

.tbl td {
  padding: 10px 8px;
  color: var(--ink2);
  border-bottom: 1px solid var(--border);
}

.tbl tr:hover td {
  background: var(--color-gb-ghost);
  cursor: pointer;
}

.td-mono {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-gb);
}

.td-action {
  color: var(--color-gb);
  cursor: pointer;
}

.td-action:hover {
  text-decoration: underline;
}

/* Tags */
.tag {
  display: inline-block;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: var(--radius-pill);
}

.tag-blue {
  background: var(--color-gb-light);
  color: var(--color-gb);
}

.tag-green {
  background: var(--success-bg);
  color: var(--success);
}

.tag-red {
  background: var(--danger-bg);
  color: var(--danger);
}

.tag-yellow {
  background: var(--warn-bg);
  color: var(--warn);
}

.tag-gray {
  background: var(--bg);
  color: var(--ink3);
}

/* Pagination */
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}

.page-info {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--ink3);
}

.page-btns {
  display: flex;
  gap: 8px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 31, 92, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  background: var(--surface);
  border-radius: var(--radius-modal);
  max-width: 720px;
  width: 90%;
  box-shadow: var(--shadow-modal);
}

.modal-lg {
  max-width: 900px;
}

.modal-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--ink);
}

.modal-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  border: none;
  border-radius: var(--radius-sm);
  font-size: 18px;
  color: var(--ink3);
  cursor: pointer;
}

.modal-close:hover {
  background: var(--color-gb-ghost);
}

.modal-body {
  padding: 20px 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-ft {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 24px;
  border-top: 1px solid var(--border);
}

/* Detail Grid */
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-row.full {
  grid-column: 1 / -1;
}

.detail-row label {
  min-width: 80px;
  font-size: 12px;
  font-weight: 500;
  color: var(--ink3);
}

.detail-row span {
  font-size: 13px;
  color: var(--ink);
}

.mono {
  font-family: var(--font-mono);
}

/* Section Title */
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 500;
  color: var(--ink3);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}

.section-marker {
  width: 3px;
  height: 14px;
  background: var(--color-gy);
  border-radius: 2px;
}

/* Log Content */
.log-content {
  background: #0d1117;
  border-radius: var(--radius-lg);
  padding: 16px;
}

.log-content pre {
  color: #c9d1d9;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
}

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px;
  color: var(--ink3);
}

.log-empty .el-icon {
  font-size: 32px;
}

/* Responsive */
@media (max-width: 768px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    flex-direction: column;
  }

  .finput, .fselect {
    width: 100%;
  }
}
</style>