import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/** 主题视觉风格 —— 决定 <html> 上挂哪个 glass-theme-xxx class */
export type ThemeStyle = 'classic' | 'liquid' | 'acg'

/**
 * 完整主题 = 视觉风格 + 写死的明暗模式。
 * 白天/夜晚不是独立开关：每个主题创建时就固定了明暗，切主题即整体切换。
 * （对齐 Anime-Manager 的 5 主题模型）
 *
 * 命名说明：classic 的两态沿用本项目既有的 'light' / 'dark' 取值，
 * 不改名为 'classic-light' / 'classic-dark'，以免迁移已存在的
 * localStorage('app_theme') 并波及所有 `appTheme === 'light'` 判断。
 */
export type AppTheme = 'light' | 'dark' | 'liquid-light' | 'liquid-dark' | 'acg'

const THEME_STORAGE_KEY = 'app_theme'
const LEGACY_STYLE_KEY = 'glass_theme'
const LEGACY_MODE_KEY = 'theme_mode'

const THEME_STYLE: Record<AppTheme, ThemeStyle> = {
  light: 'classic',
  dark: 'classic',
  'liquid-light': 'liquid',
  'liquid-dark': 'liquid',
  acg: 'acg',
}

const THEME_DARK: Record<AppTheme, boolean> = {
  light: false,
  dark: true,
  'liquid-light': false,
  'liquid-dark': true,
  acg: true,
}

/** 该主题是否使用暗色基底（ACG 与 liquid-dark 为暗色） */
export function isThemeDark(theme: AppTheme): boolean {
  return THEME_DARK[theme]
}

/** 该主题的视觉风格，用于 html.glass-theme-xxx */
export function themeStyle(theme: AppTheme): ThemeStyle {
  return THEME_STYLE[theme]
}

/**
 * 读取持久化主题。新 key app_theme 优先；
 * 旧版 glass_theme + theme_mode 双 key 自动合并迁移（ACG 恒为暗色）。
 */
export function readStoredAppTheme(): AppTheme {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  if (stored && stored in THEME_STYLE) return stored as AppTheme

  const style = localStorage.getItem(LEGACY_STYLE_KEY)
  if (style === 'acg') return 'acg'

  const dark = localStorage.getItem(LEGACY_MODE_KEY) !== 'light'
  if (style === 'liquid') return dark ? 'liquid-dark' : 'liquid-light'
  return dark ? 'dark' : 'light'
}

export const useThemeStore = defineStore('theme', () => {
  // ─── 五态主题：经典（白天/夜晚）、液态玻璃（白天/夜晚）、ACG 玻璃 ──
  const appTheme = ref<AppTheme>(readStoredAppTheme())

  // 首次加载旧版数据时立即迁移为单一 app_theme，保证之后只有一个存储来源
  if (!localStorage.getItem(THEME_STORAGE_KEY)) {
    localStorage.setItem(THEME_STORAGE_KEY, appTheme.value)
    localStorage.removeItem(LEGACY_STYLE_KEY)
    localStorage.removeItem(LEGACY_MODE_KEY)
  }

  // 派生：是否为深色模式（ACG 与 liquid-dark 也使用暗色基底）
  const isDarkMode = computed(() => isThemeDark(appTheme.value))

  // 派生：视觉风格 —— 'classic' | 'liquid' | 'acg'
  // 注意：旧版此处返回 'acg' | 'none'，现在多出 'liquid'；
  // 现有消费方一律用 `=== 'acg'` 判断，不受影响。
  const glassTheme = computed<ThemeStyle>(() => themeStyle(appTheme.value))

  function setAppTheme(theme: AppTheme) {
    appTheme.value = theme
    localStorage.setItem(THEME_STORAGE_KEY, theme)
    // 旧字段同步（向后兼容，供仍在读旧 key 的外部脚本使用）
    localStorage.setItem(LEGACY_MODE_KEY, isThemeDark(theme) ? 'dark' : 'light')
    localStorage.setItem(LEGACY_STYLE_KEY, themeStyle(theme))
  }

  // 向后兼容的方法
  function toggleDarkMode() {
    setAppTheme(isDarkMode.value ? 'light' : 'dark')
  }

  function setDarkMode(isDark: boolean) {
    setAppTheme(isDark ? 'dark' : 'light')
  }

  /** 按视觉风格切换，保留当前明暗 */
  function setGlassTheme(theme: ThemeStyle) {
    if (theme === 'acg') {
      setAppTheme('acg')
    } else if (theme === 'liquid') {
      setAppTheme(isDarkMode.value ? 'liquid-dark' : 'liquid-light')
    } else {
      setAppTheme(isDarkMode.value ? 'dark' : 'light')
    }
  }

  return { appTheme, isDarkMode, glassTheme, setAppTheme, toggleDarkMode, setDarkMode, setGlassTheme }
})
