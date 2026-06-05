import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'

// API 客户端实例
const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 30_000,
  withCredentials: true, // 为 httpOnly Cookie 做准备
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 从 localStorage 获取 token（短期方案）
    // 后续改为 httpOnly Cookie 后可移除
    const authStorage = localStorage.getItem('nas-auth')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        const token = state?.accessToken
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      } catch {
        // 解析失败，忽略
      }
    }

    // 添加 Request ID
    const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    config.headers['X-Request-ID'] = requestId

    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error: AxiosError) => {
    // 401 未授权
    if (error.response?.status === 401) {
      // 清除认证状态
      localStorage.removeItem('nas-auth')
      // 重定向到登录页
      window.location.href = '/login'
      return Promise.reject(new Error('未授权，请重新登录'))
    }

    // 403 权限不足
    if (error.response?.status === 403) {
      return Promise.reject(new Error('权限不足'))
    }

    // 500 服务器错误
    if (error.response?.status === 500) {
      const detail = (error.response?.data as any)?.detail || '服务器内部错误'
      return Promise.reject(new Error(detail))
    }

    // 其他错误
    const message = (error.response?.data as any)?.detail || error.message || '请求失败'
    return Promise.reject(new Error(message))
  }
)

export default apiClient