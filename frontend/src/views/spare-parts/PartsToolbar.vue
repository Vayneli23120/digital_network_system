<template>
  <div class="parts-toolbar">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :title="t('spareStatsTotal')" :value="stats.total_parts" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :title="t('spareStatsQuantity')" :value="stats.total_quantity" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :title="t('spareStatsLowStock')" :value="stats.low_stock_count" value-style="color: #F56C6C" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :title="t('spareStatsValue')" :value="stats.total_value" :precision="2" />
        </el-card>
      </el-col>
    </el-row>

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
</script>

<style scoped>
.parts-toolbar {
  margin-bottom: 16px;
}
.stats-row {
  margin-bottom: 16px;
}
.stat-card {
  text-align: center;
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