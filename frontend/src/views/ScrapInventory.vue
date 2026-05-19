<template>
  <div class="scrap-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('scrapManagement') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn primary" @click="showAddScrapDialog">
          <el-icon><Plus /></el-icon>
          {{ t('scrapAddMaterial') }}
        </button>
        <button class="nav-action-btn secondary" @click="loadScrapItems" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- Tab 切换 Chips -->
    <section class="tab-section">
      <div class="tab-chips">
        <div
          :class="['tab-chip', { active: activeTab === 'scrap' }]"
          @click="activeTab = 'scrap'"
        >
          <el-icon class="chip-icon"><Document /></el-icon>
          <span class="chip-label">{{ t('scrapTabLabel') }}</span>
          <span class="chip-count">{{ scrapItems.length }}</span>
        </div>
        <div
          :class="['tab-chip', 'chip-history', { active: activeTab === 'history' }]"
          @click="activeTab = 'history'"
        >
          <el-icon class="chip-icon"><Clock /></el-icon>
          <span class="chip-label">{{ t('scrapHistoryTab') }}</span>
          <span class="chip-count">{{ historyTotal }}</span>
        </div>
      </div>
    </section>

    <!-- 报废库存 Tab 内容 -->
    <section v-show="activeTab === 'scrap'" class="scrap-content">
      <!-- 统计 Dashboard -->
      <section class="stats-dashboard">
        <div class="stats-grid">
          <!-- 类型数 -->
          <div class="stat-card types">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Collection /></el-icon>
              </div>
              <div class="card-body">
                <div class="metric-value">{{ stats.total_types }}</div>
                <div class="metric-label">{{ t('scrapTypes') }}</div>
              </div>
            </div>
          </div>
          <!-- 总数量 -->
          <div class="stat-card quantity">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Box /></el-icon>
              </div>
              <div class="card-body">
                <div class="metric-value">{{ stats.total_quantity }}</div>
                <div class="metric-label">{{ t('scrapTotalCount') }}</div>
              </div>
              <div class="card-trend warning" v-if="stats.total_quantity > 0">
                <el-icon><Warning /></el-icon>
              </div>
            </div>
          </div>
          <!-- 总价值 -->
          <div class="stat-card value">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Wallet /></el-icon>
              </div>
              <div class="card-body">
                <div class="metric-value">¥{{ stats.total_value.toFixed(2) }}</div>
                <div class="metric-label">{{ t('scrapTotalValue') }}</div>
              </div>
            </div>
          </div>
          <!-- 本月新增 -->
          <div class="stat-card month">
            <div class="card-content">
              <div class="card-icon">
                <el-icon><Calendar /></el-icon>
              </div>
              <div class="card-body">
                <div class="metric-value">{{ stats.month_count }}</div>
                <div class="metric-label">{{ t('scrapMonthNew') }}</div>
              </div>
              <div class="card-trend stable">
                <span class="trend-icon">●</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 筛选工具栏 -->
      <section class="filter-section">
        <div class="filter-toolbar">
          <div class="search-box">
            <el-icon class="search-icon"><Search /></el-icon>
            <el-input
              v-model="search"
              :placeholder="t('spareSearchPlaceholder')"
              class="search-input"
              clearable
              @keyup.enter="loadScrapItems"
              @clear="loadScrapItems"
            />
          </div>
          <div class="filter-selects">
            <el-select v-model="category" :placeholder="t('spareCategory')" clearable style="width: 120px" @change="loadScrapItems">
              <el-option :label="t('spareCategoryModule')" value="module" />
              <el-option :label="t('spareCategoryPower')" value="power" />
              <el-option :label="t('spareCategoryCable')" value="cable" />
              <el-option :label="t('spareCategoryOther')" value="other" />
            </el-select>
          </div>
          <div class="filter-actions">
            <button class="filter-btn secondary" @click="resetFilters">{{ t('actionReset') }}</button>
            <button class="filter-btn primary" @click="loadScrapItems">{{ t('actionSearch') }}</button>
          </div>
        </div>
      </section>

        <!-- 数据面板 -->
      <section class="data-section">
        <el-table
          :data="scrapItems"
          stripe
          border
          v-loading="loading"
          header-align="center"
        >
          <el-table-column prop="name" :label="t('spareName')" min-width="150">
            <template #default="{ row }">
              <el-button type="primary" link @click="showScrapDetail(row)">
                {{ row.name }}
              </el-button>
            </template>
          </el-table-column>
          <el-table-column prop="part_number" :label="t('sparePartNumber')" min-width="130" />
          <el-table-column prop="quantity" :label="t('spareQuantity')" min-width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.quantity > 0 ? 'warning' : 'info'" size="small">
                {{ row.quantity }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('spareTotalPrice')" min-width="100" align="center">
            <template #default="{ row }">
              <span v-if="row.total_value && row.total_value > 0">¥{{ row.total_value.toFixed(2) }}</span>
              <span v-else class="text-muted">--</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('dashAction')" min-width="280" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button size="small" plain @click="showEditScrapDialog(row)">
                  <el-icon><Edit /></el-icon>
                  {{ t('actionEdit') }}
                </el-button>
                <el-button size="small" plain @click="showInDialog(row)">
                  <el-icon><Plus /></el-icon>
                  {{ t('spareStockIn') }}
                </el-button>
                <el-button size="small" plain @click="showScrapOutDialog(row)">
                  <el-icon><Minus /></el-icon>
                  {{ t('scrapScrap') }}
                </el-button>
                <el-button size="small" plain @click="handleDeleteScrap(row)">
                  <el-icon><Delete /></el-icon>
                  {{ t('actionDelete') }}
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </section>
    </section>

    <!-- 报废历史 Tab 内容 -->
    <section v-show="activeTab === 'history'" class="history-content">
      <!-- 数据面板 -->
      <section class="data-section">
        <el-table
          :data="historyItems"
          stripe
          border
          v-loading="historyLoading"
          header-align="center"
        >
          <el-table-column prop="created_at" :label="t('movementTime')" min-width="160">
            <template #default="{ row }">
              {{ formatDateTime(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column prop="name" :label="t('scrapPartName')" min-width="120">
            <template #default="{ row }">
              {{ row.name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="part_number" :label="t('sparePartNumber')" min-width="130" />
          <el-table-column prop="serial_number" :label="t('scrapSerialNumber')" min-width="130">
            <template #default="{ row }">
              {{ row.serial_number || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="movement_type" :label="t('movementType')" min-width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.movement_type === 'scrap_in' ? 'warning' : 'danger'" size="small">
                {{ row.movement_type === 'scrap_in' ? t('scrapScrapIn') : t('scrapScrapped') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="quantity" :label="t('spareQuantity')" min-width="80" align="center">
            <template #default="{ row }">
              {{ row.quantity }}
            </template>
          </el-table-column>
          <el-table-column :label="t('scrapSourceDevice')" min-width="100" align="center">
            <template #default="{ row }">
              {{ row.source_device_name || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="unit_price" :label="t('spareUnitPrice')" min-width="90" align="center">
            <template #default="{ row }">
              ¥{{ (row.unit_price || 0).toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="reason" :label="t('spareReason')" min-width="150" show-overflow-tooltip />
          <el-table-column prop="reference" :label="t('scrapRelatedMaintenance')" min-width="120" show-overflow-tooltip />
        </el-table>

        <div class="pagination-bar">
          <el-pagination
            v-model:current-page="historyPage"
            :page-size="50"
            layout="total, prev, pager, next"
            :total="historyTotal"
            @current-change="loadHistory"
          />
        </div>
      </section>
    </section>

    <!-- 报废详情对话框 -->
    <el-dialog v-model="detailDialogVisible" :title="t('scrapStockList')" width="750px">
      <!-- 概览（紧凑） -->
      <div v-if="currentScrapItem" class="compact-header">
        <span>{{ t('scrapStockLabel') }}: <strong class="text-danger">{{ currentScrapItem.quantity || 0 }}</strong> {{ t('spareQuantity') }}</span>
        <span>{{ t('scrapValueLabel') }}: <strong class="text-success">¥{{ (currentScrapItem.total_value || 0).toFixed(2) }}</strong></span>
        <span>{{ t('scrapPartNumberLabel') }}: {{ currentScrapItem.part_number || '-' }}</span>
      </div>

      <!-- 报废件清单表格 -->
      <el-table :data="currentScrapItem?.instances || []" stripe border size="small" style="margin-top: 8px">
        <el-table-column prop="serial_number" :label="t('scrapSerialNumber')" width="150">
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
        <el-table-column :label="t('scrapSourceDevice')" width="120">
          <template #default="{ row }">
            <span v-if="row.source_device_name">{{ row.source_device_name }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="scraped_at" :label="t('scrapScrapInTime')" width="160">
          <template #default="{ row }">{{ row.scraped_at ? formatDateTime(row.scraped_at) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="reason" :label="t('scrapScrapReason')" min-width="150" show-overflow-tooltip />
        <el-table-column prop="reference" :label="t('scrapRelatedMaintenance')" width="120" show-overflow-tooltip />
      </el-table>

      <el-empty v-if="!currentScrapItem?.instances?.length && !currentScrapItem?.noSerialCount" :description="t('scrapNoScrapStock')" />
    </el-dialog>

    <!-- 扫码录入对话框 -->
    <el-dialog v-model="scanDialogVisible" :title="t('scrapScanInput')" width="700px">
      <ScanSession
        ref="scanSessionRef"
        default-type="return"
        :auto-start="scanDialogVisible"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
      <template #footer>
        <el-button @click="scanDialogVisible = false">{{ t('actionClose') }}</el-button>
        <el-button type="primary" @click="submitScrapFromScan" :disabled="scanItems.length === 0" :loading="submitting">
          {{ t('scrapConfirmScrapInItems', { count: scanItems.length }) }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 手动录入对话框 -->
    <el-dialog v-model="manualDialogVisible" :title="t('scrapManualInput')" width="600px">
      <el-form :model="manualForm" label-width="100px">
        <el-form-item :label="t('spareSerialNumber')" required>
          <el-input v-model="manualForm.serial_number" :placeholder="t('spareSearchSerialPlaceholder')" @keyup.enter="searchSerialForScrap" />
          <el-button size="small" type="primary" @click="searchSerialForScrap" :loading="searchingSerial" style="margin-top: 8px">
            {{ t('spareQuery') }}
          </el-button>
        </el-form-item>

        <!-- 识别到的信息 -->
        <div v-if="foundPartInfo" style="background: var(--el-fill-color-light); padding: 12px; border-radius: 8px; margin-bottom: 16px">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
            <el-tag type="success" size="small">{{ t('scrapRecognized') }}</el-tag>
            <span style="font-weight: 600; color: var(--el-color-primary)">{{ foundPartInfo.serial_number }}</span>
          </div>
          <el-descriptions :column="3" size="small" border>
            <el-descriptions-item :label="t('sparePartNumber')">{{ foundPartInfo.part_number }}</el-descriptions-item>
            <el-descriptions-item :label="t('spareName')">{{ foundPartInfo.name }}</el-descriptions-item>
            <el-descriptions-item :label="t('spareUnitPrice')">¥{{ (foundPartInfo.unit_price || 0).toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item :label="t('scrapInStockTime')">{{ foundPartInfo.in_stock_at ? formatDateTime(foundPartInfo.in_stock_at) : '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('scrapOutStockTime')">{{ foundPartInfo.out_at ? formatDateTime(foundPartInfo.out_at) : '-' }}</el-descriptions-item>
            <el-descriptions-item :label="t('monitorScreenStatus')">
              <el-tag :type="foundPartInfo.status === 'scrap' ? 'danger' : 'warning'" size="small">
                {{ foundPartInfo.status === 'scrap' ? t('scrapScrapped') : foundPartInfo.status }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 未识别时手动填写 -->
        <el-divider v-if="!foundPartInfo" />

        <el-form-item :label="t('sparePartNumber')" v-if="!foundPartInfo" required>
          <el-select v-model="manualForm.part_id" :placeholder="t('scrapSelectFromParts')" filterable clearable @change="onPartSelect">
            <el-option
              v-for="part in partOptions"
              :key="part.id"
              :label="`${part.part_number} - ${part.name}`"
              :value="part.id"
            />
          </el-select>
          <div style="margin-top: 8px">
            <el-input v-model="manualForm.part_number_manual" :placeholder="t('scrapOrManualInput')" style="width: 200px" />
            <el-input v-model="manualForm.name_manual" :placeholder="t('scrapNameDefaultPartNumber')" style="width: 200px; margin-left: 8px" />
          </div>
        </el-form-item>

        <el-form-item :label="t('spareUnitPrice')">
          <el-input-number v-model="manualForm.unit_price" :min="0" :precision="2" :disabled="foundPartInfo" />
        </el-form-item>

        <el-form-item :label="t('scrapScrapReason')" required>
          <el-input v-model="manualForm.reason" type="textarea" :placeholder="t('scrapScrapReason')" />
        </el-form-item>

        <el-form-item :label="t('scrapRelatedMaintenance')">
          <el-input v-model="manualForm.reference" :placeholder="t('scrapReferenceMaintenanceNo')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualDialogVisible = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitManualScrap" :loading="submitting" :disabled="!manualForm.serial_number">
          {{ t('scrapConfirmScrapIn') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 入库对话框 -->
    <el-dialog v-model="manualInDialogVisible" :title="t('spareStockIn')" width="500px" append-to-body draggable align-center class="scrap-in-dialog">
      <!-- 扫码入库 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Aim /></el-icon>
          <span>{{ t('scrapScanSection') }}</span>
        </div>
        <div class="section-action-bar">
          <el-button type="success" @click="openScrapInScanDialog">
            <el-icon><Aim /></el-icon>
            {{ t('scrapScanGunStockIn') }}
          </el-button>
          <span class="action-tip">{{ t('scrapScanGunTip') }}</span>
        </div>
      </div>

      <!-- 手动输入 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Edit /></el-icon>
          <span>{{ t('scrapManualInputSection') }}</span>
        </div>
        <el-form :model="manualInForm" label-width="80px" size="default">
          <el-form-item :label="t('scrapPartsLabel')">
            <el-input :value="currentManualPart?.name" disabled />
          </el-form-item>
          <el-form-item :label="t('spareSerialNumber')" required>
            <el-input v-model="manualInForm.serial_number" :placeholder="t('scrapSerialScanPlaceholder')" />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item :label="t('spareUnitPrice')">
                <el-input-number v-model="manualInForm.unit_price" :min="0" :precision="2" style="width: 110px" />
                <span class="unit-text">元</span>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item :label="t('scrapScrapReason')">
            <el-input v-model="manualInForm.reason" type="textarea" :rows="2" :placeholder="t('scrapScrapReasonPlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('scrapRelatedMaintenance')">
            <el-input v-model="manualInForm.reference" :placeholder="t('scrapReferenceMaintenanceNo')" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="manualInDialogVisible = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitManualIn" :loading="manualInSubmitting">{{ t('spareConfirmIn') }}</el-button>
      </template>
    </el-dialog>

    <!-- 扫码入库对话框 -->
    <el-dialog v-model="scrapInScanDialogVisible" :title="t('scrapScanGunStockInTitle')" width="700px">
      <ScanSession
        ref="scrapInScanSessionRef"
        default-type="return"
        :part-id="currentManualPart?.part_id"
        :auto-start="scrapInScanDialogVisible"
        @complete="onScrapInScanComplete"
        @cancel="scrapInScanDialogVisible = false"
      />
      <template #footer>
        <el-button @click="scrapInScanDialogVisible = false">{{ t('actionClose') }}</el-button>
      </template>
    </el-dialog>

    <!-- 报废出库对话框 -->
    <el-dialog v-model="scrapOutDialogVisible" :title="t('scrapStockOut')" width="500px" append-to-body draggable align-center class="scrap-out-dialog">
      <!-- 扫码报废 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Aim /></el-icon>
          <span>{{ t('scrapScanSection') }}</span>
        </div>
        <div class="section-action-bar">
          <el-button type="danger" @click="openScrapOutScanDialog">
            <el-icon><Aim /></el-icon>
            {{ t('scrapScanGunStockOut') }}
          </el-button>
          <span class="action-tip">{{ t('scrapScanGunStockOutTip') }}</span>
        </div>
      </div>

      <!-- 手动报废 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Delete /></el-icon>
          <span>{{ t('scrapManualOutSection') }}</span>
        </div>
        <el-form :model="scrapOutForm" label-width="80px" size="default">
          <el-form-item :label="t('scrapPartsLabel')">
            <el-input :value="currentScrapOutPart?.name" disabled />
          </el-form-item>
          <el-form-item :label="t('spareSerialNumber')" required>
            <el-input v-model="scrapOutForm.serial_number" :placeholder="t('scrapSerialOutPlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('spareStockOutReason')" required>
            <el-input v-model="scrapOutForm.reason" type="textarea" :rows="2" :placeholder="t('scrapOutReasonPlaceholder')" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="scrapOutDialogVisible = false">{{ t('actionCancel') }}</el-button>
        <el-button type="danger" @click="submitScrapOut" :loading="scrapOutSubmitting" :disabled="!scrapOutForm.serial_number || !scrapOutForm.reason">
          {{ t('spareConfirmOut') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 报废出库扫码对话框 -->
    <el-dialog v-model="scrapOutScanDialogVisible" :title="t('scrapScanStockOutTitle')" width="700px">
      <ScanSession
        ref="scrapOutScanSessionRef"
        default-type="scrap_out"
        :auto-start="scrapOutScanDialogVisible"
        @complete="onScrapOutScanComplete"
        @cancel="scrapOutScanDialogVisible = false"
      />
    </el-dialog>

    <!-- 新增/编辑报废物料对话框 -->
    <el-dialog v-model="editScrapDialogVisible" :title="isEditScrap ? t('scrapEditDialogTitle') : t('scrapAddMaterial')" width="600px" append-to-body draggable align-center>
      <el-form :model="editScrapForm" label-width="80px" size="default">
        <el-form-item :label="t('spareName')">
          <el-input v-model="editScrapForm.name" />
        </el-form-item>
        <el-form-item :label="t('sparePartNumber')">
          <el-input v-model="editScrapForm.part_number" />
        </el-form-item>
        <el-form-item :label="t('spareSerialNumber')">
          <el-input v-model="editScrapForm.serial_number" :placeholder="t('spareSearchSerialPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('spareUnitPrice')">
          <div class="price-input-row">
            <el-input-number v-model="editScrapForm.unit_price" :min="0" :precision="2" style="width: 140px" />
            <span class="unit-text">¥</span>
          </div>
        </el-form-item>
        <el-form-item :label="t('scrapScrapReason')">
          <el-input v-model="editScrapForm.reason" type="textarea" :rows="2" :placeholder="t('scrapScrapReasonPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('scrapRelatedMaintenance')">
          <el-input v-model="editScrapForm.reference" :placeholder="t('scrapReferenceMaintenanceNo')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editScrapDialogVisible = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitEditScrap" :loading="editScrapSubmitting">{{ t('actionSave') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Aim, Document, Clock, Collection, Box, Wallet, Calendar, Warning, Search, ArrowRight, Download, Upload, Edit, Delete, Plus, Minus } from '@element-plus/icons-vue'
import { getPartList, createMovement, getMovements, getPartBySerialNumber, updateMovement, deleteMovement } from '@/api'
import { formatDateTime } from '@/utils/time'
import ScanSession from '@/components/ScanSession.vue'
import { useI18n } from '@/composables/useI18n'
import { clearCache } from '@/utils/cache.js'

const { t } = useI18n()

// 状态
const activeTab = ref('scrap')
const scrapItems = ref([])  // 按备件分组的报废库存
const loading = ref(false)
const search = ref('')
const category = ref('')

// 统计
const stats = reactive({
  total_types: 0,
  total_quantity: 0,
  total_value: 0,
  month_count: 0
})

// 报废历史
const historyItems = ref([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyTotal = ref(0)

// 详情对话框
const detailDialogVisible = ref(false)
const currentScrapItem = ref(null)

// 扫码录入
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)
const scanItems = ref([])
const submitting = ref(false)

// 手动录入
const manualDialogVisible = ref(false)
const searchingSerial = ref(false)
const foundPartInfo = ref(null)
const partOptions = ref([])
const manualForm = reactive({
  serial_number: '',
  part_id: null,
  part_number_manual: '',
  name_manual: '',
  unit_price: 0,
  reason: '',
  reference: ''
})

// 手动入库
const manualInDialogVisible = ref(false)
const currentManualPart = ref(null)
const manualInSubmitting = ref(false)
const manualInForm = reactive({
  serial_number: '',
  unit_price: 0,
  reason: '',
  reference: ''
})

// 报废出库
const scrapOutDialogVisible = ref(false)
const currentScrapOutPart = ref(null)
const scrapOutSubmitting = ref(false)
const scrapOutForm = reactive({
  serial_number: '',
  reason: ''
})

// 报废出库扫码
const scrapOutScanDialogVisible = ref(false)
const scrapOutScanSessionRef = ref(null)

// 报废入库扫码
const scrapInScanDialogVisible = ref(false)
const scrapInScanSessionRef = ref(null)
const scrapInScanItems = ref([])

// 编辑报废物料
const editScrapDialogVisible = ref(false)
const isEditScrap = ref(false)
const editScrapSubmitting = ref(false)
const editScrapPartId = ref(null)
const editScrapForm = reactive({
  name: '',
  part_number: '',
  serial_number: '',
  unit_price: 0,
  reason: '',
  reference: '',
  movement_id: null
})

// 共享的报废数据缓存
const scrapInMovementsCache = ref([])
const scrapOutMovementsCache = ref([])

// 加载所有报废数据（共享给库存和历史两个Tab）
const loadAllMovements = async () => {
  const scrapInResult = await getMovements({ movement_type: 'scrap_in', limit: 200 })
  const scrapOutResult = await getMovements({ movement_type: 'scrap_out', limit: 200 })
  scrapInMovementsCache.value = scrapInResult.items || []
  scrapOutMovementsCache.value = scrapOutResult.items || []
  return {
    scrapIn: scrapInMovementsCache.value,
    scrapOut: scrapOutMovementsCache.value
  }
}

// 加载报废库存（按序列号跟踪有序列号的，按数量跟踪无序列号的）
const loadScrapItems = async (force = false) => {
  loading.value = true
  try {
    // 加载所有数据（同时更新缓存）
    const { scrapIn: scrapInMovements, scrapOut: scrapOutMovements } = await loadAllMovements()

    // 按序列号跟踪有序列号的入库
    const scrapInBySerial = {}  // 序列号 -> 入库记录
    const scrapOutSerials = new Set()  // 已报废出库的序列号集合

    // 按备件跟踪无序列号的数量
    const scrapInByPart = {}  // part_id -> { quantity, item }
    const scrapOutByPart = {}  // part_id -> 出库数量

    scrapInMovements.forEach(item => {
      if (item.serial_number) {
        scrapInBySerial[item.serial_number] = item
      } else {
        // 无序列号的按备件ID统计数量
        const partKey = item.part_id || `unknown_${item.part_number || 'unknown'}`
        if (!scrapInByPart[partKey]) {
          scrapInByPart[partKey] = { quantity: 0, item: item }
        }
        scrapInByPart[partKey].quantity += item.quantity
      }
    })

    scrapOutMovements.forEach(item => {
      if (item.serial_number) {
        scrapOutSerials.add(item.serial_number)
      } else {
        // 无序列号的按备件ID统计数量
        const partKey = item.part_id || `unknown_${item.part_number || 'unknown'}`
        scrapOutByPart[partKey] = (scrapOutByPart[partKey] || 0) + item.quantity
      }
    })

    // 当前报废库存（有序列号的）= 报废入库序列号 - 报废出库序列号
    const currentScrapSerials = Object.keys(scrapInBySerial).filter(
      serial => !scrapOutSerials.has(serial)
    )

    // 按备件分组显示当前报废库存
    const groupedMap = {}

    // 处理有序列号的报废库存
    currentScrapSerials.forEach(serial => {
      const item = scrapInBySerial[serial]
      const key = item.part_id || `unknown_${item.part_number || 'unknown'}`
      if (!groupedMap[key]) {
        groupedMap[key] = {
          part_id: item.part_id,
          name: item.name || item.part_number || t('scanUnknown'),
          part_number: item.part_number || t('scanUnknown'),
          manufacturer: '',
          unit_price: item.unit_price || 0,
          quantity: 0,
          total_value: 0,
          instances: []
        }
      }
      groupedMap[key].quantity += 1
      groupedMap[key].total_value += (item.unit_price || 0)
      groupedMap[key].instances.push({
        serial_number: serial,
        po_number: item.po_number,
        unit_price: item.unit_price,
        scraped_at: item.created_at,
        movement_type: 'scrap_in',
        reason: item.reason,
        reference: item.reference,
        source_device_name: item.source_device_name,
        removed_from_device_id: item.source_device_id,
        movement_id: item.id  // 保存movement_id用于编辑/删除
      })
    })

    // 处理无序列号的报废库存（按数量计算）
    Object.keys(scrapInByPart).forEach(partKey => {
      const inData = scrapInByPart[partKey]
      const inQty = inData.quantity || 0
      const outQty = scrapOutByPart[partKey] || 0
      const netQty = inQty - outQty

      if (netQty > 0) {
        const inRecord = inData.item
        if (!groupedMap[partKey]) {
          groupedMap[partKey] = {
            part_id: inRecord?.part_id,
            name: inRecord?.name || inRecord?.part_number || t('scanUnknown'),
            part_number: inRecord?.part_number || t('scanUnknown'),
            manufacturer: '',
            unit_price: inRecord?.unit_price || 0,
            quantity: 0,
            total_value: 0,
            instances: []
          }
        }
        groupedMap[partKey].quantity += netQty
        groupedMap[partKey].total_value += netQty * (inRecord?.unit_price || 0)
        groupedMap[partKey].noSerialCount = netQty
      }
    })

    // 应用筛选
    let items = Object.values(groupedMap)
    if (search.value) {
      const searchLower = search.value.toLowerCase()
      items = items.filter(item =>
        item.name.toLowerCase().includes(searchLower) ||
        item.part_number.toLowerCase().includes(searchLower)
      )
    }
    if (category.value) {
      items = items.filter(item => {
        // 这里需要根据备件的category过滤，但报废记录没有直接带category
        // 暂时不实现分类筛选
        return true
      })
    }

    scrapItems.value = items
    updateStats(scrapInMovements, scrapOutMovements)

    // 同时更新历史数据（从缓存）
    updateHistoryFromCache()
  } catch (e) {
    ElMessage.error(t('scrapLoadFailed') + '：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// 从缓存更新历史数据
const updateHistoryFromCache = () => {
  const allRecords = [...scrapInMovementsCache.value, ...scrapOutMovementsCache.value]
  allRecords.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  const start = (historyPage.value - 1) * 50
  historyItems.value = allRecords.slice(start, start + 50)
  historyTotal.value = allRecords.length
}

// 更新统计（基于净库存）
const updateStats = (scrapInMovements, scrapOutMovements) => {
  stats.total_types = scrapItems.value.length
  stats.total_quantity = scrapItems.value.reduce((sum, item) => sum + item.quantity, 0)
  stats.total_value = scrapItems.value.reduce((sum, item) => sum + item.total_value, 0)

  // 本月新增（报废入库）
  const now = new Date()
  const thisMonth = now.getMonth()
  const thisYear = now.getFullYear()
  stats.month_count = scrapInMovements.filter(item => {
    const itemDate = new Date(item.created_at)
    return itemDate.getMonth() === thisMonth && itemDate.getFullYear() === thisYear
  }).length
}

// 加载报废历史（使用缓存，避免重复请求）
const loadHistory = async (force = false) => {
  historyLoading.value = true
  try {
    // 如果强制刷新或缓存为空，调用 loadScrapItems（它会填充缓存）
    if (force || scrapInMovementsCache.value.length === 0) {
      await loadScrapItems(force)
    } else {
      // 直接从缓存更新
      updateHistoryFromCache()
    }
  } catch (e) {
    if (e.name !== 'CanceledError') {
      ElMessage.error(t('scrapHistoryLoadFailed'))
    }
  } finally {
    historyLoading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  search.value = ''
  category.value = ''
  loadScrapItems(true)
}

// 显示报废详情（该备件的报废入库和出库历史）
// 显示报废详情（当前在报废库中的实例）
const showScrapDetail = (row) => {
  currentScrapItem.value = row
  detailDialogVisible.value = true
}

// 显示扫码对话框
const showScanDialog = () => {
  scanItems.value = []
  scanDialogVisible.value = true
}

// 扫码会话完成
const onScanSessionComplete = async (result) => {
  scanItems.value = result.items || []
  if (scanItems.value.length > 0) {
    ElMessage.success(t('scrapScannedItems', { count: scanItems.value.length }))
  }
}

// 提交扫码录入
const submitScrapFromScan = async () => {
  if (scanItems.value.length === 0) return

  submitting.value = true
  try {
    for (const item of scanItems.value) {
      if (item.part_id) {
        await createMovement({
          part_id: item.part_id,
          movement_type: 'scrap_in',
          quantity: 1,
          serial_number: item.serial_number,
          reason: item.notes || t('scrapScrapIn'),
          reference: ''
        })
      }
    }
    clearCache('scrap_in_movements')
    clearCache('scrap_out_movements')
    ElMessage.success(t('scrapScrapInItems', { count: scanItems.value.length }))
    scanDialogVisible.value = false
    loadScrapItems(true)
    loadHistory(true)
  } catch (e) {
    ElMessage.error(t('scrapScrapInFailed') + '：' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

// 显示手动录入对话框
const showManualDialog = async () => {
  const result = await getPartList({ limit: 100 })
  partOptions.value = result.items || []

  Object.assign(manualForm, {
    serial_number: '',
    part_id: null,
    part_number_manual: '',
    name_manual: '',
    unit_price: 0,
    reason: '',
    reference: ''
  })
  foundPartInfo.value = null
  manualDialogVisible.value = true
}

// 查询序列号
const searchSerialForScrap = async () => {
  if (!manualForm.serial_number) {
    ElMessage.warning(t('msgEnterRequired'))
    return
  }

  searchingSerial.value = true
  try {
    const result = await getPartBySerialNumber(manualForm.serial_number)
    foundPartInfo.value = result
    manualForm.part_id = result.id
    manualForm.unit_price = result.unit_price || 0
    ElMessage.success(t('scrapRecognized') + ': ' + (result.name || result.part_number))
  } catch (e) {
    foundPartInfo.value = null
    ElMessage.info(t('scrapSerialNotFound'))
  } finally {
    searchingSerial.value = false
  }
}

// 选择备件型号
const onPartSelect = () => {
  if (!manualForm.part_id) return
  const part = partOptions.value.find(p => p.id === manualForm.part_id)
  if (part) {
    manualForm.part_number_manual = part.part_number
    manualForm.name_manual = part.name || part.part_number
    manualForm.unit_price = part.unit_price || 0
  }
}

// 提交手动报废
const submitManualScrap = async () => {
  if (!manualForm.serial_number) {
    ElMessage.warning(t('msgEnterRequired'))
    return
  }
  if (!manualForm.reason) {
    ElMessage.warning(t('scrapFillReason'))
    return
  }

  submitting.value = true
  try {
    let partId = manualForm.part_id

    if (foundPartInfo.value) {
      partId = foundPartInfo.value.id
    }

    if (!partId) {
      ElMessage.warning(t('scrapSelectPartNumber'))
      submitting.value = false
      return
    }

    await createMovement({
      part_id: partId,
      movement_type: 'scrap_in',
      quantity: 1,
      serial_number: manualForm.serial_number,
      reason: manualForm.reason,
      reference: manualForm.reference
    })

    clearCache('scrap_in_movements')
    clearCache('scrap_out_movements')
    ElMessage.success(t('scrapScrapInSuccess'))
    manualDialogVisible.value = false
    loadScrapItems(true)
    loadHistory(true)
  } catch (e) {
    ElMessage.error(t('scrapScrapInFailed') + '：' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

// 显示入库对话框
const showInDialog = (row) => {
  currentManualPart.value = row
  Object.assign(manualInForm, {
    serial_number: '',
    unit_price: row.unit_price || 0,
    reason: '',
    reference: ''
  })
  manualInDialogVisible.value = true
}

// 提交手动入库
const submitManualIn = async () => {
  if (!manualInForm.serial_number) {
    ElMessage.warning(t('msgEnterRequired'))
    return
  }

  manualInSubmitting.value = true
  try {
    await createMovement({
      part_id: currentManualPart.value.part_id,
      movement_type: 'scrap_in',
      quantity: 1,
      serial_number: manualInForm.serial_number,
      reason: manualInForm.reason || t('scrapScrapIn'),
      reference: manualInForm.reference
    })
    clearCache('scrap_in_movements')
    clearCache('scrap_out_movements')
    ElMessage.success(t('scrapScrapInSuccess'))
    manualInDialogVisible.value = false
    loadScrapItems(true)
    loadHistory(true)
  } catch (e) {
    ElMessage.error(t('scrapStockInFailed') + '：' + (e.response?.data?.detail || e.message))
  } finally {
    manualInSubmitting.value = false
  }
}

// 显示报废出库对话框
const showScrapOutDialog = (row) => {
  currentScrapOutPart.value = row
  Object.assign(scrapOutForm, {
    serial_number: '',
    reason: ''
  })
  scrapOutDialogVisible.value = true
}

// 提交报废出库
const submitScrapOut = async () => {
  if (!scrapOutForm.serial_number) {
    ElMessage.warning(t('msgEnterRequired'))
    return
  }
  if (!scrapOutForm.reason) {
    ElMessage.warning(t('scrapFillOutReason'))
    return
  }

  scrapOutSubmitting.value = true
  try {
    // 先验证序列号是否在报废库存中
    const scrapInResult = await getMovements({
      movement_type: 'scrap_in',
      keyword: scrapOutForm.serial_number,
      limit: 1
    })
    const scrapOutResult = await getMovements({
      movement_type: 'scrap_out',
      keyword: scrapOutForm.serial_number,
      limit: 1
    })

    const hasScrapIn = scrapInResult.items?.some(
      item => item.serial_number === scrapOutForm.serial_number
    )
    const hasScrapOut = scrapOutResult.items?.some(
      item => item.serial_number === scrapOutForm.serial_number
    )

    if (!hasScrapIn) {
      ElMessage.warning(t('scrapSerialNotInScrap'))
      scrapOutSubmitting.value = false
      return
    }
    if (hasScrapOut) {
      ElMessage.warning(t('scrapSerialAlreadyOut'))
      scrapOutSubmitting.value = false
      return
    }

    // 验证通过，提交报废出库
    await createMovement({
      part_id: currentScrapOutPart.value.part_id,
      movement_type: 'scrap_out',
      quantity: 1,
      serial_number: scrapOutForm.serial_number,
      reason: scrapOutForm.reason,
      reference: ''
    })
    clearCache('scrap_in_movements')
    clearCache('scrap_out_movements')
    ElMessage.success(t('scrapScrapOutSuccess'))
    scrapOutDialogVisible.value = false
    loadScrapItems(true)
    loadHistory(true)
  } catch (e) {
    ElMessage.error(t('scrapStockOutFailed') + '：' + (e.response?.data?.detail || e.message))
  } finally {
    scrapOutSubmitting.value = false
  }
}

// 打开报废出库扫码对话框
const openScrapOutScanDialog = () => {
  scrapOutScanDialogVisible.value = true
}

// 报废出库扫码会话完成（后端已验证并创建出库记录）
const onScrapOutScanComplete = async (result) => {
  const scrapOutCount = result.scrap_out_count || 0
  const invalidItems = result.invalid_items || []

  if (scrapOutCount === 0 && invalidItems.length === 0) {
    ElMessage.warning(t('scrapNoSerialScanned'))
    return
  }

  if (invalidItems.length > 0) {
    const invalidMsg = invalidItems.map(i => `${i.serial_number}: ${i.reason}`).join('\n')
    ElMessage.warning(t('scrapSerialsNotInStock') + ':\n' + invalidMsg)
  }

  if (scrapOutCount > 0) {
    clearCache('scrap_in_movements')
    clearCache('scrap_out_movements')
    ElMessage.success(t('scrapScrapOutItems', { count: scrapOutCount }))
  }

  scrapOutScanDialogVisible.value = false
  scrapOutDialogVisible.value = false
  loadScrapItems(true)
  loadHistory(true)
}

// 打开报废入库扫码对话框
const openScrapInScanDialog = () => {
  scrapInScanDialogVisible.value = true
}

// 报废入库扫码会话完成
const onScrapInScanComplete = async (result) => {
  const itemCount = result.scrap_in_count || (result.items?.length || 0)
  if (itemCount === 0) {
    ElMessage.warning(t('scrapNoSerialScanned'))
    return
  }

  clearCache('scrap_in_movements')
  clearCache('scrap_out_movements')
  ElMessage.success(t('scrapScrapInItems', { count: itemCount }))
  scrapInScanDialogVisible.value = false
  manualInDialogVisible.value = false
  loadScrapItems(true)
  loadHistory(true)
}

// 显示新增报废物料对话框
const showAddScrapDialog = async () => {
  const result = await getPartList({ limit: 100 })
  partOptions.value = result.items || []

  isEditScrap.value = false
  Object.assign(editScrapForm, {
    name: '',
    part_number: '',
    serial_number: '',
    unit_price: 0,
    reason: '',
    reference: ''
  })
  editScrapPartId.value = null
  editScrapDialogVisible.value = true
}

// 显示编辑报废物料对话框
const showEditScrapDialog = (row) => {
  // 取第一个实例进行编辑
  const instance = row.instances?.[0]
  if (!instance) {
    ElMessage.warning(t('scrapNoScrapStock'))
    return
  }

  isEditScrap.value = true
  editScrapPartId.value = row.part_id

  Object.assign(editScrapForm, {
    name: row.name,
    part_number: row.part_number,
    serial_number: instance.serial_number || '',
    unit_price: instance.unit_price || 0,
    reason: instance.reason || '',
    reference: instance.reference || '',
    movement_id: instance.movement_id || null
  })

  editScrapDialogVisible.value = true
}

// 提交编辑报废物料
const submitEditScrap = async () => {
  if (!editScrapForm.serial_number) {
    ElMessage.warning(t('msgEnterRequired') + t('spareSerialNumber'))
    return
  }

  editScrapSubmitting.value = true
  try {
    // 使用存储的movement_id或重新查找
    let movementId = editScrapForm.movement_id

    if (!movementId) {
      const scrapInResult = await getMovements({
        movement_type: 'scrap_in',
        keyword: editScrapForm.serial_number,
        limit: 1
      })
      const movement = scrapInResult.items?.find(
        m => m.serial_number === editScrapForm.serial_number
      )
      movementId = movement?.id
    }

    if (!movementId) {
      ElMessage.warning(t('scrapSerialNotInScrap'))
      editScrapSubmitting.value = false
      return
    }

    await updateMovement(movementId, {
      reason: editScrapForm.reason,
      reference: editScrapForm.reference,
      unit_price: editScrapForm.unit_price
    })

    clearCache('scrap_in_movements')
    clearCache('scrap_out_movements')
    ElMessage.success(t('scrapEditSuccess'))
    editScrapDialogVisible.value = false
    loadScrapItems(true)
    loadHistory(true)
  } catch (e) {
    ElMessage.error(t('scrapEditFailed') + '：' + (e.response?.data?.detail || e.message))
  } finally {
    editScrapSubmitting.value = false
  }
}

// 删除报废物料
const handleDeleteScrap = async (row) => {
  const instance = row.instances?.[0]
  if (!instance) {
    ElMessage.warning(t('scrapNoScrapStock'))
    return
  }

  try {
    await ElMessageBox.confirm(
      t('scrapDeleteConfirm'),
      t('msgConfirm'),
      { type: 'warning' }
    )

    // 使用存储的movement_id或重新查找
    let movementId = instance.movement_id

    if (!movementId) {
      const scrapInResult = await getMovements({
        movement_type: 'scrap_in',
        keyword: instance.serial_number,
        limit: 1
      })
      const movement = scrapInResult.items?.find(
        m => m.serial_number === instance.serial_number
      )
      movementId = movement?.id
    }

    if (!movementId) {
      ElMessage.warning(t('scrapSerialNotInScrap'))
      return
    }

    await deleteMovement(movementId)

    clearCache('scrap_in_movements')
    clearCache('scrap_out_movements')
    ElMessage.success(t('scrapDeleteSuccess'))
    loadScrapItems(true)
    loadHistory(true)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(t('scrapDeleteFailed') + '：' + (e.response?.data?.detail || e.message))
    }
  }
}

onMounted(() => {
  // 只调用一次加载，loadScrapItems 会填充缓存，loadHistory 会使用缓存
  loadScrapItems()
})
</script>

<style scoped>
/* 字体清晰度优化 - 所有等宽字体 */
.metric-value,
.chip-count,
.table-count,
.part-number-text,
.serial-text,
.quantity-value,
.price-value,
.price-currency,
.time-text {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* ===== 页面整体背景 ===== */
.scrap-page {
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
  background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894);
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
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
  color: white;
  border: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(9, 132, 227, 0.25);
}

.nav-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(9, 132, 227, 0.35);
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

.nav-action-btn.primary {
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.25);
}

.nav-action-btn.primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 184, 148, 0.35);
}

/* ===== Tab 切换 Chips ===== */
.tab-section {
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 12px rgba(0, 48, 135, 0.06);
}

.tab-chips {
  display: flex;
  gap: 8px;
}

.tab-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 10px;
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.tab-chip::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  right: 50%;
  height: 2px;
  background: currentColor;
  transition: all 0.25s ease;
}

.tab-chip:hover::before,
.tab-chip.active::before {
  left: 0;
  right: 0;
}

.tab-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.1);
}

.tab-chip.active {
  background: rgba(9, 132, 227, 0.08);
  border-color: rgba(9, 132, 227, 0.3);
  color: #0984e3;
}

.chip-icon {
  font-size: 14px;
  opacity: 0.8;
}

.chip-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.tab-chip.active .chip-label {
  color: #0984e3;
}

.chip-count {
  font-size: 11px;
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--text-tertiary);
  padding: 2px 8px;
  background: rgba(0, 48, 135, 0.05);
  border-radius: 6px;
}

.tab-chip.chip-history:hover {
  background: rgba(0, 184, 148, 0.08);
  border-color: rgba(0, 184, 148, 0.3);
}

.tab-chip.chip-history.active {
  background: rgba(0, 184, 148, 0.12);
  border-color: rgba(0, 184, 148, 0.4);
  color: #00b894;
}

.tab-chip.chip-history.active .chip-label {
  color: #00b894;
}

/* ===== 内容区域 ===== */
.scrap-content,
.history-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  cursor: default;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(9, 132, 227, 0.05) 100%);
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

.stat-card.types .card-icon {
  background: linear-gradient(135deg, rgba(9, 132, 227, 0.15) 0%, rgba(9, 132, 227, 0.08) 100%);
  color: #0984e3;
}
.stat-card.quantity .card-icon {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(239, 68, 68, 0.1) 100%);
  color: #ef4444;
}
.stat-card.value .card-icon {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.2) 0%, rgba(251, 191, 36, 0.1) 100%);
  color: #f59e0b;
}
.stat-card.month .card-icon {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.2) 0%, rgba(0, 184, 148, 0.1) 100%);
  color: #00b894;
}

.card-body { flex: 1; }

.metric-value {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
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

.card-trend.stable { background: rgba(9, 132, 227, 0.1); color: #0984e3; }
.card-trend.warning { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

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
  box-shadow: 0 0 0 3px rgba(9, 132, 227, 0.15);
}

.filter-selects {
  display: flex;
  gap: 8px;
}

.filter-selects :deep(.el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  box-shadow: none;
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  border: 1px solid var(--border-default);
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-secondary);
}

.filter-btn:hover {
  transform: translateY(-1px);
}

.filter-btn.primary {
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
  color: white;
  border: none;
  box-shadow: 0 2px 8px rgba(9, 132, 227, 0.25);
}

.filter-btn.primary:hover {
  box-shadow: 0 4px 16px rgba(9, 132, 227, 0.35);
}

.filter-btn.secondary:hover {
  background: var(--bg-hover);
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}

/* ===== 数据面板 ===== */
.data-section {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
  overflow: hidden;
}

/* 表格表头居中 */
:deep(.el-table th.el-table__cell) {
  text-align: center;
}

/* 操作按钮区域 */
.table-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  justify-content: center;
}

.table-actions .el-button {
  padding: 5px 10px;
  font-size: 12px;
}

.text-muted {
  color: var(--text-tertiary);
}

/* 分页 */
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
  background: linear-gradient(135deg, #0984e3, #74b9ff);
  border-color: transparent;
  color: white;
}

/* ===== 对话框样式 ===== */
.compact-header {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-md);
  padding: var(--gap-sm) var(--gap-md);
  background: rgba(0, 48, 135, 0.04);
  border-radius: 8px;
  font-size: 13px;
  border: 1px solid rgba(0, 48, 135, 0.08);
}

.compact-header strong {
  font-weight: 600;
}

.text-primary {
  color: var(--accent-primary);
  font-weight: 500;
}

.text-success {
  color: #00b894;
  font-weight: 600;
}

.text-danger {
  color: var(--accent-danger);
  font-weight: 600;
}

.scrap-in-scan-btn,
.scrap-out-scan-btn {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.scrap-out-scan-tip {
  font-size: 12px;
  color: #ef4444;
  padding: 8px 12px;
  background: rgba(239, 68, 68, 0.08);
  border-radius: 6px;
  border: 1px solid rgba(239, 68, 68, 0.15);
}

.scrap-out-manual {
  margin-top: var(--gap-md);
}

.manual-title {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: var(--gap-sm);
  font-weight: 500;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-actions {
    margin-left: 0;
    justify-content: center;
  }

  .page-nav-bar {
    flex-direction: column;
    gap: 12px;
  }

  .nav-right {
    width: 100%;
    justify-content: center;
  }

  .tab-chips {
    justify-content: center;
  }
}

/* ===== 暗黑模式 ===== */
.dark .scrap-page {
  background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #161b22 100%);
}

.dark .page-nav-bar {
  background: rgba(22, 27, 34, 0.9);
  border-color: rgba(48, 54, 61, 0.8);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .page-nav-bar::before {
  background: linear-gradient(90deg, #0984e3, #74b9ff, #00b894);
}

.dark .page-title {
  color: #f0f6fc;
}

.dark .nav-action-btn.secondary {
  background: rgba(48, 54, 61, 0.8);
  color: #8b949e;
  border-color: #30363d;
}

.dark .nav-action-btn.secondary:hover {
  background: rgba(9, 132, 227, 0.15);
  border-color: #0984e3;
  color: #58a6ff;
}

.dark .nav-action-btn.primary {
  background: linear-gradient(135deg, rgba(63, 185, 80, 0.9) 0%, rgba(85, 239, 196, 0.9) 100%);
  box-shadow: 0 2px 8px rgba(63, 185, 80, 0.25);
}

.dark .nav-action-btn.primary:hover {
  box-shadow: 0 4px 16px rgba(63, 185, 80, 0.35);
}

.dark .tab-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.dark .tab-chip {
  background: rgba(13, 17, 23, 0.9);
  border-color: #30363d;
}

.dark .tab-chip:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .chip-label {
  color: #8b949e;
}

.dark .tab-chip.active {
  background: rgba(88, 166, 255, 0.15);
  border-color: rgba(88, 166, 255, 0.4);
  color: #58a6ff;
}

.dark .tab-chip.active .chip-label {
  color: #58a6ff;
}

.dark .chip-count {
  background: rgba(48, 54, 61, 0.3);
  color: #8b949e;
}

.dark .tab-chip.chip-history:hover {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.4);
}

.dark .tab-chip.chip-history.active {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}

.dark .tab-chip.chip-history.active .chip-label {
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

.dark .card-trend.stable { background: rgba(9, 132, 227, 0.2); color: #58a6ff; }
.dark .card-trend.warning { background: rgba(239, 68, 68, 0.2); color: #f85149; }

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
  border-color: #58a6ff;
  box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
}

.dark .search-icon {
  color: #8b949e;
}

.dark .filter-selects :deep(.el-select .el-input__wrapper) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

.dark .filter-btn {
  background: rgba(13, 17, 23, 0.9);
  border-color: #30363d;
  color: #8b949e;
}

.dark .filter-btn.secondary:hover {
  background: rgba(88, 166, 255, 0.15);
  border-color: rgba(88, 166, 255, 0.3);
  color: #58a6ff;
}

.dark .data-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.4);
}

.dark .table-header {
  border-bottom-color: rgba(48, 54, 61, 0.6);
}

.dark .table-title {
  color: #8b949e;
}

.dark .table-count {
  color: #6e7681;
}

.dark .refresh-btn {
  background: rgba(13, 17, 23, 0.9);
  border-color: #30363d;
  color: #8b949e;
}

.dark .refresh-btn:hover {
  background: rgba(88, 166, 255, 0.15);
  border-color: rgba(88, 166, 255, 0.3);
  color: #58a6ff;
}

.dark .enterprise-table :deep(.el-table__header-wrapper) {
  border-bottom-color: rgba(48, 54, 61, 0.6);
}

.dark .enterprise-table :deep(th.el-table__cell) {
  color: #8b949e;
}

.dark .enterprise-table :deep(td.el-table__cell) {
  border-bottom-color: rgba(48, 54, 61, 0.3);
}

.dark .enterprise-table :deep(.el-table__row:hover > td) {
  background: rgba(88, 166, 255, 0.08) !important;
}

.dark .name-link {
  color: #58a6ff;
}

.dark .name-badge {
  background: rgba(88, 166, 255, 0.15);
}

.dark .name-link:hover .name-badge {
  background: rgba(88, 166, 255, 0.25);
}

.dark .part-number-text,
.dark .name-text,
.dark .device-text {
  color: #8b949e;
}

.dark .serial-text {
  color: #58a6ff;
}

.dark .quantity-badge.danger {
  background: rgba(248, 81, 73, 0.15);
  color: #f85149;
}

.dark .price-value {
  color: #8b949e;
}

.dark .time-text {
  color: #8b949e;
}

.dark .type-badge {
  background: rgba(13, 17, 23, 0.9);
}

.dark .type-badge.in {
  border-color: rgba(210, 153, 34, 0.4);
  color: #d29922;
}
.dark .type-badge.in .type-dot { background: #d29922; }

.dark .type-badge.out {
  border-color: rgba(248, 81, 73, 0.4);
  color: #f85149;
}
.dark .type-badge.out .type-dot { background: #f85149; }

.dark .enterprise-table :deep(.el-button--success) {
  background: linear-gradient(135deg, rgba(63, 185, 80, 0.9) 0%, rgba(85, 239, 196, 0.9) 100%);
}

.dark .enterprise-table :deep(.el-button--danger) {
  background: linear-gradient(135deg, rgba(248, 81, 73, 0.9) 0%, rgba(248, 81, 73, 0.9) 100%);
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
  background: linear-gradient(135deg, #0984e3, #74b9ff);
  color: white;
}

.dark .compact-header {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .scrap-out-scan-tip {
  background: rgba(248, 81, 73, 0.15);
  border-color: rgba(248, 81, 73, 0.3);
  color: #f85149;
}

.dark .manual-title {
  color: #8b949e;
}

/* ===== 入库/报废出库对话框样式 ===== */
.scrap-in-dialog .form-section,
.scrap-out-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}
.scrap-in-dialog .section-header,
.scrap-out-dialog .section-header {
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
.scrap-in-dialog .section-header .el-icon,
.scrap-out-dialog .section-header .el-icon {
  color: var(--accent-primary);
}
.scrap-in-dialog .section-action-bar,
.scrap-out-dialog .section-action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.scrap-in-dialog .action-tip,
.scrap-out-dialog .action-tip {
  font-size: 12px;
  color: var(--text-tertiary);
}
.scrap-in-dialog .unit-text,
.scrap-out-dialog .unit-text {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: 4px;
}
.scrap-in-dialog .el-form-item,
.scrap-out-dialog .el-form-item {
  margin-bottom: 10px;
}

/* 价格输入行样式 */
.price-input-row {
  display: flex;
  align-items: center;
  width: 100%;
}

.price-input-row .unit-text {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: 8px;
  flex-shrink: 0;
}

/* 暗黑模式 */
.dark .scrap-in-dialog .form-section,
.dark .scrap-out-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}
.dark .scrap-in-dialog .section-header,
.dark .scrap-out-dialog .section-header {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}
.dark .scrap-in-dialog .section-header .el-icon,
.dark .scrap-out-dialog .section-header .el-icon {
  color: #58a6ff;
}
.dark .scrap-in-dialog .action-tip,
.dark .scrap-out-dialog .action-tip {
  color: #6e7681;
}
</style>
