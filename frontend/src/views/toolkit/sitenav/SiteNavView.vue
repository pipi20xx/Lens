<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSiteNav } from './composables/useSiteNav'
import { useConfirm } from '@/composables'
import NavClock from './components/NavClock.vue'
import SiteCard from './components/SiteCard.vue'
import SiteEditorDialog from './components/SiteEditorDialog.vue'
import SettingsDialog from './components/SettingsDialog.vue'

// ACG 主题状态由全局 DefaultLayout 管理（useGlassWallpaper / GlassOpticalLayer / GlassSettingsDialog）
// SiteNavView 只读 themeStore.appTheme 来决定 CSS 变量和背景层显示
import { useThemeStore } from '@/stores/useThemeStore'

const themeStore = useThemeStore()
const glassAcgEnabled = computed(() => themeStore.appTheme === 'acg')

const router = useRouter()
const { confirm } = useConfirm()
const {
  sites, categories, navSettings, loading, hitokoto, bingInfo,
  wallpaperLoading, baseRandomApiUrl, computedBgUrl, groupedSites,
  refreshWallpaper, saveCurrentWallpaper, fetchHitokoto,
  loadAll, updateNavSettings, resetNavSettings, uploadBackground,
  addSite, updateSite, deleteSite, reorderSites, fetchIconFromUrl,
  addCategory, deleteCategory, reorderCategories, updateCategory,
  exportConfig, importConfig, isEmoji, isLightBackground,
} = useSiteNav()

onMounted(() => {
  loadAll()
  fetchHitokoto()
})

// ========== 站点编辑 ==========
const showSiteDialog = ref(false)
const editingSite = ref<any>(null)
const fetchingIcon = ref(false)

function openAddSite(categoryId?: number) {
  editingSite.value = {
    title: '', url: '', icon: '', description: '',
    category_id: categoryId || (categories.value.length > 0 ? categories.value[0].id : undefined),
    order: sites.value.length,
  }
  showSiteDialog.value = true
}

function openEditSite(site: any) {
  editingSite.value = { ...site }
  showSiteDialog.value = true
}

async function handleSaveSite() {
  if (!editingSite.value) return
  const ok = editingSite.value.id
    ? await updateSite(editingSite.value.id, editingSite.value)
    : await addSite(editingSite.value)
  if (ok) showSiteDialog.value = false
}

async function handleAutoFetchIcon() {
  if (!editingSite.value?.url) return
  fetchingIcon.value = true
  const icon = await fetchIconFromUrl(editingSite.value.url)
  if (icon) editingSite.value.icon = icon
  fetchingIcon.value = false
}

// ========== 删除站点 ==========
async function handleDeleteSite(id: number) {
  const ok = await confirm({ title: '删除确认', content: '确定删除此站点吗？', confirmColor: 'error' })
  if (!ok) return
  await deleteSite(id)
}

// ========== 拖拽排序 ==========
const dragSiteId = ref<number | null>(null)

function onDragStart(siteId: number) { dragSiteId.value = siteId }

function onDragEnter(targetId: number) {
  if (!dragSiteId.value || dragSiteId.value === targetId) return
  const fromIndex = sites.value.findIndex(s => s.id === dragSiteId.value)
  const toIndex = sites.value.findIndex(s => s.id === targetId)
  if (fromIndex !== -1 && toIndex !== -1) {
    if (sites.value[fromIndex].category_id !== sites.value[toIndex].category_id) {
      sites.value[fromIndex].category_id = sites.value[toIndex].category_id
      sites.value[fromIndex].category = sites.value[toIndex].category
    }
    const [item] = sites.value.splice(fromIndex, 1)
    sites.value.splice(toIndex, 0, item)
  }
}

async function onDragEnd() {
  if (dragSiteId.value !== null) {
    await reorderSites(sites.value.map(s => s.id))
  }
  dragSiteId.value = null
}

// ========== 设置面板 ==========
const showSettings = ref(false)

async function handleUpdateSettings(patch: Record<string, any>) {
  // 实时保存到后端
  await updateNavSettings(patch)
}

async function handleUploadBg(file: File) {
  await uploadBackground(file)
}

async function handleRefreshWallpaper() {
  refreshWallpaper(baseRandomApiUrl.value, true)
}

async function handleSaveWallpaper() {
  await saveCurrentWallpaper(computedBgUrl.value)
}

async function handleResetSettings() {
  await resetNavSettings()
}

async function handleDeleteCategory(id: number) {
  const ok = await confirm({ title: '删除确认', content: '删除分类后，该分类下的站点将变为未分类。确定删除？', confirmColor: 'error' })
  if (ok) await deleteCategory(id)
}

