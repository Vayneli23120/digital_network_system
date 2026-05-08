<template>
  <div class="app-shell">
    <!-- Topbar -->
    <header class="topbar" :class="{ dark: darkMode }">
      <div class="topbar-inner">
        <!-- Logo -->
        <div class="topbar-logo">
          <div class="logo-oval">
            <el-icon><Monitor /></el-icon>
          </div>
          <span class="logo-text">NAS</span>
        </div>

        <!-- Top Navigation -->
        <nav class="top-nav">
          <button
            v-for="tab in topTabs"
            :key="tab.key"
            :class="['tn', { active: activeTopTab === tab.key }]"
            @click="setTopTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </nav>

        <!-- Topbar Right -->
        <div class="topbar-right">
          <!-- Global Search -->
          <div class="search-wrap" :class="{ active: showSearchResults }">
            <el-icon class="search-icon"><Search /></el-icon>
            <input
              ref="searchInputRef"
              class="search-input"
              :placeholder="t('searchPlaceholder')"
              v-model="searchQuery"
              @input="handleSearch"
              @focus="showSearchResults = true"
              @keydown.escape="closeSearch"
              @keydown.enter="handleEnterKey"
            />
            <kbd class="search-kbd" @click="focusSearch">⌘K</kbd>

            <!-- Search Results Dropdown -->
            <div class="search-results" v-if="showSearchResults && hasResults">
              <div class="sr-section" v-if="searchResults.devices.length > 0">
                <div class="sr-section-label">{{ t('searchDevices') }}</div>
                <div
                  class="sr-item"
                  v-for="(device, idx) in searchResults.devices"
                  :key="device.id"
                  :class="{ selected: selectedIndex === idx }"
                  @click="goToDevice(device.id)"
                >
                  <el-icon class="sr-icon"><Connection /></el-icon>
                  <div class="sr-content">
                    <span class="sr-title">{{ device.name }}</span>
                    <span class="sr-meta">{{ device.ip }} · {{ device.status }}</span>
                  </div>
                </div>
              </div>

              <div class="sr-section" v-if="searchResults.templates.length > 0">
                <div class="sr-section-label">{{ t('searchTemplates') }}</div>
                <div
                  class="sr-item"
                  v-for="(template, idx) in searchResults.templates"
                  :key="template.id"
                  :class="{ selected: selectedIndex === searchResults.devices.length + idx }"
                  @click="goToTemplate(template.id)"
                >
                  <el-icon class="sr-icon"><Document /></el-icon>
                  <div class="sr-content">
                    <span class="sr-title">{{ template.name }}</span>
                    <span class="sr-meta">{{ template.description || t('dashNoRecords') }}</span>
                  </div>
                </div>
              </div>

              <div class="sr-section" v-if="searchResults.backups.length > 0">
                <div class="sr-section-label">{{ t('searchBackups') }}</div>
                <div
                  class="sr-item"
                  v-for="(backup, idx) in searchResults.backups.slice(0, 5)"
                  :key="backup.id"
                  :class="{ selected: selectedIndex === searchResults.devices.length + searchResults.templates.length + idx }"
                  @click="goToBackups(backup.device_name)"
                >
                  <el-icon class="sr-icon"><Download /></el-icon>
                  <div class="sr-content">
                    <span class="sr-title">{{ backup.device_name }}</span>
                    <span class="sr-meta">{{ formatDate(backup.backup_time) }} · {{ backup.has_change ? t('dashModified') : t('dashClean') }}</span>
                  </div>
                </div>
              </div>

              <div class="sr-empty" v-if="searchQuery && !hasResults && !searchLoading">
                {{ t('searchNoResults') }}
              </div>
            </div>
          </div>

          <!-- Notification -->
          <button class="icon-btn" title="通知">
            <el-icon><Bell /></el-icon>
            <span class="notif-dot" v-if="hasNotifications"></span>
          </button>

          <!-- Language Toggle -->
          <button class="icon-btn lang-btn" @click="toggleLang" :title="t('langSwitch')">
            <span class="lang-label">{{ currentLang === 'zh' ? '中' : 'EN' }}</span>
          </button>

          <!-- Theme Toggle -->
          <button class="icon-btn" @click="toggleDark" :title="darkMode ? t('themeLight') : t('themeDark')">
            <el-icon><Sunny v-if="darkMode" /><Moon v-else /></el-icon>
          </button>

          <!-- User Menu -->
          <div class="avatar-wrap" @click="showUserMenu = !showUserMenu">
            <div class="avatar">A</div>
            <div class="user-menu" v-if="showUserMenu">
              <div class="um-header">
                <div class="um-avatar">A</div>
                <div class="um-info">
                  <span class="um-name">{{ t('userAdmin') }}</span>
                  <span class="um-email">admin@nas.local</span>
                </div>
              </div>
              <div class="um-divider"></div>
              <button class="um-item"><el-icon><User /></el-icon> {{ t('userProfile') }}</button>
              <button class="um-item"><el-icon><Setting /></el-icon> {{ t('userSettings') }}</button>
              <div class="um-divider"></div>
              <button class="um-item danger"><el-icon><SwitchButton /></el-icon> {{ t('userLogout') }}</button>
            </div>
          </div>
        </div>
      </div>
      <!-- Yellow underline -->
      <div class="topbar-underline"></div>
    </header>

    <!-- Sidebar + Main -->
    <div class="layout-body">
      <!-- Sidebar -->
      <aside class="sidebar" :class="{ collapsed, dark: darkMode }">
        <div class="sidebar-inner">
          <!-- Collapse Toggle -->
          <button class="collapse-toggle" @click="collapsed = !collapsed">
            <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          </button>

          <!-- Sidebar Groups -->
          <div class="sidebar-groups">
            <div v-for="group in sidebarGroups" :key="group.label" class="sg">
              <div class="sg-label" v-show="!collapsed">{{ group.label }}</div>
              <router-link
                v-for="item in group.items"
                :key="item.path"
                :to="item.path"
                :class="['si', { active: route.path === item.path }]"
              >
                <el-icon><component :is="item.icon" /></el-icon>
                <span class="si-text" v-show="!collapsed">{{ item.text }}</span>
                <span class="si-badge" v-if="item.badge" v-show="!collapsed">{{ item.badge }}</span>
              </router-link>
            </div>
          </div>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="main-content" :class="{ dark: darkMode }">
        <router-view />
      </main>
    </div>

    <!-- Mobile Overlay -->
    <div v-if="isMobile && !collapsed" class="mobile-overlay" @click="collapsed = true" />

    <!-- Search Overlay -->
    <div class="search-overlay" v-if="showSearchResults" @click="closeSearch" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Monitor, Search, Bell, Sunny, Moon, User, Setting, SwitchButton,
  Fold, Expand, DataBoard, Connection, Download, Warning, Tools,
  Upload, Document, Key, Aim, Box, Checked, List, Delete, Calendar
} from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { useI18n } from '@/composables/useI18n'

