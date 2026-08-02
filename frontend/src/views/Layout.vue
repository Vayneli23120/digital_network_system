<template>
  <div class="app-shell">
    <!-- Topbar -->
    <Topbar
      :dark-mode="darkMode"
      :active-top-tab="activeTopTab"
      :current-lang="currentLang"
      :unread-count="unreadNotifCount"
      :visible-tabs="visibleTopTabs"
      :logo-text="t('logoText')"
      :dashboard-label="t('navDashboard')"
      :devices-label="t('navDevices')"
      :config-label="t('navConfig')"
      :spare-label="t('navSpare')"
      :system-label="t('navSystem')"
      :search-placeholder="t('searchPlaceholder')"
      :search-devices-label="t('searchDevices')"
      :search-templates-label="t('searchTemplates')"
      :search-backups-label="t('searchBackups')"
      :search-no-results-label="t('searchNoResults')"
      :dash-no-records-label="t('dashNoRecords')"
      :dash-modified-label="t('dashModified')"
      :dash-clean-label="t('dashClean')"
      :notif-title="t('notifTitle')"
      :lang-switch-title="t('langSwitch')"
      :theme-light-title="t('themeLight')"
      :theme-dark-title="t('themeDark')"
      :user-name="currentUser"
      :profile-label="t('userProfile')"
      :settings-label="t('userSettings')"
      :logout-label="t('userLogout')"
      @set-top-tab="setTopTab"
      @toggle-dark="toggleDark"
      @toggle-lang="toggleLang"
    />

    <!-- Sidebar + Main -->
    <div class="layout-body">
      <!-- Sidebar -->
      <Sidebar
        :collapsed="collapsed"
        :dark-mode="darkMode"
        :sidebar-groups="sidebarGroups"
        @toggle-collapse="collapsed = !collapsed"
      />

      <!-- Main Content -->
      <main class="main-content" :class="{ dark: darkMode }">
        <router-view />
      </main>
    </div>

    <!-- Mobile Overlay -->
    <div v-if="isMobile && !collapsed" class="mobile-overlay" @click="collapsed = true" />

    <!-- Search Overlay -->
    <div class="search-overlay" v-if="showSearchOverlay" @click="closeSearchOverlay" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataBoard, Connection, Download, Warning, Tools, Upload, Document, Key, Aim, Box, Checked, List, Delete, Calendar, Bell, User, Cpu, TrendCharts, Operation, Sort, Lock, Odometer, VideoPlay, Setting, QuestionFilled } from '@element-plus/icons-vue'
import Topbar from './layout/Topbar.vue'
import Sidebar from './layout/Sidebar.vue'
import { useI18n } from '@/composables/useI18n'
import { getFaults, getUnreadCount, getMyPermissions } from '@/api'
import { cachedRequest } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const route = useRoute()
const router = useRouter()
const { t, currentLang, toggleLang } = useI18n()

// State
const collapsed = ref(false)
const darkMode = ref(localStorage.getItem('darkMode') === 'true')
const isMobile = ref(window.innerWidth < 768)
const unreadNotifCount = ref(0)
const currentUser = ref(localStorage.getItem('currentUser') || 'Admin')
const activeTopTab = ref('dashboard')
const showSearchOverlay = ref(false)
const faultTimerId = ref(null)
const notifTimerId = ref(null)

// Fault badge - count of unprocessed faults
const faultBadge = ref(0)

const loadFaultBadge = debounce(async (force = false) => {
  try {
    const res = await cachedRequest(
      () => getFaults({ limit: 500 }),
      'layout_fault_badge',
      {},
      { forceRefresh: force, ttl: 60 }
    )
    faultBadge.value = res.items?.filter(f => f.status !== 'closed').length || 0
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load fault badge:', err)
    }
  }
}, 300)

// Notification unread count
const loadUnreadNotifCount = debounce(async (force = false) => {
  try {
    const res = await cachedRequest(
      () => getUnreadCount(),
      'layout_unread_count',
      {},
      { forceRefresh: force, ttl: 30 }
    )
    unreadNotifCount.value = res.unread_count || 0
  } catch (err) {
    if (err.name !== 'CanceledError') {
      console.error('Failed to load notification count:', err)
    }
  }
}, 300)

// User permissions for nav filtering (null = not loaded / show all)
const userPermissions = ref(null)

// Nav visibility governance is only active when the current user actually
// carries at least one nav_* permission.
// A user with zero nav_* permissions is treated as "not governed by nav
// permissions" (show everything) instead of "denied everything", so that:
//   - a permission table that has not been (re)initialised with nav_* records
//   - a role saved without any nav selection
// can never lock a user out of the entire UI. Real access control must be
// enforced by the backend, not by hiding menu entries.
const navFilterActive = computed(() => {
  const perms = userPermissions.value
  if (!perms || perms.includes('admin:all')) return false
  return perms.some(p => typeof p === 'string' && p.startsWith('nav_'))
})

