import { defineStore } from 'pinia'
import api from '@/api/request'

// 登录态 / 当前用户 —— 单一数据源。
// 状态初始读 localStorage，setAuth/clearAuth 同步写回，键名与迁移前完全一致
// （accessToken / isLoggedIn / currentUser），零迁移成本、不破坏已登录会话。
export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('accessToken') || '',
    isLoggedIn: localStorage.getItem('isLoggedIn') === 'true',
    currentUser: localStorage.getItem('currentUser') || '',
    permissions: [],
    permissionsLoaded: false,
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
      this.permissions = []
      this.permissionsLoaded = false
      localStorage.removeItem('accessToken')
      localStorage.removeItem('isLoggedIn')
      localStorage.removeItem('currentUser')
    },
    async fetchMyPermissions() {
      // 供路由守卫 / 菜单渲染按权限控制；失败或空列表也置 loaded=true，
      // 让守卫按"空 = 放行"约定处理（后端 require_permission 才是真拦截）。
      try {
        const { data } = await api.get('/permissions/my-permissions')
        this.permissions = data.permissions || []
        this.permissionsLoaded = true
        return this.permissions
      } catch (e) {
        this.permissions = []
        this.permissionsLoaded = true
        return []
      }
    },
  },
})
