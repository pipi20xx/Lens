import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { LogEntry, ProgressData } from '@/types'

export const useSystemStore = defineStore('system', () => {
  const scanProgress = ref<ProgressData>({ status: 'idle', current: 0, total: 0, message: '' })
  const downloadProgress = ref<ProgressData>({ status: 'idle', current: 0, total: 0, message: '' })
  const isConnected = ref(false)
  const logs = ref<LogEntry[]>([])
  const showLogModal = ref(false)
  const logFilter = ref<string>('all')

  let socket: WebSocket | null = null
  let reconnectInterval: ReturnType<typeof setInterval> | null = null

  function parseLogLine(raw: string): LogEntry {
    const match = raw.match(/^(\d{4}-\d{2}-\d{2}\s+)?(\d{2}:\d{2}:\d{2})\s*\|\s*(\w+)\s*\|\s*(.+)$/)
    if (match) {
      return {
        time: match[2] || '',
        level: match[3] || 'INFO',
        message: match[4] || raw,
        raw,
      }
    }
    return { time: '', level: 'INFO', message: raw, raw }
  }

  const filteredLogs = computed(() => {
    if (logFilter.value === 'all') return logs.value
    return logs.value.filter(l => l.level === logFilter.value)
  })

  function connect() {
    if (socket) return
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    socket = new WebSocket(`${protocol}//${host}/ws`)

    socket.onopen = () => {
      isConnected.value = true
      if (reconnectInterval) { clearInterval(reconnectInterval); reconnectInterval = null }
    }

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'progress') {
          const task = payload.task
          if (task === 'scan') {
            scanProgress.value = payload.data
          } else {
            downloadProgress.value = payload.data
          }
        } else if (payload.type === 'log') {
          const entry = parseLogLine(payload.data)
          logs.value.push(entry)
          if (logs.value.length > 2000) logs.value.shift()
        }
      } catch (e) { console.error('WS Parse Error', e) }
    }

    socket.onclose = () => {
      isConnected.value = false
      socket = null
      if (!reconnectInterval) reconnectInterval = setInterval(() => connect(), 5000)
    }

    socket.onerror = (err) => console.error('WebSocket Error', err)
  }

  function disconnect() {
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
    isConnected, logs, filteredLogs, logFilter, showLogModal,
    connect, disconnect, clearLogs,
  }
})
