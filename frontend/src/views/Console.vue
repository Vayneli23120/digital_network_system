<template>
  <div class="console-page" :class="{ dark: isDark }">
    <!-- Page Navigation Bar -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('consoleTitle') }}</h1>
        <div class="connection-badge" :class="connected ? 'connected' : 'disconnected'">
          <span class="badge-dot"></span>
          <span>{{ connected ? t('consoleConnected') : t('consoleDisconnected') }}</span>
        </div>
      </div>
      <div class="nav-right">
        <router-link to="/deploy" class="console-btn secondary">
          <el-icon><Upload /></el-icon>
          {{ t('consoleGoToDeploy') }}
        </router-link>
      </div>
    </section>

    <!-- Console Workspace: Left Sidebar + Right Terminal -->
    <section class="console-workspace">
      <!-- Left: Configuration Sidebar -->
      <aside class="config-sidebar">

        <!-- Session Status Card -->
        <div class="session-card" :class="connected ? 'connected' : 'disconnected'">
          <div class="session-header">
            <div class="session-icon">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="session-title-group">
              <span class="session-title">Console Session</span>
              <div class="session-status">
                <span class="status-dot" :class="connected ? 'active' : 'idle'"></span>
                <span class="status-text">{{ connected ? t('consoleConnected') : t('consoleDisconnected') }}</span>
              </div>
            </div>
          </div>

          <div class="session-body">
            <div class="param-row">
              <span class="param-label">Port</span>
              <span class="param-value">{{ selectedPort || '--' }}</span>
            </div>
            <div class="param-row">
              <span class="param-label">Baud Rate</span>
              <span class="param-value">{{ baudRate }}</span>
            </div>
            <div class="param-row">
              <span class="param-label">Config</span>
              <span class="param-value">{{ dataBits }}N{{ stopBits }}</span>
            </div>
            <div class="param-row">
              <span class="param-label">Parity</span>
              <span class="param-value">None</span>
            </div>
          </div>

          <div class="session-actions">
            <button class="session-btn success" :disabled="connected" @click="connectPort">
              <el-icon><Connection /></el-icon>
              {{ t('consoleConnect') }}
            </button>
            <button class="session-btn danger" :disabled="!connected" @click="disconnectPort">
              <el-icon><SwitchButton /></el-icon>
              {{ t('consoleDisconnect') }}
            </button>
          </div>
        </div>

        <!-- Serial Configuration Panel -->
        <div class="config-panel">
          <div class="panel-header">
            <span class="panel-title">Serial Configuration</span>
          </div>
          <div class="panel-body">
            <div class="config-grid">
              <div class="config-item">
                <label class="config-label">Baud Rate</label>
                <select class="config-select" v-model="baudRate" :disabled="connected">
                  <option :value="9600">9600</option>
                  <option :value="19200">19200</option>
                  <option :value="38400">38400</option>
                  <option :value="57600">57600</option>
                  <option :value="115200">115200</option>
                </select>
              </div>
              <div class="config-item">
                <label class="config-label">Data Bits</label>
                <select class="config-select" v-model="dataBits" :disabled="connected">
                  <option :value="8">8</option>
                  <option :value="7">7</option>
                </select>
              </div>
              <div class="config-item">
                <label class="config-label">Stop Bits</label>
                <select class="config-select" v-model="stopBits" :disabled="connected">
                  <option :value="1">1</option>
                  <option :value="2">2</option>
                </select>
              </div>
            </div>

            <!-- Web Serial Support Warning -->
            <div class="serial-warning" v-if="!isSupported">
              <el-icon><WarningFilled /></el-icon>
              <span>{{ t('consoleSerialNotSupported') }}</span>
            </div>

            <!-- Port Selection -->
            <div class="port-selector" v-if="isSupported && !connected">
              <button class="select-port-btn" @click="requestPort">
                <el-icon><Search /></el-icon>
                {{ t('consoleSelectSerial') }}
              </button>
              <span class="port-tip">{{ t('consoleSelectSerialTip') }}</span>
            </div>
          </div>
        </div>

        <!-- Config Push Panel -->
        <div class="push-panel">
          <div class="panel-header">
            <span class="panel-title">Configuration Push</span>
            <el-tag v-if="!connected" type="warning" size="small" effect="plain">
              {{ t('consoleConnectRequired') }}
            </el-tag>
          </div>
          <div class="panel-body">
            <div class="push-grid">
              <div class="push-item">
                <label class="push-label">{{ t('consoleConfigTemplate') }}</label>
                <select class="push-select" v-model="selectedTemplate" :disabled="!connected">
                  <option value="">{{ t('consoleSelectTemplate') }}</option>
                  <option v-for="template in templates" :key="template.id" :value="template.id">
                    {{ template.name }}
                  </option>
                </select>
              </div>
              <div class="push-item">
                <label class="push-label">{{ t('consoleConfigFile') }}</label>
                <select class="push-select" v-model="selectedBackup" :disabled="!connected">
                  <option value="">{{ t('consoleSelectBackup') }}</option>
                  <option v-for="backup in backups" :key="backup.id" :value="backup.id">
                    {{ backup.device_name }} - {{ formatTime(backup.backup_time) }}
                  </option>
                </select>
              </div>
            </div>

            <div class="push-action">
              <button class="push-btn primary" :disabled="isPushing || (!selectedTemplate && !selectedBackup)" @click="pushConfigViaSerial">
                <el-icon v-if="isPushing" class="is-loading"><Loading /></el-icon>
                <el-icon v-else><Upload /></el-icon>
                {{ isPushing ? t('consolePushing') : t('consolePushConfig') }}
              </button>
            </div>

            <!-- Push Progress -->
            <div class="push-progress" v-if="isPushing">
              <div class="progress-track">
                <div class="progress-fill" :style="{ width: pushProgress + '%' }"></div>
              </div>
              <span class="progress-label">{{ pushStep }}</span>
            </div>
          </div>
        </div>

        <!-- Info Tip (Compact) -->
        <div class="info-tip-compact">
          <el-icon><InfoFilled /></el-icon>
          <span>{{ t('consoleSshDeployTip') }}</span>
        </div>

      </aside>

      <!-- Right: Terminal Workspace (Visual Core) -->
      <main class="terminal-workspace">
        <div class="terminal-header">
          <div class="terminal-title">
            <span class="terminal-indicator" :class="connected ? 'active' : 'idle'"></span>
            <span>{{ t('consoleTerminalOutput') }}</span>
          </div>
          <div class="terminal-actions">
            <button class="terminal-btn" @click="clearTerminal">
              <el-icon><Delete /></el-icon>
              {{ t('consoleClear') }}
            </button>
            <button class="terminal-btn" @click="downloadLog">
              <el-icon><Download /></el-icon>
              {{ t('consoleDownloadLog') }}
            </button>
          </div>
        </div>

        <div class="terminal-output" ref="terminalRef">
          <div class="cli-line" v-for="(line, idx) in terminalLines" :key="idx" :class="line.type">
            <span class="cli-timestamp">{{ line.time }}</span>
            <span class="cli-content">{{ line.text }}</span>
          </div>
          <!-- Cursor Blink -->
          <div class="cli-cursor-container" v-if="connected && terminalLines.length > 0">
            <span class="cli-cursor"></span>
          </div>
          <div class="cli-empty" v-if="terminalLines.length === 0">
            <el-icon><Monitor /></el-icon>
            <span>{{ t('consoleTerminalEmpty') }}</span>
          </div>
        </div>

        <!-- Manual Command Input -->
        <div class="terminal-input-area" v-if="connected">
          <span class="input-prompt">&gt;</span>
          <input
            class="command-input"
            v-model="manualCommand"
            @keyup.enter="sendManualCommand"
            :placeholder="t('consoleCommandPlaceholder')"
            ref="commandInputRef"
          />
          <button class="send-btn" @click="sendManualCommand">
            <el-icon><Promotion /></el-icon>
          </button>
        </div>
      </main>

      <!-- Right: Session History Panel -->
      <aside class="history-sidebar">
        <div class="history-panel">
          <div class="history-header">
            <span class="history-title">{{ t('consoleSessionHistory') }}</span>
            <button class="clear-history-btn" @click="clearSessionHistory" :disabled="sessionHistory.length === 0">
              <el-icon><Delete /></el-icon>
            </button>
          </div>
          <div class="history-list" v-if="sessionHistory.length > 0">
            <div
              class="history-item"
              v-for="session in sessionHistory"
              :key="session.id"
              :class="session.status"
              @click="viewSessionLog(session)"
            >
              <div class="history-item-header">
                <span class="history-item-status" :class="session.status">
                  {{ session.status === 'completed' ? t('consoleSessionCompleted') : session.status === 'failed' ? t('consoleSessionFailed') : t('consoleSessionAborted') }}
                </span>
                <span class="history-item-time">{{ session.endTime ? formatTime(session.endTime) : '--' }}</span>
              </div>
              <div class="history-item-body">
                <div class="history-param">
                  <span class="param-key">Port:</span>
                  <span class="param-val">{{ session.port || '--' }}</span>
                </div>
                <div class="history-param">
                  <span class="param-key">Baud:</span>
                  <span class="param-val">{{ session.baudRate }}</span>
                </div>
                <div class="history-param" v-if="session.pushSource">
                  <span class="param-key">{{ t('consolePushSource') }}:</span>
                  <span class="param-val">{{ session.pushSource }}</span>
                </div>
                <div class="history-param" v-if="session.commandCount">
                  <span class="param-key">{{ t('consoleCommandCount') }}:</span>
                  <span class="param-val">{{ session.commandCount }}</span>
                </div>
              </div>
              <div class="history-item-footer">
                <span class="history-duration">{{ session.duration ? formatDuration(session.duration) : '--' }}</span>
              </div>
            </div>
          </div>
          <div class="history-empty" v-else>
            <el-icon><Clock /></el-icon>
            <span>{{ t('consoleNoSessionHistory') }}</span>
          </div>
        </div>
      </aside>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Search, Delete, Download, SwitchButton, WarningFilled, InfoFilled, Upload, Promotion, Loading, Monitor, Clock } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { getTemplates, getBackups, getBackupContent, getTemplate } from '@/api'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

