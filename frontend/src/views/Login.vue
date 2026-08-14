<template>
  <div class="login-page">
    <div class="login-container">
      <!-- Logo -->
      <div class="login-logo">
        <div class="logo-icon">
          <!-- 固特异轮胎 -->
          <svg class="logo-tire" viewBox="0 0 64 64" aria-hidden="true" xmlns:xlink="http://www.w3.org/1999/xlink">
            <defs>
              <path id="tire-text-arc" d="M 17 32 A 15 15 0 0 1 47 32" />
            </defs>
            <!-- 轮胎主体 -->
            <circle cx="32" cy="32" r="28" fill="#FFD100" />
            <!-- 胎面花纹 -->
            <circle cx="32" cy="32" r="25" fill="none" stroke="#0A2342" stroke-width="5" stroke-dasharray="4.5 4" />
            <!-- 侧壁高光 -->
            <circle cx="32" cy="32" r="19" fill="#FFE9A8" opacity="0.55" />
            <!-- 轮毂 -->
            <circle cx="32" cy="32" r="9" fill="#0A2342" />
            <circle cx="32" cy="32" r="9" fill="none" stroke="#FFD100" stroke-width="1.6" />
            <circle cx="32" cy="32" r="3.2" fill="#FFD100" />
            <!-- GOODYEAR 字样（沿侧壁弧形排布） -->
            <text font-family="Arial, 'Helvetica Neue', sans-serif" font-size="6.6" font-weight="700" letter-spacing="0.4" fill="#0A2342">
              <textPath xlink:href="#tire-text-arc" startOffset="50%" text-anchor="middle">GOODYEAR</textPath>
            </text>
          </svg>
        </div>
        <h1 class="logo-text" :class="{ 'logo-text-en': currentLang === 'en' }">{{ t('loginLogoText') }}</h1>
      </div>

      <!-- 第一步：选择登录方式（可用的本地登录置顶，未开通的 SSO 下移弱化） -->
      <div v-if="stage === 'choose'" class="login-methods">
        <button type="button" class="method-card method-card--primary" @click="stage = 'local'">
          <div class="method-body">
            <h2 class="method-title">{{ t('loginLocalTitle') }}</h2>
            <p class="method-desc">{{ t('loginLocalDesc') }}</p>
          </div>
          <el-icon class="method-arrow"><Right /></el-icon>
        </button>

        <button
          type="button"
          class="method-card"
          :class="{ 'method-card--disabled': !ssoEnabled }"
          @click="handleSsoLogin"
        >
          <div class="method-body">
            <h2 class="method-title">{{ t('loginSsoTitle') }}</h2>
            <p class="method-desc">{{ ssoEnabled ? t('loginSsoDesc') : t('loginSsoDescSoon') }}</p>
            <p v-if="!ssoEnabled" class="method-badge">{{ t('loginSsoComingSoon') }}</p>
          </div>
          <el-icon v-if="ssoEnabled" class="method-arrow"><Right /></el-icon>
        </button>

        <div class="login-error" v-if="errorMsg">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ errorMsg }}</span>
        </div>
      </div>

      <!-- 第二步：本地账号登录 -->
      <el-form
        v-else
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            :placeholder="t('loginUsernamePlaceholder')"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            :placeholder="t('loginPasswordPlaceholder')"
            size="large"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <div class="login-options">
          <el-checkbox v-model="rememberMe" class="remember-checkbox">
            {{ t('loginRememberMe') }}
          </el-checkbox>
          <button type="button" class="forgot-link" @click="handleForgotPassword">
            {{ t('loginForgotPassword') }}
          </button>
        </div>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="locked"
            class="login-btn"
            @click="handleLogin"
          >
            {{ t('loginSubmit') }}
          </el-button>
        </el-form-item>

        <p class="login-security-hint" :class="{ 'login-security-hint--warn': locked || failedAttempts > 0 }">
          <el-icon><Lock /></el-icon>
          <span>{{ securityHint }}</span>
        </p>

        <div class="login-error" v-if="errorMsg">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ errorMsg }}</span>
        </div>

        <button type="button" class="back-link" @click="backToChoose">
          {{ t('loginBackToMethods') }}
        </button>
      </el-form>

      <!-- Language Toggle（选项卡样式） -->
      <div class="login-lang">
        <div class="lang-tabs" role="tablist">
          <button
            :class="['lang-btn', { active: currentLang === 'zh' }]"
            role="tab"
            @click="setLang('zh')"
          >中</button>
          <button
            :class="['lang-btn', { active: currentLang === 'en' }]"
            role="tab"
            @click="setLang('en')"
          >EN</button>
        </div>
      </div>

      <!-- Footer -->
      <div class="login-footer">
        <span>{{ t('brandName') }}</span>
        <span class="login-footer-sep">·</span>
        <button type="button" class="about-link" @click="aboutVisible = true">
          {{ t('loginAbout') }}
        </button>
      </div>

      <!-- 关于（版本信息从登录页移入此处，避免在登录页直接暴露版本号） -->
      <el-dialog v-model="aboutVisible" :title="t('loginAboutTitle')" width="360px" append-to-body>
        <div class="login-about">
          <p class="login-about-name">{{ t('brandName') }}</p>
          <p class="login-about-meta">{{ t('loginVersionLabel') }}：{{ t('appVersion') }}</p>
        </div>
      </el-dialog>
    </div>

    <!-- 固特异品牌背景四层：深海暗流（WebGL 流体）+ 点阵网格 + 飞足字标粒子 + 漂浮飞艇粒子 -->
    <div class="login-bg-layer login-bg-ocean"><OceanBackground /></div>
    <div class="login-bg-layer login-bg-dots"><DotGridBackground /></div>
    <GoodyearParticles class="login-particles" />
    <BlimpParticles class="login-blimp" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { WarningFilled, Right, Lock } from '@element-plus/icons-vue'
