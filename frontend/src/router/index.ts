import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from '@/store/navigationStore'
import { mobileRoutes } from '../views/mobile/mobile-routes'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { public: true }
    },
    {
      path: '/',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue'),
    },
    {
      path: '/dedupe',
      name: 'Dedupe',
      component: () => import('../views/Dedupe.vue'),
    },
    {
      path: '/toolkit/type-manager',
      name: 'TypeManager',
      component: () => import('../views/toolkit/TypeManager.vue'),
    },
    {
      path: '/toolkit/cleanup',
      name: 'Cleanup',
      component: () => import('../views/toolkit/CleanupTools.vue'),
    },
    {
      path: '/toolkit/lock-manager',
      name: 'LockManager',
      component: () => import('../views/toolkit/LockManager.vue'),
    },
    {
      path: '/toolkit/docker-manager',
      name: 'DockerManager',
      component: () => import('../views/toolkit/DockerManager.vue'),
    },
    {
      path: '/toolkit/image-builder',
      name: 'ImageBuilderView',
      component: () => import('../views/toolkit/ImageBuilder.vue'),
    },
    {
      path: '/toolkit/tmdb-lab',
      name: 'TmdbLab',
      component: () => import('../views/toolkit/TmdbLab.vue'),
    },
    {
      path: '/toolkit/bangumi-lab',
      name: 'BangumiLab',
      component: () => import('../views/toolkit/BangumiLab.vue'),
    },
    {
      path: '/toolkit/ai-lab',
      name: 'AILabView',
      component: () => import('../views/toolkit/AILab.vue'),
    },
    {
      path: '/toolkit/actor-lab',
      name: 'ActorLab',
      component: () => import('../views/toolkit/ActorLab.vue'),
    },
    {
      path: '/toolkit/terminal',
      name: 'TerminalManager',
      component: () => import('../views/toolkit/terminal/TerminalManager.vue'),
      meta: { title: '终端管理', icon: 'TerminalOutlined' }
    },
    {
      path: '/toolkit/actor-manager',
      name: 'ActorManager',
      component: () => import('../views/toolkit/ActorManager.vue'),
    },
    {
      path: '/toolkit/emby-item-query',
      name: 'EmbyItemQuery',
      component: () => import('../views/toolkit/EmbyItemQuery.vue'),
    },
    {
      path: '/toolkit/tmdb-reverse-lookup',
      name: 'TmdbReverseLookup',
      component: () => import('../views/toolkit/TmdbReverseLookup.vue'),
    },
    {
      path: '/toolkit/tmdb-id-search',
      name: 'TmdbIdSearch',
      component: () => import('../views/toolkit/TmdbIdSearch.vue'),
    },
    {
      path: '/toolkit/webhook-receiver',
      name: 'WebhookReceiver',
      component: () => import('../views/toolkit/WebhookReceiver.vue'),
    },
    {
      path: '/toolkit/autotags',
      name: 'AutoTags',
      component: () => import('../views/toolkit/autotags/AutoTagsManager.vue'),
    },
    {
      path: '/toolkit/postgres-manager',
      name: 'PostgresManager',
      component: () => import('../views/toolkit/PostgresManager.vue'),
    },
    {
      path: '/toolkit/backup-manager',
      name: 'BackupManager',
      component: () => import('../views/toolkit/BackupManager.vue'),
    },
    {
      path: '/toolkit/notification-manager',
      name: 'NotificationManager',
      component: () => import('../views/toolkit/NotificationManager.vue'),
    },
    {
      path: '/toolkit/site-nav',
      name: 'SiteNav',
      component: () => import('../views/toolkit/sitenav/SiteManager.vue'),
    },
    {
      path: '/toolkit/bookmark-manager',
      name: 'BookmarkManagerView',
      component: () => import('../views/toolkit/BookmarkManager.vue'),
    },
    {
      path: '/toolkit/external-control',
      name: 'ExternalControl',
      component: () => import('../views/toolkit/ExternalControl.vue'),
    },
    {
      path: '/emby-users',
      name: 'EmbyUsers',
      component: () => import('../views/EmbyUsers.vue'),
    },
    {
      path: '/emby-libraries',
      name: 'EmbyLibraries',
      component: () => import('../views/EmbyLibraries.vue'),
    },
    {
      path: '/toolkit/emby-scheduled-tasks',
      name: 'EmbyScheduledTasks',
      component: () => import('../views/toolkit/emby-tasks/EmbyScheduledTasks.vue'),
    },
    {
      path: '/toolkit/playback-report',
      name: 'PlaybackReport',
      component: () => import('../views/toolkit/playback-report/PlaybackReport.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('../views/Settings.vue'),
    },
    // 移动端路由
    ...mobileRoutes
  ]
})

// 设备检测 - 判断是否为移动端
const isMobileDevice = (to: any) => {
  // 如果 URL 中有 forceMobile 参数，强制使用移动端
  if (to.query.forceMobile === '1' || to.query.forceMobile === 'true') {
    return true
  }
  // 优先检查 User Agent（更可靠）
  if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
    return true
  }
  // 然后检查屏幕宽度
  return window.innerWidth <= 768
}

