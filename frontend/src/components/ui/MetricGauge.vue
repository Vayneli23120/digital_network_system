<template>
  <div class="metric-gauge" :class="sizeClass">
    <svg viewBox="0 0 100 100" class="gauge-svg">
      <!-- 背景环 -->
      <circle
        cx="50"
        cy="50"
        :r="radius"
        fill="none"
        stroke="#e8e8e8"
        :stroke-width="strokeWidth"
      />
      <!-- 进度环 -->
      <circle
        cx="50"
        cy="50"
        :r="radius"
        fill="none"
        :stroke="computedColor"
        :stroke-width="strokeWidth"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        stroke-linecap="round"
        class="progress-ring"
        :style="{ transition: 'stroke-dashoffset 0.5s ease, stroke 0.5s ease' }"
      />
      <!-- 起点装饰 -->
      <circle cx="50" cy="10" r="2" fill="#e8e8e8" />
    </svg>
    <div class="gauge-center">
      <span class="gauge-value" :style="{ color: computedColor }">
        {{ displayValue }}
      </span>
      <span class="gauge-unit" v-if="unit">{{ unit }}</span>
      <span class="gauge-label">{{ label }}</span>
    </div>
    <!-- 状态指示器 -->
    <div class="status-indicator" :class="statusClass" v-if="showStatus">
      <span class="status-dot"></span>
      <span class="status-text">{{ statusText }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },          // 数值 (0-100 或温度值)
  label: { type: String, default: '' },         // 标签文字
  unit: { type: String, default: '' },          // 单位 (%, °C, MB 等)
  thresholds: {                                 // 阈值配置
    type: Array,
    default: () => [50, 75, 90]                 // [warning, danger, critical]
  },
  colors: {                                     // 阶段颜色
    type: Array,
    default: () => ['#00b894', '#fdcb6e', '#e17055', '#d63031']
  },
  status: { type: String, default: 'normal' },  // 状态 (normal/warning/danger/critical/unknown)
  showStatus: { type: Boolean, default: false }, // 是否显示状态文字
  size: { type: String, default: 'medium' },    // 大小 (small/medium/large)
  maxValue: { type: Number, default: 100 },     // 最大值（用于温度等非百分比指标）
})

// 尺寸配置
const sizeConfig = {
  small: { radius: 35, strokeWidth: 6 },
  medium: { radius: 40, strokeWidth: 8 },
  large: { radius: 42, strokeWidth: 10 }
}

const radius = computed(() => sizeConfig[props.size]?.radius || 40)
const strokeWidth = computed(() => sizeConfig[props.size]?.strokeWidth || 8)

// 圆周长
const circumference = computed(() => 2 * Math.PI * radius.value)

// 计算偏移量（从顶部开始，顺时针）
const offset = computed(() => {
  const percent = Math.min(Math.max(props.value / props.maxValue, 0), 1)
  return circumference.value * (1 - percent)
})

// 根据值计算颜色
const computedColor = computed(() => {
  if (props.value === null || props.value === undefined) {
    return '#b0b0b0'  // 无数据时灰色
  }

  const val = props.value / props.maxValue * 100
  const thresholds = props.thresholds

  if (val < thresholds[0]) return props.colors[0]      // 正常 (绿色)
  if (val < thresholds[1]) return props.colors[1]      // 警告 (黄色)
  if (val < thresholds[2]) return props.colors[2]      // 危险 (橙色)
  return props.colors[3]                                // 严重 (红色)
})

// 显示值
const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) {
    return '--'
  }
  return typeof props.value === 'number' ? Math.round(props.value) : props.value
})

// 状态样式类
const statusClass = computed(() => {
  return `status-${props.status}`
})

// 状态文字
const statusText = computed(() => {
  const statusMap = {
    'normal': '正常',
    'warning': '警告',
    'danger': '危险',
    'critical': '严重',
    'unknown': '未知'
  }
  return statusMap[props.status] || props.status
})

// 尺寸类
const sizeClass = computed(() => `gauge-${props.size}`)
</script>

<style scoped>
.metric-gauge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}

.gauge-small {
  width: 80px;
  height: 80px;
}

.gauge-medium {
  width: 100px;
  height: 100px;
}

.gauge-large {
  width: 120px;
  height: 120px;
}

.gauge-svg {
  transform: rotate(-90deg);  /* 从顶部开始 */
  width: 100%;
  height: 100%;
}

.progress-ring {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.gauge-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.gauge-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.2;
}

.gauge-small .gauge-value {
  font-size: 14px;
}

.gauge-large .gauge-value {
  font-size: 22px;
}

.gauge-unit {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: -2px;
}

.gauge-label {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.gauge-small .gauge-label {
  font-size: 9px;
}

.gauge-large .gauge-label {
  font-size: 13px;
}

.status-indicator {
  position: absolute;
  bottom: -20px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-normal {
  color: #00b894;
}

.status-warning {
  color: #fdcb6e;
}

.status-danger {
  color: #e17055;
}

.status-critical {
  color: #d63031;
}

.status-unknown {
  color: #b0b0b0;
}
</style>