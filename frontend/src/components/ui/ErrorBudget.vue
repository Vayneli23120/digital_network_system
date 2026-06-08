<template>
  <div class="error-budget-panel">
    <div class="budget-header">
      <span class="budget-title">{{ title }}</span>
      <span class="budget-subtitle">错误预算</span>
    </div>
    <div class="budget-content">
      <!-- SLO 服务列表 -->
      <div v-for="slo in sloData" :key="slo.service" class="slo-item" :class="slo.status">
        <!-- 服务名称 -->
        <div class="slo-service-name">
          <span class="slo-status-dot" :class="slo.status"></span>
          <span>{{ slo.service }}</span>
          <span class="slo-target">SLO {{ slo.target }}%</span>
        </div>

        <!-- 预算进度条 -->
        <div class="budget-progress">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :class="slo.status"
              :style="{ width: Math.max(0, Math.min(100, slo.remaining_pct)) + '%' }"
            ></div>
          </div>
          <div class="progress-labels">
            <span class="remaining-label">
              剩余 {{ slo.remaining_pct >= 0 ? slo.remaining_pct.toFixed(1) : 0 }}%
            </span>
            <span class="consumed-label">
              已消耗 {{ slo.consumed_min.toFixed(0) }} / {{ slo.error_budget_min.toFixed(0) }} 分钟
            </span>
          </div>
        </div>

        <!-- 燃尽率指标 -->
        <div class="burn-rate-section">
          <div class="burn-rate-value">
            <span class="burn-label">燃尽率</span>
            <span class="burn-number" :class="{ warning: slo.burn_rate >= 2 }">
              {{ slo.burn_rate.toFixed(2) }}x
            </span>
          </div>
          <div class="burn-rate-desc">
            <span v-if="slo.burn_rate < 1">正常消耗（低于平均速率）</span>
            <span v-else-if="slo.burn_rate >= 2" class="warning-text">
              警告：消耗过快，建议冻结变更
            </span>
            <span v-else>高于平均消耗速率</span>
          </div>
        </div>

        <!-- 警报标识 -->
        <div v-if="slo.alert" class="slo-alert">
          <span class="alert-icon">⚠️</span>
          <span class="alert-text">建议冻结变更</span>
        </div>
      </div>

      <!-- 无 SLO 配置时的默认提示 -->
      <div v-if="sloData.length === 1 && sloData[0].service === 'default'" class="no-slo-config">
        <span class="no-config-icon">📊</span>
        <span class="no-config-text">未配置 SLO 目标，请在系统设置中添加服务 SLO</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  data: {
    type: Array,
    required: true
    // [{ service, target, window_days, error_budget_min, consumed_min, remaining_pct, burn_rate, status, alert }]
  },
  title: {
    type: String,
    default: 'SLO 错误预算'
  }
})

const { t } = useI18n()

const sloData = computed(() => props.data || [])
</script>

<style scoped>
.error-budget-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.budget-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.budget-subtitle {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  padding: 2px 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.budget-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.slo-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--border-default);
}

.slo-item.green {
  border-left-color: #10b981;
}

.slo-item.yellow {
  border-left-color: #f59e0b;
}

.slo-item.red {
  border-left-color: #ef4444;
}

.slo-item.gray {
  border-left-color: #6b7280;
}

.slo-service-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.slo-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.slo-status-dot.green {
  background: #10b981;
}

.slo-status-dot.yellow {
  background: #f59e0b;
}

.slo-status-dot.red {
  background: #ef4444;
}

.slo-status-dot.gray {
  background: #6b7280;
}

.slo-target {
  font-size: 11px;
  color: var(--text-muted);
  padding: 2px 6px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.budget-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-bar {
  height: 8px;
  background: var(--bg-secondary);
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

.progress-fill.gray {
  background: #6b7280;
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
}

.remaining-label {
  color: var(--text-secondary);
  font-weight: 500;
}

.consumed-label {
  color: var(--text-muted);
}

.burn-rate-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 4px;
}

.burn-rate-value {
  display: flex;
  align-items: center;
  gap: 6px;
}

.burn-label {
  font-size: 11px;
  color: var(--text-muted);
}

.burn-number {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.burn-number.warning {
  color: #f59e0b;
}

.burn-rate-desc {
  font-size: 11px;
  color: var(--text-muted);
}

.warning-text {
  color: #f59e0b;
  font-weight: 500;
}

.slo-alert {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: rgba(245, 158, 11, 0.1);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.alert-icon {
  font-size: 12px;
}

.alert-text {
  font-size: 11px;
  color: #f59e0b;
  font-weight: 500;
}

.no-slo-config {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.no-config-icon {
  font-size: 16px;
}

.no-config-text {
  font-size: 12px;
  color: var(--text-muted);
}

/* Dark mode */
.dark .error-budget-panel {
  background: var(--bg-tertiary);
}

.dark .slo-item {
  background: var(--bg-secondary);
}

.dark .progress-bar {
  background: var(--bg-primary);
}
</style>