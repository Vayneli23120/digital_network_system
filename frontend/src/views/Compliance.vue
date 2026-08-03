<template>
  <div class="compliance-page">
    <!-- 页面导航栏 -->
    <div class="page-nav-bar">
      <div class="nav-left">
        <span class="page-title">{{ t('complianceTitle') }}</span>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn secondary" @click="showAIConfigDialog" :disabled="!hasAIConfigPermission" :title="!hasAIConfigPermission ? t('aiPermissionConfig') : ''">
          <el-icon><Setting /></el-icon>
          {{ t('complianceAIConfigTitle') }}
        </button>
        <button class="nav-action-btn deploy-btn" @click="showAuditDialog">
          <el-icon><VideoPlay /></el-icon>
          {{ t('complianceRunCheck') }}
        </button>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content-area">
      <!-- 配置审核区域 -->
      <section class="compliance-section">
        <div class="section-header">
          <span class="section-title">{{ t('complianceRecentResults') }}</span>
          <div class="section-actions" v-if="report">
            <button class="action-btn small primary" @click="showConfigDetailDialog" v-if="auditConfigText">
              <el-icon><Document /></el-icon>
              {{ t('complianceViewConfigDetail') }}
            </button>
            <button class="action-btn small" @click="clearResults">
              <el-icon><Delete /></el-icon>
              {{ t('actionClear') }}
            </button>
          </div>
        </div>

        <div class="results-panel">
          <el-empty v-if="!report" :description="t('complianceNotRunYet')" />

          <template v-else>
            <!-- 统计概览 -->
            <div class="stats-overview">
              <div class="stats-grid">
                <div class="stats-item">
                  <div class="stats-label">{{ t('complianceTotalChecks') }}</div>
                  <div class="stats-value">{{ report.total_checks }}</div>
                </div>
                <div class="stats-item success">
                  <div class="stats-label">{{ t('compliancePassed') }}</div>
                  <div class="stats-value">{{ report.passed }}</div>
                </div>
                <div class="stats-item error">
                  <div class="stats-label">{{ t('complianceFailed') }}</div>
                  <div class="stats-value">{{ report.failed }}</div>
                </div>
                <div class="stats-item score">
                  <div class="stats-label">{{ t('complianceScore') }}</div>
                  <div class="stats-value">{{ report.compliance_score }}%</div>
                </div>
                <div class="stats-item ai" v-if="report.ai_score">
                  <div class="stats-label">{{ t('complianceAIScore') }}</div>
                  <div class="stats-value">{{ report.ai_score }}</div>
                </div>
              </div>
            </div>

            <!-- AI 洞察 -->
            <div class="ai-insights-panel" v-if="report.ai_insights">
              <div class="insights-header">
                <el-icon><MagicStick /></el-icon>
                <span>{{ t('complianceAIInsights') }}</span>
              </div>
              <div class="insights-content">{{ report.ai_insights }}</div>
            </div>

            <!-- 结果列表 -->
            <div class="results-list">
              <div
                v-for="result in report.results"
                :key="result.check_id"
                class="result-card"
                :class="result.passed ? 'passed' : 'failed'"
              >
                <div class="result-header">
                  <span class="result-id">{{ result.check_id }}</span>
                  <span class="result-name">{{ result.check_name }}</span>
                  <span class="result-status" :class="result.passed ? 'passed' : 'failed'">
                    {{ result.passed ? t('compliancePassStatus') : t('complianceFailStatus') }}
                  </span>
                </div>
                <div class="result-meta">
                  <el-tag :type="categoryType(result.category)" size="small">{{ result.category }}</el-tag>
                  <el-tag :type="severityType(result.severity)" size="small">{{ result.severity }}</el-tag>
                </div>
                <div class="result-detail" v-if="result.detail">
                  <span class="detail-label">{{ t('complianceDetail') }}:</span>
                  <span class="detail-text">{{ result.detail }}</span>
                </div>
                <div class="result-recommendation" v-if="result.recommendation">
                  <span class="recommendation-label">{{ t('complianceRecommendation') }}:</span>
                  <span class="recommendation-text">{{ result.recommendation }}</span>
                </div>
                <!-- AI 深度分析 -->
                <div class="ai-analysis-panel" v-if="result.ai_analysis">
                  <div class="ai-header">
                    <el-icon><MagicStick /></el-icon>
                    <span>{{ t('complianceAIAnalysis') }}</span>
                  </div>
                  <div class="ai-content">{{ result.ai_analysis }}</div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </section>

      <!-- 标准文档管理 -->
      <section class="compliance-section">
        <div class="section-header">
          <span class="section-title">{{ t('complianceStandardsTitle') }}</span>
          <div class="section-actions">
            <button class="action-btn small" @click="showUploadStandardDialog">
              <el-icon><Upload /></el-icon>
              {{ t('complianceStandardUpload') }}
            </button>
            <button class="action-btn small" @click="showCreateStandardDialog">
              <el-icon><Plus /></el-icon>
              {{ t('complianceStandardCreate') }}
            </button>
          </div>
        </div>

        <div class="standards-panel" v-loading="standardsLoading">
          <el-empty v-if="standards.length === 0 && !standardsLoading" :description="t('complianceNoStandards')" />

          <el-table v-else :data="standards" style="width: 100%" size="small">
            <el-table-column prop="name" :label="t('complianceStandardName')" min-width="150">
              <template #default="{ row }">
                <span class="standard-name clickable" @click="viewStandardDetail(row)">{{ row.name }}</span>
                <el-tag v-if="row.is_active" type="success" size="small">{{ t('statusActive') }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="version" :label="t('complianceStandardVersion')" width="100" />
            <el-table-column prop="rule_count" :label="t('complianceRuleCount')" width="80" align="center" />
            <el-table-column prop="updated_at" :label="t('colUpdatedAt')" width="160">
              <template #default="{ row }">
                {{ formatTime(row.updated_at) }}
              </template>
            </el-table-column>
            <el-table-column :label="t('colActions')" width="240" align="center">
              <template #default="{ row }">
                <button class="table-action-btn primary" @click="viewStandardDetail(row)">
                  <el-icon><View /></el-icon>
                  {{ t('complianceStandardViewBtn') }}
                </button>
                <button class="table-action-btn" @click="showRulesDialog(row)">
                  <el-icon><List /></el-icon>
                  {{ t('complianceRulesTitle') }}
                </button>
                <button class="table-action-btn" @click="generateRules(row.id)" :disabled="generatingRules">
                  <el-icon v-if="generatingRules" class="is-loading"><Loading /></el-icon>
                  <el-icon v-else><MagicStick /></el-icon>
                  {{ t('complianceGenerateRules') }}
                </button>
                <button class="table-action-btn danger" @click="deleteStandard(row.id)">
                  <el-icon><Delete /></el-icon>
                </button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </section>
    </div>

    <!-- AI 审核对话框 -->
    <AuditDialog
      v-model="auditDialogVisible"
      v-model:config-text="auditConfigText"
      :has-ai-permission="hasAIPermission"
      :ai-configured="aiConfigured"
      @completed="onAuditCompleted"
    />

    <!-- AI 配置对话框 -->
    <AIConfigDialog v-model="aiConfigDialogVisible" :ai-config="aiConfig" @saved="loadAIConfig" />

    <!-- 上传标准文档对话框 -->
    <UploadStandardDialog v-model="uploadStandardDialogVisible" @uploaded="loadStandards" />

    <!-- 创建标准文档对话框 -->
    <CreateStandardDialog v-model="createStandardDialogVisible" @created="loadStandards" />

    <!-- 规则列表对话框 -->
    <RulesDialog
      v-model="rulesDialogVisible"
      :rules="rules"
      :loading="rulesLoading"
      @view-rule="showRuleDetail"
      @toggle-status="toggleRuleStatus"
    />

    <!-- 规则详情对话框 -->
    <RuleDetailDialog v-model="ruleDetailVisible" :current-rule="currentRule" @toggle-status="toggleRuleStatus" />

    <!-- 标准文档详情对话框 -->
    <StandardDetailDialog
      v-model="standardDetailVisible"
      :standard="detailStandard"
      v-model:generating-rules="generatingRules"
      @rules-generated="loadStandards"
    />

    <!-- 配置问题高亮对话框 -->
    <ConfigDetailDialog v-model="configDetailVisible" :report="report" :config-text="auditConfigText" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document, VideoPlay, Loading, Setting, Upload, Plus, Delete,
  MagicStick, List, View
} from '@element-plus/icons-vue'
import {
  getRules, updateRuleStatus, getAIConfig, checkPermission
} from '@/api'
import { useI18n } from '@/composables/useI18n'
import { useComplianceStandards } from '@/composables/useComplianceStandards'
import UploadStandardDialog from '@/components/UploadStandardDialog.vue'
import CreateStandardDialog from '@/components/CreateStandardDialog.vue'
import RulesDialog from '@/components/RulesDialog.vue'
import StandardDetailDialog from '@/components/StandardDetailDialog.vue'
import AuditDialog from '@/components/AuditDialog.vue'
import AIConfigDialog from '@/components/AIConfigDialog.vue'
import RuleDetailDialog from '@/components/RuleDetailDialog.vue'
import ConfigDetailDialog from '@/components/ConfigDetailDialog.vue'
import { categoryType, severityType } from '@/utils/compliance.js'

