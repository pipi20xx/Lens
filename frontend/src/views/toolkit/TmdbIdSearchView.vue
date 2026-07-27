<script setup lang="ts">
import { ref, reactive } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { useNotification, useClipboard } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()
const { copy: copyToClipboard } = useClipboard()

const loading = ref(false)
const searched = ref(false)
const results = ref<any[]>([])
const searchTypes = ref(['movies', 'series'])
const form = reactive({ tmdb_id: '' })
const jsonModal = reactive({ show: false, data: {} as any })

async function handleSearch() {
  if (!form.tmdb_id.trim()) return
  loading.value = true
  searched.value = true
  results.value = []
  try {
    const data = await toolkitApi.tmdb.searchById({
      tmdb_id: form.tmdb_id.trim(),
      search_movies: searchTypes.value.includes('movies'),
      search_series: searchTypes.value.includes('series')
    })
    results.value = Array.isArray(data?.results) ? data.results : Array.isArray(data) ? data : []
  } catch {
    showError('搜索异常')
  } finally {
    loading.value = false
  }
}

function showJson(item: any) {
  jsonModal.data = item
  jsonModal.show = true
}

function copyRawJson() {
  copyToClipboard(JSON.stringify(jsonModal.data, null, 2), '数据已复制到剪贴板')
}

