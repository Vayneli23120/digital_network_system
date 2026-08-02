import { defineStore } from 'pinia'

// 登录态 / 当前用户 —— 单一数据源。
// 状态初始读 localStorage，setAuth/clearAuth 同步写回，键名与迁移前完全一致
// （accessToken / isLoggedIn / currentUser），零迁移成本、不破坏已登录会话。
export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('accessToken') || '',
    isLoggedIn: localStorage.getItem('isLoggedIn') === 'true',
    currentUser: localStorage.getItem('currentUser') || '',
  }),
  actions: {
    setAuth(token, username) {
      this.accessToken = token
      this.isLoggedIn = true
      this.currentUser = username
      localStorage.setItem('accessToken', token)
      localStorage.setItem('isLoggedIn', 'true')
      localStorage.setItem('currentUser', username)
    },
    clearAuth() {
      this.accessToken = ''
      this.isLoggedIn = false
      this.currentUser = ''
      localStorage.removeItem('accessToken')
      localStorage.removeItem('isLoggedIn')
      localStorage.removeItem('currentUser')
    },
  },
})
