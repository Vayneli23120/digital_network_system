<template>
  <div class="pm-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('menuPlannedMaintenance') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn" @click="showPlanDialog = true">
          <el-icon><Plus /></el-icon>
          <span>{{ t('pmCreatePlan') }}</span>
        </button>
        <button class="nav-action-btn success" @click="generateTasks">
          <el-icon><Refresh /></el-icon>
          <span>{{ t('pmAutoGenerate') }}</span>
        </button>
        <button class="nav-action-btn secondary" @click="refreshAll" :disabled="loading">
          <el-icon><Refresh /></el-icon>
        </button>
      </div>
    </section>

    <!-- 顶部统计 Dashboard -->
    <section class="stats-dashboard">
      <div class="stats-grid">
        <!-- 总任务 -->
        <div class="stat-card total" @click="filterByStatus('')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.tasks?.total || 0 }}</div>
              <div class="metric-label">{{ t('pmStatsTotal') }}</div>
            </div>
            <div class="card-trend stable">
              <span class="trend-icon">●</span>
            </div>
          </div>
        </div>
        <!-- 已完成 -->
        <div class="stat-card completed" @click="filterByStatus('completed')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.tasks?.completed || 0 }}</div>
              <div class="metric-label">{{ t('pmStatsCompleted') }}</div>
            </div>
            <div class="card-trend success">
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
        <!-- 待执行 -->
        <div class="stat-card pending" @click="filterByStatus('pending')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value">{{ stats.tasks?.pending || 0 }}</div>
              <div class="metric-label">{{ t('pmStatsPending') }}</div>
            </div>
            <div class="card-trend warning" v-if="stats.tasks?.pending > 0">
              <el-icon><Warning /></el-icon>
            </div>
          </div>
        </div>
        <!-- 已超期 -->
        <div class="stat-card overdue" @click="filterByStatus('overdue')">
          <div class="card-content">
            <div class="card-icon">
              <el-icon><WarningFilled /></el-icon>
            </div>
            <div class="card-body">
              <div class="metric-value danger-text">{{ stats.tasks?.overdue || 0 }}</div>
              <div class="metric-label">{{ t('pmStatsOverdue') }}</div>
            </div>
            <div class="card-trend danger" v-if="stats.tasks?.overdue > 0">
              <el-icon><Warning /></el-icon>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 高级筛选工具栏 -->
    <section class="filter-section">
      <div class="filter-toolbar">
        <!-- 状态 Chips -->
        <div class="status-chips">
          <div
            :class="['status-chip', { active: filterStatus === '' }]"
            @click="filterByStatus('')"
          >
            <span class="chip-label">{{ t('faultFilterAll') }}</span>
            <span class="chip-count">{{ stats.tasks?.total || 0 }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-pending', { active: filterStatus === 'pending' }]"
            @click="filterByStatus('pending')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('pmStatsPending') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-progress', { active: filterStatus === 'in_progress' }]"
            @click="filterByStatus('in_progress')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('statusRunning') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-completed', { active: filterStatus === 'completed' }]"
            @click="filterByStatus('completed')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('pmStatsCompleted') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-overdue', { active: filterStatus === 'overdue' }]"
            @click="filterByStatus('overdue')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('pmStatsOverdue') }}</span>
          </div>
          <div
            :class="['status-chip', 'chip-skipped', { active: filterStatus === 'skipped' }]"
            @click="filterByStatus('skipped')"
          >
            <span class="chip-dot"></span>
            <span class="chip-label">{{ t('taskDetailTimelineSkipped') }}</span>
          </div>
        </div>

        <!-- 更多筛选 -->
        <div class="more-filters">
          <el-select v-model="filterPlanId" :placeholder="t('pmFilterPlan')" clearable style="width: 180px" @change="loadTasks">
            <el-option v-for="p in plans" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            :range-separator="t('faultToDate')"
            :start-placeholder="t('faultStartDate')"
            :end-placeholder="t('faultEndDate')"
            value-format="YYYY-MM-DD"
            style="width: 220px"
            @change="loadTasks"
          />
        </div>
      </div>
    </section>

    <!-- 任务数据面板 -->
    <section class="data-section">
      <div class="table-header">
        <span class="table-title">Task List</span>
        <span class="table-count">{{ tasks.length }} records</span>
      </div>

      <el-table
        :data="tasks"
        class="enterprise-table"
        v-loading="loading"
        :header-cell-style="{ background: 'transparent' }"
      >
        <!-- 任务单号 -->
        <el-table-column prop="task_no" :label="t('pmColTaskNo')" width="200">
          <template #default="{ row }">
            <router-link :to="`/planned-maintenance/tasks/${row.id}`" class="task-no-link">
              <span class="task-no-badge">{{ row.task_no }}</span>
              <el-icon class="link-arrow"><ArrowRight /></el-icon>
            </router-link>
          </template>
        </el-table-column>

        <!-- 状态 -->
        <el-table-column prop="status" :label="t('pmColStatus')" width="100">
          <template #default="{ row }">
            <div :class="['status-badge', row.status]">
              <span class="status-dot"></span>
              <span class="status-text">{{ getStatusText(row.status) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 设备 -->
        <el-table-column prop="device_name" :label="t('pmColDevice')" width="160">
          <template #default="{ row }">
            <div class="device-cell">
              <el-icon class="device-icon"><Connection /></el-icon>
              <span class="device-name">{{ row.device_name }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 计划日期 -->
        <el-table-column prop="scheduled_date" :label="t('pmColScheduledDate')" width="160">
          <template #default="{ row }">
            <div class="time-cell">
              <el-icon class="time-icon"><Clock /></el-icon>
              <span class="time-text">{{ formatDate(row.scheduled_date) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 实际日期 -->
        <el-table-column prop="actual_date" :label="t('pmColActualDate')" width="160">
          <template #default="{ row }">
            <div class="time-cell" v-if="row.actual_date">
              <el-icon class="time-icon"><CircleCheck /></el-icon>
              <span class="time-text">{{ formatDate(row.actual_date) }}</span>
            </div>
            <span class="empty-text" v-else>--</span>
          </template>
        </el-table-column>

        <!-- 备注 -->
        <el-table-column prop="notes" :label="t('pmColNotes')">
          <template #default="{ row }">
            <span class="notes-text">{{ row.notes || '--' }}</span>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column :label="t('pmColAction')" width="200" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <button v-if="row.status === 'pending' || row.status === 'overdue'" class="action-btn start" @click="startTask(row)" title="开始">
                <el-icon><VideoPlay /></el-icon>
              </button>
              <button v-if="row.status === 'in_progress'" class="action-btn complete" @click="showCompleteDialog(row)" title="完成">
                <el-icon><CircleCheck /></el-icon>
              </button>
              <button v-if="row.status === 'pending' || row.status === 'overdue'" class="action-btn skip" @click="skipTask(row)" title="跳过">
                <el-icon><Right /></el-icon>
              </button>
              <button v-if="row.status === 'pending'" class="action-btn delete" @click="deleteTask(row)" title="删除">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 维护计划数据面板 -->
    <section class="data-section">
      <div class="table-header">
        <span class="table-title">Plan List</span>
        <span class="table-count">{{ plans.length }} records</span>
      </div>

      <el-table :data="plans" class="enterprise-table" :header-cell-style="{ background: 'transparent' }">
        <!-- 计划名称 -->
        <el-table-column prop="name" :label="t('pmPlanName')" width="200">
          <template #default="{ row }">
            <span class="plan-name">{{ row.name }}</span>
          </template>
        </el-table-column>

        <!-- 设备 -->
        <el-table-column prop="device_name" :label="t('pmColDevice')" width="160">
          <template #default="{ row }">
            <div class="device-cell">
              <el-icon class="device-icon"><Connection /></el-icon>
              <span class="device-name">{{ row.device_name || '--' }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 类型 -->
        <el-table-column prop="plan_type" :label="t('pmPlanType')" width="120">
          <template #default="{ row }">
            <div :class="['type-badge', row.plan_type]">
              <span class="type-text">{{ getPlanTypeText(row.plan_type) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 周期 -->
        <el-table-column prop="cycle_days" :label="t('pmPlanCycle')" width="100">
          <template #default="{ row }">
            <span class="cycle-badge">{{ row.cycle_days }}天</span>
          </template>
        </el-table-column>

        <!-- 下次日期 -->
        <el-table-column prop="next_date" :label="t('pmPlanNextDate')" width="160">
          <template #default="{ row }">
            <div class="time-cell">
              <el-icon class="time-icon"><Calendar /></el-icon>
              <span class="time-text">{{ formatDate(row.next_date) }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 数据依据 -->
        <el-table-column prop="data_basis" :label="t('pmPlanDataBasis')">
          <template #default="{ row }">
            <span class="notes-text">{{ row.data_basis || '--' }}</span>
          </template>
        </el-table-column>

        <!-- 状态 -->
        <el-table-column prop="status" :label="t('pmPlanStatus')" width="100">
          <template #default="{ row }">
            <div :class="['status-badge', row.status === 'active' ? 'active' : 'paused']">
              <span class="status-dot"></span>
              <span class="status-text">{{ row.status === 'active' ? t('pmPlanStatusActive') : t('pmPlanStatusPaused') }}</span>
            </div>
          </template>
        </el-table-column>

        <!-- 操作 -->
        <el-table-column :label="t('pmColAction')" width="150" fixed="right">
          <template #default="{ row }">
            <div class="action-group">
              <button class="action-btn edit" @click="editPlan(row)" title="编辑">
                <el-icon><Edit /></el-icon>
              </button>
              <button class="action-btn delete" @click="deletePlan(row)" title="删除">
                <el-icon><Delete /></el-icon>
              </button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <!-- 创建/编辑计划对话框 -->
    <el-dialog v-model="showPlanDialog" :title="editMode ? t('pmEditPlan') : t('pmCreatePlan')" width="600px" class="plan-dialog">
      <div class="dialog-content">
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Document /></el-icon>
            {{ t('pmPlanBasicInfo') || '计划基础信息' }}
          </div>
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
              <el-select v-model="planForm.plan_type" style="width: 100%">
                <el-option :label="t('pmPlanTypeRoutine')" value="routine_check" />
                <el-option :label="t('pmPlanTypeParts')" value="parts_replace" />
                <el-option :label="t('pmPlanTypeVendor')" value="vendor_service" />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('pmPlanCycle')" required>
              <el-input-number v-model="planForm.cycle_days" :min="1" :max="365" style="width: 100%" />
            </el-form-item>
            <el-form-item :label="t('pmPlanNextDateLabel')" required>
              <el-date-picker v-model="planForm.next_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-form>
        </div>
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><InfoFilled /></el-icon>
            {{ t('pmPlanDetailInfo') || '详细信息' }}
          </div>
          <el-form :model="planForm" label-width="120px">
            <el-form-item :label="t('pmPlanDataBasis')">
              <el-input v-model="planForm.data_basis" type="textarea" :rows="3" :placeholder="t('pmPlanDataBasisPlaceholder')" />
            </el-form-item>
            <el-form-item :label="t('pmPlanAutoGenerateLabel')">
              <el-switch v-model="planForm.auto_generate" />
            </el-form-item>
            <el-form-item :label="t('pmPlanStatus')" v-if="editMode">
              <el-select v-model="planForm.status" style="width: 100%">
                <el-option :label="t('pmPlanStatusActive')" value="active" />
                <el-option :label="t('pmPlanStatusPaused')" value="paused" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showPlanDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updatePlan() : createPlan()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 完成任务对话框 -->
    <el-dialog v-model="showCompleteDialogFlag" :title="t('pmCompleteTitle')" width="700px" class="complete-dialog">
      <div class="dialog-content">
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Document /></el-icon>
            {{ t('pmCompleteDesc') || '完成说明' }}
          </div>
          <el-form :model="completeForm" label-width="120px">
            <el-form-item :label="t('pmCompleteDesc')">
              <el-input v-model="completeForm.description" type="textarea" :rows="3" :placeholder="t('pmCompleteDescPlaceholder')" />
            </el-form-item>
          </el-form>
        </div>

        <!-- 备件更换 -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Tools /></el-icon>
            {{ t('pmReplacePartsSection') }}
          </div>
          <el-form :model="completeForm" label-width="120px">
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
                      <template #default="{ row }">
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
                <div class="empty-parts" v-else>
                  <el-tag type="info">{{ t('pmNoReplaceParts') }}</el-tag>
                </div>
              </div>
            </el-form-item>
          </el-form>
        </div>

        <!-- 返回件 -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><RefreshLeft /></el-icon>
            {{ t('pmReturnPartsSection') }}
          </div>
          <el-form :model="completeForm" label-width="120px">
            <el-form-item :label="t('pmReturnPartsLabel')">
              <div class="return-section">
                <el-select
                  v-model="selectedReturnPart"
                  :placeholder="t('pmReturnSelectPlaceholder')"
                  filterable
                  remote
                  :remote-method="searchParts"
                  style="width: 180px"
                  clearable
                >
                  <el-option v-for="part in partOptions" :key="part.id" :label="`${part.part_number} - ${part.name}`" :value="part.id" />
                </el-select>
                <el-input v-model="returnPartNumber" :placeholder="t('pmReturnModelPlaceholder')" style="width: 120px" />
                <el-input v-model="returnPartName" :placeholder="t('pmReturnNamePlaceholder')" style="width: 120px" />
                <div class="qty-input">
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
          </el-form>
        </div>

        <!-- 工时成本 -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Coin /></el-icon>
            {{ t('pmCostSection') || '成本信息' }}
          </div>
          <el-form :model="completeForm" label-width="120px">
            <el-form-item :label="t('pmLaborHoursLabel')">
              <el-input-number v-model="completeForm.labor_hours" :min="0" :precision="1" style="width: 100%" />
            </el-form-item>
            <el-form-item :label="t('pmLaborCostLabel')">
              <el-input-number v-model="completeForm.labor_cost" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-form>
        </div>
      </div>
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
import { Plus, Refresh, Document, Clock, CircleCheck, Warning, WarningFilled, ArrowRight, Connection, Edit, Delete, VideoPlay, Right, Calendar, Tools, RefreshLeft, Coin, InfoFilled } from '@element-plus/icons-vue'
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

const getStatusText = (status) => {
  const texts = { pending: t('pmStatsPending'), in_progress: t('statusRunning'), completed: t('pmStatsCompleted'), overdue: t('pmStatsOverdue'), skipped: t('taskDetailTimelineSkipped') }
  return texts[status] || status
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

const filterByStatus = (status) => {
  filterStatus.value = status
  loadTasks()
}

const refreshAll = async () => {
  loading.value = true
  try {
    await Promise.all([loadStats(), loadPlans(), loadTasks()])
  } finally {
    loading.value = false
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

onMounted(() => {
  loadStats()
  loadPlans()
  loadTasks()
  loadDevices()
})
</script>

<style scoped>
/* 字体清晰度优化 - 所有等宽字体 */
.task-no-badge,
.metric-value,
.chip-count,
.table-count,
.cycle-badge,
.time-text,
.total-cost {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

/* ===== 页面整体背景 ===== */
.pm-page {
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
  background: linear-gradient(90deg, #00b894, #55efc4, #0984e3);
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
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  color: white;
  border: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.25);
}

.nav-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 184, 148, 0.35);
}

.nav-action-btn.success {
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
  box-shadow: 0 2px 8px rgba(9, 132, 227, 0.25);
}

.nav-action-btn.success:hover {
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
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, transparent 40%, rgba(0, 184, 148, 0.05) 100%);
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

.stat-card.total .card-icon {
  background: linear-gradient(135deg, rgba(9, 132, 227, 0.15) 0%, rgba(9, 132, 227, 0.08) 100%);
  color: #0984e3;
}
.stat-card.completed .card-icon {
  background: linear-gradient(135deg, rgba(0, 184, 148, 0.2) 0%, rgba(0, 184, 148, 0.1) 100%);
  color: #00b894;
}
.stat-card.pending .card-icon {
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.2) 0%, rgba(251, 191, 36, 0.1) 100%);
  color: #f59e0b;
}
.stat-card.overdue .card-icon {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(239, 68, 68, 0.1) 100%);
  color: #ef4444;
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

.metric-value.danger-text {
  color: #ef4444;
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
.card-trend.success { background: rgba(0, 184, 148, 0.1); color: #00b894; }
.card-trend.warning { background: rgba(251, 191, 36, 0.1); color: #f59e0b; }
.card-trend.danger { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

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

/* Status Chips */
.status-chips {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.status-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  cursor: pointer;
  transition: all 0.25s ease;
  position: relative;
  overflow: hidden;
}

.status-chip::before {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  right: 50%;
  height: 2px;
  background: currentColor;
  transition: all 0.25s ease;
}

.status-chip:hover::before,
.status-chip.active::before {
  left: 0;
  right: 0;
}

.status-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.1);
}

.status-chip.active {
  background: rgba(0, 184, 148, 0.08);
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}

.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.chip-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.status-chip.active .chip-label {
  color: #00b894;
}

.chip-count {
  font-size: 11px;
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  color: var(--text-tertiary);
  padding: 2px 6px;
  background: rgba(0, 48, 135, 0.05);
  border-radius: 4px;
}

.status-chip.chip-pending .chip-dot { background: #f59e0b; }
.status-chip.chip-progress .chip-dot { background: #fd79a8; }
.status-chip.chip-completed .chip-dot { background: #00b894; }
.status-chip.chip-overdue .chip-dot { background: #ef4444; }
.status-chip.chip-skipped .chip-dot { background: #636e72; }

.status-chip.chip-pending:hover { background: rgba(251, 191, 36, 0.08); border-color: rgba(251, 191, 36, 0.3); }
.status-chip.chip-progress:hover { background: rgba(253, 121, 168, 0.08); border-color: rgba(253, 121, 168, 0.3); }
.status-chip.chip-completed:hover { background: rgba(0, 184, 148, 0.12); border-color: rgba(0, 184, 148, 0.4); }
.status-chip.chip-overdue:hover { background: rgba(239, 68, 68, 0.08); border-color: rgba(239, 68, 68, 0.3); }
.status-chip.chip-skipped:hover { background: rgba(45, 52, 54, 0.08); border-color: rgba(45, 52, 54, 0.3); }

.more-filters {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.more-filters :deep(.el-select .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  box-shadow: none;
}

.more-filters :deep(.el-date-editor) {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  border: 1px solid var(--border-default);
  box-shadow: none;
}

/* ===== 数据面板 ===== */
.data-section {
  padding: 16px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 4px 24px rgba(0, 48, 135, 0.08);
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.08);
}

.table-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.03em;
}

.table-count {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.enterprise-table { width: 100%; }

.enterprise-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.enterprise-table :deep(.el-table__header-wrapper) {
  border-bottom: 2px solid rgba(0, 48, 135, 0.1);
}

.enterprise-table :deep(th.el-table__cell) {
  background: transparent;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  letter-spacing: 0.03em;
  padding: 12px 0;
  border-bottom: none;
}

.enterprise-table :deep(td.el-table__cell) {
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
  padding: 10px 0;
  background: transparent;
}

.enterprise-table :deep(.el-table__row) {
  transition: all 0.25s ease;
  background: transparent;
}

.enterprise-table :deep(.el-table__row:hover > td) {
  background: rgba(0, 184, 148, 0.04) !important;
}

/* 任务单号链接 */
.task-no-link {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #00b894;
  text-decoration: none;
  transition: all 0.25s;
}

.task-no-link:hover {
  color: #55efc4;
}

.task-no-badge {
  font-family: 'JetBrains Mono', 'Geist Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-weight: 600;
  font-size: 13px;
  padding: 4px 8px;
  background: rgba(0, 184, 148, 0.08);
  border-radius: 6px;
  transition: all 0.25s;
}

.task-no-link:hover .task-no-badge {
  background: rgba(0, 184, 148, 0.15);
}

.link-arrow {
  opacity: 0;
  font-size: 12px;
  transition: all 0.25s;
  color: #00b894;
}

.task-no-link:hover .link-arrow {
  opacity: 1;
  transform: translateX(4px);
}

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-text {
  letter-spacing: 0.02em;
}

.status-badge.pending {
  border-color: rgba(251, 191, 36, 0.3);
  color: #f59e0b;
}
.status-badge.pending .status-dot { background: #f59e0b; }

.status-badge.in_progress {
  border-color: rgba(253, 121, 168, 0.3);
  color: #fd79a8;
}
.status-badge.in_progress .status-dot { background: #fd79a8; }

.status-badge.completed {
  border-color: rgba(0, 184, 148, 0.4);
  color: #00b894;
}
.status-badge.completed .status-dot { background: #00b894; }

.status-badge.overdue {
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}
.status-badge.overdue .status-dot { background: #ef4444; }

.status-badge.skipped {
  border-color: rgba(45, 52, 54, 0.3);
  color: #636e72;
}
.status-badge.skipped .status-dot { background: #636e72; }

.status-badge.active {
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}
.status-badge.active .status-dot { background: #00b894; }

.status-badge.paused {
  border-color: rgba(99, 110, 114, 0.3);
  color: #636e72;
}
.status-badge.paused .status-dot { background: #636e72; }

/* 设备单元格 */
.device-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.device-icon {
  font-size: 14px;
  color: var(--text-tertiary);
}

.device-name {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 时间单元格 */
.time-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-icon {
  font-size: 13px;
  color: var(--text-tertiary);
}

.time-text {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.empty-text {
  font-size: 13px;
  color: var(--text-tertiary);
}

.notes-text {
  font-size: 13px;
  color: var(--text-secondary);
}

.plan-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

/* 周期徽章 */
.cycle-badge {
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 2px 6px;
  background: rgba(9, 132, 227, 0.08);
  border-radius: 4px;
}

/* 类型徽章 */
.type-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
}

.type-badge.routine_check {
  background: rgba(0, 184, 148, 0.08);
  color: #00b894;
}

.type-badge.parts_replace {
  background: rgba(251, 191, 36, 0.08);
  color: #f59e0b;
}

.type-badge.vendor_service {
  background: rgba(9, 132, 227, 0.08);
  color: #0984e3;
}

/* 操作按钮组 */
.action-group {
  display: flex;
  gap: 4px;
}

.action-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.15);
}

.action-btn.start:hover {
  background: rgba(0, 184, 148, 0.08);
  border-color: rgba(0, 184, 148, 0.2);
  color: #00b894;
}

.action-btn.complete:hover {
  background: rgba(0, 184, 148, 0.12);
  border-color: rgba(0, 184, 148, 0.3);
  color: #00b894;
}

.action-btn.skip:hover {
  background: rgba(251, 191, 36, 0.08);
  border-color: rgba(251, 191, 36, 0.2);
  color: #f59e0b;
}

.action-btn.edit:hover {
  background: rgba(9, 132, 227, 0.08);
  border-color: rgba(9, 132, 227, 0.2);
  color: #0984e3;
}

.action-btn.delete:hover {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

/* ===== 对话框样式 ===== */
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

/* 备件选择区域 */
.parts-section {
  width: 100%;
}

.selected-parts {
  margin-top: 12px;
}

.empty-parts {
  margin-top: 8px;
}

.parts-summary {
  margin-top: 10px;
  padding: 8px 12px;
  background: rgba(0, 184, 148, 0.05);
  border-radius: 4px;
  text-align: right;
}

.total-cost {
  font-weight: 600;
  color: #00b894;
  font-size: 16px;
  font-family: 'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 备件下拉选项样式 */
.part-option {
  display: flex;
  align-items: center;
  gap: 12px;
}

.part-number {
  font-weight: 500;
  color: #0984e3;
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

.qty-input {
  display: flex;
  align-items: center;
  gap: 5px;
}

.return-parts-table {
  margin-top: 8px;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filter-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .status-chips {
    justify-content: center;
  }

  .more-filters {
    justify-content: center;
    margin-left: 0;
  }

  .page-nav-bar {
    flex-direction: column;
    gap: 12px;
  }

  .nav-right {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }

  .return-section {
    flex-direction: column;
    align-items: stretch;
  }
}

/* ===== 暗黑模式 ===== */
.dark .pm-page {
  background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 50%, #161b22 100%);
}

.dark .page-nav-bar {
  background: rgba(22, 27, 34, 0.9);
  border-color: rgba(48, 54, 61, 0.8);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .page-nav-bar::before {
  background: linear-gradient(90deg, #00b894, #55efc4, #0984e3);
}

.dark .page-title {
  color: #f0f6fc;
}

.dark .nav-action-btn {
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
}

.dark .nav-action-btn.success {
  background: linear-gradient(135deg, #0984e3 0%, #74b9ff 100%);
}

.dark .nav-action-btn.secondary {
  background: rgba(48, 54, 61, 0.8);
  color: #8b949e;
  border-color: #30363d;
}

.dark .nav-action-btn.secondary:hover {
  background: rgba(0, 184, 148, 0.15);
  border-color: #00b894;
  color: #55efc4;
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

.dark .metric-value.danger-text {
  color: #f85149;
}

.dark .metric-label {
  color: #8b949e;
}

.dark .card-trend.stable { background: rgba(9, 132, 227, 0.2); color: #58a6ff; }
.dark .card-trend.success { background: rgba(63, 185, 80, 0.2); color: #3fb950; }
.dark .card-trend.warning { background: rgba(210, 153, 34, 0.2); color: #d29922; }
.dark .card-trend.danger { background: rgba(248, 81, 73, 0.2); color: #f85149; }

.dark .filter-section {
  background: rgba(22, 27, 34, 0.85);
  border-color: rgba(48, 54, 61, 0.6);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.dark .status-chip {
  background: rgba(13, 17, 23, 0.9);
  border-color: #30363d;
}

.dark .status-chip:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .chip-label {
  color: #8b949e;
}

.dark .status-chip.active {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}

.dark .status-chip.active .chip-label {
  color: #3fb950;
}

.dark .chip-count {
  background: rgba(48, 54, 61, 0.3);
  color: #8b949e;
}

.dark .more-filters :deep(.el-select .el-input__wrapper),
.dark .more-filters :deep(.el-date-editor) {
  background: rgba(13, 17, 23, 0.95);
  border-color: #30363d;
}

/* 状态徽章暗黑模式 */
.dark .status-badge {
  background: rgba(13, 17, 23, 0.9);
}

.dark .status-badge.pending {
  border-color: rgba(210, 153, 34, 0.4);
  color: #d29922;
}
.dark .status-badge.pending .status-dot { background: #d29922; }

.dark .status-badge.in_progress {
  border-color: rgba(253, 121, 168, 0.4);
  color: #fd79a8;
}
.dark .status-badge.in_progress .status-dot { background: #fd79a8; }

.dark .status-badge.completed {
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}
.dark .status-badge.completed .status-dot { background: #3fb950; }

.dark .status-badge.overdue {
  border-color: rgba(248, 81, 73, 0.4);
  color: #f85149;
}
.dark .status-badge.overdue .status-dot { background: #f85149; }

.dark .status-badge.skipped {
  border-color: rgba(139, 148, 158, 0.4);
  color: #8b949e;
}
.dark .status-badge.skipped .status-dot { background: #8b949e; }

.dark .status-badge.active {
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}
.dark .status-badge.active .status-dot { background: #3fb950; }

.dark .status-badge.paused {
  border-color: rgba(139, 148, 158, 0.4);
  color: #8b949e;
}
.dark .status-badge.paused .status-dot { background: #8b949e; }

/* 类型徽章暗黑模式 */
.dark .type-badge.routine_check {
  background: rgba(63, 185, 80, 0.15);
  color: #3fb950;
}

.dark .type-badge.parts_replace {
  background: rgba(210, 153, 34, 0.15);
  color: #d29922;
}

.dark .type-badge.vendor_service {
  background: rgba(88, 166, 255, 0.15);
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
  background: rgba(63, 185, 80, 0.08) !important;
}

.dark .task-no-link {
  color: #3fb950;
}

.dark .task-no-badge {
  background: rgba(63, 185, 80, 0.15);
}

.dark .task-no-link:hover .task-no-badge {
  background: rgba(63, 185, 80, 0.25);
}

.dark .link-arrow {
  color: #3fb950;
}

.dark .device-name {
  color: #c9d1d9;
}

.dark .time-text {
  color: #8b949e;
}

.dark .empty-text {
  color: #6e7681;
}

.dark .notes-text {
  color: #8b949e;
}

.dark .plan-name {
  color: #c9d1d9;
}

.dark .cycle-badge {
  background: rgba(88, 166, 255, 0.15);
  color: #8b949e;
}

.dark .action-btn {
  background: rgba(13, 17, 23, 0.9);
  color: #8b949e;
  border-color: transparent;
}

.dark .action-btn:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.dark .action-btn.start:hover {
  background: rgba(63, 185, 80, 0.15);
  border-color: rgba(63, 185, 80, 0.3);
  color: #3fb950;
}

.dark .action-btn.complete:hover {
  background: rgba(63, 185, 80, 0.2);
  border-color: rgba(63, 185, 80, 0.4);
  color: #3fb950;
}

.dark .action-btn.skip:hover {
  background: rgba(210, 153, 34, 0.15);
  border-color: rgba(210, 153, 34, 0.3);
  color: #d29922;
}

.dark .action-btn.edit:hover {
  background: rgba(88, 166, 255, 0.15);
  border-color: rgba(88, 166, 255, 0.3);
  color: #58a6ff;
}

.dark .action-btn.delete:hover {
  background: rgba(248, 81, 73, 0.15);
  border-color: rgba(248, 81, 73, 0.3);
  color: #f85149;
}

.dark .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .form-section-title {
  color: #8b949e;
}

.dark .parts-summary {
  background: rgba(63, 185, 80, 0.1);
}

.dark .total-cost {
  color: #3fb950;
}

.dark .part-number {
  color: #58a6ff;
}

.dark .part-name {
  color: #c9d1d9;
}

.dark .part-stock {
  color: #8b949e;
}

.dark .part-stock.low {
  color: #f85149;
}
</style>