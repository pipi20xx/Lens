<template>
  <div class="mobile-docker-container-list">
    <n-space vertical>
      <n-space justify="space-between" align="center">
        <n-space>
          <n-button :type="buttonTypes.PRIMARY" :size="buttonSizes.MEDIUM" @click="fetchContainers(true)" :loading="loading">
            {{ buttonText.REFRESH }}
          </n-button>
          <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR" @click="handlePruneContainers" :loading="loadingPrune">
            {{ buttonText.CLEAR }}
          </n-button>
        </n-space>
        <div class="setting-item">
          <span class="setting-label">增强监控</span>
          <MobileSwitch v-model="enhancedMode" />
        </div>
      </n-space>

      <n-input
        v-model:value="searchQuery"
        :placeholder="placeholder.SEARCH_CONTAINER"
        clearable
        :size="buttonSizes.SMALL"
      />

      <div v-if="filteredContainers.length === 0" class="empty-state">
        <n-empty :description="messageText.EMPTY_DATA" :size="buttonSizes.SMALL" />
      </div>

      <div v-else class="container-list">
        <div v-for="container in filteredContainers" :key="container.id" class="container-item">
          <div class="container-header">
            <div class="container-name">
              <n-text strong>{{ container.name }}</n-text>
              <n-tag v-if="containerSettings[container.name]?.auto_update" :type="tagTypes.SUCCESS" :size="buttonSizes.TINY" round>
                自动更新
              </n-tag>
            </div>
            <n-tag :type="container.status === 'running' ? tagTypes.SUCCESS : tagTypes.ERROR" :size="buttonSizes.SMALL" round>
              {{ getStatusText(container.status) }}
            </n-tag>
          </div>

          <div v-if="enhancedMode && container.status === 'running'" class="container-stats">
            <div class="stat-item">
              <span>CPU: {{ containerStats[container.name]?.cpu || '--' }}</span>
            </div>
            <div class="stat-item">
              <span>内存: {{ containerStats[container.name]?.mem_perc || '--' }}</span>
            </div>
            <div class="stat-item">
              <span>运行时间: {{ formatUptime(container.uptime) }}</span>
            </div>
          </div>

          <div class="container-info">
            <div class="info-row">
              <n-text depth="3" style="font-size: 12px">{{ container.image }}</n-text>
            </div>
            <div v-if="container.ip" class="info-row">
              <n-text depth="3" style="font-size: 12px">{{ container.ip }}</n-text>
            </div>
          </div>

          <div v-if="container.ports || containerSettings[container.name]?.custom_port" class="container-ports">
            <n-button
              v-for="port in getPortButtons(container)"
              :key="port.label"
              :size="buttonSizes.MEDIUM"
              :type="port.type"
              secondary
              @click="port.action"
            >
              {{ port.label }}
            </n-button>
          </div>

          <div class="container-actions">
            <n-button :size="buttonSizes.MEDIUM" :type="container.status === 'running' ? buttonTypes.ERROR : buttonTypes.PRIMARY" secondary @click="handleAction(container.id, container.status === 'running' ? 'stop' : 'start')" :loading="loadingActions[container.id]">
              {{ container.status === 'running' ? buttonText.STOP : buttonText.START }}
            </n-button>
            <n-button :size="buttonSizes.MEDIUM" :type="buttonTypes.WARNING" secondary @click="handleAction(container.id, 'recreate')" :loading="loadingActions[container.id]">
              {{ buttonText.UPDATE }}
            </n-button>
            <n-button :size="buttonSizes.MEDIUM" secondary @click="showLogs(container.id, container.name)">
              {{ buttonText.LOGS }}
            </n-button>
            <n-button :size="buttonSizes.MEDIUM" secondary @click="openTerminal(container)" :disabled="container.status !== 'running'">
              {{ buttonText.TERMINAL }}
            </n-button>
            <n-button :size="buttonSizes.MEDIUM" secondary @click="openSettingsModal(container.name)">
              {{ buttonText.SETTINGS }}
            </n-button>
            <n-popconfirm @positive-click="() => handleDelete(container)" :positive-text="buttonText.CONFIRM_DELETE" :negative-text="buttonText.CANCEL">
              <template #trigger>
                <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
                  {{ buttonText.DELETE }}
                </n-button>
              </template>
              {{ messageText.DELETE_CONFIRM }}
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-space>

    <n-modal v-model:show="showLogsModal" preset="card" :title="buttonText.LOGS" style="width: 90vw; max-width: 600px">
      <pre class="logs-container">{{ containerLogs }}</pre>
    </n-modal>

    <n-modal v-model:show="showSettingsModal" preset="card" :title="buttonText.SETTINGS" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="formLabel.CUSTOM_PORT">
          <n-input v-model:value="settingsForm.custom_port" :placeholder="placeholder.CUSTOM_PORT" />
        </n-form-item>
        <n-form-item :label="formLabel.AUTO_UPDATE">
          <n-switch v-model:value="settingsForm.auto_update" class="mobile-switch" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showSettingsModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveSettings">{{ buttonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onUnmounted } from 'vue'
