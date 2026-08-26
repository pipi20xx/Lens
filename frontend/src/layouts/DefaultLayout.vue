<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, defineAsyncComponent, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore, useSystemStore } from '@/stores'
import { useNotification } from '@/composables'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import LogTerminal from '@/components/common/LogTerminal.vue'

// ACG 玻璃主题样式 — 已改为静态引入（styles/index.css 第 4 层），
// 规则限定在 html.glass-theme-acg 前缀下，classic 主题下不生效，
// 无需动态加载/卸载（对齐 Anime-Manager 的做法）

// 异步加载 GlassSettingsDialog 组件（玻璃设置弹窗）
const GlassSettingsDialog = defineAsyncComponent(() =>
  import('@/glass/components/GlassSettingsDialog.vue')
)

// 异步加载 WallpaperDialog 组件（壁纸管理弹窗）
const WallpaperDialog = defineAsyncComponent(() =>
  import('@/glass/components/WallpaperDialog.vue')
)

// 异步加载 BorderDialog 组件（边框设置弹窗）
const BorderDialog = defineAsyncComponent(() =>
  import('@/glass/components/BorderDialog.vue')
)

// 异步加载 ShadowDialog 组件（阴影设置弹窗）
const ShadowDialog = defineAsyncComponent(() =>
  import('@/glass/components/ShadowDialog.vue')
)

// 异步加载主题色设置弹窗
const PrimaryColorDialog = defineAsyncComponent(() =>
  import('@/glass/components/PrimaryColorDialog.vue')
)

// 异步加载圆角设置弹窗
const BorderRadiusDialog = defineAsyncComponent(() =>
  import('@/glass/components/BorderRadiusDialog.vue')
)

// 异步加载 Fixed Shell Backplate 组件
const GlassFixedShellBackplate = defineAsyncComponent(() =>
  import('@/glass/components/GlassFixedShellBackplate.vue')
)

// ACG 玻璃壁纸管理
import {
  useGlassFixedShellBackplate,
  usePagePresentationMotion,
} from '@/glass'
import { applyStoredThemeCustomizerAppearance } from '@/glass/host/useThemeCustomizer'

const route = useRoute()
const router = useRouter()
const themeStore = useThemeStore()
const systemStore = useSystemStore()
const { state: notifyState } = useNotification()

const username = ref(localStorage.getItem('lens_username') || 'admin')
const appVersion = __APP_VERSION__ as string

const drawer = ref(true)
const rail = ref(false)
const isMobile = ref(false)
const showGlassSettings = ref(false)
const showWallpaperDialog = ref(false)
const showBorderDialog = ref(false)
const showShadowDialog = ref(false)
const showPrimaryColorDialog = ref(false)
const showBorderRadiusDialog = ref(false)

// 玻璃 Fixed Shell Backplate —— 从 App 层注入的壁纸槽位
const fixedShellBackplate = useGlassFixedShellBackplate()
const isACG = computed(() => themeStore.appTheme === 'acg')
const isOverlayNav = computed(() => isMobile.value)
const isOverlayNavActive = computed(() => isMobile.value && drawer.value)

// 页面呈现动画
const pagePresentationMotion = usePagePresentationMotion()
const layoutMainRef = ref<any>(null)

function getLayoutMainEl(): HTMLElement | null {
  const refValue = layoutMainRef.value
  if (!refValue) return null
  if ('$el' in refValue) return (refValue.$el as HTMLElement) ?? null
  if (refValue instanceof HTMLElement) return refValue
  return null
}

