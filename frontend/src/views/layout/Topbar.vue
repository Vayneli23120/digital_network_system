<template>
  <header class="topbar" :class="{ dark: darkMode }">
    <div class="topbar-inner">
      <!-- Logo -->
      <div class="topbar-logo">
        <div class="logo-oval" :class="{ dark: darkMode }">
          <el-icon><Monitor /></el-icon>
        </div>
        <span class="logo-text" :class="{ dark: darkMode }">{{ logoText }}</span>
      </div>

      <!-- Top Navigation -->
      <nav class="top-nav">
        <button
          v-for="tab in topTabs"
          :key="tab.key"
          :class="['tn', { active: activeTopTab === tab.key, dark: darkMode }]"
          @click="setTopTab(tab.key)"
        >
          {{ tab.label }}
        </button>
      </nav>

      <!-- Topbar Right -->
      <div class="topbar-right">
        <!-- Global Search -->
        <SearchDropdown
          ref="searchDropdownRef"
          :placeholder="searchPlaceholder"
          :devices-label="searchDevicesLabel"
          :templates-label="searchTemplatesLabel"
          :backups-label="searchBackupsLabel"
          :no-results-label="searchNoResultsLabel"
          :no-records-label="dashNoRecordsLabel"
          :modified-label="dashModifiedLabel"
          :clean-label="dashCleanLabel"
          :class="{ dark: darkMode }"
          @close="closeSearchOverlay"
        />

        <!-- Notification -->
        <button class="icon-btn" :class="{ dark: darkMode }" :title="notifTitle">
          <el-icon><Bell /></el-icon>
          <span class="notif-dot" v-if="hasNotifications"></span>
        </button>

        <!-- Language Toggle -->
        <button class="icon-btn lang-btn" :class="{ dark: darkMode }" @click="toggleLang" :title="langSwitchTitle">
          <span class="lang-label">{{ currentLang === 'zh' ? '中' : 'EN' }}</span>
        </button>

        <!-- Theme Toggle -->
        <button class="icon-btn" :class="{ dark: darkMode }" @click="toggleDark" :title="darkMode ? themeLightTitle : themeDarkTitle">
          <el-icon><Sunny v-if="darkMode" /><Moon v-else /></el-icon>
        </button>

        <!-- User Menu -->
        <UserMenu
          :dark-mode="darkMode"
          :user-name="userName"
          :user-email="userEmail"
          :profile-label="profileLabel"
          :settings-label="settingsLabel"
          :logout-label="logoutLabel"
        />
      </div>
    </div>
    <!-- Yellow underline (light mode only) -->
    <div class="topbar-underline" v-if="!darkMode"></div>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Monitor, Bell, Sunny, Moon } from '@element-plus/icons-vue'
import SearchDropdown from './SearchDropdown.vue'
import UserMenu from './UserMenu.vue'

const props = defineProps({
  darkMode: {
    type: Boolean,
    default: false
  },
  activeTopTab: {
    type: String,
    default: 'dashboard'
  },
  currentLang: {
    type: String,
    default: 'zh'
  },
  hasNotifications: {
    type: Boolean,
    default: true
  },
  // Navigation Labels
  dashboardLabel: {
    type: String,
    default: 'Dashboard'
  },
  devicesLabel: {
    type: String,
    default: 'Devices'
  },
  configLabel: {
    type: String,
    default: 'Config'
  },
  spareLabel: {
    type: String,
    default: 'Spare'
  },
  systemLabel: {
    type: String,
    default: 'System'
  },
  // Labels
  logoText: {
    type: String,
    default: 'NAS'
  },
  searchPlaceholder: {
    type: String,
    default: 'Search...'
  },
  searchDevicesLabel: {
    type: String,
    default: 'Devices'
  },
  searchTemplatesLabel: {
    type: String,
    default: 'Templates'
  },
  searchBackupsLabel: {
    type: String,
    default: 'Backups'
  },
  searchNoResultsLabel: {
    type: String,
    default: 'No results found'
  },
  dashNoRecordsLabel: {
    type: String,
    default: 'No records'
  },
  dashModifiedLabel: {
    type: String,
    default: 'Modified'
  },
  dashCleanLabel: {
    type: String,
    default: 'Clean'
  },
  notifTitle: {
    type: String,
    default: 'Notifications'
  },
  langSwitchTitle: {
    type: String,
    default: 'Switch Language'
  },
  themeLightTitle: {
    type: String,
    default: 'Light Mode'
  },
  themeDarkTitle: {
    type: String,
    default: 'Dark Mode'
  },
  userName: {
    type: String,
    default: 'Admin'
  },
  userEmail: {
    type: String,
    default: 'admin@nas.local'
  },
  profileLabel: {
    type: String,
    default: 'Profile'
  },
  settingsLabel: {
    type: String,
    default: 'Settings'
  },
  logoutLabel: {
    type: String,
    default: 'Logout'
  }
})

const emit = defineEmits(['setTopTab', 'toggleDark', 'toggleLang'])

const router = useRouter()
const searchDropdownRef = ref(null)

const topTabs = computed(() => [
  { key: 'dashboard', label: props.dashboardLabel || 'Dashboard' },
  { key: 'devices', label: props.devicesLabel || 'Devices' },
  { key: 'config', label: props.configLabel || 'Config' },
  { key: 'spare', label: props.spareLabel || 'Spare' },
  { key: 'system', label: props.systemLabel || 'System' }
])

const setTopTab = (key) => {
  emit('setTopTab', key)
}

const toggleDark = () => {
  emit('toggleDark')
}

const toggleLang = () => {
  emit('toggleLang')
}

const closeSearchOverlay = () => {
  // Emit event to parent for overlay handling
}

// Expose for parent
defineExpose({
  searchDropdownRef
})
</script>

<style scoped>
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

/* Light mode: Goodyear style - dark blue background + yellow underline */
.topbar:not(.dark) {
  background: linear-gradient(135deg, #003087 0%, #001F5C 100%);
  border-bottom: none;
}

.topbar-underline {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: #f6b93b;
}

/* Dark mode: tech style - dark gray background */
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

/* Light mode: yellow Logo */
.logo-oval:not(.dark) {
  background: #f6b93b;
  color: #001F5C;
}

/* Dark mode: tech gradient Logo */
.logo-oval.dark {
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

/* Light mode: yellow text */
.logo-text:not(.dark) {
  color: #f6b93b;
}

/* Dark mode: white text */
.logo-text.dark {
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

/* Light mode nav buttons */
.tn:not(.dark) {
  color: rgba(255, 255, 255, 0.75);
}

.tn:not(.dark):hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.tn:not(.dark).active {
  color: #001F5C;
  background: #f6b93b;
}

/* Dark mode nav buttons */
.tn.dark {
  color: var(--text-tertiary);
}

.tn.dark:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.tn.dark.active {
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

/* Light mode buttons */
.icon-btn:not(.dark) {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.75);
}

.icon-btn:not(.dark):hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  color: #fff;
}

/* Dark mode buttons */
.icon-btn.dark {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
  color: var(--text-secondary);
}

.icon-btn.dark:hover {
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

@media (max-width: 768px) {
  .topbar-inner {
    padding: 0 12px;
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