const { t } = useI18n()

// 标准文档列表状态（请求与状态收拢于 composable）
const {
  standards, standardsLoading, currentStandardId, generatingRules,
  loadStandards, generateRules, deleteStandard
} = useComplianceStandards()

// 状态
const report = ref(null)
const auditDialogVisible = ref(false)
const aiConfigDialogVisible = ref(false)
const uploadStandardDialogVisible = ref(false)
const createStandardDialogVisible = ref(false)
const rulesDialogVisible = ref(false)
const standardDetailVisible = ref(false)
const configDetailVisible = ref(false)
const ruleDetailVisible = ref(false)
const detailStandard = ref(null)
const auditConfigText = ref('')

const rulesLoading = ref(false)
const currentRule = ref(null)

// 数据
const rules = ref([])
const aiConfig = ref({ configured: false })

// AI 权限
const hasAIPermission = ref(true)
const hasAIConfigPermission = ref(true)

// 计算属性
const aiConfigured = computed(() => aiConfig.value.configured === true)

// 辅助函数
const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

// 审核完成：写入报告
const onAuditCompleted = (payload) => {
  report.value = payload
}

// 加载 AI 配置
const loadAIConfig = async () => {
  try {
    const data = await getAIConfig()
    aiConfig.value = data
  } catch (e) {
    console.error('Failed to load AI config:', e)
  }
}

