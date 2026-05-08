<template>
  <div class="scan-session-wrapper">
    <!-- 会话创建阶段 -->
    <div v-if="!sessionCode && !autoStart" class="create-session">
      <el-form :model="sessionForm" label-width="80px">
        <el-form-item :label="t('scanOperationType')">
          <el-radio-group v-model="sessionForm.session_type">
            <el-radio label="in">{{ t('scanStockIn') }}</el-radio>
            <el-radio label="out">{{ t('scanStockOut') }}</el-radio>
            <el-radio label="return">{{ t('scanReturn') }}</el-radio>
            <el-radio label="scrap_out">{{ t('scanScrapOut') }}</el-radio>
            <el-radio label="maintenance">{{ t('scanMaintenanceSpare') }}</el-radio>
            <el-radio label="task">{{ t('scanOpsTask') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="sessionForm.session_type === 'maintenance'" :label="t('scanWorkOrder')">
          <el-input v-model="sessionForm.reference" :placeholder="t('scanWorkOrderPlaceholder')" />
        </el-form-item>
        <el-form-item v-if="sessionForm.session_type === 'task'" :label="t('scanTaskNumber')">
          <el-input v-model="sessionForm.reference" :placeholder="t('scanTaskNumberPlaceholder')" />
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="createSession" :loading="creating">
        {{ t('scanCreateSession') }}
      </el-button>
    </div>

    <!-- 等待自动创建会话 -->
    <div v-if="!sessionCode && autoStart" class="waiting-session">
      <el-icon class="loading-icon"><Loading /></el-icon>
      <span>{{ t('scanCreatingSession') }}</span>
    </div>

    <!-- 扫码阶段 -->
    <div v-else class="scan-phase">
      <!-- 条形码显示 -->
      <div v-if="!joined" class="barcode-section">
        <div class="barcode-tip">
          <h3>{{ t('scanBarcodeTipTitle') }}</h3>
          <p>{{ t('scanBarcodeTipDesc') }}</p>
        </div>
        <div class="barcode-display">
          <svg id="barcodeSvg" class="barcode-svg"></svg>
          <div class="barcode-text">NAS-SCAN:{{ sessionCode }}</div>
        </div>
        <p class="session-info">
          {{ t('scanSessionCodeLabel') }}<strong>{{ sessionCode }}</strong>
          <br>
          {{ t('scanExpiresLabel') }}{{ expiresAt }}{{ t('scan30Minutes') }}
        </p>
      </div>

      <!-- 扫码枪已加入 -->
      <div v-else class="scan-active">
        <div class="scan-header">
          <el-tag type="success" size="large">
            {{ t('scanScannerConnected') }}
          </el-tag>
          <span class="scan-type">
            {{ sessionTypeText }} - {{ sessionForm.session_type }}
          </span>
        </div>

        <!-- 扫描结果列表 -->
        <el-card class="scan-items-card">
          <template #header>
            <div class="items-header">
              <span>{{ t('scanScannedParts') }}（{{ scanItems.length }} {{ t('scanItemCount') }}）</span>
              <el-button size="small" @click="refreshSession">
                <el-icon><Aim /></el-icon>
                {{ t('actionRefresh') }}
              </el-button>
            </div>
          </template>

          <el-table v-if="scanItems.length > 0" :data="scanItems" stripe border>
            <el-table-column prop="serial_number" :label="t('scanColSerialNumber')" width="150" />
            <el-table-column prop="part_number" :label="t('scanColModel')" width="120">
              <template #default="{ row }">{{ row.part_number || t('scanUnknown') }}</template>
            </el-table-column>
            <el-table-column prop="name" :label="t('scanColName')" width="120">
              <template #default="{ row }">{{ row.name || t('scanNotFoundInList') }}</template>
            </el-table-column>
            <el-table-column prop="unit_price" :label="t('scanColUnitPrice')" width="100">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.unit_price"
                  :min="0"
                  :precision="2"
                  size="small"
                  controls-position="right"
                  :placeholder="t('scanUnitPricePlaceholder')"
                />
              </template>
            </el-table-column>
            <el-table-column prop="notes" :label="t('scanColNotes')" width="120">
              <template #default="{ row }">
                <el-input
                  v-model="row.notes"
                  size="small"
                  :placeholder="t('scanNotesPlaceholder')"
                />
              </template>
            </el-table-column>
            <el-table-column prop="found_in_stock" :label="t('scanColStatus')" width="80">
              <template #default="{ row }">
                <el-tag :type="row.part_id ? 'success' : 'warning'" size="small">
                  {{ row.part_id ? t('scanMatched') : t('scanNotMatched') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="t('scanColOperation')" width="60">
              <template #default="{ $index }">
                <el-button type="danger" size="small" link @click="removeItem($index)">
                  {{ t('scanRemove') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else :description="t('scanWaitForScanner')" />
        </el-card>

        <!-- 操作信息 -->
        <el-form :model="submitForm" label-width="80px" style="margin-top: 16px">
          <el-form-item :label="t('scanOperator')">
            <el-input v-model="submitForm.operator" />
          </el-form-item>
          <el-form-item :label="t('scanReasonOrNotes')">
            <el-input v-model="submitForm.reason" type="textarea" />
          </el-form-item>
          <el-form-item v-if="sessionForm.session_type === 'maintenance'" :label="t('scanRefOrder')">
            <el-input v-model="submitForm.reference" :value="sessionForm.reference" disabled />
          </el-form-item>
        </el-form>

        <!-- 提交按钮 -->
        <div class="submit-actions">
          <el-button @click="cancelSession">{{ t('scanCancelSessionBtn') }}</el-button>
          <el-button
            type="primary"
            @click="submitSession"
            :loading="submitting"
          >
            {{ t('scanConfirmSubmitBtn') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 完成提示 -->
    <el-dialog v-model="showCompleteDialog" :title="t('scanCompleteDialogTitle')" width="400px">
      <el-result icon="success" :title="t('scanOpSuccessTitle')" :sub-title="completeMessage">
        <template #extra>
          <el-button type="primary" @click="resetSession">{{ t('scanContinueBtn') }}</el-button>
          <el-button @click="showCompleteDialog = false">{{ t('actionClose') }}</el-button>
        </template>
      </el-result>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, Loading } from '@element-plus/icons-vue'
import JsBarcode from 'jsbarcode'
import {
  createScanSession,
  getScanSession,
  completeScanSession,
  deleteScanSession,
  removeScanItem
} from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

// Props
const props = defineProps({
  defaultType: {
    type: String,
    default: 'in' // in, out, maintenance, task, return, scrap_out
  },
  reference: String,
  partId: Number,  // 入库备件ID
  poNumber: String,  // PO号
  location: String,  // 存放位置
  deviceId: Number,  // 设备ID（出库/返回件时关联设备）
  autoStart: Boolean  // 是否自动创建会话（对话框打开时）
})

// Emits
const emit = defineEmits(['complete', 'cancel'])

// 状态
const creating = ref(false)
const sessionCode = ref('')
const expiresAt = ref('')
const joined = ref(false)
const scanItems = ref([])
const submitting = ref(false)
const showCompleteDialog = ref(false)
const completeMessage = ref('')
const pollTimer = ref(null)

// 表单
const sessionForm = ref({
  session_type: props.defaultType,
  reference: props.reference || ''
})

const submitForm = ref({
  operator: '',
  reason: '',
  reference: props.reference || ''
})

// 停止轮询
const stopPolling = () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

// 重置状态（每次打开对话框时调用）
const resetState = () => {
  sessionCode.value = ''
  expiresAt.value = ''
  joined.value = false
  scanItems.value = []
  stopPolling()
  // 重置 session_type 为当前 props 的值
  sessionForm.value.session_type = props.defaultType
}

// 组件挂载后检查是否需要自动创建会话
onMounted(() => {
  // 入库需要 partId 和 poNumber，出库和返回件不需要
  if (props.autoStart) {
    if (props.defaultType === 'in' && props.partId && props.poNumber) {
      createSession()
    } else if (props.defaultType === 'out' || props.defaultType === 'return' || props.defaultType === 'scrap_out') {
      createSession()
    }
  }
})

// 当autoStart变化时重新创建会话
watch(
  () => props.autoStart,
  (autoStart, oldStart) => {
    // 只有从false变true时才触发（避免重复创建）
    if (autoStart && !oldStart) {
      resetState()
      if (props.defaultType === 'in' && props.partId && props.poNumber) {
        createSession()
      } else if (props.defaultType === 'out' || props.defaultType === 'return' || props.defaultType === 'scrap_out') {
        createSession()
      }
    }
  }
)

// 计算属性
const sessionTypeText = computed(() => {
  const texts = {
    in: t('scanStockIn'),
    out: t('scanStockOut'),
    return: t('scanReturn'),
    scrap_out: t('scanScrapOut'),
    maintenance: t('scanMaintenanceSpare'),
    task: t('scanOpsTask')
  }
  return texts[sessionForm.value.session_type] || ''
})

// 生成条形码
const generateBarcode = () => {
  nextTick(() => {
    try {
      const svg = document.getElementById('barcodeSvg')
      if (svg && sessionCode.value) {
        JsBarcode(svg, `NAS-SCAN:${sessionCode.value}`, {
          format: 'CODE128',
          width: 2,
          height: 80,
          displayValue: false,
          margin: 10,
          background: '#fff',
          lineColor: '#003087'
        })
      } else if (svg) {
        // 清空SVG
        svg.innerHTML = ''
      }
    } catch (e) {
      console.error('Barcode generation failed:', e)
    }
  })
}

// 监听sessionCode变化重新生成条形码
watch(sessionCode, (newCode) => {
  if (newCode) {
    generateBarcode()
  }
})

// 创建会话
const createSession = async () => {
  creating.value = true
  try {
    const result = await createScanSession({
      session_type: sessionForm.value.session_type,
      reference: sessionForm.value.reference,
      part_id: props.partId,  // 入库备件ID
      po_number: props.poNumber,  // PO号
      location: props.location,  // 存放位置
      device_id: props.deviceId  // 设备ID（出库/返回件关联设备）
    })
    sessionCode.value = result.session_code
    expiresAt.value = result.expires_at

    // 显示备件信息（如果有）
    if (result.part_info) {
      ElMessage.success(t('scanSessionCreatedWithPart').replace('{name}', result.part_info.name))
    } else {
      ElMessage.success(t('scanSessionCreated'))
    }

    // 生成条形码
    generateBarcode()

    // 开始轮询检查状态
    startPolling()
  } catch (e) {
    ElMessage.error(t('scanCreateFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    creating.value = false
  }
}

// 开始轮询
const startPolling = () => {
  // 每2秒检查一次会话状态
  pollTimer.value = setInterval(async () => {
    if (!sessionCode.value) return
    try {
      const result = await getScanSession(sessionCode.value)
      joined.value = result.joined

      // 更新items时保留本地修改的单价和备注
      const existingItems = scanItems.value
      const newItems = result.items || []

      // 对于已存在的item，保留本地单价和备注
      newItems.forEach(newItem => {
        const existing = existingItems.find(e => e.serial_number === newItem.serial_number)
        if (existing) {
          if (existing.unit_price !== undefined) {
            newItem.unit_price = existing.unit_price
          }
          if (existing.notes !== undefined) {
            newItem.notes = existing.notes  // 保留备注
          }
        }
      })
      scanItems.value = newItems

      // 如果过期或完成，提示用户手动关闭
      if (result.status === 'expired') {
        ElMessage.warning(t('scanSessionExpired'))
      }
      if (result.status === 'completed') {
        ElMessage.success(t('scanSessionCompleted'))
        stopPolling()
      }
    } catch (e) {
      // 不自动退出，让用户手动处理
      if (e.response?.status === 404) {
        ElMessage.warning(t('scanSessionNotFound'))
      }
    }
  }, 2000)
}

// 刷新会话
const refreshSession = async () => {
  if (!sessionCode.value) return
  try {
    const result = await getScanSession(sessionCode.value)
    scanItems.value = result.items || []
  } catch (e) {
    ElMessage.error(t('scanRefreshFailed'))
  }
}

// 更新数量（本地）
const updateItemQuantity = (row) => {
  // 数量在本地更新，提交时一起发送
}

// 移除项
const removeItem = async (index) => {
  const item = scanItems.value[index]
  if (!item) return

  try {
    // 调用后端删除
    await removeScanItem(sessionCode.value, item.serial_number)
    // 本地也移除
    scanItems.value.splice(index, 1)
    ElMessage.success(t('scanRemoved') + ': ' + item.serial_number)
  } catch (e) {
    ElMessage.error(t('scanRemoveFailed') + ': ' + (e.response?.data?.detail || e.message))
  }
}

// 提交会话
const submitSession = async () => {
  submitting.value = true
  try {
    // 提交时传递包含单价和备注的 items，以及入库原因
    const itemsWithNotes = scanItems.value.map(item => ({
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      notes: item.notes || ''  // 每个备件的备注
    }))
    const result = await completeScanSession(sessionCode.value, itemsWithNotes.length > 0 ? itemsWithNotes : null, submitForm.value.reason)
    stopPolling()

    // 触发完成回调，传递后端返回的完整结果
    emit('complete', {
      session_type: sessionForm.value.session_type,
      items: result.items || scanItems.value,
      operator: submitForm.value.operator,
      reason: submitForm.value.reason,
      reference: submitForm.value.reference,
      scrap_in_count: result.scrap_in_count,
      scrap_out_count: result.scrap_out_count,
      added_count: result.added_count,
      out_count: result.out_count,
      message: result.message
    })

    // 不显示完成对话框，直接关闭让父组件处理
    // completeMessage.value = `成功处理 ${scanItems.value.length} 个备件`
    // showCompleteDialog.value = true
  } catch (e) {
    ElMessage.error(t('scanSubmitFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

// 取消会话
const cancelSession = async () => {
  try {
    if (sessionCode.value) {
      await deleteScanSession(sessionCode.value)
    }
    stopPolling()
    sessionCode.value = ''
    emit('cancel')
  } catch (e) {
    // 忽略错误，直接重置
    sessionCode.value = ''
  }
}

// 重置会话
const resetSession = () => {
  showCompleteDialog.value = false
  sessionCode.value = ''
  scanItems.value = []
  joined.value = false
}

// 暴露方法
defineExpose({
  createSession,
  cancelSession,
  getScanItems: () => scanItems.value
})

// 清理
onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.scan-session-wrapper {
  padding: 20px;
}

.create-session {
  max-width: 400px;
}

.waiting-session {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--el-text-color-secondary);
}

.loading-icon {
  font-size: 32px;
  margin-bottom: 16px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.barcode-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.barcode-tip {
  text-align: center;
  margin-bottom: 20px;
}

.barcode-tip h3 {
  font-size: 18px;
  margin-bottom: 8px;
}

.barcode-tip p {
  color: var(--el-text-color-secondary);
}

.barcode-display {
  margin: 20px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.barcode-svg {
  border: 2px solid var(--el-border-color);
  border-radius: 8px;
  background: #fff;
}

.barcode-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-color-primary);
  margin-top: 8px;
  letter-spacing: 2px;
}

.session-info {
  text-align: center;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.session-info strong {
  color: var(--el-color-primary);
  font-size: 16px;
}

.scan-active {
  max-width: 800px;
}

.scan-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.scan-type {
  font-size: 16px;
  color: var(--el-text-color-primary);
}

.scan-items-card {
  margin-bottom: 16px;
}

.items-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.submit-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 20px;
}
</style>