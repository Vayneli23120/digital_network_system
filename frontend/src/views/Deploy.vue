<template>
  <div class="deploy-page" :class="{ dark: isDark }">
    <!-- 页面标题栏 -->
    <section class="page-nav-bar">
      <div class="nav-left">
        <h1 class="page-title">{{ t('deployTitle') }}</h1>
        <el-tag v-if="executionStatus === 'running'" type="warning" effect="dark" class="status-tag">
          <el-icon class="is-loading"><Loading /></el-icon>
          {{ t('deployExecuting') }}
        </el-tag>
        <el-tag v-else-if="executionStatus === 'completed'" type="success" class="status-tag">
          <el-icon><CircleCheckFilled /></el-icon>
          {{ t('deployCompleted') }}
        </el-tag>
        <el-tag v-else-if="executionStatus === 'failed'" type="danger" class="status-tag">
          <el-icon><CircleCloseFilled /></el-icon>
          {{ t('deployFailed') }}
        </el-tag>
      </div>
      <div class="nav-right">
        <button class="nav-action-btn secondary" @click="showVariableHelp = true">
          <el-icon><QuestionFilled /></el-icon>
          {{ t('deployVariableHelp') }}
        </button>
        <button
          v-if="executionStatus === 'running'"
          class="nav-action-btn danger"
          @click="confirmAbort"
          :loading="aborting"
        >
          <el-icon><CircleClose /></el-icon>
          {{ t('deployAbort') }}
        </button>
      </div>
    </section>

    <!-- 生产环境警告 -->
    <section
      v-if="isProductionEnv && deployForm.target_devices.length > 1"
      class="warning-section"
    >
      <div class="warning-card">
        <el-icon class="warning-icon"><WarningFilled /></el-icon>
        <div class="warning-content">
          <div class="warning-title">{{ t('deployProductionWarningTitle') }}</div>
          <div class="warning-desc">
            {{ t('deployProductionWarning', { count: deployForm.target_devices.length }) }}
          </div>
        </div>
        <el-tag type="warning" effect="dark" size="large">
          {{ t('deploySerialExecution') }}
        </el-tag>
      </div>
    </section>

    <!-- 主内容区 -->
    <section class="main-content-area">
      <el-row :gutter="20" class="full-height">
        <!-- 左侧：配置面板 -->
        <el-col :span="8" class="config-column">
          <div class="config-panel" v-loading="loading">
            <div class="panel-header">
              <span class="panel-title">{{ t('deployConfigPanel') }}</span>
            </div>

            <el-form :model="deployForm" label-position="top" class="config-form">
              <!-- 部署模式 -->
              <div class="form-section">
                <div class="section-label">{{ t('deployMode') }}</div>
                <el-radio-group v-model="deployForm.mode" class="mode-radio-group">
                  <el-radio-button label="backup">
                    <el-icon><Document /></el-icon>
                    {{ t('deployFromBackup') }}
                  </el-radio-button>
                  <el-radio-button label="template">
                    <el-icon><Files /></el-icon>
                    {{ t('deployUseTemplate') }}
                  </el-radio-button>
                  <el-radio-button label="snippet">
                    <el-icon><Edit /></el-icon>
                    {{ t('deploySnippet') }}
                  </el-radio-button>
                </el-radio-group>
              </div>

              <!-- 部署引擎选择 -->
              <div class="form-section">
                <div class="section-label">{{ t('deployEngine') }}</div>
                <el-radio-group v-model="deployForm.engine" size="small">
                  <el-radio-button label="napalm">
                    <el-icon><Shield /></el-icon>
                    {{ t('deployEngineNapalm') }}
                    <el-tag type="success" size="small" effect="plain" class="engine-tag">{{ t('deployEngineNapalmTag') }}</el-tag>
                  </el-radio-button>
                  <el-radio-button label="netmiko">
                    <el-icon><Connection /></el-icon>
                    {{ t('deployEngineNetmiko') }}
                    <el-tag type="info" size="small" effect="plain" class="engine-tag">{{ t('deployEngineNetmikoTag') }}</el-tag>
                  </el-radio-button>
                </el-radio-group>
                <div v-if="deployForm.engine === 'napalm'" class="engine-tip safe">
                  <el-icon><InfoFilled /></el-icon>
                  {{ t('deployEngineNapalmTip') }}
                </div>
              </div>

              <!-- NAPALM 模式选择 -->
              <div v-if="deployForm.engine === 'napalm'" class="form-section">
                <div class="section-label">{{ t('deployNapalmMode') }}</div>
                <el-radio-group v-model="deployForm.napalm_mode" size="small">
                  <el-radio-button label="merge">{{ t('deployNapalmMerge') }}</el-radio-button>
                  <el-radio-button label="replace">{{ t('deployNapalmReplace') }}</el-radio-button>
                </el-radio-group>
                <div class="napalm-mode-tip">
                  {{ deployForm.napalm_mode === 'merge' ? t('deployNapalmMergeTip') : t('deployNapalmReplaceTip') }}
                </div>
              </div>

              <!-- 备份文件选择 -->
              <div v-if="deployForm.mode === 'backup'" class="form-section">
                <div class="section-label required">{{ t('deployBackupFile') }}</div>
                <el-select
                  v-model="deployForm.backup_file"
                  :placeholder="t('deploySelectBackupFile')"
                  style="width: 100%"
                  filterable
                >
                  <el-option
                    v-for="backup in backups"
                    :key="backup.id"
                    :label="`${backup.device_name} - ${backup.backup_file}`"
                    :value="backup.backup_file"
                  >
                    <div class="backup-option">
                      <span class="backup-name">{{ backup.device_name }}</span>
                      <span class="backup-file">{{ backup.backup_file }}</span>
                      <span class="backup-time">{{ formatDateTime(backup.backup_time) }}</span>
                    </div>
                  </el-option>
                </el-select>
              </div>

              <!-- 模板选择 -->
              <div v-if="deployForm.mode === 'template'" class="form-section">
                <div class="section-label required">{{ t('deployConfigTemplate') }}</div>
                <el-select
                  v-model="deployForm.template_id"
                  :placeholder="t('deploySelectTemplate')"
                  style="width: 100%"
                  @change="loadTemplateVariables"
                >
                  <el-option
                    v-for="template in templates"
                    :key="template.id"
                    :label="template.name"
                    :value="template.id"
                  >
                    <div class="template-option">
                      <span class="template-name">{{ template.name }}</span>
                      <span v-if="template.description" class="template-desc">
                        {{ template.description }}
                      </span>
                    </div>
                  </el-option>
                </el-select>
              </div>

              <!-- 配置片段模式 -->
              <div v-if="deployForm.mode === 'snippet'" class="form-section">
                <div class="section-label required">{{ t('deploySnippetContent') }}</div>
                <el-input
                  v-model="deployForm.snippet"
                  type="textarea"
                  :rows="8"
                  :placeholder="t('deploySnippetPlaceholder')"
                  style="width: 100%"
                  class="snippet-input"
                />
                <div class="section-desc">{{ t('deploySnippetTip') }}</div>

                <!-- 片段位置 -->
                <div class="section-label" style="margin-top: 12px;">{{ t('deploySnippetPosition') }}</div>
                <el-radio-group v-model="deployForm.snippet_position" size="small">
                  <el-radio-button label="smart">{{ t('deploySnippetSmart') }}</el-radio-button>
                  <el-radio-button label="append">{{ t('deploySnippetAppend') }}</el-radio-button>
                  <el-radio-button label="prepend">{{ t('deploySnippetPrepend') }}</el-radio-button>
                  <el-radio-button label="replace">{{ t('deploySnippetReplace') }}</el-radio-button>
                </el-radio-group>
                <div v-if="deployForm.snippet_position === 'smart'" class="smart-mode-tip">
                  <el-icon class="tip-icon"><InfoFilled /></el-icon>
                  <span class="tip-text">{{ t('deploySmartModeTip') }}</span>
                </div>

                <!-- 基础配置选择（可选） -->
                <div class="section-label" style="margin-top: 12px;">{{ t('deploySnippetBaseConfig') }}</div>
                <el-select
                  v-model="deployForm.base_backup_file"
                  :placeholder="t('deploySelectBackupOptional')"
                  style="width: 100%"
                  clearable
                >
                  <el-option
                    v-for="backup in backups"
                    :key="backup.id"
                    :label="`${backup.device_name} - ${backup.backup_file}`"
                    :value="backup.backup_file"
                  >
                    <div class="backup-option">
                      <span class="backup-name">{{ backup.device_name }}</span>
                      <span class="backup-file">{{ backup.backup_file }}</span>
                      <span class="backup-time">{{ formatDateTime(backup.backup_time) }}</span>
                    </div>
                  </el-option>
                </el-select>
                <div class="section-desc">{{ t('deploySnippetBaseTip') }}</div>
              </div>

              <!-- 目标设备 -->
              <div class="form-section">
                <div class="section-label required">{{ t('deployTargetDevice') }}</div>
                <el-select
                  v-model="deployForm.target_devices"
                  multiple
                  :placeholder="t('deploySelectDeviceMultiple')"
                  style="width: 100%"
                  filterable
                  @change="handleDeviceChange"
                >
                  <el-option
                    v-for="device in devices"
                    :key="device.id"
                    :label="`${device.name} (${device.ip})`"
                    :value="device.id"
                    :disabled="device.status === 'offline'"
                  >
                    <div class="device-option">
                      <span class="device-name">{{ device.name }}</span>
                      <span class="device-ip">{{ device.ip }}</span>
                      <el-tag
                        v-if="device.status !== 'online'"
                        size="small"
                        type="danger"
                      >
                        {{ device.status }}
                      </el-tag>
                    </div>
                  </el-option>
                </el-select>
                <div class="section-desc">{{ t('deployDeviceTip') }}</div>

                <!-- 执行模式提示 -->
                <div v-if="deployForm.target_devices.length > 1" class="execution-mode-hint">
                  <el-tag
                    v-if="isProductionEnv"
                    type="warning"
                    effect="dark"
                    size="large"
                  >
                    <el-icon><WarningFilled /></el-icon>
                    {{ t('deploySerialMode') }}
                  </el-tag>
                  <el-tag v-else type="success" effect="dark" size="large">
                    <el-icon><CircleCheckFilled /></el-icon>
                    {{ t('deployParallelMode', { limit: parallelLimit }) }}
                  </el-tag>
                </div>
              </div>

              <!-- 变量替换 -->
              <div v-if="deployForm.mode === 'template' && availableVariables.length > 0" class="form-section">
                <div class="section-label">{{ t('deployVariableReplace') }}</div>
                <div class="variables-list">
                  <div
                    v-for="(variable, index) in deployForm.variables"
                    :key="index"
                    class="variable-item"
                  >
                    <el-select
                      v-model="variable.key"
                      :placeholder="t('deploySelectVariable')"
                      style="width: 140px"
                      size="small"
                    >
                      <el-option
                        v-for="v in availableVariables"
                        :key="v.key"
                        :label="v.key"
                        :value="v.key"
                      />
                    </el-select>
                    <el-input
                      v-model="variable.value"
                      :placeholder="getVariablePlaceholder(variable.key)"
                      style="flex: 1"
                      size="small"
                    />
                    <el-button
                      size="small"
                      type="danger"
                      link
                      @click="removeVariable(index)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <el-button size="small" @click="addVariable" class="add-var-btn">
                    <el-icon><Plus /></el-icon>
                    {{ t('deployAddVariable') }}
                  </el-button>
                </div>
              </div>

              <!-- 干运行选项 -->
              <div class="form-section">
                <el-checkbox v-model="deployForm.dry_run">
                  {{ t('deployDryRun') }}
                </el-checkbox>
                <div class="section-desc">{{ t('deployPreviewTip') }}</div>
              </div>

              <!-- 操作按钮 -->
              <div class="form-section actions-section">
                <button
                  type="button"
                  class="nav-action-btn secondary preview-btn"
                  @click="previewDeploy"
                  :disabled="!canDeploy || !deployForm.dry_run"
                  :class="{ disabled: !canDeploy || !deployForm.dry_run }"
                >
                  <el-icon><View /></el-icon>
                  {{ t('deployPreviewChange') }}
                </button>
                <button
                  type="button"
                  class="nav-action-btn deploy-btn"
                  @click="confirmDeploy"
                  :disabled="!canDeploy"
                  :class="{ disabled: !canDeploy }"
                >
                  <el-icon><Upload /></el-icon>
                  {{ t('deployStart') }}
                </button>
              </div>
            </el-form>
          </div>
        </el-col>

        <!-- 右侧：执行面板 -->
        <el-col :span="16" class="execution-column">
          <div class="execution-panel" :class="{ active: executionStatus !== 'idle' }">
            <!-- 执行进度概览 -->
            <div class="execution-overview">
              <div class="overview-header">
                <div class="overview-title">
                  <el-icon v-if="executionStatus === 'running'" class="is-loading"><Loading /></el-icon>
                  <span>{{ t('deployExecutionTitle') }}</span>
                </div>
                <div class="overview-actions">
                  <div v-if="elapsedTime > 0" class="elapsed-time">
                    {{ t('deployElapsedTime') }}: {{ formatDuration(elapsedTime) }}
                  </div>
                  <el-button
                    v-if="executionStatus === 'completed' && hasRollbackAvailable"
                    type="warning"
                    size="small"
                    @click="handleRollback"
                  >
                    <el-icon><RefreshLeft /></el-icon>
                    {{ t('deployRollback') }}
                  </el-button>
                </div>
              </div>

              <div class="progress-overview">
                <div class="progress-item">
                  <div class="progress-label">{{ t('deployTotalDevices') }}</div>
                  <div class="progress-value">{{ totalDevices }}</div>
                </div>
                <div class="progress-item success">
                  <div class="progress-label">{{ t('deployCompleted') }}</div>
                  <div class="progress-value">{{ completedDevices }}</div>
                </div>
                <div class="progress-item warning">
                  <div class="progress-label">{{ t('deployInProgress') }}</div>
                  <div class="progress-value">{{ inProgressDevices }}</div>
                </div>
                <div class="progress-item error">
                  <div class="progress-label">{{ t('deployFailed') }}</div>
                  <div class="progress-value">{{ failedDevices }}</div>
                </div>
              </div>

              <el-progress
                :percentage="progressPercentage"
                :status="progressStatus"
                :stroke-width="12"
                class="overall-progress"
              />
            </div>

            <el-divider />

            <!-- 设备执行状态 -->
            <div class="devices-section">
              <div class="section-header">
                <span class="section-title">{{ t('deployDeviceExecution') }}</span>
              </div>
              <div class="device-cards">
                <div
                  v-for="device in deviceExecutions"
                  :key="device.device_id"
                  class="device-card"
                  :class="{
                    active: selectedDevice?.device_id === device.device_id,
                    success: device.status === 'completed',
                    error: device.status === 'failed',
                    skipped: device.status === 'skipped',
                    running: device.status === 'running'
                  }"
                  @click="selectDevice(device)"
                >
                  <div class="device-card-header">
                    <div class="device-info">
                      <el-icon
                        v-if="device.status === 'completed'"
                        class="status-icon success"
                      >
                        <CircleCheckFilled />
                      </el-icon>
                      <el-icon
                        v-else-if="device.status === 'failed'"
                        class="status-icon error"
                      >
                        <CircleCloseFilled />
                      </el-icon>
                      <el-icon
                        v-else-if="device.status === 'skipped'"
                        class="status-icon skipped"
                      >
                        <Minus />
                      </el-icon>
                      <el-icon
                        v-else-if="device.status === 'running'"
                        class="status-icon running is-loading"
                      >
                        <Loading />
                      </el-icon>
                      <el-icon v-else class="status-icon pending">
                        <Timer />
                      </el-icon>
                      <div class="device-text">
                        <div class="device-name">{{ device.device_name }}</div>
                        <div class="device-ip">{{ device.device_ip }}</div>
                      </div>
                    </div>
                    <el-tag
                      :type="getDeviceStatusType(device.status)"
                      size="small"
                      effect="dark"
                    >
                      {{ getDeviceStatusText(device.status) }}
                    </el-tag>
                  </div>
                  <el-progress
                    :percentage="device.progress"
                    :status="getDeviceProgressStatus(device.status)"
                    :stroke-width="4"
                    class="device-progress"
                  />
                  <div v-if="device.message" class="device-message">
                    {{ device.message }}
                  </div>
                </div>
              </div>
            </div>

            <!-- CLI 区域：并排显示命令输出和部署历史 -->
            <div class="cli-section-parallel">
              <!-- 左侧：CLI 命令输出（部署结果） -->
              <div class="cli-panel">
                <div class="cli-panel-header">
                  <span class="cli-panel-title">
                    {{ t('deployCliOutput') }}
                    <span v-if="selectedDevice" class="device-badge">{{ selectedDevice.device_name }}</span>
                  </span>
                  <el-tag v-if="executionStatus === 'running'" type="warning" size="small">
                    <el-icon class="is-loading"><Loading /></el-icon>
                    {{ t('deployExecuting') }}
                  </el-tag>
                  <el-tag v-else-if="executionStatus === 'completed'" type="success" size="small">
                    {{ t('deployCompleted') }}
                  </el-tag>
                  <button class="nav-action-btn secondary small" @click="clearCliOutput">
                    <el-icon><Delete /></el-icon>
                    {{ t('actionClear') }}
                  </button>
                </div>
                <div ref="cliOutputRef" class="cli-panel-output">
                  <div
                    v-for="(line, index) in selectedDevice?.cliLogs || []"
                    :key="index"
                    class="cli-line"
                    :class="line.type"
                  >
                    <span class="cli-timestamp">{{ formatTime(line.timestamp) }}</span>
                    <span class="cli-content">{{ line.content }}</span>
                  </div>
                  <div v-if="!selectedDevice || selectedDevice.cliLogs.length === 0" class="cli-empty">
                    {{ t('deployCliEmpty') }}
                  </div>
                </div>
              </div>

              <!-- 右侧：部署历史记录 -->
              <div class="cli-panel history-panel">
                <div class="cli-panel-header">
                  <span class="cli-panel-title">{{ t('deployHistory') }}</span>
                </div>
                <div class="history-list">
                  <div
                    v-for="(record, idx) in deployHistory"
                    :key="record.id || idx"
                    class="history-item"
                    :class="{ active: selectedHistoryId === record.id }"
                    @click="loadHistoryRecord(record)"
                  >
                    <div class="history-info">
                      <span class="history-time">{{ formatDateTime(record.timestamp) }}</span>
                      <el-tag :type="record.success ? 'success' : 'danger'" size="small">
                        {{ record.success ? t('statusSuccess') : t('statusFailed') }}
                      </el-tag>
                    </div>
                    <div class="history-devices">
                      {{ record.device_names?.join(', ') || record.device_name || '-' }}
                    </div>
                    <div class="history-status">
                      <span v-if="record.deviceResults" class="status-summary">
                        <span class="status-success">{{ record.deviceResults.filter(d => d.status === 'completed').length }} 成功</span>
                        <span v-if="record.deviceResults.filter(d => d.status === 'failed').length > 0" class="status-failed">
                          {{ record.deviceResults.filter(d => d.status === 'failed').length }} 失败
                        </span>
                      </span>
                    </div>
                    <div class="history-engine">
                      <span class="engine-tag">{{ record.engine }}</span>
                      <span v-if="record.mode === 'rollback'" class="mode-tag rollback">{{ t('deployRollback') }}</span>
                      <span v-else-if="record.mode" class="mode-tag">{{ record.mode }}</span>
                    </div>
                  </div>
                  <div v-if="deployHistory.length === 0" class="cli-empty">
                    {{ t('deployNoHistory') }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </section>

    <!-- 配置差异预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      :title="t('deployPreviewDialog')"
      width="90%"
      top="5vh"
      destroy-on-close
      align-center
    >
      <el-skeleton v-if="previewLoading" :rows="10" animated />

      <div v-else class="preview-content">
        <!-- 影响分析摘要 -->
        <div class="impact-summary">
          <div class="impact-header">
            <el-icon><WarningFilled /></el-icon>
            <span>{{ t('deployImpactAnalysis') }}</span>
          </div>
          <div class="impact-stats">
            <div class="impact-item">
              <span class="impact-label">{{ t('diffTotalChanges') }}</span>
              <span class="impact-value">{{ impactAnalysis.totalChanges }}</span>
            </div>
            <div class="impact-item">
              <span class="impact-label">{{ t('diffAffectedServices') }}</span>
              <span class="impact-value">
                {{ impactAnalysis.affectedServices.length > 0
                  ? impactAnalysis.affectedServices.join(', ')
                  : t('diffNoServices') }}
              </span>
            </div>
            <div class="impact-item">
              <span class="impact-label">{{ t('diffEstimatedDowntime') }}</span>
              <span class="impact-value">{{ impactAnalysis.estimatedDowntime }}s</span>
            </div>
            <div class="impact-item">
              <span class="impact-label">{{ t('diffRiskLevel') }}</span>
              <el-tag :type="getRiskLevelType(impactAnalysis.riskLevel)" size="large">
                {{ getRiskLevelText(impactAnalysis.riskLevel) }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 设备选择 -->
        <div class="device-selector">
          <span class="selector-label">{{ t('diffSelectDevice') }}:</span>
          <el-select v-model="selectedPreviewDevice" style="width: 300px">
            <el-option
              v-for="result in previewResults"
              :key="result.device_id"
              :label="`${result.device_name} (${result.device_ip})`"
              :value="result"
            />
          </el-select>
        </div>

        <!-- 设备差异 -->
        <div v-if="selectedPreviewDevice" class="device-diff">
          <div class="diff-device-header">
            <div class="device-info">
              <h4>{{ selectedPreviewDevice.device_name }}</h4>
              <span class="device-ip">{{ selectedPreviewDevice.device_ip }}</span>
            </div>
            <el-tag
              :type="getRiskLevelType(selectedPreviewDevice.impact?.risk_level)"
              size="small"
            >
              {{ getRiskLevelText(selectedPreviewDevice.impact?.risk_level) }}
            </el-tag>
          </div>

          <DiffViewer
            v-if="selectedPreviewDevice.diff"
            :old-config="selectedPreviewDevice.old_config || ''"
            :new-config="selectedPreviewDevice.new_config || ''"
            :diff-data="selectedPreviewDevice.diff"
            :is-dark="isDark"
          />
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showPreviewDialog = false">
            {{ t('actionClose') }}
          </el-button>
          <el-button type="primary" @click="openScheduleDialog">
            <el-icon><Calendar /></el-icon>
            {{ t('deploySchedule') }}
          </el-button>
          <el-button type="success" @click="confirmDeployFromPreview">
            <el-icon><Upload /></el-icon>
            {{ t('deployStart') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 维护窗口预约对话框 -->
    <el-dialog
      v-model="showScheduleDialog"
      :title="t('deployScheduleDialog')"
      width="600px"
      align-center
    >
      <div class="schedule-content">
        <p class="schedule-desc">{{ t('deployScheduleDesc') }}</p>

        <el-form label-position="top">
          <el-form-item :label="t('deploySelectWindow')">
            <el-radio-group v-model="selectedWindow" class="window-options">
              <el-radio-button
                v-for="window in maintenanceWindows"
                :key="window.id"
                :label="window.id"
                :disabled="!window.available"
                class="window-option"
              >
                <div class="window-label">{{ getWindowLabel(window) }}</div>
                <div class="window-time">{{ window.start_time }} - {{ window.end_time }}</div>
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-form>

        <div v-if="isScheduled" class="schedule-confirmation">
          <el-alert
            :title="t('deployScheduledConfirm', { time: scheduledTime })"
            type="success"
            :closable="false"
          />
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showScheduleDialog = false">
            {{ t('actionCancel') }}
          </el-button>
          <el-button type="primary" @click="scheduleDeployTask">
            {{ t('deployConfirmSchedule') }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 变量说明对话框 -->
    <el-dialog
      v-model="showVariableHelp"
      :title="t('deployVariableDialog')"
      width="800px"
      align-center
      draggable
    >
      <el-table :data="allVariables" style="width: 100%" stripe>
        <el-table-column prop="key" :label="t('deployVariableName')" width="200" />
        <el-table-column prop="description" :label="t('deployDescription')" />
        <el-table-column prop="example" :label="t('deployExampleValue')" width="200" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  QuestionFilled,
  Delete,
  Plus,
  View,
  Upload,
  CircleClose,
  WarningFilled,
  CircleCheckFilled,
  CircleCloseFilled,
  Loading,
  Timer,
  Document,
  Files,
  Calendar,
  Edit,
  RefreshLeft,
  Minus
} from '@element-plus/icons-vue'
import {
  getDevices,
  getBackups,
  getTemplates,
  getTemplate,
  previewDeploy as previewDeployApi,
  executeDeploy as executeDeployApi,
  rollbackDeploy as rollbackDeployApi,
  getCompatibleVariables,
  getMaintenanceWindows,
  scheduleDeploy
} from '@/api'
import { formatDateTime } from '@/utils/time'
import { useI18n } from '@/composables/useI18n'
import { cachedRequest, clearCache } from '@/utils/cache.js'
import { debounce } from '@/utils/requestManager.js'
import DiffViewer from '@/components/DiffViewer.vue'

const { t } = useI18n()

// 暗黑模式检测
const isDark = computed(() => document.documentElement.classList.contains('dark'))

// 环境控制
const isProductionEnv = ref(false)
const parallelLimit = ref(1)

// 数据
const devices = ref([])
const backups = ref([])
const templates = ref([])
const allVariables = ref([])
const availableVariables = ref([])
const loading = ref(false)

// 表单
const deployForm = ref({
  mode: 'backup',
  engine: 'netmiko',  // napalm | netmiko，默认 netmiko（无需 SCP）
  napalm_mode: 'merge',  // merge | replace，默认 merge
  backup_file: '',
  template_id: '',
  snippet: '',
  snippet_position: 'smart',
  base_backup_file: '',
  target_devices: [],
  variables: [],
  dry_run: false
})

// 执行状态
const executionStatus = ref('idle') // idle, running, completed, failed, aborted
const taskId = ref(null)
const startTime = ref(null)
const elapsedTime = ref(0)
const deviceExecutions = ref([])
const selectedDevice = ref(null)
const aborting = ref(false)
const showVariableHelp = ref(false)
const cliOutputRef = ref(null)

// 部署历史记录（从 localStorage 加载）
const deployHistory = ref([])
const selectedHistoryId = ref(null)

// 加载历史记录
const loadHistory = () => {
  try {
    const saved = localStorage.getItem('deployHistory')
    if (saved) {
      deployHistory.value = JSON.parse(saved)
    }
  } catch (e) {
    console.error('Failed to load deploy history:', e)
  }
}

// 保存历史记录到 localStorage
const saveHistoryToStorage = () => {
  try {
    localStorage.setItem('deployHistory', JSON.stringify(deployHistory.value))
  } catch (e) {
    console.error('Failed to save deploy history:', e)
  }
}

// 审批相关状态
const approvalStatus = ref('none') // none, pending, approved, rejected
const approvalId = ref(null)
const approvalLevel = ref(null)
const approvalInfo = ref(null)
const showApprovalDialog = ref(false)
const approvalComment = ref('')
const rejectionReason = ref('')

// Phase 3: 配置差异预览
const previewResults = ref([])
const showPreviewDialog = ref(false)
const previewLoading = ref(false)
const selectedPreviewDevice = ref(null)

// Phase 3: 维护窗口
const maintenanceWindows = ref([])
const selectedWindow = ref(null)
const showScheduleDialog = ref(false)
const isScheduled = ref(false)
const scheduledTime = ref(null)

// Phase 3: 影响分析
const impactAnalysis = ref({
  totalChanges: 0,
  affectedServices: [],
  estimatedDowntime: 0,
  riskLevel: 'low',
  highRiskDevices: 0
})

// 计算属性
const canDeploy = computed(() => {
  if (deployForm.value.target_devices.length === 0) return false
  if (deployForm.value.mode === 'backup') {
    return !!deployForm.value.backup_file
  }
  if (deployForm.value.mode === 'snippet') {
    return !!deployForm.value.snippet.trim()
  }
  return !!deployForm.value.template_id
})

const totalDevices = computed(() => deviceExecutions.value.length)
const completedDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'completed').length
)
const inProgressDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'running').length
)
const failedDevices = computed(() =>
  deviceExecutions.value.filter(d => d.status === 'failed').length
)

