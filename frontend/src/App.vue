<script setup lang="ts">
import { ref, watch, computed, onMounted, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import { useThemeStore, useSystemStore } from '@/stores'
import DefaultLayout from '@/layouts/DefaultLayout.vue'
import {
  useGlassWallpaper,
  isChromiumFixedShellBackplateBrowser,
  provideGlassFixedShellBackplate,
  shouldUseGlassFixedShellBackplate,
  type GlassFixedShellBackplateLayer,
  DEFAULT_GLASS_WALLPAPER_TONE_PROFILE,
  loadGlassWallpaperTone,
  type GlassWallpaperToneProfile,
} from '@/glass'

const route = useRoute()
const theme = useTheme()
const themeStore = useThemeStore()
const systemStore = useSystemStore()

// 判断当前路由是否为独立全屏页面（不带 DefaultLayout）
const isStandalone = computed(() => route.meta.standalone === true)

// 同步主题：light → Vuetify light；dark → Vuetify dark；acg → Vuetify acg
// 关键：ACG 主题使用独立的 Vuetify 主题名 'acg'，这样 Vuetify 会添加
// .v-theme--acg 类而非 .v-theme--dark，global.css 中的 .v-theme--dark
// 规则不会生效，从根本上避免了 CSS 优先级冲突
function applyTheme(appTheme: 'light' | 'dark' | 'acg') {
  const vuetifyThemeName = appTheme // 'light' | 'dark' | 'acg' 直接映射
  if (typeof theme.change === 'function') {
    theme.change(vuetifyThemeName)
  } else {
    theme.global.name.value = vuetifyThemeName
  }

  // ACG 玻璃 class 管理
  const html = document.documentElement
  const body = document.body
  html.classList.remove('glass-theme-acg', 'glass-theme-liquid', 'glass-theme-classic')
  body.classList.remove('glass-theme-acg', 'glass-theme-liquid', 'glass-theme-classic')

  if (appTheme === 'acg') {
    html.classList.add('glass-theme-acg')
    body.classList.add('glass-theme-acg')
    // 设置 data-theme 属性 —— 让 TS 文件中的 data-theme 检查和 CSS 选择器都能工作
    html.setAttribute('data-theme', 'glass')
    body.setAttribute('data-theme', 'glass')
  } else {
    html.removeAttribute('data-theme')
    body.removeAttribute('data-theme')
  }
}

applyTheme(themeStore.appTheme)

watch(() => themeStore.appTheme, (val) => {
  applyTheme(val)
})

// ── 玻璃壁纸与光学层管理 ──────────────────────────────────────

// 玻璃光学层（异步加载，避免首屏阻塞）
const GlassOpticalLayer = defineAsyncComponent(() => import('@/glass/components/GlassOpticalLayer.vue'))

// 玻璃壁纸与光学设置
const glass = useGlassWallpaper()

// 壁纸背景层状态
interface BackgroundLayer {
  key: string
  role: 'active' | 'previous'
  url: string
}

function createBackgroundLayers(): BackgroundLayer[] {
  return [
    { key: 'bg-1', role: 'active', url: '' },
    { key: 'bg-2', role: 'previous', url: '' },
  ]
}

function prepareBackgroundLayer(layers: BackgroundLayer[], newUrl: string): BackgroundLayer[] {
  return layers.map(layer =>
    layer.role === 'active'
      ? { ...layer, role: 'previous' as const, url: layer.url }
      : { ...layer, role: 'active' as const, url: newUrl },
  )
}

function activateBackgroundLayer(layers: BackgroundLayer[]): BackgroundLayer[] {
  return layers
    .filter(layer => layer.role === 'active' || layer.url)
    .map(layer => layer.role === 'previous' && !layer.url ? { ...layer, role: 'active' as const } : layer)
}

function settleBackgroundLayers(layers: BackgroundLayer[]): BackgroundLayer[] {
  return layers.map(layer =>
    layer.role === 'previous' ? { ...layer, role: 'active' as const, url: '' } : layer,
  )
}

const backgroundLayers = ref<BackgroundLayer[]>(createBackgroundLayers())
const backgroundToneProfiles = ref<Record<string, GlassWallpaperToneProfile>>({})
const backgroundDisplayImages = ref<Record<string, string>>({})
const backgroundCorsReady = ref<Record<string, boolean>>({})
const isBackgroundCrossfading = ref(false)
const backgroundCrossfadeStartedAt = ref(0)
const BACKGROUND_CROSSFADE_DURATION_MS = 1500

const isACG = computed(() => themeStore.appTheme === 'acg')
const isLogin = computed(() => Boolean(systemStore.isLoggedIn))
const shouldUseGlassBackgroundTreatment = computed(
  () => isACG.value && Boolean(isLogin.value),
)
const shouldLoadBackgroundImages = computed(
  () => Boolean(isLogin.value) && isACG.value,
)
const renderedBackgroundLayers = computed(() => backgroundLayers.value)
const activeBackgroundImage = computed(() => glass.wallpaperUrl.value)
const previousBackgroundImage = computed(() => glass.previousWallpaperUrl.value)
const isBackgroundCrossfadingNow = computed(() => isBackgroundCrossfading.value)

function getBackgroundDisplayUrl(layer: BackgroundLayer): string {
  return layer.url
}

function getBackgroundLayerImageSource(layer: BackgroundLayer): string {
  return backgroundCorsReady.value[layer.url] ? getBackgroundDisplayUrl(layer) : ''
}

function getBackgroundLayerCrossOrigin(layer: BackgroundLayer): 'anonymous' | undefined {
  return backgroundCorsReady.value[layer.url] ? 'anonymous' : undefined
}

function getBackgroundLayerStyle(layer: BackgroundLayer) {
  const profile = backgroundToneProfiles.value[layer.url] ?? DEFAULT_GLASS_WALLPAPER_TONE_PROFILE
  const appearance = glass.effectiveGlassSettings.value.glassAppearance
  const materialExposure = appearance === 'frosted' ? 0.82 : appearance === 'tinted' ? 0.85 : 0.86
  const displayUrl = getBackgroundDisplayUrl(layer)
  const usesCorsImageElement = Boolean(getBackgroundLayerImageSource(layer))

  return {
    'backgroundImage': !usesCorsImageElement && displayUrl ? `url(${displayUrl})` : undefined,
    '--glass-wallpaper-brightness': String(materialExposure * profile.exposure),
  }
}

async function preloadWallpaperCandidate(proxyUrl: string) {
  if (!proxyUrl) return false

  try {
    const tone = await loadGlassWallpaperTone(proxyUrl)
    backgroundToneProfiles.value = {
      ...backgroundToneProfiles.value,
      [proxyUrl]: tone.profile,
    }
    if (tone.corsReady) {
      backgroundDisplayImages.value = {
        ...backgroundDisplayImages.value,
        [proxyUrl]: proxyUrl,
      }
      backgroundCorsReady.value = {
        ...backgroundCorsReady.value,
        [proxyUrl]: true,
      }
      return true
    }
    backgroundDisplayImages.value = {
      ...backgroundDisplayImages.value,
      [proxyUrl]: proxyUrl,
    }
    backgroundCorsReady.value = {
      ...backgroundCorsReady.value,
      [proxyUrl]: false,
    }
    return false
  } catch {
    return false
  }
}

watch(activeBackgroundImage, async (newUrl, oldUrl) => {
  if (!newUrl) return
  if (newUrl === oldUrl) return

  await preloadWallpaperCandidate(newUrl)

  backgroundLayers.value = prepareBackgroundLayer(backgroundLayers.value, newUrl)
  isBackgroundCrossfading.value = true
  backgroundCrossfadeStartedAt.value = performance.now()

  window.setTimeout(() => {
    backgroundLayers.value = activateBackgroundLayer(backgroundLayers.value)
    backgroundLayers.value = settleBackgroundLayers(backgroundLayers.value)
    isBackgroundCrossfading.value = false
  }, BACKGROUND_CROSSFADE_DURATION_MS)
}, { immediate: true })

watch(shouldUseGlassBackgroundTreatment, (shouldUse) => {
  if (shouldUse) {
    const currentUrl = activeBackgroundImage.value
    const activeLayer = backgroundLayers.value.find(l => l.role === 'active')
    if (currentUrl && (!activeLayer || !activeLayer.url)) {
      backgroundLayers.value = backgroundLayers.value.map(layer =>
        layer.role === 'active' ? { ...layer, url: currentUrl } : layer,
      )
      void preloadWallpaperCandidate(currentUrl)
    }
  }
})

// ── Fixed Shell Backplate ──────────────────────────────────
const needsStableFixedBackdrop = isChromiumFixedShellBackplateBrowser()
const fixedShellBackplateLayers = computed<readonly GlassFixedShellBackplateLayer[]>(() => {
  const hasWallpaper = renderedBackgroundLayers.value.some(layer => Boolean(layer.url))
  if (
    !shouldUseGlassFixedShellBackplate({
      appearance: glass.effectiveGlassSettings.value.glassAppearance,
      hasWallpaper,
      isAuthenticated: Boolean(isLogin.value),
      needsStableFixedBackdrop,
      quality: glass.effectiveGlassSettings.value.glassQuality,
      themeName: 'acg',
    })
  ) {
    return []
  }

  return renderedBackgroundLayers.value.map(layer => ({
    ...layer,
    crossOrigin: getBackgroundLayerCrossOrigin(layer),
    src: getBackgroundLayerImageSource(layer),
    style: getBackgroundLayerStyle(layer),
  }))
})

provideGlassFixedShellBackplate({
  layers: fixedShellBackplateLayers,
  transitionDurationMs: BACKGROUND_CROSSFADE_DURATION_MS,
})

// 启动 WebSocket 连接
onMounted(() => {
  if (systemStore.isLoggedIn) {
    systemStore.connect()
  }
})
</script>

<template>
  <div
    class="app-wrapper"
    :class="{
      'app-wrapper--background-transition': isBackgroundCrossfadingNow,
    }"
  >
    <!-- 壁纸背景层 -->
    <div
      v-if="shouldLoadBackgroundImages && shouldUseGlassBackgroundTreatment && renderedBackgroundLayers.length > 0"
      class="background-container is-glass-theme"
    >
      <div
        v-for="layer in renderedBackgroundLayers"
        :key="layer.key"
        class="background-image"
        :class="layer.role"
        :style="getBackgroundLayerStyle(layer)"
      >
        <img
          v-if="getBackgroundLayerImageSource(layer)"
          class="background-image__source"
          :crossorigin="getBackgroundLayerCrossOrigin(layer)"
          :src="getBackgroundLayerImageSource(layer)"
          alt=""
          aria-hidden="true"
          draggable="false"
        />
      </div>
    </div>
    <!-- 玻璃光学渲染层 -->
    <GlassOpticalLayer
      v-if="isACG && glass.shouldRenderGlassOpticalLayer.value"
      :appearance="glass.effectiveGlassSettings.value.glassAppearance"
      :deformation-strength="glass.opticalDeformationStrength.value"
      :dynamics-mode="glass.effectiveGlassSettings.value.glassDynamicsMode"
      :flow-strength="glass.opticalFlowStrength.value"
      :quality="glass.opticalQuality.value === 'high' ? 'high' : 'balanced'"
      :reflection-strength="glass.opticalReflectionStrength.value"
      :surface-mode="glass.opticalSurfaceMode.value"
      :transparency-strength="glass.opticalTransparencyStrength.value"
      :transmission-strength="glass.opticalTransmissionStrength.value"
      :translation-strength="glass.opticalTranslationStrength.value"
      :route-key="route.fullPath"
      :tint-color="glass.glassMaterialTintColor.value"
      :transition-duration="glass.transitionDuration"
      :transition-started-at="glass.transitionStartedAt.value"
      :wallpaper-url="glass.wallpaperUrl.value"
      :previous-wallpaper-url="glass.previousWallpaperUrl.value"
      :pending-wallpaper-url="glass.pendingWallpaperUrl.value"
      :pending-wallpaper-revision="glass.pendingWallpaperRevision.value"
      :activate-wallpaper-revision="glass.activateWallpaperRevision.value"
    />
    <!-- 页面内容 -->
    <router-view v-if="isStandalone" />
    <DefaultLayout v-else />
  </div>
