<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NInput } from 'naive-ui'
import {
  SearchOutlined as SearchIcon,
  StorageOutlined as StorageIcon,
  TerminalOutlined as TerminalIcon,
  CleaningServicesOutlined as CleanIcon,
  SettingsOutlined as SettingsIcon,
  ScienceOutlined as LabIcon,
  DnsOutlined as SystemIcon,
  TuneOutlined as ConfigIcon,
  ChevronRightOutlined as RightIcon
} from '@vicons/material'

const router = useRouter()
const searchQuery = ref('')

// 工具分类 - 按照用户要求重新分类
const toolCategories = [
  {
    name: 'Emby 核心运维',
    icon: StorageIcon,
    color: '#3b82f6',
    tools: [
      { name: '播放统计报表', path: '/mobile/tools/reports' },
      { name: 'Emby 用户管理', path: '/mobile/tools/emby-users' },
      { name: 'Emby 媒体库管理', path: '/mobile/tools/emby' },
      { name: 'Emby 任务计划', path: '/mobile/tools/tasks' },
    ]
  },
  {
    name: 'EMBY 媒体工具',
    icon: CleanIcon,
    color: '#10b981',
    tools: [
      { name: '项目元数据查询', path: '/mobile/tools/item-query' },
      { name: '剧集 TMDB 反查', path: '/mobile/tools/tmdb-lookup' },
      { name: 'TMDB ID 深度搜索', path: '/mobile/tools/tmdb-search' },
      { name: '重复项清理', path: '/mobile/tools/dedupe' },
      { name: '类型映射管理', path: '/mobile/tools/type-manager' },
      { name: '媒体净化清理', path: '/mobile/tools/cleanup' },
      { name: '元数据锁定器', path: '/mobile/tools/lock' },
      { name: '自动标签助手', path: '/mobile/tools/autotags' },
      { name: '演员信息维护', path: '/mobile/tools/actor-manager' },
    ]
  },
  {
    name: '实验室',
    icon: LabIcon,
    color: '#8b5cf6',
    tools: [
      { name: 'TMDB 实验中心', path: '/mobile/tools/tmdb-lab' },
      { name: 'Bangumi 实验室', path: '/mobile/tools/bangumi-lab' },
      { name: 'AI 实验室', path: '/mobile/tools/ai-lab' },
      { name: 'TMDB 演员实验室', path: '/mobile/tools/actor-lab' },
    ]
  },
  {
    name: '系统与容器',
    icon: SystemIcon,
    color: '#ec4899',
    tools: [
      { name: '终端管理', path: '/mobile/tools/terminal' },
      { name: 'Docker 容器管理', path: '/mobile/tools/docker' },
      { name: '镜像构建与推送', path: '/mobile/tools/image-builder' },
      { name: 'PostgreSQL 管理', path: '/mobile/tools/postgres' },
      { name: '数据备份管理', path: '/mobile/tools/backup' },
    ]
  },
  {
    name: '配置与控制',
    icon: ConfigIcon,
    color: '#f59e0b',
    tools: [
      { name: 'Webhook 接收器', path: '/mobile/tools/webhook' },
      { name: '通知消息中心', path: '/mobile/tools/notifications' },
      { name: '账号安全管理', path: '/mobile/tools/account' },
      { name: '外部控制体系', path: '/mobile/tools/external-control' },
    ]
  },
]

// 过滤后的工具
const filteredCategories = computed(() => {
  if (!searchQuery.value.trim()) return toolCategories
  
  const query = searchQuery.value.toLowerCase()
  return toolCategories.map(cat => ({
    ...cat,
    tools: cat.tools.filter(tool => 
      tool.name.toLowerCase().includes(query)
    )
  })).filter(cat => cat.tools.length > 0)
})

const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="mobile-tools">
    <!-- 顶部标题栏 -->
    <header class="tools-header">
      <h1 class="page-title">工具箱</h1>
    </header>

    <!-- 搜索栏 -->
    <div class="search-section">
      <n-input
        v-model:value="searchQuery"
        placeholder="搜索工具..."
        class="search-input"
      >
        <template #prefix>
          <n-icon size="18"><SearchIcon /></n-icon>
        </template>
      </n-input>
    </div>

    <!-- 工具分类列表 -->
    <div class="tools-content">
      <div
        v-for="category in filteredCategories"
        :key="category.name"
        class="category-section"
      >
        <div class="category-header">
          <div class="category-icon" :style="{ backgroundColor: category.color + '20', color: category.color }">
            <n-icon size="20" :component="category.icon" />
          </div>
          <span class="category-name">{{ category.name }}</span>
        </div>
        
        <div class="tools-list">
          <div
            v-for="tool in category.tools"
            :key="tool.path"
            class="tool-item"
            @click="navigateTo(tool.path)"
          >
            <span class="tool-name">{{ tool.name }}</span>
            <n-icon size="16" class="arrow-icon"><RightIcon /></n-icon>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mobile-tools {
  width: 100vw;
  min-height: 100vh;
  background: #1e1e22;
  padding: 16px;
  padding-top: calc(16px + env(safe-area-inset-top));
  padding-bottom: calc(16px + 64px + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

/* 顶部标题栏 */
.tools-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.95);
  margin: 0;
}

/* 搜索栏 */
.search-section {
  margin-bottom: 24px;
}

.search-input {
  --n-border: 1px solid rgba(255, 255, 255, 0.1) !important;
  --n-border-hover: 1px solid rgba(255, 255, 255, 0.2) !important;
  --n-border-focus: 1px solid #705df2 !important;
  --n-color: rgba(255, 255, 255, 0.06) !important;
  --n-color-focus: rgba(255, 255, 255, 0.08) !important;
  --n-text-color: rgba(255, 255, 255, 0.9) !important;
  --n-placeholder-color: rgba(255, 255, 255, 0.4) !important;
  --n-height: 44px !important;
  --n-border-radius: 12px !important;
}

.search-input :deep(.n-input__prefix) {
  color: rgba(255, 255, 255, 0.4);
}

/* 工具分类 */
.category-section {
  margin-bottom: 20px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 16px;
  overflow: hidden;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.category-icon {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.category-name {
  font-size: 15px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.tools-list {
  padding: 4px;
}

.tool-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 10px;
  margin: 4px;
}

.tool-item:active {
  background: rgba(255, 255, 255, 0.06);
}

.tool-name {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}

.arrow-icon {
  color: rgba(255, 255, 255, 0.3);
}
</style>
