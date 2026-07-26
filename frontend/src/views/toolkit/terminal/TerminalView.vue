<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { terminalApi } from '@/api/terminal'
import { useNotification } from '@/composables'

const { success, error: showError } = useNotification()

// ========== 主机与命令 ==========
const hosts = ref<any[]>([])
const selectedHostId = ref<string | null>(null)
const commands = ref<any[]>([])
const loading = ref(false)

async function loadHosts() {
  try {
    const data = await terminalApi.getHosts()
    hosts.value = Array.isArray(data) ? data : []
    if (hosts.value.length > 0) {
      const saved = localStorage.getItem('lens_selected_terminal_host')
      selectedHostId.value = (saved && hosts.value.some(h => h.id === saved)) ? saved : hosts.value[0].id
    }
  } catch {
    showError('加载主机列表失败')
  }
}

async function loadCommands() {
  try {
    const data = await terminalApi.getCommands()
    commands.value = Array.isArray(data) ? data : []
  } catch { /* ignore */ }
}

// ========== WebSocket 终端 ==========
const terminalOutput = ref<string[]>([])
const terminalInput = ref('')
const ws = ref<WebSocket | null>(null)
const isConnected = ref(false)
const terminalRef = ref<HTMLElement | null>(null)
const commandHistory = ref<string[]>([])
const historyIndex = ref(-1)

function getWsUrl() {
  const token = localStorage.getItem('lens_access_token')
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/terminal?token=${token}`
}

function connectTerminal() {
  if (!selectedHostId.value) {
    showError('请先选择主机')
    return
  }
  if (ws.value) {
    ws.value.close()
  }

  const token = localStorage.getItem('lens_access_token')
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${proto}//${window.location.host}/ws/terminal?token=${token}&host_id=${selectedHostId.value}`

  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    isConnected.value = true
    terminalOutput.value.push('\x1b[32m● 已连接到终端\x1b[0m\n')
  }

  ws.value.onmessage = (event) => {
    const data = event.data
    terminalOutput.value.push(data)
    nextTick(scrollToBottom)
  }

  ws.value.onclose = () => {
    isConnected.value = false
    terminalOutput.value.push('\x1b[31m● 连接已断开\x1b[0m\n')
  }

  ws.value.onerror = () => {
    isConnected.value = false
    showError('终端连接错误')
  }
}

function disconnectTerminal() {
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
}

function sendCommand() {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
    showError('终端未连接')
    return
  }
  const cmd = terminalInput.value
  if (!cmd.trim()) return

  // 记录命令历史
  commandHistory.value.unshift(cmd)
  if (commandHistory.value.length > 100) commandHistory.value.pop()
  historyIndex.value = -1

  ws.value.send(JSON.stringify({ type: 'input', data: cmd + '\n' }))
  terminalInput.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    sendCommand()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (historyIndex.value < commandHistory.value.length - 1) {
      historyIndex.value++
      terminalInput.value = commandHistory.value[historyIndex.value]
    }
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (historyIndex.value > 0) {
      historyIndex.value--
      terminalInput.value = commandHistory.value[historyIndex.value]
    } else {
      historyIndex.value = -1
      terminalInput.value = ''
    }
  }
}

function scrollToBottom() {
  if (terminalRef.value) {
    terminalRef.value.scrollTop = terminalRef.value.scrollHeight
  }
}

function clearTerminal() {
  terminalOutput.value = []
}

// ========== 快捷命令 ==========
function runQuickCommand(cmd: string) {
  if (!ws.value || ws.value.readyState !== WebSocket.OPEN) {
    showError('终端未连接')
    return
  }
  ws.value.send(JSON.stringify({ type: 'input', data: cmd + '\n' }))
}

// ========== 终端设置对话框 ==========
const showSettingsDialog = ref(false)
const terminalSettings = ref({
  font_size: 14,
  scrollback: 5000,
  shell: '/bin/bash',
})

// ========== 生命周期 ==========
onMounted(() => {
  loadHosts()
  loadCommands()
})

