<template>
  <div class="mobile-tmdb-reverse-lookup">
    <div class="page-header">
      <h1 class="page-title">剧集 TMDB 反查</h1>
      <p class="page-desc">根据 Emby 单集 ID 追溯所属剧集的 TMDB ID</p>
    </div>

    <n-card class="search-card" :bordered="false">
      <n-space vertical>
        <n-input 
          v-model:value="episodeId" 
          placeholder="输入 Emby 单集 ID (例如: 108)"
          size="large"
          @keyup.enter="handleLookup"
        />
        <n-button 
          type="primary" 
          size="large" 
          block 
          :loading="loading"
          @click="handleLookup"
        >
          执行反查
        </n-button>
      </n-space>
    </n-card>

    <!-- 结果展示 -->
    <n-card v-if="result" class="result-card" :bordered="false">
      <div class="result-header">
        <n-tag type="success" size="large" round>溯源成功</n-tag>
      </div>
      
      <div class="result-content">
        <div class="result-row">
          <span class="result-label">剧集名称</span>
          <span class="result-value">{{ result.series_name }}</span>
        </div>
        <div class="result-row">
          <span class="result-label">TMDB ID</span>
          <n-tag type="success" size="small" round>{{ result.tmdb_id }}</n-tag>
        </div>
        <div class="result-row">
          <span class="result-label">剧集 ID</span>
          <span class="result-value">{{ result.series_id }}</span>
        </div>
        <div class="result-row">
          <span class="result-label">媒体类型</span>
          <span class="result-value">{{ result.item_type }}</span>
        </div>
      </div>

      <n-button block secondary @click="copyTmdb">
        复制 TMDB ID
      </n-button>
    </n-card>

    <n-empty v-else description="请输入单集 ID 并开始追溯" />

    <!-- 说明 -->
    <n-card class="info-card" :bordered="false" title="使用说明">
      <n-space vertical>
        <n-alert type="info" :bordered="false">
          单集 ID 是指具体某一集在 Emby 中的唯一标识
        </n-alert>
        <n-alert type="warning" :bordered="false">
          此工具会自动向上查找其所属的 Series (剧集) 本身
        </n-alert>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  useMessage, NCard, NInput, NButton, NTag, 
  NEmpty, NAlert, NIcon, NSpace
} from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const episodeId = ref('')
const loading = ref(false)
const result = ref<any>(null)

const handleLookup = async () => {
  if (!episodeId.value) {
    message.warning('请输入单集 ID')
    return
  }
  loading.value = true
  result.value = null
  try {
    const res = await axios.get('/api/tmdb/reverse-tmdb', {
      params: { episode_id: episodeId.value }
    })
    result.value = res.data
    message.success('溯源成功！')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '溯源失败')
  } finally {
    loading.value = false
  }
}

const copyTmdb = () => {
  if (!result.value) return
  navigator.clipboard.writeText(result.value.tmdb_id).then(() => {
    message.success('TMDB ID 已复制')
  }).catch(() => {
    message.error('复制失败')
  })
}
</script>

<style scoped>
.mobile-tmdb-reverse-lookup {
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

.search-card,
.result-card,
.info-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.result-header {
  text-align: center;
  margin-bottom: 16px;
}

.result-content {
  margin-bottom: 16px;
}

.result-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.result-row:last-child {
  border-bottom: none;
}

.result-label {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.6;
}

.result-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
}
</style>
