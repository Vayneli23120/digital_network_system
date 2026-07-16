<template>
  <div class="aop-workspace" v-loading="loading">
    <section class="aop-toolbar">
      <div class="toolbar-context">
        <el-select v-model="selectedYear" class="year-select" :aria-label="t('aopYear')">
          <el-option v-for="year in yearOptions" :key="year" :label="`${year}`" :value="year" />
        </el-select>
        <el-select
          v-model="currentProgramId"
          class="program-select"
          :placeholder="t('aopSelectProgram')"
          :disabled="programs.length === 0"
        >
          <el-option
            v-for="program in programs"
            :key="program.id"
            :label="`${program.name} · v${program.version}`"
            :value="program.id"
          />
        </el-select>
        <el-tag v-if="currentProgram" :type="programStatusType(currentProgram.status)" effect="plain">
          {{ programStatusText(currentProgram.status) }}
        </el-tag>
      </div>
      <div class="toolbar-actions">
        <el-tooltip :content="t('aopRefresh')">
          <el-button :icon="Refresh" circle @click="refreshWorkspace" />
        </el-tooltip>
        <el-button :icon="Plus" @click="openProgramDialog">{{ t('aopNewProgram') }}</el-button>
        <el-button :icon="Calendar" :disabled="!currentProgramId" @click="openWindowDialog()">
          {{ t('aopNewWindow') }}
        </el-button>
        <el-button :icon="Upload" :disabled="!currentProgramId" @click="openImportDialog">
          {{ t('aopImportWindows') }}
        </el-button>
        <el-button type="primary" :icon="DocumentAdd" :disabled="!currentProgramId" @click="openProjectDialog()">
          {{ t('aopNewProject') }}
        </el-button>
        <el-button type="success" :icon="MagicStick" :disabled="!canSchedule" @click="scheduleProjects">
          {{ t('aopSchedule') }}
        </el-button>
      </div>
    </section>

    <el-empty v-if="!currentProgramId && !loading" :description="t('aopEmptyProgram')">
      <el-button type="primary" :icon="Plus" @click="openProgramDialog">{{ t('aopNewProgram') }}</el-button>
    </el-empty>

    <template v-else-if="currentProgramId">
      <section class="aop-summary">
        <div class="summary-item budget">
          <span class="summary-label">{{ t('aopBudget') }}</span>
          <strong>{{ formatMoney(currentProgram?.budget_amount || 0) }}</strong>
          <small>{{ t('aopEstimated') }} {{ formatMoney(estimatedCost) }} · {{ t('aopActual') }} {{ formatMoney(actualCost) }}</small>
        </div>
        <div class="summary-item projects">
          <span class="summary-label">{{ t('aopProjects') }}</span>
          <strong>{{ projects.length }}</strong>
          <small>{{ approvedProjects }} {{ t('aopApproved') }}</small>
        </div>
        <div class="summary-item scheduled">
          <span class="summary-label">{{ t('aopScheduled') }}</span>
          <strong>{{ scheduledProjects }}</strong>
          <small>{{ completedProjects }} {{ t('aopCompleted') }}</small>
        </div>
        <div class="summary-item windows">
          <span class="summary-label">{{ t('aopWindows') }}</span>
          <strong>{{ windows.length }}</strong>
          <small>{{ approvedWindows }} {{ t('aopApproved') }}</small>
        </div>
      </section>

      <section class="calendar-layout">
        <div class="calendar-panel">
          <div class="section-heading">
            <div>
              <h2>{{ t('aopCalendar') }}</h2>
              <span>{{ currentProgram?.name }}</span>
            </div>
            <div class="calendar-legend">
              <span><i class="legend-window"></i>{{ t('aopWindowLegend') }}</span>
              <span><i class="legend-task"></i>{{ t('aopTaskLegend') }}</span>
            </div>
          </div>
          <el-calendar v-model="calendarDate" class="aop-calendar">
            <template #date-cell="{ data }">
              <div
                class="calendar-day"
                :class="{ selected: selectedDay === data.day }"
                @click="selectedDay = data.day"
              >
                <span class="day-number">{{ Number(data.day.slice(-2)) }}</span>
                <div class="day-signals">
                  <span v-if="windowsForDay(data.day).length" class="signal window-signal">
                    {{ windowsForDay(data.day).length }}
                  </span>
                  <span v-if="tasksForDay(data.day).length" class="signal task-signal">
                    {{ tasksForDay(data.day).length }}
                  </span>
                </div>
              </div>
            </template>
          </el-calendar>
        </div>

        <aside class="day-agenda">
          <div class="agenda-date">{{ formatDayTitle(selectedDay) }}</div>
          <div class="agenda-section">
            <h3>{{ t('aopWindows') }}</h3>
            <button
              v-for="window in selectedWindows"
              :key="window.id"
              class="agenda-row window-row"
              @click="openWindowDialog(window)"
            >
              <span class="agenda-marker"></span>
              <span>
                <strong>{{ window.name }}</strong>
                <small>{{ timeRange(window.start_at, window.end_at) }}</small>
              </span>
            </button>
            <div v-if="selectedWindows.length === 0" class="agenda-empty">{{ t('aopNoWindows') }}</div>
          </div>
          <div class="agenda-section">
            <h3>{{ t('pmTasks') }}</h3>
            <button
              v-for="task in selectedTasks"
              :key="task.id"
              class="agenda-row task-row"
              @click="router.push(`/planned-maintenance/tasks/${task.id}`)"
            >
              <span class="agenda-marker"></span>
              <span>
                <strong>{{ task.project_code }} · {{ task.project_name }}</strong>
                <small>{{ timeRange(task.scheduled_date, task.scheduled_end) }}</small>
              </span>
            </button>
            <div v-if="selectedTasks.length === 0" class="agenda-empty">{{ t('aopNoTasks') }}</div>
          </div>
        </aside>
      </section>

      <section class="cost-section" v-if="projects.length">
        <div class="section-heading">
          <div>
            <h2>{{ t('aopCostRollup') }}</h2>
            <span>{{ t('aopEstimated') }} {{ formatMoney(estimatedCost) }} · {{ t('aopActual') }} {{ formatMoney(actualCost) }}</span>
          </div>
        </div>
        <div ref="costChartRef" class="cost-chart"></div>
      </section>

      <section class="portfolio-section">
        <el-tabs v-model="activeTable">
          <el-tab-pane :label="`${t('aopProjects')} (${projects.length})`" name="projects">
            <el-table :data="projects" class="aop-table" row-key="id">
              <el-table-column prop="project_code" :label="t('aopProjectCode')" width="150" />
              <el-table-column prop="name" :label="t('aopProjectName')" min-width="210" show-overflow-tooltip />
              <el-table-column prop="project_type" :label="t('aopProjectType')" width="120">
                <template #default="{ row }">{{ projectTypeText(row.project_type) }}</template>
              </el-table-column>
              <el-table-column prop="device_name" :label="t('pmColDevice')" width="150">
                <template #default="{ row }">{{ row.device_name || '--' }}</template>
              </el-table-column>
              <el-table-column :label="t('aopPlanDate')" width="150">
                <template #default="{ row }">{{ formatDate(row.planned_start) }}</template>
              </el-table-column>
              <el-table-column prop="estimated_cost" :label="t('aopCost')" width="130" align="right">
                <template #default="{ row }">{{ formatMoney(row.estimated_cost) }}</template>
              </el-table-column>
              <el-table-column prop="actual_cost" :label="t('aopActualCost')" width="130" align="right">
                <template #default="{ row }">{{ row.actual_cost != null ? formatMoney(row.actual_cost) : '--' }}</template>
              </el-table-column>
              <el-table-column prop="completion_result" :label="t('aopResult')" width="110">
                <template #default="{ row }">
                  <el-tag v-if="row.completion_result" :type="resultType(row.completion_result)" size="small" effect="plain">
                    {{ resultText(row.completion_result) }}
                  </el-tag>
                  <span v-else>--</span>
                </template>
              </el-table-column>
              <el-table-column prop="approval_status" :label="t('aopApproval')" width="110">
                <template #default="{ row }">
                  <el-tag :type="approvalType(row.approval_status)" size="small" effect="plain">
                    {{ approvalText(row.approval_status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" :label="t('pmColStatus')" width="110">
                <template #default="{ row }">{{ projectStatusText(row.status) }}</template>
              </el-table-column>
              <el-table-column :label="t('pmColAction')" width="80" fixed="right" align="center">
                <template #default="{ row }">
                  <el-tooltip :content="t('pmBtnEdit')">
                    <el-button :icon="Edit" circle text @click="openProjectDialog(row)" />
                  </el-tooltip>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane :label="`${t('aopWindows')} (${windows.length})`" name="windows">
            <el-table :data="windows" class="aop-table" row-key="id">
              <el-table-column prop="name" :label="t('aopWindowName')" min-width="220" />
              <el-table-column prop="window_type" :label="t('aopWindowType')" width="120">
                <template #default="{ row }">{{ windowTypeText(row.window_type) }}</template>
              </el-table-column>
              <el-table-column :label="t('aopWindowRange')" min-width="250">
                <template #default="{ row }">{{ formatDateTime(row.start_at) }} - {{ formatDateTime(row.end_at) }}</template>
              </el-table-column>
              <el-table-column prop="max_parallel_tasks" :label="t('aopCapacity')" width="100" align="center" />
              <el-table-column prop="scheduled_task_count" :label="t('aopScheduled')" width="100" align="center" />
              <el-table-column prop="status" :label="t('pmColStatus')" width="110">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'approved' ? 'success' : 'info'" size="small" effect="plain">
                    {{ approvalText(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column :label="t('pmColAction')" width="80" fixed="right" align="center">
                <template #default="{ row }">
                  <el-tooltip :content="t('pmBtnEdit')">
                    <el-button :icon="Edit" circle text @click="openWindowDialog(row)" />
                  </el-tooltip>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </section>
    </template>

    <el-dialog v-model="programDialog" :title="t('aopNewProgram')" width="520px">
      <el-form :model="programForm" label-position="top">
        <div class="form-grid two-columns">
          <el-form-item :label="t('aopYear')" required>
            <el-input-number v-model="programForm.year" :min="2000" :max="2100" />
          </el-form-item>
          <el-form-item :label="t('aopVersion')" required>
            <el-input-number v-model="programForm.version" :min="1" />
          </el-form-item>
        </div>
        <el-form-item :label="t('aopProgramName')" required>
          <el-input v-model="programForm.name" />
        </el-form-item>
        <div class="form-grid two-columns">
          <el-form-item :label="t('aopOwner')"><el-input v-model="programForm.owner" /></el-form-item>
          <el-form-item :label="t('aopBudget')"><el-input-number v-model="programForm.budget_amount" :min="0" :precision="2" /></el-form-item>
        </div>
        <el-form-item :label="t('pmColStatus')">
          <el-select v-model="programForm.status">
            <el-option :label="programStatusText('draft')" value="draft" />
            <el-option :label="programStatusText('submitted')" value="submitted" />
            <el-option :label="programStatusText('approved')" value="approved" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="programDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitProgram">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="projectDialog" :title="editingProjectId ? t('aopEditProject') : t('aopNewProject')" width="780px">
      <el-form :model="projectForm" label-position="top">
        <div class="form-grid two-columns">
          <el-form-item :label="t('aopProjectCode')" required>
            <el-input v-model="projectForm.project_code" :disabled="Boolean(editingProjectId)" />
          </el-form-item>
          <el-form-item :label="t('aopProjectName')" required><el-input v-model="projectForm.name" /></el-form-item>
          <el-form-item :label="t('aopProjectType')" required>
            <el-select v-model="projectForm.project_type">
              <el-option :label="projectTypeText('replacement')" value="replacement" />
              <el-option :label="projectTypeText('maintenance')" value="maintenance" />
              <el-option :label="projectTypeText('upgrade')" value="upgrade" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('pmColDevice')">
            <el-select v-model="projectForm.device_id" clearable filterable :disabled="projectLocked">
              <el-option v-for="device in devices" :key="device.id" :label="device.name" :value="device.id" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('aopCurrentVersion')"><el-input v-model="projectForm.current_version" /></el-form-item>
          <el-form-item :label="t('aopTargetVersion')"><el-input v-model="projectForm.target_version" /></el-form-item>
          <el-form-item :label="t('aopPlannedStart')" required>
            <el-date-picker v-model="projectForm.planned_start" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" :disabled="projectLocked" />
          </el-form-item>
          <el-form-item :label="t('aopPlannedEnd')">
            <el-date-picker v-model="projectForm.planned_end" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" :disabled="projectLocked" />
          </el-form-item>
          <el-form-item :label="t('aopPreferredWindow')">
            <el-select v-model="projectForm.preferred_window_type" clearable :disabled="projectLocked">
              <el-option v-for="type in windowTypes" :key="type" :label="windowTypeText(type)" :value="type" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('aopHours')">
            <el-input-number v-model="projectForm.estimated_hours" :min="0.25" :step="0.5" :precision="2" :disabled="projectLocked" />
          </el-form-item>
          <el-form-item :label="t('aopCost')"><el-input-number v-model="projectForm.estimated_cost" :min="0" :precision="2" /></el-form-item>
          <el-form-item :label="t('aopOwner')"><el-input v-model="projectForm.owner" /></el-form-item>
          <el-form-item :label="t('aopApproval')">
            <el-select v-model="projectForm.approval_status" :disabled="projectLocked">
              <el-option v-for="status in approvalStatuses" :key="status" :label="approvalText(status)" :value="status" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('aopPriority')">
            <el-select v-model="projectForm.priority"><el-option v-for="value in ['P1', 'P2', 'P3', 'P4']" :key="value" :label="value" :value="value" /></el-select>
          </el-form-item>
          <el-form-item :label="t('aopRisk')">
            <el-select v-model="projectForm.risk_level"><el-option v-for="value in riskLevels" :key="value" :label="riskText(value)" :value="value" /></el-select>
          </el-form-item>
        </div>
        <el-form-item :label="t('aopDependencies')">
          <el-select v-model="projectForm.dependencies" multiple clearable :disabled="projectLocked">
            <el-option v-for="project in dependencyOptions" :key="project.id" :label="`${project.project_code} · ${project.name}`" :value="project.project_code" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('aopJustification')"><el-input v-model="projectForm.business_justification" type="textarea" :rows="2" /></el-form-item>
        <el-form-item :label="t('aopRollback')"><el-input v-model="projectForm.rollback_plan" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="projectDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitProject">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="windowDialog" :title="editingWindowId ? t('aopEditWindow') : t('aopNewWindow')" width="620px">
      <el-form :model="windowForm" label-position="top">
        <div class="form-grid two-columns">
          <el-form-item :label="t('aopWindowName')" required><el-input v-model="windowForm.name" /></el-form-item>
          <el-form-item :label="t('aopWindowType')" required>
            <el-select v-model="windowForm.window_type" :disabled="windowLocked">
              <el-option v-for="type in windowTypes" :key="type" :label="windowTypeText(type)" :value="type" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('aopWindowStart')" required>
            <el-date-picker v-model="windowForm.start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" :disabled="windowLocked" />
          </el-form-item>
          <el-form-item :label="t('aopWindowEnd')" required>
            <el-date-picker v-model="windowForm.end_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" :disabled="windowLocked" />
          </el-form-item>
          <el-form-item :label="t('aopCapacity')">
            <el-input-number v-model="windowForm.max_parallel_tasks" :min="1" :max="100" :disabled="windowLocked" />
          </el-form-item>
          <el-form-item :label="t('aopOwner')"><el-input v-model="windowForm.owner" /></el-form-item>
          <el-form-item :label="t('pmColStatus')">
            <el-select v-model="windowForm.status" :disabled="windowLocked">
              <el-option :label="approvalText('draft')" value="draft" />
              <el-option :label="approvalText('approved')" value="approved" />
              <el-option :label="approvalText('cancelled')" value="cancelled" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item :label="t('pmColNotes')"><el-input v-model="windowForm.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="windowDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitWindow">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="importDialog" :title="t('aopImportWindows')" width="560px">
      <el-form :model="importForm" label-position="top">
        <div class="form-grid two-columns">
          <el-form-item :label="t('aopWindowType')" required>
            <el-select v-model="importForm.window_type">
              <el-option v-for="type in windowTypes" :key="type" :label="windowTypeText(type)" :value="type" />
            </el-select>
          </el-form-item>
          <el-form-item :label="t('aopCapacity')">
            <el-input-number v-model="importForm.max_parallel_tasks" :min="1" :max="100" />
          </el-form-item>
          <el-form-item :label="t('aopWindowStart')">
            <el-time-picker v-model="importForm.start_time" value-format="HH:mm:ss" :clearable="false" />
          </el-form-item>
          <el-form-item :label="t('aopWindowEnd')">
            <el-time-picker v-model="importForm.end_time" value-format="HH:mm:ss" :clearable="false" />
          </el-form-item>
          <el-form-item :label="t('pmColStatus')">
            <el-select v-model="importForm.status">
              <el-option :label="approvalText('draft')" value="draft" />
              <el-option :label="approvalText('approved')" value="approved" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item :label="t('aopImportDates')" required>
          <el-date-picker v-model="importForm.dates" type="dates" value-format="YYYY-MM-DD" :clearable="true" style="width: 100%" />
        </el-form-item>
        <p class="import-hint">{{ t('aopImportHint') }}</p>
      </el-form>
      <template #footer>
        <el-button @click="importDialog = false">{{ t('actionCancel') }}</el-button>
        <el-button type="primary" @click="submitImport">{{ t('actionConfirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Calendar, DocumentAdd, Edit, MagicStick, Plus, Refresh, Upload } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import * as echarts from 'echarts'
import {
  createAopProgram,
  createAopProject,
  createAopWindow,
  createAopWindowsBatch,
  generateAopTasks,
  getAopCalendar,
  getAopProgram,
  getAopPrograms,
  getDevices,
  updateAopProject,
  updateAopWindow
} from '@/api'
import { useI18n } from '@/composables/useI18n'

const { t, currentLang } = useI18n()
const router = useRouter()
const thisYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 7 }, (_, index) => thisYear - 1 + index)
const windowTypes = ['shutdown', 'holiday', 'weekend', 'standard']
const approvalStatuses = ['draft', 'submitted', 'approved', 'rejected']
const riskLevels = ['low', 'medium', 'high', 'critical']

const loading = ref(false)
const selectedYear = ref(thisYear + 1)
const currentProgramId = ref(null)
const programs = ref([])
const programDetail = ref(null)
const devices = ref([])
const calendarData = ref({ windows: [], tasks: [] })
const calendarDate = ref(new Date(thisYear + 1, 0, 1))
const selectedDay = ref(dayjs(calendarDate.value).format('YYYY-MM-DD'))
const loadedMonth = ref('')
const activeTable = ref('projects')

const programDialog = ref(false)
const projectDialog = ref(false)
const windowDialog = ref(false)
const importDialog = ref(false)
const editingProjectId = ref(null)
const editingWindowId = ref(null)
const projectLocked = ref(false)
const windowLocked = ref(false)
const costChartRef = ref(null)
let costChart = null

const programsForYear = () => ({ year: selectedYear.value })
const currentProgram = computed(() => programs.value.find(item => item.id === currentProgramId.value))
const projects = computed(() => programDetail.value?.projects || [])
const windows = computed(() => programDetail.value?.maintenance_windows || [])
const approvedProjects = computed(() => projects.value.filter(item => item.approval_status === 'approved').length)
const scheduledProjects = computed(() => projects.value.filter(item => item.task).length)
const completedProjects = computed(() => projects.value.filter(item => item.status === 'completed').length)
const approvedWindows = computed(() => windows.value.filter(item => item.status === 'approved').length)
const estimatedCost = computed(() => projects.value.reduce((sum, item) => sum + Number(item.estimated_cost || 0), 0))
const actualCost = computed(() => projects.value.reduce((sum, item) => sum + Number(item.actual_cost || 0), 0))
const canSchedule = computed(() => ['approved', 'active'].includes(currentProgram.value?.status) && approvedProjects.value > 0 && approvedWindows.value > 0)
const selectedWindows = computed(() => windowsForDay(selectedDay.value))
const selectedTasks = computed(() => tasksForDay(selectedDay.value))
const dependencyOptions = computed(() => projects.value.filter(item => item.id !== editingProjectId.value))

const programForm = ref({ year: selectedYear.value, version: 1, name: '', status: 'draft', owner: '', budget_amount: 0, currency: 'CNY' })
const emptyProject = () => ({
  project_code: '', name: '', project_type: 'upgrade', device_id: null,
  current_version: '', target_version: '', planned_start: '', planned_end: '',
  preferred_window_type: 'shutdown', estimated_hours: 2, estimated_cost: 0,
  owner: '', priority: 'P3', risk_level: 'medium', approval_status: 'draft',
  dependencies: [], business_justification: '', rollback_plan: ''
})
const emptyWindow = () => ({
  name: '', window_type: 'shutdown', start_at: '', end_at: '', timezone: 'Asia/Shanghai',
  max_parallel_tasks: 1, status: 'draft', owner: '', notes: ''
})
const emptyImport = () => ({
  window_type: 'holiday', max_parallel_tasks: 1, status: 'approved',
  start_time: '00:00:00', end_time: '08:00:00', dates: []
})
const projectForm = ref(emptyProject())
const windowForm = ref(emptyWindow())
const importForm = ref(emptyImport())

const loadPrograms = async () => {
  const data = await getAopPrograms(programsForYear())
  programs.value = data.items || []
  if (!programs.value.some(item => item.id === currentProgramId.value)) {
    currentProgramId.value = programs.value[0]?.id || null
  }
  if (!currentProgramId.value) {
    programDetail.value = null
    calendarData.value = { windows: [], tasks: [] }
  }
}

const loadProgram = async () => {
  if (!currentProgramId.value) return
  programDetail.value = await getAopProgram(currentProgramId.value)
}

const calendarBounds = () => ({
  start_at: dayjs(calendarDate.value).startOf('month').startOf('week').format('YYYY-MM-DDTHH:mm:ss'),
  end_at: dayjs(calendarDate.value).endOf('month').endOf('week').add(1, 'second').format('YYYY-MM-DDTHH:mm:ss')
})

const loadCalendar = async () => {
  if (!currentProgramId.value) return
  calendarData.value = await getAopCalendar({ program_id: currentProgramId.value, ...calendarBounds() })
  loadedMonth.value = dayjs(calendarDate.value).format('YYYY-MM')
}

const refreshWorkspace = async () => {
  loading.value = true
  try {
    await loadPrograms()
    if (currentProgramId.value) await Promise.all([loadProgram(), loadCalendar()])
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('aopLoadFailed'))
  } finally {
    loading.value = false
  }
}

const loadDevices = async () => {
  try {
    const data = await getDevices({ limit: 500 })
    devices.value = data.items || []
  } catch (error) {
    console.error(error)
  }
}

const windowsForDay = (day) => calendarData.value.windows.filter(item => {
  const dayStart = dayjs(day).startOf('day')
  const dayEnd = dayjs(day).endOf('day')
  return dayjs(item.start_at).isBefore(dayEnd) && dayjs(item.end_at).isAfter(dayStart)
})
const tasksForDay = (day) => calendarData.value.tasks.filter(item => {
  const dayStart = dayjs(day).startOf('day')
  const dayEnd = dayjs(day).endOf('day')
  return dayjs(item.scheduled_date).isBefore(dayEnd) && dayjs(item.scheduled_end).isAfter(dayStart)
})

const openProgramDialog = () => {
  programForm.value = { year: selectedYear.value, version: 1, name: t('aopDefaultProgramName', { year: selectedYear.value }), status: 'draft', owner: '', budget_amount: 0, currency: 'CNY' }
  programDialog.value = true
}

const submitProgram = async () => {
  if (!programForm.value.name) return ElMessage.warning(t('pmMsgFillRequired'))
  try {
    const created = await createAopProgram(programForm.value)
    selectedYear.value = created.year
    await loadPrograms()
    currentProgramId.value = created.id
    programDialog.value = false
    ElMessage.success(t('aopSaved'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('aopSaveFailed'))
  }
}

const openProjectDialog = (project = null) => {
  editingProjectId.value = project?.id || null
  projectLocked.value = Boolean(project?.task)
  projectForm.value = project ? {
    ...emptyProject(), ...project,
    planned_start: project.planned_start?.slice(0, 19),
    planned_end: project.planned_end?.slice(0, 19) || '',
    dependencies: project.dependencies || []
  } : emptyProject()
  projectDialog.value = true
}

const submitProject = async () => {
  if (!projectForm.value.project_code || !projectForm.value.name || !projectForm.value.planned_start) {
    return ElMessage.warning(t('pmMsgFillRequired'))
  }
  const device = devices.value.find(item => item.id === projectForm.value.device_id)
  const payload = { ...projectForm.value, device_name: device?.name || null, planned_end: projectForm.value.planned_end || null }
  if (projectLocked.value) {
    delete payload.project_code
    delete payload.device_id
    delete payload.device_name
    delete payload.planned_start
    delete payload.planned_end
    delete payload.preferred_window_type
    delete payload.estimated_hours
    delete payload.dependencies
    delete payload.approval_status
  }
  try {
    if (editingProjectId.value) await updateAopProject(editingProjectId.value, payload)
    else await createAopProject(currentProgramId.value, payload)
    projectDialog.value = false
    await Promise.all([loadProgram(), loadCalendar()])
    ElMessage.success(t('aopSaved'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('aopSaveFailed'))
  }
}

const openWindowDialog = (window = null) => {
  editingWindowId.value = window?.id || null
  windowLocked.value = Boolean(window?.scheduled_task_count)
  windowForm.value = window ? {
    ...emptyWindow(), ...window,
    start_at: window.start_at?.slice(0, 19),
    end_at: window.end_at?.slice(0, 19)
  } : emptyWindow()
  windowDialog.value = true
}

const submitWindow = async () => {
  if (!windowForm.value.name || !windowForm.value.start_at || !windowForm.value.end_at) {
    return ElMessage.warning(t('pmMsgFillRequired'))
  }
  const payload = { ...windowForm.value }
  delete payload.scheduled_task_count
  if (windowLocked.value) {
    delete payload.window_type
    delete payload.start_at
    delete payload.end_at
    delete payload.timezone
    delete payload.max_parallel_tasks
    delete payload.status
  }
  try {
    if (editingWindowId.value) await updateAopWindow(editingWindowId.value, payload)
    else await createAopWindow(currentProgramId.value, payload)
    windowDialog.value = false
    await Promise.all([loadProgram(), loadCalendar()])
    ElMessage.success(t('aopSaved'))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('aopSaveFailed'))
  }
}

const openImportDialog = () => {
  importForm.value = emptyImport()
  importDialog.value = true
}

const submitImport = async () => {
  const form = importForm.value
  if (!form.dates?.length) return ElMessage.warning(t('pmMsgFillRequired'))
  const typeLabel = windowTypeText(form.window_type)
  const windowsPayload = form.dates.map(date => {
    const start = dayjs(`${date}T${form.start_time}`)
    let end = dayjs(`${date}T${form.end_time}`)
    if (!end.isAfter(start)) end = end.add(1, 'day')
    return {
      name: `${typeLabel} ${date}`,
      window_type: form.window_type,
      start_at: start.format('YYYY-MM-DDTHH:mm:ss'),
      end_at: end.format('YYYY-MM-DDTHH:mm:ss'),
      max_parallel_tasks: form.max_parallel_tasks,
      status: form.status
    }
  })
  try {
    const result = await createAopWindowsBatch(currentProgramId.value, windowsPayload)
    importDialog.value = false
    await Promise.all([loadProgram(), loadCalendar()])
    ElMessage.success(t('aopImportResult', { count: result.created || windowsPayload.length }))
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('aopSaveFailed'))
  }
}

const scheduleProjects = async () => {
  try {
    const result = await generateAopTasks(currentProgramId.value)
    const generated = result.generated_task_ids?.length || 0
    const skipped = result.skipped?.length || 0
    ElMessage({ type: skipped ? 'warning' : 'success', message: t('aopScheduleResult', { generated, skipped }) })
    await Promise.all([loadProgram(), loadCalendar()])
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || t('pmMsgGenerateFailed'))
  }
}

const activeLocale = () => currentLang.value === 'zh' ? 'zh-CN' : 'en-US'
const formatMoney = value => new Intl.NumberFormat(activeLocale(), { style: 'currency', currency: currentProgram.value?.currency || 'CNY', maximumFractionDigits: 0 }).format(Number(value || 0))
const formatDate = value => value ? dayjs(value).format('YYYY-MM-DD') : '--'
const formatDateTime = value => value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '--'
const timeRange = (start, end) => `${dayjs(start).format('HH:mm')} - ${dayjs(end).format('HH:mm')}`
const formatDayTitle = day => new Intl.DateTimeFormat(activeLocale(), { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'long' }).format(dayjs(day).toDate())
const programStatusText = status => t(`aopProgramStatus_${status}`)
const programStatusType = status => ({ approved: 'success', active: 'success', submitted: 'warning', closed: 'info' }[status] || 'info')
const projectTypeText = type => t(`aopProjectType_${type}`)
const projectStatusText = status => t(`aopProjectStatus_${status}`)
const windowTypeText = type => t(`aopWindowType_${type}`)
const approvalText = status => t(`aopApproval_${status}`)
const approvalType = status => ({ approved: 'success', submitted: 'warning', rejected: 'danger' }[status] || 'info')
const resultText = value => t(`aopResult_${value}`)
const resultType = value => ({ success: 'success', partial: 'warning', rolled_back: 'danger' }[value] || 'info')
const riskText = value => t(`aopRisk_${value}`)

const renderCostChart = () => {
  if (!costChartRef.value) return
  if (!costChart) costChart = echarts.init(costChartRef.value)
  const items = projects.value
  costChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: [t('aopEstimated'), t('aopActual')], top: 0 },
    grid: { left: 8, right: 16, bottom: 8, top: 36, containLabel: true },
    xAxis: { type: 'category', data: items.map(item => item.project_code), axisLabel: { interval: 0, rotate: items.length > 8 ? 40 : 0 } },
    yAxis: { type: 'value' },
    series: [
      { name: t('aopEstimated'), type: 'bar', itemStyle: { color: '#5b8ff9' }, data: items.map(item => Number(item.estimated_cost || 0)) },
      { name: t('aopActual'), type: 'bar', itemStyle: { color: '#5ad8a6' }, data: items.map(item => item.actual_cost != null ? Number(item.actual_cost) : 0) }
    ]
  }, true)
}

const disposeCostChart = () => {
  if (costChart) { costChart.dispose(); costChart = null }
}

const refreshCostChart = () => {
  nextTick(() => {
    if (!projects.value.length) { disposeCostChart(); return }
    renderCostChart()
  })
}

watch(selectedYear, async year => {
  calendarDate.value = new Date(year, 0, 1)
  selectedDay.value = dayjs(calendarDate.value).format('YYYY-MM-DD')
  await refreshWorkspace()
})
watch(currentProgramId, async (value, oldValue) => {
  if (!value || value === oldValue) return
  loading.value = true
  try { await Promise.all([loadProgram(), loadCalendar()]) } finally { loading.value = false }
})
watch(calendarDate, async value => {
  selectedDay.value = dayjs(value).format('YYYY-MM-DD')
  const month = dayjs(value).format('YYYY-MM')
  if (month !== loadedMonth.value) await loadCalendar()
})
watch(projects, refreshCostChart)
watch(currentLang, refreshCostChart)

const handleResize = () => costChart?.resize()

onMounted(async () => {
  await Promise.all([refreshWorkspace(), loadDevices()])
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  disposeCostChart()
})
</script>

<style scoped>
.aop-workspace { display: flex; flex-direction: column; gap: 16px; }
.aop-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 16px; background: #fff; border: 1px solid #dfe4ea; border-radius: 6px; }
.toolbar-context, .toolbar-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.year-select { width: 100px; }
.program-select { width: 260px; }
.aop-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border: 1px solid #dfe4ea; border-radius: 6px; overflow: hidden; background: #fff; }
.summary-item { min-height: 108px; padding: 18px 20px; display: flex; flex-direction: column; border-left: 3px solid #5b6673; border-right: 1px solid #e7ebef; }
.summary-item:last-child { border-right: 0; }
.summary-item.budget { border-left-color: #157a6e; }
.summary-item.projects { border-left-color: #2563a5; }
.summary-item.scheduled { border-left-color: #4f7d32; }
.summary-item.windows { border-left-color: #b56a1d; }
.summary-label { color: #66717d; font-size: 13px; }
.summary-item strong { margin-top: 5px; color: #17212b; font-size: 28px; line-height: 1.2; }
.summary-item small { margin-top: auto; color: #7b8793; }
.calendar-layout { display: grid; grid-template-columns: minmax(0, 1fr) 300px; min-height: 560px; border: 1px solid #dfe4ea; border-radius: 6px; overflow: hidden; background: #fff; }
.calendar-panel { min-width: 0; }
.section-heading { height: 66px; padding: 0 18px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #e6eaee; }
.section-heading h2 { margin: 0; font-size: 16px; color: #18222d; letter-spacing: 0; }
.section-heading span { color: #77838f; font-size: 12px; }
.calendar-legend { display: flex; gap: 14px; }
.calendar-legend span { display: flex; align-items: center; gap: 5px; }
.calendar-legend i { width: 8px; height: 8px; border-radius: 50%; }
.legend-window { background: #b56a1d; }
.legend-task { background: #2563a5; }
.aop-calendar :deep(.el-calendar__header) { padding: 12px 18px; }
.aop-calendar :deep(.el-calendar__body) { padding: 0 12px 12px; }
.aop-calendar :deep(.el-calendar-day) { height: 66px; padding: 3px; }
.calendar-day { height: 100%; padding: 6px; display: flex; justify-content: space-between; border: 1px solid transparent; }
.calendar-day.selected { border-color: #2563a5; background: #f1f6fb; }
.day-number { color: #37424e; font-size: 12px; }
.day-signals { display: flex; align-items: flex-end; gap: 3px; }
.signal { min-width: 18px; height: 18px; padding: 0 4px; border-radius: 3px; color: #fff; font-size: 10px; line-height: 18px; text-align: center; }
.window-signal { background: #b56a1d; }
.task-signal { background: #2563a5; }
.day-agenda { padding: 18px; border-left: 1px solid #dfe4ea; background: #f8fafb; }
.agenda-date { padding-bottom: 14px; border-bottom: 1px solid #dfe4ea; color: #17212b; font-weight: 700; }
.agenda-section { margin-top: 20px; }
.agenda-section h3 { margin: 0 0 9px; color: #66717d; font-size: 12px; text-transform: uppercase; letter-spacing: 0; }
.agenda-row { width: 100%; margin-bottom: 7px; padding: 9px; display: flex; gap: 9px; border: 1px solid #dfe4ea; border-radius: 4px; background: #fff; text-align: left; cursor: pointer; }
.agenda-row:hover { border-color: #96a5b4; }
.agenda-marker { width: 4px; flex: 0 0 4px; background: #b56a1d; }
.task-row .agenda-marker { background: #2563a5; }
.agenda-row span:last-child { min-width: 0; display: flex; flex-direction: column; }
.agenda-row strong { overflow: hidden; color: #25313c; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.agenda-row small { margin-top: 3px; color: #77838f; }
.agenda-empty { padding: 10px 0; color: #9aa4ae; font-size: 12px; }
.portfolio-section { padding: 0 16px 16px; border: 1px solid #dfe4ea; border-radius: 6px; background: #fff; }
.cost-section { border: 1px solid #dfe4ea; border-radius: 6px; background: #fff; }
.cost-chart { height: 300px; padding: 8px 12px 12px; }
.import-hint { margin: 4px 0 0; color: #77838f; font-size: 12px; }
.aop-table { width: 100%; }
.form-grid { display: grid; gap: 0 16px; }
.two-columns { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.form-grid :deep(.el-select), .form-grid :deep(.el-date-editor), .form-grid :deep(.el-input-number) { width: 100%; }
@media (max-width: 1100px) {
  .aop-toolbar { align-items: flex-start; flex-direction: column; }
  .aop-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .calendar-layout { grid-template-columns: 1fr; }
  .day-agenda { border-top: 1px solid #dfe4ea; border-left: 0; }
}
@media (max-width: 700px) {
  .toolbar-context, .toolbar-actions { width: 100%; }
  .program-select { flex: 1; width: auto; min-width: 180px; }
  .aop-summary { grid-template-columns: 1fr; }
  .summary-item { border-right: 0; border-bottom: 1px solid #e7ebef; }
  .two-columns { grid-template-columns: 1fr; }
  .calendar-layout { min-height: auto; }
  .aop-calendar :deep(.el-calendar-day) { height: 52px; }
}
</style>