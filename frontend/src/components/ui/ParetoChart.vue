<template>
  <div class="pareto-chart">
    <div class="pareto-header">
      <span class="pareto-title">{{ title }}</span>
      <span class="pareto-subtitle">80/20 分析</span>
    </div>
    <div class="pareto-body" ref="chartRef"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  data: {
    type: Array,
    required: true
    // [{ type, count, pct, cumulative_pct }]
  },
  title: {
    type: String,
    default: '根因分布'
  }
})

const { t, currentLang } = useI18n()
const chartRef = ref(null)
let chartInstance = null

const typeLabels = {
  hardware: '硬件故障',
  software: '软件故障',
  config: '配置问题',
  network: '网络问题',
  power: '电源问题',
  other: '其他'
}

const typeColors = {
  hardware: '#ef4444',
  software: '#f59e0b',
  config: '#3b82f6',
  network: '#10b981',
  power: '#8b5cf6',
  other: '#6b7280'
}

const initChart = () => {
  if (!chartRef.value) return
  if (chartInstance) chartInstance.dispose()

  chartInstance = echarts.init(chartRef.value)

  const isDark = document.documentElement.classList.contains('dark')
  const textColor = isDark ? '#f8fafc' : '#1e293b'
  const gridColor = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'

  const types = props.data.map(d => typeLabels[d.type] || d.type)
  const counts = props.data.map(d => d.count)
  const cumulative = props.data.map(d => d.cumulative_pct)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const bar = params[0]
        const line = params[1]
        return `${bar.name}<br/>故障数: ${bar.value}<br/>累计占比: ${line.value}%`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: types,
      axisLabel: { color: textColor, fontSize: 11 },
      axisLine: { lineStyle: { color: gridColor } }
    },
    yAxis: [
      {
        type: 'value',
        name: '故障数',
        axisLabel: { color: textColor },
        axisLine: { lineStyle: { color: gridColor } },
        splitLine: { lineStyle: { color: gridColor } }
      },
      {
        type: 'value',
        name: '累计%',
        max: 100,
        axisLabel: { color: textColor, formatter: '{value}%' },
        axisLine: { lineStyle: { color: gridColor } },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '故障数',
        type: 'bar',
        data: props.data.map(d => ({
          value: d.count,
          itemStyle: { color: typeColors[d.type] || '#6b7280' }
        })),
        barWidth: '50%'
      },
      {
        name: '累计占比',
        type: 'line',
        yAxisIndex: 1,
        data: cumulative,
        smooth: false,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { color: '#f59e0b', width: 2 },
        itemStyle: { color: '#f59e0b' },
        markLine: {
          silent: true,
          data: [
            { yAxis: 80, lineStyle: { color: '#ef4444', type: 'dashed' }, label: { formatter: '80%阈值' } }
          ]
        }
      }
    ]
  }

  chartInstance.setOption(option)
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chartInstance?.resize())
  window.addEventListener('theme-change', initChart)
})

watch(() => props.data, initChart, { deep: true })
watch(currentLang, initChart)

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', () => chartInstance?.resize())
  window.removeEventListener('theme-change', initChart)
})
</script>

<style scoped>
.pareto-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.pareto-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pareto-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.pareto-subtitle {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.pareto-body {
  height: 200px;
}

/* Dark mode */
.dark .pareto-chart {
  background: var(--bg-tertiary);
}
</style>