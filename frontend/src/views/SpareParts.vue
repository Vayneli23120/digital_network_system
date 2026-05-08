<template>
  <div class="spare-parts">
    <el-tabs v-model="activeTab">
      <!-- 备件列表 Tab -->
      <el-tab-pane label="备件列表" name="parts">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>备件资产管理</span>
              <div class="header-buttons">
                <el-button type="success" @click="showScanDialog('in')">扫码入库</el-button>
                <el-button type="warning" @click="showScanDialog('out')">扫码出库</el-button>
                <el-button type="primary" @click="showAddDialog">新增备件</el-button>
              </div>
            </div>
          </template>

          <!-- 统计卡片 -->
          <el-row :gutter="16" class="stats-row">
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="备件种类" :value="stats.total_parts" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="总库存" :value="stats.total_quantity" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="库存不足" :value="stats.low_stock_count" value-style="color: #F56C6C" />
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="stat-card">
            <el-statistic title="总价值（元）" :value="stats.total_value" :precision="2" />
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
            @keyup.enter="loadParts"
            @clear="loadParts"
          />
          <el-select v-model="category" placeholder="分类" clearable class="category-select" @change="loadParts">
            <el-option label="模块" value="模块" />
            <el-option label="电源" value="电源" />
            <el-option label="线缆" value="线缆" />
            <el-option label="其他" value="其他" />
          </el-select>
          <el-checkbox v-model="lowStock" @change="loadParts">库存不足</el-checkbox>
        </div>
        <div class="toolbar-right">
          <el-button size="small" @click="resetFilters">重置</el-button>
          <el-button size="small" type="primary" @click="loadParts">搜索</el-button>
        </div>
      </div>

      <!-- 表格 -->
      <el-table :data="parts" stripe border v-loading="loading">
        <el-table-column prop="name" label="名称" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="showPartDetail(row)">
              {{ row.name }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="part_number" label="型号" width="150" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="manufacturer" label="厂商" width="120" />
        <el-table-column prop="quantity_in_stock" label="库存" width="100">
          <template #default="{ row }">
            <el-tag :type="row.quantity_in_stock < row.min_quantity ? 'danger' : 'success'">
              {{ row.quantity_in_stock }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="min_quantity" label="最低库存" width="100" />
        <el-table-column label="总价" width="100">
          <template #default="{ row }">¥{{ (row.unit_price * row.quantity_in_stock).toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="success" @click="showManualInDialog(row)">入库</el-button>
            <el-button size="small" type="warning" @click="showManualOutDialog(row)">出库</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
      </el-tab-pane>

      <!-- 出入库历史 Tab -->
      <el-tab-pane label="出入库历史" name="movements">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>出入库记录</span>
              <el-button @click="loadMovements"><el-icon><Refresh /></el-icon> 刷新</el-button>
            </div>
          </template>

          <!-- 筛选工具栏 -->
          <div class="toolbar">
            <div class="toolbar-left">
              <el-input
                v-model="movementFilter.keyword"
                placeholder="搜索名称/型号/序列号"
                clearable
                class="search-input"
                @keyup.enter="loadMovements"
                @clear="loadMovements"
              />
              <el-select v-model="movementFilter.movement_type" placeholder="类型" clearable class="type-select" @change="loadMovements">
                <el-option label="入库" value="in" />
                <el-option label="出库" value="out" />
                <el-option label="报废入库" value="scrap_in" />
                <el-option label="报废出库" value="scrap_out" />
              </el-select>
              <el-date-picker
                v-model="movementFilter.start_date"
                type="date"
                placeholder="开始日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                class="date-picker"
                @change="loadMovements"
              />
              <el-date-picker
                v-model="movementFilter.end_date"
                type="date"
                placeholder="结束日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                class="date-picker"
                @change="loadMovements"
              />
              <el-input
                v-model="movementFilter.operator"
                placeholder="操作人"
                clearable
                class="operator-input"
                @keyup.enter="loadMovements"
                @clear="loadMovements"
              />
            </div>
            <div class="toolbar-right">
              <el-button size="small" @click="resetMovementFilter">重置</el-button>
              <el-button size="small" type="primary" @click="loadMovements">搜索</el-button>
            </div>
          </div>

          <el-table :data="movements" v-loading="movementsLoading" stripe border @row-click="showMovementDetail">
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="name" label="备件名称" width="130">
              <template #default="{ row }">
                <el-button type="primary" link>{{ row.name || '-' }}</el-button>
              </template>
            </el-table-column>
            <el-table-column prop="serial_number" label="序列号" width="120">
              <template #default="{ row }">{{ row.serial_number || '-' }}</template>
            </el-table-column>
            <el-table-column prop="po_number" label="PO号" width="80">
              <template #default="{ row }">{{ row.po_number || '-' }}</template>
            </el-table-column>
            <el-table-column prop="movement_type" label="类型" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="getMovementTypeTag(row.movement_type)" size="small">
                  {{ getMovementTypeText(row.movement_type) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="60" align="right" />
            <el-table-column prop="unit_price" label="单价" width="80">
              <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="设备" width="100">
              <template #default="{ row }">
                <span v-if="row.target_device_name">{{ row.target_device_name }}</span>
                <span v-else-if="row.source_device_name">{{ row.source_device_name }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" min-width="120" show-overflow-tooltip />
          </el-table>
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="movementPage"
              :page-size="50"
              layout="total, prev, pager, next"
              :total="movementTotal"
              @current-change="loadMovements"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 出入库详情对话框 -->
    <el-dialog v-model="movementDetailVisible" title="出入库详情" width="750px">
      <!-- 批次概览（紧凑） -->
      <div v-if="currentMovement" class="compact-header">
        <span>时间: {{ formatDateTime(currentMovement.created_at) }}</span>
        <span>
          <el-tag :type="getMovementTypeTag(currentMovement.movement_type)" size="small">
            {{ getMovementTypeText(currentMovement.movement_type) }}
          </el-tag>
        </span>
        <span>批次: <strong>{{ currentMovement.batch_total || 1 }}</strong> 件</span>
        <span v-if="currentMovement.session_code">批次码: {{ currentMovement.session_code }}</span>
        <span v-if="currentMovement.target_device_name">目标设备: {{ currentMovement.target_device_name }}</span>
        <span v-if="currentMovement.source_device_name">来源设备: {{ currentMovement.source_device_name }}</span>
        <span v-if="currentMovement.reason">原因: {{ currentMovement.reason }}</span>
      </div>

      <!-- 本批次备件清单表格 -->
      <el-table :data="batchAllItems" stripe border size="small" style="margin-top: 8px">
        <el-table-column label="" width="60">
          <template #default="{ row }">
            <el-tag v-if="row.isCurrent" type="primary" size="small">当前</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="serial_number" label="序列号" width="150">
          <template #default="{ row }">
            <span class="text-primary">{{ row.serial_number || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="po_number" label="PO号" width="100">
          <template #default="{ row }">{{ row.po_number || '-' }}</template>
        </el-table-column>
        <el-table-column prop="part_number" label="型号" width="120">
          <template #default="{ row }">{{ row.part_number || '-' }}</template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="120">
          <template #default="{ row }">{{ row.name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="unit_price" label="单价" width="80">
          <template #default="{ row }">
            <span class="text-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑备件' : '新增备件'" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="型号" required>
          <el-input v-model="form.part_number" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category">
            <el-option label="模块" value="模块" />
            <el-option label="电源" value="电源" />
            <el-option label="线缆" value="线缆" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="厂商">
          <el-input v-model="form.manufacturer" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" />
        </el-form-item>
        <el-form-item label="初始库存">
          <el-input-number v-model="form.quantity_in_stock" :min="0" />
        </el-form-item>
        <el-form-item label="最低库存">
          <el-input-number v-model="form.min_quantity" :min="0" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="form.unit_price" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="存放位置">
          <el-input v-model="form.location" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePart">保存</el-button>
      </template>
    </el-dialog>

    <!-- 入库/出库对话框 -->
    <el-dialog v-model="movementDialogVisible" :title="movementType === 'in' ? '入库' : '出库'" width="400px">
      <el-form :model="movementForm" label-width="80px">
        <el-form-item label="备件">
          <el-input :value="currentPart?.name" disabled />
        </el-form-item>
        <el-form-item label="数量" required>
          <el-input-number v-model="movementForm.quantity" :min="1" />
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="movementForm.reason" type="textarea" />
        </el-form-item>
        <el-form-item label="操作人">
          <el-input v-model="movementForm.operator" />
        </el-form-item>
        <el-form-item label="参考">
          <el-input v-model="movementForm.reference" placeholder="关联工单/设备编号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="movementDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitMovement">确认</el-button>
      </template>
    </el-dialog>

    <!-- 选择备件和填PO号对话框 -->
    <el-dialog v-model="selectPartDialogVisible" title="选择入库备件" width="500px">
      <el-form :model="scanInForm" label-width="80px">
        <el-form-item label="选择备件" required>
          <el-select v-model="scanInForm.part_id" placeholder="选择要入库的备件型号" filterable>
            <el-option
              v-for="part in parts"
              :key="part.id"
              :label="`${part.name} (${part.part_number})`"
              :value="part.id"
            >
              <span>{{ part.name }}</span>
              <span style="color: var(--el-text-color-secondary); margin-left: 8px;">{{ part.part_number }}</span>
              <span style="color: var(--el-text-color-secondary); margin-left: 8px;">库存: {{ part.quantity_in_stock }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="PO号" required>
          <el-input v-model="scanInForm.po_number" placeholder="采购订单号（同一批次）" />
        </el-form-item>
        <el-form-item label="存放位置">
          <el-input v-model="scanInForm.location" placeholder="存放位置" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="selectPartDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="startScanIn" :disabled="!scanInForm.part_id || !scanInForm.po_number">
          开始扫码入库
        </el-button>
      </template>
    </el-dialog>

    <!-- 扫码出入库对话框 -->
    <el-dialog v-model="scanDialogVisible" :title="scanMode === 'in' ? '扫码入库' : '扫码出库'" width="700px">
      <ScanSession
        ref="scanSessionRef"
        :default-type="scanMode"
        :part-id="scanInForm.part_id"
        :po-number="scanInForm.po_number"
        :location="scanInForm.location"
        :auto-start="scanDialogVisible"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
    </el-dialog>

    <!-- 备件详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="库存清单" width="750px">
      <!-- 库存概览（紧凑） -->
      <div v-if="currentDetailPart" class="compact-header">
        <span>在库: <strong>{{ currentDetailPart.in_stock_count || 0 }}</strong> 件</span>
        <span>总价: <strong class="text-success">¥{{ totalStockValue.toFixed(2) }}</strong></span>
        <span>型号: {{ currentDetailPart.part_number || '-' }}</span>
      </div>

      <!-- 库存清单表格 -->
      <el-table :data="inStockInstances" v-loading="instancesLoading" stripe border size="small" style="margin-top: 8px">
        <el-table-column prop="serial_number" label="序列号" width="150">
          <template #default="{ row }">
            <span class="text-primary">{{ row.serial_number || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="po_number" label="PO号" width="100">
          <template #default="{ row }">{{ row.po_number || '-' }}</template>
        </el-table-column>
        <el-table-column prop="unit_price" label="单价" width="80">
          <template #default="{ row }">
            <span class="text-success">¥{{ (row.unit_price || 0).toFixed(2) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="location" label="位置" width="80">
          <template #default="{ row }">{{ row.location || '-' }}</template>
        </el-table-column>
        <el-table-column prop="in_stock_at" label="入库时间" width="140">
          <template #default="{ row }">{{ row.in_stock_at ? formatDateTime(row.in_stock_at) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.notes || '-' }}</template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!instancesLoading && inStockInstances.length === 0" description="该备件暂无在库实例" />
    </el-dialog>

    <!-- 手动入库对话框 -->
    <el-dialog v-model="manualInDialogVisible" title="手动入库" width="500px">
      <el-form :model="manualInForm" label-width="80px">
        <el-form-item label="备件">
          <el-input :value="currentManualPart?.name" disabled />
        </el-form-item>
        <el-form-item label="序列号" required>
          <el-input v-model="manualInForm.serial_number" placeholder="输入序列号" />
        </el-form-item>
        <el-form-item label="PO号">
          <el-input v-model="manualInForm.po_number" placeholder="采购订单号" />
        </el-form-item>
        <el-form-item label="单价">
          <el-input-number v-model="manualInForm.unit_price" :min="0" :precision="2" placeholder="单价" />
        </el-form-item>
        <el-form-item label="存放位置">
          <el-input v-model="manualInForm.location" placeholder="存放位置" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="manualInForm.notes" type="textarea" placeholder="备注信息" />
        </el-form-item>
        <el-form-item label="入库原因">
          <el-input v-model="manualInForm.reason" type="textarea" placeholder="入库原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualInDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitManualIn" :loading="manualInSubmitting">确认入库</el-button>
      </template>
    </el-dialog>

    <!-- 手动出库对话框 -->
    <el-dialog v-model="manualOutDialogVisible" title="手动出库" width="500px">
      <el-form :model="manualOutForm" label-width="80px">
        <el-form-item label="序列号" required>
          <el-input v-model="manualOutForm.serial_number" placeholder="输入序列号查询备件" @keyup.enter="searchSerialForOut" />
          <el-button size="small" type="primary" @click="searchSerialForOut" :loading="searchingSerial" style="margin-top: 8px">查询</el-button>
        </el-form-item>
        <div v-if="outPartInfo" style="background: #f5f7fa; padding: 12px; border-radius: 8px; margin-bottom: 16px">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px">
            <el-tag :type="outPartInfo.status === 'in_stock' ? 'success' : 'warning'" size="small">
              {{ outPartInfo.status === 'in_stock' ? '在库' : '已出库' }}
            </el-tag>
            <span style="font-weight: 600; color: #1677ff">{{ outPartInfo.serial_number }}</span>
          </div>
          <div style="color: #8c8c8c; font-size: 14px">
            <span style="min-width: 50px">名称：</span>{{ outPartInfo.name }}<br>
            <span style="min-width: 50px">型号：</span>{{ outPartInfo.part_number }}<br>
            <span style="min-width: 50px">位置：</span>{{ outPartInfo.location || '-' }}
          </div>
          <el-alert v-if="outPartInfo.status !== 'in_stock'" type="warning" :closable="false" style="margin-top: 8px">
            该序列号不在库中，无法出库
          </el-alert>
        </div>
        <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" label="出库原因" required>
          <el-input v-model="manualOutForm.reason" type="textarea" placeholder="出库原因" />
        </el-form-item>
        <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" label="出库去向">
          <el-input v-model="manualOutForm.destination" placeholder="出库去向（设备/项目等）" />
        </el-form-item>
        <el-form-item v-if="outPartInfo && outPartInfo.status === 'in_stock'" label="备注">
          <el-input v-model="manualOutForm.notes" type="textarea" placeholder="备注信息" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="manualOutDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitManualOut" :loading="manualOutSubmitting" :disabled="!outPartInfo || outPartInfo.status !== 'in_stock'">确认出库</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getPartList, createPart, updatePart, getPartStats, createMovement, getMovements, getMovementDetail, getPartInstances, manualStockIn, manualStockOut, getPartBySerialNumber } from '@/api'
import { formatDateTime } from '@/utils/time'
import ScanSession from '@/components/ScanSession.vue'

const parts = ref([])
const loading = ref(false)
const search = ref('')
const category = ref('')
const lowStock = ref(false)
const stats = reactive({ total_parts: 0, total_quantity: 0, low_stock_count: 0, total_value: 0 })
const activeTab = ref('parts')
const movements = ref([])
const movementsLoading = ref(false)
const movementPage = ref(1)
const movementTotal = ref(0)

// 出入库筛选条件
const movementFilter = reactive({
  keyword: '',
  movement_type: '',
  start_date: '',
  end_date: '',
  operator: ''
})

// 备件详情对话框
const detailDialogVisible = ref(false)
const currentDetailPart = ref(null)
const partInstances = ref([])
const instancesLoading = ref(false)

// 计算库存总价（在库实例的单价之和）
const totalStockValue = computed(() => {
  return partInstances.value
    .filter(item => item.status === 'in_stock')
    .reduce((sum, item) => sum + (item.unit_price || currentDetailPart.value?.unit_price || 0), 0)
})

// 只显示在库的实例
const inStockInstances = computed(() => {
  return partInstances.value.filter(item => item.status === 'in_stock')
})

// 手动入库
const manualInDialogVisible = ref(false)
const currentManualPart = ref(null)
const manualInSubmitting = ref(false)
const manualInForm = reactive({
  serial_number: '',
  po_number: '',
  unit_price: 0,
  location: '',
  notes: '',
  reason: ''
})

// 手动出库
const manualOutDialogVisible = ref(false)
const manualOutSubmitting = ref(false)
const searchingSerial = ref(false)
const outPartInfo = ref(null)
const manualOutForm = reactive({
  serial_number: '',
  reason: '',
  destination: '',
  notes: ''
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const form = reactive({
  name: '', part_number: '', category: '', manufacturer: '',
  description: '', quantity_in_stock: 0, min_quantity: 0, unit_price: 0, location: ''
})

const movementDialogVisible = ref(false)
const movementType = ref('in')
const currentPart = ref(null)
const movementForm = reactive({ quantity: 1, reason: '', operator: '', reference: '' })

// 扫码会话相关
const scanDialogVisible = ref(false)
const scanMode = ref('in')
const scanSessionRef = ref(null)
const selectPartDialogVisible = ref(false)  // 选择备件对话框
const scanInForm = reactive({
  part_id: null,
  po_number: '',
  location: ''
})

// 显示扫码对话框（入库需要先选择备件）
const showScanDialog = (mode) => {
  scanMode.value = mode
  if (mode === 'in') {
    // 入库：先显示选择备件对话框
    selectPartDialogVisible.value = true
    scanInForm.part_id = null
    scanInForm.po_number = ''
    scanInForm.location = ''
  } else {
    // 出库：直接开始扫码会话
    scanDialogVisible.value = true
  }
}

// 出入库详情
const movementDetailVisible = ref(false)
const currentMovement = ref(null)

// 批次总价值计算
const batchTotalValue = computed(() => {
  if (!currentMovement.value) return 0
  let total = currentMovement.value.unit_price || 0
  if (currentMovement.value.batch_items) {
    for (const item of currentMovement.value.batch_items) {
      total += item.unit_price || 0
    }
  }
  return total
})

// 合并当前记录和batch_items用于表格显示
const batchAllItems = computed(() => {
  if (!currentMovement.value) return []
  const current = {
    serial_number: currentMovement.value.serial_number,
    po_number: currentMovement.value.po_number,
    part_number: currentMovement.value.part_number,
    name: currentMovement.value.name,
    unit_price: currentMovement.value.unit_price,
    isCurrent: true
  }
  const others = (currentMovement.value.batch_items || []).map(item => ({ ...item, isCurrent: false }))
  return [current, ...others]
})

const showMovementDetail = async (row) => {
  // 获取完整详情（包含同批次备件清单）
  try {
    const detail = await getMovementDetail(row.id)
    currentMovement.value = detail
  } catch (e) {
    currentMovement.value = row  // 失败时使用行数据
  }
  movementDetailVisible.value = true
}

// 开始扫码入库
const startScanIn = () => {
  selectPartDialogVisible.value = false
  scanDialogVisible.value = true
}

// 扫码会话完成处理
const onScanSessionComplete = async (result) => {
  const { session_type, items, added_count, new_stock, message } = result
  if (items && items.length === 0) return

  scanDialogVisible.value = false

  if (message) {
    ElMessage.success(message)
  } else {
    ElMessage.success(`成功处理 ${items?.length || 0} 项`)
  }

  loadParts()
}

// 显示备件详情（实例列表）
const showPartDetail = async (row) => {
  currentDetailPart.value = row
  detailDialogVisible.value = true
  instancesLoading.value = true

  try {
    const result = await getPartInstances(row.id)
    partInstances.value = result.instances || []
    currentDetailPart.value = {
      ...row,
      in_stock_count: result.in_stock_count,
      out_count: result.out_count,
      total_instances: result.total_instances
    }
  } catch (e) {
    ElMessage.error('加载备件实例失败：' + (e.response?.data?.detail || e.message))
  } finally {
    instancesLoading.value = false
  }
}

const loadParts = async () => {
  loading.value = true
  try {
    const params = { search: search.value, category: category.value, low_stock: lowStock.value, limit: 200 }
    const result = await getPartList(params)
    parts.value = result.items || []
    const statsData = await getPartStats()
    Object.assign(stats, statsData)
  } catch (e) {
    ElMessage.error('加载备件失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// 出入库类型显示
const getMovementTypeTag = (type) => {
  const tags = { in: 'success', out: 'warning', scrap_in: 'info', scrap_out: 'danger' }
  return tags[type] || ''
}

const getMovementTypeText = (type) => {
  const texts = { in: '入库', out: '出库', scrap_in: '报废入库', scrap_out: '已报废' }
  return texts[type] || type
}

// 重置筛选条件
const resetFilters = () => {
  search.value = ''
  category.value = ''
  lowStock.value = false
  loadParts()
}

// 显示手动入库对话框
const showManualInDialog = (row) => {
  currentManualPart.value = row
  Object.assign(manualInForm, {
    serial_number: '',
    po_number: '',
    unit_price: row.unit_price || 0,
    location: row.location || '',
    notes: '',
    reason: ''
  })
  manualInDialogVisible.value = true
}

// 显示手动出库对话框
const showManualOutDialog = (row) => {
  // row 可能是 null（从顶部按钮调用），或者是备件行（从表格按钮调用）
  Object.assign(manualOutForm, {
    serial_number: '',
    reason: '',
    destination: '',
    notes: ''
  })
  outPartInfo.value = null
  manualOutDialogVisible.value = true
}

// 查询序列号对应的备件信息
const searchSerialForOut = async () => {
  if (!manualOutForm.serial_number) {
    ElMessage.warning('请输入序列号')
    return
  }

  searchingSerial.value = true
  try {
    const result = await getPartBySerialNumber(manualOutForm.serial_number)
    outPartInfo.value = result
    if (result.status !== 'in_stock') {
      ElMessage.warning('该序列号不在库中')
    }
  } catch (e) {
    ElMessage.error('未找到该序列号的备件')
    outPartInfo.value = null
  } finally {
    searchingSerial.value = false
  }
}

// 提交手动入库
const submitManualIn = async () => {
  if (!manualInForm.serial_number) {
    ElMessage.warning('请输入序列号')
    return
  }

  manualInSubmitting.value = true
  try {
    const result = await manualStockIn(currentManualPart.value.id, manualInForm)
    ElMessage.success(result.message || '入库成功')
    manualInDialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error('入库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    manualInSubmitting.value = false
  }
}

// 提交手动出库
const submitManualOut = async () => {
  if (!outPartInfo.value || outPartInfo.value.status !== 'in_stock') {
    ElMessage.warning('该序列号不在库中，无法出库')
    return
  }
  if (!manualOutForm.reason) {
    ElMessage.warning('请填写出库原因')
    return
  }

  manualOutSubmitting.value = true
  try {
    // 使用查询到的 part_id 进行出库
    const result = await manualStockOut(outPartInfo.value.id, {
      serial_number: manualOutForm.serial_number,
      reason: manualOutForm.reason,
      destination: manualOutForm.destination,
      notes: manualOutForm.notes
    })
    ElMessage.success(result.message || '出库成功')
    manualOutDialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error('出库失败：' + (e.response?.data?.detail || e.message))
  } finally {
    manualOutSubmitting.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  Object.assign(form, { name: '', part_number: '', category: '', manufacturer: '', description: '', quantity_in_stock: 0, min_quantity: 0, unit_price: 0, location: '' })
  dialogVisible.value = true
}

const showEditDialog = (row) => {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, row)
  dialogVisible.value = true
}

const savePart = async () => {
  try {
    if (isEdit.value) {
      await updatePart(editId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createPart(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

const showInDialog = (row) => {
  currentPart.value = row
  movementType.value = 'in'
  movementForm.quantity = 1
  movementForm.reason = ''
  movementForm.operator = ''
  movementForm.reference = ''
  movementDialogVisible.value = true
}

const showOutDialog = (row) => {
  currentPart.value = row
  movementType.value = 'out'
  movementForm.quantity = 1
  movementForm.reason = ''
  movementForm.operator = ''
  movementForm.reference = ''
  movementDialogVisible.value = true
}

const submitMovement = async () => {
  try {
    await createMovement({
      part_id: currentPart.value.id,
      movement_type: movementType.value,
      ...movementForm
    })
    ElMessage.success(movementType.value === 'in' ? '入库成功' : '出库成功')
    movementDialogVisible.value = false
    loadParts()
  } catch (e) {
    ElMessage.error('操作失败：' + (e.response?.data?.detail || e.message))
  }
}

const loadMovements = async () => {
  movementsLoading.value = true
  try {
    const params = {
      skip: (movementPage.value - 1) * 50,
      limit: 50,
      keyword: movementFilter.keyword || undefined,
      movement_type: movementFilter.movement_type || undefined,
      start_date: movementFilter.start_date || undefined,
      end_date: movementFilter.end_date || undefined,
      operator: movementFilter.operator || undefined
    }
    const result = await getMovements(params)
    movements.value = result.items || []
    movementTotal.value = result.total || 0
  } catch (e) {
    ElMessage.error('加载出入库记录失败')
  } finally {
    movementsLoading.value = false
  }
}

// 重置出入库筛选
const resetMovementFilter = () => {
  movementFilter.keyword = ''
  movementFilter.movement_type = ''
  movementFilter.start_date = ''
  movementFilter.end_date = ''
  movementFilter.operator = ''
  movementPage.value = 1
  loadMovements()
}

onMounted(loadParts)
</script>

<style scoped>
.card-header { display: flex; justify-content: space-between; align-items: center; }
.header-buttons { display: flex; gap: 8px; }
.stats-row { margin-bottom: 20px; }
.stat-card { text-align: center; }
.pagination-bar { margin-top: 16px; display: flex; justify-content: flex-end; }
.scan-section { margin-bottom: 20px; }
.scan-tip { color: var(--el-text-color-secondary); font-size: 14px; margin-bottom: 16px; }
.scan-list-section { margin-top: 20px; }
.scan-list-section h4 { margin-bottom: 12px; font-weight: 600; }
/* 筛选工具栏样式 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.search-input {
  width: 200px;
}
.type-select {
  width: 120px;
}
.date-picker {
  width: 140px;
}
.operator-input {
  width: 120px;
}
.category-select {
  width: 100px;
}
.toolbar-right {
  display: flex;
  gap: 8px;
}

/* 紧凑头部样式 */
.compact-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 13px;
}
.compact-header strong {
  font-weight: 600;
}
.text-primary {
  color: var(--el-color-primary);
  font-weight: 500;
}
.text-success {
  color: var(--el-color-success);
  font-weight: 600;
}

/* 备件库存清单样式 */
.stock-overview {
  background: var(--el-fill-color-light);
  padding: 16px;
  border-radius: 8px;
}
.stock-overview .overview-item {
  text-align: center;
}
.stock-overview .overview-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 4px;
}
.stock-overview .overview-value {
  font-size: 14px;
  font-weight: 500;
}
.stock-count {
  color: var(--el-color-success);
  font-size: 18px;
  font-weight: 600;
}
.stock-overview .overview-value.price {
  color: var(--el-color-success);
}

.stock-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.stock-list {
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
}

.stock-row {
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.stock-row:last-child {
  border-bottom: none;
}

.stock-row:nth-child(odd) {
  background: var(--el-fill-color-lighter);
}

.row-item {
  display: flex;
  flex-direction: column;
}

.row-label {
  color: var(--el-text-color-secondary);
  font-size: 11px;
  margin-bottom: 2px;
}

.row-value {
  font-size: 13px;
}

.row-value.serial {
  color: var(--el-color-primary);
  font-weight: 500;
}

.row-value.price {
  color: var(--el-color-success);
  font-weight: 500;
}

.row-value.note {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stock-summary {
  margin-top: 12px;
  padding: 10px;
  background: var(--el-fill-color);
  border-radius: 6px;
  text-align: center;
  font-size: 14px;
  color: var(--el-text-color-regular);
}
.stock-summary strong {
  color: var(--el-color-success);
  font-size: 16px;
}
</style>