// 导航菜单
const navGroups = [
  {
    key: 'emby-query',
    label: 'Emby 查询工具',
    icon: 'mdi-magnify-scan',
    items: [
      { title: '项目元数据查询', icon: 'mdi-magnify', to: '/toolkit/emby-item-query' },
      { title: '剧集 TMDB 反查', icon: 'mdi-link-variant', to: '/toolkit/tmdb-reverse-lookup' },
      { title: 'TMDB ID 深度搜索', icon: 'mdi-identifier', to: '/toolkit/tmdb-id-search' },
      { title: 'Emby 任务计划', icon: 'mdi-clock-outline', to: '/emby/tasks' },
      { title: '播放统计报表', icon: 'mdi-chart-bar', to: '/emby/playback-report' },
    ],
  },
  {
    key: 'emby-tools',
    label: 'Emby 媒体工具',
    icon: 'mdi-tools',
    items: [
      { title: '类型映射管理', icon: 'mdi-tag-outline', to: '/toolkit/type-manager' },
      { title: '媒体净化清理', icon: 'mdi-broom', to: '/toolkit/cleanup' },
      { title: '元数据锁定器', icon: 'mdi-lock-outline', to: '/toolkit/lock-manager' },
      { title: '自动标签助手', icon: 'mdi-tag-plus-outline', to: '/toolkit/autotags' },
      { title: '演员信息维护', icon: 'mdi-account-star-outline', to: '/toolkit/actor-manager' },
    ],
  },
  {
    key: 'emby-core',
    label: 'Emby 高危运维',
    icon: 'mdi-alert-octagon-outline',
    items: [
      { title: '重复项清理', icon: 'mdi-content-duplicate', to: '/toolkit/dedupe' },
      { title: '用户管理', icon: 'mdi-account-group-outline', to: '/emby/users' },
      { title: '媒体库管理', icon: 'mdi-folder-multiple-outline', to: '/emby/libraries' },
    ],
  },
  {
    key: 'labs',
    label: '实验室',
    icon: 'mdi-flask-outline',
    items: [
      { title: 'TMDB 实验室', icon: 'mdi-movie-search-outline', to: '/toolkit/tmdb-lab' },
      { title: 'Bangumi 实验室', icon: 'mdi-animation-outline', to: '/toolkit/bangumi-lab' },
      { title: 'AI 实验室', icon: 'mdi-robot-outline', to: '/toolkit/ai-lab' },
      { title: '演员实验室', icon: 'mdi-account-tie-outline', to: '/toolkit/actor-lab' },
      { title: 'Webhook 接收器', icon: 'mdi-webhook', to: '/toolkit/webhook-receiver' },
    ],
  },
  {
    key: 'system',
    label: '系统与容器',
    icon: 'mdi-cog-outline',
    items: [
      { title: '终端', icon: 'mdi-console', to: '/toolkit/terminal' },
      { title: 'Docker 管理', icon: 'mdi-docker', to: '/toolkit/docker-manager' },
      { title: '镜像构建', icon: 'mdi-package-variant-closed', to: '/toolkit/image-builder' },
      { title: 'PostgreSQL', icon: 'mdi-database-outline', to: '/toolkit/postgres-manager' },
      { title: '备份管理', icon: 'mdi-backup-restore', to: '/toolkit/backup-manager' },
    ],
  },
  {
    key: 'config',
    label: '配置与控制',
    icon: 'mdi-tune-vertical',
    items: [
      { title: '通知管理', icon: 'mdi-bell-outline', to: '/toolkit/notification-manager' },
      { title: '账户管理', icon: 'mdi-account-cog-outline', to: '/toolkit/account-manager' },
      { title: '外部控制', icon: 'mdi-api', to: '/toolkit/external-control' },
      { title: '书签管理', icon: 'mdi-bookmark-outline', to: '/toolkit/bookmark-manager' },
    ],
  },
]

// 顶部独立导航项
const topNavItems = [
  { title: '管理仪表盘', icon: 'mdi-view-dashboard-outline', to: '/' },
  { title: '站点导航', icon: 'mdi-compass-outline', to: '/toolkit/site-nav' },
]

const currentTitle = computed(() => {
  const item = route.meta.title as string
  return item || 'Lens'
})