// Sidebar groups (organized by domain - no overlap)
const sidebarData = computed(() => {
  const groups = {
    dashboard: [
      {
        key: 'overview',
        label: t('groupOverview'),
        items: [
          { path: '/', text: t('menuDashboard'), icon: DataBoard, permission: 'nav_overview:dashboard' },
          { path: '/operations', text: t('menuOperations'), icon: Odometer, permission: 'nav_overview:operations' },
          { path: '/monitor-3d', text: t('menuMonitor3D'), icon: VideoPlay, permission: 'nav_overview:monitor_3d' },
          { path: '/device-health', text: t('menuDeviceHealth'), icon: TrendCharts, permission: 'nav_overview:device_health' },
          { path: '/ai-analysis', text: t('menuAIAnalysis'), icon: Cpu, permission: 'nav_overview:ai_analysis' },
          { path: '/workflows', text: t('menuWorkflows'), icon: Operation, permission: 'workflow:read' },
        ]
      }
    ],
    devices: [
      {
        key: 'device-manage',
        label: t('groupDeviceManage'),
        items: [
          { path: '/devices', text: t('menuDevices'), icon: Connection, permission: 'nav_devices:list' },
          { path: '/discovery', text: t('menuDiscovery'), icon: Aim, permission: 'nav_devices:discovery' },
          { path: '/backups', text: t('menuBackups'), icon: Download, permission: 'backup:read' },
          { path: '/faults', text: t('menuFaults'), icon: Warning, badge: faultBadge.value > 0 ? faultBadge.value : null, permission: 'fault:read' },
          { path: '/maintenance', text: t('menuMaintenance'), icon: Tools, permission: 'maintenance:read' },
          { path: '/planned-maintenance', text: t('menuPlannedMaintenance'), icon: Calendar, permission: 'planned_task:read' },
        ]
      },
    ],
    config: [
      {
        key: 'config-manage',
        label: t('groupConfigManage'),
        items: [
          { path: '/console', text: t('menuConsole'), icon: Connection, permission: 'nav_config:console' },
          { path: '/deploy', text: t('menuDeploy'), icon: Upload, permission: 'nav_config:deploy' },
          { path: '/templates', text: t('menuTemplates'), icon: Document, permission: 'template:read' },
          { path: '/credentials', text: t('menuCredentials'), icon: Key, permission: 'nav_config:credentials' },
          { path: '/compliance', text: t('menuCompliance'), icon: Checked, permission: 'nav_config:compliance' },
          { path: '/tool-logs', text: t('menuToolLogs'), icon: List, permission: 'nav_config:tool_logs' },
        ]
      },
    ],
    spare: [
      {
        key: 'spare-parts',
        label: t('groupSpare'),
        items: [
          { path: '/spare-parts', text: t('menuSpareParts'), icon: Box, permission: 'nav_spare:spare_parts' },
          { path: '/movements', text: t('menuMovements'), icon: Sort, permission: 'nav_spare:movements' },
          { path: '/scrap-inventory', text: t('menuScrapInventory'), icon: Delete, permission: 'nav_spare:scrap_inventory' },
        ]
      },
    ],
    system: [
      {
        key: 'system',
        label: t('groupSystem'),
        items: [
          { path: '/notifications', text: t('menuNotifications'), icon: Bell, permission: 'nav_system:notifications' },
          { path: '/logs', text: t('menuLogs'), icon: Document, permission: 'log:read' },
          { path: '/alert-settings', text: t('menuAlertSettings'), icon: Bell, permission: 'alert:manage' },
          { path: '/system-settings', text: t('menuSystemSettings'), icon: Setting, permission: 'system_config:read' },
          { path: '/system-help', text: t('menuSystemHelp'), icon: QuestionFilled, permission: 'nav_system:system_help' },
          { path: '/users', text: t('menuUsers'), icon: User, permission: 'user:read' },
          { path: '/permissions', text: t('menuPermissions'), icon: Lock, permission: 'nav_system:permissions' },
        ]
      },
    ],
  }

  // Apply permission filtering only when nav governance is active
  const perms = userPermissions.value
  if (navFilterActive.value) {
    for (const tabKey of Object.keys(groups)) {
      for (const group of groups[tabKey]) {
        group.items = group.items.filter(item => !item.permission || perms.includes(item.permission))
      }
      groups[tabKey] = groups[tabKey].filter(g => g.items.length > 0)
    }
  }

  return groups
})

const sidebarGroups = computed(() => {
  return sidebarData.value[activeTopTab.value] || []
})

