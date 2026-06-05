<template>
  <div class="spare-parts-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuSpareParts') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          <span>{{ t('spareNew') }}</span>
        </button>
        <button class="nav-action-btn secondary" @click="refreshData" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-grid">
        <!-- 总备件种类 -->
        <div class="stat-card total" @click="filterByCategory('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Box /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.total_parts }}</div>
              <div class="metric-label">{{ t('spareStatsTotal') }}</div>
            </div>
            <div class="card-trend stable">
              <span class="trend-icon">●</span>
            </div>
          </div>
        </div>
        <!-- 总库存数量 -->
        <div class="stat-card quantity" @click="filterByCategory('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Goods /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.total_quantity }}</div>
              <div class="metric-label">{{ t('spareStatsQuantity') }}</div>
            </div>
            <div class="card-trend success">
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
        <!-- 库存价值 -->
        <div class="stat-card value">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Money /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ formatValue(stats.total_value) }}</div>
              <div class="metric-label">{{ t('spareStatsValue') }}</div>
            </div>
            <div class="card-trend info">
              <span class="trend-currency">¥</span>
            </div>
          </div>
        </div>
        <!-- 低库存预警 -->
        <div class="stat-card warning" @click="toggleLowStock">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.low_stock_count }}</div>
              <div class="metric-label">{{ t('spareStatsLowStock') }}</div>
            </div>
            <div class="card-trend alert" v-if="stats.low_stock_count > 0">
              <el-icon><Warning /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 状态筛选 Chips -->
    <section class="filter-section">
      <div class="filter-toolbar">
        <!-- 搜索框 -->
        <div class="search-box">
          <el-icon class="search-icon"><Search /></el-icon>
          <el-input
            v-model="searchText"
            :placeholder="t('spareSearchPlaceholder')"
            class="search-input"
            clearable
            @input="handleSearch"
          />
        </div>

        <!-- 类型 Chips -->
        <div class="status-chips">
          <div
            :class="['status-chip', { active: filterCategory === '' }]"
            @click="filterByCategory('')"
          >
            <span class="chip-label">{{ t('spareFilterAll') }}</span>
            <span class="chip-count">{{ stats.total_parts }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-module', { active: filterCategory === 'module' }]"
            @click="filterByCategory('module')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('spareCategoryModule') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-power', { active: filterCategory === 'power' }]"
            @click="filterByCategory('power')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('spareCategoryPower') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-cable', { active: filterCategory === 'cable' }]"
            @click="filterByCategory('cable')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('spareCategoryCable') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-other', { active: filterCategory === 'other' }]"
            @click="filterByCategory('other')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('spareCategoryOther') }}</span>
          </div>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-checkbox v-model="lowStockFilter" @change="handleLowStockChange">
            <span class="low-stock-label">{{ t('spareLowStock') }}</span>
          </el-checkbox>
        </div>
      </div>
    </section>

    <!-- 数据表格区域 -->
    <section class="data-section">
      <PartsTable
        ref="partsTableRef"
        :external-search="searchText"
        :external-category="filterCategory"
        :external-low-stock="lowStockFilter"
        @show-detail="showPartDetail"
        @stats-loaded="onStatsLoaded"
      />
    </section>

    <!-- 备件详情对话框 -->
    <PartDetailDialog v-model="detailDialogVisible" :part="currentDetailPart" />

    <!-- 新增备件对话框 -->
    <el-dialog v-model="showAddDialog" :title="t('spareNew')" width="480px" append-to-body draggable align-center class="spare-add-dialog">
      <el-form :model="addForm" label-width="80px" size="default">
        <!-- 基础信息 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Box /></el-icon>
            <span>{{ t('spareBasicSection') }}</span>
          </div>
          <el-form-item :label="t('sparePartNumber')" required>
            <el-input v-model="addForm.part_number" :placeholder="t('sparePartNumberPlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('spareName')" required>
            <el-input v-model="addForm.name" :placeholder="t('spareNamePlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('spareCategory')">
            <el-select v-model="addForm.category" style="width: 100%">
              <el-option :label="t('spareCategoryModule')" value="module" />
              <el-option :label="t('spareCategoryPower')" value="power" />
              <el-option :label="t('spareCategoryCable')" value="cable" />
              <el-option :label="t('spareCategoryOther')" value="other" />
            </el-select>
          </el-form-item>
        </div>

        <!-- 存放信息 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Goods /></el-icon>
            <span>{{ t('spareLocationSection') || '存放信息' }}</span>
          </div>
          <el-form-item :label="t('spareLocation')">
            <el-input v-model="addForm.location" :placeholder="t('spareLocationPlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('spareMinQuantity')">
            <el-input-number v-model="addForm.min_quantity" :min="0" style="width: 100%" />
            <div class="field-hint">{{ t('spareMinQuantityHint') || '库存低于此数量时显示低库存警告' }}</div>
          </el-form-item>
        </div>

        <!-- 备注 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Document /></el-icon>
            <span>{{ t('spareDescSection') }}</span>
          </div>
          <el-form-item :label="t('spareDescription')">
            <el-input v-model="addForm.description" type="textarea" :rows="2" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="handleAddPart">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Box, Goods, Money, Warning, CircleCheck, Search, Plus, Document } from '@element-plus/icons-vue'
