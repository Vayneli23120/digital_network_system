import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'
import Login from '@/views/Login.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录', noAuth: true }
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
        meta: { title: 'SSH 凭证' }
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
        meta: { title: '系统日志' }
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
        meta: { title: '配置合规' }
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
        meta: { title: '设备发现' }
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
    name: 'AlertSettingsLayout',
    component: Layout,
    children: [
      {
        path: '',
        name: 'AlertSettings',
        component: () => import('@/views/AlertSettings.vue'),
        meta: { title: '告警通知' }
      }
    ]
  },
  {
    path: '/system-settings',
    name: 'SystemSettingsLayout',
    component: () => import('@/views/Layout.vue'),
    children: [
      {
        path: '',
        name: 'SystemSettings',
        component: () => import('@/views/SystemSettings.vue'),
        meta: { title: '系统设置' }
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
        meta: { title: '用户管理' }
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
        meta: { title: '系统通知' }
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
        meta: { title: '角色权限' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard - check authentication
router.beforeEach((to, from, next) => {
  const isLoggedIn = localStorage.getItem('isLoggedIn') === 'true'

  // If route doesn't require auth and user is not logged in, allow access
  if (to.meta.noAuth) {
    // If already logged in and trying to access login page, redirect to home
    if (to.path === '/login' && isLoggedIn) {
      next('/')
    } else {
      next()
    }
    return
  }

  // If route requires auth and user is not logged in, redirect to login
  if (!isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})

export default router
