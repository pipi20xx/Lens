<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore, useSystemStore } from '@/stores'
import { useNotification } from '@/composables'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import LogTerminal from '@/components/common/LogTerminal.vue'

// ACG 玻璃主题样式（全局）
import '@/glass/styles/glass-acg.scss'

// 异步加载 GlassOpticalLayer 组件（WebGL 渲染层，体积较大）
const GlassOpticalLayer = defineAsyncComponent(() =>
  import('@/glass/components/GlassOpticalLayer.vue')
)

// 异步加载 GlassSettingsDialog 组件（玻璃设置弹窗）
const GlassSettingsDialog = defineAsyncComponent(() =>
  import('@/glass/components/GlassSettingsDialog.vue')
)

// ACG 玻璃壁纸管理
import { useGlassWallpaper } from '@/glass'
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

// ACG 玻璃开启时初始化玻璃设置
watch(glassAcgEnabled, (enabled) => {
  if (enabled) {
    applyStoredThemeCustomizerAppearance()
  }
}, { immediate: true })

// 玻璃壁纸管理
const {
  wallpaperUrl,
  previousWallpaperUrl,
  transitionStartedAt,
  transitionDuration,
  shouldRenderGlassOpticalLayer,
  glassMaterialTintColor,
  opticalDeformationStrength,
  opticalFlowStrength,
  opticalQuality,
  opticalReflectionStrength,
  opticalTransparencyStrength,
  opticalTransmissionStrength,
  opticalTranslationStrength,
} = useGlassWallpaper()

// GlassOpticalLayer 的 props
const glassOpticalLayerProps = computed(() => {
  if (!shouldRenderGlassOpticalLayer.value) return null
  return {
    appearance: 'clear' as const,
    deformationStrength: opticalDeformationStrength.value,
    flowStrength: opticalFlowStrength.value,
    dynamicsMode: 'ripple' as const,
    quality: opticalQuality.value === 'css' ? 'balanced' as const : opticalQuality.value as 'balanced' | 'high',
    reflectionStrength: opticalReflectionStrength.value,
    transparencyStrength: opticalTransparencyStrength.value,
    transmissionStrength: opticalTransmissionStrength.value,
    translationStrength: opticalTranslationStrength.value,
    routeKey: 'global',
    tintColor: glassMaterialTintColor.value,
    transitionDuration: transitionDuration,
    transitionStartedAt: transitionStartedAt.value,
    wallpaperUrl: wallpaperUrl.value,
    previousWallpaperUrl: previousWallpaperUrl.value,
  }
})

// 玻璃设置弹窗
const showGlassSettings = ref(false)

function handleLogout() {
  localStorage.removeItem('lens_access_token')
  localStorage.removeItem('lens_username')
  router.push('/login')
}

// 移动端
const isMobile = ref(false)
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
})
</script>

<template>
  <v-app>
    <!-- 噪点颗粒纹理层 -->
    <div class="glass-grain" />

    <!-- 侧边导航 -->
    <v-navigation-drawer
      v-model="drawer"
      :rail="rail && !isMobile"
      :permanent="!isMobile"
      :temporary="isMobile"
      width="280"
      rail-width="72"
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

    <!-- 顶栏 -->
    <v-app-bar elevation="0" density="comfortable" color="transparent">
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

          <!-- 主题切换：白天 / 夜晚 / ACG -->
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
            <v-list density="compact" min-width="140" nav>
              <v-list-item
                prepend-icon="mdi-white-balance-sunny"
                title="白天"
                :active="themeStore.appTheme === 'light'"
                @click="themeStore.setAppTheme('light')"
                rounded="xl"
              />
              <v-list-item
                prepend-icon="mdi-weather-night"
                title="夜晚"
                :active="themeStore.appTheme === 'dark'"
                @click="themeStore.setAppTheme('dark')"
                rounded="xl"
              />
              <v-list-item
                prepend-icon="mdi-glass-mug-variant"
                title="ACG"
                :active="themeStore.appTheme === 'acg'"
                @click="themeStore.setAppTheme('acg')"
                rounded="xl"
              />
            </v-list>
          </v-menu>

          <!-- ACG 玻璃设置（仅 ACG 主题时显示） -->
          <v-btn
            v-if="glassAcgEnabled"
            variant="text"
            density="comfortable"
            size="small"
            color="primary"
            icon="mdi-tune-variant"
            @click="showGlassSettings = true"
          />

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

    <!-- 主内容 -->
    <v-main>
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </v-main>

    <!-- ACG 玻璃光学渲染层（WebGL，全局） -->
    <GlassOpticalLayer
      v-if="glassAcgEnabled && glassOpticalLayerProps"
      v-bind="glassOpticalLayerProps"
    />

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

    <!-- ACG 玻璃设置弹窗 -->
    <GlassSettingsDialog
      v-if="glassAcgEnabled"
      v-model="showGlassSettings"
    />
  </v-app>
</template>


