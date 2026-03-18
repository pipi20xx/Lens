<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NTag, NButton, NAlert } from 'naive-ui'
import {
  SearchOutlined as SearchIcon,
  SettingsOutlined as SettingsIcon,
  ChevronRightOutlined as ArrowIcon,
  HomeOutlined as HomeIcon,
  StorageOutlined as StorageIcon,
  TerminalOutlined as TerminalIcon,
  ViewListOutlined as ListIcon,
  ContentCopyOutlined as DedupeIcon,
  DnsRound as DockerIcon,
  SystemUpdateAltOutlined as UpgradeIcon
} from '@vicons/material'
import axios from 'axios'
import { useMessage } from 'naive-ui'
import {
  PageTitle,
  QuickActions,
  Colors,
  StatusText,
  ButtonSizes,
  ButtonTypes,
} from './constants'

const router = useRouter()

// 使用常量
const pageTitle = PageTitle
const statusText = StatusText
const buttonSizes = ButtonSizes
const buttonTypes = ButtonTypes
const message = useMessage()

// 快捷功能 - 使用常量并添加图标
const quickActions = [
  { name: QuickActions[0].name, icon: HomeIcon, color: Colors.SITE_NAV, path: QuickActions[0].path },
  { name: QuickActions[1].name, icon: TerminalIcon, color: Colors.TERMINAL, path: QuickActions[1].path },
  { name: QuickActions[2].name, icon: StorageIcon, color: Colors.DOCKER, path: QuickActions[2].path },
  { name: QuickActions[3].name, icon: DedupeIcon, color: Colors.ERROR, path: QuickActions[3].path },
]

// 最近使用的工具
const recentTools = ref([
  { name: 'Emby 媒体库', path: '/mobile/tools/emby-libraries' },
  { name: '媒体清理', path: '/mobile/tools/cleanup' },
  { name: '通知中心', path: '/mobile/tools/notifications' },
])

// 版本信息
const versionInfo = ref({
  current: 'v2.5.9',
  latest: 'v2.5.9',
  has_update: false,
  docker_hub: 'https://hub.docker.com/r/pipi20xx/lens'
})

const upgrading = ref(false)

const navigateTo = (path: string) => {
  router.push(path)
}

const goToSearch = () => {
  router.push('/mobile/search')
}

const goToSettings = () => {
  router.push('/mobile/settings')
}

const fetchVersion = async () => {
  try {
    const res = await axios.get('/api/system/version')
    if (res.data) {
      versionInfo.value = res.data
    }
  } catch (e) {
    console.error('Failed to fetch version:', e)
  }
}

const handleUpgrade = async () => {
  upgrading.value = true
  try {
    const res = await axios.post('/api/system/upgrade')
    message.success(res.data.message, { duration: 10000 })
    setTimeout(() => {
      window.location.reload()
    }, 20000)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '启动升级失败')
    upgrading.value = false
  }
}

onMounted(() => {
  fetchVersion()
  // 加载最近使用的工具
  const recent = localStorage.getItem('recent_tools')
  if (recent) {
    try {
      recentTools.value = JSON.parse(recent).slice(0, 3)
    } catch (e) {
      console.error('解析最近工具失败:', e)
    }
  }
})
</script>

