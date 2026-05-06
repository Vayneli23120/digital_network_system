<template>
  <div class="scan-input-wrapper">
    <el-input
      ref="inputRef"
      v-model="inputValue"
      :placeholder="placeholder"
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
        >查询</el-button>
        <el-tag v-if="foundPart" type="success" size="small">
          已匹配
        </el-tag>
      </template>
    </el-input>

    <!-- 扫码结果展示 -->
    <el-card v-if="foundPart" class="scan-result-card" shadow="hover">
      <div class="part-info">
        <div class="part-header">
          <span class="part-name">{{ foundPart.name }}</span>
          <el-tag :type="stockTagType" size="small">库存: {{ foundPart.quantity_in_stock }}</el-tag>
        </div>
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="型号">{{ foundPart.part_number }}</el-descriptions-item>
          <el-descriptions-item label="序列号">{{ foundPart.serial_number || '-' }}</el-descriptions-item>
          <el-descriptions-item label="PO号">{{ foundPart.po_number || '-' }}</el-descriptions-item>
          <el-descriptions-item label="单价">¥{{ foundPart.unit_price || 0 }}</el-descriptions-item>
          <el-descriptions-item label="位置">{{ foundPart.location || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
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
          加入列表
        </el-button>
        <el-button v-if="showOutButton" type="warning" @click="quickOut">
          <el-icon><Minus /></el-icon>
          快速出库
        </el-button>
        <el-button v-if="showInButton" type="success" @click="quickIn">
          <el-icon><Plus /></el-icon>
          快速入库
        </el-button>
      </div>
    </el-card>

    <!-- 未找到提示 -->
    <el-alert
      v-if="notFound && inputValue.length >= 4"
      title="未找到该序列号的备件"
      type="warning"
      :closable="false"
      show-icon
      class="not-found-alert"
    >
      <template #default>
        <p>序列号 "{{ inputValue }}" 未在库存中找到</p>
        <p style="margin-top: 8px">
          <el-button type="primary" size="small" @click="showAddPartDialog">新增备件</el-button>
          <el-button size="small" @click="manualInput">手动录入信息</el-button>
        </p>
      </template>
    </el-alert>

    <!-- 新增备件对话框 -->
    <el-dialog v-model="showAddDialog" title="新增备件（扫码入库）" width="500px">
      <el-form :model="addForm" label-width="100px">
        <el-form-item label="序列号">
          <el-input v-model="addForm.serial_number" disabled />
        </el-form-item>
        <el-form-item label="型号" required>
          <el-input v-model="addForm.part_number" />
        </el-form-item>
        <el-form-item label="名称" required>
          <el-input v-model="addForm.name" />
        </el-form-item>
        <el-form-item label="PO号">
          <el-input v-model="addForm.po_number" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="addForm.category">
            <el-option label="模块" value="模块" />
            <el-option label="电源" value="电源" />
            <el-option label="线缆" value="线缆" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="入库数量">
          <el-input-number v-model="addForm.quantity_in_stock" :min="1" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="addForm.unit_price" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="存放位置">
          <el-input v-model="addForm.location" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitAddPart" :loading="adding">保存并入库</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, Plus, Minus } from '@element-plus/icons-vue'
import { getPartBySerialNumber, getPartList, createPart, createMovement } from '@/api'

// 使用 Aim 图标代替 Scan（瞄准/扫描）

// Props
const props = defineProps({
  placeholder: {
    type: String,
    default: '请用扫码枪扫描序列号，或手动输入'
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
  category: '其他',
  quantity_in_stock: 1,
  unit_price: 0,
  location: ''
})

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
    ElMessage.warning('请输入至少4个字符')
    return
  }

  searching.value = true
  foundPart.value = null
  notFound.value = false

  try {
    const part = await getPartBySerialNumber(serial)
    if (part) {
      foundPart.value = part
      ElMessage.success('已找到备件信息')
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
    ElMessage.success(`已加入: ${foundPart.value.name}`)
    clearScan()
  }
}

// 快速出库
const quickOut = async () => {
  if (!foundPart.value || foundPart.value.quantity_in_stock <= 0) {
    ElMessage.warning('库存不足')
    return
  }

  try {
    await createMovement({
      part_id: foundPart.value.id,
      movement_type: 'out',
      quantity: 1,
      reason: '扫码快速出库',
      operator: '扫码枪操作'
    })
    ElMessage.success(`已出库: ${foundPart.value.name}`)
    emit('added', { ...foundPart.value, action: 'out' })
    clearScan()
  } catch (e) {
    ElMessage.error('出库失败')
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
      reason: '扫码快速入库',
      operator: '扫码枪操作'
    })
    ElMessage.success(`已入库: ${foundPart.value.name}`)
    emit('added', { ...foundPart.value, action: 'in' })
    clearScan()
  } catch (e) {
    ElMessage.error('入库失败')
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
    category: '其他',
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
    ElMessage.warning('请填写型号和名称')
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
        reason: '扫码新增入库',
        operator: '扫码枪操作'
      })
    }

    ElMessage.success('备件创建成功')
    showAddDialog.value = false
    clearScan()

    inputValue.value = addForm.value.serial_number
    handleScan()
  } catch (e) {
    ElMessage.error('创建失败: ' + (e.response?.data?.detail || e.message))
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