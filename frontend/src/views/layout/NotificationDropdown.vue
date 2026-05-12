<template>
  <div class="notif-dropdown-wrapper">
    <button
      class="icon-btn notif-btn"
      :class="{ dark: darkMode, 'has-unread': unreadCount > 0 }"
      :title="notifTitle"
      @click="toggleDropdown"
    >
      <el-icon><Bell /></el-icon>
      <span class="notif-badge" v-if="unreadCount > 0">
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <!-- Dropdown Panel -->
    <Transition name="dropdown">
      <div
        v-if="showDropdown"
        class="notif-panel"
        :class="{ dark: darkMode }"
        ref="panelRef"
      >
        <!-- Header -->
        <div class="notif-header">
          <span class="notif-header-title">{{ notifTitle }}</span>
          <button
            v-if="unreadCount > 0"
            class="notif-mark-all"
            @click="$emit('markAllRead')"
          >
            全部标记已读
          </button>
        </div>

        <!-- Notification List -->
        <div class="notif-list" v-if="notifications.length > 0">
          <div
            v-for="notif in notifications"
            :key="notif.id"
            class="notif-item"
            :class="{ unread: !notif.read, dark: darkMode }"
            @click="handleItemClick(notif)"
          >
            <div class="notif-icon">
              <el-icon :class="getIconClass(notif.type)">
                <Warning v-if="notif.type.includes('fault')" />
                <Tools v-if="notif.type.includes('maintenance')" />
                <Bell v-if="notif.type.includes('system')" />
                <InfoFilled v-if="notif.type.includes('info')" />
              </el-icon>
            </div>
            <div class="notif-content">
              <div class="notif-title">{{ notif.title }}</div>
              <div class="notif-text">{{ notif.content }}</div>
              <div class="notif-time">{{ formatTime(notif.created_at) }}</div>
            </div>
            <span class="unread-dot" v-if="!notif.read"></span>
          </div>
        </div>

        <!-- Empty State -->
        <div class="notif-empty" v-else>
          <el-icon><Bell /></el-icon>
          <span>暂无通知</span>
        </div>

        <!-- Footer -->
        <div class="notif-footer">
          <button class="notif-view-all" @click="$emit('viewAll')">
            查看全部通知
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Bell, Warning, Tools, InfoFilled } from '@element-plus/icons-vue'
import { getNotifications } from '@/api'

