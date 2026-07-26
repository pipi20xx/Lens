import { ref, computed, watch } from 'vue'
import { navigationApi } from '@/api/navigation'
import { useNotification } from '@/composables'

// ========== 类型定义 ==========
export interface SiteItem {
  id: number
  title: string
  url: string
  icon?: string
  description?: string
  category_id?: number
  category?: string
  order: number
}

export interface Category {
  id: number
  name: string
  icon?: string
  order: number
}

// ========== 默认设置 ==========
const DEFAULT_SETTINGS = {
  background_url: '',
  background_opacity: 0.5,
  background_blur: 0,
  background_size: 'cover',
  enable_hd_mode: false,
  background_color: '#1a1a1f',
  enable_background_color: false,
  card_background: 'rgba(30, 30, 35, 0.85)',
  card_blur: 12,
  card_border_color: 'rgba(255, 255, 255, 0.25)',
  card_style: 'glass',
  text_color: '#ffffff',
  text_description_color: 'rgba(255, 255, 255, 0.85)',
  category_title_color: '#ffffff',
  show_category_line: true,
  content_max_width: 85,
  page_title: '站点导航',
  page_subtitle: '个性化您的导航面板',
  wallpaper_mode: 'custom',
  wallpaper_type: 'anime',
  wallpaper_keyword: '',
  wallpaper_resolution: '1920x1080',
  show_hitokoto: false,
  show_clock: false,
  bing_mkt: 'zh-CN',
  bing_index: 0,
  bing_resolution: '1920x1080',
  show_wallpaper_info: false,
  header_alignment: 'left',
  category_alignment: 'left',
  header_item_spacing: 12,
  header_margin_top: 30,
  header_margin_bottom: 40,
  // 内容组件独立样式
  header_background: 'rgba(30, 30, 35, 0.75)',
  header_blur: 8,
  header_border_color: 'rgba(255, 255, 255, 0.2)',
  header_text_color: '#ffffff',
  header_subtitle_color: 'rgba(255, 255, 255, 0.85)',
  clock_text_color: '#ffffff',
  hitokoto_background: 'rgba(30, 30, 35, 0.6)',
  hitokoto_blur: 6,
  hitokoto_border_color: 'rgba(255, 255, 255, 0.15)',
  hitokoto_text_color: '#ffffff',
  hitokoto_from_color: 'rgba(255, 255, 255, 0.7)',
}

// ========== 全局状态 ==========
const sites = ref<SiteItem[]>([])
const categories = ref<Category[]>([])
const navSettings = ref<any>({ ...DEFAULT_SETTINGS })
const loading = ref(false)
const hitokoto = ref({ text: '', from: '' })
const bingInfo = ref({ url: '', title: '', copyright: '' })
const wallpaperLoading = ref(false)
const resolvedWallpaperUrl = ref('')

