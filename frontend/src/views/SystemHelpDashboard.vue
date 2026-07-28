<template>
  <div class="system-help-page">
    <!-- 子导航 -->
    <el-card class="sub-nav-card" shadow="never">
      <div class="sub-nav">
        <router-link to="/system-help" class="sub-nav-item">{{ t('systemHelpSubNavArch') }}</router-link>
        <router-link to="/system-help/dashboard" class="sub-nav-item active">{{ t('systemHelpSubNavDashboard') }}</router-link>
        <span class="sub-nav-spacer" />
        <el-button size="small" type="primary" @click="openStandalone">{{ t('systemHelpDbOpenStandalone') }}</el-button>
      </div>
    </el-card>

    <!-- Hero -->
    <el-card class="db-hero-card" shadow="never">
      <div class="db-hero">
        <h1>{{ t('systemHelpDbTitle') }}</h1>
        <p>{{ t('systemHelpDbSubtitle') }}</p>
      </div>
    </el-card>

    <!-- 设计初衷与背景 -->
    <el-card class="db-section-card" shadow="never">
      <div class="section-header">
        <span class="section-icon">🎯</span>
        <span>{{ t('systemHelpDbBackgroundTitle') }}</span>
      </div>
      <div class="db-section-body">
        <p>{{ t('systemHelpDbBackgroundP1') }}</p>
        <p>{{ t('systemHelpDbBackgroundP2') }}</p>
        <div class="db-highlight-box">
          <div class="db-highlight-item">
            <span class="db-highlight-num">01</span>
            <span>{{ t('systemHelpDbBackgroundQ1') }}</span>
          </div>
          <div class="db-highlight-item">
            <span class="db-highlight-num">02</span>
            <span>{{ t('systemHelpDbBackgroundQ2') }}</span>
          </div>
          <div class="db-highlight-item">
            <span class="db-highlight-num">03</span>
            <span>{{ t('systemHelpDbBackgroundQ3') }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 设计理论依据 -->
    <el-card class="db-section-card" shadow="never">
      <div class="section-header">
        <span class="section-icon">📐</span>
        <span>{{ t('systemHelpDbTheoryTitle') }}</span>
      </div>
      <div class="db-section-body">
        <div class="db-theory-item">
          <div class="db-theory-num">①</div>
          <div class="db-theory-content">
            <strong>{{ t('systemHelpDbTheory1Title') }}</strong>
            <p>{{ t('systemHelpDbTheory1Desc') }}</p>
          </div>
        </div>
        <div class="db-theory-item">
          <div class="db-theory-num">②</div>
          <div class="db-theory-content">
            <strong>{{ t('systemHelpDbTheory2Title') }}</strong>
            <p>{{ t('systemHelpDbTheory2Desc') }}</p>
          </div>
        </div>
        <div class="db-theory-item">
          <div class="db-theory-num">③</div>
          <div class="db-theory-content">
            <strong>{{ t('systemHelpDbTheory3Title') }}</strong>
            <p>{{ t('systemHelpDbTheory3Desc') }}</p>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 呈现结果 -->
    <el-card class="db-section-card db-result-card" shadow="never">
      <div class="section-header">
        <span class="section-icon">✨</span>
        <span>{{ t('systemHelpDbResultTitle') }}</span>
      </div>
      <div class="db-section-body">
        <p>{{ t('systemHelpDbResultP1') }}</p>
        <div class="db-result-grid">
          <div class="db-result-item">
            <div class="db-result-icon">🟢🟡🔴</div>
            <div class="db-result-text">
              <strong>{{ t('systemHelpDbResultColorTitle') }}</strong>
              <p>{{ t('systemHelpDbResultColorDesc') }}</p>
            </div>
          </div>
          <div class="db-result-item">
            <div class="db-result-icon">🤖</div>
            <div class="db-result-text">
              <strong>{{ t('systemHelpDbResultAiTitle') }}</strong>
              <p>{{ t('systemHelpDbResultAiDesc') }}</p>
            </div>
          </div>
          <div class="db-result-item">
            <div class="db-result-icon">📈</div>
            <div class="db-result-text">
              <strong>{{ t('systemHelpDbResultTrendTitle') }}</strong>
              <p>{{ t('systemHelpDbResultTrendDesc') }}</p>
            </div>
          </div>
        </div>
        <div class="db-summary-quote">
          <p>{{ t('systemHelpDbResultTagline') }}</p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()

function openStandalone() {
  window.open('/system-help/dashboard', '_blank', 'noopener')
}
</script>

<style scoped>
.system-help-page {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== Sub Navigation ===== */
.sub-nav-card {
  border: 1px solid #e4e7ed;
}
.sub-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sub-nav-item {
  padding: 6px 18px;
  border-radius: 6px;
  font-size: 14px;
  color: #606266;
  text-decoration: none;
  transition: all 0.2s;
}
.sub-nav-item:hover {
  background: #ecf5ff;
  color: #409eff;
}
.sub-nav-item.active {
  background: #409eff;
  color: #fff;
}
.sub-nav-spacer {
  flex: 1;
}

/* ===== Hero ===== */
.db-hero-card {
  border: 1px solid #e4e7ed;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
}
.db-hero h1 {
  margin: 0;
  font-size: 24px;
  color: #1e40af;
}
.db-hero p {
  margin: 10px 0 0;
  color: #475569;
  font-size: 15px;
  line-height: 1.7;
}

/* ===== Section Cards ===== */
.db-section-card {
  border: 1px solid #e4e7ed;
}
.db-section-body p {
  color: #475569;
  font-size: 14px;
  line-height: 1.85;
  margin: 10px 0;
}

/* ===== Three Questions Highlight ===== */
.db-highlight-box {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin: 16px 0 4px;
}
.db-highlight-item {
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 10px;
  padding: 16px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 14px;
  color: #1e40af;
  line-height: 1.6;
}
.db-highlight-num {
  font-size: 20px;
  font-weight: 800;
  color: #38bdf8;
  flex-shrink: 0;
  line-height: 1;
}

/* ===== Theory Items ===== */
.db-theory-item {
  display: flex;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid #e8ecf4;
}
.db-theory-item:last-child {
  border-bottom: none;
}
.db-theory-num {
  font-size: 22px;
  font-weight: 700;
  color: #409eff;
  flex-shrink: 0;
  line-height: 1.4;
}
.db-theory-content strong {
  display: block;
  color: #303133;
  font-size: 15px;
  margin-bottom: 4px;
}
.db-theory-content p {
  margin: 0;
  color: #475569;
  font-size: 14px;
  line-height: 1.75;
}

/* ===== Result Section ===== */
.db-result-card {
  background: linear-gradient(135deg, #f5f3ff 0%, #eef2ff 100%);
}
.db-result-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
  margin: 16px 0;
}
.db-result-item {
  display: flex;
  gap: 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #e0e7ff;
  border-radius: 10px;
  padding: 16px;
}
.db-result-icon {
  font-size: 28px;
  flex-shrink: 0;
  line-height: 1.2;
}
.db-result-text strong {
  display: block;
  color: #4338ca;
  font-size: 15px;
  margin-bottom: 4px;
}
.db-result-text p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.7;
}
.db-summary-quote {
  margin-top: 12px;
  background: rgba(255, 255, 255, 0.6);
  border-left: 4px solid #6366f1;
  border-radius: 6px;
  padding: 14px 18px;
}
.db-summary-quote p {
  margin: 0;
  color: #4338ca;
  font-size: 15px;
  line-height: 1.7;
  font-weight: 500;
}

/* ===== Common ===== */
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}
.section-icon {
  font-size: 20px;
  line-height: 1;
}

@media (max-width: 768px) {
  .system-help-page {
    padding: 12px;
  }
  .db-highlight-box {
    grid-template-columns: 1fr;
  }
}
</style>