function formatRuntime(ticks: number) {
  return Math.floor((ticks || 0) / 10000000 / 60)
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-identifier</v-icon>
      Emby TMDB ID 深度搜索
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">根据 TMDB ID <strong>在您的 Emby 库中</strong>递归检索匹配的项目及其所有季、集的完整元数据详情。</p>

    <v-row>
      <!-- 左侧：主要功能区 -->
      <v-col cols="12" md="7">
        <!-- 搜索配置 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-tune</v-icon>
            检索配置
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div class="d-flex align-center ga-3 mb-3">
              <v-text-field v-model="form.tmdb_id" prepend-inner-icon="mdi-identifier" placeholder="输入 TMDB ID (如: 94359)"
                variant="outlined" density="compact" hide-details clearable style="max-width:200px"
                @keydown.enter="handleSearch" />
              <v-btn color="primary" variant="flat" prepend-icon="mdi-magnify" @click="handleSearch" :loading="loading">执行搜索</v-btn>
            </div>
            <div class="d-flex align-center ga-2">
              <span class="text-body-2 text-medium-emphasis">检索范围:</span>
              <v-checkbox v-model="searchTypes" value="movies" label="电影" density="compact" hide-details />
              <v-checkbox v-model="searchTypes" value="series" label="剧集" density="compact" hide-details />
            </div>
          </v-card-text>
        </v-card>

        <!-- 结果展示区 -->
        <div v-if="results.length > 0">
          <div class="text-subtitle-2 font-weight-bold mb-3">搜索结果 ({{ results.length }})</div>
          <v-expansion-panels>
            <v-expansion-panel v-for="item in results" :key="item.Id" :value="item.Id">
              <v-expansion-panel-title>
                <div class="d-flex align-center ga-2 flex-grow-1">
                  <span class="font-weight-bold">{{ item.Name }}</span>
                  <v-chip size="x-small" variant="tonal" color="primary">{{ item.ProductionYear }}</v-chip>
                  <v-chip size="x-small" variant="tonal" :color="item.Type === 'Series' ? 'info' : 'success'">{{ item.Type }}</v-chip>
                </div>
                <template #actions>
                  <v-btn icon variant="tonal" size="small" @click.stop="showJson(item)">
                    <v-icon>mdi-code-block-braces</v-icon>
                  </v-btn>
                </template>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <!-- 基本信息 -->
                <v-table density="compact" class="bg-transparent mb-3">
                  <tbody>
                    <tr><td class="font-weight-medium" style="width:120px">名称</td><td>{{ item.Name }}</td></tr>
                    <tr><td class="font-weight-medium">类型</td><td>{{ item.Type }}</td></tr>
                    <tr><td class="font-weight-medium">Emby ID</td><td class="font-mono">{{ item.Id }}</td></tr>
                    <tr><td class="font-weight-medium">路径</td><td class="font-mono" style="font-size:11px">{{ item.Path }}</td></tr>
                    <tr>
                      <td class="font-weight-medium">提供者 ID</td>
                      <td>
                        <v-chip v-for="(val, key) in item.ProviderIds" :key="key" size="x-small" variant="tonal" color="info" class="mr-1">
                          {{ key }}: {{ val }}
                        </v-chip>
                      </td>
                    </tr>
                    <tr>
                      <td class="font-weight-medium">评分与分级</td>
                      <td>
                        <v-icon size="14" color="warning">mdi-star</v-icon> {{ item.CommunityRating || 'N/A' }}
                        <span class="text-medium-emphasis ml-2">{{ item.OfficialRating || 'NR' }}</span>
                      </td>
                    </tr>
                    <tr><td class="font-weight-medium">发行商/状态</td><td>{{ item.Studios?.[0]?.Name || 'N/A' }} | {{ item.Status || 'Ended' }}</td></tr>
                    <tr><td class="font-weight-medium">日期信息</td><td>首播: {{ item.PremiereDate?.split('T')[0] || 'N/A' }} <span v-if="item.EndDate">| 结束: {{ item.EndDate?.split('T')[0] }}</span></td></tr>
                  </tbody>
                </v-table>

                <!-- 简介 -->
                <div v-if="item.Overview" class="pa-3 mb-3 rounded" style="background:rgba(var(--v-theme-on-surface),0.03);border-left:4px solid rgb(var(--v-theme-primary))">
                  <p class="text-body-2 text-medium-emphasis mb-0">{{ item.Overview }}</p>
                </div>

                <!-- 季与集递归展开 -->
                <div v-if="item.Seasons && item.Seasons.length > 0">
                  <div class="text-subtitle-2 font-weight-bold mb-2">季与集 详细递归结构</div>
                  <v-expansion-panels variant="accordion">
                    <v-expansion-panel v-for="season in item.Seasons" :key="season.Id" :value="season.Id">
                      <v-expansion-panel-title>
                        <div class="d-flex align-center ga-2 flex-grow-1">
                          <span class="font-weight-bold">{{ season.Name }}</span>
                          <span class="text-caption text-medium-emphasis">(ID: {{ season.Id }})</span>
                        </div>
                        <template #actions>
                          <v-btn icon variant="tonal" size="x-small" @click.stop="showJson(season)">
                            <v-icon size="16">mdi-code-block-braces</v-icon>
                          </v-btn>
                        </template>
                      </v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <v-table density="compact" class="bg-transparent mb-2">
                          <tbody>
                            <tr><td class="font-weight-medium" style="width:100px">季号</td><td>{{ season.IndexNumber }}</td></tr>
                            <tr><td class="font-weight-medium">父 ID</td><td class="font-mono">{{ season.ParentId }}</td></tr>
                            <tr><td class="font-weight-medium">年份</td><td>{{ season.ProductionYear }}</td></tr>
                            <tr><td class="font-weight-medium">已观看</td><td>{{ season.UserData?.Played ? '是' : '否' }} ({{ season.UserData?.PlayCount }}次)</td></tr>
                          </tbody>
                        </v-table>

                        <!-- 集列表 -->
                        <div v-if="season.Episodes && season.Episodes.length">
                          <div class="text-caption font-weight-bold mb-1">集列表</div>
                          <div class="d-flex flex-column ga-2">
                            <v-card v-for="ep in season.Episodes" :key="ep.Id" rounded="lg" variant="tonal" class="list-card pa-3">
                              <div class="d-flex align-center ga-2">
                                <span class="font-weight-medium">EP {{ ep.IndexNumber }}</span> - {{ ep.Name }}
                                <v-spacer />
                                <v-btn icon variant="tonal" size="x-small" @click="showJson(ep)">
                                  <v-icon size="14" color="primary">mdi-code-block-braces</v-icon>
                                </v-btn>
                              </div>
                              <div class="d-flex ga-4 text-caption text-medium-emphasis mt-1">
                                <span>ID: {{ ep.Id }}</span>
                                <span>评分: {{ ep.CommunityRating || 'N/A' }}</span>
                                <span>首播: {{ ep.PremiereDate?.split('T')[0] || 'N/A' }}</span>
                                <span>时长: {{ formatRuntime(ep.RunTimeTicks) }} 分钟</span>
                              </div>
                              <p v-if="ep.Overview" class="text-caption text-medium-emphasis mt-1 mb-0 pl-3" style="border-left:2px solid rgba(var(--v-theme-primary),0.3)">{{ ep.Overview }}</p>
                            </v-card>
                          </div>
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <div v-else-if="searched && !loading" class="text-center py-8 text-medium-emphasis">未找到匹配项目</div>
        <div v-else-if="!searched" class="text-center py-12 text-medium-emphasis">
          <v-icon size="64" color="grey" class="mb-4">mdi-identifier</v-icon>
          <div>请输入 TMDB ID 并启动检索</div>
        </div>
      </v-col>

      <!-- 右侧：辅助信息区 -->
      <v-col cols="12" md="5">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-help-circle-outline</v-icon>
            工具说明
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p class="mb-2">此工具会根据您提供的 TMDB ID，在您的 Emby 媒体库中进行深度搜索。</p>
            <p class="mb-1"><strong>与普通搜索的区别：</strong></p>
            <p class="mb-1">1. 它是递归的：如果是剧集，会一并抓取所有季、集的信息。</p>
            <p class="mb-1">2. 它是精准的：直接匹配 ProviderIds 中的 TMDB 字段。</p>
            <p>3. 它包含元数据详情：方便您检查库中资料是否完整。</p>
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-lightbulb-outline</v-icon>
            检索技巧
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p class="mb-1">- 对于电影，通常只需要一个 ID。</p>
            <p class="mb-1">- 对于剧集，搜索结果会展示详细的层级结构。</p>
            <p>- 点击右侧的文档图标可以查看该项目的原始 JSON 元数据。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- JSON 弹窗 -->
    <GlassDialog v-model="jsonModal.show" :max-width="900"
      icon="mdi-code-block-braces" title="元数据原始 JSON 快照" cancel-text="关闭"
    >
      <pre class="code-block code-block--flat">{{ JSON.stringify(jsonModal.data, null, 2) }}</pre>

      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-content-copy" @click="copyRawJson">复制数据</v-btn>
      </template>
    </GlassDialog>
  </v-container>
</template>

