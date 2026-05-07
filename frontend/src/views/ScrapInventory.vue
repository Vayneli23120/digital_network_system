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
                placeholder="搜索名称/型号"
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

          <!-- 表格 - 按备件类型分组 -->
          <el-table :data="scrapItems" stripe border v-loading="loading">
            <el-table-column prop="name" label="名称" width="150">
              <template #default="{ row }">
                <el-button type="primary" link @click="showScrapDetail(row)">
                  {{ row.name }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="part_number" label="型号" width="150" />
            <el-table-column prop="manufacturer" label="厂商" width="120">
              <template #default="{ row }">{{ row.manufacturer || '-' }}</template>
            </el-table-column>
            <el-table-column prop="quantity" label="库存" width="100">
              <template #default="{ row }">
                <el-tag type="danger">{{ row.quantity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="总价" width="100">
              <template #default="{ row }">¥{{ row.total_value.toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" @click="showManualInDialog(row)">入库</el-button>
                <el-button size="small" type="danger" @click="showScrapOutDialog(row)">报废</el-button>
              </template>
            </el-table-column>
          </el-table>
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
                <el-tag :type="row.movement_type === 'scrap_in' ? 'warning' : 'danger'" size="small">
                  {{ row.movement_type === 'scrap_in' ? '报废入库' : '已报废' }}
                </el-tag>
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

    <!-- 报废详情对话框（只显示当前在报废库中的实例） -->
    <el-dialog v-model="detailDialogVisible" :title="currentScrapItem?.name + ' - 报废库存清单'" width="650px">
      <div v-if="currentScrapItem" class="part-info-header">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-statistic title="报废库存" :value="currentScrapItem.quantity || 0" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="库存总价" :value="currentScrapItem.total_value || 0" :precision="2" suffix="元" />
          </el-col>
        </el-row>
      </div>

      <el-table :data="currentScrapItem?.instances || []" stripe border size="small" style="margin-top: 16px">
        <el-table-column prop="serial_number" label="序列号" width="150" />
        <el-table-column prop="unit_price" label="单价" width="100">
          <template #default="{ row }">¥{{ row.unit_price?.toFixed(2) || '0.00' }}</template>
        </el-table-column>
        <el-table-column prop="scraped_at" label="报废入库时间" width="160">
          <template #default="{ row }">{{ row.scraped_at ? formatDateTime(row.scraped_at) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="报废原因" min-width="150" show-overflow-tooltip />
        <el-table-column prop="reference" label="关联维修" width="120" show-overflow-tooltip />
      </el-table>

      <el-empty v-if="!currentScrapItem?.instances?.length" description="该备件暂无报废库存" />
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

    <!-- 手动入库对话框（从备件库存页面复制） -->
    <el-dialog v-model="manualInDialogVisible" title="手动报废入库" width="500px">
      <el-form :model="manualInForm" label-width="80px">
        <el-form-item label="备件">
          <el-input :value="currentManualPart?.name" disabled />
        </el-form-item>
        <el-form-item label="序列号" required>
          <el-input v-model="manualInForm.serial_number" placeholder="输入序列号" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="manualInForm.unit_price" :min="0" :precision="2" placeholder="单价" />
        </el-form-item>
        <el-form-item label="报废原因">
          <el-input v-model="manualInForm.reason" type="textarea" placeholder="报废原因" />
        </el-form-item>
        <el-form-item label="关联维修">
          <el-input v-model="manualInForm.reference" placeholder="关联维修单号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualInDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitManualIn" :loading="manualInSubmitting">确认入库</el-button>
      </template>
    </el-dialog>

    <!-- 报废出库对话框 -->
    <el-dialog v-model="scrapOutDialogVisible" title="报废出库" width="500px">
      <div class="scrap-out-scan-btn">
        <el-button type="danger" @click="openScrapOutScanDialog">
          <el-icon><Aim /></el-icon>
          扫码报废出库
        </el-button>
        <div class="scrap-out-scan-tip">点击后用扫码枪扫描条形码建立连接，再扫描要出库的序列号</div>
      </div>

      <el-divider />

      <div class="scrap-out-manual">
        <div class="manual-title">手动输入</div>
        <el-form :model="scrapOutForm" label-width="80px">
          <el-form-item label="备件">
            <el-input :value="currentScrapOutPart?.name" disabled />
          </el-form-item>
          <el-form-item label="序列号" required>
            <el-input v-model="scrapOutForm.serial_number" placeholder="输入要出库的序列号" />
          </el-form-item>
          <el-form-item label="出库原因" required>
            <el-input v-model="scrapOutForm.reason" type="textarea" placeholder="出库原因（如：销毁、回收等）" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="scrapOutDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="submitScrapOut" :loading="scrapOutSubmitting" :disabled="!scrapOutForm.serial_number || !scrapOutForm.reason">
          确认出库
        </el-button>
      </template>
    </el-dialog>

    <!-- 报废出库扫码对话框 -->
    <el-dialog v-model="scrapOutScanDialogVisible" title="扫码报废出库" width="700px">
      <ScanSession
        ref="scrapOutScanSessionRef"
        default-type="scrap_out"
        :auto-start="scrapOutScanDialogVisible"
        @complete="onScrapOutScanComplete"
        @cancel="scrapOutScanDialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Aim } from '@element-plus/icons-vue'
import { getPartList, createMovement, getMovements, getPartBySerialNumber } from '@/api'
import { formatDateTime } from '@/utils/time'
import ScanSession from '@/components/ScanSession.vue'

// 状态
const activeTab = ref('scrap')
const scrapItems = ref([])  // 按备件分组的报废库存
const loading = ref(false)
const search = ref('')
const category = ref('')

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

// 手动入库
const manualInDialogVisible = ref(false)
const currentManualPart = ref(null)
const manualInSubmitting = ref(false)
const manualInForm = reactive({
  serial_number: '',
  unit_price: 0,
  reason: '',
  reference: ''
})

// 报废出库
const scrapOutDialogVisible = ref(false)
const currentScrapOutPart = ref(null)
const scrapOutSubmitting = ref(false)
const scrapOutForm = reactive({
  serial_number: '',
  reason: ''
})

// 报废出库扫码
const scrapOutScanDialogVisible = ref(false)
const scrapOutScanSessionRef = ref(null)

// 加载报废库存（按序列号跟踪，再按备件分组）
const loadScrapItems = async () => {
  loading.value = true
  try {
    // 查询所有报废入库和报废出库记录
    const scrapInResult = await getMovements({ movement_type: 'scrap_in', limit: 200 })
    const scrapOutResult = await getMovements({ movement_type: 'scrap_out', limit: 200 })
    const scrapInMovements = scrapInResult.items || []
    const scrapOutMovements = scrapOutResult.items || []

    // 按序列号跟踪：收集报废入库的序列号，排除已报废出库的序列号
    const scrapInBySerial = {}  // 序列号 -> 入库记录
    const scrapOutSerials = new Set()  // 已报废出库的序列号集合

    scrapInMovements.forEach(item => {
      if (item.serial_number) {
        scrapInBySerial[item.serial_number] = item
      }
    })

    scrapOutMovements.forEach(item => {
      if (item.serial_number) {
        scrapOutSerials.add(item.serial_number)
      }
    })

    // 当前报废库存 = 报废入库 - 报废出库（集合差）
    const currentScrapSerials = Object.keys(scrapInBySerial).filter(
      serial => !scrapOutSerials.has(serial)
    )

    // 按备件分组显示当前报废库存
    const groupedMap = {}
    currentScrapSerials.forEach(serial => {
      const item = scrapInBySerial[serial]
      const key = item.part_id || `unknown_${item.part_number || 'unknown'}`
      if (!groupedMap[key]) {
        groupedMap[key] = {
          part_id: item.part_id,
          name: item.name || item.part_number || '未知',
          part_number: item.part_number || '未知',
          manufacturer: '',
          unit_price: item.unit_price || 0,
          quantity: 0,
          total_value: 0,
          instances: []  // 当前在报废库中的实例
        }
      }
      groupedMap[key].quantity += 1
      groupedMap[key].total_value += (item.unit_price || 0)
      groupedMap[key].instances.push({
        serial_number: serial,
        unit_price: item.unit_price,
        scraped_at: item.created_at,
        movement_type: 'scrap_in',
        reason: item.reason,
        reference: item.reference
      })
    })

    // 应用筛选
    if (search.value) {
      const searchLower = search.value.toLowerCase()
      items = items.filter(item =>
        item.name.toLowerCase().includes(searchLower) ||
        item.part_number.toLowerCase().includes(searchLower)
      )
    }

    scrapItems.value = items
    updateStats(scrapInMovements, scrapOutMovements)
  } catch (e) {
    ElMessage.error('加载报废库存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// 更新统计（基于净库存）
const updateStats = (scrapInMovements, scrapOutMovements) => {
  stats.total_types = scrapItems.value.length
  stats.total_quantity = scrapItems.value.reduce((sum, item) => sum + item.quantity, 0)
  stats.total_value = scrapItems.value.reduce((sum, item) => sum + item.total_value, 0)

  // 本月新增（报废入库）
  const now = new Date()
  const thisMonth = now.getMonth()
  const thisYear = now.getFullYear()
  stats.month_count = scrapInMovements.filter(item => {
    const itemDate = new Date(item.created_at)
    return itemDate.getMonth() === thisMonth && itemDate.getFullYear() === thisYear
  }).length
}

// 加载报废历史（包含报废入库和报废出库）
const loadHistory = async () => {
  historyLoading.value = true
  try {
    // 查询报废入库和报废出库记录
    const scrapInResult = await getMovements({ movement_type: 'scrap_in', limit: 200 })
    const scrapOutResult = await getMovements({ movement_type: 'scrap_out', limit: 200 })
    const allRecords = [...(scrapInResult.items || []), ...(scrapOutResult.items || [])]

    // 按时间排序
    allRecords.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))

    // 分页处理
    const start = (historyPage.value - 1) * 50
    historyItems.value = allRecords.slice(start, start + 50)
    historyTotal.value = allRecords.length
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

// 显示报废详情（该备件的报废入库和出库历史）
// 显示报废详情（当前在报废库中的实例）
const showScrapDetail = (row) => {
  currentScrapItem.value = row
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

    if (foundPartInfo.value) {
      partId = foundPartInfo.value.id
    }

    if (!partId) {
      ElMessage.warning('请选择备件型号')
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

// 显示手动入库对话框（针对某个备件）
const showManualInDialog = (row) => {
  currentManualPart.value = row
  Object.assign(manualInForm, {
    serial_number: '',
    unit_price: row.unit_price || 0,
    reason: '',
    reference: ''
  })
  manualInDialogVisible.value = true
}

// 提交手动入库
const submitManualIn = async () => {
  if (!manualInForm.serial_number) {
    ElMessage.warning('请输入序列号')
    return
  }

  manualInSubmitting.value = true
  try {
    await createMovement({
      part_id: currentManualPart.value.part_id,
      movement_type: 'scrap_in',
      quantity: 1,
      serial_number: manualInForm.serial_number,
      reason: manualInForm.reason || '报废入库',
      reference: manualInForm.reference
    })
    ElMessage.success('报废入库成功')
    manualInDialogVisible.value = false
    loadScrapItems()
    loadHistory()
  } catch (e) {
    ElMessage.error('入库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    manualInSubmitting.value = false
  }
}

// 显示报废出库对话框
const showScrapOutDialog = (row) => {
  currentScrapOutPart.value = row
  Object.assign(scrapOutForm, {
    serial_number: '',
    reason: ''
  })
  scrapOutDialogVisible.value = true
}

// 提交报废出库
const submitScrapOut = async () => {
  if (!scrapOutForm.serial_number) {
    ElMessage.warning('请输入序列号')
    return
  }
  if (!scrapOutForm.reason) {
    ElMessage.warning('请填写出库原因')
    return
  }

  scrapOutSubmitting.value = true
  try {
    await createMovement({
      part_id: currentScrapOutPart.value.part_id,
      movement_type: 'scrap_out',
      quantity: 1,
      serial_number: scrapOutForm.serial_number,
      reason: scrapOutForm.reason,
      reference: ''
    })
    ElMessage.success('报废出库成功')
    scrapOutDialogVisible.value = false
    loadScrapItems()
    loadHistory()
  } catch (e) {
    ElMessage.error('出库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    scrapOutSubmitting.value = false
  }
}

// 打开报废出库扫码对话框
const openScrapOutScanDialog = () => {
  scrapOutScanDialogVisible.value = true
}

// 报废出库扫码会话完成（后端已创建出库记录，前端只需刷新数据）
const onScrapOutScanComplete = async (result) => {
  const scrapOutCount = result.scrap_out_count || (result.items?.length || 0)
  if (scrapOutCount === 0) {
    ElMessage.warning('未扫描任何序列号')
    return
  }

  ElMessage.success(`已报废出库 ${scrapOutCount} 个件`)
  scrapOutScanDialogVisible.value = false
  scrapOutDialogVisible.value = false
  loadScrapItems()
  loadHistory()
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
.scrap-out-scan-btn {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}
.scrap-out-scan-tip {
  font-size: 12px;
  color: var(--el-color-danger);
  padding: 4px 8px;
  background: var(--el-color-danger-light-9);
  border-radius: 4px;
}
.scrap-out-manual {
  margin-top: 16px;
}
.manual-title {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
}
</style>