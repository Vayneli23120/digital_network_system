<template>
  <div class="logs-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>系统日志</span>
          <div class="actions">
            <el-button
              :type="isRealtime ? 'success' : 'primary'"
              @click="toggleRealtime"
              :icon="isRealtime ? VideoPause : VideoPlay"
            >
              {{ isRealtime ? '停止实时刷新' : '实时刷新' }}
            </el-button>
            <el-button @click="refreshLogs"><el-icon><Refresh /></el-icon> 刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索日志内容..."
          style="width: 250px"
          clearable
          @keyup.enter="searchLogs"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="logLevel" placeholder="日志级别" clearable style="width: 120px" @change="loadLogs">
          <el-option label="DEBUG" value="DEBUG" />
          <el-option label="INFO" value="INFO" />
          <el-option label="WARNING" value="WARNING" />
          <el-option label="ERROR" value="ERROR" />
        </el-select>
        <el-select v-model="timeRange" placeholder="时间范围" style="width: 150px" @change="loadLogs">
          <el-option label="最近 1 天" :value="1" />
          <el-option label="最近 3 天" :value="3" />
          <el-option label="最近 7 天" :value="7" />
          <el-option label="最近 30 天" :value="30" />
        </el-select>
        <el-input-number v-model="logLimit" :min="50" :max="500" :step="50" style="width: 150px" @change="loadLogs" />
        <span class="limit-label">条</span>
      </div>

      <!-- 日志表格 -->
      <el-table :data="logList" style="width: 100%" v-loading="loading" height="600px">
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.timestamp) }}</template>
        </el-table-column>
        <el-table-column prop="level" label="级别" width="90">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="150" />
        <el-table-column prop="function" label="函数" width="120" />
        <el-table-column prop="message" label="日志内容" min-width="400" show-overflow-tooltip />
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[50, 100, 200, 500]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </el-card>

    <!-- 日志文件列表对话框 -->
    <el-dialog v-model="showFilesDialog" title="日志文件列表" width="700px">
      <el-table :data="logFiles" v-loading="filesLoading">
        <el-table-column prop="filename" label="文件名" />
        <el-table-column prop="size" label="文件大小">
          <template #default="{ row }">{{ formatSize(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="modified" label="修改时间">
          <template #default="{ row }">{{ formatDateTime(row.modified) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button size="small" @click="viewLogFile(row.filename)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 查看日志文件内容对话框 -->
    <el-dialog v-model="showFileContentDialog" title="日志文件内容" width="900px">
      <div class="log-content" v-loading="fileContentLoading">
        <pre v-if="currentFileContent" class="log-pre">{{ currentFileContent }}</pre>
        <el-empty v-else description="暂无内容" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, VideoPlay, VideoPause } from '@element-plus/icons-vue'
import { getLogs, getLogFiles, getLogFileContent, searchLogs, clearOldLogs } from '@/api'

// 状态
const loading = ref(false)
const filesLoading = ref(false)
const fileContentLoading = ref(false)
const isRealtime = ref(false)
const realtimeTimer = ref(null)
const wsConnection = ref(null)

const logList = ref([])
const logFiles = ref([])
const currentFileContent = ref('')
const total = ref(0)

// 筛选条件
const searchKeyword = ref('')
const logLevel = ref('')
const timeRange = ref(7)
const logLimit = ref(100)
const currentPage = ref(1)
const pageSize = ref(100)

// 对话框
const showFilesDialog = ref(false)
const showFileContentDialog = ref(false)

// 格式化时间
const formatDateTime = (datetimeStr) => {
  if (!datetimeStr) return ''
  try {
    const date = new Date(datetimeStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  } catch {
    return datetimeStr
  }
}

// 格式化大小
const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

// 获取日志级别类型
const getLevelType = (level) => {
  const typeMap = {
    'DEBUG': 'info',
    'INFO': 'success',
    'WARNING': 'warning',
    'ERROR': 'danger'
  }
  return typeMap[level] || 'info'
}

// 加载日志
const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      days: timeRange.value,
      level: logLevel.value || undefined,
      limit: logLimit.value
    }
    const res = await getLogs(params)
    logList.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    ElMessage.error('加载日志失败：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 搜索日志
const searchLogsFunc = async () => {
  if (!searchKeyword.value.trim()) {
    loadLogs()
    return
  }
  loading.value = true
  try {
    const res = await searchLogs(searchKeyword.value, {
      days: timeRange.value,
      level: logLevel.value || undefined
    })
    logList.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    ElMessage.error('搜索日志失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 加载日志文件列表
const loadLogFiles = async () => {
  filesLoading.value = true
  try {
    const res = await getLogFiles({ days: timeRange.value })
    logFiles.value = res.items || []
  } catch (error) {
    ElMessage.error('加载日志文件列表失败：' + error.message)
  } finally {
    filesLoading.value = false
  }
}

// 查看日志文件内容
const viewLogFile = async (filename) => {
  fileContentLoading.value = true
  showFilesDialog.value = false
  showFileContentDialog.value = true
  try {
    const res = await getLogFileContent(filename, { lines: 500 })
    currentFileContent.value = res.items.map(item => {
      return `[${item.timestamp}] [${item.level}] ${item.message}`
    }).join('\n')
  } catch (error) {
    ElMessage.error('加载日志文件内容失败：' + error.message)
  } finally {
    fileContentLoading.value = false
  }
}

// 刷新日志
const refreshLogs = () => {
  loadLogs()
}

// 切换实时刷新
const toggleRealtime = () => {
  if (isRealtime.value) {
    // 停止实时刷新
    if (realtimeTimer.value) {
      clearInterval(realtimeTimer.value)
      realtimeTimer.value = null
    }
    isRealtime.value = false
    ElMessage.success('实时刷新已停止')
  } else {
    // 开始实时刷新
    isRealtime.value = true
    realtimeTimer.value = setInterval(() => {
      loadLogs()
    }, 3000)
    ElMessage.info('实时刷新已启动（每 3 秒自动刷新）')
  }
}

onMounted(() => {
  loadLogs()
})

onUnmounted(() => {
  if (realtimeTimer.value) {
    clearInterval(realtimeTimer.value)
    realtimeTimer.value = null
  }
})
</script>

<style scoped>
.logs-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}

.limit-label {
  color: #909399;
  font-size: 14px;
}

.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.log-content {
  max-height: 500px;
  overflow-y: auto;
}

.log-pre {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}
</style>