const progressPercentage = computed(() => {
  if (totalDevices.value === 0) return 0
  const totalProgress = deviceExecutions.value.reduce((sum, d) => sum + d.progress, 0)
  return Math.round(totalProgress / totalDevices.value)
})

const progressStatus = computed(() => {
  if (executionStatus.value === 'failed') return 'exception'
  if (executionStatus.value === 'completed') return 'success'
  return ''
})

const hasRollbackAvailable = computed(() => {
  return deviceExecutions.value.some(d => d.rollback_available)
})

// 加载数据
const loadDevices = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getDevices(),
      'devices',
      {},
      { forceRefresh: force }
    )
    devices.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadDeviceFailed'))
    }
  }
}, 300)

const loadBackups = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getBackups({ limit: 50 }),
      'backups',
      { limit: 50 },
      { forceRefresh: force }
    )
    backups.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadBackupFailed'))
    }
  }
}, 300)

const loadTemplates = debounce(async (force = false) => {
  try {
    const data = await cachedRequest(
      () => getTemplates(),
      'templates',
      {},
      { forceRefresh: force }
    )
    templates.value = data.items || []
  } catch (error) {
    if (error.name !== 'CanceledError') {
      ElMessage.error(t('deployLoadTemplateFailed'))
    }
  }
}, 300)