const route = useRoute()
const router = useRouter()
const { t, currentLang, toggleLang } = useI18n()

const collapsed = ref(false)
const darkMode = ref(localStorage.getItem('darkMode') === 'true')
const isMobile = ref(window.innerWidth < 768)
const showUserMenu = ref(false)
const hasNotifications = ref(true)
const activeTopTab = ref('dashboard')

// Search state
const searchInputRef = ref(null)
const searchQuery = ref('')
const showSearchResults = ref(false)
const searchLoading = ref(false)
const selectedIndex = ref(0)
const searchResults = ref({
  devices: [],
  templates: [],
  backups: [],
})

const hasResults = computed(() => {
  return searchResults.value.devices.length > 0 ||
         searchResults.value.templates.length > 0 ||
         searchResults.value.backups.length > 0
})

const totalResults = computed(() => {
  return searchResults.value.devices.length +
         searchResults.value.templates.length +
         searchResults.value.backups.length
})

const formatDate = (dateStr) => dayjs(dateStr).format('MM-DD HH:mm')

// Search API calls
const handleSearch = async () => {
  if (!searchQuery.value.trim()) {
    searchResults.value = { devices: [], templates: [], backups: [] }
    return
  }

  searchLoading.value = true
  selectedIndex.value = 0

  try {
    const query = searchQuery.value.trim()

    // Search devices
    const devicesRes = await fetch(`/api/devices?search=${encodeURIComponent(query)}&limit=5`)
    const devicesData = await devicesRes.json()
    searchResults.value.devices = devicesData.items || []

    // Search templates
    const templatesRes = await fetch(`/api/templates`)
    const templatesData = await templatesRes.json()
    const allTemplates = templatesData.items || templatesData || []
    searchResults.value.templates = allTemplates
      .filter(t => t.name?.toLowerCase().includes(query.toLowerCase()) ||
                   t.description?.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 5)

    // Search backups
    const backupsRes = await fetch(`/api/backups?limit=20`)
    const backupsData = await backupsRes.json()
    const allBackups = backupsData.items || backupsData.backups || []
    searchResults.value.backups = allBackups
      .filter(b => b.device_name?.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 5)

  } catch (err) {
    console.error('Search failed:', err)
  }

  searchLoading.value = false
}