import PartsTable from './spare-parts/PartsTable.vue'
import PartDetailDialog from './spare-parts/PartDetailDialog.vue'
import { useI18n } from '@/composables/useI18n'
import { createPart } from '@/api'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

const partsTableRef = ref(null)
const loading = ref(false)

// 统计数据
const stats = reactive({
  total_parts: 0,
  total_quantity: 0,
  low_stock_count: 0,
  total_value: 0
})

// 篩选状态
const searchText = ref('')
const filterCategory = ref('')
const lowStockFilter = ref(false)

// 备件详情对话框
const detailDialogVisible = ref(false)
const currentDetailPart = ref(null)

// 新增备件对话框
const showAddDialog = ref(false)
const addForm = ref({
  part_number: '',
  name: '',
  category: 'other',
  min_quantity: 0,
  location: '',
  description: ''
})

// 格式化价值显示
const formatValue = (value) => {
  if (!value) return '0'
  if (value >= 10000) {
    return (value / 10000).toFixed(1) + 'w'
  }
  return value.toFixed(0)
}

// 类型筛选
const filterByCategory = (category) => {
  filterCategory.value = category
  handleSearch()
}

// 低库存筛选
const toggleLowStock = () => {
  lowStockFilter.value = !lowStockFilter.value
  handleSearch()
}

const handleLowStockChange = () => {
  handleSearch()
}

// 搜索处理
const handleSearch = () => {
  if (partsTableRef.value) {
    partsTableRef.value.loadParts()
  }
}

// 刷新数据
const refreshData = () => {
  loading.value = true
  if (partsTableRef.value) {
    partsTableRef.value.loadParts()
  }
  setTimeout(() => {
    loading.value = false
  }, 500)
}

// 显示备件详情
const showPartDetail = (row) => {
  currentDetailPart.value = row
  detailDialogVisible.value = true
}

// 新增备件
const handleAddPart = async () => {
  if (!addForm.value.part_number) {
    ElMessage.warning(t('sparePartNumberRequired'))
    return
  }
  if (!addForm.value.name) {
    ElMessage.warning(t('spareNameRequired'))
    return
  }
  try {
    await createPart(addForm.value)
    ElMessage.success(t('spareAddSuccess'))
    showAddDialog.value = false
    resetAddForm()
    refreshData()
  } catch (error) {
    ElMessage.error(t('spareAddFailed') + ': ' + (error.response?.data?.detail || error.message))
  }
}

const resetAddForm = () => {
  addForm.value = {
    part_number: '',
    name: '',
    category: 'other',
    min_quantity: 0,
    location: '',
    description: ''
  }
}

// 统计数据加载
const onStatsLoaded = (statsData) => {
  Object.assign(stats, statsData)
}

onMounted(() => {
  // 初始加载
})
</script>

