<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { imageBuilderApi } from '@/api/imageBuilder'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'
import SecretField from '@/components/common/SecretField.vue'

const { success, error: showError, info } = useNotification()
const { confirm } = useConfirm()

// ========== 通用状态 ==========
const activeTab = ref('projects')

// ========== 项目管理 ==========
const projects = ref<any[]>([])
const projectsLoading = ref(false)

// 持久化 Tag 输入（localStorage）
const LS_KEY = 'image_builder_project_tags'
const savedTags = JSON.parse(localStorage.getItem(LS_KEY) || '{}')
const projectTags = reactive<Record<string, string>>(savedTags)
watch(projectTags, (v) => localStorage.setItem(LS_KEY, JSON.stringify(v)), { deep: true })

// 下拉选项
const hostOptions = ref<{ label: string; value: string }[]>([])
const proxyOptions = ref<{ label: string; value: string }[]>([])
const registryOptions = ref<{ label: string; value: string }[]>([])
const registries = ref<any[]>([])

async function fetchProjects() {
  projectsLoading.value = true
  try {
    const data = await imageBuilderApi.getProjects()
    projects.value = Array.isArray(data) ? data : []
    projects.value.forEach((p: any) => {
      if (!projectTags[p.id]) projectTags[p.id] = 'latest'
    })
  } catch {
    showError('加载项目失败')
  } finally {
    projectsLoading.value = false
  }
}

async function fetchOptions() {
  try {
    const [regData, proxData, hostData]: any = await Promise.all([
      imageBuilderApi.getRegistries(),
      imageBuilderApi.getProxies(),
      dockerApi.getHosts()
    ])
    registries.value = Array.isArray(regData) ? regData : []
    registryOptions.value = registries.value.map((r: any) => ({ label: r.name, value: r.id }))

    const proxies = Array.isArray(proxData) ? proxData : []
    proxyOptions.value = proxies.map((p: any) => ({ label: p.name, value: p.id }))

    const hosts = Array.isArray(hostData) ? hostData : []
    hostOptions.value = hosts.map((h: any) => ({ label: h.name, value: h.id }))
  } catch {
    /* ignore */
  }
}

const getRegistry = (id: string) => registries.value.find((r: any) => r.id === id)
const splitPlatforms = (platforms: string) => (platforms || '').split(',').filter((p: string) => p.trim())

// ========== 项目编辑弹窗 ==========
const showProjectDialog = ref(false)
const editingProjectId = ref<string | null>(null)
const projectForm = ref<any>({
  name: '', host_id: '', build_context: '', dockerfile_path: 'Dockerfile',
  local_image_name: '', repo_image_name: '', platforms: 'linux/amd64',
  registry_id: null, proxy_id: null, no_cache: false, auto_cleanup: true
})
const selectedPlatforms = ref<string[]>(['linux/amd64'])
const allPlatforms = ['linux/amd64', 'linux/arm64', 'linux/arm/v7', 'linux/arm/v6', 'linux/386']

function openAddProject() {
  editingProjectId.value = null
  selectedPlatforms.value = ['linux/amd64']
  projectForm.value = {
    name: '',
    host_id: hostOptions.value.length > 0 ? hostOptions.value[0].value : 'local',
    build_context: '', dockerfile_path: 'Dockerfile',
    local_image_name: '', repo_image_name: '', platforms: 'linux/amd64',
    registry_id: null, proxy_id: null, no_cache: false, auto_cleanup: true
  }
  showProjectDialog.value = true
}

function openEditProject(row: any) {
  editingProjectId.value = row.id
  projectForm.value = { ...row }
  selectedPlatforms.value = row.platforms ? row.platforms.split(',').filter((p: string) => p.trim()) : ['linux/amd64']
  showProjectDialog.value = true
}

async function saveProject() {
  projectForm.value.platforms = selectedPlatforms.value.join(',')
  try {
    if (editingProjectId.value) {
      await imageBuilderApi.updateProject(editingProjectId.value, projectForm.value)
    } else {
      await imageBuilderApi.addProject(projectForm.value)
    }
    success('保存成功')
    showProjectDialog.value = false
    fetchProjects()
  } catch {
    showError('保存失败')
  }
}

async function deleteProject(row: any) {
  const ok = await confirm({ title: '确认删除', content: `确定要删除项目 "${row.name}" 吗？`, confirmColor: 'error' })
  if (!ok) return
  try {
    await imageBuilderApi.deleteProject(row.id)
    success('删除成功')
    fetchProjects()
  } catch {
    showError('删除失败')
  }
}

