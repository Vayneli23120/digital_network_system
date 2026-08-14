import axios from 'axios'
import { ElMessage } from 'element-plus'
import {
  generateRequestKey,
  cancelPreviousRequest,
  createRequestController,
  removeRequestController,
  withRetry,
  showNetworkError
} from '@/utils/requestManager.js'
import { useAuthStore } from '@/stores/auth'

// SSH 错误翻译映射
const SSH_ERROR_MAP_ZH = {
  'Authentication failed': 'SSH 认证失败，请检查用户名和密码',
  'authentication failed': 'SSH 认证失败，请检查用户名和密码',
  'Auth failed': 'SSH 认证失败，请检查用户名和密码',
  'auth failed': 'SSH 认证失败，请检查用户名和密码',
  'Connection timed out': '连接超时，请检查设备网络连通性',
  'connection timed out': '连接超时，请检查设备网络连通性',
  'Connection timeout': '连接超时，请检查设备网络连通性',
  'Timed out': '连接超时，请检查设备网络连通性',
  'timed out': '连接超时，请检查设备网络连通性',
  'Connection refused': '连接被拒绝，请检查 SSH 服务是否开启',
  'connection refused': '连接被拒绝，请检查 SSH 服务是否开启',
  'Connection refused by server': '连接被拒绝，请检查 SSH 服务是否开启',
  'SSH protocol error': 'SSH 协议错误',
  'ssh protocol error': 'SSH 协议错误',
  'Protocol error': 'SSH 协议错误',
  'Unable to connect': '无法连接到设备',
  'unable to connect': '无法连接到设备',
  'Could not connect': '无法连接到设备',
  'No route to host': '网络不可达',
  'no route to host': '网络不可达',
  'Network is unreachable': '网络不可达',
  'network is unreachable': '网络不可达',
  'Name or service not known': '无法解析主机名',
  'Unknown host': '无法解析主机名',
  'unknown host': '无法解析主机名',
  'Host key verification failed': '主机密钥验证失败',
  'host key verification failed': '主机密钥验证失败',
  'Banner exchange error': 'SSH 握手失败',
  'banner': 'SSH 握手失败',
  'password is required': '需要密码认证',
  'Password required': '需要密码认证'
}

// 翻译 SSH 错误信息
function translateSSHError(message) {
  const language = localStorage.getItem('lang') || 'zh'
  if (language !== 'zh') return message  // 英文模式下不翻译

  // 检查是否包含 SSH 相关错误
  for (const [english, chinese] of Object.entries(SSH_ERROR_MAP_ZH)) {
    if (message.toLowerCase().includes(english.toLowerCase())) {
      return chinese
    }
  }
  return message
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000
})

export const authenticatedAxios = axios.create({ timeout: 30000 })

function attachAuthToken(config) {
  const token = useAuthStore().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

// 401 去重守卫：并发多个 401 只弹一次提示、只触发一次跳转
let isRedirectingToLogin = false

function handleAuthFailure(error) {
  if (error.response?.status === 401) {
    if (!isRedirectingToLogin) {
      isRedirectingToLogin = true
      ElMessage.error('登录已过期，请重新登录')
      useAuthStore().clearAuth()
      window.location.href = '/login'
    }
  }
  return Promise.reject(error)
}

authenticatedAxios.interceptors.request.use(attachAuthToken)
authenticatedAxios.interceptors.response.use(response => response, handleAuthFailure)

// 请求拦截器 — 自动附加 Auth Token 和请求取消
api.interceptors.request.use(config => {
  attachAuthToken(config)

  // 为 GET 请求自动取消之前的相同请求。
  // 逃生口：调用方传 config.noAutoCancel=true 关闭；已自带 config.signal 时不覆盖。
  if (config.method?.toLowerCase() === 'get' && config.noAutoCancel !== true) {
    if (!config.signal) {
      cancelPreviousRequest(config)
      config.signal = createRequestController(config).signal
    }
  }

  return config
})

// 响应拦截器 - 处理错误和清理
api.interceptors.response.use(
  response => {
    removeRequestController(response.config)
    return response.data
  },
  error => {
    // 清理请求控制器
    if (error.config) {
      removeRequestController(error.config)
    }

    // 用户取消的请求，不显示错误
    if (error.name === 'CanceledError' || error.name === 'AbortError') {
      return Promise.reject(error)
    }

    // 登录接口的错误由登录页内联展示：其 401 表示「用户名或密码错误」，
    // 不应触发「会话过期」的全局跳转，也不应重复弹出全局提示。
    const isLoginRequest = (error.config?.url || '').includes('/auth/login')

    // 处理认证错误（登录接口除外）
    if (error.response?.status === 401 && !isLoginRequest) {
      return handleAuthFailure(error)
    }

    // 对于有具体错误信息的请求，显示具体信息而不是笼统提示（登录接口除外）
    if (!isLoginRequest) {
      const detail = error.response?.data?.detail || error.response?.data?.error
      if (detail) {
        // 翻译 SSH 相关错误
        const translatedDetail = translateSSHError(detail)
        ElMessage.error(translatedDetail)
      } else {
        // 显示通用网络错误
        showNetworkError(error)
      }
    }

    return Promise.reject(error)
  }
)

// 包装 API 方法，添加自动重试。
// 写操作（post/put/patch/delete）默认不重试：非幂等请求在超时后重发可能重复
// 下发（部署、入库），要重试请显式传 retries 覆盖。
export const apiWithRetry = {
  async get(url, config = {}) {
    return withRetry(() => api.get(url, config), {
      retries: 2,
      delay: 500,
      shouldRetry: (error) => {
        // 只对网络错误和 5xx 错误重试
        if (!error.response) return true
        if (error.response.status >= 500) return true
        return false
      }
    })
  },

  async post(url, data, config = {}, retries = 0) {
    return withRetry(() => api.post(url, data, config), {
      retries,
      delay: 500
    })
  },

  async put(url, data, config = {}, retries = 0) {
    return withRetry(() => api.put(url, data, config), {
      retries,
      delay: 500
    })
  },

  async patch(url, data, config = {}, retries = 0) {
    return withRetry(() => api.patch(url, data, config), {
      retries,
      delay: 500
    })
  },

  async delete(url, config = {}, retries = 0) {
    return withRetry(() => api.delete(url, config), {
      retries,
      delay: 500
    })
  }
}

export default api
