/**
 * Vuetify 插件配置
 *
 * 设计规范：Apple Liquid Glass — 流动玻璃设计语言
 * - 深色渐变背景，多层玻璃面板半透明 + 高斯模糊 + 饱和度增强
 * - 青色 #4ecdc4 为核心辅助色（霓虹描边）
 * - 品红 #ff2d92 为渐变填充色
 * - 紫色 #a855f7 为主强调色
 * - 图标：全部使用 MDI (@mdi/js)
 */
import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

import 'vuetify/styles'

// 亮色主题
const lightTheme = {
  dark: false,
  colors: {
    background: '#F0F0F5',
    surface: '#FFFFFF',
    'surface-variant': '#F5F5FA',
    'on-surface-variant': '#64748B',
    primary: '#a855f7',
    'primary-darken-1': '#9333EA',
    secondary: '#6b7280',
    'secondary-darken-1': '#4b5563',
    accent: '#4ecdc4',
    error: '#ef4444',
    info: '#0891b2',    // 深青色 — 白底可读（原 #4ecdc4 在白底上几乎不可见）
    success: '#059669', // 深绿色 — 白底可读（原 #10b981 对比度不足）
    warning: '#ff2d92',
  },
}

// 暗色主题 — Liquid Glass 流动玻璃色系
const darkTheme = {
  dark: true,
  colors: {
    background: '#0a0a1a',
    surface: '#0f0f2a',
    'surface-variant': '#1a1a3e',
    'on-surface-variant': '#BFC2CE',
    primary: '#a855f7',
    'primary-darken-1': '#9333EA',
    secondary: '#9ca3af',
    'secondary-darken-1': '#6b7280',
    accent: '#4ecdc4',
    error: '#ff6b6b',
    info: '#4ecdc4',
    success: '#4ecdc4',
    warning: '#ff2d92',
  },
}

export default createVuetify({
  icons: {
    defaultSet: 'mdi',
    aliases,
    sets: {
      mdi,
    },
  },
  theme: {
    defaultTheme: localStorage.getItem('theme_mode') === 'light' ? 'light' : 'dark',
    themes: {
      light: lightTheme,
      dark: darkTheme,
    },
  },
  defaults: {
    VCard: {
      rounded: 'xl',
    },
    VBtn: {
      rounded: 'xl',
      variant: 'tonal',
      density: 'default',
    },
    VChip: {
      rounded: 'lg',
      label: true,
    },
    VTextField: {
      variant: 'outlined',
      density: 'compact',
      rounded: 'xl',
      hideDetails: 'auto',
    },
    VSelect: {
      variant: 'outlined',
      density: 'compact',
      rounded: 'xl',
      hideDetails: 'auto',
    },
    VTextarea: {
      variant: 'outlined',
      density: 'compact',
      rounded: 'xl',
      hideDetails: 'auto',
    },
    VAutocomplete: {
      variant: 'outlined',
      density: 'compact',
      rounded: 'xl',
      hideDetails: 'auto',
    },
    VCombobox: {
      variant: 'outlined',
      density: 'compact',
      rounded: 'xl',
      hideDetails: 'auto',
    },
  },
})
