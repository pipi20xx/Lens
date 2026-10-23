/**
 * xterm 主题适配。
 *
 * 终端不再写死一套深色配色，而是跟随 Lens 当前主题：
 * - 背景透明（需要终端开启 allowTransparency），由外层卡片/页面透出来
 * - 前景、光标取主题的 on-surface / primary
 * - 主题切换时（html / .v-application 的 class 变化）自动同步
 */

export interface XtermThemeOptions {
  background: string
  foreground: string
  cursor: string
  cursorAccent: string
  selectionBackground: string
}

/** 从当前主题里读一个颜色变量（Vuetify 的 --v-theme-* 是 "r,g,b" 三元组） */
function themeRgb(name: string, fallback: string): string {
  const root = document.querySelector('.v-application') || document.documentElement
  const raw = getComputedStyle(root).getPropertyValue(name).trim()
  return raw || fallback
}

export function buildXtermTheme(): XtermThemeOptions {
  const onSurface = themeRgb('--v-theme-on-surface', '224, 224, 224')
  const primary = themeRgb('--v-theme-primary', '0, 230, 118')
  return {
    background: 'rgba(0, 0, 0, 0)',
    foreground: `rgb(${onSurface})`,
    cursor: `rgb(${primary})`,
    cursorAccent: `rgb(${onSurface})`,
    selectionBackground: `rgba(${primary}, 0.28)`,
  }
}

/**
 * 监听主题变化并回调。返回取消监听的函数。
 */
export function watchXtermTheme(apply: (theme: XtermThemeOptions) => void): () => void {
  const observer = new MutationObserver(() => apply(buildXtermTheme()))
  const filter = { attributes: true, attributeFilter: ['class', 'style', 'data-theme'] }
  observer.observe(document.documentElement, filter)
  const app = document.querySelector('.v-application')
  if (app) observer.observe(app, filter)
  return () => observer.disconnect()
}