// 暗黑模式检测
const isDark = computed(() => document.documentElement.classList.contains('dark'))

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

// Session History (localStorage persisted)
const sessionHistory = ref([])
const currentSession = ref(null)

// Load session history from localStorage
const loadSessionHistory = () => {
  try {
    const saved = localStorage.getItem('consoleSessionHistory')
    if (saved) {
      sessionHistory.value = JSON.parse(saved)
    }
  } catch (e) {
    console.error('Failed to load session history:', e)
  }
}

// Save session history to localStorage
const saveSessionHistory = () => {
  try {
    localStorage.setItem('consoleSessionHistory', JSON.stringify(sessionHistory.value.slice(0, 50))) // Keep last 50
  } catch (e) {
    console.error('Failed to save session history:', e)
  }
}

// Start a new session
const startSession = () => {
  currentSession.value = {
    id: Date.now(),
    startTime: new Date().toISOString(),
    port: selectedPort.value,
    baudRate: baudRate.value,
    dataBits: dataBits.value,
    stopBits: stopBits.value,
    status: 'active',
    pushSource: null,
    commandCount: 0,
    endTime: null,
    duration: null,
    logs: []
  }
}

// End current session
const endSession = (status = 'completed') => {
  if (currentSession.value) {
    currentSession.value.endTime = new Date().toISOString()
    currentSession.value.status = status
    currentSession.value.duration = Math.round((new Date(currentSession.value.endTime) - new Date(currentSession.value.startTime)) / 1000)
    sessionHistory.value.unshift(currentSession.value)
    saveSessionHistory()
    currentSession.value = null
  }
}

