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
    <el-dialog v-model="showAddDialog" :title="editMode ? '编辑维修记录' : '添加维修记录'" width="700px">
      <el-form :model="maintForm" label-width="120px">
        <el-form-item label="设备" required>
          <el-select v-model="maintForm.device_id" placeholder="选择设备" style="width: 100%" :disabled="editMode" filterable>
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

        <!-- 备件选择区域 -->
        <el-divider content-position="left">备件更换</el-divider>
        <el-form-item label="更换备件">
          <div class="spare-parts-section">
            <!-- 扫码添加备件按钮 -->
            <div class="spare-scan-btn">
              <el-button type="primary" @click="openScanDialog">
                <el-icon><Aim /></el-icon>
                扫码添加备件
              </el-button>
              <div class="spare-scan-tip">点击后用扫码枪扫描条形码建立连接，再扫描备件序列号</div>
            </div>

            <!-- 手动搜索添加备件 -->
            <div class="spare-search">
              <el-select
                v-model="selectedSparePart"
                placeholder="输入型号或名称搜索，点击选择添加"
                filterable
                remote
                :remote-method="searchSpareParts"
                :loading="spareLoading"
                style="width: 100%"
                @change="addSparePartToForm"
                clearable
              >
                <el-option
                  v-for="part in sparePartOptions"
                  :key="part.id"
                  :label="`${part.part_number} - ${part.name}`"
                  :value="part.id"
                  :disabled="part.quantity_in_stock <= 0"
                >
                  <div class="spare-option">
                    <span class="spare-number">{{ part.part_number }}</span>
                    <span class="spare-name">{{ part.name }}</span>
                    <span class="spare-stock" :class="{ low: part.quantity_in_stock <= part.min_quantity }">
                      库存: {{ part.quantity_in_stock }}
                    </span>
                  </div>
                </el-option>
              </el-select>
              <div class="spare-tip">↓ 从上方下拉列表点击选择备件，自动添加到下方列表</div>
            </div>

            <!-- 已选备件列表 -->
            <div class="selected-parts" v-if="maintForm.spare_parts.length > 0">
              <el-table :data="maintForm.spare_parts" size="small" border>
                <el-table-column prop="serial_number" label="序列号" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" label="型号" width="150" />
                <el-table-column prop="name" label="名称" width="150" />
                <el-table-column prop="quantity" label="数量" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" @change="updatePartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" label="单价" width="80">
                  <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="total" label="小计" width="80">
                  <template #default="{ row }">¥{{ (row.quantity * (row.unit_price || 0)).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeSparePart($index)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">
                备件总成本: <span class="total-cost">¥{{ maintForm.parts_cost.toFixed(2) }}</span>
              </div>
            </div>
            <div class="no-parts-tip" v-else>
              <el-icon><InfoFilled /></el-icon>
              <span>暂无更换备件，如需添加请从上方搜索框选择</span>
            </div>
          </div>
        </el-form-item>

        <el-divider content-position="left">返回件信息</el-divider>
        <el-form-item label="返回件处理">
          <div class="return-parts-section">
            <!-- 扫码查询返回件 -->
            <div class="return-scan-area">
              <el-input
                v-model="returnScanInput"
                placeholder="扫码或输入序列号查询"
                style="width: 200px"
                @keyup.enter="scanReturnPart"
                clearable
              >
                <template #prefix><el-icon><Aim /></el-icon></template>
              </el-input>
              <el-button type="primary" size="small" @click="scanReturnPart" :loading="returnScanLoading">
                查询
              </el-button>
              <div class="return-scan-tip">扫描序列号自动识别设备信息，或手动输入查询</div>
            </div>

            <!-- 扫码识别结果（如果找到历史记录） -->
            <div class="return-found-info" v-if="returnFoundInfo">
              <el-card size="small" shadow="never">
                <div class="found-header">
                  <el-tag type="success" size="small">已识别</el-tag>
                  <span>{{ returnFoundInfo.serial_number }}</span>
                </div>
                <el-descriptions :column="3" size="small" border>
                  <el-descriptions-item label="型号">{{ returnFoundInfo.part_number }}</el-descriptions-item>
                  <el-descriptions-item label="名称">{{ returnFoundInfo.name }}</el-descriptions-item>
                  <el-descriptions-item label="单价">¥{{ (returnFoundInfo.unit_price || 0).toFixed(2) }}</el-descriptions-item>
                  <el-descriptions-item label="入库时间">{{ returnFoundInfo.in_stock_at ? formatDateTime(returnFoundInfo.in_stock_at) : '-' }}</el-descriptions-item>
                  <el-descriptions-item label="出库时间">{{ returnFoundInfo.out_at ? formatDateTime(returnFoundInfo.out_at) : '-' }}</el-descriptions-item>
                  <el-descriptions-item label="状态">
                    <el-tag :type="returnFoundInfo.status === 'out' ? 'warning' : 'success'" size="small">
                      {{ returnFoundInfo.status === 'out' ? '已出库' : '在库' }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
                <div class="found-actions">
                  <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 90px" />
                  <el-checkbox v-model="returnPartScrap">入报废库</el-checkbox>
                  <el-button type="primary" size="small" @click="addFoundReturnPart">添加到列表</el-button>
                  <el-button size="small" @click="clearReturnFound">清除</el-button>
                </div>
              </el-card>
            </div>

            <!-- 手动添加返回件（未识别时） -->
            <div class="return-manual-area" v-if="!returnFoundInfo">
              <div class="return-manual-row">
                <el-select
                  v-model="selectedReturnPart"
                  placeholder="从备件库选择型号"
                  filterable
                  remote
                  :remote-method="searchReturnParts"
                  :loading="spareLoading"
                  style="width: 180px"
                  clearable
                  @change="onReturnPartSelect"
                >
                  <el-option
                    v-for="part in sparePartOptions"
                    :key="part.id"
                    :label="`${part.part_number} - ${part.name}`"
                    :value="part.id"
                  />
                </el-select>
                <el-input v-model="returnPartSerial" placeholder="序列号（必填）" style="width: 120px" />
                <el-input v-model="returnPartNumber" placeholder="型号（手动）" style="width: 130px" />
                <el-input v-model="returnPartName" placeholder="名称（默认=型号）" style="width: 130px" />
              </div>
              <div class="return-manual-row">
                <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 90px" />
                <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">入报废库</el-checkbox>
                <el-button type="primary" size="small" :disabled="!returnPartSerial" @click="addReturnPart">添加</el-button>
              </div>
              <div class="return-manual-tip">序列号未识别时：可选备件库型号自动填充，或手动输入型号/名称</div>
            </div>

            <div class="return-parts-table" v-if="maintForm.return_parts.length > 0">
              <el-table :data="maintForm.return_parts" size="small" border>
                <el-table-column prop="serial_number" label="序列号" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" label="型号" width="150" />
                <el-table-column prop="name" label="名称" width="150" />
                <el-table-column prop="quantity" label="数量" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" />
                  </template>
                </el-table-column>
                <el-table-column label="入报废库" width="120">
                  <template #default="{ row }">
                    <el-checkbox v-model="row.scrap_in" :disabled="!row.part_id" />
                    <span class="scrap-label" v-if="row.part_id && !row.scrap_in">不入库</span>
                    <span class="scrap-label no-id" v-if="!row.part_id">无备件ID</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeReturnPart($index)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="return-tip">注：需从备件库选择才能入报废库，无固定资产的返回件可不入库</div>
            </div>
            <div class="no-return-tip" v-else>
              <el-tag type="info">暂无返回件，请从上方手动录入换下来的坏件</el-tag>
            </div>
          </div>
        </el-form-item>

        <el-divider />

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

    <!-- 扫码添加备件对话框 -->
    <el-dialog v-model="scanDialogVisible" title="扫码添加备件" width="700px">
      <ScanSession
        ref="scanSessionRef"
        default-type="out"
        :auto-start="scanDialogVisible"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, InfoFilled, Aim } from '@element-plus/icons-vue'
