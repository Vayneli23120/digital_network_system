<template>
  <div class="scrap-inventory">
    <el-tabs v-model="activeTab">
      <!-- 报废库存 Tab -->
      <el-tab-pane :label="t('scrapTabLabel')" name="scrap">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>{{ t('scrapManagement') }}</span>
            </div>
          </template>

          <!-- 统计卡片 -->
          <el-row :gutter="16" class="stats-row">
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <el-statistic :title="t('scrapTypes')" :value="stats.total_types" />
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <el-statistic :title="t('scrapTotalCount')" :value="stats.total_quantity" />
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <el-statistic :title="t('scrapTotalValue')" :value="stats.total_value" :precision="2" />
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <el-statistic :title="t('scrapMonthNew')" :value="stats.month_count" />
              </el-card>
            </el-col>
          </el-row>

          <!-- 筛选工具栏 -->
          <div class="toolbar">
            <div class="toolbar-left">
              <el-input
                v-model="search"
                :placeholder="t('spareSearchPlaceholder')"
                clearable
                class="search-input"
                @keyup.enter="loadScrapItems"
                @clear="loadScrapItems"
              />
              <el-select v-model="category" :placeholder="t('spareCategory')" clearable class="category-select" @change="loadScrapItems">
                <el-option :label="t('spareCategoryModule')" value="module" />
                <el-option :label="t('spareCategoryPower')" value="power" />
                <el-option :label="t('spareCategoryCable')" value="cable" />
                <el-option :label="t('spareCategoryOther')" value="other" />
              </el-select>
            </div>
            <div class="toolbar-right">
              <el-button size="small" @click="resetFilters">{{ t('actionReset') }}</el-button>
              <el-button size="small" type="primary" @click="loadScrapItems">{{ t('actionSearch') }}</el-button>
            </div>
          </div>

          <!-- 表格 - 按备件类型分组 -->
          <el-table :data="scrapItems" stripe border v-loading="loading">
            <el-table-column prop="name" :label="t('spareName')" width="150">
              <template #default="{ row }">
                <el-button type="primary" link @click="showScrapDetail(row)">
                  {{ row.name }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="part_number" :label="t('sparePartNumber')" width="150" />
            <el-table-column prop="quantity" :label="t('spareQuantity')" width="100">
              <template #default="{ row }">
                <el-tag type="danger">{{ row.quantity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('spareTotalPrice')" width="100">
              <template #default="{ row }">¥{{ row.total_value.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column :label="t('dashAction')" width="160" fixed="right">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button size="small" type="success" @click="showInDialog(row)">{{ t('spareStockIn') }}</el-button>
                  <el-button size="small" type="danger" @click="showScrapOutDialog(row)">{{ t('scrapScrap') }}</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 报废历史 Tab -->
      <el-tab-pane :label="t('scrapHistoryTab')" name="history">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>{{ t('scrapHistoryTitle') }}</span>
              <el-button @click="loadHistory"><el-icon><Refresh /></el-icon> {{ t('toolRefresh') }}</el-button>
            </div>
          </template>
          <el-table :data="historyItems" v-loading="historyLoading" stripe border>
            <el-table-column prop="created_at" :label="t('movementTime')" width="180">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="name" :label="t('scrapPartName')" width="150">
              <template #default="{ row }">{{ row.name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="part_number" :label="t('sparePartNumber')" width="150">
              <template #default="{ row }">{{ row.part_number || '-' }}</template>
            </el-table-column>
            <el-table-column prop="serial_number" :label="t('scrapSerialNumber')" width="150">
              <template #default="{ row }">{{ row.serial_number || '-' }}</template>
            </el-table-column>
            <el-table-column prop="movement_type" :label="t('movementType')" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.movement_type === 'scrap_in' ? 'warning' : 'danger'" size="small">
                  {{ row.movement_type === 'scrap_in' ? t('scrapScrapIn') : t('scrapScrapped') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" :label="t('spareQuantity')" width="80" align="right" />
            <el-table-column :label="t('scrapSourceDevice')" width="120">
              <template #default="{ row }">
                <span v-if="row.source_device_name">{{ row.source_device_name }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="unit_price" :label="t('spareUnitPrice')" width="100">
              <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="reason" :label="t('spareReason')" min-width="150" show-overflow-tooltip />
            <el-table-column prop="reference" :label="t('scrapRelatedMaintenance')" width="120" show-overflow-tooltip />
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
        </el-card>
      </el-tab-pane>
    </el-tabs>

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
    <el-dialog v-model="manualInDialogVisible" :title="t('spareStockIn')" width="500px">
      <!-- 扫码枪入库 -->
      <div class="scrap-in-scan-btn">
        <el-button type="success" @click="openScrapInScanDialog">
          <el-icon><Aim /></el-icon>
          {{ t('scrapScanGunStockIn') }}
        </el-button>
        <div class="scrap-out-scan-tip">{{ t('scrapScanGunTip') }}</div>
      </div>

      <el-divider />

      <!-- 手动输入 -->
      <div class="manual-title">{{ t('scrapManualInputLabel') }}</div>
      <el-form :model="manualInForm" label-width="80px" style="margin-top: 12px">
        <el-form-item :label="t('scrapPartsLabel')">
          <el-input :value="currentManualPart?.name" disabled />
        </el-form-item>
        <el-form-item :label="t('spareSerialNumber')" required>
          <el-input v-model="manualInForm.serial_number" :placeholder="t('scrapSerialScanPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('spareUnitPrice')">
          <el-input-number v-model="manualInForm.unit_price" :min="0" :precision="2" :placeholder="t('spareUnitPrice')" />
        </el-form-item>
        <el-form-item :label="t('scrapScrapReason')">
          <el-input v-model="manualInForm.reason" type="textarea" :placeholder="t('scrapScrapReason')" />
        </el-form-item>
        <el-form-item :label="t('scrapRelatedMaintenance')">
          <el-input v-model="manualInForm.reference" :placeholder="t('scrapReferenceMaintenanceNo')" />
        </el-form-item>
      </el-form>
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
    <el-dialog v-model="scrapOutDialogVisible" :title="t('scrapStockOut')" width="500px">
      <div class="scrap-out-scan-btn">
        <el-button type="danger" @click="openScrapOutScanDialog">
          <el-icon><Aim /></el-icon>
          {{ t('scrapScanGunStockOut') }}
        </el-button>
        <div class="scrap-out-scan-tip">{{ t('scrapScanGunStockOutTip') }}</div>
      </div>

      <el-divider />

      <div class="scrap-out-manual">
        <div class="manual-title">{{ t('scrapManualInputLabel') }}</div>
        <el-form :model="scrapOutForm" label-width="80px">
          <el-form-item :label="t('scrapPartsLabel')">
            <el-input :value="currentScrapOutPart?.name" disabled />
          </el-form-item>
          <el-form-item :label="t('spareSerialNumber')" required>
            <el-input v-model="scrapOutForm.serial_number" :placeholder="t('scrapSerialOutPlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('spareStockOutReason')" required>
            <el-input v-model="scrapOutForm.reason" type="textarea" :placeholder="t('scrapOutReasonPlaceholder')" />
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
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Aim } from '@element-plus/icons-vue'
import { getPartList, createMovement, getMovements, getPartBySerialNumber } from '@/api'
import { formatDateTime } from '@/utils/time'
import ScanSession from '@/components/ScanSession.vue'
import { useI18n } from '@/composables/useI18n'

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

// 加载报废库存（按序列号跟踪有序列号的，按数量跟踪无序列号的）
const loadScrapItems = async () => {
  loading.value = true
  try {
    // 查询所有报废入库和报废出库记录
    const scrapInResult = await getMovements({ movement_type: 'scrap_in', limit: 200 })
    const scrapOutResult = await getMovements({ movement_type: 'scrap_out', limit: 200 })
    const scrapInMovements = scrapInResult.items || []
    const scrapOutMovements = scrapOutResult.items || []

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
        po_number: item.po_number,  // PO号
        unit_price: item.unit_price,
        scraped_at: item.created_at,
        movement_type: 'scrap_in',
        reason: item.reason,
        reference: item.reference,
        source_device_name: item.source_device_name,  // 来源设备名称
        removed_from_device_id: item.source_device_id  // 来源设备ID（备用）
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
        // 无序列号的显示数量（不展开实例）
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

    scrapItems.value = items
    updateStats(scrapInMovements, scrapOutMovements)
  } catch (e) {
    ElMessage.error(t('scrapLoadFailed') + '：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
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

// 加载报废历史（包含报废入库和报废出库）
const loadHistory = async () => {
  historyLoading.value = true
  try {
    // 查询报废入库和报废出库记录
    const scrapInResult = await getMovements({ movement_type: 'scrap_in', limit: 200 })
    const scrapOutResult = await getMovements({ movement_type: 'scrap_out', limit: 200 })
    const allRecords = [...(scrapInResult.items || []), ...(scrapOutResult.items || [])]

    // 按时间排序
    allRecords.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

    // 分页处理
    const start = (historyPage.value - 1) * 50
    historyItems.value = allRecords.slice(start, start + 50)
    historyTotal.value = allRecords.length
  } catch (e) {
    ElMessage.error(t('scrapHistoryLoadFailed'))
  } finally {
    historyLoading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  search.value = ''
  category.value = ''
  loadScrapItems()
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
    ElMessage.success(t('scrapScrapInItems', { count: scanItems.value.length }))
    scanDialogVisible.value = false
    loadScrapItems()
    loadHistory()
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

    ElMessage.success(t('scrapScrapInSuccess'))
    manualDialogVisible.value = false
    loadScrapItems()
    loadHistory()
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
    ElMessage.success(t('scrapScrapInSuccess'))
    manualInDialogVisible.value = false
    loadScrapItems()
    loadHistory()
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
    ElMessage.success(t('scrapScrapOutSuccess'))
    scrapOutDialogVisible.value = false
    loadScrapItems()
    loadHistory()
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
    ElMessage.success(t('scrapScrapOutItems', { count: scrapOutCount }))
  }

  scrapOutScanDialogVisible.value = false
  scrapOutDialogVisible.value = false
  loadScrapItems()
  loadHistory()
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

  ElMessage.success(t('scrapScrapInItems', { count: itemCount }))
  scrapInScanDialogVisible.value = false
  manualInDialogVisible.value = false
  loadScrapItems()
  loadHistory()
}

onMounted(() => {
  loadScrapItems()
  loadHistory()
})
</script>

<style scoped>
.header-buttons {
  display: flex;
  gap: var(--gap-sm);
}
.stats-row {
  margin-bottom: var(--gap-lg);
}
.stat-card {
  text-align: center;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--gap-md);
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  margin-bottom: var(--gap-md);
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}
.search-input {
  width: 200px;
}
.category-select {
  width: 100px;
}
.toolbar-right {
  display: flex;
  gap: var(--gap-sm);
}
.scrap-out-scan-btn {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  margin-bottom: var(--gap-md);
}
.scrap-out-scan-tip {
  font-size: 12px;
  color: var(--accent-danger);
  padding: 4px 8px;
  background: var(--danger-bg);
  border-radius: var(--radius-sm);
}
.scrap-out-manual {
  margin-top: var(--gap-md);
}
.manual-title {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: var(--gap-sm);
}
.compact-header {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-md);
  padding: var(--gap-sm) var(--gap-md);
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  font-size: 13px;
}
.compact-header strong {
  font-weight: 600;
}
.text-primary {
  color: var(--accent-primary);
  font-weight: 500;
}
.text-success {
  color: var(--accent-primary);
  font-weight: 600;
}
.text-danger {
  color: var(--accent-danger);
  font-weight: 600;
}
</style>