// Clear session history
const clearSessionHistory = () => {
  sessionHistory.value = []
  localStorage.removeItem('consoleSessionHistory')
}

// View session log
const viewSessionLog = (session) => {
  if (session.logs && session.logs.length > 0) {
    terminalLines.value = session.logs.map(log => ({
      time: log.time,
      text: log.text,
      type: log.type
    }))
  }
}

// Format duration
const formatDuration = (seconds) => {
  if (seconds < 60) {
    return `${seconds}s`
  }
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
}

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
    selectedPort.value = `Serial (VID:${info.usbVendorId || 'N/A'} PID:${info.usbProductId || 'N/A'})`
    port.value = newPort
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

    // Start session record
    startSession()

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

    // End session record
    endSession('completed')
  } catch (err) {
    ElMessage.error(t('consoleDisconnectFailed') + ': ' + err.message)
    endSession('failed')
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

    addLine(command, 'command')

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
  let pushSourceName = ''

  try {
    // Get config content
    if (selectedBackup.value) {
      const data = await getBackupContent(selectedBackup.value)
      configContent = data.content || ''
      // Find backup name
      const backup = backups.value.find(b => b.id === selectedBackup.value)
      pushSourceName = backup ? `${backup.device_name} Backup` : 'Backup'
    } else if (selectedTemplate.value) {
      const data = await getTemplate(selectedTemplate.value)
      configContent = data.template_content || ''
      // Find template name
      const template = templates.value.find(t => t.id === selectedTemplate.value)
      pushSourceName = template ? template.name : 'Template'
    }

    if (!configContent) {
      throw new Error(t('consoleGetConfigFailed'))
    }

    // Parse commands (skip comments and empty lines)
    const commands = configContent.split('\n')
      .map(line => line.trim())
      .filter(line => line && !line.startsWith('!') && !line.startsWith('#'))

    // Record push info to current session
    if (currentSession.value) {
      currentSession.value.pushSource = pushSourceName
      currentSession.value.commandCount = commands.length
    }

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
    if (currentSession.value) {
      currentSession.value.status = 'failed'
    }
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
  // Load session history
  loadSessionHistory()

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
/* ========================================
   Console Page - Enterprise NetDevOps Style
   ======================================== */

.console-page {
  max-width: 1600px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  min-height: calc(100vh - 120px);
}

/* ========================================
   Page Navigation Bar
   ======================================== */

.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.connection-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.connection-badge.connected {
  background: var(--success-bg);
  color: var(--accent-primary);
}

.connection-badge.disconnected {
  background: var(--bg-hover);
  color: var(--text-tertiary);
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.connection-badge.connected .badge-dot {
  background: var(--accent-primary);
  animation: badge-pulse 2s infinite;
}

@keyframes badge-pulse {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(0, 184, 148, 0.4);
  }
  50% {
    opacity: 0.8;
    box-shadow: 0 0 0 4px rgba(0, 184, 148, 0);
  }
}

.nav-right {
  display: flex;
  gap: var(--gap-sm);
}

/* ========================================
   Console Workspace - Left + Middle + Right Layout
   ======================================== */

.console-workspace {
  display: grid;
  grid-template-columns: 280px 1fr 240px;
  gap: var(--gap-md);
  flex: 1;
  min-height: 400px;
}

/* ========================================
   Right: Session History Sidebar
   ======================================== */

.history-sidebar {
  display: flex;
  flex-direction: column;
}

.history-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.history-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.clear-history-btn {
  height: 22px;
  width: 22px;
  padding: 0;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
  transition: all 0.15s ease;
}

.clear-history-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--accent-danger);
  color: var(--accent-danger);
}

