<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import { useDockerHost } from '../composables/useDockerHost'
import GlassDialog from '@/components/common/GlassDialog.vue'
import ContainerTerminalDialog from './ContainerTerminalDialog.vue'

const { success, error: showError, info, warning } = useNotification()
const { confirm } = useConfirm()
const { currentHost } = useDockerHost()

const props = defineProps<{
  active: boolean
  hostId: string | null
}>()

// ========== 自动加载 ==========
const loaded = ref(false)
watch([() => props.active, () => props.hostId], ([active, hostId]) => {
  if (active && hostId) { loadContainers(); loadContainerSettings(); loaded.value = true }
})
onMounted(() => { if (props.active && props.hostId) { loadContainers(); loadContainerSettings(); loaded.value = true } })

// ========== 容器列表 ==========
const containers = ref<any[]>([])
const containerStats = ref<Record<string, any>>({})
const searchQuery = ref('')
const enhancedMode = ref(localStorage.getItem('lens_docker_enhanced') === 'true')
const loading = ref(false)
const loadingActions = ref<Record<string, boolean>>({})

const statusMap: Record<string, { label: string; color: string }> = {
  running: { label: '运行中', color: 'success' },
  exited: { label: '已停止', color: 'error' },
  restarting: { label: '重启中', color: 'warning' },
  paused: { label: '已暂停', color: 'info' },
  created: { label: '已创建', color: 'grey' },
  removing: { label: '移除中', color: 'warning' },
  dead: { label: '已失效', color: 'error' },
}

const filteredContainers = computed(() => {
  if (!searchQuery.value) return containers.value
  const q = searchQuery.value.toLowerCase()
  return containers.value.filter((c: any) => c.name?.toLowerCase().includes(q) || c.image?.toLowerCase().includes(q))
})

async function loadContainers() {
  if (!props.hostId) return
  try {
    loading.value = true
    const data = await dockerApi.getContainers(props.hostId, enhancedMode.value)
    containers.value = Array.isArray(data) ? data : []
    if (enhancedMode.value) loadStats()
  } catch { showError('加载容器列表失败') }
  finally { loading.value = false }
}

// ========== 增强监控 ==========
async function loadStats() {
  if (!props.hostId || !enhancedMode.value) return
  try {
    const data = await dockerApi.getContainerStats(props.hostId)
    if (data && typeof data === 'object') containerStats.value = data
  } catch { /* ignore */ }
}

let statsTimer: ReturnType<typeof setInterval> | null = null
function startStatsTimer() {
  if (statsTimer) clearInterval(statsTimer)
  if (enhancedMode.value && props.hostId) { statsTimer = setInterval(loadStats, 10000) }
}

watch(enhancedMode, (val) => {
  localStorage.setItem('lens_docker_enhanced', String(val))
  loadContainers()
  if (val) startStatsTimer()
  else if (statsTimer) { clearInterval(statsTimer); statsTimer = null }
})

// ========== 容器操作 ==========
async function containerAction(containerId: string, action: string) {
  if (!props.hostId) return
  loadingActions.value[containerId] = true
  try {
    const res = await dockerApi.containerAction(props.hostId, containerId, action)
    if (res?.async) info(res.message || '任务已在后台启动')
    else success('指令已执行')
    setTimeout(() => loadContainers(), 2000)
  } catch (err: any) { showError(err.message || '操作失败') }
  finally { loadingActions.value[containerId] = false }
}

async function handleDeleteContainer(row: any) {
  const ok = await confirm({ title: '确认删除容器', content: `确定要彻底删除容器 "${row.name}" 吗？此操作不可撤销。`, confirmColor: 'error' })
  if (!ok) return
  await containerAction(row.id, 'remove')
}

async function handlePruneContainers() {
  if (!props.hostId) return
  const ok = await confirm({ title: '确认清理容器', content: '此操作将永久删除所有处于停止状态的容器。', confirmColor: 'warning' })
  if (!ok) return
  loadingActions.value['prune'] = true
  try {
    const res = await dockerApi.pruneContainers(props.hostId)
    success(res?.message || '容器清理任务已启动')
    setTimeout(() => loadContainers(), 3000)
  } catch { showError('清理失败') }
  finally { loadingActions.value['prune'] = false }
}

