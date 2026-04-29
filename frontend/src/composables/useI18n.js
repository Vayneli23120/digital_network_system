import { ref, watch } from 'vue'
import { languages, getCurrentLang, setCurrentLang } from '@/locales/index'

// 全局语言状态
const currentLang = ref(getCurrentLang())

// 获取翻译函数
export function useI18n() {
  const t = (key) => {
    return languages[currentLang.value]?.[key] || languages['zh']?.[key] || key
  }

  // 切换语言
  const toggleLang = () => {
    currentLang.value = currentLang.value === 'zh' ? 'en' : 'zh'
    setCurrentLang(currentLang.value)
  }

  // 设置语言
  const setLang = (lang) => {
    currentLang.value = lang
    setCurrentLang(lang)
  }

  // 监听语言变化，触发全局事件
  watch(currentLang, (newLang) => {
    window.dispatchEvent(new CustomEvent('lang-change', { detail: { lang: newLang } }))
  })

  return {
    t,
    currentLang,
    toggleLang,
    setLang
  }
}

// 导出当前语言供其他模块使用
export { currentLang }