<script setup lang="ts">
import { ref } from 'vue'
import { embyApi } from '@/api/emby'
import { useNotification, useClipboard } from '@/composables'

const { success, error: showError } = useNotification()
const { copy: copyToClipboard } = useClipboard()

const itemId = ref('')
const itemData = ref<any>(null)
const loading = ref(false)

async function fetchInfo() {
  if (!itemId.value.trim()) {
    showError('请输入项目 ID')
    return
  }
  try {
    loading.value = true
    itemData.value = null
    const res = await embyApi.getItemInfo({ item_id: itemId.value.trim() })
    itemData.value = res
    success('元数据抓取成功')
  } catch {
    showError('抓取失败，请确认 ID 是否正确')
  } finally {
    loading.value = false
  }
}

function copyData() {
  if (!itemData.value) return
  copyToClipboard(JSON.stringify(itemData.value, null, 2), 'JSON 已复制到剪贴板')
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-magnify</v-icon>
      Emby 项目元数据查询
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">输入项目的 Emby ID，实时抓取该项目的全量元数据 JSON 包，用于调试和审计。</p>

    <v-row>
      <!-- 左侧：主要功能区 -->
      <v-col cols="12" md="7">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon start>mdi-code-block-braces</v-icon>
            元数据即时抓取
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div class="d-flex align-center ga-3">
              <v-text-field v-model="itemId" prepend-inner-icon="mdi-identifier" placeholder="输入 Emby Item ID，例如: 12345"
                variant="outlined" density="compact" hide-details clearable style="max-width:320px"
                @keydown.enter="fetchInfo" />
              <v-btn color="primary" variant="flat" prepend-icon="mdi-download" @click="fetchInfo" :loading="loading">执行抓取</v-btn>
            </div>
          </v-card-text>
        </v-card>

        <v-card v-if="itemData" class="liquid-glass-card" rounded="xl">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon start>mdi-code-braces</v-icon>
            抓取结果 (Raw Metadata JSON)
            <v-spacer />
            <v-btn size="x-small" variant="tonal" color="info" @click="copyData" prepend-icon="mdi-content-copy">复制数据</v-btn>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div class="code-block">
              <pre>{{ JSON.stringify(itemData, null, 2) }}</pre>
            </div>
          </v-card-text>
        </v-card>

        <div v-else class="text-center py-12 text-medium-emphasis">
          <v-icon size="64" color="grey" class="mb-4">mdi-code-block-braces</v-icon>
          <div>暂无数据，请输入 ID 并点击抓取</div>
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
            <p class="mb-2">1. 在 Emby Web 端的地址栏中可以找到项目 ID。</p>
            <p class="mb-2">2. 此工具对于排查元数据同步问题非常有用。</p>
            <p>3. 如果 ID 正确但无法抓取，请检查服务器连接状态。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

