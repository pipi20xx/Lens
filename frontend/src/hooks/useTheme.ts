import { ref, computed, onMounted } from 'vue'
import { GlobalThemeOverrides, lightTheme, darkTheme } from 'naive-ui'

export type ThemeMode = 'light' | 'dark'

// 夜晚模式 (紫色主题) - 保持原有样式
const darkOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#a370f7',
    primaryColorHover: '#b794f4',
    primaryColorPressed: '#805ad5',
    borderRadius: '8px',
    cardColor: '#1a1021',
    modalColor: '#241630',
    bodyColor: '#0f0913',
    textColorBase: '#e2e2e9',
    dividerColor: 'rgba(163, 112, 247, 0.15)',
    fontSize: '15px'
  },
  Card: {
    borderRadius: '12px',
    borderColor: 'rgba(163, 112, 247, 0.2)',
    titleFontSizeMedium: '18px',
    titleFontWeight: '600'
  },
  Button: {
    borderRadiusMedium: '8px',
    fontWeight: '500',
    fontSizeMedium: '14px',
    colorPrimary: '#3B82F6',
    colorPrimaryHover: '#2563EB',
    colorPrimaryPressed: '#1D4ED8',
    colorSuccess: '#10B981',
    colorSuccessHover: '#059669',
    colorSuccessPressed: '#047857',
    colorWarning: '#F59E0B',
    colorWarningHover: '#D97706',
    colorWarningPressed: '#B45309',
    colorError: '#EF4444',
    colorErrorHover: '#DC2626',
    colorErrorPressed: '#B91C1C',
    textColorPrimary: '#ffffff',
    textColorSuccess: '#ffffff',
    textColorWarning: '#ffffff',
    textColorError: '#ffffff'
  },
  Input: {
    borderRadius: '8px',
    fontSizeMedium: '14px'
  },
  Menu: {
    fontSize: '15px',
    itemHeight: '42px'
  }
}

// 白天模式 - 浅色主题
const lightOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#7c3aed',
    primaryColorHover: '#8b5cf6',
    primaryColorPressed: '#6d28d9',
    borderRadius: '8px',
    cardColor: '#ffffff',
    modalColor: '#ffffff',
    bodyColor: '#f8f7fa',
    textColorBase: '#1f2937',
    dividerColor: 'rgba(124, 58, 237, 0.12)',
    fontSize: '15px'
  },
  Card: {
    borderRadius: '12px',
    borderColor: 'rgba(124, 58, 237, 0.15)',
    titleFontSizeMedium: '18px',
    titleFontWeight: '600'
  },
  Button: {
    borderRadiusMedium: '8px',
    fontWeight: '500',
    fontSizeMedium: '14px',
    colorPrimary: '#3B82F6',
    colorPrimaryHover: '#2563EB',
    colorPrimaryPressed: '#1D4ED8',
    colorSuccess: '#10B981',
    colorSuccessHover: '#059669',
    colorSuccessPressed: '#047857',
    colorWarning: '#F59E0B',
    colorWarningHover: '#D97706',
    colorWarningPressed: '#B45309',
    colorError: '#EF4444',
    colorErrorHover: '#DC2626',
    colorErrorPressed: '#B91C1C',
    textColorPrimary: '#ffffff',
    textColorSuccess: '#ffffff',
    textColorWarning: '#ffffff',
    textColorError: '#ffffff'
  },
  Input: {
    borderRadius: '8px',
    fontSizeMedium: '14px'
  },
  Menu: {
    fontSize: '15px',
    itemHeight: '42px'
  }
}

