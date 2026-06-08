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
            <button class="action-btn small primary" @click="showConfigDetailDialog" v-if="auditForm.config_text">
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
    <el-dialog
      v-model="auditDialogVisible"
      :title="t('complianceRunCheck')"
      width="700px"
      append-to-body
      draggable
      align-center
      class="compliance-dialog"
    >
      <el-tabs v-model="auditTab" class="audit-tabs">
        <!-- 文件上传 -->
        <el-tab-pane name="upload" :label="t('complianceUploadConfig')">
          <div class="upload-area">
            <el-upload
              ref="uploadRef"
              :auto-upload="false"
              :limit="1"
              :on-change="handleFileChange"
              :on-exceed="handleExceed"
              accept=".txt,.cfg,.log,.xlsx,.xls,.conf"
              drag
              class="config-upload"
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">
                {{ t('complianceUploadConfigHint') }}
              </div>
            </el-upload>

            <!-- 文件解析结果 -->
            <div class="parse-result" v-if="parseResult">
              <div class="parse-info">
                <span class="info-item">
                  <span class="label">{{ t('complianceHostname') }}:</span>
                  <span class="value">{{ parseResult.hostname || '-' }}</span>
                </span>
                <span class="info-item">
                  <span class="label">{{ t('complianceDeviceType') }}:</span>
                  <span class="value">{{ parseResult.device_type }}</span>
                </span>
                <span class="info-item">
                  <span class="label">{{ t('complianceConfigLines') }}:</span>
                  <span class="value">{{ parseResult.config_lines }}</span>
                </span>
                <span class="info-item" v-if="parseResult.device_count">
                  <span class="label">{{ t('complianceDeviceCount') }}:</span>
                  <span class="value">{{ parseResult.device_count }}</span>
                </span>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 手动输入 -->
        <el-tab-pane name="manual" :label="t('complianceManualInput')">
          <el-form :model="auditForm" label-width="100px" size="default" class="config-form">
            <div class="form-section">
              <div class="section-header">
                <el-icon><Connection /></el-icon>
                <span>{{ t('complianceDeviceSection') }}</span>
              </div>
              <el-form-item :label="t('complianceDeviceName')">
                <el-input v-model="auditForm.device_name" />
              </el-form-item>
              <el-form-item :label="t('complianceDeviceIp')">
                <el-input v-model="auditForm.device_ip" />
              </el-form-item>
            </div>

            <div class="form-section">
              <div class="section-header">
                <el-icon><Document /></el-icon>
                <span>{{ t('complianceConfigSection') }}</span>
              </div>
              <el-form-item :label="t('complianceConfigText')">
                <el-input
                  v-model="auditForm.config_text"
                  type="textarea"
                  :rows="12"
                  :placeholder="t('complianceConfigPlaceholder')"
                  class="snippet-input"
                />
              </el-form-item>
            </div>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <!-- 审核选项 -->
      <div class="audit-options">
        <div class="option-row">
          <span class="option-label">{{ t('complianceAuditMode') }}</span>
          <el-radio-group v-model="auditForm.audit_mode" size="small">
            <el-radio-button value="full">{{ t('complianceAuditModeFull') }}</el-radio-button>
            <el-radio-button value="basic">{{ t('complianceAuditModeBasic') }}</el-radio-button>
            <el-radio-button value="ai_only">{{ t('complianceAuditModeAIOnly') }}</el-radio-button>
          </el-radio-group>
        </div>
        <div class="option-row" v-if="auditForm.audit_mode !== 'basic'">
          <el-checkbox v-model="auditForm.use_ai" :disabled="!hasAIPermission">{{ t('complianceUseAI') }}</el-checkbox>
          <span class="ai-config-status" v-if="!aiConfigured">
            <el-icon><Warning /></el-icon>
            {{ t('complianceAIConfigHint') }}
          </span>
          <span class="ai-config-status" v-if="!hasAIPermission">
            <el-icon><Warning /></el-icon>
            {{ t('aiPermissionNoPermission') }}
          </span>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="nav-action-btn secondary" @click="auditDialogVisible = false">
            {{ t('actionCancel') }}
          </button>
          <button class="nav-action-btn deploy-btn" @click="runAudit" :disabled="auditing">
            <el-icon v-if="auditing" class="is-loading"><Loading /></el-icon>
            {{ t('complianceRunCheck') }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- AI 配置对话框 -->
    <el-dialog
      v-model="aiConfigDialogVisible"
      :title="t('complianceAIConfigTitle')"
      width="500px"
      append-to-body
      draggable
      align-center
      class="compliance-dialog"
    >
      <div class="ai-config-status-bar" v-if="aiConfig.configured">
        <el-icon><CircleCheck /></el-icon>
        <span>{{ t('complianceAIConfigured') }} - {{ aiConfig.provider }} / {{ aiConfig.model_name }}</span>
      </div>

      <el-form :model="aiConfigForm" label-width="100px" size="default" class="config-form">
        <div class="form-section">
          <el-form-item :label="t('complianceAIProvider')">
            <el-select v-model="aiConfigForm.provider" style="width: 100%">
              <el-option value="openai" :label="t('complianceAIProviderOpenAI')" />
              <el-option value="anthropic" :label="t('complianceAIProviderAnthropic')" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('complianceAIApiKey')">
            <el-input v-model="aiConfigForm.api_key" type="password" show-password />
          </el-form-item>
          <el-form-item :label="t('complianceAIBaseUrl')">
            <el-input v-model="aiConfigForm.base_url" :placeholder="getDefaultUrl()" />
          </el-form-item>
          <el-form-item :label="t('complianceAIModel')">
            <el-input v-model="aiConfigForm.model_name" />
          </el-form-item>
          <el-form-item :label="t('complianceAITemperature')">
            <el-input-number v-model="aiConfigForm.temperature" :min="0" :max="2" :step="0.1" />
          </el-form-item>
          <el-form-item :label="t('complianceAIMaxTokens')">
            <el-input-number v-model="aiConfigForm.max_tokens" :min="100" :max="32000" :step="100" />
          </el-form-item>
          <el-form-item :label="t('complianceAITimeout')">
            <el-input-number v-model="aiConfigForm.timeout" :min="10" :max="300" :step="10" />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="aiConfigForm.is_default">{{ t('complianceAISetDefault') }}</el-checkbox>
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <button class="nav-action-btn secondary" @click="testAIConfig" :disabled="testingAI">
            <el-icon v-if="testingAI" class="is-loading"><Loading /></el-icon>
            {{ t('complianceAITest') }}
          </button>
          <button class="nav-action-btn deploy-btn" @click="saveAIConfig" :disabled="savingAIConfig">
            <el-icon v-if="savingAIConfig" class="is-loading"><Loading /></el-icon>
            {{ t('complianceAISaveConfig') }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 上传标准文档对话框 -->
    <el-dialog
      v-model="uploadStandardDialogVisible"
      :title="t('complianceStandardUpload')"
      width="500px"
      append-to-body
      draggable
      align-center
      class="compliance-dialog"
    >
      <el-upload
        ref="standardUploadRef"
        :auto-upload="false"
        :limit="1"
        :on-change="handleStandardFileChange"
        accept=".txt,.pdf,.md,.doc,.docx"
        drag
        class="config-upload"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          {{ t('complianceUploadConfigHint') }}
        </div>
      </el-upload>

      <template #footer>
        <div class="dialog-footer">
          <button class="nav-action-btn secondary" @click="uploadStandardDialogVisible = false">
            {{ t('actionCancel') }}
          </button>
          <button class="nav-action-btn deploy-btn" @click="uploadStandardDocument" :disabled="uploadingStandard">
            <el-icon v-if="uploadingStandard" class="is-loading"><Loading /></el-icon>
            {{ t('complianceStandardUpload') }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 创建标准文档对话框 -->
    <el-dialog
      v-model="createStandardDialogVisible"
      :title="t('complianceStandardCreate')"
      width="600px"
      append-to-body
      draggable
      align-center
      class="compliance-dialog"
    >
      <el-form :model="standardForm" label-width="100px" size="default" class="config-form">
        <el-form-item :label="t('complianceStandardName')">
          <el-input v-model="standardForm.name" />
        </el-form-item>
        <el-form-item :label="t('complianceStandardVersion')">
          <el-input v-model="standardForm.version" />
        </el-form-item>
        <el-form-item :label="t('complianceStandardDesc')">
          <el-input v-model="standardForm.description" />
        </el-form-item>
        <el-form-item :label="t('complianceStandardContent')">
          <el-input
            v-model="standardForm.content"
            type="textarea"
            :rows="10"
            :placeholder="t('complianceStandardContent')"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <button class="nav-action-btn secondary" @click="createStandardDialogVisible = false">
            {{ t('actionCancel') }}
          </button>
          <button class="nav-action-btn deploy-btn" @click="createStandard" :disabled="creatingStandard">
            <el-icon v-if="creatingStandard" class="is-loading"><Loading /></el-icon>
            {{ t('complianceStandardCreate') }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 规则列表对话框 -->
    <el-dialog
      v-model="rulesDialogVisible"
      :title="t('complianceRulesTitle')"
      width="800px"
      append-to-body
      draggable
      align-center
      class="compliance-dialog"
    >
      <div class="rules-panel" v-loading="rulesLoading">
        <el-empty v-if="rules.length === 0 && !rulesLoading" :description="t('complianceNoRules')" />

        <el-table v-else :data="rules" style="width: 100%" size="small">
          <el-table-column prop="rule_id" :label="t('complianceRuleId')" width="100">
            <template #default="{ row }">
              <span class="rule-id-link" @click="showRuleDetail(row)">{{ row.rule_id }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="name" :label="t('complianceRuleName')" min-width="150">
            <template #default="{ row }">
              <span class="rule-name-link" @click="showRuleDetail(row)">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="category" :label="t('complianceCategory')" width="100">
            <template #default="{ row }">
              <el-tag :type="categoryType(row.category)" size="small">{{ row.category }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="severity" :label="t('complianceSeverity')" width="80">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source_type" :label="t('complianceRuleSource')" width="100">
            <template #default="{ row }">
              <el-tag :type="row.source_type === 'auto' ? 'success' : 'info'" size="small">
                {{ row.source_type === 'auto' ? t('complianceRuleSourceAuto') : t('complianceRuleSourceManual') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('colActions')" width="120" align="center">
            <template #default="{ row }">
              <button class="table-action-btn primary" @click="showRuleDetail(row)">
                <el-icon><View /></el-icon>
                {{ t('complianceStandardViewBtn') }}
              </button>
              <el-switch
                v-model="row.is_active"
                size="small"
                @change="toggleRuleStatus(row.id, row.is_active)"
              />
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 规则详情对话框 -->
    <el-dialog
      v-model="ruleDetailVisible"
      :title="t('complianceRulesTitle') + ' - ' + (currentRule?.rule_id || '')"
      width="650px"
      append-to-body
      draggable
      align-center
      class="compliance-dialog rule-detail-dialog"
    >
      <div class="rule-detail-content" v-if="currentRule">
        <!-- 编辑模式切换 -->
        <div class="edit-mode-bar">
          <el-checkbox v-model="ruleEditMode" @change="onEditModeChange">
            {{ t('complianceRuleEditMode') }}
          </el-checkbox>
        </div>

        <!-- 规则头部信息 -->
        <div class="rule-header-section">
          <div class="rule-title-row" v-if="!ruleEditMode">
            <span class="rule-id-badge">{{ currentRule.rule_id }}</span>
            <span class="rule-name-text">{{ currentRule.name }}</span>
          </div>
          <div class="rule-title-row" v-else>
            <span class="rule-id-badge">{{ currentRule.rule_id }}</span>
            <el-input v-model="ruleEditForm.name" class="rule-name-input" />
          </div>
          <div class="rule-meta-row" v-if="!ruleEditMode">
            <el-tag :type="categoryType(currentRule.category)" size="small">{{ currentRule.category }}</el-tag>
            <el-tag :type="severityType(currentRule.severity)" size="small">{{ currentRule.severity }}</el-tag>
            <el-tag :type="currentRule.source_type === 'auto' ? 'success' : 'info'" size="small">
              {{ currentRule.source_type === 'auto' ? t('complianceRuleSourceAuto') : t('complianceRuleSourceManual') }}
            </el-tag>
          </div>
          <div class="rule-meta-row" v-else>
            <el-select v-model="ruleEditForm.category" size="small" style="width: 120px">
              <el-option value="security" :label="t('complianceCategorySecurity')" />
              <el-option value="availability" :label="t('complianceCategoryAvailability')" />
              <el-option value="compliance" :label="t('complianceCategoryCompliance')" />
            </el-select>
            <el-select v-model="ruleEditForm.severity" size="small" style="width: 100px">
              <el-option value="critical" label="critical" />
              <el-option value="high" label="high" />
              <el-option value="medium" label="medium" />
              <el-option value="low" label="low" />
            </el-select>
          </div>
        </div>

        <!-- 匹配模式 -->
        <div class="rule-section">
          <div class="section-title">{{ t('complianceRulePattern') }}</div>
          <div class="pattern-box" v-if="!ruleEditMode">
            <code class="pattern-code">{{ currentRule.pattern || t('valueNa') }}</code>
          </div>
          <el-input v-else v-model="ruleEditForm.pattern" type="textarea" :rows="2" class="edit-input" />
        </div>

        <!-- 检查逻辑 -->
        <div class="rule-section">
          <div class="section-title">{{ t('complianceRuleLogic') }}</div>
          <div class="logic-text" v-if="!ruleEditMode">{{ currentRule.check_logic || t('valueNa') }}</div>
          <el-input v-else v-model="ruleEditForm.check_logic" type="textarea" :rows="3" class="edit-input" />
        </div>

        <!-- 修复建议 -->
        <div class="rule-section">
          <div class="section-title">{{ t('complianceFixRecommendation') }}</div>
          <div class="recommendation-box" v-if="!ruleEditMode">
            <pre class="recommendation-code">{{ currentRule.recommendation || t('valueNa') }}</pre>
          </div>
          <el-input v-else v-model="ruleEditForm.recommendation" type="textarea" :rows="4" class="edit-input" />
        </div>

        <!-- 规则状态 -->
        <div class="rule-status-section">
          <span class="status-label">{{ t('complianceRuleEnabled') }}:</span>
          <el-switch
            v-if="!ruleEditMode"
            v-model="currentRule.is_active"
            @change="toggleRuleStatus(currentRule.id, currentRule.is_active)"
          />
          <el-switch
            v-else
            v-model="ruleEditForm.is_active"
          />
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="nav-action-btn secondary" @click="ruleDetailVisible = false" v-if="!ruleEditMode">
            {{ t('actionCancel') }}
          </button>
          <button class="nav-action-btn secondary" @click="cancelEdit" v-if="ruleEditMode">
            {{ t('actionCancel') }}
          </button>
          <button class="nav-action-btn deploy-btn" @click="saveRuleEdit" :disabled="savingRule" v-if="ruleEditMode">
            <el-icon v-if="savingRule" class="is-loading"><Loading /></el-icon>
            {{ t('save') }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 标准文档详情对话框 -->
    <el-dialog
      v-model="standardDetailVisible"
      :title="t('complianceStandardDetail')"
      width="900px"
      append-to-body
      draggable
      align-center
      class="compliance-dialog standard-detail-dialog"
    >
      <div class="standard-meta-bar" v-if="currentStandardDetail">
        <span class="meta-item">
          <span class="meta-label">{{ t('complianceStandardName') }}:</span>
          <span class="meta-value">{{ currentStandardDetail.name }}</span>
        </span>
        <span class="meta-item">
          <span class="meta-label">{{ t('complianceStandardVersion') }}:</span>
          <span class="meta-value">v{{ currentStandardDetail.version }}</span>
        </span>
        <span class="meta-item">
          <span class="meta-label">{{ t('complianceRuleCount') }}:</span>
          <span class="meta-value">{{ currentStandardDetail.rules?.length || 0 }}</span>
        </span>
        <el-tag v-if="currentStandardDetail.is_active" type="success" size="small">{{ t('statusActive') }}</el-tag>
      </div>

      <div class="standard-detail-layout" v-loading="standardDetailLoading">
        <!-- 左侧目录 -->
        <div class="standard-toc">
          <div class="toc-title">{{ t('complianceStandardToc') }}</div>
          <div class="toc-list">
            <div
              v-for="(section, index) in documentSections"
              :key="index"
              class="toc-item"
              :class="{ active: activeSectionIndex === index }"
              @click="scrollToSection(index)"
            >
              <span class="toc-number">{{ section.number }}</span>
              <span class="toc-text">{{ section.title }}</span>
            </div>
          </div>
        </div>

        <!-- 右侧内容 -->
        <div class="standard-content" ref="standardContentRef">
          <div v-if="!currentStandardDetail?.content" class="empty-content">
            {{ t('complianceStandardNoContent') }}
          </div>
          <div v-else class="markdown-content">
            <div
              v-for="(section, index) in documentSections"
              :key="index"
              class="section-block"
              :ref="el => sectionRefs[index] = el"
            >
              <h2 class="section-heading" :id="'section-' + index">
                <span class="section-number">{{ section.number }}</span>
                {{ section.title }}
              </h2>
              <div class="section-body" v-html="renderSectionContent(section.content)"></div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <button class="nav-action-btn deploy-btn" @click="generateRulesForStandardDetail" :disabled="generatingRules">
            <el-icon v-if="generatingRules" class="is-loading"><Loading /></el-icon>
            <el-icon v-else><MagicStick /></el-icon>
            {{ t('complianceGenerateRules') }}
          </button>
          <button class="nav-action-btn secondary" @click="standardDetailVisible = false">
            {{ t('actionCancel') }}
          </button>
        </div>
      </template>
    </el-dialog>

    <!-- 配置问题高亮对话框 -->
    <el-dialog
      v-model="configDetailVisible"
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
              :key="index"
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Connection, Document, VideoPlay, Loading, Setting, Upload, Plus, Delete,
  UploadFilled, MagicStick, List, CircleCheck, Warning, WarningFilled, View
} from '@element-plus/icons-vue'
import {
  uploadConfigFile, runComplianceCheck,
  getStandards, getStandard, createStandard as createStandardApi, updateStandard, deleteStandard as deleteStandardApi,
  uploadStandardDocument as uploadStandardDocumentApi, generateRulesForStandard,
  getRules, getRuleDetail, updateRuleStatus, updateRule,
  getAIConfig, createAIConfig as createAIConfigApi, updateAIConfig as updateAIConfigApi, testAIConfig as testAIConfigApi,
  checkPermission
} from '@/api'
import { useI18n } from '@/composables/useI18n'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

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

const auditing = ref(false)
const testingAI = ref(false)
const savingAIConfig = ref(false)
const uploadingStandard = ref(false)
const creatingStandard = ref(false)
const generatingRules = ref(false)
const standardsLoading = ref(false)
const rulesLoading = ref(false)
const standardDetailLoading = ref(false)

// 规则详情
const currentRule = ref(null)
const ruleEditMode = ref(false)
const ruleEditForm = reactive({
  name: '',
  category: '',
  severity: '',
  pattern: '',
  check_logic: '',
  recommendation: '',
  is_active: true
})
const savingRule = ref(false)

// 标准文档详情相关
const currentStandardDetail = ref(null)
const documentSections = ref([])
const activeSectionIndex = ref(0)
const standardContentRef = ref(null)
const sectionRefs = ref([])

// 配置问题高亮相关
const configDetailConfigText = ref('')
const configLineAnalysis = ref([])
const selectedLine = ref(null)
const configLinesRef = ref(null)

const auditTab = ref('upload')
const uploadRef = ref(null)
const standardUploadRef = ref(null)
const currentFile = ref(null)
const parseResult = ref(null)

// 表单
const auditForm = reactive({
  device_name: '',
  device_ip: '',
  config_text: '',
  audit_mode: 'full',
  use_ai: true
})

const aiConfigForm = reactive({
  provider: 'openai',
  api_key: '',
  base_url: '',
  model_name: 'gpt-4',
  temperature: 0.7,
  max_tokens: 4096,
  timeout: 120,  // 默认120秒超时
  is_default: true
})

const standardForm = reactive({
  name: '',
  version: '1.0',
  description: '',
  content: ''
})

// 数据
const standards = ref([])
const rules = ref([])
const aiConfig = ref({ configured: false })
const currentStandardId = ref(null)

// AI 权限
const hasAIPermission = ref(true)
const hasAIConfigPermission = ref(true)

// 计算属性
const aiConfigured = computed(() => aiConfig.value.configured === true)

// 辅助函数
const categoryType = (cat) => ({ security: 'danger', availability: 'warning', compliance: 'info' }[cat] || '')
const severityType = (sev) => ({ critical: 'danger', high: 'warning', medium: 'info', low: '' }[sev] || '')

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

const getDefaultUrl = () => {
  if (aiConfigForm.provider === 'openai') {
    return 'https://api.openai.com/v1'
  } else if (aiConfigForm.provider === 'anthropic') {
    return 'https://api.anthropic.com/v1'
  }
  return ''
}

// 加载 AI 配置
const loadAIConfig = async () => {
  try {
    const data = await getAIConfig()
    aiConfig.value = data
    if (data.configured) {
      aiConfigForm.provider = data.provider || 'openai'
      aiConfigForm.base_url = data.base_url || ''
      aiConfigForm.model_name = data.model_name || 'gpt-4'
      aiConfigForm.temperature = data.temperature || 0.7
      aiConfigForm.max_tokens = data.max_tokens || 4096
      aiConfigForm.timeout = data.timeout || 120  // 如果未设置，使用120秒默认值
      aiConfigForm.is_default = data.is_default || true
    }
  } catch (e) {
    console.error('Failed to load AI config:', e)
  }
}

// 加载标准文档列表
const loadStandards = debounce(async (force = false) => {
  standardsLoading.value = true
  try {
    const data = await getStandards()
    standards.value = data.standards || []
  } catch (e) {
    ElMessage.error(t('loadFailed'))
  } finally {
    standardsLoading.value = false
  }
}, 300)

// 显示审核对话框
const showAuditDialog = () => {
  auditTab.value = 'upload'
  currentFile.value = null
  parseResult.value = null
  auditForm.device_name = ''
  auditForm.device_ip = ''
  auditForm.config_text = ''
  auditForm.audit_mode = 'full'
  auditForm.use_ai = true
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
  standardForm.name = ''
  standardForm.version = '1.0'
  standardForm.description = ''
  standardForm.content = ''
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
  ruleEditMode.value = false
  // 初始化编辑表单
  ruleEditForm.name = rule.name
  ruleEditForm.category = rule.category
  ruleEditForm.severity = rule.severity
  ruleEditForm.pattern = rule.pattern || ''
  ruleEditForm.check_logic = rule.check_logic || ''
  ruleEditForm.recommendation = rule.recommendation || ''
  ruleEditForm.is_active = rule.is_active
  ruleDetailVisible.value = true
}

// 编辑模式切换
const onEditModeChange = (val) => {
  if (val && currentRule.value) {
    // 进入编辑模式，重新初始化表单
    ruleEditForm.name = currentRule.value.name
    ruleEditForm.category = currentRule.value.category
    ruleEditForm.severity = currentRule.value.severity
    ruleEditForm.pattern = currentRule.value.pattern || ''
    ruleEditForm.check_logic = currentRule.value.check_logic || ''
    ruleEditForm.recommendation = currentRule.value.recommendation || ''
    ruleEditForm.is_active = currentRule.value.is_active
  }
}

// 取消编辑
const cancelEdit = () => {
  ruleEditMode.value = false
}

// 保存规则编辑
const saveRuleEdit = async () => {
  savingRule.value = true
  try {
    const data = await updateRule(currentRule.value.id, {
      name: ruleEditForm.name,
      category: ruleEditForm.category,
      severity: ruleEditForm.severity,
      pattern: ruleEditForm.pattern,
      check_logic: ruleEditForm.check_logic,
      recommendation: ruleEditForm.recommendation,
      is_active: ruleEditForm.is_active
    })

    if (data.success) {
      ElMessage.success(t('saveSuccess'))
      // 更新当前规则显示
      currentRule.value = data.rule
      ruleEditMode.value = false
      // 更新规则列表
      const idx = rules.value.findIndex(r => r.id === currentRule.value.id)
      if (idx !== -1) {
        rules.value[idx] = { ...rules.value[idx], ...data.rule }
      }
    } else {
      ElMessage.error(t('saveFailed') + ': ' + data.error)
    }
  } catch (e) {
    ElMessage.error(t('saveFailed'))
  } finally {
    savingRule.value = false
  }
}

// 文件上传处理
const handleFileChange = (file) => {
  currentFile.value = file.raw
  parseResult.value = null
}

const handleExceed = () => {
  ElMessage.warning(t('uploadLimitExceeded'))
}

// 标准文档文件处理
const handleStandardFileChange = (file) => {
  currentFile.value = file.raw
}

// 运行审核
const runAudit = async () => {
  auditing.value = true

  try {
    // 文件上传模式
    if (auditTab.value === 'upload' && currentFile.value) {
      const formData = new FormData()
      formData.append('file', currentFile.value)

      const data = await uploadConfigFile(formData)
      parseResult.value = data.parse_result

      if (data.format === 'multi_device') {
        // 多设备批量审核结果
        report.value = {
          total_checks: data.device_count,
          passed: data.audit_results.filter(r => r.compliance_score >= 80).length,
          failed: data.audit_results.filter(r => r.compliance_score < 80).length,
          compliance_score: Math.round(data.audit_results.reduce((sum, r) => sum + r.compliance_score, 0) / data.device_count),
          results: data.audit_results.map(r => ({
            check_id: r.device_name,
            check_name: r.device_ip || r.device_name,
            category: 'compliance',
            severity: r.compliance_score >= 80 ? 'low' : 'high',
            passed: r.compliance_score >= 80,
            detail: `${t('complianceScore')}: ${r.compliance_score}%`,
            recommendation: ''
          })),
          audit_mode: 'batch'
        }
      } else {
        // 单设备审核结果
        report.value = data.audit_result
      }

      ElMessage.success(`${t('complianceCheckComplete')}: ${report.value.compliance_score}%`)
      auditDialogVisible.value = false
    } else {
      // 手动输入模式
      if (!auditForm.config_text.trim()) {
        ElMessage.warning(t('complianceConfigPlaceholder'))
        return
      }

      const data = await runComplianceCheck(auditForm)
      report.value = data
      ElMessage.success(`${t('complianceCheckComplete')}: ${data.compliance_score}%`)
      auditDialogVisible.value = false
    }
  } catch (e) {
    ElMessage.error(t('complianceCheckFailed') + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    auditing.value = false
  }
}

// 测试 AI 配置
const testAIConfig = async () => {
  if (!aiConfigForm.api_key) {
    ElMessage.warning(t('complianceAIApiKey') + ' required')
    return
  }

  testingAI.value = true
  try {
    const data = await testAIConfigApi(aiConfigForm)
    if (data.success) {
      ElMessage.success(t('complianceAITestSuccess'))
    } else {
      ElMessage.error(t('complianceAITestFailed') + ': ' + data.error)
    }
  } catch (e) {
    ElMessage.error(t('complianceAITestFailed'))
  } finally {
    testingAI.value = false
  }
}

// 保存 AI 配置
const saveAIConfig = async () => {
  if (!aiConfigForm.api_key) {
    ElMessage.warning(t('complianceAIApiKey') + ' required')
    return
  }

  savingAIConfig.value = true
  try {
    if (aiConfig.value.configured && aiConfig.value.id) {
      await updateAIConfigApi(aiConfig.value.id, aiConfigForm)
    } else {
      await createAIConfigApi(aiConfigForm)
    }
    ElMessage.success(t('saveSuccess'))
    aiConfigDialogVisible.value = false
    loadAIConfig()
  } catch (e) {
    ElMessage.error(t('saveFailed'))
  } finally {
    savingAIConfig.value = false
  }
}

// 上传标准文档
const uploadStandardDocument = async () => {
  if (!currentFile.value) {
    ElMessage.warning(t('selectFile'))
    return
  }

  uploadingStandard.value = true
  try {
    const formData = new FormData()
    formData.append('file', currentFile.value)

    await uploadStandardDocumentApi(formData)
    ElMessage.success(t('complianceStandardUpload') + ' ' + t('success'))
    uploadStandardDialogVisible.value = false
    loadStandards()
  } catch (e) {
    ElMessage.error(t('uploadFailed'))
  } finally {
    uploadingStandard.value = false
  }
}

// 创建标准文档
const createStandard = async () => {
  if (!standardForm.name || !standardForm.content) {
    ElMessage.warning(t('fieldRequired'))
    return
  }

  creatingStandard.value = true
  try {
    await createStandardApi(standardForm)
    ElMessage.success(t('complianceStandardCreate') + ' ' + t('success'))
    createStandardDialogVisible.value = false
    loadStandards()
  } catch (e) {
    ElMessage.error(t('saveFailed'))
  } finally {
    creatingStandard.value = false
  }
}

// 生成规则
const generateRules = async (standardId) => {
  generatingRules.value = true
  try {
    const data = await generateRulesForStandard(standardId)
    if (data.success) {
      ElMessage.success(`${t('complianceRulesGenerated')}: ${data.generated_count} rules`)
      loadStandards()
    } else {
      ElMessage.error(t('complianceRulesGenerateFailed') + ': ' + data.error)
    }
  } catch (e) {
    ElMessage.error(t('complianceRulesGenerateFailed'))
  } finally {
    generatingRules.value = false
  }
}

// 删除标准文档
const deleteStandard = async (standardId) => {
  try {
    await ElMessageBox.confirm(t('confirmDelete'), t('warning'), { type: 'warning' })
    await deleteStandardApi(standardId)
    ElMessage.success(t('deleteSuccess'))
    loadStandards()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(t('deleteFailed'))
    }
  }
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

// 查看标准文档详情
const viewStandardDetail = async (standard) => {
  standardDetailLoading.value = true
  standardDetailVisible.value = true

  try {
    const data = await getStandard(standard.id)
    currentStandardDetail.value = data

    // 解析文档章节
    parseDocumentSections(data.content || '')
  } catch (e) {
    ElMessage.error(t('loadFailed'))
    standardDetailVisible.value = false
  } finally {
    standardDetailLoading.value = false
  }
}

// 解析文档章节
const parseDocumentSections = (content) => {
  const sections = []
  const lines = content.split('\n')

  let currentSection = null
  let sectionContent = []

  // 解析标题结构（支持 ## 格式的 Markdown 标题）
  for (const line of lines) {
    const headingMatch = line.match(/^#{1,3}\s+(\d+(\.\d+)*\.?)?\s*(.+)/)
    if (headingMatch) {
      // 保存上一个章节
      if (currentSection) {
        currentSection.content = sectionContent.join('\n')
        sections.push(currentSection)
      }

      // 开始新章节
      currentSection = {
        number: headingMatch[2] || '',
        title: headingMatch[3].trim(),
        content: ''
      }
      sectionContent = []
    } else if (currentSection) {
      sectionContent.push(line)
    }
  }

  // 保存最后一个章节
  if (currentSection) {
    currentSection.content = sectionContent.join('\n')
    sections.push(currentSection)
  }

  // 如果没有解析到章节，创建一个默认章节
  if (sections.length === 0) {
    sections.push({
      number: '',
      title: t('complianceStandardContent'),
      content: content
    })
  }

  documentSections.value = sections
  activeSectionIndex.value = 0
  sectionRefs.value = []
}

// 渲染章节内容（简单的 Markdown 渲染）
const renderSectionContent = (content) => {
  if (!content) return ''

  let html = content

  // 渲染代码块
  html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre class="code-block"><code>$2</code></pre>')

  // 渲染行内代码
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

  // 渲染粗体
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')

  // 渲染斜体
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')

  // 渲染列表
  html = html.replace(/^[-*]\s+(.+)/gm, '<li>$1</li>')

  // 渲染段落
  html = html.split('\n').map(line => {
    if (line.trim() && !line.startsWith('<')) {
      return `<p>${line}</p>`
    }
    return line
  }).join('\n')

  return html
}

// 滚动到指定章节
const scrollToSection = async (index) => {
  activeSectionIndex.value = index

  await nextTick()

  const el = sectionRefs.value[index]
  if (el && standardContentRef.value) {
    standardContentRef.value.scrollTo({
      top: el.offsetTop - 20,
      behavior: 'smooth'
    })
  }
}

// 为详情页标准文档生成规则
const generateRulesForStandardDetail = async () => {
  if (!currentStandardDetail.value) return

  generatingRules.value = true
  try {
    const data = await generateRulesForStandard(currentStandardDetail.value.id)
    if (data.success) {
      ElMessage.success(`${t('complianceRulesGenerated')}: ${data.generated_count} rules`)
      // 更新当前标准文档详情
      const updatedData = await getStandard(currentStandardDetail.value.id)
      currentStandardDetail.value = updatedData
      loadStandards()
    } else {
      ElMessage.error(t('complianceRulesGenerateFailed') + ': ' + data.error)
    }
  } catch (e) {
    ElMessage.error(t('complianceRulesGenerateFailed'))
  } finally {
    generatingRules.value = false
  }
}

// ==================== 配置问题高亮展示 ====================

// 打开配置详情对话框
const showConfigDetailDialog = async () => {
  if (!report.value) {
    ElMessage.warning(t('complianceNotRunYet'))
    return
  }

  // 使用 API 返回的 config_analysis
  if (report.value.config_analysis && report.value.config_analysis.length > 0) {
    configLineAnalysis.value = report.value.config_analysis.map(line => ({
      lineNum: line.line_number,
      content: line.content,
      issues: line.issues || [],
      severity: line.severity || 'ok',
      isPassed: (line.issues || []).length === 0 && line.severity === 'ok'
    }))
  } else {
    // 如果没有 config_analysis，从配置文本生成
    if (auditForm.config_text) {
      analyzeConfigLines(auditForm.config_text, report.value.results)
    } else {
      configLineAnalysis.value = []
    }
  }

  selectedLine.value = null
  configDetailVisible.value = true

  // 等待对话框 DOM 渲染完成
  await nextTick()
}

// 分析配置行与检查结果关联
const analyzeConfigLines = (configText, results) => {
  const lines = configText.split('\n')
  const analysis = []

  // 收集失败项的 pattern
  const failedPatterns = results
    .filter(r => !r.passed && r.pattern)
    .map(r => ({
      ...r,
      patternLower: r.pattern.toLowerCase()
    }))

  // 收集通过项的 pattern
  const passedPatterns = results
    .filter(r => r.passed && r.pattern)
    .map(r => r.pattern.toLowerCase())

  for (let i = 0; i < lines.length; i++) {
    const lineNum = i + 1
    const content = lines[i]
    const contentLower = content.toLowerCase()
    const issues = []
    let isPassed = false

    // 检查失败项是否匹配该行
    for (const failed of failedPatterns) {
      // 简单的关键词匹配或尝试正则匹配
      try {
        if (contentLower.includes(failed.patternLower) ||
            new RegExp(failed.pattern, 'i').test(content)) {
          issues.push({
            check_id: failed.check_id,
            check_name: failed.check_name,
            severity: failed.severity,
            category: failed.category,
            detail: failed.detail,
            recommendation: failed.recommendation
          })
        }
      } catch {
        // 正则无效时使用关键词匹配
        if (contentLower.includes(failed.patternLower)) {
          issues.push({
            check_id: failed.check_id,
            check_name: failed.check_name,
            severity: failed.severity,
            category: failed.category,
            detail: failed.detail,
            recommendation: failed.recommendation
          })
        }
      }
    }

    // 检查是否通过了某些检查
    for (const passedPattern of passedPatterns) {
      if (contentLower.includes(passedPattern)) {
        isPassed = true
        break
      }
    }

    analysis.push({
      lineNum,
      content,
      issues,
      isPassed: isPassed && issues.length === 0
    })
  }

  configLineAnalysis.value = analysis
}

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
  passed = report.value?.passed || passed

  return { critical, high, medium, low, passed }
})

// 失败结果列表
const failedResults = computed(() => {
  return report.value?.results?.filter(r => !r.passed) || []
})

// 获取行样式类
const getLineClass = (line) => {
  if (!line.issues || line.issues.length === 0) {
    return line.isPassed ? 'passed' : 'normal'
  }

  // 按最高严重程度确定样式
  const severities = line.issues.map(i => i.severity)
  if (severities.includes('critical')) return 'critical'
  if (severities.includes('high')) return 'high'
  if (severities.includes('medium')) return 'medium'
  return 'low'
}

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

// 标签类型辅助函数
const severityTagType = (sev) => {
  const types = { critical: 'danger', high: 'warning', medium: 'info', low: 'success' }
  return types[sev] || ''
}

const categoryTagType = (cat) => {
  const types = { security: 'danger', availability: 'warning', compliance: 'info' }
  return types[cat] || ''
}

const capitalize = (str) => {
  if (!str) return ''
  return str.charAt(0).toUpperCase() + str.slice(1)
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
   对话框样式
   ======================================== */

.compliance-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}

.compliance-dialog .section-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
}

.compliance-dialog .section-header .el-icon {
  color: var(--accent-primary);
}

.compliance-dialog .el-form-item {
  margin-bottom: 10px;
}

/* ========================================
   上传区域
   ======================================== */

.upload-area {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.config-upload {
  width: 100%;
}

.config-upload :deep(.el-upload-dragger) {
  background: var(--bg-hover);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 24px;
}

.config-upload :deep(.el-upload-dragger:hover) {
  border-color: var(--accent-secondary);
}

.config-upload :deep(.el-icon--upload) {
  color: var(--text-tertiary);
  font-size: 32px;
}

.config-upload :deep(.el-upload__text) {
  color: var(--text-secondary);
  font-size: 13px;
}

.parse-result {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--gap-md);
}

.parse-info {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-md);
}

.parse-info .info-item {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
}

.parse-info .label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.parse-info .value {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary);
}

/* ========================================
   审核选项
   ======================================== */

.audit-options {
  margin-top: var(--gap-md);
  padding: var(--gap-md);
  background: var(--bg-hover);
  border-radius: var(--radius-md);
}

.option-row {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.option-row + .option-row {
  margin-top: var(--gap-sm);
}

.option-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.ai-config-status {
  display: flex;
  align-items: center;
  gap: var(--gap-xs);
  font-size: 12px;
  color: var(--accent-danger);
}

/* ========================================
   AI 配置状态栏
   ======================================== */

.ai-config-status-bar {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  background: var(--success-bg);
  border: 1px solid rgba(0, 184, 148, 0.2);
  border-radius: var(--radius-md);
  padding: var(--gap-sm) var(--gap-md);
  margin-bottom: var(--gap-md);
  font-size: 13px;
  color: var(--accent-primary);
}

/* ========================================
   对话框底部
   ======================================== */

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
}

/* ========================================
   表单输入样式
   ======================================== */

.config-form :deep(.el-input__wrapper) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: none;
  padding: 0 12px;
  height: 32px;
  transition: all 0.15s ease;
}

.config-form :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
  background: var(--bg-card);
}

.config-form :deep(.el-input__inner) {
  font-size: 14px;
  color: var(--text-primary);
  height: 32px;
}

.config-form :deep(.el-input__inner::placeholder) {
  color: var(--text-tertiary);
  font-size: 13px;
  opacity: 1;
}

/* Textarea */
.config-form :deep(.el-textarea__inner) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-primary);
  padding: 12px;
  transition: all 0.15s ease;
  box-shadow: none;
}

.config-form :deep(.el-textarea__inner:hover) {
  border-color: var(--accent-secondary);
}

.config-form :deep(.el-textarea__inner:focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

/* Snippet input 特殊样式 */
.snippet-input :deep(.el-textarea__inner) {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.5;
}

/* ========================================
   暗色模式
   ======================================== */

.dark .compliance-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}

.dark .compliance-dialog .section-header {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}

.dark .compliance-dialog .section-header .el-icon {
  color: #58a6ff;
}

.dark .config-form :deep(.el-input__wrapper) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-input__wrapper.is-focus) {
  background: var(--bg-card);
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.15);
}

