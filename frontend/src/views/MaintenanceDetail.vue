<template>
  <div class="maintenance-detail-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ maintenance.maint_no || t('maintDetailTitle') }}</h1>
        <el-tag :type="getStatusTagClass(statusInfo.status)" size="default" class="status-tag">
          {{ statusInfo.status_label }}
        </el-tag>
        <el-tag :type="getPriorityTagClass(statusInfo.priority)" size="small" class="priority-tag">
          {{ statusInfo.priority }}
        </el-tag>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn secondary" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          {{ t('actionBack') }}
        </button>
        <button class="nav-action-btn" v-if="statusInfo.status !== 'completed' && statusInfo.status !== 'cancelled'" @click="openEditDialog">
          <el-icon><Edit /></el-icon>
          {{ t('actionEdit') }}
        </button>
      </div>
    </section>

    <!-- V2 左右布局 -->
    <div class="maint-header">
      <!-- 左侧：维修信息卡片 -->
      <div class="maint-info-card">
        <!-- 任务头部信息区 -->
        <div class="task-header-section">
          <div class="task-title-row">
            <span class="maint-title">{{ maintenance.maint_no || t('maintDetailTitle') }}</span>
            <el-tag :type="getStatusTagClass(statusInfo.status)" size="default" class="status-tag">
              {{ statusInfo.status_label }}
            </el-tag>
            <el-tag :type="getPriorityTagClass(statusInfo.priority)" size="small" class="priority-tag">
              {{ statusInfo.priority }}
            </el-tag>
          </div>
          <div class="task-meta-row">
            <div class="meta-item">
              <el-icon><Clock /></el-icon>
              <span>{{ formatDateTime(maintenance.created_at) }}</span>
            </div>
            <div class="meta-item owner">
              <el-icon><User /></el-icon>
              <span>{{ statusInfo.current_owner || t('maintOwnerUnassigned') }}</span>
            </div>
            <div class="meta-item sla" :class="{ overdue: statusInfo.sla_remaining === t('maintSlaOverdue') }">
              <el-icon><Timer /></el-icon>
              <span>{{ statusInfo.sla_remaining || t('maintSlaNotSet') }}</span>
            </div>
          </div>
          <div class="task-device-row">
            <span>{{ t('maintDetailDeviceName') }}: <router-link :to="`/devices/${maintenance.device_id}`" class="cell-link">{{ maintenance.device_name }}</router-link></span>
            <span>{{ t('maintType') }}: <span class="cell-tag" :class="getMaintTypeTagClass(maintenance.maint_type)">{{ getMaintTypeText(maintenance.maint_type) }}</span></span>
          </div>
        </div>

        <!-- Workflow 步骤流程（4步：创建→维修→验证→完成） -->
        <div class="workflow-steps-enhanced">
          <div class="workflow-step-item" :class="getStepClass(1)">
            <div class="step-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="step-info">
              <span class="step-label">{{ t('workflowStepCreate') }}</span>
              <span class="step-time" v-if="maintenance.created_at">{{ formatDateTime(maintenance.created_at) }}</span>
            </div>
            <div class="step-dot" :class="getStepClass(1)">{{ workflowStep >= 1 ? '✓' : '1' }}</div>
          </div>
          <div class="step-connector" :class="{ completed: workflowStep >= 2 }"></div>
          <div class="workflow-step-item" :class="getStepClass(2)">
            <div class="step-icon">
              <el-icon><Setting /></el-icon>
            </div>
            <div class="step-info">
              <span class="step-label">{{ t('workflowStepRepair') }}</span>
              <span class="step-time" v-if="statusInfo.repairing_at">{{ formatDateTime(statusInfo.repairing_at) }}</span>
            </div>
            <div class="step-dot" :class="getStepClass(2)">{{ workflowStep >= 2 ? '✓' : '2' }}</div>
          </div>
          <div class="step-connector" :class="{ completed: workflowStep >= 3 }"></div>
          <div class="workflow-step-item" :class="getStepClass(3)">
            <div class="step-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="step-info">
              <span class="step-label">{{ t('workflowStepVerify') }}</span>
              <span class="step-time" v-if="statusInfo.verifying_at">{{ formatDateTime(statusInfo.verifying_at) }}</span>
            </div>
            <div class="step-dot" :class="getStepClass(3)">{{ workflowStep >= 3 ? '✓' : '3' }}</div>
          </div>
          <div class="step-connector" :class="{ completed: workflowStep >= 4 }"></div>
          <div class="workflow-step-item" :class="getStepClass(4)">
            <div class="step-icon">
              <el-icon><SuccessFilled /></el-icon>
            </div>
            <div class="step-info">
              <span class="step-label">{{ t('workflowStepComplete') }}</span>
              <span class="step-time" v-if="statusInfo.completed_at">{{ formatDateTime(statusInfo.completed_at) }}</span>
            </div>
            <div class="step-dot" :class="getStepClass(4)">{{ workflowStep >= 4 ? '✓' : '4' }}</div>
          </div>
        </div>

        <!-- 进度条显示 -->
        <div class="progress-bar-section">
          <el-progress
            :percentage="statusInfo.progress_percent"
            :status="statusInfo.status === 'cancelled' ? 'exception' : (statusInfo.status === 'completed' ? 'success' : '')"
            :stroke-width="8"
          />
          <span class="progress-label">{{ t('maintProgress') }}: {{ statusInfo.progress_percent }}%</span>
        </div>

        <!-- 详情网格 -->
        <div class="detail-grid">
          <div class="detail-item">
            <span class="detail-item-label">{{ t('maintDetailVendor') }}</span>
            <span class="detail-item-value">{{ maintenance.vendor || t('maintDetailVendorNone') }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-item-label">{{ t('maintDetailHours') }}</span>
            <span class="detail-item-value">{{ maintenance.labor_hours }} {{ t('maintDetailHoursUnit') }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-item-label">{{ t('maintDetailPartsCost') }}</span>
            <span class="detail-item-value" style="color: var(--accent-warning)">{{ formatCurrency(maintenance.parts_cost) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-item-label">{{ t('maintDetailLaborCost') }}</span>
            <span class="detail-item-value">{{ formatCurrency(maintenance.labor_cost) }}</span>
          </div>
        </div>

        <!-- Tabs: 备件列表和返回件列表 -->
        <div class="tabs-wrapper" style="margin-top: 16px">
          <div class="tabs-header">
            <span class="tab-item" :class="{ active: activeTab === 'spare' }" @click="activeTab = 'spare'">{{ t('maintDetailSpareInfo') }}</span>
            <span class="tab-item" :class="{ active: activeTab === 'return' }" @click="activeTab = 'return'">{{ t('maintDetailReturnInfo') }}</span>
            <span class="tab-item" :class="{ active: activeTab === 'desc' }" @click="activeTab = 'desc'">{{ t('maintDetailLaborInfo') }}</span>
          </div>
          <div class="tabs-content">
            <!-- 备件列表 -->
            <div v-show="activeTab === 'spare'">
              <div class="spare-parts-display" v-if="maintenance.spare_parts_list && maintenance.spare_parts_list.length > 0">
                <el-table :data="maintenance.spare_parts_list" border size="small">
                  <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                    <template #default="{ row }">
                      <span class="cell-primary">{{ row.serial_number || '-' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="part_number" :label="t('maintColModel')" width="120" />
                  <el-table-column prop="name" :label="t('maintColName')" width="150" />
                  <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60" />
                  <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="80">
                    <template #default="{ row }">
                      <span class="cell-success">{{ formatCurrency(row.unit_price) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column :label="t('maintColSubtotal')" width="80">
                    <template #default="{ row }">
                      <span class="cell-success">{{ formatCurrency((row.quantity || 1) * (row.unit_price || 0)) }}</span>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="parts-total">
                  {{ t('maintSpareTotalCost') }}: <span class="cost">{{ formatCurrency(maintenance.parts_cost) }}</span>
                </div>
              </div>
              <div class="empty-state" v-else>
                <span class="empty-icon">📦</span>
                <span class="empty-text">{{ t('maintDetailNoSpare') }}</span>
              </div>
            </div>

            <!-- 返回件列表 -->
            <div v-show="activeTab === 'return'">
              <div class="return-parts-display" v-if="maintenance.return_parts_list && maintenance.return_parts_list.length > 0">
                <el-table :data="maintenance.return_parts_list" border size="small">
                  <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                    <template #default="{ row }">
                      <span class="cell-primary">{{ row.serial_number || '-' }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="part_number" :label="t('maintColModel')" width="120" />
                  <el-table-column prop="name" :label="t('maintColName')" width="150" />
                  <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60" />
                  <el-table-column :label="t('maintDetailReturnScrapIn')" width="80">
                    <template #default="{ row }">
                      <span class="cell-tag" :class="row.scrap_in ? 'success' : 'info'">
                        {{ row.scrap_in ? t('maintDetailReturnScrapped') : t('maintDetailReturnNoScrap') }}
                      </span>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="return-tip">{{ t('maintDetailReturnTip') }}</div>
              </div>
              <div class="empty-state" v-else>
                <span class="empty-icon">🔄</span>
                <span class="empty-text">{{ t('maintDetailNoReturn') }}</span>
              </div>
            </div>

            <!-- 维修描述 -->
            <div v-show="activeTab === 'desc'">
              <p class="description">{{ maintenance.description || t('maintDetailNoDesc') }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：操作卡片 -->
      <div class="maint-actions-card">
        <!-- 工作日志输入区（ServiceNow Notes风格） -->
        <div class="work-notes-card" v-if="statusInfo.status !== 'completed' && statusInfo.status !== 'cancelled'">
          <div class="actions-card-header">
            <el-icon><Edit /></el-icon>
            {{ t('maintWorkNotes') }}
          </div>
          <el-input
            v-model="newNote"
            type="textarea"
            :rows="3"
            :placeholder="t('maintNotePlaceholder')"
            class="note-input"
          />
          <el-button type="primary" size="default" class="note-submit-btn" @click="addWorkNote" :loading="addingNote">
            <el-icon><Plus /></el-icon>
            {{ t('maintAddNote') }}
          </el-button>
        </div>

        <!-- 流程操作区（DNAC风格：单一主按钮 + 更多操作dropdown） -->
        <div class="action-control-card" v-if="statusInfo.status !== 'completed' && statusInfo.status !== 'cancelled'">
          <!-- 主操作按钮（根据状态动态变化） -->
          <div class="primary-action-area">
            <el-button
              type="primary"
              class="primary-action-btn"
              @click="handlePrimaryAction"
            >
              <el-icon><component :is="primaryActionIcon" /></el-icon>
              {{ primaryActionText }}
            </el-button>
          </div>

          <!-- 更多操作 dropdown -->
          <div class="more-actions-area">
            <el-dropdown trigger="click" placement="bottom-end">
              <el-button type="default" class="more-actions-btn">
                <el-icon><MoreFilled /></el-icon>
                {{ t('moreActions') }}
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="openEditDialog">
                    <el-icon><Edit /></el-icon>{{ t('actionEdit') }}
                  </el-dropdown-item>
                  <el-dropdown-item divided @click="openEditDialog">
                    <el-icon><Box /></el-icon>{{ t('maintAddSpare') }}
                  </el-dropdown-item>
                  <el-dropdown-item @click="openEditDialog">
                    <el-icon><RefreshRight /></el-icon>{{ t('maintAddReturn') }}
                  </el-dropdown-item>
                  <el-dropdown-item @click="focusNoteInput">
                    <el-icon><EditPen /></el-icon>{{ t('maintAddNote') }}
                  </el-dropdown-item>
                  <el-dropdown-item divided class="dropdown-danger" @click="handleCancel">
                    <el-icon><CircleClose /></el-icon>{{ t('maintTransitionToCancelled') }}
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- 已完成/已取消状态显示 -->
        <div class="status-complete-card" v-if="statusInfo.status === 'completed' || statusInfo.status === 'cancelled'">
          <el-button type="default" class="view-details-btn" @click="openEditDialog">
            <el-icon><View /></el-icon>
            {{ t('actionViewDetails') }}
          </el-button>
        </div>

        <!-- 分配负责人（维修中或验证中状态时如果还没有负责人） -->
        <div class="assign-card" v-if="!statusInfo.current_owner && statusInfo.status !== 'completed' && statusInfo.status !== 'cancelled'">
          <div class="actions-card-header">
            <el-icon><User /></el-icon>
            {{ t('maintAssignBtn') }}
          </div>
          <el-select
            v-model="assignForm.owner"
            :placeholder="t('maintOwnerPlaceholder')"
            filterable
            clearable
            style="margin-top: 12px"
          >
            <template #prefix><el-icon><User /></el-icon></template>
            <el-option v-for="user in users" :key="user.id" :label="user.full_name || user.username" :value="user.username" />
          </el-select>
          <el-button type="primary" size="default" style="width: 100%; margin-top: 8px" @click="handleAssign">
            {{ t('maintAssignBtn') }}
          </el-button>
        </div>

        <!-- 事件时间线（DNAC Timeline风格） -->
        <div class="timeline-section" v-if="events.length > 0">
          <div class="section-header">
            <el-icon><Clock /></el-icon>
            {{ t('maintTimeline') }}
            <el-tag v-if="maintenance.has_fault_work_notes" type="info" size="small" class="fault-notes-tag">
              {{ t('maintIncludesFaultNotes') }}
            </el-tag>
          </div>
          <div class="timeline-container">
            <div
              v-for="(event, index) in events"
              :key="index"
              class="timeline-item"
              :class="{ 'from-fault': event.source === 'fault' }"
            >
              <!-- Timeline dot -->
              <div class="timeline-dot" :class="event.event_type">
                <el-icon :size="10">
                  <component :is="getEventIcon(event.event_type)" />
                </el-icon>
              </div>
              <!-- Event content -->
              <div class="timeline-content">
                <div class="timeline-header">
                  <span class="timeline-title">{{ event.notes || getEventLabel(event.event_type) }}</span>
                  <span class="timeline-time">{{ event.event_time ? formatDateTime(event.event_time) : '' }}</span>
                </div>
                <div class="timeline-meta" v-if="event.operator">
                  <el-icon :size="12"><User /></el-icon>
                  <span class="timeline-operator">{{ event.operator }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 成本统计数据卡片化 -->
        <div class="cost-stats-card">
          <div class="actions-card-header">
            <el-icon><Coin /></el-icon>
            {{ t('maintDetailCostStats') }}
          </div>
          <div class="cost-stats-grid">
            <div class="cost-stat-item">
              <div class="cost-stat-label">{{ t('maintDetailPartsCost') }}</div>
              <div class="cost-stat-value">{{ formatCurrency(maintenance.parts_cost) }}</div>
            </div>
            <div class="cost-stat-item">
              <div class="cost-stat-label">{{ t('maintDetailLaborCost') }}</div>
              <div class="cost-stat-value">{{ formatCurrency(maintenance.labor_cost) }}</div>
            </div>
            <div class="cost-stat-item total">
              <div class="cost-stat-label">{{ t('maintDetailTotalCost') }}</div>
              <div class="cost-stat-value">{{ formatCurrency((maintenance.parts_cost || 0) + (maintenance.labor_cost || 0)) }}</div>
            </div>
          </div>
        </div>

        <!-- 设备信息区增强 -->
        <div class="device-info-card" v-if="device">
          <div class="actions-card-header">
            <el-icon><Monitor /></el-icon>
            {{ t('maintDetailDeviceInfo') }}
          </div>
          <div class="device-header">
            <el-avatar :size="48" class="device-avatar">
              <el-icon><Switch /></el-icon>
            </el-avatar>
            <div class="device-meta">
              <h4 class="device-name">{{ device.name }}</h4>
              <span class="device-ip">{{ device.ip }}</span>
              <el-tag :type="device.status === 'online' ? 'success' : 'info'" size="small">
                {{ device.status }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑维修对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('maintDetailEdit')" width="720px" append-to-body draggable align-center class="edit-maint-dialog">
      <div class="edit-dialog-content">
        <!-- 基础信息 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Setting /></el-icon>
            {{ t('maintBasicInfo') }}
          </div>
          <el-form :model="editForm" label-width="70px">
            <el-form-item :label="t('maintType')" required>
              <el-select v-model="editForm.maint_type" style="width: 200px">
                <el-option :label="t('maintTypePreventiveFull')" value="preventive" />
                <el-option :label="t('maintTypeCorrectiveFull')" value="corrective" />
                <el-option :label="t('maintTypeUpgradeFull')" value="upgrade" />
                <el-option :label="t('maintTypeEmergencyFull')" value="emergency" />
              </el-select>
            </el-form-item>
          </el-form>
        </div>

        <!-- 备件更换 Section -->
        <div class="form-section">
          <div class="form-section-title">
            <el-icon><Box /></el-icon>
            {{ t('maintSparePartsSection') }}
          </div>
          <el-form :model="editForm" label-width="70px">
            <el-form-item :label="t('maintSparePartsLabel')">
              <div class="spare-parts-section">
                <!-- 扫码功能条 -->
                <div class="scan-action-bar">
                  <el-button type="default" class="scan-btn" @click="openScanDialog">
                    <el-icon><Aim /></el-icon>
                    {{ t('maintScanAddSpare') }}
                  </el-button>
                  <div class="scan-tip-badge">
                    <el-icon><InfoFilled /></el-icon>
                    {{ t('maintScanTip') }}
                  </div>
                </div>

            <!-- 手动搜索添加备件 -->
            <div class="spare-search">
              <el-select
                v-model="selectedSparePart"
                :placeholder="t('maintDetailSpareSearchPlaceholder')"
                filterable
                remote
                :remote-method="searchSpareParts"
                :loading="spareLoading"
                style="width: 200px"
                @change="addSparePartToEditForm"
              >
                <el-option
                  v-for="part in sparePartOptions"
                  :key="part.id"
                  :label="part.is_serial_match ? `${part.serial_number} - ${part.name}` : `${part.part_number} - ${part.name} (${t('maintSpareStock')}: ${part.quantity_in_stock})`"
                  :value="part.id"
                  :disabled="!part.is_serial_match && part.quantity_in_stock <= 0"
                >
                  <div class="spare-option">
                    <span class="spare-number">{{ part.part_number }}</span>
                    <span class="spare-name">{{ part.name }}</span>
                    <span v-if="part.is_serial_match" class="spare-sn">
                      {{ t('maintDetailSpareSerial') }}: {{ part.serial_number }}
                    </span>
                    <span v-else class="spare-stock" :class="{ low: part.quantity_in_stock <= part.min_quantity }">
                      {{ t('maintSpareStock') }}: {{ part.quantity_in_stock }}
                    </span>
                  </div>
                </el-option>
              </el-select>
            </div>

            <div class="selected-parts" v-if="editForm.spare_parts.length > 0">
              <el-table :data="editForm.spare_parts" size="small" border>
                <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" :label="t('maintColModel')" width="100" />
                <el-table-column prop="name" :label="t('maintColName')" min-width="100" />
                <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60">
                  <template #default="{ row }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" @change="updateEditPartsCost" />
                  </template>
                </el-table-column>
                <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="70">
                  <template #default="{ row }">{{ formatCurrency(row.unit_price) }}</template>
                </el-table-column>
                <el-table-column :label="t('colOperation')" width="40">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link class="delete-btn-icon" @click="removeEditSparePart($index)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="parts-summary">
                {{ t('maintSpareTotalCost') }}: <span class="total-cost">{{ formatCurrency(editForm.parts_cost) }}</span>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- 返回件 Section -->
    <div class="form-section">
      <div class="form-section-title">
        <el-icon><RefreshRight /></el-icon>
        {{ t('maintReturnPartsSection') }}
      </div>
      <el-form :model="editForm" label-width="70px">
        <el-form-item :label="t('maintReturnPartsLabel')">
          <div class="return-parts-section">
            <!-- 扫码功能条 -->
            <div class="scan-action-bar return">
              <el-button type="default" class="scan-btn" @click="openReturnScanDialog">
                <el-icon><Aim /></el-icon>
                {{ t('maintDetailScanAddReturn') }}
              </el-button>
              <div class="scan-tip-badge">
                <el-icon><InfoFilled /></el-icon>
                {{ t('maintDetailReturnScanTip') }}
              </div>
            </div>

            <!-- 手动输入查询 -->
            <div class="return-manual-query" style="margin-top: 8px">
              <el-input
                v-model="returnScanInput"
                :placeholder="t('maintDetailReturnManualPlaceholder')"
                style="width: 150px"
                @keyup.enter="scanReturnPart"
                clearable
              >
                <template #prefix><el-icon><Aim /></el-icon></template>
              </el-input>
              <el-button type="default" size="small" @click="scanReturnPart" :loading="returnScanLoading">
                {{ t('spareQuery') }}
              </el-button>
            </div>

            <!-- 扫码识别结果（如果找到历史记录） -->
            <div class="return-found-info" v-if="returnFoundInfo">
              <el-card size="small" shadow="never">
                <div class="found-header">
                  <el-tag type="success" size="small">{{ t('maintReturnFoundTag') }}</el-tag>
                  <span>{{ returnFoundInfo.serial_number }}</span>
                </div>
                <el-descriptions :column="3" size="small" border>
                  <el-descriptions-item :label="t('maintColModel')">{{ returnFoundInfo.part_number }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintColName')">{{ returnFoundInfo.name }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintColUnitPrice')">{{ formatCurrency(returnFoundInfo.unit_price) }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintReturnInStockAt')">{{ returnFoundInfo.in_stock_at ? formatDateTime(returnFoundInfo.in_stock_at) : '-' }}</el-descriptions-item>
                  <el-descriptions-item :label="t('maintReturnOutAt')">{{ returnFoundInfo.out_at ? formatDateTime(returnFoundInfo.out_at) : '-' }}</el-descriptions-item>
                  <el-descriptions-item :label="t('statusOnline')">
                    <span class="cell-tag" :class="returnFoundInfo.status === 'out' ? 'warning' : 'success'">
                      {{ returnFoundInfo.status === 'out' ? t('maintReturnStatusOut') : t('statusInStock') }}
                    </span>
                  </el-descriptions-item>
                </el-descriptions>
                <div class="found-actions">
                  <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 90px" />
                  <el-checkbox v-model="returnPartScrap">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                  <el-button type="primary" size="small" @click="addFoundReturnPart">{{ t('maintReturnAddToList') }}</el-button>
                  <el-button size="small" @click="clearReturnFound">{{ t('actionReset') }}</el-button>
                </div>
              </el-card>
            </div>

            <!-- 手动添加返回件（未识别时） -->
            <div class="return-manual-area" v-if="!returnFoundInfo">
              <div class="return-manual-row">
                <el-select
                  v-model="selectedReturnPart"
                  :placeholder="t('maintReturnSelectFromSpare')"
                  filterable
                  remote
                  :remote-method="searchReturnParts"
                  :loading="spareLoading"
                  style="width: 140px"
                  clearable
                  @change="onReturnPartSelect"
                >
                  <el-option
                    v-for="part in sparePartOptions"
                    :key="part.id"
                    :label="`${part.part_number} - ${part.name}`"
                    :value="part.id"
                  />
                </el-select>
                <el-input v-model="returnPartSerial" :placeholder="t('maintReturnSerialPlaceholder')" style="width: 100px" />
                <el-input v-model="returnPartNumber" :placeholder="t('maintReturnModelManual')" style="width: 100px" />
                <el-input v-model="returnPartName" :placeholder="t('maintReturnNameDefault')" style="width: 100px" />
              </div>
              <div class="return-manual-row">
                <el-input-number v-model="returnPartQty" :min="1" size="small" style="width: 70px" />
                <el-checkbox v-model="returnPartScrap" :disabled="!selectedReturnPart">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                <el-button type="primary" size="small" :disabled="!returnPartSerial" @click="addReturnPart">{{ t('actionAdd') }}</el-button>
              </div>
            </div>

            <div class="return-parts-table" v-if="editForm.return_parts.length > 0">
              <el-table :data="editForm.return_parts" size="small" border>
                <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                  <template #default="{ row }">{{ row.serial_number || '-' }}</template>
                </el-table-column>
                <el-table-column prop="part_number" :label="t('maintColModel')" width="100" />
                <el-table-column prop="name" :label="t('maintColName')" min-width="100" />
                <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60">
                  <template #default="{ row, $index }">
                    <el-input-number v-model="row.quantity" :min="1" size="small" />
                  </template>
                </el-table-column>
                <el-table-column :label="t('maintReturnScrapLabel')" width="90">
                  <template #default="{ row }">
                    <el-checkbox v-model="row.scrap_in" :disabled="!row.part_id" />
                  </template>
                </el-table-column>
                <el-table-column :label="t('colOperation')" width="40">
                  <template #default="{ row, $index }">
                    <el-button type="danger" size="small" link class="delete-btn-icon" @click="removeReturnPart($index)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div class="return-tip-form">{{ t('maintDetailReturnTipForm') }}</div>
            </div>
            <div class="no-return-tip" v-else>
              <el-tag type="info">{{ t('maintReturnNoPartsTip') }}</el-tag>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- 验证信息 Section (半自动状态机) -->
    <div class="form-section" v-if="statusInfo.status !== 'completed' && statusInfo.status !== 'cancelled'">
      <div class="form-section-title verification">
        <el-icon><CircleCheck /></el-icon>
        {{ t('maintVerificationSection') }}
        <el-tag v-if="editForm.verification_result === 'passed'" type="success" size="small" class="section-badge">{{ t('maintVerificationPassed') }}</el-tag>
        <el-tag v-if="editForm.verification_result === 'failed'" type="danger" size="small" class="section-badge">{{ t('maintVerificationFailed') }}</el-tag>
      </div>
      <el-form :model="editForm" label-width="70px">
        <el-form-item :label="t('maintVerificationResult')">
          <el-select v-model="editForm.verification_result" style="width: 150px" clearable @change="handleVerificationResultChange">
            <el-option :label="t('maintVerificationPassed')" value="passed" />
            <el-option :label="t('maintVerificationFailed')" value="failed" />
            <el-option :label="t('maintVerificationPartial')" value="partial" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('maintVerificationNotes')">
          <el-input v-model="editForm.verification_notes" type="textarea" :rows="2" :placeholder="t('maintVerificationNotesPlaceholder')" />
        </el-form-item>
      </el-form>
    </div>

    <!-- 成本与描述 Section -->
    <div class="form-section">
      <div class="form-section-title">
        <el-icon><Document /></el-icon>
        {{ t('maintCostDescSection') }}
      </div>
      <el-form :model="editForm" label-width="70px">
        <el-form-item :label="t('maintLaborHours')">
          <el-input-number v-model="editForm.labor_hours" :min="0" :precision="1" />
        </el-form-item>
        <el-form-item :label="t('maintLaborCost')">
          <el-input-number v-model="editForm.labor_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item :label="t('maintVendor')">
          <el-input v-model="editForm.vendor" />
        </el-form-item>
        <el-form-item :label="t('maintDesc')" required>
          <el-input v-model="editForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
    </div>
  </div>
  <template #footer>
    <el-button @click="showEditDialog = false">{{ t('actionCancel') }}</el-button>
    <el-button type="primary" @click="updateMaintenanceRecord">{{ t('maintConfirm') }}</el-button>
  </template>
</el-dialog>

    <!-- 扫码添加备件对话框 -->
    <el-dialog v-model="scanDialogVisible" :title="t('maintScanSpareDialog')" width="900px">
      <ScanSession
        ref="scanSessionRef"
        default-type="out"
        :device-id="maintenance?.device_id"
        :auto-start="scanDialogVisible"
        :reference="maintenance?.maint_no"
        @complete="onScanSessionComplete"
        @cancel="scanDialogVisible = false"
      />
    </el-dialog>

    <!-- 状态变更建议对话框 -->
    <el-dialog v-model="showSuggestDialog" :title="t('maintSuggestStatusTitle')" width="400px" class="suggest-dialog">
      <div class="suggest-content">
        <div class="suggest-icon">
          <el-icon :size="48" :color="getStatusTagClass(suggestInfo.suggested_status) === 'success' ? '#00b894' : '#e17055'">
            <CircleCheck v-if="suggestInfo.suggested_status === 'completed'" />
            <Setting v-else-if="suggestInfo.suggested_status === 'repairing'" />
            <Search v-else-if="suggestInfo.suggested_status === 'diagnosing'" />
            <CircleCheck v-else />
          </el-icon>
        </div>
        <div class="suggest-message">
          <p class="suggest-text">{{ suggestInfo.reason }}</p>
          <p class="suggest-target">{{ t('maintSuggestTargetStatus') }}: <strong>{{ suggestInfo.suggested_label }}</strong></p>
        </div>
      </div>
      <template #footer>
        <el-button @click="cancelSuggest">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="confirmSuggestTransition">{{ t('maintSuggestConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 扫码添加返回件对话框 -->
    <el-dialog v-model="returnScanDialogVisible" :title="t('maintDetailScanReturnDialog')" width="900px">
      <ScanSession
        ref="returnScanSessionRef"
        default-type="return"
        :device-id="maintenance?.device_id"
        :auto-start="returnScanDialogVisible"
        :reference="maintenance?.maint_no"
        @complete="onReturnScanSessionComplete"
        @cancel="returnScanDialogVisible = false"
      />
      <template #footer>
        <el-button @click="returnScanDialogVisible = false">{{ t('actionClose') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Aim, Edit, Delete, Setting, Box, RefreshRight, Document, InfoFilled, Operation, Coin, Monitor, Switch, User, Clock, Timer, CircleCheck, CircleClose, MoreFilled, Search, WarningFilled, SuccessFilled, Select, Plus, ArrowLeft } from '@element-plus/icons-vue'
import { getMaintenances, getMaintenanceDetail, updateMaintenance, deleteMaintenance, getDevices, getPartList, createMovement, getPartBySerialNumber, searchInStockParts, transitionMaintenanceStatus, getMaintenanceEvents, assignMaintenance, getUsers } from '@/api'
import api from '@/api/request'
import ScanSession from '@/components/ScanSession.vue'
import dayjs from 'dayjs'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()

const maintenance = ref({})
const device = ref(null)
const loading = ref(false)
const savingDiagnosis = ref(false)
const showEditDialog = ref(false)
const activeTab = ref('spare')

// 工作日志
const newNote = ref('')
const addingNote = ref(false)

// 状态系统
const statusInfo = ref({
  status: 'created',
  status_label: '创建',
  progress_percent: 20,
  priority: 'P3',
  current_owner: null,
  sla_deadline: null,
  sla_remaining: null,
  events: []
})
const events = ref([])
const showAssignDialog = ref(false)
const assignForm = ref({ owner: '' })
const users = ref([])  // 用户列表

// 备件相关
const sparePartOptions = ref([])
const spareLoading = ref(false)
const selectedSparePart = ref(null)

// 扫码对话框
const scanDialogVisible = ref(false)
const scanSessionRef = ref(null)
const originalSpareParts = ref([])  // 原始备件列表，用于判断新增

// 返回件扫码对话框
const returnScanDialogVisible = ref(false)
const returnScanSessionRef = ref(null)

// 返回件扫码相关
const returnScanInput = ref('')
const returnScanLoading = ref(false)
const returnFoundInfo = ref(null)
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
  description: '',
  // ===== 半自动状态机字段 =====
  diagnosis_text: '',
  diagnosis_result: '',  // fault_found, no_fault, need_replace, need_upgrade
  repair_actions: '',  // JSON数组字符串
  verification_result: '',  // passed, failed, partial
  verification_notes: '',
  verify_passed: false
})

// 状态建议对话框
const showSuggestDialog = ref(false)
const suggestInfo = ref({
  suggested_status: '',
  suggested_label: '',
  reason: '',
  needs_confirm: true
})

// 状态常量映射
const STATUS_STEPS = {
  'created': 1,
  'pending': 1,  // pending 视为初始状态
  'repairing': 2,  // 直接进入维修阶段
  'verifying': 3,
  'completed': 4,
  'cancelled': 0
}

const STATUS_ICONS = {
  'created': 'Document',
  'pending': 'Document',  // pending 视为初始状态
  'diagnosing': 'Search',
  'repairing': 'Setting',
  'verifying': 'CircleCheck',
  'completed': 'CircleCheck',
  'cancelled': 'CircleClose'
}

const STATUS_COLORS = {
  'created': 'info',
  'pending': 'info',  // pending 视为初始状态
  'diagnosing': 'warning',
  'repairing': 'primary',
  'verifying': 'success',
  'completed': 'success',
  'cancelled': 'danger'
}

const PRIORITY_COLORS = {
  'P1': 'danger',
  'P2': 'warning',
  'P3': 'info',
  'P4': 'success'
}

// 计算当前 workflow 步骤（基于后端状态）
const workflowStep = computed(() => {
  return STATUS_STEPS[statusInfo.value.status] || 1
})

// 获取下一步可转换的状态
const nextStatusOptions = computed(() => {
  const currentStatus = statusInfo.value.status
  const transitions = {
    'created': [{ status: 'repairing', label: t('maintTransitionToRepairing') }],
    'pending': [{ status: 'repairing', label: t('maintTransitionToRepairing') }],
    'repairing': [{ status: 'verifying', label: t('maintTransitionToVerifying') }],
    'verifying': [{ status: 'completed', label: t('maintTransitionToCompleted') }],
    'completed': [],
    'cancelled': []
  }
  return transitions[currentStatus] || []
})

// 是否可以取消
const canCancel = computed(() => {
  const cancellableStates = ['created', 'pending', 'repairing', 'verifying']
  return cancellableStates.includes(statusInfo.value.status)
})

// 是否可以提交验证（维修中状态且已填写备件信息）
const canSubmitVerification = computed(() => {
  // 必须在 repairing 状态
  if (statusInfo.value.status !== 'repairing') return false
  // 检查是否有备件或返回件信息（至少填写过内容）
  // 这个条件可以灵活调整，比如只要有工作日志就可以提交
  return true  // 暂时允许任何维修中状态提交验证
})

// ===== DNAC风格：主操作按钮 =====
const primaryActionText = computed(() => {
  const texts = {
    'created': t('maintActionStart'),
    'pending': t('maintActionStart'),
    'repairing': t('maintActionComplete'),
    'verifying': t('maintVerifyPass'),
    'completed': t('maintStatusCompleted'),
    'cancelled': t('maintStatusCancelled')
  }
  return texts[statusInfo.value.status] || t('actionEdit')
})

const primaryActionIcon = computed(() => {
  const icons = {
    'created': 'Setting',
    'pending': 'Setting',
    'repairing': 'CircleCheck',
    'verifying': 'SuccessFilled'
  }
  return icons[statusInfo.value.status] || 'Edit'
})

// 主操作处理（根据状态流转）
const handlePrimaryAction = async () => {
  const status = statusInfo.value.status
  try {
    if (status === 'created' || status === 'pending') {
      // created/pending -> repairing（直接进入维修）
      await transitionMaintenanceStatus(maintenance.value.id, {
        status: 'repairing',
        operator: 'Web'
      })
    } else if (status === 'repairing') {
      // repairing -> verifying
      await submitForVerification()
    } else if (status === 'verifying') {
      // verifying -> completed
      await verifyPass()
    }
  } catch (e) {
    ElMessage.error(t('maintTransitionFailed') + ': ' + (e.response?.data?.detail || e.message))
  }
}

// 聚焦到工作日志输入区
const focusNoteInput = () => {
  const noteInput = document.querySelector('.note-input textarea')
  if (noteInput) {
    noteInput.focus()
  }
}

// ===== Timeline 事件处理 =====
const getEventIcon = (eventType) => {
  const icons = {
    'created': 'Document',
    'diagnosing': 'Search',
    'repairing': 'Setting',
    'verifying': 'CircleCheck',
    'completed': 'SuccessFilled',
    'cancelled': 'CircleClose',
    'assigned': 'User',
    'work_note': 'Edit',
    'fault_diagnosis': 'WarningFilled',
    'diagnosis_added': 'Search',
    'verification_submitted': 'CircleCheck',
    'verification_passed': 'SuccessFilled'
  }
  return icons[eventType] || 'MoreFilled'
}

const getEventLabel = (eventType) => {
  const labels = {
    'created': t('maintEventCreated'),
    'diagnosing': t('maintEventDiagnosing'),
    'repairing': t('maintEventRepairing'),
    'verifying': t('maintEventVerifying'),
    'completed': t('maintEventCompleted'),
    'cancelled': t('maintEventCancelled'),
    'assigned': t('maintEventAssigned'),
    'work_note': t('maintEventNote'),
    'fault_diagnosis': t('maintEventFaultDiagnosis'),
    'diagnosis_added': t('maintEventDiagnosisAdded'),
    'verification_submitted': t('maintEventVerificationSubmitted'),
    'verification_passed': t('maintEventVerificationPassed')
  }
  return labels[eventType] || eventType
}

const getStepClass = (step) => {
  if (workflowStep.value > step) return 'completed'
  if (workflowStep.value === step) return 'active'
  return 'pending'
}

const getStatusTagClass = (status) => {
  return STATUS_COLORS[status] || 'info'
}

const getPriorityTagClass = (priority) => {
  return PRIORITY_COLORS[priority] || 'info'
}

const getMaintTypeType = (type) => {
  const types = { preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }
  return types[type] || ''
}

const getMaintTypeTagClass = (type) => {
  const classes = { preventive: 'success', corrective: 'warning', upgrade: 'info', emergency: 'danger' }
  return classes[type] || 'info'
}

const getMaintTypeText = (type) => {
  const texts = { preventive: t('maintTypePreventive'), corrective: t('maintTypeCorrective'), upgrade: t('maintTypeUpgrade'), emergency: t('maintTypeEmergency') }
  return texts[type] || type
}

const formatDateTime = (date) => dayjs(date).format('YYYY-MM-DD HH:mm')

const formatCurrency = (value) => {
  const num = value || 0
  return `¥${num.toFixed(2)}`
}

// 状态流转
const handleStatusTransition = async (targetStatus) => {
  try {
    const result = await transitionMaintenanceStatus(maintenance.value.id, {
      status: targetStatus,
      operator: 'Web'
    })
    ElMessage.success(t('maintTransitionSuccess', { status: result.status_label }))
    loadMaintenance()
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    ElMessage.error(t('maintTransitionFailed') + ': ' + detail)
  }
}

// 取消维修
const handleCancel = async () => {
  try {
    await ElMessageBox.confirm(t('maintTransitionToCancelled') + '?', t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })
    await transitionMaintenanceStatus(maintenance.value.id, {
      status: 'cancelled',
      operator: 'Web'
    })
    ElMessage.success(t('maintTransitionSuccess', { status: t('maintStatusLabelCancelled') }))
    loadMaintenance()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(t('maintTransitionFailed'))
    }
  }
}

// 添加工作日志
const addWorkNote = async () => {
  if (!newNote.value.trim()) {
    ElMessage.warning(t('maintNotePlaceholder'))
    return
  }

  addingNote.value = true
  try {
    await api.post(`/maintenance/${maintenance.value.id}/work-note`, {
      note: newNote.value,
      operator: 'Web'
    })
    ElMessage.success(t('maintNoteAdded'))
    newNote.value = ''
    loadMaintenance()
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    ElMessage.error(t('maintNoteFailed') + ': ' + detail)
  } finally {
    addingNote.value = false
  }
}

// 提交验证
const submitForVerification = async () => {
  try {
    await ElMessageBox.confirm(
      t('maintSubmitConfirm'),
      t('msgConfirm'),
      { type: 'info' }
    )

    // 先保存当前编辑的备件信息
    if (editForm.value.spare_parts.length > 0 || editForm.value.return_parts.length > 0) {
      const combinedParts = [
        ...editForm.value.spare_parts.map(p => ({ ...p, is_return: false })),
        ...editForm.value.return_parts.map(p => ({ ...p, is_return: true }))
      ]
      await updateMaintenance(maintenance.value.id, {
        parts_replaced: JSON.stringify(combinedParts),
        parts_cost: editForm.value.parts_cost
      })
    }

    // 提交验证
    const result = await api.post(`/maintenance/${maintenance.value.id}/submit-verification`, {
      operator: 'Web'
    })
    ElMessage.success(t('maintSubmitted'))
    loadMaintenance()
  } catch (e) {
    if (e !== 'cancel') {
      const detail = e.response?.data?.detail || e.message
      ElMessage.error(t('maintSubmitFailed') + ': ' + detail)
    }
  }
}

// 验证通过
const verifyPass = async () => {
  try {
    await ElMessageBox.confirm(
      t('maintVerifyConfirm'),
      t('msgConfirm'),
      { type: 'success' }
    )

    const result = await api.post(`/maintenance/${maintenance.value.id}/verify-pass`, {
      operator: 'Web'
    })
    ElMessage.success(t('maintVerified'))
    loadMaintenance()
  } catch (e) {
    if (e !== 'cancel') {
      const detail = e.response?.data?.detail || e.message
      ElMessage.error(t('maintVerifyFailed') + ': ' + detail)
    }
  }
}

// 保存诊断信息
const saveDiagnosis = async () => {
  if (!editForm.value.diagnosis_text) {
    ElMessage.warning(t('maintDiagnosisPlaceholder'))
    return
  }

  savingDiagnosis.value = true
  try {
    // 保存诊断信息
    await updateMaintenance(maintenance.value.id, {
      diagnosis_text: editForm.value.diagnosis_text,
      diagnosis_result: editForm.value.diagnosis_result
    })

    // 如果当前是 created 或 pending 状态，自动推进到 diagnosing
    if (statusInfo.value.status === 'created' || statusInfo.value.status === 'pending') {
      await transitionMaintenanceStatus(maintenance.value.id, {
        status: 'diagnosing',
        operator: 'Web',
        notes: '填写诊断信息后自动推进'
      })
      ElMessage.success(t('maintDiagnosisSavedAndTransitioned'))
    } else {
      ElMessage.success(t('maintDiagnosisSaved'))
    }

    // 刷新数据
    loadMaintenance()
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    ElMessage.error(t('maintDiagnosisSaveFailed') + ': ' + detail)
  } finally {
    savingDiagnosis.value = false
  }
}

// 验证结果变更处理
const handleVerificationResultChange = (value) => {
  // 根据验证结果自动设置 verify_passed
  editForm.value.verify_passed = value === 'passed'
}

// 分配负责人
const handleAssign = async () => {
  if (!assignForm.value.owner) {
    ElMessage.warning(t('maintOwnerPlaceholder'))
    return
  }
  try {
    await assignMaintenance(maintenance.value.id, { owner: assignForm.value.owner })
    ElMessage.success(t('maintAssignSuccess', { owner: assignForm.value.owner }))
    showAssignDialog.value = false
    loadMaintenance()
  } catch (e) {
    ElMessage.error(t('maintAssignFailed'))
  }
}

// 搜索备件（只搜索库存中 in_stock 状态的备件）
const searchSpareParts = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    // 使用专用接口搜索库存中的备件（只返回 in_stock 状态）
    const result = await searchInStockParts(query)
    if (result.items && result.items.length > 0) {
      sparePartOptions.value = result.items.map(item => ({
        id: item.id,
        part_number: item.part_number,
        name: item.name,
        serial_number: item.serial_number,
        quantity_in_stock: item.quantity_in_stock,
        unit_price: item.unit_price,
        is_serial_match: true,  // 标记为精确匹配
        instance_status: item.status  // 实例状态
      }))
    } else {
      sparePartOptions.value = []
    }
  } catch (e) {
    ElMessage.error(t('spareLoadFailed'))
    sparePartOptions.value = []
  } finally {
    spareLoading.value = false
  }
}

// 加载初始备件列表（不自动加载，用户需输入搜索）
const loadInitialSpareParts = debounce(async (force = false) => {
  sparePartOptions.value = []
}, 300)

// 添加备件到编辑表单
const addSparePartToEditForm = () => {
  if (!selectedSparePart.value) return

  const part = sparePartOptions.value.find(p => p.id === selectedSparePart.value)
  if (!part) return

  // 如果是序列号匹配，检查是否已添加过该序列号
  if (part.is_serial_match && part.serial_number) {
    const existingBySerial = editForm.value.spare_parts.find(p => p.serial_number === part.serial_number)
    if (existingBySerial) {
      ElMessage.warning(t('maintSerialAlreadyInList', { sn: part.serial_number }))
      selectedSparePart.value = null
      return
    }
  }

  const existing = editForm.value.spare_parts.find(p => p.part_id === part.id && !p.serial_number)
  if (existing) {
    existing.quantity += 1
  } else {
    editForm.value.spare_parts.push({
      part_id: part.id,
      part_number: part.part_number,
      name: part.name,
      serial_number: part.serial_number || null,  // 序列号匹配时携带SN
      unit_price: part.unit_price || 0,
      quantity: 1,
      is_serial_match: part.is_serial_match || false  // 标记来源
    })
  }

  updateEditPartsCost()
  selectedSparePart.value = null
}

// 打开扫码对话框
const openScanDialog = () => {
  scanDialogVisible.value = true
}

// 打开返回件扫码对话框
const openReturnScanDialog = () => {
  returnScanDialogVisible.value = true
}

// 扫码会话完成
const onScanSessionComplete = async (result) => {
  // 将扫描的备件加入编辑表单的更换列表（已在扫码会话中自动出库）
  for (const item of result.items) {
    const existing = editForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      existing.quantity += 1
      ElMessage.info(t('maintQuantityPlusOne', { name: item.name }))
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
      ElMessage.success(t('maintPartAdded', { name: item.name }))
    }
  }
  updateEditPartsCost()
  scanDialogVisible.value = false
  ElMessage.success(t('maintPartsAdded', { count: result.items.length }))
}

// 返回件扫码会话完成
const onReturnScanSessionComplete = async (result) => {
  // 将扫描的返回件加入编辑表单（返回件扫码会话不会自动出库，只是查询信息）
  for (const item of result.items) {
    const existing = editForm.value.return_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      ElMessage.warning(t('maintSerialAlreadyInList', { sn: item.serial_number }))
      continue
    }
    editForm.value.return_parts.push({
      part_id: item.part_id,
      part_number: item.part_number,
      name: item.name,
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      quantity: 1,
      scrap_in: item.part_id ? true : false,  // 有备件ID默认入报废库
      is_from_scan: true,
      history: item.history || []
    })
    ElMessage.success(t('maintReturnPartAdded', { sn: item.serial_number }))
  }
  returnScanDialogVisible.value = false
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
    ElMessage.error(t('spareLoadFailed'))
  } finally {
    spareLoading.value = false
  }
}

// 扫码查询返回件
const scanReturnPart = async () => {
  const serial = returnScanInput.value.trim()
  if (!serial || serial.length < 4) {
    ElMessage.warning(t('maintSerialMinLength'))
    return
  }

  returnScanLoading.value = true
  try {
    const info = await getPartBySerialNumber(serial)
    returnFoundInfo.value = info
    ElMessage.success(t('maintReturnPartIdentified', { name: info.name || info.part_number }))
    // 自动填充表单
    returnPartSerial.value = info.serial_number
    returnPartNumber.value = info.part_number
    returnPartName.value = info.name
    selectedReturnPart.value = info.id
    returnPartScrap.value = true
  } catch (e) {
    returnFoundInfo.value = null
    returnPartSerial.value = serial
    ElMessage.info(t('maintSerialNotFound'))
  } finally {
    returnScanLoading.value = false
  }
}

// 清除识别结果
const clearReturnFound = () => {
  returnFoundInfo.value = null
  returnScanInput.value = ''
  returnPartSerial.value = ''
  returnPartNumber.value = ''
  returnPartName.value = ''
  selectedReturnPart.value = null
  returnPartQty.value = 1
}

// 添加识别到的返回件
const addFoundReturnPart = () => {
  if (!returnFoundInfo.value) return

  editForm.value.return_parts.push({
    part_id: returnFoundInfo.value.id,
    part_number: returnFoundInfo.value.part_number,
    name: returnFoundInfo.value.name,
    serial_number: returnFoundInfo.value.serial_number,
    unit_price: returnFoundInfo.value.unit_price || 0,
    quantity: returnPartQty.value,
    scrap_in: returnPartScrap.value,
    is_from_scan: true,
    history: returnFoundInfo.value.history
  })

  ElMessage.success(t('maintReturnPartAdded', { sn: returnFoundInfo.value.serial_number }))
  clearReturnFound()
}

// 选择备件型号时自动填充
const onReturnPartSelect = () => {
  if (!selectedReturnPart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
  if (part) {
    returnPartNumber.value = part.part_number
    returnPartName.value = part.name || part.part_number
    returnPartScrap.value = true
  }
}

// 手动添加返回件
const addReturnPart = async () => {
  if (!returnPartSerial.value) {
    ElMessage.warning(t('maintEnterSerial'))
    return
  }

  // 检查是否已添加过该序列号
  const existing = editForm.value.return_parts.find(p => p.serial_number === returnPartSerial.value)
  if (existing) {
    ElMessage.warning(t('maintSerialAlreadyInList', { sn: returnPartSerial.value }))
    return
  }

  let partNumber = returnPartNumber.value
  let partName = returnPartName.value || returnPartNumber.value
  let partId = null
  let unitPrice = 0

  // 如果已经选择了备件型号
  if (selectedReturnPart.value) {
    const part = sparePartOptions.value.find(p => p.id === selectedReturnPart.value)
    if (part) {
      partId = part.id
      partNumber = part.part_number
      partName = part.name || part.part_number
      unitPrice = part.unit_price || 0
    }
  } else {
    // 如果没有选择备件型号，尝试通过序列号查询
    try {
      const info = await getPartBySerialNumber(returnPartSerial.value)
      partId = info.id
      partNumber = info.part_number
      partName = info.name
      unitPrice = info.unit_price || 0
      ElMessage.success(t('maintReturnPartIdentified', { name: info.name || info.part_number }))
    } catch (e) {
      // 序列号未找到，使用手动输入的信息
      partId = null
    }
  }

  editForm.value.return_parts.push({
    part_id: partId,
    part_number: partNumber,
    name: partName,
    serial_number: returnPartSerial.value,
    unit_price: unitPrice,
    quantity: returnPartQty.value,
    scrap_in: partId ? returnPartScrap.value : false,  // 有备件ID才能入报废库
    is_from_scan: false
  })

  ElMessage.success(t('maintReturnPartAddedNoMatch', { sn: returnPartSerial.value, hasId: partId ? '' : t('maintNoPartIdMatch') }))

  returnScanInput.value = ''
  returnFoundInfo.value = null
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

const loadMaintenance = debounce(async (force = false) => {
  loading.value = true
  try {
    const maintId = route.params.id
    // 使用新的 getMaintenanceDetail API 获取详情
    const data = await cachedRequest(
      () => getMaintenanceDetail(maintId),
      'maintenance_detail',
      { id: maintId },
      { forceRefresh: force }
    )
    maintenance.value = data

    // 设置状态信息
    statusInfo.value = {
      status: data.status || 'created',
      status_label: data.status_label || t('maintStatusLabelCreated'),
      progress_percent: data.progress_percent || 20,
      priority: data.priority || 'P3',
      current_owner: data.current_owner,
      sla_deadline: data.sla_deadline,
      sla_remaining: data.sla_remaining,
      diagnosing_at: data.diagnosing_at,
      repairing_at: data.repairing_at,
      verifying_at: data.verifying_at,
      completed_at: data.completed_at,
      cancelled_at: data.cancelled_at,
      events: data.events || []
    }
    events.value = data.events || []

    // 解析 parts_replaced 字段获取备件列表
    if (data.parts_replaced) {
      try {
        // 尝试JSON解析（新格式）
        const parsed = JSON.parse(data.parts_replaced)
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
        const partsList = data.parts_replaced.split(',').map(p => {
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
    if (data.device_id) {
      const devices = await getDevices()
      device.value = (devices.items || []).find(d => d.id === data.device_id)
    }
  } catch (error) {
    ElMessage.error(t('maintLoadDetailFailed'))
  } finally {
    loading.value = false
  }
}, 300)

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
    description: maintenance.value.description,
    // ===== 半自动状态机字段 =====
    diagnosis_text: maintenance.value.diagnosis_text || '',
    diagnosis_result: maintenance.value.diagnosis_result || '',
    repair_actions: maintenance.value.repair_actions || '',
    verification_result: maintenance.value.verification_result || '',
    verification_notes: maintenance.value.verification_notes || '',
    verify_passed: maintenance.value.verify_passed || false
  }
  lastSuggestStatus.value = ''  // 重置状态建议
  showEditDialog.value = true
}

const goBack = () => {
  router.push('/maintenance')
}

const updateMaintenanceRecord = async () => {
  if (!editForm.value.description) {
    ElMessage.warning(t('maintEnterDescription'))
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
    // 扫码添加的备件已在 ScanSession 完成时自动出库并关联设备
    // 手动添加的备件需要在此处出库并关联设备
    for (const part of editForm.value.spare_parts) {
      if (!part.is_from_scan && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'out',
          quantity: part.quantity || 1,
          serial_number: part.serial_number,
          reason: `${t('spareReasonMaintenancePartReplace')} - ${maintenance.value.maint_no}`,
          operator: 'Web',
          reference: maintenance.value.maint_no,
          target_device_id: maintenance.value.device_id  // 关联目标设备
        })
      }
    }

    // 处理返回件入报废库 - 记录来源设备
    // 扫码添加的返回件已在 ScanSession 完成时自动入报废库并记录来源设备
    // 手动添加的返回件需要在此处入报废库
    for (const part of editForm.value.return_parts) {
      if (!part.is_from_scan && part.scrap_in && part.part_id) {
        await createMovement({
          part_id: part.part_id,
          movement_type: 'scrap_in',
          quantity: part.quantity,
          serial_number: part.serial_number,
          reason: t('spareReasonReturnPartScrap'),
          operator: 'Web',
          reference: maintenance.value.maint_no,
          source_device_id: maintenance.value.device_id  // 记录来源设备
        })
      }
    }

    ElMessage.success(t('maintRecordUpdated'))
    showEditDialog.value = false
    loadMaintenance()
  } catch (error) {
    ElMessage.error(t('maintUpdateFailed') + ': ' + (error.response?.data?.detail || error.message))
  }
}

const deleteMaintenanceRecord = async () => {
  try {
    await ElMessageBox.confirm(t('maintDeleteConfirmMsg'), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteMaintenance(maintenance.value.id)
    ElMessage.success(t('maintRecordDeleted'))
    router.push('/maintenance')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('maintDeleteFailed'))
    }
  }
}

// ===== 智能状态建议 =====
const lastSuggestStatus = ref('')  // 防止重复弹窗

// 监听表单变化，自动检测状态建议
watch(
  [() => editForm.value.diagnosis_text, () => editForm.value.spare_parts, () => editForm.value.verification_result, () => editForm.value.verify_passed],
  async (newVals, oldVals) => {
    // 只在编辑对话框打开时检测
    if (!showEditDialog.value) return
    // 已完成或已取消状态不需要检测
    if (statusInfo.value.status === 'completed' || statusInfo.value.status === 'cancelled') return

    try {
      const result = await api.post(`/maintenance/${maintenance.value.id}/suggest-status`, {
        diagnosis_text: editForm.value.diagnosis_text,
        spare_parts_count: editForm.value.spare_parts.length,
        verification_result: editForm.value.verification_result,
        verify_passed: editForm.value.verify_passed
      })

      // 有状态建议且需要确认
      if (result.suggested_status && result.needs_confirm && result.suggested_status !== lastSuggestStatus.value) {
        lastSuggestStatus.value = result.suggested_status
        suggestInfo.value = result
        showSuggestDialog.value = true
      }
    } catch (e) {
      // 静默处理错误
    }
  },
  { deep: true }
)

// 确认状态变更
const confirmSuggestTransition = async () => {
  try {
    const result = await api.post(`/maintenance/${maintenance.value.id}/auto-transition`, {
      status: suggestInfo.value.suggested_status,
      operator: 'Web'
    })
    ElMessage.success(t('maintStatusAutoChanged', { status: result.status_label }))
    showSuggestDialog.value = false
    showEditDialog.value = false
    loadMaintenance()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message)
  }
}

// 取消状态建议
const cancelSuggest = () => {
  showSuggestDialog.value = false
  lastSuggestStatus.value = ''
}

onMounted(async () => {
  await loadMaintenance()
  // 加载用户列表
  try {
    const usersData = await getUsers()
    users.value = Array.isArray(usersData) ? usersData : (usersData.items || [])
  } catch (e) {
    console.error('Failed to load users:', e)
  }
  // 如果URL参数有 edit=true，自动打开编辑对话框
  if (route.query.edit === 'true') {
    openEditDialog()
  }
})
</script>

<style scoped>
.maintenance-detail-page {
  width: 100%;
  padding: 0;
}

/* ===== 页面顶部导航条 ===== */
.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.06);
  margin-bottom: 16px;
  position: relative;
  overflow: hidden;
}

.page-nav-bar::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #00b894, #55efc4, #0984e3);
}

.nav-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.status-tag {
  font-weight: 500;
}

.priority-tag {
  margin-left: 0;
}

.nav-right {
  display: flex;
  gap: 8px;
}

.nav-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  color: white;
  border: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.25);
}

.nav-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 184, 148, 0.35);
}