const focusSearch = () => {
  searchInputRef.value?.focus()
  showSearchResults.value = true
}

const closeSearch = () => {
  showSearchResults.value = false
  searchQuery.value = ''
  searchResults.value = { devices: [], templates: [], backups: [] }
}

const handleEnterKey = () => {
  if (totalResults.value === 0) return

  const allItems = [
    ...searchResults.value.devices.map(d => ({ type: 'device', id: d.id })),
    ...searchResults.value.templates.map(t => ({ type: 'template', id: t.id })),
    ...searchResults.value.backups.map(b => ({ type: 'backup', device_name: b.device_name })),
  ]

  if (selectedIndex.value < allItems.length) {
    const item = allItems[selectedIndex.value]
    if (item.type === 'device') {
      goToDevice(item.id)
    } else if (item.type === 'template') {
      goToTemplate(item.id)
    } else if (item.type === 'backup') {
      goToBackups(item.device_name)
    }
  }
}

const goToDevice = (id) => {
  closeSearch()
  router.push(`/devices/${id}`)
}

const goToTemplate = (id) => {
  closeSearch()
  router.push(`/templates`)
  ElMessage.info(`模板 ID: ${id}`)
}

const goToBackups = (deviceName) => {
  closeSearch()
  router.push(`/backups`)
}

// Keyboard navigation for search
const handleKeyDown = (e) => {
  // Cmd/Ctrl + K to open search
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    focusSearch()
  }

  // Arrow keys for navigation when search is open
  if (showSearchResults.value) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, totalResults.value - 1)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, 0)
    }
  }
}

// Top navigation tabs
const topTabs = computed(() => [
  { key: 'dashboard', label: t('navDashboard') },
  { key: 'devices', label: t('navDevices') },
  { key: 'config', label: t('navConfig') },
  { key: 'spare', label: t('navSpare') },
  { key: 'system', label: t('navSystem') },
])

// Fault badge - 未处理的故障数量
const faultBadge = ref(0)

