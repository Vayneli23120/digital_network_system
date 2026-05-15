// 请求管理器 - 处理请求取消、防抖、去重
import { ElMessage } from 'element-plus'

// 存储正在进行的请求控制器
const pendingRequests = new Map()

// 请求去重存储
const requestCache = new Map()

/**
 * 生成请求唯一标识
 */
export function generateRequestKey(config) {
  const { url, method, params, data } = config
  return `${method}:${url}:${JSON.stringify(params)}:${JSON.stringify(data)}`
}

/**
 * 取消之前的相同请求
 */
export function cancelPreviousRequest(config) {
  const key = generateRequestKey(config)
  if (pendingRequests.has(key)) {
    const controller = pendingRequests.get(key)
    controller.abort('Duplicate request cancelled')
    pendingRequests.delete(key)
  }
  return key
}

/**
 * 创建新的请求控制器
 */
export function createRequestController(config) {
  const key = generateRequestKey(config)
  const controller = new AbortController()
  pendingRequests.set(key, controller)
  return controller
}

/**
 * 清理已完成的请求
 */
export function removeRequestController(config) {
  const key = generateRequestKey(config)
  pendingRequests.delete(key)
}

/**
 * 防抖函数 - 延迟执行，期间有新调用则重置定时器
 */
export function debounce(fn, delay = 300) {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
      timer = null
    }, delay)
  }
}

/**
 * 节流函数 - 限制执行频率
 */
export function throttle(fn, limit = 1000) {
  let inThrottle = false
  return function (...args) {
    if (!inThrottle) {
      fn.apply(this, args)
      inThrottle = true
      setTimeout(() => inThrottle = false, limit)
    }
  }
}

/**
 * 带重试的异步函数包装器
 */
export async function withRetry(fn, options = {}) {
  const {
    retries = 3,
    delay = 1000,
    backoff = 2,
    shouldRetry = (error) => error.response?.status >= 500 || !error.response
  } = options

  let lastError
  for (let i = 0; i <= retries; i++) {
    try {
      return await fn()
    } catch (error) {
      lastError = error

      // 如果不需要重试或者是用户取消的请求，直接抛出
      if (error.name === 'CanceledError' || error.name === 'AbortError') {
        throw error
      }

      // 4xx 错误不重试（客户端错误）
      if (error.response?.status >= 400 && error.response?.status < 500) {
        throw error
      }

      // 最后一次尝试失败，抛出错误
      if (i === retries) {
        throw error
      }

      // 等待后重试
      const waitTime = delay * Math.pow(backoff, i)
      await new Promise(resolve => setTimeout(resolve, waitTime))
    }
  }
  throw lastError
}

/**
 * 检查网络连接状态
 */
export function isOnline() {
  return navigator.onLine
}

/**
 * 显示网络错误消息
 */
export function showNetworkError(error) {
  if (error.name === 'CanceledError' || error.name === 'AbortError') {
    return // 用户取消，不显示错误
  }

  if (!navigator.onLine) {
    ElMessage.error('网络连接已断开，请检查网络设置')
    return
  }

  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    ElMessage.error('请求超时，请稍后重试')
    return
  }

  if (error.response?.status === 429) {
    ElMessage.error('请求过于频繁，请稍后再试')
    return
  }

  if (error.response?.status >= 500) {
    ElMessage.error('服务器繁忙，请稍后重试')
    return
  }
}

// 清理过期的请求缓存
setInterval(() => {
  const now = Date.now()
  for (const [key, { timestamp }] of requestCache.entries()) {
    if (now - timestamp > 5000) { // 5秒后清理
      requestCache.delete(key)
    }
  }
}, 10000)
