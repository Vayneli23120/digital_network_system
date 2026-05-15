<template>
  <el-dialog :model-value="modelValue" :title="t('sparePartsList')" width="750px" @update:model-value="$emit('update:modelValue', $event)">
    <!-- 库存概览（紧凑） -->
    <div v-if="part" class="compact-header">
      <span>{{ t('statusInStock') }}: <strong>{{ part.in_stock_count || 0 }}</strong></span>
      <span>{{ t('spareTotalPrice') }}: <strong class="text-success">¥{{ totalStockValue.toFixed(2) }}</strong></span>
      <span>{{ t('sparePartNumber') }}: {{ part.part_number || '-' }}</span>
    </div>

    <!-- 库存清单表格 -->
    <el-table :data="inStockInstances" v-loading="loading" stripe border size="small" style="margin-top: 8px">
      <el-table-column prop="serial_number" :label="t('spareSerialNumber')" width="150">
        <template #default="{ row }">
          <span class="text-primary">{{ row.serial_number || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="po_number" :label="t('sparePoNumber')" width="100">
        <template #default="{ row }">{{ row.po_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="unit_price" :label="t('spareUnitPrice')" width="80">
        <template #default="{ row }">
          <span class="text-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="location" :label="t('spareLocation')" width="80">
        <template #default="{ row }">{{ row.location || '-' }}</template>
      </el-table-column>
      <el-table-column prop="in_stock_at" :label="t('movementIn')" width="140">
        <template #default="{ row }">{{ row.in_stock_at ? formatDateTime(row.in_stock_at) : '-' }}</template>
      </el-table-column>
      <el-table-column prop="notes" :label="t('spareNotes')" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ row.notes || '-' }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="!loading && inStockInstances.length === 0" :description="t('dashNoRecords')" />
  </el-dialog>
</template>

<script setup>
import { computed, watch, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getPartInstances } from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'

const { t } = useI18n()

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

// 计算库存总价
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
      const result = await cachedRequest(
        () => getPartInstances(props.part.id),
        `part_instances_${props.part.id}`,
        { part_id: props.part.id }
      )
      instances.value = result.instances || []
    } catch (e) {
      if (e.name !== 'CanceledError') {
        ElMessage.error(t('msgLoadFailed') + '：' + (e.response?.data?.detail || e.message))
      }
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