<template>
  <div class="faults-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>故障记录</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            添加故障
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索设备名称或故障单号"
          style="width: 220px"
          clearable
          @input="filterFaults"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterSeverity" placeholder="故障级别" clearable style="width: 140px" @change="filterFaults">
          <el-option label="严重" value="critical" />
          <el-option label="主要" value="major" />
          <el-option label="次要" value="minor" />
          <el-option label="警告" value="warning" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable style="width: 120px" @change="filterFaults">
          <el-option label="待处理" value="open" />
          <el-option label="处理中" value="investigating" />
          <el-option label="已解决" value="resolved" />
          <el-option label="已关闭" value="closed" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="filterFaults"
        />
        <el-select v-model="sortBy" placeholder="排序" style="width: 150px" @change="filterFaults">
          <el-option label="发生时间 ↓" value="created_at_desc" />
          <el-option label="发生时间 ↑" value="created_at_asc" />
          <el-option label="停机时长 ↓" value="downtime_desc" />
          <el-option label="停机时长 ↑" value="downtime_asc" />
        </el-select>
      </div>

      <el-table :data="filteredFaults" style="width: 100%" v-loading="loading">
        <el-table-column prop="fault_no" label="故障单号" width="200">
          <template #default="{ row }">
            <router-link :to="`/faults/${row.id}`" class="fault-link">
              {{ row.fault_no }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" label="设备名称" width="180" />
        <el-table-column prop="severity" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)">
              {{ getSeverityText(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="downtime_minutes" label="停机时长" width="100">
          <template #default="{ row }">{{ row.downtime_minutes }} 分钟</template>
        </el-table-column>
        <el-table-column prop="description" label="故障描述" />
        <el-table-column prop="created_at" label="发生时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editFault(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'open'"
              size="small"
              type="warning"
              @click="changeStatus(row, 'investigating')"
            >
              处理
            </el-button>
            <el-button
              v-if="row.status === 'investigating'"
              size="small"
              type="success"
              @click="changeStatus(row, 'resolved')"
            >
              解决
            </el-button>
            <el-button
              v-if="row.status === 'resolved'"
              size="small"
              type="info"
              @click="changeStatus(row, 'closed')"
            >
              关闭
            </el-button>
            <el-button
              v-if="row.status === 'closed'"
              size="small"
              type="primary"
              plain
              @click="changeStatus(row, 'open')"
            >
              重开
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadFaults" @current-change="loadFaults" />
      </div>
    </el-card>

    <!-- 添加故障对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? '编辑故障记录' : '添加故障记录'" width="600px">
      <el-form :model="faultForm" label-width="120px">
        <el-form-item label="设备" required>
          <el-select v-model="faultForm.device_id" placeholder="选择设备" style="width: 100%" :disabled="editMode">
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="故障级别" required>
          <el-select v-model="faultForm.severity">
            <el-option label="严重 (Critical)" value="critical" />
            <el-option label="主要 (Major)" value="major" />
            <el-option label="次要 (Minor)" value="minor" />
            <el-option label="警告 (Warning)" value="warning" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" v-if="editMode">
          <el-select v-model="faultForm.status">
            <el-option label="待处理" value="open" />
            <el-option label="处理中" value="investigating" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item label="停机时长 (分钟)">
          <el-input-number v-model="faultForm.downtime_minutes" :min="0" />
        </el-form-item>
        <el-form-item label="影响范围">
          <el-input v-model="faultForm.impact" type="textarea" :rows="2" placeholder="描述影响的业务范围" />
        </el-form-item>
        <el-form-item label="故障描述" required>
          <el-input v-model="faultForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="editMode ? updateFault() : addFault()">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getFaults, getDevices, createFault, updateFault as updateFaultApi, deleteFault } from '@/api'
import { Search } from '@element-plus/icons-vue'
import { formatDateTime, toLocalDayjs, dayjs } from '@/utils/time'

const faults = ref([])
const filteredFaults = ref([])
const devices = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const editMode = ref(false)

const searchText = ref('')
const filterSeverity = ref('')
const filterStatus = ref('')
const dateRange = ref([])
const sortBy = ref('created_at_desc')

const faultForm = ref({
  id: null,
  device_id: null,
  device_name: '',
  severity: 'major',
  downtime_minutes: 0,
  impact: '',
  description: '',
  status: 'open'
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

const filterFaults = () => {
  let result = [...faults.value]

  // 按搜索文本过滤
  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(f =>
      f.device_name?.toLowerCase().includes(search) ||
      f.fault_no?.toLowerCase().includes(search)
    )
  }

  // 按故障级别过滤
  if (filterSeverity.value) {
    result = result.filter(f => f.severity === filterSeverity.value)
  }

  // 按状态过滤
  if (filterStatus.value) {
    result = result.filter(f => f.status === filterStatus.value)
  }

  // 按日期范围过滤
  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0])
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(f => {
      const faultTime = dayjs(f.created_at)
      return faultTime.isAfter(startDate) && faultTime.isBefore(endDate)
    })
  }

  // 排序
  if (sortBy.value) {
    switch (sortBy.value) {
      case 'created_at_desc':
        result.sort((a, b) => dayjs(b.created_at) - dayjs(a.created_at))
        break
      case 'created_at_asc':
        result.sort((a, b) => dayjs(a.created_at) - dayjs(b.created_at))
        break
      case 'downtime_desc':
        result.sort((a, b) => (b.downtime_minutes || 0) - (a.downtime_minutes || 0))
        break
      case 'downtime_asc':
        result.sort((a, b) => (a.downtime_minutes || 0) - (b.downtime_minutes || 0))
        break
    }
  }

  filteredFaults.value = result
}

const loadFaults = async () => {
  loading.value = true
  try {
    const data = await getFaults({ limit: 500 })
    faults.value = data.items || []
    total.value = data.total || faults.value.length
    filterFaults()
  } catch (error) {
    ElMessage.error('加载故障记录失败')
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

const addFault = async () => {
  try {
    const device = devices.value.find(d => d.id === faultForm.value.device_id)
    await createFault({
      ...faultForm.value,
      device_name: device?.name,
      reporter: 'Web',
      status: 'open'
    })
    ElMessage.success('故障记录添加成功')
    showAddDialog.value = false
    resetForm()
    loadFaults()
  } catch (error) {
    ElMessage.error('添加故障记录失败')
    ElMessage.error('添加故障记录失败')
  }
}

const editFault = (row) => {
  editMode.value = true
  faultForm.value = {
    id: row.id,
    device_id: row.device_id,
    device_name: row.device_name,
    severity: row.severity,
    downtime_minutes: row.downtime_minutes || 0,
    impact: row.impact || '',
    description: row.description,
    status: row.status
  }
  showAddDialog.value = true
}

const updateFault = async () => {
  try {
    const device = devices.value.find(d => d.id === faultForm.value.device_id)
    await updateFaultApi(faultForm.value.id, {
      ...faultForm.value,
      device_name: device?.name
    })
    ElMessage.success('故障记录更新成功')
    showAddDialog.value = false
    editMode.value = false
    resetForm()
    loadFaults()
    // 触发事件更新导航栏badge
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    ElMessage.error('更新故障记录失败')
    ElMessage.error('更新故障记录失败')
  }
}

const closeFault = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要关闭故障 "${row.fault_no}" 吗？`, '确认关闭', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await updateFaultApi(row.id, { status: 'closed' })
    ElMessage.success('故障已关闭')
    loadFaults()
    // 触发事件更新导航栏badge
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('关闭故障失败')
      ElMessage.error('关闭故障失败')
    }
  }
}

const changeStatus = async (row, newStatus) => {
  try {
    const statusLabels = {
      open: '待处理',
      investigating: '处理中',
      resolved: '已解决',
      closed: '已关闭'
    }

    await ElMessageBox.confirm(
      `确定要将故障 "${row.fault_no}" 的状态改为 "${statusLabels[newStatus]}" 吗？`,
      '确认状态变更',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    await updateFaultApi(row.id, { status: newStatus })
    ElMessage.success(`故障状态已更新为 ${statusLabels[newStatus]}`)
    loadFaults()
    // 触发事件更新导航栏badge
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('状态更新失败')
    }
  }
}

const resetForm = () => {
  faultForm.value = {
    id: null,
    device_id: null,
    device_name: '',
    severity: 'major',
    downtime_minutes: 0,
    impact: '',
    description: '',
    status: 'open'
  }
}

onMounted(() => {
  loadFaults()
  loadDevices()
})
</script>

<style scoped>
.faults-page {
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

.fault-link {
  color: #409EFF;
  text-decoration: none;
  font-weight: 500;
}

.fault-link:hover {
  text-decoration: underline;
  color: #66b1ff;
}
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
@media (max-width: 768px) {
  .filter-bar { flex-wrap: wrap; }
  .filter-bar .el-input, .filter-bar .el-select { width: 100% !important; }
  .card-header { flex-direction: column; gap: 8px; align-items: flex-start; }
}
</style>
