<template>
  <div class="credentials-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>SSH 凭证管理</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            添加凭证组
          </el-button>
        </div>
      </template>

      <el-table :data="credentials" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="凭证组名称" width="200" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editCredential(row.id)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteCredential(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadCredentials" @current-change="loadCredentials" />
      </div>
    </el-card>

    <!-- 添加/编辑凭证组对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? '编辑凭证组' : '添加凭证组'" width="600px">
      <el-form :model="credentialForm" label-width="120px">
        <el-form-item label="凭证组名称" required>
          <el-input v-model="credentialForm.name" placeholder="如 default、admin_group" :disabled="editMode" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="credentialForm.description" placeholder="凭证组用途说明" />
        </el-form-item>
        <el-form-item label="SSH 用户名" required>
          <el-input v-model="credentialForm.username" placeholder="如 admin、cisco" />
        </el-form-item>
        <el-form-item label="SSH 密码" required :required="!editMode">
          <el-input
            v-model="credentialForm.password"
            type="password"
            show-password
            :placeholder="editMode ? '不修改请留空' : '输入 SSH 密码'"
          />
        </el-form-item>
        <el-form-item label="Enable 密码">
          <el-input
            v-model="credentialForm.enable_password"
            type="password"
            show-password
            placeholder="可选，Cisco enable 模式密码"
          />
        </el-form-item>
        <el-form-item>
          <el-alert type="info" :closable="false">
            <template #title>
              <p>所有密码将使用 AES 加密存储于数据库中。</p>
              <p>SSH 密码必填，Enable 密码用于需要特权模式的设备。</p>
            </template>
          </el-alert>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="editMode ? updateCredential() : createCredential()">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCredentials, createCredential as createCredentialApi, getCredential, updateCredential as updateCredentialApi, deleteCredential as deleteCredentialApi } from '@/api'
import dayjs from 'dayjs'

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

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

const loadCredentials = async () => {
  loading.value = true
  try {
    const data = await getCredentials()
    credentials.value = data.items || []
  } catch (error) {
    ElMessage.error('加载凭证列表失败')
  } finally {
    loading.value = false
  }
}

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
    ElMessage.error('获取凭证详情失败')
  }
}

const createCredential = async () => {
  if (!credentialForm.value.name || !credentialForm.value.username || !credentialForm.value.password) {
    ElMessage.warning('请填写凭证组名称、用户名和密码')
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

    ElMessage.success('凭证组创建成功')
    showAddDialog.value = false
    resetForm()
    loadCredentials()
  } catch (error) {
    ElMessage.error('创建凭证失败')
    ElMessage.error('创建凭证失败')
  }
}

const updateCredential = async () => {
  if (!credentialForm.value.name || !credentialForm.value.username) {
    ElMessage.warning('请填写凭证组名称和用户名')
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

    ElMessage.success('凭证组更新成功')
    showAddDialog.value = false
    editMode.value = false
    currentCredentialId.value = null
    resetForm()
    loadCredentials()
  } catch (error) {
    ElMessage.error('更新凭证失败')
    ElMessage.error('更新凭证失败')
  }
}

const deleteCredential = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除此凭证组吗？删除后使用该凭证的设备将无法备份。', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteCredentialApi(id)
    ElMessage.success('凭证组删除成功')
    loadCredentials()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除凭证失败')
      ElMessage.error('删除凭证失败')
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
@media (max-width: 768px) {
  .filter-bar { flex-wrap: wrap; }
  .filter-bar .el-input, .filter-bar .el-select { width: 100% !important; }
  .card-header { flex-direction: column; gap: 8px; align-items: flex-start; }
}
</style>
