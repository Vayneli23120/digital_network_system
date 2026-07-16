import api from './request'

// 获取 Dashboard 摘要
export function getDashboardSummary() {
  return api.get('/dashboard/summary')
}

// 获取管理层聚合 KPI
export function getExecutiveSummary(timeRange = '30d') {
  return api.get('/dashboard/executive-summary', { params: { time_range: timeRange } })
}

// 实时基础设施状态（在线率 + 进行中故障 + 按厂区）
export function getRealtimeStatus() {
  return api.get('/dashboard/realtime-status')
}

// 获取实时告警
export function getAlerts() {
  return api.get('/dashboard/alerts')
}

// AI 运营建议卡（规则聚合，未配置模型也可用）
export function getAiRecommendations(limit = 8) {
  return api.get('/ai/recommendations', { params: { limit } })
}

// 一键 AI 故障预判
export function aiPreDiagnoseFault(faultId) {
  return api.post(`/faults/${faultId}/ai-pre-diagnose`)
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

// 设备预检 API
export function testDeviceReachability(ip) {
  return api.post('/devices/test-reachability', { ip })
}

export function testDeviceConnection(ip, credential_group, vendor = 'cisco', device_type = null) {
  return api.post('/devices/test-connection', {
    ip,
    credential_group,
    vendor,
    device_type
  })
}

export function fetchDeviceInfo(ip, credential_group, vendor = 'cisco', device_type = null) {
  return api.post('/devices/fetch-info', {
    ip,
    credential_group,
    vendor,
    device_type
  }, { timeout: 60000 }) // 获取设备信息可能需要较长时间
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

// 设备性能指标（SNMP）
export function getDeviceMetrics(deviceId) {
  return api.get(`/devices/${deviceId}/metrics`, { timeout: 20000 })
}

export function getDeviceMetricHistory(deviceId, limit = 60) {
  return api.get(`/devices/${deviceId}/metrics/history`, { params: { limit } })
}

// 接口监控（SNMP）
export function listDeviceInterfaces(deviceId, monitoredOnly = false) {
  return api.get(`/devices/${deviceId}/interfaces`, { params: { monitored_only: monitoredOnly } })
}

export function updateDeviceInterface(deviceId, ifIndex, data) {
  return api.put(`/devices/${deviceId}/interfaces/${ifIndex}`, data)
}

export function getInterfaceTraffic(deviceId, ifIndex, limit = 60) {
  return api.get(`/devices/${deviceId}/interfaces/${ifIndex}/traffic`, { params: { limit } })
}

export function discoverDeviceInterfaces(deviceId) {
  return api.post(`/devices/${deviceId}/interfaces/discover`, {}, { timeout: 60000 })
}

export function discoverDeviceNeighbors(deviceId) {
  return api.post(`/devices/${deviceId}/interfaces/discover-neighbors`, {}, { timeout: 60000 })
}

export function diagnoseDeviceSnmp(deviceId) {
  return api.get(`/devices/${deviceId}/snmp-diagnose`, { timeout: 40000 })
}

// 备份相关
export function backupDevice(deviceId, operator) {
  return api.post(`/backups/backup/${deviceId}`, null, {
    params: { operator },
    timeout: 120000  // 备份操作可能需要较长时间（SSH连接设备）
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

// 部署执行 - 使用更长超时时间（批量部署可能需要很长时间）
export function executeDeploy(data) {
  return api.post('/deploy/execute', data, { timeout: 600000 }) // 10分钟
}

// 配置回滚 - 使用更长超时时间
export function rollbackDeploy(data) {
  return api.post('/deploy/rollback', data, { timeout: 600000 }) // 10分钟
}

// 部署历史
export function getDeployHistory(params) {
  return api.get('/deploy/history', { params })
}

export function getDeployHistoryDetail(historyId) {
  return api.get(`/deploy/history/${historyId}`)
}

export function deleteDeployHistory(historyId) {
  return api.delete(`/deploy/history/${historyId}`)
}

export function getCompatibleVariables() {
  return api.get('/deploy/compatible-variables')
}

// Phase 3: 维护窗口和预约部署
export function getMaintenanceWindows() {
  return api.get('/deploy/maintenance-windows')
}

export function scheduleDeploy(data) {
  return api.post('/deploy/schedule', data)
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
export function updateMovement(id, data) {
  return api.put(`/spare-movements/${id}`, data)
}
export function deleteMovement(id) {
  return api.delete(`/spare-movements/${id}`)
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
  return api.post('/compliance/check', data, {
    timeout: 180000  // AI审核可能需要较长时间（3分钟）
  })
}

// AI 配置审核
export function uploadConfigFile(formData) {
  return api.post('/compliance/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000  // AI审核可能需要较长时间（3分钟）
  })
}

export function quickComplianceCheck(data) {
  return api.post('/compliance/quick-check', data, {
    timeout: 120000  // 快速审核（2分钟）
  })
}

// 标准文档管理
export function getStandards(includeInactive = false) {
  return api.get('/compliance/standards', { params: { include_inactive: includeInactive } })
}

export function getStandard(id) {
  return api.get(`/compliance/standards/${id}`)
}

export function createStandard(data) {
  return api.post('/compliance/standards', data)
}

export function updateStandard(id, data) {
  return api.put(`/compliance/standards/${id}`, data)
}

export function deleteStandard(id) {
  return api.delete(`/compliance/standards/${id}`)
}

export function generateRulesForStandard(standardId) {
  return api.post(`/compliance/standards/${standardId}/generate-rules`, null, {
    timeout: 180000  // AI生成规则可能需要较长时间（3分钟）
  })
}

export function uploadStandardDocument(formData) {
  return api.post('/compliance/standards/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

// 规则管理
export function getRules(standardId = null) {
  return api.get('/compliance/rules', { params: { standard_id: standardId } })
}

export function getRuleDetail(ruleId) {
  return api.get(`/compliance/rules/${ruleId}`)
}

export function updateRuleStatus(ruleId, isActive) {
  return api.put(`/compliance/rules/${ruleId}/status`, null, { params: { is_active: isActive } })
}

export function updateRule(ruleId, data) {
  return api.put(`/compliance/rules/${ruleId}`, data)
}

// AI 配置管理
export function getAIConfig() {
  return api.get('/compliance/ai-config')
}

export function createAIConfig(data) {
  return api.post('/compliance/ai-config', data)
}

export function updateAIConfig(configId, data) {
  return api.put(`/compliance/ai-config/${configId}`, data)
}

export function testAIConfig(data) {
  return api.post('/compliance/ai-config/test', data, {
    timeout: 120000  // AI测试可能需要较长时间（2分钟）
  })
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

// AOP 年度规划
export function getAopPrograms(params) {
  return api.get('/planned-maintenance/aop/programs', { params })
}
export function createAopProgram(data) {
  return api.post('/planned-maintenance/aop/programs', data)
}
export function getAopProgram(id) {
  return api.get(`/planned-maintenance/aop/programs/${id}`)
}
export function updateAopProgram(id, data) {
  return api.put(`/planned-maintenance/aop/programs/${id}`, data)
}
export function getAopProjects(programId) {
  return api.get(`/planned-maintenance/aop/programs/${programId}/projects`)
}
export function createAopProject(programId, data) {
  return api.post(`/planned-maintenance/aop/programs/${programId}/projects`, data)
}
export function updateAopProject(projectId, data) {
  return api.put(`/planned-maintenance/aop/projects/${projectId}`, data)
}
export function getAopWindows(programId) {
  return api.get(`/planned-maintenance/aop/programs/${programId}/windows`)
}
export function createAopWindow(programId, data) {
  return api.post(`/planned-maintenance/aop/programs/${programId}/windows`, data)
}
export function createAopWindowsBatch(programId, windows) {
  return api.post(`/planned-maintenance/aop/programs/${programId}/windows/batch`, { windows })
}
export function updateAopWindow(windowId, data) {
  return api.put(`/planned-maintenance/aop/windows/${windowId}`, data)
}
export function generateAopTasks(programId) {
  return api.post(`/planned-maintenance/aop/programs/${programId}/generate-tasks`)
}
export function getAopCalendar(params) {
  return api.get('/planned-maintenance/aop/calendar', { params })
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

// ============ 设备健康评分 API ============
export function getHealthDashboard() {
  return api.get('/health/dashboard')
}

export function getHealthDevices(params) {
  return api.get('/devices', { params })
}

export function calculateAllHealth() {
  return api.post('/health/calculate-all')
}

export function calculateDeviceHealth(deviceId) {
  return api.post(`/health/devices/${deviceId}/calculate`)
}

export function getDeviceHealthHistory(deviceId) {
  return api.get(`/health/devices/${deviceId}/history`)
}

// ============ AI 分析 API ============
export function getAIDashboard() {
  return api.get('/ai/dashboard')
}

export function getAIHistory(params) {
  return api.get('/ai/history', { params })
}

export function analyzeFaultAI(faultId, data) {
  return api.post(`/faults/${faultId}/analyze`, data)
}

export function analyzeHealthAI(data) {
  return api.post('/ai/analyze-health', data)
}

// ============ 工作流 API ============
export function getWorkflowRules() {
  return api.get('/workflows/rules')
}

export function getWorkflowStats() {
  return api.get('/workflows/stats')
}

export function getWorkflowTriggers() {
  return api.get('/workflows/triggers')
}

export function getWorkflowActions() {
  return api.get('/workflows/actions')
}

export function initWorkflowDefaults() {
  return api.post('/workflows/init-defaults')
}

export function toggleWorkflowRule(ruleId) {
  return api.patch(`/workflows/rules/${ruleId}/toggle`)
}

export function createWorkflowRule(data) {
  return api.post('/workflows/rules', data)
}

export function updateWorkflowRule(ruleId, data) {
  return api.put(`/workflows/rules/${ruleId}`, data)
}

export function deleteWorkflowRule(ruleId) {
  return api.delete(`/workflows/rules/${ruleId}`)
}

export function testWorkflowTrigger(data) {
  return api.post('/workflows/trigger', data)
}

// ============ 系统通知 API ============
export function getNotifications(unreadOnly = false) {
  return api.get('/notifications', { params: { unread_only: unreadOnly } })
}

export function getUnreadCount() {
  return api.get('/notifications/unread-count')
}

export function markNotificationRead(id) {
  return api.post(`/notifications/${id}/read`)
}

export function markAllNotificationsRead() {
  return api.post('/notifications/read-all')
}

export function deleteNotification(id) {
  return api.delete(`/notifications/${id}`)
}

// ============ 故障状态流转 API ============
export function assignFault(faultId, assignedTo) {
  return api.post(`/faults/${faultId}/assign`, { assigned_to: assignedTo })
}

export function acceptFault(faultId) {
  return api.post(`/faults/${faultId}/accept`, { accepted: true })
}

export function reviewFault(faultId, data) {
  return api.post(`/faults/${faultId}/review`, data)
}

export function diagnoseFault(faultId, data) {
  return api.post(`/faults/${faultId}/diagnose`, data)
}

export function transferFaultToMaintenance(faultId, data) {
  return api.post(`/faults/${faultId}/transfer-to-maintenance`, data)
}

export function resolveFault(faultId, resolution) {
  return api.post(`/faults/${faultId}/resolve`, { resolution })
}

export function closeFault(faultId) {
  return api.post(`/faults/${faultId}/close`)
}

export function getFaultTransitions(faultId) {
  return api.get(`/faults/${faultId}/transitions`)
}

// ============ 权限管理 API ============
export function getPermissionsPermissions(params) {
  return api.get('/permissions/permissions', { params })
}

export function getPermissionsRoles() {
  return api.get('/permissions/roles')
}

export function getPermissionsRole(roleId) {
  return api.get(`/permissions/roles/${roleId}`)
}

export function createPermissionsRole(data) {
  return api.post('/permissions/roles', data)
}

export function updatePermissionsRole(roleId, data) {
  return api.put(`/permissions/roles/${roleId}`, data)
}

export function deletePermissionsRole(roleId) {
  return api.delete(`/permissions/roles/${roleId}`)
}

export function clonePermissionsRole(roleId, newName) {
  return api.post(`/permissions/roles/${roleId}/clone`, null, { params: { new_name: newName } })
}

export function getPermissionsResources() {
  return api.get('/permissions/resources')
}

export function getPermissionsDefaultsPermissions() {
  return api.get('/permissions/defaults/permissions')
}

export function getPermissionsDefaultsRoles() {
  return api.get('/permissions/defaults/roles')
}

export function getPermissionsInitStatus() {
  return api.get('/permissions/init-status')
}

export function initPermissionsSystem() {
  return api.post('/permissions/init')
}

export function getMyPermissions() {
  return api.get('/permissions/my-permissions')
}

export function checkPermission(permission) {
  return api.get(`/permissions/check/${permission}`)
}

export function checkPermissionsBatch(permissions) {
  return api.get('/permissions/check-batch', { params: { permissions } })
}

export function updateUserRoles(userId, roleIds) {
  return api.put(`/permissions/users/${userId}/roles`, { role_ids: roleIds })
}
