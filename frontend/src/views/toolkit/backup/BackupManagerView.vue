<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { backupApi } from '@/api/backup'
import type { BackupTask, BackupHistory, PathBrowserItem, GiteaRepo } from '@/api/backup'
import { pgsqlApi } from '@/api/pgsql'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'
import SecretField from '@/components/common/SecretField.vue'

const { success, error: showError, info } = useNotification()
const { confirm } = useConfirm()

// ========== Tab 管理 ==========
const activeTab = ref('tasks')

// ========== 备份任务 ==========
const tasks = ref<BackupTask[]>([])
const tasksLoading = ref(false)

async function fetchTasks() {
  tasksLoading.value = true
  try {
    const data = await backupApi.getTasks()
    tasks.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载备份任务失败')
  } finally {
    tasksLoading.value = false
  }
}

async function handleRunTask(row: BackupTask) {
  if (!row.id) return
  try {
    await backupApi.runTask(row.id)
    info('备份任务已启动')
    setTimeout(() => fetchHistory(), 1000)
  } catch {
    showError('启动任务失败')
  }
}

async function handleDeleteTask(row: BackupTask) {
  if (!row.id) return
  const ok = await confirm({
    title: '确认删除',
    content: `确定要删除任务 "${row.name}" 吗？`,
    confirmColor: 'error',
  })
  if (!ok) return
  try {
    await backupApi.deleteTask(row.id)
    success('任务已删除')
    fetchTasks()
  } catch {
    showError('删除失败')
  }
}

// ========== 备份历史 ==========
const history = ref<BackupHistory[]>([])
const historyLoading = ref(false)
let pollingTimer: ReturnType<typeof setInterval> | null = null

async function fetchHistory(silent = false) {
  if (!silent) historyLoading.value = true
  try {
    const data = await backupApi.getHistory()
    history.value = Array.isArray(data) ? data : []
    const hasRunning = history.value.some(item => item.status === 'running')
    if (hasRunning) startPolling()
    else stopPolling()
  } catch {
    if (!silent) showError('加载历史记录失败')
  } finally {
    historyLoading.value = false
  }
}

function startPolling() {
  if (pollingTimer) return
  pollingTimer = setInterval(() => fetchHistory(true), 5000)
}

function stopPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function formatHistoryTime(time: string) {
  return new Date(time).toLocaleString()
}

function formatSize(mb?: number) {
  const v = Number(mb)
  if (!isFinite(v) || v < 0) return '--'
  if (v >= 1024) return `${(v / 1024).toFixed(2)} GB`
  return `${v.toFixed(2)} MB`
}

// 备份耗时：进行中的任务用当前时间实时估算
function formatDuration(start?: string, end?: string, status?: string) {
  if (!start) return '--'
  const startedAt = new Date(start).getTime()
  if (isNaN(startedAt)) return '--'

  let endedAt: number
  if (end) {
    endedAt = new Date(end).getTime()
    if (isNaN(endedAt)) return '--'
  } else if (status === 'running') {
    endedAt = Date.now()
  } else {
    return '--'
  }

  const sec = Math.max(0, Math.round((endedAt - startedAt) / 1000))
  if (sec < 60) return `${sec} 秒`
  const min = Math.floor(sec / 60)
  if (min < 60) return sec % 60 ? `${min} 分 ${sec % 60} 秒` : `${min} 分`
  return `${Math.floor(min / 60)} 小时 ${min % 60} 分`
}

const statusLabels: Record<string, string> = { success: '成功', running: '进行中...', failed: '失败' }
const statusColors: Record<string, string> = { success: 'success', running: 'info', failed: 'error' }

// ========== 任务历史弹窗 ==========
const showHistoryModal = ref(false)
const historyModalTaskId = ref('')
const historyModalTaskName = ref('')
const historyModalData = ref<BackupHistory[]>([])
const historyModalLoading = ref(false)

async function openHistoryModal(row: BackupTask) {
  historyModalTaskId.value = row.id || ''
  historyModalTaskName.value = row.name
  historyModalData.value = []
  showHistoryModal.value = true
  historyModalLoading.value = true
  try {
    const data = await backupApi.getHistory(row.id)
    historyModalData.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载历史记录失败')
  } finally {
    historyModalLoading.value = false
  }
}

// ========== 还原 ==========
async function handleRestore(row: BackupHistory) {
  const ok = await confirm({
    title: '确认还原',
    content: `还原操作将影响源目录 "${row.task_name}"，确定要继续吗？`,
    confirmColor: 'warning',
  })
  if (!ok) return
  try {
    await backupApi.restoreBackup(row.id, false)
    info('还原任务已在后台启动，请关注系统日志或稍后刷新历史')
    setTimeout(() => {
      if (showHistoryModal.value) {
        openHistoryModal({ id: row.task_id, name: row.task_name } as BackupTask)
      }
      fetchHistory(true)
    }, 1000)
  } catch (e: any) {
    showError('启动还原失败: ' + (e.message || '未知错误'))
  }
}

// ========== 任务编辑弹窗 ==========
const showEditModal = ref(false)
const editTask = ref<BackupTask>({
  name: '',
  mode: '7z',
  storage_type: 'ssd',
  sync_strategy: 'mirror',
  compression_level: 1,
  src_path: '',
  dst_path: '',
  enabled: true,
  schedule_type: 'cron',
  schedule_value: '0 3 * * *',
  ignore_patterns: [],
  host_id: 'local',
  gitea_repos: [],
  gitea_format: 'tar.gz',
  gitea_ref: '',
})