.clear-history-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.clear-history-btn .el-icon {
  width: 12px;
  height: 12px;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-default) transparent;
}

.history-list::-webkit-scrollbar {
  width: 4px;
}

.history-list::-webkit-scrollbar-track {
  background: transparent;
}

.history-list::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 2px;
}

.history-item {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.history-item:hover {
  background: var(--bg-tertiary);
  border-color: var(--accent-secondary);
  transform: translateY(-1px);
}

.history-item.completed {
  border-color: rgba(0, 184, 148, 0.2);
}

.history-item.failed {
  border-color: rgba(214, 48, 49, 0.2);
}

.history-item.aborted {
  border-color: rgba(225, 112, 85, 0.2);
}

.history-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.history-item-status {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.history-item-status.completed {
  background: var(--success-bg);
  color: var(--accent-primary);
}

.history-item-status.failed {
  background: var(--error-bg);
  color: var(--accent-danger);
}

.history-item-status.aborted {
  background: var(--warn-bg);
  color: var(--accent-warning);
}

.history-item-time {
  font-size: 10px;
  color: var(--text-tertiary);
  font-family: 'Geist Mono', monospace;
}

.history-item-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.history-param {
  display: flex;
  gap: 4px;
  font-size: 11px;
}

.param-key {
  color: var(--text-tertiary);
}

.param-val {
  color: var(--text-secondary);
  font-family: 'Geist Mono', monospace;
}

.history-item-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
  border-top: 1px solid var(--border-subtle);
  margin-top: 4px;
}

.history-duration {
  font-size: 10px;
  color: var(--text-tertiary);
  font-family: 'Geist Mono', monospace;
}

.history-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--gap-sm);
  color: var(--text-tertiary);
  font-size: 12px;
  padding: 20px;
}

