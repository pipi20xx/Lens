import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type AppTheme = 'light' | 'dark' | 'acg'

export const useThemeStore = defineStore('theme', () => {
  // ─── 三态主题：白天 / 夜晚 / ACG 玻璃 ──────────────────
  const appTheme = ref<AppTheme>(
    (localStorage.getItem('app_theme') as AppTheme) || 'dark',
  )

  // 兼容旧字段：如果旧 theme_mode 存在，迁移一次
  if (!localStorage.getItem('app_theme')) {
    const oldMode = localStorage.getItem('theme_mode')
    const oldGlass = localStorage.getItem('glass_theme')
    if (oldGlass === 'acg') {
      appTheme.value = 'acg'
    } else if (oldMode === 'light') {
      appTheme.value = 'light'
    } else {
      appTheme.value = 'dark'
    }
    localStorage.setItem('app_theme', appTheme.value)
  }

  // 派生：是否为深色模式（ACG 也使用 dark 基底）
  const isDarkMode = computed(() => appTheme.value !== 'light')

  // 派生：是否为 ACG 玻璃主题
  const glassTheme = computed(() => (appTheme.value === 'acg' ? 'acg' : 'none'))

  function setAppTheme(theme: AppTheme) {
    appTheme.value = theme
    localStorage.setItem('app_theme', theme)
    // 清理旧字段
    localStorage.setItem('theme_mode', theme === 'light' ? 'light' : 'dark')
    localStorage.setItem('glass_theme', theme === 'acg' ? 'acg' : 'none')
  }

  // 向后兼容的方法
  function toggleDarkMode() {
    setAppTheme(appTheme.value === 'light' ? 'dark' : 'light')
  }

  function setDarkMode(isDark: boolean) {
    setAppTheme(isDark ? 'dark' : 'light')
  }

  function setGlassTheme(theme: 'none' | 'acg') {
    if (theme === 'acg') {
      setAppTheme('acg')
    } else {
      // 从 ACG 切回时，恢复到 dark（因为 ACG 底层是 dark）
      setAppTheme('dark')
    }
  }

  return { appTheme, isDarkMode, glassTheme, setAppTheme, toggleDarkMode, setDarkMode, setGlassTheme }
})