export function useTheme() {
  const currentMode = ref<ThemeMode>((localStorage.getItem('lens_theme_mode') as ThemeMode) || 'light')

  const isDark = computed(() => currentMode.value === 'dark')
  const isLight = computed(() => currentMode.value === 'light')

  const naiveTheme = computed(() => isDark.value ? darkTheme : lightTheme)

  const syncThemeVariables = (mode: ThemeMode) => {
    const root = document.documentElement
    
    if (mode === 'dark') {
      // 夜晚模式变量
      root.style.setProperty('--primary-color', '#a370f7')
      root.style.setProperty('--primary-hover', '#b794f4')
      root.style.setProperty('--app-bg-color', '#0f0913')
      root.style.setProperty('--card-bg-color', '#1a1021')
      root.style.setProperty('--modal-bg-color', '#241630')
      root.style.setProperty('--text-color', '#e2e2e9')
      root.style.setProperty('--border-color', 'rgba(163, 112, 247, 0.15)')
      root.style.setProperty('--sidebar-bg-color', '#140c1a')
      root.style.setProperty('--nav-bg-color', '#140c1a')
      root.style.setProperty('--sub-nav-bg-color', 'rgba(163, 112, 247, 0.05)')
      root.style.setProperty('--primary-border-color', 'rgba(163, 112, 247, 0.2)')
      root.style.setProperty('--text-secondary', '#9ca3af')
      root.style.setProperty('--hover-bg', 'rgba(163, 112, 247, 0.08)')
      // 按钮颜色
      root.style.setProperty('--btn-primary-color', '#3B82F6')
      root.style.setProperty('--btn-primary-hover', '#2563EB')
      root.style.setProperty('--btn-primary-pressed', '#1D4ED8')
      root.style.setProperty('--btn-success-color', '#10B981')
      root.style.setProperty('--btn-success-hover', '#059669')
      root.style.setProperty('--btn-success-pressed', '#047857')
      root.style.setProperty('--btn-warning-color', '#F59E0B')
      root.style.setProperty('--btn-warning-hover', '#D97706')
      root.style.setProperty('--btn-warning-pressed', '#B45309')
      root.style.setProperty('--btn-danger-color', '#EF4444')
      root.style.setProperty('--btn-danger-hover', '#DC2626')
      root.style.setProperty('--btn-danger-pressed', '#B91C1C')
    } else {
      // 白天模式变量
      root.style.setProperty('--primary-color', '#7c3aed')
      root.style.setProperty('--primary-hover', '#8b5cf6')
      root.style.setProperty('--app-bg-color', '#f8f7fa')
      root.style.setProperty('--card-bg-color', '#ffffff')
      root.style.setProperty('--modal-bg-color', '#ffffff')
      root.style.setProperty('--text-color', '#1f2937')
      root.style.setProperty('--border-color', 'rgba(124, 58, 237, 0.12)')
      root.style.setProperty('--sidebar-bg-color', '#ffffff')
      root.style.setProperty('--nav-bg-color', '#ffffff')
      root.style.setProperty('--sub-nav-bg-color', 'rgba(124, 58, 237, 0.05)')
      root.style.setProperty('--primary-border-color', 'rgba(124, 58, 237, 0.15)')
      root.style.setProperty('--text-secondary', '#6b7280')
      root.style.setProperty('--hover-bg', 'rgba(124, 58, 237, 0.06)')
      // 按钮颜色
      root.style.setProperty('--btn-primary-color', '#3B82F6')
      root.style.setProperty('--btn-primary-hover', '#2563EB')
      root.style.setProperty('--btn-primary-pressed', '#1D4ED8')
      root.style.setProperty('--btn-success-color', '#10B981')
      root.style.setProperty('--btn-success-hover', '#059669')
      root.style.setProperty('--btn-success-pressed', '#047857')
      root.style.setProperty('--btn-warning-color', '#F59E0B')
      root.style.setProperty('--btn-warning-hover', '#D97706')
      root.style.setProperty('--btn-warning-pressed', '#B45309')
      root.style.setProperty('--btn-danger-color', '#EF4444')
      root.style.setProperty('--btn-danger-hover', '#DC2626')
      root.style.setProperty('--btn-danger-pressed', '#B91C1C')
    }
  }

  const themeOverrides = computed(() => {
    const overrides = isDark.value ? darkOverrides : lightOverrides
    if (typeof document !== 'undefined') {
      syncThemeVariables(currentMode.value)
    }
    return overrides
  })

  const toggleTheme = () => {
    currentMode.value = isDark.value ? 'light' : 'dark'
    localStorage.setItem('lens_theme_mode', currentMode.value)
    syncThemeVariables(currentMode.value)
  }

  const setTheme = (mode: ThemeMode) => {
    currentMode.value = mode
    localStorage.setItem('lens_theme_mode', mode)
    syncThemeVariables(mode)
  }

  onMounted(() => {
    syncThemeVariables(currentMode.value)
  })

  return {
    currentMode,
    isDark,
    isLight,
    naiveTheme,
    themeOverrides,
    toggleTheme,
    setTheme
  }
}
