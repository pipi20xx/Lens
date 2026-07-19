<template>
  <div class="terminal-manager-view">
    <!-- 顶部状态栏 -->
    <div class="terminal-top-bar">
      <div class="bar-left">
        <!-- 移动端:主机列表抽屉触发 -->
        <n-button quaternary circle size="small" class="mobile-only" @click="showHostDrawer = true">
          <template #icon><n-icon :component="ServerStackIcon" /></template>
        </n-button>
        <!-- 桌面端:折叠侧栏 -->
        <n-button quaternary circle size="small" class="desktop-only" @click="collapsedSider = !collapsedSider">
          <template #icon><n-icon :component="Bars3Icon" /></template>
        </n-button>
        <n-divider vertical />
        <n-breadcrumb class="top-breadcrumb">
          <n-breadcrumb-item>终端管理</n-breadcrumb-item>
          <n-breadcrumb-item><n-text strong>{{ currentHostName }}</n-text></n-breadcrumb-item>
        </n-breadcrumb>
        <n-tag :type="activeSessionConnected ? 'success' : 'error'" size="small" round class="status-dot">
          {{ activeSessionConnected ? '已连接' : '已断开' }}
        </n-tag>
      </div>
      <div class="bar-right">
        <n-space :size="2">
          <!-- 移动端:快速命令抽屉触发 -->
          <n-button quaternary circle size="small" class="mobile-only" @click="showCommandDrawer = true" title="快速命令">
            <template #icon><n-icon :component="CodeBracketIcon" /></template>
          </n-button>
          <n-button quaternary circle size="small" @click="showFileManager = true" title="文件管理">
            <template #icon><n-icon :component="FolderOpenIcon" /></template>
          </n-button>
          <n-button quaternary circle size="small" @click="clearActiveTerm" title="清屏">
            <template #icon><n-icon :component="TrashIcon" /></template>
          </n-button>
          <n-button quaternary circle size="small" @click="reconnectActiveTerm" title="重连">
            <template #icon><n-icon :component="ArrowPathIcon" /></template>
          </n-button>
        </n-space>
      </div>
    </div>

    <!-- 桌面端:三栏布局 -->
    <n-layout v-if="!isMobile" has-sider class="main-layout">
      <n-layout-sider
        bordered
        collapse-mode="width"
        :collapsed-width="0"
        :width="220"
        :collapsed="collapsedSider"
      >
        <HostPanel
          :active-host-id="currentHostId"
          @select="handleHostSelect"
        />
      </n-layout-sider>

      <n-layout-content class="terminal-workspace">
        <div class="session-tabs" v-if="openSessions.length > 0">
          <n-tabs
            v-model:value="activeSessionId"
            type="card"
            closable
            @close="handleCloseSession"
            tab-style="min-width: 100px;"
          >
            <n-tab-pane
              v-for="session in openSessions"
              :key="session.sessionId"
              :name="session.sessionId"
              :tab="session.name"
            />
          </n-tabs>
        </div>

        <div class="terminal-container">
          <TerminalInstance
            v-for="session in openSessions"
            :key="session.sessionId"
            :ref="(el) => setInstanceRef(session.sessionId, el)"
            :host-id="session.hostId"
            :host-name="session.name"
            :visible="activeSessionId === session.sessionId"
            @connected="session.connected = true"
            @disconnected="session.connected = false"
          />
          <div v-if="openSessions.length === 0" class="empty-terminal">
            请从左侧选择主机以开启会话
          </div>
        </div>
      </n-layout-content>

      <n-layout-sider bordered :width="240">
        <CommandPanel @send="sendToActiveTerm" />
      </n-layout-sider>
    </n-layout>

    <!-- 移动端:单栏终端 -->
    <div v-else class="mobile-workspace">
      <div class="session-tabs" v-if="openSessions.length > 0">
        <n-tabs
          v-model:value="activeSessionId"
          type="card"
          closable
          @close="handleCloseSession"
          size="small"
        >
          <n-tab-pane
            v-for="session in openSessions"
            :key="session.sessionId"
            :name="session.sessionId"
            :tab="session.name"
          />
        </n-tabs>
      </div>

      <div class="terminal-container">
        <TerminalInstance
          v-for="session in openSessions"
          :key="session.sessionId"
          :ref="(el) => setInstanceRef(session.sessionId, el)"
          :host-id="session.hostId"
          :host-name="session.name"
          :visible="activeSessionId === session.sessionId"
          @connected="session.connected = true"
          @disconnected="session.connected = false"
        />
        <div v-if="openSessions.length === 0" class="empty-terminal">
          <n-button type="primary" secondary @click="showHostDrawer = true">
            点击选择主机开启会话
          </n-button>
        </div>
      </div>
    </div>

    <!-- 移动端:主机列表抽屉 -->
    <n-drawer v-model:show="showHostDrawer" :width="280" placement="left">
      <n-drawer-content title="主机列表" closable>
        <HostPanel
          :active-host-id="currentHostId"
          @select="handleHostSelectMobile"
        />
      </n-drawer-content>
    </n-drawer>

    <!-- 移动端:快速命令抽屉 -->
    <n-drawer v-model:show="showCommandDrawer" :width="300" placement="right">
      <n-drawer-content title="快速命令" closable>
        <CommandPanel @send="handleSendCommandMobile" />
      </n-drawer-content>
    </n-drawer>

    <!-- 文件管理器弹窗 -->
    <n-modal
      v-model:show="showFileManager"
      preset="card"
      :title="`文件管理: ${currentHostName}`"
      style="width: 90vw; max-width: 1200px"
      :segmented="{content: 'soft'}"
    >
      <div style="height: 70vh">
        <FileManager :host-id="currentHostId" :provider="terminalApi" />
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import {
  NLayout, NLayoutSider, NLayoutContent, NButton, NSpace, NTag,
  NDivider, NBreadcrumb, NBreadcrumbItem, NText, NIcon, NModal,
  NTabs, NTabPane, NDrawer, NDrawerContent
} from 'naive-ui';
import {
  ArrowPathIcon,
  Bars3Icon,
  CodeBracketIcon,
  FolderOpenIcon,
  ServerStackIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

import HostPanel from './components/HostPanel.vue';
import CommandPanel from './components/CommandPanel.vue';
import TerminalInstance from './components/TerminalInstance.vue';
import FileManager from '@/components/FileManager.vue';
import { terminalApi } from '@/api/terminal';
import { usePWA } from '@/composables/usePWA';

const { isMobile } = usePWA();

interface Session {
  sessionId: string;
  hostId: number | string;
  name: string;
  connected: boolean;
}

const collapsedSider = ref(false);
const showHostDrawer = ref(false);
const showCommandDrawer = ref(false);
const activeSessionId = ref<string>('');
const showFileManager = ref(false);
const openSessions = ref<Session[]>([]);

// 存储各个终端实例的引用
const instanceRefs = new Map<string, any>();
const setInstanceRef = (id: string, el: any) => {
  if (el) instanceRefs.set(id, el);
  else instanceRefs.delete(id);
};

const activeSession = computed(() => {
  return openSessions.value.find(s => s.sessionId === activeSessionId.value);
});

const activeSessionConnected = computed(() => {
  return activeSession.value?.connected || false;
});

const currentHostId = computed(() => {
  return activeSession.value?.hostId || 0;
});

const currentHostName = computed(() => {
  return activeSession.value?.name || '未选择主机';
});

// 处理主机选择逻辑：现在点击总是开启新会话
const handleHostSelect = (host: any) => {
  const { id, name } = host;

  // 1. 生成唯一会话 ID
  const sessionId = Date.now().toString() + Math.random().toString(36).substring(2, 5);

  // 2. 计算会话名称（如果是同一个主机的第 N 个会话，加个后缀）
  const hostSessionCount = openSessions.value.filter(s => s.hostId === id).length;
  const sessionName = hostSessionCount > 0 ? `${name} #${hostSessionCount + 1}` : name;

  // 3. 添加到会话列表
  openSessions.value.push({
    sessionId,
    hostId: id,
    name: sessionName,
    connected: false
  });

  // 4. 激活新会话
  activeSessionId.value = sessionId;
};

// 移动端:选择主机后关闭抽屉
const handleHostSelectMobile = (host: any) => {
  handleHostSelect(host);
  showHostDrawer.value = false;
};

// 移动端:发送命令后关闭命令抽屉
const handleSendCommandMobile = (cmd: string, autoEnter: boolean) => {
  sendToActiveTerm(cmd, autoEnter);
  showCommandDrawer.value = false;
};

const handleCloseSession = (sessionId: string) => {
  const index = openSessions.value.findIndex(s => s.sessionId === sessionId);
  if (index === -1) return;

  openSessions.value.splice(index, 1);
  instanceRefs.delete(sessionId);

  if (activeSessionId.value === sessionId) {
    if (openSessions.value.length > 0) {
      activeSessionId.value = openSessions.value[Math.max(0, index - 1)].sessionId;
    } else {
      activeSessionId.value = '';
    }
  }
};

const sendToActiveTerm = (cmd: string, autoEnter: boolean) => {
  const instance = instanceRefs.get(activeSessionId.value);
  if (instance) {
    instance.send(cmd + (autoEnter ? '\n' : ''));
    instance.focus();
  }
};

const clearActiveTerm = () => instanceRefs.get(activeSessionId.value)?.clear();
const reconnectActiveTerm = () => instanceRefs.get(activeSessionId.value)?.reconnect();

onMounted(() => {
  // 默认开启本地终端
  handleHostSelect({ id: 0, name: '本地 Shell' });
});
</script>

<style scoped>
.terminal-manager-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--app-bg-color);
  overflow: hidden;
}
.terminal-top-bar {
  height: 42px;
  flex-shrink: 0;
  background: var(--card-bg-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 12px;
  border-bottom: 1px solid var(--border-color);
}
.bar-left { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
.top-breadcrumb { min-width: 0; overflow: hidden; }
.main-layout { flex: 1; overflow: hidden; }
.terminal-workspace {
  background: #000;
  padding: 0;
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.session-tabs {
  background: var(--card-bg-color);
  padding: 4px 4px 0 4px;
}
:deep(.session-tabs .n-tabs-tab) {
  padding: 4px 12px;
}
.terminal-container {
  flex: 1;
  overflow: hidden;
}
.empty-terminal {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-color);
  opacity: 0.5;
}

/* 移动端工作区 */
.mobile-workspace {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #000;
  position: relative;
}
</style>

<style scoped>
/* 移动端状态栏压缩 */
@media (max-width: 767px) {
  .terminal-top-bar {
    height: 44px;
    padding: 0 8px;
  }
  .bar-left {
    gap: 4px;
  }
  /* 面包屑只保留当前主机名 */
  .top-breadcrumb :deep(.n-breadcrumb-item:first-child .n-breadcrumb-item__link) {
    display: none;
  }
  .top-breadcrumb :deep(.n-breadcrumb-item:first-child .n-breadcrumb-item__separator) {
    display: none;
  }
  /* 状态 tag 缩小 */
  .status-dot {
    transform: scale(0.9);
  }
}
</style>
