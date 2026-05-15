<template>
  <div class="credentials-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ t('credTitle') }}</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            {{ t('credNew') }}
          </el-button>
        </div>
      </template>

      <el-table :data="credentials" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" :label="t('credGroupName')" width="200" />
        <el-table-column prop="description" :label="t('credDescription')" />
        <el-table-column prop="username" :label="t('credUsername')" width="150" />
        <el-table-column :label="t('colCreatedAt')" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('colOperation')" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editCredential(row.id)">{{ t('actionEdit') }}</el-button>
            <el-button size="small" type="danger" @click="deleteCredential(row.id)">{{ t('actionDelete') }}</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoCredentials')" :image-size="80">
            <el-button type="primary" size="small" @click="showAddDialog = true">{{ t('credNew') }}</el-button>
          </el-empty>
        </template>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadCredentials" @current-change="loadCredentials" />
      </div>
    </el-card>

    <!-- 添加/编辑凭证组对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? t('credEdit') : t('credNew')" width="600px" append-to-body draggable align-center class="credential-dialog">
      <el-form :model="credentialForm" label-width="100px" size="default">
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
            <el-alert type="info" :closable="false">
              <template #title>
                <p>{{ t('credEncryptInfo') }}</p>
                <p>{{ t('credRequiredInfo') }}</p>
              </template>
            </el-alert>
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="editMode ? updateCredential() : createCredential()">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Key, Lock } from '@element-plus/icons-vue'
import { getCredentials, createCredential as createCredentialApi, getCredential, updateCredential as updateCredentialApi, deleteCredential as deleteCredentialApi } from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

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

onMounted(() => {
  loadCredentials()
})
</script>

<style scoped>
.credentials-page {
  padding: 0;
}

/* 对话框样式 */
.credential-dialog .form-section {
  background: rgba(0, 48, 135, 0.04);
  border-radius: 10px;
  padding: 14px 16px;
  border: 1px solid rgba(0, 48, 135, 0.08);
  margin-bottom: 12px;
}
.credential-dialog .section-header {
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
.credential-dialog .section-header .el-icon {
  color: var(--accent-primary);
}
.credential-dialog .el-form-item {
  margin-bottom: 10px;
}

/* 暗黑模式 */
.dark .credential-dialog .form-section {
  background: rgba(13, 17, 23, 0.6);
  border-color: rgba(48, 54, 61, 0.4);
}
.dark .credential-dialog .section-header {
  color: #8b949e;
  border-bottom-color: rgba(48, 54, 61, 0.4);
}
.dark .credential-dialog .section-header .el-icon {
  color: #58a6ff;
}
</style>
