<template>
  <el-dialog v-model="visible" :title="editMode ? t('maintDialogEdit') : t('maintDialogAdd')" width="560px" append-to-body draggable align-center class="maint-add-dialog" @close="handleClose">
    <el-form :model="maintForm" label-width="80px" size="default">
      <!-- 基础信息 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Document /></el-icon>
          <span>{{ t('maintBasicSection') }}</span>
        </div>
        <el-form-item :label="t('faultDeviceLabel')" required v-if="!presetDeviceId">
          <el-select v-model="maintForm.device_id" :placeholder="t('maintSelectDevice')" style="width: 100%" :disabled="editMode" filterable>
            <el-option v-for="device in devices" :key="device.id" :label="device.name" :value="device.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('maintType')">
          <el-select v-model="maintForm.maint_type" style="width: 100%">
            <el-option :label="t('maintTypePreventiveFull')" value="preventive" />
            <el-option :label="t('maintTypeCorrectiveFull')" value="corrective" />
            <el-option :label="t('maintTypeUpgradeFull')" value="upgrade" />
            <el-option :label="t('maintTypeEmergencyFull')" value="emergency" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('maintDescription')" required>
          <el-input v-model="maintForm.description" type="textarea" :rows="2" :placeholder="t('maintDescPlaceholder')" />
        </el-form-item>
      </div>

      <!-- 备件更换 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Box /></el-icon>
          <span>{{ t('maintSparePartsSection') }}</span>
        </div>
        <div class="section-action-bar">
          <el-select
            v-model="selectedSparePart"
            :placeholder="t('maintSpareSearchPlaceholder')"
            filterable
            remote
            :remote-method="searchSpareParts"
            :loading="spareLoading"
            style="width: 200px"
            @change="addSparePartToForm"
            clearable
          />
          <el-button type="primary" size="small" @click="openScanDialog" v-if="showScanButton">
            <el-icon><Aim /></el-icon>
            {{ t('maintScanAddSpare') }}
          </el-button>
        </div>
        <el-table v-if="maintForm.spare_parts.length > 0" :data="maintForm.spare_parts" size="small" border style="margin-top: 8px">
          <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="100">
            <template #default="{ row }"><span class="text-primary">{{ row.serial_number || '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="po_number" :label="t('sparePoNumber')" width="80">
            <template #default="{ row }">{{ row.po_number || '-' }}</template>
          </el-table-column>
          <el-table-column prop="part_number" :label="t('maintColModel')" width="90" />
          <el-table-column prop="name" :label="t('maintColName')" min-width="80" />
          <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60">
            <template #default="{ row }">
              <el-input-number v-model="row.quantity" :min="1" size="small" controls-position="right" style="width: 50px" @change="updatePartsCost" />
            </template>
          </el-table-column>
          <el-table-column :label="t('colOperation')" width="40">
            <template #default="{ $index }">
              <el-button type="danger" size="small" link @click="removeSparePart($index)"><el-icon><Delete /></el-icon></el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-form-item :label="t('maintPartsCost')">
          <el-input-number v-model="maintForm.parts_cost" :min="0" :precision="2" style="width: 120px" />
          <span class="unit-text">元</span>
        </el-form-item>
      </div>

      <!-- 返回件 -->
      <div class="form-section" v-if="showReturnParts">
        <div class="section-header">
          <el-icon><RefreshRight /></el-icon>
          <span>{{ t('maintReturnPartsSection') }}</span>
        </div>
        <div class="section-action-bar">
          <el-input
            v-model="returnScanInput"
            :placeholder="t('maintReturnScanPlaceholder')"
            style="width: 160px"
            @keyup.enter="scanReturnPart"
            clearable
          />
          <el-button size="small" @click="scanReturnPart" :loading="returnScanLoading">{{ t('spareQuery') }}</el-button>
        </div>
        <el-table v-if="maintForm.return_parts.length > 0" :data="maintForm.return_parts" size="small" border style="margin-top: 8px">
          <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="100">
            <template #default="{ row }"><span class="text-primary">{{ row.serial_number || '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="part_number" :label="t('maintColModel')" width="90" />
          <el-table-column prop="name" :label="t('maintColName')" min-width="80" />
          <el-table-column :label="t('maintReturnScrap')" width="70">
            <template #default="{ row }">
              <el-checkbox v-model="row.scrap_in" size="small" />
            </template>
          </el-table-column>
          <el-table-column :label="t('colOperation')" width="40">
            <template #default="{ $index }">
              <el-button type="danger" size="small" link @click="removeReturnPart($index)"><el-icon><Delete /></el-icon></el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 工时成本 -->
      <div class="form-section">
        <div class="section-header">
          <el-icon><Coin /></el-icon>
          <span>{{ t('maintCostSection') }}</span>
        </div>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item :label="t('maintLaborHours')">
              <el-input-number v-model="maintForm.labor_hours" :min="0" :precision="1" style="width: 120px" />
              <span class="unit-text">{{ t('maintHoursUnit') }}</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="t('maintLaborCost')">
              <el-input-number v-model="maintForm.labor_cost" :min="0" :precision="2" style="width: 120px" />
              <span class="unit-text">元</span>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item :label="t('maintVendor')">
          <el-input v-model="maintForm.vendor" style="width: 200px" />
        </el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('actionCancel') }}</el-button>
      <el-button type="primary" @click="submitForm" :loading="submitting">{{ t('maintConfirm') }}</el-button>
    </template>
  </el-dialog>

  <!-- 扫码会话对话框 -->
  <el-dialog v-model="showScanSessionDialog" title="扫码添加备件" width="400px" append-to-body>
    <div class="scan-session-info" v-if="scanSessionCode">
      <p>扫码会话码: <strong>{{ scanSessionCode }}</strong></p>
      <p>请使用扫码枪扫描备件序列号</p>
    </div>
    <el-button type="primary" @click="closeScanSession">完成扫码</el-button>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Box, Aim, Delete, Coin, RefreshRight } from '@element-plus/icons-vue'
