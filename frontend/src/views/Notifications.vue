<template>
  <div class="notifications-page">
    <div class="page-header">
      <h2>{{ t('notifPageTitle') }}</h2>
      <el-button v-if="unreadCount > 0" type="primary" @click="markAllRead">
        {{ t('notifMarkAllRead') }}
      </el-button>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <el-radio-group v-model="filterType" @change="loadNotifications">
        <el-radio-button value="all">{{ t('notifFilterAll') }}</el-radio-button>
        <el-radio-button value="unread">{{ t('notifFilterUnread') }}</el-radio-button>
        <el-radio-button value="fault">{{ t('notifFilterFault') }}</el-radio-button>
        <el-radio-button value="maintenance">{{ t('notifFilterMaintenance') }}</el-radio-button>
        <el-radio-button value="system">{{ t('notifFilterSystem') }}</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 通知列表 -->
    <div class="notif-list-container" v-loading="loading">
      <div v-if="notifications.length > 0" class="notif-list">
        <div
          v-for="notif in notifications"
          :key="notif.id"
          class="notif-card"
          :class="{ unread: !notif.read }"
          @click="handleNotifClick(notif)"
        >
          <div class="notif-icon">
            <el-icon :class="getIconClass(notif.type)" :size="24">
              <Warning v-if="notif.type.includes('fault')" />
              <Tools v-if="notif.type.includes('maintenance')" />
              <Bell v-if="notif.type.includes('system')" />
              <InfoFilled v-if="notif.type.includes('info')" />
            </el-icon>
          </div>
          <div class="notif-content">
            <div class="notif-header">
              <span class="notif-title">{{ notif.title }}</span>
              <el-tag v-if="!notif.read" type="success" size="small">{{ t('notifUnread') }}</el-tag>
            </div>
            <div class="notif-text">{{ notif.content }}</div>
            <div class="notif-meta">
              <span class="notif-time">{{ formatTime(notif.created_at) }}</span>
              <span v-if="notif.reference_type" class="notif-ref">
                {{ getRefLabel(notif.reference_type) }}: {{ notif.reference_id }}
              </span>
            </div>
          </div>
          <div class="notif-actions">
            <el-button v-if="!notif.read" type="success" size="small" @click.stop="markRead(notif.id)">
              {{ t('notifMarkRead') }}
            </el-button>
            <el-button type="danger" size="small" link @click.stop="deleteNotif(notif.id)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <el-icon :size="48"><Bell /></el-icon>
        <p>{{ t('notifNoNotifications') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell, Warning, Tools, InfoFilled, Delete } from '@element-plus/icons-vue'
import { getNotifications, markNotificationRead, markAllNotificationsRead, deleteNotification, getUnreadCount } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()
const router = useRouter()

const notifications = ref([])
const loading = ref(false)
const filterType = ref('all')
const unreadCount = ref(0)

const loadNotifications = debounce(async (force = false) => {
  loading.value = true
  try {
    const unreadOnly = filterType.value === 'unread'
    const res = await cachedRequest(
      () => getNotifications(unreadOnly),
      'notifications',
      { filter: filterType.value },
      { forceRefresh: force }
    )
    let items = res.items || []

    // 按类型筛选
    if (filterType.value !== 'all' && filterType.value !== 'unread') {
      items = items.filter(n => n.type?.includes(filterType.value))
    }

    notifications.value = items
  } catch (e) {
    if (e.name !== 'CanceledError') {
      ElMessage.error(t('notifLoadFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

const loadUnreadCount = async () => {
  try {
    const res = await getUnreadCount()
    unreadCount.value = res.count || 0
  } catch (e) {
    console.error('Failed to load unread count:', e)
  }
}

const markRead = async (id) => {
  try {
    await markNotificationRead(id)
    const notif = notifications.value.find(n => n.id === id)
    if (notif) notif.read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    ElMessage.success(t('notifMarkedRead'))
    clearCache('notifications')
  } catch (e) {
    ElMessage.error(t('notifMarkFailed'))
  }
}

const markAllRead = async () => {
  try {
    await markAllNotificationsRead()
    notifications.value.forEach(n => n.read = true)
    unreadCount.value = 0
    ElMessage.success(t('notifAllMarkedRead'))
    clearCache('notifications')
  } catch (e) {
    ElMessage.error(t('notifMarkFailed'))
  }
}

const deleteNotif = async (id) => {
  try {
    await deleteNotification(id)
    notifications.value = notifications.value.filter(n => n.id !== id)
    ElMessage.success(t('notifDeleted'))
    clearCache('notifications')
  } catch (e) {
    ElMessage.error(t('notifDeleteFailed'))
  }
}

const handleNotifClick = async (notif) => {
  // 标记已读
  if (!notif.read) {
    await markRead(notif.id)
  }

  // 跳转到关联页面
  if (notif.reference_type && notif.reference_id) {
    const refType = notif.reference_type.toLowerCase()
    if (refType.includes('fault')) {
      router.push(`/faults/${notif.reference_id}`)
    } else if (refType.includes('maintenance')) {
      router.push(`/maintenance/${notif.reference_id}`)
    }
  }
}

const getIconClass = (type) => {
  if (type?.includes('fault')) return 'icon-danger'
  if (type?.includes('maintenance')) return 'icon-warning'
  if (type?.includes('system')) return 'icon-info'
  return 'icon-default'
}

const getRefLabel = (refType) => {
  if (refType?.includes('fault')) return t('notifRefFault')
  if (refType?.includes('maintenance')) return t('notifRefMaintenance')
  return refType
}

const formatTime = (timeStr) => {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(diff / 3600000)
  const days = Math.floor(diff / 86400000)

  if (minutes < 1) return t('notifTimeJustNow')
  if (minutes < 60) return t('notifTimeMinutes', { count: minutes })
  if (hours < 24) return t('notifTimeHours', { count: hours })
  if (days < 7) return t('notifTimeDays', { count: days })
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadNotifications()
  loadUnreadCount()
})
</script>

<style scoped>
.notifications-page {
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.filter-bar {
  margin-bottom: 20px;
}

.notif-list-container {
  min-height: 400px;
}

.notif-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notif-card {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-light);
  cursor: pointer;
  transition: all 0.2s;
}

.notif-card:hover {
  background: var(--bg-hover);
  border-color: var(--border-default);
}

.notif-card.unread {
  background: rgba(0, 184, 148, 0.05);
  border-color: var(--accent-primary);
}

.notif-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
}

.icon-danger { color: var(--accent-danger); }
.icon-warning { color: var(--accent-warning); }
.icon-info { color: var(--accent-primary); }
.icon-default { color: var(--text-secondary); }

.notif-content {
  flex: 1;
  min-width: 0;
}

.notif-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.notif-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.notif-text {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 8px;
}

.notif-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.notif-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 24px;
  color: var(--text-tertiary);
}

.empty-state .el-icon {
  opacity: 0.5;
}

.empty-state p {
  font-size: 16px;
}
</style>