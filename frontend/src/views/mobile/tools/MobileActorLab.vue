<template>
  <div class="mobile-actor-lab">
    <!-- 页面标题 -->
    <div class="lab-header">
      <h1 class="lab-title">TMDB 演员实验室</h1>
      <p class="lab-desc">基于 TMDB 数据的智能探测工具</p>
    </div>

    <!-- 输入面板 -->
    <n-card class="input-card" :bordered="false">
      <n-tabs v-model:value="activeTab" type="segment" animated>
        <n-tab-pane name="search" tab="姓名搜索">
          <n-form label-placement="top" class="mobile-form">
            <n-form-item label="演员姓名">
              <n-input
                v-model:value="searchQuery"
                placeholder="中文或英文姓名..."
                @keyup.enter="handleSearch"
                size="large"
              />
            </n-form-item>
            <n-button
              block
              type="primary"
              size="large"
              :loading="searchLoading"
              @click="handleSearch"
            >
              <template #icon><n-icon><SearchIcon /></n-icon></template>
              执行搜索
            </n-button>
          </n-form>

          <!-- 搜索结果 -->
          <div v-if="searchResults.length > 0" class="search-results">
            <n-divider>搜索结果 ({{ searchResults.length }})</n-divider>
            <div class="result-list">
              <div
                v-for="person in searchResults"
                :key="person.id"
                class="result-item"
                @click="fillId(person)"
              >
                <n-avatar
                  round
                  size="medium"
                  :src="person.profile_path ? `https://image.tmdb.org/t/p/w200${person.profile_path}` : ''"
                />
                <div class="result-info">
                  <div class="result-name">{{ person.name }}</div>
                  <div class="result-meta">
                    <n-tag size="tiny" type="info">ID: {{ person.id }}</n-tag>
                    <span class="department">{{ person.known_for_department }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="direct" tab="直接 ID 探测">
          <n-form label-placement="top" class="mobile-form">
            <n-form-item label="TMDB Person ID">
              <n-input
                v-model:value="personId"
                placeholder="例如: 60063"
                size="large"
              />
            </n-form-item>
            <n-form-item label="抓取语言">
              <n-select
                v-model:value="detailLanguage"
                :options="languageOptions"
                filterable
                tag
                size="large"
              />
            </n-form-item>
            <n-button
              block
              type="primary"
              size="large"
              :loading="analyzeLoading"
              @click="handleAnalyze"
            >
              <template #icon><n-icon><LabIcon /></n-icon></template>
              执行分析
            </n-button>
          </n-form>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 结果展示区 -->
    <div v-if="result" class="result-section">
      <n-card class="result-card" :bordered="false">
        <!-- 演员头部信息 -->
        <div class="actor-header">
          <n-avatar
            round
            :size="80"
            :src="result.profile_path ? `https://image.tmdb.org/t/p/h632${result.profile_path}` : ''"
            class="actor-avatar"
          />
          <div class="actor-info">
            <h3 class="actor-name">{{ result.origin_name }}</h3>
            <p class="actor-subname">{{ result.main_name }}</p>
            <n-space size="small" wrap>
              <n-tag size="small" type="primary">{{ result.chinese_name }}</n-tag>
              <n-tag v-if="result.imdb_id" size="small" type="info">IMDB: {{ result.imdb_id }}</n-tag>
            </n-space>
          </div>
          <n-button secondary circle type="primary" @click="showJson(result.raw)">
            <template #icon><n-icon><CodeIcon /></n-icon></template>
          </n-button>
        </div>

        <!-- 详细信息 -->
        <div class="info-section">
          <div class="info-row">
            <span class="info-label">出生地</span>
            <span class="info-value">{{ result.place_of_birth || '未知' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">生日</span>
            <span class="info-value">{{ result.birthday || '未知' }}</span>
          </div>
          <div v-if="result.deathday" class="info-row">
            <span class="info-label">逝世</span>
            <span class="info-value" style="color: #ef4444">{{ result.deathday }}</span>
          </div>
        </div>

        <!-- 别名池 -->
        <div v-if="result.name_pool?.length" class="tags-section">
          <div class="section-title">全量别名池 ({{ result.name_pool.length }})</div>
          <div class="tag-pool">
            <span v-for="name in result.name_pool" :key="name" class="data-tag">{{ name }}</span>
          </div>
        </div>

        <!-- 代表作品 -->
        <div v-if="result.top_works?.length" class="works-section">
          <div class="section-title">代表作品 ({{ result.top_works.length }})</div>
          <div class="works-list">
            <div v-for="work in result.top_works" :key="work.id" class="work-item">
              <div class="work-header">
                <n-tag
                  size="tiny"
                  :type="work.media_type === 'movie' ? 'success' : 'info'"
                  quaternary
                >
                  {{ work.media_type === 'movie' ? '电影' : '剧集' }}
                </n-tag>
                <span class="work-title">{{ work.title }}</span>
                <span class="work-year">{{ work.release_date || '未知' }}</span>
              </div>
              <div class="work-meta">
                <span class="work-original">{{ work.original_title }}</span>
                <span class="work-rating">⭐ {{ work.vote_average?.toFixed(1) }}</span>
              </div>
            </div>
          </div>
        </div>
      </n-card>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!analyzeLoading" class="empty-state">
      <n-empty description="等待探测指令..." />
    </div>

    <!-- JSON 弹窗 -->
    <n-modal
      v-model:show="jsonModal.show"
      preset="card"
      style="width: 90vw; max-width: 600px"
      title="演员原始元数据"
    >
      <div class="json-wrapper">
        <n-code :code="JSON.stringify(jsonModal.data, null, 2)" language="json" word-wrap />
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import {
  NSpace, NCard, NInput, NButton,
  NCode, NTag, NEmpty, NForm, NFormItem,
  NSelect, NDivider, NIcon, NModal, NAvatar, NTabs, NTabPane
} from 'naive-ui'
import {
  TerminalOutlined as CodeIcon,
  SearchOutlined as SearchIcon,
  ScienceOutlined as LabIcon
} from '@vicons/material'

// 导入提取的逻辑
import { useActorLab } from '../../toolkit/actorLab/hooks/useActorLab'

const {
  activeTab, searchQuery, searchLoading, searchResults, personId, detailLanguage,
  analyzeLoading, result, jsonModal,
  handleSearch, handleAnalyze, fillId, showJson
} = useActorLab()

const languageOptions = [
  { label: '全语言抓取', value: 'all' },
  { label: '简体中文', value: 'zh-CN' },
  { label: '繁体中文', value: 'zh-TW' },
  { label: '英文', value: 'en-US' },
  { label: '日语', value: 'ja-JP' }
]
</script>

<style scoped>
.mobile-actor-lab {
  padding: 16px;
  padding-bottom: 32px;
  background: var(--app-bg-color);
  min-height: 100%;
}

.lab-header {
  margin-bottom: 20px;
}

.lab-title {
  font-size: 24px;
  font-weight: 700;
  color: #bb86fc;
  margin: 0 0 8px 0;
}

.lab-desc {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.7;
  margin: 0;
}

.input-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.mobile-form {
  padding: 8px 0;
}

/* 搜索结果 */
.search-results {
  margin-top: 16px;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--card-bg-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.result-item:active {
  background: var(--border-color);
  transform: scale(0.98);
}

.result-info {
  flex: 1;
}

.result-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.result-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.department {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.5;
}

/* 结果展示 */
.result-section {
  animation: slide-up 0.3s ease-out;
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.result-card {
  background: var(--card-bg-color);
  border-radius: 16px;
}

/* 演员头部 */
.actor-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 16px;
}

.actor-avatar {
  border: 3px solid rgba(187, 134, 252, 0.3);
  box-shadow: 0 0 20px rgba(187, 134, 252, 0.2);
}

.actor-info {
  flex: 1;
}

.actor-name {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 4px 0;
}

.actor-subname {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0 0 8px 0;
}

/* 信息区域 */
.info-section {
  background: var(--app-bg-color);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.6;
}

.info-value {
  font-size: 14px;
  color: var(--text-color);
}

/* 标签区域 */
.tags-section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color);
  opacity: 0.7;
  margin-bottom: 10px;
}

.tag-pool {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.data-tag {
  background: var(--app-bg-color);
  border: 1px solid var(--border-color);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.8;
}

/* 作品区域 */
.works-section {
  margin-top: 16px;
}

.works-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.work-item {
  background: var(--app-bg-color);
  border-radius: 10px;
  padding: 12px;
}

.work-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.work-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  flex: 1;
}

.work-year {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.5;
}

.work-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.work-original {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.5;
}

.work-rating {
  font-size: 12px;
  color: #f0a020;
}

/* 空状态 */
.empty-state {
  padding: 60px 0;
}

/* JSON 弹窗 */
.json-wrapper {
  background: var(--app-bg-color);
  padding: 12px;
  border-radius: 8px;
  max-height: 50vh;
  overflow-y: auto;
}
</style>