async function handleImportConfig(file: File) {
  await importConfig(file)
}

// ========== 右键菜单 ==========
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuSite = ref<any>(null)

function handleContextMenu(e: MouseEvent, site: any) {
  e.preventDefault()
  contextMenuSite.value = site
  contextMenuX.value = e.clientX
  contextMenuY.value = e.clientY
  showContextMenu.value = true
}

function contextMenuEdit() {
  showContextMenu.value = false
  if (contextMenuSite.value) openEditSite(contextMenuSite.value)
}

async function contextMenuDelete() {
  showContextMenu.value = false
  if (contextMenuSite.value) await handleDeleteSite(contextMenuSite.value.id)
}

watch(showContextMenu, (val) => {
  if (val) {
    nextTick(() => {
      document.addEventListener('click', closeContextMenu, { once: true })
    })
  }
})
function closeContextMenu() { showContextMenu.value = false }

// ========== 工具 ==========
function openUrl(url: string) {
  if (url) window.open(url, '_blank')
}

function goBack() { router.push('/') }

const getCategoryIcon = (categoryId: number) => {
  const cat = categories.value.find(c => c.id === categoryId)
  return cat?.icon || ''
}

// ========== ACG 主题：CSS 变量适配 ==========
// ACG 玻璃渲染（WebGL、壁纸、设置弹窗）已移至全局 DefaultLayout。
// 这里只负责站点导航页面的 CSS 变量适配。

// ========== CSS 变量 ==========
// ACG 玻璃开启时，卡片/背景相关变量由 glass-acg.scss 接管，
// 这里将相关变量设为 transparent / none 避免高级设置的行内样式覆盖玻璃效果。
const cssVars = computed(() => {
  const acg = glassAcgEnabled.value
  return {
    '--nav-card-bg': acg ? 'transparent' : (navSettings.value.card_background || 'rgba(255, 255, 255, 0.12)'),
    '--nav-card-blur': acg ? '0px' : `${navSettings.value.card_blur ?? 16}px`,
    '--nav-card-border': acg ? 'transparent' : (navSettings.value.card_border_color || 'rgba(255, 255, 255, 0.15)'),
    '--nav-text-color': navSettings.value.text_color || '#ffffff',
    '--nav-text-desc-color': navSettings.value.text_description_color || 'rgba(255, 255, 255, 0.7)',
    '--nav-bg-color': acg ? 'transparent' : (navSettings.value.enable_background_color ? (navSettings.value.background_color || '#1e1e22') : 'transparent'),
    '--nav-category-color': navSettings.value.category_title_color || '#ffffff',
    '--nav-content-width': `${navSettings.value.content_max_width || 90}%`,
    '--nav-category-align': navSettings.value.category_alignment || 'left',
    '--nav-header-align': navSettings.value.header_alignment || 'left',
    '--nav-header-gap': `${navSettings.value.header_item_spacing ?? 12}px`,
    '--nav-header-mt': `${navSettings.value.header_margin_top ?? 20}px`,
    '--nav-header-mb': `${navSettings.value.header_margin_bottom ?? 30}px`,
    '--nav-header-text-color': navSettings.value.header_text_color || '#ffffff',
    '--nav-header-subtitle-color': navSettings.value.header_subtitle_color || 'rgba(255, 255, 255, 0.85)',
    '--nav-clock-text-color': navSettings.value.clock_text_color || '#ffffff',
    '--nav-hitokoto-bg': acg ? 'rgba(11, 19, 34, 0.4)' : (navSettings.value.hitokoto_background || 'rgba(30, 30, 35, 0.6)'),
    '--nav-hitokoto-text-color': navSettings.value.hitokoto_text_color || '#ffffff',
    '--nav-hitokoto-from-color': navSettings.value.hitokoto_from_color || 'rgba(255, 255, 255, 0.7)',
  }
})

const headerAlignClass = computed(() => {
  const a = navSettings.value.header_alignment
  if (a === 'center') return 'align-center'
  if (a === 'right') return 'align-right'
  return 'align-left'
})

const categoryAlignStyle = computed(() => {
  const a = navSettings.value.category_alignment
  if (a === 'center') return 'center'
  if (a === 'right') return 'flex-end'
  return 'flex-start'
})

// ACG 玻璃开启时不需要原来的遮罩层，WebGL 渲染层会接管背景
const overlayBg = computed(() => {
  if (glassAcgEnabled.value) return 'none'
  if (!navSettings.value.enable_background_color || isLightBackground(navSettings.value.background_color)) {
    return 'none'
  }
  return undefined // 使用 CSS 默认值
})
</script>

