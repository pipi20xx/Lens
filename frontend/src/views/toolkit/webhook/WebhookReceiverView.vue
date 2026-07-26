<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { webhookApi } from '@/api/webhook'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const logs = ref<any[]>([])
const loading = ref(false)

async function loadLogs() {
  try {
    loading.value = true
    const data = await webhookApi.getLogs()
    logs.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载 Webhook 日志失败')
  } finally {
    loading.value = false
  }
}

async function clearLogs() {
  const ok = await confirm({ title: '清空日志', content: '确定要清空所有 Webhook 日志吗？', confirmColor: 'error' })
  if (!ok) return
  try {
    await webhookApi.clearLogs()
    success('日志已清空')
    loadLogs()
  } catch {
    showError('清空失败')
  }
}

function formatJson(data: any) {
  try {
    return JSON.stringify(typeof data === 'string' ? JSON.parse(data) : data, null, 2)
  } catch {
    return String(data)
  }
}

onMounted(loadLogs)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-webhook</v-icon>
      Webhook 接收器
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">管理 Webhook 接收端点，查看接收日志与请求详情。</p>

    <div class="d-flex ga-3 mb-4">
      <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" @click="loadLogs" :loading="loading">刷新</v-btn>
      <v-btn prepend-icon="mdi-delete-sweep-outline" variant="tonal" size="small" color="error" @click="clearLogs">清空日志</v-btn>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <div v-if="!loading && logs.length === 0" class="text-center py-12 text-medium-emphasis">
      <v-icon size="64" color="grey" class="mb-4">mdi-webhook</v-icon>
      <div>暂无 Webhook 日志</div>
    </div>

    <div class="d-flex flex-column ga-3">
      <v-card v-for="(log, idx) in logs" :key="idx" class="liquid-glass-card" rounded="xl">
        <v-card-title class="d-flex align-center pa-4 pb-2">
          <v-chip size="small" variant="tonal" :color="log.event_type ? 'primary' : 'grey'" class="mr-2">
            {{ log.event_type || log.EventType || '未知事件' }}
          </v-chip>
          <span class="text-caption text-medium-emphasis">{{ log.timestamp || log.received_at || '' }}</span>
        </v-card-title>
        <v-card-text class="pa-4 pt-0">
          <pre class="pa-3 rounded-lg" style="background:rgba(0,0,0,0.2);font-size:11px;font-family:monospace;max-height:200px;overflow:auto">{{ formatJson(log.data || log.payload || log) }}</pre>
        </v-card-text>
      </v-card>
    </div>
  </v-container>
</template>
