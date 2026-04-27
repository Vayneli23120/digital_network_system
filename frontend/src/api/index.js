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
