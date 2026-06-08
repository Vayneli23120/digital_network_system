<template>
  <div class="credentials-page" :class="{ dark: isDark }">
    <el-card>
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ t('credTitle') }}</span>
          <el-button type="primary" @click="openAddDialog" class="add-btn">
            <el-icon><Plus /></el-icon>
            {{ t('credNew') }}
          </el-button>
        </div>
      </template>

      <el-table :data="credentials" style="width: 100%" v-loading="loading" class="credentials-table">
        <el-table-column prop="name" :label="t('credGroupName')" width="200" />
        <el-table-column prop="description" :label="t('credDescription')" />
        <el-table-column prop="username" :label="t('credUsername')" width="150" />
        <el-table-column :label="t('colCreatedAt')" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('colOperation')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editCredential(row.id)" class="action-btn">{{ t('actionEdit') }}</el-button>
            <el-button size="small" type="danger" @click="deleteCredential(row.id)" class="action-btn danger">{{ t('actionDelete') }}</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoCredentials')" :image-size="80">
            <el-button type="primary" size="small" @click="openAddDialog">{{ t('credNew') }}</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadCredentials" @current-change="loadCredentials" />
      </div>
    </el-card>

    <!-- 添加/编辑凭证组对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('credEdit') : t('credNew')" width="600px" append-to-body draggable align-center class="credential-dialog">
      <el-form :model="credentialForm" label-width="100px" size="default" class="credential-form">
        <!-- 基本信息 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Key /></el-icon>
            <span>{{ t('credBasicSection') }}</span>
          </div>
          <el-form-item :label="t('credGroupName')" required>
            <el-input v-model="credentialForm.name" :placeholder="t('credGroupNamePlaceholder')" :disabled="editMode" />
          </el-form-item>
          <el-form-item :label="t('credDescription')">
            <el-input v-model="credentialForm.description" :placeholder="t('credDescriptionPlaceholder')" />
          </el-form-item>
        </div>

        <!-- SSH认证 -->
        <div class="form-section">
          <div class="section-header">
            <el-icon><Lock /></el-icon>
            <span>{{ t('credSshSection') }}</span>
          </div>
          <el-form-item :label="t('credSshUsername')" required>
            <el-input v-model="credentialForm.username" :placeholder="t('credUsernamePlaceholder')" />
          </el-form-item>
          <el-form-item :label="t('credSshPassword')" :required="!editMode">
            <el-input
              v-model="credentialForm.password"
              type="password"
              show-password
              :placeholder="editMode ? t('credPasswordEditPlaceholder') : t('credPasswordPlaceholder')"
            />
          </el-form-item>
          <el-form-item :label="t('credEnablePassword')">
            <el-input
              v-model="credentialForm.enable_password"
              type="password"
              show-password
              :placeholder="t('credEnablePasswordPlaceholder')"
            />
          </el-form-item>
          <el-form-item>
            <el-alert type="info" :closable="false" class="info-alert">
              <template #title>
                <p>{{ t('credEncryptInfo') }}</p>
                <p>{{ t('credRequiredInfo') }}</p>
              </template>
            </el-alert>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showAddDialog = false" class="footer-btn secondary">{{ t('actionCancel') }}</el-button>
          <el-button type="primary" @click="editMode ? updateCredential() : createCredential()" class="footer-btn primary">{{ t('actionConfirm') }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Key, Lock, Plus } from '@element-plus/icons-vue'
import { getCredentials, createCredential as createCredentialApi, getCredential, updateCredential as updateCredentialApi, deleteCredential as deleteCredentialApi } from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

// 暗黑模式检测
const isDark = computed(() => document.documentElement.classList.contains('dark'))

const credentials = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showAddDialog = ref(false)
const editMode = ref(false)
const currentCredentialId = ref(null)

const credentialForm = ref({
  name: '',
  description: '',
  username: '',
  password: '',
  enable_password: ''
})

