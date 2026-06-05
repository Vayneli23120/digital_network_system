<template>
  <div class="permissions-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>{{ t('permissionTitle') }}</h1>
      <div class="header-actions">
        <el-button v-if="!initialized" type="warning" :icon="Setting" @click="initPermissions">
          {{ t('permissionInit') }}
        </el-button>
        <el-button type="primary" :icon="Plus" @click="showAddRoleDialog = true">
          {{ t('permissionAddRole') }}
        </el-button>
        <el-button :icon="Refresh" @click="loadRoles(true)">{{ t('toolRefresh') }}</el-button>
      </div>
    </div>

    <!-- 未初始化提示 -->
    <el-alert v-if="!initialized && !loading" type="warning" :closable="false" class="init-alert">
      <template #title>{{ t('permissionNotInitialized') }}</template>
      <template #default>{{ t('permissionInitDesc') }}</template>
    </el-alert>

    <!-- 角色列表 -->
    <div class="roles-grid">
      <div v-for="role in roles" :key="role.id" class="role-card" @click="editRole(role)">
        <!-- 卡片顶部：角色标识 -->
        <div class="card-header">
          <div class="role-identity">
            <el-icon class="role-icon" :size="20">
              <Key v-if="role.is_system" />
              <UserFilled v-else />
            </el-icon>
            <span class="role-name">{{ role.name }}</span>
          </div>
          <el-tag v-if="role.is_system" type="warning" size="small" effect="dark" class="system-badge">
            {{ t('permissionSystemRole') }}
          </el-tag>
        </div>

        <!-- 卡片内容：数据统计 -->
        <div class="card-body">
          <div class="stat-row">
            <div class="stat-item">
              <span class="stat-label">{{ t('permissionCount') }}</span>
              <span class="stat-value">{{ role.permissions?.length || 0 }}</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-label">{{ t('permissionUserCount') }}</span>
              <span class="stat-value">{{ role.user_count }}</span>
            </div>
          </div>

          <!-- 描述 -->
          <div class="role-desc" v-if="role.description">
            {{ role.description }}
          </div>

          <!-- 权限模块预览 -->
          <div class="perm-preview">
            <div class="preview-title">{{ t('permissionModules') }}</div>
            <div class="module-list">
              <span
                v-for="module in getPermModules(role.permissions)"
                :key="module"
                class="module-tag"
              >
                {{ resourceLabels[module] || module }}
              </span>
              <span v-if="!role.permissions?.length" class="module-empty">
                {{ t('permissionNoModules') }}
              </span>
            </div>
          </div>
        </div>

        <!-- 卡片底部：操作按钮 -->
        <div class="card-footer">
          <el-button type="primary" size="small" link @click.stop="editRole(role)">
            <el-icon><Edit /></el-icon>
            {{ t('actionEdit') }}
          </el-button>
          <el-button type="default" size="small" link @click.stop="cloneRole(role)">
            <el-icon><CopyDocument /></el-icon>
            {{ t('permissionClone') }}
          </el-button>
          <el-button
            v-if="!role.is_system"
            type="danger"
            size="small"
            link
            @click.stop="deleteRoleConfirm(role)"
          >
            <el-icon><Delete /></el-icon>
            {{ t('actionDelete') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 添加角色对话框 -->
    <el-dialog v-model="showAddRoleDialog" :title="t('permissionAddRole')" width="700px" destroy-on-close>
      <el-form :model="roleForm" :rules="roleRules" ref="roleFormRef" label-width="100px">
        <el-form-item :label="t('permissionRoleName')" prop="name">
          <el-input v-model="roleForm.name" :placeholder="t('permissionRoleNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('permissionDescription')" prop="description">
          <el-input v-model="roleForm.description" type="textarea" :rows="2" :placeholder="t('permissionDescriptionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('permissionPermissions')">
          <PermissionMatrix
            v-model="roleForm.permission_ids"
            :permissions="allPermissions"
            :resource-labels="resourceLabels"
            :action-labels="actionLabels"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddRoleDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="createRole" :loading="submitting">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 编辑角色对话框 -->
    <el-dialog v-model="showEditRoleDialog" :title="t('permissionEditRole')" width="700px" destroy-on-close>
      <el-form :model="roleForm" :rules="roleRules" ref="roleFormRef" label-width="100px">
        <el-form-item :label="t('permissionRoleName')">
          <el-input v-model="roleForm.name" :disabled="roleForm.is_system" :placeholder="t('permissionRoleNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('permissionDescription')">
          <el-input v-model="roleForm.description" type="textarea" :rows="2" :placeholder="t('permissionDescriptionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('permissionPermissions')">
          <PermissionMatrix
            v-model="roleForm.permission_ids"
            :permissions="allPermissions"
            :resource-labels="resourceLabels"
            :action-labels="actionLabels"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditRoleDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="updateRole" :loading="submitting">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 克隆角色对话框 -->
    <el-dialog v-model="showCloneDialog" :title="t('permissionCloneRole')" width="400px">
      <el-form :model="cloneForm" ref="cloneFormRef" label-width="100px">
        <el-form-item :label="t('permissionNewName')">
          <el-input v-model="cloneForm.new_name" :placeholder="t('permissionNewNamePlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCloneDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitClone" :loading="submitting">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Key, User, Setting, UserFilled, Edit, CopyDocument, Delete } from '@element-plus/icons-vue'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'
import { getPermissionsRoles, createPermissionsRole, updatePermissionsRole, deletePermissionsRole, clonePermissionsRole, getPermissionsDefaultsPermissions, getPermissionsResources, getPermissionsInitStatus, initPermissionsSystem } from '@/api'
import PermissionMatrix from '@/components/PermissionMatrix.vue'

const { t } = useI18n()

const roles = ref([])
const allPermissions = ref([])
const resourceLabels = ref({})
const actionLabels = ref({})
const loading = ref(false)
const submitting = ref(false)
const initialized = ref(true)  // 默认 true，加载后更新
const showAddRoleDialog = ref(false)
const showEditRoleDialog = ref(false)
const showCloneDialog = ref(false)

const roleFormRef = ref(null)
const cloneFormRef = ref(null)

// 角色表单
const roleForm = ref({
  id: null,
  name: '',
  description: '',
  permission_ids: [],
  is_system: false
})

// 克隆表单
const cloneForm = ref({
  role_id: null,
  new_name: ''
})

// 表单验证规则
const roleRules = {
  name: [{ required: true, message: t('permissionRoleNamePrompt'), trigger: 'blur' }, { min: 2, message: t('permissionRoleNameMinLength'), trigger: 'blur' }]
}

// 加载角色列表
const loadRoles = debounce(async (force = false) => {
  loading.value = true
  try {
    // 先检查初始化状态
    const statusData = await getPermissionsInitStatus()
    initialized.value = statusData.initialized

    if (!statusData.initialized) {
      roles.value = []
      return
    }

    const data = await cachedRequest(
      () => getPermissionsRoles(),
      'permissions_roles',
      {},
      { forceRefresh: force }
    )
    roles.value = data || []
  } catch (e) {
    if (e.name !== 'CanceledError') {
      ElMessage.error(t('permissionLoadFailed'))
    }
  } finally {
    loading.value = false
  }
}, 300)

// 加载权限列表和标签
const loadPermissions = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getPermissionsDefaultsPermissions(),
      'permissions_defaults',
      {},
      { forceRefresh: force }
    )
    allPermissions.value = data.permissions || []

    // 加载资源标签
    const resourcesData = await cachedRequest(
      () => getPermissionsResources(),
      'permissions_resources',
      {},
      { forceRefresh: force }
    )
    // 从 defaults 接口获取标签
    resourceLabels.value = data.resource_labels || {}
    actionLabels.value = data.action_labels || {}
  } catch (e) {
    if (e.name !== 'CanceledError') {
      console.error(t('permissionLoadFailed'), e)
    }
  }
}, 300)

