<template>
  <div class="notif-settings-page">
    <div class="page-header">
      <h2>{{ t('notifSettingsTitle') || '通知设置' }}</h2>
      <p class="page-desc">{{ t('notifSettingsDesc') || '监控自动故障统一派发到运维组并通知管理员；超时未处理将逐级升级到部门经理。' }}</p>
    </div>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- ================= 分组与排班 ================= -->
      <el-tab-pane :label="t('notifSettingsGroups') || '分组与排班'" name="groups">
        <div class="groups-layout">
          <div class="groups-left">
            <div class="card-header">
              <span class="card-title">{{ t('notifSettingsGroupList') || '运维分组' }}</span>
              <el-button type="primary" size="small" @click="openGroupDialog()">
                {{ t('notifSettingsNewGroup') || '新建分组' }}
              </el-button>
            </div>
            <el-table :data="groups" highlight-current-row @current-change="selectGroup" v-loading="loadingGroups">
              <el-table-column prop="name" :label="t('notifSettingsGroupName') || '组名'" min-width="110" />
              <el-table-column prop="is_oncall" :label="t('notifSettingsIsOncall') || '值班组'" width="76">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.is_oncall ? 'success' : 'info'">{{ row.is_oncall ? '✓' : '—' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="t('notifSettingsMemberCount') || '成员'" width="66">
                <template #default="{ row }">{{ row.members?.length || 0 }}</template>
              </el-table-column>
              <el-table-column :label="t('notifSettingsActions') || '操作'" width="140">
                <template #default="{ row }">
                  <el-button size="small" @click="openGroupDialog(row)">{{ t('notifSettingsEdit') || '编辑' }}</el-button>
                  <el-button size="small" type="danger" link @click="removeGroup(row)">{{ t('notifSettingsDelete') || '删除' }}</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="groups-right">
            <template v-if="selectedGroup">
              <div class="card-header">
                <span class="card-title">{{ t('notifSettingsMembers') || '成员与组长' }}：{{ selectedGroup.name }}</span>
                <div class="member-add">
                  <el-select v-model="newMemberUserId" :placeholder="t('notifSettingsSelectUser') || '选择用户'" size="small" filterable style="width: 180px">
                    <el-option v-for="u in users" :key="u.id" :label="u.username + (u.email ? ` (${u.email})` : '')" :value="u.id" />
                  </el-select>
                  <el-button size="small" type="primary" :disabled="!newMemberUserId" @click="addMember">
                    {{ t('notifSettingsAddMember') || '添加' }}
                  </el-button>
                </div>
              </div>
              <el-table :data="selectedGroup.members" size="small" v-loading="loadingMembers">
                <el-table-column prop="username" :label="t('notifSettingsUsername') || '用户'" min-width="110" />
                <el-table-column :label="t('notifSettingsRole') || '角色'" width="110">
                  <template #default="{ row }">
                    <el-tag v-if="row.is_leader" type="warning" size="small">{{ t('notifSettingsLeader') || '组长(部门经理)' }}</el-tag>
                    <el-button v-else size="small" @click="setLeader(row)">{{ t('notifSettingsSetLeader') || '设为组长' }}</el-button>
                  </template>
                </el-table-column>
                <el-table-column :label="t('notifSettingsActions') || '操作'" width="80">
                  <template #default="{ row }">
                    <el-button size="small" type="danger" link @click="removeMember(row)">{{ t('notifSettingsDelete') || '移除' }}</el-button>
                  </template>
                </el-table-column>
              </el-table>

              <div class="card-header schedule-header">
                <span class="card-title">{{ t('notifSettingsSchedules') || '值班排班' }}</span>
                <div class="member-add">
                  <el-select v-model="scheduleUserId" :placeholder="t('notifSettingsSelectUser') || '值班人'" size="small" filterable style="width: 150px">
                    <el-option v-for="u in users" :key="u.id" :label="u.username" :value="u.id" />
                  </el-select>
                  <el-date-picker
                    v-model="scheduleRange"
                    type="datetimerange"
                    size="small"
                    :start-placeholder="t('notifSettingsStartAt') || '开始时间'"
                    :end-placeholder="t('notifSettingsEndAt') || '结束时间(可空)'"
                    style="width: 340px"
                  />
                  <el-button size="small" type="primary" :disabled="!scheduleUserId || !scheduleRange" @click="addSchedule">
                    {{ t('notifSettingsAddSchedule') || '添加排班' }}
                  </el-button>
                </div>
              </div>
              <el-table :data="schedules" size="small" v-loading="loadingSchedules">
                <el-table-column prop="username" :label="t('notifSettingsUsername') || '值班人'" width="110" />
                <el-table-column :label="t('notifSettingsStartAt') || '开始'" min-width="150">
                  <template #default="{ row }">{{ formatTime(row.start_at) }}</template>
                </el-table-column>
                <el-table-column :label="t('notifSettingsEndAt') || '结束'" min-width="150">
                  <template #default="{ row }">{{ row.end_at ? formatTime(row.end_at) : '长期' }}</template>
                </el-table-column>
                <el-table-column :label="t('notifSettingsActions') || '操作'" width="80">
                  <template #default="{ row }">
                    <el-button size="small" type="danger" link @click="removeSchedule(row)">{{ t('notifSettingsDelete') || '删除' }}</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <p class="hint-line">{{ t('notifSettingsOncallHint') || '提示：有值班人在岗时，监控自动故障指派给值班人；否则指派给组名、由组内认领。' }}</p>
            </template>
            <el-empty v-else :description="t('notifSettingsSelectGroupHint') || '请选择左侧分组'" />
          </div>
        </div>
      </el-tab-pane>

      <!-- ================= 分发规则 ================= -->
      <el-tab-pane :label="t('notifSettingsRules') || '分发规则'" name="rules">
        <div class="card-header">
          <span class="card-title">{{ t('notifSettingsRulesDesc') || '按来源/设备类型/级别路由到目标组（按优先级匹配，无命中回退运维组）' }}</span>
          <el-button type="primary" size="small" @click="openRuleDialog()">{{ t('notifSettingsNewRule') || '新建规则' }}</el-button>
        </div>
        <el-table :data="rules" v-loading="loadingRules">
          <el-table-column prop="name" :label="t('notifSettingsRuleName') || '规则名'" min-width="180" />
          <el-table-column prop="priority" label="优先级" width="80" />
          <el-table-column :label="t('notifSettingsRuleSource') || '来源'" min-width="130">
            <template #default="{ row }">{{ row.source_types?.length ? row.source_types.join(', ') : '全部' }}</template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsRuleDevice') || '设备类型'" min-width="130">
            <template #default="{ row }">{{ row.device_types?.length ? row.device_types.join(', ') : '全部' }}</template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsRuleSeverity') || '级别'" min-width="130">
            <template #default="{ row }">{{ row.severities?.length ? row.severities.join(', ') : '全部' }}</template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsRuleTarget') || '目标组'" width="110">
            <template #default="{ row }">{{ groupName(row.target_group_id) }}</template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsEnabled') || '启用'" width="70">
            <template #default="{ row }">
              <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '✓' : '—' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsActions') || '操作'" width="130">
            <template #default="{ row }">
              <el-button size="small" @click="openRuleDialog(row)">{{ t('notifSettingsEdit') || '编辑' }}</el-button>
              <el-button size="small" type="danger" link @click="removeRule(row)">{{ t('notifSettingsDelete') || '删除' }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ================= 升级策略 ================= -->
      <el-tab-pane :label="t('notifSettingsEscalation') || '升级策略'" name="escalation">
        <div class="escalation-card">
          <div class="card-header">
            <span class="card-title">{{ t('notifSettingsEscalationTitle') || '默认升级策略（故障未认领/未处理超时逐级升级）' }}</span>
          </div>
          <el-form label-width="280px" v-loading="loadingPolicy">
            <el-form-item :label="t('notifSettingsEscalationEnabled') || '启用升级策略'">
              <el-switch v-model="policyForm.enabled" />
            </el-form-item>
            <el-form-item :label="t('notifSettingsEscalationL2') || 'L2：超时未认领 → 通知运维组全员 + admin'">
              <el-input-number v-model="policyForm.l2Minutes" :min="1" :max="1440" /> <span class="unit">分钟</span>
            </el-form-item>
            <el-form-item :label="t('notifSettingsEscalationL3') || 'L3：超时未处理 → 升级部门经理(组长) + 复盘任务'">
              <el-input-number v-model="policyForm.l3Minutes" :min="1" :max="10080" /> <span class="unit">分钟</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="savePolicy" :loading="savingPolicy">{{ t('notifSettingsSave') || '保存' }}</el-button>
            </el-form-item>
          </el-form>
          <p class="hint-line">{{ t('notifSettingsEscalationHint') || '说明：维修单 SLA 截止超时同样升级到部门经理；每次升级都会记录通知日志，可在通知中心追溯。' }}</p>
        </div>
      </el-tab-pane>

      <!-- ================= 渠道管理 ================= -->
      <el-tab-pane :label="t('notifSettingsChannels') || '渠道管理'" name="channels">
        <div class="card-header">
          <span class="card-title">{{ t('notifSettingsChannelsDesc') || '通知渠道配置（加密入库；每种类型一个）' }}</span>
          <el-button type="primary" size="small" @click="openChannelDialog()">{{ t('notifSettingsNewChannel') || '新建渠道' }}</el-button>
        </div>
        <el-table :data="channels" v-loading="loadingChannels">
          <el-table-column prop="type" :label="t('notifSettingsChannelType') || '类型'" width="120" />
          <el-table-column prop="name" :label="t('notifSettingsChannelName') || '名称'" min-width="130" />
          <el-table-column :label="t('notifSettingsEnabled') || '启用'" width="70">
            <template #default="{ row }">
              <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '✓' : '—' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsChannelConfig') || '已配置敏感项'" min-width="160">
            <template #default="{ row }">
              <template v-for="(v, k) in row.has_secret" :key="k">
                <el-tag v-if="v" size="small" type="warning" style="margin-right: 4px">{{ k }}</el-tag>
              </template>
              <span v-if="!Object.values(row.has_secret || {}).some(Boolean)">—</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsActions') || '操作'" width="200">
            <template #default="{ row }">
              <el-button size="small" @click="openChannelDialog(row)">{{ t('notifSettingsEdit') || '编辑' }}</el-button>
              <el-button size="small" @click="testChannel(row)">{{ t('notifSettingsTest') || '测试' }}</el-button>
              <el-button size="small" type="danger" link @click="removeChannel(row)">{{ t('notifSettingsDelete') || '删除' }}</el-button>
            </template>
          </el-table-column>
        </el-table>
        <p class="hint-line">{{ t('notifSettingsChannelsHint') || '说明：数据库渠道配置优先于 config.yaml；编辑时敏感字段留空表示保留原值。' }}</p>
      </el-tab-pane>

      <!-- ================= 通知策略 ================= -->
      <el-tab-pane :label="t('notifSettingsPolicies') || '通知策略'" name="policies">
        <div class="card-header">
          <span class="card-title">{{ t('notifSettingsPoliciesDesc') || '级别×事件×目标×渠道×模板路由（优先级从小到大，命中第一个）' }}</span>
          <el-button type="primary" size="small" @click="openPolicyDialog()">{{ t('notifSettingsNewPolicy') || '新建策略' }}</el-button>
        </div>
        <el-table :data="policies" v-loading="loadingPolicies">
          <el-table-column prop="name" :label="t('notifSettingsRuleName') || '策略名'" min-width="140" />
          <el-table-column prop="priority" label="优先级" width="70" />
          <el-table-column :label="t('notifSettingsRuleEvent') || '事件'" min-width="140">
            <template #default="{ row }">{{ row.event_types?.length ? row.event_types.join(', ') : '全部' }}</template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsRuleSeverity') || '级别'" min-width="110">
            <template #default="{ row }">{{ row.severities?.length ? row.severities.join(', ') : '全部' }}</template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsRuleTarget') || '目标'" width="90">
            <template #default="{ row }">{{ row.target_type }}</template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsRuleChannels') || '渠道'" min-width="140">
            <template #default="{ row }">{{ (row.channels || []).join(', ') }}</template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsEnabled') || '启用'" width="66">
            <template #default="{ row }">
              <el-tag size="small" :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '✓' : '—' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('notifSettingsActions') || '操作'" width="130">
            <template #default="{ row }">
              <el-button size="small" @click="openPolicyDialog(row)">{{ t('notifSettingsEdit') || '编辑' }}</el-button>
              <el-button size="small" type="danger" link @click="removePolicy(row)">{{ t('notifSettingsDelete') || '删除' }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ================= 发送日志 ================= -->
      <el-tab-pane :label="t('notifSettingsLogs') || '发送日志'" name="logs">
        <div class="log-filters">
          <el-select v-model="logFilter.channel" clearable :placeholder="t('notifSettingsChannelType') || '渠道'" size="small" style="width: 140px">
            <el-option v-for="c in ['inapp','email','wechat_work','dingtalk']" :key="c" :label="c" :value="c" />
          </el-select>
          <el-select v-model="logFilter.status" clearable :placeholder="t('notifSettingsLogStatus') || '状态'" size="small" style="width: 140px">
            <el-option v-for="s in ['sent','failed','suppressed']" :key="s" :label="s" :value="s" />
          </el-select>
          <el-button size="small" type="primary" @click="loadLogs">{{ t('notifSettingsQuery') || '查询' }}</el-button>
          <span class="hint-line" style="margin-left: auto">{{ t('notifSettingsLogsHint') || '全渠道发送审计：谁、何时、渠道、结果、重试' }}</span>
        </div>
        <el-table :data="logs" v-loading="loadingLogs" size="small">
          <el-table-column prop="id" label="ID" width="60" />
          <el-table-column :label="t('notifSettingsLogTime') || '时间'" width="150">
            <template #default="{ row }">{{ row.created_at ? row.created_at.replace('T', ' ').slice(0, 19) : '-' }}</template>
          </el-table-column>
          <el-table-column prop="event_type" :label="t('notifSettingsRuleEvent') || '事件'" width="160" />
          <el-table-column prop="channel" :label="t('notifSettingsChannelType') || '渠道'" width="100" />
          <el-table-column prop="recipient" :label="t('notifSettingsLogRecipient') || '接收方'" min-width="150" />
          <el-table-column prop="title" :label="t('notifSettingsLogTitle') || '标题'" min-width="160" show-overflow-tooltip />
          <el-table-column :label="t('notifSettingsLogStatus') || '状态'" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === 'sent' ? 'success' : row.status === 'suppressed' ? 'info' : 'danger'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="error" :label="t('notifSettingsLogError') || '错误'" min-width="120" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>

      <!-- ================= 治理统计 ================= -->
      <el-tab-pane :label="t('notifSettingsStats') || '治理统计'" name="stats">
        <div class="kpi-row">
          <div class="kpi-card">
            <div class="kpi-value">{{ stats.channels_24h?.length ? (stats.channels_24h.reduce((a, c) => a + c.sent, 0)) : 0 }}</div>
            <div class="kpi-label">{{ t('notifStatsSent24h') || '24h 通知发送' }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value">{{ stats.escalations_7d?.total || 0 }}</div>
            <div class="kpi-label">{{ t('notifStatsEscalation7d') || '7d 升级触发' }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value">{{ stats.open_faults || 0 }}</div>
            <div class="kpi-label">{{ t('notifStatsOpenFaults') || '开放故障' }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value">{{ stats.silenced_open || 0 }}</div>
            <div class="kpi-label">{{ t('notifStatsSilenced') || '静默中(维护窗口)' }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-value">{{ stats.suppressed_open || 0 }}</div>
            <div class="kpi-label">{{ t('notifStatsSuppressed') || '被抑制(根因)' }}</div>
          </div>
        </div>

        <div class="card-header" style="margin-top: 20px">
          <span class="card-title">{{ t('notifStatsChannelTitle') || '渠道成功率（近 24 小时）' }}</span>
          <el-button size="small" @click="loadStats">{{ t('notifSettingsQuery') || '刷新' }}</el-button>
        </div>
        <el-table :data="stats.channels_24h || []" size="small" v-loading="loadingStats">
          <el-table-column prop="channel" :label="t('notifSettingsChannelType') || '渠道'" width="140" />
          <el-table-column prop="sent" :label="t('notifStatsSent') || '成功'" width="90" />
          <el-table-column prop="failed" :label="t('notifStatsFailed') || '失败'" width="90" />
          <el-table-column prop="suppressed" :label="t('notifStatsSuppressedCount') || '抑制'" width="90" />
          <el-table-column :label="t('notifStatsRate') || '成功率'" width="110">
            <template #default="{ row }">
              <el-tag v-if="row.success_rate !== null" size="small" :type="row.success_rate >= 95 ? 'success' : 'warning'">{{ row.success_rate }}%</el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
        </el-table>

        <div class="card-header" style="margin-top: 20px">
          <span class="card-title">{{ t('notifStatsGroupTitle') || '组 MTTA / MTTR（近 7 天）' }}</span>
        </div>
        <el-table :data="stats.groups || []" size="small">
          <el-table-column prop="group_name" :label="t('notifSettingsGroupName') || '组'" min-width="120" />
          <el-table-column prop="total" :label="t('notifStatsTotal') || '故障数'" width="90" />
          <el-table-column prop="open" :label="t('notifStatsOpen') || '未关闭'" width="90" />
          <el-table-column :label="t('notifStatsMtta') || '平均认领(分)'" width="120">
            <template #default="{ row }">{{ row.mtta_min ?? '—' }}</template>
          </el-table-column>
          <el-table-column :label="t('notifStatsMttr') || '平均恢复(时)'" width="120">
            <template #default="{ row }">{{ row.mttr_hours ?? '—' }}</template>
          </el-table-column>
        </el-table>
        <p class="hint-line">{{ t('notifStatsHint') || '升级触发分布（7 天）：' }}
          <span v-for="(v, k) in (stats.escalations_7d?.by_level || {})" :key="k" style="margin-right: 10px">{{ k }} × {{ v }}</span>
          ；当前维护窗口任务 {{ stats.active_maintenance_windows || 0 }} 个
        </p>
      </el-tab-pane>
    </el-tabs>

    <!-- 分组编辑对话框 -->
    <el-dialog v-model="groupDialogVisible" :title="groupForm.id ? (t('notifSettingsEdit') || '编辑分组') : (t('notifSettingsNewGroup') || '新建分组')" width="420px">
      <el-form label-width="90px">
        <el-form-item :label="t('notifSettingsGroupName') || '组名'">
          <el-input v-model="groupForm.name" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsGroupDesc') || '描述'">
          <el-input v-model="groupForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsIsOncall') || '值班组'">
          <el-switch v-model="groupForm.is_oncall" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="groupDialogVisible = false">{{ t('notifSettingsCancel') || '取消' }}</el-button>
        <el-button type="primary" @click="saveGroup">{{ t('notifSettingsSave') || '保存' }}</el-button>
      </template>
    </el-dialog>

    <!-- 分发规则编辑对话框 -->
    <el-dialog v-model="ruleDialogVisible" :title="ruleForm.id ? (t('notifSettingsEdit') || '编辑规则') : (t('notifSettingsNewRule') || '新建规则')" width="520px">
      <el-form label-width="90px">
        <el-form-item :label="t('notifSettingsRuleName') || '规则名'">
          <el-input v-model="ruleForm.name" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsEnabled') || '启用'">
          <el-switch v-model="ruleForm.enabled" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="ruleForm.priority" :min="1" :max="9999" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsRuleSource') || '来源(逗号分隔,空=全部)'">
          <el-input v-model="ruleForm.source_types_text" placeholder="trap, reachability" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsRuleDevice') || '设备类型(逗号分隔,空=全部)'">
          <el-input v-model="ruleForm.device_types_text" placeholder="core_switch, router" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsRuleSeverity') || '级别(逗号分隔,空=全部)'">
          <el-input v-model="ruleForm.severities_text" placeholder="critical, major" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsRuleTarget') || '目标组'">
          <el-select v-model="ruleForm.target_group_id" placeholder="选择组" style="width: 100%">
            <el-option v-for="g in groups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">{{ t('notifSettingsCancel') || '取消' }}</el-button>
        <el-button type="primary" @click="saveRule">{{ t('notifSettingsSave') || '保存' }}</el-button>
      </template>
    </el-dialog>

    <!-- 渠道编辑对话框 -->
    <el-dialog v-model="channelDialogVisible" :title="channelForm.id ? (t('notifSettingsEdit') || '编辑渠道') : (t('notifSettingsNewChannel') || '新建渠道')" width="520px">
      <el-form label-width="120px">
        <el-form-item :label="t('notifSettingsChannelType') || '类型'">
          <el-select v-model="channelForm.type" :disabled="!!channelForm.id" style="width: 100%">
            <el-option v-for="c in ['email','wechat_work','dingtalk','webhook']" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('notifSettingsChannelName') || '名称'">
          <el-input v-model="channelForm.name" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsEnabled') || '启用'">
          <el-switch v-model="channelForm.enabled" />
        </el-form-item>
        <template v-if="channelForm.type === 'email'">
          <el-form-item label="SMTP Host"><el-input v-model="channelForm.config.smtp_host" /></el-form-item>
          <el-form-item label="SMTP Port"><el-input-number v-model="channelForm.config.smtp_port" :min="1" :max="65535" /></el-form-item>
          <el-form-item label="Username"><el-input v-model="channelForm.config.username" :placeholder="channelForm.has_secret?.username ? '已配置（留空保留）' : ''" /></el-form-item>
          <el-form-item label="Password"><el-input v-model="channelForm.config.password" type="password" show-password :placeholder="channelForm.has_secret?.password ? '已配置（留空保留）' : ''" /></el-form-item>
          <el-form-item label="From"><el-input v-model="channelForm.config.from_addr" /></el-form-item>
          <el-form-item label="Recipients(逗号分隔)"><el-input v-model="channelForm.config.recipients_text" /></el-form-item>
        </template>
        <template v-else>
          <el-form-item label="Webhook URL">
            <el-input v-model="channelForm.config.webhook_url" :placeholder="channelForm.has_secret?.webhook_url ? '已配置（留空保留）' : ''" />
          </el-form-item>
          <el-form-item v-if="channelForm.type === 'dingtalk'" label="Secret">
            <el-input v-model="channelForm.config.secret" :placeholder="channelForm.has_secret?.secret ? '已配置（留空保留）' : ''" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="channelDialogVisible = false">{{ t('notifSettingsCancel') || '取消' }}</el-button>
        <el-button type="primary" @click="saveChannel">{{ t('notifSettingsSave') || '保存' }}</el-button>
      </template>
    </el-dialog>

    <!-- 策略编辑对话框 -->
    <el-dialog v-model="policyDialogVisible" :title="policyEditForm.id ? (t('notifSettingsEdit') || '编辑策略') : (t('notifSettingsNewPolicy') || '新建策略')" width="560px">
      <el-form label-width="110px">
        <el-form-item :label="t('notifSettingsRuleName') || '策略名'"><el-input v-model="policyEditForm.name" /></el-form-item>
        <el-form-item :label="t('notifSettingsEnabled') || '启用'"><el-switch v-model="policyEditForm.enabled" /></el-form-item>
        <el-form-item label="优先级"><el-input-number v-model="policyEditForm.priority" :min="1" :max="9999" /></el-form-item>
        <el-form-item :label="t('notifSettingsRuleEvent') || '事件(逗号分隔,空=全部)'">
          <el-input v-model="policyEditForm.event_types_text" placeholder="fault_auto_created, fault_assigned, escalation" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsRuleSeverity') || '级别(逗号分隔,空=全部)'">
          <el-input v-model="policyEditForm.severities_text" placeholder="critical, major" />
        </el-form-item>
        <el-form-item :label="t('notifSettingsRuleTarget') || '目标'">
          <el-select v-model="policyEditForm.target_type" style="width: 130px">
            <el-option label="all(运维组+admin)" value="all" />
            <el-option label="group" value="group" />
            <el-option label="role" value="role" />
            <el-option label="user" value="user" />
          </el-select>
          <el-select v-if="policyEditForm.target_type !== 'all'" v-model="policyEditForm.target_id" :placeholder="policyEditForm.target_type" style="width: 180px; margin-left: 8px">
            <el-option v-for="g in targetGroups" v-if="policyEditForm.target_type === 'group'" :key="g.id" :label="g.name" :value="g.id" />
            <el-option v-for="r in targetRoles" v-else-if="policyEditForm.target_type === 'role'" :key="r.id" :label="r.name" :value="r.id" />
            <el-option v-for="u in targetUsers" v-else :key="u.id" :label="u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('notifSettingsRuleChannels') || '渠道'">
          <el-select v-model="policyEditForm.channels" multiple style="width: 100%">
            <el-option v-for="c in ['inapp','email','wechat_work','dingtalk']" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('notifSettingsPolicyTemplate') || '模板(可选)'">
          <el-select v-model="policyEditForm.template_id" clearable placeholder="不套模板" style="width: 100%">
            <el-option v-for="tpl in templates" :key="tpl.id" :label="tpl.name" :value="tpl.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('notifSettingsRateLimit') || '频控(0=不限)'">
          <el-input-number v-model="policyEditForm.rate_limit_window_s" :min="0" :max="86400" /> 秒内
          <el-input-number v-model="policyEditForm.rate_limit_max" :min="0" :max="1000" style="margin-left: 8px" /> 条
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="policyDialogVisible = false">{{ t('notifSettingsCancel') || '取消' }}</el-button>
        <el-button type="primary" @click="savePolicyItem">{{ t('notifSettingsSave') || '保存' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useI18n } from '@/composables/useI18n'
import {
  getGroups, createGroup, updateGroup, deleteGroup,
  addGroupMember, removeGroupMember,
  getGroupSchedules, createGroupSchedule, deleteGroupSchedule,
  getDispatchRules, createDispatchRule, updateDispatchRule, deleteDispatchRule,
  getEscalationPolicy, updateEscalationPolicy,
  getNotificationChannels, createNotificationChannel, updateNotificationChannel,
  deleteNotificationChannel, testNotificationChannel,
  getNotificationTemplates, getNotificationPolicies,
  createNotificationPolicy, updateNotificationPolicy, deleteNotificationPolicy,
  getNotificationTargets, getNotificationLogs, getNotificationStats,
} from '@/api'
import { getUsers } from '@/api'

const { t } = useI18n()

const activeTab = ref('groups')

// ===== 分组 =====
const groups = ref([])
const users = ref([])
const selectedGroup = ref(null)
const loadingGroups = ref(false)
const loadingMembers = ref(false)
const loadingSchedules = ref(false)
const newMemberUserId = ref(null)
const groupDialogVisible = ref(false)
const groupForm = ref({ id: null, name: '', description: '', is_oncall: true })

const loadGroups = async (keepSelection = false) => {
  loadingGroups.value = true
  try {
    const res = await getGroups()
    groups.value = res.items || []
    if (keepSelection && selectedGroup.value) {
      selectedGroup.value = groups.value.find(g => g.id === selectedGroup.value.id) || null
    } else if (!selectedGroup.value && groups.value.length > 0) {
      selectedGroup.value = groups.value[0]
    }
    if (selectedGroup.value) await loadSchedules(selectedGroup.value.id)
  } catch (e) {
    ElMessage.error(t('notifSettingsLoadFailed') || '加载分组失败')
  } finally {
    loadingGroups.value = false
  }
}

const loadUsers = async () => {
  try {
    const res = await getUsers()
    users.value = res || []
  } catch (e) {
    console.error('加载用户失败:', e)
  }
}

const selectGroup = (row) => {
  if (!row) return
  selectedGroup.value = row
  loadSchedules(row.id)
}

const openGroupDialog = (row = null) => {
  groupForm.value = row
    ? { id: row.id, name: row.name, description: row.description || '', is_oncall: !!row.is_oncall }
    : { id: null, name: '', description: '', is_oncall: true }
  groupDialogVisible.value = true
}

const saveGroup = async () => {
  try {
    if (groupForm.value.id) {
      await updateGroup(groupForm.value.id, groupForm.value)
    } else {
      await createGroup(groupForm.value)
    }
    groupDialogVisible.value = false
    ElMessage.success(t('notifSettingsSaved') || '已保存')
    await loadGroups(true)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || (t('notifSettingsSaveFailed') || '保存失败'))
  }
}

const removeGroup = async (row) => {
  try {
    await ElMessageBox.confirm(
      `${t('notifSettingsConfirmDeleteGroup') || '确定删除分组'}「${row.name}」？成员与排班将一并删除。`,
      t('notifSettingsConfirm') || '确认',
      { type: 'warning' }
    )
    await deleteGroup(row.id)
    if (selectedGroup.value?.id === row.id) selectedGroup.value = null
    ElMessage.success(t('notifSettingsDeleted') || '已删除')
    await loadGroups()
  } catch (e) {
    if (e !== 'cancel' && e?.name !== 'Error') return
    // ElMessageBox cancel：忽略
  }
}

const addMember = async () => {
  if (!selectedGroup.value || !newMemberUserId.value) return
  try {
    await addGroupMember(selectedGroup.value.id, { user_id: newMemberUserId.value, is_leader: false })
    newMemberUserId.value = null
    await loadGroups(true)
    ElMessage.success(t('notifSettingsSaved') || '成员已添加')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || (t('notifSettingsSaveFailed') || '添加失败'))
  }
}

const setLeader = async (row) => {
  try {
    await addGroupMember(selectedGroup.value.id, { user_id: row.user_id, is_leader: true })
    await loadGroups(true)
    ElMessage.success(t('notifSettingsSaved') || '已设为组长')
  } catch (e) {
    ElMessage.error(t('notifSettingsSaveFailed') || '操作失败')
  }
}

const removeMember = async (row) => {
  try {
    await removeGroupMember(selectedGroup.value.id, row.user_id)
    await loadGroups(true)
    ElMessage.success(t('notifSettingsDeleted') || '成员已移除')
  } catch (e) {
    ElMessage.error(t('notifSettingsSaveFailed') || '操作失败')
  }
}

// ===== 排班 =====
const schedules = ref([])
const scheduleUserId = ref(null)
const scheduleRange = ref(null)

const loadSchedules = async (groupId) => {
  loadingSchedules.value = true
  try {
    const res = await getGroupSchedules(groupId)
    schedules.value = res.items || []
  } catch (e) {
    schedules.value = []
  } finally {
    loadingSchedules.value = false
  }
}

const addSchedule = async () => {
  if (!selectedGroup.value || !scheduleUserId.value || !scheduleRange.value) return
  const [start, end] = scheduleRange.value
  try {
    await createGroupSchedule(selectedGroup.value.id, {
      user_id: scheduleUserId.value,
      start_at: toNaiveIso(start),
      end_at: end ? toNaiveIso(end) : null,
      repeat_rule: 'none',
    })
    scheduleUserId.value = null
    scheduleRange.value = null
    await loadSchedules(selectedGroup.value.id)
    ElMessage.success(t('notifSettingsSaved') || '排班已添加')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || (t('notifSettingsSaveFailed') || '添加失败'))
  }
}

const removeSchedule = async (row) => {
  try {
    await deleteGroupSchedule(selectedGroup.value.id, row.id)
    await loadSchedules(selectedGroup.value.id)
    ElMessage.success(t('notifSettingsDeleted') || '排班已删除')
  } catch (e) {
    ElMessage.error(t('notifSettingsSaveFailed') || '操作失败')
  }
}

const toNaiveIso = (d) => {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`
}

const formatTime = (iso) => {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 16)
}

// ===== 分发规则 =====
const rules = ref([])
const loadingRules = ref(false)
const ruleDialogVisible = ref(false)
const ruleForm = ref({})

const groupName = (id) => groups.value.find(g => g.id === id)?.name || '-'

const loadRules = async () => {
  loadingRules.value = true
  try {
    const res = await getDispatchRules()
    rules.value = res.items || []
  } catch (e) {
    ElMessage.error(t('notifSettingsLoadFailed') || '加载规则失败')
  } finally {
    loadingRules.value = false
  }
}

const openRuleDialog = (row = null) => {
  ruleForm.value = row
    ? {
        id: row.id, name: row.name, enabled: row.enabled, priority: row.priority,
        source_types_text: (row.source_types || []).join(', '),
        device_types_text: (row.device_types || []).join(', '),
        severities_text: (row.severities || []).join(', '),
        target_group_id: row.target_group_id,
      }
    : { id: null, name: '', enabled: true, priority: 100, source_types_text: '', device_types_text: '', severities_text: '', target_group_id: null }
  ruleDialogVisible.value = true
}

const splitList = (text) => {
  if (!text) return null
  return text.split(',').map(s => s.trim()).filter(Boolean)
}

const saveRule = async () => {
  const payload = {
    name: ruleForm.value.name,
    enabled: ruleForm.value.enabled,
    priority: ruleForm.value.priority,
    source_types: splitList(ruleForm.value.source_types_text),
    device_types: splitList(ruleForm.value.device_types_text),
    severities: splitList(ruleForm.value.severities_text),
    target_group_id: ruleForm.value.target_group_id,
  }
  try {
    if (ruleForm.value.id) {
      await updateDispatchRule(ruleForm.value.id, payload)
    } else {
      await createDispatchRule(payload)
    }
    ruleDialogVisible.value = false
    ElMessage.success(t('notifSettingsSaved') || '已保存')
    await loadRules()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || (t('notifSettingsSaveFailed') || '保存失败'))
  }
}

const removeRule = async (row) => {
  try {
    await ElMessageBox.confirm(
      `${t('notifSettingsConfirmDeleteRule') || '确定删除规则'}「${row.name}」？`,
      t('notifSettingsConfirm') || '确认',
      { type: 'warning' }
    )
    await deleteDispatchRule(row.id)
    await loadRules()
    ElMessage.success(t('notifSettingsDeleted') || '已删除')
  } catch (e) {
    // 取消
  }
}

// ===== 升级策略 =====
const policyForm = ref({ enabled: true, l2Minutes: 15, l3Minutes: 30 })
const loadingPolicy = ref(false)
const savingPolicy = ref(false)

const loadPolicy = async () => {
  loadingPolicy.value = true
  try {
    const res = await getEscalationPolicy()
    policyForm.value.enabled = !!res.enabled
    const l2 = (res.levels || []).find(x => x.level === 2)
    const l3 = (res.levels || []).find(x => x.level === 3)
    policyForm.value.l2Minutes = l2?.timeout_minutes ?? 15
    policyForm.value.l3Minutes = l3?.timeout_minutes ?? 30
  } catch (e) {
    console.error('加载升级策略失败:', e)
  } finally {
    loadingPolicy.value = false
  }
}

const savePolicy = async () => {
  savingPolicy.value = true
  try {
    await updateEscalationPolicy({
      enabled: policyForm.value.enabled,
      levels: [
        { level: 2, timeout_minutes: policyForm.value.l2Minutes, targets: ['group'], create_review: false },
        { level: 3, timeout_minutes: policyForm.value.l3Minutes, targets: ['leader', 'admin'], create_review: true },
      ],
    })
    ElMessage.success(t('notifSettingsSaved') || '已保存')
  } catch (e) {
    ElMessage.error(t('notifSettingsSaveFailed') || '保存失败')
  } finally {
    savingPolicy.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadGroups(), loadUsers(), loadRules(), loadPolicy(), loadChannels(), loadPolicies(), loadTemplates(), loadTargets(), loadLogs(), loadStats()])
})

// ===== 渠道管理（二期） =====
const channels = ref([])
const loadingChannels = ref(false)
const channelDialogVisible = ref(false)
const channelForm = ref({})

const loadChannels = async () => {
  loadingChannels.value = true
  try {
    const res = await getNotificationChannels()
    channels.value = res.items || []
  } catch (e) {
    console.error('加载渠道失败:', e)
  } finally {
    loadingChannels.value = false
  }
}

const openChannelDialog = (row = null) => {
  channelForm.value = row
    ? {
        id: row.id, type: row.type, name: row.name, enabled: row.enabled,
        has_secret: row.has_secret || {},
        config: {
          smtp_host: row.config?.smtp_host || '',
          smtp_port: row.config?.smtp_port || 587,
          use_tls: true,
          username: '', password: '',
          from_addr: row.config?.from_addr || '',
          recipients_text: (row.config?.recipients || []).join(', '),
          webhook_url: '',
          secret: '',
        },
      }
    : { id: null, type: 'email', name: '', enabled: true, has_secret: {}, config: { smtp_host: '', smtp_port: 587, use_tls: true, username: '', password: '', from_addr: '', recipients_text: '', webhook_url: '', secret: '' } }
  channelDialogVisible.value = true
}

const saveChannel = async () => {
  const cfg = { ...channelForm.value.config }
  const payload = {
    type: channelForm.value.type,
    name: channelForm.value.name,
    enabled: channelForm.value.enabled,
  }
  const configPayload = {}
  if (payload.type === 'email') {
    configPayload.smtp_host = cfg.smtp_host || ''
    configPayload.smtp_port = cfg.smtp_port
    configPayload.use_tls = true
    if (cfg.username) configPayload.username = cfg.username
    if (cfg.password) configPayload.password = cfg.password
    configPayload.from_addr = cfg.from_addr || ''
    configPayload.recipients = (cfg.recipients_text || '').split(',').map(s => s.trim()).filter(Boolean)
  } else {
    if (cfg.webhook_url) configPayload.webhook_url = cfg.webhook_url
    if (cfg.secret) configPayload.secret = cfg.secret
  }
  try {
    if (channelForm.value.id) {
      await updateNotificationChannel(channelForm.value.id, { name: payload.name, enabled: payload.enabled, config: configPayload })
    } else {
      await createNotificationChannel({ ...payload, config: configPayload })
    }
    channelDialogVisible.value = false
    ElMessage.success(t('notifSettingsSaved') || '已保存')
    await loadChannels()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || (t('notifSettingsSaveFailed') || '保存失败'))
  }
}

const testChannel = async (row) => {
  try {
    const res = await testNotificationChannel(row.id)
    if (res.ok) {
      ElMessage.success(t('notifSettingsTestOk') || '渠道测试发送成功')
    } else {
      ElMessage.warning(res.detail || (t('notifSettingsTestFailed') || '渠道测试发送失败'))
    }
  } catch (e) {
    ElMessage.error(t('notifSettingsTestFailed') || '渠道测试发送失败')
  }
}

const removeChannel = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('notifSettingsConfirmDeleteChannel') || '确定删除渠道'}「${row.name}」？`, t('notifSettingsConfirm') || '确认', { type: 'warning' })
    await deleteNotificationChannel(row.id)
    await loadChannels()
    ElMessage.success(t('notifSettingsDeleted') || '已删除')
  } catch (e) { /* 取消 */ }
}

// ===== 通知策略（二期） =====
const policies = ref([])
const templates = ref([])
const targetGroups = ref([])
const targetRoles = ref([])
const targetUsers = ref([])
const loadingPolicies = ref(false)
const policyDialogVisible = ref(false)
const policyEditForm = ref({})

const loadPolicies = async () => {
  loadingPolicies.value = true
  try {
    const res = await getNotificationPolicies()
    policies.value = res.items || []
  } catch (e) {
    console.error('加载策略失败:', e)
  } finally {
    loadingPolicies.value = false
  }
}

const loadTemplates = async () => {
  try {
    const res = await getNotificationTemplates()
    templates.value = res.items || []
  } catch (e) { console.error('加载模板失败:', e) }
}

const loadTargets = async () => {
  try {
    const res = await getNotificationTargets()
    targetGroups.value = res.groups || []
    targetRoles.value = res.roles || []
    targetUsers.value = res.users || []
  } catch (e) { console.error('加载目标失败:', e) }
}

const openPolicyDialog = (row = null) => {
  policyEditForm.value = row
    ? {
        id: row.id, name: row.name, enabled: row.enabled, priority: row.priority,
        event_types_text: (row.event_types || []).join(', '),
        severities_text: (row.severities || []).join(', '),
        target_type: row.target_type, target_id: row.target_id,
        channels: row.channels || [], template_id: row.template_id,
        rate_limit_window_s: row.rate_limit_window_s || 0, rate_limit_max: row.rate_limit_max || 0,
      }
    : { id: null, name: '', enabled: true, priority: 100, event_types_text: '', severities_text: '', target_type: 'all', target_id: null, channels: ['inapp', 'email', 'wechat_work', 'dingtalk'], template_id: null, rate_limit_window_s: 0, rate_limit_max: 0 }
  policyDialogVisible.value = true
}

const savePolicyItem = async () => {
  const f = policyEditForm.value
  const payload = {
    name: f.name, enabled: f.enabled, priority: f.priority,
    severities: splitList(f.severities_text),
    event_types: splitList(f.event_types_text),
    target_type: f.target_type, target_id: f.target_type === 'all' ? null : f.target_id,
    channels: f.channels, template_id: f.template_id,
    rate_limit_window_s: f.rate_limit_window_s, rate_limit_max: f.rate_limit_max,
  }
  try {
    if (f.id) {
      await updateNotificationPolicy(f.id, payload)
    } else {
      await createNotificationPolicy(payload)
    }
    policyDialogVisible.value = false
    ElMessage.success(t('notifSettingsSaved') || '已保存')
    await loadPolicies()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || (t('notifSettingsSaveFailed') || '保存失败'))
  }
}

const removePolicy = async (row) => {
  try {
    await ElMessageBox.confirm(`${t('notifSettingsConfirmDeletePolicy') || '确定删除策略'}「${row.name}」？`, t('notifSettingsConfirm') || '确认', { type: 'warning' })
    await deleteNotificationPolicy(row.id)
    await loadPolicies()
    ElMessage.success(t('notifSettingsDeleted') || '已删除')
  } catch (e) { /* 取消 */ }
}

// ===== 发送日志（二期） =====
const logs = ref([])
const loadingLogs = ref(false)
const logFilter = ref({ channel: '', status: '' })

const loadLogs = async () => {
  loadingLogs.value = true
  try {
    const params = { limit: 200 }
    if (logFilter.value.channel) params.channel = logFilter.value.channel
    if (logFilter.value.status) params.status = logFilter.value.status
    const res = await getNotificationLogs(params)
    logs.value = res.items || []
  } catch (e) {
    console.error('加载日志失败:', e)
  } finally {
    loadingLogs.value = false
  }
}

// ===== 治理统计（三期） =====
const stats = ref({})
const loadingStats = ref(false)

const loadStats = async () => {
  loadingStats.value = true
  try {
    const res = await getNotificationStats()
    stats.value = res
  } catch (e) {
    console.error('加载统计失败:', e)
  } finally {
    loadingStats.value = false
  }
}
</script>

<style scoped>
.notif-settings-page {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}
.page-header h2 {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
}
.page-desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--text-secondary);
}
.groups-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  align-items: start;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 12px;
  flex-wrap: wrap;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}
.member-add {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}
.schedule-header {
  margin-top: 22px;
}
.hint-line {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
}
.unit {
  margin-left: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}
.escalation-card {
  max-width: 640px;
}
.kpi-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}
.kpi-card {
  flex: 1;
  min-width: 130px;
  padding: 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  text-align: center;
}
.kpi-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--accent-primary);
}
.kpi-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