.dark .config-form :deep(.el-textarea__inner) {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .config-form :deep(.el-textarea__inner:focus) {
  background: var(--bg-card);
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(0, 184, 148, 0.15);
}

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

.dark .parse-result {
  background: var(--bg-tertiary);
}

.dark .audit-options {
  background: var(--bg-tertiary);
}

.dark .ai-config-status-bar {
  background: rgba(0, 184, 148, 0.1);
}

.dark .config-upload :deep(.el-upload-dragger) {
  background: var(--bg-tertiary);
}

/* ========================================
   标准文档详情对话框
   ======================================== */

.standard-detail-dialog .standard-meta-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
}

.standard-meta-bar .meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.standard-meta-bar .meta-label {
  color: var(--text-tertiary);
}

.standard-meta-bar .meta-value {
  font-weight: 600;
  color: var(--text-primary);
}

.standard-detail-layout {
  display: flex;
  gap: 16px;
  min-height: 500px;
  max-height: 70vh;
}

/* 左侧目录 */
.standard-toc {
  width: 220px;
  flex-shrink: 0;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 12px;
  overflow-y: auto;
}

.toc-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
  margin-bottom: 8px;
}

.toc-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.toc-item {
  padding: 8px 10px;
  font-size: 12px;
  color: var(--text-secondary);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.toc-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.toc-item.active {
  background: rgba(9, 132, 227, 0.1);
  color: var(--accent-secondary);
}

.toc-number {
  color: var(--text-tertiary);
  font-weight: 500;
  flex-shrink: 0;
}

.toc-text {
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 右侧内容 */
.standard-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
}

.empty-content {
  text-align: center;
  padding: 40px;
  color: var(--text-tertiary);
}

.markdown-content {
  line-height: 1.6;
}

.section-block {
  margin-bottom: 24px;
}

.section-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.section-number {
  color: var(--accent-secondary);
  margin-right: 8px;
}

.section-body {
  font-size: 13px;
  color: var(--text-secondary);
}

.section-body p {
  margin-bottom: 8px;
}

.section-body li {
  margin-left: 16px;
  margin-bottom: 4px;
  list-style-type: disc;
}

.code-block {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 12px;
  margin: 12px 0;
  overflow-x: auto;
}

.code-block code {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-primary);
}

