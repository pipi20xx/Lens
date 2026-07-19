<template>
  <div class="postgres-manager">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">PostgreSQL 数据库管理</n-text></n-h2>
        <n-text depth="3">直连 PostgreSQL 数据库，支持数据表浏览、SQL 调试及库级备份还原操作。</n-text>
      </div>

      <n-card size="small" segmented>
        <template #header>
          <n-space align="center" justify="space-between" style="width: 100%" :wrap="true" :size="[12, 8]">
            <n-space align="center" :size="12" :wrap="true">
              <n-select
                v-model:value="selectedHostId"
                :options="hostOptions"
                placeholder="选择数据库实例"
                class="host-select"
                @update:value="handleHostChange"
              />
              <n-button type="primary" secondary size="small" @click="showHostModal = true">
                管理主机
              </n-button>
            </n-space>
            <n-space :size="8">
              <n-button :disabled="!selectedHost" ghost size="small" @click="refreshAll" :loading="refreshing">
                全部刷新
              </n-button>
            </n-space>
          </n-space>
        </template>

        <n-tabs v-model:value="activeTab" type="line" animated>
          <n-tab-pane name="data" tab="数据浏览器">
            <table-browser-panel ref="tablePanelRef" :host="selectedHost" />
          </n-tab-pane>

          <n-tab-pane name="databases" tab="数据库列表">
            <database-panel ref="dbPanelRef" :host="selectedHost" />
          </n-tab-pane>

          <n-tab-pane name="users" tab="用户列表">
            <user-panel ref="userPanelRef" :host="selectedHost" />
          </n-tab-pane>

          <n-tab-pane name="backup" tab="备份与恢复">
            <backup-panel ref="backupPanelRef" :host="selectedHost" />
          </n-tab-pane>
        </n-tabs>
      </n-card>
    </n-space>

    <!-- 模块化弹窗 -->
    <host-manager-modal 
      v-model:show="showHostModal" 
      @refresh="fetchHosts" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NSpace, NCard, NText, NButton, NSelect, NTabs, NTabPane, useMessage, NIcon, NH2 } from 'naive-ui'
// 导入乐高组件
import TableBrowserPanel from './pgsql/components/TableBrowserPanel.vue'
import DatabasePanel from './pgsql/components/DatabasePanel.vue'
import UserPanel from './pgsql/components/UserPanel.vue'
import BackupPanel from './pgsql/components/BackupPanel.vue'
import HostManagerModal from './pgsql/components/HostManagerModal.vue'

// 导入提取的逻辑
import { usePgsqlHosts } from './pgsql/hooks/usePgsqlHosts'

const message = useMessage()
const { hosts, selectedHostId, hostOptions, selectedHost, fetchHosts } = usePgsqlHosts()

const activeTab = ref('data')
const refreshing = ref(false)
const showHostModal = ref(false)

const tablePanelRef = ref()
const dbPanelRef = ref()
const userPanelRef = ref()
const backupPanelRef = ref()

const handleHostChange = () => {
  // 子组件通过 watch host prop 会自动处理刷新
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
/* 主机选择器：桌面端固定宽度，移动端弹性填充 */
.host-select {
  width: 220px;
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .host-select {
    width: auto;
    flex: 1 1 180px;
    min-width: 0;
  }
}
</style>