<template>
  <div class="spare-parts">
    <el-tabs v-model="activeTab">
      <!-- 备件列表 Tab -->
      <el-tab-pane label="备件列表" name="parts">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>备件资产管理</span>
              <el-button type="primary" @click="showAddDialog">新增备件</el-button>
            </div>
          </template>

          <!-- 统计卡片 -->
          <el-row :gutter="16" class="stats-row">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="备件种类" :value="stats.total_parts" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="总库存" :value="stats.total_quantity" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="库存不足" :value="stats.low_stock_count" value-style="color: #F56C6C" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="总价值（元）" :value="stats.total_value" :precision="2" />
          </el-card>
        </el-col>
      </el-row>

      <!-- 搜索和过滤 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="搜索">
          <el-input v-model="search" placeholder="名称/型号/序列号/PO号" clearable @clear="loadParts" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="category" placeholder="全部" clearable @change="loadParts">
            <el-option label="模块" value="模块" />
            <el-option label="电源" value="电源" />
            <el-option label="线缆" value="线缆" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="lowStock" @change="loadParts">仅显示库存不足</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadParts">搜索</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="parts" stripe border v-loading="loading">
        <el-table-column prop="name" label="名称" width="150" />
        <el-table-column prop="part_number" label="型号" width="150" />
        <el-table-column prop="serial_number" label="序列号" width="150">
          <template #default="{ row }">{{ row.serial_number || '-' }}</template>
        </el-table-column>
        <el-table-column prop="po_number" label="PO号" width="120">
          <template #default="{ row }">{{ row.po_number || '-' }}</template>
        </el-table-column>
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
        <el-table-column prop="unit_price" label="单价" width="100">
          <template #default="{ row }">¥{{ row.unit_price.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="location" label="存放位置" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="showInDialog(row)">入库</el-button>
            <el-button size="small" type="warning" @click="showOutDialog(row)">出库</el-button>
            <el-button size="small" @click="showEditDialog(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
      </el-tab-pane>

      <!-- 出入库历史 Tab -->
      <el-tab-pane label="出入库历史" name="movements">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>出入库记录</span>
              <el-button @click="loadMovements"><el-icon><Refresh /></el-icon> 刷新</el-button>
            </div>
          </template>
          <el-table :data="movements" v-loading="movementsLoading" stripe border>
            <el-table-column prop="created_at" label="时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="movement_type" label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="row.movement_type === 'in' ? 'success' : 'warning'" size="small">
                  {{ row.movement_type === 'in' ? '入库' : '出库' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="80" />
            <el-table-column prop="reason" label="原因" min-width="150" show-overflow-tooltip />
            <el-table-column prop="operator" label="操作人" width="100" />
            <el-table-column prop="reference" label="参考编号" width="150" show-overflow-tooltip />
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="movementPage"
              :page-size="50"
              layout="total, prev, pager, next"
              :total="movementTotal"
              @current-change="loadMovements"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑备件' : '新增备件'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="型号" required>
          <el-input v-model="form.part_number" />
        </el-form-item>
        <el-form-item label="序列号">
          <el-input v-model="form.serial_number" placeholder="扫码枪扫描或手动输入" />
        </el-form-item>
        <el-form-item label="PO号">
          <el-input v-model="form.po_number" placeholder="采购订单号" />
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

    <!-- 入库/出库对话框 -->
    <el-dialog v-model="movementDialogVisible" :title="movementType === 'in' ? '入库' : '出库'" width="400px">
      <el-form :model="movementForm" label-width="80px">
        <el-form-item label="备件">
          <el-input :value="currentPart?.name" disabled />
        </el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="movementForm.quantity" :min="1" />
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="movementForm.reason" type="textarea" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="movementForm.operator" />
        </el-form-item>
        <el-form-item label="参考">
          <el-input v-model="movementForm.reference" placeholder="关联工单/设备编号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="movementDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMovement">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getPartList, createPart, updatePart, getPartStats, createMovement, getMovements } from '@/api'
import { formatDateTime } from '@/utils/time'

const parts = ref([])
const loading = ref(false)
const search = ref('')
const category = ref('')
const lowStock = ref(false)
const stats = reactive({ total_parts: 0, total_quantity: 0, low_stock_count: 0, total_value: 0 })
const activeTab = ref('parts')
const movements = ref([])
const movementsLoading = ref(false)
const movementPage = ref(1)
const movementTotal = ref(0)

const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = reactive({
  name: '', part_number: '', serial_number: '', po_number: '', category: '', manufacturer: '',
  description: '', quantity_in_stock: 0, min_quantity: 0, unit_price: 0, location: ''
})

const movementDialogVisible = ref(false)
const movementType = ref('in')
const currentPart = ref(null)
const movementForm = reactive({ quantity: 1, reason: '', operator: '', reference: '' })

const loadParts = async () => {
  loading.value = true
  try {
    const params = { search: search.value, category: category.value, low_stock: lowStock.value, limit: 200 }
    const result = await getPartList(params)
    parts.value = result.items || []
    const statsData = await getPartStats()
    Object.assign(stats, statsData)
  } catch (e) {
    ElMessage.error('加载备件失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  Object.assign(form, { name: '', part_number: '', serial_number: '', po_number: '', category: '', manufacturer: '', description: '', quantity_in_stock: 0, min_quantity: 0, unit_price: 0, location: '' })
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, row)
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

const showInDialog = (row) => {
  currentPart.value = row
  movementType.value = 'in'
  movementForm.quantity = 1
  movementForm.reason = ''
  movementForm.operator = ''
  movementForm.reference = ''
  movementDialogVisible.value = true
}

const showOutDialog = (row) => {
  currentPart.value = row
  movementType.value = 'out'
  movementForm.quantity = 1
  movementForm.reason = ''
  movementForm.operator = ''
  movementForm.reference = ''
  movementDialogVisible.value = true
}

const submitMovement = async () => {
  try {
    await createMovement({
      part_id: currentPart.value.id,
      movement_type: movementType.value,
      ...movementForm
    })
    ElMessage.success(movementType.value === 'in' ? '入库成功' : '出库成功')
    movementDialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

const loadMovements = async () => {
  movementsLoading.value = true
  try {
    const params = { skip: (movementPage.value - 1) * 50, limit: 50 }
    const result = await getMovements(params)
    movements.value = result.items || []
    movementTotal.value = result.total || 0
  } catch (e) {
    ElMessage.error('加载出入库记录失败')
  } finally {
    movementsLoading.value = false
  }
}

onMounted(loadParts)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; }
.filter-form { margin-bottom: 20px; }
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
