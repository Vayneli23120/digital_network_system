<template>
  <div class="device-detail">
    <el-row :gutter="20">
      <!-- 左侧：设备信息 -->
      <el-col :span="8">
        <el-card class="info-card" v-loading="loading">
          <template #header>
            <span>设备信息</span>
          </template>

          <div v-if="device" class="device-info">
            <div class="device-avatar">
              <el-avatar :size="80" icon="Switch" />
              <h2>{{ device.name }}</h2>
              <el-tag :type="getStatusType(device.status)">
                {{ getStatusText(device.status) }}
              </el-tag>
            </div>

            <el-descriptions :column="1" border>
              <el-descriptions-item label="IP 地址">{{ device.ip || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item label="设备型号">{{ device.model || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item label="序列号">{{ device.serial_number || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item label="位置">{{ device.location || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item label="角色">{{ getRoleText(device.role) }}</el-descriptions-item>
              <el-descriptions-item label="供应商">{{ device.vendor || 'N/A' }}</el-descriptions-item>
              <el-descriptions-item label="采购日期">
                {{ device.purchase_date ? formatDate(device.purchase_date) : 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="采购成本">
                {{ device.purchase_cost ? '¥' + device.purchase_cost.toLocaleString() : 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="最后备份">
                {{ device.last_backup_time ? formatDateTime(device.last_backup_time) : '从未备份' }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="actions">
              <el-button type="primary" @click="backupNow">
                <el-icon><Download /></el-icon>
                立即备份
              </el-button>
              <el-button type="warning" @click="openConsoleDeploy">
                <el-icon><Connection /></el-icon>
                Console 部署
              </el-button>
              <el-button type="success" @click="showEditDialog = true">编辑</el-button>
            </div>
          </div>
        </el-card>

        <!-- 设备照片 -->
        <el-card class="photos-card" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>设备照片</span>
              <el-upload
                :action="uploadUrl"
                :headers="uploadHeaders"
                :data="{ photo_type: 'other' }"
                :on-success="handlePhotoUploadSuccess"
                :on-error="handlePhotoUploadError"
                show-upload
              >
                <el-button type="primary" size="small">
                  <el-icon><Upload /></el-icon>
                  上传照片
                </el-button>
              </el-upload>
            </div>
          </template>

          <div v-if="device?.photos?.length" class="photo-grid">
            <div v-for="photo in device.photos" :key="photo.id" class="photo-item">
              <el-image
                :src="`/assets${photo.photo_path}`"
                fit="cover"
                :preview-src-list="[`/assets${photo.photo_path}`]"
                class="photo-image"
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
              <div class="photo-actions">
                <span class="photo-type">{{ getPhotoTypeText(photo.photo_type) }}</span>
                <el-button type="danger" size="small" @click="deletePhoto(photo.id)">删除</el-button>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无照片" />
        </el-card>
      </el-col>

      <!-- 右侧：记录标签页 -->
      <el-col :span="16">
        <el-card>
          <el-tabs v-model="activeTab">
            <el-tab-pane label="备份记录" name="backups">
              <el-table :data="device?.recent_backups || []" style="width: 100%">
                <el-table-column prop="backup_time" label="备份时间" width="180">
                  <template #default="{ row }">{{ formatDateTime(row.backup_time) }}</template>
                </el-table-column>
                <el-table-column prop="has_change" label="配置变更" width="100">
                  <template #default="{ row }">
                    <el-tag :type="row.has_change ? 'warning' : 'success'" size="small">
                      {{ row.has_change ? '是' : '否' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="150">
                  <template #default="{ row }">
                    <el-button size="small" @click="viewConfig(row.id)">查看配置</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane label="故障记录" name="faults">
              <el-table :data="device?.recent_faults || []" style="width: 100%">
                <el-table-column prop="fault_no" label="故障单号" width="180">
                  <template #default="{ row }">
                    <router-link :to="`/faults/${row.id}`" class="fault-link">
                      {{ row.fault_no }}
                    </router-link>
                  </template>
                </el-table-column>
                <el-table-column prop="severity" label="级别" width="80">
                  <template #default="{ row }">
                    <el-tag :type="getSeverityType(row.severity)" size="small">
                      {{ getSeverityText(row.severity) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="status" label="状态" width="80">
                  <template #default="{ row }">
                    <el-tag :type="getFaultStatusType(row.status)" size="small">
                      {{ getFaultStatusText(row.status) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="发生时间" width="160">
                  <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="150" fixed="right">
                  <template #default="{ row }">
                    <el-button size="small" @click="editFaultInDetail(row)">编辑</el-button>
                    <el-button
                      v-if="row.status !== 'closed'"
                      size="small"
                      type="success"
                      @click="closeFaultInDetail(row)"
                    >
                      关闭
                    </el-button>
                    <el-button
                      v-else
                      size="small"
                      type="info"
                      plain
                      disabled
                    >
                      已关闭
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-button type="primary" size="small" style="margin-top: 10px" @click="openFaultDialog">
                添加故障记录
              </el-button>
            </el-tab-pane>

            <el-tab-pane label="维修记录" name="maintenance">
              <el-table :data="device?.recent_maintenances || []" style="width: 100%">
                <el-table-column prop="maint_no" label="维修单号" width="180">
                  <template #default="{ row }">
                    <router-link :to="`/maintenance/${row.id}`" class="maint-link">
                      {{ row.maint_no }}
                    </router-link>
                  </template>
                </el-table-column>
                <el-table-column prop="maint_type" label="类型" width="100">
                  <template #default="{ row }">
                    <el-tag :type="getMaintTypeType(row.maint_type)" size="small">
                      {{ getMaintTypeText(row.maint_type) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="maint_time" label="维修时间" width="160">
                  <template #default="{ row }">{{ formatDateTime(row.maint_time || row.created_at) }}</template>
                </el-table-column>
                <el-table-column prop="description" label="维修描述" min-width="200" />
                <el-table-column label="操作" width="150" fixed="right">
                  <template #default="{ row }">
                    <el-button type="primary" size="small" @click="editMaintInDetail(row)">编辑</el-button>
                    <el-button type="danger" size="small" @click="deleteMaintInDetail(row.id)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <el-button type="primary" size="small" style="margin-top: 10px" @click="openMaintDialog">
                添加维修记录
              </el-button>
            </el-tab-pane>

            <el-tab-pane label="成本统计" name="costs">
              <div class="cost-summary">
                <el-statistic title="采购成本" :value="device?.purchase_cost || 0" prefix="¥" />
                <el-statistic title="维护成本" :value="calculateMaintCost()" :precision="2" prefix="¥" />
                <el-statistic title="总拥有成本 (TCO)" :value="(device?.purchase_cost || 0) + calculateMaintCost()" :precision="2" prefix="¥" />
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑设备对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑设备" width="600px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="设备名称">
          <el-input v-model="editForm.name" :disabled="true" />
        </el-form-item>
        <el-form-item label="IP 地址">
          <el-input v-model="editForm.ip" />
        </el-form-item>
        <el-form-item label="设备型号">
          <el-input v-model="editForm.model" />
        </el-form-item>
        <el-form-item label="序列号">
          <el-input v-model="editForm.serial_number" />
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="editForm.location" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role">
            <el-option label="接入层" value="access" />
            <el-option label="汇聚层" value="distribution" />
            <el-option label="核心层" value="core" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status">
            <el-option label="在线" value="online" />
            <el-option label="离线" value="offline" />
            <el-option label="维护中" value="maintenance" />
            <el-option label="已退役" value="retired" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateDevice">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看配置对话框 -->
    <el-dialog v-model="showConfigDialog" title="配置内容" width="800px">
      <el-card v-if="configContent">
        <pre class="config-content">{{ configContent }}</pre>
      </el-card>
      <el-empty v-else description="暂无配置内容" />
    </el-dialog>

    <!-- 添加故障记录对话框 -->
    <el-dialog v-model="showFaultDialog" :title="editMode ? '编辑故障记录' : '添加故障记录'" width="500px">
      <el-form :model="faultForm" label-width="100px">
        <el-form-item label="故障级别" required>
          <el-select v-model="faultForm.severity">
            <el-option label="严重 (Critical)" value="critical" />
            <el-option label="主要 (Major)" value="major" />
            <el-option label="次要 (Minor)" value="minor" />
            <el-option label="警告 (Warning)" value="warning" />
          </el-select>
        </el-form-item>
        <el-form-item label="停机时长 (分钟)">
          <el-input-number v-model="faultForm.downtime_minutes" :min="0" />
        </el-form-item>
        <el-form-item label="故障描述" required>
          <el-input v-model="faultForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFaultDialog = false">取消</el-button>
        <el-button type="primary" @click="editMode ? updateFaultInDetail() : addFault()">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加维修记录对话框 -->
    <el-dialog v-model="showMaintDialog" :title="editMode ? '编辑维修记录' : '添加维修记录'" width="600px">
      <el-form :model="maintForm" label-width="120px">
        <el-form-item label="维修类型" required>
          <el-select v-model="maintForm.maint_type">
            <el-option label="预防性维修" value="preventive" />
            <el-option label="修复性维修" value="corrective" />
            <el-option label="升级" value="upgrade" />
            <el-option label="紧急维修" value="emergency" />
          </el-select>
        </el-form-item>
        <el-form-item label="更换备件">
          <el-input v-model="maintForm.parts_replaced" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备件成本">
          <el-input-number v-model="maintForm.parts_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="人工工时 (小时)">
          <el-input-number v-model="maintForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item label="人工成本">
          <el-input-number v-model="maintForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="维修商">
          <el-input v-model="maintForm.vendor" />
        </el-form-item>
        <el-form-item label="维修描述" required>
          <el-input v-model="maintForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showMaintDialog = false">取消</el-button>
        <el-button type="primary" @click="editMode ? updateMaintInDetail() : addMaintenance()">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDeviceDetail, createFault, createMaintenance, updateMaintenance, deleteMaintenance, updateFault, updateDevice as updateDeviceApi } from '@/api'
import dayjs from 'dayjs'
import axios from 'axios'

const route = useRoute()
const device = ref(null)
const loading = ref(false)
const activeTab = ref('backups')
const showFaultDialog = ref(false)
const showMaintDialog = ref(false)
const showEditDialog = ref(false)
const showConfigDialog = ref(false)
const editMode = ref(false)
const configContent = ref('')

const faultForm = ref({
  severity: 'major',
  downtime_minutes: 0,
  description: ''
})

const maintForm = ref({
  maint_type: 'corrective',
  parts_replaced: '',
  parts_cost: 0,
  labor_hours: 0,
  labor_cost: 0,
  vendor: '',
  description: ''
})

const editForm = ref({})

// 上传配置
const uploadUrl = computed(() => `/api/devices/${route.params.id}/photos`)
const uploadHeaders = computed(() => ({}))

const getStatusType = (status) => {
  const types = { online: 'success', offline: 'danger', maintenance: 'warning', retired: 'info' }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = { online: '在线', offline: '离线', maintenance: '维护中', retired: '已退役' }
  return texts[status] || status
}

const getFaultStatusType = (status) => {
  const types = { open: 'info', investigating: 'warning', resolved: 'success', closed: 'info' }
  return types[status] || 'info'
}

const getFaultStatusText = (status) => {
  const texts = { open: '待处理', investigating: '处理中', resolved: '已解决', closed: '已关闭' }
  return texts[status] || status
}

const getRoleText = (role) => {
  const texts = { access: '接入层', distribution: '汇聚层', core: '核心层' }
  return texts[role] || role
}

const getSeverityType = (severity) => {
  const types = { critical: 'danger', major: 'warning', minor: '', warning: 'info' }
  return types[severity] || 'info'
}

const getSeverityText = (severity) => {
  const texts = { critical: '严重', major: '主要', minor: '次要', warning: '警告' }
  return texts[severity] || severity
}

const getPhotoTypeText = (type) => {
  const texts = { front: '正面', back: '背面', label: '标签', rack: '机柜', other: '其他' }
  return texts[type] || type
}

const getMaintTypeText = (type) => {
  const texts = { preventive: '预防性', corrective: '修复性', upgrade: '升级', emergency: '紧急' }
  return texts[type] || type
}

const getMaintTypeType = (type) => {
  const types = { preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }
  return types[type] || ''
}

const formatDate = (date) => dayjs(date).format('YYYY-MM-DD')
const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

const calculateMaintCost = () => {
  if (!device.value?.recent_maintenances) return 0
  return device.value.recent_maintenances.reduce((sum, m) => {
    return sum + (parseFloat(m.parts_cost) || 0) + (parseFloat(m.labor_cost) || 0)
  }, 0)
}

const loadDevice = async () => {
  loading.value = true
  try {
    const data = await getDeviceDetail(route.params.id)
    device.value = data
    editForm.value = { ...data }
  } catch (error) {
    ElMessage.error('加载设备详情失败')
  } finally {
    loading.value = false
  }
}

const backupNow = async () => {
  try {
    const { backupDevice } = await import('@/api')
    await backupDevice(route.params.id, 'Web')
    ElMessage.success('备份成功')
    loadDevice()
  } catch (error) {
    ElMessage.error('备份失败')
  }
}

const openConsoleDeploy = () => {
  ElMessage.info('Console 部署功能开发中')
}

const handlePhotoUploadSuccess = (response) => {
  ElMessage.success('照片上传成功')
  loadDevice()
}

const handlePhotoUploadError = (error) => {
  ElMessage.error('照片上传失败')
  ElMessage.error('照片上传失败')
}

const deletePhoto = async (photoId) => {
  try {
    await ElMessageBox.confirm('确定要删除这张照片吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const api = await import('@/api')
    await api.deletePhoto(route.params.id, photoId)
    ElMessage.success('照片删除成功')
    loadDevice()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除照片失败')
    }
  }
}

const viewConfig = async (backupId) => {
  try {
    const { getBackupContent } = await import('@/api')
    const data = await getBackupContent(backupId)
    configContent.value = data.content
    showConfigDialog.value = true
  } catch (error) {
    ElMessage.error('获取配置失败')
    ElMessage.error('获取配置失败')
  }
}

const updateDevice = async () => {
  try {
    await updateDeviceApi(route.params.id, editForm.value)
    ElMessage.success('设备更新成功')
    showEditDialog.value = false
    loadDevice()
  } catch (error) {
    ElMessage.error('更新设备失败')
    ElMessage.error('更新设备失败')
  }
}

const addFault = async () => {
  try {
    console.log('Adding fault for device:', device.value)
    await createFault({
      device_id: device.value.id,
      device_name: device.value.name,
      ...faultForm.value,
      status: 'open'
    })
    ElMessage.success('故障记录添加成功')
    showFaultDialog.value = false
    resetFaultForm()
    loadDevice()
  } catch (error) {
    ElMessage.error('添加故障记录失败')
    ElMessage.error(error.response?.data?.detail || '添加故障记录失败')
  }
}

const openFaultDialog = () => {
  editMode.value = false
  resetFaultForm()
  showFaultDialog.value = true
}

const editFaultInDetail = (row) => {
  editMode.value = true
  faultForm.value = {
    id: row.id,
    device_id: row.device_id,
    severity: row.severity,
    downtime_minutes: row.downtime_minutes || 0,
    impact: row.impact || '',
    description: row.description,
    status: row.status
  }
  showFaultDialog.value = true
}

const updateFaultInDetail = async () => {
  try {
    await updateFault(faultForm.value.id, faultForm.value)
    ElMessage.success('故障记录更新成功')
    showFaultDialog.value = false
    editMode.value = false
    resetFaultForm()
    loadDevice()
  } catch (error) {
    ElMessage.error('更新故障记录失败')
    ElMessage.error('更新故障记录失败')
  }
}

const closeFaultInDetail = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要关闭故障 "${row.fault_no}" 吗？`, '确认关闭', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await updateFault(row.id, { status: 'closed' })
    console.log('API 调用成功，row:', row)
    ElMessage.success('故障已关闭')
    loadDevice()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('关闭故障失败')
      ElMessage.error('关闭故障失败')
    }
  }
}

const resetFaultForm = () => {
  faultForm.value = {
    severity: 'major',
    downtime_minutes: 0,
    impact: '',
    description: ''
  }
}

const openMaintDialog = () => {
  editMode.value = false
  resetMaintForm()
  showMaintDialog.value = true
}

const addMaintenance = async () => {
  try {
    console.log('Adding maintenance for device:', device.value)
    await createMaintenance({
      device_id: device.value.id,
      device_name: device.value.name,
      ...maintForm.value
    })
    ElMessage.success('维修记录添加成功')
    showMaintDialog.value = false
    resetMaintForm()
    loadDevice()
  } catch (error) {
    ElMessage.error('添加维修记录失败')
    ElMessage.error(error.response?.data?.detail || '添加维修记录失败')
  }
}

const editMaintInDetail = (row) => {
  editMode.value = true
  maintForm.value = {
    id: row.id,
    device_id: row.device_id,
    maint_type: row.maint_type,
    parts_replaced: row.parts_replaced || '',
    parts_cost: row.parts_cost || 0,
    labor_hours: row.labor_hours || 0,
    labor_cost: row.labor_cost || 0,
    vendor: row.vendor || '',
    description: row.description
  }
  showMaintDialog.value = true
}

const updateMaintInDetail = async () => {
  try {
    await updateMaintenance(maintForm.value.id, maintForm.value)
    ElMessage.success('维修记录更新成功')
    showMaintDialog.value = false
    editMode.value = false
    resetMaintForm()
    loadDevice()
  } catch (error) {
    ElMessage.error('更新维修记录失败')
    ElMessage.error('更新维修记录失败')
  }
}

const deleteMaintInDetail = async (maintId) => {
  try {
    await ElMessageBox.confirm('确定要删除此维修记录吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteMaintenance(maintId)
    ElMessage.success('维修记录删除成功')
    loadDevice()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除维修记录失败')
      ElMessage.error('删除维修记录失败')
    }
  }
}

const resetMaintForm = () => {
  maintForm.value = {
    maint_type: 'corrective',
    parts_replaced: '',
    parts_cost: 0,
    labor_hours: 0,
    labor_cost: 0,
    vendor: '',
    description: ''
  }
}

onMounted(() => {
  loadDevice()
})
</script>

<style scoped>
.device-info {
  text-align: center;
}

.device-avatar {
  margin-bottom: 20px;
}

.device-avatar h2 {
  margin: 15px 0 10px;
  font-size: 20px;
}

.actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.photos-card {
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
  padding: 10px;
}

.photo-item {
  position: relative;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.photo-image {
  width: 100%;
  height: 120px;
}

.photo-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: #f5f7fa;
}

.photo-type {
  font-size: 12px;
  color: #606266;
}

.image-error {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  background: #f5f7fa;
  color: #909399;
  font-size: 20px;
}

.cost-summary {
  display: flex;
  justify-content: space-around;
  padding: 20px;
}

.config-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 500px;
  overflow-y: auto;
}

.fault-link,
.maint-link {
  color: #409EFF;
  text-decoration: none;
  font-weight: 500;
}

.fault-link:hover,
.maint-link:hover {
  text-decoration: underline;
  color: #66b1ff;
}
</style>
