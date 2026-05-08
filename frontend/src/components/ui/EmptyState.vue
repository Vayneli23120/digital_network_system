<template>
  <div class="empty-state">
    <div class="empty-icon">
      <slot name="icon">
        <!-- Default: Inbox icon -->
        <svg
          v-if="!icon"
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
        <!-- Custom icon component -->
        <component v-else-if="typeof icon === 'object'" :is="icon" />
      </slot>
    </div>
    <p class="empty-message">{{ message }}</p>
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
defineProps({
  icon: {
    type: [String, Object],
    default: null,
  },
  message: {
    type: String,
    default: 'No data available',
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