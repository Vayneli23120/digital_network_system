<template>
  <div class="scanner-page">
    <!-- 未加入会话时 -->
    <div v-if="!joined" class="join-phase">
      <h1>{{ t('scannerTerminalTitle') }}</h1>
      <p class="tip">{{ t('scannerTerminalTip') }}</p>

      <div class="input-section">
        <!-- 扫码输入框（扫码枪会自动输入） -->
        <input
          ref="sessionInput"
          v-model="sessionCode"
          class="session-input"
          :placeholder="t('scannerSessionCodePlaceholder')"
          @keyup.enter="joinSession"
          autofocus
        />

        <button class="join-btn" @click="joinSession" :disabled="!sessionCode">
          {{ t('scannerJoinSession') }}
        </button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <!-- 已加入会话 -->
    <div v-else class="scan-phase">
      <div class="session-info">
        <h2>{{ sessionTypeText }}</h2>
        <p>{{ t('scannerSessionCodeLabel') }}{{ sessionCode }}</p>
      </div>

      <!-- 扫码输入 -->
      <div class="scan-section">
        <input
          ref="serialInput"
          v-model="serialNumber"
          class="serial-input"
          :placeholder="t('scannerScanSerialPlaceholder')"
          @keyup.enter="scanSerial"
          autofocus
        />
        <button class="scan-btn" @click="scanSerial" :disabled="!serialNumber">
          {{ t('scannerConfirmScan') }}
        </button>
      </div>

      <!-- 已扫描列表 -->
      <div class="scan-list">
        <h3>{{ t('scannerScannedItems', { count: scannedItems.length }) }}</h3>
        <div v-if="scannedItems.length > 0" class="items">
          <div v-for="item in scannedItems" :key="item.serial_number" class="item-card">
            <div class="item-info">
              <span class="serial">{{ item.serial_number }}</span>
              <span class="name">{{ item.name || t('scannerUnmatched') }}</span>
              <span class="qty">{{ t('scannerQuantityLabel') }}{{ item.quantity }}</span>
            </div>
            <button class="remove-btn" @click="removeItem(item.serial_number)">×</button>
          </div>
        </div>
        <p v-else class="empty-tip">{{ t('scannerWaitingScan') }}</p>
      </div>

      <!-- 操作按钮 -->
      <div class="actions">
        <button class="exit-btn" @click="exitSession">{{ t('scannerExitSession') }}</button>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="successMsg" class="success">{{ successMsg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { joinScanSession, addScanItem, getScanSession } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

const sessionCode = ref('')
const joined = ref(false)
const sessionType = ref('')
const serialNumber = ref('')
const scannedItems = ref([])
const error = ref('')
const successMsg = ref('')

const sessionInput = ref(null)
const serialInput = ref(null)

const sessionTypeText = computed(() => {
  const texts = {
    in: t('scanStockIn') + t('scannerScanTitle'),
    out: t('scanStockOut') + t('scannerScanTitle'),
    maintenance: t('scanMaintenanceSpare'),
    task: t('scanOpsTask')
  }
  return texts[sessionType.value] || t('scannerScanTitle')
})

// 解析扫码内容（可能是 NAS-SCAN:XXXXXX 格式）
const parseScanContent = (content) => {
  if (content.startsWith('NAS-SCAN:')) {
    return content.substring(9)
  }
  return content.trim().toUpperCase()
}

// 加入会话
const joinSession = debounce(async () => {
  error.value = ''
  successMsg.value = ''

  const code = parseScanContent(sessionCode.value)
  if (!code) {
    error.value = t('scannerEnterValidCode')
    return
  }

  try {
    const result = await cachedRequest(
      () => joinScanSession({ session_code: code }),
      'scan_session_join',
      { code },
      { forceRefresh: true }
    )
    sessionCode.value = code
    sessionType.value = result.session_type
    joined.value = true
    successMsg.value = t('scannerJoinedSession')

    // 获取已有项目
    const sessionData = await cachedRequest(
      () => getScanSession(code),
      'scan_session',
      { code },
      { forceRefresh: true }
    )
    scannedItems.value = sessionData.items || []

    // 聚焦到序列号输入框
    nextTick(() => {
      serialInput.value?.focus()
    })
  } catch (e) {
    if (e.name !== 'CanceledError') {
      error.value = e.response?.data?.detail || t('scannerJoinFailed')
    }
  }
}, 300)

// 扫描序列号
const scanSerial = debounce(async () => {
  error.value = ''
  successMsg.value = ''

  const sn = serialNumber.value.trim()
  if (!sn) return

  try {
    const result = await cachedRequest(
      () => addScanItem(sessionCode.value, sn, 1),
      'scan_item_add',
      { code: sessionCode.value, sn },
      { forceRefresh: true }
    )

    // 添加到列表
    const existing = scannedItems.value.find(i => i.serial_number === sn)
    if (existing) {
      existing.quantity += 1
    } else {
      scannedItems.value.push({
        serial_number: sn,
        part_id: result.part_id,
        name: result.name,
        part_number: result.part_number,
        unit_price: result.unit_price,
        quantity: 1
      })
    }

    successMsg.value = result.part_id ? t('scannerAdded', { name: result.name }) : t('scannerSerialRecorded', { sn })
    serialNumber.value = ''

    // 保持聚焦
    nextTick(() => {
      serialInput.value?.focus()
    })
  } catch (e) {
    if (e.name !== 'CanceledError') {
      error.value = e.response?.data?.detail || t('scannerScanFailed')
    }
  }
}, 300)

// 移除项目
const removeItem = (sn) => {
  const idx = scannedItems.value.findIndex(i => i.serial_number === sn)
  if (idx >= 0) {
    scannedItems.value.splice(idx, 1)
  }
}

// 退出会话
const exitSession = () => {
  joined.value = false
  sessionCode.value = ''
  serialNumber.value = ''
  scannedItems.value = []
  sessionType.value = ''

  nextTick(() => {
    sessionInput.value?.focus()
  })
}

// 页面加载聚焦
onMounted(() => {
  sessionInput.value?.focus()
})
</script>

<style scoped>
.scanner-page {
  max-width: 400px;
  margin: 20px auto;
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

.join-phase, .scan-phase {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
}

h1 {
  font-size: 24px;
  text-align: center;
  margin-bottom: 16px;
}

h2 {
  font-size: 20px;
  text-align: center;
  color: #409eff;
}

h3 {
  font-size: 16px;
  margin: 16px 0 8px;
}

.tip {
  text-align: center;
  color: #666;
  font-size: 14px;
  margin-bottom: 20px;
}

.input-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.session-input, .serial-input {
  width: 100%;
  height: 48px;
  font-size: 18px;
  padding: 8px 12px;
  border: 2px solid #409eff;
  border-radius: 4px;
  box-sizing: border-box;
}

.join-btn, .scan-btn {
  height: 48px;
  font-size: 18px;
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.join-btn:disabled, .scan-btn:disabled {
  background: #ccc;
}

.session-info {
  text-align: center;
  margin-bottom: 16px;
}

.session-info p {
  color: #666;
  font-size: 14px;
}

.scan-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.scan-list {
  background: #f9f9f9;
  padding: 16px;
  border-radius: 4px;
  min-height: 100px;
}

.items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #eee;
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.serial {
  font-weight: bold;
  font-size: 16px;
}

.name {
  color: #666;
  font-size: 14px;
}

.qty {
  color: #409eff;
  font-size: 12px;
}

.remove-btn {
  width: 32px;
  height: 32px;
  background: #f56c6c;
  color: #fff;
  border: none;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
}

.empty-tip {
  text-align: center;
  color: #999;
}

.actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.exit-btn {
  height: 40px;
  padding: 0 24px;
  background: #f56c6c;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
}

.error {
  color: #f56c6c;
  text-align: center;
  margin-top: 12px;
}

.success {
  color: #67c23a;
  text-align: center;
  margin-top: 12px;
}
</style>