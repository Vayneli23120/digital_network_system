<template>
  <div class="backups-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('backupTitle') }}</span>
          <div class="actions">
            <el-button type="primary" @click="showBatchBackupDialog = true">
              <el-icon><Download /></el-icon>
              {{ t('backupBatchBackup') }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          :placeholder="t('backupSearchPlaceholder')"
          style="width: 220px"
          clearable
          @input="filterBackups"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
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
        <el-select v-model="filterHasChange" :placeholder="t('backupConfigChange')" clearable style="width: 120px" @change="filterBackups">
          <el-option :label="t('backupHasChange')" value="true" />
          <el-option :label="t('backupNoChange')" value="false" />
        </el-select>
        <el-select v-model="sortBy" :placeholder="t('backupSort')" style="width: 150px" @change="filterBackups">
          <el-option :label="t('backupSortTimeDesc')" value="backup_time_desc" />
          <el-option :label="t('backupSortTimeAsc')" value="backup_time_asc" />
          <el-option :label="t('backupSortSizeDesc')" value="file_size_desc" />
          <el-option :label="t('backupSortSizeAsc')" value="file_size_asc" />
        </el-select>
      </div>

      <el-table :data="filteredBackups" style="width: 100%" v-loading="loading">
        <el-table-column prop="device_name" :label="t('backupColDevice')" width="180" />
        <el-table-column prop="backup_file" :label="t('backupColFile')" />
        <el-table-column prop="file_size" :label="t('backupColSize')" width="120">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="has_change" :label="t('backupConfigChange')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.has_change ? 'warning' : 'success'" size="small">
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
            <el-button size="small" @click="viewConfig(row.id)">{{ t('backupViewConfig') }}</el-button>
            <el-button size="small" @click="viewDiff(row.id)">{{ t('backupViewDiff') }}</el-button>
            <el-button size="small" @click="downloadBackup(row)">{{ t('backupDownload') }}</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoBackups')" :image-size="80">
            <el-button type="primary" size="small" @click="showBatchBackupDialog = true">{{ t('backupBatchBackup') }}</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadBackups" @current-change="loadBackups" />
      </div>
    </el-card>

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
import { Search, Download } from '@element-plus/icons-vue'
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
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

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
</style>
