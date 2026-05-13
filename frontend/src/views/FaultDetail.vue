<template>
  <div class="fault-detail-page">
    <!-- 页面顶部导航条 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ fault.fault_no || t('faultDetailTitle') }}</h1>
        <el-tag :type="getStatusType(fault.status)" size="default" class="status-tag">
          {{ getStatusText(fault.status) }}
        </el-tag>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn secondary" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          {{ t('actionBack') }}
        </button>
      </div>
    </section>

    <el-row :gutter="20" style="margin-top: 20px">
      <!-- 左侧：故障信息 + 操作区 -->
      <el-col :span="16">
        <!-- 状态流转卡片 -->
        <el-card class="status-flow-card">
          <template #header>
            <div class="card-header-flex">
              <span>{{ t('faultStatusFlow') }}</span>
              <el-tag :type="getStatusType(fault.status)" size="large">
                {{ getStatusText(fault.status) }}
              </el-tag>
            </div>
          </template>

          <!-- 状态流程指示器 -->
          <div class="status-flow-indicator">
            <div
              v-for="(step, idx) in statusSteps"
              :key="step.key"
              :class="['flow-step', { active: fault.status === step.key, completed: isStepCompleted(step.key) }]"
            >
              <div class="step-circle">
                <el-icon v-if="isStepCompleted(step.key)"><Check /></el-icon>
                <span v-else>{{ idx + 1 }}</span>
              </div>
              <div class="step-label">{{ step.label }}</div>
              <div v-if="idx < statusSteps.length - 1" class="step-line"></div>
            </div>
          </div>

          <!-- 维修中状态分支（当故障已转维修时显示） -->
          <div class="maintenance-branch" v-if="fault.status === 'transferred' && maintenanceInfo">
            <div class="branch-indicator">
              <div class="branch-arrow">↘</div>
              <div class="branch-label">{{ t('faultMaintenanceBranch') }}</div>
            </div>
            <div class="maintenance-status-flow">
              <div
                :class="['maint-step', { active: maintenanceInfo.status === 'repairing', completed: ['verifying', 'completed'].includes(maintenanceInfo.status) }]"
              >
                <div class="maint-step-circle">
                  <el-icon v-if="['verifying', 'completed'].includes(maintenanceInfo.status)"><Check /></el-icon>
                  <span v-else>M1</span>
                </div>
                <div class="maint-step-label">{{ t('maintStatusRepairing') }}</div>
              </div>
              <div class="maint-step-line" :class="{ completed: ['verifying', 'completed'].includes(maintenanceInfo.status) }"></div>
              <div
                :class="['maint-step', { active: maintenanceInfo.status === 'verifying', completed: maintenanceInfo.status === 'completed' }]"
              >
                <div class="maint-step-circle">
                  <el-icon v-if="maintenanceInfo.status === 'completed'"><Check /></el-icon>
                  <span v-else>M2</span>
                </div>
                <div class="maint-step-label">{{ t('maintStatusVerifying') }}</div>
              </div>
              <div class="maint-step-line" :class="{ completed: maintenanceInfo.status === 'completed' }"></div>
              <div
                :class="['maint-step', { active: maintenanceInfo.status === 'completed', completed: maintenanceInfo.status === 'completed' }]"
              >
                <div class="maint-step-circle">
                  <el-icon v-if="maintenanceInfo.status === 'completed'"><Check /></el-icon>
                  <span v-else>M3</span>
                </div>
                <div class="maint-step-label">{{ t('maintStatusCompleted') }}</div>
              </div>
            </div>
            <div class="branch-return" v-if="maintenanceInfo.status === 'completed'">
              <div class="branch-arrow">↗</div>
              <div class="branch-label">{{ t('faultReturnToResolve') }}</div>
            </div>
          </div>

          <!-- 可执行操作（简化版，主要操作在工作日志区域） -->
          <div class="action-buttons-simple" v-if="fault.status !== 'closed'">
            <span class="action-hint">{{ t('faultActionHint') }}</span>
          </div>
        </el-card>

        <!-- 工作日志/诊断记录（ServiceNow Activity风格 - 整合操作按钮） -->
        <el-card class="work-notes-card" style="margin-top: 20px">
          <template #header>
            <div class="card-header-flex">
              <span>{{ t('faultWorkNotes') }}</span>
              <el-tag v-if="fault.status !== 'closed'" type="warning" size="small">
                {{ getStatusText(fault.status) }}
              </el-tag>
            </div>
          </template>

          <!-- 添加新日志 + 操作按钮整合 -->
          <div class="add-note-section" v-if="fault.status !== 'closed'">
            <el-input
              v-model="newNoteContent"
              type="textarea"
              :rows="3"
              :placeholder="t('faultNotePlaceholder')"
              resize="none"
            />
            <div class="note-actions">
              <!-- 状态变更操作按钮（诊断状态下显示） -->
              <div class="state-change-actions" v-if="fault.status === 'diagnosing'">
                <el-button type="success" @click="submitNoteAndResolve" class="action-btn-with-note">
                  <el-icon><CircleCheck /></el-icon>
                  {{ t('faultNoteResolve') }}
                </el-button>
                <el-button type="warning" @click="submitNoteAndTransfer" class="action-btn-with-note">
                  <el-icon><Tools /></el-icon>
                  {{ t('faultNoteTransfer') }}
                </el-button>
              </div>
              <!-- 其他状态的快速操作按钮 -->
              <div class="quick-actions" v-if="fault.status !== 'diagnosing'">
                <el-button v-if="canTransition('assigned')" type="primary" @click="showAssignDialog = true">
                  <el-icon><UserFilled /></el-icon>
                  {{ t('faultAssignTo') }}
                </el-button>
                <el-button v-if="canTransition('diagnosing')" type="warning" @click="startDiagnosing">
                  <el-icon><Search /></el-icon>
                  {{ t('faultStartDiagnose') }}
                </el-button>
                <el-button v-if="canTransition('resolved')" type="success" @click="showResolveDialog = true">
                  <el-icon><CircleCheck /></el-icon>
                  {{ t('faultConfirmResolve') }}
                </el-button>
                <el-button v-if="canTransition('closed')" type="info" @click="closeFaultSubmit">
                  <el-icon><Lock /></el-icon>
                  {{ t('actionClose') }}
                </el-button>
              </div>
              <!-- 仅添加日志按钮（始终显示） -->
              <el-button type="default" @click="submitNoteOnly" :disabled="!newNoteContent" class="add-note-btn">
                <el-icon><Plus /></el-icon>
                {{ t('faultNoteAdd') }}
              </el-button>
            </div>
            <div class="action-tip" v-if="fault.status === 'diagnosing'">
              {{ t('faultDiagnosingTip') }}
            </div>
          </div>

          <!-- 日志时间线 -->
          <div class="notes-timeline" v-if="workNotes.length > 0">
            <div class="note-item" v-for="(note, idx) in workNotes" :key="idx">
              <div class="note-header">
                <span class="note-author">{{ note.author || 'System' }}</span>
                <span class="note-time">{{ formatDateTime(note.created_at) }}</span>
                <el-tag v-if="note.note_type" :type="getNoteTypeColor(note.note_type)" size="small">
                  {{ getNoteTypeLabel(note.note_type) }}
                </el-tag>
              </div>
              <div class="note-content">{{ note.content }}</div>
            </div>
          </div>

          <!-- 空状态 -->
          <div class="notes-empty" v-else>
            <el-icon><Document /></el-icon>
            <span>{{ t('faultNoNotes') }}</span>
          </div>
        </el-card>

        <!-- 故障基本信息 -->
        <el-card class="fault-info-card" style="margin-top: 20px">
          <template #header>
            <span>{{ t('faultDetailInfo') }}</span>
          </template>

          <el-descriptions :column="2" border v-if="fault.id">
            <el-descriptions-item :label="t('faultNo')">{{ fault.fault_no }}</el-descriptions-item>
            <el-descriptions-item :label="t('faultDevice')">
              <router-link :to="`/devices/${fault.device_id}`">{{ fault.device_name }}</router-link>
            </el-descriptions-item>
            <el-descriptions-item :label="t('faultLevel')">
              <el-tag :type="getSeverityType(fault.severity)">
                {{ getSeverityText(fault.severity) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item :label="t('faultType')">
              <el-tag v-if="fault.fault_type">{{ getFaultTypeText(fault.fault_type) }}</el-tag>
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item :label="t('faultDowntime')">{{ fault.downtime_minutes }} {{ t('faultMinutes') }}</el-descriptions-item>
            <el-descriptions-item :label="t('faultImpact')">{{ fault.impact || t('faultNoImpact') }}</el-descriptions-item>
            <el-descriptions-item :label="t('faultReporter')">{{ fault.reporter || 'Web' }}</el-descriptions-item>
            <el-descriptions-item :label="t('faultOccurTime')">{{ formatDateTime(fault.fault_time || fault.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <el-divider>{{ t('faultDescription') }}</el-divider>
          <p class="description">{{ fault.description || t('faultNoDescription') }}</p>

          <el-divider v-if="fault.resolution">{{ t('faultResolution') }}</el-divider>
          <p v-if="fault.resolution" class="description">{{ fault.resolution }}</p>
        </el-card>

        <!-- 其他操作（接收后才可编辑） -->
        <el-card style="margin-top: 20px" v-if="canEdit">
          <el-space>
            <el-button type="primary" @click="showEditDialog = true">
              <el-icon><Edit /></el-icon>
              {{ t('actionEdit') }}
            </el-button>
            <el-button type="danger" @click="deleteFaultSubmit">
              <el-icon><Delete /></el-icon>
              {{ t('actionDelete') }}
            </el-button>
          </el-space>
        </el-card>

        <!-- 关联的维修单信息（完整版） -->
        <el-card class="maintenance-card-enhanced" v-if="maintenanceInfo">
          <template #header>
            <div class="card-header-flex">
              <span>{{ t('faultRelatedMaintenance') }}</span>
              <div class="maint-header-tags">
                <el-tag :type="getMaintStatusType(maintenanceInfo.status)">
                  {{ maintenanceInfo.status_label || maintenanceInfo.status }}
                </el-tag>
                <el-tag>{{ getMaintTypeText(maintenanceInfo.maint_type) }}</el-tag>
                <el-tag type="primary" v-if="maintenanceInfo.current_owner">{{ maintenanceInfo.current_owner }}</el-tag>
              </div>
            </div>
          </template>

          <!-- 维修单号（点击打开编辑） -->
          <div class="maint-header-row">
            <span class="maint-label">{{ t('maintNo') }}:</span>
            <a v-if="fault.status !== 'closed'" class="maint-link-clickable" @click="openMaintEditDialog">
              {{ maintenanceInfo.maint_no }}
              <el-icon class="edit-icon"><Edit /></el-icon>
            </a>
            <span v-else class="maint-link-disabled">{{ maintenanceInfo.maint_no }}</span>
          </div>

          <!-- 成本信息 -->
          <div class="cost-info-grid">
            <div class="cost-item">
              <span class="cost-label">{{ t('maintLaborHours') }}</span>
              <span class="cost-value">{{ maintenanceInfo.labor_hours || 0 }} {{ t('maintDetailHoursUnit') }}</span>
            </div>
            <div class="cost-item">
              <span class="cost-label">{{ t('maintLaborCost') }}</span>
              <span class="cost-value">{{ formatCurrency(maintenanceInfo.labor_cost || 0) }}</span>
            </div>
            <div class="cost-item">
              <span class="cost-label">{{ t('maintPartsCost') }}</span>
              <span class="cost-value warning">{{ formatCurrency(maintenanceInfo.parts_cost || 0) }}</span>
            </div>
            <div class="cost-item total">
              <span class="cost-label">{{ t('maintTotalCost') }}</span>
              <span class="cost-value highlight">{{ formatCurrency((maintenanceInfo.parts_cost || 0) + (maintenanceInfo.labor_cost || 0)) }}</span>
            </div>
          </div>

          <!-- 备件列表 -->
          <div class="spare-parts-section" v-if="maintenanceInfo.spare_parts_list && maintenanceInfo.spare_parts_list.length > 0">
            <div class="section-title">
              <el-icon><Box /></el-icon>
              {{ t('maintDetailSpareInfo') }}
            </div>
            <el-table :data="maintenanceInfo.spare_parts_list" size="small" border>
              <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                <template #default="{ row }"><span class="cell-primary">{{ row.serial_number || '-' }}</span></template>
              </el-table-column>
              <el-table-column prop="part_number" :label="t('maintColModel')" width="120" />
              <el-table-column prop="name" :label="t('maintColName')" width="150" />
              <el-table-column prop="quantity" :label="t('maintColQuantity')" width="60" />
              <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="80">
                <template #default="{ row }"><span class="cell-success">{{ formatCurrency(row.unit_price) }}</span></template>
              </el-table-column>
            </el-table>
          </div>
          <div class="empty-section" v-else>
            <el-tag type="info" size="small">{{ t('maintDetailNoSpare') }}</el-tag>
          </div>

          <!-- 返回件列表 -->
          <div class="return-parts-section" v-if="maintenanceInfo.return_parts_list && maintenanceInfo.return_parts_list.length > 0">
            <div class="section-title">
              <el-icon><RefreshRight /></el-icon>
              {{ t('maintDetailReturnInfo') }}
            </div>
            <el-table :data="maintenanceInfo.return_parts_list" size="small" border>
              <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="120">
                <template #default="{ row }"><span class="cell-primary">{{ row.serial_number || '-' }}</span></template>
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
          </div>
          <div class="empty-section" v-else>
            <el-tag type="info" size="small">{{ t('maintDetailNoReturn') }}</el-tag>
          </div>

          <!-- 维修描述 -->
          <div class="description-section" v-if="maintenanceInfo.description">
            <div class="section-title">
              <el-icon><Document /></el-icon>
              {{ t('maintDescription') }}
            </div>
            <p class="description-text">{{ maintenanceInfo.description }}</p>
          </div>

          <!-- 操作按钮 -->
          <div class="maint-actions">
            <el-button v-if="fault.status !== 'closed'" type="primary" @click="openMaintEditDialog">
              <el-icon><Edit /></el-icon>
              {{ t('faultEditMaintenance') }}
            </el-button>
            <el-button v-if="maintenanceInfo.status === 'repairing' && fault.status !== 'closed'" type="warning" @click="submitMaintVerification">
              <el-icon><CircleCheck /></el-icon>
              {{ t('maintSubmitVerification') }}
            </el-button>
            <el-button v-if="maintenanceInfo.status === 'verifying' && fault.status !== 'closed'" type="success" @click="verifyMaintPass">
              <el-icon><SuccessFilled /></el-icon>
              {{ t('maintVerifyPass') }}
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：时间线 + 设备信息 -->
      <el-col :span="8">
        <el-card class="timeline-card">
          <template #header>
            <span>{{ t('faultDetailTimeline') }}</span>
          </template>

          <el-timeline>
            <el-timeline-item
              :timestamp="formatDateTime(fault.created_at)"
              placement="top"
              color="#409EFF"
            >
              <el-card>
                <h4>{{ t('faultDetailFaultOccur') }}</h4>
                <p>{{ t('faultReporter') }}：{{ fault.reporter || 'Web' }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.assigned_at"
              :timestamp="formatDateTime(fault.assigned_at)"
              placement="top"
              color="#909399"
            >
              <el-card>
                <h4>{{ t('faultStatusAssigned') }}</h4>
                <p>{{ t('faultAssignedTo') }}：{{ fault.assigned_to }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.accepted_at"
              :timestamp="formatDateTime(fault.accepted_at)"
              placement="top"
              color="#67C23A"
            >
              <el-card>
                <h4>{{ t('faultStatusAccepted') }}</h4>
                <p>{{ t('faultAcceptedBy') }}：{{ fault.assigned_to }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.diagnosing_at"
              :timestamp="formatDateTime(fault.diagnosing_at)"
              placement="top"
              color="#E6A23C"
            >
              <el-card>
                <h4>{{ t('faultStatusDiagnosing') }}</h4>
                <p>{{ t('faultDiagnosisStarted') }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.transferred_at"
              :timestamp="formatDateTime(fault.transferred_at)"
              placement="top"
              color="#F56C6C"
            >
              <el-card>
                <h4>{{ t('faultStatusTransferred') }}</h4>
                <p>{{ t('faultTransferToMaintenance') }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.resolved_at"
              :timestamp="formatDateTime(fault.resolved_at)"
              placement="top"
              color="#67C23A"
            >
              <el-card>
                <h4>{{ t('faultStatusResolved') }}</h4>
                <p>{{ t('faultDetailFaultResolved') }}</p>
              </el-card>
            </el-timeline-item>
            <el-timeline-item
              v-if="fault.closed_at"
              :timestamp="formatDateTime(fault.closed_at)"
              placement="top"
              color="#909399"
            >
              <el-card>
                <h4>{{ t('faultStatusClosed') }}</h4>
                <p>{{ t('faultDetailRecordArchived') }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- 设备快速信息 -->
        <el-card class="device-quick-info" style="margin-top: 20px" v-if="device">
          <template #header>
            <span>{{ t('faultDetailDeviceInfo') }}</span>
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

    <!-- 指派负责人对话框 -->
    <el-dialog v-model="showAssignDialog" :title="t('faultAssignTo')" width="400px">
      <el-form :model="assignForm" label-width="100px">
        <el-form-item :label="t('faultAssignTo')" required>
          <el-select v-model="assignForm.assigned_to" :placeholder="t('faultAssignPlaceholder')" filterable clearable>
            <el-option v-for="user in users" :key="user.id" :label="user.full_name || user.username" :value="user.username" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAssignDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="assignFault">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 技术处理/解决对话框 -->
    <el-dialog v-model="showResolveDialog" :title="t('faultTechResolve')" width="500px">
      <el-form :model="resolveForm" label-width="100px">
        <el-form-item :label="t('faultResolution')" required>
          <el-input
            v-model="resolveForm.resolution"
            type="textarea"
            :rows="4"
            :placeholder="t('faultResolutionPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResolveDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitResolution">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 转维修对话框 -->
    <el-dialog v-model="showTransferDialog" :title="t('faultTransferMaintenance')" width="600px">
      <el-form :model="transferForm" label-width="120px">
        <el-form-item :label="t('faultDiagnosisContent')">
          <el-input v-model="transferForm.diagnosis_text" type="textarea" :rows="3" :placeholder="t('faultDiagnosisPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('maintDescription')">
          <el-input v-model="transferForm.maintenance_description" type="textarea" :rows="3" :placeholder="t('maintDescriptionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('faultMaintenanceOwner')">
          <el-select v-model="transferForm.maintenance_owner" :placeholder="t('faultMaintenanceOwnerPlaceholder')" filterable clearable>
            <el-option :label="`${t('faultDefaultInherit')} (${fault.assigned_to || '-'})`" value="" />
            <el-option v-for="user in users" :key="user.id" :label="user.full_name || user.username" :value="user.username" />
          </el-select>
          <div class="form-tip">{{ t('faultMaintenanceOwnerTip') }}</div>
        </el-form-item>
        <el-form-item :label="t('faultEstimateParts')">
          <el-input v-model="transferForm.estimated_parts" :placeholder="t('faultEstimatePartsPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTransferDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="warning" @click="transferToMaintenance">{{ t('faultTransferConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 编辑故障对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('faultEditRecord')" width="600px">
      <el-form :model="editForm" label-width="120px">
        <el-form-item :label="t('faultLevel')" required>
          <el-select v-model="editForm.severity">
            <el-option :label="`${t('dashCritical')} (Critical)`" value="critical" />
            <el-option :label="`${t('dashMajor')} (Major)`" value="major" />
            <el-option :label="`${t('dashMinor')} (Minor)`" value="minor" />
            <el-option :label="`${t('dashWarning')} (Warning)`" value="warning" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('faultType')">
          <el-select v-model="editForm.fault_type" clearable>
            <el-option :label="t('faultTypeHardware')" value="hardware" />
            <el-option :label="t('faultTypeSoftware')" value="software" />
            <el-option :label="t('faultTypeConfig')" value="config" />
            <el-option :label="t('faultTypeNetwork')" value="network" />
            <el-option :label="t('faultTypeOther')" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('faultDowntimeMinutes')">
          <el-input-number v-model="editForm.downtime_minutes" :min="0" />
        </el-form-item>
        <el-form-item :label="t('faultImpact')">
          <el-input v-model="editForm.impact" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('faultDescription')" required>
          <el-input v-model="editForm.description" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="updateFaultSubmit">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 维修编辑对话框 -->
    <el-dialog v-model="showMaintEditDialog" :title="t('maintDetailEdit')" width="950px" class="maint-edit-dialog">
      <div class="maint-edit-content">
        <!-- 备件更换 Section -->
        <div class="edit-section">
          <div class="section-title">
            <el-icon><Box /></el-icon>
            {{ t('maintSparePartsSection') }}
          </div>
          <!-- 扫码功能条 -->
          <div class="scan-action-bar">
            <el-button type="default" class="scan-btn" @click="openSpareScanDialog">
              <el-icon><Aim /></el-icon>
              {{ t('maintScanAddSpare') }}
            </el-button>
            <div class="scan-tip-badge">
              <el-icon><InfoFilled /></el-icon>
              {{ t('maintScanTip') }}
            </div>
          </div>
          <!-- 手动搜索添加备件 -->
          <el-select
            v-model="selectedSparePart"
            :placeholder="t('maintDetailSpareSearchPlaceholder')"
            filterable
            remote
            :remote-method="searchSparePartsForMaint"
            :loading="spareLoading"
            style="width: 320px; margin-top: 12px"
            @change="addSpareToMaintEdit"
            clearable
          >
            <el-option
              v-for="part in sparePartOptions"
              :key="part.id"
              :label="part.is_serial_match ? `${part.serial_number} - ${part.name}` : `${part.part_number} - ${part.name} (${t('maintSpareStock')}: ${part.quantity_in_stock || 0})`"
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
          <!-- 已添加的备件列表 -->
          <div v-if="maintEditForm.spare_parts.length > 0" style="margin-top: 12px">
            <el-table :data="maintEditForm.spare_parts" size="small" border>
              <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="130">
                <template #default="{ row }"><span class="cell-primary">{{ row.serial_number || '-' }}</span></template>
              </el-table-column>
              <el-table-column prop="part_number" :label="t('maintColModel')" width="120" />
              <el-table-column prop="name" :label="t('maintColName')" />
              <el-table-column prop="quantity" :label="t('maintColQuantity')" width="80">
                <template #default="{ row }">
                  <el-input-number v-model="row.quantity" :min="1" size="small" @change="updateMaintPartsCost" />
                </template>
              </el-table-column>
              <el-table-column prop="unit_price" :label="t('maintColUnitPrice')" width="90">
                <template #default="{ row }"><span class="cell-success">{{ formatCurrency(row.unit_price) }}</span></template>
              </el-table-column>
              <el-table-column :label="t('colOperation')" width="50">
                <template #default="{ $index }">
                  <el-button type="danger" size="small" link @click="removeSpareFromEdit($index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="parts-cost-sum">
              {{ t('maintSpareTotalCost') }}: <span class="cost-value warning">{{ formatCurrency(maintEditForm.parts_cost) }}</span>
            </div>
          </div>
        </div>

        <!-- 返回件入库 Section -->
        <div class="edit-section">
          <div class="section-title">
            <el-icon><RefreshRight /></el-icon>
            {{ t('maintReturnPartsSection') }}
          </div>
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
          <div class="return-manual-query" style="margin-top: 12px">
            <el-input
              v-model="returnPartSerial"
              :placeholder="t('maintDetailReturnManualPlaceholder')"
              style="width: 200px"
              @keyup.enter="queryReturnPart"
              clearable
            >
              <template #prefix><el-icon><Aim /></el-icon></template>
            </el-input>
            <el-button type="default" size="small" @click="queryReturnPart" :loading="returnLoading">
              {{ t('spareQuery') }}
            </el-button>
          </div>
          <!-- 扫码识别结果 -->
          <div v-if="returnFoundPart" class="return-found-info">
            <el-card size="small" shadow="never">
              <div class="found-header">
                <el-tag type="success" size="small">{{ t('maintReturnFoundTag') }}</el-tag>
                <span class="serial-text">{{ returnFoundPart.serial_number }}</span>
              </div>
              <el-descriptions :column="3" size="small" border>
                <el-descriptions-item :label="t('maintColModel')">{{ returnFoundPart.part_number || '-' }}</el-descriptions-item>
                <el-descriptions-item :label="t('maintColName')">{{ returnFoundPart.name }}</el-descriptions-item>
                <el-descriptions-item :label="t('maintColUnitPrice')">{{ formatCurrency(returnFoundPart.unit_price) }}</el-descriptions-item>
              </el-descriptions>
              <div class="found-actions">
                <el-input-number v-model="returnQty" :min="1" size="small" style="width: 80px" />
                <el-checkbox v-model="returnScrap">{{ t('maintReturnScrapLabel') }}</el-checkbox>
                <el-button type="primary" size="small" @click="addReturnToEdit">{{ t('maintReturnAddToList') }}</el-button>
                <el-button size="small" @click="clearReturnFound">{{ t('actionReset') }}</el-button>
              </div>
            </el-card>
          </div>
          <!-- 手动添加返回件（未识别时） -->
          <div v-if="!returnFoundPart && returnPartSerial && returnNotFound" class="return-manual-add">
            <div class="manual-add-row">
              <el-input v-model="returnManualPartNumber" :placeholder="t('maintReturnModelManual')" style="width: 130px" />
              <el-input v-model="returnManualName" :placeholder="t('maintReturnNameDefault')" style="width: 150px" />
              <el-input-number v-model="returnQty" :min="1" size="small" style="width: 80px" />
              <el-checkbox v-model="returnScrap">{{ t('maintReturnScrapLabel') }}</el-checkbox>
              <el-button type="primary" size="small" @click="addManualReturn">{{ t('actionAdd') }}</el-button>
            </div>
            <div class="manual-tip">{{ t('maintReturnNotFoundTip') }}</div>
          </div>
          <!-- 已添加的返回件列表 -->
          <div v-if="maintEditForm.return_parts.length > 0" style="margin-top: 12px">
            <el-table :data="maintEditForm.return_parts" size="small" border>
              <el-table-column prop="serial_number" :label="t('maintColSerialNumber')" width="130">
                <template #default="{ row }"><span class="cell-primary">{{ row.serial_number || '-' }}</span></template>
              </el-table-column>
              <el-table-column prop="part_number" :label="t('maintColModel')" width="120" />
              <el-table-column prop="name" :label="t('maintColName')" />
              <el-table-column :label="t('maintDetailReturnScrapIn')" width="100">
                <template #default="{ row }">
                  <el-checkbox v-model="row.scrap_in" size="small" />
                </template>
              </el-table-column>
              <el-table-column :label="t('colOperation')" width="50">
                <template #default="{ $index }">
                  <el-button type="danger" size="small" link @click="removeReturnFromEdit($index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <!-- 工时成本 Section -->
        <div class="edit-section">
          <div class="section-title">
            <el-icon><Coin /></el-icon>
            {{ t('maintCostDescSection') }}
          </div>
          <el-form :model="maintEditForm" label-width="80px">
            <el-row :gutter="20">
              <el-col :span="6">
                <el-form-item :label="t('maintLaborHours')">
                  <el-input-number v-model="maintEditForm.labor_hours" :min="0" :precision="1" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="6">
                <el-form-item :label="t('maintLaborCost')">
                  <el-input-number v-model="maintEditForm.labor_cost" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item :label="t('maintDesc')">
              <el-input v-model="maintEditForm.description" type="textarea" :rows="2" />
            </el-form-item>
          </el-form>
        </div>
      </div>
      <template #footer>
        <el-button @click="showMaintEditDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="saveMaintEdit" :loading="savingMaint">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 扫码添加备件对话框 -->
    <el-dialog v-model="showSpareScanDialog" :title="t('maintScanSpareDialog')" width="800px">
      <ScanSession
        ref="spareScanSessionRef"
        default-type="out"
        :device-id="fault?.device_id"
        :auto-start="showSpareScanDialog"
        :reference="maintenanceInfo?.maint_no"
        @complete="onSpareScanComplete"
        @cancel="showSpareScanDialog = false"
      />
    </el-dialog>

    <!-- 扫码添加返回件对话框 -->
    <el-dialog v-model="showReturnScanDialog" :title="t('maintDetailScanReturnDialog')" width="800px">
      <ScanSession
        ref="returnScanSessionRef"
        default-type="return"
        :device-id="fault?.device_id"
        :auto-start="showReturnScanDialog"
        :reference="maintenanceInfo?.maint_no"
        @complete="onReturnScanComplete"
        @cancel="showReturnScanDialog = false"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Tools, UserFilled, Select, Search, Document, CircleCheck, Lock, Check, Edit, Delete, Right, Plus, Box, RefreshRight, Coin, SuccessFilled, Aim, InfoFilled, ArrowLeft } from '@element-plus/icons-vue'
import {
  getFaultDetail,
  updateFault as updateFaultApi,
  deleteFault as deleteFaultApi,
  getDevices,
  convertFaultToMaintenance,
  getFaultMaintenance,
  getFaultTransitions,
  assignFault,
  acceptFault,
  diagnoseFault,
  transferFaultToMaintenance,
  resolveFault,
  closeFault as closeFaultApi,
  getUsers,
  updateMaintenance
} from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import api from '@/api/request'
import ScanSession from '@/components/ScanSession.vue'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()

const fault = ref({})
const device = ref(null)
const loading = ref(false)
const users = ref([])
const validTransitions = ref([])
const maintenanceInfo = ref(null)

// 对话框状态
const showAssignDialog = ref(false)
const showResolveDialog = ref(false)
const showTransferDialog = ref(false)
const showEditDialog = ref(false)
const showMaintEditDialog = ref(false)  // 维修编辑对话框

// 表单
const assignForm = ref({ assigned_to: '' })
const resolveForm = ref({ resolution: '' })
const transferForm = ref({ diagnosis_text: '', maintenance_description: '', estimated_parts: '', maintenance_owner: '' })
const diagnosisForm = ref({ diagnosis_result: 'tech_resolve', diagnosis_text: '' })
const editForm = ref({
  severity: 'major',
  fault_type: '',
  downtime_minutes: 0,
  impact: '',
  description: ''
})

// 维修编辑相关
const maintEditForm = ref({
  spare_parts: [],
  return_parts: [],
  parts_cost: 0,
  labor_hours: 0,
  labor_cost: 0,
  description: ''
})
const selectedSparePart = ref(null)
const sparePartOptions = ref([])
const spareLoading = ref(false)
const returnPartSerial = ref('')
const returnLoading = ref(false)
const returnFoundPart = ref(null)
const returnQty = ref(1)
const returnScrap = ref(true)
const savingMaint = ref(false)
const returnNotFound = ref(false)
const returnManualPartNumber = ref('')
const returnManualName = ref('')
// 扫码对话框
const showSpareScanDialog = ref(false)
const showReturnScanDialog = ref(false)
const spareScanSessionRef = ref(null)
const returnScanSessionRef = ref(null)

// 工作日志相关（ServiceNow Notes风格）
const newNoteContent = ref('')
const workNotes = ref([])

// 初始化工作日志（从故障记录中提取）
const initWorkNotes = (faultData) => {
  workNotes.value = []
  // 创建记录
  if (faultData.created_at) {
    workNotes.value.push({
      author: faultData.reporter || 'System',
      content: `故障创建：${faultData.description || '无描述'}`,
      created_at: faultData.created_at,
      note_type: 'created'
    })
  }
  // 指派记录
  if (faultData.assigned_at) {
    workNotes.value.push({
      author: 'System',
      content: `故障已指派给 ${faultData.assigned_to}`,
      created_at: faultData.assigned_at,
      note_type: 'assigned'
    })
  }
  // 开始诊断记录
  if (faultData.diagnosing_at) {
    workNotes.value.push({
      author: faultData.assigned_to,
      content: '开始诊断处理',
      created_at: faultData.diagnosing_at,
      note_type: 'diagnosing'
    })
  }
  // 诊断内容（如果有）- 解析多条日志
  if (faultData.diagnosis_text) {
    // 检查是否有多条日志（用 "--- YYYY-MM-DD HH:MM ---" 分隔）
    const notePattern = /--- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) ---\n(.+)/g
    const parts = faultData.diagnosis_text.split(/\n\n--- \d{4}-\d{2}-\d{2} \d{2}:\d{2} ---\n/)

    if (parts.length > 1) {
      // 多条日志格式：第一条是原始诊断内容，后面是追加的日志
      // 第一条
      workNotes.value.push({
        author: faultData.assigned_to,
        content: parts[0].trim(),
        created_at: faultData.diagnosing_at || faultData.updated_at,
        note_type: 'diagnosis'
      })
      // 解析后续日志
      const matches = faultData.diagnosis_text.matchAll(notePattern)
      for (const match of matches) {
        workNotes.value.push({
          author: faultData.assigned_to || 'Web',
          content: match[2].trim(),
          created_at: new Date(match[1]).toISOString(),
          note_type: 'diagnosis'
        })
      }
    } else {
      // 单条日志
      workNotes.value.push({
        author: faultData.assigned_to,
        content: faultData.diagnosis_text,
        created_at: faultData.diagnosing_at || faultData.updated_at,
        note_type: 'diagnosis'
      })
    }
  }
  // 转维修记录
  if (faultData.transferred_at) {
    workNotes.value.push({
      author: faultData.assigned_to,
      content: '故障已转维修处理',
      created_at: faultData.transferred_at,
      note_type: 'transferred'
    })
  }
  // 解决记录
  if (faultData.resolved_at && faultData.resolution) {
    workNotes.value.push({
      author: faultData.assigned_to,
      content: `故障解决：${faultData.resolution}`,
      created_at: faultData.resolved_at,
      note_type: 'resolved'
    })
  }
  // 关闭记录
  if (faultData.closed_at) {
    workNotes.value.push({
      author: faultData.assigned_to || 'System',
      content: '故障已关闭',
      created_at: faultData.closed_at,
      note_type: 'closed'
    })
  }
  // 按时间排序
  workNotes.value.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
}

// 日志类型颜色
const getNoteTypeColor = (type) => {
  const colors = {
    created: 'info',
    assigned: 'primary',
    diagnosing: 'warning',
    diagnosis: '',
    transferred: 'success',
    resolved: 'success',
    closed: 'info'
  }
  return colors[type] || ''
}

// 日志类型标签
const getNoteTypeLabel = (type) => {
  const labels = {
    created: '创建',
    assigned: '指派',
    diagnosing: '开始诊断',
    diagnosis: '诊断',
    transferred: '转维修',
    resolved: '解决',
    closed: '关闭'
  }
  return labels[type] || ''
}

// 仅添加日志（不改变状态）
const submitNoteOnly = async () => {
  if (!newNoteContent.value) return
  try {
    // 调用新的工作日志API
    const result = await api.post(`/faults/${fault.value.id}/work-note`, {
      note: newNoteContent.value
    })
    // 添加到本地日志
    workNotes.value.unshift({
      author: localStorage.getItem('currentUser') || fault.value.assigned_to || 'Web',
      content: newNoteContent.value,
      created_at: new Date().toISOString(),
      note_type: 'diagnosis'
    })
    newNoteContent.value = ''
    ElMessage.success(t('faultNoteAdded'))
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    ElMessage.error(t('faultNoteFailed') + ': ' + detail)
  }
}

// 添加日志并技术解决
const submitNoteAndResolve = async () => {
  try {
    // 如果有日志内容，先保存诊断内容
    if (newNoteContent.value) {
      await diagnoseFault(fault.value.id, { diagnosis_text: newNoteContent.value })
      // 添加日志
      workNotes.value.push({
        author: localStorage.getItem('currentUser') || fault.value.assigned_to,
        content: newNoteContent.value,
        created_at: new Date().toISOString(),
        note_type: 'diagnosis'
      })
    }
    // 解决故障（直接打开解决对话框）
    showResolveDialog.value = true
  } catch (e) {
    ElMessage.error(t('faultResolveFailed'))
  }
}

// 添加日志并转维修
const submitNoteAndTransfer = async () => {
  // 如果有日志内容，保存到转维修表单
  if (newNoteContent.value) {
    transferForm.value.diagnosis_text = newNoteContent.value
  }
  // 打开转维修对话框
  showTransferDialog.value = true
}

// 状态步骤定义
const statusSteps = computed(() => [
  { key: 'open', label: t('faultStatusOpen') },
  { key: 'assigned', label: t('faultStatusAssigned') },
  { key: 'accepted', label: t('faultStatusAccepted') },
  { key: 'diagnosing', label: t('faultStatusDiagnosing') },
  { key: 'resolved', label: t('faultStatusResolved') },
  { key: 'closed', label: t('faultStatusClosed') }
])

// 判断步骤是否完成
const isStepCompleted = (stepKey) => {
  const statusOrder = ['open', 'assigned', 'accepted', 'diagnosing', 'resolving', 'transferred', 'resolved', 'closed']
  const currentIdx = statusOrder.indexOf(fault.value.status)
  const stepIdx = statusOrder.indexOf(stepKey)
  // 特殊处理：transferred 也算诊断完成
  if (stepKey === 'diagnosing' && (fault.value.status === 'transferred' || fault.value.status === 'resolving')) {
    return true
  }
  return stepIdx < currentIdx
}

// 判断是否可以转换到某状态
const canTransition = (targetStatus) => {
  return validTransitions.value.includes(targetStatus)
}

// 判断是否可以编辑（只有接收后才可编辑）
const canEdit = computed(() => {
  const editableStates = ['accepted', 'diagnosing', 'resolving', 'transferred', 'resolved']
  return editableStates.includes(fault.value.status)
})

const getSeverityType = (severity) => {
  const types = { critical: 'danger', major: 'warning', minor: '', warning: 'info' }
  return types[severity] || 'info'
}

const getSeverityText = (severity) => {
  const keys = { critical: 'dashCritical', major: 'dashMajor', minor: 'dashMinor', warning: 'dashWarning' }
  return t(keys[severity]) || severity
}

const getStatusType = (status) => {
  const types = {
    open: 'info',
    assigned: 'primary',
    accepted: 'success',
    diagnosing: 'warning',
    resolving: 'info',
    transferred: 'warning',
    resolved: 'success',
    closed: 'info',
    investigating: 'warning'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const keys = {
    open: 'faultStatusOpen',
    assigned: 'faultStatusAssigned',
    accepted: 'faultStatusAccepted',
    diagnosing: 'faultStatusDiagnosing',
    resolving: 'faultStatusResolving',
    transferred: 'faultStatusTransferred',
    resolved: 'faultStatusResolved',
    closed: 'faultStatusClosed',
    investigating: 'faultStatusInvestigating'
  }
  return t(keys[status]) || status
}

const getFaultTypeText = (type) => {
  const keys = { hardware: 'faultTypeHardware', software: 'faultTypeSoftware', config: 'faultTypeConfig', network: 'faultTypeNetwork', other: 'faultTypeOther' }
  return t(keys[type]) || type
}

const getMaintTypeText = (type) => {
  const keys = { preventive: 'maintTypePreventive', corrective: 'maintTypeCorrective', upgrade: 'maintTypeUpgrade', emergency: 'maintTypeEmergency' }
  return t(keys[type]) || type
}

const getMaintStatusType = (status) => {
  const types = { created: 'info', in_progress: 'warning', completed: 'success', verified: 'success' }
  return types[status] || 'info'
}

const getMaintProgressStep = (status) => {
  const steps = { created: 1, repairing: 2, verifying: 3, completed: 4 }
  return steps[status] || 0
}

// 维修编辑相关方法
const formatCurrency = (value) => {
  const num = value || 0
  return `¥${num.toFixed(2)}`
}

const openMaintEditDialog = async () => {
  if (!maintenanceInfo.value) return
  if (fault.value.status === 'closed') {
    ElMessage.warning('故障已关闭，无法编辑维修单')
    return
  }

  // 从 maintenanceInfo 初始化编辑表单
  maintEditForm.value = {
    spare_parts: maintenanceInfo.value.spare_parts_list || [],
    return_parts: maintenanceInfo.value.return_parts_list || [],
    parts_cost: maintenanceInfo.value.parts_cost || 0,
    labor_hours: maintenanceInfo.value.labor_hours || 0,
    labor_cost: maintenanceInfo.value.labor_cost || 0,
    description: maintenanceInfo.value.description || ''
  }

  selectedSparePart.value = null
  sparePartOptions.value = []
  returnPartSerial.value = ''
  returnFoundPart.value = null
  showMaintEditDialog.value = true
}

const searchSparePartsForMaint = async (query) => {
  if (!query || query.length < 1) {
    sparePartOptions.value = []
    return
  }
  spareLoading.value = true
  try {
    const result = await api.get('/spare-parts/search-in-stock', { params: { keyword: query } })
    sparePartOptions.value = (result.items || []).map(item => ({
      id: item.instance_id || item.id,
      part_id: item.id,
      part_number: item.part_number,
      name: item.name,
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      is_serial_match: true
    }))
  } catch (e) {
    console.error('Spare parts search failed:', e)
    sparePartOptions.value = []
  } finally {
    spareLoading.value = false
  }
}

const addSpareToMaintEdit = () => {
  if (!selectedSparePart.value) return
  const part = sparePartOptions.value.find(p => p.id === selectedSparePart.value)
  if (!part) return

  // 检查是否已存在
  const existing = maintEditForm.value.spare_parts.find(p => p.serial_number === part.serial_number)
  if (existing) {
    ElMessage.warning(t('maintSerialAlreadyInList'))
    selectedSparePart.value = null
    return
  }

  maintEditForm.value.spare_parts.push({
    part_id: part.part_id,  // 使用备件型号 ID（SparePart.id），不是实例 ID
    instance_id: part.id,   // 备件实例 ID（如果有）
    part_number: part.part_number,
    name: part.name,
    serial_number: part.serial_number,
    unit_price: part.unit_price,
    quantity: 1
  })

  // 更新成本
  maintEditForm.value.parts_cost = maintEditForm.value.spare_parts.reduce((sum, p) => sum + (p.quantity || 1) * (p.unit_price || 0), 0)
  selectedSparePart.value = null
}

const removeSpareFromEdit = (index) => {
  maintEditForm.value.spare_parts.splice(index, 1)
  maintEditForm.value.parts_cost = maintEditForm.value.spare_parts.reduce((sum, p) => sum + (p.quantity || 1) * (p.unit_price || 0), 0)
}

const queryReturnPart = async () => {
  const serial = returnPartSerial.value.trim()
  if (!serial) return
  returnLoading.value = true
  returnNotFound.value = false
  try {
    const result = await api.get(`/spare-parts/by-serial/${serial}`)
    returnFoundPart.value = result
    returnNotFound.value = false
    returnQty.value = 1
    returnScrap.value = true
    returnManualPartNumber.value = result.part_number || ''
    returnManualName.value = result.name || ''
  } catch (e) {
    // 未找到，显示手动添加区域
    returnFoundPart.value = null
    returnNotFound.value = true
    returnManualPartNumber.value = ''
    returnManualName.value = serial
    ElMessage.info(t('maintSerialNotFound'))
  } finally {
    returnLoading.value = false
  }
}

const addReturnToEdit = () => {
  if (!returnFoundPart.value) return

  // 检查是否已存在
  const existing = maintEditForm.value.return_parts.find(p => p.serial_number === returnFoundPart.value.serial_number)
  if (existing) {
    ElMessage.warning(t('maintSerialAlreadyInList'))
    return
  }

  maintEditForm.value.return_parts.push({
    part_id: returnFoundPart.value.part_id || returnFoundPart.value.id,
    part_number: returnFoundPart.value.part_number || '',
    name: returnFoundPart.value.name,
    serial_number: returnFoundPart.value.serial_number,
    quantity: returnQty.value,
    scrap_in: returnScrap.value
  })

  returnFoundPart.value = null
  returnPartSerial.value = ''
  returnNotFound.value = false
}

const clearReturnFound = () => {
  returnFoundPart.value = null
  returnPartSerial.value = ''
  returnNotFound.value = false
  returnManualPartNumber.value = ''
  returnManualName.value = ''
}

const addManualReturn = () => {
  if (!returnPartSerial.value) {
    ElMessage.warning(t('maintEnterSerial'))
    return
  }

  // 检查是否已存在
  const existing = maintEditForm.value.return_parts.find(p => p.serial_number === returnPartSerial.value)
  if (existing) {
    ElMessage.warning(t('maintSerialAlreadyInList'))
    return
  }

  maintEditForm.value.return_parts.push({
    part_id: null,
    part_number: returnManualPartNumber.value || '',
    name: returnManualName.value || returnPartSerial.value,
    serial_number: returnPartSerial.value,
    quantity: returnQty.value,
    scrap_in: returnScrap.value
  })

  ElMessage.success(t('maintReturnPartAddedNoMatch'))
  clearReturnFound()
}

const updateMaintPartsCost = () => {
  maintEditForm.value.parts_cost = maintEditForm.value.spare_parts.reduce(
    (sum, p) => sum + (p.quantity || 1) * (p.unit_price || 0), 0
  )
}

// 扫码对话框方法
const openSpareScanDialog = () => {
  showSpareScanDialog.value = true
}

const openReturnScanDialog = () => {
  showReturnScanDialog.value = true
}

const onSpareScanComplete = async (result) => {
  // 将扫描的备件加入编辑表单（已在扫码会话中自动出库）
  for (const item of result.items) {
    const existing = maintEditForm.value.spare_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      existing.quantity += 1
      ElMessage.info(t('maintQuantityPlusOne', { name: item.name }))
    } else {
      maintEditForm.value.spare_parts.push({
        part_id: item.part_id,
        part_number: item.part_number,
        name: item.name,
        serial_number: item.serial_number,
        unit_price: item.unit_price || 0,
        quantity: 1,
        is_from_scan: true  // 标记为扫码添加
      })
      ElMessage.success(t('maintPartAdded', { name: item.name }))
    }
  }
  updateMaintPartsCost()
  showSpareScanDialog.value = false
  ElMessage.success(t('maintPartsAdded', { count: result.items.length }))
}

const onReturnScanComplete = async (result) => {
  // 将扫描的返回件加入编辑表单（返回件扫码不会自动入库）
  for (const item of result.items) {
    const existing = maintEditForm.value.return_parts.find(p => p.serial_number === item.serial_number)
    if (existing) {
      ElMessage.warning(t('maintSerialAlreadyInList', { sn: item.serial_number }))
      continue
    }
    maintEditForm.value.return_parts.push({
      part_id: item.part_id,
      part_number: item.part_number,
      name: item.name,
      serial_number: item.serial_number,
      unit_price: item.unit_price || 0,
      quantity: 1,
      scrap_in: item.part_id ? true : false,  // 有备件ID默认入报废库
      is_from_scan: true
    })
    ElMessage.success(t('maintReturnPartAdded', { sn: item.serial_number }))
  }
  showReturnScanDialog.value = false
}

const saveMaintEdit = async () => {
  if (!maintenanceInfo.value?.id) {
    ElMessage.error(t('maintUpdateFailed') + ': 维修单ID不存在')
    return
  }
  savingMaint.value = true
  try {
    // 合并备件和返回件
    const combinedParts = [
      ...maintEditForm.value.spare_parts.map(p => ({ ...p, is_return: false })),
      ...maintEditForm.value.return_parts.map(p => ({ ...p, is_return: true }))
    ]

    const updateData = {
      parts_replaced: JSON.stringify(combinedParts),
      parts_cost: maintEditForm.value.parts_cost,
      labor_hours: maintEditForm.value.labor_hours,
      labor_cost: maintEditForm.value.labor_cost,
      description: maintEditForm.value.description
    }

    await updateMaintenance(maintenanceInfo.value.id, updateData)

    // 处理备件出库（如果需要）
    const outErrors = []
    for (const part of maintEditForm.value.spare_parts) {
      if (part.part_id && !part.is_from_scan) {
        try {
          await api.post('/spare-movements/', {
            part_id: part.part_id,
            movement_type: 'out',
            quantity: part.quantity || 1,
            serial_number: part.serial_number,
            reason: `维修出库 - ${maintenanceInfo.value.maint_no}`,
            operator: 'Web',
            reference: maintenanceInfo.value.maint_no,
            target_device_id: fault.value.device_id
          })
        } catch (spareError) {
          const errMsg = spareError.response?.data?.detail || spareError.message
          outErrors.push(`备件 ${part.serial_number}: ${errMsg}`)
        }
      }
    }

    // 处理返回件入报废库（如果需要）
    const returnErrors = []
    for (const part of maintEditForm.value.return_parts) {
      if (part.part_id && part.scrap_in) {
        try {
          await api.post('/spare-movements/', {
            part_id: part.part_id,
            movement_type: 'scrap_in',
            quantity: part.quantity,
            serial_number: part.serial_number,
            reason: '返回件入报废库',
            operator: 'Web',
            reference: maintenanceInfo.value.maint_no,
            source_device_id: fault.value.device_id
          })
        } catch (returnError) {
          const errMsg = returnError.response?.data?.detail || returnError.message
          returnErrors.push(`返回件 ${part.serial_number}: ${errMsg}`)
        }
      }
    }

    // 显示结果
    if (outErrors.length > 0 || returnErrors.length > 0) {
      ElMessage.warning(t('maintRecordUpdated') + '，但部分库存操作失败：\n' + [...outErrors, ...returnErrors].join('\n'))
    } else {
      ElMessage.success(t('maintRecordUpdated'))
    }

    showMaintEditDialog.value = false
    loadMaintenanceInfo()
  } catch (e) {
    const detail = e.response?.data?.detail || e.message
    ElMessage.error(t('maintUpdateFailed') + ': ' + detail)
  } finally {
    savingMaint.value = false
  }
}

const submitMaintVerification = async () => {
  try {
    await ElMessageBox.confirm(t('maintSubmitConfirm'), t('msgConfirm'), { type: 'info' })
    await api.post(`/maintenance/${maintenanceInfo.value.id}/submit-verification`, { operator: 'Web' })
    ElMessage.success(t('maintSubmitted'))
    loadMaintenanceInfo()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(t('maintSubmitFailed'))
    }
  }
}

const verifyMaintPass = async () => {
  try {
    await ElMessageBox.confirm(t('maintVerifyConfirm'), t('msgConfirm'), { type: 'success' })
    await api.post(`/maintenance/${maintenanceInfo.value.id}/verify-pass`, { operator: 'Web' })
    ElMessage.success(t('maintVerified'))
    loadMaintenanceInfo()
    // 同时刷新故障数据
    loadFault()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error(t('maintVerifyFailed'))
    }
  }
}

const loadMaintenanceInfo = async () => {
  if (!fault.value.maintenance_id) return
  try {
    const result = await api.get(`/maintenance/${fault.value.maintenance_id}`)
    maintenanceInfo.value = result
    // 解析备件列表
    if (result.parts_replaced) {
      try {
        const parsed = JSON.parse(result.parts_replaced)
        maintenanceInfo.value.spare_parts_list = parsed.filter(p => !p.is_return)
        maintenanceInfo.value.return_parts_list = parsed.filter(p => p.is_return)
      } catch (e) {
        maintenanceInfo.value.spare_parts_list = []
        maintenanceInfo.value.return_parts_list = []
      }
    }
  } catch (e) {
    console.error('Failed to load maintenance info:', e)
  }
}

const goToMaintenance = () => {
  // 直接打开编辑对话框，不跳转
  openMaintEditDialog()
}

const getDiagnosisResultType = (result) => {
  const types = { tech_resolve: 'success', need_parts: 'warning', no_action: 'info' }
  return types[result] || 'info'
}

const getDiagnosisResultText = (result) => {
  const keys = { tech_resolve: 'faultDiagnosisTechResolve', need_parts: 'faultDiagnosisNeedParts', no_action: 'faultDiagnosisNoAction' }
  return t(keys[result]) || result
}

const loadFault = async () => {
  try {
    const faultId = route.params.id
    const data = await getFaultDetail(faultId)
    fault.value = data

    // 初始化诊断表单
    diagnosisForm.value = {
      diagnosis_result: data.diagnosis_result || 'tech_resolve',
      diagnosis_text: data.diagnosis_text || ''
    }

    // 初始化编辑表单
    editForm.value = {
      severity: data.severity,
      fault_type: data.fault_type || '',
      downtime_minutes: data.downtime_minutes || 0,
      impact: data.impact || '',
      description: data.description
    }

    // 初始化工作日志
    initWorkNotes(data)

    // 加载设备信息
    if (data.device_id) {
      const devices = await getDevices()
      device.value = (devices.items || []).find(d => d.id === data.device_id)
    }

    // 加载关联的维修单信息
    if (data.maintenance_id) {
      await loadMaintenanceInfo()
    }

    // 加载可转换的状态
    try {
      const transitions = await getFaultTransitions(faultId)
      // 提取 status 字段，因为 API 返回的是对象数组 [{status: 'accepted', label: '...'}, ...]
      validTransitions.value = (transitions.valid_transitions || []).map(t => t.status)
    } catch (e) {
      validTransitions.value = []
    }

    // 加载用户列表
    const usersData = await getUsers()
    users.value = Array.isArray(usersData) ? usersData : (usersData.items || [])
  } catch (error) {
    ElMessage.error(t('faultDetailLoadFailed'))
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  router.push('/faults')
}

// 指派负责人
const assignFaultSubmit = async () => {
  try {
    await assignFault(fault.value.id, assignForm.value.assigned_to)
    ElMessage.success(t('faultAssignSuccess'))
    showAssignDialog.value = false
    assignForm.value.assigned_to = ''
    loadFault()
    // 通知状态变化
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('faultAssignFailed'))
  }
}

// 接收故障
const acceptFaultSubmit = async () => {
  try {
    await acceptFault(fault.value.id)
    ElMessage.success(t('faultAcceptSuccess'))
    loadFault()
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('faultAcceptFailed'))
  }
}

// 开始诊断
const startDiagnosing = async () => {
  try {
    await diagnoseFault(fault.value.id, {})
    ElMessage.success(t('faultDiagnoseStartSuccess'))
    loadFault()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('faultDiagnoseStartFailed'))
  }
}

// 提交诊断
const submitDiagnosis = async () => {
  try {
    await diagnoseFault(fault.value.id, diagnosisForm.value)
    ElMessage.success(t('faultDiagnosisSuccess'))

    // 根据诊断结果自动进入下一步
    if (diagnosisForm.value.diagnosis_result === 'tech_resolve') {
      // 技术处理，显示解决对话框
      showResolveDialog.value = true
    } else if (diagnosisForm.value.diagnosis_result === 'need_parts') {
      // 需备件，显示转维修对话框
      transferForm.value.diagnosis_text = diagnosisForm.value.diagnosis_text
      showTransferDialog.value = true
    } else {
      // 无需处理，直接关闭
      await closeFaultApi(fault.value.id)
      ElMessage.success(t('faultCloseSuccess'))
    }
    loadFault()
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('faultDiagnosisFailed'))
  }
}

// 提交解决
const submitResolution = async () => {
  try {
    await resolveFault(fault.value.id, resolveForm.value.resolution)
    ElMessage.success(t('faultResolveSuccess'))
    showResolveDialog.value = false
    resolveForm.value.resolution = ''
    loadFault()
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('faultResolveFailed'))
  }
}

// 转维修
const transferToMaintenance = async () => {
  try {
    const result = await transferFaultToMaintenance(fault.value.id, transferForm.value)
    ElMessage.success(`${t('faultTransferSuccess')} ${result.maint_no || ''}`)
    showTransferDialog.value = false
    transferForm.value = { diagnosis_text: '', maintenance_description: '', estimated_parts: '', maintenance_owner: '' }
    loadFault()
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('faultTransferFailed'))
  }
}

// 关闭故障
const closeFaultSubmit = async () => {
  try {
    await ElMessageBox.confirm(t('faultDetailCloseConfirm'), t('faultCloseTitle'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await closeFaultApi(fault.value.id)
    ElMessage.success(t('faultCloseSuccess'))
    loadFault()
    window.dispatchEvent(new CustomEvent('fault-status-change'))
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || t('faultCloseFailed'))
    }
  }
}

// 更新故障
const updateFaultSubmit = async () => {
  try {
    await updateFaultApi(fault.value.id, editForm.value)
    ElMessage.success(t('faultUpdateSuccess'))
    showEditDialog.value = false
    loadFault()
  } catch (error) {
    ElMessage.error(t('faultUpdateFailed'))
  }
}

// 删除故障
const deleteFaultSubmit = async () => {
  try {
    await ElMessageBox.confirm(t('faultDetailDeleteConfirm'), t('msgConfirmDelete'), {
      confirmButtonText: t('actionConfirm'),
      cancelButtonText: t('actionCancel'),
      type: 'warning'
    })

    await deleteFaultApi(fault.value.id)
    ElMessage.success(t('faultDetailDeleteSuccess'))
    router.push('/faults')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('faultDetailDeleteFailed'))
    }
  }
}