// 导航守卫
router.beforeEach((to, from, next) => {
  // 鉴权逻辑 - 强制要求登录
  if (!isLoggedIn.value && !to.meta.public) {
    next({ name: 'Login' })
    return
  }

  if (to.name === 'Login' && isLoggedIn.value) {
    // 如果已经在登录页，但已登录，则跳回首页
    next({ name: 'Dashboard' })
    return
  }

  // 移动端自动跳转
  if (isMobileDevice(to) && !to.path.startsWith('/mobile') && to.path !== '/login') {
    // 映射桌面路由到移动端路由
    const mobilePathMap: Record<string, string> = {
      '/': '/mobile/home',
      '/settings': '/mobile/settings',
      '/dedupe': '/mobile/tools/dedupe',
      '/toolkit/site-nav': '/mobile/tools/sitenav',
      '/toolkit/bookmark-manager': '/mobile/tools/bookmarks',
      '/toolkit/docker-manager': '/mobile/tools/docker',
      '/toolkit/terminal': '/mobile/tools/terminal',
      '/toolkit/cleanup': '/mobile/tools/cleanup',
      '/toolkit/notification-manager': '/mobile/tools/notifications',
      '/toolkit/emby-item-query': '/mobile/tools/item-query',
      '/toolkit/tmdb-reverse-lookup': '/mobile/tools/tmdb-lookup',
      '/toolkit/tmdb-id-search': '/mobile/tools/tmdb-search',
      '/toolkit/type-manager': '/mobile/tools/type-manager',
      '/toolkit/lock-manager': '/mobile/tools/lock',
      '/toolkit/autotags': '/mobile/tools/autotags',
      '/toolkit/actor-manager': '/mobile/tools/actor-manager',
      '/toolkit/image-builder': '/mobile/tools/image-builder',
      '/toolkit/postgres-manager': '/mobile/tools/postgres',
      '/toolkit/backup-manager': '/mobile/tools/backup',
      '/toolkit/webhook-receiver': '/mobile/tools/webhook',
      '/toolkit/account-manager': '/mobile/tools/account',
      '/toolkit/external-control': '/mobile/tools/external-control',
      '/toolkit/emby-scheduled-tasks': '/mobile/tools/tasks',
      '/toolkit/playback-report': '/mobile/tools/reports',
      '/emby-libraries': '/mobile/tools/emby',
      '/emby-users': '/mobile/tools/emby-users',
      '/toolkit/tmdb-lab': '/mobile/tools/tmdb-lab',
      '/toolkit/bangumi-lab': '/mobile/tools/bangumi-lab',
      '/toolkit/ai-lab': '/mobile/tools/ai-lab',
      '/toolkit/actor-lab': '/mobile/tools/actor-lab',
    }

    const mobilePath = mobilePathMap[to.path]
    if (mobilePath) {
      next(mobilePath)
      return
    }
  }

  // 桌面端访问移动端路由，跳回桌面端（除非有 forceMobile 参数）
  if (!isMobileDevice(to) && to.path.startsWith('/mobile')) {
    const desktopPathMap: Record<string, string> = {
      '/mobile/home': '/',
      '/mobile/tools': '/',
      '/mobile/profile': '/settings',
      '/mobile/settings': '/settings',
      '/mobile/tools/dedupe': '/dedupe',
      '/mobile/tools/sitenav': '/toolkit/site-nav',
      '/mobile/tools/bookmarks': '/toolkit/bookmark-manager',
      '/mobile/tools/docker': '/toolkit/docker-manager',
      '/mobile/tools/terminal': '/toolkit/terminal',
      '/mobile/tools/cleanup': '/toolkit/cleanup',
      '/mobile/tools/notifications': '/toolkit/notification-manager',
      '/mobile/tools/item-query': '/toolkit/emby-item-query',
      '/mobile/tools/tmdb-lookup': '/toolkit/tmdb-reverse-lookup',
      '/mobile/tools/tmdb-search': '/toolkit/tmdb-id-search',
      '/mobile/tools/type-manager': '/toolkit/type-manager',
      '/mobile/tools/lock': '/toolkit/lock-manager',
      '/mobile/tools/autotags': '/toolkit/autotags',
      '/mobile/tools/actor-manager': '/toolkit/actor-manager',
      '/mobile/tools/image-builder': '/toolkit/image-builder',
      '/mobile/tools/postgres': '/toolkit/postgres-manager',
      '/mobile/tools/backup': '/toolkit/backup-manager',
      '/mobile/tools/webhook': '/toolkit/webhook-receiver',
      '/mobile/tools/account': '/toolkit/account-manager',
      '/mobile/tools/external-control': '/toolkit/external-control',
      '/mobile/tools/tasks': '/toolkit/emby-scheduled-tasks',
      '/mobile/tools/reports': '/toolkit/playback-report',
      '/mobile/tools/emby': '/emby-libraries',
      '/mobile/tools/emby-users': '/emby-users',
      '/mobile/tools/tmdb-lab': '/toolkit/tmdb-lab',
      '/mobile/tools/bangumi-lab': '/toolkit/bangumi-lab',
      '/mobile/tools/ai-lab': '/toolkit/ai-lab',
      '/mobile/tools/actor-lab': '/toolkit/actor-lab',
    }

    const desktopPath = desktopPathMap[to.path] || '/'
    next(desktopPath)
    return
  }

  next()
})

export default router
