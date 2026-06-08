<template>
  <div class="change-correlation-panel">
    <div class="panel-header">
      <span class="panel-title">{{ displayTitle }}</span>
      <span class="panel-subtitle">{{ t('changeCorrelationSubtitle') }}</span>
    </div>
    <div class="panel-content">
      <!-- 变更成功率指标 -->
      <div class="correlation-metrics">
        <div class="metric-item">
          <span class="metric-label">{{ t('changeTotalChanges') }}</span>
          <span class="metric-value">{{ correlationData.total_changes || 0 }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">{{ t('changeFaultCorrelation') }}</span>
          <span class="metric-value warning">{{ correlationData.changes_with_faults || 0 }}</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">{{ t('changeSuccessRate') }}</span>
          <span class="metric-value" :class="successRateClass">{{ correlationData.success_rate || 100 }}%</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">{{ t('changeCorrelationWindow') }}</span>
          <span class="metric-value">{{ correlationData.correlation_window_hours || 72 }}h</span>
        </div>
      </div>

      <!-- 成功率进度条 -->
      <div class="success-rate-bar">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :class="successRateClass"
            :style="{ width: (correlationData.success_rate || 100) + '%' }"
          ></div>
        </div>
        <div class="rate-label">
          <span class="rate-text">{{ t('changeSuccessRateDesc') }}</span>
        </div>
      </div>

      <!-- 风险设备列表 -->
      <div class="risky-devices-section" v-if="correlationData.risky_devices?.length">
        <div class="section-header">
          <span class="section-title">{{ t('changeRiskyDevices') }}</span>
          <span class="section-badge">{{ correlationData.risky_devices.length }}</span>
        </div>
        <div class="risky-devices-list">
          <div
            v-for="device in correlationData.risky_devices"
            :key="device.device"
            class="risky-device-item"
          >
            <div class="device-info">
              <span class="device-name">{{ device.device }}</span>
              <span class="device-stats">
                {{ t('changeDeviceStats', { changes: device.changes, faults: device.faults_after }) }}
              </span>
            </div>
            <div class="fault-rate-bar">
              <div class="rate-fill" :style="{ width: Math.min(100, device.fault_rate * 50) + '%' }"></div>
              <span class="rate-value">{{ device.fault_rate.toFixed(1) }}x</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 无风险时显示 -->
      <div v-else class="no-risk-section">
        <span class="no-risk-icon">✓</span>
        <span class="no-risk-text">{{ t('changeNoRiskDetected') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  data: {
    type: Object,
    required: true
    // { total_changes, changes_with_faults, success_rate, correlation_window_hours, risky_devices }
  },
  title: {
    type: String,
    default: ''  // 空串，由 computed 兜底 i18n
  }
})

const { t } = useI18n()

// title 兜底：未传入时使用 i18n 默认值
const displayTitle = computed(() => props.title || t('changeCorrelationTitle'))

const correlationData = computed(() => props.data || {})

const successRateClass = computed(() => {
  const rate = correlationData.value.success_rate || 100
  if (rate >= 95) return 'green'
  if (rate >= 85) return 'yellow'
  return 'red'
})
</script>

<style scoped>
.change-correlation-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-subtitle {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.correlation-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.metric-label {
  font-size: 11px;
  color: var(--text-muted);
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary);
}

.metric-value.green {
  color: #10b981;
}

.metric-value.yellow {
  color: #f59e0b;
}

.metric-value.red {
  color: #ef4444;
}

.metric-value.warning {
  color: #f59e0b;
}

.success-rate-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-bar {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-fill.green {
  background: #10b981;
}

.progress-fill.yellow {
  background: #f59e0b;
}

.progress-fill.red {
  background: #ef4444;
}

.rate-label {
  font-size: 11px;
  color: var(--text-muted);
}

.risky-devices-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-default);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.section-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-radius: var(--radius-sm);
}

.risky-devices-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.risky-device-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.device-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.device-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.device-stats {
  font-size: 11px;
  color: var(--text-muted);
}

.fault-rate-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rate-fill {
  height: 4px;
  width: 40px;
  background: #f59e0b;
  border-radius: 2px;
}

.rate-value {
  font-size: 12px;
  font-weight: 500;
  color: #f59e0b;
}

.no-risk-section {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: var(--radius-sm);
}

.no-risk-icon {
  font-size: 14px;
  color: #10b981;
}

.no-risk-text {
  font-size: 12px;
  color: #10b981;
}

/* Dark mode */
.dark .change-correlation-panel {
  background: var(--bg-tertiary);
}

.dark .metric-item,
.dark .risky-device-item {
  background: var(--bg-secondary);
}

@media (max-width: 600px) {
  .correlation-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>