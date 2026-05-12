<template>
  <div class="app-shell">
    <!-- Topbar -->
    <Topbar
      :dark-mode="darkMode"
      :active-top-tab="activeTopTab"
      :current-lang="currentLang"
      :unread-count="unreadNotifCount"
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
import { DataBoard, Connection, Download, Warning, Tools, Upload, Document, Key, Aim, Box, Checked, List, Delete, Calendar, Bell, User, Monitor, Cpu, TrendCharts, Operation } from '@element-plus/icons-vue'
import Topbar from './layout/Topbar.vue'
import Sidebar from './layout/Sidebar.vue'
import { useI18n } from '@/composables/useI18n'
import { getUnreadCount } from '@/api'

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

// Fault badge - count of unprocessed faults
const faultBadge = ref(0)

const loadFaultBadge = async () => {
  try {
    const res = await fetch('/api/faults?status=open&status=investigating&limit=100')
    const data = await res.json()
    faultBadge.value = data.items?.filter(f => f.status === 'open' || f.status === 'investigating').length || 0
  } catch (err) {
    console.error('Failed to load fault badge:', err)
  }
}

// Notification unread count
const loadUnreadNotifCount = async () => {
  try {
    const res = await getUnreadCount()
    unreadNotifCount.value = res.unread_count || 0
  } catch (err) {
    console.error('Failed to load notification count:', err)
  }
}

// Sidebar groups (organized by domain - no overlap)
const sidebarGroups = computed(() => {
  const groups = {
    dashboard: [
      {
        label: t('groupOverview'),
        items: [
          { path: '/', text: t('menuDashboard'), icon: DataBoard },
          { path: '/monitor-screen', text: t('menuMonitorScreen'), icon: Monitor },
          { path: '/device-health', text: t('menuDeviceHealth') || '设备健康', icon: TrendCharts },
          { path: '/ai-analysis', text: t('menuAIAnalysis') || 'AI分析中心', icon: Cpu },
          { path: '/workflows', text: t('menuWorkflows') || '自动化工作流', icon: Operation },
        ]
      }
    ],
    devices: [
      {
        label: t('groupDeviceManage'),
        items: [
          { path: '/devices', text: t('menuDevices'), icon: Connection },
          { path: '/discovery', text: t('menuDiscovery'), icon: Aim },
          { path: '/backups', text: t('menuBackups'), icon: Download },
          { path: '/faults', text: t('menuFaults'), icon: Warning, badge: faultBadge.value > 0 ? faultBadge.value : null },
          { path: '/maintenance', text: t('menuMaintenance'), icon: Tools },
          { path: '/planned-maintenance', text: t('menuPlannedMaintenance'), icon: Calendar },
        ]
      },
    ],
    config: [
      {
        label: t('groupConfigManage'),
        items: [
          { path: '/console', text: t('menuConsole'), icon: Connection },
          { path: '/deploy', text: t('menuDeploy'), icon: Upload },
          { path: '/templates', text: t('menuTemplates'), icon: Document },
          { path: '/credentials', text: t('menuCredentials'), icon: Key },
          { path: '/compliance', text: t('menuCompliance'), icon: Checked },
          { path: '/tool-logs', text: t('menuToolLogs'), icon: List },
        ]
      },
    ],
    spare: [
      {
        label: t('groupSpare'),
        items: [
          { path: '/spare-parts', text: t('menuSpareParts'), icon: Box },
          { path: '/scrap-inventory', text: t('menuScrapInventory'), icon: Delete },
        ]
      },
    ],
    system: [
      {
        label: t('groupSystem'),
        items: [
          { path: '/notifications', text: t('menuNotifications') || '通知中心', icon: Bell },
          { path: '/logs', text: t('menuLogs'), icon: Document },
          { path: '/alert-settings', text: t('menuAlertSettings'), icon: Bell },
          { path: '/users', text: t('menuUsers'), icon: User },
        ]
      },
    ],
  }
  return groups[activeTopTab.value] || groups.dashboard
})

// Sync top tab based on current route
watch(route, (newRoute) => {
  const path = newRoute.path
  if (path === '/' || path.startsWith('/dashboard') || path.startsWith('/monitor-screen') || path.startsWith('/device-health') || path.startsWith('/ai-analysis') || path.startsWith('/workflows')) {
    activeTopTab.value = 'dashboard'
  } else if (path.startsWith('/devices') || path.startsWith('/discovery') || path.startsWith('/backups') || path.startsWith('/faults') || path.startsWith('/maintenance') || path.startsWith('/planned-maintenance')) {
    activeTopTab.value = 'devices'
  } else if (path.startsWith('/console') || path.startsWith('/deploy') || path.startsWith('/templates') || path.startsWith('/credentials') || path.startsWith('/compliance') || path.startsWith('/tool-logs')) {
    activeTopTab.value = 'config'
  } else if (path.startsWith('/spare') || path.startsWith('/scrap')) {
    activeTopTab.value = 'spare'
  } else if (path.startsWith('/logs') || path.startsWith('/alert-settings') || path.startsWith('/users') || path.startsWith('/notifications')) {
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
  // Load fault badge
  loadFaultBadge()
  // Load notification unread count
  loadUnreadNotifCount()
  // Update every 30 seconds
  setInterval(loadFaultBadge, 30000)
  setInterval(loadUnreadNotifCount, 30000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  window.removeEventListener('fault-status-change', loadFaultBadge)
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