import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Layout from '@/views/Layout.vue'
import Login from '@/views/Login.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录', noAuth: true }
  },
  // 临时演示路由（B1 深海暗流背景独立测试用），集成完成后可随时删除
  {
    path: '/demo/ocean-background',
    name: 'OceanBackgroundDemo',
    component: () => import('@/components/OceanBackgroundDemo.vue'),
    meta: { title: '背景演示', noAuth: true }
  },
  {
    path: '/',
    name: 'Layout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/Dashboard.vue'),
        meta: { title: '仪表板' }
      }
    ]
  },
  {
    path: '/operations',
    name: 'OperationsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Operations',
        component: () => import('@/views/Operations.vue'),
        meta: { title: '运维总览' }
      }
    ]
  },
  {
    path: '/devices',
    name: 'DevicesLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Devices',
        component: () => import('@/views/Devices.vue'),
        meta: { title: '设备管理' }
      },
      {
        path: ':id',
        name: 'DeviceDetail',
        component: () => import('@/views/DeviceDetail.vue'),
        meta: { title: '设备详情' }
      }
    ]
  },
  {
    path: '/backups',
    name: 'BackupsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Backups',
        component: () => import('@/views/Backups.vue'),
        meta: { title: '备份管理' }
      }
    ]
  },
  {
    path: '/faults',
    name: 'FaultsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Faults',
        component: () => import('@/views/Faults.vue'),
        meta: { title: '故障管理' }
      },
      {
        path: ':id',
        name: 'FaultDetail',
        component: () => import('@/views/FaultDetail.vue'),
        meta: { title: '故障详情' }
      }
    ]
  },
  {
    path: '/maintenance',
    name: 'MaintenanceLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Maintenance',
        component: () => import('@/views/Maintenance.vue'),
        meta: { title: '维修管理' }
      },
      {
        path: ':id',
        name: 'MaintenanceDetail',
        component: () => import('@/views/MaintenanceDetail.vue'),
        meta: { title: '维修详情' }
      }
    ]
  },
  {
    path: '/console',
    name: 'ConsoleLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Console',
        component: () => import('@/views/Console.vue'),
        meta: { title: 'Console 配置' }
      }
    ]
  },
  {
    path: '/deploy',
    name: 'DeployLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Deploy',
        component: () => import('@/views/Deploy.vue'),
        meta: { title: '配置部署' }
      }
    ]
  },
  {
    path: '/templates',
    name: 'TemplatesLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Templates',
        component: () => import('@/views/Templates.vue'),
        meta: { title: '配置模板' }
      }
    ]
  },
  {
    path: '/credentials',
    name: 'CredentialsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Credentials',
        component: () => import('@/views/Credentials.vue'),
        meta: { title: 'SSH 凭证', permission: 'credential:read' }
      }
    ]
  },
  {
    path: '/logs',
    name: 'LogsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Logs',
        component: () => import('@/views/Logs.vue'),
        meta: { title: '系统日志', permission: 'log:read' }
      }
    ]
  },
  // v1.1 新增路由
  {
    path: '/spare-parts',
    name: 'SparePartsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'SpareParts',
        component: () => import('@/views/SpareParts.vue'),
        meta: { title: '备件管理' }
      }
    ]
  },
  {
    path: '/movements',
    name: 'MovementsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Movements',
        component: () => import('@/views/Movements.vue'),
        meta: { title: '出入库历史' }
      }
    ]
  },
  {
    path: '/scrap-inventory',
    name: 'ScrapInventoryLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'ScrapInventory',
        component: () => import('@/views/ScrapInventory.vue'),
        meta: { title: '报废库存' }
      }
    ]
  },
  {
    path: '/compliance',
    name: 'ComplianceLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Compliance',
        component: () => import('@/views/Compliance.vue'),
        meta: { title: '配置合规', permission: 'compliance:read' }
      }
    ]
  },
  // v1.2 新增路由
  {
    path: '/discovery',
    name: 'DiscoveryLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Discovery',
        component: () => import('@/views/Discovery.vue'),
        meta: { title: '设备发现', permission: 'discovery:read' }
      }
    ]
  },
  {
    path: '/tool-logs',
    name: 'ToolLogsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'ToolLogs',
        component: () => import('@/views/ToolLogs.vue'),
        meta: { title: '工具日志' }
      }
    ]
  },
  {
    path: '/alert-settings',
    redirect: '/notification-settings'
  },
  {
    path: '/system-settings',
    name: 'SystemSettingsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'SystemSettings',
        component: () => import('@/views/SystemSettings.vue'),
        meta: { title: '系统设置', permission: 'system_config:read' }
      }
    ]
  },
  {
    path: '/system-help',
    name: 'SystemHelpLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'SystemHelp',
        component: () => import('@/views/SystemHelp.vue'),
        meta: { title: '系统帮助' }
      },
      {
        path: 'dashboard',
        name: 'SystemHelpDashboard',
        component: () => import('@/views/SystemHelpDashboard.vue'),
        meta: { title: '仪表板设计说明' }
      }
    ]
  },
  // v1.3 新增路由
  {
    path: '/users',
    name: 'UsersLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Users',
        component: () => import('@/views/Users.vue'),
        meta: { title: '用户管理', permission: 'user:read' }
      }
    ]
  },
  {
    path: '/planned-maintenance',
    name: 'PlannedMaintenanceLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'PlannedMaintenance',
        component: () => import('@/views/PlannedMaintenance.vue'),
        meta: { title: '计划性运维' }
      },
      {
        path: 'tasks/:id',
        name: 'TaskDetail',
        component: () => import('@/views/TaskDetail.vue'),
        meta: { title: '任务详情' }
      }
    ]
  },
  // 3D 数字孪生监控大屏
  {
    path: '/monitor-3d',
    name: 'Monitor3DLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Monitor3D',
        component: () => import('@/views/Monitor3D.vue'),
        meta: { title: '3D 数字孪生' }
      }
    ]
  },
  // v1.5 AI增强运维 - 设备健康评分
  {
    path: '/device-health',
    name: 'DeviceHealthLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'DeviceHealth',
        component: () => import('@/views/DeviceHealth.vue'),
        meta: { title: '设备健康评分' }
      }
    ]
  },
  // v1.5 AI增强运维 - AI分析中心
  {
    path: '/ai-analysis',
    name: 'AIAnalysisLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'AIAnalysis',
        component: () => import('@/views/AIAnalysis.vue'),
        meta: { title: 'AI分析中心' }
      }
    ]
  },
  // v1.5 AI增强运维 - 工作流管理
  {
    path: '/workflows',
    name: 'WorkflowsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Workflows',
        component: () => import('@/views/Workflows.vue'),
        meta: { title: '自动化工作流' }
      }
    ]
  },
  // 扫码枪终端页面（无需Layout）
  {
    path: '/scanner',
    name: 'ScannerTerminal',
    component: () => import('@/views/ScannerTerminal.vue'),
    meta: { title: '扫码枪终端' }
  },
  // 系统通知
  {
    path: '/notifications',
    name: 'NotificationsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Notifications',
        component: () => import('@/views/Notifications.vue'),
        meta: { title: '系统通知', permission: 'notification:read' }
      }
    ]
  },
  // 通知设置（分组/排班/分发规则/升级策略）
  {
    path: '/notification-settings',
    name: 'NotificationSettingsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'NotificationSettings',
        component: () => import('@/views/NotificationSettings.vue'),
        meta: { title: '通知设置', permission: 'notification:manage' }
      }
    ]
  },
  // 角色权限
  {
    path: '/permissions',
    name: 'PermissionsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Permissions',
        component: () => import('@/views/Permissions.vue'),
        meta: { title: '角色权限', permission: 'role:read' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard - check authentication and route-level permission.
// 前端守卫是体验层兜底，后端 require_permission 才是真正的拦截：
// 权限为空/未加载时一律放行（与 Layout.vue 的 nav 过滤约定一致），
// 只在明确持有非空权限列表且缺少所需权限时才重定向回首页。
router.beforeEach(async (to, from, next) => {
  const auth = useAuthStore()

  // If route doesn't require auth and user is not logged in, allow access
  if (to.meta.noAuth) {
    // If already logged in and trying to access login page, redirect to home
    if (to.path === '/login' && auth.isLoggedIn) {
      next('/')
    } else {
      next()
    }
    return
  }

  // If route requires auth and user is not logged in, redirect to login
  if (!auth.isLoggedIn) {
    next('/login')
    return
  }

  // Route-level permission check
  const required = to.meta.permission
  if (required) {
    if (!auth.permissionsLoaded) {
      await auth.fetchMyPermissions()
    }
    // 超管（admin:all，my-permissions 只回 admin:all 不展开）或空/未加载 = 放行；
    // 只在明确持有非空权限且缺少所需权限时才重定向回首页
    if (
      auth.permissions.length > 0
      && !auth.permissions.includes('admin:all')
      && !auth.permissions.includes(required)
    ) {
      next('/')
      return
    }
  }

  next()
})

export default router
