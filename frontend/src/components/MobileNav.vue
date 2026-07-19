<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { NIcon, NButton, NDrawer, NDropdown, NInput } from 'naive-ui'
import {
  ArrowLeftIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  CameraIcon,
  ChevronDownIcon,
  CodeBracketIcon,
  Cog6ToothIcon,
  MagnifyingGlassIcon,
  MoonIcon,
  ServerStackIcon,
  Squares2X2Icon,
  SunIcon,
  UserIcon
} from '@heroicons/vue/24/outline'
import { currentViewKey, menuLayout, activeGroupKey, isLogConsoleOpen, logout } from '../store/navigationStore'
import { allMenuItems } from '../config/menu'
import { servers, activeServerId, fetchServers, activateServer } from '../store/serverStore'

const props = defineProps<{
  isDark: boolean
  appMode: boolean  // PWA App 模式 (显示返回按钮而非汉堡菜单)
}>()

const emit = defineEmits<{
  (e: 'toggleTheme'): void
  (e: 'goBack'): void
  (e: 'openMenuManager'): void
}>()

const showMobileMenu = ref(false)
const searchKeyword = ref('')

// ── 底部 4 个主 Tab ──
// 每个 Tab 关联一个分组 key,激活态基于分组判断
const bottomNavItems = computed(() => [
  { key: 'DashboardView', label: '仪表盘', icon: Squares2X2Icon, groupKey: 'DashboardView' },
  { key: 'SiteNavView', label: '站点', icon: CameraIcon, groupKey: 'SiteNavView' },
  { key: 'PlaybackReportView', label: 'Emby', icon: ServerStackIcon, groupKey: 'group-emby-mgmt' },
  // 第 4 个固定是"更多"
])

// ── "更多"面板:按 menuLayout 分组呈现,支持搜索过滤 ──
const panelGroups = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  return menuLayout.value.map(group => {
    if (group.type === 'item') {
      const item = allMenuItems.find(m => m.key === group.key)
      // 搜索过滤
      if (kw && item) {
        const label = (item.label || '').toLowerCase()
        if (!label.includes(kw) && !group.key.toLowerCase().includes(kw)) {
          return { groupLabel: group.label, groupKey: group.key, items: [] }
        }
      }
      return {
        groupLabel: group.label,
        groupKey: group.key,
        items: item ? [item] : []
      }
    } else {
      let items = group.items
        .map(itemKey => allMenuItems.find(m => m.key === itemKey))
        .filter(Boolean) as any[]
      // 搜索过滤
      if (kw) {
        items = items.filter(item => {
          const label = (item.label || '').toLowerCase()
          return label.includes(kw) || (item.key || '').toLowerCase().includes(kw)
        })
      }
      return {
        groupLabel: group.label,
        groupKey: group.key,
        items
      }
    }
  }).filter(g => g.items.length > 0)
})

// ── 当前激活态判断 (基于分组归属,而非 key 精确匹配) ──
const isNavActive = (tabKey: string, groupKey: string) => {
  if (currentViewKey.value === tabKey) return true
  // 检查当前视图是否属于该 Tab 关联的分组
  if (groupKey.startsWith('group-')) {
    const group = menuLayout.value.find(g => g.key === groupKey)
    if (group && group.type === 'group' && group.items.includes(currentViewKey.value)) {
      return true
    }
  }
  return false
}

// ── 触觉反馈 ──
const vibrate = (ms = 10) => {
  if (typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    try { navigator.vibrate(ms) } catch {}
  }
}

// ── 底部 Tab 点击 ──
const handleMobileNav = (key: string) => {
  vibrate()
  if (key === 'MORE') {
    showMobileMenu.value = true
  } else {
    currentViewKey.value = key
    syncGroupKey(key)
  }
}

// ── "更多"面板项点击 ──
const handlePanelSelect = (key: string) => {
  vibrate()
  currentViewKey.value = key
  syncGroupKey(key)
  showMobileMenu.value = false
}

// ── 同步 activeGroupKey ──
const syncGroupKey = (viewKey: string) => {
  for (const group of menuLayout.value) {
    if (group.type === 'group' && group.items.includes(viewKey)) {
      if (activeGroupKey.value !== group.key) {
        activeGroupKey.value = group.key
        localStorage.setItem('lens_active_group', group.key)
      }
      break
    }
    if (group.type === 'item' && group.key === viewKey) {
      if (activeGroupKey.value !== group.key) {
        activeGroupKey.value = group.key
        localStorage.setItem('lens_active_group', group.key)
      }
      break
    }
  }
}