// 监听刷新事件（点击通知刷新同一页面）
const handleRefresh = (event) => {
  if (event.detail && event.detail.id == route.params.id) {
    loadFault()
    ElMessage.success('数据已刷新')
  }
}

onMounted(() => {
  loadFault()
  window.addEventListener('refresh-detail', handleRefresh)
})

onUnmounted(() => {
  window.removeEventListener('refresh-detail', handleRefresh)
})
</script>

<style scoped>
.fault-detail-page {
  max-width: 1400px;
  margin: 0 auto;
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

.card-header-flex {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* 状态流转指示器 */
.status-flow-indicator {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 10px;
  margin-bottom: 20px;
}

.flow-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.step-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  background: #e4e7ed;
  color: #909399;
  transition: all 0.3s;
}

.flow-step.active .step-circle {
  background: #409EFF;
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.flow-step.completed .step-circle {
  background: #67C23A;
  color: #fff;
}

.step-label {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
}

.flow-step.active .step-label {
  color: #409EFF;
  font-weight: 500;
}

.flow-step.completed .step-label {
  color: #67C23A;
}

.step-line {
  width: 40px;
  height: 2px;
  background: #e4e7ed;
  position: absolute;
  left: calc(100% + 8px);
  top: 16px;
}

.flow-step.completed .step-line {
  background: #67C23A;
}

/* 维修中状态分支 */
.maintenance-branch {
  margin-top: 20px;
  padding: 16px;
  background: rgba(255, 184, 0, 0.08);
  border-radius: 12px;
  border: 1px dashed var(--accent-warning, #e17055);
}

.branch-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.branch-arrow {
  font-size: 18px;
  color: var(--accent-warning, #e17055);
  font-weight: bold;
}

.branch-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--accent-warning, #e17055);
}

.maintenance-status-flow {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 30px;
}

.maint-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.maint-step-circle {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  background: #f5f5f5;
  color: #999;
  border: 2px solid #ddd;
  transition: all 0.3s;
}

.maint-step.active .maint-step-circle {
  background: var(--accent-primary, #003087);
  color: #fff;
  border-color: var(--accent-primary, #003087);
  box-shadow: 0 2px 8px rgba(0, 48, 135, 0.3);
}

.maint-step.completed .maint-step-circle {
  background: var(--accent-success, #00b894);
  color: #fff;
  border-color: var(--accent-success, #00b894);
}

.maint-step-label {
  font-size: 11px;
  color: #999;
  margin-top: 6px;
}

.maint-step.active .maint-step-label {
  color: var(--accent-primary, #003087);
  font-weight: 500;
}

.maint-step.completed .maint-step-label {
  color: var(--accent-success, #00b894);
}

.maint-step-line {
  width: 30px;
  height: 2px;
  background: #ddd;
}

.maint-step-line.completed {
  background: var(--accent-success, #00b894);
}

.branch-return {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding-left: 30px;
}

.branch-return .branch-arrow {
  color: var(--accent-success, #00b894);
}

.branch-return .branch-label {
  color: var(--accent-success, #00b894);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding: 16px 0;
}

/* 玻璃渐变按钮样式 */
.glass-btn-primary {
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  border: none;
  color: white;
  border-radius: 8px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.25);
  transition: all 0.25s ease;
}

.glass-btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 184, 148, 0.35);
  background: linear-gradient(135deg, #00d9a5 0%, #6af7d4 100%);
}

.glass-btn-warning {
  background: linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%);
  border: none;
  color: white;
  border-radius: 8px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(251, 191, 36, 0.25);
  transition: all 0.25s ease;
}

.glass-btn-warning:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.35);
}

.glass-btn-success {
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  border: none;
  color: white;
  border-radius: 8px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.25);
  transition: all 0.25s ease;
}

.glass-btn-success:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0, 184, 148, 0.35);
}

.glass-btn-info {
  background: linear-gradient(135deg, #636e72 0%, #b2bec3 100%);
  border: none;
  color: white;
  border-radius: 8px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(99, 110, 114, 0.25);
  transition: all 0.25s ease;
}

.glass-btn-info:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(99, 110, 114, 0.35);
}

.glass-btn-danger {
  background: linear-gradient(135deg, #ef4444 0%, #f87171 100%);
  border: none;
  color: white;
  border-radius: 8px;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.25);
  transition: all 0.25s ease;
}

.glass-btn-danger:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(239, 68, 68, 0.35);
}

/* 诊断区域 */
.diagnosis-card {
  margin-top: 20px;
}

.diagnosis-result-display {
  padding: 10px;
}

.fault-info-card {
  min-height: 300px;
}

.description {
  line-height: 1.8;
  color: #606266;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.timeline-card {
  min-height: 300px;
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

.total-cost {
  font-weight: 600;
  color: #E6A23C;
  font-size: 16px;
}

/* 维修卡片增强样式 */
.maintenance-card-enhanced {
  margin-top: 20px;
}

.maint-header-tags {
  display: flex;
  gap: 8px;
}

.maint-header-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.maint-label {
  font-size: 14px;
  color: var(--text-secondary, #606266);
}

.maint-link-clickable {
  font-size: 16px;
  font-weight: 600;
  color: var(--accent-primary, #409EFF);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}

.maint-link-clickable:hover {
  color: var(--accent-secondary, #66b1ff);
}

.maint-link-clickable .edit-icon {
  font-size: 14px;
  opacity: 0.7;
}

.maint-link-disabled {
  font-weight: 600;
  color: var(--text-muted, #909399);
  cursor: default;
}

.cost-info-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.cost-item {
  padding: 12px;
  background: var(--bg-tertiary, #f5f7fa);
  border-radius: 8px;
  text-align: center;
}

.cost-item.total {
  background: rgba(255, 184, 0, 0.1);
}

.cost-label {
  font-size: 12px;
  color: var(--text-tertiary, #909399);
  display: block;
  margin-bottom: 4px;
}

.cost-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #303133);
  font-family: var(--font-display, monospace);
}

.cost-value.warning {
  color: var(--accent-warning, #E6A23C);
}

.cost-value.highlight {
  color: var(--accent-warning, #E6A23C);
  font-size: 18px;
}

.spare-parts-section, .return-parts-section, .description-section {
  margin-top: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #303133);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle, #EBEEF5);
}

.empty-section {
  margin-top: 12px;
}

.description-text {
  padding: 12px;
  background: var(--bg-tertiary, #f5f7fa);
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.6;
}

.maint-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle, #EBEEF5);
}

.cell-primary {
  color: var(--accent-primary, #409EFF);
  font-weight: 500;
}

.cell-success {
  color: var(--accent-success, #67C23A);
  font-weight: 500;
}

.cell-tag {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.cell-tag.success {
  background: rgba(103, 194, 58, 0.1);
  color: #67C23A;
}

.cell-tag.info {
  background: rgba(144, 147, 153, 0.1);
  color: #909399;
}

/* 维修编辑对话框样式 */
.maint-edit-dialog .maint-edit-content {
  max-width: 850px;
}

.maint-edit-dialog .edit-section {
  margin-bottom: 20px;
  padding: 16px;
  background: var(--bg-tertiary, #f5f7fa);
  border-radius: 8px;
}

.maint-edit-dialog .section-title {
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle, #EBEEF5);
}

.maint-edit-dialog .parts-cost-sum {
  margin-top: 10px;
  text-align: right;
  font-size: 14px;
}

.maint-edit-dialog .found-part-card {
  margin-top: 12px;
}

.maint-edit-dialog .found-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

/* 扫码功能条样式 */
.maint-edit-dialog .scan-action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #003087 0%, #0984e3 100%);
  border-radius: 8px;
}

.maint-edit-dialog .scan-action-bar.return {
  background: linear-gradient(135deg, #636e72 0%, #4a5455 100%);
}

.maint-edit-dialog .scan-btn {
  background: rgba(255,255,255,0.15);
  border-color: rgba(255,255,255,0.3);
  color: #fff;
  font-weight: 500;
  height: 36px;
  border-radius: 8px;
  transition: all 0.2s;
}

.maint-edit-dialog .scan-btn:hover {
  background: rgba(255,255,255,0.25);
  transform: translateY(-1px);
}

.maint-edit-dialog .scan-tip-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255,255,255,0.1);
  border-radius: 4px;
  color: rgba(255,255,255,0.9);
  font-size: 12px;
}

/* 备件下拉选项样式 */
.maint-edit-dialog .spare-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.maint-edit-dialog .spare-number {
  font-weight: 500;
  color: #409EFF;
}

.maint-edit-dialog .spare-name {
  color: #606266;
}

.maint-edit-dialog .spare-sn {
  font-size: 12px;
  color: #67C23A;
}

.maint-edit-dialog .spare-stock {
  font-size: 12px;
  color: #909399;
}

.maint-edit-dialog .spare-stock.low {
  color: #E6A23C;
}

/* 返回件查询结果样式 */
.maint-edit-dialog .return-found-info {
  margin-top: 12px;
}

.maint-edit-dialog .found-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.maint-edit-dialog .serial-text {
  font-weight: 500;
  color: #409EFF;
}

/* 返回件手动添加样式 */
.maint-edit-dialog .return-manual-add {
  margin-top: 12px;
  padding: 12px;
  background: #fdf6ec;
  border-radius: 8px;
  border: 1px dashed #e6a23c;
}

.maint-edit-dialog .manual-add-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.maint-edit-dialog .manual-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

/* 成本值样式 */
.cost-value.warning {
  color: #E6A23C;
  font-weight: 600;
}

/* 工作日志样式（ServiceNow Notes风格） */
.work-notes-card {
  margin-top: 20px;
}

.add-note-section {
  margin-bottom: 20px;
}

.add-note-section .el-textarea {
  margin-bottom: 12px;
}

.note-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.state-change-actions {
  display: flex;
  gap: 8px;
}

.action-btn-with-note {
  font-weight: 600;
}

.quick-actions {
  display: flex;
  gap: 8px;
}

.add-note-btn {
  margin-left: auto;
}

.action-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  background: #f5f7fa;
  padding: 6px 12px;
  border-radius: 4px;
}

.action-buttons-simple {
  padding: 12px;
  text-align: center;
}

.action-hint {
  font-size: 13px;
  color: #909399;
}

.notes-timeline {
  max-height: 400px;
  overflow-y: auto;
}

.note-item {
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  transition: background 0.2s;
}

.note-item:hover {
  background: #f5f7fa;
}

.note-item:last-child {
  border-bottom: none;
}

.note-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.note-author {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.note-time {
  font-size: 12px;
  color: #909399;
}

.note-content {
  font-size: 14px;
  line-height: 1.6;
  color: #606266;
  white-space: pre-wrap;
}

.notes-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 20px;
  color: #909399;
}

.notes-empty .el-icon {
  font-size: 32px;
  opacity: 0.5;
}

.maint-link {
  color: #409EFF;
  font-weight: 500;
  text-decoration: none;
}

.maint-link:hover {
  text-decoration: underline;
}

.maint-progress {
  margin-top: 16px;
}

.maint-actions {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

@media (max-width: 768px) {
  .status-flow-indicator {
    flex-wrap: wrap;
    gap: 20px;
  }

  .step-line {
    display: none;
  }

  .note-actions .el-button-group {
    flex-wrap: wrap;
  }
}

/* 暗色模式 */
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

.dark .glass-btn-primary {
  background: linear-gradient(135deg, #3fb950 0%, #55efc4 100%);
}

.dark .glass-btn-warning {
  background: linear-gradient(135deg, #d29922 0%, #e3b341 100%);
}

.dark .glass-btn-info {
  background: linear-gradient(135deg, #636e72 0%, #95a5a6 100%);
}
</style>