import { login, getSsoStatus } from '@/api'
import { useI18n } from '@/composables/useI18n'
import { useAuthStore } from '@/stores/auth'
import OceanBackground from '@/components/OceanBackground.vue'
import DotGridBackground from '@/components/DotGridBackground.vue'
import GoodyearParticles from '@/components/GoodyearParticles.vue'
import BlimpParticles from '@/components/BlimpParticles.vue'

const { t, currentLang, setLang } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const loginFormRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')
const rememberMe = ref(localStorage.getItem('login_remember_username') === '1')
const aboutVisible = ref(false)

// —— 登录失败保护（客户端软锁，叠加后端 15 次/分钟认证限流） ——
const MAX_FAILED_ATTEMPTS = 5
const LOCKOUT_SECONDS = 60
const failedAttempts = ref(0)
const lockedUntil = ref(0)
const lockCountdown = ref(0)
let lockTimer = null
const locked = computed(() => Date.now() < lockedUntil.value)

// 'choose' = 选择登录方式，'local' = 本地账号表单
const stage = ref('choose')

// SSO 状态由后端 /api/auth/sso/status 决定，未开通时入口仍显示但会给出提示
const ssoStatus = ref({ enabled: false, display_name: '', login_url: '/api/auth/sso/login' })
const ssoEnabled = computed(() => ssoStatus.value.enabled === true)

onMounted(async () => {
  try {
    ssoStatus.value = await getSsoStatus()
  } catch (e) {
    // 后端不可用时保持 SSO 入口为"未开通"状态，本地登录仍可用
    ssoStatus.value = { enabled: false, display_name: '', login_url: '/api/auth/sso/login' }
  }

  // 「记住我」：预填上次记住的用户名
  if (rememberMe.value) {
    loginForm.username = localStorage.getItem('login_username') || ''
  }
})

const backToChoose = () => {
  stage.value = 'choose'
  errorMsg.value = ''
}

