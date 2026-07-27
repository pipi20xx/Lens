<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { webhookApi } from '@/api/webhook'
import { useNotification, useClipboard } from '@/composables'
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()
const { copy: copyToClipboard } = useClipboard()
const { confirm } = useConfirm()

const logs = ref<any[]>([])
const loading = ref(false)

// ========== Webhook URL ==========
const webhookBaseUrl = computed(() => {
  return `${window.location.origin}/api/webhook/receive`
})

function copyUrl() {
  copyToClipboard(webhookBaseUrl.value, 'Webhook URL 已复制到剪贴板')
}

// ========== 日志管理 ==========
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

// ========== 原始 JSON 弹窗 ==========
const detailDialog = ref(false)
const selectedLog = ref<any>(null)

function showDetail(log: any) {
  selectedLog.value = log
  detailDialog.value = true
}

function copyPayload() {
  if (!selectedLog.value) return
  const text = formatJson(selectedLog.value.payload || selectedLog.value)
  copyToClipboard(text, '原始 JSON 已复制到剪贴板')
}

// ========== 工具函数 ==========
function formatJson(data: any) {
  try {
    return JSON.stringify(typeof data === 'string' ? JSON.parse(data) : data, null, 2)
  } catch {
    return String(data)
  }
}

function formatTime(dt: string) {
  if (!dt) return ''
  try {
    const d = new Date(dt)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return dt
  }
}

/** 从 payload 中提取摘要信息 */
function getSummary(log: any) {
  const p = log.payload || {}
  return {
    event: p.Event || log.event_type || '未知事件',
    item: p.Item?.Name || 'N/A',
    user: p.User?.Name || 'N/A',
  }
}

/** 事件类型对应颜色 */
const EVENT_COLORS: Record<string, string> = {
  'item.added': 'success',
  'ItemAdded': 'success',
  'library.new': 'success',
  'LibraryChanged': 'info',
  'playback.start': 'primary',
  'playback.stop': 'warning',
  'playback.progress': 'info',
}
function getEventColor(event: string) {
  return EVENT_COLORS[event] || 'secondary'
}

onMounted(loadLogs)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-webhook</v-icon>
      Webhook 接收器
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">纯接收端点，用于查看 Webhook 发送方的实际请求内容与结构，方便调试。</p>

    <!-- Webhook URL 展示 -->
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start>mdi-link-variant</v-icon>
        接收端点
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-4">
        <div class="d-flex ga-3 align-center mb-3">
          <v-text-field :model-value="webhookBaseUrl" label="Webhook URL" variant="outlined" density="compact" readonly hide-details />
          <v-btn variant="tonal" color="info" size="small" prepend-icon="mdi-content-copy" @click="copyUrl">复制 URL</v-btn>
        </div>
        <v-alert type="info" variant="tonal" density="compact">
          在 Emby 后台添加此 URL，选择 <strong>application/json</strong> 类型，并勾选需要监听的事件。URL 后可追加路径后缀以区分不同来源，如 <code>/api/webhook/receive/emby</code>。
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- 日志列表 -->
    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start>mdi-history</v-icon>
        接收日志
        <span v-if="logs.length" class="text-caption text-medium-emphasis ml-2">({{ logs.length }} 条)</span>
        <v-spacer />
        <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="loadLogs" :loading="loading" class="mr-2">刷新</v-btn>
        <v-btn prepend-icon="mdi-delete-sweep-outline" variant="tonal" size="small" color="error" @click="clearLogs">清空日志</v-btn>
      </v-card-title>
      <v-divider />

      <v-progress-linear v-if="loading" indeterminate color="primary" class="ma-4" />

      <div v-else-if="logs.length === 0" class="text-center py-12 text-medium-emphasis">
        <v-icon size="64" color="grey" class="mb-4">mdi-webhook</v-icon>
        <div>暂无 Webhook 日志</div>
        <div class="text-caption mt-2">当 Emby 发送 Webhook 事件后，日志将在此显示</div>
      </div>

      <!-- 卡片式日志列表 -->
      <div v-else class="d-flex flex-column ga-2 pa-4">
        <v-card
          v-for="(log, idx) in logs"
          :key="idx"
          variant="outlined"
          rounded="lg"
        >
          <div class="d-flex align-center flex-wrap pa-3">
            <!-- 事件类型标签 -->
            <v-chip
              size="small"
              variant="tonal"
              :color="getEventColor(getSummary(log).event)"
              class="mr-3 font-weight-medium"
            >
              <v-icon start size="14">mdi-bell-ring-outline</v-icon>
              {{ getSummary(log).event }}
            </v-chip>

            <!-- 摘要信息 -->
            <div class="d-flex align-center ga-4 flex-wrap text-body-2 text-medium-emphasis">
              <span v-if="getSummary(log).item !== 'N/A'" class="d-flex align-center">
                <v-icon size="14" class="mr-1">mdi-movie-open-outline</v-icon>
                {{ getSummary(log).item }}
              </span>
              <span v-if="getSummary(log).user !== 'N/A'" class="d-flex align-center">
                <v-icon size="14" class="mr-1">mdi-account-outline</v-icon>
                {{ getSummary(log).user }}
              </span>
              <span v-if="log.source_ip" class="d-flex align-center">
                <v-icon size="14" class="mr-1">mdi-ip-network</v-icon>
                {{ log.source_ip }}
              </span>
              <span class="d-flex align-center">
                <v-icon size="14" class="mr-1">mdi-clock-outline</v-icon>
                {{ formatTime(log.created_at) }}
              </span>
            </div>

            <v-spacer />

            <!-- 查看原始 JSON 按钮 -->
            <v-btn
              size="small"
              variant="tonal"
              color="primary"
              prepend-icon="mdi-code-block-braces"
              @click="showDetail(log)"
            >
              查看原始信息
            </v-btn>
          </div>
        </v-card>
      </div>
    </v-card>

    <!-- 原始 JSON 弹窗 -->
    <GlassDialog
      v-model="detailDialog"
      :max-width="800"
      :title="selectedLog ? `原始 JSON - ${getSummary(selectedLog).event}` : '原始 JSON'"
      icon="mdi-code-block-braces"
    >
      <pre v-if="selectedLog" class="code-block code-block--flat">{{ formatJson(selectedLog.payload || selectedLog) }}</pre>

      <template #actions>
        <v-btn variant="tonal" color="info" prepend-icon="mdi-content-copy" @click="copyPayload">
          复制 JSON
        </v-btn>
      </template>
    </GlassDialog>
  </v-container>
</template>

