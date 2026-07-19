<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { 
  NCard, NSpace, NButton, NIcon, NTag, NSwitch, NVirtualList, NSelect, NSpin, NText
} from 'naive-ui'
import axios from 'axios'
import { CodeBracketIcon } from '@heroicons/vue/24/outline'
const props = defineProps({
  // 组件放置在 NModal 里
})

const emit = defineEmits(['close'])

// ... logic ...

const openFullLog = () => {
  if (selectedDate.value) {
    window.open(`/api/system/logs/export/${selectedDate.value}`, '_blank')
  } else {
    window.open(`/api/system/logs/raw?type=monitor`, '_blank')
  }
}

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_BASE = `${WS_PROTOCOL}//${window.location.host}`

interface LogItem {
  id: number
  content: string
}

const consoleLogs = ref<LogItem[]>([])
const isPaused = ref(false)
const autoScroll = ref(true)
const virtualListInst = ref<any>(null)
const socketStatus = ref<'connected' | 'disconnected' | 'connecting'>('disconnected')
const logDates = ref<string[]>([])
const selectedDate = ref<string | null>(null) // null 表示实时日志流
const isLoadingHistory = ref(false)

let logCounter = 0
let socket: WebSocket | null = null
let retryTimer: any = null

const fetchLogDates = async () => {
  try {
    const res = await axios.get('/api/system/logs/dates')
    logDates.value = res.data
  } catch (e) { console.error('获取日志日期失败') }
}

const fetchHistoryLog = async (date: string) => {
  isLoadingHistory.value = true
  consoleLogs.value = []
  try {
    const res = await axios.get(`/api/system/logs/content/${date}`)
    const lines = res.data.content.split('\n').filter((l: string) => l.trim())
    // 历史日志按倒序排（最新在上）
    lines.reverse()
    consoleLogs.value = lines.map((line: string, index: number) => ({
      id: index,
      content: line
    }))
    logCounter = lines.length
    nextTick(scrollToTop)
  } catch (e) {
    appendLog(`>>> 无法加载 ${date} 的日志文件 <<<`)
  } finally {
    isLoadingHistory.value = false
  }
}

const handleDateChange = (val: string | null) => {
  if (val === null) {
    clearConsole()
    // 重新连接以获取最新的回填日志
    if (socket) {
      socket.close()
      socket = null
    }
    connectWebSocket()
    isPaused.value = false
  } else {
    isPaused.value = true // 查看历史时自动暂停实时流
    fetchHistoryLog(val)
  }
}

const connectWebSocket = () => {
  if (socket) return
  socketStatus.value = 'connecting'
  const token = localStorage.getItem('lens_access_token') || ''
  const wsUrl = `${WS_BASE}/ws/system/logs?token=${encodeURIComponent(token)}`
  socket = new WebSocket(wsUrl)

  socket.onopen = () => {
    socketStatus.value = 'connected'
    appendLog(">>> 系统实时控制台连接成功 <<<")
    if (retryTimer) { clearTimeout(retryTimer); retryTimer = null; }
  }

  socket.onmessage = (event) => {
    if (isPaused.value) return
    appendLog(event.data)
  }

  socket.onclose = () => {
    socket = null
    socketStatus.value = 'disconnected'
    appendLog(">>> 连接断开，正在尝试重连... <<<")
    retryTimer = setTimeout(connectWebSocket, 3000)
  }
}

const appendLog = (content: string) => {
  if (consoleLogs.value.length > 10000) {
    consoleLogs.value = consoleLogs.value.slice(0, 8000)
  }
  // 核心改动：使用 unshift 将新日志放入数组头部 (最新在上)
  consoleLogs.value.unshift({
    id: logCounter++,
    content: content
  })
  if (autoScroll.value) {
    nextTick(scrollToTop)
  }
}

const scrollToTop = () => {
  virtualListInst.value?.scrollTo({ position: 'top' })
}

const scrollToBottom = () => {
  virtualListInst.value?.scrollTo({ position: 'bottom' })
}

const clearConsole = () => {
  consoleLogs.value = []
  logCounter = 0
}

onMounted(() => {
  connectWebSocket()
  fetchLogDates()
})

onUnmounted(() => {
  if (socket) { socket.close(); socket = null; }
  if (retryTimer) clearTimeout(retryTimer)
})
</script>

<template>
  <div class="console-wrapper">
    <div class="console-header">
      <n-space align="center" :size="12">
        <n-icon size="20" color="var(--primary-color)"><CodeBracketIcon /></n-icon>
        <span class="header-title">{{ selectedDate ? `历史记录: ${selectedDate}` : '实时系统日志 (Live)' }}</span>
        <n-tag v-if="!selectedDate" :type="socketStatus === 'connected' ? 'success' : 'error'" size="tiny" round>
          <template #icon>
            <div v-if="socketStatus === 'connected'" class="pulse-dot"></div>
          </template>
          {{ socketStatus === 'connected' ? '就绪' : '断开' }}
        </n-tag>
      </n-space>

      <n-space align="center">
        <n-select 
          v-model:value="selectedDate"
          placeholder="历史日志回溯"
          size="tiny"
          style="width: 160px;"
          :options="[
            { label: '🔴 实时日志流', value: null },
            ...logDates.map(d => ({ label: `📅 ${d}`, value: d }))
          ]"
          @update:value="handleDateChange"
        />
        <n-button size="tiny" @click="autoScroll = !autoScroll" :type="autoScroll ? 'primary' : 'default'" secondary>
          {{ autoScroll ? '跟随' : '自由' }}
        </n-button>
        <n-button v-if="!selectedDate" size="tiny" @click="isPaused = !isPaused" :type="isPaused ? 'warning' : 'default'" secondary>
          {{ isPaused ? '恢复' : '暂停' }}
        </n-button>
        <n-button size="tiny" @click="openFullLog" secondary>
          查看导出
        </n-button>
        <n-button size="tiny" @click="clearConsole" secondary>
          清空
        </n-button>
        <n-button size="tiny" @click="emit('close')" type="error" ghost>
          关闭
        </n-button>
      </n-space>
    </div>

    <div class="console-body">
      <n-spin :show="isLoadingHistory">
        <div v-if="consoleLogs.length === 0 && !isLoadingHistory" class="empty-tip">
          等待系统日志流输出...
        </div>
        <n-virtual-list
          ref="virtualListInst"
          class="log-list"
          :items="consoleLogs"
          :item-size="15"
          key-field="id"
        >
          <template #default="{ item }">
            <div class="log-line">{{ item.content }}</div>
          </template>
        </n-virtual-list>
      </n-spin>
    </div>
  </div>
</template>

<style scoped>
.console-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: var(--modal-bg-color);
  border-radius: 8px;
  overflow: hidden;
}

.console-header {
  padding: 10px 16px;
  background-color: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-weight: bold;
  font-size: 13px;
  color: var(--text-color);
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background-color: var(--primary-color);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--primary-border-color);
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% { transform: scale(0.9); opacity: 0.6; }
  50% { transform: scale(1.1); opacity: 1; }
  100% { transform: scale(0.9); opacity: 0.6; }
}

.console-body {
  flex: 1;
  background-color: rgba(0, 0, 0, 0.2);
  padding: 8px 0;
  position: relative;
}

.log-list {
  height: 100%;
}

.log-line {
  padding: 0 16px;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 20px;
  color: var(--text-color);
  opacity: 0.8;
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.empty-tip {
  position: absolute;
  top: 40%;
  width: 100%;
  text-align: center;
  color: var(--text-color);
  opacity: 0.4;
  font-style: italic;
}
</style>