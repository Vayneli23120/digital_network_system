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
    <div class="grid2">
      <div class="panel">
        <div class="panel-hd">
          <span class="panel-title">{{ t('consoleSerialConnection') }}</span>
        </div>
        <div class="panel-body">
          <div class="form-grid">
            <div class="form-row">
              <label class="form-label">{{ t('consoleSerialDevice') }}</label>
              <div class="port-selector">
                <select class="fselect" v-model="selectedPort" :disabled="connected">
                  <option value="">{{ t('consoleSelectSerialPlaceholder') }}</option>
                  <option v-for="port in availablePorts" :key="port" :value="port">{{ port }}</option>
                </select>
                <button class="btn btn-primary" @click="requestPort" :disabled="connected">
                  <el-icon><Search /></el-icon>
                  {{ t('consoleSelectSerial') }}
                </button>
              </div>
            </div>

            <div class="form-row">
              <label class="form-label">{{ t('consoleBaudRate') }}</label>
              <select class="fselect" v-model="baudRate" :disabled="connected">
                <option :value="9600">9600 ({{ t('consoleBaudRateDefault') }})</option>
                <option :value="19200">19200</option>
                <option :value="38400">38400</option>
                <option :value="57600">57600</option>
                <option :value="115200">115200</option>
              </select>
            </div>

            <div class="form-row">
              <label class="form-label">{{ t('consoleDataBits') }}</label>
              <select class="fselect" v-model="dataBits" :disabled="connected">
                <option :value="8">8</option>
                <option :value="7">7</option>
              </select>
            </div>

            <div class="form-row">
              <label class="form-label">{{ t('consoleStopBits') }}</label>
              <select class="fselect" v-model="stopBits" :disabled="connected">
                <option :value="1">1</option>
                <option :value="2">2</option>
              </select>
            </div>

            <div class="form-row buttons">
              <button class="btn btn-success" @click="connectPort" :disabled="!selectedPort || connected">
                <el-icon><Connection /></el-icon>
                {{ t('consoleConnect') }}
              </button>
              <button class="btn btn-danger" @click="disconnectPort" :disabled="!connected">
                <el-icon><SwitchButton /></el-icon>
                {{ t('consoleDisconnect') }}
              </button>
            </div>
          </div>

          <!-- Web Serial Support Check -->
          <div class="serial-warning" v-if="!isSupported">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ t('consoleSerialNotSupported') }}</span>
          </div>
        </div>
      </div>

      <!-- Device & Config Selection -->
      <div class="panel">
        <div class="panel-hd">
          <span class="panel-title">{{ t('consoleConfigDeploy') }}</span>
        </div>
        <div class="panel-body">
          <div class="form-grid">
            <div class="form-row">
              <label class="form-label">{{ t('consoleTargetDevice') }}</label>
              <select class="fselect" v-model="selectedDevice">
                <option value="">{{ t('consoleSelectDevice') }}</option>
                <option v-for="device in devices" :key="device.id" :value="device.id">
                  {{ device.name }} ({{ device.ip || 'N/A' }})
                </option>
              </select>
            </div>

            <div class="form-row">
              <label class="form-label">{{ t('consoleConfigTemplate') }}</label>
              <select class="fselect" v-model="selectedTemplate">
                <option value="">{{ t('consoleSelectTemplate') }}</option>
                <option v-for="template in templates" :key="template.id" :value="template.id">
                  {{ template.name }}
                </option>
              </select>
            </div>

            <div class="form-row">
              <label class="form-label">{{ t('consoleConfigFile') }}</label>
              <select class="fselect" v-model="selectedBackup">
                <option value="">{{ t('consoleSelectBackup') }}</option>
                <option v-for="backup in backups" :key="backup.id" :value="backup.id">
                  {{ backup.device_name }} - {{ formatShortTime(backup.backup_time) }}
                </option>
              </select>
            </div>

            <div class="form-row buttons">
              <button class="btn btn-primary" @click="deployConfig" :disabled="!connected || isDeploying">
                <el-icon><Upload /></el-icon>
                {{ isDeploying ? t('consoleDeploying') : t('consoleStartDeploy') }}
              </button>
              <button class="btn btn-ghost" @click="loadConfigPreview" :disabled="!selectedBackup">
                <el-icon><View /></el-icon>
                {{ t('consolePreviewConfig') }}
              </button>
            </div>
          </div>
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

        <!-- Progress -->
        <div class="deploy-progress" v-if="isDeploying">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: deployProgress + '%' }"></div>
          </div>
          <span class="progress-text">{{ deployProgress }}% - {{ deployStep }}</span>
        </div>

        <!-- Manual Input -->
        <div class="terminal-input" v-if="connected && !isDeploying">
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

    <!-- Config Preview Modal -->
    <div class="modal-overlay" v-if="showPreviewModal" @click="showPreviewModal = false">
      <div class="modal modal-lg" @click.stop>
        <div class="modal-hd">
          <span class="modal-title">{{ t('consoleConfigPreview') }}</span>
          <button class="modal-close" @click="showPreviewModal = false">×</button>
        </div>
        <div class="modal-body">
          <pre class="config-preview">{{ configPreview }}</pre>
        </div>
        <div class="modal-ft">
          <button class="btn btn-ghost" @click="showPreviewModal = false">{{ t('actionClose') }}</button>
          <button class="btn btn-primary" @click="deployConfig; showPreviewModal = false" :disabled="!connected">
            {{ t('consoleDirectDeploy') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Connection, Search, Upload, View, Delete, Download,
  SwitchButton, WarningFilled
} from '@element-plus/icons-vue'
import { getDevices, getTemplates, getBackups, getBackupContent, getTemplate } from '@/api'
import { formatShortTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

// Web Serial API Support
const isSupported = ref('serial' in navigator)
const port = ref(null)
const reader = ref(null)
const writer = ref(null)
const connected = ref(false)
const selectedPort = ref('')
const availablePorts = ref([])

// Serial settings
const baudRate = ref(9600)
const dataBits = ref(8)
const stopBits = ref(1)

// Device & config selection
const devices = ref([])
const templates = ref([])
const backups = ref([])
const selectedDevice = ref('')
const selectedTemplate = ref('')
const selectedBackup = ref('')

// Terminal
const terminalRef = ref(null)
const commandInputRef = ref(null)
const terminalLines = ref([])
const manualCommand = ref('')

// Deploy state
const isDeploying = ref(false)
const deployProgress = ref(0)
const deployStep = ref('')

// Preview
const showPreviewModal = ref(false)
const configPreview = ref('')

// ReadableStream controller for async reading
let readLoopPromise = null
let abortController = null

// Add line to terminal
const addLine = (text, type = 'output') => {
  terminalLines.value.push({
    time: dayjs().format('HH:mm:ss'),
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

// Deploy configuration
const deployConfig = async () => {
  if (!connected.value) {
    ElMessage.warning(t('consoleConnectSerialFirst'))
    return
  }

  if (!selectedBackup.value && !selectedTemplate.value) {
    ElMessage.warning(t('consoleSelectConfigOrTemplate'))
    return
  }

  isDeploying.value = true
  deployProgress.value = 0
  deployStep.value = t('consolePrepareDeploy')

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

    const totalSteps = commands.length + 5 // +5 for enter/exit/save

    // Step 1: Wake up
    deployStep.value = t('consoleWakeDevice')
    deployProgress.value = 5
    await sendCommand('\r', 0.5)
    await sendCommand('\r', 0.5)

    // Step 2: Enter enable mode
    deployStep.value = t('consoleEnterEnableMode')
    deployProgress.value = 10
    await sendCommand('enable', 1)

    // Step 3: Enter config mode
    deployStep.value = t('consoleEnterConfigMode')
    deployProgress.value = 15
    await sendCommand('configure terminal', 1)

    // Step 4: Send config commands
    for (let i = 0; i < commands.length; i++) {
      deployStep.value = `${t('consoleExecuteCommand')} ${i + 1}/${commands.length}`
      deployProgress.value = 15 + Math.floor((i / commands.length) * 70)
      await sendCommand(commands[i], 0.3)
    }

    // Step 5: Exit config mode
    deployStep.value = t('consoleExitConfigMode')
    deployProgress.value = 90
    await sendCommand('end', 1)

    // Step 6: Save config
    deployStep.value = t('consoleSaveConfig')
    deployProgress.value = 95
    await sendCommand('write memory', 2)

    deployStep.value = t('consoleDeployComplete')
    deployProgress.value = 100
    addLine(t('consoleDeploySuccess'), 'success')
    ElMessage.success(t('consoleDeploySuccess'))

  } catch (err) {
    addLine(t('consoleDeployFailed') + ': ' + err.message, 'error')
    ElMessage.error(t('consoleDeployFailed') + ': ' + err.message)
  }

  isDeploying.value = false
}

// Load config preview
const loadConfigPreview = async () => {
  if (!selectedBackup.value) {
    ElMessage.warning(t('consoleSelectBackupFile'))
    return
  }

  try {
    const data = await getBackupContent(selectedBackup.value)
    configPreview.value = data.content || t('consoleGetConfigFailed')
    showPreviewModal.value = true
  } catch (err) {
    ElMessage.error(t('consoleLoadFailed') + ': ' + err.message)
  }
}

// Clear terminal
const clearTerminal = () => {
  terminalLines.value = []
}

// Download log
const downloadLog = () => {
  const log = terminalLines.value.map(l => `[${l.time}] ${l.text}`).join('\n')
  const blob = new Blob([log], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `console-log-${dayjs().format('YYYYMMDD-HHmmss')}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

// Load data
onMounted(async () => {
  try {
    const deviceData = await getDevices()
    devices.value = deviceData.items || []

    const templateData = await getTemplates()
    templates.value = templateData.items || templateData || []

    const backupData = await getBackups({ limit: 20 })
    backups.value = backupData.items || backupData.backups || []
  } catch (err) {
    console.error('Failed to load data:', err)
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

/* Deploy Progress */
.deploy-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  padding: 12px;
  background: var(--bg);
  border-radius: var(--radius-sm);
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-gb);
  transition: width 0.3s;
}

.progress-text {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--ink2);
  min-width: 120px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 31, 92, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.modal {
  background: var(--surface);
  border-radius: var(--radius-modal);
  max-width: 720px;
  width: 90%;
  box-shadow: var(--shadow-modal);
}

.modal-lg {
  max-width: 900px;
}

.modal-hd {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--ink);
}

.modal-close {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  border: none;
  border-radius: var(--radius-sm);
  font-size: 18px;
  color: var(--ink3);
  cursor: pointer;
}

.modal-close:hover {
  background: var(--color-gb-ghost);
}

.modal-body {
  padding: 20px 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.modal-ft {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 24px;
  border-top: 1px solid var(--border);
}

.config-preview {
  background: var(--bg);
  padding: 16px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--ink2);
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
}

/* Responsive */
@media (max-width: 768px) {
  .grid2 {
    grid-template-columns: 1fr;
  }

  .terminal {
    min-height: 200px;
  }
}
</style>