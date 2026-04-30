<template>
  <div class="task-detail-page">
    <el-page-header @back="goBack" :title="'返回任务列表'">
      <template #content>
        <span class="page-title">{{ task.task_no || '任务详情' }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：任务信息 -->
      <el-col :span="16">
        <el-card class="task-info-card">
          <template #header>
            <span>任务信息</span>
          </template>

          <el-descriptions :column="2" border v-if="task.id">
            <el-descriptions-item label="任务编号">{{ task.task_no }}</el-descriptions-item>
            <el-descriptions-item label="设备名称">
              <router-link v-if="task.device_id" :to="`/devices/${task.device_id}`">{{ task.device_name }}</router-link>
              <span v-else>{{ task.device_name || '通用任务' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="计划日期">{{ formatDate(task.scheduled_date) }}</el-descriptions-item>
            <el-descriptions-item label="当前状态">
              <el-tag :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="实际执行日期">
              {{ task.actual_date ? formatDate(task.actual_date) : '未执行' }}
            </el-descriptions-item>
            <el-descriptions-item label="关联计划">
              <span v-if="task.plan">{{ task.plan.name }} ({{ getPlanTypeText(task.plan.plan_type) }})</span>
              <span v-else>手动创建</span>
            </el-descriptions-item>
            <el-descriptions-item label="备注">{{ task.notes || '无' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(task.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 维修执行详情（已完成时显示） -->
        <el-card style="margin-top: 20px" v-if="task.maintenance">
          <template #header>
            <span>维修执行详情</span>
          </template>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="维修单号">
              <router-link :to="`/maintenance/${task.maintenance.id}`">{{ task.maintenance.maint_no }}</router-link>
            </el-descriptions-item>
            <el-descriptions-item label="维修类型">
              <el-tag>{{ getMaintTypeText(task.maintenance.maint_type) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="备件成本">¥{{ task.maintenance.parts_cost?.toFixed(2) || '0.00' }}</el-descriptions-item>
            <el-descriptions-item label="人工成本">¥{{ task.maintenance.labor_cost?.toFixed(2) || '0.00' }}</el-descriptions-item>
            <el-descriptions-item label="总成本">
              <span class="total-cost">¥{{ ((task.maintenance.parts_cost || 0) + (task.maintenance.labor_cost || 0)).toFixed(2) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="维修时间">{{ formatDateTime(task.maintenance.maint_time) }}</el-descriptions-item>
          </el-descriptions>

          <!-- 更换备件详情 -->
          <el-divider v-if="parsedParts && parsedParts.length > 0">更换备件</el-divider>
          <div v-if="parsedParts && parsedParts.length > 0" class="parts-detail">
            <el-table :data="parsedParts" size="small" border>
              <el-table-column prop="part_number" label="型号" width="120" />
              <el-table-column prop="name" label="名称" width="150" />
              <el-table-column prop="quantity" label="数量" width="60" />
              <el-table-column label="类型" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.is_return ? 'warning' : 'success'" size="small">
                    {{ row.is_return ? '返回件' : '更换' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="报废入库" width="100">
                <template #default="{ row }">
                  <el-tag v-if="row.scrap_in" type="danger" size="small">已入库</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <el-divider>维修描述</el-divider>
          <p class="description">{{ task.maintenance.description || '无描述' }}</p>
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
              开始执行
            </el-button>
            <el-button
              v-if="task.status === 'in_progress'"
              type="success"
              @click="showCompleteDialog = true"
            >
              <el-icon><Check /></el-icon>
              完成任务
            </el-button>
            <el-button
              v-if="task.status === 'pending' || task.status === 'overdue'"
              type="warning"
              @click="skipTask"
            >
              <el-icon><Close /></el-icon>
              跳过
            </el-button>
            <el-button
              v-if="task.status === 'pending'"
              type="danger"
              @click="deleteTask"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </el-space>
        </el-card>
      </el-col>

      <!-- 右侧：时间线和计划信息 -->
      <el-col :span="8">
        <el-card class="timeline-card">
          <template #header>
            <span>任务时间线</span>
          </template>

          <el-timeline>
            <el-timeline-item
              :timestamp="formatDateTime(task.created_at)"
              placement="top"
              color="#409EFF"
            >
              <el-card>
                <h4>任务创建</h4>
                <p>计划日期: {{ formatDate(task.scheduled_date) }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="task.status === 'in_progress'"
              timestamp="进行中"
              placement="top"
              color="#E6A23C"
            >
              <el-card>
                <h4>开始执行</h4>
                <p>任务正在执行中</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="task.status === 'completed'"
              :timestamp="formatDateTime(task.actual_date)"
              placement="top"
              color="#67C23A"
            >
              <el-card>
                <h4>任务完成</h4>
                <p v-if="task.maintenance">维修单: {{ task.maintenance.maint_no }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="task.status === 'skipped'"
              timestamp="已跳过"
              placement="top"
              color="#909399"
            >
              <el-card>
                <h4>任务跳过</h4>
                <p>{{ task.notes || '原因未说明' }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="task.status === 'overdue'"
              timestamp="已超期"
              placement="top"
              color="#F56C6C"
            >
              <el-card>
                <h4>任务超期</h4>
                <p>计划日期已过，请尽快执行</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- 关联计划信息 -->
        <el-card class="plan-card" style="margin-top: 20px" v-if="task.plan">
          <template #header>
            <span>关联计划</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="计划名称">{{ task.plan.name }}</el-descriptions-item>
            <el-descriptions-item label="计划类型">
              <el-tag :type="getPlanTypeColor(task.plan.plan_type)" size="small">
                {{ getPlanTypeText(task.plan.plan_type) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="执行周期">{{ task.plan.cycle_days }} 天</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 完成任务对话框 -->
    <el-dialog v-model="showCompleteDialog" title="完成任务" width="700px">
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
        <el-button @click="showCompleteDialog = false">取消</el-button>
        <el-button type="success" @click="completeTask">确认完成</el-button>
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
  const texts = { pending: '待执行', in_progress: '进行中', completed: '已完成', overdue: '已超期', skipped: '已跳过' }
  return texts[status] || status
}

const getMaintTypeText = (type) => {
  const texts = { preventive: '预防性', corrective: '修复性', upgrade: '升级', emergency: '紧急' }
  return texts[type] || type
}

const getPlanTypeColor = (type) => {
  const colors = { routine_check: 'success', parts_replace: 'warning', vendor_service: 'info' }
  return colors[type] || ''
}

const getPlanTypeText = (type) => {
  const texts = { routine_check: '例行巡检', parts_replace: '备件更换', vendor_service: '原厂保养' }
  return texts[type] || type
}

const goBack = () => {
  router.push('/planned-maintenance')
}

const loadTask = async () => {
  try {
    const taskId = route.params.id
    const data = await getMaintenanceTask(taskId)
    task.value = data
  } catch (error) {
    ElMessage.error('加载任务详情失败')
  }
}

const startTask = async () => {
  try {
    await ElMessageBox.confirm('确定要开始执行此任务吗？', '开始执行', { type: 'info' })
    await startMaintenanceTask(task.value.id)
    ElMessage.success('任务已开始')
    loadTask()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('开始失败')
  }
}

const skipTask = async () => {
  try {
    const { value } = await ElMessageBox.prompt('请输入跳过原因', '跳过任务', {
      inputPlaceholder: '跳过原因（可选）'
    })
    await skipMaintenanceTask(task.value.id, value || '')
    ElMessage.success('任务已跳过')
    router.push('/planned-maintenance')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('跳过失败')
  }
}

const deleteTask = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除任务 "${task.value.task_no}" 吗？`, '确认删除', { type: 'warning' })
    await deleteMaintenanceTask(task.value.id)
    ElMessage.success('删除成功')
    router.push('/planned-maintenance')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
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
    description: `计划性运维任务 ${task.value.task_no} 完成`,
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
  await loadInitialParts()
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
        reason: `计划性运维 - ${task.value.task_no}`,
        operator: 'Web',
        reference: task.value.device_name || '计划运维'
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
          reference: task.value.device_name || '计划运维'
        })
      }
    }

    ElMessage.success('任务已完成')
    showCompleteDialog.value = false
    loadTask()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '完成失败')
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