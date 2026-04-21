<template>
  <div class="backups-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>备份记录</span>
          <div class="actions">
            <el-button type="primary" @click="showBatchBackupDialog = true">
              <el-icon><Download /></el-icon>
              批量备份
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索设备名称或文件名"
          style="width: 220px"
          clearable
          @input="filterBackups"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="filterBackups"
        />
        <el-select v-model="filterHasChange" placeholder="配置变更" clearable style="width: 120px" @change="filterBackups">
          <el-option label="有变更" value="true" />
          <el-option label="无变更" value="false" />
        </el-select>
        <el-select v-model="sortBy" placeholder="排序" style="width: 150px" @change="filterBackups">
          <el-option label="备份时间 ↓" value="backup_time_desc" />
          <el-option label="备份时间 ↑" value="backup_time_asc" />
          <el-option label="文件大小 ↓" value="file_size_desc" />
          <el-option label="文件大小 ↑" value="file_size_asc" />
        </el-select>
      </div>

      <el-table :data="filteredBackups" style="width: 100%" v-loading="loading">
        <el-table-column prop="device_name" label="设备名称" width="180" />
        <el-table-column prop="backup_file" label="备份文件" />
        <el-table-column prop="file_size" label="文件大小" width="120">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column prop="has_change" label="配置变更" width="100">
          <template #default="{ row }">
            <el-tag :type="row.has_change ? 'warning' : 'success'" size="small">
              {{ row.has_change ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="backup_time" label="备份时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.backup_time) }}</template>
        </el-table-column>
        <el-table-column prop="operator" label="操作员" width="100" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewConfig(row.id)">查看配置</el-button>
            <el-button size="small" @click="viewDiff(row.id)">对比差异</el-button>
            <el-button size="small" @click="downloadBackup(row)">下载</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadBackups" @current-change="loadBackups" />
      </div>
    </el-card>

    <!-- 查看配置对话框 -->
    <el-dialog v-model="showConfigDialog" title="配置内容" width="900px">
      <div v-if="configContent">
        <div class="config-header">
          <strong>设备:</strong> {{ configDeviceName }}
          <strong style="margin-left: 20px;">时间:</strong> {{ configBackupTime }}
        </div>
        <pre class="config-content">{{ configContent }}</pre>
      </div>
      <el-empty v-else description="暂无配置内容" />
    </el-dialog>

    <!-- 差异对比对话框 -->
    <el-dialog v-model="showDiffDialog" title="配置差异对比" width="900px">
      <div v-if="diffContent">
        <pre class="diff-content">{{ diffContent }}</pre>
      </div>
      <el-empty v-else description="暂无差异内容" />
    </el-dialog>

    <!-- 批量备份对话框 -->
    <el-dialog v-model="showBatchBackupDialog" title="批量备份" width="500px">
      <el-form label-width="100px">
        <el-form-item label="选择设备">
          <el-select v-model="selectedDeviceIds" multiple placeholder="选择设备" style="width: 100%">
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
        <el-button @click="showBatchBackupDialog = false">取消</el-button>
        <el-button type="primary" @click="doBatchBackup">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getBackups, getBackupContent, getBackupDiff, batchBackup, getDevices } from '@/api'
import { Search } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

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

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

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
    const startDate = dayjs(dateRange.value[0])
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(b => {
      const backupTime = dayjs(b.backup_time)
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
        result.sort((a, b) => dayjs(b.backup_time) - dayjs(a.backup_time))
        break
      case 'backup_time_asc':
        result.sort((a, b) => dayjs(a.backup_time) - dayjs(b.backup_time))
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
    ElMessage.error('加载备份记录失败')
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (error) {
    ElMessage.error('加载设备列表失败')
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
    ElMessage.error('获取配置失败')
    ElMessage.error('获取配置失败')
  }
}

const viewDiff = async (backupId) => {
  try {
    const data = await getBackupDiff(backupId)
    diffContent.value = data.diff || '没有差异内容'
    showDiffDialog.value = true
  } catch (error) {
    ElMessage.error('获取差异失败')
    ElMessage.error('获取差异失败')
  }
}

const downloadBackup = (row) => {
  // 创建下载链接
  const link = document.createElement('a')
  link.href = `/api/backups/${row.id}/download`
  link.download = `${row.device_name}_${row.backup_time}.cfg`
  link.click()
  ElMessage.info(`下载备份：${row.backup_file}`)
}

const doBatchBackup = async () => {
  if (selectedDeviceIds.value.length === 0) {
    ElMessage.warning('请选择至少一台设备')
    return
  }

  try {
    await batchBackup(selectedDeviceIds.value, 'Web')
    ElMessage.success('批量备份完成')
    showBatchBackupDialog.value = false
    loadBackups()
  } catch (error) {
    ElMessage.error('批量备份失败')
    ElMessage.error('批量备份失败')
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
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
