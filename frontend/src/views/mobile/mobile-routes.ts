import { RouteRecordRaw } from 'vue-router'

// 移动端路由配置
export const mobileRoutes: RouteRecordRaw[] = [
  {
    path: '/mobile',
    component: () => import('./layout/MobileLayout.vue'),
    redirect: '/mobile/home',
    children: [
      {
        path: 'home',
        name: 'MobileHome',
        component: () => import('./MobileHome.vue'),
        meta: { title: '首页' }
      },
      {
        path: 'tools',
        name: 'MobileTools',
        component: () => import('./MobileTools.vue'),
        meta: { title: '工具箱' }
      },
      {
        path: 'profile',
        name: 'MobileProfile',
        component: () => import('./MobileProfile.vue'),
        meta: { title: '我的' }
      },
      // 统一的工具视图 - 使用桌面组件
      {
        path: 'tools/:tool',
        name: 'MobileToolView',
        component: () => import('./MobileToolView.vue'),
        meta: { title: '工具' }
      },
      // 设置页面
      {
        path: 'settings',
        name: 'MobileSettings',
        component: () => import('./MobileSettings.vue'),
        meta: { title: '设置' }
      },
      {
        path: 'search',
        name: 'MobileSearch',
        component: () => import('./MobileSearch.vue'),
        meta: { title: '搜索' }
      },
      {
        path: 'about',
        name: 'MobileAbout',
        component: () => import('./MobileAbout.vue'),
        meta: { title: '关于' }
      }
    ]
  }
]

// 设备检测守卫
export const createMobileGuard = (router: any) => {
  router.beforeEach((to: any, from: any, next: any) => {
    const isMobile = window.innerWidth <= 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)

    // 如果是移动端访问桌面路由，重定向到移动端路由
    if (isMobile && !to.path.startsWith('/mobile') && to.path !== '/login') {
      const mobilePath = '/mobile' + to.path
      // 检查是否有对应的移动端路由
      const mobileRoute = router.resolve(mobilePath)
      if (mobileRoute.name !== 'NotFound') {
        return next(mobilePath)
      }
    }

    // 如果是桌面端访问移动端路由，重定向到桌面路由
    if (!isMobile && to.path.startsWith('/mobile')) {
      const desktopPath = to.path.replace('/mobile', '') || '/'
      return next(desktopPath)
    }

    next()
  })
}
