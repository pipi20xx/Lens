/**
 * Vuetify 插件配置
 *
 * 设计规范：Apple Liquid Glass — 流动玻璃设计语言
 * - 深色渐变背景，多层玻璃面板半透明 + 高斯模糊 + 饱和度增强
 * - 夜间模式：蓝色系（primary #3b82f6 / accent #38bdf8）为主色调
 * - 白天模式：紫色 #a855f7 为主强调色，青色 #4ecdc4 为辅助色
 * - 图标：全部使用 MDI (@mdi/js)
 */
import { createVuetify } from 'vuetify'
import { aliases, mdi } from 'vuetify/iconsets/mdi'

import 'vuetify/styles'

// 白天模式
const lightTheme = {
  dark: false,
  colors: {
    background: '#F5F7FA',
    surface: '#FFFFFF',
    'surface-variant': '#F5F5FA',
    'on-surface-variant': '#64748B',
    primary: '#a855f7',
    'primary-darken-1': '#9333EA',
    secondary: '#6b7280',
    'secondary-darken-1': '#4b5563',
    accent: '#4ecdc4',
    error: '#ef4444',
    info: '#0891b2',    // 深青色 — 白天模式白底可读
    success: '#059669', // 深绿色 — 白天模式白底可读
    warning: '#d97706', // 琥珀色 — 白天模式白底可读
  },
}

// 夜间模式 — Liquid Glass 流动玻璃色系
const darkTheme = {
  dark: true,
  colors: {
    background: '#0e0e1a',
    surface: '#141428',
    'surface-variant': '#1a1a2e',
    'on-surface-variant': '#BFC2CE',
    primary: '#3b82f6',  // 蓝色 — 夜间模式主色
    'primary-darken-1': '#2563eb',
    secondary: '#9ca3af',
    'secondary-darken-1': '#6b7280',
    accent: '#38bdf8',    // 天蓝色 — 夜间模式辅助色
    error: '#ff6b6b',
    info: '#38bdf8',      // 天蓝色 — 夜间模式 info 语义色
    success: '#34d399', // 翠绿色 — 与 info 区分
    warning: '#fbbf24', // 琥珀金 — 深色底醒目（原 #ff2d92 偏品红容易和 error 混）
  },
}

// ACG 玻璃主题 — 颜色复用 dark 主题，但 Vuetify 会生成 .v-theme--acg 类
// 这样 visual.css 中的 .v-theme--dark 规则不会在 ACG 模式下生效，
// 避免了与 glass-acg.scss 的 CSS 优先级冲突
const acgTheme = {
  dark: true,
  colors: {
    background: '#0b1322',
    surface: '#0b1322',
    'surface-variant': '#1a1a2e',
    'on-surface-variant': '#BFC2CE',
    primary: '#3b82f6',
    'primary-darken-1': '#2563eb',
    secondary: '#9ca3af',
    'secondary-darken-1': '#6b7280',
    accent: '#38bdf8',
    error: '#ff6b6b',
    info: '#38bdf8',
    success: '#34d399',
    warning: '#fbbf24',
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
    defaultTheme: (() => {
      const t = localStorage.getItem('app_theme')
      if (t === 'light') return 'light'
      if (t === 'acg') return 'acg'
      return 'dark'
    })(),
    themes: {
      light: lightTheme,
      dark: darkTheme,
      acg: acgTheme,
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
