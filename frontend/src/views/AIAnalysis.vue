<template>
  <div class="ai-analysis-page">
    <!-- Header -->
    <div class="page-header">
      <h2>{{ $t('ai.title') || 'AI分析中心' }}</h2>
      <div class="header-actions">
        <el-button @click="refreshDashboard">
          <el-icon><Refresh /></el-icon>
          {{ $t('common.refresh') || '刷新' }}
        </el-button>
      </div>
    </div>

    <!-- AI Dashboard Stats -->
    <div class="dashboard-stats">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ dashboard.total_calls || 0 }}</div>
            <div class="stat-label">{{ $t('ai.totalCalls') || '总分析次数' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card success">
            <div class="stat-value">{{ dashboard.success_rate || 0 }}%</div>
            <div class="stat-label">{{ $t('ai.successRate') || '成功率' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card info">
            <div class="stat-value">{{ dashboard.total_tokens || 0 }}</div>
            <div class="stat-label">{{ $t('ai.totalTokens') || 'Token使用' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card warning">
            <div class="stat-value">¥{{ dashboard.total_cost || 0 }}</div>
            <div class="stat-label">{{ $t('ai.totalCost') || '总成本' }}</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Providers Status -->
    <div class="providers-section">
      <div class="section-title">{{ $t('ai.providers') || 'AI Provider状态' }}</div>
      <el-row :gutter="20">
        <el-col :span="12" v-for="provider in providers" :key="provider.provider">
          <div class="provider-card" :class="{ available: provider.available }">
            <div class="provider-name">{{ provider.provider }}</div>
            <div class="provider-model">{{ provider.model }}</div>
            <el-tag :type="provider.available ? 'success' : 'info'" size="small">
              {{ provider.available ? '可用' : '未配置' }}
            </el-tag>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <div class="section-title">{{ $t('ai.quickActions') || '快速分析' }}</div>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="action-card" @click="openFaultAnalysisDialog">
            <el-icon size="32"><Warning /></el-icon>
            <div class="action-title">{{ $t('ai.analyzeFault') || '故障分析' }}</div>
            <div class="action-desc">AI辅助故障根因分析</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="action-card" @click="openHealthAnalysisDialog">
            <el-icon size="32"><Monitor /></el-icon>
            <div class="action-title">{{ $t('ai.analyzeHealth') || '健康分析' }}</div>
            <div class="action-desc">AI辅助健康评分</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="action-card" @click="openPMDialog">
            <el-icon size="32"><Calendar /></el-icon>
            <div class="action-title">{{ $t('ai.predictive') || '预测性维护' }}</div>
            <div class="action-desc">预测维护需求</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="action-card" @click="openSummaryDialog">
            <el-icon size="32"><Document /></el-icon>
            <div class="action-title">{{ $t('ai.summary') || '维修总结' }}</div>
            <div class="action-desc">生成维修报告</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Analysis History -->
    <div class="history-section">
      <div class="section-header">
        <h3>{{ $t('ai.history') || '分析历史' }}</h3>
        <el-select v-model="historyFilter" placeholder="类型筛选" clearable style="width: 150px">
          <el-option label="故障分析" value="fault" />
          <el-option label="健康分析" value="health" />
          <el-option label="预测性维护" value="pm_recommend" />
          <el-option label="维修总结" value="summary" />
        </el-select>
      </div>

      <el-table :data="filteredHistory" style="width: 100%" v-loading="historyLoading">
        <el-table-column prop="analysis_type" label="类型" width="120">
          <template #default="{ row }">
            {{ getTypeLabel(row.analysis_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="target_type" label="目标" width="100">
          <template #default="{ row }">
            {{ getTargetLabel(row.target_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="provider" label="Provider" width="120" />
        <el-table-column prop="model" label="模型" width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'danger'" size="small">
              {{ row.status === 'completed' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="{ row }">
            {{ row.confidence ? `${(row.confidence * 100).toFixed(0)}%` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="processing_time_ms" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.processing_time_ms ? `${row.processing_time_ms}ms` : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="tokens_used" label="Tokens" width="100" />
        <el-table-column prop="cost" label="成本" width="100">
          <template #default="{ row }">
            ¥{{ row.cost?.toFixed(4) || '0' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewAnalysisDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Fault Analysis Dialog -->
    <el-dialog v-model="faultDialogVisible" title="故障AI分析" width="600px">
      <el-form :model="faultForm" label-width="100px">
        <el-form-item label="选择故障">
          <el-select v-model="faultForm.fault_id" placeholder="选择要分析的故障" style="width: 100%">
            <el-option v-for="f in activeFaults" :key="f.id" :label="f.fault_no + ' - ' + f.device_name" :value="f.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="自动创建维修单">
          <el-switch v-model="faultForm.auto_create_maintenance" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="faultDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="analyzeFault" :loading="analyzing">开始分析</el-button>
      </template>
    </el-dialog>

    <!-- Health Analysis Dialog -->
    <el-dialog v-model="healthDialogVisible" title="设备健康AI分析" width="600px">
      <el-form :model="healthForm" label-width="100px">
        <el-form-item label="选择设备">
          <el-select v-model="healthForm.device_id" placeholder="选择要分析的设备" style="width: 100%">
            <el-option v-for="d in devices" :key="d.id" :label="d.name + ' (' + d.ip + ')'" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="更新健康评分">
          <el-switch v-model="healthForm.update_health_score" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="healthDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="analyzeHealth" :loading="analyzing">开始分析</el-button>
      </template>
    </el-dialog>

    <!-- Analysis Result Dialog -->
    <el-dialog v-model="resultDialogVisible" title="分析结果" width="800px">
      <div v-if="analysisResult" class="analysis-result">
        <div class="result-header">
          <el-tag :type="analysisResult.success ? 'success' : 'danger'" size="large">
            {{ analysisResult.success ? '分析成功' : '分析失败' }}
          </el-tag>
          <span class="result-provider">{{ analysisResult.provider }} / {{ analysisResult.model }}</span>
        </div>

        <div v-if="analysisResult.result" class="result-content">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="分析类型">
              {{ getTypeLabel(analysisResult.analysis_type) }}
            </el-descriptions-item>
            <el-descriptions-item label="置信度">
              {{ analysisResult.confidence ? `${(analysisResult.confidence * 100).toFixed(0)}%` : '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="处理耗时">
              {{ analysisResult.processing_time_ms ? `${analysisResult.processing_time_ms}ms` : '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="Token使用">
              {{ analysisResult.tokens_used || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="result-details">
            <h4>分析结果详情</h4>
            <pre class="result-json">{{ JSON.stringify(analysisResult.result, null, 2) }}</pre>
          </div>

          <div v-if="analysisResult.created_maintenance_id" class="created-maintenance">
            <el-alert type="success" :closable="false">
              已自动创建维修单: {{ analysisResult.created_maintenance_no }}
            </el-alert>
          </div>
        </div>

        <div v-else class="result-error">
          <el-alert type="error" :closable="false">
            {{ analysisResult.error }}
          </el-alert>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Warning, Monitor, Calendar, Document } from '@element-plus/icons-vue'
import api from '@/api/request'

// Data
const dashboard = ref({})
const providers = ref([])
const history = ref([])
const activeFaults = ref([])
const devices = ref([])
const historyLoading = ref(false)
const analyzing = ref(false)
const historyFilter = ref('')
const analysisResult = ref(null)

// Dialog visibility
const faultDialogVisible = ref(false)
const healthDialogVisible = ref(false)
const resultDialogVisible = ref(false)

// Forms
const faultForm = ref({
  fault_id: null,
  auto_create_maintenance: false
})

const healthForm = ref({
  device_id: null,
  update_health_score: true
})

// Computed
const filteredHistory = computed(() => {
  if (!historyFilter.value) return history.value
  return history.value.filter(h => h.analysis_type === historyFilter.value)
})

// Methods
const refreshDashboard = async () => {
  try {
    const res = await api.get('/ai/dashboard')
    dashboard.value = res
    providers.value = res.providers_available || []
  } catch (error) {
    console.error('Failed to fetch dashboard:', error)
  }
}

const fetchHistory = async () => {
  try {
    historyLoading.value = true
    const res = await api.get('/ai/history', { params: { limit: 50 } })
    history.value = res.history || []
  } catch (error) {
    console.error('Failed to fetch history:', error)
  } finally {
    historyLoading.value = false
  }
}

const fetchActiveFaults = async () => {
  try {
    const res = await api.get('/faults', {
      params: { status: 'open,investigating', limit: 50 }
    })
    activeFaults.value = res.items || []
  } catch (error) {
    console.error('Failed to fetch faults:', error)
  }
}

const fetchDevices = async () => {
  try {
    const res = await api.get('/devices', { params: { limit: 100 } })
    devices.value = res.items || []
  } catch (error) {
    console.error('Failed to fetch devices:', error)
  }
}

const openFaultAnalysisDialog = async () => {
  await fetchActiveFaults()
  faultDialogVisible.value = true
}

const openHealthAnalysisDialog = async () => {
  await fetchDevices()
  healthDialogVisible.value = true
}

const openPMDialog = () => {
  ElMessage.info('预测性维护功能正在开发中')
}

const openSummaryDialog = () => {
  ElMessage.info('维修总结功能正在开发中')
}

const analyzeFault = async () => {
  if (!faultForm.value.fault_id) {
    ElMessage.warning('请选择要分析的故障')
    return
  }

  try {
    analyzing.value = true
    const res = await api.post(`/faults/${faultForm.value.fault_id}/analyze`, {
      auto_create_maintenance: faultForm.value.auto_create_maintenance
    })

    analysisResult.value = res
    faultDialogVisible.value = false

    if (res.success) {
      ElMessage.success('AI分析完成')
    } else {
      ElMessage.error(res.error || '分析失败')
    }

    await fetchHistory()
  } catch (error) {
    ElMessage.error('分析请求失败')
    console.error(error)
  } finally {
    analyzing.value = false
  }
}

const analyzeHealth = async () => {
  if (!healthForm.value.device_id) {
    ElMessage.warning('请选择要分析的设备')
    return
  }

  try {
    analyzing.value = true
    const res = await api.post('/ai/analyze-health', {
      device_id: healthForm.value.device_id,
      update_health_score: healthForm.value.update_health_score
    })

    analysisResult.value = res
    healthDialogVisible.value = false

    if (res.success) {
      ElMessage.success('AI健康分析完成')
    }

    await fetchHistory()
  } catch (error) {
    ElMessage.error('分析请求失败')
    console.error(error)
  } finally {
    analyzing.value = false
  }
}

const viewAnalysisDetail = (row) => {
  // TODO: Fetch full analysis details
  ElMessage.info('详情查看功能正在开发中')
}

// Helper functions
const getTypeLabel = (type) => {
  const labels = {
    fault: '故障分析',
    health: '健康分析',
    pm_recommend: '预测性维护',
    summary: '维修总结',
    root_cause: '根因分析'
  }
  return labels[type] || type
}

const getTargetLabel = (target) => {
  const labels = { device: '设备', fault: '故障', maintenance: '维修' }
  return labels[target] || target
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// Lifecycle
onMounted(() => {
  refreshDashboard()
  fetchHistory()
})
</script>

<style scoped>
.ai-analysis-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  color: #303133;
}

.dashboard-stats {
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  border: 1px solid #ebeef5;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-card.success .stat-value {
  color: #67c23a;
}

.stat-card.info .stat-value {
  color: #409eff;
}

.stat-card.warning .stat-value {
  color: #e6a23c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.section-title {
  font-size: 16px;
  color: #303133;
  margin-bottom: 15px;
}

.providers-section {
  margin-bottom: 20px;
}

.provider-card {
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  border: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  gap: 15px;
}

.provider-card.available {
  border-color: #67c23a;
}

.provider-name {
  font-size: 16px;
  font-weight: bold;
}

.provider-model {
  font-size: 12px;
  color: #909399;
}

.quick-actions {
  margin-bottom: 20px;
}

.action-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  border: 1px solid #ebeef5;
  cursor: pointer;
  transition: all 0.3s;
}

.action-card:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
}

.action-card .el-icon {
  color: #409eff;
  margin-bottom: 10px;
}

.action-title {
  font-size: 14px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.action-desc {
  font-size: 12px;
  color: #909399;
}

.history-section {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
}

.analysis-result {
  padding: 20px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.result-provider {
  font-size: 14px;
  color: #909399;
}

.result-content {
  margin-top: 20px;
}

.result-details {
  margin-top: 20px;
}

.result-details h4 {
  margin-bottom: 10px;
  font-size: 14px;
}

.result-json {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  font-size: 12px;
  overflow-x: auto;
}

.created-maintenance {
  margin-top: 20px;
}

.result-error {
  margin-top: 20px;
}
</style>