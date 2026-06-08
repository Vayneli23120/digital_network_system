<template>
  <div class="backups-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuBackups') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn" @click="showBatchBackupDialog = true">
          <el-icon><Download /></el-icon>
          <span>{{ t('backupBatchBackup') }}</span>
        </button>
        <button class="nav-action-btn secondary" @click="loadBackups" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-grid">
        <!-- 总备份 -->
        <div class="stat-card total" @click="filterByChange('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.total }}</div>
              <div class="metric-label">{{ t('backupStatsTotal') }}</div>
            </div>
            <div class="card-trend stable">
              <span class="trend-icon">●</span>
            </div>
          </div>
        </div>
        <!-- 有变更 -->
        <div class="stat-card has-change" @click="filterByChange('true')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><WarningFilled /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value warning">{{ stats.hasChange }}</div>
              <div class="metric-label">{{ t('backupStatsHasChange') }}</div>
            </div>
            <div class="card-trend warning" v-if="stats.hasChange > 0">
              <el-icon><Warning /></el-icon>
            </div>
          </div>
        </div>
        <!-- 无变更 -->
        <div class="stat-card no-change" @click="filterByChange('false')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.noChange }}</div>
              <div class="metric-label">{{ t('backupStatsNoChange') }}</div>
            </div>
            <div class="card-trend success">
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
        <!-- 近期备份 -->
        <div class="stat-card recent" @click="filterByChange('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.recent }}</div>
              <div class="metric-label">{{ t('backupStatsRecent') }}</div>
            </div>
            <div class="card-progress">
              <div class="progress-ring" :style="{ '--percent': getRecentPercent() }"></div>
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
            :placeholder="t('backupSearchPlaceholder')"
            class="search-input"
            clearable
            @input="filterBackups"
          />
        </div>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <div
            :class="['status-chip', { active: filterHasChange === '' }]"
            @click="filterByChange('')"
          >
            <span class="chip-label">{{ t('backupFilterAll') }}</span>
            <span class="chip-count">{{ stats.total }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-has-change', { active: filterHasChange === 'true' }]"
            @click="filterByChange('true')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('backupFilterHasChange') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-no-change', { active: filterHasChange === 'false' }]"
            @click="filterByChange('false')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('backupFilterNoChange') }}</span>
          </div>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :range-separator="t('backupDateSeparator')"
            :start-placeholder="t('backupDateFrom')"
            :end-placeholder="t('backupDateTo')"
            value-format="YYYY-MM-DD"
            style="width: 240px"
            @change="filterBackups"
          />
          <el-select v-model="sortBy" :placeholder="t('backupSort')" style="width: 150px" @change="filterBackups">
            <el-option :label="t('backupSortTimeDesc')" value="backup_time_desc" />
            <el-option :label="t('backupSortTimeAsc')" value="backup_time_asc" />
            <el-option :label="t('backupSortSizeDesc')" value="file_size_desc" />
            <el-option :label="t('backupSortSizeAsc')" value="file_size_asc" />
          </el-select>
        </div>
      </div>
    </section>

    <!-- 备份数据面板 -->
    <section class="data-section">
      <div class="table-header">
        <span class="table-title">Backup Records</span>
        <span class="table-count">{{ filteredTotal }} records</span>
      </div>

      <el-table
        :data="filteredBackups"
        class="enterprise-table"
        v-loading="loading"
        :header-cell-style="{ background: 'transparent' }"
      >
        <!-- 设备名称 -->
        <el-table-column prop="device_name" :label="t('backupColDevice')" width="180">
          <template #default="{ row }">
            <div class="device-cell">
              <el-icon class="device-icon"><Connection /></el-icon>
              <span class="device-name">{{ row.device_name }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 备份文件 -->
        <el-table-column prop="backup_file" :label="t('backupColFile')">
          <template #default="{ row }">
            <div class="file-cell">
              <el-icon class="file-icon"><Document /></el-icon>
              <span class="file-name">{{ row.backup_file }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 文件大小 -->
        <el-table-column prop="file_size" :label="t('backupColSize')" width="120">
          <template #default="{ row }">
            <div class="size-cell">
              <span class="size-value">{{ formatSize(row.file_size) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 配置变更 -->
        <el-table-column prop="has_change" :label="t('backupConfigChange')" width="100">
          <template #default="{ row }">
            <div :class="['change-badge', row.has_change ? 'changed' : 'unchanged']">
              <span class="change-dot"></span>
              <span class="change-text">{{ row.has_change ? t('statusYes') : t('statusNo') }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 备份时间 -->
        <el-table-column prop="backup_time" :label="t('backupColTime')" width="180">
          <template #default="{ row }">
            <div class="time-cell">
              <el-icon class="time-icon"><Clock /></el-icon>
              <span class="time-text">{{ formatDateTime(row.backup_time) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 操作人 -->
        <el-table-column prop="operator" :label="t('backupColOperator')" width="120">
          <template #default="{ row }">
            <div class="owner-cell">
              <div class="owner-avatar">{{ (row.operator || '?')[0] }}</div>
              <span class="owner-name">{{ row.operator || '--' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column :label="t('backupColAction')" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <button class="action-btn view" @click="viewConfig(row.id)" title="查看配置">
                <el-icon><View /></el-icon>
              </button>
              <button class="action-btn diff" @click="viewDiff(row.id)" title="差异对比">
                <el-icon><DocumentCopy /></el-icon>
              </button>
              <button class="action-btn download" @click="downloadBackup(row)" title="下载">
                <el-icon><Download /></el-icon>
              </button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoBackups')" :image-size="80">
            <el-button type="primary" size="small" @click="showBatchBackupDialog = true">{{ t('backupBatchBackup') }}</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="filteredTotal" @size-change="handlePageSizeChange" @current-change="handlePageChange" />
      </div>
    </section>

    <!-- 查看配置对话框 -->
    <el-dialog v-model="showConfigDialog" :title="t('backupConfigContent')" width="900px">
      <div v-if="configContent">
        <div class="config-header">
          <strong>{{ t('backupDevice') }}:</strong> {{ configDeviceName }}
          <strong style="margin-left: 20px;">{{ t('backupTime') }}:</strong> {{ configBackupTime }}
        </div>
        <pre class="config-content">{{ configContent }}</pre>
      </div>
      <el-empty v-else :description="t('backupNoConfig')" />
    </el-dialog>

    <!-- 差异对比对话框 -->
    <el-dialog v-model="showDiffDialog" :title="t('backupDiffTitle')" width="900px">
      <div v-if="diffContent">
        <pre class="diff-content">{{ diffContent }}</pre>
      </div>
      <el-empty v-else :description="t('backupNoDiff')" />
    </el-dialog>

    <!-- 批量备份对话框 -->
    <el-dialog v-model="showBatchBackupDialog" :title="t('backupBatchBackup')" width="500px">
      <el-form label-width="100px">
        <el-form-item :label="t('backupSelectDevice')">
          <el-select v-model="selectedDeviceIds" multiple :placeholder="t('backupSelectDevice')" style="width: 100%">
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatchBackupDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="doBatchBackup">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getBackups, getBackupContent, getBackupDiff, batchBackup, getDevices } from '@/api'
import { Search, Download, Refresh, Document, WarningFilled, CircleCheck, Clock, View, DocumentCopy, Connection, Warning } from '@element-plus/icons-vue'
import { formatDateTime, toLocalDayjs, dayjs } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'

const { t } = useI18n()

const backups = ref([])
const filteredBackups = ref([])
const devices = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showConfigDialog = ref(false)
const showDiffDialog = ref(false)
const showBatchBackupDialog = ref(false)
const selectedDeviceIds = ref([])

const searchText = ref('')
const dateRange = ref([])
const filterHasChange = ref('')
const sortBy = ref('backup_time_desc')

const configContent = ref('')
const configDeviceName = ref('')
const configBackupTime = ref('')
const diffContent = ref('')

// 统计数据
const stats = computed(() => {
  const list = backups.value
  const totalCount = list.length
  const hasChangeCount = list.filter(b => b.has_change === true).length
  const noChangeCount = list.filter(b => b.has_change === false).length
  // 近7天内的备份
  const sevenDaysAgo = dayjs().subtract(7, 'day')
  const recentCount = list.filter(b => {
    const backupTime = toLocalDayjs(b.backup_time)
    return backupTime.isAfter(sevenDaysAgo)
  }).length
  return {
    total: totalCount,
    hasChange: hasChangeCount,
    noChange: noChangeCount,
    recent: recentCount
  }
})

// 分页后的总数
const filteredTotal = computed(() => filteredBackups.value.length)

// 近期备份百分比
const getRecentPercent = () => {
  if (stats.value.total === 0) return 0
  return Math.round((stats.value.recent / stats.value.total) * 100)
}

// 变更状态筛选
const filterByChange = (hasChange) => {
  filterHasChange.value = hasChange
  currentPage.value = 1
  filterBackups()
}

// 分页处理
const handlePageSizeChange = () => {
  currentPage.value = 1
}

const handlePageChange = () => {
  // 分页切换
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const filterBackups = () => {
  let result = [...backups.value]

  // 按搜索文本过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(b =>
      b.device_name?.toLowerCase().includes(search) ||
      b.backup_file?.toLowerCase().includes(search)
    )
  }

  // 按日期范围过滤
  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0]).startOf('day')
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(b => {
      // UTC 时间转换为本地时间进行比较
      const backupTime = toLocalDayjs(b.backup_time)
      return backupTime.isAfter(startDate) && backupTime.isBefore(endDate)
    })
  }

  // 按配置变更过滤
  if (filterHasChange.value !== '') {
    const hasChange = filterHasChange.value === 'true'
    result = result.filter(b => b.has_change === hasChange)
  }

  // 排序
  if (sortBy.value) {
    switch (sortBy.value) {
      case 'backup_time_desc':
        result.sort((a, b) => toLocalDayjs(b.backup_time).valueOf() - toLocalDayjs(a.backup_time).valueOf())
        break
      case 'backup_time_asc':
        result.sort((a, b) => toLocalDayjs(a.backup_time).valueOf() - toLocalDayjs(b.backup_time).valueOf())
        break
      case 'file_size_desc':
        result.sort((a, b) => (b.file_size || 0) - (a.file_size || 0))
        break
      case 'file_size_asc':
        result.sort((a, b) => (a.file_size || 0) - (b.file_size || 0))
        break
    }
  }

  filteredBackups.value = result
}

const loadBackups = async (force = false) => {
  loading.value = true
  try {
    const data = await cachedRequest(
      () => getBackups(),
      'backups',
      {},
      { forceRefresh: force }
    )
    backups.value = data.items || []
    filterBackups()
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('backupLoadRecordsFailed'))
    }
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (error) {
    ElMessage.error(t('backupLoadDevicesFailed'))
  }
}

const viewConfig = async (backupId) => {
  try {
    const data = await getBackupContent(backupId)
    configContent.value = data.content
    configDeviceName.value = data.device_name
    configBackupTime.value = formatDateTime(data.backup_time)
    showConfigDialog.value = true
  } catch (error) {
    ElMessage.error(t('backupGetConfigFailed'))
  }
}

const viewDiff = async (backupId) => {
  try {
    const data = await getBackupDiff(backupId)
    diffContent.value = data.diff || t('backupNoDiffContent')
    showDiffDialog.value = true
  } catch (error) {
    ElMessage.error(t('backupGetDiffFailed'))
  }
}

const downloadBackup = (row) => {
  // 创建下载链接
  const link = document.createElement('a')
  link.href = `/api/backups/${row.id}/download`
  link.download = `${row.device_name}_${row.backup_time}.cfg`
  link.click()
  ElMessage.info(`${t('backupDownloadMsg')}: ${row.backup_file}`)
}

const doBatchBackup = async () => {
  if (selectedDeviceIds.value.length === 0) {
    ElMessage.warning(t('backupSelectAtLeastOne'))
    return
  }

  try {
    await batchBackup(selectedDeviceIds.value, 'Web')
    clearCache('backups')
    ElMessage.success(t('backupBatchComplete'))
    showBatchBackupDialog.value = false
    loadBackups(true)
  } catch (error) {
    ElMessage.error(t('backupBatchFailed'))
  }
}

onMounted(() => {
  loadBackups()
  loadDevices()
})
</script>

<style scoped>
/* 字体清晰度优化 - 所有等宽字体 */
.metric-value,
.chip-count,
.table-count,
.size-value,
.time-text,
.change-text {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* ===== 页面整体背景 ===== */
.backups-page {
  padding: 0;
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
  grid-template-columns: repeat(4, 1fr);
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
.stat-card.has-change .card-icon {
  background: linear-gradient(135deg, rgba(225, 112, 85, 0.2) 0%, rgba(225, 112, 85, 0.1) 100%);
  color: #e17055;
}
.stat-card.no-change .card-icon {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.2) 0%, rgba(0, 184, 148, 0.1) 100%);
  color: #00b894;
}
.stat-card.recent .card-icon {
  background: linear-gradient(135deg, rgba(116, 185, 255, 0.2) 0%, rgba(116, 185, 255, 0.1) 100%);
  color: #74b9ff;
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

.metric-value.warning {
  color: #e17055;
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
.card-trend.warning { background: rgba(225, 112, 85, 0.1); color: #e17055; }
.card-trend.success { background: rgba(0, 184, 148, 0.1); color: #00b894; }

.card-progress {
  width: 24px;
  height: 24px;
  position: relative;
}

.progress-ring {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: conic-gradient(#74b9ff calc(var(--percent) * 1%), rgba(116, 185, 255, 0.2) 0);
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

.status-chip.chip-has-change .chip-dot { background: #e17055; }
.status-chip.chip-no-change .chip-dot { background: #00b894; }

.status-chip.chip-has-change:hover { background: rgba(225, 112, 85, 0.08); border-color: rgba(225, 112, 85, 0.3); }
.status-chip.chip-no-change:hover { background: rgba(0, 184, 148, 0.08); border-color: rgba(0, 184, 148, 0.3); }

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

/* 文件单元格 */
.file-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-icon {
  font-size: 14px;
  color: var(--text-tertiary);
}

.file-name {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 大小单元格 */
.size-cell {
  display: flex;
  align-items: center;
}

.size-value {
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* 变更徽章 */
.change-badge {
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

.change-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.change-text {
  letter-spacing: 0.02em;
}

.change-badge.changed {
  border-color: rgba(225, 112, 85, 0.3);
  color: #e17055;
}
.change-badge.changed .change-dot { background: #e17055; }

.change-badge.unchanged {
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}
.change-badge.unchanged .change-dot { background: #00b894; }

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

.action-btn.diff:hover {
  background: rgba(251, 191, 36, 0.08);
  border-color: rgba(251, 191, 36, 0.2);
  color: #f59e0b;
}

.action-btn.download:hover {
  background: rgba(0, 184, 148, 0.08);
  border-color: rgba(0, 184, 148, 0.2);
  color: #00b894;
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

/* 配置内容样式 */
.config-header {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  padding: 10px;
  background: rgba(0, 48, 135, 0.04);
  border-radius: 8px;
  border: 1px solid rgba(0, 48, 135, 0.08);
}

.config-content,
.diff-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 8px;
  font-family: 'JetBrains Mono', 'Geist Mono', Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 500px;
  overflow-y: auto;
  -webkit-font-smoothing: antialiased;
}

.diff-content :deep(.+) {
  color: #22863a;
}

.diff-content :deep(.-) {
  color: #cb2431;
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
.dark .backups-page {
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

.dark .metric-value.warning {
  color: #f85149;
}

.dark .metric-label {
  color: #8b949e;
}

.dark .card-trend.stable { background: rgba(9, 132, 227, 0.2); color: #58a6ff; }
.dark .card-trend.warning { background: rgba(225, 112, 85, 0.2); color: #f85149; }
.dark .card-trend.success { background: rgba(0, 184, 148, 0.2); color: #3fb950; }

.dark .progress-ring {
  background: conic-gradient(#74b9ff calc(var(--percent) * 1%), rgba(116, 185, 255, 0.2) 0);
}

.dark .progress-ring::after {
  background: #0d1117;
}

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

.dark .status-chip.chip-has-change:hover { background: rgba(248, 81, 73, 0.15); border-color: rgba(248, 81, 73, 0.4); }
.dark .status-chip.chip-no-change:hover { background: rgba(63, 185, 80, 0.15); border-color: rgba(63, 185, 80, 0.4); }

.dark .more-filters :deep(.el-select .el-input__wrapper),
.dark .more-filters :deep(.el-date-editor) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

/* 变更徽章暗黑模式 */
.dark .change-badge {
  background: rgba(13, 17, 23, 0.9);
}

.dark .change-badge.changed {
  border-color: rgba(248, 81, 73, 0.4);
  color: #f85149;
}
.dark .change-badge.changed .change-dot { background: #f85149; }

.dark .change-badge.unchanged {
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}
.dark .change-badge.unchanged .change-dot { background: #3fb950; }

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

.dark .device-name {
  color: #c9d1d9;
}

.dark .file-name {
  color: #c9d1d9;
}

.dark .size-value {
  color: #8b949e;
}

.dark .time-text {
  color: #8b949e;
}

.dark .owner-name {
  color: #8b949e;
}

.dark .owner-avatar {
  background: linear-gradient(135deg, #0984e3, #74b9ff);
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

.dark .action-btn.diff:hover {
  background: rgba(210, 153, 34, 0.15);
  border-color: rgba(210, 153, 34, 0.3);
  color: #d29922;
}

.dark .action-btn.download:hover {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.3);
  color: #3fb950;
}

.dark .config-header {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}
</style>