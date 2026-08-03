<template>
  <el-dialog
    v-model="visible"
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
          <el-select v-model="aiConfigForm.provider" style="width: 100%" @change="onProviderChange">
            <el-option-group :label="t('complianceAIProviderGroupOfficial')">
              <el-option value="openai" :label="t('complianceAIProviderOpenAI')" />
              <el-option value="anthropic" :label="t('complianceAIProviderAnthropic')" />
              <el-option value="groq" label="Groq API" />
              <el-option value="deepseek" label="DeepSeek" />
              <el-option value="cohere" label="Cohere" />
            </el-option-group>
            <el-option-group :label="t('complianceAIProviderGroupLocal')">
              <el-option value="ollama" :label="t('complianceAIProviderOllama')" />
              <el-option value="llmstudio" :label="t('complianceAIProviderLMStudio')" />
              <el-option value="local" :label="t('complianceAIProviderLocal')" />
            </el-option-group>
            <el-option-group :label="t('complianceAIProviderGroupCloud')">
              <el-option value="azure" label="Azure OpenAI" />
              <el-option value="together" label="Together AI" />
              <el-option value="replicate" label="Replicate" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item :label="t('complianceAIApiKey')" :required="isApiKeyRequired">
          <el-input
            v-model="aiConfigForm.api_key"
            type="password"
            show-password
            :placeholder="apiKeyPlaceholder"
          />
          <div v-if="!isApiKeyRequired" class="form-hint">
            {{ t('complianceAIApiKeyOptional') }}
          </div>
        </el-form-item>
        <el-form-item :label="t('complianceAIBaseUrl')">
          <el-input
            v-model="aiConfigForm.base_url"
            :placeholder="getBaseUrlPlaceholder()"
          />
          <div class="form-hint">
            {{ getBaseUrlHint() }}
          </div>
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
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, Loading } from '@element-plus/icons-vue'
import { createAIConfig as createAIConfigApi, updateAIConfig as updateAIConfigApi, testAIConfig as testAIConfigApi } from '@/api'
import { useI18n } from '@/composables/useI18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  aiConfig: { type: Object, default: () => ({ configured: false }) }
})

const emit = defineEmits(['update:modelValue', 'saved'])

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const aiConfig = computed(() => props.aiConfig)

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

const testingAI = ref(false)
const savingAIConfig = ref(false)

// 根据提供商返回 Base URL 的 Placeholder
const getBaseUrlPlaceholder = () => {
  const provider = aiConfigForm.provider
  const placeholders = {
    openai: 'https://api.openai.com/v1 (官方 API，通常不需要)',
    anthropic: 'https://api.anthropic.com/v1 (官方 API，通常不需要)',
    groq: 'https://api.groq.com/openai/v1 (官方 API，通常不需要)',
    deepseek: 'https://api.deepseek.com/v1 (官方 API，通常不需要)',
    cohere: 'https://api.cohere.com/v1 (官方 API，通常不需要)',
    ollama: t('compliancePhOllama'),
    llmstudio: t('compliancePhLlmStudio'),
    lmstudio: t('compliancePhLlmStudio'),
    local: 'http://localhost:8000/v1 (vLLM / text-generation-webui)',
    azure: t('compliancePhAzure'),
    together: t('compliancePhTogether'),
    replicate: t('compliancePhReplicate'),
  }
  return placeholders[provider] || t('complianceAIBaseUrlFallback')
}

// 根据提供商返回 Base URL 的提示
const getBaseUrlHint = () => {
  const provider = aiConfigForm.provider
  const localProviders = ['ollama', 'llmstudio', 'lmstudio', 'local']
  const cloudProviders = ['openai', 'anthropic', 'groq', 'deepseek', 'cohere', 'together', 'replicate', 'cohere']

  if (localProviders.includes(provider)) {
    return t('complianceAIHintLocalModel')
  } else if (provider === 'azure') {
    return t('complianceAIHintAzure')
  }
  return t('complianceAIHintOfficial')
}

// 判断 API Key 是否必需
const isApiKeyRequired = computed(() => {
  const provider = aiConfigForm.provider
  // Ollama 通常不需要 API Key
  return !['ollama'].includes(provider)
})

// API Key 的 Placeholder
const apiKeyPlaceholder = computed(() => {
  const provider = aiConfigForm.provider
  if (provider === 'ollama') {
    return t('complianceAIApiKeyOptionalPlaceholder')
  }
  return t('complianceAIApiKeyInput')
})

// Provider 变化时的回调
const onProviderChange = () => {
  // 根据提供商自动设置默认模型
  const defaultModels = {
    openai: 'gpt-4',
    anthropic: 'claude-3-opus-20240229',
    groq: 'mixtral-8x7b-32768',
    deepseek: 'deepseek-chat',
    cohere: 'command',
    ollama: 'llama2',
    llmstudio: 'local-model',
    lmstudio: 'local-model',
    local: 'local-model',
    azure: 'gpt-4',
    together: 'mistralai/Mixtral-8x7B-Instruct-v0.1',
    replicate: 'model:version',
  }
  if (defaultModels[aiConfigForm.provider]) {
    aiConfigForm.model_name = defaultModels[aiConfigForm.provider]
  }
}

// aiConfig 变化时填充表单（不含 api_key，对齐原 loadAIConfig 时机）
watch(() => props.aiConfig, (data) => {
  if (data && data.configured) {
    aiConfigForm.provider = data.provider || 'openai'
    aiConfigForm.base_url = data.base_url || ''
    aiConfigForm.model_name = data.model_name || 'gpt-4'
    aiConfigForm.temperature = data.temperature || 0.7
    aiConfigForm.max_tokens = data.max_tokens || 4096
    aiConfigForm.timeout = data.timeout || 120  // 如果未设置，使用120秒默认值
    aiConfigForm.is_default = data.is_default || true
  }
}, { immediate: true })

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
    visible.value = false
    emit('saved')
  } catch (e) {
    ElMessage.error(t('saveFailed'))
  } finally {
    savingAIConfig.value = false
  }
}
</script>

<style scoped>
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

/* ========================================
   对话框表单卡片
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

.dark .ai-config-status-bar {
  background: rgba(0, 184, 148, 0.1);
}
</style>
