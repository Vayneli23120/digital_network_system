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

// 在途请求去重存储（cachedRequest 同键并发合并）
const inFlight = new Map()

/**
 * 稳定序列化：对象键递归排序，保证相同参数产出相同字符串（键序无关）。
 * 避免直接 JSON.stringify 后做非字母数字替换导致的键碰撞（如 {"a_b":1} 与 {"a":"b_1"}）。
 */
function stableStringify(value) {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`
  }
  const keys = Object.keys(value).sort()
  const body = keys
    .map(k => `${JSON.stringify(k)}:${stableStringify(value[k])}`)
    .join(',')
  return `{${body}}`
}

/**
 * 生成缓存键：稳定序列化 + djb2 哈希，确定性、键序无关、无 _ 替换碰撞
 */
export function generateCacheKey(resource, params = {}) {
  const serialized = stableStringify(params)
  let hash = 5381
  for (let i = 0; i < serialized.length; i++) {
    hash = ((hash << 5) + hash) ^ serialized.charCodeAt(i)
  }
  return `${CACHE_CONFIG.STORAGE_PREFIX}${resource}_${(hash >>> 0).toString(36)}`
}

/**
 * 从 localStorage 读取缓存
 * 返回完整记录 { value, expires, timestamp }，让内存回填时能保留原过期时间，
 * 避免读取即续期导致数据无限存活。
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
    return parsed
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

  // 先检查内存缓存
  if (memoryCache.has(key)) {
    const item = memoryCache.get(key)
    if (Date.now() < item.expires) {
      return item.value
    }
    memoryCache.delete(key)
  }

  // 再检查 localStorage；回填内存时保留原 expires，读取不续期
  const stored = readFromStorage(key)
  if (stored !== null) {
    memoryCache.set(key, {
      value: stored.value,
      expires: stored.expires,
    })
    return stored.value
  }

  return null
}

/**
 * 设置缓存
 */
export function setCache(resource, params, value, ttl = null) {
  const key = generateCacheKey(resource, params)
  const expiresIn = ttl || CACHE_CONFIG.DEFAULT_TTL[resource] || 30000

  const item = {
    value,
    expires: Date.now() + expiresIn,
    timestamp: Date.now(),
  }

  // 写入内存
  memoryCache.set(key, item)

  // 写入 localStorage
  writeToStorage(key, value, expiresIn)
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
 * ttl 单位为毫秒（与 CACHE_CONFIG.DEFAULT_TTL 一致），缺省用资源默认值。
 */
export async function cachedRequest(
  apiFn,
  resource,
  params = {},
  options = {}
) {
  const {
    forceRefresh = false,
    ttl = null,
    onError = null,
  } = options
  const key = generateCacheKey(resource, params)

  // 检查缓存
  if (!forceRefresh) {
    const cached = getCache(resource, params)
    if (cached !== null) {
      return Promise.resolve(cached)
    }
    // 同键请求在途则复用其结果，避免并发打穿后端
    if (inFlight.has(key)) {
      return inFlight.get(key)
    }
  }

  const requestPromise = (async () => {
    try {
      const result = await apiFn()
      // 缓存结果
      setCache(resource, params, result, ttl)
      return result
    } catch (error) {
      if (onError) {
        return onError(error)
      }
      throw error
    } finally {
      inFlight.delete(key)
    }
  })()

  inFlight.set(key, requestPromise)
  return requestPromise
}

// 导出配置
export const CacheConfig = CACHE_CONFIG