// 主题切换图标与颜色
const themeIcon = computed(() => {
  switch (themeStore.appTheme) {
    case 'light': return 'mdi-white-balance-sunny'
    case 'acg': return 'mdi-glass-mug-variant'
    default: return 'mdi-weather-night'
  }
})
const themeColor = computed(() => {
  switch (themeStore.appTheme) {
    case 'light': return 'warning'
    case 'acg': return 'primary'
    default: return 'info'
  }
})

// ========== ACG 玻璃主题（全局） ==========
const glassAcgEnabled = computed(() => themeStore.appTheme === 'acg')

// ACG 玻璃开启时初始化玻璃设置（样式已静态引入，无需动态加载）
watch(glassAcgEnabled, (enabled) => {
  if (enabled) {
    applyStoredThemeCustomizerAppearance()
  }
}, { immediate: true })

// 路由变化时，移动端自动关闭抽屉 + 触发页面呈现动画
watch(() => route.path, () => {
  if (isMobile.value) drawer.value = false
  if (isACG.value) {
    nextTick(() => {
      pagePresentationMotion.start(route.fullPath, getLayoutMainEl())
    })
  }
})

// 玻璃设置弹窗
function handleLogout() {
  localStorage.removeItem('lens_access_token')
  localStorage.removeItem('lens_username')
  router.push('/login')
}

// 移动端
function checkMobile() {
  isMobile.value = window.innerWidth < 960
  if (isMobile.value) drawer.value = false
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})
onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  pagePresentationMotion.cancel()
})
</script>

