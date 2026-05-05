<template>
  <div class="scan-session-wrapper">
    <!-- 会话创建阶段 -->
    <div v-if="!sessionCode" class="create-session">
      <el-form :model="sessionForm" label-width="80px">
        <el-form-item label="操作类型">
          <el-radio-group v-model="sessionForm.session_type">
            <el-radio label="in">入库</el-radio>
            <el-radio label="out">出库</el-radio>
            <el-radio label="maintenance">维修备件</el-radio>
            <el-radio label="task">运维任务</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="sessionForm.session_type === 'maintenance'" label="维修工单">
          <el-input v-model="sessionForm.reference" placeholder="维修单号" />
        </el-form-item>
        <el-form-item v-if="sessionForm.session_type === 'task'" label="任务编号">
          <el-input v-model="sessionForm.reference" placeholder="任务编号" />
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="createSession" :loading="creating">
        创建扫码会话
      </el-button>
    </div>

    <!-- 扫码阶段 -->
    <div v-else class="scan-phase">
      <!-- 二维码显示 -->
      <div v-if="!joined" class="qr-section">
        <div class="qr-tip">
          <h3>扫码枪扫描下方二维码</h3>
          <p>扫描后即可开始扫描备件序列号</p>
        </div>
        <div class="qr-display">
          <div class="qr-code" :style="{ background: qrPattern }">
            <div class="qr-content">{{ qrContent }}</div>
            <div class="session-code">{{ sessionCode }}</div>
          </div>
        </div>
        <p class="session-info">
          会话码：<strong>{{ sessionCode }}</strong>
          <br>
          有效期：{{ expiresAt }}（30分钟）
        </p>
      </div>

      <!-- 扫码枪已加入 -->
      <div v-else class="scan-active">
        <div class="scan-header">
          <el-tag type="success" size="large">
            扫码枪已连接
          </el-tag>
          <span class="scan-type">
            {{ sessionTypeText }} - {{ sessionForm.session_type }}
          </span>
        </div>

        <!-- 扫描结果列表 -->
        <el-card class="scan-items-card">
          <template #header>
            <div class="items-header">
              <span>已扫描备件（{{ scanItems.length }} 项）</span>
              <el-button size="small" @click="refreshSession">
                <el-icon><Aim /></el-icon>
                刷新
              </el-button>
            </div>
          </template>

          <el-table v-if="scanItems.length > 0" :data="scanItems" stripe border>
            <el-table-column prop="serial_number" label="序列号" width="150" />
            <el-table-column prop="part_number" label="型号" width="120">
              <template #default="{ row }">{{ row.part_number || '未知' }}</template>
            </el-table-column>
            <el-table-column prop="name" label="名称" width="150">
              <template #default="{ row }">{{ row.name || '未找到' }}</template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="80">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.quantity"
                  :min="1"
                  size="small"
                  controls-position="right"
                  @change="updateItemQuantity(row)"
                />
              </template>
            </el-table-column>
            <el-table-column prop="unit_price" label="单价" width="80">
              <template #default="{ row }">
                {{ row.unit_price ? `¥${row.unit_price}` : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="found_in_stock" label="库存状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.part_id ? 'success' : 'warning'" size="small">
                  {{ row.part_id ? '已匹配' : '未找到' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60">
              <template #default="{ $index }">
                <el-button type="danger" size="small" link @click="removeItem($index)">
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else description="等待扫码枪扫描备件序列号..." />
        </el-card>

        <!-- 操作信息 -->
        <el-form :model="submitForm" label-width="80px" style="margin-top: 16px">
          <el-form-item label="操作人">
            <el-input v-model="submitForm.operator" />
          </el-form-item>
          <el-form-item label="原因/备注">
            <el-input v-model="submitForm.reason" type="textarea" />
          </el-form-item>
          <el-form-item v-if="sessionForm.session_type === 'maintenance'" label="参考工单">
            <el-input v-model="submitForm.reference" :value="sessionForm.reference" disabled />
          </el-form-item>
        </el-form>

        <!-- 提交按钮 -->
        <div class="submit-actions">
          <el-button @click="cancelSession">取消会话</el-button>
          <el-button
            type="primary"
            @click="submitSession"
            :disabled="scanItems.length === 0"
            :loading="submitting"
          >
            确认提交（{{ scanItems.length }} 项）
          </el-button>
        </div>
      </div>
    </div>

    <!-- 完成提示 -->
    <el-dialog v-model="showCompleteDialog" title="扫码完成" width="400px">
      <el-result icon="success" title="操作成功" :sub-title="completeMessage">
        <template #extra>
          <el-button type="primary" @click="resetSession">继续扫码</el-button>
          <el-button @click="showCompleteDialog = false">关闭</el-button>
        </template>
      </el-result>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim } from '@element-plus/icons-vue'
import {
  createScanSession,
  getScanSession,
  completeScanSession,
  deleteScanSession
} from '@/api'
import { formatDateTime } from '@/utils/time'

// Props
const props = defineProps({
  defaultType: {
    type: String,
    default: 'in' // in, out, maintenance, task
  },
  reference: String,
  onComplete: Function // 完成回调
})

// Emits
const emit = defineEmits(['complete', 'cancel'])

// 状态
const creating = ref(false)
const sessionCode = ref('')
const qrContent = ref('')
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

// 计算属性
const sessionTypeText = computed(() => {
  const texts = { in: '入库', out: '出库', maintenance: '维修备件', task: '运维任务' }
  return texts[sessionForm.value.session_type] || ''
})

// 生成简单的二维码图案（CSS模拟）
const qrPattern = computed(() => {
  if (!sessionCode.value) return '#fff'
  // 使用会话码生成伪随机图案
  const code = sessionCode.value
  let pattern = 'linear-gradient(45deg, '
  for (let i = 0; i < code.length; i++) {
    const c = code.charCodeAt(i)
    const x = (c % 8) * 12.5
    const y = ((c * 7) % 8) * 12.5
    pattern += `#333 ${x}% ${y}%, #fff ${x + 12.5}% ${y + 12.5}%, `
  }
  pattern += '#fff 100%)'
  return pattern
})

// 创建会话
const createSession = async () => {
  creating.value = true
  try {
    const result = await createScanSession({
      session_type: sessionForm.value.session_type,
      reference: sessionForm.value.reference
    })
    sessionCode.value = result.session_code
    qrContent.value = result.qr_content
    expiresAt.value = result.expires_at
    ElMessage.success('扫码会话已创建')

    // 开始轮询检查状态
    startPolling()
  } catch (e) {
    ElMessage.error('创建失败: ' + (e.response?.data?.detail || e.message))
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
      scanItems.value = result.items || []

      // 如果过期，停止轮询
      if (result.status === 'expired') {
        stopPolling()
        ElMessage.warning('会话已过期')
        sessionCode.value = ''
      }
    } catch (e) {
      if (e.response?.status === 404 || e.response?.status === 400) {
        stopPolling()
        sessionCode.value = ''
      }
    }
  }, 2000)
}

// 停止轮询
const stopPolling = () => {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

// 刷新会话
const refreshSession = async () => {
  if (!sessionCode.value) return
  try {
    const result = await getScanSession(sessionCode.value)
    scanItems.value = result.items || []
  } catch (e) {
    ElMessage.error('刷新失败')
  }
}

// 更新数量（本地）
const updateItemQuantity = (row) => {
  // 数量在本地更新，提交时一起发送
}

// 移除项
const removeItem = (index) => {
  scanItems.value.splice(index, 1)
}

// 提交会话
const submitSession = async () => {
  if (scanItems.value.length === 0) return

  submitting.value = true
  try {
    const result = await completeScanSession(sessionCode.value)
    stopPolling()

    // 触发完成回调
    emit('complete', {
      session_type: sessionForm.value.session_type,
      items: scanItems.value,
      operator: submitForm.value.operator,
      reason: submitForm.value.reason,
      reference: submitForm.value.reference
    })

    if (props.onComplete) {
      props.onComplete(scanItems.value)
    }

    completeMessage.value = `成功处理 ${scanItems.value.length} 个备件`
    showCompleteDialog.value = true
  } catch (e) {
    ElMessage.error('提交失败: ' + (e.response?.data?.detail || e.message))
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

.qr-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.qr-tip {
  text-align: center;
  margin-bottom: 20px;
}

.qr-tip h3 {
  font-size: 18px;
  margin-bottom: 8px;
}

.qr-tip p {
  color: var(--el-text-color-secondary);
}

.qr-display {
  margin: 20px 0;
}

.qr-code {
  width: 200px;
  height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 2px solid var(--el-border-color);
  border-radius: 8px;
  background-size: 100% 100%;
}

.qr-content {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 4px 8px;
  background: rgba(255,255,255,0.9);
  border-radius: 4px;
}

.session-code {
  font-size: 28px;
  font-weight: bold;
  letter-spacing: 4px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.95);
  border-radius: 4px;
  margin-top: 8px;
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