// ── 面板底部快捷操作 ──
const handlePanelAction = (action: 'theme' | 'console' | 'settings' | 'account' | 'menuManager' | 'logout') => {
  vibrate()
  showMobileMenu.value = false
  if (action === 'theme') {
    emit('toggleTheme')
  } else if (action === 'console') {
    isLogConsoleOpen.value = true
  } else if (action === 'settings') {
    currentViewKey.value = 'SettingsView'
    syncGroupKey('SettingsView')
  } else if (action === 'account') {
    currentViewKey.value = 'AccountManagerView'
    syncGroupKey('AccountManagerView')
  } else if (action === 'menuManager') {
    emit('openMenuManager')
  } else if (action === 'logout') {
    logout()
  }
}

// ── 服务器选择 ──
const serverOptions = computed(() => {
  return servers.value.map(s => ({
    label: s.name,
    key: s.id
  }))
})

const activeServerName = computed(() => {
  const active = servers.value.find(s => s.id === activeServerId.value)
  return active ? active.name : '未选择'
})

const handleServerSelect = async (serverId: string) => {
  const success = await activateServer(serverId)
  if (success) {
    window.location.reload()
  }
}

onMounted(() => {
  fetchServers()
})

// ── Android 返回键关闭"更多"面板 ──
// 打开面板时 push 一个 history state,按返回键时 popstate 关闭面板
let panelPushedState = false

watch(showMobileMenu, (val) => {
  if (val) {
    // 打开:push state
    window.history.pushState({ mobileMenu: true }, '')
    panelPushedState = true
  } else if (panelPushedState) {
    // 通过关闭按钮/选择项关闭:消费 push 的 state
    panelPushedState = false
    window.history.back()
  }
  // 关闭时清空搜索
  if (!val) {
    searchKeyword.value = ''
  }
})

const onPopState = (e: PopStateEvent) => {
  if (showMobileMenu.value) {
    // 返回键关闭面板
    panelPushedState = false  // 阻止 watch 再次 history.back()
    showMobileMenu.value = false
  }
}

onMounted(() => {
  window.addEventListener('popstate', onPopState)
})

onUnmounted(() => {
  window.removeEventListener('popstate', onPopState)
})
</script>