// 显示审核对话框
const showAuditDialog = () => {
  auditDialogVisible.value = true
}

// 显示 AI 配置对话框
const showAIConfigDialog = () => {
  aiConfigDialogVisible.value = true
}

// 显示上传标准文档对话框
const showUploadStandardDialog = () => {
  uploadStandardDialogVisible.value = true
}

// 显示创建标准文档对话框
const showCreateStandardDialog = () => {
  createStandardDialogVisible.value = true
}

// 显示规则列表对话框
const showRulesDialog = async (standard) => {
  currentStandardId.value = standard.id
  rulesLoading.value = true
  rulesDialogVisible.value = true
  try {
    const data = await getRules(standard.id)
    rules.value = data.rules || []
  } catch (e) {
    ElMessage.error(t('loadFailed'))
  } finally {
    rulesLoading.value = false
  }
}

// 显示规则详情
const showRuleDetail = (rule) => {
  currentRule.value = rule
  ruleDetailVisible.value = true
}

// 切换规则状态
const toggleRuleStatus = async (ruleId, isActive) => {
  try {
    await updateRuleStatus(ruleId, isActive)
    // 更新本地规则列表中的状态
    const idx = rules.value.findIndex(r => r.id === ruleId)
    if (idx !== -1) {
      rules.value[idx].is_active = isActive
    }
    // 如果当前正在查看规则详情，也更新当前规则状态
    if (currentRule.value && currentRule.value.id === ruleId) {
      currentRule.value.is_active = isActive
    }
    ElMessage.success(t('saveSuccess'))
  } catch (e) {
    // 恢复原状态
    const idx = rules.value.findIndex(r => r.id === ruleId)
    if (idx !== -1) {
      rules.value[idx].is_active = !isActive
    }
    ElMessage.error(t('saveFailed'))
  }
}

