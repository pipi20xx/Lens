import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  // ── 仪表盘 ──
  {
    path: '/',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true, title: '管理仪表盘', icon: 'mdi-view-dashboard-outline' },
  },
  // ── Emby 核心运维 ──
  {
    path: '/emby/users',
    name: 'embyUsers',
    component: () => import('@/views/emby/EmbyUsersView.vue'),
    meta: { requiresAuth: true, title: 'Emby 用户管理', group: 'emby-core' },
  },
  {
    path: '/emby/libraries',
    name: 'embyLibraries',
    component: () => import('@/views/emby/EmbyLibrariesView.vue'),
    meta: { requiresAuth: true, title: 'Emby 媒体库管理', group: 'emby-core' },
  },
  {
    path: '/emby/tasks',
    name: 'embyTasks',
    component: () => import('@/views/emby/EmbyTasksView.vue'),
    meta: { requiresAuth: true, title: 'Emby 任务计划', group: 'emby-core' },
  },
  {
    path: '/emby/playback-report',
    name: 'playbackReport',
    component: () => import('@/views/emby/PlaybackReportView.vue'),
    meta: { requiresAuth: true, title: '播放统计报表', group: 'emby-core' },
  },
  // ── Emby 媒体工具 ──
  {
    path: '/toolkit/emby-item-query',
    name: 'embyItemQuery',
    component: () => import('@/views/toolkit/EmbyItemQueryView.vue'),
    meta: { requiresAuth: true, title: '项目元数据查询', group: 'emby-tools' },
  },
  {
    path: '/toolkit/tmdb-reverse-lookup',
    name: 'tmdbReverseLookup',
    component: () => import('@/views/toolkit/TmdbReverseLookupView.vue'),
    meta: { requiresAuth: true, title: '剧集 TMDB 反查', group: 'emby-tools' },
  },
  {
    path: '/toolkit/tmdb-id-search',
    name: 'tmdbIdSearch',
    component: () => import('@/views/toolkit/TmdbIdSearchView.vue'),
    meta: { requiresAuth: true, title: 'TMDB ID 深度搜索', group: 'emby-tools' },
  },
  {
    path: '/toolkit/dedupe',
    name: 'dedupe',
    component: () => import('@/views/toolkit/DedupeView.vue'),
    meta: { requiresAuth: true, title: '重复项清理', group: 'emby-tools' },
  },
  {
    path: '/toolkit/type-manager',
    name: 'typeManager',
    component: () => import('@/views/toolkit/TypeManagerView.vue'),
    meta: { requiresAuth: true, title: '类型映射管理', group: 'emby-tools' },
  },
  {
    path: '/toolkit/cleanup',
    name: 'cleanup',
    component: () => import('@/views/toolkit/CleanupView.vue'),
    meta: { requiresAuth: true, title: '媒体净化清理', group: 'emby-tools' },
  },
  {
    path: '/toolkit/lock-manager',
    name: 'lockManager',
    component: () => import('@/views/toolkit/LockManagerView.vue'),
    meta: { requiresAuth: true, title: '元数据锁定器', group: 'emby-tools' },
  },
  {
    path: '/toolkit/autotags',
    name: 'autotags',
    component: () => import('@/views/toolkit/autotags/AutoTagsView.vue'),
    meta: { requiresAuth: true, title: '自动标签助手', group: 'emby-tools' },
  },
  {
    path: '/toolkit/actor-manager',
    name: 'actorManager',
    component: () => import('@/views/toolkit/actor/ActorManagerView.vue'),
    meta: { requiresAuth: true, title: '演员信息维护', group: 'emby-tools' },
  },
  // ── 实验室 ──
  {
    path: '/toolkit/tmdb-lab',
    name: 'tmdbLab',
    component: () => import('@/views/toolkit/tmdb/TmdbLabView.vue'),
    meta: { requiresAuth: true, title: 'TMDB 实验室', group: 'labs' },
  },
  {
    path: '/toolkit/bangumi-lab',
    name: 'bangumiLab',
    component: () => import('@/views/toolkit/bangumi/BangumiLabView.vue'),
    meta: { requiresAuth: true, title: 'Bangumi 实验室', group: 'labs' },
  },
  {
    path: '/toolkit/ai-lab',
    name: 'aiLab',
    component: () => import('@/views/toolkit/ai/AILabView.vue'),
    meta: { requiresAuth: true, title: 'AI 实验室', group: 'labs' },
  },
  {
    path: '/toolkit/actor-lab',
    name: 'actorLab',
    component: () => import('@/views/toolkit/actorLab/ActorLabView.vue'),
    meta: { requiresAuth: true, title: '演员实验室', group: 'labs' },
  },
  // ── 系统与容器 ──
  {
    path: '/toolkit/terminal',
    name: 'terminal',
    component: () => import('@/views/toolkit/terminal/TerminalView.vue'),
    meta: { requiresAuth: true, title: '终端', group: 'system' },
  },
  {
    path: '/toolkit/docker-manager',
    name: 'dockerManager',
    component: () => import('@/views/toolkit/docker/DockerManagerView.vue'),
    meta: { requiresAuth: true, title: 'Docker 管理', group: 'system' },
  },
  {
    path: '/toolkit/image-builder',
    name: 'imageBuilder',
    component: () => import('@/views/toolkit/image_builder/ImageBuilderView.vue'),
    meta: { requiresAuth: true, title: '镜像构建与推送', group: 'system' },
  },
  {
    path: '/toolkit/postgres-manager',
    name: 'postgresManager',
    component: () => import('@/views/toolkit/pgsql/PgsqlManagerView.vue'),
    meta: { requiresAuth: true, title: 'PostgreSQL 管理', group: 'system' },
  },
  {
    path: '/toolkit/backup-manager',
    name: 'backupManager',
    component: () => import('@/views/toolkit/backup/BackupManagerView.vue'),
    meta: { requiresAuth: true, title: '数据备份管理', group: 'system' },
  },
  // ── 配置与控制 ──
  {
    path: '/toolkit/webhook-receiver',
    name: 'webhookReceiver',
    component: () => import('@/views/toolkit/webhook/WebhookReceiverView.vue'),
    meta: { requiresAuth: true, title: 'Webhook 接收器', group: 'config' },
  },
  {
    path: '/toolkit/notification-manager',
    name: 'notificationManager',
    component: () => import('@/views/toolkit/notification/NotificationManagerView.vue'),
    meta: { requiresAuth: true, title: '通知管理', group: 'config' },
  },
  {
    path: '/toolkit/account-manager',
    name: 'accountManager',
    component: () => import('@/views/toolkit/auth/AccountManagerView.vue'),
    meta: { requiresAuth: true, title: '账户管理', group: 'config' },
  },
  {
    path: '/toolkit/external-control',
    name: 'externalControl',
    component: () => import('@/views/toolkit/externalControl/ExternalControlView.vue'),
    meta: { requiresAuth: true, title: '外部控制', group: 'config' },
  },
  // ── 站点导航 ──
  {
    path: '/toolkit/site-nav',
    name: 'siteNav',
    component: () => import('@/views/toolkit/sitenav/SiteNavView.vue'),
    meta: { requiresAuth: true, title: '站点导航', icon: 'mdi-compass-outline' },
  },
  {
    path: '/toolkit/bookmark-manager',
    name: 'bookmarkManager',
    component: () => import('@/views/toolkit/bookmark/BookmarkManagerView.vue'),
    meta: { requiresAuth: true, title: '书签管理', group: 'config' },
  },
  // ── 设置 ──
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/settings/SettingsView.vue'),
    meta: { requiresAuth: true, title: '系统设置', icon: 'mdi-cog-outline' },
  },
  // ── 404 ──
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 导航守卫：未登录时跳转 login
router.beforeEach((to) => {
  const token = localStorage.getItem('lens_access_token')
  if (to.meta.requiresAuth !== false && !token) {
    return { name: 'login' }
  } else if (to.name === 'login' && token) {
    return { name: 'dashboard' }
  }
})

export default router
