<template>
  <div class="container-panel">
    <!-- 顶部工具栏 -->
    <div class="toolbar-row">
      <div class="toolbar-left">
        <n-button type="primary" secondary @click="fetchContainers(true)" :loading="loading">
          刷新
        </n-button>
        <n-button type="error" secondary @click="handlePruneContainers" :loading="loadingPrune">
          清理停止的容器
        </n-button>
        <div class="enhanced-toggle">
          <n-text depth="3">增强监控</n-text>
          <n-switch v-model:value="enhancedMode" size="small" />
          <n-tooltip trigger="hover">
            <template #trigger>
              <n-icon size="16" depth="3" style="cursor: help"><MagnifyingGlassIcon /></n-icon>
            </template>
            开启后将实时获取 CPU、内存占用、IP 及运行时间。关闭可降低服务器负担。
          </n-tooltip>
        </div>
      </div>

      <n-input
        v-model:value="searchQuery"
        placeholder="搜索容器名称或镜像..."
        clearable
        class="search-input"
      >
        <template #prefix>
          <n-icon><MagnifyingGlassIcon /></n-icon>
        </template>
      </n-input>
    </div>

    <!-- 卡片网格 -->
    <n-spin :show="loading">
      <div v-if="filteredContainers.length" class="container-grid">
        <div
          v-for="row in filteredContainers"
          :key="row.id"
          class="container-card"
          :class="{ 'is-running': row.status === 'running' }"
        >
          <!-- 卡片头部：名称 + 状态 -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="container-name text-truncate">{{ row.name }}</n-text>
              <n-tooltip v-if="containerSettings[row.name]?.auto_update" trigger="hover">
                <template #trigger>
                  <n-icon size="16" color="#18a058" class="auto-update-icon"><ArrowPathIcon /></n-icon>
                </template>
                已开启自动更新
              </n-tooltip>
            </div>
            <n-tag
              :type="row.status === 'running' ? 'success' : 'error'"
              size="small"
              round
            >
              {{ statusMap[row.status] || row.status }}
            </n-tag>
          </div>

          <!-- 容器 ID -->
          <div class="card-id text-truncate">{{ row.id }}</div>

          <!-- 镜像信息 -->
          <div class="card-row">
            <span class="row-label">镜像</span>
            <div class="row-value image-value">
              <n-text
                depth="3"
                class="image-name text-truncate"
                style="cursor: pointer"
                @click="checkSingleUpdate(row.image)"
              >
                {{ row.image }}
              </n-text>
              <n-tag
                v-if="updateInfo[row.image]?.has_update"
                size="tiny"
                type="error"
                quaternary
              >
                NEW
              </n-tag>
              <n-button
                v-else-if="!updateInfo[row.image] && !loadingActions[row.image]"
                size="tiny"
                quaternary
                circle
                class="check-update-btn"
                @click="checkSingleUpdate(row.image)"
              >
                <template #icon><n-icon size="14"><ArrowDownTrayIcon /></n-icon></template>
              </n-button>
              <n-text v-else-if="loadingActions[row.image]" depth="3" style="font-size: 10px">...</n-text>
            </div>
          </div>

          <!-- 增强监控信息 -->
          <template v-if="enhancedMode">
            <div class="card-row" v-if="row.status === 'running' && containerStats[row.name]">
              <span class="row-label">资源</span>
              <div class="row-value">
                <div class="stats-bar">
                  <span class="stat-item">CPU: {{ containerStats[row.name].cpu }}</span>
                  <span class="stat-item">内存: {{ containerStats[row.name].mem_perc }}</span>
                </div>
                <n-text depth="3" style="font-size: 10px">{{ containerStats[row.name].mem }}</n-text>
              </div>
            </div>
            <div class="card-row">
              <span class="row-label">IP</span>
              <n-text depth="2" class="mono-text">{{ row.ip || '--' }}</n-text>
            </div>
            <div class="card-row">
              <span class="row-label">运行</span>
              <n-text depth="3" style="font-size: 12px">{{ formatUptime(row.uptime) }}</n-text>
            </div>
          </template>

          <!-- 端口映射 -->
          <div class="card-row" v-if="getPortBindings(row).length || containerSettings[row.name]?.custom_port">
            <span class="row-label">端口</span>
            <div class="row-value port-list">
              <n-button
                v-for="(port, idx) in getPortBindings(row)"
                :key="idx"
                size="tiny"
                type="primary"
                quaternary
                @click="openPort(getTargetIp(), port.hostPort)"
              >
                {{ port.label }}
              </n-button>
              <n-button
                v-if="containerSettings[row.name]?.custom_port"
                size="tiny"
                type="warning"
                secondary
                @click="openPort(getTargetIp(), containerSettings[row.name].custom_port)"
              >
                {{ containerSettings[row.name].custom_port }} (自定)
              </n-button>
            </div>
          </div>

          <!-- 无端口时的设置入口 -->
          <div class="card-row" v-if="!getPortBindings(row).length && !containerSettings[row.name]?.custom_port">
            <span class="row-label">端口</span>
            <n-text depth="3" style="font-size: 11px">无映射</n-text>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <n-button
              size="small"
              :type="row.status === 'running' ? 'error' : 'primary'"
              secondary
              :loading="loadingActions[row.id]"
              @click="handleAction(row.id, row.status === 'running' ? 'stop' : 'start')"
            >
              {{ row.status === 'running' ? '停止' : '启动' }}
            </n-button>
            <n-button
              size="small"
              :type="updateInfo[row.image]?.has_update ? 'error' : 'warning'"
              :secondary="!updateInfo[row.image]?.has_update"
              :pulse="!!updateInfo[row.image]?.has_update"
              :loading="loadingActions[row.id]"
              @click="handleAction(row.id, 'recreate')"
            >
              {{ updateInfo[row.image]?.has_update ? '发现新镜像' : '更新' }}
            </n-button>
            <n-button
              size="small"
              type="error"
              secondary
              :loading="loadingActions[row.id]"
              @click="handleDelete(row)"
            >
              删除
            </n-button>
            <n-button
              size="small"
              type="info"
              secondary
              @click="showLogs(row.id, row.name)"
            >
              日志
            </n-button>
            <n-button
              size="small"
              type="info"
              secondary
              @click="openTerminal(row)"
            >
              终端
            </n-button>
            <n-button
              size="small"
              secondary
              @click="openSettingsModal(row.name)"
            >
              设置
            </n-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-else-if="!loading"
        description="暂无容器"
        style="padding: 60px 0"
      />
    </n-spin>

    <!-- 日志弹窗 -->
    <n-modal v-model:show="showLogsModal" preset="card" title="查看日志" style="width: 80vw">
      <pre class="logs-container">{{ containerLogs }}</pre>
    </n-modal>

    <!-- 容器设置弹窗 -->
    <n-modal v-model:show="showSettingsModal" preset="card" title="容器设置" style="width: 400px">
      <n-space vertical>
        <n-form-item label="自定义访问端口">
          <n-input v-model:value="settingsForm.custom_port" placeholder="Host 模式或未识别端口跳转" />
        </n-form-item>
        <n-form-item label="自动更新镜像">
          <n-switch v-model:value="settingsForm.auto_update" />
          <template #feedback>开启后，系统将每日凌晨 03:00 检查并自动升级该容器镜像。</template>
        </n-form-item>
        <n-space justify="end">
          <n-button @click="showSettingsModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="saveSettings">
            保存设置
          </n-button>
        </n-space>
      </n-space>
    </n-modal>

    <!-- 终端弹窗 -->
    <terminal-modal
      v-model:show="showTerminalModal"
      :host-id="hostId || ''"
      :container-id="currentContainer.id"
      :container-name="currentContainer.name"
      :command="currentContainer.shell"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, h, computed } from 'vue'
