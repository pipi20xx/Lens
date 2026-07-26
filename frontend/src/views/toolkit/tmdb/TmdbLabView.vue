<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { useNotification, useClipboard } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError, warning } = useNotification()
const { copy: copyToClipboard } = useClipboard()

// ========== Tab 控制 ==========
const activeTab = ref('search')

// ========== 选项配置 ==========
const mediaTypeOptions = [
  { title: '电影 (Movie)', value: 'movie' },
  { title: '剧集 (TV)', value: 'tv' },
]
const languageOptions = [
  { title: '全语言抓取 (All Translations)', value: 'all' },
  { title: '简体中文 (zh-CN)', value: 'zh-CN' },
  { title: '繁体中文 (zh-TW)', value: 'zh-TW' },
  { title: '英文 (en-US)', value: 'en-US' },
  { title: '日语 (ja-JP)', value: 'ja-JP' },
]

// ========== 1. 搜索逻辑 ==========
const searchLoading = ref(false)
const searchResults = ref<any[]>([])
const searchForm = reactive({
  query: '',
  media_type: 'movie',
  language: 'zh-CN',
})

async function handleSearch() {
  if (!searchForm.query) return
  searchLoading.value = true
  try {
    const data: any = await toolkitApi.tmdb.search(searchForm)
    searchResults.value = data?.results || []
    if (searchResults.value.length === 0) warning('未找到相关结果')
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '未知错误'
    showError('搜索失败: ' + detail)
  } finally {
    searchLoading.value = false
  }
}

// ========== 2. 抓取逻辑 ==========
const detailLoading = ref(false)
const detailResult = ref<any>(null)
const detailForm = reactive({
  tmdb_id: '',
  media_type: 'movie',
  language: 'zh-CN',
  recursive: false,
})

const titlePool = computed(() => {
  if (!detailResult.value || !detailResult.value.translations) return []
  const titles = new Set<string>()
  if (detailResult.value.title) titles.add(detailResult.value.title)
  if (detailResult.value.name) titles.add(detailResult.value.name)
  if (detailResult.value.original_title) titles.add(detailResult.value.original_title)
  if (detailResult.value.original_name) titles.add(detailResult.value.original_name)
  const trans = detailResult.value.translations.translations || []
  trans.forEach((t: any) => {
    if (t.data?.title) titles.add(t.data.title)
    if (t.data?.name) titles.add(t.data.name)
  })
  return Array.from(titles).sort()
})

const aliasPool = computed(() => {
  if (!detailResult.value) return []
  const aliases = new Set<string>()
  const aData = detailResult.value.alternative_titles
  const list = aData?.titles || aData?.results || []
  list.forEach((item: any) => {
    if (item.title) aliases.add(item.title)
  })
  return Array.from(aliases).sort()
})

const keywordsList = computed(() => {
  if (!detailResult.value) return []
  const kData = detailResult.value.keywords
  return kData?.keywords || kData?.results || []
})

async function handleFetchDetail() {
  if (!detailForm.tmdb_id) {
    warning('请输入 TMDB ID')
    return
  }
  detailLoading.value = true
  detailResult.value = null
  const isAll = detailForm.language === 'all'
  const params = {
    tmdb_id: detailForm.tmdb_id,
    media_type: detailForm.media_type,
    language: isAll ? '' : detailForm.language,
    include_translations: isAll,
    recursive: detailForm.recursive,
  }
  try {
    const data: any = await toolkitApi.tmdb.fetch(params)
    if (data.error) {
      showError(data.error)
    } else {
      detailResult.value = data
      success('抓取成功')
    }
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '未知错误'
    showError('抓取失败: ' + detail)
  } finally {
    detailLoading.value = false
  }
}

// ========== 3. 填入 ID ==========
function fillDetail(item: any) {
  detailForm.tmdb_id = item.id.toString()
  detailForm.media_type = searchForm.media_type
  detailForm.language = searchForm.language
  detailForm.recursive = searchForm.media_type === 'tv'
  activeTab.value = 'direct'
  success('已填入 ID，请确认配置后启动抓取')
}