import { 
  NSpace, NButton, NTag, NText, NModal, NForm, NFormItem, 
  NInput, NEmpty, NPopconfirm, useMessage, useDialog 
} from 'naive-ui'
import axios from 'axios'
import { useDockerStore } from '@/store/dockerStore'
import MobileSwitch from '../components/MobileSwitch.vue'
import {
  ButtonTypes,
  ButtonSizes,
  TagTypes,
  ButtonText,
  MessageText,
} from '../constants'

const props = defineProps<{
  hostId: string | null
}>()

const message = useMessage()
const dialog = useDialog()
const dockerStore = useDockerStore()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const tagTypes = TagTypes
const buttonText = ButtonText
const messageText = MessageText

// 表单标签
const formLabel = {
  CUSTOM_PORT: '自定义访问端口',
  AUTO_UPDATE: '自动更新镜像',
}

// 占位符
const placeholder = {
  SEARCH_CONTAINER: '搜索容器名称或镜像...',
  CUSTOM_PORT: 'Host 模式或未识别端口跳转',
}

const containers = computed(() => dockerStore.containers[props.hostId || ''] || [])
const containerStats = computed(() => dockerStore.containerStats[props.hostId || ''] || {})
const loading = computed(() => {
  const cacheKey = `containers_${props.hostId}_${enhancedMode.value}`
  return dockerStore.loading[cacheKey] || false
})

const loadingPrune = ref(false)
const searchQuery = ref('')
const loadingActions = ref<Record<string, boolean>>({})
const containerSettings = ref<Record<string, any>>({})
const containerLogs = ref('')
const showLogsModal = ref(false)
const showSettingsModal = ref(false)
const settingsForm = ref({ name: '', custom_port: '', auto_update: false })
const enhancedMode = ref(localStorage.getItem('lens_docker_enhanced') === 'true')

let statsTimer: any = null

watch(enhancedMode, (val) => {
  localStorage.setItem('lens_docker_enhanced', String(val))
  fetchContainers(true)
  if (!val && statsTimer) {
    clearInterval(statsTimer)
    statsTimer = null
  } else if (val && !statsTimer) {
    startStatsTimer()
  }
})

const filteredContainers = computed(() => {
  const data = containers.value
  if (!searchQuery.value) return data
  const query = searchQuery.value.toLowerCase()
  return data.filter((c: any) => 
    c.name.toLowerCase().includes(query) || 
    c.image.toLowerCase().includes(query)
  )
})

const statusMap: Record<string, string> = {
  'running': '运行中',
  'exited': '已停止',
  'restarting': '重启中',
  'paused': '已暂停',
  'created': '已创建',
  'removing': '移除中',
  'dead': '已失效'
}

const getStatusText = (status: string) => {
  return statusMap[status] || status
}

const formatUptime = (uptime: string) => {
  if (!uptime) return '--'
  if (uptime.startsWith('Up ')) {
    return uptime.replace('Up ', '已运行 ')
      .replace(' days', ' 天')
      .replace(' day', ' 天')
      .replace(' hours', ' 小时')
      .replace(' hour', ' 小时')
      .replace(' minutes', ' 分钟')
      .replace(' minute', ' 分钟')
      .replace(' seconds', ' 秒')
      .replace(' second', ' 秒')
  }
  return uptime
}

const fetchContainers = async (force = false) => {
  if (!props.hostId) return
  await dockerStore.fetchContainers(props.hostId, force, enhancedMode.value)
  try {
    const settingsRes = await axios.get('/api/docker/container-settings')
    containerSettings.value = settingsRes.data
  } catch (e) {}
}

const startStatsTimer = () => {
  if (statsTimer) clearInterval(statsTimer)
  if (enhancedMode.value) {
    statsTimer = setInterval(() => {
      if (props.hostId) dockerStore.fetchStats(props.hostId)
    }, 10000)
  }
}

