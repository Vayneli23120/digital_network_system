<template>
  <div class="kpi-stat" :class="statusClass" @click="handleClick">
    <div class="kpi-status-indicator">
      <span class="kpi-status-dot" :class="statusClass"></span>
      <span class="kpi-status-label" v-if="showStatusLabel">{{ statusLabel }}</span>
    </div>
    <div class="kpi-value-section">
      <span class="kpi-value">{{ formattedValue }}</span>
      <span class="kpi-unit" v-if="kpi.unit">{{ kpi.unit }}</span>
      <span class="kpi-trend" :class="trendClass" v-if="kpi.trend !== 0 && kpi.trend !== null">
        {{ trendArrow }}
        <span class="kpi-trend-value" v-if="showTrendValue">{{ formatTrend }}</span>
      </span>
    </div>
    <div class="kpi-target-section" v-if="kpi.target || estimated">
      <span class="kpi-target" v-if="kpi.target">
        {{ t('kpiTarget') }}: {{ kpi.target }}{{ kpi.unit }}
      </span>
      <span class="kpi-estimated-badge" v-if="estimated">
        <el-icon><WarningFilled /></el-icon>
        {{ t('kpiEstimated') }}
      </span>
    </div>
    <div class="kpi-title-section">
      <span class="kpi-title">{{ title }}</span>
      <span class="kpi-link" v-if="link">
        <el-icon><ArrowRight /></el-icon>
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { WarningFilled, ArrowRight, ArrowUp, ArrowDown } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  kpi: {
    type: Object,
    required: true,
    // { value, unit, target, threshold, trend, status, is_estimated }
  },
  title: {
    type: String,
    required: true
  },
  link: {
    type: String,
    default: null
  },
  showStatusLabel: {
    type: Boolean,
    default: false
  },
  showTrendValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['click'])

const { t } = useI18n()
const router = useRouter()

const statusClass = computed(() => {
  const status = props.kpi.status || 'gray'
  return `status-${status}`
})

const estimated = computed(() => props.kpi.is_estimated === true)

const statusLabel = computed(() => {
  const labels = {
    'green': t('statusGood'),
    'yellow': t('statusWarning'),
    'red': t('statusCritical'),
    'gray': t('statusNoData')
  }
  return labels[props.kpi.status] || ''
})

const formattedValue = computed(() => {
  const value = props.kpi.value
  if (value === null || value === undefined) return '--'
  if (props.kpi.unit === '¥') {
    return `¥${formatNumber(value)}`
  }
  if (typeof value === 'number') {
    return value % 1 === 0 ? value : value.toFixed(1)
  }
  return value
})

const formatNumber = (num) => {
  if (num >= 10000) {
    return (num / 1000).toFixed(1) + 'k'
  }
  return num.toLocaleString()
}

const formatTrend = computed(() => {
  const trend = props.kpi.trend
  if (trend === null || trend === undefined) return ''
  const prefix = trend > 0 ? '+' : ''
  return `${prefix}${trend.toFixed(1)}`
})

const trendClass = computed(() => {
  const trend = props.kpi.trend
  if (trend === null || trend === 0) return ''
  // 趋势方向：正数可能好也可能坏，取决于指标类型
  // 这里简化处理：正数=上升(可能预警)，负数=下降(可能改善)
  return trend > 0 ? 'trend-up' : 'trend-down'
})

const trendArrow = computed(() => {
  const trend = props.kpi.trend
  if (trend === null || trend === 0) return ''
  return trend > 0 ? '↑' : '↓'
})

const handleClick = () => {
  if (props.link) {
    router.push(props.link)
  }
  emit('click')
}
</script>

<style scoped>
.kpi-stat {
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.kpi-stat:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transform: translateY(-1px);
}

/* Status-based styling */
.status-green {
  border-left: 3px solid var(--success-color);
}

.status-yellow {
  border-left: 3px solid var(--warning-color);
}

.status-red {
  border-left: 3px solid var(--danger-color);
  background: linear-gradient(135deg, rgba(239, 83, 80, 0.05), var(--bg-secondary));
}

.status-gray {
  border-left: 3px solid var(--text-muted);
}

/* Status indicator */
.kpi-status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.kpi-status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-green .kpi-status-dot {
  background: var(--success-color);
  box-shadow: 0 0 6px var(--success-color);
}

.status-yellow .kpi-status-dot {
  background: var(--warning-color);
}

.status-red .kpi-status-dot {
  background: var(--danger-color);
  box-shadow: 0 0 6px var(--danger-color);
}

.status-gray .kpi-status-dot {
  background: var(--text-muted);
}

.kpi-status-label {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
}

/* Value section */
.kpi-value-section {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 8px;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  font-family: var(--font-display);
  color: var(--text-primary);
  line-height: 1;
}

.kpi-unit {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.kpi-trend {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  font-weight: 600;
  margin-left: auto;
}

.trend-up {
  color: var(--warning-color);
}

.trend-down {
  color: var(--success-color);
}

.kpi-trend-value {
  font-size: 11px;
}

/* Target section */
.kpi-target-section {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
}

.kpi-target {
  color: var(--text-muted);
}

.kpi-estimated-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: rgba(251, 191, 36, 0.1);
  border: 1px solid rgba(251, 191, 36, 0.3);
  border-radius: var(--radius-sm);
  color: #b45309;
  font-size: 11px;
  font-weight: 500;
}

.kpi-estimated-badge .el-icon {
  font-size: 12px;
}

/* Title section */
.kpi-title-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kpi-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.kpi-link {
  color: var(--accent-primary);
  opacity: 0;
  transition: opacity 0.2s;
}

.kpi-stat:hover .kpi-link {
  opacity: 1;
}

.kpi-link .el-icon {
  font-size: 14px;
}

/* Dark mode */
.dark .kpi-stat {
  background: var(--bg-tertiary);
}

.dark .status-red {
  background: linear-gradient(135deg, rgba(239, 83, 80, 0.1), var(--bg-tertiary));
}

.dark .kpi-estimated-badge {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}
</style>