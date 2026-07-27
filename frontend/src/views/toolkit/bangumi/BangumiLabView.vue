<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { bangumiLabApi } from '@/api/bangumiLab'
import { useNotification, useClipboard } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError, warning } = useNotification()
const { copy: copyToClipboard } = useClipboard()

// ========== Tab 控制 ==========
const activeTab = ref('search')

// ========== 搜索逻辑 ==========
const searchLoading = ref(false)
const searchResults = ref<any[]>([])
const searchForm = reactive({ keywords: '', type: 2 })

async function handleSearch() {
  if (!searchForm.keywords) return
  searchLoading.value = true
  try {
    const data: any = await bangumiLabApi.search(searchForm.keywords)
    searchResults.value = data?.results || []
    if (searchResults.value.length === 0) warning('未找到相关条目')
  } catch {
    showError('搜索失败')
  } finally {
    searchLoading.value = false
  }
}

// ========== 抓取逻辑 ==========
const loading = ref(false)
const subjectResult = ref<any>(null)
const charactersResult = ref<any>(null)
const episodesResult = ref<any>(null)
const form = reactive({ subject_id: '' })

// 解析 Infobox
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

// 标题池
const titlePool = computed(() => {
  if (!subjectResult.value) return []
  const titles = new Set<string>()
  if (subjectResult.value.name) titles.add(subjectResult.value.name)
  if (subjectResult.value.name_cn) titles.add(subjectResult.value.name_cn)
  return Array.from(titles)
})

// 去重后的系统标签
const uniqueMetaTags = computed(() => {
  const rawTags = subjectResult.value?.meta_tags || []
  return Array.from(new Set(rawTags.map((t: any) => {
    if (typeof t === 'string') return t.trim()
    return (t.name || t.label || '').trim()
  }))).filter(Boolean)
})

// 别名池
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

// 类型名映射
const typeName = computed(() => {
  if (!subjectResult.value) return ''
  const types: Record<number, string> = { 1: '书籍', 2: '动画', 3: '音乐', 4: '游戏', 6: '三次元' }
  return types[subjectResult.value.type] || '未知'
})