import { getMaintenances, getDevices, createMaintenance, updateMaintenance as updateMaintenanceApi, deleteMaintenance as deleteMaintenanceApi, getPartList, createMovement, getPartBySerialNumber } from '@/api'
import ScanSession from '@/components/ScanSession.vue'
import { formatDateTime } from '@/utils/time'
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

// 备件相关
const sparePartOptions = ref([])
const spareLoading = ref(false)
const selectedSparePart = ref(null)
const currentFoundPart = ref(null)  // 当前扫码找到的备件

// 扫码对话框
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)

// 返回件扫码相关
const returnScanInput = ref('')
const returnScanLoading = ref(false)
const returnFoundInfo = ref(null)  // 扫码识别到的返回件信息
const selectedReturnPart = ref(null)
const returnPartSerial = ref('')
const returnPartNumber = ref('')
const returnPartName = ref('')
const returnPartQty = ref(1)
const returnPartScrap = ref(true)

const openAddDialog = async () => {
  editMode.value = false
  resetForm()
  // 预加载备件列表
  await loadInitialSpareParts()
  showAddDialog.value = true
}

// 加载初始备件列表
const loadInitialSpareParts = async () => {
  spareLoading.value = true
  try {
    const result = await getPartList({ limit: 50 })
    sparePartOptions.value = result.items || []
  } catch (e) {
    console.error('加载备件失败:', e)
  } finally {
    spareLoading.value = false
  }
}