import { createMaintenance, updateMaintenance, getDevices, searchInStockParts, getPartBySerialNumber, createScanSession, getScanSession, addScanItem, completeScanSession } from '@/api'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  presetDeviceId: { type: Number, default: null },  // 预设设备ID（设备详情页使用）
  presetDeviceName: { type: String, default: '' },  // 预设设备名称
  editData: { type: Object, default: null },        // 编辑时传入的数据
  showScanButton: { type: Boolean, default: true }, // 是否显示扫码按钮
  showReturnParts: { type: Boolean, default: true } // 是否显示返回件区域
})

const emit = defineEmits(['update:modelValue', 'success'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const editMode = computed(() => props.editData !== null)
const submitting = ref(false)

// 设备列表（仅在需要选择设备时加载）
const devices = ref([])

const maintForm = ref({
  device_id: null,
  maint_type: 'corrective',
  spare_parts: [],
  return_parts: [],
  parts_cost: 0,
  labor_hours: 0,
  labor_cost: 0,
  vendor: '',
  description: ''
})

// 备件相关
const selectedSparePart = ref(null)
const sparePartOptions = ref([])
const spareLoading = ref(false)
const returnScanInput = ref('')
const returnScanLoading = ref(false)

// 扫码会话
const showScanSessionDialog = ref(false)
const scanSessionCode = ref('')
const scanSessionId = ref(null)

// 初始化表单
watch(() => props.modelValue, (val) => {
  if (val) {
    if (props.editData) {
      // 编辑模式
      maintForm.value = {
        id: props.editData.id,
        device_id: props.editData.device_id,
        maint_type: props.editData.maint_type || 'corrective',
        spare_parts: props.editData.spare_parts || [],
        return_parts: [],
        parts_cost: props.editData.parts_cost || 0,
        labor_hours: props.editData.labor_hours || 0,
        labor_cost: props.editData.labor_cost || 0,
        vendor: props.editData.vendor || '',
        description: props.editData.description || ''
      }
    } else {
      // 新增模式
      maintForm.value = {
        device_id: props.presetDeviceId || null,
        maint_type: 'corrective',
        spare_parts: [],
        return_parts: [],
        parts_cost: 0,
        labor_hours: 0,
        labor_cost: 0,
        vendor: '',
        description: ''
      }
    }
    selectedSparePart.value = null
    sparePartOptions.value = []

    // 如果没有预设设备，加载设备列表
    if (!props.presetDeviceId && !props.editData) {
      loadDevices()
    }
  }
})

const loadDevices = async () => {
  try {
    const result = await getDevices({ limit: 500 })
    devices.value = result.items || []
  } catch (error) {
    // Silent fail
  }
}

// 备件搜索
const searchSpareParts = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    const result = await searchInStockParts(query)
    sparePartOptions.value = (result.items || []).map(item => ({
      id: item.instance_id,
      part_id: item.id,
      part_number: item.part_number,
      name: item.name,
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      po_number: item.po_number || ''
    }))
  } catch (error) {
    sparePartOptions.value = []
  } finally {
    spareLoading.value = false
  }
}

