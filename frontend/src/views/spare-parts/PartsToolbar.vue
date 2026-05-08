<template>
  <div class="parts-toolbar">
    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_parts }}</div>
        <div class="stat-label">{{ t('spareStatsTotal') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_quantity }}</div>
        <div class="stat-label">{{ t('spareStatsQuantity') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" style="color: var(--accent-warning)">{{ stats.low_stock_count }}</div>
        <div class="stat-label">{{ t('spareStatsLowStock') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">¥{{ formatValue(stats.total_value) }}</div>
        <div class="stat-label">{{ t('spareStatsValue') }}</div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-buttons">
      <el-button type="success" @click="$emit('scan-in')">{{ t('spareScanIn') }}</el-button>
      <el-button type="warning" @click="$emit('scan-out')">{{ t('spareScanOut') }}</el-button>
      <el-button type="primary" @click="$emit('add')">{{ t('spareNew') }}</el-button>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

defineProps({
  stats: {
    type: Object,
    required: true
  }
})

defineEmits(['scan-in', 'scan-out', 'add'])

const formatValue = (val) => {
  if (!val) return '0'
  return val.toLocaleString()
}
</script>

<style scoped>
.parts-toolbar {
  margin-bottom: 16px;
}
.action-buttons {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: nowrap;
}
.action-buttons .el-button {
  flex-shrink: 0;
  white-space: nowrap;
}
</style>