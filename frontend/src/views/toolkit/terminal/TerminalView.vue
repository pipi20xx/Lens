<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import HostPanel from './components/HostPanel.vue'
import CommandPanel from './components/CommandPanel.vue'
import TerminalInstance from './components/TerminalInstance.vue'

// ========== 会话管理 ==========
interface Session {
  sessionId: string
  hostId: number | string
  name: string
  connected: boolean
}

const activeSessionId = ref('')
const openSessions = ref<Session[]>([])
const collapsedSider = ref(false)

// 存储终端实例引用
const instanceRefs = new Map<string, any>()
function setInstanceRef(id: string, el: any) {
  if (el) instanceRefs.set(id, el)
  else instanceRefs.delete(id)
}

const activeSession = computed(() => {
  return openSessions.value.find((s) => s.sessionId === activeSessionId.value)
})

const activeSessionConnected = computed(() => {
  return activeSession.value?.connected || false
})

const currentHostId = computed(() => {
  return activeSession.value?.hostId ?? 0
})

const currentHostName = computed(() => {
  return activeSession.value?.name || '未选择主机'
})

// 处理主机选择：点击主机开启新会话
function handleHostSelect(host: any) {
  const { id, name } = host
  const sessionId = Date.now().toString() + Math.random().toString(36).substring(2, 5)
  const hostSessionCount = openSessions.value.filter((s) => s.hostId === id).length
  const sessionName = hostSessionCount > 0 ? `${name} #${hostSessionCount + 1}` : name

  openSessions.value.push({
    sessionId,
    hostId: id,
    name: sessionName,
    connected: false,
  })
  activeSessionId.value = sessionId
}

function handleCloseSession(sessionId: string) {
  const index = openSessions.value.findIndex((s) => s.sessionId === sessionId)
  if (index === -1) return

  openSessions.value.splice(index, 1)
  instanceRefs.delete(sessionId)

  if (activeSessionId.value === sessionId) {
    if (openSessions.value.length > 0) {
      activeSessionId.value = openSessions.value[Math.max(0, index - 1)].sessionId
    } else {
      activeSessionId.value = ''
    }
  }
}

// 快速命令发送
function sendToActiveTerm(cmd: string, autoEnter: boolean) {
  const instance = instanceRefs.get(activeSessionId.value)
  if (instance) {
    instance.send(cmd + (autoEnter ? '\n' : ''))
    instance.focus()
  }
}

// 工具栏操作
function clearActiveTerm() {
  instanceRefs.get(activeSessionId.value)?.clear()
}
function reconnectActiveTerm() {
  instanceRefs.get(activeSessionId.value)?.reconnect()
}

// 默认开启本地终端
onMounted(() => {
  handleHostSelect({ id: 0, name: '本地 Shell' })
})
</script>

<template>
  <div class="terminal-view">
    <!-- 顶部状态栏 -->
    <div class="terminal-top-bar">
      <div class="bar-left d-flex align-center ga-2">
        <v-btn icon variant="text" size="small" @click="collapsedSider = !collapsedSider">
          <v-icon size="18">mdi-menu</v-icon>
        </v-btn>
        <v-divider vertical />
        <span class="text-body-2 font-weight-bold">{{ currentHostName }}</span>
        <v-chip :color="activeSessionConnected ? 'success' : 'grey'" size="small" variant="tonal" class="ml-1">
          <v-icon start size="12">{{ activeSessionConnected ? 'mdi-circle' : 'mdi-circle-outline' }}</v-icon>
          {{ activeSessionConnected ? '已连接' : '未连接' }}
        </v-chip>
      </div>
      <div class="bar-right d-flex ga-1">
        <v-btn icon variant="text" size="small" @click="clearActiveTerm" title="清屏">
          <v-icon size="18">mdi-eraser</v-icon>
        </v-btn>
        <v-btn icon variant="text" size="small" @click="reconnectActiveTerm" title="重连">
          <v-icon size="18">mdi-refresh</v-icon>
        </v-btn>
      </div>
    </div>

    <!-- 三栏布局 -->
    <div class="terminal-body">
      <!-- 左侧：主机列表 -->
      <div class="terminal-sider-left" :class="{ collapsed: collapsedSider }">
        <HostPanel :active-host-id="currentHostId" @select="handleHostSelect" />
      </div>

      <!-- 中间：终端区域 -->
      <div class="terminal-workspace">
        <!-- 会话标签 -->
        <div v-if="openSessions.length > 0" class="session-tabs">
          <div
            v-for="session in openSessions"
            :key="session.sessionId"
            class="session-tab"
            :class="{ active: activeSessionId === session.sessionId }"
            @click="activeSessionId = session.sessionId"
          >
            <v-icon size="14" class="mr-1">{{ session.connected ? 'mdi-circle' : 'mdi-circle-outline' }}</v-icon>
            <span class="tab-name">{{ session.name }}</span>
            <v-icon size="14" class="tab-close ml-1" @click.stop="handleCloseSession(session.sessionId)">mdi-close</v-icon>
          </div>
        </div>

        <!-- 终端容器 -->
        <div class="terminal-container">
          <TerminalInstance
            v-for="session in openSessions"
            :key="session.sessionId"
            :ref="(el: any) => setInstanceRef(session.sessionId, el)"
            :host-id="session.hostId"
            :host-name="session.name"
            :visible="activeSessionId === session.sessionId"
            @connected="session.connected = true"
            @disconnected="session.connected = false"
          />
          <div v-if="openSessions.length === 0" class="empty-terminal">
            <v-icon size="48" color="grey" class="mb-3">mdi-console-line</v-icon>
            <div class="text-body-2 text-medium-emphasis">请从左侧选择主机以开启会话</div>
          </div>
        </div>
      </div>

      <!-- 右侧：快速命令 -->
      <div class="terminal-sider-right">
        <CommandPanel @send="sendToActiveTerm" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.terminal-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.terminal-top-bar {
  height: 44px;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.terminal-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧主机面板 */
.terminal-sider-left {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
  transition: width 0.2s ease, opacity 0.2s ease;
}
.terminal-sider-left.collapsed {
  width: 0;
  opacity: 0;
}

/* 右侧命令面板 */
.terminal-sider-right {
  width: 260px;
  flex-shrink: 0;
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

/* 中间终端区域 */
.terminal-workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* 会话标签栏 */
.session-tabs {
  display: flex;
  gap: 2px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  overflow-x: auto;
  flex-shrink: 0;
}

.session-tab {
  display: flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 6px 6px 0 0;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
  transition: background 0.2s;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.03);
  user-select: none;
}
.session-tab:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.7);
}
.session-tab.active {
  background: #1a1a2e;
  color: #fff;
}
.session-tab .tab-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.session-tab .tab-close {
  opacity: 0.3;
  transition: opacity 0.2s;
}
.session-tab .tab-close:hover {
  opacity: 1;
  color: rgb(var(--v-theme-error));
}

/* 终端容器 */
.terminal-container {
  flex: 1;
  overflow: hidden;
  position: relative;
  background: #1a1a2e;
}

.empty-terminal {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

/* 移动端响应式 */
@media (max-width: 960px) {
  .terminal-sider-left {
    width: 0;
    opacity: 0;
  }
  .terminal-sider-right {
    width: 0;
    opacity: 0;
  }
}
</style>