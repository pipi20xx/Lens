<template>
  <div class="mobile-tmdb-lab">
    <!-- 页面标题 -->
    <div class="lab-header">
      <h1 class="lab-title">TMDB 实验室</h1>
      <p class="lab-desc">直接从 TMDB 官方抓取元数据</p>
    </div>

    <!-- 输入面板 -->
    <n-card class="input-card" :bordered="false">
      <MobileTabs v-model="activeTab" :tabs="tabs">
        <template #search>
          <n-form label-placement="top" class="mobile-form">
            <n-form-item :label="formLabel.NAME">
              <n-input 
                v-model:value="searchForm.query" 
                :placeholder="placeholder.MOVIE_OR_SERIES_NAME" 
                @keyup.enter="handleSearch"
                size="large"
              />
            </n-form-item>
            <n-form-item :label="formLabel.TYPE">
              <n-select v-model:value="searchForm.media_type" :options="mediaTypeOptions" size="large" />
            </n-form-item>
            <n-form-item :label="formLabel.LANGUAGE">
              <n-select v-model:value="searchForm.language" :options="languageOptions" filterable tag size="large" />
            </n-form-item>
            <n-button 
              block 
              :type="buttonTypes.PRIMARY" 
              size="large"
              :loading="searchLoading" 
              @click="handleSearch"
            >
              {{ buttonText.EXECUTE_SEARCH }}
            </n-button>
          </n-form>

          <!-- 搜索结果 -->
          <div v-if="searchResults.length > 0" class="search-results">
            <n-divider>搜索结果 ({{ searchResults.length }})</n-divider>
            <div class="result-list">
              <div 
                v-for="item in searchResults" 
                :key="item.id" 
                class="result-item"
                @click="fillDetail(item)"
              >
                <div class="result-title">{{ item.title || item.name }}</div>
                <div class="result-meta">
                  <n-tag size="tiny" :type="tagTypes.INFO">ID: {{ item.id }}</n-tag>
                  <n-tag size="tiny" :type="tagTypes.SUCCESS">{{ item.release_date || item.first_air_date || '未知日期' }}</n-tag>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template #direct>
          <n-form label-placement="top" class="mobile-form">
            <n-form-item label="TMDB ID">
              <n-input v-model:value="detailForm.tmdb_id" :placeholder="placeholder.EXAMPLE_TMDB_ID" size="large" />
            </n-form-item>
            <n-form-item :label="formLabel.TYPE">
              <n-select v-model:value="detailForm.media_type" :options="mediaTypeOptions" size="large" />
            </n-form-item>
            <n-form-item :label="formLabel.LANGUAGE">
              <n-select v-model:value="detailForm.language" :options="languageOptions" filterable tag size="large" />
            </n-form-item>
            <n-form-item v-if="detailForm.media_type === 'tv'" label=" ">
              <n-checkbox v-model:checked="detailForm.recursive" size="large">
                递归抓取所有季与集
              </n-checkbox>
            </n-form-item>
            <n-button 
              block 
              :type="buttonTypes.PRIMARY" 
              size="large"
              :loading="detailLoading" 
              @click="handleFetchDetail"
            >
              {{ buttonText.EXECUTE_FETCH }}
            </n-button>
          </n-form>
        </template>
      </MobileTabs>
    </n-card>

    <!-- 结果展示区 -->
    <div v-if="detailResult" class="result-section">
      <n-card class="result-card" :bordered="false">
        <template #header>
          <div class="result-header">
            <h3 class="result-name">{{ detailResult.title || detailResult.name }}</h3>
            <n-space size="small">
              <n-tag size="small" :type="tagTypes.PRIMARY">{{ detailResult.media_type === 'movie' ? '电影' : '剧集' }}</n-tag>
              <n-tag size="small" :type="tagTypes.INFO">ID: {{ detailResult.id }}</n-tag>
            </n-space>
          </div>
        </template>

        <!-- 基本信息 -->
        <div class="info-section">
          <div class="info-row">
            <span class="info-label">原名</span>
            <span class="info-value">{{ detailResult.original_title || detailResult.original_name || 'N/A' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">上映日期</span>
            <span class="info-value">{{ detailResult.release_date || detailResult.first_air_date || '未知' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">评分</span>
            <span class="info-value">
              <span class="rating">{{ detailResult.vote_average?.toFixed(1) || 'N/A' }}</span>
              <span class="vote-count">({{ detailResult.vote_count || 0 }} 票)</span>
            </span>
          </div>
        </div>

        <!-- 简介 -->
        <div v-if="detailResult.overview" class="overview-section">
          <p class="overview-text">{{ detailResult.overview }}</p>
        </div>

        <!-- 标题池 -->
        <div v-if="titlePool.length > 0" class="tags-section">
          <div class="section-title">标题池 ({{ titlePool.length }})</div>
          <div class="tag-pool">
            <span v-for="title in titlePool" :key="title" class="data-tag">{{ title }}</span>
          </div>
        </div>

        <!-- 别名池 -->
        <div v-if="aliasPool.length > 0" class="tags-section">
          <div class="section-title">别名池 ({{ aliasPool.length }})</div>
          <div class="tag-pool">
            <span v-for="alias in aliasPool" :key="alias" class="data-tag tag-orange">{{ alias }}</span>
          </div>
        </div>

        <!-- 关键词 -->
        <div v-if="keywordsList.length > 0" class="tags-section">
          <div class="section-title">关键词 ({{ keywordsList.length }})</div>
          <div class="tag-pool">
            <span v-for="kw in keywordsList" :key="kw.id" class="data-tag">{{ kw.name }}</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="action-section">
          <n-button block secondary :type="buttonTypes.PRIMARY" @click="showJson(detailResult, 'main')">
            {{ buttonText.VIEW_FULL_JSON }}
          </n-button>
        </div>

        <!-- 季与集 - 递归详情 -->
        <div v-if="detailResult.full_seasons_data?.length" class="seasons-section">
          <n-divider>季与集 ({{ detailResult.full_seasons_data.length }} 季)</n-divider>
          <n-collapse>
            <n-collapse-item 
              v-for="season in detailResult.full_seasons_data" 
              :key="season.id"
            >
              <template #header>
                <div class="season-header">
                  <span class="season-title">{{ season.name }} ({{ season.episodes?.length || 0 }} 集)</span>
                  <n-space size="small">
                    <n-button secondary circle size="tiny" @click.stop="showJson(season, 'season', false)">
                      </n-button>
                    <n-button secondary circle size="tiny" :type="buttonTypes.INFO" @click.stop="showJson(season, 'season', true)">
                      </n-button>
                  </n-space>
                </div>
              </template>
              <div class="episodes-list">
                <div v-for="ep in season.episodes" :key="ep.id" class="episode-item">
                  <div class="episode-header-row">
                    <div class="episode-title">EP {{ ep.episode_number }} - {{ ep.name }}</div>
                    <n-space size="small">
                      <n-button secondary circle size="tiny" @click.stop="showJson(ep, 'episode', false)">
                        </n-button>
                      <n-button secondary circle size="tiny" :type="buttonTypes.PRIMARY" @click.stop="showJson(ep, 'episode', true)">
                        </n-button>
                    </n-space>
                  </div>
                  <div class="episode-meta">
                    <n-tag v-if="ep.air_date" size="tiny" :type="tagTypes.INFO">{{ ep.air_date }}</n-tag>
                    <n-tag v-if="ep.vote_average" size="tiny" :type="tagTypes.WARNING">⭐ {{ ep.vote_average }}</n-tag>
                    <n-tag v-if="ep.runtime" size="tiny">{{ ep.runtime }} min</n-tag>
                  </div>
                  <p v-if="ep.overview" class="episode-overview">{{ ep.overview }}</p>
                </div>
              </div>
            </n-collapse-item>
          </n-collapse>
        </div>
        <div v-else-if="detailForm.media_type === 'tv' && !detailForm.recursive" class="hint-section">
          <n-alert :type="tagTypes.INFO" size="small">仅获取了剧集概况，如需查看季、集详情，请开启"递归抓取所有季与集"后重新执行。</n-alert>
        </div>
      </n-card>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!detailLoading" class="empty-state">
      <n-empty :description="emptyText.WAITING_FETCH_COMMAND" />
    </div>

    <!-- JSON 弹窗 -->
    <n-modal 
      v-model:show="jsonModal.show" 
      preset="card" 
      style="width: 90vw; max-width: 600px" 
      :title="jsonModal.title || '原始 JSON 数据'"
    >
      <div class="json-wrapper">
        <n-code :code="JSON.stringify(jsonModal.data, null, 2)" language="json" word-wrap />
      </div>
      <template #footer>
        <n-button block :type="buttonTypes.PRIMARY" secondary @click="copyRawJson">
          {{ buttonText.COPY_JSON_DATA }}
        </n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  useMessage, NSpace, NCard, NInput, NButton, 
  NCode, NTag, NEmpty, NForm, NFormItem,
  NSelect, NDivider,
  NCheckbox, NAlert, NCollapse, NCollapseItem, NIcon, NModal, NProgress
} from 'naive-ui'
// 导入提取的逻辑
import { useTmdbSearch } from '../../toolkit/tmdb/hooks/useTmdbSearch'
import { useTmdbFetch } from '../../toolkit/tmdb/hooks/useTmdbFetch'
import { useTmdbJson } from '../../toolkit/tmdb/hooks/useTmdbJson'
import { copyElementContent } from '@/utils/clipboard'
import MobileTabs from '../components/MobileTabs.vue'
import {
  ButtonTypes,
  ButtonText,
  TagTypes,
  MessageText,
} from '../constants'

const message = useMessage()
const activeTab = ref('search')

const tabs = [
  { name: 'search', label: '搜索' },
  { name: 'collection', label: '收藏' },
]

// 使用常量
const buttonTypes = ButtonTypes
const buttonText = ButtonText
const tagTypes = TagTypes
const messageText = MessageText

// 额外的文本常量
const formLabel = {
  NAME: '名称',
  TYPE: '类型',
  LANGUAGE: '语言',
}

const placeholder = {
  MOVIE_OR_SERIES_NAME: '电影或剧集名称...',
  EXAMPLE_TMDB_ID: '例如: 550',
}

const emptyText = {
  WAITING_FETCH_COMMAND: '等待抓取指令...',
}

// 选项配置
const mediaTypeOptions = [
  { label: '电影 (Movie)', value: 'movie' },
  { label: '剧集 (TV)', value: 'tv' }
]

const languageOptions = [
  { label: '全语言抓取', value: 'all' },
  { label: '简体中文', value: 'zh-CN' },
  { label: '繁体中文', value: 'zh-TW' },
  { label: '英文', value: 'en-US' },
  { label: '日语', value: 'ja-JP' }
]

// 1. 搜索逻辑
const { searchLoading, searchResults, searchForm, handleSearch } = useTmdbSearch()

// 2. 抓取逻辑
const { 
  detailLoading, detailResult, detailForm, 
  titlePool, aliasPool, keywordsList, handleFetchDetail 
} = useTmdbFetch()

// 3. JSON 弹窗逻辑
const { jsonModal, showJson } = useTmdbJson(detailResult, detailForm)

const fillDetail = (item: any) => {
  detailForm.tmdb_id = item.id.toString()
  detailForm.media_type = searchForm.media_type
  detailForm.language = searchForm.language
  detailForm.recursive = (searchForm.media_type === 'tv')
  activeTab.value = 'direct'
  message.info(messageText.ID_FILLED_CHECK_CONFIG)
}

const copyRawJson = () => {
  const selector = '.json-wrapper pre'
  if (copyElementContent(selector)) {
    message.success(messageText.COPY_SUCCESS)
  } else {
    message.error(messageText.COPY_FAILED)
  }
}
</script>

<style scoped>
.mobile-tmdb-lab {
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
  color: #705df2;
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
  background: var(--card-bg-color);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.result-item:active {
  background: var(--border-color);
  transform: scale(0.98);
}

.result-title {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 8px;
}

.result-meta {
  display: flex;
  gap: 8px;
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

.result-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0;
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
  display: flex;
  align-items: center;
  gap: 8px;
}

.vote-count {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.5;
}

/* 简介 */
.overview-section {
  background: rgba(112, 93, 242, 0.1);
  border-left: 3px solid #705df2;
  border-radius: 0 8px 8px 0;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.overview-text {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.8;
  line-height: 1.6;
  margin: 0;
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

.tag-orange {
  color: #f0a020;
  border-color: rgba(240, 160, 32, 0.3);
}

/* 操作区域 */
.action-section {
  margin: 20px 0;
}

/* 季与集 */
.seasons-section {
  margin-top: 20px;
}

:deep(.n-collapse-item__header) {
  padding: 12px 0 !important;
}

:deep(.n-collapse-item__header-main) {
  width: 100%;
}

.season-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding-right: 8px;
}

.season-title {
  font-weight: 500;
  color: var(--text-color);
  font-size: 14px;
}

.episodes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.episode-item {
  background: var(--app-bg-color);
  border-radius: 10px;
  padding: 12px;
}

.episode-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.episode-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.episode-meta {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}

.episode-overview {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.5;
  line-height: 1.5;
  margin: 0;
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
