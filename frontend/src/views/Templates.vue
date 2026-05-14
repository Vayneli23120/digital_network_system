<template>
  <div class="templates-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('tplTitle') }}</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            {{ t('tplNew') }}
          </el-button>
        </div>
      </template>

      <el-table :data="templates" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" :label="t('tplName')" width="200" />
        <el-table-column prop="description" :label="t('tplDescription')" />
        <el-table-column prop="created_at" :label="t('colCreatedAt')" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('colOperation')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewTemplate(row.id)">{{ t('actionView') }}</el-button>
            <el-button size="small" @click="editTemplate(row.id)">{{ t('actionEdit') }}</el-button>
            <el-button size="small" type="danger" @click="deleteTemplate(row.id)">{{ t('actionDelete') }}</el-button>
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
      <el-form :model="templateForm" label-width="90px" size="default">
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
            <el-alert type="info" :closable="false">
              <p>{{ t('tplAvailableVars') }}</p>
              <ul>
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
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateTemplate() : createTemplate()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 查看模板对话框 -->
    <el-dialog v-model="showViewDialog" :title="t('tplView')" width="800px">
      <div v-if="currentTemplate">
        <h4>{{ currentTemplate.name }}</h4>
        <p>{{ currentTemplate.description }}</p>
        <pre class="template-content">{{ currentTemplate.template_content }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Edit, Setting } from '@element-plus/icons-vue'
import { getTemplates, createTemplate as createTemplateApi, getTemplate, updateTemplate as updateTemplateApi, deleteTemplate as deleteTemplateApi } from '@/api'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

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

const loadTemplates = async () => {
  loading.value = true
  try {
    const data = await getTemplates()
    templates.value = data.items || []
  } catch (error) {
    ElMessage.error(t('tplLoadFailed'))
  } finally {
    loading.value = false
  }
}

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

    ElMessage.success(t('tplCreateSuccess'))
    showAddDialog.value = false
    resetForm()
    loadTemplates()
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

    ElMessage.success(t('tplUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    currentTemplate.value = null
    resetForm()
    loadTemplates()
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
    ElMessage.success(t('tplDeleteSuccess'))
    loadTemplates()
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
.templates-page {
  padding: 0;
}

.template-editor {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.template-content {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  padding: var(--gap-md);
  border-radius: var(--radius-md);
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
  margin-top: var(--gap-sm);
}

.dark .template-content {
  background: #1e1e1e;
  color: #d4d4d4;
}

/* 对话框样式 */
.template-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}
.template-dialog .section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(0, 48, 135, 0.06);
}
.template-dialog .section-header .el-icon {
  color: var(--accent-primary);
}
.template-dialog .el-form-item {
  margin-bottom: 10px;
}

/* 暗黑模式 */
.dark .template-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}
.dark .template-dialog .section-header {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}
.dark .template-dialog .section-header .el-icon {
  color: #58a6ff;
}

ul {
  margin: var(--gap-xs) 0;
  padding-left: 20px;
}

code {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: 'Consolas', 'Monaco', monospace;
}
</style>
