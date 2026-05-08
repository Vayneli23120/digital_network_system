<template>
  <el-dialog :model-value="modelValue" title="出入库详情" width="750px" @update:model-value="$emit('update:modelValue', $event)">
    <!-- 批次概览（紧凑） -->
    <div v-if="movement" class="compact-header">
      <span>时间: {{ formatDateTime(movement.created_at) }}</span>
      <span>
        <el-tag :type="getMovementTypeTag(movement.movement_type)" size="small">
          {{ getMovementTypeText(movement.movement_type) }}
        </el-tag>
      </span>
      <span>批次: <strong>{{ movement.batch_total || 1 }}</strong> 件</span>
      <span v-if="movement.session_code">批次码: {{ movement.session_code }}</span>
      <span v-if="movement.target_device_name">目标设备: {{ movement.target_device_name }}</span>
      <span v-if="movement.source_device_name">来源设备: {{ movement.source_device_name }}</span>
      <span v-if="movement.reason">原因: {{ movement.reason }}</span>
    </div>

    <!-- 本批次备件清单表格 -->
    <el-table :data="batchAllItems" stripe border size="small" style="margin-top: 8px">
      <el-table-column label="" width="60">
        <template #default="{ row }">
          <el-tag v-if="row.isCurrent" type="primary" size="small">当前</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="serial_number" label="序列号" width="150">
        <template #default="{ row }">
          <span class="text-primary">{{ row.serial_number || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="po_number" label="PO号" width="100">
        <template #default="{ row }">{{ row.po_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="part_number" label="型号" width="120">
        <template #default="{ row }">{{ row.part_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="120">
        <template #default="{ row }">{{ row.name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="unit_price" label="单价" width="80">
        <template #default="{ row }">
          <span class="text-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'
import { formatDateTime } from '@/utils/time'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  movement: {
    type: Object,
    default: null
  }
})

defineEmits(['update:modelValue'])

// 出入库类型显示
const getMovementTypeTag = (type) => {
  const tags = { in: 'success', out: 'warning', scrap_in: 'info', scrap_out: 'danger' }
  return tags[type] || ''
}

const getMovementTypeText = (type) => {
  const texts = { in: '入库', out: '出库', scrap_in: '报废入库', scrap_out: '已报废' }
  return texts[type] || type
}

// 合并当前记录和batch_items用于表格显示
const batchAllItems = computed(() => {
  if (!props.movement) return []
  const current = {
    serial_number: props.movement.serial_number,
    po_number: props.movement.po_number,
    part_number: props.movement.part_number,
    name: props.movement.name,
    unit_price: props.movement.unit_price,
    isCurrent: true
  }
  const others = (props.movement.batch_items || []).map(item => ({ ...item, isCurrent: false }))
  return [current, ...others]
})
</script>

<style scoped>
.compact-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 13px;
}
.compact-header strong {
  font-weight: 600;
}
.text-primary {
  color: var(--el-color-primary);
  font-weight: 500;
}
.text-success {
  color: var(--el-color-success);
  font-weight: 600;
}
</style>