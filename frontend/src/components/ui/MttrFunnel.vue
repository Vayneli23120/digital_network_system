<template>
  <div class="mttr-funnel">
    <div class="funnel-header">
      <span class="funnel-title">{{ title }}</span>
      <span class="funnel-total">端到端 {{ breakdown.total_h }}h</span>
    </div>
    <div class="funnel-body">
      <div class="funnel-stage" v-for="(stage, idx) in stages" :key="stage.key">
        <div class="stage-bar" :style="getStageStyle(stage, idx)">
          <span class="stage-value">{{ formatValue(stage) }}</span>
          <span class="stage-unit">{{ stage.unit }}</span>
          <!-- 验证段异常角标 -->
          <span v-if="stage.key === 'verify' && breakdown.verify_anomalies > 0" class="stage-anomaly">
            {{ breakdown.verify_anomalies }}
          </span>
        </div>
        <div class="stage-info">
          <span class="stage-name">
            {{ stage.name }}
            <!-- 验证段显示异常说明 -->
            <span v-if="stage.key === 'verify' && breakdown.verify_anomalies > 0" class="anomaly-text">
              ({{ breakdown.verify_anomalies }} {{ t('mttrUnclosedTimely') }})
            </span>
          </span>
          <span class="stage-target" :class="getStageStatus(stage)">
            目标 ≤{{ stage.target }}{{ stage.unit }}
          </span>
        </div>
        <div class="stage-arrow" v-if="idx < stages.length - 1">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" fill="currentColor"/>
          </svg>
        </div>
      </div>
    </div>
    <!-- 口径说明 -->
    <div class="funnel-note" v-if="breakdown.note">
      <span class="note-icon">ℹ️</span>
      <span class="note-text">{{ breakdown.note }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  breakdown: {
    type: Object,
    required: true
    // { mtta_min, diagnose_min, repair_h, verify_h, total_h, target_mtta, target_diagnose, target_repair, target_verify }
  },
  title: {
    type: String,
    default: '修复链路分析'
  }
})

const { t } = useI18n()

const stages = computed(() => [
  { key: 'mtta', name: t('mttrStageResponse'), value: props.breakdown.mtta_min, unit: 'min', target: props.breakdown.target_mtta },
  { key: 'diagnose', name: t('mttrStageDiagnose'), value: props.breakdown.diagnose_min, unit: 'min', target: props.breakdown.target_diagnose },
  { key: 'repair', name: t('mttrStageRepair'), value: props.breakdown.repair_h, unit: 'h', target: props.breakdown.target_repair },
  { key: 'verify', name: t('mttrStageVerify'), value: props.breakdown.verify_h, unit: 'h', target: props.breakdown.target_verify }
])

const maxValue = computed(() => {
  const values = stages.value.map(s => {
    if (s.unit === 'min') return s.value
    return s.value * 60  // Convert hours to minutes for comparison
  })
  return Math.max(...values, 1)
})

const getStageStyle = (stage, idx) => {
  const valueInMin = stage.unit === 'min' ? stage.value : stage.value * 60
  const pct = (valueInMin / maxValue.value) * 100
  const width = Math.max(pct, 20) // Minimum 20% width

  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444']
  const color = colors[idx] || '#6b7280'

  return {
    width: `${width}%`,
    background: `linear-gradient(90deg, ${color}, ${color}80)`,
    opacity: 1 - (idx * 0.1)
  }
}

const getStageStatus = (stage) => {
  if (stage.value <= stage.target) return 'good'
  if (stage.value <= stage.target * 2) return 'warn'
  return 'critical'
}

const formatValue = (stage) => {
  if (stage.value === 0) return '—'
  if (stage.unit === 'min') return Math.round(stage.value)
  return stage.value.toFixed(1)
}
</script>

<style scoped>
.mttr-funnel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-default);
}

.funnel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.funnel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.funnel-total {
  font-size: 12px;
  font-weight: 500;
  color: var(--accent-primary);
}

.funnel-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.funnel-stage {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stage-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 32px;
  border-radius: var(--radius-sm);
  color: #fff;
  font-weight: 600;
  transition: width 0.3s ease;
}

.stage-value {
  font-size: 14px;
}

.stage-unit {
  font-size: 11px;
  opacity: 0.8;
}

.stage-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 100px;
}

.stage-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.stage-target {
  font-size: 11px;
  font-weight: 500;
}

.stage-target.good {
  color: var(--success-color);
}

.stage-target.warn {
  color: var(--warning-color);
}

.stage-target.critical {
  color: var(--danger-color);
}

.stage-arrow {
  color: var(--text-muted);
  opacity: 0.5;
}

/* Dark mode */
.dark .mttr-funnel {
  background: var(--bg-tertiary);
}

/* 验证段异常角标 */
.stage-anomaly {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 600;
  background: rgba(239, 68, 68, 0.9);
  border-radius: 8px;
  margin-left: 6px;
}

.anomaly-text {
  font-size: 11px;
  color: #ef4444;
  font-weight: 500;
  margin-left: 4px;
}

/* 口径说明 */
.funnel-note {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-default);
  margin-top: 4px;
}

.note-icon {
  font-size: 12px;
}

.note-text {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.4;
}
</style>