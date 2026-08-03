<template>
  <div class="execution-panel" :class="{ active: status !== 'idle' }">
    <!-- 执行进度概览 -->
    <div class="execution-overview">
      <div class="overview-header">
        <div class="overview-title">
          <el-icon v-if="status === 'running'" class="is-loading"><Loading /></el-icon>
          <span>{{ t('deployExecutionTitle') }}</span>
        </div>
        <div class="overview-actions">
          <div v-if="elapsedTime > 0" class="elapsed-time">
            {{ t('deployElapsedTime') }}: {{ formatDuration(elapsedTime) }}
          </div>
          <el-button
            v-if="status === 'completed' && hasRollbackAvailable"
            type="warning"
            size="small"
            @click="emit('rollback')"
          >
            <el-icon><RefreshLeft /></el-icon>
            {{ t('deployRollback') }}
          </el-button>
        </div>
      </div>

      <div class="progress-overview">
        <div class="progress-item">
          <div class="progress-label">{{ t('deployTotalDevices') }}</div>
          <div class="progress-value">{{ totalDevices }}</div>
        </div>
        <div class="progress-item success">
          <div class="progress-label">{{ t('deployCompleted') }}</div>
          <div class="progress-value">{{ completedDevices }}</div>
        </div>
        <div class="progress-item warning">
          <div class="progress-label">{{ t('deployInProgress') }}</div>
          <div class="progress-value">{{ inProgressDevices }}</div>
        </div>
        <div class="progress-item error">
          <div class="progress-label">{{ t('deployFailed') }}</div>
          <div class="progress-value">{{ failedDevices }}</div>
        </div>
      </div>

      <el-progress
        :percentage="progressPercentage"
        :status="progressStatus"
        :stroke-width="12"
        class="overall-progress"
      />
    </div>

    <!-- 设备执行状态 -->
    <div class="devices-section">
      <div class="section-header">
        <span class="section-title">{{ t('deployDeviceExecution') }}</span>
      </div>
      <div class="device-cards">
        <div
          v-for="device in deviceExecutions"
          :key="device.device_id"
          class="device-card"
          :class="{
            active: selectedDevice?.device_id === device.device_id,
            success: device.status === 'completed',
            error: device.status === 'failed',
            skipped: device.status === 'skipped',
            running: device.status === 'running'
          }"
          @click="emit('select-device', device)"
        >
          <div class="device-card-header">
            <div class="device-info">
              <el-icon
                v-if="device.status === 'completed'"
                class="status-icon success"
              >
                <CircleCheckFilled />
              </el-icon>
              <el-icon
                v-else-if="device.status === 'failed'"
                class="status-icon error"
              >
                <CircleCloseFilled />
              </el-icon>
              <el-icon
                v-else-if="device.status === 'skipped'"
                class="status-icon skipped"
              >
                <Minus />
              </el-icon>
              <el-icon
                v-else-if="device.status === 'running'"
                class="status-icon running is-loading"
              >
                <Loading />
              </el-icon>
              <el-icon v-else class="status-icon pending">
                <Timer />
              </el-icon>
              <div class="device-text">
                <div class="device-name">{{ device.device_name }}</div>
                <div class="device-ip">{{ device.device_ip }}</div>
              </div>
            </div>
            <el-tag
              :type="getDeviceStatusType(device.status)"
              size="small"
              effect="dark"
            >
              {{ getDeviceStatusText(device.status) }}
            </el-tag>
          </div>
          <el-progress
            :percentage="device.progress"
            :status="getDeviceProgressStatus(device.status)"
            :stroke-width="4"
            class="device-progress"
          />
          <div v-if="device.message" class="device-message">
            {{ device.message }}
          </div>
        </div>
      </div>
    </div>

    <!-- CLI 区域：并排显示命令输出和部署历史 -->
    <div class="cli-section-parallel">
      <!-- 左侧：CLI 命令输出（部署结果） -->
      <div class="cli-panel">
        <div class="cli-panel-header">
          <span class="cli-panel-title">
            {{ t('deployCliOutput') }}
            <span v-if="selectedDevice" class="device-badge">{{ selectedDevice.device_name }}</span>
          </span>
          <el-tag v-if="status === 'running'" type="warning" size="small">
            <el-icon class="is-loading"><Loading /></el-icon>
            {{ t('deployExecuting') }}
          </el-tag>
          <el-tag v-else-if="status === 'completed'" type="success" size="small">
            {{ t('deployCompleted') }}
          </el-tag>
          <button class="nav-action-btn secondary small" @click="emit('clear-cli')">
            <el-icon><Delete /></el-icon>
            {{ t('actionClear') }}
          </button>
        </div>
        <div ref="cliOutputRef" class="cli-panel-output">
          <div
            v-for="(line, index) in selectedDevice?.cliLogs || []"
            :key="index"
            class="cli-line"
            :class="line.type"
          >
            <span class="cli-timestamp">{{ formatTime(line.timestamp) }}</span>
            <span class="cli-content">{{ line.content }}</span>
          </div>
          <div v-if="!selectedDevice || selectedDevice.cliLogs.length === 0" class="cli-empty">
            {{ t('deployCliEmpty') }}
          </div>
        </div>
      </div>

      <!-- 右侧：部署历史记录（由父通过 #history 插槽注入） -->
      <slot name="history"></slot>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import {
  Loading,
  RefreshLeft,
  CircleCheckFilled,
  CircleCloseFilled,
  Minus,
  Timer,
  Delete
} from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import {
  getDeviceStatusType,
  getDeviceProgressStatus,
  formatDuration,
  formatTime
} from '@/utils/deploy.js'