import { NTag, NButton, NSpace, NIcon, NModal, NText, NFormItem, NInput, NSpin, NEmpty, useMessage, useDialog, NRadioGroup, NRadioButton, NSwitch, NTooltip } from 'naive-ui'
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  MagnifyingGlassIcon
} from '@heroicons/vue/24/outline'
import axios from 'axios'
import TerminalModal from './TerminalModal.vue'
import { useDockerStore } from '@/store/dockerStore'

const props = defineProps<{
  hostId: string | null
  hosts: any[]
}>()

const message = useMessage()
const dialog = useDialog()
const dockerStore = useDockerStore()

const containers = computed(() => dockerStore.containers[props.hostId || ''] || [])
const containerStats = computed(() => dockerStore.containerStats[props.hostId || ''] || {})
const loading = computed(() => {
  const cacheKey = `containers_${props.hostId}_${enhancedMode.value}`
  return dockerStore.loading[cacheKey] || false
})

const loadingPrune = ref(false)
const searchQuery = ref('')
const updateInfo = ref<Record<string, any>>({})

const filteredContainers = computed(() => {
  const data = containers.value
  if (!searchQuery.value) return data
  const query = searchQuery.value.toLowerCase()
  return data.filter((c: any) =>
    c.name.toLowerCase().includes(query) ||
    c.image.toLowerCase().includes(query)
  )
})
const loadingActions = ref<Record<string, boolean>>({})
const containerSettings = ref<Record<string, any>>({})
const containerLogs = ref('')
const showLogsModal = ref(false)
const showSettingsModal = ref(false)
const showTerminalModal = ref(false)
const currentContainer = ref({ id: '', name: '', shell: '/bin/bash' })
const settingsForm = ref({ name: '', custom_port: '', auto_update: false })
const enhancedMode = ref(localStorage.getItem('lens_docker_enhanced') === 'true')

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

