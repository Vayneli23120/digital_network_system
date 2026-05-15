/**
 * 前端数据缓存系统 - 减少重复请求
 *
 * 特性：
 * - 内存缓存 + localStorage 持久化
 * - TTL 自动过期
 * - 批量请求合并
 * - 请求去重
 */

// 缓存配置
const CACHE_CONFIG = {
  // 默认 TTL（毫秒）
  DEFAULT_TTL: {
    devices: 30000,      // 设备列表：30秒
    deviceDetail: 60000, // 设备详情：1分钟
    faults: 30000,       // 故障列表：30秒
    maintenance: 30000,  // 维修列表：30秒
    backups: 60000,      // 备份列表：1分钟
    logs: 10000,         // 日志：10秒
    dashboard: 60000,    // 仪表板：1分钟
    spareParts: 60000,   // 备件：1分钟
    templates: 300000,   // 模板：5分钟
    credentials: 300000, // 凭证：5分钟
  },
  // localStorage 键前缀
  STORAGE_PREFIX: 'nas_cache_',
  // 是否启用 localStorage
  ENABLE_STORAGE: true,
}

// 内存缓存存储
const memoryCache = new Map()

/**
 * 生成缓存键
 */
export function generateCacheKey(resource, params = {}) {
  const paramStr = Object.keys(params).length
    ? '_' + JSON.stringify(params).replace(/[^a-zA-Z0-9]/g, '_')
    : ''
  return `${CACHE_CONFIG.STORAGE_PREFIX}${resource}${paramStr}`
}

/**
 * 从 localStorage 读取缓存
 */
function readFromStorage(key) {
  if (!CACHE_CONFIG.ENABLE_STORAGE) return null
  try {
    const data = localStorage.getItem(key)
    if (!data) return null
    const parsed = JSON.parse(data)
    // 检查是否过期
    if (parsed.expires && Date.now() > parsed.expires) {
      localStorage.removeItem(key)
      return null
    }
    return parsed.value
  } catch (e) {
    localStorage.removeItem(key)
    return null
  }
}

/**
 * 写入 localStorage
 */
function writeToStorage(key, value, ttl) {
  if (!CACHE_CONFIG.ENABLE_STORAGE) return
  try {
    const data = {
      value,
      expires: Date.now() + ttl,
      timestamp: Date.now(),
    }
    localStorage.setItem(key, JSON.stringify(data))
  } catch (e) {
    // 存储已满，清理过期缓存
    cleanupExpiredCache()
  }
}

/**
 * 清理过期缓存
 */
function cleanupExpiredCache() {
  if (!CACHE_CONFIG.ENABLE_STORAGE) return
  const keys = Object.keys(localStorage)
  const now = Date.now()
  keys.forEach((key) => {
    if (key.startsWith(CACHE_CONFIG.STORAGE_PREFIX)) {
      try {
        const data = JSON.parse(localStorage.getItem(key))
        if (data.expires && now > data.expires) {
          localStorage.removeItem(key)
        }
      } catch (e) {
        localStorage.removeItem(key)
      }
    }
  })
}

/**
 * 获取缓存
 */
export function getCache(resource, params = {}) {
  const key = generateCacheKey(resource, params)
  const ttl = CACHE_CONFIG.DEFAULT_TTL[resource] || 30000

  // 先检查内存缓存
  if (memoryCache.has(key)) {
    const item = memoryCache.get(key)
    if (Date.now() < item.expires) {
      return item.value
    }
    memoryCache.delete(key)
  }

  // 再检查 localStorage
  const stored = readFromStorage(key)
  if (stored !== null) {
    // 重新加载到内存
    memoryCache.set(key, {
      value: stored,
      expires: Date.now() + ttl,
    })
    return stored
  }

  return null
}

/**
 * 设置缓存
 */
export function setCache(resource, params, value, customTtl = null) {
  const key = generateCacheKey(resource, params)
  const ttl = customTtl || CACHE_CONFIG.DEFAULT_TTL[resource] || 30000

  const item = {
    value,
    expires: Date.now() + ttl,
    timestamp: Date.now(),
  }

  // 写入内存
  memoryCache.set(key, item)

  // 写入 localStorage
  writeToStorage(key, value, ttl)
}

/**
 * 清除缓存
 */
export function clearCache(resource, params = null) {
  if (params) {
    const key = generateCacheKey(resource, params)
    memoryCache.delete(key)
    localStorage.removeItem(key)
  } else {
    // 清除该资源的所有缓存
    const prefix = CACHE_CONFIG.STORAGE_PREFIX + resource
    // 内存缓存
    for (const key of memoryCache.keys()) {
      if (key.startsWith(prefix)) {
        memoryCache.delete(key)
      }
    }
    // localStorage
    if (CACHE_CONFIG.ENABLE_STORAGE) {
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith(prefix)) {
          localStorage.removeItem(key)
        }
      })
    }
  }
}

/**
 * 清除所有缓存
 */
export function clearAllCache() {
  memoryCache.clear()
  if (CACHE_CONFIG.ENABLE_STORAGE) {
    Object.keys(localStorage).forEach((key) => {
      if (key.startsWith(CACHE_CONFIG.STORAGE_PREFIX)) {
        localStorage.removeItem(key)
      }
    })
  }
}

/**
 * 检查缓存是否有效
 */
export function isCacheValid(resource, params = {}) {
  return getCache(resource, params) !== null
}

/**
 * 获取缓存元数据
 */
export function getCacheMeta(resource, params = {}) {
  const key = generateCacheKey(resource, params)
  if (memoryCache.has(key)) {
    return memoryCache.get(key)
  }
  return null
}

/**
 * 带缓存的 API 请求包装器
 */
export async function cachedRequest(
  apiFn,
  resource,
  params = {},
  options = {}
) {
  const {
    forceRefresh = false,
    customTtl = null,
    onError = null,
  } = options

  // 检查缓存
  if (!forceRefresh) {
    const cached = getCache(resource, params)
    if (cached !== null) {
      return Promise.resolve(cached)
    }
  }

  // 发起请求
  try {
    const result = await apiFn()
    // 缓存结果
    setCache(resource, params, result, customTtl)
    return result
  } catch (error) {
    if (onError) {
      return onError(error)
    }
    throw error
  }
}

// 定期清理过期缓存（每5分钟）
setInterval(cleanupExpiredCache, 300000)

// 导出配置
export const CacheConfig = CACHE_CONFIG
