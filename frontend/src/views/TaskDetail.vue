<template>
  <div class="task-detail-page">
    <el-page-header @back="goBack" :title="t('taskDetailBack')">
      <template #content>
        <span class="page-title">{{ task.task_no || t('taskDetailTitle') }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：任务信息 -->
      <el-col :span="16">
        <el-card class="task-info-card">
          <template #header>
            <span>{{ t('taskDetailInfo') }}</span>
          </template>

          <el-descriptions :column="2" border v-if="task.id">
            <el-descriptions-item :label="t('taskDetailNo')">{{ task.task_no }}</el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailDevice')">
              <router-link v-if="task.device_id" :to="`/devices/${task.device_id}`">{{ task.device_name }}</router-link>
              <span v-else>{{ task.device_name || t('taskDetailGenericTask') }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailScheduledDate')">{{ formatDate(task.scheduled_date) }}</el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailCurrentStatus')">
              <el-tag :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailActualDate')">
              {{ task.actual_date ? formatDate(task.actual_date) : t('taskDetailNotExecuted') }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailRelatedPlan')">
              <span v-if="task.plan">{{ task.plan.name }} ({{ getPlanTypeText(task.plan.plan_type) }})</span>
              <span v-else>{{ t('taskDetailManualCreated') }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailNotes')">{{ task.notes || t('taskDetailNoNotes') }}</el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailCreatedAt')">{{ formatDateTime(task.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 维修执行详情（已完成时显示） -->
        <el-card style="margin-top: 20px" v-if="task.maintenance">
          <template #header>
            <span>{{ t('taskDetailMaintInfo') }}</span>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item :label="t('taskDetailMaintNo')">
              <router-link :to="`/maintenance/${task.maintenance.id}`">{{ task.maintenance.maint_no }}</router-link>
            </el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailMaintType')">
              <el-tag>{{ getMaintTypeText(task.maintenance.maint_type) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailPartsCost')">¥{{ task.maintenance.parts_cost?.toFixed(2) || '0.00' }}</el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailLaborCost')">¥{{ task.maintenance.labor_cost?.toFixed(2) || '0.00' }}</el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailTotalCost')">
              <span class="total-cost">¥{{ ((task.maintenance.parts_cost || 0) + (task.maintenance.labor_cost || 0)).toFixed(2) }}</span>
            </el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailMaintTime')">{{ formatDateTime(task.maintenance.maint_time) }}</el-descriptions-item>
          </el-descriptions>

          <!-- 更换备件详情 -->
          <el-divider v-if="parsedParts && parsedParts.length > 0">{{ t('taskDetailReplaceParts') }}</el-divider>
          <div v-if="parsedParts && parsedParts.length > 0" class="parts-detail">
            <el-table :data="parsedParts" size="small" border>
              <el-table-column prop="part_number" :label="t('taskDetailColModel')" width="120" />
              <el-table-column prop="name" :label="t('taskDetailColName')" width="150" />
              <el-table-column prop="quantity" :label="t('taskDetailColQty')" width="60" />
              <el-table-column :label="t('taskDetailReturnType')" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.is_return ? 'warning' : 'success'" size="small">
                    {{ row.is_return ? t('taskDetailReturnPart') : t('taskDetailReplace') }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="t('taskDetailScrapIn')" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.scrap_in" type="danger" size="small">{{ t('taskDetailScrapInTag') }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-divider>{{ t('taskDetailMaintDesc') }}</el-divider>
          <p class="description">{{ task.maintenance.description || t('taskDetailNoDesc') }}</p>
        </el-card>

        <!-- 操作按钮 -->
        <el-card style="margin-top: 20px">
          <el-space>
            <el-button
              v-if="task.status === 'pending' || task.status === 'overdue'"
              type="primary"
              @click="startTask"
            >
              <el-icon><VideoPlay /></el-icon>
              {{ t('taskDetailBtnStart') }}
            </el-button>
            <el-button
              v-if="task.status === 'in_progress'"
              type="success"
              @click="showCompleteDialog = true"
            >
              <el-icon><Check /></el-icon>
              {{ t('taskDetailBtnComplete') }}
            </el-button>
            <el-button
              v-if="task.status === 'pending' || task.status === 'overdue'"
              type="warning"
              @click="skipTask"
            >
              <el-icon><Close /></el-icon>
              {{ t('taskDetailBtnSkip') }}
            </el-button>
            <el-button
              v-if="task.status === 'pending'"
              type="danger"
              @click="deleteTask"
            >
              <el-icon><Delete /></el-icon>
              {{ t('taskDetailBtnDelete') }}
            </el-button>
          </el-space>
        </el-card>
      </el-col>

      <!-- 右侧：时间线和计划信息 -->
      <el-col :span="8">
        <el-card class="timeline-card">
          <template #header>
            <span>{{ t('taskDetailTimeline') }}</span>
          </template>

          <el-timeline>
            <el-timeline-item
              :timestamp="formatDateTime(task.created_at)"
              placement="top"
              color="#409EFF"
            >
              <el-card>
                <h4>{{ t('taskDetailTimelineCreated') }}</h4>
                <p>{{ t('taskDetailTimelinePlanDate') }}: {{ formatDate(task.scheduled_date) }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="task.status === 'in_progress'"
              :timestamp="t('taskDetailTimelineInProgress')"
              placement="top"
              color="#E6A23C"
            >
              <el-card>
                <h4>{{ t('taskDetailTimelineStarted') }}</h4>
                <p>{{ t('taskDetailTimelineExecuting') }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="task.status === 'completed'"
              :timestamp="formatDateTime(task.actual_date)"
              placement="top"
              color="#67C23A"
            >
              <el-card>
                <h4>{{ t('taskDetailTimelineCompleted') }}</h4>
                <p v-if="task.maintenance">{{ t('taskDetailTimelineMaintNo') }}: {{ task.maintenance.maint_no }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="task.status === 'skipped'"
              :timestamp="t('taskDetailTimelineSkipped')"
              placement="top"
              color="#909399"
            >
              <el-card>
                <h4>{{ t('taskDetailTimelineTaskSkipped') }}</h4>
                <p>{{ task.notes || t('taskDetailTimelineSkipReason') }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="task.status === 'overdue'"
              :timestamp="t('taskDetailTimelineOverdue')"
              placement="top"
              color="#F56C6C"
            >
              <el-card>
                <h4>{{ t('taskDetailTimelineTaskOverdue') }}</h4>
                <p>{{ t('taskDetailTimelineOverdueTip') }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- 关联计划信息 -->
        <el-card class="plan-card" style="margin-top: 20px" v-if="task.plan">
          <template #header>
            <span>{{ t('taskDetailRelatedPlanTitle') }}</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item :label="t('pmPlanName')">{{ task.plan.name }}</el-descriptions-item>
            <el-descriptions-item :label="t('pmPlanType')">
              <el-tag :type="getPlanTypeColor(task.plan.plan_type)" size="small">
                {{ getPlanTypeText(task.plan.plan_type) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('taskDetailPlanCycle')">{{ task.plan.cycle_days }} {{ t('taskDetailPlanCycleUnit') }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 完成任务对话框 -->
    <el-dialog v-model="showCompleteDialog" :title="t('taskDetailCompleteTitle')" width="700px">
      <el-form :model="completeForm" label-width="120px">
        <el-form-item :label="t('taskDetailCompleteDesc')">
          <el-input v-model="completeForm.description" type="textarea" :rows="3" :placeholder="t('taskDetailCompleteDescPlaceholder')" />
        </el-form-item>

        <!-- 备件更换 -->
        <el-divider content-position="left">{{ t('taskDetailReplacePartsSection') }}</el-divider>
        <el-form-item :label="t('taskDetailSelectPart')">
          <div class="parts-section">
            <el-select
              v-model="selectedPart"
              :placeholder="t('taskDetailSearchPartPlaceholder')"
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
                    {{ t('taskDetailStockLabel') }}: {{ part.quantity_in_stock }}
                  </span>
                </div>
              </el-option>
            </el-select>

            <div class="selected-parts" v-if="completeForm.parts.length > 0">
              <el-table :data="completeForm.parts" size="small" border>
                <el-table-column prop="part_number" :label="t('taskDetailColModel')" width="120" />
                <el-table-column prop="name" :label="t('taskDetailColName')" width="120" />
                <el-table-column prop="quantity" :label="t('taskDetailColQty')" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" :max="row.max_qty" size="small" @change="updatePartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" :label="t('taskDetailColUnitPrice')" width="80">
                  <template #default="{ row }">¥{{ row.unit_price.toFixed(2) }}</template>
                </el-table-column>
                <el-table-column :label="t('taskDetailColSubtotal')" width="80">
                  <template #default="{ row }">¥{{ (row.quantity * row.unit_price).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column :label="t('taskDetailColOperation')" width="60">
                  <template #default="{ $index }">
                    <el-button type="danger" size="small" link @click="removePart($index)">{{ t('pmBtnDelete') }}</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">{{ t('taskDetailPartsTotalCost') }}: <span class="total-cost">¥{{ completeForm.parts_cost.toFixed(2) }}</span></div>
            </div>
            <el-tag v-else type="info">{{ t('taskDetailNoReplaceParts') }}</el-tag>
          </div>
        </el-form-item>

        <!-- 返回件 -->
        <el-divider content-position="left">{{ t('taskDetailReturnPartsSection') }}</el-divider>
        <el-form-item :label="t('taskDetailReturnPartsLabel')">
          <div class="return-section">
            <el-select
              v-model="selectedReturnPart"
              :placeholder="t('taskDetailReturnSelectPlaceholder')"
              filterable
              remote
              :remote-method="searchParts"
              style="width: 200px"
              clearable
            >
              <el-option v-for="part in partOptions" :key="part.id" :label="`${part.part_number} - ${part.name}`" :value="part.id" />
            </el-select>
            <el-input v-model="returnPartNumber" :placeholder="t('taskDetailReturnModelPlaceholder')" style="width: 120px" />
            <el-input v-model="returnPartName" :placeholder="t('taskDetailReturnNamePlaceholder')" style="width: 120px" />
            <div style="display: flex; align-items: center; gap: 5px;">
              <span>{{ t('taskDetailReturnQtyLabel') }}:</span>
              <el-input-number v-model="returnPartQty" :min="1" style="width: 100px" controls-position="right" />
            </div>
            <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">{{ t('taskDetailReturnScrapLabel') }}</el-checkbox>
            <el-button type="primary" size="small" :disabled="!returnPartNumber && !selectedReturnPart" @click="addReturnPart">{{ t('taskDetailReturnBtnAdd') }}</el-button>
          </div>

          <div class="return-parts-table" v-if="completeForm.return_parts.length > 0">
            <el-table :data="completeForm.return_parts" size="small" border>
              <el-table-column prop="part_number" :label="t('taskDetailColModel')" width="120" />
              <el-table-column prop="name" :label="t('taskDetailColName')" width="120" />
              <el-table-column prop="quantity" :label="t('taskDetailColQty')" width="60" />
              <el-table-column :label="t('taskDetailReturnScrapLabel')" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.scrap_in" type="warning">{{ t('taskDetailReturnScrapTag') }}</el-tag>
                  <el-tag v-else type="info">{{ t('taskDetailReturnNoScrapTag') }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="t('taskDetailColOperation')" width="60">
                <template #default="{ $index }">
                  <el-button type="danger" size="small" link @click="removeReturnPart($index)">{{ t('pmBtnDelete') }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-form-item>

        <el-divider />
        <el-form-item :label="t('taskDetailLaborHoursLabel')">
          <el-input-number v-model="completeForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item :label="t('taskDetailLaborCostLabel')">
          <el-input-number v-model="completeForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCompleteDialog = false">{{ t('taskDetailBtnCancel') }}</el-button>
        <el-button type="success" @click="completeTask">{{ t('taskDetailBtnConfirmComplete') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, Check, Close, Delete } from '@element-plus/icons-vue'
import {
  getMaintenanceTask, startMaintenanceTask, completeMaintenanceTask, skipMaintenanceTask, deleteMaintenanceTask,
  getPartList, createMovement
} from '@/api'
import { formatDate, formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const task = ref({})
const showCompleteDialog = ref(false)

// 备件相关
const partOptions = ref([])
const partsLoading = ref(false)
const selectedPart = ref(null)
const selectedReturnPart = ref(null)
const returnPartNumber = ref('')
const returnPartName = ref('')
const returnPartQty = ref(1)
const returnPartScrap = ref(true)

const completeForm = ref({
  description: '',
  parts: [],
  parts_cost: 0,
  return_parts: [],
  labor_hours: 0,
  labor_cost: 0
})

// 解析备件 JSON
const parsedParts = computed(() => {
  if (!task.value.maintenance?.parts_replaced) return []
  try {
    return JSON.parse(task.value.maintenance.parts_replaced)
  } catch {
    return []
  }
})

const getStatusType = (status) => {
  const types = { pending: 'info', in_progress: 'warning', completed: 'success', overdue: 'danger', skipped: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { pending: t('pmStatsPending'), in_progress: t('taskDetailTimelineInProgress'), completed: t('pmStatsCompleted'), overdue: t('taskDetailTimelineOverdue'), skipped: t('taskDetailTimelineSkipped') }
  return texts[status] || status
}

const getMaintTypeText = (type) => {
  const texts = { preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }
  return texts[type] || type
}

const getPlanTypeColor = (type) => {
  const colors = { routine_check: 'success', parts_replace: 'warning', vendor_service: 'info' }
  return colors[type] || ''
}

const getPlanTypeText = (type) => {
  const texts = { routine_check: t('pmPlanTypeRoutine'), parts_replace: t('pmPlanTypeParts'), vendor_service: t('pmPlanTypeVendor') }
  return texts[type] || type
}

const goBack = () => {
  router.push('/planned-maintenance')
}

const loadTask = debounce(async (force = false) => {
  try {
    const taskId = route.params.id
    const data = await cachedRequest(
      () => getMaintenanceTask(taskId),
      'maintenance_task',
      { id: taskId },
      { forceRefresh: force }
    )
    task.value = data
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('taskDetailMsgLoadFailed'))
    }
  }
}, 300)

const startTask = async () => {
  try {
    await ElMessageBox.confirm(t('taskDetailMsgConfirmStart'), t('taskDetailMsgStartTitle'), { type: 'info' })
    await startMaintenanceTask(task.value.id)
    clearCache('maintenance_task')
    ElMessage.success(t('taskDetailMsgStartSuccess'))
    loadTask(true)
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('taskDetailMsgStartFailed'))
  }
}

const skipTask = async () => {
  try {
    const { value } = await ElMessageBox.prompt(t('taskDetailMsgSkipReasonPrompt'), t('taskDetailMsgSkipTitle'), {
      inputPlaceholder: t('taskDetailMsgSkipPlaceholder')
    })
    await skipMaintenanceTask(task.value.id, value || '')
    clearCache('maintenance_task')
    ElMessage.success(t('taskDetailMsgSkipSuccess'))
    router.push('/planned-maintenance')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('taskDetailMsgSkipFailed'))
  }
}

const deleteTask = async () => {
  try {
    await ElMessageBox.confirm(`${t('taskDetailMsgDeleteConfirm')} "${task.value.task_no}" ?`, t('taskDetailMsgDeleteTitle'), { type: 'warning' })
    await deleteMaintenanceTask(task.value.id)
    clearCache('maintenance_task')
    ElMessage.success(t('taskDetailMsgDeleteSuccess'))
    router.push('/planned-maintenance')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(t('taskDetailMsgDeleteFailed'))
  }
}

// 搜索备件
const searchParts = debounce(async (query) => {
  if (!query || query.length < 1) {
    partOptions.value = []
    return
  }
  partsLoading.value = true
  try {
    const result = await cachedRequest(
      () => getPartList({ search: query, limit: 20 }),
      'part_list',
      { search: query, limit: 20 },
      { forceRefresh: true }
    )
    partOptions.value = result.items || []
  } catch (e) {
    if (e.name !== 'CanceledError') {
      console.error(t('maintSearchFailed'), e)
    }
  } finally {
    partsLoading.value = false
  }
}, 300)

// 加载初始备件列表
const loadInitialParts = debounce(async (force = false) => {
  partsLoading.value = true
  try {
    const result = await cachedRequest(
      () => getPartList({ limit: 50 }),
      'part_list',
      { limit: 50 },
      { forceRefresh: force }
    )
    partOptions.value = result.items || []
  } catch (e) {
    if (e.name !== 'CanceledError') {
      console.error(t('spareLoadFailed'), e)
    }
  } finally {
    partsLoading.value = false
  }
}, 300)

// 添加备件到完成表单
const addPartToComplete = () => {
  if (!selectedPart.value) return

  const part = partOptions.value.find(p => p.id === selectedPart.value)
  if (!part) return

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
    ElMessage.warning(t('taskDetailMsgReturnRequired'))
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

const openCompleteDialog = async () => {
  completeForm.value = {
    description: `${t('pmTitle')} ${task.value.task_no} ${t('pmStatsCompleted')}`,
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
  await loadInitialParts(true)
  showCompleteDialog.value = true
}

const completeTask = async () => {
  try {
    const combinedParts = [
      ...completeForm.value.parts.map(p => ({ ...p, is_return: false })),
      ...completeForm.value.return_parts.map(p => ({ ...p, is_return: true }))
    ]

    await completeMaintenanceTask(task.value.id, {
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
        reason: `${t('pmTitle')} - ${task.value.task_no}`,
        operator: 'Web',
        reference: task.value.device_name || t('pmTitle')
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
          reference: task.value.device_name || t('pmTitle')
        })
      }
    }

    clearCache('maintenance_task')
    clearCache('part_list')
    ElMessage.success(t('pmMsgTaskCompleteSuccess'))
    showCompleteDialog.value = false
    loadTask(true)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('pmMsgTaskCompleteFailed'))
  }
}

onMounted(() => {
  loadTask()
})
</script>

<style scoped>
.task-detail-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
}

.task-info-card {
  min-height: 200px;
}

.timeline-card {
  min-height: 200px;
}

.plan-card {
  min-height: 120px;
}

.description {
  line-height: 1.8;
  color: #606266;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.total-cost {
  font-weight: 600;
  color: #E6A23C;
  font-size: 16px;
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

.parts-detail {
  margin-top: 10px;
}

@media (max-width: 768px) {
  .return-section {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>