const visibleTopTabs = computed(() => {
  return Object.entries(sidebarData.value)
    .filter(([, groups]) => groups.length > 0)
    .map(([key]) => key)
})

// Sync top tab based on current route
watch(route, (newRoute) => {
  const path = newRoute.path
  if (path === '/' || path.startsWith('/dashboard') || path.startsWith('/monitor-3d') || path.startsWith('/device-health') || path.startsWith('/ai-analysis') || path.startsWith('/workflows')) {
    activeTopTab.value = 'dashboard'
  } else if (path.startsWith('/devices') || path.startsWith('/discovery') || path.startsWith('/backups') || path.startsWith('/faults') || path.startsWith('/maintenance') || path.startsWith('/planned-maintenance')) {
    activeTopTab.value = 'devices'
  } else if (path.startsWith('/console') || path.startsWith('/deploy') || path.startsWith('/templates') || path.startsWith('/credentials') || path.startsWith('/compliance') || path.startsWith('/tool-logs')) {
    activeTopTab.value = 'config'
  } else if (path.startsWith('/spare') || path.startsWith('/scrap') || path.startsWith('/movements')) {
    activeTopTab.value = 'spare'
  } else if (path.startsWith('/logs') || path.startsWith('/alert-settings') || path.startsWith('/system-settings') || path.startsWith('/system-help') || path.startsWith('/users') || path.startsWith('/permissions') || path.startsWith('/notifications')) {
    activeTopTab.value = 'system'
  }
}, { immediate: true })

const setTopTab = (key) => {
  activeTopTab.value = key
  const groups = sidebarGroups.value
  if (groups.length > 0 && groups[0].items.length > 0) {
    router.push(groups[0].items[0].path)
  }
}

const toggleDark = () => {
  darkMode.value = !darkMode.value
  localStorage.setItem('darkMode', darkMode.value)
  if (darkMode.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
  // Trigger global event for Dashboard to refresh charts
  window.dispatchEvent(new CustomEvent('theme-change', { detail: { dark: darkMode.value } }))
}

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    collapsed.value = true
  }
}

const closeSearchOverlay = () => {
  showSearchOverlay.value = false
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  window.addEventListener('fault-status-change', loadFaultBadge)
  handleResize()
  // Check localStorage for dark mode preference
  if (darkMode.value) {
    document.documentElement.classList.add('dark')
  }
  // Load user permissions for nav filtering
  getMyPermissions().then(data => {
    userPermissions.value = data.permissions || []
    if (!navFilterActive.value) return

    // Safety net: the user carries nav_* permissions but none of them matches a
    // known menu entry (stale/renamed permissions). Rather than rendering an
    // empty shell with no way out, fall back to showing everything.
    if (visibleTopTabs.value.length === 0) {
      console.warn('[Layout] nav permissions matched no menu entry, nav filtering disabled')
      userPermissions.value = null
      return
    }

    // If the current active tab is not visible, redirect to the first visible one
    if (!visibleTopTabs.value.includes(activeTopTab.value)) {
      activeTopTab.value = visibleTopTabs.value[0]
      const groups = sidebarGroups.value
      if (groups.length > 0 && groups[0].items.length > 0) {
        router.push(groups[0].items[0].path)
      }
    }
  }).catch(() => {
    // On error, show all (userPermissions stays null)
  })
  // Load fault badge
  loadFaultBadge()
  // Load notification unread count
  loadUnreadNotifCount()
  // Update every 30 seconds - store timer IDs for cleanup
  faultTimerId.value = setInterval(loadFaultBadge, 30000)
  notifTimerId.value = setInterval(loadUnreadNotifCount, 30000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('fault-status-change', loadFaultBadge)
  // Clear timers to prevent memory leaks and continued requests
  if (faultTimerId.value) clearInterval(faultTimerId.value)
  if (notifTimerId.value) clearInterval(notifTimerId.value)
})
</script>

<style scoped>
/* ===== App Shell ===== */
.app-shell {
  min-height: 100vh;
  background: var(--bg-primary);
}

/* ===== Layout Body ===== */
.layout-body {
  display: flex;
  margin-top: var(--layout-topbar-h);
  min-height: calc(100vh - var(--layout-topbar-h));
}

/* ===== Main Content ===== */
.main-content {
  flex: 1;
  min-width: 0;
  padding: var(--layout-page-pad);
  background: var(--bg-primary);
}

/* ===== Mobile ===== */
.mobile-overlay {
  position: fixed;
  top: var(--layout-topbar-h);
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
}

.search-overlay {
  position: fixed;
  top: var(--layout-topbar-h);
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
}

@media (max-width: 768px) {
  .main-content {
    padding: 16px;
  }
}
</style>