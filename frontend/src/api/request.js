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
  const language = localStorage.getItem('language') || 'zh'
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

// 请求拦截器 — 自动附加 Auth Token 和请求取消
api.interceptors.request.use(config => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  // 同时传递当前用户名作为备用
  const currentUser = localStorage.getItem('currentUser')
  if (currentUser) {
    config.headers['X-User'] = currentUser
  }

  // 为 GET 请求自动取消之前的相同请求
  if (config.method?.toLowerCase() === 'get') {
    cancelPreviousRequest(config)
    const controller = createRequestController(config)
    config.signal = controller.signal
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

    // 处理认证错误
    if (error.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      localStorage.removeItem('accessToken')
      localStorage.removeItem('isLoggedIn')
      localStorage.removeItem('currentUser')
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // 对于有具体错误信息的请求，显示具体信息而不是笼统提示
    const detail = error.response?.data?.detail || error.response?.data?.error
    if (detail) {
      // 翻译 SSH 相关错误
      const translatedDetail = translateSSHError(detail)
      ElMessage.error(translatedDetail)
    } else {
      // 显示通用网络错误
      showNetworkError(error)
    }

    return Promise.reject(error)
  }
)

// 包装 API 方法，添加自动重试
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

  async post(url, data, config = {}) {
    return withRetry(() => api.post(url, data, config), {
      retries: 1,
      delay: 500
    })
  },

  async put(url, data, config = {}) {
    return withRetry(() => api.put(url, data, config), {
      retries: 1,
      delay: 500
    })
  },

  async patch(url, data, config = {}) {
    return withRetry(() => api.patch(url, data, config), {
      retries: 1,
      delay: 500
    })
  },

  async delete(url, config = {}) {
    return withRetry(() => api.delete(url, config), {
      retries: 1,
      delay: 500
    })
  }
}

export default api