const defaultTask = (): BackupTask => ({
  name: '',
  mode: '7z',
  storage_type: 'ssd',
  sync_strategy: 'mirror',
  compression_level: 1,
  src_path: '',
  dst_path: '',
  enabled: true,
  schedule_type: 'cron',
  schedule_value: '0 3 * * *',
  ignore_patterns: [],
  host_id: 'local',
  gitea_repos: [],
  gitea_format: 'tar.gz',
  gitea_ref: '',
})

// ========== Gitea 仓库（复用系统设置里的 Gitea 连接配置）==========
const giteaRepos = ref<GiteaRepo[]>([])
const giteaReposLoading = ref(false)
const giteaReposError = ref('')
// 「全部可见仓库」在数据层是空列表；用独立的 UI 状态表达，避免多选框空着被误读成"一个都没选"
const giteaScope = ref<'all' | 'pick'>('all')

const giteaRepoOptions = computed(() =>
  giteaRepos.value.map((r) => ({
    title: r.private ? `🔒 ${r.full_name}` : r.full_name,
    value: r.full_name,
  }))
)

// 只有文件类模式才需要 存储介质 / 源路径 / 忽略模式
const isFileMode = computed(() => ['7z', 'tar', 'sync'].includes(editTask.value.mode))

async function fetchGiteaRepos() {
  giteaReposLoading.value = true
  giteaReposError.value = ''
  try {
    const data = await backupApi.listGiteaRepos()
    giteaRepos.value = Array.isArray(data) ? data : []
    if (!giteaRepos.value.length) giteaReposError.value = '该账号下没有可见的仓库'
  } catch (e: any) {
    giteaRepos.value = []
    giteaReposError.value = e?.message || '读取 Gitea 仓库列表失败'
  } finally {
    giteaReposLoading.value = false
  }
}

// 卡片上显示备份范围：空列表 = 全部可见仓库
function giteaScopeSummary(row: BackupTask) {
  const list = row.gitea_repos || []
  if (!list.length) return '全部可见仓库'
  if (list.length <= 3) return list.join('、')
  return `${list.length} 个指定仓库`
}

function handleAddTask() {
  editTask.value = defaultTask()
  giteaScope.value = 'all'
  showEditModal.value = true
}

function handleEditTask(row: BackupTask) {
  // 用默认值兜底：老任务可能没有后来新增的字段，也可能存了 null
  editTask.value = { ...defaultTask(), ...row }
  if (!Array.isArray(editTask.value.gitea_repos)) editTask.value.gitea_repos = []
  if (!Array.isArray(editTask.value.ignore_patterns)) editTask.value.ignore_patterns = []
  giteaScope.value = row.gitea_repos?.length ? 'pick' : 'all'
  showEditModal.value = true
}

async function saveTask() {
  try {
    // 「全部可见仓库」在数据层用空列表表示
    if (editTask.value.mode === 'gitea' && giteaScope.value === 'all') {
      editTask.value.gitea_repos = []
    }
    await backupApi.saveTask(editTask.value)
    success('保存成功')
    showEditModal.value = false
    fetchTasks()
  } catch {
    showError('保存失败')
  }
}

// ========== 选项配置 ==========
const modeOptions = [
  { title: '7z 压缩', value: '7z' },
  { title: 'Tar.gz 打包', value: 'tar' },
  { title: '物理增量镜像 (Sync)', value: 'sync' },
  { title: 'PostgreSQL 数据库备份', value: 'pgsql' },
  { title: 'Gitea 仓库归档下载', value: 'gitea' },
]

const storageOptions = [
  { title: 'SSD (高性能)', value: 'ssd' },
  { title: 'HDD (机械硬盘)', value: 'hdd' },
  { title: '云盘 (CloudDrive/Rclone)', value: 'cloud' },
]

const scheduleModeOptions = [
  { title: '每天固定时间', value: 'daily' },
  { title: '固定间隔频率', value: 'interval' },
  { title: '自定义 Cron', value: 'cron' },
]

const unitOptions = [
  { title: '分钟', value: 1 },
  { title: '小时', value: 60 },
  { title: '天', value: 1440 },
]

const presetPatterns = [
  '__pycache__', '*.pyc', '.git', 'node_modules', 'target',
  '.vscode', '.idea', 'dist', 'build', '*.log', '.DS_Store',
]

const storageLabels: Record<string, string> = { ssd: 'SSD', hdd: 'HDD', cloud: '云盘' }
const modeLabels: Record<string, string> = { '7z': '7z 压缩', tar: 'Tar 打包', sync: 'Sync 同步', pgsql: 'PG 备份', gitea: 'Gitea 仓库' }

// ========== 简化计划配置 ==========
const simpleScheduleMode = ref('daily')
const dailyTime = ref('03:00')
const intervalValue = ref(1)
const intervalUnit = ref(60)

