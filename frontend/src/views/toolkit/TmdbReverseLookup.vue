<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">剧集 TMDB ID 反向查询</n-text></n-h2>
        <n-text depth="3">根据 <b>Emby 库内</b>的单集 (Episode) ID 向上追溯其所属剧集并提取 TMDB 唯一标识符。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：主要功能区 -->
        <n-gi span="24 m:16">
          <n-space vertical size="large">
            <!-- 1. 输入表单 -->
            <n-card title="单集溯源 (Reverse Mapping)" size="small">
              <template #header-extra>
                <n-tag type="warning" round quaternary size="small">Series Lookup</n-tag>
              </template>
              <n-input-group>
                <n-input-group-label style="width: 140px">Emby 单集 ID</n-input-group-label>
                <n-input v-model:value="episodeId" placeholder="输入 Episode ID (例如: 108)" @keyup.enter="handleLookup" />
                <n-button type="primary" @click="handleLookup" :loading="loading">
                  执行反查
                </n-button>
              </n-input-group>
            </n-card>

            <!-- 2. 结果展示 -->
            <n-card v-if="result" :title="result.series_name" size="small" segmented>
              <template #header-extra>
                <n-text type="info">已定位到上级剧集</n-text>
              </template>
              <n-descriptions label-placement="left" :column="2" bordered size="small">
                <n-descriptions-item label="剧集名称">{{ result.series_name }}</n-descriptions-item>
                <n-descriptions-item label="TMDB ID">
                  <n-tag type="success" size="small" round>{{ result.tmdb_id }}</n-tag>
                </n-descriptions-item>
                <n-descriptions-item label="剧集 ID (SeriesId)">{{ result.series_id }}</n-descriptions-item>
                <n-descriptions-item label="媒体类型">{{ result.item_type }}</n-descriptions-item>
              </n-descriptions>
              <template #footer>
                <n-button secondary size="tiny" block @click="copyTmdb">
                  复制数据
                </n-button>
              </template>
            </n-card>
            <n-empty v-else description="请输入单集 ID 并开始追溯" />
          </n-space>
        </n-gi>

        <!-- 右侧：辅助信息区 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <n-card title="使用说明" size="small" segmented>
              <n-text depth="3">
                1. 单集 ID 是指具体某一集在 Emby 中的唯一标识。<br/>
                2. 此工具会自动向上查找其所属的 Series (剧集) 本身。<br/>
                3. 最终返回该剧集在 TMDB 上的 ID，方便进行元数据修正。
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  useMessage, NSpace, NH2, NText, NCard, NInput, NButton, NInputGroup, 
  NInputGroupLabel, NCode, NTag, NDescriptions, NDescriptionsItem, NGi, NGrid, NEmpty, NIcon
} from 'naive-ui'
import axios from 'axios'
import { copyText } from '@/utils/clipboard'

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
    message.error(e.response?.data?.detail || '反向查询失败')
  } finally {
    loading.value = false
  }
}

const copyTmdb = async () => {
  if (result.value) {
    if (await copyText(result.value.tmdb_id)) {
      message.info('TMDB ID 已复制')
    } else {
      message.error('复制失败')
    }
  }
}
</script>

<style scoped>
</style>