<template>
  <div class="site-nav-page" :class="{ 'glass-acg': glassAcgEnabled }" :style="cssVars" @click="showContextMenu = false">
    <!-- 非_ACG 背景层 -->
    <div v-if="!glassAcgEnabled" class="bg-base"></div>
    <transition v-if="!glassAcgEnabled" name="fade-bg">
      <div
        v-if="computedBgUrl"
        :key="computedBgUrl"
        class="bg-image"
        :style="{
          backgroundImage: `url('${computedBgUrl}')`,
          opacity: navSettings.enable_hd_mode ? 1 : (navSettings.background_opacity ?? 0.7),
          filter: navSettings.enable_hd_mode ? 'none' : `blur(${navSettings.background_blur ?? 0}px)`,
          backgroundSize: navSettings.background_size || 'cover',
        }"
      ></div>
    </transition>
    <div v-if="!glassAcgEnabled && !navSettings.enable_hd_mode" class="bg-overlay" :style="{ background: overlayBg }"></div>

    <!-- ACG 模式下背景由全局 WebGL 渲染层和 body 壁纸接管 -->

    <!--
      ACG 模式：整个页面用一块大玻璃卡片包裹。
      标记 data-glass-optical-surface 让 WebGL 渲染器发现该表面并渲染水纹折射。
      CSS 中覆盖掉 [data-glass-optical-surface] 自动添加的 backdrop-filter: blur(16px)，
      保持卡片本身完全透明——水纹效果由 WebGL canvas 直接渲染，不需要 DOM 磨砂基底。
    -->
    <div class="glass-page-surface" :data-glass-optical-surface="glassAcgEnabled ? '' : undefined">
      <!-- 必应壁纸信息 -->
      <div
        v-if="navSettings.wallpaper_mode === 'bing' && navSettings.show_wallpaper_info && bingInfo.title"
        class="wallpaper-info"
      >
        <div class="wp-title">{{ bingInfo.title }}</div>
        <div class="wp-copyright">{{ bingInfo.copyright }}</div>
      </div>

      <!-- 内容包裹层 -->
      <div class="nav-content">
        <!-- 顶部头部 -->
        <div class="nav-header" :style="{ marginTop: 'var(--nav-header-mt)', marginBottom: 'var(--nav-header-mb)' }">
          <div class="header-left" :class="headerAlignClass" :style="{ gap: 'var(--nav-header-gap)' }">
            <!-- 时钟 -->
            <NavClock
              v-if="navSettings.show_clock"
              :alignment="navSettings.header_alignment"
              :text-color="navSettings.clock_text_color"
            />

            <div v-if="navSettings.page_title" class="page-title">{{ navSettings.page_title }}</div>
            <div class="page-subtitle">{{ navSettings.page_subtitle || '' }}</div>

            <!-- 每日一言 -->
            <div
              v-if="navSettings.show_hitokoto"
              class="hitokoto-container"
              :class="headerAlignClass"
              @click="fetchHitokoto"
            >
              <span class="hitokoto-text">" {{ hitokoto.text }} "</span>
              <span class="hitokoto-from">—— {{ hitokoto.from }}</span>
            </div>
          </div>

          <div class="header-right">
            <v-btn icon variant="text" size="small" @click="goBack" title="返回管理后台">
              <v-icon>mdi-arrow-left</v-icon>
            </v-btn>
            <v-btn icon variant="text" size="small" @click="openAddSite()" title="添加站点">
              <v-icon>mdi-plus</v-icon>
            </v-btn>
            <v-btn icon variant="text" size="small" @click="showSettings = true" title="设置">
              <v-icon>mdi-cog-outline</v-icon>
            </v-btn>
            <v-btn icon variant="text" size="small" @click="loadAll" :loading="loading" title="刷新">
              <v-icon>mdi-refresh</v-icon>
            </v-btn>
          </div>
        </div>

        <!-- 加载中 -->
        <div v-if="loading && sites.length === 0" class="loading-state">
          <v-progress-circular indeterminate size="48" color="white" />
        </div>

        <!-- 空状态 -->
        <div v-if="!loading && sites.length === 0" class="empty-state">
          <v-icon size="64" color="rgba(255,255,255,0.5)" class="mb-4">mdi-compass-outline</v-icon>
          <div class="empty-text">还没有站点</div>
          <v-btn variant="tonal" color="white" class="mt-4" prepend-icon="mdi-plus" @click="openAddSite()">
            添加第一个站点
          </v-btn>
        </div>

        <!-- 分类分组展示 -->
        <transition-group name="stagger" tag="div">
          <div v-for="group in groupedSites" :key="group.id" class="category-section">
            <div class="category-header" :style="{ justifyContent: categoryAlignStyle }">
              <div class="category-title-container">
                <span v-if="getCategoryIcon(group.id) && isEmoji(getCategoryIcon(group.id))" class="category-emoji">
                  {{ getCategoryIcon(group.id) }}
                </span>
                <img v-else-if="getCategoryIcon(group.id)" :src="getCategoryIcon(group.id)" class="category-img-icon" />
                <div class="category-title">{{ group.name }}</div>
              </div>
              <div v-if="navSettings.show_category_line" class="category-line"></div>
              <v-btn icon variant="text" size="x-small" class="category-add-btn" @click="openAddSite(group.id)">
                <v-icon size="16">mdi-plus-circle-outline</v-icon>
              </v-btn>
            </div>

            <div class="sites-grid">
              <SiteCard
                v-for="(site, index) in group.sites"
                :key="site.id"
                :site="site"
                :style-mode="navSettings.card_style"
                :is-dragging="dragSiteId === site.id"
                :style="{ '--i': index }"
                @click="openUrl(site.url)"
                @contextmenu="handleContextMenu($event, site)"
                @dragstart="onDragStart(site.id)"
                @dragenter="onDragEnter(site.id)"
                @dragend="onDragEnd"
              />
            </div>
          </div>
        </transition-group>
      </div>
    </div><!-- /glass-page-surface -->

    <!-- 右键菜单 -->
    <div
      v-if="showContextMenu"
      class="context-menu"
      :style="{ left: contextMenuX + 'px', top: contextMenuY + 'px' }"
      @click.stop
    >
      <div class="context-menu-item" @click="contextMenuEdit">
        <v-icon size="16" class="mr-2">mdi-pencil-outline</v-icon>编辑站点
      </div>
      <div class="context-menu-item danger" @click="contextMenuDelete">
        <v-icon size="16" class="mr-2">mdi-delete-outline</v-icon>删除站点
      </div>
    </div>

    <!-- 站点编辑弹窗 -->
    <SiteEditorDialog
      v-model="showSiteDialog"
      :editing-site="editingSite"
      :categories="categories"
      :fetching-icon="fetchingIcon"
      @save="handleSaveSite"
      @fetch-icon="handleAutoFetchIcon"
      @update:editing-site="editingSite = $event"
    />

    <!-- 设置弹窗 -->
    <SettingsDialog
      v-model="showSettings"
      :settings="navSettings"
      :categories="categories"
      :wallpaper-loading="wallpaperLoading"
      :base-random-api-url="baseRandomApiUrl"
      @update:settings="handleUpdateSettings"
      @reset-settings="handleResetSettings"
      @upload-bg="handleUploadBg"
      @refresh-wallpaper="handleRefreshWallpaper"
      @save-wallpaper="handleSaveWallpaper"
      @add-category="(name, icon) => addCategory(name, icon)"
      @delete-category="handleDeleteCategory"
      @reorder-categories="reorderCategories"
      @update-category="updateCategory"
      @export="exportConfig"
      @import="handleImportConfig"
    />

  </div>