// ========== 构建任务 ==========
async function directBuild(row: any) {
  const tag = projectTags[row.id] || 'latest'
  try {
    await imageBuilderApi.buildProject(row.id, tag)
    success(`任务 [${tag}] 已在后台启动，完成后将通过通知告知`)
  } catch {
    showError('启动构建失败')
  }
}

async function clearAllLogs() {
  const ok = await confirm({
    title: '确认清空',
    content: '该操作将彻底删除所有项目的构建历史及物理日志文件，且不可恢复。是否继续？',
    confirmColor: 'error', confirmText: '确定清空'
  })
  if (!ok) return
  try {
    await imageBuilderApi.clearAllTasks()
    success('历史记录已全部清空')
  } catch {
    showError('清空失败')
  }
}

// ========== 构建历史弹窗 ==========
const showHistoryDialog = ref(false)
const historyProjectId = ref('')
const historyProjectName = ref('')
const historyTasks = ref<any[]>([])
const historyLoading = ref(false)

function openHistory(row: any) {
  historyProjectId.value = row.id
  historyProjectName.value = row.name
  showHistoryDialog.value = true
  fetchHistory()
}

async function fetchHistory() {
  if (!historyProjectId.value) return
  historyLoading.value = true
  try {
    const data = await imageBuilderApi.getTaskLogs(historyProjectId.value)
    historyTasks.value = Array.isArray(data) ? data : []
  } catch {
    showError('获取历史失败')
  } finally {
    historyLoading.value = false
  }
}

async function deleteTaskLog(taskId: string) {
  const ok = await confirm({ title: '确认删除', content: '确定要删除这条构建记录吗？', confirmColor: 'error' })
  if (!ok) return
  try {
    await imageBuilderApi.deleteTaskLog(taskId)
    success('已删除')
    fetchHistory()
  } catch {
    showError('删除失败')
  }
}

// 日志查看器
const showLogViewer = ref(false)
const logLoading = ref(false)
const currentLog = ref('')
const currentLogTaskId = ref('')
const currentLogStatus = ref('')
const logContainerRef = ref<HTMLElement | null>(null)

function getStatusConfig(status: string) {
  const m: Record<string, { label: string; color: string }> = {
    'SUCCESS': { label: '成功', color: 'success' },
    'FAILED': { label: '失败', color: 'error' },
    'PENDING': { label: '处理中', color: 'info' },
    'success': { label: '成功', color: 'success' },
    'failed': { label: '失败', color: 'error' },
    'running': { label: '运行中', color: 'info' },
    'pending': { label: '等待中', color: 'warning' },
  }
  return m[status] || { label: status || '未知', color: 'grey' }
}

function formatDate(createdAt: string) {
  if (!createdAt) return '-'
  return new Date(createdAt).toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
  })
}

function formatDuration(start: string, end: string) {
  const s = new Date(start).getTime(), e = new Date(end).getTime()
  if (isNaN(s) || isNaN(e) || e < s) return '-'
  const sec = Math.floor((e - s) / 1000)
  if (sec < 60) return `${sec}秒`
  const min = Math.floor(sec / 60), rs = sec % 60
  if (min < 60) return `${min}分${rs}秒`
  return `${Math.floor(min / 60)}小时${min % 60}分${rs}秒`
}

async function viewLog(row: any) {
  currentLogTaskId.value = row.id
  currentLogStatus.value = row.status || ''
  showLogViewer.value = true
  await fetchLogContent()
}

async function fetchLogContent() {
  if (!currentLogTaskId.value) return
  logLoading.value = true
  try {
    const data = await imageBuilderApi.getTaskLogContent(currentLogTaskId.value)
    currentLog.value = data?.content || ''
    nextTick(() => {
      if (logContainerRef.value) logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
    })
  } catch {
    currentLog.value = '加载日志失败'
  } finally {
    logLoading.value = false
  }
}

function scrollLogToBottom() {
  nextTick(() => {
    if (logContainerRef.value) logContainerRef.value.scrollTop = logContainerRef.value.scrollHeight
  })
}

// ========== 仓库与凭据 ==========
const regList = ref<any[]>([])
const credList = ref<any[]>([])
const regLoading = ref(false)

async function fetchRegAndCred() {
  regLoading.value = true
  try {
    const [regData, credData]: any = await Promise.all([
      imageBuilderApi.getRegistries(),
      imageBuilderApi.getCredentials()
    ])
    regList.value = Array.isArray(regData) ? regData : []
    credList.value = Array.isArray(credData) ? credData : []
    credOptions.value = credList.value.map((c: any) => ({ label: c.name, value: c.id }))
  } catch {
    showError('加载仓库/凭据失败')
  } finally {
    regLoading.value = false
  }
}

