// Deploy 视图部署历史逻辑（item 946 切片 5）
// 从 frontend/src/views/Deploy.vue 拆分，行为与原实现完全一致。
// 与 useDeployExecution 存在 deployForm↔deviceExecutions 交叉耦合，
// 通过晚绑定 deps 解耦（构造后在父中接线，调用处使用 ?.() 守卫）。
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from '@/composables/useI18n'
import { getDeployHistory, getDeployHistoryDetail, deleteDeployHistory } from '@/api'
import { stampUid } from '@/utils/uid.js'

export function useDeployHistory(deps = {}) {
  const { t } = useI18n()
  const { deployForm } = deps

  // 部署历史记录（从后端 API 加载）
  const deployHistory = ref([])
  const selectedHistoryId = ref(null)
  const currentHistoryId = ref(null)  // 当前正在操作的部署记录ID（用于回滚关联）
  const historyLoading = ref(false)

  // 加载历史记录
  const loadHistory = async () => {
    try {
      historyLoading.value = true
      const res = await getDeployHistory({ limit: 50 })
      deployHistory.value = res.history || []
    } catch (e) {
      console.error('Failed to load deploy history:', e)
      ElMessage.error(t('deployLoadHistoryFailed'))
    } finally {
      historyLoading.value = false
    }
  }

  // 加载历史记录详情到左侧面板
  const loadHistoryRecord = async (record) => {
    selectedHistoryId.value = record.id

    // 如果 record 只有摘要信息，从 API 加载完整详情
    let fullRecord = record
    if (!record.deviceResults || record.deviceResults.length === 0 || !record.deviceResults[0]?.logs) {
      try {
        fullRecord = await getDeployHistoryDetail(record.id)
      } catch (e) {
        console.error('Failed to load history detail:', e)
        return
      }
    }

    // 清空当前设备执行状态，使用保存的状态
    const deviceExecutions = (fullRecord.deviceResults || []).map(d => ({
      device_id: d.device_id,
      device_name: d.device_name,
      status: d.status || 'completed',  // 使用保存的状态，默认 completed
      message: d.message || '',
      progress: 100,
      cliLogs: d.logs || [],
      rollback_available: d.rollback_available || false
    }))
    deps.setDeviceExecutions?.(deviceExecutions)
    // 选中第一个设备
    if (deviceExecutions.length > 0) {
      deps.setSelectedDevice?.(deviceExecutions[0])
    }
  }

  // 任务链分组：将部署历史按父子关系分组
  const groupedHistory = computed(() => {
    const groups = []
    const processedIds = new Set()

    // 先找出所有父记录（原始部署）
    const parentRecords = deployHistory.value.filter(r => !r.parent_id && r.operation_type === 'deploy')

    for (const parent of parentRecords) {
      if (processedIds.has(parent.id)) continue

      // 找出所有子记录（回滚、重新部署）
      const children = deployHistory.value
        .filter(r => r.parent_id === parent.id)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)) // 按时间倒序

      groups.push({
        parent,
        children,
        parentId: parent.id  // 用于跟踪展开状态
      })

      processedIds.add(parent.id)
      children.forEach(c => processedIds.add(c.id))
    }

    // 再处理独立的记录（没有父记录的回滚等）
    const orphanRecords = deployHistory.value.filter(r => !processedIds.has(r.id))
    for (const orphan of orphanRecords) {
      groups.push({
        parent: orphan,
        children: [],
        parentId: orphan.id
      })
    }

    return groups
  })

  // 展开状态存储（响应式）
  const expandedGroups = ref({})

  // 判断组是否展开
  const isGroupExpanded = (parentId) => {
    // 默认展开，除非明确设置为 false
    return expandedGroups.value[parentId] !== false
  }

  // 展开/折叠任务链
  const toggleGroupExpand = (parentId) => {
    const current = expandedGroups.value[parentId]
    expandedGroups.value[parentId] = current === false ? true : false
  }

  // 从历史记录执行回滚
  const handleHistoryRollback = async (record) => {
    // 先加载历史记录到设备执行列表
    await loadHistoryRecord(record)
    // 然后执行回滚
    await deps.handleRollback?.()
  }

  // 从历史记录重新部署
  const handleRedeploy = async (record) => {
    try {
      // 如果需要完整配置，从 API 加载详情
      let fullRecord = record
      if (!record.deployConfig && !record.deploy_config) {
        try {
          fullRecord = await getDeployHistoryDetail(record.id)
        } catch (e) {
          ElMessage.warning(t('deployRedeployNoConfig'))
          return
        }
      }

      // 检查是否有部署配置
      const config = fullRecord.deployConfig || fullRecord.deploy_config
      if (!config) {
        ElMessage.warning(t('deployRedeployNoConfig'))
        return
      }

      const deviceIds = fullRecord.deviceResults?.map(d => d.device_id) || fullRecord.target_devices?.map(d => d.id) || []
      if (deviceIds.length === 0) {
        ElMessage.warning(t('deployNoDevicesInHistory'))
        return
      }

      await ElMessageBox.confirm(
        t('deployRedeployConfirmDetail', {
          count: deviceIds.length,
          engine: config.engine,
          mode: config.mode
        }),
        t('deployRedeployTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'info' }
      )

      // 恢复部署配置
      deployForm.value.mode = config.mode || 'backup'
      deployForm.value.engine = config.engine || 'napalm'
      deployForm.value.napalm_mode = config.napalm_mode || 'merge'
      deployForm.value.backup_file = config.backup_file || ''
      deployForm.value.template_id = config.template_id || ''
      deployForm.value.snippet = config.snippet || ''
      deployForm.value.snippet_position = config.snippet_position || 'append'
      deployForm.value.base_backup_file = config.base_backup_file || ''
      deployForm.value.target_devices = deviceIds
      // variables 可能是对象格式，需要转换为数组
      if (config.variables && typeof config.variables === 'object' && !Array.isArray(config.variables)) {
        deployForm.value.variables = Object.entries(config.variables).map(([key, value]) => stampUid({ key, value }))
      } else {
        deployForm.value.variables = (config.variables || []).map(stampUid)
      }
      deployForm.value.dry_run = false

      // 检查必要配置是否存在
      let missingConfig = ''
      if (deployForm.value.mode === 'backup' && !deployForm.value.backup_file) {
        missingConfig = t('deploySelectBackupFile')
      } else if (deployForm.value.mode === 'template' && !deployForm.value.template_id) {
        missingConfig = t('deploySelectTemplate')
      } else if (deployForm.value.mode === 'snippet' && !deployForm.value.snippet) {
        missingConfig = t('deployInputSnippet')
      }

      if (missingConfig) {
        ElMessage.warning(t('deployRedeployConfigMissing') + ': ' + missingConfig)
        return
      }

      // 记录父记录 ID，用于建立任务链
      redeployParentId.value = record.id

      // 直接执行部署
      await deps.executeDeploy?.()

    } catch (error) {
      if (error !== 'cancel') {
        console.error('重新部署失败:', error)
        ElMessage.error(t('deployRedeployFailed'))
      }
    }
  }

  // 删除历史记录
  const handleDeleteHistory = async (record) => {
    try {
      await ElMessageBox.confirm(
        t('deployDeleteConfirm'),
        t('deployDeleteHistory'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )

      await deleteDeployHistory(record.id)
      ElMessage.success(t('deployDeleteSuccess'))
      // 重新加载历史记录
      await loadHistory()

      // 如果删除的是当前选中的记录，清空选中状态
      if (selectedHistoryId.value === record.id) {
        selectedHistoryId.value = null
        deps.setDeviceExecutions?.([])
        deps.setSelectedDevice?.(null)
      }
    } catch (error) {
      if (error !== 'cancel') {
        if (error.response?.status === 403) {
          ElMessage.error(t('deployDeletePermissionDenied'))
        } else {
          ElMessage.error(t('deployDeleteFailed'))
        }
        console.error('删除历史记录失败:', error)
      }
    }
  }

  // 重新部署的父记录 ID
  const redeployParentId = ref(null)

  // 供 useDeployExecution 读写（回滚关联 / 清除父记录 ID）
  const setCurrentHistoryId = (id) => {
    currentHistoryId.value = id
  }

  const getSelectedHistoryId = () => selectedHistoryId.value
  const getCurrentHistoryId = () => currentHistoryId.value

  const setRedeployParentId = (id) => {
    redeployParentId.value = id
  }

  const clearRedeployParentId = () => {
    redeployParentId.value = null
  }

  return {
    deployHistory,
    selectedHistoryId,
    currentHistoryId,
    historyLoading,
    redeployParentId,
    expandedGroups,
    loadHistory,
    loadHistoryRecord,
    groupedHistory,
    isGroupExpanded,
    toggleGroupExpand,
    handleHistoryRollback,
    handleRedeploy,
    handleDeleteHistory,
    setCurrentHistoryId,
    getSelectedHistoryId,
    getCurrentHistoryId,
    setRedeployParentId,
    clearRedeployParentId
  }
}
