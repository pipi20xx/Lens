<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NGrid, NGridItem } from 'naive-ui'
import {
  HomeOutlined as HomeIcon,
  SettingsOutlined as SettingsIcon,
  SearchOutlined as SearchIcon,
  BookmarkOutlined as BookmarkIcon,
  TerminalOutlined as TerminalIcon,
  StorageOutlined as StorageIcon,
  CleaningServicesOutlined as CleanIcon,
  NotificationsOutlined as NotifyIcon
} from '@vicons/material'

const router = useRouter()

// 快捷功能入口 - 使用桌面导航的完整名称
const quickActions = [
  { name: '站点导航页', icon: HomeIcon, path: '/mobile/tools/sitenav', color: '#705df2' },
  { name: '管理仪表盘', icon: StorageIcon, path: '/mobile/home', color: '#3b82f6' },
  { name: '终端管理', icon: TerminalIcon, path: '/mobile/tools/terminal', color: '#f59e0b' },
  { name: 'Docker 容器管理', icon: StorageIcon, path: '/mobile/tools/docker', color: '#3b82f6' },
]

// 最近使用 - 使用桌面导航的完整名称
const recentTools = ref([
  { name: 'Emby 媒体库管理', path: '/mobile/tools/emby', icon: StorageIcon },
  { name: '媒体净化清理', path: '/mobile/tools/cleanup', icon: CleanIcon },
  { name: '通知消息中心', path: '/mobile/tools/notifications', icon: NotifyIcon },
])

// 搜索
const searchQuery = ref('')

const navigateTo = (path: string) => {
  router.push(path)
}

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    router.push(`/mobile/tools/search?q=${encodeURIComponent(searchQuery.value)}`)
  }
}
</script>

<template>
  <div class="mobile-home">
    <!-- 顶部标题栏 -->
    <header class="home-header">
      <h1 class="app-title">Lens</h1>
      <div class="header-actions">
        <div class="action-btn" @click="navigateTo('/mobile/search')">
          <n-icon size="22"><SearchIcon /></n-icon>
        </div>
        <div class="action-btn" @click="navigateTo('/mobile/settings')">
          <n-icon size="22"><SettingsIcon /></n-icon>
        </div>
      </div>
    </header>

    <!-- 搜索栏 -->
    <div class="search-section">
      <div class="search-bar" @click="navigateTo('/mobile/search')">
        <n-icon size="18" class="search-icon"><SearchIcon /></n-icon>
        <span class="search-placeholder">搜索工具...</span>
      </div>
    </div>

    <!-- 快捷功能 -->
    <section class="quick-actions">
      <h2 class="section-title">快捷功能</h2>
      <div class="actions-grid">
        <div
          v-for="action in quickActions"
          :key="action.name"
          class="action-item"
          @click="navigateTo(action.path)"
        >
          <div class="action-icon" :style="{ backgroundColor: action.color + '20', color: action.color }">
            <n-icon size="24" :component="action.icon" />
          </div>
          <span class="action-name">{{ action.name }}</span>
        </div>
      </div>
    </section>

    <!-- 最近使用 -->
    <section class="recent-tools">
      <h2 class="section-title">最近使用</h2>
      <div class="tools-list">
        <div
          v-for="tool in recentTools"
          :key="tool.name"
          class="tool-item"
          @click="navigateTo(tool.path)"
        >
          <div class="tool-icon">
            <n-icon size="20" :component="tool.icon" />
          </div>
          <span class="tool-name">{{ tool.name }}</span>
          <n-icon size="16" class="arrow-icon"><RightIcon /></n-icon>
        </div>
      </div>
    </section>

    <!-- 系统状态卡片 -->
    <section class="status-cards">
      <h2 class="section-title">系统状态</h2>
      <div class="cards-row">
        <div class="status-card">
          <div class="card-label">Docker</div>
          <div class="card-value">12</div>
          <div class="card-sublabel">运行中</div>
        </div>
        <div class="status-card">
          <div class="card-label">存储</div>
          <div class="card-value">68%</div>
          <div class="card-sublabel">已使用</div>
        </div>
        <div class="status-card">
          <div class="card-label">任务</div>
          <div class="card-value">3</div>
          <div class="card-sublabel">进行中</div>
        </div>
      </div>
    </section>
  </div>
</template>

<script lang="ts">
import { ChevronRightOutlined as RightIcon } from '@vicons/material'
export { RightIcon }
</script>

<style scoped>
.mobile-home {
  width: 100vw;
  min-height: 100vh;
  background: #1e1e22;
  padding: 16px;
  padding-top: calc(16px + env(safe-area-inset-top));
  box-sizing: border-box;
}

/* 顶部标题栏 */
.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.app-title {
  font-size: 28px;
  font-weight: 800;
  background: linear-gradient(135deg, #705df2, #bb86fc);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:active {
  background: rgba(255, 255, 255, 0.1);
  transform: scale(0.95);
}

/* 搜索栏 */
.search-section {
  margin-bottom: 24px;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: all 0.2s ease;
}

.search-bar:active {
  background: rgba(255, 255, 255, 0.1);
}

.search-icon {
  color: rgba(255, 255, 255, 0.4);
}

.search-placeholder {
  color: rgba(255, 255, 255, 0.4);
  font-size: 15px;
}

/* 区块标题 */
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin: 0 0 16px 0;
}

/* 快捷功能 */
.quick-actions {
  margin-bottom: 28px;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 4px;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.action-item:active {
  background: rgba(255, 255, 255, 0.05);
}

.action-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.action-item:active .action-icon {
  transform: scale(0.95);
}

.action-name {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
  text-align: center;
  line-height: 1.2;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 最近使用 */
.recent-tools {
  margin-bottom: 28px;
}

.tools-list {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 16px;
  overflow: hidden;
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.tool-item:last-child {
  border-bottom: none;
}

.tool-item:active {
  background: rgba(255, 255, 255, 0.06);
}

.tool-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(112, 93, 242, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #705df2;
}

.tool-name {
  flex: 1;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.9);
}

.arrow-icon {
  color: rgba(255, 255, 255, 0.3);
}

/* 状态卡片 */
.status-cards {
  margin-bottom: 24px;
}

.cards-row {
  display: flex;
  gap: 12px;
}

.status-card {
  flex: 1;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 16px;
  padding: 16px;
  text-align: center;
}

.card-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 8px;
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: #705df2;
  margin-bottom: 4px;
}

.card-sublabel {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}
</style>