const handleSsoLogin = () => {
  if (!ssoEnabled.value) {
    errorMsg.value = t('loginSsoNotReadyHint')
    return
  }
  // 授权码流必须整页跳转到身份提供方，不能用 XHR
  window.location.href = ssoStatus.value.login_url || '/api/auth/sso/login'
}

const loginForm = reactive({
  username: '',
  password: ''
})

const loginRules = {
  username: [
    { required: true, message: t('loginUsernameRequired'), trigger: 'blur' }
  ],
  password: [
    { required: true, message: t('loginPasswordRequired'), trigger: 'blur' }
  ]
}

// —— 记住用户名（仅记忆用户名，不存储密码） ——
const persistRememberedUsername = () => {
  if (rememberMe.value) {
    localStorage.setItem('login_remember_username', '1')
    localStorage.setItem('login_username', loginForm.username)
  } else {
    localStorage.removeItem('login_remember_username')
    localStorage.removeItem('login_username')
  }
}

// —— 忘记密码（占位：后续接入自助重置流程） ——
const handleForgotPassword = () => {
  ElMessage.info(t('loginForgotPasswordHint'))
}

// —— 登录失败保护的体验呈现：软锁倒计时 + 剩余次数提示 ——
const securityHint = computed(() => {
  if (locked.value) {
    return t('loginLockedHint').replace('{seconds}', String(lockCountdown.value))
  }
  if (failedAttempts.value > 0) {
    return t('loginRemainingAttempts')
      .replace('{n}', String(failedAttempts.value))
      .replace('{m}', String(MAX_FAILED_ATTEMPTS - failedAttempts.value))
  }
  return t('loginSecurityHint')
})

const handleLockTick = () => {
  const remaining = Math.ceil((lockedUntil.value - Date.now()) / 1000)
  lockCountdown.value = Math.max(0, remaining)
  if (remaining <= 0) {
    clearInterval(lockTimer)
    lockTimer = null
    failedAttempts.value = 0
  }
}

const startLockCountdown = () => {
  if (lockTimer) clearInterval(lockTimer)
  lockCountdown.value = LOCKOUT_SECONDS
  lockTimer = setInterval(handleLockTick, 1000)
}

// 记录一次失败；返回 true 表示本次失败触发了临时锁定
const recordFailedAttempt = () => {
  failedAttempts.value += 1
  if (failedAttempts.value >= MAX_FAILED_ATTEMPTS) {
    lockedUntil.value = Date.now() + LOCKOUT_SECONDS * 1000
    failedAttempts.value = 0
    startLockCountdown()
    return true
  }
  return false
}

const resetFailedAttempts = () => {
  failedAttempts.value = 0
  lockedUntil.value = 0
  lockCountdown.value = 0
  if (lockTimer) {
    clearInterval(lockTimer)
    lockTimer = null
  }
}

/**
 * 验证 JWT Token 格式
 * 确保 token 是有效的 JWT 结构（三段 base64url）
 * 注意：认证关闭模式下的 placeholder token 跳过验证
 */
const validateTokenFormat = (token) => {
  if (!token || typeof token !== 'string') {
    throw new Error('Invalid token format')
  }
  // 认证关闭模式下的 placeholder token，跳过验证
  if (token === 'placeholder_token_auth_disabled') {
    return true
  }
  const parts = token.split('.')
  if (parts.length !== 3) {
    throw new Error('Invalid JWT structure')
  }
  // 验证每段是否为有效的 base64url
  for (const part of parts) {
    if (!part || !/^[A-Za-z0-9_-]+$/.test(part)) {
      throw new Error('Invalid JWT segment')
    }
  }
  return true
}

/**
 * 安全存储 Token
 * - 验证 token 格式
 * - 不在 URL 参数中传递 token
 * - 不在日志中打印 token
 */
const secureStoreToken = (token, username) => {
  validateTokenFormat(token)
  // 存入 auth store（内部写 localStorage，短期方案）
  // 中期目标：后端使用 httpOnly Cookie，前端不再手动管理 token
  authStore.setAuth(token, username)
}

