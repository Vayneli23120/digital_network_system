<template>
  <div class="maintenance-detail-page">
    <el-page-header @back="goBack" :title="'返回维修列表'">
      <template #content>
        <span class="page-title">{{ maintenance.maint_no || '维修详情' }}</span>
      </template>
    </el-page-header>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：维修信息 -->
      <el-col :span="16">
        <el-card class="maintenance-info-card">
          <template #header>
            <span>维修信息</span>
          </template>

          <el-descriptions :column="2" border v-if="maintenance.id">
            <el-descriptions-item label="维修单号">{{ maintenance.maint_no }}</el-descriptions-item>
            <el-descriptions-item label="设备名称">
              <router-link :to="`/devices/${maintenance.device_id}`">{{ maintenance.device_name }}</router-link>
            </el-descriptions-item>
            <el-descriptions-item label="维修类型">
              <el-tag :type="getMaintTypeType(maintenance.maint_type)">
                {{ getMaintTypeText(maintenance.maint_type) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="维修时间">{{ formatDateTime(maintenance.maint_time || maintenance.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="供应商">{{ maintenance.vendor || '无' }}</el-descriptions-item>
            <el-descriptions-item label="工时">{{ maintenance.labor_hours }} 小时</el-descriptions-item>
          </el-descriptions>

          <el-divider>备件信息</el-divider>

          <!-- 备件列表显示 -->
          <div class="spare-parts-display" v-if="maintenance.spare_parts_list && maintenance.spare_parts_list.length > 0">
            <el-table :data="maintenance.spare_parts_list" border size="small">
              <el-table-column prop="serial_number" label="序列号" width="150">
                <template #default="{ row }">{{ row.serial_number || '-' }}</template>
              </el-table-column>
              <el-table-column prop="part_number" label="型号" width="150" />
              <el-table-column prop="name" label="名称" width="150" />
              <el-table-column prop="quantity" label="数量" width="80" />
              <el-table-column prop="unit_price" label="单价" width="100">
                <template #default="{ row }">¥{{ row.unit_price?.toFixed(2) || '0.00' }}</template>
              </el-table-column>
              <el-table-column prop="total" label="小计" width="100">
                <template #default="{ row }">¥{{ ((row.quantity || 1) * (row.unit_price || 0)).toFixed(2) }}</template>
              </el-table-column>
            </el-table>
            <div class="parts-total">
              备件总成本: <span class="cost">¥{{ (maintenance.parts_cost || 0).toFixed(2) }}</span>
            </div>
          </div>
          <el-empty description="无更换备件" v-else :image-size="60" />

          <el-divider>返回件信息</el-divider>

          <!-- 返回件列表显示 -->
          <div class="return-parts-display" v-if="maintenance.return_parts_list && maintenance.return_parts_list.length > 0">
            <el-table :data="maintenance.return_parts_list" border size="small">
              <el-table-column prop="serial_number" label="序列号" width="150">
                <template #default="{ row }">{{ row.serial_number || '-' }}</template>
              </el-table-column>
              <el-table-column prop="part_number" label="型号" width="150" />
              <el-table-column prop="name" label="名称" width="150" />
              <el-table-column prop="quantity" label="数量" width="80" />
              <el-table-column prop="scrap_in" label="入报废库" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.scrap_in ? 'success' : 'info'" size="small">
                    {{ row.scrap_in ? '已入库' : '不入库' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
            <div class="return-tip">注：无固定资产的返回件可选择不入报废库</div>
          </div>
          <el-empty description="无返回件" v-else :image-size="60" />

          <el-divider>人工信息</el-divider>
          <p class="description">{{ maintenance.description || '无描述' }}</p>
        </el-card>

        <!-- 操作按钮 -->
        <el-card style="margin-top: 20px">
          <el-space>
            <el-button type="primary" @click="openEditDialog">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button type="danger" @click="deleteMaintenanceRecord">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </el-space>
        </el-card>
      </el-col>

      <!-- 右侧：成本统计 -->
      <el-col :span="8">
        <el-card class="cost-card">
          <template #header>
            <span>成本统计</span>
          </template>

          <div class="cost-items">
            <div class="cost-item">
              <span class="cost-label">备件成本</span>
              <span class="cost-value">¥{{ (maintenance.parts_cost || 0).toFixed(2) }}</span>
            </div>
            <div class="cost-item">
              <span class="cost-label">人工成本</span>
              <span class="cost-value">¥{{ (maintenance.labor_cost || 0).toFixed(2) }}</span>
            </div>
            <el-divider />
            <div class="cost-item total">
              <span class="cost-label">总成本</span>
              <span class="cost-value highlight">
                ¥{{ ((maintenance.parts_cost || 0) + (maintenance.labor_cost || 0)).toFixed(2) }}
              </span>
            </div>
          </div>
        </el-card>

        <!-- 设备快速信息 -->
        <el-card class="device-quick-info" style="margin-top: 20px" v-if="device">
          <template #header>
            <span>设备信息</span>
          </template>
          <div class="device-summary">
            <el-avatar :size="60" icon="Switch" />
            <div class="device-info">
              <h4>{{ device.name }}</h4>
              <p>{{ device.ip }}</p>
              <el-tag :type="device.status === 'online' ? 'success' : 'info'" size="small">
                {{ device.status }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 编辑维修对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑维修记录" width="700px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="维修类型" required>
          <el-select v-model="editForm.maint_type">
            <el-option label="预防性维修" value="preventive" />
            <el-option label="修复性维修" value="corrective" />
            <el-option label="升级" value="upgrade" />
            <el-option label="紧急维修" value="emergency" />
          </el-select>
        </el-form-item>

        <!-- 备件选择区域 -->
        <el-divider content-position="left">备件更换</el-divider>
        <el-form-item label="更换备件">
          <div class="spare-parts-section">
            <!-- 扫码添加按钮 -->
            <div class="spare-scan-btn">
              <el-button type="primary" @click="openScanDialog">
                <el-icon><Aim /></el-icon>
                扫码添加备件
              </el-button>
              <div class="spare-scan-tip">点击后用扫码枪扫描条形码建立连接，再扫描备件序列号</div>
            </div>

            <!-- 手动搜索添加备件 -->
            <div class="spare-search">
              <el-select
                v-model="selectedSparePart"
                placeholder="搜索备件型号/名称/序列号"
                filterable
                remote
                :remote-method="searchSpareParts"
                :loading="spareLoading"
                style="width: 300px"
                @change="addSparePartToEditForm"
              >
                <el-option
                  v-for="part in sparePartOptions"
                  :key="part.id"
                  :label="`${part.part_number} - ${part.name} (库存: ${part.quantity_in_stock})`"
                  :value="part.id"
                  :disabled="part.quantity_in_stock <= 0"
                >
                  <div class="spare-option">
                    <span class="spare-number">{{ part.part_number }}</span>
                    <span class="spare-name">{{ part.name }}</span>
                    <span class="spare-stock" :class="{ low: part.quantity_in_stock <= part.min_quantity }">
                      库存: {{ part.quantity_in_stock }}
                    </span>
                  </div>
                </el-option>
              </el-select>
            </div>

            <div class="selected-parts" v-if="editForm.spare_parts.length > 0">
              <el-table :data="editForm.spare_parts" size="small" border>
                <el-table-column prop="serial_number" label="序列号" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" label="型号" width="150" />
                <el-table-column prop="name" label="名称" width="150" />
                <el-table-column prop="quantity" label="数量" width="80">
                  <template #default="{ row }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" @change="updateEditPartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" label="单价" width="80">
                  <template #default="{ row }">¥{{ (row.unit_price || 0).toFixed(2) }}</template>
                </el-table-column>
                <el-table-column label="操作" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeEditSparePart($index)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">
                备件总成本: <span class="total-cost">¥{{ editForm.parts_cost.toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-divider content-position="left">返回件信息</el-divider>
        <el-form-item label="返回件处理">
          <div class="return-parts-section">
            <!-- 手动添加返回件 -->
            <div class="return-add">
              <el-select
                v-model="selectedReturnPart"
                placeholder="从备件库选择（可选）"
                filterable
                remote
                :remote-method="searchReturnParts"
                :loading="spareLoading"
                style="width: 200px"
                clearable
              >
                <el-option
                  v-for="part in sparePartOptions"
                  :key="part.id"
                  :label="`${part.part_number} - ${part.name}`"
                  :value="part.id"
                />
              </el-select>
              <el-input v-model="returnPartSerial" placeholder="序列号" style="width: 120px" />
              <el-input v-model="returnPartNumber" placeholder="型号（手动输入）" style="width: 130px" />
              <el-input v-model="returnPartName" placeholder="名称" style="width: 130px" />
              <el-input-number v-model="returnPartQty" :min="1" style="width: 90px" />
              <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">入报废库</el-checkbox>
              <el-button type="primary" size="small" :disabled="!returnPartNumber && !selectedReturnPart" @click="addReturnPart">添加</el-button>
            </div>

            <div class="return-parts-table" v-if="editForm.return_parts.length > 0">
              <el-table :data="editForm.return_parts" size="small" border>
                <el-table-column prop="serial_number" label="序列号" width="150">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" label="型号" width="150" />
                <el-table-column prop="name" label="名称" width="150" />
                <el-table-column prop="quantity" label="数量" width="80">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" />
                  </template>
                </el-table-column>
                <el-table-column label="入报废库" width="120">
                  <template #default="{ row }">
                    <el-checkbox v-model="row.scrap_in" :disabled="!row.part_id" />
                    <span class="scrap-label" v-if="row.part_id && !row.scrap_in">不入库</span>
                    <span class="scrap-label no-id" v-if="!row.part_id">无备件ID</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="60">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link @click="removeReturnPart($index)">
                      删除
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="return-tip-form">注：需从备件库选择才能入报废库，无固定资产的返回件可不入库</div>
            </div>
            <div class="no-return-tip" v-else>
              <el-tag type="info">暂无返回件，请从上方手动录入换下来的坏件</el-tag>
            </div>
          </div>
        </el-form-item>

        <el-divider />

        <el-form-item label="人工工时 (小时)">
          <el-input-number v-model="editForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item label="人工成本">
          <el-input-number v-model="editForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="editForm.vendor" />
        </el-form-item>
        <el-form-item label="维修描述" required>
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="updateMaintenanceRecord">确定</el-button>
      </template>
    </el-dialog>

    <!-- 扫码添加备件对话框 -->
    <el-dialog v-model="scanDialogVisible" title="扫码添加备件" width="700px">
      <ScanSession
        ref="scanSessionRef"
        default-type="out"
        :auto-start="scanDialogVisible"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Aim, Edit, Delete } from '@element-plus/icons-vue'
import { getMaintenances, updateMaintenance, deleteMaintenance, getDevices, getPartList, createMovement } from '@/api'
import ScanSession from '@/components/ScanSession.vue'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const maintenance = ref({})
const device = ref(null)
const loading = ref(false)
const showEditDialog = ref(false)

// 备件相关
const sparePartOptions = ref([])
const spareLoading = ref(false)
const selectedSparePart = ref(null)

// 扫码对话框
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)
const originalSpareParts = ref([])  // 原始备件列表，用于判断新增

// 返回件录入
const selectedReturnPart = ref(null)
const returnPartNumber = ref('')
const returnPartSerial = ref('')
const returnPartName = ref('')
const returnPartQty = ref(1)
const returnPartScrap = ref(true)

const editForm = ref({
  maint_type: 'corrective',
  spare_parts: [],
  return_parts: [],  // 返回件列表（换下来的坏件）
  parts_cost: 0,
  labor_hours: 0,
  labor_cost: 0,
  vendor: '',
  description: ''
})

const getMaintTypeType = (type) => {
  const types = { preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }
  return types[type] || ''
}

const getMaintTypeText = (type) => {
  const texts = { preventive: '预防性', corrective: '修复性', upgrade: '升级', emergency: '紧急' }
  return texts[type] || type
}

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

// 搜索备件
const searchSpareParts = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    const result = await getPartList({ search: query, limit: 20 })
    sparePartOptions.value = result.items || []
  } catch (e) {
    ElMessage.error('搜索备件失败')
  } finally {
    spareLoading.value = false
  }
}

// 加载初始备件列表
const loadInitialSpareParts = async () => {
  spareLoading.value = true
  try {
    const result = await getPartList({ limit: 50 })
    sparePartOptions.value = result.items || []
  } catch (e) {
    console.error('加载备件失败:', e)
  } finally {
    spareLoading.value = false
  }
}

// 添加备件到编辑表单
const addSparePartToEditForm = () => {
  if (!selectedSparePart.value) return

  const part = sparePartOptions.value.find(p => p.id === selectedSparePart.value)
  if (!part) return

  const existing = editForm.value.spare_parts.find(p => p.part_id === part.id)
  if (existing) {
    existing.quantity += 1
  } else {
    editForm.value.spare_parts.push({
      part_id: part.id,
      part_number: part.part_number,
      name: part.name,
      unit_price: part.unit_price || 0,
      quantity: 1
    })
  }

  updateEditPartsCost()
  selectedSparePart.value = null
}

// 打开扫码对话框
const openScanDialog = () => {
  scanDialogVisible.value = true
}

// 扫码会话完成
const onScanSessionComplete = async (result) => {
  // 将扫描的备件加入编辑表单的更换列表（已在扫码会话中自动出库）
  for (const item of result.items) {
    const existing = editForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      existing.quantity += 1
      ElMessage.info(`${item.name} 数量+1`)
    } else {
      editForm.value.spare_parts.push({
        part_id: item.part_id,
        part_number: item.part_number,
        name: item.name,
        serial_number: item.serial_number,
        unit_price: item.unit_price || 0,
        quantity: 1,
        is_from_scan: true  // 标记为扫码添加，已在扫码会话中出库
      })
      ElMessage.success(`已添加: ${item.name}`)
    }
  }
  updateEditPartsCost()
  scanDialogVisible.value = false
  ElMessage.success(`已添加 ${result.items.length} 个备件到更换列表`)
}

// 移除备件
const removeEditSparePart = (index) => {
  editForm.value.spare_parts.splice(index, 1)
  updateEditPartsCost()
}

// 搜索返回件备件
const searchReturnParts = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    const result = await getPartList({ search: query, limit: 20 })
    sparePartOptions.value = result.items || []
  } catch (e) {
    ElMessage.error('搜索备件失败')
  } finally {
    spareLoading.value = false
  }
}

// 手动添加返回件
const addReturnPart = () => {
  if (!returnPartNumber.value && !selectedReturnPart.value) {
    ElMessage.warning('请输入返回件型号或从备件库选择')
    return
  }

  let partNumber = returnPartNumber.value
  let partName = returnPartName.value
  let partId = null

  if (selectedReturnPart.value) {
    const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
    if (part) {
      partId = part.id
      partNumber = part.part_number
      partName = part.name
    }
  }

  editForm.value.return_parts.push({
    part_id: partId,
    part_number: partNumber,
    name: partName || partNumber,
    serial_number: returnPartSerial.value,
    quantity: returnPartQty.value,
    scrap_in: selectedReturnPart.value ? returnPartScrap.value : false
  })

  selectedReturnPart.value = null
  returnPartSerial.value = ''
  returnPartNumber.value = ''
  returnPartName.value = ''
  returnPartQty.value = 1
  returnPartScrap.value = true
}

// 移除返回件
const removeReturnPart = (index) => {
  editForm.value.return_parts.splice(index, 1)
}

// 更新备件成本
const updateEditPartsCost = () => {
  editForm.value.parts_cost = editForm.value.spare_parts.reduce(
    (sum, p) => sum + p.quantity * p.unit_price, 0
  )
}

const loadMaintenance = async () => {
  loading.value = true
  try {
    const maintId = route.params.id
    const data = await getMaintenances()
    const found = (data.items || []).find(m => m.id === parseInt(maintId))
    if (found) {
      maintenance.value = found

      // 解析 parts_replaced 字段获取备件列表
      if (found.parts_replaced) {
        try {
          // 尝试JSON解析（新格式）
          const parsed = JSON.parse(found.parts_replaced)
          if (Array.isArray(parsed)) {
            // 分离备件和返回件
            maintenance.value.spare_parts_list = parsed.filter(p => !p.is_return).map(p => ({
              part_number: p.part_number || '',
              name: p.name || p.part_number || '',
              serial_number: p.serial_number || '',
              quantity: p.quantity || 1,
              unit_price: p.unit_price || 0
            }))
            maintenance.value.return_parts_list = parsed.filter(p => p.is_return).map(p => ({
              part_number: p.part_number || '',
              name: p.name || p.part_number || '',
              serial_number: p.serial_number || '',
              quantity: p.quantity || 1,
              scrap_in: p.scrap_in || false
            }))
            // 如果没有分离标记，尝试使用旧的 scrap_in 字段作为返回件
            if (maintenance.value.return_parts_list.length === 0 && parsed.some(p => p.scrap_in !== undefined)) {
              maintenance.value.return_parts_list = parsed.map(p => ({
                part_number: p.part_number || '',
                name: p.name || p.part_number || '',
                quantity: p.quantity || 1,
                scrap_in: p.scrap_in || false
              }))
            }
          } else {
            maintenance.value.spare_parts_list = []
            maintenance.value.return_parts_list = []
          }
        } catch (e) {
          // 兼容旧格式：解析 "型号(数量), 型号(数量)" 格式
          const partsList = found.parts_replaced.split(',').map(p => {
            const match = p.trim().match(/(.+)\((\d+)\)/)
            if (match) {
              return {
                part_number: match[1],
                name: match[1],
                quantity: parseInt(match[2]),
                unit_price: 0,
                scrap_in: false
              }
            }
            return { part_number: p.trim(), name: p.trim(), quantity: 1, unit_price: 0, scrap_in: false }
          })
          maintenance.value.spare_parts_list = partsList
          maintenance.value.return_parts_list = partsList.map(p => ({ ...p, unit_price: undefined }))
        }
      } else {
        maintenance.value.spare_parts_list = []
        maintenance.value.return_parts_list = []
      }

      // 加载设备信息
      if (found.device_id) {
        const devices = await getDevices()
        device.value = (devices.items || []).find(d => d.id === found.device_id)
      }
    }
  } catch (error) {
    ElMessage.error('加载维修详情失败')
  } finally {
    loading.value = false
  }
}

const openEditDialog = async () => {
  await loadInitialSpareParts()
  // 保存原始备件列表，用于后续判断新增的备件
  originalSpareParts.value = (maintenance.value.spare_parts_list || []).map(p => p.serial_number || p.part_id)
  editForm.value = {
    maint_type: maintenance.value.maint_type,
    spare_parts: maintenance.value.spare_parts_list || [],
    return_parts: maintenance.value.return_parts_list || [],
    parts_cost: maintenance.value.parts_cost || 0,
    labor_hours: maintenance.value.labor_hours || 0,
    labor_cost: maintenance.value.labor_cost || 0,
    vendor: maintenance.value.vendor || '',
    description: maintenance.value.description
  }
  showEditDialog.value = true
}

const goBack = () => {
  router.push('/maintenance')
}

const updateMaintenanceRecord = async () => {
  if (!editForm.value.description) {
    ElMessage.warning('请填写维修描述')
    return
  }

  try {
    // 合并备件和返回件数据，标记返回件
    const combinedParts = [
      ...editForm.value.spare_parts.map(p => ({ ...p, is_return: false })),
      ...editForm.value.return_parts.map(p => ({ ...p, is_return: true }))
    ]

    await updateMaintenance(maintenance.value.id, {
      ...editForm.value,
      parts_replaced: JSON.stringify(combinedParts)
    })

    // 处理备件出库 - 仅在通过手动搜索添加（非扫码）时需要
    // 扫码添加的备件已在 ScanSession 完成时自动出库
    // 此处不再重复出库

    // 处理返回件入报废库
    for (const part of editForm.value.return_parts) {
      if (part.scrap_in && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'scrap_in',
          quantity: part.quantity,
          serial_number: part.serial_number,
          reason: `维修返回件入库 - 报废`,
          operator: 'Web',
          reference: maintenance.value.maint_no
        })
      }
    }

    ElMessage.success('维修记录更新成功')
    showEditDialog.value = false
    loadMaintenance()
  } catch (error) {
    ElMessage.error('更新维修记录失败: ' + (error.response?.data?.detail || error.message))
  }
}

const deleteMaintenanceRecord = async () => {
  try {
    await ElMessageBox.confirm('确定要删除此维修记录吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await deleteMaintenance(maintenance.value.id)
    ElMessage.success('维修记录删除成功')
    router.push('/maintenance')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除维修记录失败')
    }
  }
}

onMounted(() => {
  loadMaintenance()
})
</script>

<style scoped>
.maintenance-detail-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  font-size: 18px;
  font-weight: bold;
}

