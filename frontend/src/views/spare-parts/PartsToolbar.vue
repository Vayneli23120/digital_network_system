<template>
  <div class="parts-toolbar">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="备件种类" :value="stats.total_parts" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="总库存" :value="stats.total_quantity" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="库存不足" :value="stats.low_stock_count" value-style="color: #F56C6C" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic title="总价值（元）" :value="stats.total_value" :precision="2" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作按钮 -->
    <div class="action-buttons">
      <el-button type="success" @click="$emit('scan-in')">扫码入库</el-button>
      <el-button type="warning" @click="$emit('scan-out')">扫码出库</el-button>
      <el-button type="primary" @click="$emit('add')">新增备件</el-button>
    </div>
  </div>
</template>

<script setup>
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
}
</style>