watch(showEditModal, (newVal) => {
  if (newVal) {
    if (editTask.value.schedule_type === 'cron') {
      const cron = editTask.value.schedule_value || ''
      const dailyMatch = cron.match(/^(\d+)\s+(\d+)\s+\*\s+\*\s+\*$/)
      if (dailyMatch) {
        simpleScheduleMode.value = 'daily'
        const m = dailyMatch[1].padStart(2, '0')
        const h = dailyMatch[2].padStart(2, '0')
        dailyTime.value = `${h}:${m}`
      } else {
        simpleScheduleMode.value = 'cron'
      }
    } else if (editTask.value.schedule_type === 'interval') {
      simpleScheduleMode.value = 'interval'
      const totalMin = parseInt(editTask.value.schedule_value) || 60
      if (totalMin % 1440 === 0) {
        intervalUnit.value = 1440
        intervalValue.value = totalMin / 1440
      } else if (totalMin % 60 === 0) {
        intervalUnit.value = 60
        intervalValue.value = totalMin / 60
      } else {
        intervalUnit.value = 1
        intervalValue.value = totalMin
      }
    }
  }
})

function applyScheduleToTask() {
  if (simpleScheduleMode.value === 'daily') {
    const [h, m] = dailyTime.value.split(':').map(x => parseInt(x))
    editTask.value.schedule_type = 'cron'
    editTask.value.schedule_value = `${m} ${h} * * *`
  } else if (simpleScheduleMode.value === 'interval') {
    editTask.value.schedule_type = 'interval'
    editTask.value.schedule_value = String(intervalValue.value * intervalUnit.value)
  }
}

function handleSaveTask() {
  applyScheduleToTask()
  saveTask()
}

// ========== Docker 主机选项 ==========
const dockerHosts = ref<any[]>([])
const hostOptions = computed(() => [
  { title: '本机 (local)', value: 'local' },
  ...dockerHosts.value.map((h: any) => ({ title: `${h.name} (${h.host})`, value: h.id })),
])

async function fetchDockerHosts() {
  try {
    const data = await dockerApi.getHosts()
    dockerHosts.value = Array.isArray(data) ? data : []
  } catch { /* 忽略 */ }
}

// ========== PostgreSQL 主机和数据库 ==========
const pgsqlHosts = ref<any[]>([])
const pgsqlDatabases = ref<string[]>([])
const loadingDatabases = ref(false)

const pgsqlHostOptions = computed(() =>
  pgsqlHosts.value.map((h: any) => ({ title: `${h.name} (${h.host}:${h.port})`, value: h.id }))
)

async function fetchPgsqlHosts() {
  try {
    const data = await pgsqlApi.getHosts()
    pgsqlHosts.value = Array.isArray(data) ? data : []
  } catch { /* 忽略 */ }
}

async function fetchPgDatabases(hostId: string) {
  if (!hostId) return
  const host = pgsqlHosts.value.find((h: any) => h.id === hostId)
  if (!host) return
  loadingDatabases.value = true
  try {
    const config = { host: host.host, port: host.port, username: host.username, password: host.password, database: host.database }
    const res = await pgsqlApi.getDatabases(config)
    pgsqlDatabases.value = Array.isArray(res) ? res.map((db: any) => db.name || db) : []
  } catch {
    pgsqlDatabases.value = []
  } finally {
    loadingDatabases.value = false
  }
}

watch(() => editTask.value.pgsql_host_id, (newVal) => {
  if (newVal && editTask.value.mode === 'pgsql') {
    fetchPgDatabases(newVal)
  }
})

watch(() => editTask.value.mode, (newVal) => {
  if (newVal === 'pgsql') {
    if (editTask.value.pgsql_host_id) fetchPgDatabases(editTask.value.pgsql_host_id)
    if (!editTask.value.dst_path) editTask.value.dst_path = 'data/backups/pg'
  } else if (newVal === 'gitea') {
    if (!editTask.value.dst_path) editTask.value.dst_path = 'data/backups/gitea'
    if (!giteaRepos.value.length && !giteaReposLoading.value) fetchGiteaRepos()
  } else if (newVal === '7z' || newVal === 'tar') {
    if (!editTask.value.dst_path) editTask.value.dst_path = 'data/backups/files'
  }
})

// ========== 忽略模式切换 ==========
function handleTogglePattern(pattern: string, checked: boolean) {
  const patterns = [...editTask.value.ignore_patterns]
  if (checked) {
    if (!patterns.includes(pattern)) patterns.push(pattern)
  } else {
    const index = patterns.indexOf(pattern)
    if (index > -1) patterns.splice(index, 1)
  }
  editTask.value.ignore_patterns = patterns
}

function handleToggleDbName(dbName: string) {
  if (!editTask.value.db_names) editTask.value.db_names = []
  const idx = editTask.value.db_names.indexOf(dbName)
  if (idx > -1) {
    editTask.value.db_names.splice(idx, 1)
  } else {
    editTask.value.db_names.push(dbName)
  }
}

// ========== 格式化计划显示 ==========
function formatSchedule(row: BackupTask) {
  if (!row.enabled) return '-'
  if (row.schedule_type === 'interval') {
    const min = parseInt(row.schedule_value)
    if (min % 1440 === 0) return `每隔 ${min / 1440} 天`
    if (min % 60 === 0) return `每隔 ${min / 60} 小时`
    return `每隔 ${min} 分钟`
  }
  if (row.schedule_type === 'cron') {
    const cron = row.schedule_value || ''
    const dailyMatch = cron.match(/^(\d+)\s+(\d+)\s+\*\s+\*\s+\*$/)
    if (dailyMatch) {
      const m = dailyMatch[1].padStart(2, '0')
      const h = dailyMatch[2].padStart(2, '0')
      return `每天 ${h}:${m}`
    }
    return cron
  }
  return row.schedule_value || '-'
}

