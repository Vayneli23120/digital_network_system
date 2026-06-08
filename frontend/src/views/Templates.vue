<template>
  <div class="templates-page" :class="{ dark: isDark }">
    <!-- 页面标题栏 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('tplTitle') }}</h1>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn primary" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          {{ t('tplNew') }}
        </button>
      </div>
    </section>

    <el-card class="templates-card">
      <el-table :data="templates" style="width: 100%" v-loading="loading" class="templates-table">
        <el-table-column prop="name" :label="t('tplName')" width="200">
          <template #default="{ row }">
            <span class="template-name">{{ row.name }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" :label="t('tplDescription')">
          <template #default="{ row }">
            <span class="template-desc">{{ row.description || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" :label="t('colCreatedAt')" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('colOperation')" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <button class="nav-action-btn small secondary" @click="viewTemplate(row.id)">
                <el-icon><View /></el-icon>
                {{ t('actionView') }}
              </button>
              <button class="nav-action-btn small secondary" @click="editTemplate(row.id)">
                <el-icon><Edit /></el-icon>
                {{ t('actionEdit') }}
              </button>
              <button class="nav-action-btn small danger" @click="deleteTemplate(row.id)">
                <el-icon><Delete /></el-icon>
                {{ t('actionDelete') }}
              </button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoTemplates')" :image-size="80">
            <el-button type="primary" size="small" @click="showAddDialog = true">{{ t('tplNew') }}</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadTemplates" @current-change="loadTemplates" />
      </div>
    </el-card>

    <!-- 添加/编辑模板对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('tplEdit') : t('tplNew')" width="800px" append-to-body draggable align-center class="template-dialog">
      <el-form :model="templateForm" label-width="90px" size="default" class="config-form">
        <!-- 基本信息 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Document /></el-icon>
            <span>{{ t('tplBasicSection') }}</span>
          </div>
          <el-form-item :label="t('tplName')" required>
            <el-input v-model="templateForm.name" :placeholder="t('tplNamePlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('tplDescription')">
            <el-input v-model="templateForm.description" :placeholder="t('tplDescriptionPlaceholder')" />
          </el-form-item>
        </div>

        <!-- 模板内容 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Edit /></el-icon>
            <span>{{ t('tplContentSection') }}</span>
          </div>
          <el-form-item :label="t('tplContent')" required>
            <el-input
              v-model="templateForm.template_content"
              type="textarea"
              :rows="12"
              :placeholder="t('tplContentPlaceholder')"
              class="template-editor"
            />
          </el-form-item>
        </div>

        <!-- 变量配置 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Setting /></el-icon>
            <span>{{ t('tplVariablesSection') }}</span>
          </div>
          <el-form-item :label="t('tplVariables')">
            <el-input
              v-model="templateForm.variables"
              type="textarea"
              :rows="3"
              :placeholder="t('tplVariablesPlaceholder')"
            />
          </el-form-item>
          <el-form-item :label="t('tplVarHelp')">
            <el-alert type="info" :closable="false" class="var-alert">
              <p>{{ t('tplAvailableVars') }}</p>
              <ul class="var-list">
                <li><code>{{ hostname }}</code> - {{ t('tplVarHostname') }}</li>
                <li><code>{{ ip }}</code> - {{ t('tplVarIp') }}</li>
                <li><code>{{ location }}</code> - {{ t('tplVarLocation') }}</li>
                <li><code>{{ now }}</code> - {{ t('tplVarNow') }}</li>
                <li><code>{{ now_str }}</code> - {{ t('tplVarNowStr') }}</li>
              </ul>
            </el-alert>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
          <el-button type="primary" @click="editMode ? updateTemplate() : createTemplate()">{{ t('actionConfirm') }}</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 查看模板对话框 -->
    <el-dialog v-model="showViewDialog" :title="t('tplView')" width="800px" align-center class="view-dialog">
      <div v-if="currentTemplate" class="view-content">
        <div class="view-header">
          <h4 class="view-title">{{ currentTemplate.name }}</h4>
          <p class="view-desc">{{ currentTemplate.description }}</p>
        </div>
        <pre class="template-content">{{ currentTemplate.template_content }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Edit, Setting, Plus, View, Delete } from '@element-plus/icons-vue'
import { getTemplates, createTemplate as createTemplateApi, getTemplate, updateTemplate as updateTemplateApi, deleteTemplate as deleteTemplateApi } from '@/api'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

// 暗黑模式检测
const isDark = computed(() => document.documentElement.classList.contains('dark'))

const templates = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const showViewDialog = ref(false)
const editMode = ref(false)
const currentTemplate = ref(null)

const templateForm = ref({
  name: '',
  description: '',
  template_content: '',
  variables: ''
})

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

const loadTemplates = debounce(async (force = false) => {
  loading.value = true
  try {
    const data = await cachedRequest(
      () => getTemplates(),
      'templates',
      {},
      { forceRefresh: force }
    )
    templates.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('tplLoadFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

const viewTemplate = async (id) => {
  try {
    const data = await getTemplate(id)
    currentTemplate.value = data
    showViewDialog.value = true
  } catch (error) {
    ElMessage.error(t('tplGetFailed'))
  }
}

const editTemplate = async (id) => {
  try {
    const data = await getTemplate(id)
    currentTemplate.value = data
    templateForm.value = {
      name: data.name,
      description: data.description,
      template_content: data.template_content,
      variables: typeof data.variables === 'string' ? data.variables : JSON.stringify(data.variables)
    }
    editMode.value = true
    showAddDialog.value = true
  } catch (error) {
    ElMessage.error(t('tplGetFailed'))
  }
}

const createTemplate = async () => {
  try {
    let variables = {}
    if (templateForm.value.variables) {
      try {
        variables = JSON.parse(templateForm.value.variables)
      } catch (e) {
        ElMessage.warning(t('tplInvalidJsonStored'))
      }
    }

    await createTemplateApi({
      name: templateForm.value.name,
      description: templateForm.value.description,
      template_content: templateForm.value.template_content,
      variables: JSON.stringify(variables)
    })

    clearCache('templates')
    ElMessage.success(t('tplCreateSuccess'))
    showAddDialog.value = false
    resetForm()
    loadTemplates(true)
  } catch (error) {
    ElMessage.error(t('tplCreateFailed'))
  }
}

const updateTemplate = async () => {
  try {
    let variables = {}
    if (templateForm.value.variables) {
      try {
        variables = JSON.parse(templateForm.value.variables)
      } catch (e) {
        ElMessage.warning(t('tplInvalidJson'))
      }
    }

    await updateTemplateApi(currentTemplate.value.id, {
      name: templateForm.value.name,
      description: templateForm.value.description,
      template_content: templateForm.value.template_content,
      variables: JSON.stringify(variables)
    })

    clearCache('templates')
    ElMessage.success(t('tplUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    currentTemplate.value = null
    resetForm()
    loadTemplates(true)
  } catch (error) {
    ElMessage.error(t('tplUpdateFailed'))
  }
}

const deleteTemplate = async (id) => {
  try {
    await ElMessageBox.confirm(t('tplDeleteConfirm'), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteTemplateApi(id)
    clearCache('templates')
    ElMessage.success(t('tplDeleteSuccess'))
    loadTemplates(true)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('tplDeleteFailed'))
    }
  }
}

const resetForm = () => {
  templateForm.value = {
    name: '',
    description: '',
    template_content: '',
    variables: ''
  }
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
/* ========================================
   使用全局 Theme Token（来自 tokens.css）
   不要重新定义变量，直接使用全局变量
   ======================================== */

.templates-page {
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
   按钮系统 - 现代、轻量、主次分明
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

/* 小按钮 */
.nav-action-btn.small {
  height: 22px;
  padding: 0 8px;
  font-size: 11px;
}

/* 主按钮 */
.nav-action-btn.primary {
  background: var(--accent-primary);
  color: white;
  border: none;
}

.nav-action-btn.primary:hover {
  background: #00a884;
  box-shadow: 0 2px 6px rgba(0, 184, 148, 0.2);
  transform: translateY(-1px);
}

/* 次按钮 */
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

/* 危险按钮 */
.nav-action-btn.danger {
  background: var(--accent-danger);
  color: white;
  border: none;
}

.nav-action-btn.danger:hover {
  background: #c42a2a;
  box-shadow: 0 2px 6px rgba(214, 48, 49, 0.2);
  transform: translateY(-1px);
}

/* ========================================
   卡片样式
   ======================================== */

.templates-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.templates-card :deep(.el-card__body) {
  padding: var(--gap-md);
}

/* ========================================
   表格样式
   ======================================== */

.templates-table :deep(.el-table__header-wrapper th) {
  background: var(--bg-hover);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.templates-table :deep(.el-table__body-wrapper td) {
  font-size: 13px;
  color: var(--text-primary);
}

.templates-table :deep(.el-table__row:hover td) {
  background: var(--bg-hover) !important;
}

/* 暗色模式表格 */
.dark .templates-table :deep(.el-table__header-wrapper th) {
  background: var(--bg-tertiary);
}

.dark .templates-table :deep(.el-table__row:hover td) {
  background: var(--bg-hover) !important;
}

/* ========================================
   模板名称和描述
   ======================================== */

.template-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.template-desc {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ========================================
   操作按钮区域
   ======================================== */

.action-buttons {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* ========================================
   分页栏
   ======================================== */

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding: var(--gap-md) 0;
  margin-top: var(--gap-md);
  border-top: 1px solid var(--border-subtle);
}

/* ========================================
   Dialog/Modal 样式
   ======================================== */

.template-dialog :deep(.el-dialog) {
  border-radius: var(--radius-lg);
}

.template-dialog :deep(.el-dialog__header) {
  font-size: 14px;
  font-weight: 600;
}

.dialog-footer {
  display: flex;
  gap: var(--gap-md);
  justify-content: flex-end;
}

/* ========================================
   表单区域 - 现代 DevOps 风格
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

/* Placeholder 提高可见度 */
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
   模板编辑器
   ======================================== */

.template-editor :deep(.el-textarea__inner) {
  font-family: 'Geist Mono', 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
}

/* ========================================
   form-section 卡片分组样式
   ======================================== */

.form-section {
  background: var(--bg-hover);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  border: 1px solid var(--border-subtle);
  margin-bottom: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.section-header .el-icon {
  color: var(--accent-primary);
}

.config-form :deep(.el-form-item) {
  margin-bottom: 10px;
}

/* 暗色模式 */
.dark .form-section {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.dark .section-header {
  color: var(--text-secondary);
  border-bottom-color: var(--border-default);
}

.dark .section-header .el-icon {
  color: var(--accent-primary);
}

/* ========================================
   变量提示样式
   ======================================== */

.var-alert {
  border-radius: var(--radius-md);
}

.var-alert :deep(.el-alert__content) {
  padding: var(--gap-sm);
}

.var-list {
  margin: var(--gap-xs) 0;
  padding-left: 20px;
}

.var-list li {
  margin-bottom: 4px;
  color: var(--text-secondary);
  font-size: 12px;
}

.var-list code {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: 'Geist Mono', 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: var(--accent-secondary);
}

/* ========================================
   查看对话框样式
   ======================================== */

.view-dialog :deep(.el-dialog) {
  border-radius: var(--radius-lg);
}

.view-content {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.view-header {
  padding-bottom: var(--gap-md);
  border-bottom: 1px solid var(--border-subtle);
}

.view-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.view-desc {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.template-content {
  background: var(--bg-hover);
  color: var(--text-primary);
  padding: var(--gap-md);
  border-radius: var(--radius-md);
  font-family: 'Geist Mono', 'JetBrains Mono', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border-subtle);
}

/* 暗色模式模板内容 */
.dark .template-content {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

/* ========================================
   暗色模式全局适配
   ======================================== */

.dark .templates-card {
  background: var(--bg-card);
  border-color: var(--border-default);
}

.dark .page-title {
  color: var(--text-primary);
}

.dark .nav-action-btn {
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.dark .nav-action-btn.secondary {
  border-color: var(--border-default);
}

.dark .nav-action-btn.secondary:hover {
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

/* ========================================
   动画
   ======================================== */

@keyframes fade-slide-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.templates-card {
  animation: fade-slide-in 0.2s ease;
}
</style>