<template>
  <!-- 移动端顶部栏 -->
  <div class="mobile-header">
    <div class="mobile-header-left">
      <!-- PWA App 模式: 返回按钮 -->
      <n-button v-if="appMode" quaternary size="small" class="mobile-icon-btn" @click="emit('goBack')" title="返回">
        <template #icon><n-icon size="24"><ArrowLeftIcon /></n-icon></template>
      </n-button>
      <!-- 移动浏览器模式: 汉堡菜单 -->
      <n-button v-else quaternary size="small" class="mobile-icon-btn" @click="showMobileMenu = true" title="菜单">
        <template #icon><n-icon size="24"><Bars3Icon /></n-icon></template>
      </n-button>
      <span class="mobile-title">LENS</span>
    </div>

    <div class="mobile-header-center">
      <!-- 服务器选择器 -->
      <n-dropdown trigger="click" :options="serverOptions" @select="handleServerSelect">
        <n-button quaternary size="small" class="server-btn" :title="activeServerName">
          <n-icon size="16" class="server-icon"><ServerStackIcon /></n-icon>
          <span class="server-name">{{ activeServerName }}</span>
          <n-icon size="14" class="server-arrow"><ChevronDownIcon /></n-icon>
        </n-button>
      </n-dropdown>
    </div>

    <div class="mobile-header-right">
      <n-button quaternary size="small" class="mobile-icon-btn" @click="emit('toggleTheme')">
        <template #icon>
          <n-icon size="20">
            <MoonIcon v-if="isDark" />
            <SunIcon v-else />
          </n-icon>
        </template>
      </n-button>
    </div>
  </div>

  <!-- 浮动底部 Tab 导航 -->
  <Teleport to="body">
    <Transition name="nav-slide-up">
      <div class="mobile-nav-container">
        <div class="mobile-nav-card">
          <div
            v-for="item in bottomNavItems"
            :key="item.key"
            class="nav-item"
            :class="{ active: isNavActive(item.key, item.groupKey) }"
            @click="handleMobileNav(item.key)"
          >
            <n-icon size="26"><component :is="item.icon" /></n-icon>
            <span class="label">{{ item.label }}</span>
          </div>
          <!-- 更多按钮 -->
          <div class="nav-item" :class="{ active: showMobileMenu }" @click="handleMobileNav('MORE')">
            <n-icon size="26"><Bars3Icon /></n-icon>
            <span class="label">更多</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- 全屏功能面板 -->
  <n-drawer v-model:show="showMobileMenu" placement="bottom" :height="'100dvh'" :style="{ '--n-drawer-body-padding': '0' }">
    <div class="full-panel">
      <!-- 顶部标题栏 + 搜索框 -->
      <div class="full-panel-header">
        <div class="full-panel-title">
          <span>全部功能</span>
        </div>
        <n-input
          v-model:value="searchKeyword"
          placeholder="搜索功能..."
          clearable
          size="small"
          class="full-panel-search"
        >
          <template #prefix>
            <n-icon size="14"><MagnifyingGlassIcon /></n-icon>
          </template>
        </n-input>
        <n-button quaternary size="small" class="full-panel-close" @click="showMobileMenu = false">
          <template #icon><n-icon size="24"><ArrowLeftIcon /></n-icon></template>
        </n-button>
      </div>

      <!-- 可滚动功能网格 -->
      <div class="full-panel-body">
        <div v-if="panelGroups.length === 0" class="empty-state">
          <n-icon size="48" opacity="0.3"><MagnifyingGlassIcon /></n-icon>
          <p>未找到匹配的功能</p>
        </div>
        <div v-for="group in panelGroups" :key="group.groupKey" class="panel-group">
          <div class="panel-group-title">{{ group.groupLabel }}</div>
          <div class="app-grid-panel">
            <div
              v-for="item in group.items"
              :key="item.key"
              class="app-grid-item"
              :class="{ active: currentViewKey === item.key }"
              @click="handlePanelSelect(item.key)"
            >
              <div class="app-grid-icon">
                <component :is="item.icon" />
              </div>
              <div class="app-grid-label">{{ item.label }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部快捷操作栏 -->
      <div class="full-panel-footer">
        <div class="panel-footer-item" @click="handlePanelAction('theme')">
          <n-icon size="22" :color="isDark ? 'var(--primary-color, #705df2)' : 'var(--text-color, #fff)'">
            <MoonIcon v-if="isDark" />
            <SunIcon v-else />
          </n-icon>
          <span>{{ isDark ? '夜间' : '日间' }}</span>
        </div>
        <div class="panel-footer-item" @click="handlePanelAction('account')">
          <n-icon size="22"><UserIcon /></n-icon>
          <span>账号</span>
        </div>
        <div class="panel-footer-item" @click="handlePanelAction('menuManager')">
          <n-icon size="22"><Bars3Icon /></n-icon>
          <span>菜单</span>
        </div>
        <div class="panel-footer-item" @click="handlePanelAction('console')">
          <n-icon size="22"><CodeBracketIcon /></n-icon>
          <span>日志</span>
        </div>
        <div class="panel-footer-item" @click="handlePanelAction('settings')">
          <n-icon size="22"><Cog6ToothIcon /></n-icon>
          <span>设置</span>
        </div>
        <div class="panel-footer-item" @click="handlePanelAction('logout')">
          <n-icon size="22" color="var(--color-error, #EF4444)"><ArrowRightOnRectangleIcon /></n-icon>
          <span>退出</span>
        </div>
      </div>
    </div>
  </n-drawer>
</template>

<style scoped>
/* ============ 移动端顶部栏 ============ */
.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  padding-top: max(8px, env(safe-area-inset-top, 0px));
  background-color: var(--sidebar-bg-color, var(--app-bg-color, #101014));
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));
  position: sticky;
  top: 0;
  z-index: 100;
  gap: 8px;
}

.mobile-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  min-width: 0;
}

.mobile-header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  min-width: 0;
  overflow: hidden;
}

.mobile-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.mobile-icon-btn {
  --n-size: 36px !important;
}

.mobile-title {
  font-size: 1.1rem;
  font-weight: 900;
  letter-spacing: 1px;
  color: var(--primary-color, #705df2);
  white-space: nowrap;
}

.server-btn {
  max-width: 100%;
  height: 30px;
  padding: 0 10px !important;
  font-weight: 600;
  font-size: 0.8rem;
  border-radius: 999px !important;
  background-color: transparent !important;
  border: 1px solid var(--border-color) !important;
  transition: background-color 0.2s ease, border-color 0.2s ease !important;
}
.server-btn:hover {
  background-color: var(--hover-bg) !important;
  border-color: var(--primary-color) !important;
}
.server-btn :deep(.n-button__content) {
  display: flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
}
.server-btn .server-icon {
  color: var(--primary-color);
  flex-shrink: 0;
}
.server-btn .server-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 30vw;
}
.server-btn .server-arrow {
  color: var(--text-secondary);
  flex-shrink: 0;
  transition: transform 0.2s ease, color 0.2s ease;
}
.server-btn:hover .server-arrow {
  color: var(--primary-color);
  transform: translateY(1px);
}

/* ============ 浮动底部 Tab 导航 (胶囊式) ============ */
.mobile-nav-container {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 2000;
  padding: 0 12px max(8px, env(safe-area-inset-bottom, 0px)) 12px;
  pointer-events: none;
}

