import { defineStore } from 'pinia'

// 暗色主题 —— 单一数据源。
// 状态初始读 localStorage('darkMode')；apply() 负责把 class 打到 <html>，
// toggle() 写回并派发 'theme-change'（ParetoChart/Operations/Monitor3D 消费，
// 与迁移前 Layout.toggleDark 行为一致）。
export const useThemeStore = defineStore('theme', {
  state: () => ({
    darkMode: localStorage.getItem('darkMode') === 'true',
  }),
  actions: {
    apply() {
      if (this.darkMode) {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    },
    toggle() {
      this.darkMode = !this.darkMode
      localStorage.setItem('darkMode', this.darkMode)
      this.apply()
      window.dispatchEvent(new CustomEvent('theme-change', { detail: { dark: this.darkMode } }))
    },
  },
})