<style scoped>
/* 字体清晰度优化 - 所有等宽字体 */
.metric-value,
.chip-count,
.table-count,
.time-text,
.price-value {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* ===== 页面整体背景 ===== */
.spare-parts-page {
  padding: 0;
  min-height: calc(100vh - 60px);
  background: linear-gradient(135deg, #f8fafc 0%, #e8f4fc 50%, #f0f7ff 100%);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 页面顶部导航条 ===== */
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
  align-items: baseline;
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

/* ===== 统计 Dashboard ===== */
.stats-dashboard {
  padding: 16px;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(16px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(0, 184, 148, 0.05) 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.stat-card:hover::before {
  opacity: 1;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 32px rgba(0, 48, 135, 0.12);
}

.card-content {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
}

.card-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  transition: transform 0.3s;
}

.stat-card:hover .card-icon {
  transform: scale(1.05);
}

.stat-card.total .card-icon {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.15) 0%, rgba(0, 184, 148, 0.08) 100%);
  color: #00b894;
}

.stat-card.quantity .card-icon {
  background: linear-gradient(135deg, rgba(9, 132, 227, 0.15) 0%, rgba(9, 132, 227, 0.08) 100%);
  color: #0984e3;
}

.stat-card.value .card-icon {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.15) 0%, rgba(251, 191, 36, 0.08) 100%);
  color: #f59e0b;
}

.stat-card.warning .card-icon {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.08) 100%);
  color: #ef4444;
}

.card-body {
  flex: 1;
}

.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
  letter-spacing: -0.02em;
}

.metric-label {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-top: 6px;
  font-weight: 500;
}

.card-trend {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.card-trend.stable {
  background: rgba(0, 184, 148, 0.1);
  color: #00b894;
}

.card-trend.success {
  background: rgba(9, 132, 227, 0.1);
  color: #0984e3;
}

.card-trend.info {
  background: rgba(251, 191, 36, 0.1);
  color: #f59e0b;
}

.card-trend.alert {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.trend-currency {
  font-size: 11px;
  font-weight: 600;
  color: #f59e0b;
}

/* ===== 筛选工具栏 ===== */
.filter-section {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 12px rgba(0, 48, 135, 0.06);
}

.filter-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--text-tertiary);
  font-size: 14px;
  z-index: 1;
}

.search-input {
  width: 240px;
}

.search-input :deep(.el-input__wrapper) {
  padding-left: 36px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  box-shadow: none;
  transition: all 0.25s;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-primary);
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(0, 184, 148, 0.15);
}

/* Status Chips */
.status-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.status-chip::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  right: 50%;
  height: 2px;
  background: currentColor;
  transition: all 0.25s ease;
}

.status-chip:hover::before,
.status-chip.active::before {
  left: 0;
  right: 0;
}

.status-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.1);
}