const props = defineProps({
  status: { type: String, default: 'idle' },
  elapsedTime: { type: Number, default: 0 },
  deviceExecutions: { type: Array, default: () => [] },
  selectedDevice: { type: Object, default: null },
  totalDevices: { type: Number, default: 0 },
  completedDevices: { type: Number, default: 0 },
  inProgressDevices: { type: Number, default: 0 },
  failedDevices: { type: Number, default: 0 },
  progressPercentage: { type: Number, default: 0 },
  progressStatus: { type: String, default: '' },
  hasRollbackAvailable: { type: Boolean, default: false },
  registerCliOutput: { type: Function, default: () => {} }
})

const emit = defineEmits(['select-device', 'clear-cli', 'rollback'])

const { t } = useI18n()

// 设备状态文本
const getDeviceStatusText = (status) => {
  const texts = {
    pending: t('deployDevicePending'),
    running: t('deployDeviceRunning'),
    completed: t('deployDeviceCompleted'),
    failed: t('deployDeviceFailed'),
    skipped: t('deployDeviceSkipped')
  }
  return texts[status] || status
}

// CLI 输出容器：将 DOM 句柄交给父 composable（scrollToBottom 用）
const cliOutputRef = ref(null)
onMounted(() => {
  props.registerCliOutput(cliOutputRef.value)
})
onBeforeUnmount(() => {
  props.registerCliOutput(null)
})
</script>

<style scoped>
/* ========================================
   按钮系统 - 现代、轻量、主次分明
   ======================================== */

.nav-action-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: none;
  background: var(--bg-card);
  color: var(--text-secondary);
}

.nav-action-btn .el-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

/* 小按钮 */
.nav-action-btn.small {
  height: 22px;
  padding: 0 8px;
  font-size: 11px;
}

/* 主按钮 - deploy */
.nav-action-btn.deploy-btn {
  background: var(--accent-primary);
  color: white;
  border: none;
}

.nav-action-btn.deploy-btn:hover:not(.disabled) {
  background: #00a884;
  box-shadow: 0 2px 6px rgba(0, 184, 148, 0.2);
  transform: translateY(-1px);
}

.nav-action-btn.deploy-btn.disabled {
  background: rgba(0, 184, 148, 0.4);
  cursor: not-allowed;
}

/* 次按钮 */
.nav-action-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

/* 危险按钮 */
.nav-action-btn.danger {
  background: var(--accent-danger);
  color: white;
  border: none;
}

.nav-action-btn.danger:hover {
  background: #c42a2a;
  box-shadow: 0 2px 6px rgba(214, 48, 49, 0.2);
  transform: translateY(-1px);
}

/* 预览按钮 */
.nav-action-btn.preview-btn {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.preview-btn:hover:not(.disabled) {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
}

.nav-action-btn.preview-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ========================================
   执行面板 - 浅色卡片风格
   ======================================== */

.execution-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--gap-lg);
  height: 100%;
  overflow-y: auto;
  box-shadow: var(--shadow-card);
}

