<template>
  <div class="data-table-wrapper">
    <!-- Filter Bar -->
    <div v-if="showFilter" class="filter-bar">
      <slot name="filter" :filters="filters" :apply="applyFilters" :reset="resetFilters">
        <!-- Default filter slot -->
      </slot>
      <div class="filter-actions">
        <el-button size="small" @click="resetFilters">{{ t('tableReset') }}</el-button>
        <el-button size="small" type="primary" @click="applyFilters">{{ t('tableSearch') }}</el-button>
      </div>
    </div>

    <!-- Table -->
    <el-table
      ref="tableRef"
      :data="data"
      :loading="loading"
      :stripe="stripe"
      :border="border"
      :size="size"
      :row-key="rowKey"
      :height="height"
      :max-height="maxHeight"
      @selection-change="handleSelectionChange"
      @row-click="handleRowClick"
      @sort-change="handleSortChange"
      v-bind="$attrs"
    >
      <slot />
    </el-table>

    <!-- Pagination -->
    <div v-if="showPagination" class="pagination-bar">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="pageSizes"
        :total="total"
        :layout="paginationLayout"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps({
  data: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  total: { type: Number, default: 0 },
  showFilter: { type: Boolean, default: true },
  showPagination: { type: Boolean, default: true },
  stripe: { type: Boolean, default: true },
  border: { type: Boolean, default: true },
  size: { type: String, default: 'small' },
  rowKey: { type: String, default: 'id' },
  height: { type: [String, Number], default: undefined },
  maxHeight: { type: [String, Number], default: undefined },
  pageSizes: { type: Array, default: () => [10, 20, 50, 100] },
  paginationLayout: { type: String, default: 'total, sizes, prev, pager, next' },
  initialFilters: { type: Object, default: () => {} },
})

const emit = defineEmits([
  'page-change',
  'size-change',
  'filter-change',
  'selection-change',
  'row-click',
  'sort-change',
])

const tableRef = ref(null)
const currentPage = ref(1)
const pageSize = ref(20)
const filters = ref({ ...props.initialFilters })

const applyFilters = () => {
  emit('filter-change', { ...filters.value, page: currentPage.value, size: pageSize.value })
}

const resetFilters = () => {
  filters.value = { ...props.initialFilters }
  currentPage.value = 1
  pageSize.value = 20
  applyFilters()
}

const handlePageChange = (page) => {
  currentPage.value = page
  emit('page-change', { page, size: pageSize.value, filters: filters.value })
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  emit('size-change', { page: currentPage.value, size, filters: filters.value })
}

const handleSelectionChange = (selection) => {
  emit('selection-change', selection)
}

const handleRowClick = (row) => {
  emit('row-click', row)
}

const handleSortChange = (sort) => {
  emit('sort-change', sort)
}

// Expose methods
defineExpose({
  refresh: applyFilters,
  reset: resetFilters,
  getTableRef: () => tableRef.value,
})
</script>

<style scoped>
.data-table-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding: 12px 0;
}
</style>