.nav-action-btn.secondary {
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  box-shadow: none;
  padding: 8px 12px;
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
}

.maintenance-detail-page .el-page-header {
  margin-bottom: 16px;
}

/* V2 左右布局 */
.maint-header {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  width: 100%;
}

.maint-info-card {
  flex: 1;
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-default, #E2E8F2);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 48, 135, 0.06), 0 1px 2px rgba(0, 48, 135, 0.04);
}

/* 任务头部信息区 */
.task-header-section {
  margin-bottom: 20px;
}

.task-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.maint-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #0D1B2A);
}

.status-tag {
  font-weight: 500;
}

.priority-tag {
  margin-left: 0;
}

.task-meta-row {
  display: flex;
  gap: 20px;
  color: var(--text-secondary, #3A4A5C);
  font-size: 13px;
  margin-bottom: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.meta-item .el-icon {
  color: var(--text-tertiary, #9BAABB);
}

.meta-item.sla.overdue {
  color: var(--accent-danger, #d63031);
  font-weight: 500;
}

.meta-item.sla.overdue .el-icon {
  color: var(--accent-danger, #d63031);
}

.task-device-row {
  display: flex;
  gap: 16px;
  color: var(--text-secondary, #3A4A5C);
  font-size: 13px;
}

/* Workflow 步骤增强版 */
.workflow-steps-enhanced {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 16px;
  background: var(--bg-tertiary, #f7f9fc);
  border-radius: 10px;
  margin-bottom: 16px;
  overflow-x: auto;
}

.workflow-step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--bg-card, #ffffff);
  transition: all 0.2s;
}

.workflow-step-item.completed {
  background: rgba(0, 184, 148, 0.1);
}

.workflow-step-item.active {
  background: rgba(225, 112, 85, 0.15);
  box-shadow: 0 0 0 2px var(--accent-warning, #e17055);
}

.workflow-step-item.pending {
  opacity: 0.6;
}

.step-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg-tertiary);
}

.workflow-step-item.completed .step-icon {
  background: var(--accent-success, #00b894);
  color: #fff;
}

.workflow-step-item.active .step-icon {
  background: var(--accent-warning, #e17055);
  color: #fff;
}

.workflow-step-item.pending .step-icon {
  background: var(--bg-tertiary);
  color: var(--text-muted, #9BAABB);
}

.step-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

.workflow-step-item.completed .step-label {
  color: var(--accent-success);
}

.workflow-step-item.active .step-label {
  color: var(--accent-warning);
  font-weight: 600;
}

.step-time {
  font-size: 11px;
  color: var(--text-muted, #9BAABB);
  font-family: var(--font-display);
}

.step-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 600;
}

.step-dot.completed {
  background: var(--accent-success, #00b894);
  color: #fff;
}

.step-dot.active {
  background: var(--accent-warning, #e17055);
  color: #fff;
}

.step-dot.pending {
  background: var(--bg-card, #ffffff);
  border: 2px solid var(--border-default, #E2E8F2);
  color: var(--text-muted, #9BAABB);
}

.step-connector {
  width: 20px;
  height: 2px;
  background: var(--border-default, #E2E8F2);
  flex-shrink: 0;
}

.step-connector.completed {
  background: var(--accent-success, #00b894);
}

/* 进度条 */
.progress-bar-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.progress-bar-section .el-progress {
  flex: 1;
}

.progress-label {
  font-size: 12px;
  color: var(--text-tertiary);
  font-weight: 500;
}

.maint-actions-card {
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 状态流转操作区 */
.status-transition-card,
.assign-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.transition-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.transition-btn {
  width: 100%;
  min-width: 100%;
  max-width: 100%;
  height: 44px !important;
  min-height: 44px;
  max-height: 44px;
  border-radius: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  padding: 0 16px !important;
  margin: 0 !important;
  box-sizing: border-box;
}

.transition-btn .el-icon {
  margin: 0 !important;
}

.transition-btn span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.transition-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* 工作日志输入区 */
.work-notes-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.note-input {
  margin-top: 12px;
}

.note-submit-btn {
  width: 100%;
  margin-top: 12px;
  height: 40px;
  border-radius: 8px;
  font-weight: 600;
}

/* DNAC风格流程操作区 */
.action-control-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.primary-action-area {
  margin-bottom: 12px;
}

.primary-action-btn {
  width: 100%;
  height: 40px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: var(--accent-primary);
  border: none;
  color: white;
  transition: all 0.2s;
}

.primary-action-btn:hover {
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.2);
  transform: translateY(-1px);
}

.more-actions-area {
  display: flex;
  justify-content: flex-end;
}

.more-actions-btn {
  height: 36px;
  border-radius: 8px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  transition: all 0.2s;
}

.more-actions-btn:hover {
  background: var(--bg-hover);
  border-color: var(--border-default);
}

/* dropdown危险项样式 */
.dropdown-danger {
  color: var(--accent-danger) !important;
}

.el-dropdown-menu__item.dropdown-danger:hover {
  background-color: rgba(214, 48, 49, 0.1);
  color: var(--accent-danger);
}

/* 取消按钮区 */
.cancel-card {
  padding: 12px;
}

.cancel-btn {
  width: 100%;
  height: 40px;
}

/* 故障来源标记 */
.fault-notes-tag {
  margin-left: 8px;
}

/* DNAC风格事件时间线 */
.timeline-section {
  margin-top: 16px;
}

.timeline-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.timeline-container {
  position: relative;
  padding-left: 24px;
  max-height: 400px;
  overflow-y: auto;
  scrollbar-width: thin;
}

.timeline-container::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--border-light);
}

.timeline-item {
  position: relative;
  padding: 8px 0 16px 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-item.from-fault {
  position: relative;
}

.timeline-dot {
  position: absolute;
  left: -20px;
  top: 8px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 2px solid var(--accent-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.timeline-dot.completed {
  background: var(--accent-success);
  border-color: var(--accent-success);
}

.timeline-dot.cancelled {
  background: var(--accent-danger);
  border-color: var(--accent-danger);
}

.timeline-dot.diagnosis_added,
.timeline-dot.verifying {
  background: var(--accent-secondary);
  border-color: var(--accent-secondary);
}

.timeline-dot.verification_passed,
.timeline-dot.verification_submitted {
  background: var(--accent-success);
  border-color: var(--accent-success);
}

.timeline-dot.created {
  background: var(--accent-primary);
  border-color: var(--accent-primary);
}

.timeline-dot.fault_diagnosis {
  background: var(--accent-warning);
  border-color: var(--accent-warning);
}

.timeline-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}

.timeline-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: normal;
  word-wrap: break-word;
  overflow-wrap: break-word;
  line-height: 1.4;
}

.timeline-time {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: var(--font-display);
  white-space: nowrap;
}

.timeline-meta {
  display: flex;
  align-items: center;
  gap: 4px;
}

.timeline-operator {
  font-size: 12px;
  color: var(--text-secondary);
}

/* 操作区独立 Card */
.actions-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.actions-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
}

.actions-card-header .el-icon {
  color: var(--color-gb);
}

.action-btn-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn-group .el-button {
  width: 100%;
  min-width: 100%;
  max-width: 100%;
  height: 44px !important;
  min-height: 44px;
  max-height: 44px;
  border-radius: 10px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
  padding: 0 16px !important;
  margin: 0 !important;
  box-sizing: border-box;
}

.action-btn-group .el-button .el-icon {
  margin: 0 !important;
}

.action-btn-group .el-button span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn-group .el-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

/* 成本统计数据卡片化 */
.cost-stats-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.cost-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}

.cost-stat-item {
  padding: 12px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-md);
  text-align: center;
}

.cost-stat-label {
  font-size: 11px;
  color: var(--text-tertiary);
  margin-bottom: 4px;
}

.cost-stat-value {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.cost-stat-item.total {
  grid-column: 1 / -1;
  background: rgba(214, 48, 49, 0.1);
}

.cost-stat-item.total .cost-stat-value {
  color: var(--accent-danger);
  font-size: 20px;
}

/* 设备信息区增强 */
.device-info-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.device-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}

.device-avatar {
  background: linear-gradient(135deg, var(--color-gb) 0%, var(--color-gb-mid) 100%);
  color: #fff;
}

.device-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.device-name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.device-ip {
  font-size: 12px;
  color: var(--text-tertiary);
  font-family: var(--font-display);
}

/* 暗色模式适配 */
.dark .actions-card-header .el-icon {
  color: var(--accent-primary);
}

.dark .cost-stat-item.total {
  background: rgba(214, 48, 49, 0.15);
}

.dark .device-avatar {
  background: linear-gradient(135deg, var(--accent-primary) 0%, #00a884 100%);
}

.dark .workflow-step-item.completed {
  background: rgba(0, 184, 148, 0.15);
}

.dark .workflow-step-item.active {
  background: rgba(225, 112, 85, 0.2);
}

.dark .timeline-item.created {
  background: rgba(9, 132, 227, 0.12);
}

.dark .timeline-item.completed {
  background: rgba(0, 184, 148, 0.15);
}

.dark .timeline-item.cancelled {
  background: rgba(214, 48, 49, 0.15);
}

.dark .timeline-item.diagnosis_added {
  background: rgba(9, 132, 227, 0.15);
}

.dark .timeline-item.verification_submitted {
  background: rgba(116, 185, 255, 0.15);
}

.dark .timeline-item.verification_passed {
  background: rgba(0, 184, 148, 0.2);
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #0D1B2A);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle, #f1f5f9);
}

/* 详情网格 */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  background: var(--bg-tertiary, #f7f9fc);
  border-radius: 6px;
}

.detail-item-label {
  font-size: 11px;
  color: var(--text-muted, #9BAABB);
  font-weight: 500;
}

.detail-item-value {
  font-size: 14px;
  color: var(--text-primary, #0D1B2A);
  font-weight: 500;
}

/* Tabs 样式 */
.tabs-wrapper {
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border-default, #E2E8F2);
  border-radius: 12px;
  overflow: hidden;
}

.tabs-header {
  display: flex;
  border-bottom: 1px solid var(--border-default, #E2E8F2);
  padding: 0 16px;
}

.tab-item {
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary, #3A4A5C);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-item:hover {
  color: var(--text-primary, #0D1B2A);
}

.tab-item.active {
  color: var(--accent-primary, #003087);
  border-bottom-color: var(--accent-primary, #003087);
}

.tabs-content {
  padding: 16px;
}

/* Cell 样式 */
.cell-link {
  color: var(--accent-secondary, #0984e3);
  font-weight: 500;
  text-decoration: none;
}

.cell-link:hover {
  text-decoration: underline;
}

.cell-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.cell-tag.success {
  background: rgba(0, 184, 148, 0.15);
  color: var(--accent-success, #00b894);
}

.cell-tag.warning {
  background: rgba(255, 184, 0, 0.15);
  color: var(--accent-warning, #e17055);
}

.cell-tag.danger {
  background: rgba(214, 48, 49, 0.15);
  color: var(--accent-danger, #d63031);
}

.cell-tag.info {
  background: rgba(9, 132, 227, 0.15);
  color: var(--accent-secondary, #0984e3);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
  min-height: 200px;
}

.empty-icon {
  font-size: 48px;
  color: var(--text-muted, #9BAABB);
  margin-bottom: 16px;
}

.empty-text {
  font-size: 14px;
  color: var(--text-secondary, #3A4A5C);
}

/* 备件显示样式 */
.spare-parts-display {
  margin-bottom: 20px;
}

.parts-total {
  margin-top: 10px;
  padding: 8px 12px;
  background: var(--bg-tertiary, #f7f9fc);
  border-radius: 4px;
  text-align: right;
}

.cost {
  color: var(--accent-warning, #e17055);
  font-weight: bold;
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
  gap: 8px;
  margin-bottom: 6px;
}

.selected-parts {
  margin-top: 6px;
}

.parts-summary {
  margin-top: 6px;
  padding: 6px 10px;
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
  margin-bottom: 10px;
}

.return-tip {
  margin-top: 6px;
  padding: 4px 8px;
  background: #fdf6ec;
  border-radius: 4px;
  color: #909399;
  font-size: 12px;
}

/* 返回件编辑区域 */
.return-parts-section {
  width: 100%;
}

.return-scan-area {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.return-scan-tip {
  font-size: 12px;
  color: var(--el-color-primary);
  padding: 4px 8px;
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
}

.return-found-info {
  margin-bottom: 16px;
}

.found-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.found-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.return-manual-area {
  margin-bottom: 6px;
}

.return-manual-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.return-manual-tip {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  padding: 3px 6px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.return-parts-table {
  margin-top: 6px;
}

.scrap-label {
  margin-left: 6px;
  font-size: 12px;
  color: #909399;
}

.scrap-label.no-id {
  color: #E6A23C;
}

.return-tip-form {
  margin-top: 6px;
  padding: 4px 8px;
  background: #fdf6ec;
  border-radius: 4px;
  color: #909399;
  font-size: 12px;
}

.no-return-tip {
  margin-top: 6px;
}

.cell-primary {
  color: var(--el-color-primary);
  font-weight: 500;
}

.cell-success {
  color: var(--accent-success, #00b894);
  font-weight: 500;
}

/* 成本统计 */
.cost-section {
  margin-top: 16px;
}

.cost-items {
  padding: 8px 0;
}

.cost-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.cost-label {
  font-size: 13px;
  color: var(--text-muted, #9BAABB);
}

.cost-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #0D1B2A);
}

.cost-value.highlight {
  color: var(--accent-warning, #e17055);
  font-size: 16px;
}

.cost-item.total {
  border-top: 2px solid var(--border-default, #E2E8F2);
  padding-top: 12px;
}

/* 设备信息 */
.device-section {
  margin-top: 16px;
}

.device-summary {
  display: flex;
  align-items: center;
  gap: 12px;
}

.device-info h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: var(--text-primary, #0D1B2A);
}

.device-info p {
  margin: 0 0 4px 0;
  color: var(--text-secondary, #3A4A5C);
  font-size: 13px;
}

/* 维修描述 */
.description {
  line-height: 1.8;
  color: var(--text-secondary, #3A4A5C);
  padding: 12px;
  background: var(--bg-tertiary, #f7f9fc);
  border-radius: 6px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .maint-header {
    flex-direction: column;
  }
  .maint-actions-card {
    width: 100%;
  }
}

/* ===== 编辑对话框样式 ===== */
.edit-dialog-content {
  max-width: 680px;
  margin: 0 auto;
}

.edit-dialog-content .el-form-item {
  margin-bottom: 8px;
}

.edit-dialog-content .el-form-item__label {
  font-size: 13px;
}

/* Section 卡片化 */
.form-section {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 8px 10px;
  margin-bottom: 8px;
  transition: all 0.2s;
}

.form-section:hover {
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.08);
}

.form-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border-subtle);
}

.form-section-title .el-icon {
  color: var(--color-gb);
}

/* 扫码功能条 */
.scan-action-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: linear-gradient(135deg, var(--color-gb) 0%, var(--color-gb-mid) 100%);
  border-radius: var(--radius-md);
  margin-bottom: 6px;
}

.scan-action-bar.return {
  background: linear-gradient(135deg, #636e72 0%, #4a5455 100%);
}

.scan-action-bar .scan-btn {
  background: rgba(255,255,255,0.15);
  border-color: rgba(255,255,255,0.3);
  color: #fff;
  font-weight: 600;
  height: 36px;
  border-radius: 8px;
  transition: all 0.2s;
}

.scan-action-bar .scan-btn:hover {
  background: rgba(255,255,255,0.25);
  transform: translateY(-1px);
}

.scan-tip-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  color: rgba(255,255,255,0.9);
  font-size: 12px;
}

/* 暗色模式适配 */
.dark .form-section {
  background: var(--bg-card);
  border-color: var(--border-default);
}

.dark .form-section:hover {
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.1);
}

.dark .form-section-title .el-icon {
  color: var(--accent-primary);
}

/* ===== 表格样式优化 ===== */
.selected-parts .el-table,
.return-parts-table .el-table {
  border-radius: var(--radius-md);
}

.selected-parts .el-table__cell,
.return-parts-table .el-table__cell {
  padding: 12px 14px;
}

.selected-parts .el-table__body tr:hover > td.el-table__cell,
.return-parts-table .el-table__body tr:hover > td.el-table__cell {
  background: rgba(0, 48, 135, 0.05) !important;
}

.dark .selected-parts .el-table__body tr:hover > td.el-table__cell,
.dark .return-parts-table .el-table__body tr:hover > td.el-table__cell {
  background: rgba(0, 184, 148, 0.08) !important;
}

/* 数量输入优化 */
.selected-parts .el-input-number,
.return-parts-table .el-input-number {
  width: 80px;
}

.selected-parts .el-input-number .el-input__inner,
.return-parts-table .el-input-number .el-input__inner {
  text-align: center;
  font-family: var(--font-display);
}

/* 删除按钮图标化 */
.delete-btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  transition: all 0.2s;
}

.delete-btn-icon:hover {
  background: var(--danger-bg);
}

/* ===== 诊断和验证 Section 标题样式 ===== */
.form-section-title.diagnosis {
  color: var(--accent-secondary);
}

.form-section-title.diagnosis .el-icon {
  color: #0984e3;
}

.form-section-title.verification {
  color: var(--accent-success);
}

.form-section-title.verification .el-icon {
  color: #00b894;
}

.section-badge {
  margin-left: 8px;
  font-size: 11px;
}

.save-tip {
  margin-left: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
}

.verify-badge {
  margin-left: 12px;
}

/* ===== 状态建议对话框样式 ===== */
.suggest-dialog .suggest-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 24px 16px;
  text-align: center;
}

.suggest-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 184, 148, 0.1);
  border-radius: 50%;
}

.suggest-message {
  width: 100%;
}

.suggest-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.suggest-target {
  font-size: 13px;
  color: var(--text-primary);
}

.suggest-target strong {
  color: var(--accent-primary);
  font-size: 16px;
}

/* 暗色模式 */
.dark .suggest-icon {
  background: rgba(0, 184, 148, 0.15);
}

/* 暗色模式 page-nav-bar */
.dark .page-nav-bar {
  background: rgba(22, 27, 34, 0.9);
  border-color: rgba(48, 54, 61, 0.8);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.dark .page-nav-bar::before {
  background: linear-gradient(90deg, #3fb950, #55efc4, #58a6ff);
}

.dark .page-title {
  color: #f0f6fc;
}

.dark .nav-action-btn {
  background: linear-gradient(135deg, #3fb950 0%, #55efc4 100%);
}

.dark .nav-action-btn.secondary {
  background: rgba(48, 54, 61, 0.8);
  color: #8b949e;
  border-color: #30363d;
}

.dark .nav-action-btn.secondary:hover {
  background: rgba(63, 185, 80, 0.15);
  border-color: #3fb950;
  color: #3fb950;
}
</style>