// 创建角色
const createRole = async () => {
  const valid = await roleFormRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    await createPermissionsRole(roleForm.value)
    clearCache('permissions_roles')
    ElMessage.success(t('permissionCreateSuccess'))
    showAddRoleDialog.value = false
    roleForm.value = { id: null, name: '', description: '', permission_ids: [], is_system: false }
    loadRoles(true)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('permissionCreateFailed'))
  } finally {
    submitting.value = false
  }
}

// 编辑角色
const editRole = (role) => {
  roleForm.value = {
    id: role.id,
    name: role.name,
    description: role.description || '',
    permission_ids: role.permissions?.map(p => p.id) || [],
    is_system: role.is_system
  }
  showEditRoleDialog.value = true
}

// 更新角色
const updateRole = async () => {
  const valid = await roleFormRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    await updatePermissionsRole(roleForm.value.id, {
      name: roleForm.value.name,
      description: roleForm.value.description,
      permission_ids: roleForm.value.permission_ids
    })
    clearCache('permissions_roles')
    ElMessage.success(t('permissionUpdateSuccess'))
    showEditRoleDialog.value = false
    loadRoles(true)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('permissionUpdateFailed'))
  } finally {
    submitting.value = false
  }
}

// 克隆角色
const cloneRole = (role) => {
  cloneForm.value = {
    role_id: role.id,
    new_name: role.name + '_copy'
  }
  showCloneDialog.value = true
}

