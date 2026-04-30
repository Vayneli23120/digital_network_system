<template>
  <div class="users-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>用户管理</h1>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="showAddDialog = true">
          添加用户
        </el-button>
        <el-button :icon="Refresh" @click="loadUsers">刷新</el-button>
      </div>
    </div>

    <!-- 用户列表 -->
    <el-card class="table-card">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="full_name" label="姓名" width="150">
          <template #default="{ row }">{{ row.full_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" width="200">
          <template #default="{ row }">{{ row.email || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="200">
          <template #default="{ row }">
            <el-tag v-for="role in row.roles" :key="role.id" size="small" type="info" class="role-tag">
              {{ role.name }}
            </el-tag>
            <span v-if="!row.roles || row.roles.length === 0">-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="超级用户" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_superuser" type="warning" size="small">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="160">
          <template #default="{ row }">{{ row.last_login ? formatDateTime(row.last_login) : '从未登录' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="editUser(row)">编辑</el-button>
            <el-button type="warning" size="small" link @click="resetPassword(row)">重置密码</el-button>
            <el-button
              v-if="!row.is_superuser"
              type="danger"
              size="small"
              link
              @click="deleteUserConfirm(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加用户对话框 -->
    <el-dialog v-model="showAddDialog" title="添加用户" width="500px">
      <el-form :model="addForm" :rules="addRules" ref="addFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="addForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="addForm.full_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="addForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="addForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="addForm.role_ids" multiple placeholder="请选择角色" style="width: 100%">
            <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="addForm.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="createUser" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑用户对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑用户" width="500px">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="80px">
        <el-form-item label="用户名">
          <el-input :value="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="editForm.full_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="editForm.role_ids" multiple placeholder="请选择角色" style="width: 100%">
            <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="editForm.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateUser" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="showPasswordDialog" title="重置密码" width="400px">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="80px">
        <el-form-item label="用户">
          <el-input :value="passwordForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="submitPasswordReset" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { formatDateTime } from '@/utils/time'
import {
  getUsers, createUser as createUserApi, updateUser as updateUserApi,
  deleteUser as deleteUserApi, getRoles
} from '@/api'

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
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, message: '用户名至少3个字符', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少6个字符', trigger: 'blur' }],
  email: [{ type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }]
}

const editRules = {
  email: [{ type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }]
}

const passwordRules = {
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '密码至少6个字符', trigger: 'blur' }]
}

// 加载用户列表
const loadUsers = async () => {
  loading.value = true
  try {
    const data = await getUsers()
    users.value = data || []
  } catch (e) {
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

// 加载角色列表
const loadRoles = async () => {
  try {
    const data = await getRoles()
    roles.value = data || []
  } catch (e) {
    console.error('加载角色失败', e)
  }
}

// 创建用户
const createUser = async () => {
  const valid = await addFormRef.value?.validate()
  if (!valid) return

  submitting.value = true
  try {
    await createUserApi(addForm.value)
    ElMessage.success('用户创建成功')
    showAddDialog.value = false
    addForm.value = { username: '', full_name: '', email: '', password: '', role_ids: [], is_active: true }
    loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建用户失败')
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
    ElMessage.success('用户更新成功')
    showEditDialog.value = false
    loadUsers()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '更新用户失败')
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
    ElMessage.success('密码重置成功')
    showPasswordDialog.value = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '密码重置失败')
  } finally {
    submitting.value = false
  }
}

// 删除用户确认
const deleteUserConfirm = async (user) => {
  try {
    await ElMessageBox.confirm(`确定删除用户 "${user.username}"？此操作不可恢复。`, '删除确认', {
      type: 'warning'
    })
    await deleteUserApi(user.id)
    ElMessage.success('用户删除成功')
    loadUsers()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除用户失败')
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