const loadCompatibleVariables = async () => {
  try {
    const data = await cachedRequest(
      () => getCompatibleVariables(),
      'compatibleVariables',
      {},
      { ttl: 300000 }  // 缓存 5 分钟
    )
    allVariables.value = data.variables || []
  } catch (error) {
    // Silent fail
  }
}

const loadTemplateVariables = async (templateId) => {
  if (!templateId) {
    availableVariables.value = []
    return
  }

  try {
    const data = await cachedRequest(
      () => getTemplate(templateId),
      'template',
      { id: templateId },
      { ttl: 60000 }  // 缓存 1 分钟
    )
    if (data.variables) {
      try {
        const vars = typeof data.variables === 'string'
          ? JSON.parse(data.variables)
          : data.variables
        availableVariables.value = vars
        deployForm.value.variables = vars.map(v => ({
          key: v.key,
          value: v.default || ''
        }))
      } catch (e) {
        console.error('Parse template variables failed:', e)
      }
    }
  } catch (error) {
    ElMessage.error(t('deployLoadTemplateVarFailed'))
  }
}

// 环境检测
const detectEnvironment = () => {
  const productionPatterns = [
    /prod/i, /production/i, /live/i, /core/i,
    /border/i, /wan/i, /internet/i
  ]

  const hasProductionDevice = deployForm.value.target_devices.some(deviceId => {
    const device = devices.value.find(d => d.id === deviceId)
    if (!device) return false
    return productionPatterns.some(pattern =>
      pattern.test(device.name) || pattern.test(device.ip)
    )
  })

  isProductionEnv.value = hasProductionDevice
  parallelLimit.value = isProductionEnv.value ? 1 : 3
}

