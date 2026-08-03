// 操作者会话级 SSH 凭证（批次二·步骤5）
//
// 安全约定：所有 SSH 连接设备必须使用操作者自己的凭证，密码不存储在服务器上。
// 凭证仅保存在浏览器会话（sessionStorage）：刷新保留、关闭标签页/登出清除，
// 非 localStorage，不做跨会话持久化。凭证仅在发起请求时随请求体短暂上传，
// 后端仅存于请求内存，不落库、不入日志。
const KEYS = {
  username: 'session_ssh_username',
  password: 'session_ssh_password',
  secret: 'session_ssh_secret',
}

export function getSessionCredentials() {
  const username = sessionStorage.getItem(KEYS.username) || ''
  const password = sessionStorage.getItem(KEYS.password) || ''
  const secret = sessionStorage.getItem(KEYS.secret) || ''
  if (!username || !password) return null
  return { username, password, secret }
}

export function setSessionCredentials(creds) {
  sessionStorage.setItem(KEYS.username, creds.username || '')
  sessionStorage.setItem(KEYS.password, creds.password || '')
  sessionStorage.setItem(KEYS.secret, creds.secret || '')
}

export function clearSessionCredentials() {
  sessionStorage.removeItem(KEYS.username)
  sessionStorage.removeItem(KEYS.password)
  sessionStorage.removeItem(KEYS.secret)
}

export function useSessionCredentials() {
  return { getSessionCredentials, setSessionCredentials, clearSessionCredentials }
}