.history-empty .el-icon {
  width: 24px;
  height: 24px;
  opacity: 0.5;
}

/* ========================================
   Left Sidebar - Configuration
   ======================================== */

.config-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: var(--border-default) transparent;
}

.config-sidebar::-webkit-scrollbar {
  width: 4px;
}

.config-sidebar::-webkit-scrollbar-track {
  background: transparent;
}

.config-sidebar::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 2px;
}

/* ========================================
   Session Card - Console Session Panel
   ======================================== */

.session-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: all 0.2s ease;
}

.session-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-elevated);
}

.session-card.connected {
  border-color: rgba(0, 184, 148, 0.3);
  box-shadow: var(--shadow-card), 0 0 10px rgba(0, 184, 148, 0.1);
}

.session-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.session-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(9, 132, 227, 0.1);
  border-radius: var(--radius-md);
  color: var(--accent-secondary);
}

.session-icon .el-icon {
  width: 14px;
  height: 14px;
}

.session-title-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.session-status {
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.status-dot.active {
  background: var(--accent-primary);
  animation: status-pulse 2s infinite;
}

.status-dot.idle {
  background: var(--text-tertiary);
}

@keyframes status-pulse {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(0, 184, 148, 0.5);
  }
  50% {
    opacity: 0.6;
    box-shadow: 0 0 0 3px rgba(0, 184, 148, 0);
  }
}

.status-text {
  font-size: 11px;
  color: var(--text-tertiary);
}

.session-card.connected .status-text {
  color: var(--accent-primary);
}

.session-body {
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.param-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.param-value {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
}

.session-actions {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  border-top: 1px solid var(--border-subtle);
}

.session-btn {
  flex: 1;
  height: 24px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.session-btn .el-icon {
  width: 12px;
  height: 12px;
}

.session-btn.success {
  background: var(--accent-primary);
  color: white;
}

.session-btn.success:hover:not(:disabled) {
  background: #00a884;
  box-shadow: 0 0 6px rgba(0, 184, 148, 0.3);
}

.session-btn.danger {
  background: var(--accent-danger);
  color: white;
}

.session-btn.danger:hover:not(:disabled) {
  background: #c42a2a;
  box-shadow: 0 0 6px rgba(214, 48, 49, 0.3);
}

.session-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ========================================
   Config Panel - Serial Configuration
   ======================================== */

.config-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: all 0.2s ease;
}

.config-panel:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-elevated);
}

.config-panel .panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.config-panel .panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.config-panel .panel-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-label {
  font-size: 10px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.config-select {
  height: 28px;
  padding: 0 8px;
  font-size: 12px;
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  color: var(--text-primary);
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
}

.config-select:hover:not(:disabled) {
  border-color: var(--accent-secondary);
}

.config-select:focus {
  border-color: var(--accent-secondary);
  outline: none;
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

.config-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Serial Warning */
.serial-warning {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: var(--warn-bg);
  color: var(--accent-warning);
  border-radius: var(--radius-md);
  font-size: 11px;
  border: 1px solid rgba(225, 112, 85, 0.2);
}

.serial-warning .el-icon {
  width: 12px;
  height: 12px;
}

/* Port Selector */
.port-selector {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px;
  background: rgba(9, 132, 227, 0.05);
  border-radius: var(--radius-md);
}

.select-port-btn {
  width: 100%;
  height: 28px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  background: var(--accent-secondary);
  color: white;
  border: none;
  transition: all 0.15s ease;
}

.select-port-btn:hover {
  background: #0873d1;
  box-shadow: 0 0 6px rgba(9, 132, 227, 0.3);
}

.select-port-btn .el-icon {
  width: 12px;
  height: 12px;
}

.port-tip {
  font-size: 11px;
  color: var(--text-tertiary);
  text-align: center;
}

/* ========================================
   Push Panel - Configuration Push
   ======================================== */

.push-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  transition: all 0.2s ease;
}

.push-panel:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-elevated);
}

.push-panel .panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
}

.push-panel .panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
}

.push-panel .panel-header .el-tag {
  height: 18px;
  padding: 0 6px;
  font-size: 10px;
}

.push-panel .panel-body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.push-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.push-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.push-label {
  font-size: 11px;
  color: var(--text-tertiary);
}