const maintForm = ref({
  device_id: null,
  maint_type: 'corrective',
  spare_parts: [],  // 更换的备件列表
  return_parts: [], // 返回件列表（换下来的坏件）
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

// 搜索备件
const searchSpareParts = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    const result = await getPartList({ search: query, limit: 20 })
    sparePartOptions.value = result.items || []
  } catch (e) {
    ElMessage.error('搜索备件失败')
  } finally {
    spareLoading.value = false
  }
}

// 搜索返回件备件（共用同一个搜索）
const searchReturnParts = async (query) => {
  await searchSpareParts(query)
}

// 扫码找到备件（只显示信息，不自动添加）
const onScanPartFound = (part) => {
  // 不自动添加，等用户点击按钮后再添加
  currentFoundPart.value = part
}

// 扫码添加备件（从ScanInput组件点击按钮）
const onScanPartAdded = (item) => {
  // 加入更换列表
  const existing = maintForm.value.spare_parts.find(p => p.part_id === item.id)
  if (existing) {
    existing.quantity += 1
    ElMessage.info(`${item.name} 数量+1`)
  } else {
    maintForm.value.spare_parts.push({
      part_id: item.id,
      part_number: item.part_number,
      name: item.name,
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      quantity: 1
    })
    // 如果是出库操作，提示用户
    if (item.action === 'out') {
      ElMessage.success(`已出库并加入: ${item.name}`)
    } else {
      ElMessage.success(`已添加: ${item.name}`)
    }
  }
  updatePartsCost()
  currentFoundPart.value = null
}

// 打开扫码对话框
const openScanDialog = () => {
  scanDialogVisible.value = true
}

// 扫码会话完成
const onScanSessionComplete = async (result) => {
  // 将扫描的备件加入更换列表（已在扫码会话中自动出库，标记跳过重复出库）
  for (const item of result.items) {
    const existing = maintForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      existing.quantity += 1
      ElMessage.info(`${item.name} 数量+1`)
    } else {
      maintForm.value.spare_parts.push({
        part_id: item.part_id,
        part_number: item.part_number,
        name: item.name,
        serial_number: item.serial_number,
        unit_price: item.unit_price || 0,
        quantity: 1,
        is_from_scan: true  // 标记为扫码添加，已在扫码会话中出库
      })
      ElMessage.success(`已添加: ${item.name}`)
    }
  }
  updatePartsCost()
  scanDialogVisible.value = false
  ElMessage.success(`已添加 ${result.items.length} 个备件到更换列表`)
}

// 添加备件到表单
const addSparePartToForm = () => {
  if (!selectedSparePart.value) return

  const part = sparePartOptions.value.find(p => p.id === selectedSparePart.value)
  if (!part) return

  // 检查是否已添加
  const existing = maintForm.value.spare_parts.find(p => p.part_id === part.id)
  if (existing) {
    existing.quantity += 1
  } else {
    maintForm.value.spare_parts.push({
      part_id: part.id,
      part_number: part.part_number,
      name: part.name,
      unit_price: part.unit_price || 0,
      quantity: 1
    })
  }

  updatePartsCost()
  selectedSparePart.value = null
}

// 移除备件
const removeSparePart = (index) => {
  maintForm.value.spare_parts.splice(index, 1)
  updatePartsCost()
}

// 扫码查询返回件
const scanReturnPart = async () => {
  const serial = returnScanInput.value.trim()
  if (!serial || serial.length < 4) {
    ElMessage.warning('请输入至少4个字符的序列号')
    return
  }

  returnScanLoading.value = true
  try {
    const info = await getPartBySerialNumber(serial)
    returnFoundInfo.value = info
    ElMessage.success(`已识别: ${info.name || info.part_number}`)
    // 自动填充表单
    returnPartSerial.value = info.serial_number
    returnPartNumber.value = info.part_number
    returnPartName.value = info.name
    selectedReturnPart.value = info.id
    returnPartScrap.value = true  // 有记录的默认入报废库
  } catch (e) {
    // 未找到，提示手动输入
    returnFoundInfo.value = null
    returnPartSerial.value = serial
    ElMessage.info('序列号未在系统中找到，请手动输入型号/名称或从备件库选择')
  } finally {
    returnScanLoading.value = false
  }
}