const loadCredentials = debounce(async (force = false) => {
  loading.value = true
  try {
    const data = await cachedRequest(
      () => getCredentials(),
      'credentials',
      {},
      { forceRefresh: force }
    )
    credentials.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('credLoadFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

const editCredential = async (id) => {
  try {
    const data = await getCredential(id)
    currentCredentialId.value = id
    credentialForm.value = {
      name: data.name,
      description: data.description,
      username: data.username,
      password: '',  // 密码不回填，用户需要修改时才输入
      enable_password: data.enable_password || ''
    }
    editMode.value = true
    showAddDialog.value = true
    // 如果密码解密失败，提示用户需要重新输入
    if (data.decrypt_warning) {
      ElMessage.warning(t('credDecryptWarning'))
    }
  } catch (error) {
    ElMessage.error(t('credGetFailed'))
  }
}

const createCredential = async () => {
  if (!credentialForm.value.name || !credentialForm.value.username || !credentialForm.value.password) {
    ElMessage.warning(t('credRequiredFields'))
    return
  }

  try {
    await createCredentialApi({
      name: credentialForm.value.name,
      description: credentialForm.value.description,
      username: credentialForm.value.username,
      password: credentialForm.value.password,
      enable_password: credentialForm.value.enable_password || undefined
    })

    clearCache('credentials')
    ElMessage.success(t('credCreateSuccess'))
    showAddDialog.value = false
    resetForm()
    loadCredentials(true)
  } catch (error) {
    ElMessage.error(t('credCreateFailed'))
  }
}

const updateCredential = async () => {
  if (!credentialForm.value.name || !credentialForm.value.username) {
    ElMessage.warning(t('credRequiredFieldsEdit'))
    return
  }

  try {
    const updateData = {
      name: credentialForm.value.name,
      description: credentialForm.value.description,
      username: credentialForm.value.username
    }

    // 只有当用户输入密码时才更新
    if (credentialForm.value.password) {
      updateData.password = credentialForm.value.password
    }
    if (credentialForm.value.enable_password !== undefined) {
      updateData.enable_password = credentialForm.value.enable_password || ''
    }

    await updateCredentialApi(currentCredentialId.value, updateData)

    clearCache('credentials')
    ElMessage.success(t('credUpdateSuccess'))
    showAddDialog.value = false
    editMode.value = false
    currentCredentialId.value = null
    resetForm()
    loadCredentials(true)
  } catch (error) {
    ElMessage.error(t('credUpdateFailed'))
  }
}

const deleteCredential = async (id) => {
  try {
    await ElMessageBox.confirm(t('credDeleteConfirm'), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteCredentialApi(id)
    clearCache('credentials')
    ElMessage.success(t('credDeleteSuccess'))
    loadCredentials(true)
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('credDeleteFailed'))
    }
  }
}

const resetForm = () => {
  credentialForm.value = {
    name: '',
    description: '',
    username: '',
    password: '',
    enable_password: ''
  }
}

const openAddDialog = () => {
  editMode.value = false
  currentCredentialId.value = null
  resetForm()
  showAddDialog.value = true
}

onMounted(() => {
  loadCredentials()
})
</script>

<style scoped>
/* ========================================
   使用全局 Theme Token（来自 tokens.css）
   不要重新定义变量，直接使用全局变量
   ======================================== */

.credentials-page {
  padding: 0;
  background: var(--bg-primary);
}

/* ========================================
   卡片头部样式
   ======================================== */

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.add-btn {
  height: 28px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: var(--gap-xs);
  background: var(--accent-primary);
  border: none;
}

.add-btn:hover {
  background: #00a884;
  box-shadow: 0 2px 6px rgba(0, 184, 148, 0.2);
  transform: translateY(-1px);
}

.add-btn .el-icon {
  width: 12px;
  height: 12px;
}

/* ========================================
   表格样式
   ======================================== */

.credentials-table {
  background: var(--bg-card);
}

.credentials-table :deep(.el-table__header-wrapper th) {
  background: var(--bg-hover);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  border-bottom: 1px solid var(--border-default);
}

.credentials-table :deep(.el-table__body tr) {
  background: var(--bg-card);
  transition: background 0.15s ease;
}

.credentials-table :deep(.el-table__body tr:hover > td) {
  background: var(--bg-hover) !important;
}

.credentials-table :deep(.el-table__body td) {
  color: var(--text-primary);
  font-size: 14px;
  border-bottom: 1px solid var(--border-subtle);
}

/* 操作按钮 */
.action-btn {
  height: 24px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  transition: all 0.15s ease;
}

.action-btn:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.action-btn.danger {
  border-color: rgba(214, 48, 49, 0.3);
  color: var(--accent-danger);
}

.action-btn.danger:hover {
  background: var(--error-bg);
  border-color: var(--accent-danger);
}

/* ========================================
   分页栏样式
   ======================================== */

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding: var(--gap-md) 0;
  margin-top: var(--gap-sm);
  border-top: 1px solid var(--border-subtle);
}

.pagination-bar :deep(.el-pagination) {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.pagination-bar :deep(.el-pagination .el-pager li) {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  min-width: 28px;
  height: 28px;
  font-size: 12px;
  color: var(--text-secondary);
  margin: 0 2px;
  transition: all 0.15s ease;
}

.pagination-bar :deep(.el-pagination .el-pager li:hover) {
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.pagination-bar :deep(.el-pagination .el-pager li.is-active) {
  background: var(--accent-secondary);
  border-color: var(--accent-secondary);
  color: white;
}

.pagination-bar :deep(.el-pagination button) {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  height: 28px;
  color: var(--text-secondary);
  transition: all 0.15s ease;
}

.pagination-bar :deep(.el-pagination button:hover:not(:disabled)) {
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.pagination-bar :deep(.el-pagination button:disabled) {
  opacity: 0.5;
}

.pagination-bar :deep(.el-pagination .el-pagination__sizes .el-select .el-input__wrapper) {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  height: 28px;
}

.pagination-bar :deep(.el-pagination .el-pagination__total) {
  color: var(--text-secondary);
  font-size: 12px;
}

/* ========================================
   对话框样式
   ======================================== */

.credential-dialog .form-section {
  background: var(--bg-hover);
  border-radius: var(--radius-lg);
  padding: var(--gap-md);
  border: 1px solid var(--border-subtle);
  margin-bottom: var(--gap-md);
}

.credential-dialog .section-header {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--gap-md);
  padding-bottom: var(--gap-sm);
  border-bottom: 1px solid var(--border-subtle);
}

.credential-dialog .section-header .el-icon {
  color: var(--accent-primary);
  width: 14px;
  height: 14px;
}

/* ========================================
   输入框样式
   ======================================== */

.credential-form :deep(.el-input__wrapper) {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: none;
  padding: 0 12px;
  height: 32px;
  transition: all 0.15s ease;
}

.credential-form :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-secondary);
}

.credential-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
  background: var(--bg-card);
}

.credential-form :deep(.el-input__inner) {
  font-size: 14px;
  color: var(--text-primary);
  height: 32px;
}

.credential-form :deep(.el-input__inner::placeholder) {
  color: var(--text-tertiary);
  font-size: 13px;
  opacity: 1;
}

/* 密码输入框 */
.credential-form :deep(.el-input--password .el-input__wrapper) {
  padding-right: 32px;
}

/* 表单项标签 */
.credential-form :deep(.el-form-item__label) {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
}

/* ========================================
   信息提示框样式
   ======================================== */

.info-alert {
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--gap-sm) var(--gap-md);
}