// ========== 4. JSON 弹窗逻辑 ==========
const jsonModal = reactive({
  show: false,
  title: '原始 JSON 数据',
  loading: false,
  data: {} as any,
})

async function fetchFullSeason(season: any) {
  jsonModal.loading = true
  jsonModal.title = `深度探针: ${season.name}`
  jsonModal.show = true
  jsonModal.data = { message: '正在从 TMDB 实时抓取该季全量数据...' }
  try {
    const isAll = detailForm.language === 'all'
    const data = await toolkitApi.tmdb.fetchSeason({
      tmdb_id: detailResult.value.id,
      season_number: season.season_number,
      language: isAll ? '' : detailForm.language,
      include_translations: isAll,
    })
    jsonModal.data = data
    jsonModal.title = `季全量详情 - ${(data as any).name}`
  } catch {
    jsonModal.data = season
  } finally {
    jsonModal.loading = false
  }
}

async function fetchFullEpisode(ep: any) {
  jsonModal.loading = true
  jsonModal.title = `深度抓取单集: EP ${ep.episode_number}`
  jsonModal.show = true
  jsonModal.data = { message: '正在从 TMDB 实时获取单集全量数据...' }
  try {
    const isAll = detailForm.language === 'all'
    const data = await toolkitApi.tmdb.fetchEpisode({
      tmdb_id: detailResult.value.id,
      season_number: ep.season_number,
      episode_number: ep.episode_number,
      language: isAll ? '' : detailForm.language,
      include_translations: isAll,
    })
    jsonModal.data = data
    jsonModal.title = `单集全量 JSON - EP ${ep.episode_number}: ${(data as any).name}`
  } catch {
    jsonModal.data = ep
  } finally {
    jsonModal.loading = false
  }
}

function showJson(data: any, type: 'main' | 'season' | 'episode' = 'main', isDeep: boolean = false) {
  if (isDeep) {
    if (type === 'episode') fetchFullEpisode(data)
    else if (type === 'season') fetchFullSeason(data)
  } else {
    jsonModal.data = data
    jsonModal.title = `元数据快照 - ${data.name || data.title || '详情'}`
    jsonModal.show = true
    jsonModal.loading = false
  }
}