</template>

<style lang="scss">
/* 全局样式 */
.app-wrapper {
  position: relative;
  inline-size: 100%;
  min-block-size: 100vh;
}

.background-container {
  position: fixed;
  z-index: 0;
  overflow: hidden;
  block-size: 100%;
  inline-size: 100%;
  inset-block-start: 0;
  inset-inline-start: 0;
}

.background-image {
  position: absolute;
  background-position: center;
  background-repeat: no-repeat;
  background-size: cover;
  block-size: 100%;
  inline-size: 100%;
  inset-block-start: 0;
  inset-inline-start: 0;
  opacity: 0;
  transition: opacity 1.5s ease;

  &::after {
    position: absolute;
    background: linear-gradient(rgba(0, 0, 0, 30%) 0%, rgba(0, 0, 0, 60%) 100%);
    block-size: 100%;
    content: '';
    inline-size: 100%;
    inset-block-start: 0;
    inset-inline-start: 0;
  }

  &.active {
    z-index: 2;
    opacity: 1;
  }

  &.previous {
    z-index: 1;
  }
}

.background-container.is-glass-theme .background-image.active,
.background-container.is-glass-theme .background-image.previous {
  filter: brightness(var(--glass-wallpaper-brightness, 0.86)) saturate(0.95) contrast(1.02);
}

.background-container.is-glass-theme .background-image.active {
  opacity: 0.94;
}

.background-container.is-glass-theme .background-image.active::after,
.background-container.is-glass-theme .background-image.previous::after {
  background:
    radial-gradient(circle at 50% 18%, transparent 24%, rgba(6, 10, 19, 12%) 100%),
    linear-gradient(rgba(6, 10, 19, 10%) 0%, rgba(6, 10, 19, 30%) 100%);
}

.background-image__source {
  position: absolute;
  display: block;
  block-size: 100%;
  inline-size: 100%;
  inset: 0;
  object-fit: cover;
  pointer-events: none;
}
</style>
