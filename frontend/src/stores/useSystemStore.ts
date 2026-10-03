import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ProgressData } from '@/types'

export const useSystemStore = defineStore('system', () => {
  const scanProgress = ref<ProgressData>({ status: 'idle', current: 0, total: 0, message: '' })
  const downloadProgress = ref<ProgressData>({ status: 'idle', current: 0, total: 0, message: '' })
  const isConnected = ref(false)
  // 原始日志行（未经解析），由 LogTerminal 组件负责解析 / 筛选 / 分组
  const logs = ref<string[]>([])
  const showLogModal = ref(false)

  // 登录状态 —— 从 localStorage 读取 token 判断
  // App.vue 的玻璃壁纸渲染需要此属性来决定是否加载背景层
  const isLoggedIn = ref<boolean>(
    !!(localStorage.getItem('lens_access_token')),
  )

  let socket: WebSocket | null = null
  let reconnectInterval: ReturnType<typeof setInterval> | null = null
  let manualClose = false

  function connect() {
    if (socket) return
    const token = localStorage.getItem('lens_access_token') || ''
    // 未登录时不建立连接（服务端会拒绝，白触发重连循环）
    if (!token) return
    manualClose = false
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // 后端 WebSocket 路径: /ws/system/logs?token=xxx
    const wsUrl = `${protocol}//${host}/ws/system/logs?token=${encodeURIComponent(token)}`
    socket = new WebSocket(wsUrl)

    socket.onopen = () => {
      isConnected.value = true
      if (reconnectInterval) { clearInterval(reconnectInterval); reconnectInterval = null }
    }

    socket.onmessage = (event) => {
      try {
        const data = event.data
        if (typeof data === 'string') {
          // 后端发送纯文本日志，原样入队（多行消息由组件自行拆分解析）
          logs.value.push(data)
          if (logs.value.length > 2000) logs.value.shift()
        }
      } catch (e) { console.error('WS Parse Error', e) }
    }

    socket.onclose = () => {
      isConnected.value = false
      socket = null
      // 主动断开（登出）后不自动重连
      if (manualClose) return
      if (!reconnectInterval) reconnectInterval = setInterval(() => connect(), 5000)
    }

    socket.onerror = (err) => console.error('WebSocket Error', err)
  }

  function disconnect() {
    manualClose = true
    if (socket) {
      socket.close()
      socket = null
    }
    if (reconnectInterval) {
      clearInterval(reconnectInterval)
      reconnectInterval = null
    }
    isConnected.value = false
  }

  function clearLogs() { logs.value = [] }

  return {
    scanProgress, downloadProgress,
    isConnected, isLoggedIn, logs, showLogModal,
    connect, disconnect, clearLogs,
  }
})
