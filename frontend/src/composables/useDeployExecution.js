// Deploy 视图执行状态与 WebSocket 逻辑（item 946 切片 5）
// 从 frontend/src/views/Deploy.vue 拆分，行为与原实现完全一致。
// 与 useDeployHistory 存在 deployForm↔deviceExecutions 交叉耦合，
// 通过晚绑定 hooks 解耦（构造后在父中接线，调用处使用 ?.() 守卫）。
import { ref, computed, nextTick, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from '@/composables/useI18n'
import { useAuthStore } from '@/stores/auth'
import { rollbackDeploy as rollbackDeployApi } from '@/api'
import { clearCache } from '@/utils/cache.js'
import { getSessionCredentials } from '@/composables/useSessionCredentials'

export function useDeployExecution(form, hooks = {}) {
  const { t } = useI18n()
  const authStore = useAuthStore()
  const { deployForm, executionMode, parallelLimit, devices } = form

  // 执行状态
  const executionStatus = ref('idle') // idle, running, completed, failed, aborted
  const startTime = ref(null)
  const elapsedTime = ref(0)
  const deviceExecutions = ref([])
  const selectedDevice = ref(null)
  const aborting = ref(false)

  // CLI 输出容器 DOM 句柄（非响应式，由 DeployExecutionPanel 在 onMounted 注入）
  let cliOutputEl = null

  const registerCliOutput = (el) => {
    cliOutputEl = el
  }

  // 计算属性
  const totalDevices = computed(() => deviceExecutions.value.length)
  const completedDevices = computed(() =>
    deviceExecutions.value.filter(d => d.status === 'completed').length
  )
  const inProgressDevices = computed(() =>
    deviceExecutions.value.filter(d => d.status === 'running').length
  )
  const failedDevices = computed(() =>
    deviceExecutions.value.filter(d => d.status === 'failed').length
  )

  const progressPercentage = computed(() => {
    if (totalDevices.value === 0) return 0
    const totalProgress = deviceExecutions.value.reduce((sum, d) => sum + d.progress, 0)
    return Math.round(totalProgress / totalDevices.value)
  })

  const progressStatus = computed(() => {
    if (executionStatus.value === 'failed') return 'exception'
    if (executionStatus.value === 'completed') return 'success'
    return ''
  })

  const hasRollbackAvailable = computed(() => {
    return deviceExecutions.value.some(d => d.rollback_available)
  })

  // 按目标设备列表构建设备执行记录（executeDeploy 与 handleDeviceChange 共用）
  const buildDeviceExecutions = (deviceIds) => {
    return (deviceIds || []).map(id => {
      const device = (devices.value || []).find(d => d.id === id)
      return {
        device_id: id,
        device_name: device?.name || '',
        device_ip: device?.ip || '',
        status: 'pending',
        progress: 0,
        message: '',
        cliLogs: [],
        rollback_available: false
      }
    })
  }

  const initDeviceExecutions = (deviceIds) => {
    deviceExecutions.value = buildDeviceExecutions(deviceIds)
  }

  // 供 useDeployHistory 写入（loadHistoryRecord / handleDeleteHistory）
  const setDeviceExecutions = (list) => {
    deviceExecutions.value = list
  }

  const setSelectedDevice = (dev) => {
    selectedDevice.value = dev
  }

  const selectDevice = (device) => {
    selectedDevice.value = device
  }

  const clearCliOutput = () => {
    if (selectedDevice.value) {
      selectedDevice.value.cliLogs = []
    }
  }

  // 自动滚动到底部
  const scrollToBottom = () => {
    nextTick(() => {
      if (cliOutputEl) {
        cliOutputEl.scrollTop = cliOutputEl.scrollHeight
      }
    })
  }

  // WebSocket 连接
  let deployWebSocket = null
  let timer = null

  const executeDeploy = async () => {
    try {
      // 操作者会话级 SSH 凭证：缺少时先弹对话框收集（取消则中止部署）
      if (!(await hooks.ensureCredentials?.())) return

      // 初始化设备执行列表
      deviceExecutions.value = buildDeviceExecutions(deployForm.value.target_devices)

      // 准备部署数据（携带操作者会话级凭证，仅 WebSocket 会话内存传输）
      const deployData = {
        action: 'start_deploy',
        access_token: authStore.accessToken || undefined,
        mode: deployForm.value.mode,
        engine: deployForm.value.engine,
        napalm_mode: deployForm.value.napalm_mode,
        transfer_mode: deployForm.value.transfer_mode,  // scp | inline
        backup_file: deployForm.value.backup_file,
        template_id: deployForm.value.template_id,
        snippet: deployForm.value.snippet,
        snippet_position: deployForm.value.snippet_position,
        base_backup_file: deployForm.value.base_backup_file,
        target_devices: deployForm.value.target_devices,
        variables: {},
        dry_run: deployForm.value.dry_run,
        parallel_limit: executionMode.value === 'serial' ? 1 : parallelLimit.value,
        credentials: getSessionCredentials()
      }

      deployForm.value.variables.forEach(v => {
        if (v.key) deployData.variables[v.key] = v.value
      })

      // 开始执行部署
      executionStatus.value = 'running'
      startTime.value = Date.now()
      startElapsedTicker()

      // 使用 WebSocket 执行部署
      const sessionId = `deploy_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = window.location.host
      // VITE_WS_URL 为可选覆盖（远程访问或后端不同域时设置），缺省按 location.host 拼
      const wsBase = import.meta.env.VITE_WS_URL || `${wsProtocol}//${wsHost}`
      const wsUrl = `${wsBase}/ws/deploy/${sessionId}`

      deployWebSocket = new WebSocket(wsUrl)

      deployWebSocket.onopen = () => {
        // 发送部署请求
        deployWebSocket.send(JSON.stringify(deployData))
      }

      deployWebSocket.onmessage = (event) => {
        const data = JSON.parse(event.data)
        handleDeployMessage(data)
      }

      deployWebSocket.onerror = (error) => {
        console.error('WebSocket 错误:', error)
        stopTimer()
        executionStatus.value = 'failed'
        ElMessage.error(t('deployWsConnectFailed'))
      }

      deployWebSocket.onclose = () => {
        stopTimer()
      }

    } catch (error) {
      stopTimer()
      executionStatus.value = 'failed'
      hooks.clearRedeployParentId?.()
      ElMessage.error(t('deployFailed'))
    }
  }

  // 处理 WebSocket 消息
  const handleDeployMessage = (data) => {
    if (data.type === 'deploy_started') {
      // 部署开始
      ElMessage.info(t('deployStartCount', { count: data.total_count }))
    }
    else if (data.type === 'device_started') {
      // 设备开始部署
      const device = deviceExecutions.value.find(d => d.device_id === data.device_id)
      if (device) {
        device.status = 'running'
        device.message = t('deployDeploying')
        device.cliLogs.push({
          timestamp: data.timestamp,
          content: t('deployDeviceStartLog', { name: data.device_name }),
          type: 'info'
        })
      }
    }
    else if (data.type === 'device_progress') {
      // 设备进度更新
      const device = deviceExecutions.value.find(d => d.device_id === data.device_id)
      if (device) {
        device.status = data.status
        device.message = data.message
        device.progress = 100
        device.rollback_available = data.rollback_available || false

        // 显示 CLI 输出或配置差异
        if (data.cli_output) {
          device.cliLogs.push({
            timestamp: data.timestamp,
            content: data.cli_output,
            type: 'info'
          })
        }
        if (data.diff) {
          device.cliLogs.push({
            timestamp: data.timestamp,
            content: t('deployConfigDiffLog', { diff: data.diff }),
            type: 'diff'
          })
        }
        if (data.rollback_available) {
          device.cliLogs.push({
            timestamp: data.timestamp,
            content: t('deployRollbackAvailableLog'),
            type: 'info'
          })
        }
        if (!data.success) {
          device.cliLogs.push({
            timestamp: data.timestamp,
            content: t('deployErrorLog', { msg: data.message }),
            type: 'error'
          })
        }
        scrollToBottom()
      }

      // 更新整体进度
      const totalDevices = deviceExecutions.value.length
      const completedDevices = deviceExecutions.value.filter(d => d.status === 'completed' || d.status === 'failed').length
      if (totalDevices > 0) {
        const progress = Math.round((completedDevices / totalDevices) * 100)
        // 可以在这里更新整体进度条
      }
    }
    else if (data.type === 'deploy_complete') {
      // 部署完成
      stopTimer()

      const successCount = data.success_count || 0
      const failedCount = data.failed_count || 0

      // 更新执行状态
      executionStatus.value = failedCount === 0 ? 'completed' : (successCount > 0 ? 'completed' : 'failed')

      if (data.history_id) {
        hooks.setCurrentHistoryId?.(data.history_id)
      }

      // 重新加载历史记录
      hooks.reloadHistory?.()

      // 清除重新部署的父记录 ID
      hooks.clearRedeployParentId?.()

      // 关闭 WebSocket
      if (deployWebSocket) {
        deployWebSocket.close()
        deployWebSocket = null
      }

      // 清除设备缓存
      clearCache('devices')

      if (failedCount === 0) {
        ElMessage.success(t('deployCompleteAllSuccess', { count: successCount }))
      } else if (successCount > 0) {
        ElMessage.warning(t('deployCompletePartial', { ok: successCount, failed: failedCount }))
      } else {
        ElMessage.error(t('deployAllFailed', { count: failedCount }))
      }
    }
    else if (data.type === 'deploy_error') {
      // 部署错误
      ElMessage.error(data.message)
    }
  }

  const stopTimer = () => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  // 启动运行计时器：先清掉旧计时器再启动，避免产生孤儿计时器
  const startElapsedTicker = () => {
    if (timer) clearInterval(timer)
    timer = setInterval(() => {
      elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
    }, 1000)
  }

  const handleRollback = async () => {
    // 只回滚成功部署的设备（有 rollback_available 标记）
    const rollbackDevices = deviceExecutions.value
      .filter(d => d.rollback_available)
      .map(d => d.device_id)

    if (rollbackDevices.length === 0) {
      ElMessage.warning(t('deployNoRollbackDevices'))
      return
    }

    // 操作者会话级 SSH 凭证：缺少时先弹对话框收集（取消则中止回滚）
    if (!(await hooks.ensureCredentials?.())) return

    try {
      await ElMessageBox.confirm(
        t('deployRollbackConfirm'),
        t('deployRollbackTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )

      const rollbackData = {
        target_devices: rollbackDevices,
        parent_id: hooks.getSelectedHistoryId?.() || hooks.getCurrentHistoryId?.() || null,
        credentials: getSessionCredentials()
      }

      executionStatus.value = 'running'
      const result = await rollbackDeployApi(rollbackData)

      stopTimer()

      // 处理回滚结果
      deviceExecutions.value.forEach(d => {
        if (!d.rollback_available) {
          d.status = 'skipped'
          d.message = t('deployRollbackSkippedMsg')
        }
      })

      if (result.results && result.results.length > 0) {
        result.results.forEach(r => {
          const device = deviceExecutions.value.find(d => Number(d.device_id) === Number(r.device_id))
          if (device) {
            device.status = r.success ? 'completed' : 'failed'
            device.message = r.message || (r.success ? t('deployRollbackSucceeded') : t('deployRollbackFailed'))
            device.progress = 100
            device.rollback_available = false
            device.cliLogs = []

            if (r.cli_output) {
              device.cliLogs.push({
                timestamp: new Date().toISOString(),
                content: r.cli_output,
                type: 'info'
              })
            }
            if (r.diff) {
              device.cliLogs.push({
                timestamp: new Date().toISOString(),
                content: t('deployConfigChangeLog', { diff: r.diff }),
                type: 'diff'
              })
            }
            if (r.errors && r.errors.length > 0) {
              r.errors.forEach(err => {
                device.cliLogs.push({
                  timestamp: new Date().toISOString(),
                  content: t('deployErrorLog', { msg: err }),
                  type: 'error'
                })
              })
            }
          }
        })
      }

      executionStatus.value = result.success ? 'completed' : 'failed'
      clearCache('devices')

      // 重新加载历史记录
      await hooks.reloadHistory?.()

      if (result.success) {
        ElMessage.success(t('deployRollbackSuccess'))
      } else {
        ElMessage.error(t('deployRollbackFailed'))
      }

    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error(t('deployRollbackFailed'))
      }
    }
  }

  const confirmAbort = async () => {
    try {
      await ElMessageBox.confirm(
        t('deployAbortConfirm'),
        t('deployAbortTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )
      await abortExecution()
    } catch {
      // Cancelled
    }
  }

  const abortExecution = async () => {
    aborting.value = true
    try {
      // 关闭 WebSocket 连接
      if (deployWebSocket) {
        deployWebSocket.close()
        deployWebSocket = null
      }
      executionStatus.value = 'aborted'
      stopTimer()
      ElMessage.warning(t('deployAborted'))
    } catch (error) {
      ElMessage.error(t('deployAbortFailed'))
    } finally {
      aborting.value = false
    }
  }

  // 卸载清理：停止运行计时器并关闭部署 WebSocket，避免切路由后资源残留
  onBeforeUnmount(() => {
    stopTimer()
    if (deployWebSocket) {
      deployWebSocket.onclose = null  // 关闭时不再触发 stopTimer（无副作用，仅避免多余回调）
      deployWebSocket.close()
      deployWebSocket = null
    }
  })

  return {
    executionStatus,
    startTime,
    elapsedTime,
    deviceExecutions,
    selectedDevice,
    aborting,
    totalDevices,
    completedDevices,
    inProgressDevices,
    failedDevices,
    progressPercentage,
    progressStatus,
    hasRollbackAvailable,
    initDeviceExecutions,
    setDeviceExecutions,
    setSelectedDevice,
    selectDevice,
    clearCliOutput,
    registerCliOutput,
    executeDeploy,
    handleRollback,
    confirmAbort,
    abortExecution
  }
}