// 提交克隆
const submitClone = async () => {
  submitting.value = true
  try {
    await clonePermissionsRole(cloneForm.value.role_id, cloneForm.value.new_name)
    clearCache('permissions_roles')
    ElMessage.success(t('permissionCloneSuccess'))
    showCloneDialog.value = false
    loadRoles(true)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || t('permissionCloneFailed'))
  } finally {
    submitting.value = false
  }
}

// 删除角色确认
const deleteRoleConfirm = async (role) => {
  try {
    await ElMessageBox.confirm(t('permissionDeleteConfirmMsg', { name: role.name }), t('permissionDeleteConfirmTitle'), {
      type: 'warning'
    })
    await deletePermissionsRole(role.id)
    clearCache('permissions_roles')
    ElMessage.success(t('permissionDeleteSuccess'))
    loadRoles(true)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || t('permissionDeleteFailed'))
    }
  }
}

// 初始化权限系统
const initPermissions = async () => {
  try {
    await ElMessageBox.confirm(t('permissionInitConfirm'), t('permissionInit'), {
      type: 'info'
    })
    submitting.value = true
    const result = await initPermissionsSystem()
    ElMessage.success(t('permissionInitSuccess'))
    initialized.value = true
    loadRoles(true)
    loadPermissions(true)
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || t('permissionInitFailed'))
    }
  } finally {
    submitting.value = false
  }
}

// 获取权限模块列表
const getPermModules = (permissions) => {
  if (!permissions || !permissions.length) return []
  const modules = new Set()
  for (const perm of permissions) {
    if (perm.name) {
      const resource = perm.name.split(':')[0]
      modules.add(resource)
    }
  }
  return Array.from(modules).slice(0, 6)
}

onMounted(() => {
  loadRoles()
  loadPermissions()
})
</script>

<style scoped>
.permissions-page {
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

.roles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

/* DNAC风格卡片 */
.role-card {
  background: #fff;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;
}

.role-card:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 卡片顶部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 16px 12px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-light);
}

.role-identity {
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-icon {
  color: var(--el-color-primary);
}

.role-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.system-badge {
  font-size: 11px;
}

/* 卡片内容 */
.card-body {
  padding: 16px;
}

.stat-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--el-border-color-lighter);
}

.role-desc {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.5;
  margin-bottom: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--el-border-color-extra-light);
}

/* 权限模块预览 */
.perm-preview {
  margin-top: 12px;
}

.preview-title {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.module-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.module-tag {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--el-fill-color);
  border-radius: 3px;
  color: var(--el-text-color-regular);
}

.module-empty {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

/* 卡片底部 */
.card-footer {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--el-border-color-light);
  background: var(--el-fill-color-lighter);
}

.card-footer .el-button {
  font-size: 13px;
}

@media (max-width: 768px) {
  .roles-grid {
    grid-template-columns: 1fr;
  }
}

.init-alert {
  margin-bottom: 20px;
}
</style>