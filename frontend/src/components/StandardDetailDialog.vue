<template>
  <el-dialog
    v-model="visible"
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
        <button class="nav-action-btn secondary" @click="visible = false">
          {{ t('actionCancel') }}
        </button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, MagicStick } from '@element-plus/icons-vue'
import { getStandard, generateRulesForStandard } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { parseDocumentSections, renderSectionContent } from '@/utils/compliance.js'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  standard: { type: Object, default: null }
})

const emit = defineEmits(['update:modelValue', 'rules-generated'])

const generatingRules = defineModel('generatingRules', { type: Boolean, default: false })

const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const currentStandardDetail = ref(null)
const standardDetailLoading = ref(false)
const documentSections = ref([])
const activeSectionIndex = ref(0)
const standardContentRef = ref(null)
const sectionRefs = ref([])

// 打开时加载标准文档详情并解析章节
watch(() => props.modelValue, async (val) => {
  if (!val || !props.standard) return

  standardDetailLoading.value = true
  try {
    const data = await getStandard(props.standard.id)
    currentStandardDetail.value = data
    documentSections.value = parseDocumentSections(data.content || '', t('complianceStandardContent'))
    activeSectionIndex.value = 0
    sectionRefs.value = []
  } catch (e) {
    ElMessage.error(t('loadFailed'))
    visible.value = false
  } finally {
    standardDetailLoading.value = false
  }
})

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
      emit('rules-generated')
    } else {
      ElMessage.error(t('complianceRulesGenerateFailed') + ': ' + data.error)
    }
  } catch (e) {
    ElMessage.error(t('complianceRulesGenerateFailed'))
  } finally {
    generatingRules.value = false
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
   对话框底部
   ======================================== */

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
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
</style>
