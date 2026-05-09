<template>
  <div class="backups-page">
    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-header">
        <span class="stats-title">{{ t('backupStatsTitle') }}</span>
        <button class="refresh-btn" @click="loadBackups" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
      <div class="stats-grid">
        <!-- 总备份 -->
        <div class="stat-card total" @click="filterByChange('')">
          <div class="card-icon">
            <el-icon><Document /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.total }}</div>
            <div class="metric-label">{{ t('backupStatsTotal') }}</div>
          </div>
        </div>
        <!-- 有变更 -->
        <div class="stat-card has-change" @click="filterByChange('true')">
          <div class="card-icon">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value warning">{{ stats.hasChange }}</div>
            <div class="metric-label">{{ t('backupStatsHasChange') }}</div>
          </div>
        </div>
        <!-- 无变更 -->
        <div class="stat-card no-change" @click="filterByChange('false')">
          <div class="card-icon">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.noChange }}</div>
            <div class="metric-label">{{ t('backupStatsNoChange') }}</div>
          </div>
        </div>
        <!-- 近期备份 -->
        <div class="stat-card recent" @click="filterByChange('')">
          <div class="card-icon">
            <el-icon><Clock /></el-icon>
          </div>
          <div class="card-body">
            <div class="metric-value">{{ stats.recent }}</div>
            <div class="metric-label">{{ t('backupStatsRecent') }}</div>
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
          :placeholder="t('backupSearchPlaceholder')"
          class="search-input"
          clearable
          @input="filterBackups"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>

        <!-- 状态 Chips -->
        <div class="status-chips">
          <el-tag
            :class="['status-chip', { active: filterHasChange === '' }]"
            @click="filterByChange('')"
          >{{ t('backupFilterAll') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-has-change', { active: filterHasChange === 'true' }]"
            type="warning"
            @click="filterByChange('true')"
          >{{ t('backupFilterHasChange') }}</el-tag>
          <el-tag
            :class="['status-chip', 'chip-no-change', { active: filterHasChange === 'false' }]"
            type="success"
            @click="filterByChange('false')"
          >{{ t('backupFilterNoChange') }}</el-tag>
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

        <!-- 批量备份按钮 -->
        <el-button type="primary" class="add-btn" @click="showBatchBackupDialog = true">
          <el-icon><Download /></el-icon>
          {{ t('backupBatchBackup') }}
        </el-button>
      </div>
    </section>

    <!-- 备份数据面板 -->
    <section class="data-section">
      <el-table :data="filteredBackups" class="modern-table" style="width: 100%" v-loading="loading">
        <el-table-column prop="device_name" :label="t('backupColDevice')" width="180" />
        <el-table-column prop="backup_file" :label="t('backupColFile')" />
        <el-table-column prop="file_size" :label="t('backupColSize')" width="120">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="has_change" :label="t('backupConfigChange')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.has_change ? 'warning' : 'success'" size="small" class="status-tag">
              {{ row.has_change ? t('statusYes') : t('statusNo') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="backup_time" :label="t('backupColTime')" width="180">
          <template #default="{ row }">{{ formatDateTime(row.backup_time) }}</template>
        </el-table-column>
        <el-table-column prop="operator" :label="t('backupColOperator')" width="100" />
        <el-table-column :label="t('backupColAction')" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-icons">
              <el-button size="small" @click="viewConfig(row.id)">{{ t('backupViewConfig') }}</el-button>
              <el-button size="small" @click="viewDiff(row.id)">{{ t('backupViewDiff') }}</el-button>
              <el-button size="small" @click="downloadBackup(row)">{{ t('backupDownload') }}</el-button>
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
import { Search, Download, Refresh, Document, WarningFilled, CircleCheck, Clock } from '@element-plus/icons-vue'
import { formatDateTime, toLocalDayjs, dayjs } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'

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

const loadBackups = async () => {
  loading.value = true
  try {
    const data = await getBackups()
    backups.value = data.items || []
    filterBackups()
  } catch (error) {
    ElMessage.error(t('backupLoadRecordsFailed'))
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
    ElMessage.success(t('backupBatchComplete'))
    showBatchBackupDialog.value = false
    loadBackups()
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
.backups-page {
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
  grid-template-columns: repeat(4, 1fr);
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

.stat-card.has-change .card-icon {
  background: rgba(225, 112, 85, 0.15);
  color: #e17055;
}

.stat-card.no-change .card-icon {
  background: rgba(0, 184, 148, 0.15);
  color: #00b894;
}

.stat-card.recent .card-icon {
  background: rgba(116, 185, 255, 0.15);
  color: #74b9ff;
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

.metric-value.warning {
  color: #e17055;
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

.status-chip.chip-has-change {
  background: rgba(225, 112, 85, 0.1);
  border-color: rgba(225, 112, 85, 0.3);
  color: #e17055;
}

.status-chip.chip-no-change {
  background: rgba(0, 184, 148, 0.1);
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}

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

/* 状态标签 */
.status-tag {
  font-weight: 500;
}

/* 操作图标 */
.action-icons {
  display: flex;
  gap: 4px;
}

/* 分页 */
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* 配置内容样式 */
.config-header {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.config-content,
.diff-content {
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

.diff-content {
  background: #1e1e1e;
}

.diff-content :deep(.+) {
  color: #22863a;
}

.diff-content :deep(.-) {
  color: #cb2431;
}

/* ===== 响应式 ===== */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
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
.dark .stat-card.has-change .card-icon { background: rgba(225, 112, 85, 0.2); }
.dark .stat-card.no-change .card-icon { background: rgba(0, 184, 148, 0.2); }
.dark .stat-card.recent .card-icon { background: rgba(116, 185, 255, 0.2); }

.dark .status-chip.chip-has-change { background: rgba(225, 112, 85, 0.15); }
.dark .status-chip.chip-no-change { background: rgba(0, 184, 148, 0.15); }
</style>