const props = defineProps({
  darkMode: {
    type: Boolean,
    default: false
  },
  notifTitle: {
    type: String,
    default: 'Notifications'
  },
  unreadCount: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['markRead', 'markAllRead', 'viewAll'])

const router = useRouter()
const showDropdown = ref(false)
const panelRef = ref(null)
const notifications = ref([])
const loading = ref(false)

const toggleDropdown = async () => {
  showDropdown.value = !showDropdown.value
  if (showDropdown.value) {
    await loadNotifications()
  }
}

const loadNotifications = async () => {
  loading.value = true
  try {
    const res = await getNotifications(false)  // false = all, true = unread_only
    notifications.value = res.items || []
  } catch (e) {
    console.error('Failed to load notifications:', e)
  } finally {
    loading.value = false
  }
}

const handleItemClick = async (notif) => {
  // 先关闭下拉面板
  showDropdown.value = false

  // 标记已读
  if (!notif.read) {
    emit('markRead', notif.id)
  }

  // 跳转到关联页面
  if (notif.reference_type && notif.reference_id) {
    const refType = notif.reference_type.toLowerCase()
    let targetPath = ''

    if (refType.includes('fault')) {
      targetPath = `/faults/${notif.reference_id}`
    } else if (refType.includes('maintenance')) {
      targetPath = `/maintenance/${notif.reference_id}`
    }

    // 如果当前已在目标页面，刷新数据
    if (router.currentRoute.value.path === targetPath) {
      // 触发刷新事件
      window.dispatchEvent(new CustomEvent('refresh-detail', { detail: { id: notif.reference_id } }))
    } else {
      // 否则跳转到目标页面
      router.push(targetPath)
    }
  }
}

const getIconClass = (type) => {
  // 支持 fault_assigned, maintenance_assigned 等类型
  if (type.includes('fault')) return 'icon-danger'
  if (type.includes('maintenance')) return 'icon-warning'
  if (type.includes('system')) return 'icon-info'
  return 'icon-default'
}

const getIconComponent = (type) => {
  if (type.includes('fault')) return 'Warning'
  if (type.includes('maintenance')) return 'Tools'
  if (type.includes('system')) return 'Bell'
  return 'InfoFilled'
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

// Close dropdown on outside click
const handleClickOutside = (e) => {
  if (panelRef.value && !panelRef.value.contains(e.target)) {
    const btn = e.target.closest('.notif-btn')
    if (!btn) {
      showDropdown.value = false
    }
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.notif-dropdown-wrapper {
  position: relative;
}

.notif-btn {
  position: relative;
}

.notif-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;
  text-align: center;
  border-radius: 9px;
}

/* Light mode badge */
.icon-btn:not(.dark) .notif-badge {
  background: #f6b93b;
  color: #001F5C;
}

/* Dark mode badge */
.icon-btn.dark .notif-badge {
  background: var(--accent-primary);
  color: #fff;
}

/* Dropdown Panel */
.notif-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 360px;
  max-height: 480px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
  z-index: 100;
}

/* Light mode panel */
.notif-panel:not(.dark) {
  background: #fff;
  border: 1px solid #e5e7eb;
}

/* Dark mode panel */
.notif-panel.dark {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
}

/* Header */
.notif-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
}

.notif-panel:not(.dark) .notif-header {
  border-bottom-color: #e5e7eb;
}

.notif-panel.dark .notif-header {
  border-bottom-color: var(--border-default);
}

.notif-header-title {
  font-size: 14px;
  font-weight: 600;
}

.notif-panel:not(.dark) .notif-header-title {
  color: #1f2937;
}

.notif-panel.dark .notif-header-title {
  color: var(--text-primary);
}

.notif-mark-all {
  font-size: 12px;
  color: var(--accent-primary);
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.notif-mark-all:hover {
  background: rgba(0, 184, 148, 0.1);
}

/* Notification List */
.notif-list {
  max-height: 320px;
  overflow-y: auto;
}

.notif-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.notif-panel:not(.dark) .notif-item {
  border-bottom: 1px solid #f3f4f6;
}

.notif-panel:not(.dark) .notif-item:hover {
  background: #f9fafb;
}

.notif-panel.dark .notif-item {
  border-bottom: 1px solid var(--border-light);
}

.notif-panel.dark .notif-item:hover {
  background: var(--bg-hover);
}

.notif-item.unread {
  background: rgba(0, 184, 148, 0.05);
}

.notif-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
}

.notif-panel:not(.dark) .notif-icon {
  background: #f3f4f6;
}

.notif-panel.dark .notif-icon {
  background: var(--bg-tertiary);
}

.notif-icon .icon-danger {
  color: var(--accent-danger);
}

.notif-icon .icon-warning {
  color: var(--accent-warning);
}

.notif-icon .icon-info {
  color: var(--accent-primary);
}

.notif-icon .icon-default {
  color: var(--text-secondary);
}

.notif-content {
  flex: 1;
  min-width: 0;
}

.notif-title {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  margin-bottom: 4px;
}

.notif-panel:not(.dark) .notif-title {
  color: #1f2937;
}

.notif-panel.dark .notif-title {
  color: var(--text-primary);
}

.notif-text {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-secondary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.notif-time {
  font-size: 11px;
  color: var(--text-tertiary);
}

.unread-dot {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 8px;
  height: 8px;
  background: var(--accent-primary);
  border-radius: 50%;
}

/* Empty State */
.notif-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 48px 16px;
  color: var(--text-tertiary);
}

.notif-empty .el-icon {
  font-size: 32px;
  opacity: 0.5;
}

/* Footer */
.notif-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border-light);
}

.notif-panel:not(.dark) .notif-footer {
  border-top-color: #e5e7eb;
}

.notif-panel.dark .notif-footer {
  border-top-color: var(--border-default);
}

.notif-view-all {
  width: 100%;
  padding: 8px;
  font-size: 13px;
  font-weight: 500;
  color: var(--accent-primary);
  background: transparent;
  border: 1px solid var(--accent-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
}

.notif-view-all:hover {
  background: var(--accent-primary);
  color: #fff;
}

/* Dropdown Transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

@media (max-width: 576px) {
  .notif-panel {
    width: 300px;
    right: -60px;
  }
}
</style>