async function handleFetchAll() {
  if (!form.subject_id) {
    warning('请输入 Subject ID')
    return
  }
  loading.value = true
  subjectResult.value = null
  charactersResult.value = null
  episodesResult.value = null

  try {
    const [subData, charData, epData] = await Promise.all([
      bangumiLabApi.getSubject(Number(form.subject_id)),
      bangumiLabApi.getSubjectCharacters(Number(form.subject_id)),
      bangumiLabApi.getEpisodes({ subject_id: form.subject_id, limit: 100 }),
    ])
    if ((subData as any)?.error) {
      const errMsg = (subData as any).error
      if (errMsg.includes('Token')) warning('条目获取失败: ' + errMsg)
      else showError('条目获取失败: ' + errMsg)
    }
    else subjectResult.value = subData
    if (charData && !(charData as any)?.error) charactersResult.value = charData
    if (epData && !(epData as any)?.error) episodesResult.value = epData
    else if ((epData as any)?.error) {
      const errMsg = (epData as any).error
      if (errMsg.includes('Token')) warning('章节获取失败: ' + errMsg)
      else warning('章节获取失败: ' + errMsg)
    }
    if (subjectResult.value) success('抓取完成')
  } catch (e: any) {
    showError('请求异常: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function fillSubject(item: any) {
  form.subject_id = item.id.toString()
  activeTab.value = 'direct'
  handleFetchAll()
}

// ========== JSON 弹窗 ==========
const jsonModal = reactive({ show: false, title: 'Bangumi JSON', data: {} as any })

function showJson(data: any, label: string) {
  jsonModal.data = data
  jsonModal.title = `Bangumi ${label} JSON`
  jsonModal.show = true
}

function copyJsonData() {
  copyToClipboard(JSON.stringify(jsonModal.data, null, 2))
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-flask-outline</v-icon>
      Bangumi 实验室
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">直接从 Bangumi (番组计划) 官方抓取条目与角色元数据。采用乐高模块化设计。</p>

    <v-row>
      <!-- 左侧：输入面板 -->
      <v-col cols="12" md="4">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4 pb-2">
            <v-icon start size="20">mdi-magnify</v-icon>
            检索/定位
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-tabs v-model="activeTab" density="compact" class="mb-4">
              <v-tab value="search" size="small">关键词搜索</v-tab>
              <v-tab value="direct" size="small">直接 ID 抓取</v-tab>
            </v-tabs>

            <v-window v-model="activeTab">
              <v-window-item value="search">
                <v-text-field v-model="searchForm.keywords" label="关键词" placeholder="番剧名称..."
                  variant="outlined" density="compact" class="mb-3" @keydown.enter="handleSearch" />
                <v-btn block color="primary" variant="flat" prepend-icon="mdi-magnify" :loading="searchLoading" @click="handleSearch">执行搜索</v-btn>
                <div v-if="searchResults.length > 0" class="mt-4">
                  <div class="text-subtitle-2 font-weight-bold mb-2">搜索结果</div>
                  <div class="d-flex flex-column ga-2" style="max-height:350px;overflow-y:auto">
                    <v-card v-for="item in searchResults" :key="item.id" @click="fillSubject(item)"
                      rounded="lg" variant="tonal" class="list-card pa-3 cursor-pointer">
                      <div class="text-body-2 font-weight-medium">{{ item.name_cn || item.name }}</div>
                      <div class="text-caption text-medium-emphasis">{{ item.name }} | ID: {{ item.id }}</div>
                    </v-card>
                  </div>
                </div>
              </v-window-item>

              <v-window-item value="direct">
                <v-text-field v-model="form.subject_id" label="Subject ID (条目 ID)" placeholder="例如: 253, 302506..."
                  variant="outlined" density="compact" class="mb-3" @keydown.enter="handleFetchAll" />
                <v-btn block color="primary" variant="flat" prepend-icon="mdi-download" :loading="loading" @click="handleFetchAll">执行抓取</v-btn>
              </v-window-item>
            </v-window>
          </v-card-text>
        </v-card>

        <!-- 快捷工具 -->
        <v-card v-if="subjectResult" class="liquid-glass-card mt-4" rounded="xl">
          <v-card-title class="pa-4 pb-2">
            <v-icon start size="20">mdi-tools</v-icon>
            快捷工具
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 d-flex flex-column ga-2">
<v-btn block variant="tonal" color="info" prepend-icon="mdi-code-block-braces" @click="showJson(subjectResult, 'Subject')">查看条目原始 JSON</v-btn>
            <v-btn block variant="tonal" color="info" prepend-icon="mdi-code-block-braces" @click="showJson(episodesResult, 'Episodes')">查看章节原始 JSON</v-btn>
            <v-btn block variant="tonal" color="info" prepend-icon="mdi-code-block-braces" @click="showJson(charactersResult, 'Characters')">查看角色原始 JSON</v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧：结果展示区 -->
      <v-col cols="12" md="8">
        <template v-if="subjectResult">
          <!-- 条目详情卡片 -->
          <v-card class="liquid-glass-card mb-4" rounded="xl">
            <v-card-title class="d-flex align-center pa-4">
              <v-icon start color="primary">mdi-bookmark-outline</v-icon>
              <span class="text-h6 font-weight-bold">{{ subjectResult.name_cn || subjectResult.name }}</span>
              <v-chip size="small" variant="tonal" class="ml-2">{{ subjectResult.date || '未知日期' }}</v-chip>
              <v-chip size="small" color="info" variant="tonal" class="ml-1">{{ typeName }}</v-chip>
            </v-card-title>
            <v-divider />
            <v-card-text class="pa-4">
              <v-row>
                <v-col cols="4" md="3">
                  <v-img :src="subjectResult.images?.large || 'https://bgm.tv/img/no_icon_subject.png'" rounded="lg" cover aspect-ratio="3/4" />
                </v-col>
                <v-col cols="8" md="9">
                  <v-table density="compact" class="bg-transparent">
                    <tbody>
                      <tr><td class="text-medium-emphasis" style="width:100px">原始名称</td><td>{{ subjectResult.name }}</td></tr>
                      <tr><td class="text-medium-emphasis">中文名称</td><td>{{ subjectResult.name_cn || 'N/A' }}</td></tr>
                      <tr><td class="text-medium-emphasis">Bangumi ID</td><td>{{ subjectResult.id }}</td></tr>
                      <tr>
                        <td class="text-medium-emphasis">评分</td>
                        <td><span class="text-warning font-weight-bold">{{ subjectResult.rating?.score || '0.0' }}</span> ({{ subjectResult.rating?.total || 0 }} 人评价)</td>
                      </tr>
                    </tbody>
                  </v-table>
                </v-col>
              </v-row>
              <v-alert variant="tonal" color="primary" class="mt-4" rounded="lg">
                <div class="text-body-2" style="white-space:pre-wrap">{{ subjectResult.summary || '暂无简介' }}</div>
              </v-alert>
            </v-card-text>
          </v-card>

          <!-- 元数据探针报告 -->
          <v-card class="liquid-glass-card mb-4" rounded="xl">
            <div class="d-flex align-center pa-3" style="background:linear-gradient(90deg, rgba(var(--v-theme-primary),0.1), transparent)">
              <v-icon color="primary" size="20" class="mr-2">mdi-tag-multiple-outline</v-icon>
              <span class="text-subtitle-2 font-weight-bold" style="color:rgb(var(--v-theme-primary))">元数据探针报告</span>
            </div>
            <!-- Infobox -->
            <div v-if="infoboxList.length" class="pa-3 border-b-thin">
              <div class="text-caption text-medium-emphasis mb-1">Infobox</div>
              <v-table density="compact" class="bg-transparent">
                <tbody>
                  <tr v-for="item in infoboxList" :key="item.key">
                    <td class="text-medium-emphasis" style="width:120px">{{ item.key }}</td>
                    <td>{{ item.value }}</td>
                  </tr>
                </tbody>
              </v-table>
            </div>
            <!-- Meta Tags -->
            <div v-if="uniqueMetaTags.length" class="pa-3 border-b-thin">
              <div class="text-caption text-medium-emphasis mb-1">系统标签</div>
              <div>
                <v-chip v-for="tag in uniqueMetaTags" :key="tag" size="x-small" variant="tonal" class="mr-1 mb-1">{{ tag }}</v-chip>
              </div>
            </div>
            <!-- 标题池 -->
            <div class="pa-3 border-b-thin">
              <div class="text-caption text-medium-emphasis mb-1">全量标题池 ({{ titlePool.length }})</div>
              <div>
                <v-chip v-for="t in titlePool" :key="t" size="x-small" variant="outlined" class="mr-1 mb-1">{{ t }}</v-chip>
              </div>
            </div>
            <!-- 别名池 -->
            <div class="pa-3">
              <div class="text-caption font-weight-bold mb-1 text-warning">全量别名池 ({{ aliasPool.length }})</div>
              <div v-if="aliasPool.length">
                <v-chip v-for="a in aliasPool" :key="a" size="x-small" variant="outlined" color="warning" class="mr-1 mb-1">{{ a }}</v-chip>
              </div>
              <div v-else class="text-caption text-medium-emphasis">暂无别名信息</div>
            </div>
          </v-card>

          <!-- 角色面板 -->
          <v-card v-if="charactersResult?.length" class="liquid-glass-card mb-4" rounded="xl">
            <v-card-title class="pa-4 pb-2">
              <v-icon start size="20" color="primary">mdi-account-group-outline</v-icon>
              角色 ({{ charactersResult.length }})
            </v-card-title>
            <v-divider />
            <v-card-text class="pa-4">
              <v-row>
                <v-col v-for="char in charactersResult.slice(0, 20)" :key="char.id" cols="6" sm="4" md="3">
                  <div class="text-center mb-2">
                    <v-avatar size="64" rounded="xl" class="mb-1">
                      <v-img v-if="char.images?.large" :src="char.images.large" />
                      <v-icon v-else icon="mdi-account" size="32" />
                    </v-avatar>
                    <div class="text-body-2 font-weight-medium text-truncate">{{ char.name }}</div>
                    <div class="text-caption text-medium-emphasis">{{ char.type || '' }}</div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- 章节面板 -->
          <v-card v-if="episodesResult?.length" class="liquid-glass-card" rounded="xl">
            <v-card-title class="pa-4 pb-2">
              <v-icon start size="20" color="primary">mdi-playlist-play</v-icon>
              章节 ({{ episodesResult.length }})
            </v-card-title>
            <v-divider />
            <v-table density="compact" class="bg-transparent" style="max-height:400px;overflow-y:auto">
              <thead>
                <tr><th>#</th><th>标题</th><th>日期</th><th class="text-right">时长</th></tr>
              </thead>
              <tbody>
                <tr v-for="ep in episodesResult" :key="ep.id">
                  <td class="font-weight-bold" style="width:50px">{{ ep.sort || ep.ep }}</td>
                  <td>{{ ep.name_cn || ep.name }}</td>
                  <td class="text-medium-emphasis">{{ ep.airdate || '-' }}</td>
                  <td class="text-right text-medium-emphasis">{{ ep.duration || '-' }}</td>
                </tr>
              </tbody>
            </v-table>
          </v-card>
        </template>

        <!-- 空状态 -->
        <v-card v-else class="liquid-glass-card text-center" rounded="xl" style="min-height:400px;display:flex;align-items:center;justify-content:center">
          <div class="py-12">
            <v-icon size="64" color="grey" class="mb-4">mdi-flask-outline</v-icon>
            <div class="text-body-1 text-medium-emphasis">等待抓取 Bangumi 数据...</div>
          </div>
        </v-card>
      </v-col>
    </v-row>

<!-- JSON 弹窗 -->
<GlassDialog v-model="jsonModal.show" :max-width="800"
  icon="mdi-code-block-braces" :title="jsonModal.title" cancel-text="关闭"
>
  <pre class="code-block code-block--flat">{{ JSON.stringify(jsonModal.data, null, 2) }}</pre>
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-copy" @click="copyJsonData">复制 JSON 数据</v-btn>
  </template>
</GlassDialog>
  </v-container>
</template>
