<template>
  <div class="spare-parts">
    <el-tabs v-model="activeTab">
      <!-- 备件列表 Tab -->
      <el-tab-pane :label="t('sparePartsList')" name="parts">
        <PartsTable
          ref="partsTableRef"
          @scan-in="showScanDialog('in')"
          @scan-out="showScanDialog('out')"
          @show-detail="showPartDetail"
          @refreshed="onPartsRefreshed"
        />
      </el-tab-pane>

      <!-- 出入库历史 Tab -->
      <el-tab-pane :label="t('spareMovementsHistory')" name="movements">
        <MovementsTable ref="movementsTableRef" @show-detail="showMovementDetail" />
      </el-tab-pane>
    </el-tabs>

    <!-- 备件详情对话框 -->
    <PartDetailDialog v-model="detailDialogVisible" :part="currentDetailPart" />

    <!-- 出入库详情对话框 -->
    <MovementDetailDialog v-model="movementDetailVisible" :movement="currentMovement" />

    <!-- 选择备件和填PO号对话框 -->
    <el-dialog v-model="selectPartDialogVisible" :title="t('spareSelectPart')" width="500px">
      <el-form :model="scanInForm" label-width="80px">
        <el-form-item :label="t('spareName')" required>
          <el-select v-model="scanInForm.part_id" :placeholder="t('spareSelectPartPlaceholder')" filterable>
            <el-option
              v-for="part in partsList"
              :key="part.id"
              :label="`${part.name} (${part.part_number})`"
              :value="part.id"
            >
              <span>{{ part.name }}</span>
              <span style="color: var(--el-text-color-secondary); margin-left: 8px;">{{ part.part_number }}</span>
              <span style="color: var(--el-text-color-secondary); margin-left: 8px;">{{ t('spareQuantity') }}: {{ part.quantity_in_stock }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item :label="t('sparePoNumber')" required>
          <el-input v-model="scanInForm.po_number" :placeholder="t('sparePoNumberPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('spareLocation')">
          <el-input v-model="scanInForm.location" :placeholder="t('spareLocation')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="selectPartDialogVisible = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="startScanIn" :disabled="!scanInForm.part_id || !scanInForm.po_number">
          {{ t('spareStartScanIn') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 扫码出入库对话框 -->
    <el-dialog v-model="scanDialogVisible" :title="scanMode === 'in' ? t('spareScanIn') : t('spareScanOut')" width="700px">
      <ScanSession
        ref="scanSessionRef"
        :default-type="scanMode"
        :part-id="scanInForm.part_id"
        :po-number="scanInForm.po_number"
        :location="scanInForm.location"
        :auto-start="scanDialogVisible"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import ScanSession from '@/components/ScanSession.vue'
import PartsTable from './spare-parts/PartsTable.vue'
import MovementsTable from './spare-parts/MovementsTable.vue'
import PartDetailDialog from './spare-parts/PartDetailDialog.vue'
import MovementDetailDialog from './spare-parts/MovementDetailDialog.vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const activeTab = ref('parts')
const partsTableRef = ref(null)
const movementsTableRef = ref(null)

// 备件列表（用于选择备件对话框）
const partsList = ref([])

// 备件详情对话框
const detailDialogVisible = ref(false)
const currentDetailPart = ref(null)

// 出入库详情对话框
const movementDetailVisible = ref(false)
const currentMovement = ref(null)

// 扫码会话相关
const scanDialogVisible = ref(false)
const scanMode = ref('in')
const scanSessionRef = ref(null)
const selectPartDialogVisible = ref(false)
const scanInForm = reactive({
  part_id: null,
  po_number: '',
  location: ''
})

// 显示扫码对话框（入库需要先选择备件）
const showScanDialog = (mode) => {
  scanMode.value = mode
  if (mode === 'in') {
    selectPartDialogVisible.value = true
    scanInForm.part_id = null
    scanInForm.po_number = ''
    scanInForm.location = ''
  } else {
    scanDialogVisible.value = true
  }
}

// 开始扫码入库
const startScanIn = () => {
  selectPartDialogVisible.value = false
  scanDialogVisible.value = true
}

// 扫码会话完成处理
const onScanSessionComplete = async (result) => {
  const { items, message } = result
  if (items && items.length === 0) return

  scanDialogVisible.value = false

  if (message) {
    ElMessage.success(message)
  } else {
    ElMessage.success(`${t('msgSuccess')} ${items?.length || 0} ${t('dashAction')}`)
  }

  partsTableRef.value?.loadParts()
}

// 显示备件详情
const showPartDetail = (row) => {
  currentDetailPart.value = row
  detailDialogVisible.value = true
}

// 显示出入库详情
const showMovementDetail = (detail) => {
  currentMovement.value = detail
  movementDetailVisible.value = true
}

// 备件刷新后获取列表
const onPartsRefreshed = () => {
  if (partsTableRef.value) {
    partsList.value = partsTableRef.value.parts || []
  }
}
</script>

<style scoped>
.spare-parts {
  padding: 0;
}
</style>