import api from './request'

// 获取 Dashboard 摘要
export function getDashboardSummary() {
  return api.get('/dashboard/summary')
}

// 设备相关
export function getDevices(params) {
  return api.get('/devices', { params })
}

export function getDeviceDetail(id) {
  return api.get(`/devices/${id}`)
}

export function createDevice(data) {
  return api.post('/devices', data)
}

export function updateDevice(id, data) {
  return api.put(`/devices/${id}`, data)
}

export function deleteDevice(id) {
  return api.delete(`/devices/${id}`)
}

// 照片相关
export function getDevicePhotos(deviceId) {
  return api.get(`/devices/${deviceId}/photos`)
}

export function uploadPhoto(deviceId, file, photoType = 'other') {
  const formData = new FormData()
  formData.append('photo', file)
  formData.append('photo_type', photoType)
  return api.post(`/devices/${deviceId}/photos`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deletePhoto(deviceId, photoId) {
  return api.delete(`/devices/${deviceId}/photos/${photoId}`)
}

export function getDeviceInventory(deviceId) {
  return api.get(`/devices/${deviceId}/inventory`)
}

// 备份相关
export function backupDevice(deviceId, operator) {
  return api.post(`/backups/backup/${deviceId}`, null, {
    params: { operator }
  })
}

export function batchBackup(deviceIds, operator) {
  return api.post('/backups/batch', deviceIds, {
    params: { operator }
  })
}

export function getBackups(params) {
  return api.get('/backups', { params })
}

export function getBackupContent(backupId) {
  return api.get(`/backups/${backupId}/content`)
}

export function getBackupDiff(backupId) {
  return api.get(`/backups/${backupId}/diff`)
}

// 故障相关
export function getFaults(params) {
  return api.get('/faults', { params })
}

export function getFaultDetail(id) {
  return api.get(`/faults/${id}`)
}

export function createFault(data) {
  return api.post('/faults', data)
}

export function updateFault(id, data) {
  return api.put(`/faults/${id}`, data)
}

export function deleteFault(id) {
  return api.delete(`/faults/${id}`)
}

// 维修相关
export function getMaintenances(params) {
  return api.get('/maintenance', { params })
}

export function getMaintenanceDetail(id) {
  return api.get(`/maintenance/${id}`)
}

export function createMaintenance(data) {
  return api.post('/maintenance', data)
}

export function updateMaintenance(id, data) {
  return api.put(`/maintenance/${id}`, data)
}

export function deleteMaintenance(id) {
  return api.delete(`/maintenance/${id}`)
}

// 维修状态流转
export function transitionMaintenanceStatus(id, data) {
  return api.post(`/maintenance/${id}/transition`, data)
}

// 获取维修事件时间线
export function getMaintenanceEvents(id) {
  return api.get(`/maintenance/${id}/events`)
}

// 分配维修负责人
export function assignMaintenance(id, data) {
  return api.put(`/maintenance/${id}/assign`, data)
}

// Console 相关
export function getConsolePorts() {
  return api.get('/console/ports')
}

export function autoDetectConsole() {
  return api.post('/console/auto-detect')
}

export function deployConsoleConfig(data) {
  return api.post('/console/deploy', data)
}

// 模板相关
export function getTemplates() {
  return api.get('/templates')
}

export function createTemplate(data) {
  return api.post('/templates', data)
}

export function getTemplate(id) {
  return api.get(`/templates/${id}`)
}

export function updateTemplate(id, data) {
  return api.put(`/templates/${id}`, data)
}

export function deleteTemplate(id) {
  return api.delete(`/templates/${id}`)
}

export function renderTemplate(id, variables) {
  return api.post(`/templates/${id}/render`, variables)
}

// 凭证管理
export function getCredentials() {
  return api.get('/credentials')
}

export function createCredential(data) {
  return api.post('/credentials', data)
}

export function getCredential(id) {
  return api.get(`/credentials/${id}`)
}

export function updateCredential(id, data) {
  return api.put(`/credentials/${id}`, data)
}

export function deleteCredential(id) {
  return api.delete(`/credentials/${id}`)
}

// 设备导入导出
export function exportDevices() {
  return api.get('/devices/export', { responseType: 'blob' })
}

export function importDevices(formData) {
  return api.post('/devices/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 配置部署
export function previewDeploy(data) {
  return api.post('/deploy/preview', data)
}

export function executeDeploy(data) {
  return api.post('/deploy/execute', data)
}

export function getCompatibleVariables() {
  return api.get('/deploy/compatible-variables')
}

// 日志管理
export function getLogs(params) {
  return api.get('/logs', { params })
}

export function getLogFiles(params) {
  return api.get('/logs/files', { params })
}

export function getLogFileContent(filename, params) {
  return api.get(`/logs/files/${filename}`, { params })
}

export function searchLogs(keyword, params) {
  return api.get('/logs/search', { params: { keyword, ...params } })
}

export function clearOldLogs(days) {
  return api.post('/logs/clear', null, { params: { days } })
}

// 仪表盘趋势
export function getFaultTrend(params) {
  return api.get('/dashboard/fault-trend', { params })
}

// 设备发现
export function pingSweep(data) {
  return api.post('/discovery/ping-sweep', data)
}
export function discoverDevices(data) {
  return api.post('/discovery/discover', data)
}
export function getDiscoveryCapabilities() {
  return api.get('/discovery/capabilities')
}

// 工具日志
export function getToolLogs(params) {
  return api.get('/tool-logs/', { params })
}
export function searchToolLogs(keyword, params) {
  return api.get('/tool-logs/search', { params: { keyword, ...params } })
}
export function getToolLogDetail(id) {
  return api.get(`/tool-logs/${id}`)
}
export function getToolLogStats() {
  return api.get('/tool-logs/stats/summary')
}
export function cleanupToolLogs(days) {
  return api.delete('/tool-logs/cleanup', { params: { days } })
}

// 备件管理
export function getPartList(params) {
  return api.get('/spare-parts/', { params })
}
export function getPart(id) {
  return api.get(`/spare-parts/${id}`)
}
export function createPart(data) {
  return api.post('/spare-parts/', data)
}
export function updatePart(id, data) {
  return api.put(`/spare-parts/${id}`, data)
}
export function deletePart(id) {
  return api.delete(`/spare-parts/${id}`)
}
export function getPartStats() {
  return api.get('/spare-parts/stats/summary')
}
// 扫码枪查询 - 通过序列号查找备件
export function getPartBySerialNumber(serialNumber) {
  return api.get(`/spare-parts/by-serial/${serialNumber}`)
}

// 搜索库存中的备件实例（维修更换备件专用，只返回 in_stock 状态）
export function searchInStockParts(keyword) {
  return api.get('/spare-parts/search-in-stock', { params: { keyword } })
}

// 获取备件实例列表
export function getPartInstances(partId, status = null) {
  const params = status ? { status } : {}
  return api.get(`/spare-parts/${partId}/instances`, { params })
}

// 手动入库（创建实例）
export function manualStockIn(partId, data) {
  return api.post(`/spare-parts/${partId}/manual-in`, data)
}

// 手动出库（更新实例状态）
export function manualStockOut(partId, data) {
  return api.post(`/spare-parts/${partId}/manual-out`, data)
}

// 备件出入库
export function createMovement(data) {
  return api.post('/spare-movements/', data)
}
export function getMovements(params) {
  return api.get('/spare-movements/', { params })
}
export function getMovementDetail(id) {
  return api.get(`/spare-movements/${id}`)
}

// 认证
export function login(data) {
  return api.post('/auth/login', data)
}
export function logout() {
  return api.post('/auth/logout')
}
export function getCurrentUser() {
  return api.get('/auth/me')
}
export function registerUser(data) {
  return api.post('/auth/register', data)
}
export function changePassword(data) {
  return api.post('/auth/change-password', data)
}

// 告警通知
export function getAlertSettings() {
  return api.get('/alerts/settings')
}
export function saveAlertSettings(data) {
  return api.post('/alerts/settings', data)
}
export function getAlertStatus() {
  return api.get('/alerts/status')
}
export function testAlertChannel(channel = 'all') {
  return api.post('/alerts/test', null, { params: { channel } })
}

// 配置合规
export function getCheckItems() {
  return api.get('/compliance/checks')
}
export function runComplianceCheck(data) {
  return api.post('/compliance/check', data)
}

// 厂商管理
export function getVendors() {
  return api.get('/devices/vendors')
}
export function getVendorInfo(vendor) {
  return api.get(`/devices/vendors/${vendor}`)
}

// 故障转维修
export function convertFaultToMaintenance(faultId) {
  return api.post(`/faults/${faultId}/convert-to-maintenance`)
}
export function getFaultMaintenance(faultId) {
  return api.get(`/faults/${faultId}/maintenance`)
}

// 计划性运维
export function getMaintenancePlans(params) {
  return api.get('/planned-maintenance/plans', { params })
}
export function createMaintenancePlan(data) {
  return api.post('/planned-maintenance/plans', data)
}
export function getMaintenancePlan(id) {
  return api.get(`/planned-maintenance/plans/${id}`)
}
export function updateMaintenancePlan(id, data) {
  return api.put(`/planned-maintenance/plans/${id}`, data)
}
export function deleteMaintenancePlan(id) {
  return api.delete(`/planned-maintenance/plans/${id}`)
}

export function getMaintenanceTasks(params) {
  return api.get('/planned-maintenance/tasks', { params })
}
export function createMaintenanceTask(data) {
  return api.post('/planned-maintenance/tasks', data)
}
export function getMaintenanceTask(id) {
  return api.get(`/planned-maintenance/tasks/${id}`)
}
export function startMaintenanceTask(id) {
  return api.post(`/planned-maintenance/tasks/${id}/start`)
}
export function completeMaintenanceTask(id, data) {
  return api.post(`/planned-maintenance/tasks/${id}/complete`, data)
}
export function skipMaintenanceTask(id, reason) {
  return api.post(`/planned-maintenance/tasks/${id}/skip`, null, { params: { reason } })
}
export function deleteMaintenanceTask(id) {
  return api.delete(`/planned-maintenance/tasks/${id}`)
}

export function getPlannedMaintenanceStats(params) {
  return api.get('/planned-maintenance/stats', { params })
}
export function generateTasksForPlans() {
  return api.post('/planned-maintenance/generate-tasks')
}

// ============ 用户管理 API ============
export function getUsers() {
  return api.get('/auth/users')
}

export function createUser(data) {
  return api.post('/auth/users', data)
}

export function updateUser(id, data) {
  return api.put(`/auth/users/${id}`, data)
}

export function deleteUser(id) {
  return api.delete(`/auth/users/${id}`)
}

export function getRoles() {
  return api.get('/auth/roles')
}

// ============ 扫码会话 API ============
export function createScanSession(data) {
  return api.post('/scan/sessions', data)
}

export function getScanSession(sessionCode) {
  return api.get(`/scan/sessions/${sessionCode}`)
}

export function joinScanSession(sessionCode) {
  return api.post('/scan/sessions/join', { session_code: sessionCode })
}

export function addScanItem(sessionCode, serialNumber, quantity = 1) {
  return api.post('/scan/sessions/items', {
    session_code: sessionCode,
    serial_number: serialNumber,
    quantity
  })
}

export function removeScanItem(sessionCode, serialNumber) {
  return api.delete(`/scan/sessions/${sessionCode}/items/${serialNumber}`)
}

export function completeScanSession(sessionCode, items = null, reason = '') {
  const data = { items, reason }
  return api.post(`/scan/sessions/${sessionCode}/complete`, data)
}

export function deleteScanSession(sessionCode) {
  return api.delete(`/scan/sessions/${sessionCode}`)
}

// ============ 系统监控大屏 API ============
export function getFloorPlans() {
  return api.get('/floor-plans')
}

export function getFloorPlan(id) {
  return api.get(`/floor-plans/${id}`)
}

export function createFloorPlan(formData) {
  return api.post('/floor-plans', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function updateFloorPlan(id, formData) {
  return api.put(`/floor-plans/${id}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deleteFloorPlan(id) {
  return api.delete(`/floor-plans/${id}`)
}

export function getFloorPlanNodes(planId) {
  return api.get(`/floor-plans/${planId}/nodes`)
}

export function getAvailableDevices(planId) {
  return api.get(`/floor-plans/${planId}/available-devices`)
}

export function createDeviceNode(planId, data) {
  return api.post(`/floor-plans/${planId}/nodes`, data)
}

export function updateDeviceNode(planId, nodeId, data) {
  return api.put(`/floor-plans/${planId}/nodes/${nodeId}`, data)
}

export function deleteDeviceNode(planId, nodeId) {
  return api.delete(`/floor-plans/${planId}/nodes/${nodeId}`)
}

export function getMonitorDeviceDetail(deviceId) {
  return api.get(`/monitor-screen/device/${deviceId}/detail`)
}

export function getOfflineAlerts() {
  return api.get('/monitor-screen/offline-alerts')
}

export function getMonitorStats() {
  return api.get('/monitor-screen/stats')
}