// 添加备件到表单
const addSparePartToForm = (item) => {
  if (!item) return
  const existing = maintForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
  if (existing) {
    existing.quantity++
  } else {
    maintForm.value.spare_parts.push({
      part_id: item.part_id,
      part_number: item.part_number,
      name: item.name,
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      quantity: 1,
      po_number: item.po_number || ''
    })
  }
  selectedSparePart.value = null
  updatePartsCost()
}

// 移除备件
const removeSparePart = (index) => {
  maintForm.value.spare_parts.splice(index, 1)
  updatePartsCost()
}

// 计算备件成本
const updatePartsCost = () => {
  maintForm.value.parts_cost = maintForm.value.spare_parts.reduce((sum, p) => sum + (p.unit_price * p.quantity), 0)
}

// 扫码添加备件
const openScanDialog = async () => {
  try {
    const result = await createScanSession({ session_type: 'maintenance_out', device_id: maintForm.value.device_id })
    scanSessionCode.value = result.session_code
    scanSessionId.value = result.id
    showScanSessionDialog.value = true
  } catch (error) {
    ElMessage.error('创建扫码会话失败')
  }
}

const closeScanSession = async () => {
  try {
    const result = await completeScanSession(scanSessionCode.value)
    // 将扫码结果添加到备件列表
    if (result.items && result.items.length > 0) {
      for (const item of result.items) {
        const existing = maintForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
        if (existing) {
          existing.quantity += item.quantity || 1
        } else {
          maintForm.value.spare_parts.push({
            part_id: item.part_id,
            part_number: item.part_number,
            name: item.name,
            serial_number: item.serial_number,
            unit_price: item.unit_price || 0,
            quantity: item.quantity || 1,
            po_number: item.po_number || ''
          })
        }
      }
      updatePartsCost()
    }
    showScanSessionDialog.value = false
    ElMessage.success('扫码添加完成')
  } catch (error) {
    ElMessage.error('完成扫码会话失败')
  }
}

// 返回件扫描
const scanReturnPart = async () => {
  if (!returnScanInput.value) return
  returnScanLoading.value = true
  try {
    const result = await getPartBySerialNumber(returnScanInput.value)
    if (result && result.instance) {
      const existing = maintForm.value.return_parts.find(p => p.serial_number === result.instance.serial_number)
      if (existing) {
        ElMessage.warning('该返回件已在列表中')
      } else {
        maintForm.value.return_parts.push({
          part_id: result.id,
          part_number: result.part_number,
          name: result.name,
          serial_number: result.instance.serial_number,
          unit_price: result.instance.unit_price || 0,
          scrap_in: false
        })
      }
      returnScanInput.value = ''
    } else {
      ElMessage.warning('未找到该序列号的备件')
    }
  } catch (error) {
    ElMessage.error('查询备件失败')
  } finally {
    returnScanLoading.value = false
  }
}

// 移除返回件
const removeReturnPart = (index) => {
  maintForm.value.return_parts.splice(index, 1)
}

// 提交表单
const submitForm = async () => {
  if (!maintForm.value.device_id && !props.presetDeviceId) {
    ElMessage.warning('请选择设备')
    return
  }
  if (!maintForm.value.description) {
    ElMessage.warning('请填写维修描述')
    return
  }

  submitting.value = true
  try {
    const deviceName = props.presetDeviceName || devices.value.find(d => d.id === maintForm.value.device_id)?.name || ''
    const submitData = {
      ...maintForm.value,
      device_id: props.presetDeviceId || maintForm.value.device_id,
      device_name: deviceName
    }

    if (editMode.value) {
      await updateMaintenance(maintForm.value.id, submitData)
      ElMessage.success(t('maintUpdateSuccess'))
    } else {
      await createMaintenance(submitData)
      ElMessage.success(t('maintAddSuccess'))
    }

    visible.value = false
    emit('success')
  } catch (error) {
    ElMessage.error(editMode.value ? t('maintUpdateFailed') : t('maintAddFailed'))
  } finally {
    submitting.value = false
  }
}

const handleClose = () => {
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
}
</script>

<style scoped>
.maint-add-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}

.maint-add-dialog .section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.maint-add-dialog .section-header .el-icon {
  color: var(--accent-primary);
}

.maint-add-dialog .section-action-bar {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.maint-add-dialog .unit-text {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 4px;
}

.maint-add-dialog .text-primary {
  color: var(--accent-secondary);
  font-weight: 500;
}

.maint-add-dialog .el-form-item__content {
  flex-wrap: nowrap;
}

.scan-session-info {
  text-align: center;
  padding: 20px;
}

.scan-session-info strong {
  font-size: 18px;
  color: var(--accent-primary);
}
</style>