</template>

<style scoped>
.site-nav-page {
  position: relative;
  min-height: 100vh;
  width: 100vw;
  overflow-x: hidden;
  color: var(--nav-text-color, #fff);
}

/* === ACG 大玻璃卡片表面 === */
.glass-page-surface {
  position: relative;
  min-height: 100vh;
  width: 100%;
  z-index: 4;
}

/* === 背景层 === */
.bg-base {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  z-index: 0;
  background-color: var(--nav-bg-color);
}
.bg-image {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  z-index: 1;
  background-position: center;
  background-repeat: no-repeat;
  pointer-events: none;
  transition: opacity 1s ease, filter 1s ease;
}
.bg-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  z-index: 2;
  background: radial-gradient(circle at center, transparent 0%, rgba(0,0,0,0.4) 100%),
              linear-gradient(to bottom, rgba(0,0,0,0.2) 0%, transparent 20%, transparent 80%, rgba(0,0,0,0.3) 100%);
  pointer-events: none;
}

/* === 必应壁纸信息 === */
.wallpaper-info {
  position: fixed; bottom: 16px; right: 20px;
  z-index: 3; text-align: right;
  text-shadow: 0 2px 8px rgba(0,0,0,0.6);
  pointer-events: none;
}
.wp-title { font-size: 14px; font-weight: 600; color: rgb(255,255,255); }
.wp-copyright { font-size: 11px; color: rgb(255,255,255); margin-top: 2px; }

