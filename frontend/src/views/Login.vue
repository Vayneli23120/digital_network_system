<template>
  <div class="login-page">
    <div class="login-container">
      <!-- Logo -->
      <div class="login-logo">
        <div class="logo-icon">
          <el-icon><Monitor /></el-icon>
        </div>
        <h1 class="logo-text">NAS</h1>
        <p class="logo-subtitle">{{ t('brandSubtitle') }}</p>
      </div>

      <!-- 第一步：选择登录方式 -->
      <div v-if="stage === 'choose'" class="login-methods">
        <button type="button" class="method-card" @click="handleSsoLogin">
          <div class="method-body">
            <h2 class="method-title">{{ ssoDisplayName }}</h2>
            <p class="method-desc">{{ t('loginSsoDesc') }}</p>
            <p v-if="!ssoEnabled" class="method-badge">{{ t('loginSsoNotReady') }}</p>
          </div>
          <el-icon class="method-arrow"><Right /></el-icon>
        </button>

        <button type="button" class="method-card" @click="stage = 'local'">
          <div class="method-body">
            <h2 class="method-title">{{ t('loginLocalTitle') }}</h2>
            <p class="method-desc">{{ t('loginLocalDesc') }}</p>
          </div>
          <el-icon class="method-arrow"><Right /></el-icon>
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

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            {{ t('loginSubmit') }}
          </el-button>
        </el-form-item>

        <div class="login-error" v-if="errorMsg">
          <el-icon><WarningFilled /></el-icon>
          <span>{{ errorMsg }}</span>
        </div>

        <button type="button" class="back-link" @click="backToChoose">
          {{ t('loginBackToMethods') }}
        </button>
      </el-form>

      <!-- Footer -->
      <div class="login-footer">
        <span>{{ t('brandName') }} v1.5</span>
      </div>
    </div>

    <!-- Background decoration -->
    <div class="login-bg-pattern"></div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor, WarningFilled, Right } from '@element-plus/icons-vue'
import { login, getSsoStatus } from '@/api'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const router = useRouter()

const loginFormRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')

// 'choose' = 选择登录方式，'local' = 本地账号表单
const stage = ref('choose')

// SSO 状态由后端 /api/auth/sso/status 决定，未开通时入口仍显示但会给出提示
const ssoStatus = ref({ enabled: false, display_name: '', login_url: '/api/auth/sso/login' })
const ssoEnabled = computed(() => ssoStatus.value.enabled === true)
const ssoDisplayName = computed(() => ssoStatus.value.display_name || t('loginSsoTitle'))

onMounted(async () => {
  try {
    ssoStatus.value = await getSsoStatus()
  } catch (e) {
    // 后端不可用时保持 SSO 入口为"未开通"状态，本地登录仍可用
    ssoStatus.value = { enabled: false, display_name: '', login_url: '/api/auth/sso/login' }
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
const secureStoreToken = (token) => {
  validateTokenFormat(token)
  // 存储到 localStorage（短期方案）
  // 中期目标：后端使用 httpOnly Cookie，前端不再手动管理 token
  localStorage.setItem('accessToken', token)
}

const handleLogin = async () => {
  try {
    await loginFormRef.value.validate()
    loading.value = true
    errorMsg.value = ''

    const result = await login(loginForm)

    // 安全存储 Token
    try {
      secureStoreToken(result.access_token)
    } catch (tokenError) {
      console.error('Token validation failed')
      errorMsg.value = t('loginFailed')
      return
    }

    // Store login state and username (use backend returned username for consistency)
    localStorage.setItem('isLoggedIn', 'true')
    localStorage.setItem('currentUser', result.username || loginForm.username)

    ElMessage.success(t('loginSuccess'))

    // Redirect to dashboard
    router.push('/')
  } catch (error) {
    if (error.response?.data?.detail) {
      errorMsg.value = error.response.data.detail
    } else if (error !== false) {
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

.method-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 18px 20px;
  border: none;
  border-radius: 4px;
  background: #f6b33b;
  color: #001f5c;
  text-align: left;
  cursor: pointer;
  transition: filter 0.15s ease, transform 0.15s ease;
}

.method-card:hover {
  filter: brightness(1.06);
}

.method-card:active {
  transform: translateY(1px);
}

.method-card:focus-visible {
  outline: 2px solid #fff;
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
  opacity: 0.85;
}

.method-badge {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 600;
  opacity: 0.75;
}

.method-arrow {
  flex-shrink: 0;
  font-size: 18px;
}

.back-link {
  display: block;
  width: 100%;
  margin-top: 4px;
  padding: 8px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
  cursor: pointer;
}

.back-link:hover {
  color: #fff;
  text-decoration: underline;
}

.login-bg-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image:
    radial-gradient(circle at 20% 80%, rgba(246, 179, 59, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(0, 184, 148, 0.1) 0%, transparent 50%);
  pointer-events: none;
}

.login-container {
  width: 400px;
  max-width: 90vw;
  padding: 40px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 1;
}

.login-logo {
  text-align: center;
  margin-bottom: 30px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #00b894, #0984e3);
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 28px;
  margin-bottom: 16px;
}

.logo-text {
  font-size: 28px;
  font-weight: 700;
  color: #001F5C;
  letter-spacing: -0.02em;
  margin: 0;
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

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #00b894, #0984e3);
  border: none;
  transition: all 0.3s;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 184, 148, 0.3);
}

.login-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef0f0;
  border-radius: 8px;
  color: #f56c6c;
  font-size: 14px;
}

.login-footer {
  text-align: center;
  margin-top: 30px;
  color: #999;
  font-size: 12px;
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