const loadFaultBadge = async () => {
  try {
    const res = await fetch('/api/faults?status=open&status=investigating&limit=100')
    const data = await res.json()
    // 计算待处理和处理中的故障总数
    faultBadge.value = data.items?.filter(f => f.status === 'open' || f.status === 'investigating').length || 0
  } catch (err) {
    console.error('Failed to load fault badge:', err)
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
  if (path === '/' || path.startsWith('/dashboard') || path.startsWith('/monitor-screen')) {
    activeTopTab.value = 'dashboard'
  } else if (path.startsWith('/devices') || path.startsWith('/discovery') || path.startsWith('/backups') || path.startsWith('/faults') || path.startsWith('/maintenance') || path.startsWith('/planned-maintenance')) {
    activeTopTab.value = 'devices'
  } else if (path.startsWith('/console') || path.startsWith('/deploy') || path.startsWith('/templates') || path.startsWith('/credentials') || path.startsWith('/compliance') || path.startsWith('/tool-logs')) {
    activeTopTab.value = 'config'
  } else if (path.startsWith('/spare') || path.startsWith('/scrap')) {
    activeTopTab.value = 'spare'
  } else if (path.startsWith('/logs') || path.startsWith('/alert-settings') || path.startsWith('/users')) {
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
  // 触发全局事件让 Dashboard 刷新图表
  window.dispatchEvent(new CustomEvent('theme-change', { detail: { dark: darkMode.value } }))
}

const handleResize = () => {
  isMobile.value = window.innerWidth < 768
  if (isMobile.value) {
    collapsed.value = true
  }
}

// Close user menu on outside click
const handleOutsideClick = (e) => {
  if (!e.target.closest('.avatar-wrap')) {
    showUserMenu.value = false
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  document.addEventListener('click', handleOutsideClick)
  document.addEventListener('keydown', handleKeyDown)
  window.addEventListener('fault-status-change', loadFaultBadge)
  handleResize()
  // 检查 localStorage 中是否保存了暗黑模式偏好
  if (darkMode.value) {
    document.documentElement.classList.add('dark')
  }
  // 加载故障badge
  loadFaultBadge()
  // 每30秒更新一次
  setInterval(loadFaultBadge, 30000)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('click', handleOutsideClick)
  document.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('fault-status-change', loadFaultBadge)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('click', handleOutsideClick)
  document.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
/* ===== App Shell ===== */
.app-shell {
  min-height: 100vh;
  background: var(--bg-primary);
}

/* ===== Topbar ===== */
.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--layout-topbar-h);
  background: var(--topbar-bg);
  border-bottom: 1px solid var(--border-default);
  z-index: 1000;
}

/* 明亮模式：Goodyear 风格 - 深蓝背景 + 黄色下划线 */
.topbar:not(.dark) {
  background: linear-gradient(135deg, #003087 0%, #001F5C 100%);
  border-bottom: none;
}

.topbar:not(.dark)::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: #f6b93b;
}

/* 暗黑模式：科技风格 - 深灰背景 */
.topbar.dark {
  background: var(--bg-secondary);
}

.topbar-inner {
  height: 100%;
  padding: 0 var(--layout-page-pad);
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
}

/* Logo */
.topbar-logo {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.logo-oval {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 明亮模式：黄色 Logo */
.topbar:not(.dark) .logo-oval {
  background: #f6b93b;
  color: #001F5C;
}

/* 暗黑模式：科技渐变 Logo */
.topbar.dark .logo-oval {
  background: linear-gradient(135deg, #00b894, #0984e3);
  color: #fff;
}

.logo-oval .el-icon {
  font-size: 18px;
}

.logo-text {
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

/* 明亮模式：黄色文字 */
.topbar:not(.dark) .logo-text {
  color: #f6b93b;
}

/* 暗黑模式：白色文字 */
.topbar.dark .logo-text {
  color: var(--text-primary);
}

/* Top Navigation */
.top-nav {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  margin-left: var(--gap-lg);
}

.tn {
  padding: 6px 12px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

/* 明亮模式导航按钮 */
.topbar:not(.dark) .tn {
  color: rgba(255, 255, 255, 0.75);
}

.topbar:not(.dark) .tn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.topbar:not(.dark) .tn.active {
  color: #001F5C;
  background: #f6b93b;
}

/* 暗黑模式导航按钮 */
.topbar.dark .tn {
  color: var(--text-tertiary);
}

.topbar.dark .tn:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.topbar.dark .tn.active {
  color: #00b894;
  background: rgba(0, 212, 170, 0.1);
}

/* Topbar Right */
.topbar-right {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--gap-sm);
}

/* Search */
.search-wrap {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 6px 12px;
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  transition: all 0.2s;
  width: 240px;
  position: relative;
}

/* 明亮模式搜索框 */
.topbar:not(.dark) .search-wrap {
  background: rgba(255, 255, 255, 0.12);
}

.topbar:not(.dark) .search-wrap:focus-within,
.topbar:not(.dark) .search-wrap.active {
  border-color: #f6b93b;
  background: rgba(255, 255, 255, 0.18);
  box-shadow: 0 0 0 3px rgba(255, 204, 0, 0.2);
}

.topbar:not(.dark) .search-icon {
  color: rgba(255, 255, 255, 0.6);
}

.topbar:not(.dark) .search-input {
  color: #fff;
}

.topbar:not(.dark) .search-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.topbar:not(.dark) .search-kbd {
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.1);
}

/* 暗黑模式搜索框 */
.topbar.dark .search-wrap {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.topbar.dark .search-wrap:focus-within,
.topbar.dark .search-wrap.active {
  border-color: #00b894;
  box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.15);
}

.topbar.dark .search-icon {
  color: var(--text-tertiary);
}

.topbar.dark .search-input {
  color: var(--text-primary);
}

.topbar.dark .search-input::placeholder {
  color: var(--text-muted);
}

.topbar.dark .search-kbd {
  color: var(--text-muted);
  background: var(--bg-hover);
}

.search-icon {
  font-size: 14px;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  font-size: 13px;
  outline: none;
}

.search-kbd {
  padding: 2px 6px;
  font-family: var(--font-display);
  font-size: 10px;
  border-radius: 4px;
  cursor: pointer;
}

/* Search Results Dropdown */
.search-results {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  max-height: 400px;
  overflow-y: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
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

.sr-section {
  padding: 8px 0;
}

.sr-section:not(:last-child) {
  border-bottom: 1px solid var(--border-subtle);
}

.sr-section-label {
  padding: 6px 16px;
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.sr-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
}

.sr-item:hover,
.sr-item.selected {
  background: var(--bg-hover);
}

.sr-icon {
  font-size: 16px;
  color: var(--accent-secondary);
}

.sr-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sr-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.sr-meta {
  font-size: 12px;
  font-family: var(--font-display);
  color: var(--text-tertiary);
}

.sr-empty {
  padding: 20px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary);
}

/* Icon Button */
.icon-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  border: 1px solid transparent;
}

/* Language Button */
.lang-btn {
  width: auto;
  padding: 0 10px;
  min-width: 40px;
}

.lang-label {
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 600;
}

/* 明亮模式按钮 */
.topbar:not(.dark) .icon-btn {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.75);
}

.topbar:not(.dark) .icon-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  color: #fff;
}

/* 暗黑模式按钮 */
.topbar.dark .icon-btn {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
  color: var(--text-secondary);
}

.topbar.dark .icon-btn:hover {
  background: var(--bg-hover);
  border-color: #00b894;
  color: #00b894;
}

.icon-btn .el-icon {
  font-size: 16px;
}

.notif-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 8px;
  height: 8px;
  background: var(--accent-danger);
  border-radius: 50%;
}

/* Avatar / User Menu */
.avatar-wrap {
  position: relative;
  cursor: pointer;
}

.avatar {
  width: 32px;
  height: 32px;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 明亮模式头像 */
.topbar:not(.dark) .avatar {
  background: #f6b93b;
  color: #001F5C;
}

/* 暗黑模式头像 */
.topbar.dark .avatar {
  background: linear-gradient(135deg, #00b894, #0984e3);
  color: #fff;
}

.user-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 200px;
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-elevated);
  border: 1px solid var(--border-default);
  overflow: hidden;
}

.um-header {
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-tertiary);
}

