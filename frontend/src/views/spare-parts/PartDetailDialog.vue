<template>
  <el-dialog :model-value="modelValue" title="库存清单" width="750px" @update:model-value="$emit('update:modelValue', $event)">
    <!-- 库存概览（紧凑） -->
    <div v-if="part" class="compact-header">
      <span>在库: <strong>{{ part.in_stock_count || 0 }}</strong> 件</span>
      <span>总价: <strong class="text-success">¥{{ totalStockValue.toFixed(2) }}</strong></span>
      <span>型号: {{ part.part_number || '-' }}</span>
    </div>

    <!-- 库存清单表格 -->
    <el-table :data="inStockInstances" v-loading="loading" stripe border size="small" style="margin-top: 8px">
      <el-table-column prop="serial_number" label="序列号" width="150">
        <template #default="{ row }">
          <span class="text-primary">{{ row.serial_number || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="po_number" label="PO号" width="100">
        <template #default="{ row }">{{ row.po_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="unit_price" label="单价" width="80">
        <template #default="{ row }">
          <span class="text-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="location" label="位置" width="80">
        <template #default="{ row }">{{ row.location || '-' }}</template>
      </el-table-column>
      <el-table-column prop="in_stock_at" label="入库时间" width="140">
        <template #default="{ row }">{{ row.in_stock_at ? formatDateTime(row.in_stock_at) : '-' }}</template>
      </el-table-column>
      <el-table-column prop="notes" label="备注" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ row.notes || '-' }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && inStockInstances.length === 0" description="该备件暂无在库实例" />
  </el-dialog>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getPartInstances } from '@/api'
import { formatDateTime } from '@/utils/time'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  part: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const instances = ref([])
const loading = ref(false)

// 计算库存总价（在库实例的单价之和）
const totalStockValue = computed(() => {
  return instances.value
    .filter(item => item.status === 'in_stock')
    .reduce((sum, item) => sum + (item.unit_price || props.part?.unit_price || 0), 0)
})

// 只显示在库的实例
const inStockInstances = computed(() => {
  return instances.value.filter(item => item.status === 'in_stock')
})

// 监听对话框打开，加载数据
watch(() => props.modelValue, async (val) => {
  if (val && props.part) {
    loading.value = true
    try {
      const result = await getPartInstances(props.part.id)
      instances.value = result.instances || []
    } catch (e) {
      ElMessage.error('加载备件实例失败：' + (e.response?.data?.detail || e.message))
    } finally {
      loading.value = false
    }
  }
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