// ========== 路径浏览器 ==========
const showBrowser = ref(false)
const browserTargetField = ref<'src' | 'dst'>('src')
const browserCurrentPath = ref('/')
const browserItems = ref<PathBrowserItem[]>([])
const browserLoading = ref(false)
const browserPathParts = computed(() => browserCurrentPath.value.split('/').filter(Boolean))

function openBrowser(field: 'src' | 'dst') {
  browserTargetField.value = field
  browserCurrentPath.value = (field === 'src' ? editTask.value.src_path : editTask.value.dst_path) || '/'
  showBrowser.value = true
  fetchBrowserItems()
}

async function fetchBrowserItems() {
  browserLoading.value = true
  try {
    const data = await backupApi.browsePath(browserCurrentPath.value)
    browserItems.value = data?.items || []
  } catch {
    showError('无法读取目录')
    browserItems.value = []
  } finally {
    browserLoading.value = false
  }
}

function browserItemClick(item: PathBrowserItem) {
  if (item.is_dir) {
    browserCurrentPath.value = item.path
    fetchBrowserItems()
  }
}

function browserGoUp() {
  const parts = browserCurrentPath.value.split('/').filter(Boolean)
  parts.pop()
  browserCurrentPath.value = '/' + (parts.join('/') || '')
  if (browserCurrentPath.value === '//') browserCurrentPath.value = '/'
  fetchBrowserItems()
}

function browserJumpTo(index: number) {
  const parts = browserPathParts.value.slice(0, index + 1)
  browserCurrentPath.value = '/' + parts.join('/')
  fetchBrowserItems()
}

function confirmBrowserPath() {
  if (browserTargetField.value === 'src') {
    editTask.value.src_path = browserCurrentPath.value
  } else {
    editTask.value.dst_path = browserCurrentPath.value
  }
  showBrowser.value = false
}

