<script setup lang="ts">
import { ref, reactive } from 'vue'
import { actorsApi } from '@/api/actors'
import { toolkitApi } from '@/api/toolkit'
import { useNotification, useClipboard } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError, warning } = useNotification()
const { copy: copyToClipboard } = useClipboard()

const activeTab = ref('search')

const languageOptions = [
  { title: '全语言抓取 (All Translations)', value: 'all' },
  { title: '简体中文 (zh-CN)', value: 'zh-CN' },
  { title: '繁体中文 (zh-TW)', value: 'zh-TW' },
  { title: '英文 (en-US)', value: 'en-US' },
  { title: '日语 (ja-JP)', value: 'ja-JP' },
]

const searchQuery = ref('')
const searchLoading = ref(false)
const searchResults = ref<any[]>([])

async function handleSearch() {
  if (!searchQuery.value) return
  searchLoading.value = true
  try {
    const res: any = await actorsApi.searchTmdb(searchQuery.value)
    searchResults.value = res.results || []
    if (searchResults.value.length === 0) warning('未找到相关演员')
  } catch {
    showError('搜索异常')
  } finally {
    searchLoading.value = false
  }
}

const personId = ref('')
const detailLanguage = ref('zh-CN')
const analyzeLoading = ref(false)
const result = ref<any>(null)

async function handleAnalyze() {
  if (!personId.value) { warning('请输入 Person ID'); return }
  analyzeLoading.value = true
  result.value = null
  const isAll = detailLanguage.value === 'all'
  const params = {
    person_id: personId.value,
    language: isAll ? '' : detailLanguage.value,
    include_translations: isAll,
  }
  try {
    const res: any = await toolkitApi.actorLab.analyze(params)
    result.value = res
    success('深度分析完成')
  } catch { showError('分析失败') }
  finally { analyzeLoading.value = false }
}

function fillId(person: any) {
  personId.value = person.id.toString()
  activeTab.value = 'direct'
  handleAnalyze()
}

const jsonModal = reactive({ show: false, data: {} as any })
function showJson(data: any) { jsonModal.data = data; jsonModal.show = true }

