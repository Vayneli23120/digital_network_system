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
            <option value="netmiko">{{ t('toolNetmiko') }}</option>
            <option value="napalm">{{ t('toolNapalm') }}</option>
            <option value="jira">{{ t('toolJira') }}</option>
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

    <!-- Detail Dialog -->
    <el-dialog v-model="showDetailDialog" :title="t('toolDetailTitle')" width="700px" append-to-body draggable align-center class="tool-detail-dialog">
      <div v-loading="detailLoading">
        <!-- 基本信息 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ t('toolBasicInfo') }}</span>
          </div>
          <div class="detail-grid">
            <el-row :gutter="16">
              <el-col :span="8">
                <div class="detail-item">
                  <label>{{ t('toolDetailToolType') }}</label>
                  <el-tag type="primary" size="small">{{ selectedLog?.tool_type }}</el-tag>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="detail-item">
                  <label>{{ t('toolDetailStatus') }}</label>
                  <el-tag :type="getStatusTagType(selectedLog?.status)" size="small">{{ selectedLog?.status }}</el-tag>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="detail-item">
                  <label>{{ t('toolDetailTime') }}</label>
                  <span class="mono-text">{{ formatDateTime(selectedLog?.timestamp) }}</span>
                </div>
              </el-col>
            </el-row>
            <el-row :gutter="16" style="margin-top: 12px">
              <el-col :span="8">
                <div class="detail-item">
                  <label>{{ t('toolDetailDuration') }}</label>
                  <span class="mono-text">{{ selectedLog?.duration_ms ? selectedLog.duration_ms + 'ms' : '-' }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="detail-item">
                  <label>{{ t('toolDetailTarget') }}</label>
                  <span class="mono-text">{{ selectedLog?.target || '-' }}</span>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="detail-item">
                  <label>{{ t('toolDetailOperator') }}</label>
                  <span>{{ selectedLog?.created_by || '-' }}</span>
                </div>
              </el-col>
            </el-row>
            <div class="detail-item full-width" style="margin-top: 12px">
              <label>{{ t('toolDetailAction') }}</label>
              <span>{{ selectedLog?.operation }}</span>
            </div>
          </div>
        </div>

        <!-- 日志内容 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Document /></el-icon>
            <span>{{ t('toolDetailContent') }}</span>
          </div>
          <div class="log-content" v-if="selectedLog?.log_content">
            <pre>{{ selectedLog.log_content }}</pre>
          </div>
          <div class="log-empty" v-else>
            <el-icon><Document /></el-icon>
            <span>{{ t('toolNoContent') }}</span>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showDetailDialog = false">{{ t('actionClose') }}</el-button>
        <el-button type="primary" @click="copyLogContent" v-if="selectedLog?.log_content">
          <el-icon><CopyDocument /></el-icon>
          {{ t('toolCopyLog') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Delete, Search, Document, CopyDocument, InfoFilled } from '@element-plus/icons-vue'
import { getToolLogs, getToolLogStats, cleanupToolLogs, getToolLogDetail } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

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

const loadLogs = debounce(async (force = false) => {
  loading.value = true
  try {
    const params = {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      tool_type: filterToolType.value || undefined,
      status: filterStatus.value || undefined,
      keyword: searchKeyword.value || undefined,
    }
    const res = await cachedRequest(
      () => getToolLogs(params),
      'logs',
      params,
      { forceRefresh: force }
    )
    logList.value = res.items || res || []
    total.value = res.total || logList.value.length
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('msgLoadFailed') + '：' + (error.response?.data?.detail || error.message))
    }
  } finally {
    loading.value = false
  }
}, 300)

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

const getStatusTagType = (status) => {
  const map = { success: 'success', failed: 'danger', running: 'warning' }
  return map[status] || 'info'
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
    clearCache('logs')
    ElMessage.success(t('msgCleanupComplete'))
    loadLogs(true)
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
/* ========================================
   使用全局 Theme Token（来自 tokens.css）
   不要重新定义变量，直接使用全局变量
   ======================================== */

.tool-logs-page {
  max-width: 1200px;
}

/* ========================================
   页面导航栏 - 与 Deploy.vue 一致
   ======================================== */

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--gap-lg);
}

.page-title h1 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 12px;
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  color: var(--text-secondary);
}

.btn-row {
  display: flex;
  gap: var(--gap-sm);
}

/* ========================================
   按钮系统 - 现代、轻量、主次分明
   ======================================== */

.btn {
  height: 28px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: none;
  background: var(--bg-card);
  color: var(--text-secondary);
}

.btn .el-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

/* 主按钮 */
.btn-primary {
  background: var(--accent-secondary);
  color: white;
  border: none;
}

.btn-primary:hover:not(:disabled) {
  background: #0077b6;
  box-shadow: 0 2px 6px rgba(9, 132, 227, 0.2);
  transform: translateY(-1px);
}

/* 小按钮 */
.btn-sm {
  height: 32px;
  padding: 8px 12px;
  font-size: 13px;
}

.btn-tiny {
  height: 22px;
  padding: 4px 8px;
  font-size: 11px;
}

