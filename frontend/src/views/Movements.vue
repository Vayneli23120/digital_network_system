<template>
  <div class="movements-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuMovements') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn secondary" @click="loadMovements" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 筛选工具栏 -->
    <section class="filter-section">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="filter.keyword"
            :placeholder="t('spareSearchPlaceholder')"
            clearable
            class="search-input"
            @keyup.enter="loadMovements"
            @clear="loadMovements"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="filter.movement_type" :placeholder="t('movementType')" clearable class="type-select" @change="loadMovements">
            <el-option :label="t('movementIn')" value="in" />
            <el-option :label="t('movementOut')" value="out" />
            <el-option :label="t('movementScrapIn')" value="scrap_in" />
            <el-option :label="t('movementScrapOut')" value="scrap_out" />
          </el-select>
          <el-date-picker
            v-model="filter.start_date"
            type="date"
            :placeholder="t('movementStartDate')"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            class="date-picker"
            @change="loadMovements"
          />
          <el-date-picker
            v-model="filter.end_date"
            type="date"
            :placeholder="t('movementEndDate')"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            class="date-picker"
            @change="loadMovements"
          />
          <el-input
            v-model="filter.operator"
            :placeholder="t('movementOperator')"
            clearable
            class="operator-input"
            @keyup.enter="loadMovements"
            @clear="loadMovements"
          />
        </div>
        <div class="toolbar-right">
          <el-button size="small" @click="resetFilter">{{ t('actionReset') }}</el-button>
          <el-button size="small" type="primary" @click="loadMovements">{{ t('actionSearch') }}</el-button>
        </div>
      </div>
    </section>

    <!-- 数据表格 -->
    <section class="data-section">
      <div class="table-header">
        <span class="table-title">{{ t('movementHistory') }}</span>
        <span class="table-count">{{ total }} {{ t('deviceRecords') }}</span>
      </div>

      <el-table :data="movements" v-loading="loading" stripe @row-click="handleRowClick">
        <el-table-column prop="created_at" :label="t('movementTime')" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="name" :label="t('spareName')" width="130">
          <template #default="{ row }">
            <el-button type="primary" link>{{ row.name || '-' }}</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="serial_number" :label="t('spareSerialNumber')" width="120">
          <template #default="{ row }">{{ row.serial_number || '-' }}</template>
        </el-table-column>
        <el-table-column prop="po_number" :label="t('sparePoNumber')" width="100">
          <template #default="{ row }">{{ row.po_number || '-' }}</template>
        </el-table-column>
        <el-table-column prop="movement_type" :label="t('movementType')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getMovementTypeTag(row.movement_type)" size="small">
              {{ getMovementTypeText(row.movement_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" :label="t('spareQuantity')" width="80" align="right" />
        <el-table-column prop="unit_price" :label="t('spareUnitPrice')" width="100">
          <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column :label="t('monitorScreenTotalDevices')" width="120">
          <template #default="{ row }">
            <span v-if="row.target_device_name">{{ row.target_device_name }}</span>
            <span v-else-if="row.source_device_name">{{ row.source_device_name }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="reason" :label="t('spareReason')" min-width="150" show-overflow-tooltip />
      </el-table>

      <div class="pagination-bar">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          layout="total, prev, pager, next"
          :total="total"
          @current-change="loadMovements"
        />
      </div>
    </section>

    <!-- 详情对话框 -->
    <MovementDetailDialog v-model="detailDialogVisible" :movement="currentMovement" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { getMovements, getMovementDetail } from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'
import MovementDetailDialog from './spare-parts/MovementDetailDialog.vue'

const { t } = useI18n()

const movements = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)

const filter = reactive({
  keyword: '',
  movement_type: '',
  start_date: '',
  end_date: '',
  operator: ''
})

const detailDialogVisible = ref(false)
const currentMovement = ref(null)

const getMovementTypeTag = (type) => {
  const tags = { in: 'success', out: 'warning', scrap_in: 'info', scrap_out: 'danger' }
  return tags[type] || ''
}

const getMovementTypeText = (type) => {
  const texts = {
    in: t('movementIn'),
    out: t('movementOut'),
    scrap_in: t('movementScrapIn'),
    scrap_out: t('movementScrapOut')
  }
  return texts[type] || type
}

const loadMovements = debounce(async (force = false) => {
  loading.value = true
  try {
    const params = {
      skip: (page.value - 1) * pageSize.value,
      limit: pageSize.value,
      keyword: filter.keyword || undefined,
      movement_type: filter.movement_type || undefined,
      start_date: filter.start_date || undefined,
      end_date: filter.end_date || undefined,
      operator: filter.operator || undefined
    }
    const result = await cachedRequest(
      () => getMovements(params),
      'movements',
      params,
      { forceRefresh: force }
    )
    movements.value = result.items || []
    total.value = result.total || 0
  } catch (e) {
    if (e.name !== 'CanceledError') {
      ElMessage.error(t('msgLoadFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

const resetFilter = () => {
  filter.keyword = ''
  filter.movement_type = ''
  filter.start_date = ''
  filter.end_date = ''
  filter.operator = ''
  page.value = 1
  loadMovements()
}

const handleRowClick = async (row) => {
  try {
    const detail = await getMovementDetail(row.id)
    currentMovement.value = detail
  } catch (e) {
    currentMovement.value = row
  }
  detailDialogVisible.value = true
}

onMounted(loadMovements)
</script>

<style scoped>
.movements-page {
  padding: 0;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f8fafc 0%, #e8f4fc 50%, #f0f7ff 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 页面顶部导航条 */
.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.06);
  position: relative;
  overflow: hidden;
}

.page-nav-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #00b894, #55efc4, #0984e3);
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.nav-right {
  display: flex;
  gap: 8px;
}

.nav-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  color: white;
  border: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.25);
}

.nav-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 184, 148, 0.35);
}

.nav-action-btn.secondary {
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  box-shadow: none;
  padding: 8px 12px;
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

/* 筛选工具栏 */
.filter-section {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 12px rgba(0, 48, 135, 0.06);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.search-input {
  width: 200px;
}

.type-select {
  width: 120px;
}

.date-picker {
  width: 140px;
}

.operator-input {
  width: 120px;
}

/* 数据面板 */
.data-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.08);
}

.table-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.table-count {
  font-size: 12px;
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
}

.data-section :deep(.el-table) {
  border-radius: 8px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  background: rgba(255, 255, 255, 0.95);
}

.data-section :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.data-section :deep(th.el-table__cell) {
  background: transparent;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.03em;
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 48, 135, 0.1);
}

.data-section :deep(td.el-table__cell) {
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
  padding: 10px 0;
  background: transparent;
}

.data-section :deep(.el-table__row:hover > td) {
  background: rgba(0, 184, 148, 0.04) !important;
}

.data-section :deep(.el-button--primary.is-link) {
  color: #00b894;
  font-weight: 500;
}

.data-section :deep(.el-tag) {
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  padding: 4px 10px;
  border: 1px solid;
}

.data-section :deep(.el-tag.el-tag--success) {
  background: rgba(0, 184, 148, 0.08);
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}

.data-section :deep(.el-tag.el-tag--warning) {
  background: rgba(251, 191, 36, 0.08);
  border-color: rgba(251, 191, 36, 0.3);
  color: #f59e0b;
}

.data-section :deep(.el-tag.el-tag--info) {
  background: rgba(9, 132, 227, 0.08);
  border-color: rgba(9, 132, 227, 0.3);
  color: #0984e3;
}

.data-section :deep(.el-tag.el-tag--danger) {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.pagination-bar {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 48, 135, 0.06);
  display: flex;
  justify-content: flex-end;
}

.pagination-bar :deep(.el-pagination) {
  gap: 8px;
}

.pagination-bar :deep(.el-pagination button),
.pagination-bar :deep(.el-pager li) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 6px;
  border: 1px solid var(--border-default);
  font-size: 12px;
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.pagination-bar :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #00b894, #55efc4);
  border-color: transparent;
  color: white;
}

/* 暗黑模式 */
.dark .movements-page {
  background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #161b22 100%);
}

.dark .page-nav-bar {
  background: rgba(22, 27, 34, 0.9);
  border-color: rgba(48, 54, 61, 0.8);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .page-nav-bar::before {
  background: linear-gradient(90deg, #3fb950, #55efc4, #58a6ff);
}

.dark .page-title {
  color: #f0f6fc;
}

.dark .nav-action-btn {
  background: linear-gradient(135deg, #3fb950 0%, #55efc4 100%);
}

.dark .nav-action-btn.secondary {
  background: rgba(48, 54, 61, 0.8);
  color: #8b949e;
  border-color: #30363d;
}

.dark .nav-action-btn.secondary:hover {
  background: rgba(63, 185, 80, 0.15);
  border-color: #3fb950;
  color: #3fb950;
}

.dark .filter-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.dark .data-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

.dark .table-title {
  color: #f0f6fc;
}

.dark .table-count {
  color: #8b949e;
}

.dark .data-section :deep(.el-table) {
  border-color: rgba(48, 54, 61, 0.3);
  background: rgba(13, 17, 23, 0.95);
}

.dark .data-section :deep(th.el-table__cell) {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.6);
}

.dark .data-section :deep(td.el-table__cell) {
  border-bottom-color: rgba(48, 54, 61, 0.3);
}

.dark .data-section :deep(.el-table__row:hover > td) {
  background: rgba(63, 185, 80, 0.08) !important;
}

.dark .data-section :deep(.el-button--primary.is-link) {
  color: #3fb950;
}

.dark .data-section :deep(.el-tag.el-tag--success) {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}

.dark .data-section :deep(.el-tag.el-tag--warning) {
  background: rgba(210, 153, 34, 0.15);
  border-color: rgba(210, 153, 34, 0.4);
  color: #d29922;
}

.dark .data-section :deep(.el-tag.el-tag--info) {
  background: rgba(88, 166, 255, 0.15);
  border-color: rgba(88, 166, 255, 0.4);
  color: #58a6ff;
}

.dark .data-section :deep(.el-tag.el-tag--danger) {
  background: rgba(248, 81, 73, 0.15);
  border-color: rgba(248, 81, 73, 0.4);
  color: #f85149;
}

.dark .pagination-bar {
  border-top-color: rgba(48, 54, 61, 0.3);
}

.dark .pagination-bar :deep(.el-pagination button),
.dark .pagination-bar :deep(.el-pager li) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
  color: #8b949e;
}

.dark .pagination-bar :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #3fb950, #55efc4);
  color: white;
}

@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    flex-wrap: wrap;
  }

  .search-input,
  .type-select,
  .date-picker,
  .operator-input {
    width: 100%;
  }
}
</style>