// 仓库编辑
const showRegDialog = ref(false)
const editRegMode = ref(false)
const currentRegId = ref('')
const regForm = ref<any>({ name: '', url: '', is_https: true, credential_id: null })
const credOptions = ref<{ label: string; value: string }[]>([])
const testingRegId = ref('')

function openAddRegistry() {
  editRegMode.value = false
  regForm.value = { name: '', url: '', is_https: true, credential_id: null }
  showRegDialog.value = true
}

function openEditRegistry(row: any) {
  editRegMode.value = true
  currentRegId.value = row.id
  regForm.value = { ...row }
  showRegDialog.value = true
}

async function saveRegistry() {
  try {
    if (editRegMode.value) {
      await imageBuilderApi.updateRegistry(currentRegId.value, regForm.value)
    } else {
      await imageBuilderApi.addRegistry(regForm.value)
    }
    success('已保存')
    showRegDialog.value = false
    fetchRegAndCred()
    fetchOptions()
  } catch {
    showError('保存失败')
  }
}

async function testRegistry(id: string) {
  testingRegId.value = id
  try {
    const data = await imageBuilderApi.testRegistry(id)
    if (data?.success) success(data.message || '连接成功')
    else showError(data?.message || '连接失败')
  } catch {
    showError('测试请求失败')
  } finally {
    testingRegId.value = ''
  }
}

async function deleteRegistry(id: string) {
  const ok = await confirm({
    title: '确认删除',
    content: '删除仓库配置可能导致关联的构建任务失败，是否继续？',
    confirmColor: 'error'
  })
  if (!ok) return
  try {
    await imageBuilderApi.deleteRegistry(id)
    fetchRegAndCred()
    fetchOptions()
  } catch {
    showError('删除失败')
  }
}

// 凭据编辑
const showCredDialog = ref(false)
const editCredMode = ref(false)
const currentCredId = ref('')
const credForm = ref<any>({ name: '', username: '', password: '' })

function openAddCredential() {
  editCredMode.value = false
  credForm.value = { name: '', username: '', password: '' }
  showCredDialog.value = true
}

function openEditCredential(row: any) {
  editCredMode.value = true
  currentCredId.value = row.id
  credForm.value = { name: row.name, username: row.username, password: row.encrypted_password || '' }
  showCredDialog.value = true
}

async function saveCredential() {
  try {
    if (editCredMode.value) {
      await imageBuilderApi.updateCredential(currentCredId.value, credForm.value)
    } else {
      await imageBuilderApi.addCredential(credForm.value)
    }
    success('已保存')
    showCredDialog.value = false
    fetchRegAndCred()
  } catch {
    showError('保存失败')
  }
}

async function deleteCredential(id: string) {
  const ok = await confirm({
    title: '确认删除',
    content: '删除凭据将导致所有使用该凭据的仓库无法登录，是否继续？',
    confirmColor: 'error'
  })
  if (!ok) return
  try {
    await imageBuilderApi.deleteCredential(id)
    fetchRegAndCred()
  } catch {
    showError('删除失败')
  }
}

// ========== 代理设置 ==========
const proxyList = ref<any[]>([])
const proxyLoading = ref(false)

async function fetchProxies() {
  proxyLoading.value = true
  try {
    const data = await imageBuilderApi.getProxies()
    proxyList.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载代理失败')
  } finally {
    proxyLoading.value = false
  }
}

const showProxyDialog = ref(false)
const editProxyMode = ref(false)
const currentProxyId = ref('')
const proxyForm = ref<any>({ name: '', url: '', username: '', password: '' })

function openAddProxy() {
  editProxyMode.value = false
  proxyForm.value = { name: '', url: '', username: '', password: '' }
  showProxyDialog.value = true
}

function openEditProxy(row: any) {
  editProxyMode.value = true
  currentProxyId.value = row.id
  proxyForm.value = { ...row }
  showProxyDialog.value = true
}

async function saveProxy() {
  try {
    if (editProxyMode.value) {
      await imageBuilderApi.updateProxy(currentProxyId.value, proxyForm.value)
    } else {
      await imageBuilderApi.addProxy(proxyForm.value)
    }
    success('已保存')
    showProxyDialog.value = false
    fetchProxies()
    fetchOptions()
  } catch {
    showError('保存失败')
  }
}

async function deleteProxy(id: string) {
  const ok = await confirm({
    title: '确认删除',
    content: '删除代理设置可能影响关联项目的镜像构建，是否继续？',
    confirmColor: 'error'
  })
  if (!ok) return
  try {
    await imageBuilderApi.deleteProxy(id)
    fetchProxies()
    fetchOptions()
  } catch {
    showError('删除失败')
  }
}