const handleDeviceChange = () => {
  detectEnvironment()
  // 重置设备执行列表
  deviceExecutions.value = deployForm.value.target_devices.map(id => {
    const device = devices.value.find(d => d.id === id)
    return {
      device_id: id,
      device_name: device?.name || '',
      device_ip: device?.ip || '',
      status: 'pending',
      progress: 0,
      message: '',
      cliLogs: [],
      rollback_available: false
    }
  })
}

// 变量操作
const getVariablePlaceholder = (key) => {
  const v = allVariables.value.find(v => v.key === key)
  return v ? t('deployExample') + v.example : ''
}

const addVariable = () => {
  deployForm.value.variables.push({ key: '', value: '' })
}

const removeVariable = (index) => {
  deployForm.value.variables.splice(index, 1)
}

// 设备状态
const getDeviceStatusType = (status) => {
  const types = { pending: 'info', running: 'primary', completed: 'success', failed: 'danger', skipped: 'warning' }
  return types[status] || 'info'
}

const getDeviceStatusText = (status) => {
  const texts = {
    pending: t('deployDevicePending'),
    running: t('deployDeviceRunning'),
    completed: t('deployDeviceCompleted'),
    failed: t('deployDeviceFailed'),
    skipped: t('deployDeviceSkipped')
  }
  return texts[status] || status
}