.info-alert :deep(.el-alert__title) {
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.info-alert :deep(.el-alert__title p) {
  margin: 0;
  color: var(--text-secondary);
}

/* ========================================
   对话框底部按钮
   ======================================== */

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--gap-md);
}

.footer-btn {
  height: 28px;
  padding: 0 16px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: var(--gap-xs);
  transition: all 0.15s ease;
}

.footer-btn.secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.footer-btn.secondary:hover {
  background: var(--bg-hover);
  border-color: var(--accent-secondary);
  color: var(--accent-secondary);
}

.footer-btn.primary {
  background: var(--accent-primary);
  border: none;
  color: white;
}

.footer-btn.primary:hover {
  background: #00a884;
  box-shadow: 0 2px 6px rgba(0, 184, 148, 0.2);
  transform: translateY(-1px);
}

/* ========================================
   暗黑模式适配
   ======================================== */

.dark .credentials-page {
  background: var(--bg-primary);
}

.dark .card-title {
  color: var(--text-primary);
}

.dark .credentials-table :deep(.el-table__header-wrapper th) {
  background: rgba(13, 17, 23, 0.6);
  border-bottom-color: var(--border-default);
}

.dark .credentials-table :deep(.el-table__body tr) {
  background: var(--bg-card);
}

.dark .credentials-table :deep(.el-table__body tr:hover > td) {
  background: rgba(13, 17, 23, 0.8) !important;
}

.dark .credentials-table :deep(.el-table__body td) {
  border-bottom-color: var(--border-subtle);
}

.dark .pagination-bar {
  border-top-color: var(--border-subtle);
}

.dark .pagination-bar :deep(.el-pagination .el-pager li) {
  background: var(--bg-card);
  border-color: var(--border-default);
}

.dark .pagination-bar :deep(.el-pagination .el-pager li.is-active) {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

.dark .pagination-bar :deep(.el-pagination button) {
  background: var(--bg-card);
  border-color: var(--border-default);
}

.dark .credential-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: var(--border-subtle);
}

.dark .credential-dialog .section-header {
  color: #8b949e;
  border-bottom-color: var(--border-subtle);
}

.dark .credential-dialog .section-header .el-icon {
  color: var(--accent-primary);
}

.dark .credential-form :deep(.el-input__wrapper) {
  background: rgba(13, 17, 23, 0.8);
  border-color: var(--border-subtle);
}

.dark .credential-form :deep(.el-input__wrapper:hover) {
  border-color: var(--accent-secondary);
}

.dark .credential-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 2px rgba(9, 132, 227, 0.15);
}

.dark .credential-form :deep(.el-form-item__label) {
  color: var(--text-secondary);
}

.dark .info-alert {
  background: rgba(13, 17, 23, 0.6);
  border-color: var(--border-subtle);
}

.dark .info-alert :deep(.el-alert__title) {
  color: var(--text-secondary);
}
</style>