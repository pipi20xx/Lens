import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const isDarkMode = ref(localStorage.getItem('theme_mode') === 'light' ? false : true)

  // ─── Glass 主题 ──────────────────────────────────────
  // 'none' = 不使用玻璃主题；'acg' = ACG 玻璃主题
  const glassTheme = ref<'none' | 'acg'>(
    (localStorage.getItem('glass_theme') as 'none' | 'acg') || 'none',
  )

  function toggleDarkMode() {
    isDarkMode.value = !isDarkMode.value
    localStorage.setItem('theme_mode', isDarkMode.value ? 'dark' : 'light')
  }

  function setDarkMode(isDark: boolean) {
    isDarkMode.value = isDark
    localStorage.setItem('theme_mode', isDark ? 'dark' : 'light')
  }

  function setGlassTheme(theme: 'none' | 'acg') {
    glassTheme.value = theme
    localStorage.setItem('glass_theme', theme)
  }

  return { isDarkMode, glassTheme, toggleDarkMode, setDarkMode, setGlassTheme }
})
