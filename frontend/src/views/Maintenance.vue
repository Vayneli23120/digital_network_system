<template>
  <div class="maintenance-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('maintTitle') }}</span>
          <el-button type="primary" @click="openAddDialog">
            <el-icon><Plus /></el-icon>
            {{ t('maintAddRecord') }}
          </el-button>
        </div>
      </template>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          :placeholder="t('maintSearchPlaceholder')"
          style="width: 220px"
          clearable
          @input="filterMaintenances"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="filterMaintType" :placeholder="t('maintType')" clearable style="width: 140px" @change="filterMaintenances">
          <el-option :label="t('maintTypePreventive')" value="preventive" />
          <el-option :label="t('maintTypeCorrective')" value="corrective" />
          <el-option :label="t('maintTypeUpgrade')" value="upgrade" />
          <el-option :label="t('maintTypeEmergency')" value="emergency" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          :range-separator="t('maintDateTo')"
          :start-placeholder="t('maintDateStart')"
          :end-placeholder="t('maintDateEnd')"
          value-format="YYYY-MM-DD"
          style="width: 240px"
          @change="filterMaintenances"
        />
        <el-select v-model="sortBy" :placeholder="t('maintSort')" style="width: 150px" @change="filterMaintenances">
          <el-option :label="t('maintSortTimeDesc')" value="maint_time_desc" />
          <el-option :label="t('maintSortTimeAsc')" value="maint_time_asc" />
          <el-option :label="t('maintSortCostDesc')" value="total_cost_desc" />
          <el-option :label="t('maintSortCostAsc')" value="total_cost_asc" />
        </el-select>
      </div>

      <el-table :data="filteredMaintenances" style="width: 100%" v-loading="loading">
        <el-table-column prop="maint_no" :label="t('maintColNo')" width="180">
          <template #default="{ row }">
            <router-link :to="`/maintenance/${row.id}`" class="maint-link">
              {{ row.maint_no }}
            </router-link>
          </template>
        </el-table-column>
        <el-table-column prop="device_name" :label="t('maintColDevice')" width="160" />
        <el-table-column prop="maint_type" :label="t('maintColType')" width="100">
          <template #default="{ row }">
            <el-tag :type="getMaintTypeType(row.maint_type)">
              {{ getMaintTypeText(row.maint_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="parts_cost" :label="t('maintColPartsCost')" width="100">
          <template #default="{ row }">¥{{ row.parts_cost?.toFixed(2) || '0.00' }}</template>
        </el-table-column>
        <el-table-column prop="labor_cost" :label="t('maintColLaborCost')" width="100">
          <template #default="{ row }">¥{{ row.labor_cost?.toFixed(2) || '0.00' }}</template>
        </el-table-column>
        <el-table-column prop="total_cost" :label="t('maintColTotalCost')" width="100">
          <template #default="{ row }">
            ¥{{ ((row.parts_cost || 0) + (row.labor_cost || 0)).toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="maint_time" :label="t('maintColTime')" width="160">
          <template #default="{ row }">{{ formatDateTime(row.maint_time || row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="description" :label="t('maintColDesc')" min-width="200" />
        <el-table-column :label="t('colOperation')" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="editMaintenance(row)">{{ t('actionEdit') }}</el-button>
            <el-button type="danger" size="small" @click="deleteMaintenance(row)">{{ t('actionDelete') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadMaintenances" @current-change="loadMaintenances" />
      </div>
    </el-card>

    <!-- 添加/编辑维修记录对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('maintDialogEdit') : t('maintDialogAdd')" width="700px">
      <el-form :model="maintForm" label-width="120px">
        <el-form-item :label="t('faultDeviceLabel')" required>
          <el-select v-model="maintForm.device_id" :placeholder="t('maintSelectDevice')" style="width: 100%" :disabled="editMode" filterable>
            <el-option
              v-for="device in devices"
              :key="device.id"
              :label="device.name"
              :value="device.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('maintType')" required>
          <el-select v-model="maintForm.maint_type">
            <el-option :label="t('maintTypePreventiveFull')" value="preventive" />
            <el-option :label="t('maintTypeCorrectiveFull')" value="corrective" />
            <el-option :label="t('maintTypeUpgradeFull')" value="upgrade" />
            <el-option :label="t('maintTypeEmergencyFull')" value="emergency" />
          </el-select>
        </el-form-item>

        <!-- 备件选择区域 -->
        <el-divider content-position="left">{{ t('maintSparePartsSection') }}</el-divider>
        <el-form-item :label="t('maintSparePartsLabel')">
          <div class="spare-parts-section">
            <!-- 扫码添加备件按钮 -->
            <div class="spare-scan-btn">
              <el-button type="primary" @click="openScanDialog">
                <el-icon><Aim /></el-icon>
                {{ t('maintScanAddSpare') }}
              </el-button>
              <div class="spare-scan-tip">{{ t('maintScanTip') }}</div>
            </div>

            <!-- 手动搜索添加备件 -->
            <div class="spare-search">
              <el-select
                v-model="selectedSparePart"
                :placeholder="t('maintSpareSearchPlaceholder')"
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
                      {{ t('maintSpareStock') }}: {{ part.quantity_in_stock }}
                    </span>
                  </div>
                </el-option>
              </el-select>
              <div class="spare-tip">{{ t('maintSpareSelectTip') }}</div>
            </div>

            <!-- 已选备件列表 -->
            <div class="selected-parts" v-if="maintForm.spare_parts.length > 0">
              <el-table :data="maintForm.spare_parts" size="small" border>
                <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" :label="t('maintColModel')" width="150" />
                <el-table-column prop="name" :label="t('maintColName')" width="150" />
                <el-table-column prop="quantity" :label="t('maintColQuantity')" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" @change="updatePartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="80">
                  <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="total" :label="t('maintColSubtotal')" width="80">
                  <template #default="{ row }">¥{{ (row.quantity * (row.unit_price || 0)).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column :label="t('colOperation')" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeSparePart($index)">
                      {{ t('actionDelete') }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">
                {{ t('maintSpareTotalCost') }}: <span class="total-cost">¥{{ maintForm.parts_cost.toFixed(2) }}</span>
              </div>
            </div>
            <div class="no-parts-tip" v-else>
              <el-icon><InfoFilled /></el-icon>
              <span>{{ t('maintNoSpareTip') }}</span>
            </div>
          </div>
        </el-form-item>

        <el-divider content-position="left">{{ t('maintReturnPartsSection') }}</el-divider>
        <el-form-item :label="t('maintReturnPartsLabel')">
          <div class="return-parts-section">
            <!-- 扫码查询返回件 -->
            <div class="return-scan-area">
              <el-input
                v-model="returnScanInput"
                :placeholder="t('maintReturnScanPlaceholder')"
                style="width: 200px"
                @keyup.enter="scanReturnPart"
                clearable
              >
                <template #prefix><el-icon><Aim /></el-icon></template>
              </el-input>
              <el-button type="primary" size="small" @click="scanReturnPart" :loading="returnScanLoading">
                {{ t('spareQuery') }}
              </el-button>
              <div class="return-scan-tip">{{ t('maintReturnScanTip') }}</div>
            </div>

            <!-- 扫码识别结果（如果找到历史记录） -->
            <div class="return-found-info" v-if="returnFoundInfo">
              <el-card size="small" shadow="never">
                <div class="found-header">
                  <el-tag type="success" size="small">{{ t('maintReturnFoundTag') }}</el-tag>
                  <span>{{ returnFoundInfo.serial_number }}</span>
                </div>
                <el-descriptions :column="3" size="small" border>
                  <el-descriptions-item :label="t('maintColModel')">{{ returnFoundInfo.part_number }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintColName')">{{ returnFoundInfo.name }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintColUnitPrice')">¥{{ (returnFoundInfo.unit_price || 0).toFixed(2) }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintReturnInStockAt')">{{ returnFoundInfo.in_stock_at ? formatDateTime(returnFoundInfo.in_stock_at) : '-' }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintReturnOutAt')">{{ returnFoundInfo.out_at ? formatDateTime(returnFoundInfo.out_at) : '-' }}</el-descriptions-item>
                  <el-descriptions-item :label="t('faultStatus')">
                    <el-tag :type="returnFoundInfo.status === 'out' ? 'warning' : 'success'" size="small">
                      {{ returnFoundInfo.status === 'out' ? t('maintReturnStatusOut') : t('statusInStock') }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
                <div class="found-actions">
                  <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 90px" />
                  <el-checkbox v-model="returnPartScrap">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                  <el-button type="primary" size="small" @click="addFoundReturnPart">{{ t('maintReturnAddToList') }}</el-button>
                  <el-button size="small" @click="clearReturnFound">{{ t('actionReset') }}</el-button>
                </div>
              </el-card>
            </div>

            <!-- 手动添加返回件（未识别时） -->
            <div class="return-manual-area" v-if="!returnFoundInfo">
              <div class="return-manual-row">
                <el-select
                  v-model="selectedReturnPart"
                  :placeholder="t('maintReturnSelectFromSpare')"
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
                <el-input v-model="returnPartSerial" :placeholder="t('maintReturnSerialPlaceholder')" style="width: 120px" />
                <el-input v-model="returnPartNumber" :placeholder="t('maintReturnModelManual')" style="width: 130px" />
                <el-input v-model="returnPartName" :placeholder="t('maintReturnNameDefault')" style="width: 130px" />
              </div>
              <div class="return-manual-row">
                <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 90px" />
                <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                <el-button type="primary" size="small" :disabled="!returnPartSerial" @click="addReturnPart">{{ t('actionAdd') }}</el-button>
              </div>
              <div class="return-manual-tip">{{ t('maintReturnNotFoundTip') }}</div>
            </div>

            <div class="return-parts-table" v-if="maintForm.return_parts.length > 0">
              <el-table :data="maintForm.return_parts" size="small" border>
                <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" :label="t('maintColModel')" width="150" />
                <el-table-column prop="name" :label="t('maintColName')" width="150" />
                <el-table-column prop="quantity" :label="t('maintColQuantity')" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" />
                  </template>
                </el-table-column>
                <el-table-column :label="t('maintColScrapIn')" width="120">
                  <template #default="{ row }">
                    <el-checkbox v-model="row.scrap_in" :disabled="!row.part_id" />
                    <span class="scrap-label" v-if="row.part_id && !row.scrap_in">{{ t('maintReturnNoScrap') }}</span>
                    <span class="scrap-label no-id" v-if="!row.part_id">{{ t('maintReturnNoPartId') }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="t('colOperation')" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeReturnPart($index)">
                      {{ t('actionDelete') }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="return-tip">{{ t('maintReturnScrapTip') }}</div>
            </div>
            <div class="no-return-tip" v-else>
              <el-tag type="info">{{ t('maintReturnNoPartsTip') }}</el-tag>
            </div>
          </div>
        </el-form-item>

        <el-divider />

        <el-form-item :label="t('maintLaborHours')">
          <el-input-number v-model="maintForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item :label="t('maintLaborCost')">
          <el-input-number v-model="maintForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item :label="t('maintVendor')">
          <el-input v-model="maintForm.vendor" />
        </el-form-item>
        <el-form-item :label="t('maintDesc')" required>
          <el-input v-model="maintForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateMaintenance() : addMaintenance()">{{ t('maintConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 扫码添加备件对话框 -->
    <el-dialog v-model="scanDialogVisible" :title="t('maintScanSpareDialog')" width="700px">
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
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

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
    console.error(t('spareLoadFailed'), e)
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
  const texts = {
    preventive: t('maintTypePreventive'),
    corrective: t('maintTypeCorrective'),
    upgrade: t('maintTypeUpgrade'),
    emergency: t('maintTypeEmergency')
  }
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
    ElMessage.error(t('maintSearchFailed'))
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
    ElMessage.info(`${item.name} ${t('maintPartQtyAdded')}`)
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
      ElMessage.success(`${t('maintAlreadyOut')}: ${item.name}`)
    } else {
      ElMessage.success(`${t('maintPartAdded')}: ${item.name}`)
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
      ElMessage.info(`${item.name} ${t('maintPartQtyAdded')}`)
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
      ElMessage.success(`${t('maintPartAdded')}: ${item.name}`)
    }
  }
  updatePartsCost()
  scanDialogVisible.value = false
  ElMessage.success(`${t('maintAddedCount')} ${result.items.length} ${t('maintPartAdded')}`)
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
    ElMessage.warning(t('maintSerialMinLength'))
    return
  }

  returnScanLoading.value = true
  try {
    const info = await getPartBySerialNumber(serial)
    returnFoundInfo.value = info
    ElMessage.success(`${t('maintIdentified')}: ${info.name || info.part_number}`)
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
    ElMessage.info(t('maintSerialNotFound'))
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

  ElMessage.success(`${t('maintReturnAdded')}: ${returnFoundInfo.value.serial_number}`)
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
    ElMessage.warning(t('maintSerialPrompt'))
    return
  }

  // 检查是否已添加过该序列号
  const existing = maintForm.value.return_parts.find(p => p.serial_number === returnPartSerial.value)
  if (existing) {
    ElMessage.warning(`${t('maintSerialDuplicate')} ${returnPartSerial.value}`)
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

  ElMessage.success(`${t('maintReturnAdded')}: ${returnPartSerial.value}`)

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
    ElMessage.error(t('maintLoadFailed'))
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices()
    devices.value = data.items || []
  } catch (error) {
    ElMessage.error(t('maintDeviceLoadFailed'))
  }
}

const addMaintenance = async () => {
  if (!maintForm.value.device_id) {
    ElMessage.warning(t('maintSelectDevicePrompt'))
    return
  }
  if (!maintForm.value.description) {
    ElMessage.warning(t('maintDescPrompt'))
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
          reason: `${t('spareReasonMaintenanceReplace')} - ${maintForm.value.maint_type}`,
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
          reason: t('spareReasonReturnPartScrap'),
          operator: 'Web',
          reference: device?.name
        })
      }
    }

    ElMessage.success(t('maintAddSuccess'))
    showAddDialog.value = false
    resetForm()
    loadMaintenances()
  } catch (error) {
    ElMessage.error(`${t('maintAddFailed')}: ${error.response?.data?.detail || error.message}`)
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
    ElMessage.warning(t('maintDescPrompt'))
    return
  }

  try {
    const device = devices.value.find(d => d.id === maintForm.value.device_id)
    await updateMaintenanceApi(maintForm.value.id, {
      ...maintForm.value,
      device_name: device?.name,
      parts_replaced: JSON.stringify(maintForm.value.spare_parts)
    })
    ElMessage.success(t('maintUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    resetForm()
    loadMaintenances()
  } catch (error) {
    ElMessage.error(t('maintUpdateFailed'))
  }
}

const deleteMaintenance = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('maintConfirmDeletePrompt')} "${row.maint_no}"?`, t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteMaintenanceApi(row.id)
    ElMessage.success(t('maintDeleteSuccess'))
    loadMaintenances()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('maintDeleteFailed'))
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
