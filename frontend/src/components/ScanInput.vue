<template>
  <div class="scan-input-wrapper">
    <el-input
      ref="inputRef"
      v-model="inputValue"
      :placeholder="computedPlaceholder"
      :class="['scan-input', { 'scanning': isScanning, 'found': foundPart }]"
      @keyup.enter="handleScan"
      @input="onInputChange"
      clearable
      @clear="clearScan"
    >
      <template #prefix>
        <el-icon :class="{ 'scan-animation': isScanning }">
          <Aim />
        </el-icon>
      </template>
      <template #suffix>
        <el-button
          v-if="!foundPart && inputValue.length >= 4"
          type="primary"
          size="small"
          @click="handleScan"
          :loading="searching"
        >{{ t('scanQuery') }}</el-button>
        <el-tag v-if="foundPart" type="success" size="small">
          {{ t('scanMatched') }}
        </el-tag>
      </template>
    </el-input>

    <!-- 扫码结果展示 -->
    <el-card v-if="foundPart" class="scan-result-card" shadow="hover">
      <div class="part-info">
        <div class="part-header">
          <span class="part-name">{{ foundPart.name }}</span>
          <el-tag :type="stockTagType" size="small">{{ t('scanStock') }} {{ foundPart.quantity_in_stock }}</el-tag>
        </div>
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item :label="t('sparePartNumber')">{{ foundPart.part_number }}</el-descriptions-item>
          <el-descriptions-item :label="t('spareSerialNumber')">{{ foundPart.serial_number || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('sparePoNumber')">{{ foundPart.po_number || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('spareUnitPrice')">¥{{ foundPart.unit_price || 0 }}</el-descriptions-item>
          <el-descriptions-item :label="t('spareLocation')">{{ foundPart.location || '-' }}</el-descriptions-item>
          <el-descriptions-item :label="t('scanStatus')">
            <el-tag :type="foundPart.status === 'active' ? 'success' : 'info'" size="small">
              {{ foundPart.status }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 操作按钮 -->
      <div class="part-actions">
        <el-button type="primary" @click="addToSelection">
          <el-icon><Plus /></el-icon>
          {{ t('scanAddToList') }}
        </el-button>
        <el-button v-if="showOutButton" type="warning" @click="quickOut">
          <el-icon><Minus /></el-icon>
          {{ t('scanQuickOut') }}
        </el-button>
        <el-button v-if="showInButton" type="success" @click="quickIn">
          <el-icon><Plus /></el-icon>
          {{ t('scanQuickIn') }}
        </el-button>
      </div>
    </el-card>

    <!-- 未找到提示 -->
    <el-alert
      v-if="notFound && inputValue.length >= 4"
      :title="t('spareNotFound')"
      type="warning"
      :closable="false"
      show-icon
      class="not-found-alert"
    >
      <template #default>
        <p>{{ t('scanSerialNotFoundMsg', { serial: inputValue }) }}</p>
        <p style="margin-top: 8px">
          <el-button type="primary" size="small" @click="showAddPartDialog">{{ t('spareNew') }}</el-button>
          <el-button size="small" @click="manualInput">{{ t('scanManualInput') }}</el-button>
        </p>
      </template>
    </el-alert>

    <!-- 新增备件对话框 -->
    <el-dialog v-model="showAddDialog" :title="t('scanNewPartScanIn')" width="500px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item :label="t('spareSerialNumber')">
          <el-input v-model="addForm.serial_number" disabled />
        </el-form-item>
        <el-form-item :label="t('sparePartNumber')" required>
          <el-input v-model="addForm.part_number" />
        </el-form-item>
        <el-form-item :label="t('spareName')" required>
          <el-input v-model="addForm.name" />
        </el-form-item>
        <el-form-item :label="t('sparePoNumber')">
          <el-input v-model="addForm.po_number" />
        </el-form-item>
        <el-form-item :label="t('spareCategory')">
          <el-select v-model="addForm.category">
            <el-option :label="t('spareCategoryModule')" value="module" />
            <el-option :label="t('spareCategoryPower')" value="power" />
            <el-option :label="t('spareCategoryCable')" value="cable" />
            <el-option :label="t('spareCategoryOther')" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('scanStockInQuantity')">
          <el-input-number v-model="addForm.quantity_in_stock" :min="1" />
        </el-form-item>
        <el-form-item :label="t('spareUnitPrice')">
          <el-input-number v-model="addForm.unit_price" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item :label="t('scanStorageLocation')">
          <el-input v-model="addForm.location" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitAddPart" :loading="adding">{{ t('scanSaveAndStockIn') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, Plus, Minus } from '@element-plus/icons-vue'
import { getPartBySerialNumber, getPartList, createPart, createMovement } from '@/api'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

// Props
const props = defineProps({
  placeholder: {
    type: String,
    default: ''
  },
  mode: {
    type: String,
    default: 'select' // select | out | in | return
  },
  autoAdd: {
    type: Boolean,
    default: false // 扫码后自动加入列表
  }
})

// Emits
const emit = defineEmits(['found', 'added', 'not-found', 'manual'])

// 计算属性
const computedPlaceholder = computed(() => {
  return props.placeholder || t('scanScanPlaceholder')
})

// 状态
const inputRef = ref(null)
const inputValue = ref('')
const isScanning = ref(false)
const searching = ref(false)
const foundPart = ref(null)
const notFound = ref(false)
const showAddDialog = ref(false)
const adding = ref(false)

// 新增备件表单
const addForm = ref({
  serial_number: '',
  part_number: '',
  name: '',
  po_number: '',
  category: '',
  quantity_in_stock: 1,
  unit_price: 0,
  location: ''
})

// 初始化默认分类
const defaultCategory = computed(() => 'other')

// 计算属性
const stockTagType = computed(() => {
  if (!foundPart.value) return 'info'
  const qty = foundPart.value.quantity_in_stock
  const min = foundPart.value.min_quantity || 0
  if (qty <= 0) return 'danger'
  if (qty < min) return 'warning'
  return 'success'
})

const showOutButton = computed(() => props.mode === 'out' && foundPart.value?.quantity_in_stock > 0)
const showInButton = computed(() => props.mode === 'in')

// 监听输入变化
watch(inputValue, (val) => {
  if (val.length > 0) {
    isScanning.value = true
    setTimeout(() => {
      if (inputValue.value === val) {
        isScanning.value = false
      }
    }, 500)
  }
})

// 输入变化时重置状态
const onInputChange = () => {
  foundPart.value = null
  notFound.value = false
}

// 处理扫码/查询
const handleScan = async () => {
  const serial = inputValue.value.trim()
  if (serial.length < 4) {
    ElMessage.warning(t('scanMinLengthWarn'))
    return
  }

  searching.value = true
  foundPart.value = null
  notFound.value = false

  try {
    const part = await getPartBySerialNumber(serial)
    if (part) {
      foundPart.value = part
      ElMessage.success(t('scanFoundSuccess'))
      emit('found', part)

      if (props.autoAdd) {
        addToSelection()
      }
    } else {
      notFound.value = true
      emit('not-found', serial)
    }
  } catch (e) {
    notFound.value = true
    emit('not-found', serial)
  } finally {
    searching.value = false
    isScanning.value = false
  }
}

// 加入选择列表
const addToSelection = () => {
  if (foundPart.value) {
    emit('added', foundPart.value)
    ElMessage.success(t('scanAddedSuccess', { name: foundPart.value.name }))
    clearScan()
  }
}

// 快速出库
const quickOut = async () => {
  if (!foundPart.value || foundPart.value.quantity_in_stock <= 0) {
    ElMessage.warning(t('scanInsufficientStock'))
    return
  }

  try {
    await createMovement({
      part_id: foundPart.value.id,
      movement_type: 'out',
      quantity: 1,
      reason: t('scanQuickOutReason'),
      operator: t('scanScannerOperator')
    })
    ElMessage.success(t('scanOutSuccess', { name: foundPart.value.name }))
    emit('added', { ...foundPart.value, action: 'out' })
    clearScan()
  } catch (e) {
    ElMessage.error(t('scanOutFailed'))
  }
}

// 快速入库
const quickIn = async () => {
  if (!foundPart.value) return

  try {
    await createMovement({
      part_id: foundPart.value.id,
      movement_type: 'in',
      quantity: 1,
      reason: t('scanQuickInReason'),
      operator: t('scanScannerOperator')
    })
    ElMessage.success(t('scanInSuccess', { name: foundPart.value.name }))
    emit('added', { ...foundPart.value, action: 'in' })
    clearScan()
  } catch (e) {
    ElMessage.error(t('scanInFailed'))
  }
}

// 清空扫码
const clearScan = () => {
  inputValue.value = ''
  foundPart.value = null
  notFound.value = false
  isScanning.value = false
}

// 显示新增备件对话框
const showAddPartDialog = () => {
  addForm.value = {
    serial_number: inputValue.value,
    part_number: '',
    name: '',
    po_number: '',
    category: defaultCategory.value,
    quantity_in_stock: 1,
    unit_price: 0,
    location: ''
  }
  showAddDialog.value = true
}

// 手动录入
const manualInput = () => {
  emit('manual', inputValue.value)
}

// 提交新增备件
const submitAddPart = async () => {
  if (!addForm.value.part_number || !addForm.value.name) {
    ElMessage.warning(t('scanFillModelName'))
    return
  }

  adding.value = true
  try {
    const result = await createPart(addForm.value)

    if (props.mode === 'in') {
      await createMovement({
        part_id: result.id,
        movement_type: 'in',
        quantity: addForm.value.quantity_in_stock,
        reason: t('scanNewPartCreatedIn'),
        operator: t('scanScannerOperator')
      })
    }

    ElMessage.success(t('scanPartCreatedSuccess'))
    showAddDialog.value = false
    clearScan()

    inputValue.value = addForm.value.serial_number
    handleScan()
  } catch (e) {
    ElMessage.error(t('scanCreateFailedMsg', { msg: e.response?.data?.detail || e.message }))
  } finally {
    adding.value = false
  }
}

// 聚焦输入框
const focus = () => {
  inputRef.value?.focus()
}

// 暴露方法
defineExpose({
  focus,
  clearScan,
  handleScan
})

onMounted(() => {
  // 可选：自动聚焦等待扫码
})
</script>

<style scoped>
.scan-input-wrapper {
  position: relative;
}

.scan-input {
  font-size: 16px;
  height: 44px;
}

.scan-input.scanning {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-5);
}

.scan-input.found {
  border-color: var(--el-color-success);
}

.scan-animation {
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.scan-result-card {
  margin-top: 12px;
  border: 1px solid var(--el-color-success-light-5);
}

.part-info {
  padding: 8px 0;
}

.part-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.part-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.part-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.not-found-alert {
  margin-top: 12px;
}
</style>