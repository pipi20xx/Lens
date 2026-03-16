<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  PersonOutlined as PersonIcon,
  SettingsOutlined as SettingsIcon,
  InfoOutlined as InfoIcon,
  ExitToAppOutlined as LogoutIcon,
  ChevronRightOutlined as RightIcon,
  DarkModeOutlined as DarkIcon,
  LanguageOutlined as LanguageIcon,
  NotificationsOutlined as NotifyIcon
} from '@vicons/material'

const router = useRouter()

// 设置菜单
const settingMenus = [
  { name: '页面设置', icon: SettingsIcon, path: '/mobile/settings' },
  { name: '通知设置', icon: NotifyIcon, path: '/mobile/tools/notifications' },
  { name: '深色模式', icon: DarkIcon, action: 'toggleDark' },
  { name: '语言', icon: LanguageIcon, action: 'language' },
]

// 关于菜单
const aboutMenus = [
  { name: '关于 Lens', icon: InfoIcon, path: '/mobile/about' },
  { name: '退出登录', icon: LogoutIcon, action: 'logout', danger: true },
]

const navigateTo = (path: string) => {
  if (path) router.push(path)
}

const handleAction = (action: string) => {
  switch (action) {
    case 'logout':
      // 处理退出登录
      router.push('/login')
      break
    case 'toggleDark':
      // 切换深色模式
      break
    case 'language':
      // 切换语言
      break
  }
}
</script>

<template>
  <div class="mobile-profile">
    <!-- 用户信息卡片 -->
    <div class="user-card">
      <div class="avatar">
        <n-icon size="40"><PersonIcon /></n-icon>
      </div>
      <div class="user-info">
        <div class="username">管理员</div>
        <div class="user-role">admin</div>
      </div>
    </div>

    <!-- 设置菜单 -->
    <div class="menu-section">
      <div class="menu-title">设置</div>
      <div class="menu-list">
        <div
          v-for="item in settingMenus"
          :key="item.name"
          class="menu-item"
          :class="{ danger: item.danger }"
          @click="item.path ? navigateTo(item.path) : handleAction(item.action)"
        >
          <div class="menu-icon">
            <n-icon size="20" :component="item.icon" />
          </div>
          <span class="menu-name">{{ item.name }}</span>
          <n-icon size="16" class="arrow-icon"><RightIcon /></n-icon>
        </div>
      </div>
    </div>

    <!-- 关于菜单 -->
    <div class="menu-section">
      <div class="menu-title">关于</div>
      <div class="menu-list">
        <div
          v-for="item in aboutMenus"
          :key="item.name"
          class="menu-item"
          :class="{ danger: item.danger }"
          @click="item.path ? navigateTo(item.path) : handleAction(item.action)"
        >
          <div class="menu-icon" :class="{ danger: item.danger }">
            <n-icon size="20" :component="item.icon" />
          </div>
          <span class="menu-name">{{ item.name }}</span>
          <n-icon size="16" class="arrow-icon"><RightIcon /></n-icon>
        </div>
      </div>
    </div>

    <!-- 版本信息 -->
    <div class="version-info">
      <span>Lens v2.5.6</span>
    </div>
  </div>
</template>

<style scoped>
.mobile-profile {
  width: 100%;
  min-height: 100vh;
  background: var(--app-bg-color);
  padding: 16px;
  padding-top: calc(16px + env(safe-area-inset-top));
  padding-bottom: calc(16px + 64px + env(safe-area-inset-bottom));
  box-sizing: border-box;
  transition: background-color 0.3s ease;
}

/* 用户卡片 */
.user-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px 20px;
  background: linear-gradient(135deg, rgba(112, 93, 242, 0.2), rgba(187, 134, 252, 0.1));
  border-radius: 20px;
  margin-bottom: 24px;
  border: 1px solid rgba(112, 93, 242, 0.2);
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(112, 93, 242, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #705df2;
}

.user-info {
  flex: 1;
}

.username {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 4px;
}

.user-role {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 菜单区块 */
.menu-section {
  margin-bottom: 24px;
}

.menu-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
  padding-left: 4px;
}

.menu-list {
  background: var(--card-bg-color);
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 1px solid var(--border-color);
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-item:active {
  background: var(--hover-bg);
}

.menu-item.danger .menu-name {
  color: #ef4444;
}

.menu-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--hover-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.menu-icon.danger {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.menu-name {
  flex: 1;
  font-size: 15px;
  color: var(--text-color);
}

.arrow-icon {
  color: var(--text-secondary);
}

/* 版本信息 */
.version-info {
  text-align: center;
  padding: 24px;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