/* === 内容层 === */
.nav-content {
  position: relative;
  max-width: var(--nav-content-width);
  margin: 0 auto;
  padding: 0 20px 60px;
  min-height: 100vh;
}

/* === 头部 === */
.nav-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  flex-wrap: wrap; gap: 12px;
}
.header-left {
  flex: 1; display: flex; flex-direction: column; min-width: 200px;
}
.header-left.align-left { align-items: flex-start; }
.header-left.align-center { align-items: center; }
.header-left.align-right { align-items: flex-end; }

.page-title {
  font-size: 24px; font-weight: 800;
  color: var(--nav-header-text-color);
  text-shadow: 0 4px 12px rgba(0,0,0,0.5);
  letter-spacing: -0.5px;
}
.page-subtitle {
  font-size: 13px; color: var(--nav-header-subtitle-color);
  margin-bottom: 0;
}

/* 每日一言 */
.hitokoto-container {
  display: inline-flex; flex-direction: column;
  margin-top: 12px; cursor: pointer;
  transition: all 0.3s ease;
  max-width: 600px; padding: 8px 12px;
  border-radius: 8px;
  background: var(--nav-hitokoto-bg);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(255,255,255,0.08);
}
.hitokoto-container.align-center { align-items: center; }
.hitokoto-container.align-right { align-items: flex-end; }
.hitokoto-container.align-left { align-items: flex-start; }
.hitokoto-container:hover {
  background: rgba(255,255,255,0.1);
  transform: translateY(-2px);
}
.hitokoto-text { font-size: 14px; color: var(--nav-hitokoto-text-color); font-style: italic; }
.hitokoto-from { font-size: 12px; color: var(--nav-hitokoto-from-color); align-self: flex-end; margin-top: 6px; }

/* === 右上按钮 === */
.header-right {
  display: flex; gap: 4px; align-items: center; flex-shrink: 0;
  align-self: flex-start;
}
.header-right :deep(.v-btn) {
  color: rgb(255,255,255) !important;
}

/* === 加载 / 空状态 === */
.loading-state, .empty-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 120px 0; text-align: center;
}
.empty-text { font-size: 16px; color: rgb(255,255,255); }

/* === 分类区域 === */
.category-section { margin-bottom: 48px; }
.category-header {
  display: flex; align-items: center; gap: 12px;
  min-height: 32px; margin: 0 0 20px 0;
}
.category-title-container { display: flex; align-items: center; gap: 8px; }
.category-emoji { font-size: 20px; line-height: 1; display: flex; align-items: center; }
.category-img-icon { width: 22px; height: 22px; object-fit: contain; }
.category-title {
  font-size: 18px; font-weight: 700;
  color: var(--nav-category-color);
  text-shadow: 0 2px 4px rgba(0,0,0,0.3);
  opacity: 0.95; white-space: nowrap;
}
.category-line {
  height: 1px; flex: 1;
  background: linear-gradient(to right, var(--nav-category-color), transparent);
  opacity: 0.2;
}
.category-add-btn {
  opacity: 0; transition: all 0.3s ease;
  color: rgb(255,255,255) !important;
}
.category-header:hover .category-add-btn { opacity: 1; }

/* === 站点网格 === */
.sites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px; width: 100%;
}

/* === 右键菜单 === */
.context-menu {
  position: fixed; z-index: 9999;
  background: rgba(30,30,35,0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 10px; padding: 4px;
  min-width: 160px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.context-menu-item {
  display: flex; align-items: center; padding: 8px 12px;
  border-radius: 6px; cursor: pointer; font-size: 13px;
  color: rgb(255,255,255); transition: background 0.2s;
}
.context-menu-item:hover { background: rgba(255,255,255,0.1); }
.context-menu-item.danger:hover { background: rgba(244,67,54,0.2); color: #ef5350; }

/* === 动画 === */
.fade-bg-enter-active, .fade-bg-leave-active { transition: opacity 1.2s ease; }
.fade-bg-enter-from, .fade-bg-leave-to { opacity: 0; }

.stagger-enter-active {
  transition: all 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  transition-delay: calc(var(--i, 0) * 0.05s);
}
.stagger-enter-from { opacity: 0; transform: translateY(30px) scale(0.9); }

/* === 响应式 === */
@media (max-width: 600px) {
  .nav-content { padding: 0 12px 40px; }
  .sites-grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
  .page-title { font-size: 20px; }
}
</style>
