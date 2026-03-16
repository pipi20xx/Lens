<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NIcon, NInput, NEmpty } from 'naive-ui'
import {
  ArrowBackOutlined as BackIcon,
  SearchOutlined as SearchIcon,
  HistoryOutlined as HistoryIcon,
  TrendingUpOutlined as TrendingIcon,
  CloseOutlined as CloseIcon
} from '@vicons/material'

const router = useRouter()
const searchQuery = ref('')
const searchHistory = ref(['Docker', 'Emby', '清理', '备份'])
const hotSearches = ['站点导航', '终端', '通知', 'TMDB']

// 搜索结果
const searchResults = computed(() => {
  if (!searchQuery.value.trim()) return []

  const query = searchQuery.value.toLowerCase()
  const allTools = [
    { name: '站点导航', path: '/mobile/tools/sitenav', category: '导航' },
    { name: '书签管理', path: '/mobile/tools/bookmarks', category: '导航' },
    { name: '终端', path: '/mobile/tools/terminal', category: '系统' },
    { name: 'Docker', path: '/mobile/tools/docker', category: '系统' },
    { name: 'Emby 库管理', path: '/mobile/tools/emby', category: 'Emby' },
    { name: '清理工具', path: '/mobile/tools/cleanup', category: '维护' },
    { name: '去重工具', path: '/mobile/tools/dedupe', category: '维护' },
    { name: '备份管理', path: '/mobile/tools/backup', category: '维护' },
    { name: '通知管理', path: '/mobile/tools/notifications', category: '其他' },
    { name: 'TMDB 工具', path: '/mobile/tools/tmdb', category: '其他' },
  ]

  return allTools.filter(tool =>
    tool.name.toLowerCase().includes(query) ||
    tool.category.toLowerCase().includes(query)
  )
})

const goBack = () => {
  router.back()
}

const handleSearch = (keyword: string) => {
  searchQuery.value = keyword
  // 添加到历史记录
  if (keyword && !searchHistory.value.includes(keyword)) {
    searchHistory.value.unshift(keyword)
    if (searchHistory.value.length > 10) {
      searchHistory.value.pop()
    }
  }
}

const clearHistory = () => {
  searchHistory.value = []
}

const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="mobile-search">
    <!-- 搜索头部 -->
    <header class="search-header">
      <div class="back-btn" @click="goBack">
        <n-icon size="24"><BackIcon /></n-icon>
      </div>
      <div class="search-input-wrapper">
        <n-input
          v-model:value="searchQuery"
          placeholder="搜索工具..."
          class="search-input"
          clearable
          @keyup.enter="handleSearch(searchQuery)"
        >
          <template #prefix>
            <n-icon size="18"><SearchIcon /></n-icon>
          </template>
        </n-input>
      </div>
    </header>

    <!-- 搜索结果 -->
    <div v-if="searchQuery.trim()" class="search-results">
      <div v-if="searchResults.length > 0" class="results-list">
        <div
          v-for="result in searchResults"
          :key="result.path"
          class="result-item"
          @click="navigateTo(result.path)"
        >
          <div class="result-info">
            <div class="result-name">{{ result.name }}</div>
            <div class="result-category">{{ result.category }}</div>
          </div>
          <n-icon size="16" class="arrow-icon"><RightIcon /></n-icon>
        </div>
      </div>
      <n-empty v-else description="未找到相关工具" class="empty-result" />
    </div>

    <!-- 搜索建议 -->
    <div v-else class="search-suggestions">
      <!-- 搜索历史 -->
      <div v-if="searchHistory.length > 0" class="suggestion-section">
        <div class="section-header">
          <span class="section-title">搜索历史</span>
          <span class="clear-btn" @click="clearHistory">清空</span>
        </div>
        <div class="tags-list">
          <span
            v-for="item in searchHistory"
            :key="item"
            class="history-tag"
            @click="handleSearch(item)"
          >
            <n-icon size="14"><HistoryIcon /></n-icon>
            {{ item }}
          </span>
        </div>
      </div>

      <!-- 热门搜索 -->
      <div class="suggestion-section">
        <div class="section-header">
          <span class="section-title">热门搜索</span>
        </div>
        <div class="tags-list">
          <span
            v-for="(item, index) in hotSearches"
            :key="item"
            class="hot-tag"
            @click="handleSearch(item)"
          >
            <span class="hot-rank" :class="{ top: index < 3 }">{{ index + 1 }}</span>
            {{ item }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { ChevronRightOutlined as RightIcon } from '@vicons/material'
export { RightIcon }
</script>

<style scoped>
.mobile-search {
  min-height: 100vh;
  background: var(--app-bg-color);
  transition: background-color 0.3s ease;
}

/* 搜索头部 */
.search-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  padding-top: calc(12px + env(safe-area-inset-top));
  background: var(--card-bg-color);
  border-bottom: 1px solid var(--border-color);
}

.back-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.back-btn:active {
  background: var(--hover-bg);
}

.search-input-wrapper {
  flex: 1;
}

.search-input {
  --n-border: 1px solid var(--border-color) !important;
  --n-color: var(--card-bg-color) !important;
  --n-color-focus: var(--hover-bg) !important;
  --n-text-color: var(--text-color) !important;
  --n-placeholder-color: var(--text-secondary) !important;
  --n-height: 42px !important;
  --n-border-radius: 10px !important;
}

.search-input :deep(.n-input__prefix) {
  color: var(--text-secondary);
  margin-right: 8px;
}

/* 搜索结果 */
.search-results {
  padding: 16px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--card-bg-color);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--border-color);
}

.result-item:active {
  background: var(--hover-bg);
}

.result-name {
  font-size: 15px;
  color: var(--text-color);
  margin-bottom: 4px;
}

.result-category {
  font-size: 12px;
  color: var(--text-secondary);
}

.arrow-icon {
  color: var(--text-secondary);
}

.empty-result {
  margin-top: 60px;
}

/* 搜索建议 */
.search-suggestions {
  padding: 20px 16px;
}

.suggestion-section {
  margin-bottom: 28px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.clear-btn {
  font-size: 13px;
  color: var(--primary-color);
  cursor: pointer;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.history-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--card-bg-color);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-color);
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--border-color);
}

.history-tag:active {
  background: var(--hover-bg);
}

.hot-tag {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--card-bg-color);
  border-radius: 20px;
  font-size: 13px;
  color: var(--text-color);
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid var(--border-color);
}

.hot-tag:active {
  background: var(--hover-bg);
}

.hot-rank {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--hover-bg);
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
}

.hot-rank.top {
  background: var(--primary-color);
  color: white;
}
</style>
