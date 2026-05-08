<template>
  <div class="avatar-wrap" @click="toggleMenu">
    <div class="avatar" :class="{ dark: darkMode }">A</div>
    <div class="user-menu" v-if="showMenu">
      <div class="um-header">
        <div class="um-avatar">A</div>
        <div class="um-info">
          <span class="um-name">{{ userName }}</span>
          <span class="um-email">{{ userEmail }}</span>
        </div>
      </div>
      <div class="um-divider"></div>
      <button class="um-item"><el-icon><User /></el-icon> {{ profileLabel }}</button>
      <button class="um-item"><el-icon><Setting /></el-icon> {{ settingsLabel }}</button>
      <div class="um-divider"></div>
      <button class="um-item danger"><el-icon><SwitchButton /></el-icon> {{ logoutLabel }}</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { User, Setting, SwitchButton } from '@element-plus/icons-vue'

const props = defineProps({
  darkMode: {
    type: Boolean,
    default: false
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

const emit = defineEmits(['toggle'])

const showMenu = ref(false)

const toggleMenu = () => {
  showMenu.value = !showMenu.value
  emit('toggle', showMenu.value)
}

const closeMenu = () => {
  showMenu.value = false
}

// Close menu on outside click
const handleOutsideClick = (e) => {
  if (!e.target.closest('.avatar-wrap')) {
    showMenu.value = false
  }
}

// Expose methods for parent component
defineExpose({
  closeMenu
})

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
})

onUnmounted(() => {
  document.removeEventListener('click', handleOutsideClick)
})
</script>

<style scoped>
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
  /* Light mode: yellow background */
  background: #f6b93b;
  color: #001F5C;
}

/* Dark mode avatar */
.avatar.dark {
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
</style>