// ========== 环境监测 ==========
const selectedHostId = ref<string | null>(null)
const sysHostOptions = ref<{ label: string; value: string }[]>([])
const sysProxyOptions = ref<{ label: string; value: string }[]>([])
const selectedProxyId = ref<string | null>(null)
const sysInfo = ref<any>({
  docker_version: 'Unknown', buildx_version: 'Not Found', builders: [], platforms: []
})
const sysLoading = ref(false)
const sysFixing = ref(false)

async function fetchSysHosts() {
  try {
    const [hData, pData]: any = await Promise.all([
      dockerApi.getHosts(),
      imageBuilderApi.getProxies()
    ])
    const hosts = Array.isArray(hData) ? hData : []
    sysHostOptions.value = hosts.map((h: any) => ({ label: h.name, value: h.id }))
    const proxies = Array.isArray(pData) ? pData : []
    sysProxyOptions.value = proxies.map((p: any) => ({ label: p.name, value: p.id }))

    if (sysHostOptions.value.length > 0 && !selectedHostId.value) {
      selectedHostId.value = sysHostOptions.value[0].value
      fetchSysInfo()
    }
  } catch { /* ignore */ }
}

async function fetchSysInfo() {
  if (!selectedHostId.value) return
  sysLoading.value = true
  try {
    const data = await imageBuilderApi.getSystemInfo(selectedHostId.value)
    sysInfo.value = data || { docker_version: 'Unknown', buildx_version: 'Not Found', builders: [], platforms: [] }
  } catch {
    sysInfo.value = { docker_version: 'Unknown', buildx_version: 'Not Found', builders: [], platforms: [] }
  } finally {
    sysLoading.value = false
  }
}

