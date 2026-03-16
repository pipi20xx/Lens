<template>
  <div class="mobile-postgres-manager">
    <div class="page-header">
      <h1 class="page-title">PostgreSQL 数据库管理</h1>
      <p class="page-desc">直连 PostgreSQL 数据库，支持数据表浏览、SQL 调试及库级备份还原操作</p>
    </div>

    <n-card class="connection-card" :bordered="false" title="连接配置">
      <n-space vertical>
        <n-select
          v-model:value="selectedHostId"
          :options="hostOptions"
          placeholder="选择数据库实例"
          @update:value="handleHostChange"
        />
        <n-button block type="primary" secondary @click="showHostModal = true">
          <template #icon><n-icon><ServerIcon /></n-icon></template>
          管理主机
        </n-button>
        <n-button block secondary @click="refreshAll" :disabled="!selectedHost" :loading="refreshing">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          全部刷新
        </n-button>
      </n-space>
    </n-card>

    <n-card v-if="selectedHost" class="tabs-card" :bordered="false">
      <n-tabs v-model:value="activeTab" type="segment" animated>
        <n-tab-pane name="data" tab="数据浏览器">
          <MobilePgsqlTableBrowser ref="tablePanelRef" :host="selectedHost" />
        </n-tab-pane>

        <n-tab-pane name="databases" tab="数据库列表">
          <MobilePgsqlDatabasePanel ref="dbPanelRef" :host="selectedHost" />
        </n-tab-pane>

        <n-tab-pane name="users" tab="用户列表">
          <MobilePgsqlUserPanel ref="userPanelRef" :host="selectedHost" />
        </n-tab-pane>

        <n-tab-pane name="backup" tab="备份与恢复">
          <MobilePgsqlBackupPanel ref="backupPanelRef" :host="selectedHost" />
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <MobilePgsqlHostManagerModal 
      v-model:show="showHostModal" 
      @refresh="fetchHosts" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NIcon, NTabs, NTabPane, NSelect, useMessage } from 'naive-ui'
import { 
  DnsOutlined as ServerIcon,
  RefreshOutlined as RefreshIcon
} from '@vicons/material'

import MobilePgsqlTableBrowser from './MobilePgsqlTableBrowser.vue'
import MobilePgsqlDatabasePanel from './MobilePgsqlDatabasePanel.vue'
import MobilePgsqlUserPanel from './MobilePgsqlUserPanel.vue'
import MobilePgsqlBackupPanel from './MobilePgsqlBackupPanel.vue'
import MobilePgsqlHostManagerModal from './MobilePgsqlHostManagerModal.vue'

import { usePgsqlHosts } from '@/views/toolkit/pgsql/hooks/usePgsqlHosts'

const message = useMessage()
const activeTab = ref('data')
const refreshing = ref(false)

const { hosts, selectedHostId, hostOptions, selectedHost, fetchHosts } = usePgsqlHosts()

const showHostModal = ref(false)

const tablePanelRef = ref()
const dbPanelRef = ref()
const userPanelRef = ref()
const backupPanelRef = ref()

const handleHostChange = () => {
  // 手动触发所有子组件刷新
  setTimeout(() => {
    tablePanelRef.value?.refresh()
    dbPanelRef.value?.refresh()
    userPanelRef.value?.refresh()
    backupPanelRef.value?.refresh()
  }, 100)
}

const refreshAll = async () => {
  if (!selectedHost.value) return
  refreshing.value = true
  await Promise.all([
    tablePanelRef.value?.refresh(),
    dbPanelRef.value?.refresh(),
    userPanelRef.value?.refresh(),
    backupPanelRef.value?.refresh()
  ])
  refreshing.value = false
}

onMounted(fetchHosts)
</script>

<style scoped>
.mobile-postgres-manager {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.connection-card,
.tabs-card {
  margin-bottom: 12px;
}
</style>