// 清除结果
const clearResults = () => {
  report.value = null
}

// 检查 AI 权限
const checkAIPermissions = async () => {
  try {
    const result = await checkPermission('ai:use')
    hasAIPermission.value = result.has_permission

    const configResult = await checkPermission('ai:config')
    hasAIConfigPermission.value = configResult.has_permission
  } catch (e) {
    // 权限检查失败时默认允许（可能是认证关闭）
    hasAIPermission.value = true
    hasAIConfigPermission.value = true
  }
}

// ==================== 标准文档详情查看 ====================

// 查看标准文档详情（详情加载与解析在 StandardDetailDialog 子组件内完成）
const viewStandardDetail = (standard) => {
  detailStandard.value = standard
  standardDetailVisible.value = true
}

// ==================== 配置问题高亮展示 ====================

// 打开配置详情对话框（分析构建在 ConfigDetailDialog 子组件内完成）
const showConfigDetailDialog = () => {
  if (!report.value) {
    ElMessage.warning(t('complianceNotRunYet'))
    return
  }
  configDetailVisible.value = true
}

// 初始化
onMounted(() => {
  loadAIConfig()
  loadStandards()
  checkAIPermissions()
})

</script>

<style scoped>
/* ========================================
   使用全局 Theme Token
   ======================================== */

.compliance-page {
  padding: 0;
  background: var(--bg-primary);
}

/* ========================================
   页面导航栏
   ======================================== */

.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--gap-md);
}

.nav-left {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.nav-right {
  display: flex;
  gap: 10px;
}

/* ========================================
   按钮系统
   ======================================== */

.nav-action-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: none;
  background: var(--bg-card);
  color: var(--text-secondary);
}

.nav-action-btn .el-icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

.nav-action-btn.deploy-btn {
  background: var(--accent-primary);
  color: white;
  border: none;
}

.nav-action-btn.deploy-btn:hover:not(:disabled) {
  background: #00a884;
  box-shadow: 0 2px 6px rgba(0, 184, 148, 0.2);
  transform: translateY(-1px);
}

.nav-action-btn.deploy-btn:disabled {
  background: rgba(0, 184, 148, 0.4);
  cursor: not-allowed;
}

.nav-action-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.table-action-btn {
  height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
}

.table-action-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.table-action-btn.danger:hover {
  color: var(--accent-danger);
}

.action-btn.small {
  height: 24px;
  padding: 0 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  border: 1px solid var(--border-default);
  background: transparent;
  color: var(--text-secondary);
}

.action-btn.small:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--text-primary);
}

/* Loading 动画 */
.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ========================================
   主内容区域
   ======================================== */

.main-content-area {
  display: flex;
  flex-direction: column;
  gap: var(--gap-lg);
}

/* ========================================
   合规检查区块
   ======================================== */

.compliance-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--gap-md);
  box-shadow: var(--shadow-card);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
  margin-bottom: var(--gap-md);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.section-actions {
  display: flex;
  gap: 8px;
}

/* ========================================
   结果面板
   ======================================== */

.results-panel {
  min-height: 200px;
}

/* ========================================
   统计概览
   ======================================== */

.stats-overview {
  margin-bottom: var(--gap-lg);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--gap-md);
}

.stats-item {
  background: var(--bg-hover);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
  transition: all 0.15s ease;
}

.stats-item:hover {
  transform: translateY(-1px);
}

.stats-item.success {
  background: var(--success-bg);
  border-color: rgba(0, 184, 148, 0.3);
}

.stats-item.error {
  background: var(--error-bg);
  border-color: rgba(214, 48, 49, 0.3);
}

