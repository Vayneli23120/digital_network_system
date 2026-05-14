<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>{{ t('sparePartsList') }}</span>
      </div>
    </template>

    <!-- 表格 -->
    <el-table :data="parts" stripe border v-loading="loading">
      <el-table-column prop="name" :label="t('spareName')" width="150">
        <template #default="{ row }">
          <el-button type="primary" link @click="$emit('show-detail', row)">
            {{ row.name }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column prop="part_number" :label="t('sparePartNumber')" width="150" />
      <el-table-column prop="category" :label="t('spareCategory')" width="100" />
      <el-table-column prop="manufacturer" :label="t('spareManufacturer')" width="120" />
      <el-table-column prop="quantity_in_stock" :label="t('spareQuantity')" width="100">
        <template #default="{ row }">
          <el-tag :type="row.quantity_in_stock < row.min_quantity ? 'danger' : 'success'">
            {{ row.quantity_in_stock }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="min_quantity" :label="t('spareMinQuantity')" width="100" />
      <el-table-column :label="t('spareTotalPrice')" width="100">
        <template #default="{ row }">¥{{ (row.unit_price * row.quantity_in_stock).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column :label="t('dashAction')" width="160" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button size="small" type="success" @click="showManualInDialog(row)">{{ t('spareStockIn') }}</el-button>
            <el-button size="small" type="warning" @click="showManualOutDialog(row)">{{ t('spareStockOut') }}</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 新增/编辑对话框 -->
  <el-dialog v-model="dialogVisible" :title="isEdit ? t('spareEdit') : t('spareNew')" width="600px" append-to-body draggable align-center>
    <el-form :model="form" label-width="100px">
      <el-form-item :label="t('spareName')" required>
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item :label="t('sparePartNumber')" required>
        <el-input v-model="form.part_number" />
      </el-form-item>
      <el-form-item :label="t('spareCategory')">
        <el-select v-model="form.category">
          <el-option :label="t('spareCategoryModule')" value="module" />
          <el-option :label="t('spareCategoryPower')" value="power" />
          <el-option :label="t('spareCategoryCable')" value="cable" />
          <el-option :label="t('spareCategoryOther')" value="other" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('spareManufacturer')">
        <el-input v-model="form.manufacturer" />
      </el-form-item>
      <el-form-item :label="t('spareDescription')">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item :label="t('spareInitialStock')">
        <el-input-number v-model="form.quantity_in_stock" :min="0" />
      </el-form-item>
      <el-form-item :label="t('spareMinQuantity')">
        <el-input-number v-model="form.min_quantity" :min="0" />
      </el-form-item>
      <el-form-item :label="t('spareUnitPrice')">
        <el-input-number v-model="form.unit_price" :min="0" :precision="2" />
      </el-form-item>
      <el-form-item :label="t('spareLocation')">
        <el-input v-model="form.location" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" @click="savePart">{{ t('actionSave') }}</el-button>
    </template>
  </el-dialog>

  <!-- 入库对话框（带扫码功能） -->
  <el-dialog v-model="manualInDialogVisible" :title="t('spareStockIn')" width="700px" append-to-body draggable align-center class="stock-in-dialog">
    <div class="stock-content">
      <!-- 扫码功能条 -->
      <div class="scan-action-bar">
        <el-button type="default" class="scan-btn" @click="openScanInDialog">
          <el-icon><Aim /></el-icon>
          {{ t('spareScanToAdd') }}
        </el-button>
        <div class="scan-tip-badge">
          <el-icon><InfoFilled /></el-icon>
          {{ t('spareScanInTip') }}
        </div>
      </div>

      <!-- 手动输入表单 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Edit /></el-icon>
          <span>{{ t('spareManualInputSection') }}</span>
        </div>
        <el-form :model="manualInForm" label-width="80px" size="default">
          <el-form-item :label="t('spareName')">
            <el-input :value="currentManualPart?.name" disabled />
          </el-form-item>
          <el-form-item :label="t('spareSerialNumber')" required>
            <el-input v-model="manualInForm.serial_number" :placeholder="t('spareEnterSerialPlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('sparePoNumber')">
            <el-input v-model="manualInForm.po_number" :placeholder="t('sparePoNumberPlaceholder')" />
          </el-form-item>
          <el-row :gutter="12">
            <el-col :span="12">
              <el-form-item :label="t('spareUnitPrice')">
                <el-input-number v-model="manualInForm.unit_price" :min="0" :precision="2" style="width: 110px" />
                <span class="unit-text">元</span>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="t('spareQuantity')">
                <el-input-number v-model="manualInForm.quantity" :min="1" style="width: 110px" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item :label="t('spareLocation')">
            <el-input v-model="manualInForm.location" :placeholder="t('spareLocationPlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('spareNotes')">
            <el-input v-model="manualInForm.notes" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
      </div>
    </div>
    <template #footer>
      <el-button @click="manualInDialogVisible = false">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" @click="submitManualIn" :loading="manualInSubmitting">{{ t('spareConfirmIn') }}</el-button>
    </template>
  </el-dialog>

  <!-- 扫码入库对话框 -->
  <el-dialog v-model="scanInDialogVisible" :title="t('spareScanStockIn')" width="800px" append-to-body draggable align-center>
    <ScanSession
      ref="scanInSessionRef"
      default-type="in"
      :part-id="currentManualPart?.id"
      :po-number="manualInForm.po_number"
      :location="manualInForm.location"
      :auto-start="scanInDialogVisible"
      @complete="onScanInComplete"
      @cancel="scanInDialogVisible = false"
    />
  </el-dialog>

  <!-- 出库对话框（带扫码功能） -->
  <el-dialog v-model="manualOutDialogVisible" :title="t('spareStockOut')" width="700px" append-to-body draggable align-center class="stock-out-dialog">
    <div class="stock-content">
      <!-- 扫码功能条 -->
      <div class="scan-action-bar out">
        <el-button type="default" class="scan-btn" @click="openScanOutDialog">
          <el-icon><Aim /></el-icon>
          {{ t('spareScanToOut') }}
        </el-button>
        <div class="scan-tip-badge">
          <el-icon><InfoFilled /></el-icon>
          {{ t('spareScanOutTip') }}
        </div>
      </div>

      <!-- 手动输入表单 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Edit /></el-icon>
          <span>{{ t('spareManualInputSection') }}</span>
        </div>
        <el-form :model="manualOutForm" label-width="80px" size="default">
          <el-form-item :label="t('spareSerialNumber')" required>
            <el-input v-model="manualOutForm.serial_number" :placeholder="t('spareSearchSerialPlaceholder')" @keyup.enter="searchSerialForOut" />
            <el-button size="small" type="primary" @click="searchSerialForOut" :loading="searchingSerial" style="margin-top: 8px">{{ t('spareQuery') }}</el-button>
          </el-form-item>
          <div v-if="outPartInfo" class="part-info-card">
            <div class="info-header">
              <el-tag :type="outPartInfo.status === 'in_stock' ? 'success' : 'warning'" size="small">
                {{ outPartInfo.status === 'in_stock' ? t('statusInStock') : t('statusOut') }}
              </el-tag>
              <span class="serial-text">{{ outPartInfo.serial_number }}</span>
            </div>
            <div class="info-body">
              <span>{{ t('spareName') }}: {{ outPartInfo.name }}</span>
              <span>{{ t('sparePartNumber') }}: {{ outPartInfo.part_number }}</span>
              <span>{{ t('spareLocation') }}: {{ outPartInfo.location || '-' }}</span>
            </div>
            <el-alert v-if="outPartInfo.status !== 'in_stock'" type="warning" :closable="false" style="margin-top: 8px">
              {{ t('msgCannotOut') }}
            </el-alert>
          </div>
          <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" :label="t('spareStockOutReason')" required>
            <el-input v-model="manualOutForm.reason" type="textarea" :rows="2" :placeholder="t('spareStockOutReasonPlaceholder')" />
          </el-form-item>
          <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" :label="t('spareDestination')">
            <el-input v-model="manualOutForm.destination" :placeholder="t('spareDestinationPlaceholder')" />
          </el-form-item>
          <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" :label="t('spareNotes')">
            <el-input v-model="manualOutForm.notes" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
      </div>
    </div>
    <template #footer>
      <el-button @click="manualOutDialogVisible = false">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" @click="submitManualOut" :loading="manualOutSubmitting" :disabled="!outPartInfo || outPartInfo.status !== 'in_stock'">{{ t('spareConfirmOut') }}</el-button>
    </template>
  </el-dialog>

  <!-- 扫码出库对话框 -->
  <el-dialog v-model="scanOutDialogVisible" :title="t('spareScanStockOut')" width="800px" append-to-body draggable align-center>
    <ScanSession
      ref="scanOutSessionRef"
      default-type="out"
      :auto-start="scanOutDialogVisible"
      @complete="onScanOutComplete"
      @cancel="scanOutDialogVisible = false"
    />
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, InfoFilled, Edit } from '@element-plus/icons-vue'
import { getPartList, createPart, updatePart, getPartStats, manualStockIn, manualStockOut, getPartBySerialNumber } from '@/api'
import { useI18n } from '@/composables/useI18n'
import ScanSession from '@/components/ScanSession.vue'

const { t } = useI18n()
const emit = defineEmits(['show-detail', 'stats-loaded'])

// 接收外部筛选参数
const props = defineProps({
  externalSearch: { type: String, default: '' },
  externalCategory: { type: String, default: '' },
  externalLowStock: { type: Boolean, default: false }
})

const parts = ref([])
const loading = ref(false)

// 新增/编辑对话框
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = reactive({
  name: '', part_number: '', category: '', manufacturer: '',
  description: '', quantity_in_stock: 0, min_quantity: 0, unit_price: 0, location: ''
})

// 手动入库
const manualInDialogVisible = ref(false)
const currentManualPart = ref(null)
const manualInSubmitting = ref(false)
const manualInForm = reactive({
  serial_number: '',
  po_number: '',
  unit_price: 0,
  quantity: 1,
  location: '',
  notes: '',
  reason: ''
})

// 扫码入库
const scanInDialogVisible = ref(false)
const scanInSessionRef = ref(null)

// 手动出库
const manualOutDialogVisible = ref(false)
const manualOutSubmitting = ref(false)
const searchingSerial = ref(false)
const outPartInfo = ref(null)
const manualOutForm = reactive({
  serial_number: '',
  reason: '',
  destination: '',
  notes: ''
})

// 扫码出库
const scanOutDialogVisible = ref(false)
const scanOutSessionRef = ref(null)

const loadParts = async () => {
  loading.value = true
  try {
    const params = {
      search: props.externalSearch || '',
      category: props.externalCategory || '',
      low_stock: props.externalLowStock || false,
      limit: 200
    }
    const result = await getPartList(params)
    parts.value = result.items || []
    emit('stats-loaded', await getPartStats())
  } catch (e) {
    ElMessage.error(t('spareLoadFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  Object.assign(form, { name: '', part_number: '', category: '', manufacturer: '', description: '', quantity_in_stock: 0, min_quantity: 0, unit_price: 0, location: '' })
  dialogVisible.value = true
}

const savePart = async () => {
  try {
    if (isEdit.value) {
      await updatePart(editId.value, form)
      ElMessage.success(t('msgUpdatedSuccess'))
    } else {
      await createPart(form)
      ElMessage.success(t('msgCreatedSuccess'))
    }
    dialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error(t('msgOpFailed') + ': ' + (e.response?.data?.detail || e.message))
  }
}

// 手动入库
const showManualInDialog = (row) => {
  currentManualPart.value = row
  Object.assign(manualInForm, {
    serial_number: '',
    po_number: '',
    unit_price: row.unit_price || 0,
    location: row.location || '',
    notes: '',
    reason: ''
  })
  manualInDialogVisible.value = true
}

const submitManualIn = async () => {
  if (!manualInForm.serial_number) {
    ElMessage.warning(t('spareSerialNumber'))
    return
  }

  manualInSubmitting.value = true
  try {
    const result = await manualStockIn(currentManualPart.value.id, manualInForm)
    ElMessage.success(result.message || t('spareStockIn') + t('msgSuccess'))
    manualInDialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error(t('spareStockIn') + t('msgFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    manualInSubmitting.value = false
  }
}

// 手动出库
const showManualOutDialog = (row) => {
  Object.assign(manualOutForm, {
    serial_number: '',
    reason: '',
    destination: '',
    notes: ''
  })
  outPartInfo.value = null
  manualOutDialogVisible.value = true
}

const searchSerialForOut = async () => {
  if (!manualOutForm.serial_number) {
    ElMessage.warning(t('msgEnterRequired') + t('spareSerialNumber'))
    return
  }

  searchingSerial.value = true
  try {
    const result = await getPartBySerialNumber(manualOutForm.serial_number)
    outPartInfo.value = result
    if (result.status !== 'in_stock') {
      ElMessage.warning(t('msgNotInStock'))
    }
  } catch (e) {
    ElMessage.error(t('spareNotFound'))
    outPartInfo.value = null
  } finally {
    searchingSerial.value = false
  }
}

const submitManualOut = async () => {
  if (!outPartInfo.value || outPartInfo.value.status !== 'in_stock') {
    ElMessage.warning(t('msgCannotOut'))
    return
  }
  if (!manualOutForm.reason) {
    ElMessage.warning(t('msgEnterRequired') + t('spareStockOutReason'))
    return
  }

  manualOutSubmitting.value = true
  try {
    const result = await manualStockOut(outPartInfo.value.id, {
      serial_number: manualOutForm.serial_number,
      reason: manualOutForm.reason,
      destination: manualOutForm.destination,
      notes: manualOutForm.notes
    })
    ElMessage.success(result.message || t('spareStockOut') + t('msgSuccess'))
    manualOutDialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error(t('spareStockOut') + t('msgFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    manualOutSubmitting.value = false
  }
}

// 扫码入库功能
const openScanInDialog = () => {
  if (!manualInForm.po_number) {
    ElMessage.warning(t('spareEnterPoFirst'))
    return
  }
  scanInDialogVisible.value = true
}

const onScanInComplete = (result) => {
  const count = result.items?.length || 0
  if (count > 0) {
    ElMessage.success(t('spareStockIn') + t('msgSuccess') + ` (${count} ${t('spareQuantity')})`)
  }
  scanInDialogVisible.value = false
  manualInDialogVisible.value = false
  loadParts()
}

// 扫码出库功能
const openScanOutDialog = () => {
  scanOutDialogVisible.value = true
}

const onScanOutComplete = (result) => {
  const count = result.out_count || result.items?.length || 0
  if (count > 0) {
    ElMessage.success(t('spareStockOut') + t('msgSuccess') + ` (${count} ${t('spareQuantity')})`)
  }
  scanOutDialogVisible.value = false
  manualOutDialogVisible.value = false
  loadParts()
}

onMounted(loadParts)

defineExpose({ loadParts, parts })
</script>

<style scoped>
.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.search-input {
  width: 200px;
}

.category-select {
  width: 120px;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.table-actions {
  display: flex;
  gap: 8px;
}

/* 入库/出库对话框内容样式 */
.stock-content {
  padding: 0;
}

/* 扫码功能条样式 */
.scan-action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #00b894 0%, #0984e3 100%);
  border-radius: 8px;
  margin-bottom: 16px;
}

.scan-action-bar.out {
  background: linear-gradient(135deg, #636e72 0%, #4a5455 100%);
}

.scan-action-bar .scan-btn {
  background: rgba(255,255,255,0.15);
  border-color: rgba(255,255,255,0.3);
  color: #fff;
  font-weight: 500;
  height: 36px;
  border-radius: 8px;
  transition: all 0.2s;
}

.scan-action-bar .scan-btn:hover {
  background: rgba(255,255,255,0.25);
  transform: translateY(-1px);
}

.scan-tip-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  color: rgba(255,255,255,0.9);
  font-size: 12px;
}

/* 手动输入区域 */
.form-section {
  padding: 14px 16px;
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  border: 1px solid rgba(0, 48, 135, 0.08);
}

.section-header {
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

.section-header .el-icon {
  color: var(--accent-primary);
}

.unit-text {
  font-size: 12px;
  color: var(--text-tertiary);
  margin-left: 4px;
}

.stock-in-dialog .el-form-item,
.stock-out-dialog .el-form-item {
  margin-bottom: 10px;
}

/* 备件信息卡片 */
.part-info-card {
  background: rgba(0, 48, 135, 0.06);
  border: 1px solid rgba(0, 48, 135, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.serial-text {
  font-weight: 600;
  color: #1677ff;
  font-size: 14px;
}

.info-body {
  color: var(--text-secondary);
  font-size: 13px;
}

.info-body span {
  display: block;
  line-height: 1.6;
}

/* 暗色模式 */
.dark .scan-action-bar {
  background: linear-gradient(135deg, #3fb950 0%, #58a6ff 100%);
}

.dark .scan-action-bar.out {
  background: linear-gradient(135deg, #636e72 0%, #95a5a6 100%);
}

.dark .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .section-header {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}

.dark .section-header .el-icon {
  color: #58a6ff;
}

.dark .part-info-card {
  background: rgba(63, 185, 80, 0.08);
  border-color: rgba(63, 185, 80, 0.2);
}

.dark .serial-text {
  color: #3fb950;
}
</style>