<template>
  <div class="console-page">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card v-loading="loading">
          <template #header>
            <span>Console 连接配置</span>
          </template>

          <el-form :model="consoleForm" label-width="120px">
            <el-form-item label="COM 端口">
              <el-select v-model="consoleForm.port" placeholder="选择 COM 端口" style="width: 100%">
                <el-option
                  v-for="port in availablePorts"
                  :key="port.device"
                  :label="`${port.device} - ${port.description}`"
                  :value="port.device"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="波特率">
              <el-select v-model="consoleForm.baudrate">
                <el-option label="9600" :value="9600" />
                <el-option label="19200" :value="19200" />
                <el-option label="38400" :value="38400" />
                <el-option label="115200" :value="115200" />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="detectPort">
                <el-icon><Search /></el-icon>
                自动检测端口
              </el-button>
              <el-button @click="refreshPorts">刷新端口列表</el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <el-form label-width="120px">
            <el-form-item label="目标设备">
              <el-select v-model="selectedDevice" placeholder="选择设备" style="width: 100%">
                <el-option
                  v-for="device in devices"
                  :key="device.id"
                  :label="`${device.name} (${device.ip})`"
                  :value="device.id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="配置文件">
              <el-select v-model="selectedConfig" placeholder="选择配置文件" style="width: 100%">
                <el-option
                  v-for="backup in recentBackups"
                  :key="backup.id"
                  :label="backup.backup_file"
                  :value="backup.backup_file"
                />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button type="success" @click="startDeploy" :disabled="!canDeploy">
                <el-icon><Connection /></el-icon>
                开始部署配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card v-loading="loading">
          <template #header>
            <span>部署进度</span>
          </template>

          <div class="console-output" ref="consoleOutput">
            <div v-if="deployLog.length === 0" class="empty">
              等待部署...
            </div>
            <div v-for="(line, index) in deployLog" :key="index" class="log-line">
              <span class="time">{{ formatTime(line.time) }}</span>
              <span :class="['message', line.type]">{{ line.message }}</span>
            </div>
          </div>

          <div class="progress-section" v-if="isDeploying">
            <el-progress :percentage="deployProgress" :status="deployStatus" />
          </div>

          <div class="actions" style="margin-top: 20px">
            <el-button type="danger" @click="stopDeploy" :disabled="!isDeploying">停止</el-button>
            <el-button @click="clearLog">清空日志</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getConsolePorts, autoDetectConsole, getDevices, getBackups } from '@/api'
import dayjs from 'dayjs'

const availablePorts = ref([])
const devices = ref([])
const loading = ref(false)
const recentBackups = ref([])

const consoleForm = ref({
  port: '',
  baudrate: 9600
})

const selectedDevice = ref(null)
const selectedConfig = ref(null)

const deployLog = ref([])
const isDeploying = ref(false)
const deployProgress = ref(0)
const deployStatus = ref('')

const canDeploy = computed(() => {
  return consoleForm.value.port && selectedDevice.value && selectedConfig.value && !isDeploying.value
})

const detectPort = async () => {
  try {
    const data = await autoDetectConsole()
    if (data.found) {
      consoleForm.value.port = data.port
      ElMessage.success(`找到 Console 设备：${data.port}`)
    } else {
      ElMessage.warning('未找到 Console 设备，请检查 USB 连接')
    }
  } catch (error) {
    ElMessage.error('检测失败：' + (error.response?.data?.detail || error.message))
  }
}

const refreshPorts = async () => {
  try {
    const data = await getConsolePorts()
    availablePorts.value = data.ports || []
  } catch (error) {
    ElMessage.error('刷新端口失败：' + (error.response?.data?.detail || error.message))
  }
}

const startDeploy = () => {
  isDeploying.value = true
  deployProgress.value = 0
  deployStatus.value = ''

  addLog('开始部署...', 'info')

  // 模拟部署进度
  const steps = [
    '连接 Console 端口',
    '唤醒设备 CLI',
    '进入 Enable 模式',
    '进入配置模式',
    '发送配置命令',
    '保存配置',
    '验证配置',
    '部署完成'
  ]

  let step = 0
  const interval = setInterval(() => {
    if (step >= steps.length) {
      clearInterval(interval)
      isDeploying.value = false
      deployStatus.value = 'success'
      deployProgress.value = 100
      addLog('配置部署成功!', 'success')
      ElMessage.success('配置部署成功')
      return
    }

    const progress = ((step + 1) / steps.length) * 100
    deployProgress.value = progress
    addLog(steps[step], 'info')
    step++
  }, 800)
}

const stopDeploy = () => {
  isDeploying.value = false
  deployStatus.value = 'exception'
  addLog('部署已停止', 'error')
  ElMessage.warning('部署已停止')
}

const clearLog = () => {
  deployLog.value = []
}

const addLog = (message, type = 'info') => {
  deployLog.value.push({
    time: new Date(),
    message,
    type
  })
}

const formatTime = (date) => dayjs(date).format('HH:mm:ss')

onMounted(() => {
  refreshPorts()
  getDevices().then(data => devices.value = data.items || [])
  getBackups({ limit: 10 }).then(data => recentBackups.value = data.items || [])
})
</script>

<style scoped>
.console-page {
  padding: 0;
}

.console-output {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  height: 400px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.empty {
  color: #666;
  text-align: center;
  padding: 50px 0;
}

.log-line {
  display: flex;
  gap: 10px;
  margin-bottom: 5px;
}

.log-line .time {
  color: #6a9955;
  white-space: nowrap;
}

.log-line .message {
  flex: 1;
}

.log-line .message.info { color: #d4d4d4; }
.log-line .message.success { color: #6a9955; }
.log-line .message.error { color: #f44747; }
.log-line .message.warning { color: #dcdcaa; }

.progress-section {
  margin-top: 15px;
}

.actions {
  display: flex;
  gap: 10px;
}
</style>
