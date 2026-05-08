<template>
  <el-card>
    <template #header>
      <div class="card-header">
        <span>备件资产管理</span>
      </div>
    </template>

    <!-- 工具栏 -->
    <PartsToolbar
      :stats="stats"
      @scan-in="$emit('scan-in')"
      @scan-out="$emit('scan-out')"
      @add="showAddDialog"
    />

    <!-- 筛选工具栏 -->
    <div class="filter-toolbar">
      <div class="toolbar-left">
        <el-input
          v-model="search"
          placeholder="搜索名称/型号"
          clearable
          class="search-input"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select v-model="category" placeholder="分类" clearable class="category-select" @change="handleSearch">
          <el-option label="模块" value="模块" />
          <el-option label="电源" value="电源" />
          <el-option label="线缆" value="线缆" />
          <el-option label="其他" value="其他" />
        </el-select>
        <el-checkbox v-model="lowStock" @change="handleSearch">库存不足</el-checkbox>
      </div>
      <div class="toolbar-right">
        <el-button size="small" @click="resetFilters">重置</el-button>
        <el-button size="small" type="primary" @click="handleSearch">搜索</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table :data="parts" stripe border v-loading="loading">
      <el-table-column prop="name" label="名称" width="150">
        <template #default="{ row }">
          <el-button type="primary" link @click="$emit('show-detail', row)">
            {{ row.name }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column prop="part_number" label="型号" width="150" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column prop="manufacturer" label="厂商" width="120" />
      <el-table-column prop="quantity_in_stock" label="库存" width="100">
        <template #default="{ row }">
          <el-tag :type="row.quantity_in_stock < row.min_quantity ? 'danger' : 'success'">
            {{ row.quantity_in_stock }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="min_quantity" label="最低库存" width="100" />
      <el-table-column label="总价" width="100">
        <template #default="{ row }">¥{{ (row.unit_price * row.quantity_in_stock).toFixed(2) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="success" @click="showManualInDialog(row)">入库</el-button>
          <el-button size="small" type="warning" @click="showManualOutDialog(row)">出库</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <!-- 新增/编辑对话框 -->
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑备件' : '新增备件'" width="600px">
    <el-form :model="form" label-width="100px">
      <el-form-item label="名称" required>
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item label="型号" required>
        <el-input v-model="form.part_number" />
      </el-form-item>
      <el-form-item label="分类">
        <el-select v-model="form.category">
          <el-option label="模块" value="模块" />
          <el-option label="电源" value="电源" />
          <el-option label="线缆" value="线缆" />
          <el-option label="其他" value="其他" />
        </el-select>
      </el-form-item>
      <el-form-item label="厂商">
        <el-input v-model="form.manufacturer" />
      </el-form-item>
      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" />
      </el-form-item>
      <el-form-item label="初始库存">
        <el-input-number v-model="form.quantity_in_stock" :min="0" />
      </el-form-item>
      <el-form-item label="最低库存">
        <el-input-number v-model="form.min_quantity" :min="0" />
      </el-form-item>
      <el-form-item label="单价">
        <el-input-number v-model="form.unit_price" :min="0" :precision="2" />
      </el-form-item>
      <el-form-item label="存放位置">
        <el-input v-model="form.location" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" @click="savePart">保存</el-button>
    </template>
  </el-dialog>

  <!-- 手动入库对话框 -->
  <el-dialog v-model="manualInDialogVisible" title="手动入库" width="500px">
    <el-form :model="manualInForm" label-width="80px">
      <el-form-item label="备件">
        <el-input :value="currentManualPart?.name" disabled />
      </el-form-item>
      <el-form-item label="序列号" required>
        <el-input v-model="manualInForm.serial_number" placeholder="输入序列号" />
      </el-form-item>
      <el-form-item label="PO号">
        <el-input v-model="manualInForm.po_number" placeholder="采购订单号" />
      </el-form-item>
      <el-form-item label="单价">
        <el-input-number v-model="manualInForm.unit_price" :min="0" :precision="2" placeholder="单价" />
      </el-form-item>
      <el-form-item label="存放位置">
        <el-input v-model="manualInForm.location" placeholder="存放位置" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="manualInForm.notes" type="textarea" placeholder="备注信息" />
      </el-form-item>
      <el-form-item label="入库原因">
        <el-input v-model="manualInForm.reason" type="textarea" placeholder="入库原因" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="manualInDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitManualIn" :loading="manualInSubmitting">确认入库</el-button>
    </template>
  </el-dialog>

  <!-- 手动出库对话框 -->
  <el-dialog v-model="manualOutDialogVisible" title="手动出库" width="500px">
    <el-form :model="manualOutForm" label-width="80px">
      <el-form-item label="序列号" required>
        <el-input v-model="manualOutForm.serial_number" placeholder="输入序列号查询备件" @keyup.enter="searchSerialForOut" />
        <el-button size="small" type="primary" @click="searchSerialForOut" :loading="searchingSerial" style="margin-top: 8px">查询</el-button>
      </el-form-item>
      <div v-if="outPartInfo" style="background: #f5f7fa; padding: 12px; border-radius: 8px; margin-bottom: 16px">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
          <el-tag :type="outPartInfo.status === 'in_stock' ? 'success' : 'warning'" size="small">
            {{ outPartInfo.status === 'in_stock' ? '在库' : '已出库' }}
          </el-tag>
          <span style="font-weight: 600; color: #1677ff">{{ outPartInfo.serial_number }}</span>
        </div>
        <div style="color: #8c8c8c; font-size: 14px">
          <span style="min-width: 50px">名称：</span>{{ outPartInfo.name }}<br>
          <span style="min-width: 50px">型号：</span>{{ outPartInfo.part_number }}<br>
          <span style="min-width: 50px">位置：</span>{{ outPartInfo.location || '-' }}
        </div>
        <el-alert v-if="outPartInfo.status !== 'in_stock'" type="warning" :closable="false" style="margin-top: 8px">
          该序列号不在库中，无法出库
        </el-alert>
      </div>
      <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" label="出库原因" required>
        <el-input v-model="manualOutForm.reason" type="textarea" placeholder="出库原因" />
      </el-form-item>
      <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" label="出库去向">
        <el-input v-model="manualOutForm.destination" placeholder="出库去向（设备/项目等）" />
      </el-form-item>
      <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" label="备注">
        <el-input v-model="manualOutForm.notes" type="textarea" placeholder="备注信息" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="manualOutDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="submitManualOut" :loading="manualOutSubmitting" :disabled="!outPartInfo || outPartInfo.status !== 'in_stock'">确认出库</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getPartList, createPart, updatePart, getPartStats, manualStockIn, manualStockOut, getPartBySerialNumber } from '@/api'
import PartsToolbar from './PartsToolbar.vue'

const emit = defineEmits(['scan-in', 'scan-out', 'show-detail', 'refreshed'])

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
    const params = { search: search.value, category: category.value, low_stock: lowStock.value, limit: 200 }
    const result = await getPartList(params)
    parts.value = result.items || []
    const statsData = await getPartStats()
    Object.assign(stats, statsData)
    emit('refreshed')
  } catch (e) {
    ElMessage.error('加载备件失败：' + (e.response?.data?.detail || e.message))
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
      ElMessage.success('更新成功')
    } else {
      await createPart(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
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
    ElMessage.warning('请输入序列号')
    return
  }

  manualInSubmitting.value = true
  try {
    const result = await manualStockIn(currentManualPart.value.id, manualInForm)
    ElMessage.success(result.message || '入库成功')
    manualInDialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error('入库失败：' + (e.response?.data?.detail || e.message))
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
    ElMessage.warning('请输入序列号')
    return
  }

  searchingSerial.value = true
  try {
    const result = await getPartBySerialNumber(manualOutForm.serial_number)
    outPartInfo.value = result
    if (result.status !== 'in_stock') {
      ElMessage.warning('该序列号不在库中')
    }
  } catch (e) {
    ElMessage.error('未找到该序列号的备件')
    outPartInfo.value = null
  } finally {
    searchingSerial.value = false
  }
}

const submitManualOut = async () => {
  if (!outPartInfo.value || outPartInfo.value.status !== 'in_stock') {
    ElMessage.warning('该序列号不在库中，无法出库')
    return
  }
  if (!manualOutForm.reason) {
    ElMessage.warning('请填写出库原因')
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
    ElMessage.success(result.message || '出库成功')
    manualOutDialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error('出库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    manualOutSubmitting.value = false
  }
}

onMounted(loadParts)

defineExpose({ loadParts, parts })
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
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
  width: 100px;
}
.toolbar-right {
  display: flex;
  gap: 8px;
}
</style>