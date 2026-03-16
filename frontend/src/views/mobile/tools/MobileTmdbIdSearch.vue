<template>
  <div class="mobile-tmdb-id-search">
    <div class="page-header">
      <h1 class="page-title">TMDB ID 深度搜索</h1>
      <p class="page-desc">在 Emby 库中递归检索 TMDB ID 匹配的项目</p>
    </div>

    <n-card class="search-card" :bordered="false">
      <n-space vertical>
        <n-input 
          v-model:value="form.tmdb_id" 
          placeholder="输入 TMDB ID (如: 94359)"
          size="large"
          @keyup.enter="handleSearch"
        />
        <n-checkbox-group v-model:value="searchTypes">
          <n-space>
            <n-checkbox value="movies">电影</n-checkbox>
            <n-checkbox value="series">剧集</n-checkbox>
          </n-space>
        </n-checkbox-group>
        <n-button 
          type="primary" 
          size="large" 
          block 
          :loading="loading"
          @click="handleSearch"
        >
          执行搜索
        </n-button>
      </n-space>
    </n-card>

    <!-- 结果列表 -->
    <div v-if="results.length > 0" class="results-section">
      <n-divider>搜索结果 ({{ results.length }})</n-divider>
      <n-collapse>
        <n-collapse-item v-for="item in results" :key="item.Id" :name="item.Id">
          <template #header>
            <div class="result-header">
              <span class="result-name">{{ item.Name }}</span>
              <n-space size="small">
                <n-tag size="tiny" type="primary">{{ item.ProductionYear }}</n-tag>
                <n-tag size="tiny" :type="item.Type === 'Series' ? 'info' : 'success'">{{ item.Type }}</n-tag>
              </n-space>
            </div>
          </template>

          <n-card size="small" :bordered="false" class="detail-card">
            <div class="detail-row">
              <span class="detail-label">Emby ID</span>
              <span class="detail-value">{{ item.Id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">路径</span>
              <span class="detail-value path">{{ item.Path }}</span>
            </div>
            <div v-if="item.Overview" class="overview-box">
              {{ item.Overview }}
            </div>

            <!-- 季与集 -->
            <div v-if="item.Seasons?.length" class="seasons-section">
              <n-divider>季与集</n-divider>
              <n-collapse>
                <n-collapse-item v-for="season in item.Seasons" :key="season.Id" :name="season.Id">
                  <template #header>
                    <div class="season-header">
                      <span>{{ season.Name }}</span>
                      <n-button secondary circle size="tiny" @click.stop="showJson(season)">
                        </n-button>
                    </div>
                  </template>
                  <div class="episodes-list">
                    <div v-for="ep in season.Episodes" :key="ep.Id" class="episode-item">
                      <div class="episode-header">
                        <span class="episode-name">EP {{ ep.IndexNumber }} - {{ ep.Name }}</span>
                        <n-button secondary circle size="tiny" @click.stop="showJson(ep)">
                          </n-button>
                      </div>
                      <div class="episode-meta">
                        <n-tag v-if="ep.PremiereDate" size="tiny">{{ ep.PremiereDate?.split('T')[0] }}</n-tag>
                        <n-tag v-if="ep.CommunityRating" size="tiny" type="warning">⭐ {{ ep.CommunityRating }}</n-tag>
                      </div>
                    </div>
                  </div>
                </n-collapse-item>
              </n-collapse>
            </div>

            <n-button block secondary type="primary" @click="showJson(item)" style="margin-top: 12px">
              查看 JSON
            </n-button>
          </n-card>
        </n-collapse-item>
      </n-collapse>
    </div>

    <n-empty v-else-if="searched && !loading" description="未找到匹配项目" />

    <!-- JSON 弹窗 -->
    <n-modal v-model:show="jsonModal.show" preset="card" style="width: 90vw; max-width: 600px" title="元数据 JSON">
      <div class="json-wrapper">
        <n-code :code="JSON.stringify(jsonModal.data, null, 2)" language="json" word-wrap />
      </div>
      <template #footer>
        <n-button block type="primary" secondary @click="copyRawJson">
          复制数据
        </n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { 
  useMessage, NCard, NInput, NButton, NCheckboxGroup, NCheckbox, 
  NTag, NEmpty, NCollapse, NCollapseItem, NDivider, NCode, NModal, NIcon, NSpace
} from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const loading = ref(false)
const searched = ref(false)
const results = ref<any[]>([])
const searchTypes = ref(['movies', 'series'])
const form = reactive({ tmdb_id: '' })
const jsonModal = reactive({ show: false, data: {} as any })

const showJson = (item: any) => { jsonModal.data = item; jsonModal.show = true; }
const copyRawJson = () => { 
  const text = JSON.stringify(jsonModal.data, null, 2);
  navigator.clipboard.writeText(text).then(() => {
    message.success('已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}

const handleSearch = async () => {
  if (!form.tmdb_id) return
  loading.value = true; searched.value = true; results.value = []
  try {
    const res = await axios.post('/api/tmdb-search/search-by-id', {
      tmdb_id: form.tmdb_id,
      search_movies: searchTypes.value.includes('movies'),
      search_series: searchTypes.value.includes('series')
    })
    results.value = res.data.results
    if (results.value.length === 0) {
      message.info('未找到匹配项目')
    }
  } catch (e) {
    message.error('搜索失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.mobile-tmdb-id-search {
  padding: 16px;
  padding-bottom: 32px;
  background: var(--app-bg-color);
  min-height: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color);
  margin: 0 0 8px 0;
}

.page-desc {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.search-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.results-section {
  margin-top: 16px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.result-name {
  font-weight: 500;
  color: var(--text-color);
  font-size: 15px;
}

.detail-card {
  background: var(--app-bg-color);
  border-radius: 12px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
}

.detail-value {
  font-size: 13px;
  color: var(--text-color);
}

.detail-value.path {
  max-width: 60%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.overview-box {
  background: var(--card-bg-color);
  padding: 12px;
  border-radius: 8px;
  margin: 12px 0;
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.8;
  line-height: 1.6;
}

.seasons-section {
  margin-top: 16px;
}

.season-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 1;
  padding-right: 8px;
}

.episodes-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.episode-item {
  background: var(--card-bg-color);
  border-radius: 8px;
  padding: 10px;
}

.episode-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.episode-name {
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
}

.json-wrapper {
  background: var(--app-bg-color);
  padding: 12px;
  border-radius: 8px;
  max-height: 50vh;
  overflow-y: auto;
}
</style>
