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

      <!-- Login Form -->
      <el-form
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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Monitor, WarningFilled } from '@element-plus/icons-vue'
import { login } from '@/api'
import { useI18n } from '@/composables/useI18n'

const { t } = useI18n()
const router = useRouter()

const loginFormRef = ref(null)
const loading = ref(false)
const errorMsg = ref('')

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

const handleLogin = async () => {
  try {
    await loginFormRef.value.validate()
    loading.value = true
    errorMsg.value = ''

    const result = await login(loginForm)

    // Store login state and username
    localStorage.setItem('isLoggedIn', 'true')
    localStorage.setItem('currentUser', loginForm.username)
    localStorage.setItem('accessToken', result.access_token)

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