const getDeviceProgressStatus = (status) => {
  if (status === 'failed') return 'exception'
  if (status === 'completed') return 'success'
  return ''
}

const selectDevice = (device) => {
  selectedDevice.value = device
}

const clearCliOutput = () => {
  if (selectedDevice.value) {
    selectedDevice.value.cliLogs = []
  }
}

const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

// 自动滚动到底部
const scrollToBottom = () => {
  nextTick(() => {
    if (cliOutputRef.value) {
      cliOutputRef.value.scrollTop = cliOutputRef.value.scrollHeight
    }
  })
}

// 保存部署到历史记录
const saveToHistory = (result) => {
  // 计算每个设备的状态
  const deviceResults = deviceExecutions.value.map(d => {
    const r = result.results?.find(r => r.device_id === d.device_id)
    return {
      device_id: d.device_id,
      device_name: d.device_name,
      status: r?.success ? 'completed' : 'failed',
      message: r?.message || '',
      rollback_available: r?.rollback_available || false,
      logs: d.cliLogs
    }
  })

  // 计算总体状态：所有设备都成功才算成功
  const allSuccess = deviceResults.every(d => d.status === 'completed')

  const historyRecord = {
    id: Date.now(),
    timestamp: new Date().toISOString(),
    success: allSuccess,
    engine: deployForm.value.engine,
    mode: deployForm.value.napalm_mode || deployForm.value.mode,
    device_names: deviceResults.map(d => d.device_name),
    results: result.results,
    deviceResults: deviceResults,  // 保存每个设备的详细状态
    cliLogs: deviceResults
  }
  // 添加到历史列表顶部
  deployHistory.value.unshift(historyRecord)
  // 限制历史记录数量
  if (deployHistory.value.length > 50) {
    deployHistory.value.pop()
  }
  // 保存到 localStorage
  saveHistoryToStorage()
}

// 加载历史记录到左侧面板
const loadHistoryRecord = (record) => {
  selectedHistoryId.value = record.id
  // 清空当前设备执行状态，使用保存的状态
  deviceExecutions.value = (record.deviceResults || record.cliLogs).map(d => ({
    device_id: d.device_id,
    device_name: d.device_name,
    status: d.status || 'completed',  // 使用保存的状态，默认 completed
    message: d.message || '',
    progress: 100,
    cliLogs: d.logs || [],
    rollback_available: d.rollback_available || false
  }))
  // 选中第一个设备
  if (deviceExecutions.value.length > 0) {
    selectedDevice.value = deviceExecutions.value[0]
  }
}

// 预览部署
const previewDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  const deployData = {
    mode: deployForm.value.mode,
    engine: deployForm.value.engine,
    napalm_mode: deployForm.value.napalm_mode,
    backup_file: deployForm.value.backup_file,
    template_id: deployForm.value.template_id,
    snippet: deployForm.value.snippet,
    snippet_position: deployForm.value.snippet_position,
    base_backup_file: deployForm.value.base_backup_file,
    target_devices: deployForm.value.target_devices,
    variables: {}
  }

  deployForm.value.variables.forEach(v => {
    if (v.key) deployData.variables[v.key] = v.value
  })

  previewLoading.value = true
  showPreviewDialog.value = true

  try {
    const result = await previewDeployApi(deployData)
    previewResults.value = result.preview || []
    selectedPreviewDevice.value = previewResults.value[0] || null

    // 更新影响分析
    impactAnalysis.value = {
      totalChanges: result.summary?.total_changes || 0,
      highRiskDevices: result.summary?.high_risk_devices || 0,
      affectedServices: [...new Set(previewResults.value.flatMap(p => p.impact?.affected_services || []))],
      estimatedDowntime: Math.max(...previewResults.value.map(p => p.impact?.estimated_downtime_seconds || 0)),
      riskLevel: result.summary?.high_risk_devices > 0 ? 'high' :
                 result.summary?.total_changes > 20 ? 'medium' : 'low'
    }

    ElMessage.success(t('deployPreviewSuccess'))
  } catch (error) {
    ElMessage.error(t('deployPreviewFailed'))
    showPreviewDialog.value = false
  } finally {
    previewLoading.value = false
  }
}

// 加载维护窗口
const loadMaintenanceWindows = async () => {
  try {
    const data = await cachedRequest(
      () => getMaintenanceWindows(),
      'maintenanceWindows',
      {},
      { ttl: 300000 }  // 缓存 5 分钟
    )
    maintenanceWindows.value = data.windows || []
  } catch (error) {
    console.error('Load maintenance windows failed:', error)
  }
}

// 预约部署
const scheduleDeployTask = async () => {
  if (!selectedWindow.value) {
    ElMessage.warning(t('deploySelectWindow'))
    return
  }

  const deployData = {
    mode: deployForm.value.mode,
    engine: deployForm.value.engine,
    napalm_mode: deployForm.value.napalm_mode,
    backup_file: deployForm.value.backup_file,
    template_id: deployForm.value.template_id,
    snippet: deployForm.value.snippet,
    snippet_position: deployForm.value.snippet_position,
    base_backup_file: deployForm.value.base_backup_file,
    target_devices: deployForm.value.target_devices,
    variables: {}
  }

  deployForm.value.variables.forEach(v => {
    if (v.key) deployData.variables[v.key] = v.value
  })

  try {
    const result = await scheduleDeploy({
      window_id: selectedWindow.value,
      deploy_data: deployData
    })

    isScheduled.value = true
    scheduledTime.value = result.scheduled_at
    showScheduleDialog.value = false
    ElMessage.success(t('deployScheduled'))
  } catch (error) {
    ElMessage.error(t('deployScheduleFailed'))
  }
}

// 获取风险等级标签
const getRiskLevelType = (level) => {
  const types = { low: 'success', medium: 'warning', high: 'danger' }
  return types[level] || 'info'
}

const getRiskLevelText = (level) => {
  const texts = {
    low: t('diffRiskLow'),
    medium: t('diffRiskMedium'),
    high: t('diffRiskHigh')
  }
  return texts[level] || level
}

// 维护窗口标签生成
const getWindowLabel = (window) => {
  const dateStr = window.date ? window.date.slice(5) : ''  // 取 MM-DD
  const periodLabels = {
    morning: t('deployWindowMorning'),
    afternoon: t('deployWindowAfternoon'),
    evening: t('deployWindowEvening')
  }
  const periodText = periodLabels[window.period] || window.period
  return `${dateStr} ${periodText} (${window.start_time}-${window.end_time})`
}

// 变量描述生成
const getVariableDescription = (key) => {
  const descriptions = {
    HOSTNAME: t('varDescHostname'),
    ENABLE_SECRET: t('varDescEnableSecret'),
    ADMIN_USERNAME: t('varDescAdminUsername'),
    ADMIN_PASSWORD: t('varDescAdminPassword'),
    DOMAIN_NAME: t('varDescDomainName'),
    MGMT_VLAN_ID: t('varDescMgmtVlanId'),
    MGMT_IP: t('varDescMgmtIp'),
    MGMT_NETMASK: t('varDescMgmtNetmask'),
    DEFAULT_GATEWAY: t('varDescDefaultGateway'),
    SNMP_COMMUNITY: t('varDescSnmpCommunity'),
    LOCATION: t('varDescLocation'),
    CONTACT: t('varDescContact'),
    NTP_SERVER: t('varDescNtpServer'),
    SYSLOG_SERVER: t('varDescSyslogServer'),
    DEFAULT_ROUTE: t('varDescDefaultRoute'),
    OSPF_ROUTER_ID: t('varDescOspfRouterId'),
    ACCESS_PORT_RANGE: t('varDescAccessPortRange'),
    UPLINK_PORT: t('varDescUplinkPort'),
    BUSINESS_VLAN_LIST: t('varDescBusinessVlanList'),
    TRUNK_VLANS: t('varDescTrunkVlans')
  }
  return descriptions[key] || key
}

