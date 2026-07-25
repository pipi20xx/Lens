import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const isDarkMode = ref(localStorage.getItem('theme_mode') === 'light' ? false : true)

  function toggleDarkMode() {
    isDarkMode.value = !isDarkMode.value
    localStorage.setItem('theme_mode', isDarkMode.value ? 'dark' : 'light')
  }

  function setDarkMode(isDark: boolean) {
    isDarkMode.value = isDark
    localStorage.setItem('theme_mode', isDark ? 'dark' : 'light')
  }

  return { isDarkMode, toggleDarkMode, setDarkMode }
})
