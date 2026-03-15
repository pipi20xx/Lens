<template>
  <div class="mobile-docker-manager">
    <div class="page-header">
      <h1 class="page-title">Docker 容器管理</h1>
      <p class="page-desc">管理 Docker 容器与 Compose 项目</p>
    </div>

    <n-card class="filter-card" :bordered="false">
      <n-select v-model:value="selectedHostId" :options="hostOptions" placeholder="选择主机" @update:value="loadContainers" />
    </n-card>

    <n-card class="containers-card" :bordered="false" title="容器列表">
      <n-space vertical>
        <n-button block type="primary" secondary @click="loadContainers" :loading="loading">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          刷新容器
        </n-button>
        <div v-if="containers.length === 0" class="empty-state">
          <n-empty description="暂无容器" />
        </div>
        <div v-else class="container-list">
          <div v-for="container in containers" :key="container.id" class="container-item">
            <div class="container-header">
              <div class="container-name">{{ container.name }}</div>
              <n-tag :type="container.state === 'running' ? 'success' : 'error'" size="small" round>
                {{ container.state === 'running' ? '运行中' : '已停止' }}
              </n-tag>
            </div>
            <div class="container-info">
              <div class="container-image">{{ container.image }}</div>
              <div class="container-ports">{{ container.ports || '无端口映射' }}</div>
            </div>
            <div class="container-actions">
              <n-button v-if="container.state === 'running'" size="small" secondary type="warning" @click="stopContainer(container.id)">
                停止
              </n-button>
              <n-button v-else size="small" secondary type="success" @click="startContainer(container.id)">
                启动
              </n-button>
              <n-button size="small" secondary type="info" @click="viewLogs(container.id)">
                日志
              </n-button>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <!-- 日志弹窗 -->
    <n-modal v-model:show="showLogsModal" preset="card" title="容器日志" style="width: 95vw; max-width: 800px">
      <pre class="logs-content">{{ containerLogs }}</pre>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NCard, NButton, NSelect, NSpace, NEmpty, NTag, NIcon, NModal } from 'naive-ui'
import { RefreshOutlined as RefreshIcon } from '@vicons/material'
import { dockerApi } from '@/api/docker'
import { useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const loading = ref(false)
const selectedHostId = ref<number | null>(null)
const containers = ref<any[]>([])
const hosts = ref<any[]>([])

const hostOptions = computed(() => {
  return hosts.value.map(h => ({ label: h.name, value: h.id }))
})

const loadHosts = async () => {
  try {
    const res = await dockerApi.getHosts()
    hosts.value = res as any || []
    if (hosts.value.length > 0 && !selectedHostId.value) {
      selectedHostId.value = hosts.value[0].id
      await loadContainers()
    }
  } catch (e) {
    message.error('加载主机列表失败')
  }
}

const loadContainers = async () => {
  if (!selectedHostId.value) return
  loading.value = true
  try {
    const res = await dockerApi.getContainers(selectedHostId.value)
    containers.value = res as any || []
  } catch (e) {
    message.error('加载容器列表失败')
  } finally {
    loading.value = false
  }
}

const startContainer = async (id: string) => {
  if (!selectedHostId.value) return
  try {
    const res = await axios.post(`/api/docker/${selectedHostId.value}/containers/${id}/action`, { action: 'start' })
    message.success('容器已启动')
    setTimeout(() => loadContainers(), 2000)
  } catch (e: any) {
    message.error('启动失败: ' + (e.response?.data?.detail || e.message))
  }
}

const stopContainer = async (id: string) => {
  if (!selectedHostId.value) return
  try {
    const res = await axios.post(`/api/docker/${selectedHostId.value}/containers/${id}/action`, { action: 'stop' })
    message.success('容器已停止')
    setTimeout(() => loadContainers(), 2000)
  } catch (e: any) {
    message.error('停止失败: ' + (e.response?.data?.detail || e.message))
  }
}

const viewLogs = async (id: string) => {
  if (!selectedHostId.value) return
  try {
    const res = await axios.get(`/api/docker/${selectedHostId.value}/containers/${id}/logs?tail=100`)
    containerLogs.value = res.data.logs || '暂无日志'
    showLogsModal.value = true
  } catch (e: any) {
    message.error('获取日志失败: ' + (e.response?.data?.detail || e.message))
  }
}

const containerLogs = ref('')
const showLogsModal = ref(false)

onMounted(() => {
  loadHosts()
})
</script>

<style scoped>
.mobile-docker-manager {
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

.filter-card,
.containers-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.container-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.container-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.container-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.container-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.container-info {
  margin-bottom: 8px;
}

.container-image,
.container-ports {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 4px;
}

.container-actions {
  display: flex;
  gap: 8px;
}

.logs-content {
  margin: 0;
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--text-color);
  max-height: 60vh;
  overflow-y: auto;
  background: var(--app-bg-color);
  border-radius: 8px;
}
</style>
