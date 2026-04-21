<template>
  <div class="tool-logs-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>工具执行日志</span>
          <div class="actions">
            <el-button @click="loadLogs"><el-icon><Refresh /></el-icon> 刷新</el-button>
            <el-button type="danger" @click="cleanupLogs">清理旧日志</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="filterToolType" placeholder="工具类型" clearable style="width: 150px" @change="loadLogs">
          <el-option label="Netmiko" value="netmiko" />
          <el-option label="NAPALM" value="napalm" />
          <el-option label="JIRA" value="jira" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="loadLogs">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
          <el-option label="运行中" value="running" />
        </el-select>
        <el-input v-model="searchKeyword" placeholder="搜索操作/目标..." style="width: 250px" clearable @keyup.enter="loadLogs" />
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" style="width: 240px" @change="loadLogs" />
      </div>

      <!-- 统计卡片 -->
      <el-row :gutter="16" class="stats-row">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="总执行次数" :value="stats.total" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="成功" :value="stats.success" value-style="color: #67C23A" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="失败" :value="stats.failed" value-style="color: #F56C6C" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="平均耗时" :value="stats.avgDuration" suffix="ms" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 日志表格 -->
      <el-table :data="logList" v-loading="loading" style="width: 100%" @row-click="showDetail">
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.timestamp) }}</template>
        </el-table-column>
        <el-table-column prop="tool_type" label="工具" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.tool_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operation" label="操作" min-width="200" show-overflow-tooltip />
        <el-table-column prop="target" label="目标" width="180" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时" width="100">
          <template #default="{ row }">{{ row.duration_ms ? row.duration_ms + 'ms' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_by" label="操作人" width="120" />
      </el-table>

      <!-- 分页 -->
      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          layout="total, sizes, prev, pager, next"
          :total="total"
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="日志详情" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="工具类型">{{ selectedLog?.tool_type }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(selectedLog?.status)" size="small">{{ selectedLog?.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="操作" :span="2">{{ selectedLog?.operation }}</el-descriptions-item>
        <el-descriptions-item label="目标">{{ selectedLog?.target || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作人">{{ selectedLog?.created_by || '-' }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ selectedLog?.duration_ms ? selectedLog.duration_ms + 'ms' : '-' }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatDateTime(selectedLog?.timestamp) }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="selectedLog?.log_content" class="log-content">
        <h4>日志内容</h4>
        <pre>{{ selectedLog.log_content }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getToolLogs, getToolLogStats, cleanupToolLogs } from '@/api'

const loading = ref(false)
const logList = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(50)
const showDetailDialog = ref(false)
const selectedLog = ref(null)

const filterToolType = ref('')
const filterStatus = ref('')
const searchKeyword = ref('')
const dateRange = ref(null)

const stats = reactive({ total: 0, success: 0, failed: 0, avgDuration: 0 })

const loadStats = async () => {
  try {
    const res = await getToolLogStats()
    Object.assign(stats, res)
  } catch (error) {
    // Stats endpoint may not exist yet, ignore
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
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0].toISOString()
      params.end_date = dateRange.value[1].toISOString()
    }
    const res = await getToolLogs(params)
    logList.value = res.items || []
    total.value = res.total || 0
  } catch (error) {
    ElMessage.error('加载日志失败：' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const showDetail = (row) => {
  selectedLog.value = row
  showDetailDialog.value = true
}

const getStatusType = (status) => {
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
    await ElMessageBox.confirm('确认清理 30 天前的旧日志？', '清理确认', { type: 'warning' })
    await cleanupToolLogs(30)
    ElMessage.success('清理完成')
    loadLogs()
    loadStats()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清理失败：' + error.message)
    }
  }
}

onMounted(() => {
  loadLogs()
  loadStats()
})
</script>

<style scoped>
.tool-logs-page { padding: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.filter-bar { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-card :deep(.el-card__body) { padding: 16px; }
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
.log-content { margin-top: 16px; }
.log-content pre { background: #f5f7fa; padding: 12px; border-radius: 4px; max-height: 300px; overflow: auto; font-size: 12px; }
</style>
