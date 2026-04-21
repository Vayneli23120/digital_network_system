<template>
  <div class="templates-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>配置模板</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            新建模板
          </el-button>
        </div>
      </template>

      <el-table :data="templates" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="模板名称" width="200" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewTemplate(row.id)">查看</el-button>
            <el-button size="small" @click="editTemplate(row.id)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteTemplate(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="currentPage" v-model:page-size="pageSize" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @size-change="loadTemplates" @current-change="loadTemplates" />
      </div>
    </el-card>

    <!-- 添加/编辑模板对话框 -->
    <el-dialog v-model="showAddDialog" :title="editMode ? '编辑模板' : '新建模板'" width="800px">
      <el-form :model="templateForm" label-width="100px">
        <el-form-item label="模板名称" required>
          <el-input v-model="templateForm.name" placeholder="如 switch_base_config" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="templateForm.description" placeholder="模板描述" />
        </el-form-item>
        <el-form-item label="模板内容" required>
          <el-input
            v-model="templateForm.template_content"
            type="textarea"
            :rows="15"
            placeholder="输入 Jinja2 模板内容，使用 {{ variable }} 表示变量"
            class="template-editor"
          />
        </el-form-item>
        <el-form-item label="变量定义">
          <el-input
            v-model="templateForm.variables"
            type="textarea"
            :rows="3"
            placeholder='JSON 格式，如：{"hostname": "SW-01", "ip": "192.168.1.1"}'
          />
        </el-form-item>
        <el-form-item label="变量说明">
          <el-alert type="info" :closable="false">
            <p>可用变量：</p>
            <ul>
              <li><code>{{ hostname }}</code> - 设备主机名</li>
              <li><code>{{ ip }}</code> - 管理 IP</li>
              <li><code>{{ location }}</code> - 设备位置</li>
              <li><code>{{ now }}</code> - 当前时间</li>
              <li><code>{{ now_str }}</code> - 当前时间字符串</li>
            </ul>
          </el-alert>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="editMode ? updateTemplate() : createTemplate()">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看模板对话框 -->
    <el-dialog v-model="showViewDialog" title="查看模板" width="800px">
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
import { getTemplates, createTemplate as createTemplateApi, getTemplate, updateTemplate as updateTemplateApi, deleteTemplate as deleteTemplateApi } from '@/api'
import dayjs from 'dayjs'

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
    ElMessage.error('加载模板失败')
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
    ElMessage.error('获取模板失败')
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
    ElMessage.error('获取模板失败')
  }
}

const createTemplate = async () => {
  try {
    let variables = {}
    if (templateForm.value.variables) {
      try {
        variables = JSON.parse(templateForm.value.variables)
      } catch (e) {
        ElMessage.warning('变量定义不是有效的 JSON 格式，将作为字符串存储')
      }
    }

    await createTemplateApi({
      name: templateForm.value.name,
      description: templateForm.value.description,
      template_content: templateForm.value.template_content,
      variables: JSON.stringify(variables)
    })

    ElMessage.success('模板创建成功')
    showAddDialog.value = false
    resetForm()
    loadTemplates()
  } catch (error) {
    ElMessage.error('创建模板失败')
    ElMessage.error('创建模板失败')
  }
}

const updateTemplate = async () => {
  try {
    let variables = {}
    if (templateForm.value.variables) {
      try {
        variables = JSON.parse(templateForm.value.variables)
      } catch (e) {
        ElMessage.warning('变量定义不是有效的 JSON 格式')
      }
    }

    await updateTemplateApi(currentTemplate.value.id, {
      name: templateForm.value.name,
      description: templateForm.value.description,
      template_content: templateForm.value.template_content,
      variables: JSON.stringify(variables)
    })

    ElMessage.success('模板更新成功')
    showAddDialog.value = false
    editMode.value = false
    currentTemplate.value = null
    resetForm()
    loadTemplates()
  } catch (error) {
    ElMessage.error('更新模板失败')
    ElMessage.error('更新模板失败')
  }
}

const deleteTemplate = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个模板吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteTemplateApi(id)
    ElMessage.success('模板删除成功')
    loadTemplates()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除模板失败')
      ElMessage.error('删除模板失败')
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.template-editor {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
}

.template-content {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
  margin-top: 10px;
}

ul {
  margin: 5px 0;
  padding-left: 20px;
}

code {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', 'Monaco', monospace;
}
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
@media (max-width: 768px) {
  .filter-bar { flex-wrap: wrap; }
  .filter-bar .el-input, .filter-bar .el-select { width: 100% !important; }
  .card-header { flex-direction: column; gap: 8px; align-items: flex-start; }
}
</style>
