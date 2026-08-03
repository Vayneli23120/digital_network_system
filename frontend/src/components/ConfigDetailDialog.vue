<template>
  <el-dialog
    v-model="visible"
    :title="t('complianceConfigViewerTitle')"
    width="95%"
    top="2vh"
    append-to-body
    draggable
    align-center
    class="compliance-dialog config-detail-dialog"
  >
    <div class="config-detail-layout">
      <!-- 左侧配置行展示 -->
      <div class="config-lines-panel">
        <div class="panel-header">
          <span class="panel-title">{{ t('complianceConfigText') }}</span>
          <div class="issue-stats-bar">
            <span class="stat-item critical" v-if="issueStats.critical > 0">
              <el-icon><WarningFilled /></el-icon>
              {{ issueStats.critical }} {{ t('complianceCriticalIssues') }}
            </span>
            <span class="stat-item high" v-if="issueStats.high > 0">
              <el-icon><WarningFilled /></el-icon>
              {{ issueStats.high }} {{ t('complianceHighIssues') }}
            </span>
            <span class="stat-item medium" v-if="issueStats.medium > 0">
              <el-icon><WarningFilled /></el-icon>
              {{ issueStats.medium }} {{ t('complianceMediumIssues') }}
            </span>
            <span class="stat-item passed">
              <el-icon><CircleCheck /></el-icon>
              {{ issueStats.passed }} {{ t('compliancePassedChecks') }}
            </span>
          </div>
        </div>
        <div class="config-lines-container" ref="configLinesRef">
          <div
            v-for="(line, index) in configLineAnalysis"
            :key="line.lineNum"
            class="config-line"
            :class="getLineClass(line)"
            @click="selectConfigLine(line, index)"
          >
            <span class="line-number">{{ line.lineNum }}</span>
            <code class="line-content">{{ line.content }}</code>
            <div v-if="line.issues && line.issues.length > 0" class="issue-marker">
              <el-icon><WarningFilled /></el-icon>
              <span class="issue-count">{{ line.issues.length }}</span>
            </div>
            <div v-if="line.isPassed" class="passed-marker">
              <el-icon><CircleCheck /></el-icon>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧问题详情面板 -->
      <div class="issue-detail-panel">
        <div class="panel-header">
          <span class="panel-title">{{ t('complianceIssueDetail') }}</span>
        </div>

        <!-- 选中配置行的问题 -->
        <div v-if="selectedLine" class="selected-line-info">
          <div class="line-info-header">
            <span class="line-num">Line {{ selectedLine.lineNum }}</span>
            <el-tag v-if="selectedLine.issues?.length > 0" type="danger" size="small">
              {{ selectedLine.issues?.length }} issues
            </el-tag>
            <el-tag v-else type="success" size="small">{{ t('complianceNoIssues') }}</el-tag>
          </div>
          <code class="line-code">{{ selectedLine.content }}</code>
        </div>

        <div class="issue-list" v-if="selectedLine?.issues?.length > 0">
          <div v-for="issue in selectedLine.issues" :key="issue.check_id" class="issue-card">
            <div class="issue-header">
              <el-tag :type="severityTagType(issue.severity)" size="small">
                {{ t('complianceSeverity' + capitalize(issue.severity)) }}
              </el-tag>
              <span class="issue-id">{{ issue.check_id }}</span>
            </div>
            <div class="issue-name">{{ issue.check_name }}</div>
            <div class="issue-category">
              <el-tag :type="categoryTagType(issue.category)" size="small">
                {{ t('complianceCategory' + capitalize(issue.category)) }}
              </el-tag>
            </div>
            <div class="issue-detail-text">{{ issue.detail }}</div>
            <div class="issue-recommendation" v-if="issue.recommendation">
              <span class="rec-label">{{ t('complianceFixRecommendation') }}:</span>
              <pre class="rec-code">{{ issue.recommendation }}</pre>
            </div>
            <div class="issue-recommendation" v-else>
              <span class="rec-label">{{ t('complianceFixRecommendation') }}:</span>
              <span class="rec-empty">{{ t('valueNa') }}</span>
            </div>
          </div>
        </div>

        <!-- 所有失败问题列表 -->
        <div v-else class="all-issues-list">
          <div class="list-title">{{ t('complianceIssueSummary') }}</div>
          <div v-for="result in failedResults" :key="result.check_id" class="issue-summary-card"
               @click="highlightIssueLines(result)">
            <div class="card-header">
              <el-tag :type="severityTagType(result.severity)" size="small">
                {{ t('complianceSeverity' + capitalize(result.severity)) }}
              </el-tag>
              <span class="card-id">{{ result.check_id }}</span>
              <el-tag :type="categoryTagType(result.category)" size="small" class="card-category">
                {{ t('complianceCategory' + capitalize(result.category)) }}
              </el-tag>
            </div>
            <div class="card-name">{{ result.check_name }}</div>
            <div class="card-detail">{{ result.detail }}</div>
            <div class="card-recommendation" v-if="result.recommendation">
              <span class="rec-label">{{ t('complianceFixRecommendation') }}:</span>
              <pre class="rec-preview">{{ result.recommendation.substring(0, 100) }}{{ result.recommendation.length > 100 ? '...' : '' }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { WarningFilled, CircleCheck } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { analyzeConfigLines, getLineClass, severityTagType, categoryTagType, capitalize } from '@/utils/compliance.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  report: { type: Object, default: null },
  configText: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const configLineAnalysis = ref([])
const selectedLine = ref(null)
const configLinesRef = ref(null)

// 打开时构建行级分析（mirror 原 showConfigDetailDialog）
watch(() => props.modelValue, (val) => {
  if (val && props.report) {
    // 使用 API 返回的 config_analysis
    if (props.report.config_analysis && props.report.config_analysis.length > 0) {
      configLineAnalysis.value = props.report.config_analysis.map(line => ({
        lineNum: line.line_number,
        content: line.content,
        issues: line.issues || [],
        severity: line.severity || 'ok',
        isPassed: (line.issues || []).length === 0 && line.severity === 'ok'
      }))
    } else {
      // 如果没有 config_analysis，从配置文本生成
      if (props.configText) {
        configLineAnalysis.value = analyzeConfigLines(props.configText, props.report.results)
      } else {
        configLineAnalysis.value = []
      }
    }

    selectedLine.value = null
  }
})

// 计算问题统计
const issueStats = computed(() => {
  let critical = 0, high = 0, medium = 0, low = 0, passed = 0

  for (const line of configLineAnalysis.value) {
    if (line.issues && line.issues.length > 0) {
      for (const issue of line.issues) {
        if (issue.severity === 'critical') critical++
        else if (issue.severity === 'high') high++
        else if (issue.severity === 'medium') medium++
        else low++
      }
    } else if (line.isPassed) {
      passed++
    }
  }

  // 同时统计报告中的通过数
  passed = props.report?.passed || passed

  return { critical, high, medium, low, passed }
})

// 失败结果列表
const failedResults = computed(() => {
  return props.report?.results?.filter(r => !r.passed) || []
})

// 选中配置行
const selectConfigLine = async (line, index) => {
  selectedLine.value = line

  // 等待 DOM 更新
  await nextTick()

  // 高亮选中的行
  const container = configLinesRef.value
  if (container) {
    const lineElements = container.querySelectorAll('.config-line')
    lineElements.forEach((el, i) => {
      if (i === index) {
        el.classList.add('selected')
      } else {
        el.classList.remove('selected')
      }
    })
  }
}

// 高亮问题相关的配置行（根据结果中的 line_numbers）
const highlightIssueLines = async (result) => {
  // 使用结果中的 line_numbers
  const lineNumbers = result.line_numbers || []

  if (lineNumbers.length === 0) {
    // 如果没有行号，尝试从其他信息匹配
    const matchPatterns = []

    if (result.pattern) {
      matchPatterns.push(result.pattern.toLowerCase())
    }

    if (result.recommendation) {
      const recLines = result.recommendation.split('\n')
      for (const line of recLines) {
        const cmdMatch = line.match(/^\s*(?:interface|ip|ntp|logging|snmp|aaa|username|service|enable|switchport|spanning-tree|banner|crypto|line)\s+/i)
        if (cmdMatch) {
          matchPatterns.push(line.trim().toLowerCase())
        }
      }
    }

    if (matchPatterns.length === 0) return

    // 搜索匹配的行
    for (let i = 0; i < configLineAnalysis.value.length; i++) {
      const line = configLineAnalysis.value[i]
      const contentLower = line.content.toLowerCase()

      for (const pattern of matchPatterns) {
        if (contentLower.includes(pattern)) {
          lineNumbers.push(line.lineNum)
          break
        }
      }
    }
  }

  if (lineNumbers.length === 0) return

  // 找到第一个匹配行
  const firstMatchLineNum = lineNumbers[0]
  const firstMatchIndex = configLineAnalysis.value.findIndex(l => l.lineNum === firstMatchLineNum)

  if (firstMatchIndex !== -1) {
    const line = configLineAnalysis.value[firstMatchIndex]
    await selectConfigLine(line, firstMatchIndex)

    // 再次等待 DOM 更新后滚动
    await nextTick()

    const container = configLinesRef.value
    if (container) {
      const lineElements = container.querySelectorAll('.config-line')
      if (lineElements[firstMatchIndex]) {
        lineElements[firstMatchIndex].scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }
}
</script>

<style scoped>
/* ========================================
   配置问题高亮对话框
   ======================================== */

.config-detail-dialog .config-detail-layout {
  display: flex;
  gap: 16px;
  height: 70vh;
}

/* 左侧配置行面板 */
.config-lines-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.config-lines-panel .panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.issue-stats-bar {
  display: flex;
  gap: 12px;
}

.issue-stats-bar .stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}

.issue-stats-bar .stat-item.critical {
  background: rgba(214, 48, 49, 0.1);
  color: var(--accent-danger);
}

.issue-stats-bar .stat-item.high {
  background: rgba(230, 162, 60, 0.1);
  color: #e6a23c;
}

.issue-stats-bar .stat-item.medium {
  background: rgba(9, 132, 227, 0.1);
  color: var(--accent-secondary);
}

.issue-stats-bar .stat-item.passed {
  background: rgba(0, 184, 148, 0.1);
  color: var(--accent-primary);
}

.config-lines-container {
  flex: 1;
  overflow-y: auto;
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.config-line {
  display: flex;
  align-items: center;
  min-height: 24px;
  padding: 4px 8px;
  cursor: pointer;
  transition: background 0.15s ease;
  border-left: 3px solid transparent;
}

.config-line:hover {
  background: var(--bg-hover);
}

.config-line.selected {
  background: rgba(9, 132, 227, 0.1);
  border-left-color: var(--accent-secondary);
}

.config-line.critical {
  background: rgba(214, 48, 49, 0.15);
  border-left-color: var(--accent-danger);
}

.config-line.high {
  background: rgba(230, 162, 60, 0.15);
  border-left-color: #e6a23c;
}

.config-line.medium {
  background: rgba(9, 132, 227, 0.15);
  border-left-color: var(--accent-secondary);
}

.config-line.low {
  background: rgba(102, 126, 234, 0.1);
  border-left-color: #667eea;
}

.config-line.passed {
  background: transparent;
}

.config-line.normal {
  background: transparent;
}

.line-number {
  width: 50px;
  text-align: right;
  color: var(--text-tertiary);
  flex-shrink: 0;
  padding-right: 12px;
}

.line-content {
  flex: 1;
  white-space: pre;
  overflow-x: auto;
  color: var(--text-primary);
}

.issue-marker,
.passed-marker {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  flex-shrink: 0;
  margin-left: 8px;
}

.issue-marker {
  background: rgba(214, 48, 49, 0.1);
  color: var(--accent-danger);
}

.passed-marker {
  background: rgba(0, 184, 148, 0.1);
  color: var(--accent-primary);
}

.issue-count {
  font-size: 11px;
  font-weight: 600;
}

/* 右侧问题详情面板 */
.issue-detail-panel {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.issue-detail-panel .panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.selected-line-info {
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-subtle);
}

.line-info-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.line-num {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.line-code {
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  color: var(--text-primary);
  background: var(--bg-hover);
  padding: 8px 12px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre;
}

.issue-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.issue-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.issue-card .issue-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.issue-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.issue-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.issue-category {
  margin-bottom: 8px;
}

.issue-detail-text {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
  line-height: 1.5;
}

.issue-recommendation {
  background: rgba(0, 184, 148, 0.05);
  border: 1px solid rgba(0, 184, 148, 0.1);
  border-radius: 4px;
  padding: 8px;
}

.rec-label {
  font-size: 12px;
  color: var(--accent-primary);
  font-weight: 500;
  display: block;
  margin-bottom: 4px;
}

.rec-code {
  font-family: 'Geist Mono', monospace;
  font-size: 11px;
  color: var(--text-primary);
  display: block;
  white-space: pre-wrap;
}

/* 所有问题列表 */
.all-issues-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.list-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.issue-summary-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  margin-bottom: 8px;
}

.issue-summary-card:hover {
  border-color: var(--accent-secondary);
  background: var(--bg-hover);
}

.issue-summary-card .card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.card-id {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
}

.card-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.card-detail {
  font-size: 11px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-category {
  margin-left: auto;
}

.card-recommendation {
  margin-top: 6px;
  padding: 6px;
  background: rgba(0, 184, 148, 0.05);
  border-radius: 4px;
}

.rec-preview {
  font-family: 'Geist Mono', monospace;
  font-size: 10px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  margin: 0;
}

.rec-empty {
  color: var(--text-tertiary);
  font-size: 11px;
}

/* ========================================
   暗色模式补充
   ======================================== */

.dark .config-lines-panel,
.dark .issue-detail-panel {
  background: rgba(13, 17, 23, 0.4);
}

.dark .config-line.critical {
  background: rgba(214, 48, 49, 0.2);
}

.dark .config-line.high {
  background: rgba(230, 162, 60, 0.2);
}

.dark .config-line.medium {
  background: rgba(9, 132, 227, 0.2);
}

.dark .config-line.selected {
  background: rgba(0, 184, 148, 0.15);
  border-left-color: var(--accent-primary);
}

.dark .issue-card,
.dark .issue-summary-card {
  background: rgba(13, 17, 23, 0.6);
}

.dark .issue-recommendation {
  background: rgba(0, 184, 148, 0.1);
}
</style>
