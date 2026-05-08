<template>
  <div class="planned-maintenance-page">
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value">{{ stats.tasks?.total || 0 }}</div>
            <div class="stat-label">{{ t('pmStatsTotal') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value success">{{ stats.tasks?.completed || 0 }}</div>
            <div class="stat-label">{{ t('pmStatsCompleted') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value warning">{{ stats.tasks?.pending || 0 }}</div>
            <div class="stat-label">{{ t('pmStatsPending') }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-item">
            <div class="stat-value danger">{{ stats.tasks?.overdue || 0 }}</div>
            <div class="stat-label">{{ t('pmStatsOverdue') }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 任务列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('pmTasks') }}</span>
          <div class="actions">
            <el-button type="primary" @click="showPlanDialog = true">
              <el-icon><Plus /></el-icon>
              {{ t('pmCreatePlan') }}
            </el-button>
            <el-button type="success" @click="generateTasks">
              <el-icon><Refresh /></el-icon>
              {{ t('pmAutoGenerate') }}
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="filterStatus" :placeholder="t('pmFilterStatus')" clearable style="width: 120px" @change="loadTasks">
          <el-option :label="t('pmStatsPending')" value="pending" />
          <el-option :label="t('statusRunning')" value="in_progress" />
          <el-option :label="t('pmStatsCompleted')" value="completed" />
          <el-option :label="t('pmStatsOverdue')" value="overdue" />
          <el-option :label="t('taskDetailTimelineSkipped')" value="skipped" />
        </el-select>
        <el-select v-model="filterPlanId" :placeholder="t('pmFilterPlan')" clearable style="width: 200px" @change="loadTasks">
          <el-option v-for="p in plans" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          :range-separator="t('faultToDate')"
          :start-placeholder="t('faultStartDate')"
          :end-placeholder="t('faultEndDate')"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="loadTasks"
        />
      </div>

      <!-- 任务表格 -->
      <el-table :data="tasks" style="width: 100%" v-loading="loading">
        <el-table-column prop="task_no" :label="t('pmColTaskNo')" width="180">
          <template #default="{ row }">
            <el-link type="primary" @click="showTaskDetail(row)">{{ row.task_no }}</el-link>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" :label="t('pmColDevice')" width="160" />
        <el-table-column prop="scheduled_date" :label="t('pmColScheduledDate')" width="160">
          <template #default="{ row }">{{ formatDate(row.scheduled_date) }}</template>
        </el-table-column>
        <el-table-column prop="status" :label="t('pmColStatus')" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actual_date" :label="t('pmColActualDate')" width="160">
          <template #default="{ row }">{{ row.actual_date ? formatDate(row.actual_date) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="notes" :label="t('pmColNotes')" />
        <el-table-column :label="t('pmColAction')" width="200" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'pending' || row.status === 'overdue'" type="primary" size="small" @click="startTask(row)">{{ t('pmBtnStart') }}</el-button>
            <el-button v-if="row.status === 'in_progress'" type="success" size="small" @click="showCompleteDialog(row)">{{ t('pmBtnComplete') }}</el-button>
            <el-button v-if="row.status === 'pending' || row.status === 'overdue'" type="warning" size="small" @click="skipTask(row)">{{ t('pmBtnSkip') }}</el-button>
            <el-button v-if="row.status === 'pending'" type="danger" size="small" @click="deleteTask(row)">{{ t('pmBtnDelete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 维护计划列表 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <span>{{ t('pmPlans') }}</span>
      </template>
      <el-table :data="plans" style="width: 100%">
        <el-table-column prop="name" :label="t('pmPlanName')" width="200" />
        <el-table-column prop="device_name" :label="t('pmColDevice')" width="160" />
        <el-table-column prop="plan_type" :label="t('pmPlanType')" width="120">
          <template #default="{ row }">
            <el-tag :type="getPlanTypeColor(row.plan_type)">{{ getPlanTypeText(row.plan_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cycle_days" :label="t('pmPlanCycle')" width="100" />
        <el-table-column prop="next_date" :label="t('pmPlanNextDate')" width="160">
          <template #default="{ row }">{{ formatDate(row.next_date) }}</template>
        </el-table-column>
        <el-table-column prop="data_basis" :label="t('pmPlanDataBasis')" />
        <el-table-column prop="status" :label="t('pmPlanStatus')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? t('pmPlanStatusActive') : t('pmPlanStatusPaused') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('pmColAction')" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="editPlan(row)">{{ t('pmBtnEdit') }}</el-button>
            <el-button type="danger" size="small" @click="deletePlan(row)">{{ t('pmBtnDelete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑计划对话框 -->
    <el-dialog v-model="showPlanDialog" :title="editMode ? t('pmEditPlan') : t('pmCreatePlan')" width="600px">
      <el-form :model="planForm" label-width="120px">
        <el-form-item :label="t('pmPlanName')" required>
          <el-input v-model="planForm.name" :placeholder="t('pmPlanPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('deviceName')">
          <el-select v-model="planForm.device_id" :placeholder="t('pmPlanSelectDevice')" clearable filterable style="width: 100%">
            <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('pmPlanType')" required>
          <el-select v-model="planForm.plan_type">
            <el-option :label="t('pmPlanTypeRoutine')" value="routine_check" />
            <el-option :label="t('pmPlanTypeParts')" value="parts_replace" />
            <el-option :label="t('pmPlanTypeVendor')" value="vendor_service" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('pmPlanCycle')" required>
          <el-input-number v-model="planForm.cycle_days" :min="1" :max="365" />
        </el-form-item>
        <el-form-item :label="t('pmPlanNextDateLabel')" required>
          <el-date-picker v-model="planForm.next_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item :label="t('pmPlanDataBasis')">
          <el-input v-model="planForm.data_basis" type="textarea" :rows="3" :placeholder="t('pmPlanDataBasisPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('pmPlanAutoGenerateLabel')">
          <el-switch v-model="planForm.auto_generate" />
        </el-form-item>
        <el-form-item :label="t('pmPlanStatus')" v-if="editMode">
          <el-select v-model="planForm.status">
            <el-option :label="t('pmPlanStatusActive')" value="active" />
            <el-option :label="t('pmPlanStatusPaused')" value="paused" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPlanDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updatePlan() : createPlan()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 完成任务对话框 -->
    <el-dialog v-model="showCompleteDialogFlag" :title="t('pmCompleteTitle')" width="700px">
      <el-form :model="completeForm" label-width="120px">
        <el-form-item :label="t('pmCompleteDesc')">
          <el-input v-model="completeForm.description" type="textarea" :rows="3" :placeholder="t('pmCompleteDescPlaceholder')" />
        </el-form-item>

        <!-- 备件更换 -->
        <el-divider content-position="left">{{ t('pmReplacePartsSection') }}</el-divider>
        <el-form-item :label="t('pmSelectPart')">
          <div class="parts-section">
            <el-select
              v-model="selectedPart"
              :placeholder="t('pmSearchPartPlaceholder')"
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
                    {{ t('pmStockLabel') }}: {{ part.quantity_in_stock }}
                  </span>
                </div>
              </el-option>
            </el-select>

            <!-- 已选备件列表 -->
            <div class="selected-parts" v-if="completeForm.parts.length > 0">
              <el-table :data="completeForm.parts" size="small" border>
                <el-table-column prop="part_number" :label="t('pmColModel')" width="120" />
                <el-table-column prop="name" :label="t('pmColName')" width="120" />
                <el-table-column prop="quantity" :label="t('pmColQty')" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" :max="row.max_qty" size="small" @change="updatePartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" :label="t('pmColUnitPrice')" width="80">
                  <template #default="{ row }">¥{{ row.unit_price.toFixed(2) }}</template>
                </el-table-column>
                <el-table-column :label="t('pmColSubtotal')" width="80">
                  <template #default="{ row }">¥{{ (row.quantity * row.unit_price).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column :label="t('pmColOperation')" width="60">
                  <template #default="{ $index }">
                    <el-button type="danger" size="small" link @click="removePart($index)">{{ t('pmBtnDelete') }}</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">{{ t('pmPartsTotalCost') }}: <span class="total-cost">¥{{ completeForm.parts_cost.toFixed(2) }}</span></div>
            </div>
            <el-tag v-else type="info">{{ t('pmNoReplaceParts') }}</el-tag>
          </div>
        </el-form-item>

        <!-- 返回件 -->
        <el-divider content-position="left">{{ t('pmReturnPartsSection') }}</el-divider>
        <el-form-item :label="t('pmReturnPartsLabel')">
          <div class="return-section">
            <el-select
              v-model="selectedReturnPart"
              :placeholder="t('pmReturnSelectPlaceholder')"
              filterable
              remote
              :remote-method="searchParts"
              style="width: 200px"
              clearable
            >
              <el-option v-for="part in partOptions" :key="part.id" :label="`${part.part_number} - ${part.name}`" :value="part.id" />
            </el-select>
            <el-input v-model="returnPartNumber" :placeholder="t('pmReturnModelPlaceholder')" style="width: 120px" />
            <el-input v-model="returnPartName" :placeholder="t('pmReturnNamePlaceholder')" style="width: 120px" />
            <div style="display: flex; align-items: center; gap: 5px;">
              <span>{{ t('pmReturnQtyLabel') }}:</span>
              <el-input-number v-model="returnPartQty" :min="1" style="width: 100px" controls-position="right" />
            </div>
            <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">{{ t('pmReturnScrapLabel') }}</el-checkbox>
            <el-button type="primary" size="small" :disabled="!returnPartNumber && !selectedReturnPart" @click="addReturnPart">{{ t('pmReturnBtnAdd') }}</el-button>
          </div>

          <div class="return-parts-table" v-if="completeForm.return_parts.length > 0">
            <el-table :data="completeForm.return_parts" size="small" border>
              <el-table-column prop="part_number" :label="t('pmColModel')" width="120" />
              <el-table-column prop="name" :label="t('pmColName')" width="120" />
              <el-table-column prop="quantity" :label="t('pmColQty')" width="60" />
              <el-table-column :label="t('pmReturnScrapLabel')" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.scrap_in" type="warning">{{ t('pmReturnScrapTag') }}</el-tag>
                  <el-tag v-else type="info">{{ t('pmReturnNoScrapTag') }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="t('pmColOperation')" width="60">
                <template #default="{ $index }">
                  <el-button type="danger" size="small" link @click="removeReturnPart($index)">{{ t('pmBtnDelete') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-form-item>

        <el-divider />
        <el-form-item :label="t('pmLaborHoursLabel')">
          <el-input-number v-model="completeForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item :label="t('pmLaborCostLabel')">
          <el-input-number v-model="completeForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCompleteDialogFlag = false">{{ t('actionCancel') }}</el-button>
        <el-button type="success" @click="completeTask">{{ t('pmBtnConfirmComplete') }}</el-button>
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
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
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
  const texts = { pending: t('pmStatsPending'), in_progress: t('statusRunning'), completed: t('pmStatsCompleted'), overdue: t('pmStatsOverdue'), skipped: t('taskDetailTimelineSkipped') }
  return texts[status] || status
}

const getPlanTypeColor = (type) => {
  const colors = { routine_check: 'success', parts_replace: 'warning', vendor_service: 'info' }
  return colors[type] || ''
}

const getPlanTypeText = (type) => {
  const texts = { routine_check: t('pmPlanTypeRoutine'), parts_replace: t('pmPlanTypeParts'), vendor_service: t('pmPlanTypeVendor') }
  return texts[type] || type
}

const loadStats = async () => {
  try {
    const data = await getPlannedMaintenanceStats()
    stats.value = data
  } catch (e) {
    console.error(t('pmMsgLoadStatsFailed'), e)
  }
}

const loadPlans = async () => {
  try {
    const data = await getMaintenancePlans()
    plans.value = data.items || []
  } catch (e) {
    ElMessage.error(t('pmMsgLoadPlansFailed'))
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
    ElMessage.error(t('pmMsgLoadTasksFailed'))
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (e) {
    ElMessage.error(t('pmMsgLoadDevicesFailed'))
  }
}

const createPlan = async () => {
  if (!planForm.value.name || !planForm.value.next_date) {
    ElMessage.warning(t('pmMsgFillRequired'))
    return
  }
  try {
    const device = devices.value.find(d => d.id === planForm.value.device_id)
    await createMaintenancePlan({
      ...planForm.value,
      device_name: device?.name
    })
    ElMessage.success(t('pmMsgPlanCreateSuccess'))
    showPlanDialog.value = false
    resetPlanForm()
    loadPlans()
    loadStats()
  } catch (e) {
    ElMessage.error(t('pmMsgPlanCreateFailed') + ': ' + (e.response?.data?.detail || e.message))
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
    ElMessage.success(t('pmMsgPlanUpdateSuccess'))
    showPlanDialog.value = false
    editMode.value = false
    resetPlanForm()
    loadPlans()
  } catch (e) {
    ElMessage.error(t('pmMsgPlanUpdateFailed'))
  }
}

const deletePlan = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('pmMsgConfirmDeletePlan')} "${row.name}" ?`, t('pmMsgConfirmDelete'), { type: 'warning' })
    await deletePlanApi(row.id)
    ElMessage.success(t('pmMsgPlanDeleteSuccess'))
    loadPlans()
    loadStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('pmMsgPlanDeleteFailed'))
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
    ElMessage.error(t('pmMsgGenerateFailed'))
  }
}

const startTask = async (row) => {
  try {
    await startMaintenanceTask(row.id)
    ElMessage.success(t('pmMsgTaskStartSuccess'))
    loadTasks()
    loadStats()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('pmMsgTaskStartFailed'))
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
    console.error(t('maintSearchFailed'), e)
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
    console.error(t('spareLoadFailed'), e)
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
    ElMessage.warning(t('pmMsgReturnPartRequired'))
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
    description: `${t('pmTitle')} ${row.task_no} ${t('pmStatsCompleted')}`,
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
        reason: `${t('pmTitle')} - ${currentTask.value.task_no}`,
        operator: 'Web',
        reference: currentTask.value.device_name || t('pmTitle')
      })
    }

    // 处理返回件入报废库
    for (const part of completeForm.value.return_parts) {
      if (part.scrap_in && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'scrap_in',
          quantity: part.quantity,
          reason: `${t('pmReturnPartsSection')} - ${t('scrapScrap')}`,
          operator: 'Web',
          reference: currentTask.value.device_name || t('pmTitle')
        })
      }
    }

    ElMessage.success(t('pmMsgTaskCompleteSuccess'))
    showCompleteDialogFlag.value = false
    loadTasks()
    loadStats()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('pmMsgTaskCompleteFailed'))
  }
}

const skipTask = async (row) => {
  try {
    const { value } = await ElMessageBox.prompt(t('pmMsgSkipReasonPrompt'), t('pmMsgSkipTaskTitle'), {
      inputPlaceholder: t('pmMsgSkipReasonPlaceholder')
    })
    await skipMaintenanceTask(row.id, value || '')
    ElMessage.success(t('pmMsgTaskSkipSuccess'))
    loadTasks()
    loadStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('pmMsgTaskSkipFailed'))
  }
}

const deleteTask = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('pmMsgConfirmDeleteTask')} "${row.task_no}" ?`, t('pmMsgConfirmDelete'), { type: 'warning' })
    await deleteTaskApi(row.id)
    ElMessage.success(t('pmMsgTaskDeleteSuccess'))
    loadTasks()
    loadStats()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('pmMsgTaskDeleteFailed'))
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