// 执行部署
const confirmDeploy = async () => {
  if (!canDeploy.value) {
    ElMessage.warning(t('deploySelectModeAndDevice'))
    return
  }

  detectEnvironment()

  // 生产环境多设备警告
  if (isProductionEnv.value && deployForm.value.target_devices.length > 1) {
    try {
      await ElMessageBox.confirm(
        t('deployProductionConfirm', { count: deployForm.value.target_devices.length }),
        t('deployProductionWarningTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )
    } catch {
      return
    }
  } else {
    try {
      await ElMessageBox.confirm(
        t('deployConfirmMessage'),
        t('deployConfirmTitle'),
        { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
      )
    } catch {
      return
    }
  }

  await executeDeploy()
}

// SSE 执行
let eventSource = null
let timer = null

const executeDeploy = async () => {
  try {
    // 初始化设备执行列表
    deviceExecutions.value = deployForm.value.target_devices.map(id => {
      const device = devices.value.find(d => d.id === id)
      return {
        device_id: id,
        device_name: device?.name || '',
        device_ip: device?.ip || '',
        status: 'pending',
        progress: 0,
        message: '',
        cliLogs: [],
        rollback_available: false
      }
    })

    // 正常部署模式
    const deployData = {
      mode: deployForm.value.mode,
      engine: deployForm.value.engine,
      napalm_mode: deployForm.value.napalm_mode,
      backup_file: deployForm.value.backup_file,
      template_id: deployForm.value.template_id,
      snippet: deployForm.value.snippet,
      snippet_position: deployForm.value.snippet_position,
      base_backup_file: deployForm.value.base_backup_file,
      target_devices: deployForm.value.target_devices,
      variables: {},
      dry_run: deployForm.value.dry_run,
      is_production: isProductionEnv.value,
      parallel_limit: parallelLimit.value
    }

    deployForm.value.variables.forEach(v => {
      if (v.key) deployData.variables[v.key] = v.value
    })

    // 开始执行部署
    executionStatus.value = 'running'
    startTime.value = Date.now()
    timer = setInterval(() => {
      elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
    }, 1000)

    const result = await executeDeployApi(deployData)

    // 检查是否需要审批
    if (result.requires_approval) {
      clearInterval(timer)
      approvalStatus.value = 'pending'
      approvalId.value = result.approval_id
      approvalLevel.value = result.approval_level
      approvalInfo.value = {
        requester: currentUser?.username || 'Unknown',
        requestedAt: new Date().toISOString(),
        level: result.approval_level
      }
      return
    }

    // 直接处理返回结果（后端已同步完成）
    stopTimer()

    // 处理每个设备的执行结果
    if (result.results && result.results.length > 0) {
      result.results.forEach(r => {
        const device = deviceExecutions.value.find(d => d.device_id === r.device_id)
        if (device) {
          device.status = r.success ? 'completed' : 'failed'
          device.message = r.message || (r.success ? '部署成功' : '部署失败')
          device.progress = 100
          device.rollback_available = r.rollback_available || false

          // 显示 CLI 输出或配置差异
          if (r.cli_output) {
            device.cliLogs.push({
              timestamp: new Date().toISOString(),
              content: r.cli_output,
              type: 'info'
            })
          }
          if (r.diff) {
            device.cliLogs.push({
              timestamp: new Date().toISOString(),
              content: `配置差异:\n${r.diff}`,
              type: 'diff'
            })
          }
          if (r.rollback_available) {
            device.cliLogs.push({
              timestamp: new Date().toISOString(),
              content: '支持回滚，可通过 rollback 操作恢复',
              type: 'info'
            })
          }
          if (r.errors && r.errors.length > 0) {
            r.errors.forEach(err => {
              device.cliLogs.push({
                timestamp: new Date().toISOString(),
                content: `错误: ${err}`,
                type: 'error'
              })
            })
          }
          scrollToBottom()
        }
      })
    }

    // 更新执行状态
    executionStatus.value = result.success ? 'completed' : 'failed'
    clearCache('devices')

    if (result.success) {
      ElMessage.success(t('deployComplete'))
    } else {
      ElMessage.error(t('deployFailed'))
    }

    // 保存到部署历史
    saveToHistory(result)

  } catch (error) {
    stopTimer()
    executionStatus.value = 'failed'
    ElMessage.error(t('deployFailed'))
  }
}

const connectExecutionStream = () => {
  if (!taskId.value) return

  eventSource = new EventSource(`/api/deploy/execute/${taskId.value}/stream`)

  eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data)
    handleExecutionEvent(data)
  }

  eventSource.onerror = () => {
    if (executionStatus.value === 'running') {
      executionStatus.value = 'failed'
      ElMessage.error(t('deployStreamError'))
    }
    closeEventSource()
  }
}

const handleExecutionEvent = (data) => {
  const device = deviceExecutions.value.find(d => d.device_id === data.device_id)

  switch (data.type) {
    case 'device_start':
      if (device) {
        device.status = 'running'
        device.message = data.message
      }
      break
    case 'device_progress':
      if (device) {
        device.progress = data.progress
        device.message = data.message
      }
      break
    case 'device_cli':
      if (device) {
        device.cliLogs.push({
          timestamp: data.timestamp,
          content: data.cli_output,
          type: data.log_type || 'info'
        })
        // 自动滚动
        if (selectedDevice.value?.device_id === data.device_id) {
          nextTick(() => {
            if (cliOutputRef.value) {
              cliOutputRef.value.scrollTop = cliOutputRef.value.scrollHeight
            }
          })
        }
      }
      break
    case 'device_complete':
      if (device) {
        device.status = 'completed'
        device.progress = 100
        device.message = data.message
      }
      break
    case 'device_failed':
      if (device) {
        device.status = 'failed'
        device.message = data.message
      }
      break
    case 'execution_complete':
      executionStatus.value = data.success ? 'completed' : 'failed'
      closeEventSource()
      stopTimer()
      clearCache('devices')
      ElMessage.success(t('deployComplete'))
      break
  }
}

const closeEventSource = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

const stopTimer = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const handleRollback = async () => {
  // 只回滚成功部署的设备（有 rollback_available 标记）
  const rollbackDevices = deviceExecutions.value
    .filter(d => d.rollback_available)
    .map(d => d.device_id)

  if (rollbackDevices.length === 0) {
    ElMessage.warning('没有可回滚的设备')
    return
  }

  try {
    await ElMessageBox.confirm(
      t('deployRollbackConfirm'),
      t('deployRollbackTitle'),
      { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
    )

    const rollbackData = {
      target_devices: rollbackDevices
    }

    executionStatus.value = 'running'
    const result = await rollbackDeployApi(rollbackData)

    stopTimer()

    // 处理回滚结果
    // 先将所有没有 rollback_available 的设备标记为 skipped
    deviceExecutions.value.forEach(d => {
      if (!d.rollback_available) {
        d.status = 'skipped'
        d.message = '原部署失败，未执行回滚'
      }
    })

    // 然后处理有回滚结果的设备
    if (result.results && result.results.length > 0) {
      result.results.forEach(r => {
        // 使用宽松比较，确保类型匹配
        const device = deviceExecutions.value.find(d => Number(d.device_id) === Number(r.device_id))
        if (device) {
          device.status = r.success ? 'completed' : 'failed'
          device.message = r.message || (r.success ? '回滚成功' : '回滚失败')
          device.progress = 100
          device.rollback_available = false

          // 清空之前的日志并显示回滚日志
          device.cliLogs = []

          // 显示 CLI 输出
          if (r.cli_output) {
            device.cliLogs.push({
              timestamp: new Date().toISOString(),
              content: r.cli_output,
              type: 'info'
            })
          }

          // 显示配置差异
          if (r.diff) {
            device.cliLogs.push({
              timestamp: new Date().toISOString(),
              content: `配置变更:\n${r.diff}`,
              type: 'diff'
            })
          }

          // 显示错误
          if (r.errors && r.errors.length > 0) {
            r.errors.forEach(err => {
              device.cliLogs.push({
                timestamp: new Date().toISOString(),
                content: `错误: ${err}`,
                type: 'error'
              })
            })
          }
        }
      })
    }

    executionStatus.value = result.success ? 'completed' : 'failed'
    clearCache('devices')

    // 保存回滚到历史记录
    if (result.results) {
      // 计算每个设备的回滚状态
      const rollbackDeviceResults = deviceExecutions.value.map(d => {
        const rollbackResult = result.results.find(r => Number(r.device_id) === Number(d.device_id))
        // 如果有回滚结果（说明该设备被执行了回滚），使用回滚结果状态
        // 如果没有回滚结果（说明该设备原部署失败，未执行回滚），标记为 skipped
        if (rollbackResult) {
          return {
            device_id: d.device_id,
            device_name: d.device_name,
            status: rollbackResult.success ? 'completed' : 'failed',
            message: rollbackResult.message || (rollbackResult.success ? '回滚成功' : '回滚失败'),
            rollback_available: false,  // 回滚后不再可回滚
            logs: d.cliLogs
          }
        } else {
          return {
            device_id: d.device_id,
            device_name: d.device_name,
            status: 'skipped',  // 跳过回滚（原部署失败）
            message: '原部署失败，未执行回滚',
            rollback_available: false,
            logs: d.cliLogs
          }
        }
      })

      const rollbackHistory = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        success: result.success,
        engine: deployForm.value.engine,
        mode: 'rollback',  // 标记为回滚操作
        device_names: rollbackDeviceResults.map(d => d.device_name),
        results: result.results,
        deviceResults: rollbackDeviceResults,  // 保存每个设备的详细回滚状态
        cliLogs: rollbackDeviceResults
      }
      deployHistory.value.unshift(rollbackHistory)
      if (deployHistory.value.length > 50) {
        deployHistory.value.pop()
      }
      saveHistoryToStorage()
    }

    if (result.success) {
      ElMessage.success(t('deployRollbackSuccess'))
    } else {
      ElMessage.error(t('deployRollbackFailed'))
    }

  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(t('deployRollbackFailed'))
    }
  }
}

