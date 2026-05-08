<template>
  <el-card :shadow="shadow" :class="['page-card', { 'no-header': !title }]">
    <template #header v-if="title || $slots.header">
      <div class="card-header">
        <span class="card-title" v-if="title">{{ title }}</span>
        <slot name="header-actions" />
      </div>
    </template>

    <slot />
  </el-card>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  shadow: { type: String, default: 'hover' },
})
</script>

<style scoped>
.page-card {
  border-radius: var(--radius-md);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.page-card.no-header :deep(.el-card__header) {
  display: none;
}
</style>