.stats-item.score {
  background: rgba(9, 132, 227, 0.08);
  border-color: rgba(9, 132, 227, 0.2);
}

.stats-item.ai {
  background: rgba(102, 126, 234, 0.08);
  border-color: rgba(102, 126, 234, 0.2);
}

.stats-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.stats-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.stats-item.success .stats-value {
  color: var(--accent-primary);
}

.stats-item.error .stats-value {
  color: var(--accent-danger);
}

.stats-item.score .stats-value {
  color: var(--accent-secondary);
}

.stats-item.ai .stats-value {
  color: #667eea;
}

/* ========================================
   AI 洞察面板
   ======================================== */

.ai-insights-panel {
  background: rgba(102, 126, 234, 0.05);
  border: 1px solid rgba(102, 126, 234, 0.15);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  margin-bottom: var(--gap-lg);
}

.insights-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
  margin-bottom: var(--gap-sm);
}

.insights-content {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
}

/* ========================================
   结果列表
   ======================================== */

.results-list {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.result-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
  transition: all 0.15s ease;
}

.result-card:hover {
  border-color: var(--accent-secondary);
}

.result-card.passed {
  border-color: rgba(0, 184, 148, 0.2);
}

.result-card.failed {
  border-color: rgba(214, 48, 49, 0.2);
}

.result-header {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  margin-bottom: var(--gap-sm);
}

.result-id {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  padding: 2px 6px;
  background: var(--bg-hover);
  border-radius: 4px;
}

.result-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  flex: 1;
}

.result-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
}

.result-status.passed {
  background: rgba(0, 184, 148, 0.1);
  color: var(--accent-primary);
}

.result-status.failed {
  background: rgba(214, 48, 49, 0.1);
  color: var(--accent-danger);
}

.result-meta {
  display: flex;
  gap: var(--gap-sm);
  margin-bottom: var(--gap-sm);
}

.result-detail,
.result-recommendation {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-top: var(--gap-xs);
}

.detail-label,
.recommendation-label {
  font-weight: 500;
  color: var(--text-tertiary);
}

.detail-text,
.recommendation-text {
  margin-left: var(--gap-xs);
}

/* AI 分析面板 */
.ai-analysis-panel {
  margin-top: var(--gap-sm);
  background: rgba(102, 126, 234, 0.05);
  border: 1px solid rgba(102, 126, 234, 0.15);
  border-radius: var(--radius-sm);
  padding: var(--gap-sm) var(--gap-md);
}

.ai-header {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  font-size: 12px;
  font-weight: 600;
  color: #667eea;
  margin-bottom: var(--gap-xs);
}

.ai-content {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* ========================================
   标准文档面板
   ======================================== */

.standards-panel {
  min-height: 120px;
}

.standard-name {
  font-weight: 500;
  color: var(--text-primary);
}







/* ========================================
   暗色模式
   ======================================== */


.dark .stats-item {
  background: var(--bg-tertiary);
}

.dark .stats-item.success {
  background: rgba(0, 184, 148, 0.1);
}

.dark .stats-item.error {
  background: rgba(214, 48, 49, 0.1);
}

.dark .stats-item.ai {
  background: rgba(102, 126, 234, 0.1);
}

.dark .result-card {
  background: var(--bg-tertiary);
}

.dark .ai-insights-panel {
  background: rgba(102, 126, 234, 0.08);
}

.dark .ai-analysis-panel {
  background: rgba(102, 126, 234, 0.08);
}



/* 按钮样式增强 */
.action-btn.small.primary {
  background: rgba(9, 132, 227, 0.1);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.action-btn.small.primary:hover {
  background: rgba(9, 132, 227, 0.15);
}

.table-action-btn.primary {
  color: var(--accent-secondary);
}

.table-action-btn.primary:hover {
  background: rgba(9, 132, 227, 0.1);
}

.standard-name.clickable {
  cursor: pointer;
  transition: color 0.15s ease;
}

.standard-name.clickable:hover {
  color: var(--accent-secondary);
}

/* ========================================
   暗色模式补充
   ======================================== */


/* ========================================
   规则详情对话框
   ======================================== */


.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}



</style>