// 状态本地化
const statusMap: Record<string, string> = {
  'running': '运行中',
  'exited': '已停止',
  'restarting': '重启中',
  'paused': '已暂停',
  'created': '已创建',
  'removing': '移除中',
  'dead': '已失效'
}

// 辅助函数：获取目标 IP
const getTargetIp = () => {
  const hostsList = Array.isArray(props.hosts) ? props.hosts : []
  const currentHost = hostsList.find(h => h && h.id === props.hostId)
  return (!currentHost?.ssh_host || currentHost.ssh_host === '127.0.0.1') ? window.location.hostname : currentHost.ssh_host
}

// 辅助函数：获取端口绑定
const getPortBindings = (row: any) => {
  const tags: { label: string; hostPort: string }[] = []
  if (row.ports) {
    for (const [containerPort, bindings] of Object.entries(row.ports)) {
      if (bindings && Array.isArray(bindings)) {
        bindings.forEach((b: any) => {
          tags.push({ label: `${b.HostPort}->${containerPort}`, hostPort: b.HostPort })
        })
      }
    }
  }
  return tags
}

// 辅助函数：打开端口
const openPort = (ip: string, port: string) => {
  window.open(`http://${ip}:${port}`, '_blank')
}

// 辅助函数：格式化运行时间
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

let statsTimer: any = null
const startStatsTimer = () => {
  if (statsTimer) clearInterval(statsTimer)
  if (enhancedMode.value) {
    statsTimer = setInterval(() => {
      if (props.hostId) dockerStore.fetchStats(props.hostId)
    }, 10000)
  }
}

watch(() => props.hostId, () => {
  fetchContainers()
  startStatsTimer()
}, { immediate: true })

import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (statsTimer) clearInterval(statsTimer)
})

const handleAction = async (id: string, action: string) => {
  loadingActions.value[id] = true
  try {
    const res = await axios.post(`/api/docker/${props.hostId}/containers/${id}/action`, { action })
    if (res.data.async) {
      message.info(res.data.message || '任务已在后台启动，请留意系统通知')
    } else {
      message.success('指令已执行')
    }
    setTimeout(() => fetchContainers(true), 2000)
  } catch (e: any) {
    const errorMsg = e.response?.data?.detail || e.message || '操作失败'
    message.error(`操作失败: ${errorMsg}`)
  } finally {
    loadingActions.value[id] = false
  }
}

const handleDelete = (row: any) => {
  dialog.error({
    title: '确认删除容器',
    content: `确定要彻底删除容器 "${row.name}" 吗？此操作不可撤销。`,
    positiveText: '确认删除',
    negativeText: '取消',
    onPositiveClick: () => handleAction(row.id, 'remove')
  })
}

