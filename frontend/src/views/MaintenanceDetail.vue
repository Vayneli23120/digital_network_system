<template>
  <div class="maintenance-detail-page">
    <el-page-header @back="goBack" :title="'返回维修列表'">
      <template #content>
        <span class="page-title">{{ maintenance.maint_no || '维修详情' }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：维修信息 -->
      <el-col :span="16">
        <el-card class="maintenance-info-card">
          <template #header>
            <span>维修信息</span>
          </template>

          <el-descriptions :column="2" border v-if="maintenance.id">
            <el-descriptions-item label="维修单号">{{ maintenance.maint_no }}</el-descriptions-item>
            <el-descriptions-item label="设备名称">
              <router-link :to="`/devices/${maintenance.device_id}`">{{ maintenance.device_name }}</router-link>
            </el-descriptions-item>
            <el-descriptions-item label="维修类型">
              <el-tag :type="getMaintTypeType(maintenance.maint_type)">
                {{ getMaintTypeText(maintenance.maint_type) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="维修时间">{{ formatDateTime(maintenance.maint_time || maintenance.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="供应商">{{ maintenance.vendor || '无' }}</el-descriptions-item>
            <el-descriptions-item label="工时">{{ maintenance.labor_hours }} 小时</el-descriptions-item>
          </el-descriptions>

          <el-divider>维修详情</el-divider>

          <el-row :gutter="20">
            <el-col :span="12">
              <h4>备件信息</h4>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="更换备件">
                  {{ maintenance.parts_replaced || '无' }}
                </el-descriptions-item>
                <el-descriptions-item label="备件成本">
                  <span class="cost">¥{{ (maintenance.parts_cost || 0).toFixed(2) }}</span>
                </el-descriptions-item>
              </el-descriptions>
            </el-col>
            <el-col :span="12">
              <h4>人工信息</h4>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="人工工时">
                  {{ maintenance.labor_hours }} 小时
                </el-descriptions-item>
                <el-descriptions-item label="人工成本">
                  <span class="cost">¥{{ (maintenance.labor_cost || 0).toFixed(2) }}</span>
                </el-descriptions-item>
              </el-descriptions>
            </el-col>
          </el-row>

          <el-divider>维修描述</el-divider>
          <p class="description">{{ maintenance.description || '无描述' }}</p>
        </el-card>

        <!-- 操作按钮 -->
        <el-card style="margin-top: 20px">
          <el-space>
            <el-button type="primary" @click="showEditDialog = true">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button type="danger" @click="deleteMaintenance">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </el-space>
        </el-card>
      </el-col>

      <!-- 右侧：成本统计 -->
      <el-col :span="8">
        <el-card class="cost-card">
          <template #header>
            <span>成本统计</span>
          </template>

          <div class="cost-items">
            <div class="cost-item">
              <span class="cost-label">备件成本</span>
              <span class="cost-value">¥{{ (maintenance.parts_cost || 0).toFixed(2) }}</span>
            </div>
            <div class="cost-item">
              <span class="cost-label">人工成本</span>
              <span class="cost-value">¥{{ (maintenance.labor_cost || 0).toFixed(2) }}</span>
            </div>
            <el-divider />
            <div class="cost-item total">
              <span class="cost-label">总成本</span>
              <span class="cost-value highlight">
                ¥{{ ((maintenance.parts_cost || 0) + (maintenance.labor_cost || 0)).toFixed(2) }}
              </span>
            </div>
          </div>
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

        <!-- 维修类型说明 -->
        <el-card class="type-info-card" style="margin-top: 20px">
          <template #header>
            <span>维修类型说明</span>
          </template>
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="预防性">定期保养、检查</el-descriptions-item>
            <el-descriptions-item label="修复性">故障后修复</el-descriptions-item>
            <el-descriptions-item label="升级">硬件/软件升级</el-descriptions-item>
            <el-descriptions-item label="紧急">紧急故障处理</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑维修对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑维修记录" width="600px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="维修类型" required>
          <el-select v-model="editForm.maint_type">
            <el-option label="预防性维修" value="preventive" />
            <el-option label="修复性维修" value="corrective" />
            <el-option label="升级" value="upgrade" />
            <el-option label="紧急维修" value="emergency" />
          </el-select>
        </el-form-item>
        <el-form-item label="更换备件">
          <el-input v-model="editForm.parts_replaced" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备件成本">
          <el-input-number v-model="editForm.parts_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="人工工时 (小时)">
          <el-input-number v-model="editForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item label="人工成本">
          <el-input-number v-model="editForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="editForm.vendor" />
        </el-form-item>
        <el-form-item label="维修描述" required>
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateMaintenance">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMaintenances, updateMaintenance as updateMaintenanceApi, deleteMaintenance as deleteMaintenanceApi, getDevices } from '@/api'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const maintenance = ref({})
const device = ref(null)
const loading = ref(false)
const showEditDialog = ref(false)

const editForm = ref({
  maint_type: 'corrective',
  parts_replaced: '',
  parts_cost: 0,
  labor_hours: 0,
  labor_cost: 0,
  vendor: '',
  description: ''
})

const getMaintTypeType = (type) => {
  const types = { preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }
  return types[type] || ''
}

const getMaintTypeText = (type) => {
  const texts = { preventive: '预防性', corrective: '修复性', upgrade: '升级', emergency: '紧急' }
  return texts[type] || type
}

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

const loadMaintenance = async () => {
  loading.value = true
  try {
    const maintId = route.params.id
    // 获取所有维修列表，然后找到对应的维修
    const data = await getMaintenances()
    const found = (data.items || []).find(m => m.id === parseInt(maintId))
    if (found) {
      maintenance.value = found
      editForm.value = {
        maint_type: found.maint_type,
        parts_replaced: found.parts_replaced || '',
        parts_cost: found.parts_cost || 0,
        labor_hours: found.labor_hours || 0,
        labor_cost: found.labor_cost || 0,
        vendor: found.vendor || '',
        description: found.description
      }

      // 加载设备信息
      if (found.device_id) {
        const devices = await getDevices()
        device.value = (devices.items || []).find(d => d.id === found.device_id)
      }
    }
  } catch (error) {
    ElMessage.error('加载维修详情失败')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/maintenance')
}

const updateMaintenance = async () => {
  try {
    await updateMaintenanceApi(maintenance.value.id, editForm.value)
    ElMessage.success('维修记录更新成功')
    showEditDialog.value = false
    loadMaintenance()
  } catch (error) {
    ElMessage.error('更新维修记录失败')
    ElMessage.error('更新维修记录失败')
  }
}

const deleteMaintenance = async () => {
  try {
    await ElMessageBox.confirm('确定要删除此维修记录吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteMaintenanceApi(maintenance.value.id)
    ElMessage.success('维修记录删除成功')
    router.push('/maintenance')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除维修记录失败')
      ElMessage.error('删除维修记录失败')
    }
  }
}

onMounted(() => {
  loadMaintenance()
})
</script>

<style scoped>
.maintenance-detail-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
}

.maintenance-info-card {
  min-height: 400px;
}

.description {
  line-height: 1.8;
  color: #606266;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.cost {
  color: #f56c6c;
  font-weight: bold;
}

.cost-card {
  min-height: 200px;
}

.cost-items {
  padding: 10px 0;
}

.cost-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.cost-label {
  font-size: 14px;
  color: #909399;
}

.cost-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.cost-value.highlight {
  color: #f56c6c;
  font-size: 20px;
}

.total {
  border-top: 2px solid #eee;
  padding-top: 15px;
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

.type-info-card {
  font-size: 13px;
}
</style>