.mobile-nav-card {
  pointer-events: auto;
  display: flex;
  justify-content: space-around;
  align-items: center;
  height: 58px;
  background-color: color-mix(in srgb, var(--sidebar-bg-color, #1a1a1f) 85%, transparent);
  backdrop-filter: blur(24px) saturate(1.8);
  -webkit-backdrop-filter: blur(24px) saturate(1.8);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));
  border-radius: 28px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25), 0 1px 4px rgba(0, 0, 0, 0.15);
  overflow: hidden;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  height: 100%;
  color: var(--text-color, #fff);
  opacity: 0.6;
  transition: all 0.25s ease;
  cursor: pointer;
  position: relative;
  -webkit-tap-highlight-color: transparent;
}

/* 选中态的"胶囊高亮"效果 */
.nav-item::before {
  content: '';
  position: absolute;
  top: 6px;
  left: 50%;
  transform: translateX(-50%) scale(0);
  width: 44px;
  height: 32px;
  background: color-mix(in srgb, var(--primary-color, #705df2) 15%, transparent);
  border-radius: 16px;
  transition: transform 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55);
  z-index: -1;
}

.nav-item.active {
  opacity: 1;
  color: var(--primary-color, #705df2);
}

.nav-item.active::before {
  transform: translateX(-50%) scale(1);
}

.nav-item:active {
  transform: scale(0.92);
}

.nav-item .label {
  font-size: 10px;
  margin-top: 2px;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.nav-item.active .label {
  font-weight: 600;
  transform: scale(1.05);
}

/* ============ 全屏功能面板 ============ */
.full-panel {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  height: 100vh;
  background: var(--app-bg-color, #101014);
  overflow: hidden;
}

.full-panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top, 0px));
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));
  flex-shrink: 0;
  background: color-mix(in srgb, var(--sidebar-bg-color, #1a1a1f) 90%, transparent);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.full-panel-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-color, #fff);
  white-space: nowrap;
  flex-shrink: 0;
}

.full-panel-search {
  flex: 1;
  min-width: 0;
}

.full-panel-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  padding: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px 20px;
  color: var(--text-color, #fff);
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: 0.9rem;
}

.full-panel-footer {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 8px 0 max(8px, env(safe-area-inset-bottom, 0px)) 0;
  flex-shrink: 0;
  border-top: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));
  background: color-mix(in srgb, var(--sidebar-bg-color, #1a1a1f) 90%, transparent);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

/* ============ 面板分组 ============ */
.panel-group {
  margin-bottom: 24px;
}

.panel-group:last-child {
  margin-bottom: 0;
}

.panel-group-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-color, #fff);
  opacity: 0.7;
  margin-bottom: 12px;
  padding-left: 4px;
  letter-spacing: 0.5px;
}

/* ============ 功能网格 (4 列) ============ */
.app-grid-panel {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 0;
}

.app-grid-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 4px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  background: color-mix(in srgb, var(--sidebar-bg-color, #1a1a1f) 50%, transparent);
  border: 1px solid transparent;
  -webkit-tap-highlight-color: transparent;
}

.app-grid-item:active {
  transform: scale(0.94);
}

.app-grid-item.active {
  background: color-mix(in srgb, var(--primary-color, #705df2) 15%, transparent);
  border-color: var(--primary-color, #705df2);
}

.app-grid-item.active .app-grid-icon {
  color: var(--primary-color, #705df2);
}

.app-grid-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: var(--text-color, #fff);
  opacity: 0.8;
  transition: color 0.25s ease;
}

.app-grid-item:hover .app-grid-icon {
  color: var(--primary-color, #705df2);
  opacity: 1;
}

.app-grid-label {
  font-size: 11px;
  text-align: center;
  color: var(--text-color, #fff);
  opacity: 0.7;
  line-height: 1.3;
  word-break: break-all;
}

.app-grid-item.active .app-grid-label {
  color: var(--primary-color, #705df2);
  opacity: 1;
  font-weight: 600;
}

/* ============ 面板底部快捷操作 ============ */
.panel-footer-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 8px;
  transition: all 0.25s ease;
  color: var(--text-color, #fff);
  opacity: 0.7;
  -webkit-tap-highlight-color: transparent;
  flex: 1;
  min-width: 0;
}

.panel-footer-item:active {
  transform: scale(0.92);
  background: color-mix(in srgb, var(--primary-color, #705df2) 10%, transparent);
}

.panel-footer-item span {
  font-size: 10px;
  white-space: nowrap;
}

/* ============ 滑入动画 ============ */
.nav-slide-up-enter-active {
  transition: transform 0.35s cubic-bezier(0.68, -0.55, 0.265, 1.55), opacity 0.25s ease;
}

.nav-slide-up-leave-active {
  transition: transform 0.2s ease, opacity 0.15s ease;
}

.nav-slide-up-enter-from {
  transform: translateY(100%);
  opacity: 0;
}

.nav-slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
