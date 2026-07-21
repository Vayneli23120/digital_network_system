<template>
  <div class="system-help-page">
    <el-card class="hero-card" shadow="never">
      <div class="hero-header">
        <div>
          <h1>{{ t('systemHelpTitle') || '系统架构中心' }}</h1>
          <p>{{ t('systemHelpSubtitle') || '统一展示系统拓扑、模块关系与数据流，便于运维交接和故障分析。' }}</p>
          <div class="meta-row">
            <span>{{ t('systemHelpVersionLabel') || '架构版本' }}: {{ selectedVersionMeta.label }}</span>
            <span>{{ t('systemHelpUpdatedAtLabel') || '最近更新' }}: {{ selectedVersionMeta.updatedAt }}</span>
          </div>
        </div>
        <div class="hero-actions">
          <el-button :type="compareMode ? 'warning' : 'default'" @click="toggleCompare">
            {{ compareMode ? (t('systemHelpExitCompare') || '退出对比') : (t('systemHelpCompare') || '版本对比') }}
          </el-button>
          <el-button @click="refreshDiagram">{{ t('commonRefresh') || '刷新' }}</el-button>
          <el-button @click="printAsPdf">{{ t('systemHelpPrintPdf') || '打印/PDF' }}</el-button>
          <el-button type="primary" @click="openStandalone">{{ t('systemHelpOpenNewTab') || '新窗口打开' }}</el-button>
        </div>
      </div>

      <div class="highlights">
        <div class="highlight-item">{{ t('systemHelpPointFlexible') || '灵活配置: 仅需 Base URL + API Key，可接入任意兼容端点。' }}</div>
        <div class="highlight-item">{{ t('systemHelpPointPlugin') || '即插即用: 支持 OpenAI / Anthropic / Ollama / 本地 OpenAI 兼容服务。' }}</div>
        <div class="highlight-item">{{ t('systemHelpPointAsync') || '异步研判: 规则卡片秒级返回，AI 总结后台生成并自动更新。' }}</div>
      </div>
    </el-card>

    <div class="workspace-grid" v-if="!compareMode">
      <el-card class="catalog-card" shadow="never">
        <template #header>
          <span>{{ t('systemHelpCatalogTitle') || '架构目录' }}</span>
        </template>
        <el-select v-model="selectedVersion" class="version-select" @change="onVersionChange">
          <el-option v-for="version in versionOptions" :key="version.value" :label="version.label" :value="version.value" />
        </el-select>
        <div class="catalog-list">
          <button
            v-for="section in sections"
            :key="section.id"
            class="catalog-item"
            :class="{ active: section.id === selectedSection }"
            @click="jumpToSection(section.id)"
          >
            {{ section.label }}
          </button>
        </div>
      </el-card>

      <el-card class="diagram-card">
        <template #header>
          <div class="diagram-header">
            <span>{{ t('systemHelpDiagramTitle') || '系统全景架构图' }}</span>
            <span class="diagram-tip">{{ t('systemHelpDiagramTip') || '支持缩放与滚动查看' }}</span>
          </div>
        </template>

        <div class="diagram-wrap">
          <iframe
            :key="iframeKey"
            class="diagram-frame"
            :src="diagramUrl"
            title="System Architecture Diagram"
          />
        </div>
      </el-card>
    </div>

    <el-card class="compare-card" v-else shadow="never">
      <template #header>
        <div class="diagram-header">
          <span>{{ t('systemHelpCompareTitle') || '版本对比视图 (v1.0 ↔ v1.1)' }}</span>
          <el-select v-model="compareSection" class="compare-section-select" size="small" @change="onCompareSectionChange">
            <el-option v-for="section in sections" :key="section.id" :label="section.label" :value="section.id" />
          </el-select>
        </div>
      </template>

      <div class="compare-grid">
        <div class="compare-pane">
          <div class="compare-pane-title baseline">{{ baselineVersion.label }}</div>
          <iframe
            :key="`base-${compareKey}`"
            class="compare-frame"
            :src="`${baselineVersion.url}#${compareSection}`"
            title="Architecture Baseline"
          />
        </div>
        <div class="compare-pane">
          <div class="compare-pane-title latest">{{ latestVersion.label }}</div>
          <iframe
            :key="`latest-${compareKey}`"
            class="compare-frame"
            :src="`${latestVersion.url}#${compareSection}`"
            title="Architecture Latest"
          />
        </div>
      </div>

      <div class="change-log">
        <div class="change-log-title">{{ t('systemHelpChangeLogTitle') || '变更清单 (v1.0 → v1.1)' }}</div>
        <div class="change-item" v-for="(item, idx) in changeLog" :key="idx">
          <el-tag :type="item.type" size="small" effect="light">{{ item.tag }}</el-tag>
          <span class="change-text">{{ item.text }}</span>
        </div>
      </div>
    </el-card>

    <el-card class="release-card" shadow="never">
      <template #header>
        <span>{{ t('systemHelpReleaseTitle') || '受控发布说明' }}</span>
      </template>
      <div class="release-grid">
        <div class="release-item">
          <div class="label">{{ t('systemHelpReleaseOwner') || '负责人' }}</div>
          <div class="value">{{ selectedVersionMeta.owner || 'NOC Architecture Team' }}</div>
        </div>
        <div class="release-item">
          <div class="label">{{ t('systemHelpReleaseReviewer') || '审核人' }}</div>
          <div class="value">{{ selectedVersionMeta.reviewer || 'Platform Governance' }}</div>
        </div>
        <div class="release-item">
          <div class="label">{{ t('systemHelpReleaseWindow') || '生效窗口' }}</div>
          <div class="value">{{ selectedVersionMeta.effectiveWindow || '—' }}</div>
        </div>
        <div class="release-item">
          <div class="label">{{ t('systemHelpReleaseSummary') || '变更摘要' }}</div>
          <div class="value">{{ t('systemHelpReleaseSummaryText') || '新增系统内架构中心、版本切换、目录导航与打印导出能力。' }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

const iframeKey = ref(0)
const selectedSection = ref('overall-architecture')
const selectedVersion = ref('v1.1')
const compareMode = ref(false)
const compareSection = ref('overall-architecture')
const compareKey = ref(0)

// Fallback data used until the manifest is loaded (keeps page usable offline)
const versionOptions = ref([
  { value: 'v1.1', label: 'v1.1 (Latest)', url: '/system-architecture.html', updatedAt: '2026-07-21', owner: 'NOC Architecture Team', reviewer: 'Platform Governance', effectiveWindow: '2026-07-21 00:00 - 23:59' },
  { value: 'v1.0', label: 'v1.0 (Baseline)', url: '/system-architecture-v1.0.html', updatedAt: '2026-07-20', owner: 'NOC Architecture Team', reviewer: 'Platform Governance', effectiveWindow: '2026-07-20 00:00 - 23:59' },
])

const sections = ref([
  { id: 'overall-architecture', label: '📐 整体系统架构' },
  { id: 'core-dataflow-offline', label: '🔄 核心数据流：设备离线检测' },
  { id: 'realtime-alert-stream', label: '🚨 实时告警事件流系统' },
  { id: 'health-scoring', label: '💊 设备健康评分算法' },
  { id: 'ai-analysis-system', label: '🤖 AI研判与建议系统' },
  { id: 'fault-ai-triage', label: '🔬 故障创建与AI预判流程' },
  { id: 'cache-strategy', label: '⚡ 多层缓存策略' },
  { id: 'frontend-auto-refresh', label: '🔄 前端自动刷新机制' },
  { id: 'cost-trend-analysis', label: '💰 成本分析与趋势预测' },
  { id: 'deployment-architecture', label: '🏗️ 部署架构' },
])

const changeLog = ref([
  { type: 'success', tag: '新增', text: '系统内“系统架构中心”页面，可直接在系统内查看架构图。' },
  { type: 'success', tag: '新增', text: '架构目录导航、版本切换与打印/PDF 导出能力。' },
  { type: 'warning', tag: '调整', text: 'LLM 集成由 Kimi 专用改为通用端点（Base URL + API Key，可接入任意兼容服务）。' },
  { type: 'info', tag: '优化', text: '告警事件流统一排序，AI 研判改为卡片秒出 + 后台异步生成。' },
])

const baselineVersion = computed(() => {
  return versionOptions.value.find(v => v.value !== selectedVersion.value) || versionOptions.value[versionOptions.value.length - 1]
})

const latestVersion = computed(() => versionOptions.value[0] || {})

const selectedVersionMeta = computed(() => {
  return versionOptions.value.find(v => v.value === selectedVersion.value) || versionOptions.value[0]
})

async function loadManifest() {
  try {
    const res = await fetch('/system-architecture-manifest.json', { cache: 'no-cache' })
    if (!res.ok) return
    const data = await res.json()
    if (Array.isArray(data.versions) && data.versions.length) {
      versionOptions.value = data.versions
      if (!versionOptions.value.some(v => v.value === selectedVersion.value)) {
        selectedVersion.value = versionOptions.value[0].value
      }
    }
    if (Array.isArray(data.sections) && data.sections.length) {
      sections.value = data.sections
    }
    if (Array.isArray(data.changeLog) && data.changeLog.length) {
      changeLog.value = data.changeLog
    }
  } catch (err) {
    // Silent fallback to built-in defaults
    console.warn('Failed to load architecture manifest, using defaults.', err)
  }
}

onMounted(loadManifest)

function toggleCompare() {
  compareMode.value = !compareMode.value
  if (compareMode.value) {
    compareSection.value = selectedSection.value
    compareKey.value += 1
  }
}

function onCompareSectionChange() {
  compareKey.value += 1
}

const diagramUrl = computed(() => {
  const base = selectedVersionMeta.value?.url || '/system-architecture.html'
  const anchor = selectedSection.value ? `#${selectedSection.value}` : ''
  return `${base}${anchor}`
})

function onVersionChange() {
  iframeKey.value += 1
}

function jumpToSection(sectionId) {
  selectedSection.value = sectionId
  iframeKey.value += 1
}

function openStandalone() {
  window.open(diagramUrl.value, '_blank', 'noopener')
}

function refreshDiagram() {
  iframeKey.value += 1
}

function printAsPdf() {
  const iframe = document.querySelector('.diagram-frame')
  if (iframe && iframe.contentWindow) {
    iframe.contentWindow.focus()
    iframe.contentWindow.print()
  }
}
</script>

<style scoped>
.system-help-page {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.hero-card {
  border: 1px solid #e4e7ed;
  background: linear-gradient(130deg, #f5f7fa 0%, #eef6ff 100%);
}

.hero-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.hero-header h1 {
  margin: 0;
  font-size: 22px;
  color: #303133;
}

.hero-header p {
  margin: 8px 0 0;
  color: #606266;
  font-size: 14px;
}

.meta-row {
  margin-top: 10px;
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: #64748b;
  font-size: 12px;
}

.hero-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.highlights {
  margin-top: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
}

.highlight-item {
  background: #ffffff;
  border: 1px solid #e5eaf3;
  border-left: 4px solid #409eff;
  border-radius: 8px;
  padding: 10px 12px;
  color: #475569;
  font-size: 13px;
  line-height: 1.5;
}

.diagram-card {
  border: 1px solid #e4e7ed;
}

.workspace-grid {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 16px;
}

.catalog-card {
  border: 1px solid #e4e7ed;
  height: fit-content;
  position: sticky;
  top: 84px;
}

.version-select {
  width: 100%;
  margin-bottom: 12px;
}

.catalog-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 70vh;
  overflow: auto;
}

.catalog-item {
  text-align: left;
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  padding: 8px 10px;
  background: #fff;
  color: #334155;
  cursor: pointer;
  font-size: 13px;
}

.catalog-item.active,
.catalog-item:hover {
  border-color: #409eff;
  background: #ecf5ff;
  color: #1d4ed8;
}

.diagram-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-weight: 600;
}

.diagram-tip {
  font-size: 12px;
  color: #909399;
  font-weight: 400;
}

.diagram-wrap {
  width: 100%;
  min-height: 74vh;
}

.diagram-frame {
  width: 100%;
  height: 74vh;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
}

.release-card {
  border: 1px solid #e4e7ed;
}

.compare-card {
  border: 1px solid #e4e7ed;
}

.compare-section-select {
  width: 260px;
}

.compare-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.compare-pane {
  display: flex;
  flex-direction: column;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.compare-pane-title {
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.compare-pane-title.baseline {
  background: #909399;
}

.compare-pane-title.latest {
  background: #409eff;
}

.compare-frame {
  width: 100%;
  height: 62vh;
  border: none;
  background: #fff;
}

.change-log {
  margin-top: 16px;
  border-top: 1px dashed #dcdfe6;
  padding-top: 12px;
}

.change-log-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.change-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
}

.change-text {
  font-size: 13px;
  color: #475569;
}

.release-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.release-item {
  border: 1px solid #e5eaf3;
  border-radius: 8px;
  padding: 10px;
  background: #fafcff;
}

.release-item .label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}

.release-item .value {
  font-size: 14px;
  color: #334155;
}

@media (max-width: 900px) {
  .hero-header {
    flex-direction: column;
  }

  .hero-actions {
    width: 100%;
  }

  .hero-actions .el-button {
    flex: 1;
  }

  .workspace-grid {
    grid-template-columns: 1fr;
  }

  .catalog-card {
    position: static;
  }

  .compare-grid {
    grid-template-columns: 1fr;
  }

  .diagram-wrap,
  .diagram-frame {
    min-height: 66vh;
    height: 66vh;
  }
}
</style>
