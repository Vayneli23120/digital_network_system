<template>
  <div class="fault-detail-page">
    <el-page-header @back="goBack" :title="'返回故障列表'">
      <template #content>
        <span class="page-title">{{ fault.fault_no || '故障详情' }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：故障信息 -->
      <el-col :span="16">
        <el-card class="fault-info-card">
          <template #header>
            <span>故障信息</span>
          </template>

          <el-descriptions :column="2" border v-if="fault.id">
            <el-descriptions-item label="故障单号">{{ fault.fault_no }}</el-descriptions-item>
            <el-descriptions-item label="设备名称">
              <router-link :to="`/devices/${fault.device_id}`">{{ fault.device_name }}</router-link>
            </el-descriptions-item>
            <el-descriptions-item label="故障级别">
              <el-tag :type="getSeverityType(fault.severity)">
                {{ getSeverityText(fault.severity) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="当前状态">
              <el-tag :type="getStatusType(fault.status)">
                {{ getStatusText(fault.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="停机时长">{{ fault.downtime_minutes }} 分钟</el-descriptions-item>
            <el-descriptions-item label="影响范围">{{ fault.impact || '无' }}</el-descriptions-item>
            <el-descriptions-item label="报告人">{{ fault.reporter || 'Web' }}</el-descriptions-item>
            <el-descriptions-item label="发生时间">{{ formatDateTime(fault.fault_time || fault.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <el-divider>故障描述</el-divider>
          <p class="description">{{ fault.description || '无描述' }}</p>

          <el-divider v-if="fault.resolution">解决方案</el-divider>
          <p v-if="fault.resolution" class="description">{{ fault.resolution }}</p>
        </el-card>

        <!-- 操作按钮 -->
        <el-card style="margin-top: 20px">
          <el-space>
            <el-button type="primary" @click="showEditDialog = true">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <!-- 转维修按钮：未关闭且未关联维修单 -->
            <el-button
              v-if="fault.status !== 'closed' && !fault.maintenance_id"
              type="warning"
              @click="convertToMaintenance"
            >
              <el-icon><Tools /></el-icon>
              转维修单
            </el-button>
            <el-button
              v-if="fault.status !== 'closed'"
              type="success"
              @click="closeFault"
            >
              <el-icon><CircleCheck /></el-icon>
              关闭故障
            </el-button>
            <el-button type="danger" @click="deleteFault">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </el-space>
        </el-card>

        <!-- 关联的维修单信息 -->
        <el-card style="margin-top: 20px" v-if="maintenanceInfo">
          <template #header>
            <span>关联维修单</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="维修单号">
              <router-link :to="`/maintenance/${maintenanceInfo.id}`">
                {{ maintenanceInfo.maint_no }}
              </router-link>
            </el-descriptions-item>
            <el-descriptions-item label="维修类型">
              <el-tag>{{ getMaintTypeText(maintenanceInfo.maint_type) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="备件成本">¥{{ maintenanceInfo.parts_cost }}</el-descriptions-item>
            <el-descriptions-item label="人工成本">¥{{ maintenanceInfo.labor_cost }}</el-descriptions-item>
            <el-descriptions-item label="维修时间">{{ formatDateTime(maintenanceInfo.maint_time) }}</el-descriptions-item>
            <el-descriptions-item label="总成本">
              <span class="total-cost">¥{{ (maintenanceInfo.parts_cost + maintenanceInfo.labor_cost).toFixed(2) }}</span>
            </el-descriptions-item>
          </el-descriptions>
          <el-divider>维修描述</el-divider>
          <p class="description">{{ maintenanceInfo.description || '无描述' }}</p>
        </el-card>
      </el-col>

      <!-- 右侧：时间线 -->
      <el-col :span="8">
        <el-card class="timeline-card">
          <template #header>
            <span>处理时间线</span>
          </template>

          <el-timeline>
            <el-timeline-item
              :timestamp="formatDateTime(fault.created_at)"
              placement="top"
              color="#409EFF"
            >
              <el-card>
                <h4>故障发生</h4>
                <p>报告人：{{ fault.reporter || 'Web' }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.status === 'investigating'"
              timestamp="处理中"
              placement="top"
              color="#E6A23C"
            >
              <el-card>
                <h4>开始调查</h4>
                <p>故障正在处理中</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.status === 'resolved'"
              timestamp="已解决"
              placement="top"
              color="#67C23A"
            >
              <el-card>
                <h4>故障解决</h4>
                <p>故障已解决</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.status === 'closed'"
              timestamp="已关闭"
              placement="top"
              color="#909399"
            >
              <el-card>
                <h4>故障关闭</h4>
                <p>故障记录已归档</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- 设备快速信息 -->
        <el-card class="device-quick-info" style="margin-top: 20px" v-if="device">
          <template #header>
            <span>设备信息</span>
          </template>
          <div class="device-summary">
            <el-avatar :size="60" icon="Switch" />
            <div class="device-info">
              <h4>{{ device.name }}</h4>
              <p>{{ device.ip }}</p>
              <el-tag :type="device.status === 'online' ? 'success' : 'info'" size="small">
                {{ device.status }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑故障对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑故障记录" width="600px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="故障级别" required>
          <el-select v-model="editForm.severity">
            <el-option label="严重 (Critical)" value="critical" />
            <el-option label="主要 (Major)" value="major" />
            <el-option label="次要 (Minor)" value="minor" />
            <el-option label="警告 (Warning)" value="warning" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" required>
          <el-select v-model="editForm.status">
            <el-option label="待处理" value="open" />
            <el-option label="处理中" value="investigating" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="停机时长 (分钟)">
          <el-input-number v-model="editForm.downtime_minutes" :min="0" />
        </el-form-item>
        <el-form-item label="影响范围">
          <el-input v-model="editForm.impact" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="故障描述" required>
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="解决方案">
          <el-input v-model="editForm.resolution" type="textarea" :rows="3" placeholder="记录故障解决方案" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateFault">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tools } from '@element-plus/icons-vue'
import { getFaultDetail, updateFault as updateFaultApi, deleteFault as deleteFaultApi, getDevices, convertFaultToMaintenance, getFaultMaintenance } from '@/api'
import { formatDateTime } from '@/utils/time'

const route = useRoute()
const router = useRouter()

const fault = ref({})
const device = ref(null)
const loading = ref(false)
const showEditDialog = ref(false)
const maintenanceInfo = ref(null)

const editForm = ref({
  severity: 'major',
  status: 'open',
  downtime_minutes: 0,
  impact: '',
  description: '',
  resolution: ''
})

const getSeverityType = (severity) => {
  const types = { critical: 'danger', major: 'warning', minor: '', warning: 'info' }
  return types[severity] || 'info'
}

const getSeverityText = (severity) => {
  const texts = { critical: '严重', major: '主要', minor: '次要', warning: '警告' }
  return texts[severity] || severity
}

const getStatusType = (status) => {
  const types = { open: 'info', investigating: 'warning', resolved: 'success', closed: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { open: '待处理', investigating: '处理中', resolved: '已解决', closed: '已关闭' }
  return texts[status] || status
}

const getMaintTypeText = (type) => {
  const texts = { preventive: '预防性', corrective: '修复性', upgrade: '升级', emergency: '紧急' }
  return texts[type] || type
}

const loadFault = async () => {
  try {
    const faultId = route.params.id
    // 获取故障详情
    const data = await getFaultDetail(faultId)
    fault.value = data
    editForm.value = {
      severity: data.severity,
      status: data.status,
      downtime_minutes: data.downtime_minutes || 0,
      impact: data.impact || '',
      description: data.description,
      resolution: data.resolution || ''
    }

    // 加载设备信息
    if (data.device_id) {
      const devices = await getDevices()
      device.value = (devices.items || []).find(d => d.id === data.device_id)
    }

    // 加载关联的维修单信息
    if (data.maintenance_id) {
      const maintData = await getFaultMaintenance(faultId)
      maintenanceInfo.value = maintData.maintenance
    }
  } catch (error) {
    ElMessage.error('加载故障详情失败')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/faults')
}

const convertToMaintenance = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要将此故障转换为维修单吗？转换后故障状态将更新，维修单将继承故障信息。',
      '转维修单',
      {
        confirmButtonText: '确定转换',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const result = await convertFaultToMaintenance(fault.value.id)
    ElMessage.success(`维修单 ${result.maint_no} 创建成功`)
    loadFault()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '转换失败')
    }
  }
}

const updateFault = async () => {
  try {
    await updateFaultApi(fault.value.id, editForm.value)
    ElMessage.success('故障记录更新成功')
    showEditDialog.value = false
    loadFault()
  } catch (error) {
    ElMessage.error('更新故障记录失败')
  }
}

const closeFault = async () => {
  try {
    await ElMessageBox.confirm('确定要关闭此故障吗？', '确认关闭', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await updateFaultApi(fault.value.id, { status: 'closed' })
    ElMessage.success('故障已关闭')
    loadFault()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('关闭故障失败')
    }
  }
}

const deleteFault = async () => {
  try {
    await ElMessageBox.confirm('确定要删除此故障记录吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteFaultApi(fault.value.id)
    ElMessage.success('故障记录删除成功')
    router.push('/faults')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除故障失败')
    }
  }
}

onMounted(() => {
  loadFault()
})
</script>

<style scoped>
.fault-detail-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
}

.fault-info-card {
  min-height: 400px;
}

.description {
  line-height: 1.8;
  color: #606266;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.timeline-card {
  min-height: 300px;
}

.device-summary {
  display: flex;
  align-items: center;
  gap: 15px;
}

.device-info h4 {
  margin: 0 0 5px 0;
  font-size: 16px;
}

.device-info p {
  margin: 0 0 5px 0;
  color: #909399;
  font-size: 14px;
}

.total-cost {
  font-weight: 600;
  color: #E6A23C;
  font-size: 16px;
}
</style>
