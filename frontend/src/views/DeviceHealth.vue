<template>
  <div class="device-health-page">
    <!-- Header -->
    <div class="page-header">
      <h2>{{ t('healthTitle') || '设备健康评分' }}</h2>
      <div class="header-actions">
        <el-button type="primary" @click="calculateAllHealth" :loading="calculating">
          <el-icon><Refresh /></el-icon>
          {{ t('healthCalculateAll') || '批量计算' }}
        </el-button>
      </div>
    </div>

    <!-- Dashboard Stats -->
    <div class="dashboard-stats">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-card">
            <div class="stat-value">{{ dashboard.total_devices }}</div>
            <div class="stat-label">{{ t('healthTotalDevices') || '总设备数' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card health-score">
            <div class="stat-value">{{ dashboard.average_health_score }}</div>
            <div class="stat-label">{{ t('healthAvgScore') || '平均健康评分' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card risk-low">
            <div class="stat-value">{{ dashboard.risk_distribution?.low || 0 }}</div>
            <div class="stat-label">{{ t('healthLowRisk') || '低风险' }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card risk-critical">
            <div class="stat-value">{{ (dashboard.risk_distribution?.high || 0) + (dashboard.risk_distribution?.critical || 0) }}</div>
            <div class="stat-label">{{ t('healthHighRisk') || '高风险' }}</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Risk Distribution Chart -->
    <div class="charts-section">
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="chart-card">
            <div class="chart-title">{{ t('healthRiskDistribution') || '风险等级分布' }}</div>
            <div ref="riskChartRef" class="chart-container"></div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="chart-card">
            <div class="chart-title">{{ t('healthScoreDistribution') || '评分分布' }}</div>
            <div ref="scoreChartRef" class="chart-container"></div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="chart-card">
            <div class="chart-title">{{ t('healthHealthTrend') || '健康趋势' }}</div>
            <div ref="trendChartRef" class="chart-container"></div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Device Health List -->
    <div class="device-list-section">
      <div class="section-header">
        <h3>{{ t('healthDeviceList') || '设备健康列表' }}</h3>
        <div class="filters">
          <el-select v-model="filters.risk_level" placeholder="风险等级" clearable style="width: 150px">
            <el-option label="低风险" value="low" />
            <el-option label="中风险" value="medium" />
            <el-option label="高风险" value="high" />
            <el-option label="严重风险" value="critical" />
          </el-select>
          <el-input v-model="filters.search" placeholder="搜索设备名称" clearable style="width: 200px" />
        </div>
      </div>

      <el-table :data="filteredDevices" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="设备名称" width="180">
          <template #default="{ row }">
            <router-link :to="`/devices/${row.id}`" class="device-link">
              {{ row.name }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP地址" width="140" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="health_score" label="健康评分" width="200">
          <template #default="{ row }">
            <div class="health-score-cell">
              <el-progress
                :percentage="row.health_score || 100"
                :color="getHealthColor(row.health_score)"
                :stroke-width="12"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险等级" width="120">
          <template #default="{ row }">
            <el-tag :type="getRiskType(row.risk_level)" effect="dark" size="small">
              {{ getRiskLabel(row.risk_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="lifecycle_stage" label="生命周期" width="120">
          <template #default="{ row }">
            {{ getLifecycleLabel(row.lifecycle_stage) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_health_check" label="最后检查" width="160">
          <template #default="{ row }">
            {{ formatTime(row.last_health_check) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="calculateDeviceHealth(row.id)">
              {{ t('healthCalculate') || '计算' }}
            </el-button>
            <el-button type="info" size="small" @click="viewDeviceHealth(row.id)">
              {{ t('healthViewHistory') || '历史' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Health History Dialog -->
    <el-dialog
      v-model="historyDialogVisible"
      title="健康评分历史"
      width="800px"
    >
      <div v-if="selectedDeviceHistory.length > 0">
        <el-table :data="selectedDeviceHistory" style="width: 100%">
          <el-table-column prop="health_score" label="评分" width="100" />
          <el-table-column prop="risk_level" label="风险等级" width="120">
            <template #default="{ row }">
              <el-tag :type="getRiskType(row.risk_level)" size="small">
                {{ getRiskLabel(row.risk_level) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="trend" label="趋势" width="100">
            <template #default="{ row }">
              <el-icon v-if="row.trend === 'improving'" color="#67c23a"><Top /></el-icon>
              <el-icon v-else-if="row.trend === 'declining'" color="#f56c6c"><Bottom /></el-icon>
              <el-icon v-else color="#909399"><Minus /></el-icon>
            </template>
          </el-table-column>
          <el-table-column prop="last_calculated_at" label="计算时间" width="180">
            <template #default="{ row }">
              {{ formatTime(row.last_calculated_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="recommendations" label="建议">
            <template #default="{ row }">
              <div class="recommendations-list">
                <span v-for="(rec, idx) in row.recommendations" :key="idx" class="recommendation-item">
                  {{ rec }}
                </span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else class="empty-history">
        <el-empty description="暂无历史记录" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Top, Bottom, Minus } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getHealthDashboard, getHealthDevices, calculateAllHealth as calcAllHealth, calculateDeviceHealth as calcDeviceHealth, getDeviceHealthHistory } from '@/api'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

// Data
const loading = ref(false)
const calculating = ref(false)
const dashboard = ref({})
const devices = ref([])
const historyDialogVisible = ref(false)
const selectedDeviceHistory = ref([])

// Filters
const filters = ref({
  risk_level: '',
  search: ''
})

// Chart refs
const riskChartRef = ref(null)
const scoreChartRef = ref(null)
const trendChartRef = ref(null)

// Computed
const filteredDevices = computed(() => {
  let result = devices.value

  if (filters.value.risk_level) {
    result = result.filter(d => d.risk_level === filters.value.risk_level)
  }

  if (filters.value.search) {
    result = result.filter(d =>
      d.name?.toLowerCase().includes(filters.value.search.toLowerCase())
    )
  }

  // Sort by health score (lowest first)
  result = [...result].sort((a, b) => (a.health_score || 100) - (b.health_score || 100))

  return result
})

// Methods
const fetchDashboard = async () => {
  try {
    dashboard.value = await getHealthDashboard()

    // Initialize charts after data loaded
    await nextTick()
    initCharts()
  } catch (error) {
    console.error('Failed to fetch dashboard:', error)
  }
}

const fetchRiskDevices = async () => {
  try {
    loading.value = true
    const res = await getHealthDevices({ limit: 100 })
    devices.value = res.items || []
  } catch (error) {
    console.error('Failed to fetch devices:', error)
  } finally {
    loading.value = false
  }
}

const calculateAllHealth = async () => {
  try {
    calculating.value = true
    const res = await calcAllHealth()

    ElMessage.success(`计算完成: ${res.total} 个设备`)

    // Refresh data
    await fetchDashboard()
    await fetchRiskDevices()
  } catch (error) {
    ElMessage.error('批量计算失败')
    console.error(error)
  } finally {
    calculating.value = false
  }
}

const calculateDeviceHealth = async (deviceId) => {
  try {
    const res = await calcDeviceHealth(deviceId)
    ElMessage.success(`健康评分: ${res.health_score}, 风险等级: ${res.risk_level}`)

    // Refresh list
    await fetchRiskDevices()
  } catch (error) {
    ElMessage.error('计算失败')
    console.error(error)
  }
}

const viewDeviceHealth = async (deviceId) => {
  try {
    const res = await getDeviceHealthHistory(deviceId)
    selectedDeviceHistory.value = res.history || []
    historyDialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取历史失败')
    console.error(error)
  }
}

const initCharts = () => {
  // Risk Distribution Pie Chart
  if (riskChartRef.value) {
    const chart = echarts.init(riskChartRef.value)
    const riskData = dashboard.value.risk_distribution || {}

    chart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: '5%', left: 'center' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' }
        },
        data: [
          { value: riskData.low || 0, name: '低风险', itemStyle: { color: '#67c23a' } },
          { value: riskData.medium || 0, name: '中风险', itemStyle: { color: '#e6a23c' } },
          { value: riskData.high || 0, name: '高风险', itemStyle: { color: '#f56c6c' } },
          { value: riskData.critical || 0, name: '严重风险', itemStyle: { color: '#c45656' } }
        ]
      }]
    })
  }

  // Score Distribution Bar Chart
  if (scoreChartRef.value) {
    const chart = echarts.init(scoreChartRef.value)
    const scoreData = dashboard.value.score_distribution || {}

    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ['优秀(90-100)', '良好(70-89)', '一般(50-69)', '较差(0-49)']
      },
      yAxis: { type: 'value' },
      series: [{
        type: 'bar',
        data: [
          { value: scoreData.excellent || 0, itemStyle: { color: '#67c23a' } },
          { value: scoreData.good || 0, itemStyle: { color: '#409eff' } },
          { value: scoreData.fair || 0, itemStyle: { color: '#e6a23c' } },
          { value: scoreData.poor || 0, itemStyle: { color: '#f56c6c' } }
        ],
        barWidth: '60%'
      }]
    })
  }

  // Trend Line Chart (placeholder)
  if (trendChartRef.value) {
    const chart = echarts.init(trendChartRef.value)

    chart.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
      },
      yAxis: { type: 'value', min: 0, max: 100 },
      series: [{
        type: 'line',
        data: [85, 82, 88, 91, 87, 90, dashboard.value.average_health_score || 90],
        smooth: true,
        lineStyle: { color: '#409eff', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
          ])
        }
      }]
    })
  }
}

// Helper functions
const getHealthColor = (score) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  if (score >= 40) return '#f56c6c'
  return '#c45656'
}

const getRiskType = (level) => {
  const types = { low: 'success', medium: 'warning', high: 'danger', critical: 'danger' }
  return types[level] || 'info'
}

const getRiskLabel = (level) => {
  const labels = { low: '低风险', medium: '中风险', high: '高风险', critical: '严重' }
  return labels[level] || level
}

const getLifecycleLabel = (stage) => {
  const labels = { new: '新设备', active: '运行中', aging: '老化', retired: '已退役' }
  return labels[stage] || stage
}

const getStatusType = (status) => {
  const types = { online: 'success', offline: 'danger', maintenance: 'warning' }
  return types[status] || 'info'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// Lifecycle
onMounted(() => {
  fetchDashboard()
  fetchRiskDevices()
})
</script>

<style scoped>
.device-health-page {
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
  transition: all 0.3s;
}

.stat-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-card.health-score .stat-value {
  color: #409eff;
}

.stat-card.risk-low .stat-value {
  color: #67c23a;
}

.stat-card.risk-critical .stat-value {
  color: #f56c6c;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.charts-section {
  margin-bottom: 20px;
}

.chart-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #ebeef5;
}

.chart-title {
  font-size: 14px;
  color: #303133;
  margin-bottom: 10px;
}

.chart-container {
  height: 250px;
}

.device-list-section {
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

.filters {
  display: flex;
  gap: 10px;
}

.device-link {
  color: #409eff;
  text-decoration: none;
}

.device-link:hover {
  text-decoration: underline;
}

.health-score-cell {
  display: flex;
  align-items: center;
}

.recommendations-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.recommendation-item {
  font-size: 12px;
  color: #606266;
}

.empty-history {
  padding: 40px 0;
}

/* Operations column buttons alignment */
.el-table .el-button + .el-button {
  margin-left: 8px;
}

.el-table-column--fixed-right .cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>