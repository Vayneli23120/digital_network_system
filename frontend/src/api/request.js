import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000
})

// 请求拦截器 — 自动附加 Auth Token
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
  return config
})

// 响应拦截器 - 只处理认证等特殊错误，业务错误由调用处处理
api.interceptors.response.use(
  response => response.data,
  error => {
    // 只处理认证相关错误
    if (error.response?.status === 401) {
      ElMessage.error('登录已过期，请重新登录')
      localStorage.removeItem('accessToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
