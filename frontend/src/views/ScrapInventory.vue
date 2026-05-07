<template>
  <div class="scrap-inventory">
    <el-tabs v-model="activeTab">
      <!-- 报废库存 Tab -->
      <el-tab-pane label="报废库存" name="scrap">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>报废资产管理</span>
              <div class="header-buttons">
                <el-button type="success" @click="showScanDialog">扫码录入</el-button>
                <el-button type="primary" @click="showManualDialog">手动录入</el-button>
              </div>
            </div>
          </template>

          <!-- 统计卡片 -->
          <el-row :gutter="16" class="stats-row">
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <el-statistic title="报废种类" :value="stats.total_types" />
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <el-statistic title="报废总数" :value="stats.total_quantity" />
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <el-statistic title="报废总价值（元）" :value="stats.total_value" :precision="2" />
              </el-card>
            </el-col>
            <el-col :span="6">
              <el-card shadow="hover" class="stat-card">
                <el-statistic title="本月新增" :value="stats.month_count" />
              </el-card>
            </el-col>
          </el-row>

          <!-- 筛选工具栏 -->
          <div class="toolbar">
            <div class="toolbar-left">
              <el-input
                v-model="search"
                placeholder="搜索名称/型号/序列号"
                clearable
                class="search-input"
                @keyup.enter="loadScrapItems"
                @clear="loadScrapItems"
              />
              <el-select v-model="category" placeholder="分类" clearable class="category-select" @change="loadScrapItems">
                <el-option label="模块" value="模块" />
                <el-option label="电源" value="电源" />
                <el-option label="线缆" value="线缆" />
                <el-option label="其他" value="其他" />
              </el-select>
            </div>
            <div class="toolbar-right">
              <el-button size="small" @click="resetFilters">重置</el-button>
              <el-button size="small" type="primary" @click="loadScrapItems">搜索</el-button>
            </div>
          </div>

          <!-- 表格 -->
          <el-table :data="scrapItems" stripe border v-loading="loading">
            <el-table-column prop="serial_number" label="序列号" width="150">
              <template #default="{ row }">{{ row.serial_number || '-' }}</template>
            </el-table-column>
            <el-table-column prop="name" label="名称" width="150">
              <template #default="{ row }">
                <el-button type="primary" link @click="showScrapDetail(row)">
                  {{ row.name }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="part_number" label="型号" width="150">
              <template #default="{ row }">{{ row.part_number || '-' }}</template>
            </el-table-column>
            <el-table-column prop="unit_price" label="单价" width="100">
              <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="scraped_at" label="报废时间" width="160">
              <template #default="{ row }">{{ formatDateTime(row.scraped_at) }}</template>
            </el-table-column>
            <el-table-column prop="reason" label="报废原因" min-width="150" show-overflow-tooltip />
            <el-table-column prop="reference" label="关联维修" width="120" show-overflow-tooltip />
          </el-table>

          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="page"
              :page-size="50"
              layout="total, prev, pager, next"
              :total="total"
              @current-change="loadScrapItems"
            />
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 报废历史 Tab -->
      <el-tab-pane label="报废历史" name="history">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>报废记录历史</span>
              <el-button @click="loadHistory"><el-icon><Refresh /></el-icon> 刷新</el-button>
            </div>
          </template>
          <el-table :data="historyItems" v-loading="historyLoading" stripe border>
            <el-table-column prop="created_at" label="时间" width="180">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="name" label="备件名称" width="150">
              <template #default="{ row }">{{ row.name || '-' }}</template>
            </el-table-column>
            <el-table-column prop="part_number" label="型号" width="150">
              <template #default="{ row }">{{ row.part_number || '-' }}</template>
            </el-table-column>
            <el-table-column prop="serial_number" label="序列号" width="150">
              <template #default="{ row }">{{ row.serial_number || '-' }}</template>
            </el-table-column>
            <el-table-column prop="movement_type" label="类型" width="100" align="center">
              <template #default="{ row }">
                <el-tag type="danger" size="small">报废入库</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="80" align="right" />
            <el-table-column prop="unit_price" label="单价" width="100">
              <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" min-width="150" show-overflow-tooltip />
            <el-table-column prop="reference" label="关联维修" width="120" show-overflow-tooltip />
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="historyPage"
              :page-size="50"
              layout="total, prev, pager, next"
              :total="historyTotal"
              @current-change="loadHistory"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 报废详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="报废件详情" width="600px">
      <el-descriptions :column="2" border v-if="currentScrapItem">
        <el-descriptions-item label="序列号">{{ currentScrapItem.serial_number || '-' }}</el-descriptions-item>
        <el-descriptions-item label="名称">{{ currentScrapItem.name }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ currentScrapItem.part_number || '-' }}</el-descriptions-item>
        <el-descriptions-item label="单价">¥{{ (currentScrapItem.unit_price || 0).toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="报废时间">{{ formatDateTime(currentScrapItem.scraped_at) }}</el-descriptions-item>
        <el-descriptions-item label="报废原因">{{ currentScrapItem.reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="入库时间">{{ currentScrapItem.in_stock_at ? formatDateTime(currentScrapItem.in_stock_at) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="出库时间">{{ currentScrapItem.out_at ? formatDateTime(currentScrapItem.out_at) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="原位置">{{ currentScrapItem.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ currentScrapItem.notes || '-' }}</el-descriptions-item>
      </el-descriptions>

      <!-- 使用历史 -->
      <el-divider content-position="left">使用历史</el-divider>
      <el-table :data="currentScrapHistory" size="small" border v-if="currentScrapHistory.length > 0">
        <el-table-column prop="movement_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.movement_type === 'in' ? 'success' : row.movement_type === 'out' ? 'warning' : 'danger'" size="small">
              {{ row.movement_type === 'in' ? '入库' : row.movement_type === 'out' ? '出库' : '报废' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" min-width="150" />
        <el-table-column prop="reference" label="关联" width="120" />
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="暂无历史记录" :image-size="60" />
    </el-dialog>

    <!-- 扫码录入对话框 -->
    <el-dialog v-model="scanDialogVisible" title="扫码录入报废件" width="700px">
      <ScanSession
        ref="scanSessionRef"
        default-type="return"
        :auto-start="scanDialogVisible"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
      <template #footer>
        <el-button @click="scanDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="submitScrapFromScan" :disabled="scanItems.length === 0" :loading="submitting">
          确认报废入库（{{ scanItems.length }} 项）
        </el-button>
      </template>
    </el-dialog>

    <!-- 手动录入对话框 -->
    <el-dialog v-model="manualDialogVisible" title="手动录入报废件" width="600px">
      <el-form :model="manualForm" label-width="100px">
        <el-form-item label="序列号" required>
          <el-input v-model="manualForm.serial_number" placeholder="输入序列号查询" @keyup.enter="searchSerialForScrap" />
          <el-button size="small" type="primary" @click="searchSerialForScrap" :loading="searchingSerial" style="margin-top: 8px">
            查询
          </el-button>
        </el-form-item>

        <!-- 识别到的信息 -->
        <div v-if="foundPartInfo" style="background: var(--el-fill-color-light); padding: 12px; border-radius: 8px; margin-bottom: 16px">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
            <el-tag type="success" size="small">已识别</el-tag>
            <span style="font-weight: 600; color: var(--el-color-primary)">{{ foundPartInfo.serial_number }}</span>
          </div>
          <el-descriptions :column="3" size="small" border>
            <el-descriptions-item label="型号">{{ foundPartInfo.part_number }}</el-descriptions-item>
            <el-descriptions-item label="名称">{{ foundPartInfo.name }}</el-descriptions-item>
            <el-descriptions-item label="单价">¥{{ (foundPartInfo.unit_price || 0).toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="入库时间">{{ foundPartInfo.in_stock_at ? formatDateTime(foundPartInfo.in_stock_at) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="出库时间">{{ foundPartInfo.out_at ? formatDateTime(foundPartInfo.out_at) : '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="foundPartInfo.status === 'scrap' ? 'danger' : 'warning'" size="small">
                {{ foundPartInfo.status === 'scrap' ? '已报废' : foundPartInfo.status }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 未识别时手动填写 -->
        <el-divider v-if="!foundPartInfo" />

        <el-form-item label="型号" v-if="!foundPartInfo" required>
          <el-select v-model="manualForm.part_id" placeholder="从备件库选择型号" filterable clearable @change="onPartSelect">
            <el-option
              v-for="part in partOptions"
              :key="part.id"
              :label="`${part.part_number} - ${part.name}`"
              :value="part.id"
            />
          </el-select>
          <div style="margin-top: 8px">
            <el-input v-model="manualForm.part_number_manual" placeholder="或手动输入型号" style="width: 200px" />
            <el-input v-model="manualForm.name_manual" placeholder="名称（默认=型号）" style="width: 200px; margin-left: 8px" />
          </div>
        </el-form-item>

        <el-form-item label="单价">
          <el-input-number v-model="manualForm.unit_price" :min="0" :precision="2" :disabled="foundPartInfo" />
        </el-form-item>

        <el-form-item label="报废原因" required>
          <el-input v-model="manualForm.reason" type="textarea" placeholder="报废原因" />
        </el-form-item>

        <el-form-item label="关联维修">
          <el-input v-model="manualForm.reference" placeholder="关联维修单号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitManualScrap" :loading="submitting" :disabled="!manualForm.serial_number">
          确认报废入库
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getPartList, createMovement, getMovements, getPartBySerialNumber } from '@/api'
import { formatDateTime } from '@/utils/time'
import ScanSession from '@/components/ScanSession.vue'

// 状态
const activeTab = ref('scrap')
const scrapItems = ref([])
const loading = ref(false)
const search = ref('')
const category = ref('')
const page = ref(1)
const total = ref(0)

// 统计
const stats = reactive({
  total_types: 0,
  total_quantity: 0,
  total_value: 0,
  month_count: 0
})

// 报废历史
const historyItems = ref([])
const historyLoading = ref(false)
const historyPage = ref(1)
const historyTotal = ref(0)

// 详情对话框
const detailDialogVisible = ref(false)
const currentScrapItem = ref(null)
const currentScrapHistory = ref([])

// 扫码录入
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)
const scanItems = ref([])
const submitting = ref(false)

// 手动录入
const manualDialogVisible = ref(false)
const searchingSerial = ref(false)
const foundPartInfo = ref(null)
const partOptions = ref([])
const manualForm = reactive({
  serial_number: '',
  part_id: null,
  part_number_manual: '',
  name_manual: '',
  unit_price: 0,
  reason: '',
  reference: ''
})

// 加载报废库存
const loadScrapItems = async () => {
  loading.value = true
  try {
    // 查询报废入库记录
    const params = {
      movement_type: 'scrap_in',
      search: search.value,
      skip: (page.value - 1) * 50,
      limit: 50
    }
    const result = await getMovements(params)
    scrapItems.value = (result.items || []).map(item => ({
      serial_number: item.serial_number,
      name: item.name,
      part_number: item.part_number,
      unit_price: item.unit_price,
      scraped_at: item.created_at,
      reason: item.reason,
      reference: item.reference,
      part_id: item.part_id
    }))
    total.value = result.total || 0

    // 计算统计
    updateStats()
  } catch (e) {
    ElMessage.error('加载报废库存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// 更新统计
const updateStats = () => {
  const uniqueTypes = new Set(scrapItems.value.map(item => item.part_number))
  stats.total_types = uniqueTypes.size
  stats.total_quantity = scrapItems.value.length
  stats.total_value = scrapItems.value.reduce((sum, item) => sum + (item.unit_price || 0), 0)

  // 本月新增
  const now = new Date()
  const thisMonth = now.getMonth()
  const thisYear = now.getFullYear()
  stats.month_count = scrapItems.value.filter(item => {
    const itemDate = new Date(item.scraped_at)
    return itemDate.getMonth() === thisMonth && itemDate.getFullYear() === thisYear
  }).length
}

// 加载报废历史
const loadHistory = async () => {
  historyLoading.value = true
  try {
    const params = {
      movement_type: 'scrap_in',
      skip: (historyPage.value - 1) * 50,
      limit: 50
    }
    const result = await getMovements(params)
    historyItems.value = result.items || []
    historyTotal.value = result.total || 0
  } catch (e) {
    ElMessage.error('加载报废历史失败')
  } finally {
    historyLoading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  search.value = ''
  category.value = ''
  loadScrapItems()
}

// 显示报废详情
const showScrapDetail = async (row) => {
  currentScrapItem.value = row
  currentScrapHistory.value = []

  // 查询该序列号的完整历史
  if (row.serial_number) {
    try {
      const info = await getPartBySerialNumber(row.serial_number)
      currentScrapItem.value = {
        ...row,
        in_stock_at: info.in_stock_at,
        out_at: info.out_at,
        location: info.location,
        notes: info.notes
      }
      currentScrapHistory.value = info.history || []
    } catch (e) {
      // 如果查询失败，使用现有数据
    }
  }

  detailDialogVisible.value = true
}

// 显示扫码对话框
const showScanDialog = () => {
  scanItems.value = []
  scanDialogVisible.value = true
}

// 扫码会话完成
const onScanSessionComplete = async (result) => {
  scanItems.value = result.items || []
  if (scanItems.value.length > 0) {
    ElMessage.success(`已扫描 ${scanItems.value.length} 个报废件`)
  }
}

// 提交扫码录入
const submitScrapFromScan = async () => {
  if (scanItems.value.length === 0) return

  submitting.value = true
  try {
    for (const item of scanItems.value) {
      if (item.part_id) {
        await createMovement({
          part_id: item.part_id,
          movement_type: 'scrap_in',
          quantity: 1,
          serial_number: item.serial_number,
          reason: item.notes || '报废入库',
          reference: ''
        })
      }
    }
    ElMessage.success(`已报废入库 ${scanItems.value.length} 个件`)
    scanDialogVisible.value = false
    loadScrapItems()
    loadHistory()
  } catch (e) {
    ElMessage.error('报废入库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

// 显示手动录入对话框
const showManualDialog = async () => {
  // 加载备件列表供选择
  const result = await getPartList({ limit: 100 })
  partOptions.value = result.items || []

  Object.assign(manualForm, {
    serial_number: '',
    part_id: null,
    part_number_manual: '',
    name_manual: '',
    unit_price: 0,
    reason: '',
    reference: ''
  })
  foundPartInfo.value = null
  manualDialogVisible.value = true
}

// 查询序列号
const searchSerialForScrap = async () => {
  if (!manualForm.serial_number) {
    ElMessage.warning('请输入序列号')
    return
  }

  searchingSerial.value = true
  try {
    const result = await getPartBySerialNumber(manualForm.serial_number)
    foundPartInfo.value = result
    manualForm.part_id = result.id
    manualForm.unit_price = result.unit_price || 0
    ElMessage.success(`已识别: ${result.name || result.part_number}`)
  } catch (e) {
    foundPartInfo.value = null
    ElMessage.info('序列号未在系统中找到，请手动输入型号/名称')
  } finally {
    searchingSerial.value = false
  }
}

// 选择备件型号
const onPartSelect = () => {
  if (!manualForm.part_id) return
  const part = partOptions.value.find(p => p.id === manualForm.part_id)
  if (part) {
    manualForm.part_number_manual = part.part_number
    manualForm.name_manual = part.name || part.part_number
    manualForm.unit_price = part.unit_price || 0
  }
}

// 提交手动报废
const submitManualScrap = async () => {
  if (!manualForm.serial_number) {
    ElMessage.warning('请输入序列号')
    return
  }
  if (!manualForm.reason) {
    ElMessage.warning('请填写报废原因')
    return
  }

  submitting.value = true
  try {
    let partId = manualForm.part_id
    let partNumber = manualForm.part_number_manual
    let name = manualForm.name_manual || manualForm.part_number_manual

    if (foundPartInfo.value) {
      partId = foundPartInfo.value.id
      partNumber = foundPartInfo.value.part_number
      name = foundPartInfo.value.name
    }

    if (!partId && !partNumber) {
      ElMessage.warning('请选择或输入备件型号')
      submitting.value = false
      return
    }

    await createMovement({
      part_id: partId,
      movement_type: 'scrap_in',
      quantity: 1,
      serial_number: manualForm.serial_number,
      reason: manualForm.reason,
      reference: manualForm.reference
    })

    ElMessage.success('报废入库成功')
    manualDialogVisible.value = false
    loadScrapItems()
    loadHistory()
  } catch (e) {
    ElMessage.error('报废入库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadScrapItems()
  loadHistory()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-buttons {
  display: flex;
  gap: 8px;
}
.stats-row {
  margin-bottom: 20px;
}
.stat-card {
  text-align: center;
}
.pagination-bar {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  margin-bottom: 16px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.search-input {
  width: 200px;
}
.category-select {
  width: 100px;
}
.toolbar-right {
  display: flex;
  gap: 8px;
}
</style>