// 清除识别结果
const clearReturnFound = () => {
  returnFoundInfo.value = null
  returnScanInput.value = ''
  returnPartSerial.value = ''
  returnPartNumber.value = ''
  returnPartName.value = ''
  selectedReturnPart.value = null
  returnPartQty.value = 1
}

// 添加识别到的返回件
const addFoundReturnPart = () => {
  if (!returnFoundInfo.value) return

  maintForm.value.return_parts.push({
    part_id: returnFoundInfo.value.id,
    part_number: returnFoundInfo.value.part_number,
    name: returnFoundInfo.value.name,
    serial_number: returnFoundInfo.value.serial_number,
    unit_price: returnFoundInfo.value.unit_price || 0,
    quantity: returnPartQty.value,
    scrap_in: returnPartScrap.value,
    is_from_scan: true,  // 标记为扫码识别
    history: returnFoundInfo.value.history  // 保存历史记录
  })

  ElMessage.success(`已添加返回件: ${returnFoundInfo.value.serial_number}`)
  clearReturnFound()
}

// 选择备件型号时自动填充
const onReturnPartSelect = () => {
  if (!selectedReturnPart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
  if (part) {
    returnPartNumber.value = part.part_number
    returnPartName.value = part.name || part.part_number  // 名称默认用型号
    returnPartScrap.value = true
  }
}

// 手动添加返回件
const addReturnPart = () => {
  if (!returnPartSerial.value) {
    ElMessage.warning('请输入序列号')
    return
  }

  // 检查是否已添加过该序列号
  const existing = maintForm.value.return_parts.find(p => p.serial_number === returnPartSerial.value)
  if (existing) {
    ElMessage.warning(`序列号 ${returnPartSerial.value} 已在列表中`)
    return
  }

  // 如果从备件库选择，使用备件信息
  let partNumber = returnPartNumber.value
  let partName = returnPartName.value || returnPartNumber.value  // 名称默认=型号
  let partId = null

  if (selectedReturnPart.value) {
    const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
    if (part) {
      partId = part.id
      partNumber = part.part_number
      partName = part.name || part.part_number
    }
  }

  maintForm.value.return_parts.push({
    part_id: partId,
    part_number: partNumber,
    name: partName,
    serial_number: returnPartSerial.value,
    quantity: returnPartQty.value,
    scrap_in: selectedReturnPart.value ? returnPartScrap.value : false,
    is_from_scan: false
  })

  ElMessage.success(`已添加返回件: ${returnPartSerial.value}`)

  // 清空输入
  returnScanInput.value = ''
  returnFoundInfo.value = null
  selectedReturnPart.value = null
  returnPartSerial.value = ''
  returnPartNumber.value = ''
  returnPartName.value = ''
  returnPartQty.value = 1
  returnPartScrap.value = true
}

// 移除返回件
const removeReturnPart = (index) => {
  maintForm.value.return_parts.splice(index, 1)
}

// 更新备件成本
const updatePartsCost = () => {
  maintForm.value.parts_cost = maintForm.value.spare_parts.reduce(
    (sum, p) => sum + p.quantity * p.unit_price, 0
  )
}

const filterMaintenances = () => {
  let result = [...maintenances.value]

  if (searchText.value) {
    const search = searchText.value.toLowerCase()
    result = result.filter(m =>
      m.device_name?.toLowerCase().includes(search) ||
      m.maint_no?.toLowerCase().includes(search)
    )
  }

  if (filterMaintType.value) {
    result = result.filter(m => m.maint_type === filterMaintType.value)
  }

  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dayjs(dateRange.value[0])
    const endDate = dayjs(dateRange.value[1]).endOf('day')
    result = result.filter(m => {
      const maintTime = dayjs(m.maint_time || m.created_at)
      return maintTime.isAfter(startDate) && maintTime.isBefore(endDate)
    })
  }

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
    const data = await getMaintenances({ limit: 500 })
    maintenances.value = data.items || []
    total.value = data.total || maintenances.value.length
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
    // 创建维修记录 - 合并备件和返回件数据
    const device = devices.value.find(d => d.id === maintForm.value.device_id)
    const combinedParts = [
      ...maintForm.value.spare_parts.map(p => ({ ...p, is_return: false })),
      ...maintForm.value.return_parts.map(p => ({ ...p, is_return: true }))
    ]

    await createMaintenance({
      ...maintForm.value,
      device_name: device?.name,
      parts_replaced: JSON.stringify(combinedParts)
    })

    // 处理备件出库（只处理手动添加的，扫码添加的已在扫码会话中自动出库）
    for (const part of maintForm.value.spare_parts) {
      if (part.part_id && !part.is_from_scan) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'out',
          quantity: part.quantity,
          serial_number: part.serial_number,
          reason: `维修更换 - ${maintForm.value.maint_type}`,
          operator: 'Web',
          reference: device?.name
        })
      }
    }

    // 处理返回件入报废库
    for (const part of maintForm.value.return_parts) {
      if (part.scrap_in && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'scrap_in',
          quantity: part.quantity,
          serial_number: part.serial_number,
          reason: `维修返回件入库 - 报废`,
          operator: 'Web',
          reference: device?.name
        })
      }
    }

    ElMessage.success('维修记录添加成功')
    showAddDialog.value = false
    resetForm()
    loadMaintenances()
  } catch (error) {
    ElMessage.error('添加维修记录失败: ' + (error.response?.data?.detail || error.message))
  }
}

