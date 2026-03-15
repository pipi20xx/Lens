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
      '/toolkit/site-nav': '/mobile/tools/sitenav',
      '/toolkit/bookmark-manager': '/mobile/tools/bookmarks',
      '/toolkit/docker-manager': '/mobile/tools/docker',
      '/toolkit/terminal': '/mobile/tools/terminal',
      '/toolkit/cleanup': '/mobile/tools/cleanup',
      '/toolkit/notification-manager': '/mobile/tools/notifications',
      '/emby-libraries': '/mobile/tools/emby',
      '/tmdb-lab': '/mobile/tools/tmdb',
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
      '/mobile/tools/sitenav': '/toolkit/site-nav',
      '/mobile/tools/bookmarks': '/toolkit/bookmark-manager',
      '/mobile/tools/docker': '/toolkit/docker-manager',
      '/mobile/tools/terminal': '/toolkit/terminal',
      '/mobile/tools/cleanup': '/toolkit/cleanup',
      '/mobile/tools/notifications': '/toolkit/notification-manager',
      '/mobile/tools/emby': '/emby-libraries',
      '/mobile/tools/tmdb': '/tmdb-lab',
    }

    const desktopPath = desktopPathMap[to.path] || '/'
    next(desktopPath)
    return
  }

  next()
})

export default router
