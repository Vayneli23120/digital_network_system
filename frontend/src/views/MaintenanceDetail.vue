<template>
  <div class="maintenance-detail-page">
    <el-page-header @back="goBack" :title="t('maintDetailBack')">
      <template #content>
        <span class="page-title">{{ maintenance.maint_no || t('maintDetailTitle') }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：维修信息 -->
      <el-col :span="16">
        <el-card class="maintenance-info-card">
          <template #header>
            <span>{{ t('maintDetailInfo') }}</span>
          </template>

          <el-descriptions :column="2" border v-if="maintenance.id">
            <el-descriptions-item :label="t('maintNo')">{{ maintenance.maint_no }}</el-descriptions-item>
            <el-descriptions-item :label="t('maintDetailDeviceName')">
              <router-link :to="`/devices/${maintenance.device_id}`">{{ maintenance.device_name }}</router-link>
            </el-descriptions-item>
            <el-descriptions-item :label="t('maintType')">
              <el-tag :type="getMaintTypeType(maintenance.maint_type)">
                {{ getMaintTypeText(maintenance.maint_type) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('maintDetailTime')">{{ formatDateTime(maintenance.maint_time || maintenance.created_at) }}</el-descriptions-item>
            <el-descriptions-item :label="t('maintDetailVendor')">{{ maintenance.vendor || t('maintDetailVendorNone') }}</el-descriptions-item>
            <el-descriptions-item :label="t('maintDetailHours')">{{ maintenance.labor_hours }} {{ t('maintDetailHoursUnit') }}</el-descriptions-item>
          </el-descriptions>

          <el-divider>{{ t('maintDetailSpareInfo') }}</el-divider>

          <!-- 备件列表显示（标准表格） -->
          <div class="spare-parts-display" v-if="maintenance.spare_parts_list && maintenance.spare_parts_list.length > 0">
            <el-table :data="maintenance.spare_parts_list" border size="small">
              <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                <template #default="{ row }">
                  <span class="cell-primary">{{ row.serial_number || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="part_number" :label="t('maintColModel')" width="120" />
              <el-table-column prop="name" :label="t('maintColName')" width="150" />
              <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60" />
              <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="80">
                <template #default="{ row }">
                  <span class="cell-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column :label="t('maintColSubtotal')" width="80">
                <template #default="{ row }">
                  <span class="cell-success">¥{{ ((row.quantity || 1) * (row.unit_price || 0)).toFixed(2) }}</span>
                </template>
              </el-table-column>
            </el-table>
            <div class="parts-total">
              {{ t('maintSpareTotalCost') }}: <span class="cost">¥{{ (maintenance.parts_cost || 0).toFixed(2) }}</span>
            </div>
          </div>
          <el-empty :description="t('maintDetailNoSpare')" v-else :image-size="60" />

          <el-divider>{{ t('maintDetailReturnInfo') }}</el-divider>

          <!-- 返回件列表显示（标准表格） -->
          <div class="return-parts-display" v-if="maintenance.return_parts_list && maintenance.return_parts_list.length > 0">
            <el-table :data="maintenance.return_parts_list" border size="small">
              <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                <template #default="{ row }">
                  <span class="cell-primary">{{ row.serial_number || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="part_number" :label="t('maintColModel')" width="120" />
              <el-table-column prop="name" :label="t('maintColName')" width="150" />
              <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60" />
              <el-table-column :label="t('maintDetailReturnScrapIn')" width="80">
                <template #default="{ row }">
                  <el-tag :type="row.scrap_in ? 'success' : 'info'" size="small">
                    {{ row.scrap_in ? t('maintDetailReturnScrapped') : t('maintDetailReturnNoScrap') }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <div class="return-tip">{{ t('maintDetailReturnTip') }}</div>
          </div>
          <el-empty :description="t('maintDetailNoReturn')" v-else :image-size="60" />

          <el-divider>{{ t('maintDetailLaborInfo') }}</el-divider>
          <p class="description">{{ maintenance.description || t('maintDetailNoDesc') }}</p>
        </el-card>

        <!-- 操作按钮 -->
        <el-card style="margin-top: 20px">
          <el-space>
            <el-button type="primary" @click="openEditDialog">
              <el-icon><Edit /></el-icon>
              {{ t('actionEdit') }}
            </el-button>
            <el-button type="danger" @click="deleteMaintenanceRecord">
              <el-icon><Delete /></el-icon>
              {{ t('actionDelete') }}
            </el-button>
          </el-space>
        </el-card>
      </el-col>

      <!-- 右侧：成本统计 -->
      <el-col :span="8">
        <el-card class="cost-card">
          <template #header>
            <span>{{ t('maintDetailCostStats') }}</span>
          </template>

          <div class="cost-items">
            <div class="cost-item">
              <span class="cost-label">{{ t('maintDetailPartsCost') }}</span>
              <span class="cost-value">¥{{ (maintenance.parts_cost || 0).toFixed(2) }}</span>
            </div>
            <div class="cost-item">
              <span class="cost-label">{{ t('maintDetailLaborCost') }}</span>
              <span class="cost-value">¥{{ (maintenance.labor_cost || 0).toFixed(2) }}</span>
            </div>
            <el-divider />
            <div class="cost-item total">
              <span class="cost-label">{{ t('maintDetailTotalCost') }}</span>
              <span class="cost-value highlight">
                ¥{{ ((maintenance.parts_cost || 0) + (maintenance.labor_cost || 0)).toFixed(2) }}
              </span>
            </div>
          </div>
        </el-card>

        <!-- 设备快速信息 -->
        <el-card class="device-quick-info" style="margin-top: 20px" v-if="device">
          <template #header>
            <span>{{ t('maintDetailDeviceInfo') }}</span>
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

    <!-- 编辑维修对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('maintDetailEdit')" width="700px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item :label="t('maintType')" required>
          <el-select v-model="editForm.maint_type">
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
            <!-- 扫码添加按钮 -->
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
                :placeholder="t('maintDetailSpareSearchPlaceholder')"
                filterable
                remote
                :remote-method="searchSpareParts"
                :loading="spareLoading"
                style="width: 300px"
                @change="addSparePartToEditForm"
              >
                <el-option
                  v-for="part in sparePartOptions"
                  :key="part.id"
                  :label="part.is_serial_match ? `${part.serial_number} - ${part.name}` : `${part.part_number} - ${part.name} (${t('maintSpareStock')}: ${part.quantity_in_stock})`"
                  :value="part.id"
                  :disabled="!part.is_serial_match && part.quantity_in_stock <= 0"
                >
                  <div class="spare-option">
                    <span class="spare-number">{{ part.part_number }}</span>
                    <span class="spare-name">{{ part.name }}</span>
                    <span v-if="part.is_serial_match" class="spare-sn">
                      {{ t('maintDetailSpareSerial') }}: {{ part.serial_number }}
                    </span>
                    <span v-else class="spare-stock" :class="{ low: part.quantity_in_stock <= part.min_quantity }">
                      {{ t('maintSpareStock') }}: {{ part.quantity_in_stock }}
                    </span>
                  </div>
                </el-option>
              </el-select>
            </div>

            <div class="selected-parts" v-if="editForm.spare_parts.length > 0">
              <el-table :data="editForm.spare_parts" size="small" border>
                <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" :label="t('maintColModel')" width="150" />
                <el-table-column prop="name" :label="t('maintColName')" width="150" />
                <el-table-column prop="quantity" :label="t('maintColQuantity')" width="80">
                  <template #default="{ row }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" @change="updateEditPartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="80">
                  <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column :label="t('colOperation')" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeEditSparePart($index)">
                      {{ t('actionDelete') }}
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">
                {{ t('maintSpareTotalCost') }}: <span class="total-cost">¥{{ editForm.parts_cost.toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-divider content-position="left">{{ t('maintReturnPartsSection') }}</el-divider>
        <el-form-item :label="t('maintReturnPartsLabel')">
          <div class="return-parts-section">
            <!-- 扫码查询返回件 -->
            <div class="return-scan-area">
              <el-button type="primary" @click="openReturnScanDialog">
                <el-icon><Aim /></el-icon>
                {{ t('maintDetailScanAddReturn') }}
              </el-button>
              <div class="return-scan-tip">{{ t('maintDetailReturnScanTip') }}</div>
            </div>

            <!-- 手动输入查询 -->
            <div class="return-manual-query" style="margin-top: 12px">
              <el-input
                v-model="returnScanInput"
                :placeholder="t('maintDetailReturnManualPlaceholder')"
                style="width: 200px"
                @keyup.enter="scanReturnPart"
                clearable
              >
                <template #prefix><el-icon><Aim /></el-icon></template>
              </el-input>
              <el-button type="default" size="small" @click="scanReturnPart" :loading="returnScanLoading">
                {{ t('spareQuery') }}
              </el-button>
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
                  <el-descriptions-item :label="t('statusOnline')">
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

            <div class="return-parts-table" v-if="editForm.return_parts.length > 0">
              <el-table :data="editForm.return_parts" size="small" border>
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
                <el-table-column :label="t('maintReturnScrapLabel')" width="120">
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
              <div class="return-tip-form">{{ t('maintDetailReturnTipForm') }}</div>
            </div>
            <div class="no-return-tip" v-else>
              <el-tag type="info">{{ t('maintReturnNoPartsTip') }}</el-tag>
            </div>
          </div>
        </el-form-item>

        <el-divider />

        <el-form-item :label="t('maintLaborHours')">
          <el-input-number v-model="editForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item :label="t('maintLaborCost')">
          <el-input-number v-model="editForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item :label="t('maintVendor')">
          <el-input v-model="editForm.vendor" />
        </el-form-item>
        <el-form-item :label="t('maintDesc')" required>
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="updateMaintenanceRecord">{{ t('maintConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 扫码添加备件对话框 -->
    <el-dialog v-model="scanDialogVisible" :title="t('maintScanSpareDialog')" width="700px">
      <ScanSession
        ref="scanSessionRef"
        default-type="out"
        :device-id="maintenance?.device_id"
        :auto-start="scanDialogVisible"
        :reference="maintenance?.maint_no"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
    </el-dialog>

    <!-- 扫码添加返回件对话框 -->
    <el-dialog v-model="returnScanDialogVisible" :title="t('maintDetailScanReturnDialog')" width="700px">
      <ScanSession
        ref="returnScanSessionRef"
        default-type="return"
        :device-id="maintenance?.device_id"
        :auto-start="returnScanDialogVisible"
        :reference="maintenance?.maint_no"
        @complete="onReturnScanSessionComplete"
        @cancel="returnScanDialogVisible = false"
      />
      <template #footer>
        <el-button @click="returnScanDialogVisible = false">{{ t('actionClose') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Aim, Edit, Delete } from '@element-plus/icons-vue'
import { getMaintenances, updateMaintenance, deleteMaintenance, getDevices, getPartList, createMovement, getPartBySerialNumber, searchInStockParts } from '@/api'
import ScanSession from '@/components/ScanSession.vue'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()

const maintenance = ref({})
const device = ref(null)
const loading = ref(false)
const showEditDialog = ref(false)

// 备件相关
const sparePartOptions = ref([])
const spareLoading = ref(false)
const selectedSparePart = ref(null)

// 扫码对话框
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)
const originalSpareParts = ref([])  // 原始备件列表，用于判断新增

// 返回件扫码对话框
const returnScanDialogVisible = ref(false)
const returnScanSessionRef = ref(null)

// 返回件扫码相关
const returnScanInput = ref('')
const returnScanLoading = ref(false)
const returnFoundInfo = ref(null)
const selectedReturnPart = ref(null)
const returnPartNumber = ref('')
const returnPartSerial = ref('')
const returnPartName = ref('')
const returnPartQty = ref(1)
const returnPartScrap = ref(true)

const editForm = ref({
  maint_type: 'corrective',
  spare_parts: [],
  return_parts: [],  // 返回件列表（换下来的坏件）
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
  const texts = { preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }
  return texts[type] || type
}

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

// 搜索备件（只搜索库存中 in_stock 状态的备件）
const searchSpareParts = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    // 使用专用接口搜索库存中的备件（只返回 in_stock 状态）
    const result = await searchInStockParts(query)
    if (result.items && result.items.length > 0) {
      sparePartOptions.value = result.items.map(item => ({
        id: item.id,
        part_number: item.part_number,
        name: item.name,
        serial_number: item.serial_number,
        quantity_in_stock: item.quantity_in_stock,
        unit_price: item.unit_price,
        is_serial_match: true,  // 标记为精确匹配
        instance_status: item.status  // 实例状态
      }))
    } else {
      sparePartOptions.value = []
    }
  } catch (e) {
    ElMessage.error(t('spareLoadFailed'))
    sparePartOptions.value = []
  } finally {
    spareLoading.value = false
  }
}

// 加载初始备件列表（不自动加载，用户需输入搜索）
const loadInitialSpareParts = async () => {
  sparePartOptions.value = []
}

// 添加备件到编辑表单
const addSparePartToEditForm = () => {
  if (!selectedSparePart.value) return

  const part = sparePartOptions.value.find(p => p.id === selectedSparePart.value)
  if (!part) return

  // 如果是序列号匹配，检查是否已添加过该序列号
  if (part.is_serial_match && part.serial_number) {
    const existingBySerial = editForm.value.spare_parts.find(p => p.serial_number === part.serial_number)
    if (existingBySerial) {
      ElMessage.warning(t('maintSerialAlreadyInList', { sn: part.serial_number }))
      selectedSparePart.value = null
      return
    }
  }

  const existing = editForm.value.spare_parts.find(p => p.part_id === part.id && !p.serial_number)
  if (existing) {
    existing.quantity += 1
  } else {
    editForm.value.spare_parts.push({
      part_id: part.id,
      part_number: part.part_number,
      name: part.name,
      serial_number: part.serial_number || null,  // 序列号匹配时携带SN
      unit_price: part.unit_price || 0,
      quantity: 1,
      is_serial_match: part.is_serial_match || false  // 标记来源
    })
  }

  updateEditPartsCost()
  selectedSparePart.value = null
}

// 打开扫码对话框
const openScanDialog = () => {
  scanDialogVisible.value = true
}

// 打开返回件扫码对话框
const openReturnScanDialog = () => {
  returnScanDialogVisible.value = true
}

// 扫码会话完成
const onScanSessionComplete = async (result) => {
  // 将扫描的备件加入编辑表单的更换列表（已在扫码会话中自动出库）
  for (const item of result.items) {
    const existing = editForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      existing.quantity += 1
      ElMessage.info(t('maintQuantityPlusOne', { name: item.name }))
    } else {
      editForm.value.spare_parts.push({
        part_id: item.part_id,
        part_number: item.part_number,
        name: item.name,
        serial_number: item.serial_number,
        unit_price: item.unit_price || 0,
        quantity: 1,
        is_from_scan: true  // 标记为扫码添加，已在扫码会话中出库
      })
      ElMessage.success(t('maintPartAdded', { name: item.name }))
    }
  }
  updateEditPartsCost()
  scanDialogVisible.value = false
  ElMessage.success(t('maintPartsAdded', { count: result.items.length }))
}

// 返回件扫码会话完成
const onReturnScanSessionComplete = async (result) => {
  // 将扫描的返回件加入编辑表单（返回件扫码会话不会自动出库，只是查询信息）
  for (const item of result.items) {
    const existing = editForm.value.return_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      ElMessage.warning(t('maintSerialAlreadyInList', { sn: item.serial_number }))
      continue
    }
    editForm.value.return_parts.push({
      part_id: item.part_id,
      part_number: item.part_number,
      name: item.name,
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      quantity: 1,
      scrap_in: item.part_id ? true : false,  // 有备件ID默认入报废库
      is_from_scan: true,
      history: item.history || []
    })
    ElMessage.success(t('maintReturnPartAdded', { sn: item.serial_number }))
  }
  returnScanDialogVisible.value = false
}

// 移除备件
const removeEditSparePart = (index) => {
  editForm.value.spare_parts.splice(index, 1)
  updateEditPartsCost()
}

// 搜索返回件备件
const searchReturnParts = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    const result = await getPartList({ search: query, limit: 20 })
    sparePartOptions.value = result.items || []
  } catch (e) {
    ElMessage.error(t('spareLoadFailed'))
  } finally {
    spareLoading.value = false
  }
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
    ElMessage.success(t('maintReturnPartIdentified', { name: info.name || info.part_number }))
    // 自动填充表单
    returnPartSerial.value = info.serial_number
    returnPartNumber.value = info.part_number
    returnPartName.value = info.name
    selectedReturnPart.value = info.id
    returnPartScrap.value = true
  } catch (e) {
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

  editForm.value.return_parts.push({
    part_id: returnFoundInfo.value.id,
    part_number: returnFoundInfo.value.part_number,
    name: returnFoundInfo.value.name,
    serial_number: returnFoundInfo.value.serial_number,
    unit_price: returnFoundInfo.value.unit_price || 0,
    quantity: returnPartQty.value,
    scrap_in: returnPartScrap.value,
    is_from_scan: true,
    history: returnFoundInfo.value.history
  })

  ElMessage.success(t('maintReturnPartAdded', { sn: returnFoundInfo.value.serial_number }))
  clearReturnFound()
}

// 选择备件型号时自动填充
const onReturnPartSelect = () => {
  if (!selectedReturnPart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
  if (part) {
    returnPartNumber.value = part.part_number
    returnPartName.value = part.name || part.part_number
    returnPartScrap.value = true
  }
}

// 手动添加返回件
const addReturnPart = async () => {
  if (!returnPartSerial.value) {
    ElMessage.warning(t('maintEnterSerial'))
    return
  }

  // 检查是否已添加过该序列号
  const existing = editForm.value.return_parts.find(p => p.serial_number === returnPartSerial.value)
  if (existing) {
    ElMessage.warning(t('maintSerialAlreadyInList', { sn: returnPartSerial.value }))
    return
  }

  let partNumber = returnPartNumber.value
  let partName = returnPartName.value || returnPartNumber.value
  let partId = null
  let unitPrice = 0

  // 如果已经选择了备件型号
  if (selectedReturnPart.value) {
    const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
    if (part) {
      partId = part.id
      partNumber = part.part_number
      partName = part.name || part.part_number
      unitPrice = part.unit_price || 0
    }
  } else {
    // 如果没有选择备件型号，尝试通过序列号查询
    try {
      const info = await getPartBySerialNumber(returnPartSerial.value)
      partId = info.id
      partNumber = info.part_number
      partName = info.name
      unitPrice = info.unit_price || 0
      ElMessage.success(t('maintReturnPartIdentified', { name: info.name || info.part_number }))
    } catch (e) {
      // 序列号未找到，使用手动输入的信息
      partId = null
    }
  }

  editForm.value.return_parts.push({
    part_id: partId,
    part_number: partNumber,
    name: partName,
    serial_number: returnPartSerial.value,
    unit_price: unitPrice,
    quantity: returnPartQty.value,
    scrap_in: partId ? returnPartScrap.value : false,  // 有备件ID才能入报废库
    is_from_scan: false
  })

  ElMessage.success(t('maintReturnPartAddedNoMatch', { sn: returnPartSerial.value, hasId: partId ? '' : t('maintNoPartIdMatch') }))

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
  editForm.value.return_parts.splice(index, 1)
}

// 更新备件成本
const updateEditPartsCost = () => {
  editForm.value.parts_cost = editForm.value.spare_parts.reduce(
    (sum, p) => sum + p.quantity * p.unit_price, 0
  )
}

const loadMaintenance = async () => {
  loading.value = true
  try {
    const maintId = route.params.id
    const data = await getMaintenances()
    const found = (data.items || []).find(m => m.id === parseInt(maintId))
    if (found) {
      maintenance.value = found

      // 解析 parts_replaced 字段获取备件列表
      if (found.parts_replaced) {
        try {
          // 尝试JSON解析（新格式）
          const parsed = JSON.parse(found.parts_replaced)
          if (Array.isArray(parsed)) {
            // 分离备件和返回件
            maintenance.value.spare_parts_list = parsed.filter(p => !p.is_return).map(p => ({
              part_number: p.part_number || '',
              name: p.name || p.part_number || '',
              serial_number: p.serial_number || '',
              quantity: p.quantity || 1,
              unit_price: p.unit_price || 0
            }))
            maintenance.value.return_parts_list = parsed.filter(p => p.is_return).map(p => ({
              part_number: p.part_number || '',
              name: p.name || p.part_number || '',
              serial_number: p.serial_number || '',
              quantity: p.quantity || 1,
              scrap_in: p.scrap_in || false
            }))
            // 如果没有分离标记，尝试使用旧的 scrap_in 字段作为返回件
            if (maintenance.value.return_parts_list.length === 0 && parsed.some(p => p.scrap_in !== undefined)) {
              maintenance.value.return_parts_list = parsed.map(p => ({
                part_number: p.part_number || '',
                name: p.name || p.part_number || '',
                quantity: p.quantity || 1,
                scrap_in: p.scrap_in || false
              }))
            }
          } else {
            maintenance.value.spare_parts_list = []
            maintenance.value.return_parts_list = []
          }
        } catch (e) {
          // 兼容旧格式：解析 "型号(数量), 型号(数量)" 格式
          const partsList = found.parts_replaced.split(',').map(p => {
            const match = p.trim().match(/(.+)\((\d+)\)/)
            if (match) {
              return {
                part_number: match[1],
                name: match[1],
                quantity: parseInt(match[2]),
                unit_price: 0,
                scrap_in: false
              }
            }
            return { part_number: p.trim(), name: p.trim(), quantity: 1, unit_price: 0, scrap_in: false }
          })
          maintenance.value.spare_parts_list = partsList
          maintenance.value.return_parts_list = partsList.map(p => ({ ...p, unit_price: undefined }))
        }
      } else {
        maintenance.value.spare_parts_list = []
        maintenance.value.return_parts_list = []
      }

      // 加载设备信息
      if (found.device_id) {
        const devices = await getDevices()
        device.value = (devices.items || []).find(d => d.id === found.device_id)
      }
    }
  } catch (error) {
    ElMessage.error(t('maintLoadDetailFailed'))
  } finally {
    loading.value = false
  }
}

const openEditDialog = async () => {
  await loadInitialSpareParts()
  // 保存原始备件列表，用于后续判断新增的备件
  originalSpareParts.value = (maintenance.value.spare_parts_list || []).map(p => p.serial_number || p.part_id)
  editForm.value = {
    maint_type: maintenance.value.maint_type,
    spare_parts: maintenance.value.spare_parts_list || [],
    return_parts: maintenance.value.return_parts_list || [],
    parts_cost: maintenance.value.parts_cost || 0,
    labor_hours: maintenance.value.labor_hours || 0,
    labor_cost: maintenance.value.labor_cost || 0,
    vendor: maintenance.value.vendor || '',
    description: maintenance.value.description
  }
  showEditDialog.value = true
}

const goBack = () => {
  router.push('/maintenance')
}

const updateMaintenanceRecord = async () => {
  if (!editForm.value.description) {
    ElMessage.warning(t('maintEnterDescription'))
    return
  }

  try {
    // 合并备件和返回件数据，标记返回件
    const combinedParts = [
      ...editForm.value.spare_parts.map(p => ({ ...p, is_return: false })),
      ...editForm.value.return_parts.map(p => ({ ...p, is_return: true }))
    ]

    await updateMaintenance(maintenance.value.id, {
      ...editForm.value,
      parts_replaced: JSON.stringify(combinedParts)
    })

    // 处理备件出库 - 仅在通过手动搜索添加（非扫码）时需要
    // 扫码添加的备件已在 ScanSession 完成时自动出库并关联设备
    // 手动添加的备件需要在此处出库并关联设备
    for (const part of editForm.value.spare_parts) {
      if (!part.is_from_scan && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'out',
          quantity: part.quantity || 1,
          serial_number: part.serial_number,
          reason: `${t('spareReasonMaintenancePartReplace')} - ${maintenance.value.maint_no}`,
          operator: 'Web',
          reference: maintenance.value.maint_no,
          target_device_id: maintenance.value.device_id  // 关联目标设备
        })
      }
    }

    // 处理返回件入报废库 - 记录来源设备
    // 扫码添加的返回件已在 ScanSession 完成时自动入报废库并记录来源设备
    // 手动添加的返回件需要在此处入报废库
    for (const part of editForm.value.return_parts) {
      if (!part.is_from_scan && part.scrap_in && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'scrap_in',
          quantity: part.quantity,
          serial_number: part.serial_number,
          reason: t('spareReasonReturnPartScrap'),
          operator: 'Web',
          reference: maintenance.value.maint_no,
          source_device_id: maintenance.value.device_id  // 记录来源设备
        })
      }
    }

    ElMessage.success(t('maintRecordUpdated'))
    showEditDialog.value = false
    loadMaintenance()
  } catch (error) {
    ElMessage.error(t('maintUpdateFailed') + ': ' + (error.response?.data?.detail || error.message))
  }
}

const deleteMaintenanceRecord = async () => {
  try {
    await ElMessageBox.confirm(t('maintDeleteConfirmMsg'), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteMaintenance(maintenance.value.id)
    ElMessage.success(t('maintRecordDeleted'))
    router.push('/maintenance')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('maintDeleteFailed'))
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

/* 备件显示样式 */
.spare-parts-display {
  margin-bottom: 20px;
}

.parts-total {
  margin-top: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  text-align: right;
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
  gap: 10px;
  margin-bottom: 12px;
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

/* 返回件显示样式 */
.return-parts-display {
  margin-bottom: 20px;
}

.return-tip {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fdf6ec;
  border-radius: 4px;
  color: #909399;
  font-size: 12px;
}

/* 返回件编辑区域 */
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

.return-tip-form {
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

.cell-primary {
  color: var(--el-color-primary);
  font-weight: 500;
}

.cell-success {
  color: var(--el-color-success);
  font-weight: 500;
}
</style>