<template>
  <v-app>
    <!-- 噪点颗粒纹理层 -->
    <div class="glass-grain" />

    <!-- 玻璃 Fixed Shell Backplate —— 在固定导航栏后面渲染壁纸背板 -->
    <GlassFixedShellBackplate
      v-if="isACG && fixedShellBackplate.layers.value.length > 0"
      :is-overlay-nav-active="isOverlayNavActive"
      :is-overlay-nav="isOverlayNav"
      :layers="fixedShellBackplate.layers.value"
      :transition-duration-ms="fixedShellBackplate.transitionDurationMs"
    />

    <!-- 布局根容器 —— AM/MP 使用 layout-wrapper 包裹全部内容，玻璃渲染器依赖此 class 发现固定表面 -->
    <div
      class="layout-wrapper layout-nav-type-vertical layout-navbar-fixed layout-content-width-fluid"
      :class="{
        'layout-overlay-nav': isMobile,
        'layout-vertical-nav-collapsed': rail && !isMobile,
        'layout-fixed-shell-backplate-active': isACG && fixedShellBackplate.layers.value.length > 0,
      }"
    >
    <!-- 侧边导航 —— 添加 layout-vertical-nav class 供渲染器表面发现 -->
    <v-navigation-drawer
      v-model="drawer"
      :rail="rail && !isMobile"
      :permanent="!isMobile"
      :temporary="isMobile"
      width="280"
      rail-width="72"
      :class="['layout-vertical-nav', { 'overlay-nav': isMobile }]"
    >
      <!-- Logo 区域 -->
      <div class="logo-header" :class="{ 'logo-header--rail': rail && !isMobile }">
        <v-avatar class="liquid-avatar" rounded="xl" size="40">
          <v-icon icon="mdi-eye-outline" size="24" />
        </v-avatar>
        <div v-if="!rail || isMobile" class="logo-text">
          <div class="text-subtitle-1 font-weight-bold liquid-glass-subtitle">LENS</div>
          <div class="text-caption text-medium-emphasis">导航与管理工具</div>
          <div class="sidebar-version">v{{ appVersion }}</div>
        </div>
        <v-btn
          v-if="!isMobile"
          variant="text"
          :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          size="x-small"
          density="comfortable"
          @click.stop="rail = !rail"
        />
      </div>

      <v-divider />

      <!-- 顶部独立导航 -->
      <v-list density="compact" nav class="px-3 py-2">
        <v-list-item
          v-for="item in topNavItems"
          :key="item.to"
          :prepend-icon="item.icon"
          :title="item.title"
          :to="item.to"
          :value="item.to"
          rounded="xl"
          class="mb-1"
          :exact="item.to === '/'"
        />
      </v-list>

      <v-divider class="mx-3" />

      <!-- 分组导航 -->
      <v-list density="compact" nav class="px-3 py-2 flex-grow-0 overflow-y-auto">
        <template v-for="group in navGroups" :key="group.key">
          <v-list-group :value="group.key">
            <template #activator="{ props: groupProps }">
              <v-list-item
                v-bind="groupProps"
                :prepend-icon="group.icon"
                :title="rail ? '' : group.label"
                rounded="xl"
                class="mb-1"
              />
            </template>
            <v-list-item
              v-for="item in group.items"
              :key="item.to"
              :prepend-icon="item.icon"
              :title="item.title"
              :to="item.to"
              :value="item.to"
              rounded="xl"
              class="mb-1 ml-2"
            />
          </v-list-group>
        </template>
      </v-list>

      <!-- 底部区域 -->
      <template #append>
        <v-divider />
        <div class="pa-3">
          <v-list-item
            prepend-icon="mdi-cog-outline"
            title="系统设置"
            to="/settings"
            rounded="xl"
          />
        </div>
      </template>
    </v-navigation-drawer>

    <!-- 顶栏 —— 添加 layout-navbar navbar-blur class 供渲染器表面发现 -->
    <v-app-bar
      elevation="0"
      density="comfortable"
      class="layout-navbar navbar-blur"
    >
      <v-app-bar-nav-icon v-if="isMobile" @click="drawer = !drawer" />

      <v-app-bar-title class="font-weight-bold text-body-1">{{ currentTitle }}</v-app-bar-title>

      <template #append>
        <div class="d-flex align-center ga-2">
          <!-- WS 连接状态 -->
          <v-chip
            :color="systemStore.isConnected ? 'success' : 'error'"
            size="small"
            variant="tonal"
            label
          >
            <v-icon start size="14">{{ systemStore.isConnected ? 'mdi-access-point-check' : 'mdi-access-point-off' }}</v-icon>
            {{ systemStore.isConnected ? '已连接' : '断开' }}
          </v-chip>

          <!-- 主题选择菜单 -->
          <v-menu>
            <template #activator="{ props: themeProps }">
              <v-btn
                v-bind="themeProps"
                variant="text"
                density="comfortable"
                size="small"
                :icon="themeIcon"
                :color="themeColor"
              />
            </template>
            <v-list density="compact" min-width="200" nav>
              <v-list-item
                prepend-icon="mdi-white-balance-sunny"
                title="白天"
                subtitle="纯白明亮风格"
                :active="themeStore.appTheme === 'light'"
                @click="themeStore.setAppTheme('light')"
                rounded="xl"
              />
              <v-list-item
                prepend-icon="mdi-weather-night"
                title="夜晚"
                subtitle="纯黑暗色风格"
                :active="themeStore.appTheme === 'dark'"
                @click="themeStore.setAppTheme('dark')"
                rounded="xl"
              />
              <v-list-item
                prepend-icon="mdi-glass-mug-variant"
                title="ACG 毛玻璃"
                subtitle="二次元壁纸 + 暗色毛玻璃"
                :active="themeStore.appTheme === 'acg'"
                @click="themeStore.setAppTheme('acg')"
                rounded="xl"
              />
              <v-divider class="my-2 mx-2" />
              <v-list-item
                prepend-icon="mdi-palette"
                title="主题色"
                subtitle="选择应用主色调"
                @click="showPrimaryColorDialog = true"
              />
              <v-list-item
                prepend-icon="mdi-border-radius"
                title="圆角"
                subtitle="无 / 小 / 默认 / 大 / 更大"
                @click="showBorderRadiusDialog = true"
              />
              <v-list-item
                prepend-icon="mdi-border-all-variant"
                title="边框"
                subtitle="无 / 轻微 / 默认 / 明显 / 强边框"
                @click="showBorderDialog = true"
              />
              <v-list-item
                prepend-icon="mdi-box-shadow"
                title="阴影"
                subtitle="无 / 轻微 / 默认 / 明显 / 夸张"
                @click="showShadowDialog = true"
              />
              <v-list-item
                prepend-icon="mdi-wallpaper"
                title="壁纸管理"
                subtitle="API / 上传 / 自定义 URL"
                @click="showWallpaperDialog = true"
              />
              <v-list-item
                prepend-icon="mdi-tune-variant"
                title="玻璃材质设置"
                subtitle="材质 / 质量 / 动态效果 / 参数"
                :disabled="themeStore.appTheme !== 'acg'"
                @click="showGlassSettings = true"
              />
            </v-list>
          </v-menu>

          <!-- 任务日志 -->
          <v-btn
            variant="text"
            density="comfortable"
            size="small"
            color="primary"
            icon="mdi-card-text-outline"
            @click="systemStore.showLogModal = true"
          />

          <!-- 用户菜单 -->
          <v-menu>
            <template #activator="{ props: menuProps }">
              <v-chip size="small" variant="outlined" label v-bind="menuProps" class="cursor-pointer">
                <v-icon start size="14">mdi-account-circle</v-icon>
                {{ username }}
                <v-icon end size="14">mdi-chevron-down</v-icon>
              </v-chip>
            </template>
            <v-list density="compact" min-width="160">
              <v-list-item
                prepend-icon="mdi-cog-outline"
                title="设置"
                to="/settings"
                rounded="xl"
              />
              <v-divider />
              <v-list-item
                prepend-icon="mdi-logout"
                title="退出登录"
                @click="handleLogout"
                rounded="xl"
                color="error"
              />
            </v-list>
          </v-menu>
        </div>
      </template>
    </v-app-bar>

    <!-- 主内容 —— 添加 layout-content-wrapper / layout-page-content / page-content-container 供渲染器发现滚动表面 -->
    <v-main ref="layoutMainRef" class="layout-content-wrapper">
      <main class="layout-page-content">
        <section class="page-content-container">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </section>
      </main>
    </v-main>

    <!-- 系统日志终端 -->
    <LogTerminal />

    <!-- 确认对话框 -->
    <ConfirmDialog />

    <!-- 全局通知 SnackBar -->
    <v-snackbar
      v-model="notifyState.show"
      :color="notifyState.color"
      :timeout="notifyState.timeout"
      location="top right"
    >
      <div v-if="notifyState.title" class="font-weight-bold mb-1">{{ notifyState.title }}</div>
      {{ notifyState.message }}
      <template #actions>
        <v-btn variant="text" icon="mdi-close" size="small" @click="notifyState.show = false" />
      </template>
    </v-snackbar>

    <!-- 玻璃材质设置弹窗 -->
    <GlassSettingsDialog
      v-model="showGlassSettings"
      @close="showGlassSettings = false"
    />

    <!-- 壁纸管理弹窗 -->
    <WallpaperDialog
      v-model="showWallpaperDialog"
      @close="showWallpaperDialog = false"
    />

    <!-- 边框设置弹窗 -->
    <BorderDialog
      v-model="showBorderDialog"
      @close="showBorderDialog = false"
    />

    <!-- 阴影设置弹窗 -->
    <ShadowDialog
      v-model="showShadowDialog"
      @close="showShadowDialog = false"
    />

    <!-- 主题色设置弹窗 -->
    <PrimaryColorDialog
      v-model="showPrimaryColorDialog"
      @close="showPrimaryColorDialog = false"
    />

    <!-- 圆角设置弹窗 -->
    <BorderRadiusDialog
      v-model="showBorderRadiusDialog"
      @close="showBorderRadiusDialog = false"
    />
    </div><!-- /layout-wrapper -->
  </v-app>
</template>
