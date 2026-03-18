<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">项目元数据查询</n-text></n-h2>
        <n-text depth="3">输入项目的 Emby ID，实时抓取该项目的全量元数据 JSON 包，用于调试和审计。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：主要功能区 -->
        <n-gi span="24 m:16">
          <n-space vertical size="large">
            <!-- 1. 查询表单 -->
            <n-card title="元数据即时抓取" size="small">
              <template #header-extra>
                <n-tag type="info" round quaternary size="small">Direct API</n-tag>
              </template>
              <n-input-group>
                <n-input-group-label style="width: 140px">Emby Item ID</n-input-group-label>
                <n-input v-model:value="itemId" placeholder="输入 ID，例如: 12345" @keyup.enter="fetchInfo" />
                <n-button type="primary" @click="fetchInfo" :loading="loading">
                  执行抓取
                </n-button>
              </n-input-group>
            </n-card>

            <!-- 2. 结果展示 -->
            <n-card v-if="itemData" title="抓取结果 (Raw Metadata JSON)" size="small" segmented>
              <template #header-extra>
                <n-button secondary size="tiny" @click="copyData">
                  复制数据
                </n-button>
              </template>
              <div class="json-viewer">
                <n-code :code="JSON.stringify(itemData, null, 2)" language="json" word-wrap />
              </div>
            </n-card>

            <n-empty v-else description="暂无数据，请输入 ID 并点击抓取" />
          </n-space>
        </n-gi>

        <!-- 右侧：辅助信息区 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <n-card title="使用说明" size="small" segmented>
              <n-text depth="3">
                1. 在 Emby Web 端的地址栏中可以找到项目 ID。<br/>
                2. 此工具对于排查元数据同步问题非常有用。<br/>
                3. 如果 ID 正确但无法抓取，请检查服务器连接状态。
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { 
  useMessage, NSpace, NH2, NText, NCard, NInput, NButton, NInputGroup, 
  NInputGroupLabel, NCode, NTag, NEmpty, NGrid, NGi, NIcon
} from 'naive-ui'
import { 
  ScienceOutlined as LabIcon,
  ContentCopyOutlined as CopyIcon
} from '@vicons/material'
import { copyElementContent } from '@/utils/clipboard'

// 导入提取的逻辑
import { useEmbyItem } from './emby/hooks/useEmbyItem'

const message = useMessage()
const { itemId, itemData, loading, fetchInfo } = useEmbyItem()

const copyData = () => {
  const selector = document.querySelector('.json-viewer pre') ? '.json-viewer pre' : '.json-viewer'
  if (copyElementContent(selector)) {
    message.success('JSON 已复制到剪贴板')
  } else {
    message.error('复制失败')
  }
}
</script>

<style scoped>
.json-viewer {
  background-color: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}
</style>