<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon">
        <!-- Default: Inbox icon -->
        <svg
          v-if="icon === 'default' || !icon"
          xmlns="http://www.w3.org/2000/svg"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
          <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
        </svg>
        <!-- Table icon -->
        <svg v-else-if="icon === 'table'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <path d="M3 9h18M9 3v18"/>
        </svg>
        <!-- List icon -->
        <svg v-else-if="icon === 'list'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>
        </svg>
        <!-- Device icon -->
        <svg v-else-if="icon === 'device'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <path d="M8 21h8M12 17v4"/>
        </svg>
        <!-- Search icon -->
        <svg v-else-if="icon === 'search'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
        <!-- Warning icon -->
        <svg v-else-if="icon === 'warning'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M12 9v4M12 17h.01"/>
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.47a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
        </svg>
        <!-- Backup icon -->
        <svg v-else-if="icon === 'backup'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        <!-- Fault icon -->
        <svg v-else-if="icon === 'fault'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 8v4M12 16h.01"/>
        </svg>
        <!-- Custom icon component -->
        <component v-else-if="typeof icon === 'object'" :is="icon" />
      </slot>
    </div>
    <p class="empty-message">{{ message || t('msgNoData') }}</p>
    <button
      v-if="action"
      class="empty-action"
      @click="$emit('action')"
    >
      {{ action }}
    </button>
  </div>
</template>

<script setup>
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

defineProps({
  icon: {
    type: [String, Object],
    default: 'default', // default | table | list | device | search | warning | backup | fault
  },
  message: {
    type: String,
    default: '',
  },
  action: {
    type: String,
    default: '',
  },
})

defineEmits(['action'])
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--gap-xl) var(--gap-md);
  text-align: center;
}

.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  margin-bottom: var(--gap-md);
  background: var(--bg-tertiary);
  border-radius: 50%;
  color: var(--text-tertiary);
}

.empty-icon :deep(svg) {
  width: 40px;
  height: 40px;
}

.empty-message {
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 400;
  color: var(--text-secondary);
  margin: 0 0 var(--gap-md) 0;
  max-width: 320px;
  line-height: 1.5;
}

.empty-action {
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  color: var(--accent-primary);
  background: transparent;
  border: 1px solid var(--accent-primary);
  border-radius: var(--radius-md);
  padding: 8px 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.empty-action:hover {
  background: var(--success-bg);
}

.empty-action:active {
  transform: scale(0.98);
}
</style>