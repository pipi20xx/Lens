import { ref, computed, watch, onMounted } from 'vue'
import { useThemeStore } from '@/stores/useThemeStore'
import { useEffectiveGlassSettings, applyStoredThemeCustomizerAppearance, themeCustomizerPrimaryColors } from '../host/useThemeCustomizer'
import { normalizeThemeMaterialAccent } from '../utils/glassColor'
import { loadGlassWallpaperTone, DEFAULT_GLASS_WALLPAPER_TONE_PROFILE, type GlassWallpaperToneProfile } from '../utils/glassWallpaperTone'
import { useTheme } from 'vuetify'

/**
 * 从 CSS 变量 --am-wallpaper-source 中提取壁纸源 URL。
 * tokens.css 中定义了 https://www.loliapi.com/acg/pc/ 等地址（纯字符串，非 url() 包裹）。
 * 壁纸图片的加载统一通过后端代理，body::before 不再直接请求原始 URL。
 */
function extractWallpaperUrlFromCss(): string {
  const raw = getComputedStyle(document.documentElement)
    .getPropertyValue('--am-wallpaper-source')
    .trim()
  // 去掉可能的引号包裹
  return raw.replace(/^["']|["']$/g, '')
}

/**
 * 已知的随机壁纸 API 域名 —— URL 不变但每次请求返回不同图片。
 * 对这类源需要添加 cache-buster 让前端缓存和浏览器 HTTP 缓存失效，
 * 否则页面刷新后永远拿到同一张图。
 */
const RANDOM_WALLPAPER_DOMAINS = new Set([
  'loliapi.com',
  'www.loliapi.com',
  'api.loliapi.com',
  'random.iisu.cn',
  'api.dujin.org',
  'img.xjh.me',
  'random.52ecy.cn',
])

function isRandomWallpaperUrl(url: string): boolean {
  try {
    const host = new URL(url).hostname.toLowerCase()
    return RANDOM_WALLPAPER_DOMAINS.has(host)
  } catch {
    return false
  }
}

/**
 * 构建代理 URL。对随机壁纸 API 添加时间戳 cache-buster，
 * 使每次页面加载都能获取新图片（前端内存缓存和浏览器 HTTP 缓存均以 URL 为 key）。
 * 对固定 URL 的壁纸不加 cache-buster，保留缓存优势。
 */
function buildProxyUrl(sourceUrl: string): string {
  const encodedUrl = encodeURIComponent(sourceUrl)
  if (isRandomWallpaperUrl(sourceUrl)) {
    const ts = Date.now()
    return `/api/appearance/wallpaper_proxy?url=${encodedUrl}&_ts=${ts}`
  }
  return `/api/appearance/wallpaper_proxy?url=${encodedUrl}`
}

/**
 * 玻璃壁纸管理：
 * 壁纸 URL 来源优先级：
 * 1. localStorage 中用户保存的 URL
 * 2. CSS 变量 --am-wallpaper-source（tokens.css 中定义）
 * 3. 默认 loliapi 地址
 *
 * WebGL 纹理加载需要 CORS 支持，外部壁纸通过后端 /api/appearance/wallpaper_proxy 代理。
 * 壁纸色调分析（tone profile）用于材质亮度调节。
 */
export function useGlassWallpaper() {
  const themeStore = useThemeStore()
  const vuetifyTheme = useTheme()
  const effectiveGlassSettings = useEffectiveGlassSettings()

  // 从 CSS 变量或 localStorage 获取壁纸源 URL
  const cssWallpaperUrl = extractWallpaperUrlFromCss()
  const savedWallpaperUrl = localStorage.getItem('glass_wallpaper_url') || ''
  const sourceWallpaperUrl = savedWallpaperUrl || cssWallpaperUrl || 'https://www.loliapi.com/acg/pc/'

  // WebGL 使用的壁纸 URL —— 通过后端代理避免 CORS 问题
  // 同源请求天然满足 CORS，WebGL 纹理可直接读取
  // 对随机壁纸 API 添加 _ts cache-buster，每次页面加载获取新图片
  const wallpaperUrl = ref<string>(buildProxyUrl(sourceWallpaperUrl))
  const previousWallpaperUrl = ref<string>('')
  const transitionStartedAt = ref<number>(0)
  const pendingWallpaperUrl = ref<string>('')
  const pendingWallpaperRevision = ref<number>(0)
  const activateWallpaperRevision = ref<number>(0)

  // 壁纸色调 profile —— 用于材质亮度调节
  const wallpaperToneProfile = ref<GlassWallpaperToneProfile>(DEFAULT_GLASS_WALLPAPER_TONE_PROFILE)

  // 壁纸交叉淡化时长
  const TRANSITION_DURATION_MS = 1500

  // 初始化守卫 —— 避免 watch(immediate) 和 onMounted 重复调用 initDefaultWallpaper
  // 导致生成不同的 _ts cache-buster，使同一次页面加载请求多张不同的随机壁纸
  let defaultWallpaperInitialized = false

  const isGlassTheme = computed(() => themeStore.glassTheme === 'acg')
  const shouldRenderGlassOpticalLayer = computed(
    () =>
      isGlassTheme.value &&
      effectiveGlassSettings.value.glassQuality !== 'css' &&
      Boolean(wallpaperUrl.value),
  )

  // 玻璃材质色
  const glassMaterialTintColor = computed(
    () =>
      normalizeThemeMaterialAccent(String(vuetifyTheme.current.value.colors.primary))?.hex ??
      normalizeThemeMaterialAccent(themeCustomizerPrimaryColors[0].value)!.hex,
  )

  // 光学参数
  const opticalDeformationStrength = computed(() => effectiveGlassSettings.value.glassDeformationStrength)
  const opticalFlowStrength = computed(() => effectiveGlassSettings.value.glassFlowStrength)
  const opticalQuality = computed(() => effectiveGlassSettings.value.glassQuality)
  const opticalReflectionStrength = computed(() => effectiveGlassSettings.value.glassReflectionStrength)
  const opticalTransparencyStrength = computed(() => effectiveGlassSettings.value.glassTransparencyStrength)
  const opticalTransmissionStrength = computed(() => effectiveGlassSettings.value.glassTransmissionStrength)
  const opticalTranslationStrength = computed(() => effectiveGlassSettings.value.glassTranslationStrength)

  /** 设置壁纸源 URL（内部会自动转换为代理 URL） */
  function setWallpaperUrl(url: string) {
    if (!url) return
    const proxyUrl = buildProxyUrl(url)
    if (proxyUrl === wallpaperUrl.value) return
    previousWallpaperUrl.value = wallpaperUrl.value
    wallpaperUrl.value = proxyUrl
    transitionStartedAt.value = performance.now()
    localStorage.setItem('glass_wallpaper_url', url)
    syncWallpaperCssVar(url, proxyUrl)
    // 异步分析壁纸色调
    void loadWallpaperTone(proxyUrl)
  }

  /** 将壁纸 URL 同步到 CSS 变量。对随机壁纸 API 使用代理 URL（带 cache-buster），
   * 避免浏览器缓存旧图片；对固定 URL 使用原始 URL（不受 CORS 限制）。 */
  function syncWallpaperCssVar(sourceUrl: string, proxyUrl: string) {
    if (!sourceUrl) {
      document.documentElement.style.removeProperty('--glass-wallpaper-url')
      return
    }
    // 随机壁纸 API 用代理 URL（带 cache-buster），固定壁纸用原始 URL
    const cssUrl = isRandomWallpaperUrl(sourceUrl) ? proxyUrl : sourceUrl
    document.documentElement.style.setProperty('--glass-wallpaper-url', `url("${cssUrl}")`)
  }

  /** 异步加载壁纸色调分析结果，用于材质亮度调节 */
  async function loadWallpaperTone(proxyUrl: string) {
    try {
      const result = await loadGlassWallpaperTone(proxyUrl)
      wallpaperToneProfile.value = result.profile
    } catch {
      wallpaperToneProfile.value = DEFAULT_GLASS_WALLPAPER_TONE_PROFILE
    }
  }

  /** 初始化默认壁纸 —— 从 CSS 变量读取，经后端代理供 WebGL 使用。
   *  含初始化守卫，避免重复调用生成不同的 cache-buster。 */
  function initDefaultWallpaper() {
    if (defaultWallpaperInitialized) return
    defaultWallpaperInitialized = true
    const cssUrl = extractWallpaperUrlFromCss()
    const sourceUrl = cssUrl || 'https://www.loliapi.com/acg/pc/'
    const proxyUrl = buildProxyUrl(sourceUrl)
    wallpaperUrl.value = proxyUrl
    // 同步 CSS 背景变量：随机壁纸用代理 URL（带 cache-buster），固定壁纸用原始 URL
    syncWallpaperCssVar(sourceUrl, proxyUrl)
    // 异步分析壁纸色调
    void loadWallpaperTone(proxyUrl)
  }

  // 当切换到 ACG 主题时，应用玻璃设置并初始化壁纸
  watch(
    () => themeStore.glassTheme,
    (theme) => {
      if (theme === 'acg') {
        applyStoredThemeCustomizerAppearance()
        initDefaultWallpaper()
      }
    },
    { immediate: true },
  )

  onMounted(() => {
    if (isGlassTheme.value) {
      applyStoredThemeCustomizerAppearance()
      initDefaultWallpaper()
    }
  })

  return {
    wallpaperUrl,
    previousWallpaperUrl,
    transitionStartedAt,
    transitionDuration: TRANSITION_DURATION_MS,
    pendingWallpaperUrl,
    pendingWallpaperRevision,
    activateWallpaperRevision,
    shouldRenderGlassOpticalLayer,
    glassMaterialTintColor,
    opticalDeformationStrength,
    opticalFlowStrength,
    opticalQuality,
    opticalReflectionStrength,
    opticalTransparencyStrength,
    opticalTransmissionStrength,
    opticalTranslationStrength,
    effectiveGlassSettings,
    wallpaperToneProfile,
    setWallpaperUrl,
  }
}
