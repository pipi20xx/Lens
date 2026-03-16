<template>
  <div class="mobile-emby-item-query">
    <div class="page-header">
      <h1 class="page-title">项目元数据查询</h1>
      <p class="page-desc">输入 Emby ID 实时抓取全量元数据</p>
    </div>

    <n-card class="search-card" :bordered="false">
      <n-space vertical>
        <n-input 
          v-model:value="itemId" 
          placeholder="输入 Emby Item ID (例如: 12345)"
          size="large"
          @keyup.enter="fetchInfo"
        />
        <n-button 
          type="primary" 
          size="large" 
          block 
          :loading="loading"
          @click="fetchInfo"
        >
          执行抓取
        </n-button>
      </n-space>
    </n-card>

    <!-- 结果展示 -->
    <n-card v-if="itemData" class="result-card" :bordered="false">
      <template #header>
        <div class="result-header">
          <span class="result-title">抓取结果</span>
          <n-button secondary size="small" @click="copyData">
            复制
          </n-button>
        </div>
      </template>
      <div class="json-viewer">
        <n-code :code="JSON.stringify(itemData, null, 2)" language="json" word-wrap />
      </div>
    </n-card>

    <n-empty v-else description="暂无数据，请输入 ID 并点击抓取" />

    <!-- 说明 -->
    <n-card class="info-card" :bordered="false" title="使用说明">
      <n-space vertical>
        <n-alert type="info" :bordered="false">
          在 Emby Web 端的地址栏中可以找到项目 ID
        </n-alert>
        <n-alert type="warning" :bordered="false">
          此工具对于排查元数据同步问题非常有用
        </n-alert>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  useMessage, NCard, NInput, NButton, NCode, 
  NEmpty, NAlert, NIcon, NSpace
} from 'naive-ui'
import { embyApi } from '@/api/emby'

const message = useMessage()
const itemId = ref('')
const itemData = ref<any>(null)
const loading = ref(false)

const fetchInfo = async () => {
  if (!itemId.value) {
    message.warning('请输入 Item ID')
    return
  }
  loading.value = true
  itemData.value = null
  try {
    const res = await embyApi.getItemInfo(itemId.value)
    itemData.value = res.data
    message.success('元数据抓取成功')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '抓取失败，请确认 ID 是否正确')
  } finally {
    loading.value = false
  }
}

const copyData = () => {
  if (!itemData.value) return
  const text = JSON.stringify(itemData.value, null, 2)
  navigator.clipboard.writeText(text).then(() => {
    message.success('JSON 已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}
</script>

<style scoped>
.mobile-emby-item-query {
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
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.result-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
}

.json-viewer {
  background: var(--app-bg-color);
  padding: 12px;
  border-radius: 8px;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
