<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NSpace, NCard, NText, NSelect, NButton, NTabs, NTabPane, NIcon, useMessage } from 'naive-ui'
import { DnsOutlined as ServerIcon, RefreshOutlined as RefreshIcon } from '@vicons/material'
import MobileDockerContainerList from './MobileDockerContainerList.vue'
import MobileDockerComposeList from './MobileDockerComposeList.vue'
import MobileDockerSystemInfo from './MobileDockerSystemInfo.vue'
import MobileDockerMaintenancePanel from './MobileDockerMaintenancePanel.vue'
import MobileDockerHostManager from './MobileDockerHostManager.vue'
import { dockerApi } from '@/api/docker'

const message = useMessage()

const loading = ref(false)
const selectedHostId = ref<string | null>(null)
const hosts = ref<any[]>([])
const activeTab = ref('containers')
const showHostManager = ref(false)

const hostOptions = computed(() => {
  return hosts.value.map(h => ({ label: h.name, value: h.id }))
})

const currentHost = computed(() => {
  return hosts.value.find(h => h.id === selectedHostId.value)
})

const loadHosts = async () => {
  try {
    const res = await dockerApi.getHosts()
    hosts.value = res as any || []
    if (hosts.value.length > 0 && !selectedHostId.value) {
      selectedHostId.value = hosts.value[0].id
    }
  } catch (e) {
    message.error('加载主机列表失败')
  }
}

const refreshAll = async () => {
  loading.value = true
  try {
    await loadHosts()
    message.success('刷新成功')
  } catch (e) {
    message.error('刷新失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadHosts()
})
</script>

<template>
  <div class="mobile-docker-manager">
    <div class="page-header">
      <h1 class="page-title">Docker 容器管理</h1>
      <p class="page-desc">管理 Docker 容器与 Compose 项目</p>
    </div>

    <n-card class="filter-card" :bordered="false">
      <n-space vertical>
        <n-select 
          v-model:value="selectedHostId" 
          :options="hostOptions" 
          placeholder="选择主机"
          size="medium"
        />
        <n-space justify="space-between">
          <n-button type="primary" secondary @click="showHostManager = true" size="small">
            <template #icon>
              <n-icon><ServerIcon /></n-icon>
            </template>
            管理主机
          </n-button>
          <n-button type="info" secondary @click="refreshAll" :loading="loading" size="small">
            <template #icon>
              <n-icon><RefreshIcon /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </n-space>
    </n-card>

    <n-card class="content-card" :bordered="false">
      <n-tabs v-model:value="activeTab" type="segment" size="medium">
        <n-tab-pane name="containers" tab="容器">
          <MobileDockerContainerList :host-id="selectedHostId" />
        </n-tab-pane>
        <n-tab-pane name="compose" tab="Compose">
          <MobileDockerComposeList :host-id="selectedHostId" />
        </n-tab-pane>
        <n-tab-pane name="system" tab="环境">
          <MobileDockerSystemInfo :host-id="selectedHostId" />
        </n-tab-pane>
        <n-tab-pane name="maintenance" tab="配置">
          <MobileDockerMaintenancePanel :host-id="selectedHostId" />
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <MobileDockerHostManager 
      :show="showHostManager" 
      @update:show="showHostManager = $event"
      :hosts="hosts" 
      @refresh="loadHosts"
    />
  </div>
</template>

<style scoped>
.mobile-docker-manager {
  padding: 16px;
  background: var(--app-bg-color);
  min-height: 100vh;
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

.filter-card,
.content-card {
  margin-bottom: 12px;
  background: var(--card-color);
  border-radius: 12px;
}
</style>
