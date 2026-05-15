<template>
  <div class="console-page">
    <!-- Page Header -->
    <div class="page-header">
      <div class="page-title">
        <h1>{{ t('consoleTitle') }}</h1>
        <span class="page-subtitle">{{ t('consoleSubtitle') }}</span>
      </div>
      <div class="btn-row">
        <div class="connection-status" :class="connected ? 'connected' : 'disconnected'">
          <el-icon><Connection /></el-icon>
          <span>{{ connected ? t('consoleConnected') : t('consoleDisconnected') }}</span>
        </div>
      </div>
    </div>

    <!-- Connection Panel -->
    <div class="panel">
      <div class="panel-hd">
        <span class="panel-title">{{ t('consoleSerialConnection') }}</span>
      </div>
      <div class="panel-body">
        <div class="form-grid">
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="form-row">
                <label class="form-label">{{ t('consoleBaudRate') }}</label>
                <select class="fselect" v-model="baudRate" :disabled="connected">
                  <option :value="9600">9600</option>
                  <option :value="19200">19200</option>
                  <option :value="38400">38400</option>
                  <option :value="57600">57600</option>
                  <option :value="115200">115200</option>
                </select>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="form-row">
                <label class="form-label">{{ t('consoleDataBits') }}</label>
                <select class="fselect" v-model="dataBits" :disabled="connected">
                  <option :value="8">8</option>
                  <option :value="7">7</option>
                </select>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="form-row">
                <label class="form-label">{{ t('consoleStopBits') }}</label>
                <select class="fselect" v-model="stopBits" :disabled="connected">
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                </select>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="form-row buttons-inline">
                <button class="btn btn-success" @click="connectPort" :disabled="connected">
                  <el-icon><Connection /></el-icon>
                  {{ t('consoleConnect') }}
                </button>
                <button class="btn btn-danger" @click="disconnectPort" :disabled="!connected">
                  <el-icon><SwitchButton /></el-icon>
                  {{ t('consoleDisconnect') }}
                </button>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- Web Serial Support Check -->
        <div class="serial-warning" v-if="!isSupported">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ t('consoleSerialNotSupported') }}</span>
        </div>

        <!-- Serial Port Selection -->
        <div class="port-selection-area" v-if="isSupported && !connected">
          <button class="btn btn-primary btn-lg" @click="requestPort">
            <el-icon><Search /></el-icon>
            {{ t('consoleSelectSerial') }}
          </button>
          <span class="port-tip">{{ t('consoleSelectSerialTip') }}</span>
        </div>
      </div>
    </div>

    <!-- Tips for SSH Deploy -->
    <div class="info-tip-card">
      <el-icon><InfoFilled /></el-icon>
      <span>{{ t('consoleSshDeployTip') }}</span>
      <router-link to="/deploy" class="tip-link">{{ t('consoleGoToDeploy') }}</router-link>
    </div>

    <!-- Serial Config Push Panel -->
    <div class="panel config-push-panel">
      <div class="panel-hd">
        <span class="panel-title">{{ t('consoleSerialPushTitle') }}</span>
        <el-tag v-if="!connected" type="warning" size="small">{{ t('consoleConnectRequired') }}</el-tag>
      </div>
      <div class="panel-body">
        <el-row :gutter="16">
          <el-col :span="8">
            <div class="form-row">
              <label class="form-label">{{ t('consoleConfigTemplate') }}</label>
              <select class="fselect" v-model="selectedTemplate" :disabled="!connected">
                <option value="">{{ t('consoleSelectTemplate') }}</option>
                <option v-for="template in templates" :key="template.id" :value="template.id">
                  {{ template.name }}
                </option>
              </select>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="form-row">
              <label class="form-label">{{ t('consoleConfigFile') }}</label>
              <select class="fselect" v-model="selectedBackup" :disabled="!connected">
                <option value="">{{ t('consoleSelectBackup') }}</option>
                <option v-for="backup in backups" :key="backup.id" :value="backup.id">
                  {{ backup.device_name }} - {{ formatTime(backup.backup_time) }}
                </option>
              </select>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="form-row buttons-inline">
              <button class="btn btn-primary" @click="pushConfigViaSerial" :disabled="isPushing || (!selectedTemplate && !selectedBackup)">
                <el-icon><Upload /></el-icon>
                {{ isPushing ? t('consolePushing') : t('consolePushConfig') }}
              </button>
            </div>
          </el-col>
        </el-row>

        <!-- Push Progress -->
        <div class="push-progress" v-if="isPushing">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: pushProgress + '%' }"></div>
          </div>
          <span class="progress-text">{{ pushProgress }}% - {{ pushStep }}</span>
        </div>
      </div>
    </div>

    <!-- Console Terminal -->
    <div class="panel terminal-panel">
      <div class="panel-hd">
        <span class="panel-title">{{ t('consoleTerminalOutput') }}</span>
        <div class="terminal-actions">
          <button class="btn btn-tiny btn-ghost" @click="clearTerminal">
            <el-icon><Delete /></el-icon>
            {{ t('consoleClear') }}
          </button>
          <button class="btn btn-tiny btn-ghost" @click="downloadLog">
            <el-icon><Download /></el-icon>
            {{ t('consoleDownloadLog') }}
          </button>
        </div>
      </div>
      <div class="panel-body">
        <div class="terminal" ref="terminalRef">
          <div class="terminal-line" v-for="(line, idx) in terminalLines" :key="idx" :class="line.type">
            <span class="terminal-time">{{ line.time }}</span>
            <span class="terminal-text">{{ line.text }}</span>
          </div>
          <div class="terminal-empty" v-if="terminalLines.length === 0">
            {{ t('consoleTerminalEmpty') }}
          </div>
        </div>

        <!-- Manual Input -->
        <div class="terminal-input" v-if="connected">
          <input
            class="command-input"
            v-model="manualCommand"
            @keyup.enter="sendManualCommand"
            :placeholder="t('consoleCommandPlaceholder')"
            ref="commandInputRef"
          />
          <button class="btn btn-tiny btn-primary" @click="sendManualCommand">
            {{ t('consoleSend') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Search, Delete, Download, SwitchButton, WarningFilled, InfoFilled, Upload } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { getTemplates, getBackups, getBackupContent, getTemplate } from '@/api'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

// Web Serial API Support
const isSupported = ref('serial' in navigator)
const port = ref(null)
const reader = ref(null)
const writer = ref(null)
const connected = ref(false)

// Serial settings
const baudRate = ref(9600)
const dataBits = ref(8)
const stopBits = ref(1)

// Terminal
const terminalRef = ref(null)
const commandInputRef = ref(null)
const terminalLines = ref([])
const manualCommand = ref('')
const selectedPort = ref('')

// Config push
const templates = ref([])
const backups = ref([])
const selectedTemplate = ref('')
const selectedBackup = ref('')
const isPushing = ref(false)
const pushProgress = ref(0)
const pushStep = ref('')

// ReadableStream controller for async reading
let readLoopPromise = null
let abortController = null

// Format time
const formatTime = (datetimeStr) => {
  if (!datetimeStr) return ''
  try {
    return new Date(datetimeStr).toLocaleString('zh-CN', { hour12: false, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return datetimeStr }
}

// Add line to terminal
const addLine = (text, type = 'output') => {
  terminalLines.value.push({
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    text,
    type
  })
  nextTick(() => {
    if (terminalRef.value) {
      terminalRef.value.scrollTop = terminalRef.value.scrollHeight
    }
  })
}

// Request port from user (Web Serial API requires user gesture)
const requestPort = async () => {
  if (!isSupported.value) {
    ElMessage.error(t('consoleBrowserNotSupported'))
    return
  }

  try {
    const newPort = await navigator.serial.requestPort()
    const info = await newPort.getInfo()
    selectedPort.value = `Serial Port (USB VID:${info.usbVendorId || 'N/A'} PID:${info.usbProductId || 'N/A'})`
    port.value = newPort
    availablePorts.value = [selectedPort.value]
    addLine(t('consoleSerialSelected'), 'info')
  } catch (err) {
    if (err.name === 'NotFoundError') {
      ElMessage.warning(t('consoleSerialNotFound'))
    } else {
      ElMessage.error(t('consoleSelectSerialFailed') + ': ' + err.message)
    }
  }
}

// Connect to port
const connectPort = async () => {
  if (!port.value) {
    ElMessage.warning(t('consoleSelectSerialFirst'))
    return
  }

  try {
    await port.value.open({
      baudRate: baudRate.value,
      dataBits: dataBits.value,
      stopBits: stopBits.value,
    })

    connected.value = true
    addLine(`${t('consoleConnect')}: ${baudRate.value} baud, ${dataBits.value}N${stopBits.value}`, 'success')

    // Start reading loop
    startReadLoop()

    // Send a few enters to wake up the device
    await sendCommand('\r', 0.3)
    await sendCommand('\r', 0.5)

    ElMessage.success(t('consoleConnectSuccess'))

  } catch (err) {
    ElMessage.error(t('consoleConnectFailed') + ': ' + err.message)
    addLine(t('consoleConnectFailed') + ': ' + err.message, 'error')
  }
}

// Disconnect from port
const disconnectPort = async () => {
  try {
    if (reader.value) {
      await reader.value.cancel()
      reader.value = null
    }
    if (writer.value) {
      writer.value.releaseLock()
      writer.value = null
    }
    if (port.value) {
      await port.value.close()
    }
    connected.value = false
    addLine(t('consoleDisconnectSuccess'), 'warning')
    ElMessage.info(t('consoleDisconnectSuccess'))
  } catch (err) {
    ElMessage.error(t('consoleDisconnectFailed') + ': ' + err.message)
  }
}

// Start reading loop (async)
const startReadLoop = () => {
  if (!port.value) return

  abortController = new AbortController()
  readLoopPromise = (async () => {
    try {
      reader.value = port.value.readable.getReader()
      const decoder = new TextDecoderStream()
      const input = reader.value.readThrough(decoder)

      while (!abortController.signal.aborted) {
        const { value, done } = await reader.value.read()
        if (done) break
        if (value) {
          // Process incoming data (terminal output from device)
          value.split('\n').forEach(line => {
            if (line.trim()) {
              addLine(line.trim(), 'output')
            }
          })
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        addLine(t('consoleReadError') + ': ' + err.message, 'error')
      }
    }
  })()
}

// Send command to device
const sendCommand = async (command, delay = 0.5) => {
  if (!connected.value || !port.value) {
    ElMessage.warning(t('consoleConnectSerialFirst'))
    return
  }

  try {
    writer.value = port.value.writable.getWriter()
    const encoder = new TextEncoderStream()
    const output = encoder.readable.pipeTo(port.value.writable)

    await writer.value.write(command + '\r\n')
    writer.value.releaseLock()
    writer.value = null

    addLine(command, 'input')

    await new Promise(r => setTimeout(r, delay * 1000))
  } catch (err) {
    addLine(t('consoleSendFailed') + ': ' + err.message, 'error')
  }
}

// Send manual command
const sendManualCommand = async () => {
  if (!manualCommand.value.trim()) return
  await sendCommand(manualCommand.value.trim(), 0.3)
  manualCommand.value = ''
}

// Clear terminal
const clearTerminal = () => {
  terminalLines.value = []
}

// Push config via serial
const pushConfigViaSerial = async () => {
  if (!connected.value) {
    ElMessage.warning(t('consoleConnectSerialFirst'))
    return
  }

  if (!selectedTemplate.value && !selectedBackup.value) {
    ElMessage.warning(t('consoleSelectConfigOrTemplate'))
    return
  }

  isPushing.value = true
  pushProgress.value = 0
  pushStep.value = t('consolePreparePush')

  let configContent = ''

  try {
    // Get config content
    if (selectedBackup.value) {
      const data = await getBackupContent(selectedBackup.value)
      configContent = data.content || ''
    } else if (selectedTemplate.value) {
      const data = await getTemplate(selectedTemplate.value)
      configContent = data.template_content || ''
    }

    if (!configContent) {
      throw new Error(t('consoleGetConfigFailed'))
    }

    // Parse commands (skip comments and empty lines)
    const commands = configContent.split('\n')
      .map(line => line.trim())
      .filter(line => line && !line.startsWith('!') && !line.startsWith('#'))

    addLine(t('consolePushStart') + ` (${commands.length} ${t('consoleCommands')})`, 'info')

    // Step 1: Wake up
    pushStep.value = t('consoleWakeDevice')
    pushProgress.value = 5
    await sendCommand('\r', 0.5)
    await sendCommand('\r', 0.5)

    // Step 2: Enter enable mode
    pushStep.value = t('consoleEnterEnableMode')
    pushProgress.value = 10
    await sendCommand('enable', 1)

    // Step 3: Enter config mode
    pushStep.value = t('consoleEnterConfigMode')
    pushProgress.value = 15
    await sendCommand('configure terminal', 1)

    // Step 4: Send config commands
    for (let i = 0; i < commands.length; i++) {
      pushStep.value = `${t('consoleExecuteCommand')} ${i + 1}/${commands.length}`
      pushProgress.value = 15 + Math.floor((i / commands.length) * 70)
      await sendCommand(commands[i], 0.3)
    }

    // Step 5: Exit config mode
    pushStep.value = t('consoleExitConfigMode')
    pushProgress.value = 90
    await sendCommand('end', 1)

    // Step 6: Save config
    pushStep.value = t('consoleSaveConfig')
    pushProgress.value = 95
    await sendCommand('write memory', 2)

    pushStep.value = t('consolePushComplete')
    pushProgress.value = 100
    addLine(t('consolePushSuccess'), 'success')
    ElMessage.success(t('consolePushSuccess'))

  } catch (err) {
    addLine(t('consolePushFailed') + ': ' + err.message, 'error')
    ElMessage.error(t('consolePushFailed') + ': ' + err.message)
  }

  isPushing.value = false
}

// Download log
const downloadLog = () => {
  const log = terminalLines.value.map(l => `[${l.time}] ${l.text}`).join('\n')
  const blob = new Blob([log], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `console-log-${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// Load templates and backups on mount
onMounted(async () => {
  try {
    const templateData = await cachedRequest(
      () => getTemplates(),
      'templates',
      {},
      { forceRefresh: false }
    )
    templates.value = templateData.items || templateData || []

    const backupData = await cachedRequest(
      () => getBackups({ limit: 50 }),
      'backups',
      { limit: 50 },
      { forceRefresh: false }
    )
    backups.value = backupData.items || backupData.backups || []
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load templates/backups:', err)
    }
  }
})

// Cleanup on unmount
onUnmounted(async () => {
  if (connected.value) {
    await disconnectPort()
  }
})
</script>

<style scoped>
.console-page {
  max-width: 1200px;
}

/* Page Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--gap-lg);
}

.page-title h1 {
  font-size: 20px;
  font-weight: 500;
  color: var(--ink);
  margin: 0;
}

.page-subtitle {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--ink3);
}

.btn-row {
  display: flex;
  gap: var(--gap-sm);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  font-weight: 500;
}

.connection-status.connected {
  background: var(--success-bg);
  color: var(--success);
}

.connection-status.disconnected {
  background: var(--bg);
  color: var(--ink3);
}

/* Grid */
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--gap-md);
  margin-bottom: var(--gap-lg);
}

/* Panel */
.panel {
  background: var(--surface);
  border-radius: var(--radius-panel);
  border: 1px solid var(--border);
}

.panel-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}

.panel-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--ink);
}

.panel-body {
  padding: 18px 20px;
}

/* Form Grid */
.form-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-row.buttons {
  margin-top: 8px;
}

.form-label {
  min-width: 80px;
  font-size: 12px;
  font-weight: 500;
  color: var(--ink2);
}

.port-selector {
  display: flex;
  gap: 8px;
  flex: 1;
}

.fselect {
  flex: 1;
  padding: 8px 12px;
  font-size: 13px;
  font-family: var(--font-body);
  color: var(--ink);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.fselect:focus {
  border-color: var(--color-gb);
  outline: none;
}

.fselect:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 400;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.btn .el-icon {
  font-size: 14px;
}

.btn-primary {
  background: var(--color-gb);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-gb-mid);
}

.btn-success {
  background: var(--success);
  color: #fff;
}

.btn-success:hover:not(:disabled) {
  background: #15703b;
}

.btn-danger {
  background: var(--danger);
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #991b1b;
}

.btn-ghost {
  background: var(--surface);
  color: var(--ink2);
  border-color: var(--border);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--color-gb-ghost);
  border-color: var(--border2);
}

.btn-tiny {
  padding: 4px 8px;
  font-size: 11px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Serial Warning */
.serial-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  padding: 10px 12px;
  background: var(--warn-bg);
  color: var(--warn);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

/* Terminal Panel */
.terminal-panel {
  margin-bottom: var(--gap-lg);
}

.terminal-actions {
  display: flex;
  gap: 8px;
}

.terminal {
  background: #0d1117;
  color: #c9d1d9;
  border-radius: var(--radius-lg);
  padding: 16px;
  min-height: 300px;
  max-height: 400px;
  overflow-y: auto;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.4;
}

.terminal-line {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
}

.terminal-time {
  color: #6e7681;
  font-size: 11px;
}

.terminal-text {
  flex: 1;
  white-space: pre-wrap;
  word-break: break-all;
}

.terminal-line.input .terminal-text {
  color: #58a6ff;
}

.terminal-line.success .terminal-text {
  color: #3fb950;
}

.terminal-line.error .terminal-text {
  color: #f85149;
}

.terminal-line.warning .terminal-text {
  color: #d29922;
}

.terminal-line.info .terminal-text {
  color: #8b949e;
}

.terminal-empty {
  color: #6e7681;
  text-align: center;
  padding: 100px 0;
}

/* Terminal Input */
.terminal-input {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.command-input {
  flex: 1;
  padding: 8px 12px;
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--ink);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.command-input:focus {
  border-color: var(--color-gb);
  outline: none;
}

/* Buttons Inline */
.buttons-inline {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* Port Selection Area */
.port-selection-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  background: rgba(0, 48, 135, 0.04);
  border-radius: var(--radius-md);
  margin-top: 14px;
}

.btn-lg {
  padding: 12px 24px;
  font-size: 14px;
}

.port-tip {
  font-size: 12px;
  color: var(--ink3);
}

/* Info Tip Card */
.info-tip-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(9, 132, 227, 0.08);
  border: 1px solid rgba(9, 132, 227, 0.2);
  border-radius: var(--radius-sm);
  margin-bottom: var(--gap-md);
  color: var(--ink2);
  font-size: 13px;
}

.info-tip-card .el-icon {
  color: var(--color-gb-mid);
}

.tip-link {
  color: var(--color-gb-mid);
  font-weight: 500;
  margin-left: 8px;
}

.tip-link:hover {
  color: var(--color-gb);
}

/* Config Push Panel */
.config-push-panel {
  margin-bottom: var(--gap-md);
}

.push-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 12px;
  background: var(--bg);
  border-radius: var(--radius-sm);
}

.push-progress .progress-bar {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.push-progress .progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-gb), var(--color-gb-mid));
  transition: width 0.3s;
}

.push-progress .progress-text {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--ink2);
  min-width: 120px;
}

/* Responsive */
@media (max-width: 768px) {
  .terminal {
    min-height: 200px;
  }
}
</style>