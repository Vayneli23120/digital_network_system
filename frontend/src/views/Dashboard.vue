<template>
  <div class="dashboard">
    <!-- 顶部指标卡 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <el-card class="stat-card online">
          <div class="stat-icon"><el-icon class="icon"><CircleCheck /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.devices?.online || 0 }}</div>
            <div class="stat-label">在线设备</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card offline">
          <div class="stat-icon"><el-icon class="icon"><CircleClose /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.devices?.offline || 0 }}</div>
            <div class="stat-label">离线设备</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card maintenance">
          <div class="stat-icon"><el-icon class="icon"><Tools /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.devices?.maintenance || 0 }}</div>
            <div class="stat-label">维护中</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card cost">
          <div class="stat-icon"><el-icon class="icon"><Money /></el-icon></div>
          <div class="stat-content">
            <div class="stat-value">¥{{ (stats.costs?.month_total || 0).toLocaleString() }}</div>
            <div class="stat-label">本月运维成本</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>设备状态分布</span>
            </div>
          </template>
          <div ref="devicePieChart" class="chart"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>故障趋势</span>
              <div class="trend-controls">
                <div class="fault-total">
                  <span class="label">总故障数：</span>
                  <span class="value">{{ faultTotal }}<span class="unit">次</span></span>
                </div>
                <el-select v-model="faultTimeRange" size="small" @change="updateFaultChart">
                  <el-option label="近 7 天" value="7d" />
                  <el-option label="近 30 天" value="30d" />
                  <el-option label="近 3 个月" value="3m" />
                  <el-option label="近 1 年" value="1y" />
                  <el-option label="自定义" value="custom" />
                </el-select>
                <el-date-picker
                  v-if="faultTimeRange === 'custom'"
                  v-model="customDateRange"
                  type="daterange"
                  size="small"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  @change="updateFaultChart"
                  style="margin-left: 10px"
                />
              </div>
            </div>
          </template>
          <div ref="faultLineChart" class="chart"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="tables-row">
      <!-- 最近备份记录 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近备份记录</span>
              <el-button type="primary" size="small" @click="$router.push('/backups')">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentBackups" style="width: 100%" :height="250">
            <el-table-column prop="device_name" label="设备名称" />
            <el-table-column prop="backup_time" label="备份时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.backup_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="has_change" label="配置变更" width="80">
              <template #default="{ row }">
                <el-tag :type="row.has_change ? 'warning' : 'success'" size="small">
                  {{ row.has_change ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 待办事项 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>待办事项</span>
            </div>
          </template>
          <el-timeline>
            <el-timeline-item type="warning" placement="top">
              <el-card>
                <h4>3 台设备超过 30 天未备份</h4>
                <p>请及时进行配置备份</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item type="info" placement="top">
              <el-card>
                <h4>2 台设备保修期即将到期</h4>
                <p>请联系供应商确认保修状态</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item type="success" placement="top">
              <el-card>
                <h4>本周备份任务完成</h4>
                <p>所有设备配置已备份</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getDashboardSummary, getFaultTrend } from '@/api'
import dayjs from 'dayjs'

const stats = ref({})
const recentBackups = ref([])
const devicePieChart = ref(null)
const faultLineChart = ref(null)
const faultTimeRange = ref('30d')
const faultChartInstance = ref(null)
const customDateRange = ref([dayjs().subtract(30, 'day'), dayjs()])
const faultTotal = ref(0)
const faultData = ref({ labels: [], by_severity: [] })
const selectedLegends = ref(['严重', '主要', '次要', '警告'])

const formatDate = (dateStr) => {
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm')
}

const loadDashboardData = async () => {
  try {
    const data = await getDashboardSummary()
    stats.value = data
    recentBackups.value = data.backups?.recent || []

    nextTick(() => {
      initDevicePieChart(data.devices)
      initFaultLineChart()
      updateFaultChart()
    })
  } catch (error) {
    ElMessage.error('加载 Dashboard 数据失败：' + (error.response?.data?.detail || error.message))
  }
}

const initDevicePieChart = (devices) => {
  const chart = echarts.init(devicePieChart.value)
  chart.setOption({
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      left: 'left'
    },
    series: [
      {
        name: '设备状态',
        type: 'pie',
        radius: '60%',
        data: [
          { value: devices?.online || 0, name: '在线' },
          { value: devices?.offline || 0, name: '离线' },
          { value: devices?.maintenance || 0, name: '维护中' },
          { value: devices?.retired || 0, name: '已退役' }
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  })
}

const initFaultLineChart = () => {
  faultChartInstance.value = echarts.init(faultLineChart.value)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    legend: {
      data: ['严重', '主要', '次要', '警告'],
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: [],
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      name: '故障次数',
      minInterval: 1
    },
    series: [
      {
        name: '严重',
        type: 'line',
        stack: '总量',
        smooth: true,
        areaStyle: {
          opacity: 0.3
        },
        itemStyle: {
          color: '#F56C6C'
        },
        data: []
      },
      {
        name: '主要',
        type: 'line',
        stack: '总量',
        smooth: true,
        areaStyle: {
          opacity: 0.3
        },
        itemStyle: {
          color: '#E6A23C'
        },
        data: []
      },
      {
        name: '次要',
        type: 'line',
        stack: '总量',
        smooth: true,
        areaStyle: {
          opacity: 0.3
        },
        itemStyle: {
          color: '#409EFF'
        },
        data: []
      },
      {
        name: '警告',
        type: 'line',
        stack: '总量',
        smooth: true,
        areaStyle: {
          opacity: 0.3
        },
        itemStyle: {
          color: '#909399'
        },
        data: []
      }
    ]
  }

  faultChartInstance.value.setOption(option)

  // 绑定图例点击事件
  faultChartInstance.value.on('legendselectchanged', legendClickHandler)
}

const legendClickHandler = (params) => {
  // 获取当前选中的图例
  selectedLegends.value = []
  const legendData = ['严重', '主要', '次要', '警告']
  legendData.forEach(name => {
    if (params.selected[name]) {
      selectedLegends.value.push(name)
    }
  })

  // 根据选中的图例重新计算总故障数
  updateFaultTotal()
}

const updateFaultChart = async () => {
  if (!faultChartInstance.value) return

  try {
    const range = faultTimeRange.value
    let url = `/api/dashboard/fault-trend?time_range=${range}`

    // 如果是自定义日期范围，传递开始和结束日期
    if (range === 'custom' && customDateRange.value) {
      const startDate = dayjs(customDateRange.value[0]).format('YYYY-MM-DD')
      const endDate = dayjs(customDateRange.value[1]).format('YYYY-MM-DD')
      url = `/api/dashboard/fault-trend?time_range=custom&start_date=${startDate}&end_date=${endDate}`
    }

    const response = await fetch(url)
    const data = await response.json()

    // 保存原始数据
    faultData.value = {
      labels: data.labels || [],
      by_severity: data.by_severity || {}
    }

    // 重置选中的图例为全部
    selectedLegends.value = ['严重', '主要', '次要', '警告']

    // 构建各级别数据数组
    const severityData = {
      critical: [],
      major: [],
      minor: [],
      warning: []
    }

    // 遍历每个时间标签，填充各级别的数据
    data.labels.forEach((label) => {
      const severityCounts = data.by_severity?.[label] || {}
      severityData.critical.push(severityCounts.critical || 0)
      severityData.major.push(severityCounts.major || 0)
      severityData.minor.push(severityCounts.minor || 0)
      severityData.warning.push(severityCounts.warning || 0)
    })

    const option = {
      xAxis: {
        data: data.labels || []
      },
      series: [
        { name: '严重', data: severityData.critical },
        { name: '主要', data: severityData.major },
        { name: '次要', data: severityData.minor },
        { name: '警告', data: severityData.warning }
      ]
    }

    faultChartInstance.value.setOption(option)

    // 更新总故障数
    updateFaultTotal()
  } catch (error) {
    ElMessage.error('加载故障趋势数据失败：' + (error.response?.data?.detail || error.message))
  }
}

const updateFaultTotal = () => {
  // 根据选中的图例重新计算总故障数
  const labels = faultData.value.labels
  const by_severity = faultData.value.by_severity

  let total = 0
  labels.forEach((label) => {
    const severityCounts = by_severity[label] || {}
    if (selectedLegends.value.includes('严重')) {
      total += severityCounts.critical || 0
    }
    if (selectedLegends.value.includes('主要')) {
      total += severityCounts.major || 0
    }
    if (selectedLegends.value.includes('次要')) {
      total += severityCounts.minor || 0
    }
    if (selectedLegends.value.includes('警告')) {
      total += severityCounts.warning || 0
    }
  })

  faultTotal.value = total
}

onMounted(() => {
  loadDashboardData()

  window.addEventListener('resize', () => {
    devicePieChart.value && echarts.getInstanceByDom(devicePieChart.value)?.resize()
    faultChartInstance.value && echarts.getInstanceByDom(faultChartInstance.value)?.resize()
  })
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-cards {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
}

.stat-icon .icon {
  font-size: 32px;
  color: #fff;
}

.stat-card.online .stat-icon {
  background: linear-gradient(135deg, #67c23a, #529b2e);
}

.stat-card.offline .stat-icon {
  background: linear-gradient(135deg, #f56c6c, #c45656);
}

.stat-card.maintenance .stat-icon {
  background: linear-gradient(135deg, #e6a23c, #b88230);
}

.stat-card.cost .stat-icon {
  background: linear-gradient(135deg, #409eff, #337ecc);
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.charts-row {
  margin-bottom: 20px;
}

.chart-card {
  height: 350px;
}

.chart {
  height: 280px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trend-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.fault-total {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: linear-gradient(135deg, #f5f7fa, #e9ecef);
  border-radius: 6px;
  margin-right: 8px;
  white-space: nowrap;
}

.fault-total .label {
  font-size: 11px;
  color: #606266;
  font-weight: 500;
  white-space: nowrap;
}

.fault-total .value {
  font-size: 16px;
  font-weight: bold;
  color: #F56C6C;
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  white-space: nowrap;
}

.fault-total .unit {
  font-size: 10px;
  color: #909399;
  font-weight: normal;
}
</style>
