<template>
  <el-dialog :model-value="modelValue" :title="t('movementDetail')" width="750px" @update:model-value="$emit('update:modelValue', $event)">
    <!-- 批次概览 -->
    <div v-if="movement" class="compact-header">
      <span>{{ t('movementTime') }}: {{ formatDateTime(movement.created_at) }}</span>
      <span>
        <el-tag :type="getMovementTypeTag(movement.movement_type)" size="small">
          {{ getMovementTypeText(movement.movement_type) }}
        </el-tag>
      </span>
      <span>{{ t('dashTotal') }}: <strong>{{ movement.batch_total || 1 }}</strong></span>
      <span v-if="movement.session_code">Session: {{ movement.session_code }}</span>
      <span v-if="movement.target_device_name">{{ t('monitorScreenTotalDevices') }}: {{ movement.target_device_name }}</span>
      <span v-if="movement.source_device_name">{{ t('scrapSourceDevice') }}: {{ movement.source_device_name }}</span>
      <span v-if="movement.reason">{{ t('spareReason') }}: {{ movement.reason }}</span>
    </div>

    <!-- 本批次备件清单表格 -->
    <el-table :data="batchAllItems" stripe border size="small" style="margin-top: 8px">
      <el-table-column label="" width="60">
        <template #default="{ row }">
          <el-tag v-if="row.isCurrent" type="primary" size="small">{{ t('labelCurrent') }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="serial_number" :label="t('spareSerialNumber')" width="150">
        <template #default="{ row }">
          <span class="text-primary">{{ row.serial_number || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="po_number" :label="t('sparePoNumber')" width="100">
        <template #default="{ row }">{{ row.po_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="part_number" :label="t('sparePartNumber')" width="120">
        <template #default="{ row }">{{ row.part_number || '-' }}</template>
      </el-table-column>
      <el-table-column prop="name" :label="t('spareName')" min-width="120">
        <template #default="{ row }">{{ row.name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="unit_price" :label="t('spareUnitPrice')" width="80">
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
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

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
  const texts = {
    in: t('movementIn'),
    out: t('movementOut'),
    scrap_in: t('movementScrapIn'),
    scrap_out: t('movementScrapped')
  }
  return texts[type] || type
}

// 合并当前记录和batch_items
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