const editMaintenance = (row) => {
  editMode.value = true
  maintForm.value = {
    id: row.id,
    device_id: row.device_id,
    maint_type: row.maint_type,
    spare_parts: [],
    return_parts: [],
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
    const device = devices.value.find(d => d.id === maintForm.value.device_id)
    await updateMaintenanceApi(maintForm.value.id, {
      ...maintForm.value,
      device_name: device?.name,
      parts_replaced: JSON.stringify(maintForm.value.spare_parts)
    })
    ElMessage.success('维修记录更新成功')
    showAddDialog.value = false
    editMode.value = false
    resetForm()
    loadMaintenances()
  } catch (error) {
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
    }
  }
}

const resetForm = () => {
  maintForm.value = {
    device_id: null,
    maint_type: 'corrective',
    spare_parts: [],
    return_parts: [],
    parts_cost: 0,
    labor_hours: 0,
    labor_cost: 0,
    vendor: '',
    description: ''
  }
  selectedSparePart.value = null
  sparePartOptions.value = []
  currentFoundPart.value = null
  returnScanInput.value = ''
  returnFoundInfo.value = null
  selectedReturnPart.value = null
  returnPartSerial.value = ''
  returnPartNumber.value = ''
  returnPartName.value = ''
  returnPartQty.value = 1
  returnPartScrap.value = true
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

.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* 备件选择区域 */
.spare-parts-section {
  width: 100%;
}

.spare-scan-btn {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.spare-scan-tip {
  font-size: 12px;
  color: var(--el-color-primary);
  padding: 4px 8px;
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
}

.spare-search {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.spare-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 4px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.selected-parts {
  margin-top: 12px;
}

.no-parts-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 4px;
  color: #909399;
  font-size: 13px;
  margin-top: 12px;
}

.no-parts-tip .el-icon {
  font-size: 16px;
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
.spare-option {
  display: flex;
  align-items: center;
  gap: 12px;
}

.spare-number {
  font-weight: 500;
  color: #409EFF;
}

.spare-name {
  color: #606266;
}

.spare-stock {
  font-size: 12px;
  color: #909399;
}

.spare-stock.low {
  color: #F56C6C;
  font-weight: 500;
}

/* 返回件区域样式 */
.return-parts-section {
  width: 100%;
}

.return-scan-area {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.return-scan-tip {
  font-size: 12px;
  color: var(--el-color-primary);
  padding: 4px 8px;
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
}

.return-found-info {
  margin-bottom: 16px;
}

.found-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.found-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.return-manual-area {
  margin-bottom: 12px;
}

.return-manual-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.return-manual-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 4px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.return-parts-table {
  margin-top: 8px;
}

.scrap-label {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.scrap-label.no-id {
  color: #E6A23C;
}

.return-tip {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fdf6ec;
  border-radius: 4px;
  color: #909399;
  font-size: 12px;
}

.no-return-tip {
  margin-top: 8px;
}

@media (max-width: 768px) {
  .filter-bar {
    flex-wrap: wrap;
  }
  .filter-bar .el-input, .filter-bar .el-select {
    width: 100% !important;
  }
  .card-header {
    flex-direction: column;
    gap: 8px;
    align-items: flex-start;
  }
  .spare-search {
    flex-direction: column;
  }
  .spare-search .el-select {
    width: 100% !important;
  }
}
</style>
