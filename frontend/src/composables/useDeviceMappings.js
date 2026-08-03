// Monitor3D 设备类型/状态标签映射（item 946 切片 8）
// 从 frontend/src/views/Monitor3D.vue 拆分，行为与原实现完全一致。
// 纯映射函数（无共享可变状态），父（场景 HUD/标签）与 SidePanel（模板）各调用一次均安全。
import { Box, Position, Connection, Lock } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'

export function useDeviceMappings() {
  const { t } = useI18n()

  // 设备库模板（拖拽到画布创建设备）
  const deviceTemplates = [
    { type: 'switch',   icon: Box,        labelKey: 'deviceTypeSwitch' },
    { type: 'ap',       icon: Position,   labelKey: 'deviceTypeAP' },
    { type: 'router',   icon: Connection, labelKey: 'deviceTypeRouter' },
    { type: 'firewall', icon: Lock,       labelKey: 'deviceTypeFirewall' },
  ]

  // 设备类型/状态中文映射（i18n 键优先，缺失回退中文）
  const deviceTypeMap = {
    'office_switch': '办公交换机',
    'core_switch': '核心交换机',
    'server_switch': '服务器交换机',
    'uce': 'UCE',
    'ap': 'AP',
    'wlc': '无线控制器',
    'router': '路由器',
    'firewall': '防火墙',
  }

  const statusMap = {
    'online': '在线',
    'offline': '离线',
    'maintenance': '维护中',
    'unknown': '未知',
  }

  // i18n 版本：随语言切换显示状态/设备类型（用于 HUD 等动态渲染）
  const statusI18nKey = { online: 'statusOnline', offline: 'statusOffline', maintenance: 'statusMaintenance', unknown: 'statusUnknown' }
  function getStatusLabelI18n(status) {
    const key = statusI18nKey[status]
    return key ? t(key) : (statusMap[status] || status)
  }
  const deviceTypeI18nKey = {
    office_switch: 'deviceTypeOfficeSwitch',
    core_switch: 'deviceTypeCoreSwitch',
    server_switch: 'deviceTypeServerSwitch',
    uce: 'deviceTypeUCE',
    ap: 'deviceTypeAP',
    wlc: 'deviceTypeWLC',
    router: 'deviceTypeRouter',
    firewall: 'deviceTypeFirewall',
  }
  function getDeviceTypeLabelI18n(type) {
    const key = deviceTypeI18nKey[type]
    return key ? t(key) : (deviceTypeMap[type] || type)
  }

  function faultSeverityTag(severity) {
    if (severity === 'critical') return 'danger'
    if (severity === 'major') return 'warning'
    if (severity === 'warning') return 'warning'
    return 'info'
  }

  // 统一以可达性(reachability)推导设备显示状态，替代旧 status 字段
  // reachable -> online, unreachable -> offline, 其余 -> unknown
  function deviceStatus(d) {
    if (d?.reachability === 'unreachable') return 'offline'
    if (d?.reachability === 'reachable') return 'online'
    return 'unknown'
  }
  function isDeviceOffline(d) {
    return d?.reachability === 'unreachable'
  }
  function isDeviceOnline(d) {
    return d?.reachability === 'reachable'
  }

  return { deviceTemplates, getStatusLabelI18n, getDeviceTypeLabelI18n, deviceStatus, isDeviceOffline, isDeviceOnline, faultSeverityTag }
}