.status-chip.active {
  background: rgba(0, 184, 148, 0.08);
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.chip-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.status-chip.active .chip-label {
  color: #00b894;
}

.chip-count {
  font-size: 11px;
  color: var(--text-tertiary);
  padding: 2px 6px;
  background: rgba(0, 48, 135, 0.05);
  border-radius: 4px;
}

.status-chip.chip-module .chip-dot { background: #0984e3; }
.status-chip.chip-power .chip-dot { background: #f59e0b; }
.status-chip.chip-cable .chip-dot { background: #74b9ff; }
.status-chip.chip-other .chip-dot { background: #636e72; }

.status-chip.chip-module:hover { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); }
.status-chip.chip-module.active { background: rgba(9, 132, 227, 0.08); border-color: rgba(9, 132, 227, 0.3); color: #0984e3; }
.status-chip.chip-power:hover { background: rgba(251, 191, 36, 0.08); border-color: rgba(251, 191, 36, 0.3); }
.status-chip.chip-power.active { background: rgba(251, 191, 36, 0.08); border-color: rgba(251, 191, 36, 0.3); color: #f59e0b; }
.status-chip.chip-cable:hover { background: rgba(116, 185, 255, 0.08); border-color: rgba(116, 185, 255, 0.3); }
.status-chip.chip-cable.active { background: rgba(116, 185, 255, 0.08); border-color: rgba(116, 185, 255, 0.3); color: #74b9ff; }
.status-chip.chip-other:hover { background: rgba(45, 52, 54, 0.08); border-color: rgba(45, 52, 54, 0.3); }
.status-chip.chip-other.active { background: rgba(45, 52, 54, 0.08); border-color: rgba(45, 52, 54, 0.3); color: #636e72; }

.more-filters {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.low-stock-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.more-filters :deep(.el-checkbox__label) {
  font-size: 13px;
}

/* ===== 数据表格区域 ===== */
.data-section {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
  overflow: hidden;
}

/* ===== 子组件样式覆盖 - 企业级表格 ===== */
.data-section :deep(.el-card) {
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
}

.data-section :deep(.el-card__header) {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.08);
  background: transparent;
}

.data-section :deep(.el-card__body) {
  padding: 0 16px 16px;
}

.data-section :deep(.card-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-section :deep(.filter-toolbar),
.data-section :deep(.toolbar) {
  padding: 12px 0;
  margin-bottom: 8px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.data-section :deep(.toolbar-left) {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.data-section :deep(.toolbar-right) {
  display: flex;
  gap: 8px;
}

.data-section :deep(.el-input__wrapper),
.data-section :deep(.el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 6px;
  border: 1px solid var(--border-default);
  box-shadow: none;
}

.data-section :deep(.el-table) {
  border-radius: 8px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  background: rgba(255, 255, 255, 0.95);
}

.data-section :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.data-section :deep(.el-table__header-wrapper) {
  border-bottom: 2px solid rgba(0, 48, 135, 0.1);
}

.data-section :deep(th.el-table__cell) {
  background: transparent;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
  padding: 12px 0;
  border-bottom: none;
}

.data-section :deep(td.el-table__cell) {
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
  padding: 10px 0;
  background: transparent;
}

.data-section :deep(.el-table__row) {
  transition: all 0.25s ease;
  background: transparent;
}

.data-section :deep(.el-table__row:hover > td) {
  background: rgba(0, 184, 148, 0.04) !important;
}

.data-section :deep(.el-button--primary.is-link) {
  color: #00b894;
  font-weight: 500;
}

.data-section :deep(.el-button--primary.is-link:hover) {
  color: #55efc4;
}

/* 状态徽章 */
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

.data-section :deep(.el-tag.el-tag--danger) {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
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

/* 操作按钮 */
.data-section :deep(.table-actions) {
  display: flex;
  gap: 4px;
}

.data-section :deep(.el-button--small) {
  border-radius: 6px;
  font-size: 12px;
  padding: 6px 12px;
}

.data-section :deep(.el-button--success) {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.9) 0%, rgba(85, 239, 196, 0.9) 100%);
  border: none;
}

.data-section :deep(.el-button--warning) {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.9) 0%, rgba(250, 200, 100, 0.9) 100%);
  border: none;
}

/* 分页 */
.data-section :deep(.pagination-bar) {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 48, 135, 0.06);
  display: flex;
  justify-content: flex-end;
}

.data-section :deep(.el-pagination) {
  gap: 8px;
}

.data-section :deep(.el-pagination button),
.data-section :deep(.el-pager li) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 6px;
  border: 1px solid var(--border-default);
  font-size: 12px;
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.data-section :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #00b894, #55efc4);
  border-color: transparent;
  color: white;
}

/* ===== 新增备件对话框样式 ===== */
.spare-add-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}
.spare-add-dialog .section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
}
.spare-add-dialog .section-header .el-icon {
  color: var(--accent-primary);
}
.spare-add-dialog .el-form-item {
  margin-bottom: 10px;
}
.spare-add-dialog .field-hint {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 4px;
  line-height: 1.4;
}

/* ===== 对话框样式 ===== */
.spare-dialog :deep(.el-dialog__header) {
  border-bottom: 1px solid rgba(0, 48, 135, 0.08);
  padding-bottom: 16px;
}

.spare-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

.spare-dialog :deep(.el-dialog__footer) {
  border-top: 1px solid rgba(0, 48, 135, 0.08);
  padding-top: 16px;
}

.dialog-content {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .status-chips {
    justify-content: center;
  }

  .more-filters {
    justify-content: center;
    margin-left: 0;
  }

  .page-nav-bar {
    flex-direction: column;
    gap: 12px;
  }

  .nav-right {
    width: 100%;
    justify-content: center;
  }
}

/* ===== 暗黑模式 ===== */
.dark .spare-parts-page {
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

.dark .stats-dashboard {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

.dark .stat-card {
  background: rgba(13, 17, 23, 0.95);
  border-color: rgba(48, 54, 61, 0.6);
}

.dark .stat-card:hover {
  background: rgba(22, 27, 34, 0.95);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.dark .metric-value {
  color: #f0f6fc;
}

.dark .metric-label {
  color: #8b949e;
}

.dark .card-trend.stable { background: rgba(63, 185, 80, 0.2); color: #3fb950; }
.dark .card-trend.success { background: rgba(88, 166, 255, 0.2); color: #58a6ff; }
.dark .card-trend.info { background: rgba(210, 153, 34, 0.2); color: #d29922; }
.dark .card-trend.alert { background: rgba(248, 81, 73, 0.2); color: #f85149; }

.dark .filter-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.dark .search-input :deep(.el-input__wrapper) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

.dark .search-input :deep(.el-input__wrapper:hover),
.dark .search-input :deep(.el-input__wrapper.is-focus) {
  border-color: #3fb950;
  box-shadow: 0 0 0 3px rgba(63, 185, 80, 0.15);
}

.dark .search-icon {
  color: #8b949e;
}

.dark .status-chip {
  background: rgba(13, 17, 23, 0.9);
  border-color: #30363d;
}

.dark .status-chip:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .chip-label {
  color: #8b949e;
}

.dark .status-chip.active {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}

.dark .status-chip.active .chip-label {
  color: #3fb950;
}

.dark .chip-count {
  background: rgba(48, 54, 61, 0.3);
  color: #8b949e;
}

.dark .low-stock-label {
  color: #8b949e;
}

.dark .data-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

/* 暗黑模式子组件覆盖 */
.dark .data-section :deep(.el-card__header) {
  border-bottom-color: rgba(48, 54, 61, 0.6);
}

.dark .data-section :deep(.filter-toolbar),
.dark .data-section :deep(.toolbar) {
  border-bottom-color: rgba(48, 54, 61, 0.3);
}

.dark .data-section :deep(.el-input__wrapper),
.dark .data-section :deep(.el-select .el-input__wrapper) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

.dark .data-section :deep(.el-table) {
  border-color: rgba(48, 54, 61, 0.3);
  background: rgba(13, 17, 23, 0.95);
}

.dark .data-section :deep(.el-table__header-wrapper) {
  border-bottom-color: rgba(48, 54, 61, 0.6);
}

.dark .data-section :deep(th.el-table__cell) {
  color: #8b949e;
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

.dark .data-section :deep(.el-button--primary.is-link:hover) {
  color: #55efc4;
}

/* 暗黑模式状态徽章 */
.dark .data-section :deep(.el-tag.el-tag--success) {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}

.dark .data-section :deep(.el-tag.el-tag--danger) {
  background: rgba(248, 81, 73, 0.15);
  border-color: rgba(248, 81, 73, 0.4);
  color: #f85149;
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

.dark .data-section :deep(.pagination-bar) {
  border-top-color: rgba(48, 54, 61, 0.3);
}

.dark .data-section :deep(.el-pagination button),
.dark .data-section :deep(.el-pager li) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
  color: #8b949e;
}

.dark .data-section :deep(.el-pager li.is-active) {
  background: linear-gradient(135deg, #3fb950, #55efc4);
  color: white;
}

/* 暗黑模式新增备件对话框 */
.dark .spare-add-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}
.dark .spare-add-dialog .section-header {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}
.dark .spare-add-dialog .section-header .el-icon {
  color: #58a6ff;
}

/* 暗黑模式对话框 */
.dark .spare-dialog :deep(.el-dialog) {
  background: rgba(22, 27, 34, 0.95);
  border: 1px solid #30363d;
}

.dark .spare-dialog :deep(.el-dialog__header) {
  border-bottom-color: rgba(48, 54, 61, 0.6);
}

.dark .spare-dialog :deep(.el-dialog__title) {
  color: #f0f6fc;
}

.dark .spare-dialog :deep(.el-dialog__footer) {
  border-top-color: rgba(48, 54, 61, 0.6);
}

.dark .dialog-content {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}
</style>