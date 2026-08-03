// Deploy 视图纯逻辑：无 vue 依赖、无 i18n 调用，便于单测。
// 从 frontend/src/views/Deploy.vue 拆分（item 946 切片 3），行为与原实现完全一致。

// 设备状态标签类型
export const getDeviceStatusType = (status) => {
  const types = { pending: 'info', running: 'primary', completed: 'success', failed: 'danger', skipped: 'warning' }
  return types[status] || 'info'
}

// 设备进度条状态
export const getDeviceProgressStatus = (status) => {
  if (status === 'failed') return 'exception'
  if (status === 'completed') return 'success'
  return ''
}

// 时长格式化（秒 → M:SS）
export const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 时间格式化
export const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// 检查历史记录是否已被回滚
export const hasBeenRolledBack = (record) => {
  if (record.mode === 'rollback') return false  // 回滚记录本身不算"已被回滚"
  // 检查是否所有成功设备都已被回滚（rollback_available = false 且有 rollback_status）
  const successDevices = record.deviceResults?.filter(d => d.status === 'completed') || []
  if (successDevices.length === 0) return false
  return successDevices.every(d => d.rollback_status === 'rolled_back')
}

// 检查历史记录是否可以回滚
export const canRollback = (record) => {
  if (record.mode === 'rollback') return false  // 回滚记录不能再回滚
  if (record.engine !== 'napalm') return false  // 只有 NAPALM 支持回滚
  // 检查是否有 rollback_available = true 的设备
  return record.deviceResults?.some(d => d.rollback_available) || false
}

// 风险等级标签类型
export const getRiskLevelType = (level) => {
  const types = { low: 'success', medium: 'warning', high: 'danger' }
  return types[level] || 'info'
}
