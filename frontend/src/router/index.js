import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/views/Layout.vue'

const routes = [
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