const handlePruneContainers = async () => {
  if (!props.hostId) return
  dialog.warning({
    title: '确认清理容器',
    content: '此操作将永久删除所有处于停止状态的容器。',
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      loadingPrune.value = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune-containers`)
        message.success(res.data.message || '容器清理任务已启动')
        setTimeout(() => fetchContainers(true), 3000)
      } catch (e) {
        message.error('请求失败')
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

  const selectedShell = ref('/bin/bash')
  const shellOptions = [
    { label: 'bash', value: '/bin/bash' },
    { label: 'sh', value: '/bin/sh' },
    { label: 'ash', value: '/bin/ash' }
  ]

  dialog.info({
    title: '选择终端 Shell',
    content: () => h('div', { style: 'margin-top: 10px' }, [
      h(NRadioGroup, {
        value: selectedShell.value,
        'onUpdate:value': (val: string) => selectedShell.value = val,
        name: 'shell-type'
      }, {
        default: () => shellOptions.map(opt => h(NRadioButton, {
          key: opt.value,
          value: opt.value,
          label: opt.label
        }))
      })
    ]),
    positiveText: '进入终端',
    negativeText: '取消',
    onPositiveClick: () => {
      currentContainer.value = {
        id: row.full_id || row.id,
        name: row.name,
        shell: selectedShell.value
      }
      showTerminalModal.value = true
    }
  })
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
  message.success('设置已保存')
  showSettingsModal.value = false
  fetchContainers(true)
}

const checkSingleUpdate = async (image: string) => {
  if (!props.hostId || !image) return
  loadingActions.value[image] = true
  try {
    const res = await axios.get(`/api/docker/${props.hostId}/check-image-update`, { params: { image } })
    updateInfo.value = { ...updateInfo.value, ...res.data }
    message.success(`镜像 ${image} 检查完成`)
  } catch (e) {
    message.error('检查失败')
  } finally {
    loadingActions.value[image] = false
  }
}

defineExpose({ refresh: fetchContainers })
</script>

<style scoped>
.container-panel {
  width: 100%;
}

/* 工具栏 */
.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.enhanced-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 8px;
}

.search-input {
  width: 250px;
  flex-shrink: 1;
  min-width: 180px;
}

/* 卡片网格：统一一行一个卡片 */
.container-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
  margin-top: 4px;
}

.container-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  background: var(--card-bg-color, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
  transition: border-color var(--transition-normal), box-shadow var(--transition-normal), transform var(--transition-fast);
  position: relative;
  overflow: hidden;
}

.container-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: transparent;
  transition: background var(--transition-normal);
}

.container-card.is-running::before {
  background: var(--color-success, #10B981);
}

.container-card:hover {
  border-color: var(--border-medium, rgba(255, 255, 255, 0.12));
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.container-card:active {
  transform: scale(0.99);
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.container-name {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

.auto-update-icon {
  flex-shrink: 0;
}

.card-id {
  font-size: 10px;
  opacity: 0.5;
  font-family: var(--font-mono, monospace);
  margin-top: -4px;
}

/* 卡片行 */
.card-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  min-width: 0;
}

.row-label {
  flex-shrink: 0;
  width: 36px;
  color: var(--text-color, #fff);
  opacity: 0.5;
  font-size: 11px;
  line-height: 22px;
}

.row-value {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.image-value {
  gap: 6px;
}

.image-name {
  max-width: 100%;
  font-size: 12px;
}

.image-name:hover {
  opacity: 0.8;
}

.check-update-btn {
  opacity: 0.5;
}

.stats-bar {
  display: flex;
  gap: 12px;
  font-size: 11px;
  opacity: 0.7;
  width: 100%;
}

.mono-text {
  font-family: var(--font-mono, monospace);
  font-size: 12px;
}

.port-list {
  gap: 4px;
}

/* 操作按钮 */
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
}

.card-actions .n-button {
  flex: 1 1 auto;
  min-width: 56px;
}

/* 日志 */
.logs-container {
  background-color: rgba(0, 0, 0, 0.3);
  color: var(--text-color);
  padding: 12px;
  max-height: 500px;
  overflow: auto;
  font-size: 12px;
  font-family: var(--font-mono, 'Fira Code', 'JetBrains Mono', monospace);
  border-radius: 4px;
}

/* 移动端适配 */
@media (max-width: 767px) {
  .toolbar-row {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .enhanced-toggle {
    margin-left: 0;
    width: 100%;
    justify-content: flex-start;
  }

  .search-input {
    width: 100%;
  }

  .container-card {
    padding: 12px;
  }

  .card-actions .n-button {
    flex: 1 1 calc(50% - 3px);
    min-width: 0;
  }
}

@media (max-width: 380px) {
  .card-actions .n-button {
    flex: 1 1 100%;
  }
}
</style>