.inline-code {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  color: var(--accent-secondary);
}

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

.dark .standard-meta-bar {
  background: rgba(13, 17, 23, 0.8);
}

.dark .standard-toc {
  background: rgba(13, 17, 23, 0.6);
}

.dark .toc-item.active {
  background: rgba(0, 184, 148, 0.15);
  color: var(--accent-primary);
}

.dark .standard-content {
  background: rgba(13, 17, 23, 0.4);
}

.dark .section-heading {
  color: #e6edf3;
}

.dark .code-block {
  background: rgba(13, 17, 23, 0.8);
}

.dark .inline-code {
  background: rgba(13, 17, 23, 0.6);
  color: #58a6ff;
}

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

/* ========================================
   规则详情对话框
   ======================================== */

.rule-detail-dialog .rule-detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rule-header-section {
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  padding: 16px;
}

.rule-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.rule-id-badge {
  background: var(--accent-secondary);
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 600;
}

.rule-name-text {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.rule-meta-row {
  display: flex;
  gap: 8px;
}

.rule-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 16px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.pattern-box {
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.pattern-code {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 13px;
  color: var(--accent-secondary);
}

.logic-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
}

.recommendation-box {
  background: rgba(0, 184, 148, 0.05);
  border: 1px solid rgba(0, 184, 148, 0.15);
  border-radius: var(--radius-sm);
  padding: 12px;
}

.recommendation-code {
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
  color: var(--text-primary);
  white-space: pre-wrap;
  margin: 0;
}

.rule-status-section {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
}

.status-label {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 规则表格中的链接样式 */
.rule-id-link,
.rule-name-link {
  color: var(--accent-secondary);
  cursor: pointer;
  transition: color 0.15s ease;
}

.rule-id-link:hover,
.rule-name-link:hover {
  color: var(--accent-primary);
}

/* 暗色模式 */
.dark .rule-header-section {
  background: rgba(13, 17, 23, 0.6);
}

.dark .rule-section {
  background: rgba(13, 17, 23, 0.4);
}

.dark .pattern-box {
  background: rgba(13, 17, 23, 0.6);
}

.dark .pattern-code {
  color: #58a6ff;
}

.dark .recommendation-box {
  background: rgba(0, 184, 148, 0.1);
}

.dark .rule-status-section {
  background: rgba(13, 17, 23, 0.6);
}

/* 规则编辑模式样式 */
.edit-mode-bar {
  display: flex;
  justify-content: flex-end;
  padding: 8px 0;
  margin-bottom: 8px;
}

.rule-name-input {
  flex: 1;
}

.rule-name-input :deep(.el-input__wrapper) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
}

.edit-input :deep(.el-textarea__inner) {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  font-family: 'Geist Mono', 'JetBrains Mono', monospace;
  font-size: 12px;
}
</style>