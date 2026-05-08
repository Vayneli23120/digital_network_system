<template>
  <el-dialog
    v-model="visible"
    :title="title"
    :width="width"
    :close-on-click-modal="closeOnClickModal"
    :close-on-press-escape="closeOnPressEscape"
    v-bind="$attrs"
    @close="handleClose"
  >
    <!-- Header Summary -->
    <div v-if="summary" class="dialog-summary">
      <template v-for="(item, key) in summary" :key="key">
        <span class="summary-item">
          <span class="summary-label">{{ item.label }}:</span>
          <span :class="['summary-value', item.class]">{{ item.value }}</span>
        </span>
      </template>
    </div>

    <!-- Content Table -->
    <el-table
      v-if="items.length > 0"
      :data="items"
      :stripe="stripe"
      :border="border"
      :size="size"
      :loading="loading"
      style="margin-top: 8px"
    >
      <el-table-column v-for="col in columns" :key="col.prop" :prop="col.prop" :label="col.label" :width="col.width" :min-width="col.minWidth">
        <template #default="{ row }">
          <span v-if="col.class" :class="col.class">{{ formatValue(row[col.prop], col.format) }}</span>
          <span v-else>{{ formatValue(row[col.prop], col.format) }}</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- Empty State -->
    <div v-else-if="!loading" class="empty-state">
      <span>{{ emptyText }}</span>
    </div>

    <!-- Footer Summary -->
    <div v-if="footerSummary && items.length > 0" class="dialog-footer-summary">
      <template v-for="(item, key) in footerSummary" :key="key">
        <span class="footer-item">
          {{ item.label }}: <strong :class="item.class">{{ item.value }}</strong>
        </span>
      </template>
    </div>

    <!-- Custom Footer -->
    <template #footer v-if="$slots.footer">
      <slot name="footer" />
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  width: { type: String, default: '750px' },
  summary: { type: Object, default: null },
  items: { type: Array, default: () => [] },
  columns: { type: Array, default: () => [] },
  footerSummary: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  stripe: { type: Boolean, default: true },
  border: { type: Boolean, default: true },
  size: { type: String, default: 'small' },
  emptyText: { type: String, default: '暂无数据' },
  closeOnClickModal: { type: Boolean, default: true },
  closeOnPressEscape: { type: Boolean, default: true },
})

const emit = defineEmits(['update:modelValue', 'close'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const formatValue = (value, format) => {
  if (!value) return '-'
  if (format === 'currency') return `¥${Number(value).toFixed(2)}`
  if (format === 'datetime') return value
  return value
}

const handleClose = () => {
  emit('close')
}
</script>

<style scoped>
.dialog-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 13px;
}

.summary-item {
  display: inline-flex;
  gap: 4px;
}

.summary-label {
  color: var(--text-tertiary);
}

.summary-value {
  font-weight: 500;
}

.summary-value.text-primary {
  color: var(--accent-primary);
}

.summary-value.text-success {
  color: var(--accent-primary);
}

.summary-value.text-danger {
  color: var(--accent-danger);
}

.empty-state {
  padding: 24px;
  text-align: center;
  color: var(--text-tertiary);
}

.dialog-footer-summary {
  margin-top: 12px;
  padding: 10px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  text-align: center;
  font-size: 13px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.footer-item strong {
  font-size: 15px;
}

.footer-item strong.text-primary {
  color: var(--accent-primary);
}

.footer-item strong.text-success {
  color: var(--accent-primary);
}

.footer-item strong.text-danger {
  color: var(--accent-danger);
}
</style>