const handleLogin = async () => {
  if (locked.value) return

  try {
    await loginFormRef.value.validate()
    loading.value = true
    errorMsg.value = ''

    const result = await login(loginForm)

    // 安全存储 Token 与登录态（含用户名，优先用后端返回值保持一致）
    try {
      secureStoreToken(result.access_token, result.username || loginForm.username)
    } catch (tokenError) {
      console.error('Token validation failed')
      errorMsg.value = t('loginFailed')
      return
    }

    persistRememberedUsername()
    resetFailedAttempts()

    ElMessage.success(t('loginSuccess'))

    // Redirect to dashboard
    router.push('/')
  } catch (error) {
    // 表单校验未通过（Element Plus validate 以 false reject）
    if (error === false) {
      return
    }

    // 后端认证限流（429）：独立呈现，不计入失败次数，避免双重惩罚
    if (error.response?.status === 429) {
      const retryAfter = error.response?.data?.retry_after
      errorMsg.value = retryAfter
        ? `${t('loginRateLimited')}（${retryAfter} 秒）`
        : t('loginRateLimited')
      return
    }

    const justLocked = recordFailedAttempt()
    if (justLocked) {
      errorMsg.value = t('loginLockedHint').replace('{seconds}', String(LOCKOUT_SECONDS))
    } else if (error.response?.data?.detail) {
      errorMsg.value = error.response.data.detail
    } else {
      errorMsg.value = t('loginFailed')
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #003087 0%, #001F5C 100%);
  position: relative;
  overflow: hidden;
}

/* ===== 登录方式选择（SSO / 本地账号） ===== */
.login-methods {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 8px;
}

/* 登录方式卡片：与面板一致的玻璃质感，hover 时固特异黄描边 */
.method-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 18px 20px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.07);
  color: #fff;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}

.method-card:hover {
  background: rgba(255, 255, 255, 0.13);
  border-color: rgba(255, 209, 0, 0.55);
}

.method-card:active {
  transform: translateY(1px);
}

.method-card:focus-visible {
  outline: 2px solid #ffd100;
  outline-offset: 2px;
}

.method-body {
  flex: 1;
  min-width: 0;
}

.method-title {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.3;
}

.method-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.65);
}

.method-badge {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: #ffd100;
}

/* 可用入口（本地登录）置顶并给予轻微强调 */
.method-card--primary {
  border-color: rgba(255, 209, 0, 0.38);
  background: rgba(255, 255, 255, 0.11);
}

/* 未开通入口（SSO）弱化：降透明度、去 hover 高亮、默认光标 */
.method-card--disabled {
  opacity: 0.55;
  cursor: default;
}

.method-card--disabled:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.14);
}

.method-card--disabled:hover .method-arrow {
  color: rgba(255, 255, 255, 0.55);
}

.method-arrow {
  flex-shrink: 0;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.55);
}

.method-card:hover .method-arrow {
  color: #ffd100;
}

.back-link {
  display: block;
  width: 100%;
  margin-top: 4px;
  padding: 8px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.65);
  font-size: 13px;
  cursor: pointer;
}

.back-link:hover {
  color: #fff;
  text-decoration: underline;
}

/* ===== 背景三层（固特异品牌风） ===== */
.login-bg-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login-bg-ocean {
  z-index: 0;
}

.login-bg-dots {
  z-index: 1;
}

/* 飞足 + 字标粒子层：居中于卡片上方，避开中央不透明登录卡片 */
.login-particles {
  z-index: 2;
  top: max(98px, calc(50vh - 360px));
  left: 50%;
  transform: translate(-50%, -50%);
}

/* 飞艇粒子层：GOODYEAR 字标正下方，从面板前面（Logo 区域）缓缓飞过，始终可见 */
.login-blimp {
  z-index: 11; /* 高于登录卡片（z10）：飞艇在面板前方可见，不遮登录表单，pointer-events none 不拦截操作 */
  top: max(284px, calc(50vh - 174px));
  left: 50%;
  transform: translate(-50%, -50%);
}

