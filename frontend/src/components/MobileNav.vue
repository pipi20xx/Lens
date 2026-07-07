<script setup lang="ts">
import { ref, computed, h, Component } from 'vue'
import { NIcon, NButton, NDrawer } from 'naive-ui'
import {
  DashboardOutlined as DashboardIcon,
  CameraOutlined as SiteNavIcon,
  DnsOutlined as EmbyIcon,
  MenuOutlined as HamburgerIcon,
  ArrowBackOutlined as ArrowBackIcon,
  SettingsOutlined as SettingIcon,
  TerminalOutlined as ConsoleIcon,
  LightModeOutlined as LightIcon,
  DarkModeOutlined as DarkIcon,
  PersonOutlined as ProfileIcon,
  ExitToAppOutlined as LogoutIcon
} from '@vicons/material'
import { currentViewKey, menuLayout, activeGroupKey, isLogConsoleOpen, logout } from '../store/navigationStore'
import { allMenuItems } from '../config/menu'

const props = defineProps<{
  isDark: boolean
  appMode: boolean  // PWA App 模式 (显示返回按钮而非汉堡菜单)
}>()

const emit = defineEmits<{
  (e: 'toggleTheme'): void
  (e: 'goBack'): void
}>()

const showMobileMenu = ref(false)

// ── 底部 4 个主 Tab (最常用的入口) ──
const bottomNavItems = computed(() => [
  { key: 'DashboardView', label: '仪表盘', icon: DashboardIcon },
  { key: 'SiteNavView', label: '站点', icon: SiteNavIcon },
  { key: 'PlaybackReportView', label: 'Emby', icon: EmbyIcon },
  // 第 4 个固定是"更多"
])

// ── "更多"面板:按 menuLayout 分组呈现 ──
const panelGroups = computed(() => {
  return menuLayout.value.map(group => {
    if (group.type === 'item') {
      // 单项组:直接展示
      const item = allMenuItems.find(m => m.key === group.key)
      return {
        groupLabel: group.label,
        groupKey: group.key,
        items: item ? [item] : []
      }
    } else {
      // 多项组:展示所有子项
      const items = group.items
        .map(itemKey => allMenuItems.find(m => m.key === itemKey))
        .filter(Boolean) as any[]
      return {
        groupLabel: group.label,
        groupKey: group.key,
        items
      }
    }
  }).filter(g => g.items.length > 0)
})

// ── 当前激活态判断 ──
const isNavActive = (key: string) => {
  return currentViewKey.value === key
}

// ── 底部 Tab 点击 ──
const handleMobileNav = (key: string) => {
  if (key === 'MORE') {
    showMobileMenu.value = true
  } else {
    currentViewKey.value = key
    // 同步 activeGroupKey
    syncGroupKey(key)
  }
}

// ── "更多"面板项点击 ──
const handlePanelSelect = (key: string) => {
  currentViewKey.value = key
  syncGroupKey(key)
  showMobileMenu.value = false
}

// ── 同步 activeGroupKey (用于桌面端切换回来时保持一致) ──
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
const handlePanelAction = (action: 'theme' | 'console' | 'settings' | 'logout') => {
  showMobileMenu.value = false
  if (action === 'theme') {
    emit('toggleTheme')
  } else if (action === 'console') {
    isLogConsoleOpen.value = true
  } else if (action === 'settings') {
    currentViewKey.value = 'SettingsView'
    syncGroupKey('SettingsView')
  } else if (action === 'logout') {
    logout()
  }
}

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}
</script>

<template>
  <!-- 移动端顶部栏 -->
  <div class="mobile-header">
    <div class="mobile-header-left">
      <!-- PWA App 模式: 返回按钮 -->
      <n-button v-if="appMode" quaternary size="small" class="mobile-icon-btn" @click="emit('goBack')" title="返回">
        <template #icon><n-icon size="24"><ArrowBackIcon /></n-icon></template>
      </n-button>
      <!-- 移动浏览器模式: 汉堡菜单 -->
      <n-button v-else quaternary size="small" class="mobile-icon-btn" @click="showMobileMenu = true" title="菜单">
        <template #icon><n-icon size="24"><HamburgerIcon /></n-icon></template>
      </n-button>
      <span class="mobile-title">LENS</span>
    </div>
    <div class="mobile-header-right">
      <n-button quaternary size="small" class="mobile-icon-btn" @click="emit('toggleTheme')">
        <template #icon>
          <n-icon size="20">
            <DarkIcon v-if="isDark" />
            <LightIcon v-else />
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
            :class="{ active: isNavActive(item.key) }"
            @click="handleMobileNav(item.key)"
          >
            <n-icon size="26"><component :is="item.icon" /></n-icon>
            <span class="label">{{ item.label }}</span>
          </div>
          <!-- 更多按钮 -->
          <div class="nav-item" :class="{ active: showMobileMenu }" @click="handleMobileNav('MORE')">
            <n-icon size="26"><HamburgerIcon /></n-icon>
            <span class="label">更多</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- 全屏功能面板 -->
  <n-drawer v-model:show="showMobileMenu" placement="bottom" :height="'100dvh'" :style="{ '--n-drawer-body-padding': '0' }">
    <div class="full-panel">
      <!-- 顶部标题栏 -->
      <div class="full-panel-header">
        <div class="full-panel-title">
          <span>全部功能</span>
        </div>
        <n-button quaternary size="small" class="full-panel-close" @click="showMobileMenu = false">
          <template #icon><n-icon size="24"><ArrowBackIcon /></n-icon></template>
        </n-button>
      </div>

      <!-- 可滚动功能网格(按分组呈现) -->
      <div class="full-panel-body">
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
          <n-icon size="24" :color="isDark ? 'var(--primary-color)' : 'var(--text-color, #fff)'">
            <DarkIcon v-if="isDark" />
            <LightIcon v-else />
          </n-icon>
          <span>{{ isDark ? '夜间' : '日间' }}</span>
        </div>
        <div class="panel-footer-item" @click="handlePanelAction('console')">
          <n-icon size="24"><ConsoleIcon /></n-icon>
          <span>日志</span>
        </div>
        <div class="panel-footer-item" @click="handlePanelAction('settings')">
          <n-icon size="24"><SettingIcon /></n-icon>
          <span>设置</span>
        </div>
        <div class="panel-footer-item" @click="handlePanelAction('logout')">
          <n-icon size="24" color="var(--color-error, #EF4444)"><LogoutIcon /></n-icon>
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
}

.mobile-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mobile-icon-btn {
  --n-size: 36px !important;
}

.mobile-title {
  font-size: 1.1rem;
  font-weight: 900;
  letter-spacing: 1px;
  color: var(--primary-color, #705df2);
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
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: max(12px, env(safe-area-inset-top, 0px));
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.06));
  flex-shrink: 0;
  background: color-mix(in srgb, var(--sidebar-bg-color, #1a1a1f) 90%, transparent);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.full-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-color, #fff);
}

.full-panel-body {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  padding: 16px;
}

.full-panel-footer {
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
.full-panel-footer {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 8px 0 max(8px, env(safe-area-inset-bottom, 0px)) 0;
}

.panel-footer-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 8px;
  transition: all 0.25s ease;
  color: var(--text-color, #fff);
  opacity: 0.7;
  -webkit-tap-highlight-color: transparent;
}

.panel-footer-item:active {
  transform: scale(0.92);
  background: color-mix(in srgb, var(--primary-color, #705df2) 10%, transparent);
}

.panel-footer-item span {
  font-size: 10px;
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
