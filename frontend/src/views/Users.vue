<template>
  <div class="users-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>{{ t('userTitle') }}</h1>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="showAddDialog = true">
          {{ t('userAdd') }}
        </el-button>
        <el-button :icon="Refresh" @click="loadUsers">{{ t('toolRefresh') }}</el-button>
      </div>
    </div>

    <!-- 用户列表 -->
    <el-card class="table-card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" :label="t('userUsername')" width="120" />
        <el-table-column prop="full_name" :label="t('userFullName')" width="150">
          <template #default="{ row }">{{ row.full_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="email" :label="t('userEmail')" width="200">
          <template #default="{ row }">{{ row.email || '-' }}</template>
        </el-table-column>
        <el-table-column :label="t('userRole')" width="200">
          <template #default="{ row }">
            <el-tag v-for="role in row.roles" :key="role.id" size="small" type="info" class="role-tag">
              {{ role.name }}
            </el-tag>
            <span v-if="!row.roles || row.roles.length === 0">-</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('userStatus')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? t('userEnabled') : t('userDisabled') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('userSuperuser')" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_superuser" type="warning" size="small">{{ t('statusYes') }}</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" :label="t('userLastLogin')" width="160">
          <template #default="{ row }">{{ row.last_login ? formatDateTime(row.last_login) : t('userNeverLogin') }}</template>
        </el-table-column>
        <el-table-column prop="created_at" :label="t('colCreatedAt')" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('colOperation')" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="editUser(row)">{{ t('actionEdit') }}</el-button>
            <el-button type="warning" size="small" link @click="resetPassword(row)">{{ t('userResetPassword') }}</el-button>
            <el-button
              v-if="!row.is_superuser"
              type="danger"
              size="small"
              link
              @click="deleteUserConfirm(row)"
            >{{ t('actionDelete') }}</el-button>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :description="t('msgNoUsers')" :image-size="80">
            <el-button type="primary" size="small" @click="showAddDialog = true">{{ t('userAdd') }}</el-button>
          </el-empty>
        </template>
      </el-table>
    </el-card>

    <!-- 添加用户对话框 -->
    <el-dialog v-model="showAddDialog" :title="t('userAdd')" width="500px">
      <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="80px">
        <el-form-item :label="t('userUsername')" prop="username">
          <el-input v-model="addForm.username" :placeholder="t('userUsernamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('userFullName')" prop="full_name">
          <el-input v-model="addForm.full_name" :placeholder="t('userFullNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('userEmail')" prop="email">
          <el-input v-model="addForm.email" :placeholder="t('userEmailPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('userPassword')" prop="password">
          <el-input v-model="addForm.password" type="password" :placeholder="t('userPasswordPlaceholder')" show-password />
        </el-form-item>
        <el-form-item :label="t('userRole')">
          <el-select v-model="addForm.role_ids" multiple :placeholder="t('userRolePlaceholder')" style="width: 100%">
            <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('userStatus')">
          <el-switch v-model="addForm.is_active" :active-text="t('userEnabled')" :inactive-text="t('userDisabled')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="createUser" :loading="submitting">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('userEdit')" width="500px">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="80px">
        <el-form-item :label="t('userUsername')">
          <el-input :value="editForm.username" disabled />
        </el-form-item>
        <el-form-item :label="t('userFullName')" prop="full_name">
          <el-input v-model="editForm.full_name" :placeholder="t('userFullNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('userEmail')" prop="email">
          <el-input v-model="editForm.email" :placeholder="t('userEmailPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('userRole')">
          <el-select v-model="editForm.role_ids" multiple :placeholder="t('userRolePlaceholder')" style="width: 100%">
            <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('userStatus')">
          <el-switch v-model="editForm.is_active" :active-text="t('userEnabled')" :inactive-text="t('userDisabled')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="updateUser" :loading="submitting">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="showPasswordDialog" :title="t('userResetPassword')" width="400px">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="80px">
        <el-form-item :label="t('userUser')">
          <el-input :value="passwordForm.username" disabled />
        </el-form-item>
        <el-form-item :label="t('userNewPassword')" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" :placeholder="t('userNewPasswordPlaceholder')" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitPasswordReset" :loading="submitting">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'
import {
  getUsers, createUser as createUserApi, updateUser as updateUserApi,
  deleteUser as deleteUserApi, getRoles
} from '@/api'

const { t } = useI18n()

const users = ref([])
const roles = ref([])
const loading = ref(false)
const submitting = ref(false)
const showAddDialog = ref(false)
const showEditDialog = ref(false)
const showPasswordDialog = ref(false)