// ========== 日志 ==========
const showLogsDialog = ref(false)
const logContainerName = ref('')
const containerLogs = ref('')
const loadingLogs = ref(false)

async function showLogs(containerId: string, name: string) {
  if (!props.hostId) return
  logContainerName.value = name
  loadingLogs.value = true
  showLogsDialog.value = true
  try {
    const res = await dockerApi.getContainerLogs(props.hostId, containerId, 300)
    containerLogs.value = res?.logs || '无日志'
  } catch { containerLogs.value = '加载日志失败' }
  finally { loadingLogs.value = false }
}

// ========== 容器设置 ==========
const showSettingsDialog = ref(false)
const settingsForm = ref({ name: '', custom_port: '', auto_update: false })
const containerSettings = ref<Record<string, any>>({})

async function loadContainerSettings() {
  try { const data = await dockerApi.getContainerSettings(); containerSettings.value = data || {} }
  catch { /* ignore */ }
}

function openSettingsModal(name: string) {
  const current = containerSettings.value[name] || {}
  settingsForm.value = { name, custom_port: current.custom_port || '', auto_update: current.auto_update || false }
  showSettingsDialog.value = true
}

async function saveContainerSettings() {
  try {
    await dockerApi.saveContainerSettings(settingsForm.value.name, { custom_port: settingsForm.value.custom_port, auto_update: settingsForm.value.auto_update, host_id: props.hostId })
    success('设置已保存')
    showSettingsDialog.value = false
    loadContainerSettings()
  } catch { showError('保存设置失败') }
}

// ========== 镜像更新检测 ==========
const updateInfo = ref<Record<string, any>>({})

async function checkSingleUpdate(image: string) {
  if (!props.hostId || !image) return
  loadingActions.value[image] = true
  try {
    const res = await dockerApi.checkImageUpdate(props.hostId, image)
    updateInfo.value = { ...updateInfo.value, ...res }
    success(`镜像 ${image} 检查完成`)
  } catch { showError('检查失败') }
  finally { loadingActions.value[image] = false }
}

// ========== 终端 ==========
const showTerminalDialog = ref(false)
const terminalContainer = ref({ id: '', name: '', shell: '/bin/bash' })
const showShellDialog = ref(false)
const selectedShell = ref('/bin/bash')
const shellOptions = [
  { title: 'bash', value: '/bin/bash' },
  { title: 'sh', value: '/bin/sh' },
  { title: 'ash', value: '/bin/ash' },
]

function openTerminal(row: any) {
  if (row.status !== 'running') {
    warning('只有运行中的容器可以进入终端')
    return
  }
  terminalContainer.value = { id: row.full_id || row.id, name: row.name, shell: '/bin/bash' }
  selectedShell.value = '/bin/bash'
  showShellDialog.value = true
}

function confirmOpenTerminal() {
  terminalContainer.value.shell = selectedShell.value
  showShellDialog.value = false
  showTerminalDialog.value = true
}

// ========== 工具函数 ==========
function getTargetIp() {
  const host = currentHost.value
  if (!host?.ssh_host || host.ssh_host === '127.0.0.1') return window.location.hostname
  return host.ssh_host
}

function getPortBindings(row: any) {
  const tags: { label: string; hostPort: string }[] = []
  if (row.ports) {
    for (const [containerPort, bindings] of Object.entries(row.ports)) {
      if (Array.isArray(bindings)) {
        (bindings as any[]).forEach((b: any) => { tags.push({ label: `${b.HostPort}->${containerPort}`, hostPort: b.HostPort }) })
      }
    }
  }
  return tags
}

function openPort(ip: string, port: string) { window.open(`http://${ip}:${port}`, '_blank') }

