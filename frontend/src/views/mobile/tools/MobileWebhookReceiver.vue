<template>
  <div class="mobile-webhook-receiver">
    <div class="page-header">
      <h1 class="page-title">Webhook 接收器</h1>
      <p class="page-desc">管理 Webhook 端点与事件处理</p>
    </div>

    <n-card class="info-card" :bordered="false" title="接收地址">
      <n-space vertical>
        <p style="color: var(--text-color); font-size: 13px;">
          请在 Emby 管理后台 -> Webhook 中添加以下地址：
        </p>
        <code class="webhook-url">
          http://{{ currentHost }}:6565/api/webhook/receive
        </code>
        <n-button block secondary @click="copyWebhookUrl">
          <template #icon><n-icon><CopyIcon /></n-icon></template>
          复制地址
        </n-button>
      </n-space>
    </n-card>

    <n-card class="logs-card" :bordered="false" title="事件捕获日志">
      <template #header-extra>
        <n-space>
          <n-button secondary type="error" size="small" @click="handleClear">
            <template #icon><n-icon><DeleteIcon /></n-icon></template>
            清空
          </n-button>
          <n-button secondary size="small" @click="loadLogs" :loading="loading">
            <template #icon><n-icon><RefreshIcon /></n-icon></template>
            刷新
          </n-button>
        </n-space>
      </template>
      <div v-if="logs.length === 0" class="empty-state">
        <n-empty description="暂无调用日志" />
      </div>
      <div v-else class="log-list">
        <div v-for="log in logs" :key="log.id" class="log-item" @click="showJsonDetail(log.payload)">
          <div class="log-info">
            <div class="log-header">
              <n-tag type="primary" size="small" quaternary>{{ log.event_type }}</n-tag>
              <span class="log-time">{{ formatDate(log.created_at) }}</span>
            </div>
            <div class="log-ip">来源: {{ log.source_ip }}</div>
          </div>
          <n-icon class="log-arrow"><ChevronRightIcon /></n-icon>
        </div>
      </div>
    </n-card>

    <!-- JSON 详情弹窗 -->
    <n-modal v-model:show="showDetailModal" preset="card" title="Webhook 原始 JSON 载荷" style="width: 95vw; max-width: 600px">
      <div class="json-code-wrapper">
        <n-code :code="JSON.stringify(selectedPayload, null, 2)" language="json" word-wrap />
      </div>
      <template #footer>
        <n-button block type="primary" secondary @click="copyPayload">
          复制数据
        </n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, NIcon, NCode } from 'naive-ui'
import { RefreshOutlined as RefreshIcon, DeleteOutlined as DeleteIcon, ContentCopyOutlined as CopyIcon, ChevronRightOutlined as ChevronRightIcon } from '@vicons/material'
import { webhookApi } from '@/api/webhook'
import { useMessage, useDialog } from 'naive-ui'

const message = useMessage()
const dialog = useDialog()
const endpoints = ref<any[]>([])
const logs = ref<any[]>([])
const showAddModal = ref(false)
const saving = ref(false)
const loading = ref(false)
const showDetailModal = ref(false)
const selectedPayload = ref({})

const newEndpoint = ref({
  name: '',
  url: '',
  events: []
})

const eventOptions = [
  { label: '备份完成', value: 'backup_completed' },
  { label: '任务完成', value: 'task_completed' },
  { label: '系统告警', value: 'system_alert' },
  { label: '用户登录', value: 'user_login' }
]

const loadLogs = async () => {
  loading.value = true
  try {
    const res = await webhookApi.getLogs()
    logs.value = res as any || []
  } catch (e) {
    message.error('加载日志失败')
  } finally {
    loading.value = false
  }
}

const handleClear = () => {
  dialog.warning({
    title: '确认清空日志',
    content: '确定要清空所有 Webhook 日志吗？此操作无法撤销。',
    positiveText: '确认清空',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await webhookApi.clearLogs()
        message.success('日志已清空')
        loadLogs()
      } catch (e) {
        message.error('清空失败')
      }
    }
  })
}

const showJsonDetail = (payload: any) => {
  selectedPayload.value = payload
  showDetailModal.value = true
}

const copyPayload = () => {
  const text = JSON.stringify(selectedPayload.value, null, 2)
  navigator.clipboard.writeText(text)
  message.success('已复制到剪贴板')
}

const currentHost = window.location.hostname

const copyWebhookUrl = () => {
  const url = `http://${currentHost}:6565/api/webhook/receive`
  navigator.clipboard.writeText(url)
  message.success('Webhook 地址已复制')
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.mobile-webhook-receiver {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.info-card,
.logs-card {
  margin-bottom: 12px;
}

.webhook-url {
  display: block;
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
  font-size: 13px;
  color: var(--primary-color);
  word-break: break-all;
}

.empty-state {
  padding: 24px 0;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
}

.log-info {
  flex: 1;
}

.log-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.log-time {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.log-ip {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.5;
}

.log-arrow {
  color: var(--text-color);
  opacity: 0.3;
}

.json-code-wrapper {
  background: var(--app-bg-color);
  padding: 16px;
  border-radius: 8px;
  max-height: 60vh;
  overflow-y: auto;
}
</style>
