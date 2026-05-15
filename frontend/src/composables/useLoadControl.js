import { ref, computed } from 'vue'
import { debounce, throttle } from '@/utils/requestManager.js'

/**
 * 使用防抖加载状态
 * @param {Function} loadFn - 加载函数
 * @param {Object} options - 配置选项
 */
export function useDebouncedLoad(loadFn, options = {}) {
  const { debounceMs = 300, throttleMs = 1000 } = options

  const loading = ref(false)
  const error = ref(null)
  const data = ref(null)

  // 防抖加载函数
  const debouncedLoad = debounce(async (...args) => {
    loading.value = true
    error.value = null
    try {
      const result = await loadFn(...args)
      data.value = result
      return result
    } catch (err) {
      error.value = err
      throw err
    } finally {
      loading.value = false
    }
  }, debounceMs)

  // 节流加载函数
  const throttledLoad = throttle(async (...args) => {
    loading.value = true
    error.value = null
    try {
      const result = await loadFn(...args)
      data.value = result
      return result
    } catch (err) {
      error.value = err
      throw err
    } finally {
      loading.value = false
    }
  }, throttleMs)

  // 直接加载（不防抖）
  const loadImmediately = async (...args) => {
    loading.value = true
    error.value = null
    try {
      const result = await loadFn(...args)
      data.value = result
      return result
    } catch (err) {
      error.value = err
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    data,
    load: debouncedLoad,
    loadThrottled: throttledLoad,
    loadImmediately,
    refresh: loadImmediately
  }
}

/**
 * 使用请求取消
 * @param {Function} requestFn - 返回 Promise 的请求函数
 */
export function useCancellableRequest(requestFn) {
  const loading = ref(false)
  const error = ref(null)
  const data = ref(null)

  let currentController = null

  const execute = async (...args) => {
    // 取消之前的请求
    if (currentController) {
      currentController.abort('New request initiated')
    }

    currentController = new AbortController()

    loading.value = true
    error.value = null

    try {
      const result = await requestFn({
        ...args[0],
        signal: currentController.signal
      })
      data.value = result
      return result
    } catch (err) {
      if (err.name !== 'CanceledError' && err.name !== 'AbortError') {
        error.value = err
        throw err
      }
    } finally {
      loading.value = false
      currentController = null
    }
  }

  const cancel = () => {
    if (currentController) {
      currentController.abort('User cancelled')
      currentController = null
      loading.value = false
    }
  }

  return {
    loading,
    error,
    data,
    execute,
    cancel
  }
}

/**
 * 使用智能刷新（根据页面可见性和网络状态）
 */
export function useSmartRefresh(refreshFn, options = {}) {
  const { interval = 30000, onReconnect = true } = options

  let intervalId = null

  const startAutoRefresh = () => {
    if (intervalId) return
    intervalId = setInterval(() => {
      // 只在页面可见且在线时刷新
      if (document.visibilityState === 'visible' && navigator.onLine) {
        refreshFn()
      }
    }, interval)
  }

  const stopAutoRefresh = () => {
    if (intervalId) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  // 网络恢复时自动刷新
  if (onReconnect) {
    window.addEventListener('online', () => {
      refreshFn()
    })
  }

  // 页面可见性变化处理
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      refreshFn()
    }
  })

  return {
    startAutoRefresh,
    stopAutoRefresh
  }
}