.push-select {
  height: 28px;
  padding: 0 8px;
  font-size: 12px;
  color: var(--text-primary);
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.15s ease;
}

.push-select:hover:not(:disabled) {
  border-color: var(--accent-secondary);
}

.push-select:focus {
  border-color: var(--accent-secondary);
  outline: none;
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

.push-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.push-action {
  padding-top: 4px;
}

.push-btn {
  width: 100%;
  height: 28px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.push-btn.primary {
  background: var(--accent-primary);
  color: white;
  border: none;
}

.push-btn.primary:hover:not(:disabled) {
  background: #00a884;
  box-shadow: 0 0 6px rgba(0, 184, 148, 0.3);
}

.push-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.push-btn .el-icon {
  width: 12px;
  height: 12px;
}

.push-btn .is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Push Progress */
.push-progress {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 8px;
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}

.progress-track {
  flex: 1;
  height: 4px;
  background: var(--border-default);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent-primary);
  transition: width 0.3s ease;
}

.progress-label {
  font-size: 11px;
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  color: var(--text-secondary);
  min-width: 100px;
}

/* ========================================
   Info Tip (Compact)
   ======================================== */

.info-tip-compact {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  background: rgba(9, 132, 227, 0.05);
  border: 1px solid rgba(9, 132, 227, 0.1);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 11px;
}

.info-tip-compact .el-icon {
  width: 12px;
  height: 12px;
  color: var(--accent-secondary);
}

/* ========================================
   Right: Terminal Workspace - Light Mode Default
   ======================================== */

.terminal-workspace {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

/* ========================================
   Terminal Header - Light Mode
   ======================================== */

.terminal-header {
  background: var(--bg-hover);
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 36px;
}

.terminal-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.terminal-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-tertiary);
}

.terminal-indicator.active {
  background: var(--accent-primary);
  animation: terminal-pulse 2s infinite;
}

.terminal-indicator.idle {
  background: var(--text-tertiary);
}

@keyframes terminal-pulse {
  0%, 100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(0, 184, 148, 0.6);
  }
  50% {
    opacity: 0.7;
    box-shadow: 0 0 0 4px rgba(0, 184, 148, 0);
  }
}

.terminal-actions {
  display: flex;
  gap: 6px;
}

.terminal-btn {
  height: 22px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  transition: all 0.15s ease;
}

.terminal-btn:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.terminal-btn .el-icon {
  width: 12px;
  height: 12px;
}

/* ========================================
   Terminal Output - Light Mode
   ======================================== */

.terminal-output {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-family: 'JetBrains Mono', 'Geist Mono', 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 12px 16px;
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
  scrollbar-width: thin;
  scrollbar-color: var(--border-default) transparent;
}

.terminal-output::-webkit-scrollbar {
  width: 6px;
}

.terminal-output::-webkit-scrollbar-track {
  background: transparent;
}

.terminal-output::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 3px;
}

.terminal-output::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}

/* CLI Line */
.cli-line {
  display: flex;
  gap: 10px;
  padding: 1px 0;
}

.cli-timestamp {
  color: var(--text-tertiary);
  font-size: 10px;
  flex-shrink: 0;
}

.cli-content {
  color: var(--text-primary);
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}

/* Light Mode - ANSI Style Colors */
.cli-line.command .cli-content {
  color: var(--accent-secondary);
  font-weight: 500;
}

.cli-line.success .cli-content {
  color: var(--accent-primary);
}

.cli-line.error .cli-content {
  color: var(--accent-danger);
}

.cli-line.warning .cli-content {
  color: var(--accent-warning);
}

.cli-line.info .cli-content {
  color: var(--accent-secondary);
}

.cli-line.output .cli-content {
  color: var(--text-secondary);
}

/* Cursor Container */
.cli-cursor-container {
  display: flex;
  padding: 2px 0;
}

.cli-cursor {
  display: inline-block;
  width: 10px;
  height: 16px;
  background: var(--accent-secondary);
  animation: cursor-blink 1s step-end infinite;
  margin-left: 10px;
}

@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* Empty State */
.cli-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--gap-sm);
  height: 100%;
  color: var(--text-tertiary);
  font-size: 12px;
}

.cli-empty .el-icon {
  width: 24px;
  height: 24px;
  opacity: 0.5;
}

/* ========================================
   Terminal Input Area - Light Mode
   ======================================== */

