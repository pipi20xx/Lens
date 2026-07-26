<script setup lang="ts">
/**
 * 容器终端对话框
 *
 * 通过 WebSocket 连接后端 /api/docker/{hostId}/containers/{containerId}/exec
 * 使用 xterm.js 渲染交互式终端。
 */
import { ref, watch, onBeforeUnmount, nextTick } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

const props = defineProps<{
  modelValue: boolean
  hostId: string
  containerId: string
  containerName: string
  command?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [val: boolean] }>()

const terminalRef = ref<HTMLElement | null>(null)
let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null
let connectTimeout: ReturnType<typeof setTimeout> | null = null

function initTerminal() {
  if (!terminalRef.value) return
  if (term) return // 防止重复初始化

  term = new Terminal({
    cursorBlink: true,
    fontFamily: '"Fira Code", "JetBrains Mono", "Cascadia Code", monospace',
    fontSize: 14,
    lineHeight: 1.2,
    convertEol: true,
    theme: { background: '#1a1a2e', foreground: '#e0e0e0' },
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)
  term.open(terminalRef.value)
  // 等待 DOM 布局完成再 fit
  requestAnimationFrame(() => fitAddon?.fit())
  term.focus()

  term.writeln('\x1b[1;32mConnecting to container terminal...\x1b[0m')

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  const shell = props.command || '/bin/bash'
  const wsUrl = `${protocol}//${host}/api/docker/${props.hostId}/containers/${props.containerId}/exec?command=${encodeURIComponent(shell)}`

  try {
    ws = new WebSocket(wsUrl)
  } catch (e) {
    term?.writeln('\r\n\x1b[1;31mFailed to create WebSocket connection.\x1b[0m')
    return
  }

  // 连接超时检测
  connectTimeout = setTimeout(() => {
    if (ws && ws.readyState === WebSocket.CONNECTING) {
      term?.writeln('\r\n\x1b[1;31m连接超时，请检查网络或后端状态。\x1b[0m')
      term?.writeln(`\x1b[2mWebSocket URL: ${wsUrl}\x1b[0m`)
      term?.writeln('\x1b[2m可能原因: 容器未运行 / ID 不正确 / 网络不通\x1b[0m')
      ws.close()
    }
  }, 8000)

  ws.onopen = () => {
    if (connectTimeout) { clearTimeout(connectTimeout); connectTimeout = null }
    term?.writeln('\x1b[1;32mConnected.\x1b[0m')
    term?.onData((data) => {
      if (ws?.readyState === WebSocket.OPEN) ws.send(data)
    })
  }

  ws.onmessage = (event) => {
    if (event.data instanceof Blob) {
      const reader = new FileReader()
      reader.onload = () => {
        term?.write(new Uint8Array(reader.result as ArrayBuffer))
      }
      reader.readAsArrayBuffer(event.data)
    } else {
      term?.write(event.data)
    }
  }

  ws.onclose = (event) => {
    if (connectTimeout) { clearTimeout(connectTimeout); connectTimeout = null }
    if (event.code === 1008) {
      term?.writeln('\r\n\x1b[1;31mAuthentication failed. Please refresh the page and try again.\x1b[0m')
    } else {
      term?.writeln('\r\n\x1b[1;33mTerminal session closed.\x1b[0m')
    }
  }

  ws.onerror = () => {
    if (connectTimeout) { clearTimeout(connectTimeout); connectTimeout = null }
    term?.writeln('\r\n\x1b[1;31mConnection error.\x1b[0m')
  }

  window.addEventListener('resize', handleResize)
}

function handleResize() {
  fitAddon?.fit()
}

function destroyTerminal() {
  if (connectTimeout) { clearTimeout(connectTimeout); connectTimeout = null }
  window.removeEventListener('resize', handleResize)
  if (ws) {
    ws.onclose = null
    ws.onerror = null
    ws.close()
    ws = null
  }
  if (term) {
    term.dispose()
    term = null
  }
  fitAddon = null
}

watch(
  () => props.modelValue,
  async (val) => {
    if (val) {
      await nextTick()
      // 等待 dialog 过渡动画完成
      setTimeout(initTerminal, 200)
    } else {
      destroyTerminal()
    }
  }
)

onBeforeUnmount(destroyTerminal)

function close() {
  emit('update:modelValue', false)
}
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    max-width="1000"
    :scrim="true"
    transition="dialog-bottom-transition"
  >
    <v-card rounded="xl" class="d-flex flex-column" style="overflow:hidden">
      <!-- 标题栏 -->
      <div class="d-flex align-center px-4 py-3">
        <v-icon start color="primary">mdi-console</v-icon>
        <span class="text-subtitle-1 font-weight-bold">容器终端: {{ containerName }}</span>
        <v-spacer />
        <v-chip size="x-small" variant="tonal" color="success">{{ command || '/bin/bash' }}</v-chip>
        <v-btn icon="mdi-close" variant="text" size="small" class="ml-2" @click="close" />
      </div>
      <v-divider />

      <!-- 终端区域 -->
      <div ref="terminalRef" class="docker-terminal-container" />

      <v-divider />

      <!-- 底部栏 -->
      <div class="d-flex align-center justify-space-between px-4 py-2">
        <span class="text-caption text-medium-emphasis">
          <v-icon size="14" start>mdi-information-outline</v-icon>
          输入 <code>exit</code> 或关闭窗口退出终端
        </span>
        <v-btn variant="tonal" color="grey" size="small" prepend-icon="mdi-close" @click="close">关闭终端</v-btn>
      </div>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.docker-terminal-container {
  height: 520px;
  min-height: 400px;
  background: #1a1a2e;
  padding: 8px;
  overflow: hidden;
}

:deep(.xterm) {
  height: 100%;
}

:deep(.xterm-viewport) {
  background-color: #1a1a2e !important;
  overflow-y: auto !important;
}

:deep(.xterm-screen) {
  background: #1a1a2e;
}

:deep(.xterm .xterm-rows) {
  color: #e0e0e0 !important;
}
</style>