onUnmounted(() => {
  if (ws.value) ws.value.close()
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-console</v-icon>
      终端
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">通过 SSH 连接远程主机执行命令，支持多主机切换与实时输出。</p>

    <!-- 控制栏 -->
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <div class="d-flex align-center pa-4 ga-3 flex-wrap">
        <v-select v-model="selectedHostId" :items="hosts.map(h => ({ title: h.name, value: h.id }))"
          label="选择主机" variant="outlined" density="compact" hide-details style="max-width: 220px"
          prepend-inner-icon="mdi-server" />

        <v-btn v-if="!isConnected" color="primary" variant="flat" size="small" prepend-icon="mdi-play" @click="connectTerminal">连接</v-btn>
        <v-btn v-else color="error" variant="tonal" size="small" prepend-icon="mdi-stop" @click="disconnectTerminal">断开</v-btn>

        <v-btn variant="tonal" color="warning" size="small" @click="clearTerminal" prepend-icon="mdi-eraser">清屏</v-btn>
        <v-btn variant="tonal" color="secondary" size="small" @click="showSettingsDialog = true" prepend-icon="mdi-cog-outline">设置</v-btn>

        <v-spacer />

        <v-chip :color="isConnected ? 'success' : 'grey'" size="small" variant="tonal">
          <v-icon start size="14">{{ isConnected ? 'mdi-circle' : 'mdi-circle-outline' }}</v-icon>
          {{ isConnected ? '已连接' : '未连接' }}
        </v-chip>
      </div>
    </v-card>

    <!-- 快捷命令 -->
    <v-card v-if="commands.length" class="liquid-glass-card mb-4" rounded="xl">
      <v-card-title class="pa-4 pb-2 text-subtitle-2">
        <v-icon start size="18">mdi-lightning-bolt</v-icon>
        快捷命令
      </v-card-title>
      <v-card-text class="pa-4 pt-0">
        <div class="d-flex flex-wrap ga-2">
          <v-chip v-for="cmd in commands" :key="cmd.id || cmd.name" size="small" variant="tonal" color="primary"
            @click="runQuickCommand(cmd.command)" style="cursor:pointer">
            {{ cmd.name || cmd.command }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- 终端窗口 -->
    <v-card class="liquid-glass-card" rounded="xl" style="min-height:500px">
      <div ref="terminalRef" class="terminal-output pa-4" style="height:500px;overflow:auto;font-family:'Fira Code','JetBrains Mono',monospace;font-size:14px;background:rgba(0,0,0,0.4);border-radius:0 0 12px 12px;white-space:pre-wrap;word-break:break-all">
        <template v-if="terminalOutput.length === 0">
          <span class="text-medium-emphasis">点击"连接"按钮开始终端会话...</span>
        </template>
        <template v-for="(line, idx) in terminalOutput" :key="idx">
          <span>{{ line }}</span>
        </template>
      </div>

      <!-- 输入行 -->
      <div class="d-flex align-center pa-2" style="background:rgba(0,0,0,0.3);border-top:1px solid rgba(255,255,255,0.1)">
        <span class="text-success mr-2 font-mono" style="font-size:14px">$</span>
        <input v-model="terminalInput" @keydown="handleKeydown" :disabled="!isConnected"
          class="terminal-input flex-grow-1" placeholder="输入命令..." autocomplete="off" spellcheck="false" />
      </div>
    </v-card>

    <!-- 终端设置对话框 -->
    <v-dialog v-model="showSettingsDialog" max-width="400">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-cog-outline</v-icon>
          终端设置
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-slider v-model="terminalSettings.font_size" label="字体大小" min="10" max="24" thumb-label class="mb-3" />
          <v-text-field v-model="terminalSettings.scrollback" label="回滚行数" type="number" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="terminalSettings.shell" label="默认 Shell" variant="outlined" density="compact" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end pa-4">
          <v-btn color="primary" variant="flat" prepend-icon="mdi-check" @click="showSettingsDialog = false">确定</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>