.terminal-input-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-hover);
  border-top: 1px solid var(--border-subtle);
}

.input-prompt {
  color: var(--accent-secondary);
  font-family: 'JetBrains Mono', 'Geist Mono', monospace;
  font-size: 12px;
  font-weight: 500;
}

.command-input {
  flex: 1;
  height: 26px;
  padding: 0 10px;
  font-family: 'JetBrains Mono', 'Geist Mono', monospace;
  font-size: 12px;
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  transition: all 0.15s ease;
}

.command-input:focus {
  border-color: var(--accent-secondary);
  outline: none;
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

.command-input::placeholder {
  color: var(--text-tertiary);
}

.send-btn {
  height: 26px;
  width: 26px;
  padding: 0;
  border-radius: var(--radius-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: var(--accent-secondary);
  color: white;
  border: none;
  transition: all 0.15s ease;
}

.send-btn:hover {
  background: #0873d1;
  box-shadow: 0 0 6px rgba(9, 132, 227, 0.3);
}

.send-btn .el-icon {
  width: 12px;
  height: 12px;
}

/* ========================================
   Console Button System
   ======================================== */

.console-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.console-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.console-btn.secondary:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.console-btn .el-icon {
  width: 12px;
  height: 12px;
}

/* ========================================
   DARK MODE - Terminal Deep Style
   ======================================== */

.console-page.dark .terminal-workspace {
  background: #1e1e1e;
  border-color: #3c3c3c;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4), 0 0 1px rgba(86, 156, 214, 0.1);
}

.console-page.dark .terminal-header {
  background: #252526;
  border-color: #3c3c3c;
}

.console-page.dark .terminal-title {
  color: #cccccc;
}

.console-page.dark .terminal-indicator.idle {
  background: #636e72;
}

.console-page.dark .terminal-btn {
  border-color: #3c3c3c;
  color: #cccccc;
}

.console-page.dark .terminal-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: #569cd6;
  color: #569cd6;
}

.console-page.dark .terminal-output {
  background: #1e1e1e;
  color: #d4d4d4;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

.console-page.dark .terminal-output::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
}

.console-page.dark .terminal-output::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

.console-page.dark .cli-timestamp {
  color: #6a9955;
  opacity: 0.8;
}

.console-page.dark .cli-content {
  color: #d4d4d4;
}

/* Dark Mode - ANSI Colors */
.console-page.dark .cli-line.command .cli-content {
  color: #4ec9b0;
}

.console-page.dark .cli-line.success .cli-content {
  color: #89d185;
}

.console-page.dark .cli-line.error .cli-content {
  color: #f14c4c;
}

.console-page.dark .cli-line.warning .cli-content {
  color: #cca700;
}

.console-page.dark .cli-line.info .cli-content {
  color: #569cd6;
}

.console-page.dark .cli-line.output .cli-content {
  color: #d4d4d4;
}

.console-page.dark .cli-cursor {
  background: #4ec9b0;
}

.console-page.dark .cli-empty {
  color: #858585;
}

.console-page.dark .terminal-input-area {
  background: #252526;
  border-color: #3c3c3c;
}

.console-page.dark .input-prompt {
  color: #4ec9b0;
}

.console-page.dark .command-input {
  background: #1e1e1e;
  border-color: #3c3c3c;
  color: #d4d4d4;
}

.console-page.dark .command-input:focus {
  border-color: #569cd6;
  box-shadow: 0 0 0 2px rgba(86, 156, 214, 0.2);
}

.console-page.dark .command-input::placeholder {
  color: #858585;
}

/* ========================================
   Responsive
   ======================================== */

@media (max-width: 1400px) {
  .console-workspace {
    grid-template-columns: 280px 1fr;
  }

  .history-sidebar {
    display: none;
  }
}

@media (max-width: 900px) {
  .console-workspace {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .config-sidebar {
    max-height: none;
    overflow: visible;
  }

  .terminal-output {
    min-height: 200px;
  }
}

@media (max-width: 600px) {
  .page-nav-bar {
    flex-direction: column;
    gap: var(--gap-sm);
    align-items: flex-start;
  }

  .nav-left {
    flex-direction: column;
    align-items: flex-start;
  }

  .config-grid {
    grid-template-columns: 1fr;
  }

  .push-grid {
    grid-template-columns: 1fr;
  }
}
</style>