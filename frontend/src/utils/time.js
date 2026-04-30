/**
 * 时间格式化工具
 * 处理 UTC 时间转换为本地时间显示
 */

import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'

// 扩展 dayjs UTC 插件
dayjs.extend(utc)

/**
 * 格式化日期时间（UTC -> 本地时间）
 * @param {string|Date} date - UTC 时间
 * @returns {string} 本地时间格式 YYYY-MM-DD HH:mm
 */
export function formatDateTime(date) {
  if (!date) return '-'
  return dayjs.utc(date).local().format('YYYY-MM-DD HH:mm')
}

/**
 * 格式化日期（UTC -> 本地时间）
 * @param {string|Date} date - UTC 时间
 * @returns {string} 本地时间格式 YYYY-MM-DD
 */
export function formatDate(date) {
  if (!date) return '-'
  return dayjs.utc(date).local().format('YYYY-MM-DD')
}

/**
 * 格式化简短时间（UTC -> 本地时间）
 * @param {string|Date} date - UTC 时间
 * @returns {string} 本地时间格式 MM-DD HH:mm
 */
export function formatShortTime(date) {
  if (!date) return '-'
  return dayjs.utc(date).local().format('MM-DD HH:mm')
}

/**
 * 获取本地 dayjs 对象（从 UTC 时间转换）
 * @param {string|Date} date - UTC 时间
 * @returns {dayjs} 本地时间的 dayjs 对象
 */
export function toLocalDayjs(date) {
  return dayjs.utc(date).local()
}

export { dayjs }