const handleAction = async (id: string, action: string) => {
  loadingActions.value[id] = true
  try {
    const res = await axios.post(`/api/docker/${props.hostId}/containers/${id}/action`, { action })
    if (res.data.async) {
      message.info(res.data.message || '任务已在后台启动')
    } else {
      message.success('指令已执行')
    }
    setTimeout(() => fetchContainers(true), 2000)
  } catch (e: any) {
    const errorMsg = e.response?.data?.detail || e.message || messageText.OPERATION_FAILED
    message.error(`${messageText.OPERATION_FAILED}: ${errorMsg}`)
  } finally {
    loadingActions.value[id] = false
  }
}

const handleDelete = (row: any) => {
  dialog.error({
    title: '确认删除容器',
    content: `确定要彻底删除容器 "${row.name}" 吗？此操作不可撤销。`,
    positiveText: buttonText.CONFIRM_DELETE,
    negativeText: buttonText.CANCEL,
    onPositiveClick: () => handleAction(row.id, 'remove')
  })
}

const handlePruneContainers = async () => {
  if (!props.hostId) return
  dialog.warning({
    title: '确认清理容器',
    content: '此操作将永久删除所有处于停止状态的容器。',
    positiveText: buttonText.CONFIRM,
    negativeText: buttonText.CANCEL,
    onPositiveClick: async () => {
      loadingPrune.value = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune-containers`)
        message.success(res.data.message || '容器清理任务已启动')
        setTimeout(() => fetchContainers(true), 3000)
      } catch (e) {
        message.error(messageText.OPERATION_FAILED)
      } finally {
        loadingPrune.value = false
      }
    }
  })
}

const showLogs = async (id: string, name: string) => {
  const res = await axios.get(`/api/docker/${props.hostId}/containers/${id}/logs?tail=200`)
  containerLogs.value = res.data.logs
  showLogsModal.value = true
}

const openTerminal = (row: any) => {
  if (row.status !== 'running') {
    message.warning('只有运行中的容器可以进入终端')
    return
  }
  message.info('终端功能暂未实现')
}

const openSettingsModal = (name: string) => {
  const current = containerSettings.value[name] || {}
  settingsForm.value = { 
    name, 
    custom_port: current.custom_port || '',
    auto_update: current.auto_update || false
  }
  showSettingsModal.value = true
}

const saveSettings = async () => {
  await axios.post(`/api/docker/container-settings/${settingsForm.value.name}`, { 
    custom_port: settingsForm.value.custom_port,
    auto_update: settingsForm.value.auto_update,
    host_id: props.hostId
  })
  message.success(messageText.SETTINGS_SAVED)
  showSettingsModal.value = false
  fetchContainers(true)
}

const getPortButtons = (container: any) => {
  const buttons: any[] = []
  const customPort = containerSettings.value[container.name]?.custom_port
  
  if (container.ports) {
    for (const [containerPort, bindings] of Object.entries(container.ports)) {
      if (bindings && Array.isArray(bindings)) {
        bindings.forEach((b: any) => {
          const hostPort = b.HostPort || b.hostPort || b.host_port
          if (hostPort) {
            buttons.push({
              label: `${hostPort}->${containerPort}`,
              type: buttonTypes.PRIMARY,
              action: () => window.open(`http://${window.location.hostname}:${hostPort}`, '_blank')
            })
          }
        })
      }
    }
  }
  
  if (customPort) {
    buttons.push({
      label: `${customPort} (自定)`,
      type: buttonTypes.WARNING,
      action: () => window.open(`http://${window.location.hostname}:${customPort}`, '_blank')
    })
  }
  
  return buttons
}

watch(() => props.hostId, () => {
  fetchContainers()
  startStatsTimer()
}, { immediate: true })

onUnmounted(() => {
  if (statsTimer) clearInterval(statsTimer)
})

defineExpose({ refresh: fetchContainers })
</script>

<style scoped>
.mobile-docker-container-list {
  padding: 12px 0;
}

.empty-state {
  padding: 40px 0;
}

.container-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.container-item {
  background: var(--card-color);
  border: 1px solid #3B82F6;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 12px;
}

.container-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.switch-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.setting-label {
  font-size: 14px;
  color: var(--text-color);
  font-weight: 500;
}

.container-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 500;
}

.container-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  padding: 8px;
  background: var(--n-color);
  border-radius: 4px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-color);
}

.container-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.container-ports {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.container-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.logs-container {
  background: rgba(0, 0, 0, 0.3);
  color: var(--text-color);
  padding: 12px;
  max-height: 400px;
  overflow: auto;
  font-size: 12px;
  font-family: monospace;
  border-radius: 4px;
}
</style>
