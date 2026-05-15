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

    <!-- 差异内容 -->
    <div class="diff-content">
      <div class="diff-header">
        <div class="diff-title old">{{ t('diffCurrentConfig') }}</div>
        <div class="diff-title new">{{ t('diffNewConfig') }}</div>
      </div>
      <div class="diff-body">
        <div
          v-for="(line, index) in diffLines"
          :key="index"
          class="diff-line"
          :class="line.type"
        >
          <div class="line-number old">{{ line.oldLineNum || '' }}</div>
          <div class="line-number new">{{ line.newLineNum || '' }}</div>
          <div class="line-content">
            <span v-if="line.type === 'added'" class="marker">+</span>
            <span v-else-if="line.type === 'removed'" class="marker">-</span>
            <span v-else class="marker"> </span>
            <code class="code-content">{{ line.content }}</code>
          </div>
        </div>
        <div v-if="diffLines.length === 0" class="diff-empty">
          {{ t('diffEmpty') }}
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
import { useI18n } '@/composables/useI18n'

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
  }
})

// 计算差异
const diffLines = computed(() => {
  const oldLines = props.oldConfig.split('\n')
  const newLines = props.newConfig.split('\n')

  const result = []
  let oldLineNum = 0
  let newLineNum = 0

  // 简化的diff算法 - 使用LCS（最长公共子序列）
  const lcs = computeLCS(oldLines, newLines)

  let oldIdx = 0
  let newIdx = 0

  for (const line of lcs) {
    // 处理删除的行
    while (oldIdx < oldLines.length && oldLines[oldIdx] !== line) {
      result.push({
        type: 'removed',
        content: oldLines[oldIdx],
        oldLineNum: ++oldLineNum,
        newLineNum: null
      })
      oldIdx++
    }

    // 处理的添加的行
    while (newIdx < newLines.length && newLines[newIdx] !== line) {
      result.push({
        type: 'added',
        content: newLines[newIdx],
        oldLineNum: null,
        newLineNum: ++newLineNum
      })
      newIdx++
    }

    // 相同的行
    if (line !== undefined) {
      result.push({
        type: 'unchanged',
        content: line,
        oldLineNum: ++oldLineNum,
        newLineNum: ++newLineNum
      })
      oldIdx++
      newIdx++
    }
  }

  // 处理剩余的行
  while (oldIdx < oldLines.length) {
    result.push({
      type: 'removed',
      content: oldLines[oldIdx],
      oldLineNum: ++oldLineNum,
      newLineNum: null
    })
    oldIdx++
  }

  while (newIdx < newLines.length) {
    result.push({
      type: 'added',
      content: newLines[newIdx],
      oldLineNum: null,
      newLineNum: ++newLineNum
    })
    newIdx++
  }

  return result
})

// 统计信息
const stats = computed(() => {
  return {
    added: diffLines.value.filter(l => l.type === 'added').length,
    removed: diffLines.value.filter(l => l.type === 'removed').length,
    modified: diffLines.value.filter(l => l.type === 'modified').length
  }
})

// 计算最长公共子序列
function computeLCS(a, b) {
  const m = a.length
  const n = b.length
  const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0))

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1])
      }
    }
  }

  // 回溯获取LCS
  const lcs = []
  let i = m, j = n
  while (i > 0 && j > 0) {
    if (a[i - 1] === b[j - 1]) {
      lcs.unshift(a[i - 1])
      i--
      j--
    } else if (dp[i - 1][j] > dp[i][j - 1]) {
      i--
    } else {
      j--
    }
  }

  return lcs
}
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

/* 差异内容 */
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

.diff-title.old { border-right: 1px solid var(--border-default); }

.diff-body {
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.diff-line {
  display: flex;
  min-height: 24px;
}

.diff-line.added {
  background: rgba(103, 194, 58, 0.08);
}

.diff-line.removed {
  background: rgba(245, 108, 108, 0.08);
}

.diff-line.unchanged {
  background: transparent;
}

.line-number {
  width: 40px;
  padding: 2px 8px;
  text-align: right;
  color: #909399;
  background: var(--el-fill-color-light);
  border-right: 1px solid var(--border-default);
  flex-shrink: 0;
}

.line-content {
  flex: 1;
  padding: 2px 12px;
  display: flex;
  gap: 8px;
  white-space: pre;
  overflow-x: auto;
}

.marker {
  width: 12px;
  flex-shrink: 0;
  font-weight: 600;
}

.diff-line.added .marker { color: #67c23a; }
.diff-line.removed .marker { color: #f56c6c; }
.diff-line.unchanged .marker { color: transparent; }

.code-content {
  color: var(--text-primary);
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

.diff-viewer.dark .diff-header,
.diff-viewer.dark .line-number {
  background: rgba(255, 255, 255, 0.05);
}

.diff-viewer.dark .diff-line.added {
  background: rgba(103, 194, 58, 0.15);
}

.diff-viewer.dark .diff-line.removed {
  background: rgba(245, 108, 108, 0.15);
}
</style>
