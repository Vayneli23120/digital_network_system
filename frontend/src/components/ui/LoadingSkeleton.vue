<template>
  <div :class="['loading-skeleton', variant]">
    <!-- Table variant -->
    <template v-if="variant === 'table'">
      <div class="skeleton-table">
        <!-- Header -->
        <div class="skeleton-header">
          <div
            v-for="col in cols"
            :key="`header-${col}`"
            class="skeleton-cell skeleton-shimmer"
          />
        </div>
        <!-- Rows -->
        <div
          v-for="row in rows"
          :key="`row-${row}`"
          class="skeleton-row"
        >
          <div
            v-for="col in cols"
            :key="`cell-${row}-${col}`"
            class="skeleton-cell skeleton-shimmer"
          />
        </div>
      </div>
    </template>

    <!-- Card variant -->
    <template v-else-if="variant === 'card'">
      <div class="skeleton-cards">
        <div
          v-for="card in rows"
          :key="`card-${card}`"
          class="skeleton-card"
        >
          <div class="skeleton-card-header">
            <div class="skeleton-avatar skeleton-shimmer" />
            <div class="skeleton-card-title">
              <div class="skeleton-line skeleton-shimmer" style="width: 60%" />
              <div class="skeleton-line skeleton-shimmer" style="width: 40%" />
            </div>
          </div>
          <div class="skeleton-card-body">
            <div class="skeleton-line skeleton-shimmer" style="width: 100%" />
            <div class="skeleton-line skeleton-shimmer" style="width: 80%" />
            <div class="skeleton-line skeleton-shimmer" style="width: 60%" />
          </div>
        </div>
      </div>
    </template>

    <!-- List variant -->
    <template v-else-if="variant === 'list'">
      <div class="skeleton-list">
        <div
          v-for="item in rows"
          :key="`list-${item}`"
          class="skeleton-list-item"
        >
          <div class="skeleton-icon skeleton-shimmer" />
          <div class="skeleton-list-content">
            <div class="skeleton-line skeleton-shimmer" style="width: 70%" />
            <div class="skeleton-line skeleton-shimmer" style="width: 50%" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
defineProps({
  rows: {
    type: Number,
    default: 5,
  },
  cols: {
    type: Number,
    default: 6,
  },
  variant: {
    type: String,
    default: 'table',
    validator: (v) => ['table', 'card', 'list'].includes(v),
  },
})
</script>

<style scoped>
.loading-skeleton {
  width: 100%;
}

/* Shimmer animation */
@keyframes shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

.skeleton-shimmer {
  background: linear-gradient(
    90deg,
    var(--bg-tertiary) 25%,
    var(--bg-hover) 50%,
    var(--bg-tertiary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
  border-radius: var(--radius-sm);
}

/* Table variant */
.skeleton-table {
  display: flex;
  flex-direction: column;
  gap: 1px;
  background: var(--border-default);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.skeleton-header {
  display: flex;
  gap: 1px;
  background: var(--bg-tertiary);
}

.skeleton-header .skeleton-cell {
  height: 36px;
  background: var(--bg-hover);
}

.skeleton-row {
  display: flex;
  gap: 1px;
  background: var(--bg-tertiary);
}

.skeleton-cell {
  flex: 1;
  min-height: 44px;
  border-radius: 0;
}

.skeleton-row .skeleton-cell {
  min-height: 48px;
}

/* Card variant */
.skeleton-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--gap-md);
}

.skeleton-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
}

.skeleton-card-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  margin-bottom: var(--gap-md);
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.skeleton-card-title {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.skeleton-card-body {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.skeleton-line {
  height: 14px;
  border-radius: var(--radius-sm);
}

/* List variant */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  padding: var(--gap-md);
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.skeleton-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.skeleton-list-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}
</style>