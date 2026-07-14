<template>
  <div class="pareto-chart">
    <div class="pareto-header">
      <span class="pareto-title">{{ displayTitle }}</span>
      <span class="pareto-subtitle">{{ t('pareto80Analysis') }}</span>
    </div>
    <div class="pareto-body" ref="chartRef"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted, computed } from 'vue'
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
    default: ''  // 空串，由 computed 兜底 i18n
  }
})

const { t, currentLang } = useI18n()
const chartRef = ref(null)
let chartInstance = null
let resizeHandler = null
let themeHandler = null

// title 兜底：未传入时使用 i18n 默认值
const displayTitle = computed(() => props.title || t('paretoChartTitle'))

// 使用 i18n 映射根因类型标签
const getTypeLabel = (type) => {
  const labelMap = {
    hardware: t('rootCauseHardware'),
    software: t('rootCauseSoftware'),
    config: t('rootCauseConfig'),
    network: t('rootCauseNetwork'),
    power: t('rootCausePower'),
    other: t('rootCauseOther')
  }
  return labelMap[type] || type
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

  const types = props.data.map(d => getTypeLabel(d.type))
  const counts = props.data.map(d => d.count)
  const cumulative = props.data.map(d => d.cumulative_pct)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const bar = params[0]
        const line = params[1]
        return `${bar.name}<br/>${t('paretoFaultCount')}: ${bar.value}<br/>${t('paretoCumulativePct')}: ${line.value}%`
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
        name: t('paretoFaultCount'),
        axisLabel: { color: textColor },
        axisLine: { lineStyle: { color: gridColor } },
        splitLine: { lineStyle: { color: gridColor } }
      },
      {
        type: 'value',
        name: t('paretoCumulativePct'),
        max: 100,
        axisLabel: { color: textColor, formatter: '{value}%' },
        axisLine: { lineStyle: { color: gridColor } },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: t('paretoFaultCount'),
        type: 'bar',
        data: props.data.map(d => ({
          value: d.count,
          itemStyle: { color: typeColors[d.type] || '#6b7280' }
        })),
        barWidth: '50%'
      },
      {
        name: t('paretoCumulativePct'),
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
            { yAxis: 80, lineStyle: { color: '#ef4444', type: 'dashed' }, label: { formatter: t('paretoThreshold80') } }
          ]
        }
      }
    ]
  }

  chartInstance.setOption(option)
}

onMounted(() => {
  initChart()
  resizeHandler = () => { if (chartInstance && !chartInstance.isDisposed()) chartInstance.resize() }
  themeHandler = initChart
  window.addEventListener('resize', resizeHandler)
  window.addEventListener('theme-change', themeHandler)
})

watch(() => props.data, initChart, { deep: true })
watch(currentLang, initChart)

onUnmounted(() => {
  chartInstance?.dispose()
  chartInstance = null
  if (resizeHandler) window.removeEventListener('resize', resizeHandler)
  if (themeHandler) window.removeEventListener('theme-change', themeHandler)
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