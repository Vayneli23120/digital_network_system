<template>
  <div class="maintenance-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>维修记录</span>
          <el-button type="primary" @click="openAddDialog">
            <el-icon><Plus /></el-icon>
            添加维修记录
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索设备名称或维修单号"
          style="width: 220px"
          clearable
          @input="filterMaintenances"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterMaintType" placeholder="维修类型" clearable style="width: 140px" @change="filterMaintenances">
          <el-option label="预防性" value="preventive" />
          <el-option label="修复性" value="corrective" />
          <el-option label="升级" value="upgrade" />
          <el-option label="紧急" value="emergency" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="filterMaintenances"
        />
        <el-select v-model="sortBy" placeholder="排序" style="width: 150px" @change="filterMaintenances">
          <el-option label="维修时间 ↓" value="maint_time_desc" />
          <el-option label="维修时间 ↑" value="maint_time_asc" />
          <el-option label="总成本 ↓" value="total_cost_desc" />
          <el-option label="总成本 ↑" value="total_cost_asc" />
        </el-select>
      </div>

      <el-table :data="filteredMaintenances" style="width: 100%" v-loading="loading">
        <el-table-column prop="maint_no" label="维修单号" width="180">
          <template #default="{ row }">
            <router-link :to="`/maintenance/${row.id}`" class="maint-link">
              {{ row.maint_no }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" label="设备名称" width="160" />
        <el-table-column prop="maint_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getMaintTypeType(row.maint_type)">
              {{ getMaintTypeText(row.maint_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="parts_cost" label="备件成本" width="100">
          <template #default="{ row }">¥{{ row.parts_cost?.toFixed(2) || '0.00' }}</template>
        </el-table-column>
        <el-table-column prop="labor_cost" label="人工成本" width="100">
          <template #default="{ row }">¥{{ row.labor_cost?.toFixed(2) || '0.00' }}</template>
        </el-table-column>
        <el-table-column prop="total_cost" label="总成本" width="100">
          <template #default="{ row }">
            ¥{{ ((row.parts_cost || 0) + (row.labor_cost || 0)).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="maint_time" label="维修时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.maint_time || row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="维修描述" min-width="200" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="editMaintenance(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="deleteMaintenance(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadMaintenances" @current-change="loadMaintenances" />
      </div>
    </el-card>

    <!-- 添加/编辑维修记录对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? '编辑维修记录' : '添加维修记录'" width="600px">
      <el-form :model="maintForm" label-width="120px">
        <el-form-item label="设备" required>
          <el-select v-model="maintForm.device_id" placeholder="选择设备" style="width: 100%" :disabled="editMode">
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            />
          </el-select>
        </el-form-item>
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
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="editMode ? updateMaintenance() : addMaintenance()">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMaintenances, getDevices, createMaintenance as createMaintenanceApi, updateMaintenance as updateMaintenanceApi, deleteMaintenance as deleteMaintenanceApi } from '@/api'
import { Search } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const maintenances = ref([])
const filteredMaintenances = ref([])
const devices = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const editMode = ref(false)

const searchText = ref('')
const filterMaintType = ref('')
const dateRange = ref([])
const sortBy = ref('maint_time_desc')

const openAddDialog = () => {
  console.log('打开添加维修记录对话框')
  showAddDialog.value = true
}

const maintForm = ref({
  device_id: null,
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

const filterMaintenances = () => {
  let result = [...maintenances.value]

  // 按搜索文本过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(m =>
      m.device_name?.toLowerCase().includes(search) ||
      m.maint_no?.toLowerCase().includes(search)
    )
  }

  // 按维修类型过滤
  if (filterMaintType.value) {
    result = result.filter(m => m.maint_type === filterMaintType.value)
  }

  // 按日期范围过滤
  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0])
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(m => {
      const maintTime = dayjs(m.maint_time || m.created_at)
      return maintTime.isAfter(startDate) && maintTime.isBefore(endDate)
    })
  }

  // 排序
  if (sortBy.value) {
    switch (sortBy.value) {
      case 'maint_time_desc':
        result.sort((a, b) => dayjs(b.maint_time || b.created_at) - dayjs(a.maint_time || a.created_at))
        break
      case 'maint_time_asc':
        result.sort((a, b) => dayjs(a.maint_time || a.created_at) - dayjs(b.maint_time || b.created_at))
        break
      case 'total_cost_desc':
        result.sort((a, b) => ((b.parts_cost || 0) + (b.labor_cost || 0)) - ((a.parts_cost || 0) + (a.labor_cost || 0)))
        break
      case 'total_cost_asc':
        result.sort((a, b) => ((a.parts_cost || 0) + (a.labor_cost || 0)) - ((b.parts_cost || 0) + (b.labor_cost || 0)))
        break
    }
  }

  filteredMaintenances.value = result
}

const loadMaintenances = async () => {
  loading.value = true
  try {
    const data = await getMaintenances()
    maintenances.value = data.items || []
    filterMaintenances()
  } catch (error) {
    ElMessage.error('加载维修记录失败')
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (error) {
    ElMessage.error('加载设备列表失败')
  }
}

const addMaintenance = async () => {
  if (!maintForm.value.device_id) {
    ElMessage.warning('请选择设备')
    return
  }
  if (!maintForm.value.description) {
    ElMessage.warning('请填写维修描述')
    return
  }

  try {
    await createMaintenanceApi(maintForm.value)
    ElMessage.success('维修记录添加成功')
    showAddDialog.value = false
    resetForm()
    loadMaintenances()
  } catch (error) {
    ElMessage.error('添加维修记录失败')
    ElMessage.error('添加维修记录失败')
  }
}

const editMaintenance = (row) => {
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
  showAddDialog.value = true
}

const updateMaintenance = async () => {
  if (!maintForm.value.description) {
    ElMessage.warning('请填写维修描述')
    return
  }

  try {
    await updateMaintenanceApi(maintForm.value.id, maintForm.value)
    ElMessage.success('维修记录更新成功')
    showAddDialog.value = false
    editMode.value = false
    resetForm()
    loadMaintenances()
  } catch (error) {
    ElMessage.error('更新维修记录失败')
    ElMessage.error('更新维修记录失败')
  }
}

const deleteMaintenance = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除维修记录 "${row.maint_no}" 吗？`, '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteMaintenanceApi(row.id)
    ElMessage.success('维修记录删除成功')
    loadMaintenances()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除维修记录失败')
      ElMessage.error('删除维修记录失败')
    }
  }
}

const resetForm = () => {
  maintForm.value = {
    device_id: null,
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
  loadMaintenances()
  loadDevices()
})
</script>

<style scoped>
.maintenance-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-bar {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.maint-link {
  color: #409EFF;
  text-decoration: none;
  font-weight: 500;
}

.maint-link:hover {
  text-decoration: underline;
  color: #66b1ff;
}
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