// ========== 生命周期 ==========
onMounted(() => {
  fetchTasks()
  fetchHistory()
  fetchDockerHosts()
  fetchPgsqlHosts()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-backup-restore</v-icon>
      数据备份管理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">
      支持多模式增量备份，内置针对 <span class="text-info">云盘 (CloudDrive/Rclone)</span>、SSD 及 HDD 的传输优化逻辑。
    </p>

    <v-tabs v-model="activeTab" class="mb-4" color="primary">
      <v-tab value="tasks"><v-icon start>mdi-format-list-bulleted</v-icon> 备份任务</v-tab>
      <v-tab value="history"><v-icon start>mdi-history</v-icon> 执行历史</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- ====== 备份任务 ====== -->
      <v-window-item value="tasks">
        <div class="d-flex justify-end mb-4 ga-2">
          <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="fetchTasks" :loading="tasksLoading">刷新</v-btn>
          <v-btn prepend-icon="mdi-plus" color="primary" variant="tonal" size="small" @click="handleAddTask">新增任务</v-btn>
        </div>

        <v-progress-linear v-if="tasksLoading" indeterminate color="primary" class="mb-4" />

        <!-- 空状态 -->
        <v-row v-if="!tasksLoading && tasks.length === 0">
          <v-col cols="12" class="text-center py-12 text-medium-emphasis">
            <v-icon size="64" color="grey" class="mb-4">mdi-backup-restore</v-icon>
            <div>暂无备份任务</div>
          </v-col>
        </v-row>

        <!-- 任务卡片列表 -->
        <div v-if="tasks.length" class="card-grid">
          <v-card
            v-for="row in tasks"
            :key="row.id"
            class="status-card liquid-glass-card"
            :class="{ 'is-auto': row.enabled }"
            rounded="lg"
          >
            <!-- 卡片头部 -->
            <div class="card-header pa-4 pb-2">
              <div class="card-title">
                <v-icon start color="primary" size="20">mdi-backup-restore</v-icon>
                <span class="text-subtitle-2 font-weight-bold">{{ row.name }}</span>
                <v-chip v-if="row.host_id && row.host_id !== 'local'" size="x-small" color="warning" variant="tonal" class="ml-1">远程</v-chip>
              </div>
              <v-chip
                :color="row.enabled ? 'success' : 'grey'"
                size="small"
                variant="tonal"
                label
              >
                {{ row.enabled ? '自动计划中' : '仅手动' }}
              </v-chip>
            </div>

            <!-- 信息行：所有字段恒定渲染（缺值用 -- 占位），行数固定才能保证同一排卡片对齐 -->
            <div class="card-info card-info--stacked px-4 pb-2">
              <div class="info-item">
                <span class="info-label">模式</span>
                <v-chip size="x-small" variant="tonal" color="info" label>{{ modeLabels[row.mode] || row.mode || '--' }}</v-chip>
              </div>
              <div class="info-item">
                <span class="info-label">{{ row.mode === 'gitea' ? '归档格式' : '介质' }}</span>
                <span class="text-caption text-medium-emphasis">{{ row.mode === 'gitea' ? (row.gitea_format || 'tar.gz') : (storageLabels[row.storage_type] || 'SSD') }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">计划</span>
                <span class="text-caption" :class="{ 'text-medium-emphasis': !row.enabled }">{{ row.enabled ? formatSchedule(row) : '仅手动执行' }}</span>
              </div>

              <!-- 每个模式在这一行放各自最关键的"来源"：数据库 / 仓库范围 / 源路径。
                   三种情况都恒定占一行，行数才不会随模式变化 -->
              <div class="info-item">
                <span class="info-label">{{ row.mode === 'pgsql' ? '数据库' : (row.mode === 'gitea' ? '仓库范围' : '源路径') }}</span>
                <span
                  v-if="row.mode === 'pgsql'"
                  class="text-caption text-truncate"
                  :class="{ 'text-medium-emphasis': !row.db_names?.length }"
                  :title="(row.db_names || []).join(', ')"
                >{{ (row.db_names || []).join(', ') || '--' }}</span>
                <span
                  v-else-if="row.mode === 'gitea'"
                  class="text-caption text-truncate"
                  :title="(row.gitea_repos || []).join(', ')"
                >{{ giteaScopeSummary(row) }}</span>
                <span
                  v-else
                  class="font-mono text-caption text-truncate"
                  :class="{ 'text-medium-emphasis': !row.src_path }"
                  :title="row.src_path"
                >{{ row.src_path || '--' }}</span>
              </div>

              <div class="info-item">
                <span class="info-label">目标路径</span>
                <span class="font-mono text-caption text-truncate" :class="{ 'text-medium-emphasis': !row.dst_path }" :title="row.dst_path">{{ row.dst_path || '--' }}</span>
              </div>

              <div class="info-item">
                <span class="info-label">{{ row.mode === 'gitea' ? '分支 / 标签' : '压缩级别' }}</span>
                <span class="text-caption text-medium-emphasis">{{ row.mode === 'gitea' ? (row.gitea_ref || '各仓库默认分支') : (row.mode === '7z' ? `${row.compression_level ?? 1} 级` : '--') }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">{{ row.mode === 'gitea' ? '下载方式' : '同步策略' }}</span>
                <span
                  class="text-caption text-medium-emphasis"
                  :title="row.mode === 'gitea' ? '通过 Gitea API 逐个仓库拉取归档包' : (row.mode === 'sync' ? (row.sync_strategy === 'incremental' ? '仅同步新增和修改，目标端已有的文件即使源端删了也保留' : '目标目录与源目录完全同步，源端删除的文件目标端也会清理') : '')"
                >{{ row.mode === 'gitea' ? '逐个仓库归档' : (row.mode === 'sync' ? (row.sync_strategy === 'incremental' ? '增量' : '镜像') : '--') }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">{{ row.mode === 'gitea' ? '不含内容' : '忽略规则' }}</span>
                <span
                  class="text-caption text-medium-emphasis"
                  :title="row.mode === 'gitea' ? 'Gitea 归档只有代码仓库，不含 issues / PR / 用户 / 附件等数据库内容' : (row.ignore_patterns || []).join(', ')"
                >{{ row.mode === 'gitea' ? 'issues / PR / 附件' : (row.ignore_patterns?.length ? `${row.ignore_patterns.length} 条` : '--') }}</span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <v-divider class="mt-2" />
            <div class="d-flex flex-wrap ga-2 pa-3">
              <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-play" @click="handleRunTask(row)">执行</v-btn>
              <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-history" @click="openHistoryModal(row)">历史</v-btn>
              <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="handleEditTask(row)">编辑</v-btn>
              <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" @click="handleDeleteTask(row)">删除</v-btn>
            </div>
          </v-card>
        </div>
      </v-window-item>

      <!-- ====== 执行历史 ====== -->
      <v-window-item value="history">
        <div class="d-flex justify-end mb-4">
          <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="fetchHistory" :loading="historyLoading">刷新</v-btn>
        </div>

        <!-- 空状态 -->
        <v-row v-if="!historyLoading && history.length === 0">
          <v-col cols="12" class="text-center py-12 text-medium-emphasis">
            <v-icon size="64" color="grey" class="mb-4">mdi-history</v-icon>
            <div>暂无执行历史</div>
          </v-col>
        </v-row>

        <!-- 历史卡片列表 -->
        <div v-if="history.length" class="card-grid">
          <v-card
            v-for="row in history"
            :key="row.id"
            class="status-card liquid-glass-card"
            :class="`is-${row.status}`"
            rounded="lg"
          >
            <div class="card-header pa-4 pb-2">
              <div class="card-title">
                <span class="text-subtitle-2 font-weight-bold">{{ row.task_name }}</span>
              </div>
              <v-chip
                :color="statusColors[row.status] || 'grey'"
                size="small"
                variant="tonal"
                label
              >
                {{ statusLabels[row.status] || row.status }}
              </v-chip>
            </div>

            <div class="card-info card-info--stacked px-4 pb-2">
              <div class="info-item">
                <span class="info-label">开始时间</span>
                <span class="text-caption text-medium-emphasis">{{ formatHistoryTime(row.start_time) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">耗时</span>
                <span class="text-caption text-medium-emphasis">{{ formatDuration(row.start_time, row.end_time, row.status) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">大小</span>
                <span class="text-caption text-medium-emphasis">{{ formatSize(row.size) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">模式</span>
                <span class="text-caption text-medium-emphasis">{{ modeLabels[row.mode] || row.mode || '--' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">输出文件</span>
                <span class="font-mono text-caption text-truncate" :class="{ 'text-medium-emphasis': !row.output_path }" :title="row.output_path">{{ row.output_path || '--' }}</span>
              </div>
            </div>

            <div class="card-message px-4 pb-3">
              <span class="text-caption text-medium-emphasis">{{ row.message || '--' }}</span>
            </div>
          </v-card>
        </div>
      </v-window-item>
    </v-window>

    <!-- ====== 任务历史弹窗 ====== -->
    <GlassDialog v-model="showHistoryModal" :max-width="850" icon="mdi-history" :title="'备份历史:' + (historyModalTaskName || '加载中...')" cancel-text="关闭">
  <v-table class="bg-transparent" density="compact" v-if="!historyModalLoading">
            <thead>
              <tr>
                <th>开始时间</th>
                <th>状态</th>
                <th>大小</th>
                <th>摘要/错误信息</th>
                <th class="text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!historyModalData.length">
                <td colspan="5" class="text-center py-8 text-medium-emphasis">暂无历史记录</td>
              </tr>
              <tr v-for="row in historyModalData" :key="row.id">
                <td class="text-medium-emphasis" style="white-space:nowrap">{{ formatHistoryTime(row.start_time) }}</td>
                <td>
                  <v-chip
                    :color="statusColors[row.status] || 'grey'"
                    size="small" variant="tonal" label
                  >
                    {{ statusLabels[row.status] || row.status }}
                  </v-chip>
                </td>
                <td class="text-medium-emphasis">{{ formatSize(row.size) }}</td>
                <td class="text-medium-emphasis" style="max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">
                  {{ row.message || '-' }}
                </td>
                <td class="text-right">
                  <v-btn v-if="row.status === 'success' && row.mode !== 'gitea'" size="small" variant="tonal" color="warning"
                    prepend-icon="mdi-restore" @click="handleRestore(row)">还原</v-btn>
                </td>
              </tr>
            </tbody>
          </v-table>
          <div v-else class="text-center py-8">
            <v-progress-circular indeterminate color="primary" />
          </div>
</GlassDialog>

    <!-- ====== 任务编辑弹窗 ====== -->
    <GlassDialog v-model="showEditModal" :max-width="700" icon="mdi-backup-restore" :title="editTask.id ? '编辑备份任务' : '新增备份任务'">
  <!-- 远程任务提示 -->
          <v-alert v-if="editTask.host_id && editTask.host_id !== 'local'" type="warning" variant="tonal" density="compact" class="mb-4" title="远程 SSH 备份模式">
            <template v-slot:text>
              <ul style="margin: 0; padding-left: 18px; font-size: 12px; line-height: 1.6">
                <li><b>数据源：</b>该任务将从远程 Docker 主机拉取文件夹。</li>
                <li><b>依赖环境：</b>请确保远程主机已安装 <code>tar</code> 或 <code>7z</code> 命令。</li>
                <li><b>中转逻辑：</b>Lens 将通过网络执行远程打包并拉取回本地目的地。</li>
                <li><b>过滤规则：</b>已自动同步 Lens 的精准过滤逻辑。</li>
              </ul>
            </template>
          </v-alert>

          <!-- 任务名称 -->
          <v-text-field v-model="editTask.name" label="任务名称" variant="outlined" density="compact"
            placeholder="例如：数据库每日备份" class="mb-3" />

          <!-- 备份模式 -->
          <v-select v-model="editTask.mode" :items="modeOptions" label="备份模式" variant="outlined" density="compact" class="mb-2" />
          <div class="text-body-2 text-medium-emphasis mb-3" style="font-size: 12px; line-height: 1.5">
            <span v-if="editTask.mode === '7z'">🗜️ <b>7z 压缩</b>：最高压缩比，支持密码加密和文件名加密。适合节省空间的长期存档。</span>
            <span v-if="editTask.mode === 'tar'">📦 <b>Tar 打包</b>：Linux 原生打包格式，速度快，完美保持文件权限。适合快速迁移。</span>
            <span v-if="editTask.mode === 'sync'">🔄 <b>Sync 同步</b>：直接同步原始文件（不打包），无需解压即可直接查看，支持增量更新。</span>
            <span v-if="editTask.mode === 'pgsql'">🐘 <b>PostgreSQL 备份</b>：使用 pg_dump 对指定数据库进行逻辑备份。</span>
            <span v-if="editTask.mode === 'gitea'">🔗 <b>Gitea 仓库归档</b>：通过 Gitea API 把仓库的 tar.gz / zip 归档拉回本地。连接信息复用「设置 → 第三方 API 集成 → Gitea 仓库集成」。</span>
          </div>

          <!-- 存储介质 (仅文件类模式) -->
          <v-select v-if="isFileMode" v-model="editTask.storage_type" :items="storageOptions"
            label="存储介质" variant="outlined" density="compact" class="mb-2" />
          <div v-if="isFileMode" class="text-body-2 text-medium-emphasis mb-3" style="font-size: 12px; line-height: 1.5">
            <span v-if="editTask.storage_type === 'ssd'">🚀 <b>SSD 优化</b>：开启最大并发线程，充分利用闪存带宽。</span>
            <span v-if="editTask.storage_type === 'hdd'">🛡️ <b>HDD 保护</b>：限制并发线程（max=2），防止磁头剧烈抖动，保护硬盘寿命。</span>
            <span v-if="editTask.storage_type === 'cloud'">☁️ <b>云盘优化</b>：本地生成暂存盘后再流式上传，通过 --size-only 规避 API 频率限制。</span>
          </div>

          <!-- 同步策略 (sync 模式) -->
          <template v-if="editTask.mode === 'sync'">
            <v-select v-model="editTask.sync_strategy"
              :items="[
                { title: '镜像模式 (完全一致)', value: 'mirror' },
                { title: '增量模式 (只增不删)', value: 'incremental' }
              ]"
              label="同步策略" variant="outlined" density="compact" class="mb-2" />
            <div class="text-body-2 text-medium-emphasis mb-3" style="font-size: 12px; line-height: 1.5">
              <span v-if="editTask.sync_strategy === 'mirror'">🔄 <b>镜像</b>：目标目录将与源目录完全同步，源端删除的文件目标端也会被清理。</span>
              <span v-if="editTask.sync_strategy === 'incremental'">📥 <b>增量</b>：仅同步新增和修改，目标端已有的文件即使源端删了也会保留。</span>
            </div>
          </template>

          <!-- PostgreSQL 字段 -->
          <template v-if="editTask.mode === 'pgsql'">
            <v-select v-model="editTask.pgsql_host_id" :items="pgsqlHostOptions"
              label="PG 主机" variant="outlined" density="compact"
              placeholder="选择已配置的 PostgreSQL 主机" class="mb-3" />

            <div class="mb-3">
              <div class="text-body-2 mb-1">待备份数据库</div>
              <div v-if="loadingDatabases" class="text-caption text-medium-emphasis">正在加载数据库列表...</div>
              <div v-else-if="pgsqlDatabases.length === 0" class="text-caption text-medium-emphasis">请先选择主机</div>
              <div v-else class="d-flex flex-wrap ga-2">
                <v-chip v-for="db in pgsqlDatabases" :key="db" size="small"
                  :variant="editTask.db_names?.includes(db) ? 'flat' : 'outlined'"
                  :color="editTask.db_names?.includes(db) ? 'primary' : 'default'"
                  @click="handleToggleDbName(db)"
                  style="cursor:pointer"
                >
                  {{ db }}
                </v-chip>
              </div>
            </div>
          </template>

          <!-- Gitea 仓库字段 -->
          <template v-if="editTask.mode === 'gitea'">
            <v-select v-model="giteaScope"
              :items="[
                { title: '全部可见仓库', value: 'all' },
                { title: '指定仓库', value: 'pick' }
              ]"
              label="备份范围" variant="outlined" density="compact" class="mb-2" />

            <v-select v-if="giteaScope === 'pick'" v-model="editTask.gitea_repos"
              :items="giteaRepoOptions" :loading="giteaReposLoading"
              label="选择仓库" placeholder="可多选" multiple chips closable-chips
              variant="outlined" density="compact" class="mb-2" />

            <div class="d-flex align-center ga-3 mb-2 flex-wrap">
              <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh"
                :loading="giteaReposLoading" @click="fetchGiteaRepos">读取仓库列表</v-btn>
              <span v-if="giteaReposError" class="text-caption text-error">{{ giteaReposError }}</span>
              <span v-else-if="giteaRepos.length" class="text-caption text-medium-emphasis">
                共 {{ giteaRepos.length }} 个可见仓库
              </span>
            </div>

            <v-select v-model="editTask.gitea_format"
              :items="[{ title: 'tar.gz', value: 'tar.gz' }, { title: 'zip', value: 'zip' }]"
              label="归档格式" variant="outlined" density="compact" class="mb-2" />

            <v-text-field v-model="editTask.gitea_ref" label="分支 / 标签（可选）"
              placeholder="留空 = 各仓库自己的默认分支" variant="outlined" density="compact" class="mb-2" />

            <v-alert type="info" variant="tonal" density="compact" class="mb-3" style="font-size: 12px">
              备份的是代码仓库本身（全部分支、标签、提交历史）。<b>不含</b> issues、PR、用户、附件等数据库内容。
            </v-alert>
          </template>

          <!-- Docker 主机选择（Gitea 模式由控制端直接走 HTTP 下载，与 Docker 主机无关）-->
          <v-select v-if="editTask.mode !== 'gitea'" v-model="editTask.host_id" :items="hostOptions"
            label="执行主机" variant="outlined" density="compact" class="mb-3" />

          <!-- 源路径 (仅文件类模式) -->
          <div v-if="isFileMode" class="mb-3">
            <v-label class="mb-1 text-body-2">
              {{ editTask.host_id && editTask.host_id !== 'local' ? '源路径 (远程)' : '源路径' }}
            </v-label>
            <v-text-field v-model="editTask.src_path"
              :placeholder="editTask.host_id && editTask.host_id !== 'local' ? '远程主机上的绝对路径' : '/app/data'"
              variant="outlined" density="compact"
              append-inner-icon="mdi-folder-open"
              @click:append-inner="openBrowser('src')"
            />
          </div>

          <!-- 目标目录 -->
          <div class="mb-3">
            <v-label class="mb-1 text-body-2">目标目录</v-label>
            <v-text-field v-model="editTask.dst_path" placeholder="/backup"
              variant="outlined" density="compact"
              append-inner-icon="mdi-folder-open"
              @click:append-inner="openBrowser('dst')"
            />
          </div>

          <!-- 压缩强度 (7z) -->
          <div v-if="editTask.mode === '7z'" class="mb-3">
            <v-label class="mb-1 text-body-2">压缩强度</v-label>
            <v-slider v-model="editTask.compression_level" :min="1" :max="9" :step="1" thumb-label />
          </div>

          <!-- 加密密码 (7z) -->
          <SecretField v-if="editTask.mode === '7z'" v-model="editTask.password"
            label="加密密码" placeholder="可选" :show-copy="false" class="mb-3" />

          <!-- ====== 自动化运行计划 ====== -->
          <v-divider class="mb-3" />
          <div class="text-subtitle-2 mb-3">自动化运行计划</div>

          <v-switch v-model="editTask.enabled" label="启用定时备份" density="compact" color="primary" class="mb-2" />

          <template v-if="editTask.enabled">
            <v-select v-model="simpleScheduleMode" :items="scheduleModeOptions"
              label="运行频率" variant="outlined" density="compact" class="mb-3" />

            <!-- 每天固定时间 -->
            <div v-if="simpleScheduleMode === 'daily'" class="d-flex align-center mb-3">
              <v-text-field v-model="dailyTime" label="执行时间" variant="outlined" density="compact"
                type="time" style="max-width: 160px" class="mr-3" />
              <span class="text-body-2 text-medium-emphasis">每天此时间点自动开始备份</span>
            </div>

            <!-- 固定间隔 -->
            <div v-if="simpleScheduleMode === 'interval'" class="d-flex align-center mb-3">
              <v-text-field v-model.number="intervalValue" label="间隔值" variant="outlined" density="compact"
                type="number" :min="1" style="max-width: 120px" class="mr-2" />
              <v-select v-model="intervalUnit" :items="unitOptions" variant="outlined" density="compact"
                style="max-width: 100px" />
            </div>

            <!-- Cron 表达式 -->
            <v-text-field v-if="simpleScheduleMode === 'cron'" v-model="editTask.schedule_value"
              label="Cron 表达式" variant="outlined" density="compact"
              placeholder="0 3 * * *" class="mb-3" />
          </template>

          <!-- 忽略模式 (仅文件类模式) -->
          <template v-if="isFileMode">
            <v-divider class="mb-3" />
            <div class="text-subtitle-2 mb-2">忽略模式</div>
            <div class="d-flex flex-wrap ga-1 mb-2">
              <span class="text-caption text-medium-emphasis mr-2" style="line-height:28px">常用预设:</span>
              <v-chip v-for="p in presetPatterns" :key="p" size="x-small"
                :variant="editTask.ignore_patterns.includes(p) ? 'flat' : 'outlined'"
                :color="editTask.ignore_patterns.includes(p) ? 'primary' : 'default'"
                @click="handleTogglePattern(p, !editTask.ignore_patterns.includes(p))"
                style="cursor:pointer"
              >
                {{ p }}
              </v-chip>
            </div>
            <div class="d-flex flex-wrap ga-1">
              <v-chip v-for="(p, i) in editTask.ignore_patterns" :key="i"
                size="small" closable variant="tonal" color="primary"
                @click:close="editTask.ignore_patterns.splice(i, 1)"
              >
                {{ p }}
              </v-chip>
              <v-btn size="small" variant="outlined" density="compact" prepend-icon="mdi-plus"
                @click="editTask.ignore_patterns.push('')">
                添加
              </v-btn>
            </div>
          </template>
  <template #actions>
    <v-btn color="primary" variant="tonal" prepend-icon="mdi-content-save-outline" @click="handleSaveTask">保存</v-btn>
  </template>
</GlassDialog>

    <!-- ====== 路径浏览器弹窗 ====== -->
    <GlassDialog v-model="showBrowser" :max-width="550" icon="mdi-folder-open" title="选择路径" :cancel-visible="false">
  <v-progress-linear v-if="browserLoading" indeterminate color="primary" class="mb-2" />

          <!-- 返回上级 -->
          <div v-if="browserCurrentPath !== '/'" class="d-flex align-center pa-2 rounded hoverable"
            @click="browserGoUp" style="cursor:pointer">
            <v-icon start size="20" color="warning">mdi-folder</v-icon>
            <span class="text-body-2">.. (返回上级)</span>
          </div>

          <!-- 目录/文件列表 -->
          <div v-for="item in browserItems" :key="item.path"
            class="d-flex align-center pa-2 rounded hoverable"
            @click="browserItemClick(item)"
            style="cursor:pointer"
          >
            <v-icon :icon="item.is_dir ? 'mdi-folder' : 'mdi-file-outline'" size="20" class="mr-2"
              :color="item.is_dir ? 'warning' : 'grey'" />
            <span class="text-body-2 flex-grow-1">{{ item.name }}</span>
            <span v-if="!item.is_dir" class="text-caption text-medium-emphasis">
              {{ formatSize(item.size / 1024 / 1024) }}
            </span>
          </div>

          <div v-if="!browserLoading && browserItems.length === 0 && browserCurrentPath !== '/'" class="text-center py-4 text-medium-emphasis text-body-2">
            空目录
          </div>
</GlassDialog>
  </v-container>
</template>