const confirmAbort = async () => {
  try {
    await ElMessageBox.confirm(
      t('deployAbortConfirm'),
      t('deployAbortTitle'),
      { confirmButtonText: t('actionConfirm'), cancelButtonText: t('actionCancel'), type: 'warning' }
    )
    await abortExecution()
  } catch {
    // Cancelled
  }
}

const abortExecution = async () => {
  aborting.value = true
  try {
    await fetch(`/api/deploy/execute/${taskId.value}/abort`, { method: 'POST' })
    executionStatus.value = 'aborted'
    ElMessage.warning(t('deployAborted'))
    closeEventSource()
    stopTimer()
  } catch (error) {
    ElMessage.error(t('deployAbortFailed'))
  } finally {
    aborting.value = false
  }
}

// 审批处理函数
const handleApprovalSubmit = async () => {
  if (!approvalComment.value.trim()) {
    ElMessage.warning(t('deployApprovalCommentRequired'))
    return
  }

  try {
    const response = await fetch(`/api/deploy-approval/${approvalId.value}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment: approvalComment.value })
    })

    if (response.ok) {
      approvalStatus.value = 'approved'
      ElMessage.success(t('deployApproved'))
      // 刷新并开始执行
      await startApprovedDeployment()
    } else {
      ElMessage.error(t('deployApproveFailed'))
    }
  } catch (error) {
    ElMessage.error(t('deployApproveFailed'))
  }
}

const handleRejectionSubmit = async () => {
  if (!rejectionReason.value.trim()) {
    ElMessage.warning(t('deployRejectionReasonRequired'))
    return
  }

  try {
    const response = await fetch(`/api/deploy-approval/${approvalId.value}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: rejectionReason.value })
    })

    if (response.ok) {
      approvalStatus.value = 'rejected'
      ElMessage.warning(t('deployRejected'))
    } else {
      ElMessage.error(t('deployRejectFailed'))
    }
  } catch (error) {
    ElMessage.error(t('deployRejectFailed'))
  }
}

const startApprovedDeployment = async () => {
  // 审批通过后开始执行
  executionStatus.value = 'running'
  startTime.value = Date.now()
  timer = setInterval(() => {
    elapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
  }, 1000)

  // 重新调用部署API
  // 注意：实际实现需要一个新的API端点或在原API中处理
  // 这里简化处理，直接显示执行状态
}

// 打开预约对话框
const openScheduleDialog = () => {
  showPreviewDialog.value = false
  showScheduleDialog.value = true
}

// 从预览确认部署
const confirmDeployFromPreview = async () => {
  showPreviewDialog.value = false
  await confirmDeploy()
}

onMounted(async () => {
  // 加载部署历史
  loadHistory()

  // 依次加载，避免同时触发太多请求
  await loadDevices()
  await new Promise(r => setTimeout(r, 100))
  await loadBackups()
  await new Promise(r => setTimeout(r, 100))
  await loadTemplates()
  await new Promise(r => setTimeout(r, 100))
  loadCompatibleVariables()  // 这个请求失败不影响，可以并行
  loadMaintenanceWindows()   // 这个也不影响，可以并行
})
</script>

<style scoped>
/* ========================================
   使用全局 Theme Token（来自 tokens.css）
   不要重新定义变量，直接使用全局变量
   ======================================== */

.deploy-page {
  padding: 0;
  min-height: 100vh;
  background: var(--bg-primary);
}

/* ========================================
   页面导航栏
   ======================================== */

.page-nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.nav-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.status-tag {
  display: inline-flex !important;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
}

.status-tag :deep(.el-icon) {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.status-tag :deep(.is-loading) {
  display: inline-flex;
  align-items: center;
}

.nav-right {
  display: flex;
  gap: 10px;
}

.nav-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  border: none;
  background: var(--bg-card);
  color: var(--text-secondary);
}

.nav-action-btn :deep(.el-icon) {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.nav-action-btn.secondary {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
}

.nav-action-btn.secondary:hover {
  background: var(--bg-hover);
}

.nav-action-btn.danger {
  background: linear-gradient(135deg, #ef4444 0%, #f87171 100%);
  color: white;
}

.nav-action-btn.danger:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.nav-action-btn.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.nav-action-btn.small {
  padding: 4px 8px;
  font-size: 12px;
  gap: 4px;
}

.nav-action-btn.small :deep(.el-icon) {
  width: 12px;
  height: 12px;
}

/* ========================================
   警告区域
   ======================================== */

.warning-section {
  margin-bottom: 20px;
}

.warning-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px 20px;
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.3);
  border-radius: 12px;
}

.warning-icon {
  font-size: 24px;
  color: var(--color-warning);
}

.warning-content {
  flex: 1;
}

.warning-title {
  font-weight: 600;
  color: var(--color-warning);
  margin-bottom: 4px;
}

.warning-desc {
  font-size: 13px;
  color: var(--text-secondary);
}

/* ========================================
   主内容区域
   ======================================== */

.main-content-area {
  height: calc(100vh - 200px);
}

.full-height {
  height: 100%;
}

.config-column,
.execution-column {
  height: 100%;
}

/* ========================================
   配置面板
   ======================================== */

.config-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.config-panel::-webkit-scrollbar {
  width: 6px;
}

.config-panel::-webkit-scrollbar-track {
  background: transparent;
}

.config-panel::-webkit-scrollbar-thumb {
  background: var(--border-default);
  border-radius: 3px;
}

.config-panel::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}

.panel-header {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--border-subtle);
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

/* ========================================
   表单区域
   ======================================== */

.form-section {
  margin-bottom: 20px;
}

.section-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.section-label.required::after {
  content: ' *';
  color: var(--color-danger);
}

.section-desc {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 5px;
}

/* ========================================
   引擎选择
   ======================================== */

.engine-tag {
  margin-left: 6px;
  font-size: 11px;
}

.engine-tip {
  margin-top: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  background: var(--bg-hover);
}

.engine-tip.safe {
  background: rgba(103, 194, 58, 0.1);
  color: var(--color-success);
}

.napalm-mode-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 6px 10px;
  background: var(--bg-hover);
  border-radius: 4px;
}

.smart-mode-tip {
  margin-top: 8px;
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg-hover);
  border-radius: 4px;
  white-space: nowrap;
}

.smart-mode-tip .tip-icon,
.smart-mode-tip .tip-text {
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}

.mode-radio-group {
  display: flex;
  width: 100%;
  flex-wrap: nowrap;
}

.mode-radio-group :deep(.el-radio-button) {
  flex: 1;
  min-width: 0;
}

.mode-radio-group :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ========================================
   选项样式
   ======================================== */

.backup-option,
.template-option,
.device-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

.backup-name,
.template-name,
.device-name {
  font-weight: 500;
}

.backup-file,
.template-desc,
.device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