.um-avatar {
  width: 36px;
  height: 36px;
  font-family: var(--font-display);
  font-size: 14px;
  font-weight: 600;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #00b894, #0984e3);
  color: #fff;
}

.um-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.um-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.um-email {
  font-size: 11px;
  font-family: var(--font-display);
  color: var(--text-tertiary);
}

.um-divider {
  height: 1px;
  background: var(--border-subtle);
}

.um-item {
  width: 100%;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: background 0.15s;
}

.um-item:hover {
  background: var(--bg-hover);
}

.um-item .el-icon {
  font-size: 14px;
  color: var(--text-tertiary);
}

.um-item.danger {
  color: var(--accent-danger);
}

.um-item.danger .el-icon {
  color: var(--accent-danger);
}

/* ===== Layout Body ===== */
.layout-body {
  display: flex;
  margin-top: var(--layout-topbar-h);
  min-height: calc(100vh - var(--layout-topbar-h));
}

/* ===== Sidebar ===== */
.sidebar {
  width: var(--layout-sidebar-w);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-default);
  position: sticky;
  top: var(--layout-topbar-h);
  height: calc(100vh - var(--layout-topbar-h));
  overflow-y: auto;
  overflow-x: hidden;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 64px;
}

.sidebar-inner {
  padding: var(--gap-sm);
}

/* Collapse Toggle */
.collapse-toggle {
  width: 100%;
  height: 36px;
  margin-bottom: var(--gap-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.2s;
}

.collapse-toggle:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
}

.collapse-toggle .el-icon {
  font-size: 16px;
}

/* Sidebar Groups */
.sidebar-groups {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.sg {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.sg-label {
  padding: 6px 12px;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Sidebar Item */
.si {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.15s;
  position: relative;
}

.si:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.si.active {
  background: var(--sidebar-active-bg);
  border-left: 2px solid var(--sidebar-active-border);
  padding-left: 10px;
}

/* 明亮模式激活项 */
.sidebar:not(.dark) .si.active {
  color: var(--color-gb);
}

/* 暗黑模式激活项 */
.sidebar.dark .si.active {
  color: #00b894;
}

.si .el-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.si-text {
  font-size: 13px;
  font-weight: 400;
  white-space: nowrap;
}

.si.active .si-text {
  font-weight: 500;
}

.si-badge {
  padding: 2px 6px;
  font-family: var(--font-display);
  font-size: 10px;
  font-weight: 600;
  color: #fff;
  background: var(--accent-danger);
  border-radius: var(--radius-sm);
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

@media (max-width: 768px) {
  .topbar-inner {
    padding: 0 12px;
  }

  .search-wrap {
    width: 140px;
  }

  .search-kbd {
    display: none;
  }

  .sidebar {
    position: fixed;
    left: 0;
    top: var(--layout-topbar-h);
    bottom: 0;
    z-index: 1000;
    transform: translateX(0);
  }

  .sidebar.collapsed {
    transform: translateX(-100%);
  }

  .main-content {
    padding: 16px;
  }
}

@media (max-width: 576px) {
  .top-nav {
    display: none;
  }

  .logo-text {
    display: none;
  }
}
</style>