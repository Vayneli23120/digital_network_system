<template>
  <div class="diff-viewer" :class="{ dark: isDark }">
    <!-- 差异统计 -->
    <div class="diff-stats">
      <div class="stat-item added">
        <span class="stat-count">{{ stats.added }}</span>
        <span class="stat-label">{{ t('diffAdded') }}</span>
      </div>
      <div class="stat-item removed">
        <span class="stat-count">{{ stats.removed }}</span>
        <span class="stat-label">{{ t('diffRemoved') }}</span>
      </div>
      <div class="stat-item modified">
        <span class="stat-count">{{ stats.modified }}</span>
        <span class="stat-label">{{ t('diffModified') }}</span>
      </div>
    </div>

    <!-- 差异内容 - 双栏布局 -->
    <div class="diff-content">
      <div class="diff-header">
        <div class="diff-title old">{{ t('diffCurrentConfig') }}</div>
        <div class="diff-title new">{{ t('diffNewConfig') }}</div>
      </div>
      <div class="diff-body-wrapper">
        <!-- 当前配置列 -->
        <div class="diff-column old-column">
          <div
            v-for="(line, index) in oldColumnLines"
            :key="'old-'+index"
            class="diff-cell"
            :class="line.type"
          >
            <span class="line-num">{{ line.lineNum || '' }}</span>
            <code class="line-content">{{ line.content }}</code>
          </div>
        </div>
        <!-- 新配置列 -->
        <div class="diff-column new-column">
          <div
            v-for="(line, index) in newColumnLines"
            :key="'new-'+index"
            class="diff-cell"
            :class="line.type"
          >
            <span class="line-num">{{ line.lineNum || '' }}</span>
            <code class="line-content">{{ line.content }}</code>
          </div>
        </div>
      </div>
    </div>

    <!-- 图例 -->
    <div class="diff-legend">
      <div class="legend-item">
        <span class="legend-color added"></span>
        <span>{{ t('diffLegendAdded') }}</span>
      </div>
      <div class="legend-item">
        <span class="legend-color removed"></span>
        <span>{{ t('diffLegendRemoved') }}</span>
      </div>
      <div class="legend-item">
        <span class="legend-color modified"></span>
        <span>{{ t('diffLegendModified') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const props = defineProps({
  oldConfig: {
    type: String,
    default: ''
  },
  newConfig: {
    type: String,
    default: ''
  },
  isDark: {
    type: Boolean,
    default: false
  },
  diffData: {
    type: Object,
    default: null
  }
})

const stats = computed(() => {
  if (props.diffData && props.diffData.stats) {
    return props.diffData.stats
  }
  return { added: 0, removed: 0, modified: 0 }
})

// 使用传入的diff数据构建两列显示
const oldColumnLines = computed(() => {
  if (!props.diffData || !props.diffData.lines) return []

  const lines = []
  props.diffData.lines.forEach(line => {
    if (line.type === 'removed') {
      lines.push({ type: 'removed', lineNum: line.old_line_num, content: line.content })
    } else if (line.type === 'unchanged') {
      lines.push({ type: 'unchanged', lineNum: line.old_line_num, content: line.content })
    }
    // added行在old列显示为空行（保持对齐）
    if (line.type === 'added') {
      lines.push({ type: 'empty', lineNum: '', content: '' })
    }
  })
  return lines
})

const newColumnLines = computed(() => {
  if (!props.diffData || !props.diffData.lines) return []

  const lines = []
  props.diffData.lines.forEach(line => {
    if (line.type === 'added') {
      lines.push({ type: 'added', lineNum: line.new_line_num, content: line.content })
    } else if (line.type === 'unchanged') {
      lines.push({ type: 'unchanged', lineNum: line.new_line_num, content: line.content })
    }
    // removed行在new列显示为空行（保持对齐）
    if (line.type === 'removed') {
      lines.push({ type: 'empty', lineNum: '', content: '' })
    }
  })
  return lines
})
</script>

<style scoped>
.diff-viewer {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 统计栏 */
.diff-stats {
  display: flex;
  gap: 16px;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.stat-item.added { color: #67c23a; }
.stat-item.removed { color: #f56c6c; }
.stat-item.modified { color: #e6a23c; }

.stat-count {
  font-size: 18px;
  font-weight: 600;
}

.stat-label {
  font-size: 13px;
}

/* 差异内容 - 双栏布局 */
.diff-content {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.diff-header {
  display: flex;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--border-default);
}

.diff-title {
  flex: 1;
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.diff-title.old {
  border-right: 1px solid var(--border-default);
}

/* 双栏主体 */
.diff-body-wrapper {
  display: flex;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.diff-column {
  flex: 1;
  min-width: 0;
}

.old-column {
  border-right: 1px solid var(--border-default);
}

.diff-cell {
  display: flex;
  min-height: 24px;
  padding: 2px 0;
}

.diff-cell.added {
  background: rgba(103, 194, 58, 0.08);
}

.diff-cell.removed {
  background: rgba(245, 108, 108, 0.08);
}

.diff-cell.unchanged {
  background: transparent;
}

.diff-cell.empty {
  background: #f5f7fa;
}

.line-num {
  width: 50px;
  padding: 2px 8px;
  text-align: right;
  color: #909399;
  flex-shrink: 0;
}

.line-content {
  flex: 1;
  padding: 2px 8px;
  white-space: pre;
  overflow-x: auto;
}

.diff-empty {
  padding: 40px;
  text-align: center;
  color: var(--text-secondary);
}

/* 图例 */
.diff-legend {
  display: flex;
  gap: 16px;
  padding: 8px 0;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.legend-color {
  width: 16px;
  height: 16px;
  border-radius: 3px;
}

.legend-color.added { background: rgba(103, 194, 58, 0.3); }
.legend-color.removed { background: rgba(245, 108, 108, 0.3); }
.legend-color.modified { background: rgba(230, 162, 60, 0.3); }

/* Dark mode */
.diff-viewer.dark .diff-stats {
  background: rgba(255, 255, 255, 0.05);
}

.diff-viewer.dark .diff-header {
  background: rgba(255, 255, 255, 0.05);
}

.diff-viewer.dark .diff-cell.added {
  background: rgba(103, 194, 58, 0.15);
}

.diff-viewer.dark .diff-cell.removed {
  background: rgba(245, 108, 108, 0.15);
}

.diff-viewer.dark .diff-cell.empty {
  background: rgba(0, 0, 0, 0.2);
}
</style>