function copyJsonData() {
  copyToClipboard(JSON.stringify(jsonModal.data, null, 2))
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-movie-search-outline</v-icon>
      TMDB 实验室
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">直接从 TMDB 官方抓取元数据。支持递归抓取季、集信息，并提供结构化预览与原始数据导出。</p>

    <v-row>
      <!-- 左侧：输入面板 -->
      <v-col cols="12" md="4">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4 pb-2">
            <v-icon start size="20">mdi-magnify</v-icon>
            1. 检索/定位
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-tabs v-model="activeTab" density="compact" class="mb-4">
              <v-tab value="search" size="small">关键词搜索</v-tab>
              <v-tab value="direct" size="small">直接 ID 抓取</v-tab>
            </v-tabs>

            <v-window v-model="activeTab">
              <!-- 关键词搜索 -->
              <v-window-item value="search">
                <v-text-field v-model="searchForm.query" label="名称" placeholder="电影或剧集名称..."
                  variant="outlined" density="compact" class="mb-3"
                  @keydown.enter="handleSearch" />
                <v-row class="mb-3">
                  <v-col cols="6">
                    <v-select v-model="searchForm.media_type" :items="mediaTypeOptions" label="类型"
                      variant="outlined" density="compact" />
                  </v-col>
                  <v-col cols="6">
                    <v-select v-model="searchForm.language" :items="languageOptions" label="语言"
                      variant="outlined" density="compact" />
                  </v-col>
                </v-row>
                <v-btn block color="primary" variant="flat" prepend-icon="mdi-magnify" :loading="searchLoading" @click="handleSearch">
                  执行搜索
                </v-btn>

                <!-- 搜索结果列表 -->
                <div v-if="searchResults.length > 0" class="mt-4">
                  <div class="text-subtitle-2 font-weight-bold mb-2">搜索结果</div>
                  <v-list density="compact" class="bg-transparent" style="max-height:350px;overflow-y:auto">
                    <v-list-item v-for="item in searchResults" :key="item.id" @click="fillDetail(item)" class="rounded-lg mb-1">
                      <v-list-item-title class="text-body-2 font-weight-medium">{{ item.title || item.name }}</v-list-item-title>
                      <v-list-item-subtitle class="text-caption text-medium-emphasis">
                        ID: {{ item.id }} | {{ item.release_date || item.first_air_date || '未知' }}
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </div>
              </v-window-item>

              <!-- 直接 ID 抓取 -->
              <v-window-item value="direct">
                <v-text-field v-model="detailForm.tmdb_id" label="TMDB ID" placeholder="输入 ID"
                  variant="outlined" density="compact" class="mb-3" />
                <v-row class="mb-3">
                  <v-col cols="6">
                    <v-select v-model="detailForm.media_type" :items="mediaTypeOptions" label="类型"
                      variant="outlined" density="compact" />
                  </v-col>
                  <v-col cols="6">
                    <v-select v-model="detailForm.language" :items="languageOptions" label="抓取语言/模式"
                      variant="outlined" density="compact" />
                  </v-col>
                </v-row>
                <div v-if="detailForm.media_type === 'tv'" class="d-flex align-center mb-3">
                  <v-switch v-model="detailForm.recursive" density="compact" color="primary" hide-details class="mr-2" />
                  <span class="text-body-2 text-medium-emphasis">深度递归抓取所有季和集详情</span>
                </div>
                <v-btn block color="primary" variant="flat" prepend-icon="mdi-download" :loading="detailLoading" @click="handleFetchDetail">
                  执行抓取
                </v-btn>
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>

        <!-- 快捷工具 -->
        <v-card v-if="detailResult" class="liquid-glass-card mt-4" rounded="xl">
          <v-card-title class="pa-4 pb-2">
            <v-icon start size="20">mdi-tools</v-icon>
            快捷工具
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 d-flex flex-column ga-2">
            <v-btn block variant="tonal" color="info" prepend-icon="mdi-code-block-braces" @click="showJson(detailResult, 'main')">查看本体 JSON</v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧：结果展示区 -->
      <v-col cols="12" md="8">
        <template v-if="detailResult">
          <v-card class="liquid-glass-card" rounded="xl">
            <!-- 头部 -->
            <v-card-title class="d-flex align-center pa-4">
              <v-icon start color="primary">mdi-movie-open-outline</v-icon>
              <span class="text-h6 font-weight-bold">{{ detailResult.name || detailResult.title }}</span>
              <v-chip size="small" variant="tonal" class="ml-2">{{ detailResult.release_date || detailResult.first_air_date }}</v-chip>
              <v-chip size="small" :color="detailForm.media_type === 'tv' ? 'info' : 'success'" variant="tonal" class="ml-1">
                {{ detailForm.media_type.toUpperCase() }}
              </v-chip>
              <v-spacer />
              <v-btn icon variant="tonal" size="small" @click="showJson(detailResult, 'main')" title="查看本体 JSON">
                <v-icon>mdi-code-block-braces</v-icon>
              </v-btn>
            </v-card-title>
            <v-divider />

            <v-card-text class="pa-4">
              <!-- 基本信息 -->
              <v-table density="compact" class="bg-transparent mb-4">
                <tbody>
                  <tr><td class="text-medium-emphasis" style="width:120px">原始标题</td><td>{{ detailResult.original_name || detailResult.original_title }}</td></tr>
                  <tr><td class="text-medium-emphasis">状态</td><td>{{ detailResult.status }}</td></tr>
                  <tr><td class="text-medium-emphasis">评分</td><td><v-icon size="14" color="warning">mdi-star</v-icon> {{ detailResult.vote_average }} ({{ detailResult.vote_count }} 票)</td></tr>
                  <tr><td class="text-medium-emphasis">TMDB ID</td><td>{{ detailResult.id }}</td></tr>
                  <tr>
                    <td class="text-medium-emphasis">流派</td>
                    <td>
                      <v-chip v-for="g in detailResult.genres" :key="g.id" size="x-small" variant="tonal" class="mr-1 mb-1">{{ g.name }}</v-chip>
                    </td>
                  </tr>
                </tbody>
              </v-table>

              <!-- 简介 -->
              <v-alert variant="tonal" color="primary" class="mb-4" rounded="lg">
                <div class="text-body-2">{{ detailResult.overview || '暂无简介' }}</div>
              </v-alert>

              <!-- 详细名称对照表 -->
              <v-card variant="outlined" rounded="lg" class="mb-4">
                <div class="d-flex align-center pa-3" style="background:linear-gradient(90deg, rgba(var(--v-theme-primary),0.1), transparent)">
                  <v-icon color="primary" size="20" class="mr-2">mdi-translate</v-icon>
                  <span class="text-subtitle-2 font-weight-bold" style="color:rgb(var(--v-theme-primary))">详细名称对照表 (分拣参考)</span>
                </div>

                <!-- 1. 流派 -->
                <div class="pa-3 border-b-thin">
                  <div class="text-caption text-medium-emphasis mb-1">1. 所有流派</div>
                  <div>
                    <v-chip v-for="g in detailResult.genres" :key="g.id" size="x-small" variant="outlined" class="mr-1 mb-1">{{ g.name }} ({{ g.id }})</v-chip>
                    <span v-if="!detailResult.genres?.length" class="text-medium-emphasis">N/A</span>
                  </div>
                </div>

                <!-- 2. 制作公司 -->
                <div class="pa-3 border-b-thin">
                  <div class="text-caption text-medium-emphasis mb-1">2. 制作公司</div>
                  <div>
                    <v-chip v-for="c in detailResult.production_companies" :key="c.id" size="x-small" variant="outlined" class="mr-1 mb-1">{{ c.name }} ({{ c.id }})</v-chip>
                    <span v-if="!detailResult.production_companies?.length" class="text-medium-emphasis">N/A</span>
                  </div>
                </div>

                <!-- 3. 关键词 -->
                <div class="pa-3 border-b-thin">
                  <div class="text-caption text-medium-emphasis mb-1">3. 关键标签 (Keywords)</div>
                  <div>
                    <v-chip v-for="k in keywordsList" :key="k.id" size="x-small" variant="outlined" class="mr-1 mb-1">{{ k.name }} ({{ k.id }})</v-chip>
                    <span v-if="!keywordsList.length" class="text-medium-emphasis">N/A</span>
                  </div>
                </div>

                <!-- 4. 标题池 -->
                <div class="pa-3 border-b-thin">
                  <div class="text-caption text-medium-emphasis mb-1">4. 全量标题池 ({{ titlePool.length }})</div>
                  <div v-if="titlePool.length > 0">
                    <v-chip v-for="t in titlePool" :key="t" size="x-small" variant="outlined" class="mr-1 mb-1">{{ t }}</v-chip>
                  </div>
                  <div v-else class="text-caption text-medium-emphasis pa-2 rounded" style="background:rgba(var(--v-theme-on-surface),0.03)">
                    {{ detailForm.language === 'all' ? '暂无翻译标题' : '未获取全量标题。请在左侧选择"全语言抓取"模式。' }}
                  </div>
                </div>

                <!-- 5. 别名池 -->
                <div class="pa-3">
                  <div class="text-caption font-weight-bold mb-1 text-warning">5. 全量别名池 ({{ aliasPool.length }})</div>
                  <div v-if="aliasPool.length > 0">
                    <v-chip v-for="a in aliasPool" :key="a" size="x-small" variant="outlined" color="warning" class="mr-1 mb-1">{{ a }}</v-chip>
                  </div>
                  <div v-else class="text-caption text-medium-emphasis pa-2 rounded" style="background:rgba(var(--v-theme-on-surface),0.03)">暂无别名信息</div>
                </div>
              </v-card>

              <!-- 递归季和集信息 -->
              <template v-if="detailResult.full_seasons_data">
                <h2 class="text-subtitle-1 font-weight-bold mb-3">
                  <v-icon start color="primary">mdi-television-classic</v-icon>
                  季与集 递归详情
                </h2>
                <v-expansion-panels variant="accordion" class="mb-4">
                  <v-expansion-panel v-for="season in detailResult.full_seasons_data" :key="season.id" :value="season.id">
                    <v-expansion-panel-title class="d-flex align-center">
                      <span class="font-weight-bold">{{ season.name }} ({{ season.episodes?.length || 0 }} 集)</span>
                      <v-spacer />
                      <v-btn icon variant="tonal" size="x-small" @click.stop="showJson(season, 'season', false)" title="查看当前快照">
                        <v-icon size="16">mdi-code-block-braces</v-icon>
                      </v-btn>
                      <v-btn icon variant="tonal" size="x-small" color="info" class="ml-1" @click.stop="showJson(season, 'season', true)" title="全语言深度探针">
                        <v-icon size="16">mdi-magnify-scan</v-icon>
                      </v-btn>
                    </v-expansion-panel-title>
                    <v-expansion-panel-text>
                      <v-list density="compact" class="bg-transparent">
                        <v-list-item v-for="ep in season.episodes" :key="ep.id" class="mb-2">
                          <v-list-item-title>
                            <span class="font-weight-bold">EP {{ ep.episode_number }}</span> - {{ ep.name }}
                          </v-list-item-title>
                          <v-list-item-subtitle class="d-flex align-center ga-2">
                            <v-chip size="x-small" variant="tonal" color="warning">⭐ {{ ep.vote_average }}</v-chip>
                            <v-chip size="x-small" variant="tonal" color="info">{{ ep.air_date }}</v-chip>
                            <v-chip v-if="ep.runtime" size="x-small" variant="tonal">{{ ep.runtime }} min</v-chip>
                            <v-spacer />
                            <v-btn icon variant="tonal" size="x-small" @click="showJson(ep, 'episode', false)" title="查看快照">
                              <v-icon size="14">mdi-code-block-braces</v-icon>
                            </v-btn>
                            <v-btn icon variant="tonal" size="x-small" color="primary" @click="showJson(ep, 'episode', true)" title="全语言深度探针">
                              <v-icon size="14">mdi-magnify-scan</v-icon>
                            </v-btn>
                          </v-list-item-subtitle>
                          <div v-if="ep.overview" class="text-caption text-medium-emphasis mt-1">{{ ep.overview }}</div>
                        </v-list-item>
                      </v-list>
                    </v-expansion-panel-text>
                  </v-expansion-panel>
                </v-expansion-panels>
              </template>
              <v-alert v-else-if="detailForm.media_type === 'tv' && !detailForm.recursive" variant="tonal" type="info" class="mb-4" rounded="lg">
                仅获取了剧集概况，如需查看季、集详情，请在左侧开启"深度递归抓取"后重新执行。
              </v-alert>
            </v-card-text>
          </v-card>
        </template>

        <!-- 空状态 -->
        <v-card v-else class="liquid-glass-card text-center" rounded="xl" style="min-height:400px;display:flex;align-items:center;justify-content:center">
          <div class="py-12">
            <v-icon size="64" color="grey" class="mb-4">mdi-movie-search-outline</v-icon>
            <div class="text-body-1 text-medium-emphasis">等待抓取数据...</div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- JSON 详情弹窗 -->
    <GlassDialog v-model="jsonModal.show" :max-width="900"
      icon="mdi-code-block-braces" :title="jsonModal.title" cancel-text="关闭"
    >
      <v-progress-linear v-if="jsonModal.loading" indeterminate color="primary" class="mb-2" />
      <pre class="code-block code-block--flat">{{ JSON.stringify(jsonModal.data, null, 2) }}</pre>

      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-content-copy" @click="copyJsonData">复制 JSON 数据</v-btn>
      </template>
    </GlassDialog>
  </v-container>
</template>
