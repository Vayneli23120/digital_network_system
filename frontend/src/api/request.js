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
      window.location.href = '/login'
      return Promise.reject(error)
    }

    // 显示网络错误
    showNetworkError(error)

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
