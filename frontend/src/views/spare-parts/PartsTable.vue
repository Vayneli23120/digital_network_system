<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>{{ t('spareTitle') }}</span>
      </div>
    </template>

    <!-- 工具栏 -->
    <PartsToolbar
      :stats="stats"
      @scan-in="$emit('scan-in')"
      @scan-out="$emit('scan-out')"
      @add="showAddDialog"
    />

    <!-- 篮选工具栏 -->
    <div class="filter-toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="search"
          :placeholder="t('spareSearchPlaceholder')"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select v-model="category" :placeholder="t('spareCategory')" clearable class="category-select" @change="handleSearch">
          <el-option :label="t('spareCategoryModule')" value="module" />
          <el-option :label="t('spareCategoryPower')" value="power" />
          <el-option :label="t('spareCategoryCable')" value="cable" />
          <el-option :label="t('spareCategoryOther')" value="other" />
        </el-select>
        <el-checkbox v-model="lowStock" @change="handleSearch">{{ t('spareLowStock') }}</el-checkbox>
      </div>
      <div class="toolbar-right">
        <el-button size="small" @click="resetFilters">{{ t('actionReset') }}</el-button>
        <el-button size="small" type="primary" @click="handleSearch">{{ t('actionSearch') }}</el-button>
      </div>
    </div>

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
  <el-dialog v-model="dialogVisible" :title="isEdit ? t('spareEdit') : t('spareNew')" width="600px">
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

  <!-- 手动入库对话框 -->
  <el-dialog v-model="manualInDialogVisible" :title="t('spareManualIn')" width="500px">
    <el-form :model="manualInForm" label-width="80px">
      <el-form-item :label="t('spareName')">
        <el-input :value="currentManualPart?.name" disabled />
      </el-form-item>
      <el-form-item :label="t('spareSerialNumber')" required>
        <el-input v-model="manualInForm.serial_number" :placeholder="t('spareEnterSerialPlaceholder')" />
      </el-form-item>
      <el-form-item :label="t('sparePoNumber')">
        <el-input v-model="manualInForm.po_number" :placeholder="t('sparePoNumberPlaceholder')" />
      </el-form-item>
      <el-form-item :label="t('spareUnitPrice')">
        <el-input-number v-model="manualInForm.unit_price" :min="0" :precision="2" :placeholder="t('spareUnitPrice')" />
      </el-form-item>
      <el-form-item :label="t('spareLocation')">
        <el-input v-model="manualInForm.location" :placeholder="t('spareLocation')" />
      </el-form-item>
      <el-form-item :label="t('spareNotes')">
        <el-input v-model="manualInForm.notes" type="textarea" :placeholder="t('spareNotes')" />
      </el-form-item>
      <el-form-item :label="t('spareStockInReason')">
        <el-input v-model="manualInForm.reason" type="textarea" :placeholder="t('spareStockInReason')" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="manualInDialogVisible = false">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" @click="submitManualIn" :loading="manualInSubmitting">{{ t('spareConfirmIn') }}</el-button>
    </template>
  </el-dialog>

  <!-- 手动出库对话框 -->
  <el-dialog v-model="manualOutDialogVisible" :title="t('spareManualOut')" width="500px">
    <el-form :model="manualOutForm" label-width="80px">
      <el-form-item :label="t('spareSerialNumber')" required>
        <el-input v-model="manualOutForm.serial_number" :placeholder="t('spareSearchSerialPlaceholder')" @keyup.enter="searchSerialForOut" />
        <el-button size="small" type="primary" @click="searchSerialForOut" :loading="searchingSerial" style="margin-top: 8px">{{ t('spareQuery') }}</el-button>
      </el-form-item>
      <div v-if="outPartInfo" style="background: #f5f7fa; padding: 12px; border-radius: 8px; margin-bottom: 16px">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
          <el-tag :type="outPartInfo.status === 'in_stock' ? 'success' : 'warning'" size="small">
            {{ outPartInfo.status === 'in_stock' ? t('statusInStock') : t('statusOut') }}
          </el-tag>
          <span style="font-weight: 600; color: #1677ff">{{ outPartInfo.serial_number }}</span>
        </div>
        <div style="color: #8c8c8c; font-size: 14px">
          <span style="min-width: 50px">{{ t('spareName') }}:</span>{{ outPartInfo.name }}<br>
          <span style="min-width: 50px">{{ t('sparePartNumber') }}:</span>{{ outPartInfo.part_number }}<br>
          <span style="min-width: 50px">{{ t('spareLocation') }}:</span>{{ outPartInfo.location || '-' }}
        </div>
        <el-alert v-if="outPartInfo.status !== 'in_stock'" type="warning" :closable="false" style="margin-top: 8px">
          {{ t('msgCannotOut') }}
        </el-alert>
      </div>
      <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" :label="t('spareStockOutReason')" required>
        <el-input v-model="manualOutForm.reason" type="textarea" :placeholder="t('spareStockOutReason')" />
      </el-form-item>
      <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" :label="t('spareDestination')">
        <el-input v-model="manualOutForm.destination" :placeholder="t('spareDestinationPlaceholder')" />
      </el-form-item>
      <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" :label="t('spareNotes')">
        <el-input v-model="manualOutForm.notes" type="textarea" :placeholder="t('spareNotes')" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="manualOutDialogVisible = false">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" @click="submitManualOut" :loading="manualOutSubmitting" :disabled="!outPartInfo || outPartInfo.status !== 'in_stock'">{{ t('spareConfirmOut') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getPartList, createPart, updatePart, getPartStats, manualStockIn, manualStockOut, getPartBySerialNumber } from '@/api'
import { useI18n } from '@/composables/useI18n'
import PartsToolbar from './PartsToolbar.vue'

const { t } = useI18n()
const emit = defineEmits(['scan-in', 'scan-out', 'show-detail', 'refreshed', 'stats-loaded'])

// 接收外部筛选参数
const props = defineProps({
  externalSearch: { type: String, default: '' },
  externalCategory: { type: String, default: '' },
  externalLowStock: { type: Boolean, default: false }
})

const parts = ref([])
const loading = ref(false)
const search = ref('')
const category = ref('')
const lowStock = ref(false)
const stats = reactive({ total_parts: 0, total_quantity: 0, low_stock_count: 0, total_value: 0 })

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
  location: '',
  notes: '',
  reason: ''
})

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

const loadParts = async () => {
  loading.value = true
  try {
    // 使用外部筛选参数或内部筛选参数
    const effectiveSearch = props.externalSearch || search.value
    const effectiveCategory = props.externalCategory || category.value
    const effectiveLowStock = props.externalLowStock || lowStock.value

    const params = { search: effectiveSearch, category: effectiveCategory, low_stock: effectiveLowStock, limit: 200 }
    const result = await getPartList(params)
    parts.value = result.items || []
    const statsData = await getPartStats()
    Object.assign(stats, statsData)
    emit('stats-loaded', statsData)
    emit('refreshed')
  } catch (e) {
    ElMessage.error(t('spareLoadFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const handleSearch = () => loadParts()

const resetFilters = () => {
  search.value = ''
  category.value = ''
  lowStock.value = false
  loadParts()
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

onMounted(loadParts)

defineExpose({ loadParts, parts })
</script>

<style scoped>
.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  flex-wrap: wrap;
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
</style>