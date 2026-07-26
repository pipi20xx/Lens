<script setup lang="ts">
import { ref } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { useNotification, useClipboard } from '@/composables'

const { success, error: showError } = useNotification()
const { copy: copyToClipboard } = useClipboard()

const episodeId = ref('')
const loading = ref(false)
const result = ref<any>(null)

async function handleLookup() {
  if (!episodeId.value.trim()) {
    showError('请输入单集 ID')
    return
  }
  try {
    loading.value = true
    result.value = null
    const data = await toolkitApi.tmdb.reverseLookup(episodeId.value.trim())
    result.value = data
    success('溯源成功！')
  } catch {
    showError('反向查询失败，请确认 ID 是否正确')
  } finally {
    loading.value = false
  }
}

function copyTmdb() {
  if (!result.value?.tmdb_id) return
  copyToClipboard(String(result.value.tmdb_id), 'TMDB ID 已复制到剪贴板')
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-swap-horizontal</v-icon>
      Emby 剧集 TMDB 反查
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">根据 <strong>Emby 库内</strong>的单集 (Episode) ID 向上追溯其所属剧集并提取 TMDB 唯一标识符。</p>

    <v-row>
      <!-- 左侧：主要功能区 -->
      <v-col cols="12" md="7">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon start>mdi-arrow-top-right</v-icon>
            单集溯源 (Reverse Mapping)
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div class="d-flex align-center ga-3">
              <v-text-field v-model="episodeId" prepend-inner-icon="mdi-identifier" placeholder="输入 Episode ID (例如: 108)"
                variant="outlined" density="compact" hide-details clearable style="max-width:320px"
                @keydown.enter="handleLookup" />
              <v-btn color="primary" variant="flat" prepend-icon="mdi-magnify" @click="handleLookup" :loading="loading">执行反查</v-btn>
            </div>
          </v-card-text>
        </v-card>

        <v-card v-if="result" class="liquid-glass-card" rounded="xl">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon start>mdi-check-circle</v-icon>
            {{ result.series_name }}
            <v-spacer />
            <v-chip size="x-small" variant="tonal" color="success">已定位到上级剧集</v-chip>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-table density="compact" class="bg-transparent">
              <tbody>
                <tr><td class="font-weight-medium" style="width:160px">剧集名称</td><td>{{ result.series_name }}</td></tr>
                <tr><td class="font-weight-medium">TMDB ID</td><td><v-chip size="small" variant="tonal" color="success">{{ result.tmdb_id }}</v-chip></td></tr>
                <tr><td class="font-weight-medium">剧集 ID (SeriesId)</td><td class="font-mono">{{ result.series_id }}</td></tr>
                <tr><td class="font-weight-medium">媒体类型</td><td>{{ result.item_type }}</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
          <v-divider />
          <div class="d-flex justify-end pa-4">
            <v-btn variant="tonal" color="info" size="small" @click="copyTmdb" prepend-icon="mdi-content-copy">复制 TMDB ID</v-btn>
          </div>
        </v-card>

        <div v-else-if="!loading" class="text-center py-12 text-medium-emphasis">
          <v-icon size="64" color="grey" class="mb-4">mdi-swap-horizontal</v-icon>
          <div>请输入单集 ID 并开始追溯</div>
        </div>
      </v-col>

      <!-- 右侧：辅助信息区 -->
      <v-col cols="12" md="5">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-help-circle-outline</v-icon>
            使用说明
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p class="mb-2">1. 单集 ID 是指具体某一集在 Emby 中的唯一标识。</p>
            <p class="mb-2">2. 此工具会自动向上查找其所属的 Series (剧集) 本身。</p>
            <p>3. 最终返回该剧集在 TMDB 上的 ID，方便进行元数据修正。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