.execution-panel.active {
  border-color: var(--accent-secondary);
}

/* 执行面板分隔线 - 浅色风格 */
.execution-panel :deep(.el-divider) {
  border-color: var(--border-subtle);
}

/* ========================================
   执行概览 - 浅色风格 Pipeline Summary
   ======================================== */

.execution-overview {
  margin-bottom: var(--gap-md);
  padding: 16px;
  background: transparent;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: var(--gap-sm);
}

.overview-title {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.overview-title .is-loading {
  display: inline-flex;
  align-items: center;
}

.elapsed-time {
  font-size: 12px;
  color: var(--text-secondary);
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
}

.overview-actions {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
}

/* ========================================
   进度统计 - 浅色卡片风格
   ======================================== */

.progress-overview {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  padding: 12px 0;
}

.progress-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 6px;
  background: var(--bg-hover);
  font-size: 13px;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
}

.progress-item.success {
  background: var(--success-bg);
  border-color: rgba(0, 184, 148, 0.3);
}

.progress-item.warning {
  background: var(--warn-bg);
  border-color: rgba(210, 153, 34, 0.3);
}

.progress-item.error {
  background: var(--error-bg);
  border-color: rgba(214, 48, 49, 0.3);
}

.progress-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.progress-value {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
}

.progress-item.success .progress-value {
  color: var(--accent-primary);
}

.progress-item.warning .progress-value {
  color: var(--accent-warning);
}

.progress-item.error .progress-value {
  color: var(--accent-danger);
}

.overall-progress {
  margin-top: var(--gap-sm);
}

/* 进度条 - 浅色背景 */
.overall-progress :deep(.el-progress-bar__outer) {
  height: 4px !important;
  border-radius: 2px;
  background: var(--bg-hover) !important;
}

.overall-progress :deep(.el-progress-bar__inner) {
  border-radius: 2px;
  transition: width 0.3s ease;
  background: var(--accent-primary) !important;
}

/* Progress shimmer 动画 */
@keyframes progress-shimmer {
  0% { background-position: -200% center; }
  100% { background-position: 200% center; }
}

.execution-panel.active .overall-progress :deep(.el-progress-bar__inner) {
  background: linear-gradient(
    90deg,
    var(--accent-primary) 0%,
    #2ecc71 25%,
    var(--accent-primary) 50%,
    #2ecc71 75%,
    var(--accent-primary) 100%
  ) !important;
  background-size: 200% 100%;
  animation: progress-shimmer 2s linear infinite;
}

/* ========================================
   设备区域 - 浅色企业风格
   ======================================== */

.devices-section {
  margin-bottom: var(--gap-lg);
  background: transparent;
}

.section-header {
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
  margin-bottom: 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.device-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--gap-md);
}

/* 设备卡片 - 浅色卡片风格 */
.device-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.device-card:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  transform: translateY(-1px);
}

.device-card.active {
  border-color: var(--accent-primary);
  background: var(--bg-hover);
}

/* 状态边框 */
.device-card.success {
  border-color: rgba(0, 184, 148, 0.3);
}

.device-card.error {
  border-color: rgba(214, 48, 49, 0.3);
}

.device-card.skipped {
  border-color: rgba(139, 148, 158, 0.3);
}

.device-card.running {
  border-color: var(--accent-secondary);
}

.device-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--gap-sm);
}

.device-info {
  display: flex;
  align-items: flex-start;
  gap: var(--gap-sm);
}

.status-icon {
  font-size: 16px;
  margin-top: 2px;
}

.status-icon.success { color: var(--accent-primary); }
.status-icon.error { color: var(--accent-danger); }
.status-icon.running { color: var(--accent-secondary); }
.status-icon.pending { color: var(--text-muted); }
.status-icon.skipped { color: var(--text-secondary); }

.device-text {
  display: flex;
  flex-direction: column;
}

.device-name {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 13px;
}

.device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

.device-progress {
  margin-top: var(--gap-sm);
}

/* 设备进度条 - 浅色风格 */
.device-progress :deep(.el-progress-bar__outer) {
  height: 3px !important;
  background: var(--bg-hover) !important;
}

.device-progress :deep(.el-progress-bar__inner) {
  background: var(--accent-secondary) !important;
}