const addFormRef = ref(null)
const editFormRef = ref(null)
const passwordFormRef = ref(null)

// 添加用户表单
const addForm = ref({
  username: '',
  full_name: '',
  email: '',
  password: '',
  role_ids: [],
  is_active: true
})

// 编辑用户表单
const editForm = ref({
  id: null,
  username: '',
  full_name: '',
  email: '',
  role_ids: [],
  is_active: true
})

// 重置密码表单
const passwordForm = ref({
  id: null,
  username: '',
  new_password: ''
})

// 表单验证规则
const addRules = {
  username: [{ required: true, message: t('userUsernamePrompt'), trigger: 'blur' }, { min: 3, message: t('userUsernameMinLength'), trigger: 'blur' }],
  password: [{ required: true, message: t('userPasswordPrompt'), trigger: 'blur' }, { min: 6, message: t('userPasswordMinLength'), trigger: 'blur' }],
  email: [{ type: 'email', message: t('userEmailInvalidFormat'), trigger: 'blur' }]
}

const editRules = {
  email: [{ type: 'email', message: t('userEmailInvalidFormat'), trigger: 'blur' }]
}

const passwordRules = {
  new_password: [{ required: true, message: t('userNewPasswordPrompt'), trigger: 'blur' }, { min: 6, message: t('userPasswordMinLength'), trigger: 'blur' }]
}

// 加载用户列表
const loadUsers = debounce(async (force = false) => {
  loading.value = true
  try {
    const data = await cachedRequest(
      () => getUsers(),
      'users',
      {},
      { forceRefresh: force }
    )
    users.value = data || []
  } catch (e) {
    if (e.name !== 'CanceledError') {
      ElMessage.error(t('userLoadFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

// 加载角色列表
const loadRoles = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getRoles(),
      'roles',
      {},
      { forceRefresh: force }
    )
    roles.value = data || []
  } catch (e) {
    if (e.name !== 'CanceledError') {
      console.error(t('userRoleLoadFailed'), e)
    }
  }
}, 300)

// 创建用户
const createUser = async () => {
  const valid = await addFormRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    await createUserApi(addForm.value)
    clearCache('users')
    ElMessage.success(t('userCreateSuccess'))
    showAddDialog.value = false
    addForm.value = { username: '', full_name: '', email: '', password: '', role_ids: [], is_active: true }
    loadUsers(true)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('userCreateFailed'))
  } finally {
    submitting.value = false
  }
}

// 编辑用户
const editUser = (user) => {
  editForm.value = {
    id: user.id,
    username: user.username,
    full_name: user.full_name || '',
    email: user.email || '',
    role_ids: user.roles?.map(r => r.id) || [],
    is_active: user.is_active
  }
  showEditDialog.value = true
}

// 更新用户
const updateUser = async () => {
  const valid = await editFormRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    await updateUserApi(editForm.value.id, {
      full_name: editForm.value.full_name,
      email: editForm.value.email,
      role_ids: editForm.value.role_ids,
      is_active: editForm.value.is_active
    })
    clearCache('users')
    ElMessage.success(t('userUpdateSuccess'))
    showEditDialog.value = false
    loadUsers(true)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('userUpdateFailed'))
  } finally {
    submitting.value = false
  }
}

// 重置密码
const resetPassword = (user) => {
  passwordForm.value = {
    id: user.id,
    username: user.username,
    new_password: ''
  }
  showPasswordDialog.value = true
}

// 提交密码重置
const submitPasswordReset = async () => {
  const valid = await passwordFormRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    // 使用更新用户 API 的扩展接口来重置密码
    await updateUserApi(passwordForm.value.id, { password: passwordForm.value.new_password })
    ElMessage.success(t('userResetPasswordSuccess'))
    showPasswordDialog.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('userResetPasswordFailed'))
  } finally {
    submitting.value = false
  }
}

// 删除用户确认
const deleteUserConfirm = async (user) => {
  try {
    await ElMessageBox.confirm(t('userDeleteConfirmMsg', { username: user.username }), t('userDeleteConfirmTitle'), {
      type: 'warning'
    })
    await deleteUserApi(user.id)
    clearCache('users')
    ElMessage.success(t('userDeleteSuccess'))
    loadUsers(true)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || t('userDeleteFailed'))
    }
  }
}

onMounted(() => {
  loadUsers()
  loadRoles()
})
</script>

<style scoped>
.users-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.table-card {
  border-radius: 8px;
}

.role-tag {
  margin-right: 4px;
}
</style>