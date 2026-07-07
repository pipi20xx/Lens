import { ref, computed, onMounted, onUnmounted } from 'vue'

/**
 * Lens PWA 三态判断 Composable
 * 参考 123123 项目 (番剧管家) 的 usePWA 设计
 *
 * 三种 UI 模式:
 *   1. Desktop       — 桌面端顶部 Tab 导航
 *   2. Mobile Browser — 移动浏览器 (汉堡菜单 + 抽屉)
 *   3. PWA App       — 安装后独立运行 (底部导航 + 返回按钮)
 *
 * 用户可通过 setUIMode 手动覆盖:
 *   'auto'    — 自动检测 (默认)
 *   'desktop' — 强制桌面模式
 *   'app'     — 强制 App 模式
 */

export type UIMode = 'auto' | 'desktop' | 'app'

// ── Module-level singletons (全局共享) ──
const uiMode = ref<UIMode>(
  (typeof localStorage !== 'undefined' && (localStorage.getItem('lens_ui_mode') as UIMode)) || 'auto'
)
const isStandalone = ref(false)
const isMobileWidth = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)

let listenerCount = 0
let standaloneMediaQuery: MediaQueryList | null = null

/** 手动切换 UI 模式 */
function setUIMode(mode: UIMode) {
  uiMode.value = mode
  localStorage.setItem('lens_ui_mode', mode)
}

/** 检测是否在 PWA standalone 模式 (已安装到桌面) */
function detectStandalone(): boolean {
  if (typeof window === 'undefined') return false
  // iOS Safari
  if ((navigator as any).standalone === true) return true
  // Android Chrome / Edge / Desktop PWA
  if (window.matchMedia('(display-mode: standalone)').matches) return true
  return false
}

function handleResize() {
  isMobileWidth.value = window.innerWidth < 768
}

function handleStandaloneChange(e: MediaQueryListEvent) {
  isStandalone.value = e.matches
}

export function usePWA() {
  /**
   * appMode: 是否使用 App 交互模式
   * - 手动 'app' → true
   * - 手动 'desktop' → false
   * - auto → PWA standalone + 窄屏
   */
  const appMode = computed(() => {
    if (uiMode.value === 'app') return true
    if (uiMode.value === 'desktop') return false
    return isStandalone.value && isMobileWidth.value
  })

  /** 是否窄屏 (用于移动端组件切换) */
  const isMobile = computed(() => isMobileWidth.value)

  onMounted(() => {
    // 初始检测
    isStandalone.value = detectStandalone()
    handleResize()

    listenerCount++
    if (listenerCount === 1) {
      window.addEventListener('resize', handleResize)
      // 监听 display-mode 变化 (浏览器 ↔ PWA 切换)
      standaloneMediaQuery = window.matchMedia('(display-mode: standalone)')
      if (standaloneMediaQuery.addEventListener) {
        standaloneMediaQuery.addEventListener('change', handleStandaloneChange)
      } else {
        // Safari < 14 fallback
        ;(standaloneMediaQuery as any).addListener(handleStandaloneChange)
      }
    }
  })

  onUnmounted(() => {
    listenerCount--
    if (listenerCount === 0) {
      window.removeEventListener('resize', handleResize)
      if (standaloneMediaQuery) {
        if (standaloneMediaQuery.removeEventListener) {
          standaloneMediaQuery.removeEventListener('change', handleStandaloneChange)
        } else {
          ;(standaloneMediaQuery as any).removeListener(handleStandaloneChange)
        }
      }
    }
  })

  return {
    isStandalone,
    isMobile,
    appMode,
    uiMode,
    setUIMode,
  }
}