async function handleRepair() {
  const ok = await confirm({
    title: '初始化构建环境',
    content: '该操作将为远程主机安装 QEMU 仿真支持并配置专用 Buildx 构建器，以实现跨平台（如 ARM64）构建。是否继续？',
    confirmColor: 'warning', confirmText: '立即开始'
  })
  if (!ok) return
  sysFixing.value = true
  try {
    const data = await imageBuilderApi.setupEnv(selectedHostId.value!, selectedProxyId.value || undefined)
    if (data?.success) {
      if (data?.async) {
        info(data.message || '环境初始化任务已在后台启动，请留意系统通知进度')
      } else {
        success('构建环境初始化成功')
        fetchSysInfo()
      }
    } else {
      showError('初始化失败: ' + (data?.message || '未知错误'))
    }
  } catch {
    showError('请求失败')
  } finally {
    sysFixing.value = false
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  fetchProjects()
  fetchOptions()
  fetchRegAndCred()
  fetchProxies()
  fetchSysHosts()
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-hammer-wrench</v-icon>
      Docker 镜像构建与推送
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">模块化管理 Docker 镜像构建项目，支持多平台 (Buildx) 构建、自动推送至私有仓库及代理加速。</p>

    <v-tabs v-model="activeTab" class="mb-4" color="primary">
      <v-tab value="projects"><v-icon start>mdi-folder-outline</v-icon> 项目管理</v-tab>
      <v-tab value="registries"><v-icon start>mdi-database-outline</v-icon> 仓库与凭据</v-tab>
      <v-tab value="proxies"><v-icon start>mdi-swap-horizontal</v-icon> 代理设置</v-tab>
      <v-tab value="system"><v-icon start>mdi-monitor-dashboard</v-icon> 环境监测</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">

      <!-- ==================== 项目管理 ==================== -->
      <v-window-item value="projects">
        <div class="d-flex flex-wrap justify-space-between align-center mb-4">
          <v-btn prepend-icon="mdi-plus" color="primary" variant="flat" size="small" @click="openAddProject">新建项目</v-btn>
          <div class="d-flex ga-2">
            <v-btn variant="tonal" color="info" size="small" prepend-icon="mdi-refresh" @click="fetchProjects">刷新列表</v-btn>
            <v-btn color="error" variant="tonal" size="small" prepend-icon="mdi-delete-sweep-outline" @click="clearAllLogs">清空所有记录</v-btn>
          </div>
        </div>

        <v-progress-linear v-if="projectsLoading" indeterminate color="primary" class="mb-4" />

        <div v-if="projects.length" class="d-flex flex-column ga-3">
          <v-card v-for="row in projects" :key="row.id" class="liquid-glass-card" rounded="xl">
            <div class="pa-4">
              <!-- 头部：项目名 + 仓库标签 -->
              <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-2">
                <span class="text-subtitle-1 font-weight-bold">{{ row.name }}</span>
                <v-chip v-if="getRegistry(row.registry_id)" size="small" color="warning" variant="tonal">
                  {{ getRegistry(row.registry_id).name }}
                </v-chip>
                <v-chip v-else size="small" variant="tonal">默认仓库</v-chip>
              </div>

              <!-- 远程镜像名 -->
              <div class="text-body-2 text-medium-emphasis mb-2" style="word-break:break-all">
                远程镜像: {{ row.repo_image_name || '-' }}
              </div>

              <!-- 平台标签 -->
              <div class="d-flex flex-wrap ga-1 mb-3">
                <v-chip v-for="p in splitPlatforms(row.platforms)" :key="p" size="small" color="info" variant="tonal" label>{{ p }}</v-chip>
              </div>

              <!-- Tag 输入 + 构建 -->
              <div class="d-flex ga-2 mb-3" style="max-width:360px">
                <v-text-field v-model="projectTags[row.id]" density="compact" variant="outlined" label="Tag" hide-details style="flex:0 0 120px" />
                <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-play" @click="directBuild(row)">立即构建</v-btn>
              </div>

              <v-divider class="mb-2" />
              <!-- 操作按钮 -->
              <div class="d-flex flex-wrap ga-2 pt-1">
                <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-history" @click="openHistory(row)">查看历史</v-btn>
                <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-pencil-outline" @click="openEditProject(row)">修改</v-btn>
                <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="deleteProject(row)">删除</v-btn>
              </div>
            </div>
          </v-card>
        </div>

        <div v-else-if="!projectsLoading" class="text-center py-12 text-medium-emphasis">
          <v-icon size="64" color="grey" class="mb-4">mdi-hammer-wrench</v-icon>
          <div>暂无项目</div>
        </div>
      </v-window-item>

      <!-- ==================== 仓库与凭据 ==================== -->
      <v-window-item value="registries">
        <v-progress-linear v-if="regLoading" indeterminate color="primary" class="mb-4" />

        <!-- 仓库配置 -->
        <v-card class="liquid-glass-card mb-6" rounded="xl">
          <v-card-title class="d-flex align-center justify-space-between pa-4 pb-2">
            <span class="text-subtitle-1 font-weight-bold">仓库配置</span>
            <v-btn size="small" color="primary" variant="flat" prepend-icon="mdi-plus" @click="openAddRegistry">添加仓库</v-btn>
          </v-card-title>
          <v-divider />
          <div class="pa-4">
            <div v-if="regList.length" class="d-flex flex-column ga-3">
              <v-card v-for="row in regList" :key="row.id" variant="outlined" rounded="lg" class="pa-3">
                <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-1">
                  <span class="font-weight-bold">{{ row.name }}</span>
                  <v-chip :color="row.is_https ? 'success' : 'warning'" size="small" variant="tonal">
                    {{ row.is_https ? 'HTTPS' : 'HTTP' }}
                  </v-chip>
                </div>
                <div class="text-body-2 text-medium-emphasis mb-2" style="word-break:break-all">{{ row.url }}</div>
                <v-divider class="mb-2" />
                <div class="d-flex flex-wrap ga-2">
                  <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-lan-connect" :loading="testingRegId === row.id" @click="testRegistry(row.id)">测试</v-btn>
                  <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="openEditRegistry(row)">编辑</v-btn>
                  <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="deleteRegistry(row.id)">删除</v-btn>
                </div>
              </v-card>
            </div>
            <div v-else class="text-center py-8 text-medium-emphasis">暂无仓库配置</div>
          </div>
        </v-card>

        <!-- 凭据管理 -->
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="d-flex align-center justify-space-between pa-4 pb-2">
            <span class="text-subtitle-1 font-weight-bold">凭据管理</span>
            <v-btn size="small" color="primary" variant="flat" prepend-icon="mdi-plus" @click="openAddCredential">添加凭据</v-btn>
          </v-card-title>
          <v-divider />
          <div class="pa-4">
            <div v-if="credList.length" class="d-flex flex-column ga-3">
              <v-card v-for="row in credList" :key="row.id" variant="outlined" rounded="lg" class="pa-3">
                <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-1">
                  <span class="font-weight-bold">{{ row.name }}</span>
                  <v-chip size="small" color="info" variant="tonal">{{ row.username }}</v-chip>
                </div>
                <v-divider class="mb-2 mt-2" />
                <div class="d-flex flex-wrap ga-2">
                  <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="openEditCredential(row)">编辑</v-btn>
                  <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="deleteCredential(row.id)">删除</v-btn>
                </div>
              </v-card>
            </div>
            <div v-else class="text-center py-8 text-medium-emphasis">暂无凭据</div>
          </div>
        </v-card>
      </v-window-item>

      <!-- ==================== 代理设置 ==================== -->
      <v-window-item value="proxies">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="d-flex align-center justify-space-between pa-4 pb-2">
            <span class="text-subtitle-1 font-weight-bold">构建代理设置</span>
            <v-btn size="small" color="primary" variant="flat" prepend-icon="mdi-plus" @click="openAddProxy">添加代理</v-btn>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <p class="text-body-2 text-medium-emphasis mb-4">配置 HTTP/HTTPS 代理，用于在构建过程中加速下载基础镜像或依赖包。</p>

            <v-progress-linear v-if="proxyLoading" indeterminate color="primary" class="mb-4" />

            <div v-if="proxyList.length" class="d-flex flex-column ga-3">
              <v-card v-for="row in proxyList" :key="row.id" variant="outlined" rounded="lg" class="pa-3">
                <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-1">
                  <span class="font-weight-bold">{{ row.name }}</span>
                  <v-chip v-if="row.username" size="small" color="info" variant="tonal">已鉴权</v-chip>
                </div>
                <div class="text-body-2 text-medium-emphasis mb-2" style="word-break:break-all">{{ row.url }}</div>
                <v-divider class="mb-2" />
                <div class="d-flex flex-wrap ga-2">
                  <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="openEditProxy(row)">编辑</v-btn>
                  <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="deleteProxy(row.id)">删除</v-btn>
                </div>
              </v-card>
            </div>
            <div v-else-if="!proxyLoading" class="text-center py-8 text-medium-emphasis">暂无代理配置</div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- ==================== 环境监测 ==================== -->
      <v-window-item value="system">
        <!-- 主机选择 + 状态标签 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <div class="d-flex align-center justify-space-between flex-wrap ga-4 pa-4">
            <div class="d-flex align-center ga-3">
              <span class="text-body-2 font-weight-medium">选择监测主机:</span>
              <v-select v-model="selectedHostId" :items="sysHostOptions" item-title="label" item-value="value"
                density="compact" variant="outlined" hide-details style="max-width:220px" @update:model-value="fetchSysInfo" />
            </div>
            <v-chip v-if="sysInfo.platforms?.length" color="success" size="small" variant="tonal" prepend-icon="mdi-check-circle">
              多架构环境就绪
            </v-chip>
            <v-chip v-else-if="sysInfo.docker_version !== 'Unknown'" color="warning" size="small" variant="tonal">
              基础 Docker 就绪
            </v-chip>
          </div>
        </v-card>

        <!-- Docker 服务状态 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="d-flex align-center justify-space-between pa-4 pb-2">
            <span class="text-subtitle-1 font-weight-bold">Docker 服务状态</span>
            <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh" :loading="sysLoading" @click="fetchSysInfo">重新检测</v-btn>
          </v-card-title>
          <v-divider />
          <div class="pa-4">
            <v-row>
              <v-col cols="12" sm="6">
                <v-card variant="outlined" rounded="lg" class="pa-3">
                  <div class="text-caption text-medium-emphasis mb-1">Docker 版本</div>
                  <div class="d-flex align-center ga-2">
                    <span class="font-weight-bold">{{ sysInfo.docker_version }}</span>
                    <v-chip v-if="sysInfo.docker_version !== 'Unknown'" size="x-small" color="success" variant="tonal">运行中</v-chip>
                  </div>
                </v-card>
              </v-col>
              <v-col cols="12" sm="6">
                <v-card variant="outlined" rounded="lg" class="pa-3">
                  <div class="text-caption text-medium-emphasis mb-1">Buildx 构建引擎</div>
                  <div class="d-flex align-center ga-2">
                    <span class="font-weight-bold">{{ sysInfo.buildx_version }}</span>
                    <v-chip v-if="sysInfo.buildx_version !== 'Not Found'" size="x-small" color="success" variant="tonal">就绪</v-chip>
                  </div>
                </v-card>
              </v-col>
            </v-row>
          </div>
        </v-card>

        <!-- 多架构构建支持 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="d-flex align-center justify-space-between pa-4 pb-2">
            <span class="text-subtitle-1 font-weight-bold">多架构构建支持</span>
            <span v-if="sysInfo.platforms?.length" class="text-caption text-success">多架构环境已就绪</span>
          </v-card-title>
          <v-divider />
          <div class="pa-4">
            <div v-if="sysInfo.platforms?.length" class="d-flex flex-wrap ga-2">
              <v-chip v-for="plat in sysInfo.platforms" :key="plat" size="small" color="info" variant="tonal">{{ plat }}</v-chip>
            </div>
            <div v-else class="text-center py-4 text-medium-emphasis">未检测到多架构支持</div>
          </div>
        </v-card>

        <!-- 构建器列表 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4 pb-2">
            <span class="text-subtitle-1 font-weight-bold">Buildx 构建器列表 (Builders)</span>
          </v-card-title>
          <v-divider />
          <div class="pa-4">
            <pre v-if="sysInfo.builders?.length" class="code-block">{{ sysInfo.builders.join('\n') }}</pre>
            <div v-else class="text-center py-4 text-medium-emphasis">未发现活跃构建器</div>
          </div>
        </v-card>

        <!-- 底部操作区 -->
        <div class="d-flex flex-column align-center ga-4 mt-6">
          <div class="d-flex align-center ga-3">
            <span class="text-body-2">初始化环境时绑定代理:</span>
            <v-select v-model="selectedProxyId" :items="sysProxyOptions" item-title="label" item-value="value"
              density="compact" variant="outlined" hide-details clearable placeholder="不使用代理" style="max-width:200px" />
          </div>
          <div class="d-flex flex-wrap justify-center ga-3">
            <v-btn variant="tonal" color="primary" prepend-icon="mdi-refresh" :loading="sysLoading" @click="fetchSysInfo">手动刷新环境状态</v-btn>
            <v-btn variant="tonal" color="warning" prepend-icon="mdi-wrench-outline" :loading="sysFixing" @click="handleRepair">一键初始化/修复构建环境</v-btn>
          </div>
        </div>
      </v-window-item>
    </v-window>

    <!-- ==================== 项目编辑弹窗 ==================== -->
    <GlassDialog v-model="showProjectDialog" :max-width="620" icon="mdi-folder-outline" :title="editingProjectId ? '编辑项目' : '新建项目'">
  <v-text-field v-model="projectForm.name" label="项目名称" variant="outlined" density="compact"
            hint="例如: My App" persistent-hint class="mb-3" />
          <v-select v-model="projectForm.host_id" :items="hostOptions" item-title="label" item-value="value"
            label="构建主机" variant="outlined" density="compact" hint="选择执行构建的服务器" persistent-hint class="mb-3" />
          <v-text-field v-model="projectForm.build_context" label="构建上下文" variant="outlined" density="compact"
            hint="宿主机目录, 例如: /root/my-app" persistent-hint class="mb-3" />
          <v-text-field v-model="projectForm.dockerfile_path" label="Dockerfile 路径" variant="outlined" density="compact"
            hint="相对于上下文的路径, 例如: Dockerfile" persistent-hint class="mb-3" />
          <v-text-field v-model="projectForm.local_image_name" label="本地镜像名" variant="outlined" density="compact"
            hint="例如: my-app" persistent-hint class="mb-3" />
          <v-text-field v-model="projectForm.repo_image_name" label="远程镜像名" variant="outlined" density="compact"
            hint="例如: username/my-app" persistent-hint class="mb-3" />

          <div class="mb-3">
            <div class="text-body-2 text-medium-emphasis mb-2">目标平台</div>
            <v-checkbox v-for="plat in allPlatforms" :key="plat" v-model="selectedPlatforms" :value="plat"
              :label="plat.replace('linux/', '')" density="compact" hide-details class="d-inline-flex mr-4" color="primary" />
          </div>

          <v-select v-model="projectForm.registry_id" :items="registryOptions" item-title="label" item-value="value"
            label="目标仓库" variant="outlined" density="compact" clearable hint="选择推送仓库 (选填)" persistent-hint class="mb-3" />
          <v-select v-model="projectForm.proxy_id" :items="proxyOptions" item-title="label" item-value="value"
            label="构建代理" variant="outlined" density="compact" clearable hint="选择代理 (选填)" persistent-hint class="mb-3" />

          <div class="d-flex ga-4">
            <v-switch v-model="projectForm.no_cache" label="禁用缓存" density="compact" color="primary" hide-details />
            <v-switch v-model="projectForm.auto_cleanup" label="自动清理本地镜像" density="compact" color="primary" hide-details />
          </div>
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveProject">保存项目</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 构建历史弹窗 ==================== -->
    <GlassDialog v-model="showHistoryDialog" :max-width="800" icon="mdi-history" :title="'构建历史 —' + (historyProjectName)" :cancel-visible="false">
  <v-progress-linear v-if="historyLoading" indeterminate color="primary" class="mb-4" />
          <div v-if="historyTasks.length" class="d-flex flex-column ga-3">
            <v-card v-for="row in historyTasks" :key="row.id" variant="outlined" rounded="lg" class="pa-3">
              <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-1">
                <span class="font-weight-bold" style="overflow:hidden;text-overflow:ellipsis">{{ row.image_name || row.tag || '-' }}</span>
                <v-chip :color="getStatusConfig(row.status).color" size="small" variant="tonal">
                  {{ getStatusConfig(row.status).label }}
                </v-chip>
              </div>
              <div v-if="row.platforms" class="d-flex flex-wrap ga-1 mb-2">
                <v-chip v-for="p in splitPlatforms(row.platforms)" :key="p" size="x-small" color="info" variant="tonal" label>{{ p }}</v-chip>
              </div>
              <div class="d-flex flex-wrap ga-2 text-caption text-medium-emphasis mb-2">
                <span v-if="row.host_name">构建主机: {{ row.host_name }}</span>
                <span>开始: {{ formatDate(row.created_at) }}</span>
                <span v-if="row.completed_at">完成: {{ formatDate(row.completed_at) }}</span>
                <span v-if="row.completed_at && row.created_at">耗时: {{ formatDuration(row.created_at, row.completed_at) }}</span>
              </div>
              <v-divider class="mb-2" />
              <div class="d-flex ga-2">
                <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-text-box-outline" @click="viewLog(row)">查看日志</v-btn>
                <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="deleteTaskLog(row.id)">删除</v-btn>
              </div>
            </v-card>
          </div>
          <div v-else-if="!historyLoading" class="text-center py-8 text-medium-emphasis">暂无构建历史</div>
</GlassDialog>

    <!-- ==================== 日志查看器弹窗 ==================== -->
    <GlassDialog v-model="showLogViewer" :max-width="1200" :cancel-visible="false">
      <template #title>
        <v-icon start>mdi-text-box-outline</v-icon>
        构建日志
        <v-chip v-if="currentLogStatus" :color="getStatusConfig(currentLogStatus).color" size="small" variant="tonal" class="ml-3">
          {{ getStatusConfig(currentLogStatus).label }}
        </v-chip>
        <span v-if="!logLoading && currentLog" class="text-caption text-medium-emphasis ml-2">共 {{ currentLog.split('\n').length }} 行</span>
        <v-spacer />
        <div class="d-flex ga-2">
          <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh" :loading="logLoading" @click="fetchLogContent">刷新</v-btn>
          <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-arrow-down" @click="scrollLogToBottom">滚动到底部</v-btn>
        </div>
      </template>
      <v-progress-linear v-if="logLoading" indeterminate color="primary" class="mb-2" />
      <pre ref="logContainerRef" class="code-block code-block--flat">{{ currentLog || '暂无日志内容' }}</pre>
    </GlassDialog>

    <!-- ==================== 仓库编辑弹窗 ==================== -->
    <GlassDialog v-model="showRegDialog" :max-width="500" icon="mdi-database-outline" :title="editRegMode ? '编辑仓库' : '添加仓库'">
  <v-text-field v-model="regForm.name" label="名称" variant="outlined" density="compact"
            hint="例如: Docker Hub" persistent-hint class="mb-3" />
          <v-text-field v-model="regForm.url" label="URL" variant="outlined" density="compact"
            hint="例如: docker.io" persistent-hint class="mb-3" />
          <v-switch v-model="regForm.is_https" label="HTTPS" density="compact" color="primary" class="mb-3" />
          <v-select v-model="regForm.credential_id" :items="credOptions" item-title="label" item-value="value"
            label="关联凭据" variant="outlined" density="compact" clearable class="mb-3" />
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveRegistry">保存</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 凭据编辑弹窗 ==================== -->
    <GlassDialog v-model="showCredDialog" :max-width="500" icon="mdi-key-outline" :title="editCredMode ? '编辑凭据' : '添加凭据'">
  <v-text-field v-model="credForm.name" label="名称" variant="outlined" density="compact"
            hint="例如: my-docker-hub-login" persistent-hint class="mb-3" />
          <v-text-field v-model="credForm.username" label="用户名" variant="outlined" density="compact" class="mb-3" />
<SecretField v-model="credForm.password" label="密码/Token"
  hint="请输入密码或仓库 Token" persistent-hint class="mb-3" :show-copy="false" />
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveCredential">保存</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 代理编辑弹窗 ==================== -->
    <GlassDialog v-model="showProxyDialog" :max-width="500" icon="mdi-swap-horizontal" :title="editProxyMode ? '编辑代理' : '添加代理'">
  <v-text-field v-model="proxyForm.name" label="名称" variant="outlined" density="compact"
            hint="例如: Clash" persistent-hint class="mb-3" />
          <v-text-field v-model="proxyForm.url" label="代理地址" variant="outlined" density="compact"
            hint="例如: http://192.168.1.5:7890" persistent-hint class="mb-3" />
          <v-text-field v-model="proxyForm.username" label="用户名" variant="outlined" density="compact"
            hint="可选" persistent-hint class="mb-3" />
<SecretField v-model="proxyForm.password" label="密码"
  hint="可选" persistent-hint class="mb-3" :show-copy="false" />
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveProxy">保存</v-btn>
  </template>
</GlassDialog>
  </v-container>
</template>