/* 幽灵按钮 */
.btn-ghost {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

/* 危险按钮 */
.btn-danger {
  background: var(--accent-danger);
  color: white;
  border: none;
}

.btn-danger:hover:not(:disabled) {
  background: #c42a2a;
  box-shadow: 0 2px 6px rgba(214, 48, 49, 0.2);
  transform: translateY(-1px);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ========================================
   KPI Grid - 浅色卡片风格
   ======================================== */

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
}

.kpi {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  overflow: hidden;
  box-shadow: var(--shadow-card);
  transition: all 0.2s ease;
}

.kpi:hover {
  border-color: var(--accent-secondary);
  transform: translateY(-1px);
}

.kpi-top {
  height: 4px;
}

.kpi-blue .kpi-top { background: var(--accent-secondary); }
.kpi-green .kpi-top { background: var(--accent-primary); }
.kpi-red .kpi-top { background: var(--accent-danger); }
.kpi-yellow .kpi-top { background: var(--accent-warning); }

.kpi-body {
  padding: 16px 20px;
}

.kpi-value {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 28px;
  font-weight: 300;
  color: var(--text-primary);
  line-height: 1;
}

.kpi-label {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-secondary);
  margin-top: 6px;
}

/* ========================================
   Panel - 浅色企业风格
   ======================================== */

.panel {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  margin-bottom: var(--gap-md);
  box-shadow: var(--shadow-card);
}

.panel-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-meta {
  font-size: 12px;
  font-family: 'Geist Mono', monospace;
  color: var(--text-secondary);
}

.panel-body {
  padding: 16px 20px;
}

/* ========================================
   Filter Bar - 现代表单风格
   ======================================== */

.filter-bar {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
}

.fselect {
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--text-primary);
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  min-width: 120px;
  transition: all 0.15s ease;
}

.fselect:hover {
  border-color: var(--accent-secondary);
}

.fselect:focus {
  border-color: var(--accent-secondary);
  outline: none;
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

.finput {
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--text-primary);
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  width: 200px;
  transition: all 0.15s ease;
}

.finput:hover {
  border-color: var(--accent-secondary);
}

.finput:focus {
  border-color: var(--accent-secondary);
  outline: none;
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
  background: var(--bg-card);
}

/* ========================================
   Table - 浅色企业风格
   ======================================== */

.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.tbl th {
  padding: 12px 10px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 1px solid var(--border-default);
}

.tbl td {
  padding: 12px 10px;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-subtle);
}

.tbl tr:hover td {
  background: var(--bg-hover);
  cursor: pointer;
}

.td-mono {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--accent-secondary);
}

.td-action {
  color: var(--accent-secondary);
  cursor: pointer;
}

.td-action:hover {
  text-decoration: underline;
}

/* ========================================
   Tags / Badge - 状态标签
   ======================================== */

.tag {
  display: inline-block;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: var(--radius-sm);
}

.tag-blue {
  background: rgba(9, 132, 227, 0.1);
  color: var(--accent-secondary);
}

.tag-green {
  background: var(--success-bg);
  color: var(--accent-primary);
}

.tag-red {
  background: var(--danger-bg);
  color: var(--accent-danger);
}

.tag-yellow {
  background: var(--warn-bg);
  color: var(--accent-warning);
}

.tag-gray {
  background: var(--bg-hover);
  color: var(--text-secondary);
}

/* ========================================
   Pagination - 浅色风格
   ======================================== */

.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.page-info {
  font-size: 12px;
  font-family: 'Geist Mono', monospace;
  color: var(--text-secondary);
}

.page-btns {
  display: flex;
  gap: var(--gap-sm);
}

/* ========================================
   详情对话框 - form-section 风格
   ======================================== */

.tool-detail-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: var(--gap-md);
}

.tool-detail-dialog .section-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--gap-md);
  padding-bottom: var(--gap-sm);
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
}

.tool-detail-dialog .section-header .el-icon {
  color: var(--accent-secondary);
}

.tool-detail-dialog .detail-item {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.tool-detail-dialog .detail-item label {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.tool-detail-dialog .detail-item span {
  font-size: 13px;
  color: var(--text-primary);
}

.tool-detail-dialog .detail-item.full-width {
  flex-direction: row;
  align-items: center;
  gap: var(--gap-sm);
}

.tool-detail-dialog .detail-item.full-width label {
  min-width: 80px;
}

.tool-detail-dialog .mono-text {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
}

/* ========================================
   Log Content - VSCode Terminal 风格（深色）
   ======================================== */

.log-content {
  background: #1e1e1e;
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  border: 1px solid #3c3c3c;
}

.log-content pre {
  color: #cccccc;
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
}

.log-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
  padding: 40px;
  color: var(--text-secondary);
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}

.log-empty .el-icon {
  font-size: 32px;
  color: var(--text-muted);
}

/* ========================================
   暗色模式适配
   ======================================== */

.dark .tool-detail-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .tool-detail-dialog .section-header {
  color: var(--text-secondary);
  border-bottom-color: rgba(48, 54, 61, 0.4);
}

.dark .tool-detail-dialog .section-header .el-icon {
  color: var(--accent-primary);
}

.dark .log-content {
  background: #0d1117;
  border-color: #30363d;
}

.dark .log-content pre {
  color: #c9d1d9;
}

/* ========================================
   Responsive
   ======================================== */

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