.maintenance-info-card {
  min-height: 400px;
}

.description {
  line-height: 1.8;
  color: #606266;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.cost {
  color: #f56c6c;
  font-weight: bold;
}

.cost-card {
  min-height: 200px;
}

.cost-items {
  padding: 10px 0;
}

.cost-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}

.cost-label {
  font-size: 14px;
  color: #909399;
}

.cost-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.cost-value.highlight {
  color: #f56c6c;
  font-size: 20px;
}

.total {
  border-top: 2px solid #eee;
  padding-top: 15px;
}

.device-summary {
  display: flex;
  align-items: center;
  gap: 15px;
}

.device-info h4 {
  margin: 0 0 5px 0;
  font-size: 16px;
}

.device-info p {
  margin: 0 0 5px 0;
  color: #909399;
  font-size: 14px;
}

/* 备件显示样式 */
.spare-parts-display {
  margin-bottom: 20px;
}

.parts-total {
  margin-top: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  text-align: right;
}

/* 备件选择区域 */
.spare-parts-section {
  width: 100%;
}

.spare-scan-btn {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.spare-scan-tip {
  font-size: 12px;
  color: var(--el-color-primary);
  padding: 4px 8px;
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
}

.spare-search {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.selected-parts {
  margin-top: 12px;
}

.parts-summary {
  margin-top: 10px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
  text-align: right;
}

.total-cost {
  font-weight: 600;
  color: #409EFF;
  font-size: 16px;
}

/* 备件下拉选项样式 */
.spare-option {
  display: flex;
  align-items: center;
  gap: 12px;
}

.spare-number {
  font-weight: 500;
  color: #409EFF;
}

.spare-name {
  color: #606266;
}

.spare-stock {
  font-size: 12px;
  color: #909399;
}

.spare-stock.low {
  color: #F56C6C;
  font-weight: 500;
}

/* 返回件显示样式 */
.return-parts-display {
  margin-bottom: 20px;
}

.return-tip {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fdf6ec;
  border-radius: 4px;
  color: #909399;
  font-size: 12px;
}

/* 返回件编辑区域 */
.return-parts-section {
  width: 100%;
}

.return-add {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.return-parts-table {
  margin-top: 8px;
}

.scrap-label {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}

.scrap-label.no-id {
  color: #E6A23C;
}

.return-tip-form {
  margin-top: 10px;
  padding: 8px 12px;
  background: #fdf6ec;
  border-radius: 4px;
  color: #909399;
  font-size: 12px;
}

.no-return-tip {
  margin-top: 8px;
}
</style>