<template>
  <div class="mobile-home">
    <!-- 顶部标题栏 -->
    <header class="home-header">
      <h1 class="app-title">Lens</h1>
      <div class="header-actions">
        <div class="action-btn" @click="goToSearch">
          <n-icon size="22" :component="SearchIcon" />
        </div>
        <div class="action-btn" @click="goToSettings">
          <n-icon size="22" :component="SettingsIcon" />
        </div>
      </div>
    </header>

    <!-- 搜索栏 -->
    <section class="search-section" @click="goToSearch">
      <div class="search-bar">
        <n-icon size="20" :component="SearchIcon" class="search-icon" />
        <span class="search-placeholder">搜索工具...</span>
      </div>
    </section>

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
          <div class="action-icon" :style="{ background: `${action.color}20`, color: action.color }">
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
          <span class="tool-name">{{ tool.name }}</span>
          <n-icon size="18" :component="ArrowIcon" class="arrow-icon" />
        </div>
      </div>
    </section>

    <!-- 系统状态 -->
    <section class="status-cards">
      <h2 class="section-title">系统状态监控</h2>
      <n-card class="status-card" :bordered="false">
        <div class="status-list">
          <div class="status-item">
            <span class="status-label">运行版本</span>
            <div class="status-value">
              <n-tag :size="buttonSizes.TINY" :type="buttonTypes.PRIMARY" quaternary>{{ versionInfo.current }}</n-tag>
              <n-tag v-if="!versionInfo.has_update" :size="buttonSizes.TINY" :type="buttonTypes.SUCCESS" quaternary>Latest</n-tag>
              <n-tag v-else :size="buttonSizes.TINY" :type="buttonTypes.ERROR" quaternary>Update</n-tag>
            </div>
          </div>
          <div class="status-item">
            <span class="status-label">远端构建</span>
            <div class="status-value">
              <span class="version-text">{{ versionInfo.latest }}</span>
              <n-button 
                v-if="versionInfo.docker_hub"
                text 
                tag="a" 
                :href="versionInfo.docker_hub" 
                target="_blank" 
                :type="buttonTypes.PRIMARY"
                :size="buttonSizes.TINY"
              >
                <n-icon size="16"><DockerIcon /></n-icon>
              </n-button>
            </div>
          </div>
          <div class="status-item">
            <span class="status-label">运行环境</span>
            <n-tag :size="buttonSizes.TINY" :type="buttonTypes.INFO" quaternary>Lens Core v2</n-tag>
          </div>
        </div>
        
        <n-alert v-if="versionInfo.has_update" :type="buttonTypes.WARNING" :size="buttonSizes.SMALL" :bordered="false" class="update-alert">
          检测到新版本 {{ versionInfo.latest }}，请及时更新。
        </n-alert>

        <template #footer>
          <n-space vertical style="width: 100%">
            <n-button 
              v-if="versionInfo.has_update" 
              block 
              :size="buttonSizes.MEDIUM"
              :type="buttonTypes.WARNING" 
              :loading="upgrading"
              @click="handleUpgrade"
            >
              {{ upgrading ? '正在执行更新任务...' : '立即执行系统升级' }}
            </n-button>
            <n-button block :size="buttonSizes.MEDIUM" :type="buttonTypes.PRIMARY" secondary @click="goToSettings">
              配置中心
            </n-button>
          </n-space>
        </template>
      </n-card>
    </section>
  </div>
</template>

<style scoped>
.mobile-home {
  width: 100vw;
  min-height: 100vh;
  background: var(--app-bg-color);
  padding: 16px;
  padding-top: calc(16px + env(safe-area-inset-top));
  box-sizing: border-box;
  transition: background-color 0.3s ease;
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
  background: linear-gradient(135deg, var(--primary-color, #705df2), #bb86fc);
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
  background: var(--hover-bg, rgba(255, 255, 255, 0.06));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-color);
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn:active {
  background: var(--border-color);
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
  background: var(--card-bg-color);
  border-radius: 12px;
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.2s ease;
}

.search-bar:active {
  background: var(--hover-bg);
}

.search-icon {
  color: var(--text-secondary);
}

.search-placeholder {
  color: var(--text-secondary);
  font-size: 15px;
}

/* 区块标题 */
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
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
  background: var(--hover-bg);
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
  color: var(--text-secondary);
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
  background: var(--card-bg-color);
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.tool-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-bottom: 1px solid var(--border-color);
}

.tool-item:last-child {
  border-bottom: none;
}

.tool-item:active {
  background: var(--hover-bg);
}

.tool-name {
  flex: 1;
  font-size: 15px;
  color: var(--text-color);
}

.arrow-icon {
  color: var(--text-secondary);
}

/* 状态卡片 */
.status-cards {
  margin-bottom: 24px;
}

.status-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  border: 1px solid var(--border-color);
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.status-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.status-value {
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-text {
  font-size: 13px;
  font-family: monospace;
  color: var(--text-color);
}

.update-alert {
  margin-top: 12px;
}
</style>
