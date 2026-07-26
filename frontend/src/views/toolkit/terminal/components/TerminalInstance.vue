<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'
import { terminalApi } from '@/api/terminal'

const props = defineProps<{
  hostId: number | string
  hostName: string
  visible: boolean
}>()

const emit = defineEmits<{
  connected: []
  disconnected: []
}>()

const terminalRef = ref<HTMLElement | null>(null)
let term: Terminal | null = null
let fitAddon: FitAddon | null = null
let ws: WebSocket | null = null

function initTerminal() {
  term = new Terminal({
    cursorBlink: true,
    fontSize: 14,
    lineHeight: 1.2,
    fontFamily: '"Fira Code", "JetBrains Mono", Menlo, Monaco, "Courier New", monospace',
    convertEol: true,
    theme: {
      background: '#1a1a2e',
      foreground: '#e0e0e0',
      cursor: '#00e676',
      selectionBackground: 'rgba(0, 230, 118, 0.3)',
    },
    allowProposedApi: true,
  })

  fitAddon = new FitAddon()
  term.loadAddon(fitAddon)

  if (terminalRef.value) {
    term.open(terminalRef.value)
    fitAddon.fit()
  }

  connectWS()

  term.onData((data) => {
    if (ws?.readyState === WebSocket.OPEN) ws.send(data)
  })
}

function connectWS() {
  if (ws) {
    ws.close()
    ws = null
  }

  const wsUrl = terminalApi.getWsUrl(props.hostId)
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    emit('connected')
    term?.write(`\x1b[32m[系统] 已连接至 ${props.hostName}\x1b[0m\r\n`)
    fitAddon?.fit()
  }

  ws.onmessage = (e) => {
    term?.write(e.data)
  }

  ws.onclose = () => {
    emit('disconnected')
    term?.write('\r\n\x1b[31m[系统] 会话已断开\x1b[0m\r\n')
  }

  ws.onerror = () => {
    emit('disconnected')
  }
}

// 暴露给父组件的方法
function fit() {
  fitAddon?.fit()
}
function write(data: string) {
  term?.write(data)
}
function send(data: string) {
  if (ws?.readyState === WebSocket.OPEN) ws.send(data)
}
function focus() {
  term?.focus()
}
function clear() {
  term?.clear()
}
function reconnect() {
  if (ws) ws.close()
  term?.reset()
  connectWS()
}

defineExpose({ fit, write, send, focus, clear, reconnect })

// 当组件变为可见时，重新自适应大小
watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      setTimeout(() => {
        fitAddon?.fit()
        term?.focus()
      }, 50)
    }
  }
)

onMounted(() => {
  setTimeout(initTerminal, 100)
  window.addEventListener('resize', fit)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', fit)
  if (ws) ws.close()
  if (term) term.dispose()
})
</script>

<template>
  <div class="terminal-instance-wrapper" v-show="visible">
    <div ref="terminalRef" class="xterm-box"></div>
  </div>
</template>

<style scoped>
.terminal-instance-wrapper {
  height: 100%;
  width: 100%;
  background: #1a1a2e;
  padding: 8px;
  box-sizing: border-box;
}
.xterm-box {
  height: 100%;
  width: 100%;
}
</style>
