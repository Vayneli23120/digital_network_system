<template>
  <div class="planned-maintenance-page">
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value">{{ stats.tasks?.total || 0 }}</div>
            <div class="stat-label">总任务</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value success">{{ stats.tasks?.completed || 0 }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value warning">{{ stats.tasks?.pending || 0 }}</div>
            <div class="stat-label">待执行</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value danger">{{ stats.tasks?.overdue || 0 }}</div>
            <div class="stat-label">已超期</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>运维任务</span>
          <div class="actions">
            <el-button type="primary" @click="showPlanDialog = true">
              <el-icon><Plus /></el-icon>
              创建计划
            </el-button>
            <el-button type="success" @click="generateTasks">
              <el-icon><Refresh /></el-icon>
              自动生成任务
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="filterStatus" placeholder="任务状态" clearable style="width: 120px" @change="loadTasks">
          <el-option label="待执行" value="pending" />
          <el-option label="进行中" value="in_progress" />
          <el-option label="已完成" value="completed" />
          <el-option label="已超期" value="overdue" />
          <el-option label="已跳过" value="skipped" />
        </el-select>
        <el-select v-model="filterPlanId" placeholder="维护计划" clearable style="width: 200px" @change="loadTasks">
          <el-option v-for="p in plans" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="loadTasks"
        />
      </div>

      <!-- 任务表格 -->
      <el-table :data="tasks" style="width: 100%" v-loading="loading">
        <el-table-column prop="task_no" label="任务编号" width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="showTaskDetail(row)">{{ row.task_no }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" label="设备" width="160" />
        <el-table-column prop="scheduled_date" label="计划日期" width="160">
          <template #default="{ row }">{{ formatDate(row.scheduled_date) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actual_date" label="实际执行" width="160">
          <template #default="{ row }">{{ row.actual_date ? formatDate(row.actual_date) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending' || row.status === 'overdue'" type="primary" size="small" @click="startTask(row)">开始</el-button>
            <el-button v-if="row.status === 'in_progress'" type="success" size="small" @click="showCompleteDialog(row)">完成</el-button>
            <el-button v-if="row.status === 'pending' || row.status === 'overdue'" type="warning" size="small" @click="skipTask(row)">跳过</el-button>
            <el-button v-if="row.status === 'pending'" type="danger" size="small" @click="deleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 维护计划列表 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <span>维护计划</span>
      </template>
      <el-table :data="plans" style="width: 100%">
        <el-table-column prop="name" label="计划名称" width="200" />
        <el-table-column prop="device_name" label="设备" width="160" />
        <el-table-column prop="plan_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getPlanTypeColor(row.plan_type)">{{ getPlanTypeText(row.plan_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cycle_days" label="周期(天)" width="100" />
        <el-table-column prop="next_date" label="下次执行" width="160">
          <template #default="{ row }">{{ formatDate(row.next_date) }}</template>
        </el-table-column>
        <el-table-column prop="data_basis" label="数据依据" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '活跃' : '暂停' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="editPlan(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="deletePlan(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑计划对话框 -->
    <el-dialog v-model="showPlanDialog" :title="editMode ? '编辑计划' : '创建计划'" width="600px">
      <el-form :model="planForm" label-width="120px">
        <el-form-item label="计划名称" required>
          <el-input v-model="planForm.name" placeholder="如：每月例行巡检" />
        </el-form-item>
        <el-form-item label="设备">
          <el-select v-model="planForm.device_id" placeholder="选择设备（可选）" clearable filterable style="width: 100%">
            <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划类型" required>
          <el-select v-model="planForm.plan_type">
            <el-option label="例行巡检" value="routine_check" />
            <el-option label="备件更换" value="parts_replace" />
            <el-option label="原厂保养" value="vendor_service" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行周期(天)" required>
          <el-input-number v-model="planForm.cycle_days" :min="1" :max="365" />
        </el-form-item>
        <el-form-item label="下次执行日期" required>
          <el-date-picker v-model="planForm.next_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数据依据">
          <el-input v-model="planForm.data_basis" type="textarea" :rows="3" placeholder="为什么做这个计划？数据支撑是什么？" />
        </el-form-item>
        <el-form-item label="自动生成任务">
          <el-switch v-model="planForm.auto_generate" />
        </el-form-item>
        <el-form-item label="状态" v-if="editMode">
          <el-select v-model="planForm.status">
            <el-option label="活跃" value="active" />
            <el-option label="暂停" value="paused" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPlanDialog = false">取消</el-button>
        <el-button type="primary" @click="editMode ? updatePlan() : createPlan()">确定</el-button>
      </template>
    </el-dialog>

    <!-- 完成任务对话框 -->
    <el-dialog v-model="showCompleteDialogFlag" title="完成任务" width="700px">
      <el-form :model="completeForm" label-width="120px">
        <el-form-item label="维修描述">
          <el-input v-model="completeForm.description" type="textarea" :rows="3" placeholder="记录运维工作内容" />
        </el-form-item>

        <!-- 备件更换 -->
        <el-divider content-position="left">更换备件（从库存扣除）</el-divider>
        <el-form-item label="选择备件">
          <div class="parts-section">
            <el-select
              v-model="selectedPart"
              placeholder="搜索备件型号或名称"
              filterable
              remote
              :remote-method="searchParts"
              :loading="partsLoading"
              style="width: 100%"
              @change="addPartToComplete"
              clearable
            >
              <el-option
                v-for="part in partOptions"
                :key="part.id"
                :label="`${part.part_number} - ${part.name}`"
                :value="part.id"
                :disabled="part.quantity_in_stock <= 0"
              >
                <div class="part-option">
                  <span class="part-number">{{ part.part_number }}</span>
                  <span class="part-name">{{ part.name }}</span>
                  <span class="part-stock" :class="{ low: part.quantity_in_stock <= part.min_quantity }">
                    库存: {{ part.quantity_in_stock }}
                  </span>
                </div>
              </el-option>
            </el-select>

            <!-- 已选备件列表 -->
            <div class="selected-parts" v-if="completeForm.parts.length > 0">
              <el-table :data="completeForm.parts" size="small" border>
                <el-table-column prop="part_number" label="型号" width="120" />
                <el-table-column prop="name" label="名称" width="120" />
                <el-table-column prop="quantity" label="数量" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" :max="row.max_qty" size="small" @change="updatePartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" label="单价" width="80">
                  <template #default="{ row }">¥{{ row.unit_price.toFixed(2) }}</template>
                </el-table-column>
                <el-table-column label="小计" width="80">
                  <template #default="{ row }">¥{{ (row.quantity * row.unit_price).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="60">
                  <template #default="{ $index }">
                    <el-button type="danger" size="small" link @click="removePart($index)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">备件总成本: <span class="total-cost">¥{{ completeForm.parts_cost.toFixed(2) }}</span></div>
            </div>
            <el-tag v-else type="info">暂无更换备件</el-tag>
          </div>
        </el-form-item>

        <!-- 返回件 -->
        <el-divider content-position="left">返回件（入报废库存）</el-divider>
        <el-form-item label="换下的坏件">
          <div class="return-section">
            <el-select
              v-model="selectedReturnPart"
              placeholder="从备件库选择（可选）"
              filterable
              remote
              :remote-method="searchParts"
              style="width: 200px"
              clearable
            >
              <el-option v-for="part in partOptions" :key="part.id" :label="`${part.part_number} - ${part.name}`" :value="part.id" />
            </el-select>
            <el-input v-model="returnPartNumber" placeholder="型号（手动输入）" style="width: 120px" />
            <el-input v-model="returnPartName" placeholder="名称" style="width: 120px" />
            <div style="display: flex; align-items: center; gap: 5px;">
              <span>数量:</span>
              <el-input-number v-model="returnPartQty" :min="1" style="width: 100px" controls-position="right" />
            </div>
            <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">入报废库</el-checkbox>
            <el-button type="primary" size="small" :disabled="!returnPartNumber && !selectedReturnPart" @click="addReturnPart">添加</el-button>
          </div>

          <div class="return-parts-table" v-if="completeForm.return_parts.length > 0">
            <el-table :data="completeForm.return_parts" size="small" border>
              <el-table-column prop="part_number" label="型号" width="120" />
              <el-table-column prop="name" label="名称" width="120" />
              <el-table-column prop="quantity" label="数量" width="60" />
              <el-table-column label="入报废库" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.scrap_in" type="warning">入库</el-tag>
                  <el-tag v-else type="info">不入库</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="60">
                <template #default="{ $index }">
                  <el-button type="danger" size="small" link @click="removeReturnPart($index)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-form-item>

        <el-divider />
        <el-form-item label="人工工时(小时)">
          <el-input-number v-model="completeForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item label="人工成本">
          <el-input-number v-model="completeForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCompleteDialogFlag = false">取消</el-button>
        <el-button type="success" @click="completeTask">确认完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, InfoFilled } from '@element-plus/icons-vue'
import {
  getMaintenancePlans, createMaintenancePlan, updateMaintenancePlan, deleteMaintenancePlan as deletePlanApi,
  getMaintenanceTasks, startMaintenanceTask, completeMaintenanceTask, skipMaintenanceTask, deleteMaintenanceTask as deleteTaskApi,
  getPlannedMaintenanceStats, generateTasksForPlans, getDevices, getPartList, createMovement
} from '@/api'
import { formatDate } from '@/utils/time'

const router = useRouter()
const plans = ref([])
const tasks = ref([])
const devices = ref([])
const stats = ref({})
const loading = ref(false)
const showPlanDialog = ref(false)
const showCompleteDialogFlag = ref(false)
const editMode = ref(false)
const currentTask = ref(null)

// 备件相关
const partOptions = ref([])
const partsLoading = ref(false)
const selectedPart = ref(null)
const selectedReturnPart = ref(null)
const returnPartNumber = ref('')
const returnPartName = ref('')
const returnPartQty = ref(1)
const returnPartScrap = ref(true)

const filterStatus = ref('')
const filterPlanId = ref('')
const dateRange = ref([])

const planForm = ref({
  id: null,
  name: '',
  device_id: null,
  plan_type: 'routine_check',
  cycle_days: 30,
  next_date: '',
  data_basis: '',
  auto_generate: true,
  status: 'active'
})

const completeForm = ref({
  description: '',
  parts: [],
  parts_cost: 0,
  return_parts: [],
  labor_hours: 0,
  labor_cost: 0
})

const getStatusType = (status) => {
  const types = { pending: 'info', in_progress: 'warning', completed: 'success', overdue: 'danger', skipped: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { pending: '待执行', in_progress: '进行中', completed: '已完成', overdue: '已超期', skipped: '已跳过' }
  return texts[status] || status
}

const getPlanTypeColor = (type) => {
  const colors = { routine_check: 'success', parts_replace: 'warning', vendor_service: 'info' }
  return colors[type] || ''
}

const getPlanTypeText = (type) => {
  const texts = { routine_check: '例行巡检', parts_replace: '备件更换', vendor_service: '原厂保养' }
  return texts[type] || type
}

const loadStats = async () => {
  try {
    const data = await getPlannedMaintenanceStats()
    stats.value = data
  } catch (e) {
    console.error('加载统计失败', e)
  }
}

const loadPlans = async () => {
  try {
    const data = await getMaintenancePlans()
    plans.value = data.items || []
  } catch (e) {
    ElMessage.error('加载计划失败')
  }
}

const loadTasks = async () => {
  loading.value = true
  try {
    const params = {
      status: filterStatus.value || undefined,
      plan_id: filterPlanId.value || undefined
    }
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const data = await getMaintenanceTasks(params)
    tasks.value = data.items || []
  } catch (e) {
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (e) {
    ElMessage.error('加载设备失败')
  }
}

const createPlan = async () => {
  if (!planForm.value.name || !planForm.value.next_date) {
    ElMessage.warning('请填写必要信息')
    return
  }
  try {
    const device = devices.value.find(d => d.id === planForm.value.device_id)
    await createMaintenancePlan({
      ...planForm.value,
      device_name: device?.name
    })
    ElMessage.success('计划创建成功')
    showPlanDialog.value = false
    resetPlanForm()
    loadPlans()
    loadStats()
  } catch (e) {
    ElMessage.error('创建失败: ' + (e.response?.data?.detail || e.message))
  }
}

const editPlan = (row) => {
  editMode.value = true
  planForm.value = {
    id: row.id,
    name: row.name,
    device_id: row.device_id,
    plan_type: row.plan_type,
    cycle_days: row.cycle_days,
    next_date: row.next_date?.split('T')[0],
    data_basis: row.data_basis,
    auto_generate: row.auto_generate,
    status: row.status
  }
  showPlanDialog.value = true
}

const updatePlan = async () => {
  try {
    await updateMaintenancePlan(planForm.value.id, planForm.value)
    ElMessage.success('更新成功')
    showPlanDialog.value = false
    editMode.value = false
    resetPlanForm()
    loadPlans()
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

const deletePlan = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除计划 "${row.name}" 吗？`, '确认删除', { type: 'warning' })
    await deletePlanApi(row.id)
    ElMessage.success('删除成功')
    loadPlans()
    loadStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const resetPlanForm = () => {
  planForm.value = {
    id: null,
    name: '',
    device_id: null,
    plan_type: 'routine_check',
    cycle_days: 30,
    next_date: '',
    data_basis: '',
    auto_generate: true,
    status: 'active'
  }
}

const generateTasks = async () => {
  try {
    const result = await generateTasksForPlans()
    ElMessage.success(result.message)
    loadTasks()
    loadStats()
  } catch (e) {
    ElMessage.error('生成任务失败')
  }
}

const startTask = async (row) => {
  try {
    await startMaintenanceTask(row.id)
    ElMessage.success('任务已开始')
    loadTasks()
    loadStats()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '开始失败')
  }
}

// 搜索备件
const searchParts = async (query) => {
  if (!query || query.length < 1) {
    partOptions.value = []
    return
  }
  partsLoading.value = true
  try {
    const result = await getPartList({ search: query, limit: 20 })
    partOptions.value = result.items || []
  } catch (e) {
    console.error('搜索备件失败:', e)
  } finally {
    partsLoading.value = false
  }
}

// 加载初始备件列表
const loadInitialParts = async () => {
  partsLoading.value = true
  try {
    const result = await getPartList({ limit: 50 })
    partOptions.value = result.items || []
  } catch (e) {
    console.error('加载备件失败:', e)
  } finally {
    partsLoading.value = false
  }
}

// 添加备件到完成表单
const addPartToComplete = () => {
  if (!selectedPart.value) return

  const part = partOptions.value.find(p => p.id === selectedPart.value)
  if (!part) return

  // 检查是否已添加
  const existing = completeForm.value.parts.find(p => p.part_id === part.id)
  if (existing) {
    existing.quantity += 1
  } else {
    completeForm.value.parts.push({
      part_id: part.id,
      part_number: part.part_number,
      name: part.name,
      unit_price: part.unit_price || 0,
      quantity: 1,
      max_qty: part.quantity_in_stock
    })
  }

  updatePartsCost()
  selectedPart.value = null
}

// 移除备件
const removePart = (index) => {
  completeForm.value.parts.splice(index, 1)
  updatePartsCost()
}

// 更新备件成本
const updatePartsCost = () => {
  completeForm.value.parts_cost = completeForm.value.parts.reduce(
    (sum, p) => sum + p.quantity * p.unit_price, 0
  )
}

// 添加返回件
const addReturnPart = () => {
  if (!returnPartNumber.value && !selectedReturnPart.value) {
    ElMessage.warning('请输入返回件型号或从备件库选择')
    return
  }

  let partNumber = returnPartNumber.value
  let partName = returnPartName.value
  let partId = null

  if (selectedReturnPart.value) {
    const part = partOptions.value.find(p => p.id === selectedReturnPart.value)
    if (part) {
      partId = part.id
      partNumber = part.part_number
      partName = part.name
    }
  }

  completeForm.value.return_parts.push({
    part_id: partId,
    part_number: partNumber,
    name: partName || partNumber,
    quantity: returnPartQty.value,
    scrap_in: selectedReturnPart.value ? returnPartScrap.value : false
  })

  // 清空输入
  selectedReturnPart.value = null
  returnPartNumber.value = ''
  returnPartName.value = ''
  returnPartQty.value = 1
  returnPartScrap.value = true
}

// 移除返回件
const removeReturnPart = (index) => {
  completeForm.value.return_parts.splice(index, 1)
}

const showCompleteDialog = async (row) => {
  currentTask.value = row
  completeForm.value = {
    description: `计划性运维任务 ${row.task_no} 完成`,
    parts: [],
    parts_cost: 0,
    return_parts: [],
    labor_hours: 0,
    labor_cost: 0
  }
  selectedPart.value = null
  selectedReturnPart.value = null
  returnPartNumber.value = ''
  returnPartName.value = ''
  returnPartQty.value = 1
  returnPartScrap.value = true
  partOptions.value = []

  // 预加载备件列表
  await loadInitialParts()
  showCompleteDialogFlag.value = true
}

const completeTask = async () => {
  try {
    // 构建提交数据 - 合并备件和返回件
    const combinedParts = [
      ...completeForm.value.parts.map(p => ({ ...p, is_return: false })),
      ...completeForm.value.return_parts.map(p => ({ ...p, is_return: true }))
    ]

    await completeMaintenanceTask(currentTask.value.id, {
      description: completeForm.value.description,
      parts_replaced: JSON.stringify(combinedParts),
      parts_cost: completeForm.value.parts_cost,
      labor_hours: completeForm.value.labor_hours,
      labor_cost: completeForm.value.labor_cost
    })

    // 处理备件出库
    for (const part of completeForm.value.parts) {
      await createMovement({
        part_id: part.part_id,
        movement_type: 'out',
        quantity: part.quantity,
        reason: `计划性运维 - ${currentTask.value.task_no}`,
        operator: 'Web',
        reference: currentTask.value.device_name || '计划运维'
      })
    }

    // 处理返回件入报废库
    for (const part of completeForm.value.return_parts) {
      if (part.scrap_in && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'scrap_in',
          quantity: part.quantity,
          reason: `运维返回件入库 - 报废`,
          operator: 'Web',
          reference: currentTask.value.device_name || '计划运维'
        })
      }
    }

    ElMessage.success('任务已完成')
    showCompleteDialogFlag.value = false
    loadTasks()
    loadStats()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '完成失败')
  }
}

const skipTask = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt('请输入跳过原因', '跳过任务', {
      inputPlaceholder: '跳过原因（可选）'
    })
    await skipMaintenanceTask(row.id, value || '')
    ElMessage.success('任务已跳过')
    loadTasks()
    loadStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('跳过失败')
  }
}

const deleteTask = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除任务 "${row.task_no}" 吗？`, '确认删除', { type: 'warning' })
    await deleteTaskApi(row.id)
    ElMessage.success('删除成功')
    loadTasks()
    loadStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const showTaskDetail = (row) => {
  router.push(`/planned-maintenance/tasks/${row.id}`)
}

onMounted(() => {
  loadStats()
  loadPlans()
  loadTasks()
  loadDevices()
})
</script>

<style scoped>
.planned-maintenance-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.actions {
  display: flex;
  gap: 10px;
}

.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.stat-card {
  text-align: center;
}

.stat-item {
  padding: 10px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #409EFF;
}

.stat-value.success {
  color: #67C23A;
}

.stat-value.warning {
  color: #E6A23C;
}

.stat-value.danger {
  color: #F56C6C;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

/* 备件选择区域 */
.parts-section {
  width: 100%;
}

.selected-parts {
  margin-top: 12px;
}

.parts-summary {
  margin-top: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  text-align: right;
}

.total-cost {
  font-weight: 600;
  color: #409EFF;
  font-size: 16px;
}

/* 备件下拉选项样式 */
.part-option {
  display: flex;
  align-items: center;
  gap: 12px;
}

.part-number {
  font-weight: 500;
  color: #409EFF;
}

.part-name {
  color: #606266;
}

.part-stock {
  font-size: 12px;
  color: #909399;
}

.part-stock.low {
  color: #F56C6C;
  font-weight: 500;
}

/* 返回件区域 */
.return-section {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.return-parts-table {
  margin-top: 8px;
}

@media (max-width: 768px) {
  .filter-bar {
    flex-wrap: wrap;
  }
  .filter-bar .el-select, .filter-bar .el-date-picker {
    width: 100% !important;
  }
  .return-section {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>