.backup-time {
  font-size: 11px;
  color: var(--text-secondary);
}

/* ========================================
   变量区域
   ======================================== */

.variables-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.variable-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.add-var-btn {
  margin-top: 5px;
}

/* ========================================
   操作按钮
   ======================================== */

.actions-section {
  display: flex;
  gap: 10px;
  padding-top: 15px;
  border-top: 1px solid var(--border-subtle);
}

.preview-btn,
.deploy-btn {
  flex: 1;
  justify-content: center;
}

.deploy-btn {
  background: linear-gradient(135deg, #00b894 0%, #55efc4 100%);
  color: white;
}

.deploy-btn:hover:not(.disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 184, 148, 0.3);
}

/* ========================================
   执行面板
   ======================================== */

.execution-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.execution-panel.active {
  border-color: #00b894;
  box-shadow: 0 0 20px rgba(0, 184, 148, 0.1);
}

/* ========================================
   执行概览
   ======================================== */

.execution-overview {
  margin-bottom: 20px;
}

.overview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.overview-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.overview-title .is-loading {
  display: inline-flex;
  align-items: center;
}

.elapsed-time {
  font-size: 13px;
  color: var(--text-secondary);
}

.overview-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* ========================================
   进度统计
   ======================================== */

.progress-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 15px;
  margin-bottom: 15px;
}

.progress-item {
  text-align: center;
  padding: 12px;
  background: var(--bg-hover);
  border-radius: 8px;
}

.progress-item.success {
  background: rgba(103, 194, 58, 0.1);
}

.progress-item.warning {
  background: rgba(230, 162, 60, 0.1);
}

.progress-item.error {
  background: rgba(245, 108, 108, 0.1);
}

.progress-label {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 5px;
}

.progress-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.progress-item.success .progress-value {
  color: var(--color-success);
}

.progress-item.warning .progress-value {
  color: var(--color-warning);
}

.progress-item.error .progress-value {
  color: var(--color-danger);
}

.overall-progress {
  margin-top: 10px;
}

/* ========================================
   设备区域
   ======================================== */

.devices-section {
  margin-bottom: 20px;
}

.section-header {
  margin-bottom: 15px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.device-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.device-card {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.device-card:hover {
  border-color: var(--color-primary);
  background: var(--bg-hover);
}

.device-card.active {
  border-color: #00b894;
  box-shadow: 0 2px 8px rgba(0, 184, 148, 0.2);
  background: var(--bg-hover);
}

.device-card.success {
  border-color: var(--color-success);
  background: rgba(103, 194, 58, 0.1);
}

.device-card.error {
  border-color: var(--color-danger);
  background: rgba(245, 108, 108, 0.1);
}

.device-card.skipped {
  border-color: var(--color-warning);
  background: rgba(230, 162, 60, 0.1);
}

.device-card.running {
  border-color: var(--color-primary);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(64, 158, 255, 0.4); }
  50% { box-shadow: 0 0 0 4px rgba(64, 158, 255, 0); }
}

.device-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.device-info {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.status-icon {
  font-size: 16px;
  margin-top: 2px;
}

.status-icon.success { color: var(--color-success); }
.status-icon.error { color: var(--color-danger); }
.status-icon.running { color: var(--color-primary); }
.status-icon.pending { color: var(--text-secondary); }
.status-icon.skipped { color: var(--color-warning); }

.device-text {
  display: flex;
  flex-direction: column;
}

.device-name {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 13px;
}

.device-ip {
  font-size: 11px;
  color: var(--text-secondary);
}

.device-progress {
  margin-top: 8px;
}

.device-message {
  margin-top: 8px;
  font-size: 11px;
  color: var(--text-secondary);
}

/* ========================================
   CLI 并排布局
   ======================================== */

.cli-section-parallel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 20px;
}

.cli-panel {
  background: var(--bg-card);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  height: 340px;
}

.cli-panel.realtime {
  border-color: var(--color-primary);
}

.cli-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: var(--bg-hover);
  border-bottom: 1px solid var(--border-default);
  height: 40px;
  flex-shrink: 0;
}

.cli-panel.realtime .cli-panel-header {
  background: rgba(64, 158, 255, 0.1);
}

.cli-panel-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.cli-panel-header .el-tag {
  display: inline-flex !important;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 8px;
}

.cli-panel-header .el-tag :deep(.el-icon) {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.cli-panel-header .el-tag .is-loading {
  display: inline-flex;
  align-items: center;
}

.device-badge {
  margin-left: 8px;
  padding: 2px 8px;
  background: rgba(0, 184, 148, 0.15);
  border-radius: 4px;
  font-size: 12px;
  color: #00b894;
}

/* ========================================
   CLI 输出区域 - 终端风格（始终深色）
   ======================================== */

.cli-panel-output {
  background: var(--cli-bg);
  color: var(--cli-text);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 12px 15px;
  flex: 1;
  overflow-y: auto;
}

.cli-empty {
  color: var(--text-muted);
  text-align: center;
  padding: 20px;
}

.cli-line {
  display: flex;
  gap: 10px;
  padding: 2px 0;
  flex-wrap: wrap;
}

.cli-timestamp {
  color: var(--cli-timestamp);
  flex-shrink: 0;
  font-size: 11px;
}

.cli-command {
  color: #4ec9b0;
  font-weight: 500;
}

.cli-content {
  white-space: pre-wrap;
  word-break: break-all;
  flex: 1;
}

.cli-line.command .cli-content { color: #4ec9b0; }
.cli-line.error .cli-content,
.cli-error-text { color: #f48771; }
.cli-line.warning .cli-content { color: #dcdcaa; }
.cli-line.success .cli-content { color: #7ee787; }
.cli-line.diff .cli-content { color: #ce9178; }

.cli-step {
  color: #569cd6;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.cli-diff-inline {
  color: #ce9178;
  white-space: pre-wrap;
  font-size: 11px;
  margin: 4px 0;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  max-width: 100%;
  overflow-x: auto;
}

/* ========================================
   历史记录面板
   ======================================== */

.history-panel {
  border: 1px solid var(--border-default);
}

.history-list {
  background: var(--bg-card);
  padding: 8px;
  flex: 1;
  overflow-y: auto;
}

.history-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 8px;
  background: var(--bg-hover);
  border: 1px solid transparent;
}

.history-item:hover {
  background: var(--bg-hover);
  border-color: var(--color-primary);
}

.history-item.active {
  background: rgba(64, 158, 255, 0.15);
  border-color: var(--color-primary);
}

.history-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.history-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.history-devices {
  font-size: 13px;
  color: var(--text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-status {
  margin-bottom: 4px;
}

.status-summary {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.status-success {
  color: var(--status-active);
}

.status-failed {
  color: var(--status-error);
}

.history-engine {
  display: flex;
  gap: 8px;
}

.engine-tag, .mode-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.mode-tag.rollback {
  background: rgba(230, 162, 60, 0.15);
  color: var(--color-warning);
}

/* ========================================
   动画
   ======================================== */

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* ========================================
   对话框样式
   ======================================== */

.preview-content {
  max-height: 70vh;
  overflow-y: auto;
}

.impact-summary {
  background: var(--bg-hover);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid var(--border-default);
}

.impact-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.impact-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.impact-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.impact-label {
  font-size: 12px;
  color: var(--text-secondary);
}

.impact-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.device-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 16px;
  background: var(--bg-hover);
  border-radius: 8px;
}

.selector-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.device-diff {
  border: 1px solid var(--border-default);
  border-radius: 8px;
  overflow: hidden;
}

.diff-device-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--bg-hover);
  border-bottom: 1px solid var(--border-default);
}

.diff-device-header .device-info h4 {
  margin: 0;
  font-size: 14px;
  color: var(--text-primary);
}

.diff-device-header .device-ip {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ========================================
   预约对话框
   ======================================== */

.schedule-content {
  padding: 10px 0;
}

.schedule-desc {
  margin-bottom: 20px;
  color: var(--text-secondary);
  font-size: 14px;
}

.window-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.window-option {
  width: 100%;
}

.window-option :deep(.el-radio-button__inner) {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 12px 16px;
}

.window-label {
  font-weight: 500;
  font-size: 14px;
  color: var(--text-primary);
}

.window-time {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.schedule-confirmation {
  margin-top: 20px;
}

.dialog-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
</style>