.login-container {
  width: 400px;
  max-width: 90vw;
  padding: 40px;
  /* 透明玻璃质感（学习 DeepSeek harness 右侧面板）：深海军蓝玻璃 + 背景模糊 */
  background: rgba(10, 35, 66, 0.45);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  position: relative;
  z-index: 10; /* 卡片置于三层背景之上 */
}

/* 老浏览器（如 chrome63 扫码机）不支持 backdrop-filter：加深底色保证可读性 */
@supports not ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px))) {
  .login-container {
    background: rgba(10, 35, 66, 0.94);
  }
}

.login-logo {
  text-align: center;
  margin-bottom: 30px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #004F9F, #001F3F);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #FFD100;
  font-size: 28px;
  margin-bottom: 16px;
}

.logo-tire {
  width: 42px;
  height: 42px;
  display: block;
}

.logo-text {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.02em;
  margin: 0;
}

/* 英文标题 "Network Automation System" 较长，28px 会换行拉高面板遮挡上方字标：
   缩至 20px 单行显示（复合选择器压过下方 480px 媒体查询） */
.logo-text.logo-text-en {
  font-size: 20px;
  white-space: nowrap;
}

.logo-subtitle {
  font-size: 14px;
  color: #666;
  margin: 8px 0 0;
}

.login-form {
  margin-top: 20px;
}

.login-form .el-form-item {
  margin-bottom: 20px;
}

/* 深色玻璃面板内的输入框（Element Plus 深色适配） */
.login-form :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.16) inset;
  border-radius: 8px;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 0 1px #ffd100 inset;
}

.login-form :deep(.el-input__inner) {
  color: #fff;
}

.login-form :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.4);
}

.login-form :deep(.el-input__icon) {
  color: rgba(255, 255, 255, 0.5);
}

/* 记住我 / 忘记密码 一行 */
.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -6px 0 16px;
}

.login-form :deep(.remember-checkbox .el-checkbox__label) {
  color: rgba(255, 255, 255, 0.78);
  font-size: 13px;
}

.login-form :deep(.remember-checkbox .el-checkbox__inner) {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.35);
}

.forgot-link {
  border: none;
  background: transparent;
  padding: 0;
  color: #ffd100;
  font-size: 13px;
  cursor: pointer;
}

.forgot-link:hover {
  color: #ffe066;
  text-decoration: underline;
}

/* 登录安全提示（限流 / 失败锁定） */
.login-security-hint {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: -8px 0 12px;
  color: rgba(255, 255, 255, 0.45);
  font-size: 12px;
  line-height: 1.5;
}

.login-security-hint .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.login-security-hint--warn {
  color: #ffd100;
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #ffd100, #ffcc00);
  border: none;
  color: #001f5c;
  transition: all 0.3s;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 209, 0, 0.35);
}

.login-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(245, 108, 108, 0.12);
  border: 1px solid rgba(245, 108, 108, 0.35);
  border-radius: 8px;
  color: #ff9d9d;
  font-size: 14px;
}

.login-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 30px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
}

.login-footer-sep {
  color: rgba(255, 255, 255, 0.3);
}

.about-link {
  border: none;
  background: transparent;
  padding: 0;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  cursor: pointer;
}

.about-link:hover {
  color: #fff;
  text-decoration: underline;
}

/* 关于弹窗内容（append-to-body 后仍可命中自身类名） */
.login-about-name {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.login-about-meta {
  margin: 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.65);
}

.login-lang {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

/* 中/EN 选项卡（分段式玻璃 tab，学习 DeepSeek 右侧面板的选项卡样式） */
.lang-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 10px;
}

.lang-btn {
  padding: 6px 20px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.lang-btn:hover {
  color: #fff;
}

.lang-btn.active {
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

@media (max-width: 480px) {
  .login-container {
    padding: 30px 20px;
  }

  .logo-icon {
    width: 48px;
    height: 48px;
    font-size: 22px;
  }

  .logo-text {
    font-size: 22px;
  }
}
</style>