function formatUptime(uptime: string) {
  if (!uptime) return '--'
  if (uptime.startsWith('Up ')) {
    return uptime.replace('Up ', '已运行 ').replace(/ days?/, ' 天').replace(/ hours?/, ' 小时').replace(/ minutes?/, ' 分钟').replace(/ seconds?/, ' 秒')
  }
  return uptime
}

// ========== 生命周期 ==========
onUnmounted(() => { if (statsTimer) clearInterval(statsTimer) })

defineExpose({ loadContainers, loadContainerSettings })
</script>

<template>
  <div>
    <div class="control-row mb-4">
      <v-text-field v-model="searchQuery" prepend-inner-icon="mdi-magnify" placeholder="搜索容器名称或镜像..." variant="outlined" density="compact" hide-details clearable class="flex-grow-0" style="max-width:360px" />
      <v-spacer />
      <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" color="info" @click="loadContainers" :loading="loading">刷新</v-btn>
      <v-btn prepend-icon="mdi-delete-sweep" variant="tonal" size="small" color="error" :loading="loadingActions['prune']" @click="handlePruneContainers">清理停止的容器</v-btn>
      <v-switch v-model="enhancedMode" label="增强监控" density="compact" hide-details color="primary" />
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-row v-if="!loading && filteredContainers.length === 0">
      <v-col cols="12" class="text-center py-12 text-medium-emphasis">
        <v-icon size="64" color="grey" class="mb-4">mdi-package-variant-closed</v-icon>
        <div>暂无容器</div>
      </v-col>
    </v-row>

    <div v-if="filteredContainers.length" class="task-list">
      <v-card
        v-for="row in filteredContainers"
        :key="row.id"
        class="status-card liquid-glass-card"
        :class="{ 'is-running': row.status === 'running' }"
        rounded="lg"
      >
        <!-- 卡片头部 -->
        <div class="card-header pa-4 pb-2">
          <div class="card-title">
            <v-icon start :color="statusMap[row.status]?.color || 'grey'" size="20">mdi-package-variant-closed</v-icon>
            <span class="text-subtitle-2 font-weight-bold text-truncate">{{ row.name }}</span>
            <v-icon v-if="containerSettings[row.name]?.auto_update" size="16" color="success">mdi-autorenew</v-icon>
          </div>
          <v-chip :color="statusMap[row.status]?.color || 'grey'" size="small" variant="tonal" label>
            {{ statusMap[row.status]?.label || row.status }}
          </v-chip>
        </div>

        <!-- 信息行 -->
        <div class="card-info px-4 pb-2">
          <div class="info-item">
            <span class="info-label">容器ID</span>
            <span class="font-mono text-caption text-medium-emphasis">{{ row.id }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">镜像</span>
            <span class="font-mono text-body-2 text-truncate" style="cursor:pointer" @click="checkSingleUpdate(row.image)">{{ row.image }}</span>
            <v-chip v-if="updateInfo[row.image]?.has_update" size="x-small" color="error" variant="flat">NEW</v-chip>
            <v-progress-circular v-else-if="loadingActions[row.image]" size="12" width="2" indeterminate color="primary" />
          </div>
          <template v-if="enhancedMode && row.status === 'running' && containerStats[row.name]">
            <div class="info-item">
              <span class="info-label">资源</span>
              <span class="text-caption">CPU: {{ containerStats[row.name].cpu }} | 内存: {{ containerStats[row.name].mem_perc }}</span>
              <span class="text-caption text-medium-emphasis">{{ containerStats[row.name].mem }}</span>
            </div>
          </template>
          <template v-if="enhancedMode">
            <div v-if="row.ip" class="info-item">
              <span class="info-label">IP</span>
              <span class="font-mono text-caption">{{ row.ip }}</span>
            </div>
            <div v-if="row.uptime" class="info-item">
              <span class="info-label">运行</span>
              <span class="text-caption">{{ formatUptime(row.uptime) }}</span>
            </div>
          </template>
          <div class="info-item">
            <span class="info-label">端口</span>
            <template v-if="getPortBindings(row).length || containerSettings[row.name]?.custom_port">
              <v-chip v-for="port in getPortBindings(row)" :key="port.label" size="x-small" variant="tonal" color="primary" @click="openPort(getTargetIp(), port.hostPort)" style="cursor:pointer">{{ port.label }}</v-chip>
              <v-chip v-if="containerSettings[row.name]?.custom_port" size="x-small" variant="tonal" color="warning" @click="openPort(getTargetIp(), containerSettings[row.name].custom_port)" style="cursor:pointer">{{ containerSettings[row.name].custom_port }} (自定)</v-chip>
            </template>
            <span v-else class="text-caption text-medium-emphasis">无映射</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <v-divider class="mt-2" />
        <div class="d-flex flex-wrap ga-2 pa-3">
          <v-btn size="small" :color="row.status === 'running' ? 'error' : 'primary'" variant="tonal" :prepend-icon="row.status === 'running' ? 'mdi-stop' : 'mdi-play'" :loading="loadingActions[row.id]" @click="containerAction(row.id, row.status === 'running' ? 'stop' : 'start')">{{ row.status === 'running' ? '停止' : '启动' }}</v-btn>
          <v-btn size="small" :color="updateInfo[row.image]?.has_update ? 'error' : 'warning'" variant="tonal" prepend-icon="mdi-update" :loading="loadingActions[row.id]" @click="containerAction(row.id, 'recreate')">{{ updateInfo[row.image]?.has_update ? '发现新镜像' : '更新' }}</v-btn>
          <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" :loading="loadingActions[row.id]" @click="handleDeleteContainer(row)">删除</v-btn>
          <v-btn size="small" color="info" variant="tonal" @click="showLogs(row.id, row.name)"><v-icon start>mdi-text-box-outline</v-icon> 日志</v-btn>
          <v-btn size="small" color="success" variant="tonal" prepend-icon="mdi-console" @click="openTerminal(row)">终端</v-btn>
          <v-btn size="small" variant="tonal" color="info" @click="openSettingsModal(row.name)"><v-icon start>mdi-cog-outline</v-icon> 设置</v-btn>
        </div>
      </v-card>
    </div>

    <!-- 日志对话框 -->
    <GlassDialog v-model="showLogsDialog" :max-width="900"
      icon="mdi-text-box-outline" :title="'日志 — ' + logContainerName" cancel-text="关闭"
    >
      <v-progress-linear v-if="loadingLogs" indeterminate color="primary" />
      <pre class="code-block code-block--flat">{{ containerLogs }}</pre>
    </GlassDialog>

    <!-- 容器设置对话框 -->
    <GlassDialog v-model="showSettingsDialog" :max-width="420"
      icon="mdi-cog-outline" :title="'容器设置 — ' + settingsForm.name"
    >
      <v-text-field v-model="settingsForm.custom_port" label="自定义访问端口" variant="outlined" density="compact" hint="Host 模式或未识别端口的跳转地址" persistent-hint class="mb-3" />
      <v-switch v-model="settingsForm.auto_update" label="自动更新镜像" density="compact" color="primary" hint="开启后每日凌晨 03:00 自动检查并升级该容器镜像" persistent-hint />
      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveContainerSettings">保存</v-btn>
      </template>
    </GlassDialog>

    <!-- Shell 选择对话框 -->
    <GlassDialog v-model="showShellDialog" :max-width="380"
      icon="mdi-console" title="选择终端 Shell" cancel-text="取消"
    >
      <v-radio-group v-model="selectedShell" density="compact">
        <v-radio v-for="opt in shellOptions" :key="opt.value" :value="opt.value" :label="opt.title" />
      </v-radio-group>
      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-console" @click="confirmOpenTerminal">进入终端</v-btn>
      </template>
    </GlassDialog>

    <!-- 容器终端对话框 -->
    <ContainerTerminalDialog
      v-model="showTerminalDialog"
      :host-id="hostId || ''"
      :container-id="terminalContainer.id"
      :container-name="terminalContainer.name"
      :command="terminalContainer.shell"
    />
  </div>
</template>