function copyRawJson() {
  copyToClipboard(JSON.stringify(jsonModal.data, null, 2))
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-account-star</v-icon>
      TMDB 演员实验室
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">基于 TMDB 数据的智能探测工具。能够根据出生地自动匹配母语姓名，并生成全量别名池。</p>

    <v-row>
      <v-col cols="12" md="4">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4 pb-2"><v-icon start size="20">mdi-account-search-outline</v-icon> 1. 演员定位</v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-tabs v-model="activeTab" density="compact" class="mb-4">
              <v-tab value="search" size="small">姓名搜索</v-tab>
              <v-tab value="direct" size="small">直接 ID 探测</v-tab>
            </v-tabs>
            <v-window v-model="activeTab">
              <v-window-item value="search">
                <v-text-field v-model="searchQuery" label="演员姓名" placeholder="中文或英文姓名..." variant="outlined" density="compact" class="mb-3" @keydown.enter="handleSearch" />
                <v-btn block color="primary" variant="flat" prepend-icon="mdi-magnify" :loading="searchLoading" @click="handleSearch">执行搜索</v-btn>
                <div v-if="searchResults.length > 0" class="mt-4">
                  <div class="text-subtitle-2 font-weight-bold mb-2">搜索结果</div>
                  <v-list density="compact" class="bg-transparent" style="max-height:400px;overflow-y:auto">
                    <v-list-item v-for="person in searchResults" :key="person.id" @click="fillId(person)" class="rounded-lg mb-1">
                      <template #prepend><v-avatar size="40" rounded="xl" class="mr-3"><v-img v-if="person.profile_path" :src="'https://image.tmdb.org/t/p/w200' + person.profile_path" /><v-icon v-else icon="mdi-account" /></v-avatar></template>
                      <v-list-item-title class="text-body-2 font-weight-medium">{{ person.name }}</v-list-item-title>
                      <v-list-item-subtitle class="text-caption text-medium-emphasis">Known for: {{ person.known_for_department }} | ID: {{ person.id }}</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </div>
              </v-window-item>
              <v-window-item value="direct">
                <v-text-field v-model="personId" label="TMDB Person ID" placeholder="例如: 60063" variant="outlined" density="compact" class="mb-3" />
                <v-select v-model="detailLanguage" :items="languageOptions" label="抓取语言/模式" variant="outlined" density="compact" class="mb-3" />
                <v-btn block color="primary" variant="flat" prepend-icon="mdi-chart-bell-curve-cumulative" :loading="analyzeLoading" @click="handleAnalyze">执行分析</v-btn>
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <template v-if="result">
          <v-card class="liquid-glass-card" rounded="xl">
            <div class="d-flex align-center pa-6" style="background:linear-gradient(135deg, rgba(var(--v-theme-primary),0.08), transparent)">
              <v-avatar size="100" rounded="xl" class="mr-6" style="border:3px solid rgba(var(--v-theme-primary),0.3)">
                <v-img v-if="result.profile_path" :src="'https://image.tmdb.org/t/p/h632' + result.profile_path" />
                <v-icon v-else icon="mdi-account" size="48" />
              </v-avatar>
              <div class="flex-grow-1">
                <h2 class="text-h5 font-weight-bold" style="color:rgb(var(--v-theme-primary))">{{ result.origin_name }}</h2>
                <div class="text-body-1 text-medium-emphasis mb-2">{{ result.main_name }}</div>
                <div class="d-flex flex-wrap ga-2">
                  <v-chip size="small" color="primary" variant="tonal">{{ result.chinese_name }}</v-chip>
                  <v-chip v-if="result.imdb_id" size="small" color="info" variant="tonal">IMDB: {{ result.imdb_id }}</v-chip>
                  <v-chip size="small" variant="tonal">TMDB: {{ result.id }}</v-chip>
                </div>
              </div>
              <v-btn icon variant="tonal" @click="showJson(result.raw)"><v-icon>mdi-code-block-braces</v-icon></v-btn>
            </div>
            <v-divider />
            <v-card-text class="pa-4">
              <v-card variant="outlined" rounded="lg">
                <div class="d-flex align-center pa-3" style="background:linear-gradient(90deg, rgba(var(--v-theme-primary),0.1), transparent)">
                  <v-icon color="primary" size="20" class="mr-2">mdi-card-account-details-outline</v-icon>
                  <span class="text-subtitle-2 font-weight-bold" style="color:rgb(var(--v-theme-primary))">演员关键信息深度解析 (扫描报告)</span>
                </div>
                <v-row class="pa-3 border-b-thin">
                  <v-col cols="6"><div class="text-caption text-medium-emphasis mb-1">1. 中文/通用名</div><v-chip size="small" variant="outlined">{{ result.chinese_name }}</v-chip></v-col>
                  <v-col cols="6"><div class="text-caption text-medium-emphasis mb-1">2. 原产地/母语名</div><v-chip size="small" variant="outlined" color="primary">{{ result.origin_name }}</v-chip></v-col>
                </v-row>
                <v-row class="pa-3 border-b-thin">
                  <v-col cols="6"><div class="text-caption text-medium-emphasis mb-1">3. 出生地</div><div class="text-body-2">{{ result.place_of_birth || '未知' }}</div></v-col>
                  <v-col cols="6"><div class="text-caption text-medium-emphasis mb-1">4. 生日/逝世</div><div class="text-body-2">{{ result.birthday || '未知' }}<span v-if="result.deathday" class="text-error"> 至 {{ result.deathday }}</span></div></v-col>
                </v-row>
                <div class="pa-3 border-b-thin">
                  <div class="text-caption text-medium-emphasis mb-1">5. 全量别名池 (Alias Pool - {{ result.name_pool?.length || 0 }})</div>
                  <div v-if="result.name_pool?.length"><v-chip v-for="name in result.name_pool" :key="name" size="x-small" variant="outlined" class="mr-1 mb-1">{{ name }}</v-chip></div>
                  <div v-else class="text-caption text-medium-emphasis">N/A</div>
                </div>
                <div class="pa-3">
                  <div class="text-caption text-medium-emphasis mb-2">6. 代表作品 (Top Works)</div>
                  <div v-if="result.top_works?.length" class="rounded pa-2" style="background:rgba(var(--v-theme-on-surface),0.03)">
                    <div v-for="work in result.top_works" :key="work.id" class="d-flex align-center justify-space-between pa-2 border-b-thin">
                      <div class="d-flex align-center ga-2">
                        <v-chip size="x-small" :color="work.media_type === 'movie' ? 'success' : 'info'" variant="tonal">{{ work.media_type === 'movie' ? '电影' : '剧集' }}</v-chip>
                        <span class="text-body-2 font-weight-medium">{{ work.title }}</span>
                        <span class="text-caption text-medium-emphasis">({{ work.original_title }})</span>
                      </div>
                      <div class="d-flex ga-2">
                        <span class="text-caption text-medium-emphasis font-mono">{{ work.release_date || '未知' }}</span>
                        <span class="text-caption text-warning">⭐ {{ work.vote_average?.toFixed(1) }}</span>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-caption text-medium-emphasis">N/A</div>
                </div>
              </v-card>
            </v-card-text>
          </v-card>
        </template>
        <v-card v-else class="liquid-glass-card text-center" rounded="xl" style="min-height:400px;display:flex;align-items:center;justify-content:center">
          <div class="py-12"><v-icon size="64" color="grey" class="mb-4">mdi-account-search-outline</v-icon><div class="text-body-1 text-medium-emphasis">等待探测指令...</div></div>
        </v-card>
      </v-col>
    </v-row>

<GlassDialog v-model="jsonModal.show" :max-width="900"
  icon="mdi-code-block-braces" title="演员原始元数据 (Raw JSON)" cancel-text="关闭"
>
  <pre class="code-block code-block--flat">{{ JSON.stringify(jsonModal.data, null, 2) }}</pre>
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-copy" @click="copyRawJson">复制数据</v-btn>
  </template>
</GlassDialog>
  </v-container>
</template>