// ========== composable ==========
export function useSiteNav() {
  const { success, error: showError } = useNotification()

  // --- 壁纸逻辑 ---
  const baseRandomApiUrl = computed(() => {
    const mode = navSettings.value.wallpaper_mode
    const type = navSettings.value.wallpaper_type || 'scenery'
    const res = navSettings.value.wallpaper_resolution || '1920x1080'
    let [width, height] = res.split('x')
    if (res === 'UHD' || res === '3840x2160') { width = '3840'; height = '2160' }
    if (res === '2K' || res === '2560x1440') { width = '2560'; height = '1440' }

    if (mode === 'unsplash') {
      if (type === 'anime') return 'https://www.loliapi.com/acg/pc/'
      if (type === 'scenery') return `https://picsum.photos/${width}/${height}?nature,landscape`
      if (type === 'minimalist') return `https://picsum.photos/${width}/${height}?minimalist,abstract`
      return `https://picsum.photos/${width}/${height}`
    }
    return ''
  })

  const computedBgUrl = computed(() => {
    const mode = navSettings.value.wallpaper_mode
    if (mode === 'bing') return bingInfo.value.url
    if (mode === 'unsplash') return resolvedWallpaperUrl.value || baseRandomApiUrl.value
    return navSettings.value.background_url
  })

  async function refreshWallpaper(apiUrl?: string, forceRefresh = false) {
    if (!apiUrl) { resolvedWallpaperUrl.value = ''; return }
    const seed = Date.now()
    const finalUrl = apiUrl.includes('?')
      ? `${apiUrl}&_seed=${seed}`
      : `${apiUrl}?_seed=${seed}`

    const cacheKey = `lens_wallpaper_cache_${apiUrl}`
    if (!forceRefresh) {
      const cached = localStorage.getItem(cacheKey)
      if (cached) {
        try {
          const { url, expiry } = JSON.parse(cached)
          if (expiry > Date.now()) { resolvedWallpaperUrl.value = url; return }
        } catch { localStorage.removeItem(cacheKey) }
      }
    }

    wallpaperLoading.value = true
    try {
      const res = await fetch(finalUrl, { method: 'GET' })
      if (res.url) {
        resolvedWallpaperUrl.value = res.url
        localStorage.setItem(cacheKey, JSON.stringify({ url: res.url, expiry: Date.now() + 3600 * 1000 }))
      }
    } catch { resolvedWallpaperUrl.value = '' }
    wallpaperLoading.value = false
  }

  // 监听壁纸参数变化
  watch(() => [
    navSettings.value.wallpaper_mode,
    navSettings.value.wallpaper_type,
    navSettings.value.wallpaper_resolution,
    navSettings.value.wallpaper_keyword,
  ], ([mode]) => {
    if (mode === 'unsplash') {
      refreshWallpaper(baseRandomApiUrl.value)
    }
  }, { immediate: true })

  async function saveCurrentWallpaper(url: string) {
    if (!url) return
    try {
      wallpaperLoading.value = true
      const data: any = await navigationApi.saveRemoteBackground(url)
      navSettings.value.background_url = data.url
      navSettings.value.wallpaper_mode = 'custom'
      resolvedWallpaperUrl.value = ''
      success('已成功保存当前壁纸')
    } catch { showError('保存失败') }
    finally { wallpaperLoading.value = false }
  }

  // --- 一言 ---
  async function fetchHitokoto() {
    try {
      const res = await fetch('https://v1.hitokoto.cn')
      const data = await res.json()
      hitokoto.value = { text: data.hitokoto, from: data.from }
    } catch {
      hitokoto.value = { text: '心之所向，素履以往。', from: '七堇年' }
    }
  }

  // --- 必应壁纸 ---
  async function fetchBingWallpaper() {
    try {
      const { bing_index, bing_mkt, bing_resolution } = navSettings.value
      const data: any = await navigationApi.getBingWallpaper(bing_index || 0, bing_mkt || 'zh-CN', bing_resolution || '1920x1080')
      if (data.url) bingInfo.value = data
    } catch { /* ignore */ }
  }

  watch(() => navSettings.value.wallpaper_mode, (mode) => {
    if (mode === 'bing') fetchBingWallpaper()
  })

  watch(() => [
    navSettings.value.bing_mkt,
    navSettings.value.bing_index,
    navSettings.value.bing_resolution,
  ], () => {
    if (navSettings.value.wallpaper_mode === 'bing') fetchBingWallpaper()
  })

  // --- 数据加载 ---
  async function loadAll() {
    try {
      loading.value = true
      const [sitesData, catsData, settingsData] = await Promise.all([
        navigationApi.getSites(),
        navigationApi.getCategories(),
        navigationApi.getSettings(),
      ])
      sites.value = Array.isArray(sitesData) ? sitesData.sort((a: any, b: any) => a.order - b.order) : []
      categories.value = Array.isArray(catsData) ? catsData.sort((a: any, b: any) => a.order - b.order) : []
      navSettings.value = { ...DEFAULT_SETTINGS, ...(settingsData || {}) }
    } catch { showError('加载导航数据失败') }
    finally { loading.value = false }
  }

  // --- 设置 ---
  async function updateNavSettings(settings: Record<string, any>) {
    try {
      await navigationApi.updateSettings(settings)
      navSettings.value = { ...navSettings.value, ...settings }
    } catch { showError('保存设置失败') }
  }

  async function resetNavSettings() {
    const { background_url, ...styleSettings } = DEFAULT_SETTINGS
    await updateNavSettings(styleSettings)
    success('已恢复默认样式')
  }

  async function uploadBackground(file: File) {
    try {
      const data: any = await navigationApi.uploadBackground(file)
      navSettings.value.background_url = data.url
      success('背景上传成功')
      return data.url
    } catch { showError('背景上传失败'); return null }
  }

  // --- 站点 CRUD ---
  async function addSite(site: Partial<SiteItem>): Promise<boolean> {
    try {
      await navigationApi.createSite(site)
      success('添加成功')
      await loadAll()
      return true
    } catch { showError('添加失败'); return false }
  }

  async function updateSite(id: number, site: Partial<SiteItem>): Promise<boolean> {
    try {
      await navigationApi.updateSite(id, site)
      success('更新成功')
      await loadAll()
      return true
    } catch { showError('更新失败'); return false }
  }

  async function deleteSite(id: number) {
    try {
      await navigationApi.deleteSite(id)
      success('删除成功')
      await loadAll()
    } catch { showError('删除失败') }
  }

  async function reorderSites(ids: number[]) {
    try { await navigationApi.reorderSites(ids) } catch { /* ignore */ }
  }

  async function fetchIconFromUrl(url: string): Promise<string | null> {
    if (!url) return null
    try {
      const data: any = await navigationApi.fetchIcon(url)
      return data.icon || null
    } catch { return null }
  }

  // --- 分类 CRUD ---
  async function addCategory(name: string, icon = '') {
    try {
      await navigationApi.createCategory({ name, icon, order: categories.value.length })
      await loadAll()
    } catch { showError('添加分类失败') }
  }

  async function updateCategory(id: number, name: string, icon = '') {
    try {
      await navigationApi.updateCategory(id, { name, icon })
      await loadAll()
    } catch { showError('更新分类失败') }
  }

  async function deleteCategory(id: number) {
    try {
      await navigationApi.deleteCategory(id)
      await loadAll()
    } catch { showError('删除分类失败') }
  }

  async function reorderCategories(ids: number[]) {
    try {
      await navigationApi.reorderCategories(ids)
      const newCats = [...categories.value].sort((a, b) => ids.indexOf(a.id) - ids.indexOf(b.id))
      categories.value = newCats
    } catch { /* ignore */ }
  }

  // --- 导出导入 ---
  function exportConfig() {
    const token = localStorage.getItem('lens_access_token')
    const url = '/api/navigation/export'
    // 通过隐藏链接下载（带 auth header 需要特殊处理）
    const link = document.createElement('a')
    link.href = url + (token ? `?token=${token}` : '')
    link.download = 'navigation_backup.zip'
    link.click()
  }

  async function importConfig(file: File) {
    try {
      await navigationApi.importNavigation(file)
      success('配置导入成功')
      await loadAll()
      return true
    } catch { showError('导入失败，请检查文件格式'); return false }
  }

  // --- 工具函数 ---
  const groupedSites = computed(() => {
    const result: { id: number; name: string; icon?: string; sites: SiteItem[] }[] = []
    categories.value.forEach(cat => {
      result.push({ id: cat.id, name: cat.name, icon: cat.icon, sites: [] })
    })
    sites.value.forEach(site => {
      const group = result.find(g => g.id === site.category_id)
      if (group) group.sites.push(site)
    })
    return result.filter(g => g.sites.length > 0)
  })

  function isEmoji(str: string) {
    if (!str) return false
    if (str.includes('/') || str.includes('.')) return false
    return /\p{Emoji}/u.test(str) && str.length <= 4
  }

  function isLightBackground(color: string): boolean {
    if (!color) return false
    const hex = color.replace('#', '')
    let r: number, g: number, b: number
    if (hex.length === 3) {
      r = parseInt(hex[0] + hex[0], 16); g = parseInt(hex[1] + hex[1], 16); b = parseInt(hex[2] + hex[2], 16)
    } else if (hex.length >= 6) {
      r = parseInt(hex.substring(0, 2), 16); g = parseInt(hex.substring(2, 4), 16); b = parseInt(hex.substring(4, 6), 16)
    } else { return false }
    return (r * 299 + g * 587 + b * 114) / 1000 > 200
  }

  return {
    // 状态
    sites, categories, navSettings, loading, hitokoto, bingInfo,
    wallpaperLoading, resolvedWallpaperUrl,
    // 计算
    baseRandomApiUrl, computedBgUrl, groupedSites,
    // 壁纸
    refreshWallpaper, saveCurrentWallpaper, fetchBingWallpaper,
    // 一言
    fetchHitokoto,
    // 数据
    loadAll, updateNavSettings, resetNavSettings, uploadBackground,
    // 站点
    addSite, updateSite, deleteSite, reorderSites, fetchIconFromUrl,
    // 分类
    addCategory, updateCategory, deleteCategory, reorderCategories,
    // 导出导入
    exportConfig, importConfig,
    // 工具
    isEmoji, isLightBackground,
  }
}