.device-message {
  margin-top: var(--gap-sm);
  font-size: 12px;
  color: var(--text-secondary);
}

/* ========================================
   CLI 并排布局 - 企业级 SSH Console
   ======================================== */

.cli-section-parallel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--gap-lg);
  margin-top: var(--gap-lg);
}

/* CLI Panel - 保持深色 Terminal 风格 */
.cli-panel {
  background: #1e1e1e;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 340px;
}

.cli-panel.active {
  border-color: var(--accent-secondary);
}

.cli-panel.realtime {
  border-color: var(--accent-secondary);
}

/* CLI Header - VSCode Terminal 风格 */
.cli-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
  height: 36px;
  flex-shrink: 0;
  font-size: 12px;
  color: #cccccc;
}

.cli-panel.realtime .cli-panel-header {
  background: rgba(9, 132, 227, 0.1);
  border-bottom-color: rgba(9, 132, 227, 0.3);
}

.cli-panel-title {
  font-size: 12px;
  font-weight: 500;
  color: #cccccc;
}

.cli-panel-header .el-tag {
  display: inline-flex !important;
  align-items: center;
  gap: var(--gap-xs);
  height: 22px;
  padding: 0 8px;
}

.cli-panel-header .el-tag :deep(.el-icon) {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

.cli-panel-header .el-tag .is-loading {
  display: inline-flex;
  align-items: center;
}

/* Device Badge - VSCode Terminal 风格 */
.device-badge {
  margin-left: var(--gap-sm);
  padding: 2px 6px;
  background: rgba(9, 132, 227, 0.15);
  border-radius: 4px;
  font-size: 11px;
  color: #569cd6;
}

/* ========================================
   CLI 输出区域 - VSCode Terminal 风格（始终深色）
   ======================================== */

.cli-panel-output {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: 'JetBrains Mono', 'Geist Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 16px;
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
  position: relative;
}

.cli-panel-output::-webkit-scrollbar {
  width: 4px;
}

.cli-panel-output::-webkit-scrollbar-track {
  background: transparent;
}

.cli-panel-output::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

.cli-panel-output::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* CLI 滚动指示 */
.cli-panel-output.autoscroll::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 40px;
  background: linear-gradient(transparent, rgba(30, 30, 30, 0.8));
  pointer-events: none;
}

.cli-empty {
  color: #858585;
  text-align: center;
  padding: var(--gap-lg);
}

.cli-line {
  display: flex;
  gap: 8px;
  padding: 1px 0;
}

.cli-timestamp {
  color: #6a9955;
  font-size: 10px;
  opacity: 0.8;
  flex-shrink: 0;
}

.cli-command {
  color: #4ec9b0;
  font-weight: 500;
}

.cli-content {
  color: #d4d4d4;
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}

/* ANSI 风格高亮 - VSCode Terminal */
.cli-line.command .cli-content {
  color: #4ec9b0;
  font-weight: 500;
}

.cli-line.error .cli-content,
.cli-error-text {
  color: #f14c4c;
}

.cli-line.warning .cli-content {
  color: #cca700;
}

.cli-line.success .cli-content {
  color: #89d185;
}

.cli-line.diff .cli-content {
  color: #ce9178;
}

.cli-line.info .cli-content {
  color: #569cd6;
}

.cli-step {
  color: #569cd6;
  display: inline-flex;
  align-items: center;
  gap: var(--gap-xs);
}

.cli-diff-inline {
  color: #ce9178;
  white-space: pre-wrap;
  font-size: 11px;
  margin: var(--gap-xs) 0;
  padding: var(--gap-xs) 10px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: var(--radius-sm);
  max-width: 100%;
  overflow-x: auto;
}

/* 光标闪烁动画 */
@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.cli-cursor {
  display: inline-block;
  width: 8px;
  height: 14px;
  background: #4ec9b0;
  animation: cursor-blink 1s step-end infinite;
}

/* ========================================
   动画
   ======================================== */

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ========================================
   全页面微交互增强
   ======================================== */

/* 1. Fade slide in animation */
@keyframes fade-slide-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.device-card {
  animation: fade-slide-in 0.2s ease;
}

/* 2. Terminal cursor blink */
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.cli-panel-output.running::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 30px;
  background: linear-gradient(transparent, rgba(30, 30, 30, 0.8));
  pointer-events: none;
  z-index: 1;
}
</style>
