<template>
  <div class="mobile-bangumi-lab">
    <!-- 页面标题 -->
    <div class="lab-header">
      <h1 class="lab-title">Bangumi 实验室</h1>
      <p class="lab-desc">从 Bangumi 官方抓取条目与角色元数据</p>
    </div>

    <!-- 输入面板 -->
    <n-card class="input-card" :bordered="false">
      <n-tabs v-model:value="activeTab" type="segment" animated>
        <n-tab-pane name="search" tab="关键词搜索">
          <n-form label-placement="top" class="mobile-form">
            <n-form-item label="关键词">
              <n-input
                v-model:value="searchForm.keywords"
                placeholder="动画、漫画、游戏名称..."
                @keyup.enter="handleSearch"
                size="large"
              />
            </n-form-item>
            <n-form-item label="类型">
              <n-select
                v-model:value="searchForm.type"
                :options="typeOptions"
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
                v-for="item in searchResults"
                :key="item.id"
                class="result-item"
                @click="fillSubject(item)"
              >
                <div class="result-title">{{ item.name_cn || item.name }}</div>
                <div class="result-meta">
                  <n-tag size="tiny" type="info">ID: {{ item.id }}</n-tag>
                  <span class="result-type">{{ getTypeLabel(item.type) }}</span>
                </div>
              </div>
            </div>
          </div>
        </n-tab-pane>

        <n-tab-pane name="direct" tab="直接 ID 抓取">
          <n-form label-placement="top" class="mobile-form">
            <n-form-item label="Subject ID">
              <n-input
                v-model:value="form.subject_id"
                placeholder="例如: 253, 302506..."
                @keyup.enter="handleFetchAll"
                size="large"
              />
            </n-form-item>
            <n-button
              block
              type="primary"
              size="large"
              :loading="loading"
              @click="handleFetchAll"
            >
              <template #icon><n-icon><LabIcon /></n-icon></template>
              执行抓取
            </n-button>
          </n-form>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 结果展示区 -->
    <div v-if="subjectResult" class="result-section">
      <n-card class="result-card" :bordered="false">
        <template #header>
          <div class="result-header">
            <h3 class="result-name">{{ subjectResult.name_cn || subjectResult.name }}</h3>
            <n-space size="small" wrap>
              <n-tag size="small" type="primary">{{ getTypeLabel(subjectResult.type) }}</n-tag>
              <n-tag size="small" type="info">ID: {{ subjectResult.id }}</n-tag>
            </n-space>
          </div>
        </template>

        <!-- 封面 -->
        <div v-if="subjectResult.images?.common" class="cover-section">
          <img :src="subjectResult.images.common" class="cover-image" />
        </div>

        <!-- 简介 -->
        <div v-if="subjectResult.summary" class="overview-section">
          <p class="overview-text">{{ subjectResult.summary }}</p>
        </div>

        <!-- 信息列表 -->
        <div v-if="infoboxList.length > 0" class="info-section">
          <div
            v-for="(item, index) in infoboxList.slice(0, 8)"
            :key="index"
            class="info-row"
          >
            <span class="info-label">{{ item.key }}</span>
            <span class="info-value">{{ item.value }}</span>
          </div>
        </div>

        <!-- 标签池 -->
        <div v-if="uniqueMetaTags.length > 0" class="tags-section">
          <div class="section-title">标签 ({{ uniqueMetaTags.length }})</div>
          <div class="tag-pool">
            <span v-for="tag in uniqueMetaTags" :key="tag" class="data-tag">{{ tag }}</span>
          </div>
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
          <div class="section-title">别名 ({{ aliasPool.length }})</div>
          <div class="tag-pool">
            <span v-for="alias in aliasPool" :key="alias" class="data-tag tag-orange">{{ alias }}</span>
          </div>
        </div>

        <!-- 快捷工具 -->
        <n-card class="tools-card" :bordered="false">
          <div class="tools-list">
            <n-button block secondary type="primary" @click="showJson(subjectResult, '条目')" :disabled="!subjectResult">
              <template #icon><n-icon><CodeIcon /></n-icon></template>
              条目 JSON
            </n-button>
            <n-button block secondary type="info" @click="showJson(episodesResult, '章节')" :disabled="!episodesResult">
              <template #icon><n-icon><ListIcon /></n-icon></template>
              章节 JSON
            </n-button>
            <n-button block secondary type="success" @click="showJson(charactersResult, '角色')" :disabled="!charactersResult">
              <template #icon><n-icon><PeopleIcon /></n-icon></template>
              角色 JSON
            </n-button>
          </div>
        </n-card>

        <!-- 角色列表 -->
        <div v-if="charactersResult?.length" class="characters-section">
          <n-divider>角色列表 ({{ charactersResult.length }})</n-divider>
          <div class="character-list">
            <div v-for="char in charactersResult.slice(0, 10)" :key="char.id" class="character-item">
              <n-avatar
                v-if="char.images?.small"
                round
                size="small"
                :src="char.images.small"
              />
              <div class="character-info">
                <div class="character-name">{{ char.name }}</div>
                <div v-if="char.relation" class="character-relation">{{ char.relation }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 章节列表 -->
        <div v-if="episodesResult?.data?.length" class="episodes-section">
          <n-divider>章节列表 ({{ episodesResult.data.length }})</n-divider>
          <div class="episode-list">
            <div v-for="ep in episodesResult.data.slice(0, 10)" :key="ep.id" class="episode-item">
              <div class="episode-header">
                <span class="episode-ep">EP{{ ep.ep }}</span>
                <span class="episode-name">{{ ep.name_cn || ep.name }}</span>
              </div>
              <div v-if="ep.airdate" class="episode-date">{{ ep.airdate }}</div>
            </div>
          </div>
        </div>
      </n-card>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading" class="empty-state">
      <n-empty description="等待抓取指令..." />
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
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import {
  useMessage, NSpace, NCard, NInput, NButton,
  NCode, NTag, NEmpty, NForm, NFormItem,
  NSelect, NDivider, NTabs, NTabPane,
  NIcon, NModal, NAvatar
} from 'naive-ui'
import {
  TerminalOutlined as CodeIcon,
  SearchOutlined as SearchIcon,
  ScienceOutlined as LabIcon,
  ListAltOutlined as ListIcon,
  PeopleAltOutlined as PeopleIcon
} from '@vicons/material'
import axios from 'axios'

const message = useMessage()
const activeTab = ref('search')

// 类型选项
const typeOptions = [
  { label: '动画', value: 2 },
  { label: '漫画', value: 1 },
  { label: '游戏', value: 4 },
  { label: '音乐', value: 3 },
  { label: '书籍', value: 6 }
]

const getTypeLabel = (type: number) => {
  const map: Record<number, string> = {
    1: '漫画',
    2: '动画',
    3: '音乐',
    4: '游戏',
    6: '书籍'
  }
  return map[type] || '未知'
}

// 状态
const loading = ref(false)
const searchLoading = ref(false)
const subjectResult = ref<any>(null)
const charactersResult = ref<any>(null)
const episodesResult = ref<any>(null)
const searchResults = ref<any[]>([])

const form = reactive({
  subject_id: ''
})

const searchForm = reactive({
  keywords: '',
  type: 2
})

// JSON 弹窗
const jsonModal = ref({
  show: false,
  title: '',
  data: null as any
})

const showJson = (data: any, title: string) => {
  if (!data) {
    message.warning(`${title} 数据为空`)
    return
  }
  jsonModal.value.data = data
  jsonModal.value.title = title
  jsonModal.value.show = true
}

// 搜索
const handleSearch = async () => {
  if (!searchForm.keywords) return
  searchLoading.value = true
  try {
    const res = await axios.get('/api/bangumi_lab/search', { params: searchForm })
    searchResults.value = res.data.results || []
    if (searchResults.value.length === 0) message.warning('未找到相关条目')
  } catch (e) {
    message.error('搜索失败')
  } finally {
    searchLoading.value = false
  }
}

const fillSubject = (item: any) => {
  form.subject_id = item.id.toString()
  activeTab.value = 'direct'
  message.info('已填入 ID，请确认后启动抓取')
}

// 计算属性
const infoboxList = computed(() => {
  if (!subjectResult.value?.infobox) return []
  return subjectResult.value.infobox.map((item: any) => {
    let value = ''
    if (Array.isArray(item.value)) {
      value = item.value.map((v: any) => v.v || v).join(', ')
    } else {
      value = item.value
    }
    return { key: item.key, value }
  })
})

const titlePool = computed(() => {
  if (!subjectResult.value) return []
  const titles = new Set<string>()
  if (subjectResult.value.name) titles.add(subjectResult.value.name)
  if (subjectResult.value.name_cn) titles.add(subjectResult.value.name_cn)
  return Array.from(titles)
})

const uniqueMetaTags = computed(() => {
  const rawTags = subjectResult.value?.meta_tags || []
  return Array.from(new Set(rawTags.map((t: any) => {
    if (typeof t === 'string') return t.trim()
    return (t.name || t.label || '').trim()
  }))).filter(Boolean)
})

const aliasPool = computed(() => {
  if (!subjectResult.value?.infobox) return []
  const aliases = new Set<string>()
  const aliasItem = subjectResult.value.infobox.find((item: any) =>
    ['别名', 'Alias', '又名'].includes(item.key)
  )
  if (aliasItem) {
    if (Array.isArray(aliasItem.value)) {
      aliasItem.value.forEach((v: any) => {
        const val = typeof v === 'string' ? v : (v.v || v)
        if (val) aliases.add(val)
      })
    } else {
      aliases.add(aliasItem.value)
    }
  }
  return Array.from(aliases).sort()
})

// 抓取
const handleFetchAll = async () => {
  if (!form.subject_id) {
    message.warning('请输入 Subject ID')
    return
  }

  loading.value = true
  subjectResult.value = null
  charactersResult.value = null
  episodesResult.value = null

  try {
    const [subRes, charRes, epRes] = await Promise.all([
      axios.get(`/api/bangumi_lab/subject/${form.subject_id}`),
      axios.get(`/api/bangumi_lab/subject/${form.subject_id}/characters`),
      axios.get('/api/bangumi_lab/episodes', { params: { subject_id: form.subject_id, limit: 100 } })
    ])

    if (subRes.data.error) message.error(`条目抓取失败: ${subRes.data.error}`)
    else subjectResult.value = subRes.data

    if (charRes.data && !charRes.data.error) charactersResult.value = charRes.data
    if (epRes.data && !epRes.data.error) episodesResult.value = epRes.data

    if (subjectResult.value) message.success('抓取完成')
  } catch (e: any) {
    message.error('请求异常: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.mobile-bangumi-lab {
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
  color: #f4a261;
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
  align-items: center;
  gap: 8px;
}

.result-type {
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

/* 封面 */
.cover-section {
  margin-bottom: 16px;
}

.cover-image {
  width: 100%;
  max-width: 200px;
  border-radius: 12px;
  display: block;
  margin: 0 auto;
}

/* 简介 */
.overview-section {
  background: rgba(244, 162, 97, 0.1);
  border-left: 3px solid #f4a261;
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
  flex-shrink: 0;
}

.info-value {
  font-size: 14px;
  color: var(--text-color);
  text-align: right;
  flex: 1;
  margin-left: 12px;
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

/* 工具卡片 */
.tools-card {
  background: var(--app-bg-color);
  border-radius: 12px;
  margin: 16px 0;
}

.tools-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 角色列表 */
.characters-section {
  margin-top: 20px;
}

.character-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.character-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--app-bg-color);
  border-radius: 10px;
  padding: 10px;
}

.character-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
}

.character-relation {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.5;
}

/* 章节列表 */
.episodes-section {
  margin-top: 20px;
}

.episode-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.episode-item {
  background: var(--app-bg-color);
  border-radius: 10px;
  padding: 10px;
}

.episode-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.episode-ep {
  font-size: 12px;
  font-weight: 600;
  color: #f4a261;
  background: rgba(244, 162, 97, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.episode-name {
  font-size: 14px;
  color: var(--text-color);
  flex: 1;
}

.episode-date {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.5;
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
