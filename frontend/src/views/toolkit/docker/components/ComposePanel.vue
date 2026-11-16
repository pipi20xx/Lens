<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError, info } = useNotification()
const { confirm } = useConfirm()

const props = defineProps<{
  active: boolean
  hostId: string | null
}>()

// ========== 自动加载 ==========
watch([() => props.active, () => props.hostId], ([active, hostId], old) => {
  // 换主机时丢掉上一台主机的任务进度，避免张冠李戴
  if (old && old[1] !== hostId) { composeTasks.value = {}; activeTask.value = null; stopTaskPolling() }
  if (active && hostId) loadComposeProjects()
})
onMounted(() => { if (props.active && props.hostId) loadComposeProjects() })

// ========== 列表 ==========
const composeProjects = ref<any[]>([])
const loadingCompose = ref(false)
const composeSearchQuery = ref('')
const startingActions = ref<Record<string, boolean>>({})

const filteredComposeProjects = computed(() => {
  if (!composeSearchQuery.value) return composeProjects.value
  const q = composeSearchQuery.value.toLowerCase()
  return composeProjects.value.filter((p: any) => p.name?.toLowerCase().includes(q) || (p.config_file || p.path || '').toLowerCase().includes(q))
})

async function loadComposeProjects() {
  if (!props.hostId) return
  try {
    loadingCompose.value = true
    const data = await dockerApi.getComposeProjects(props.hostId)
    composeProjects.value = Array.isArray(data) ? data : []
  } catch { showError('加载 Compose 项目失败') }
  finally { loadingCompose.value = false }
}

// ========== 任务进度（阶段 / 条目 / 输出 / 终止） ==========
const BULK_KEY = '__bulk__'
const composeTasks = ref<Record<string, any>>({})
const showTaskDialog = ref(false)
const activeTask = ref<any>(null)
const cancelingTask = ref(false)
let taskTimer: ReturnType<typeof setInterval> | null = null

const composeStageLabels: Record<string, string> = {
  pending: '等待中',
  preparing: '准备配置',
  pulling: '拉取镜像',
  creating: '创建容器',
  starting: '启动容器',
  stopping: '停止/移除容器',
  done: '完成',
}

const ACTION_LABELS: Record<string, string> = {
  up: '启动/更新',
  down: '停止',
  pull: '拉取镜像',
  restart: '重启',
}

function taskFor(projectName: string) {
  const t = composeTasks.value[projectName]
  return t && !t.done ? t : null
}

/** 批量任务（模板里用它避免非空断言） */
const bulkTask = computed(() => taskFor(BULK_KEY))

function taskStageText(task: any) {
  if (!task) return ''
  if (task.done) {
    if (task.status === 'cancelled') return '已终止'
    return task.success ? '完成' : '失败'
  }
  return composeStageLabels[task.stage] || '执行中'
}

function taskProgressText(task: any) {
  const p = task?.progress || {}
  if (!p.total) return ''
  return `已完成 ${p.completed || 0}/${p.total}`
}

/** 任务条目列表（后端 items 是字典，顺序由 item_order 决定） */
function taskItemList(task: any) {
  if (!task?.items) return []
  const order: string[] = Array.isArray(task.item_order) ? task.item_order : Object.keys(task.items)
  return order.map((k) => ({ key: k, ...task.items[k] })).filter((i) => !!i.name)
}

const activeTaskItems = computed(() => taskItemList(activeTask.value))
const activeTaskLines = computed(() => (activeTask.value?.lines || []).slice(-14))

const itemColorMap: Record<string, string> = {
  error: 'error', failed: 'error', cancelled: 'warning',
  started: 'success', done: 'success', pulled: 'success', created: 'success',
  'up-to-date': 'success', running: 'success', restarted: 'success',
  pulling: 'info', downloading: 'info', creating: 'info', starting: 'info',
  stopping: 'warning', removing: 'warning', skipped: 'grey',
  waiting: 'grey', extracting: 'info', restarting: 'warning',
}

function startTaskPolling() {
  if (taskTimer) return
  taskTimer = setInterval(() => { pollTasks() }, 1000)
  pollTasks()
}

function stopTaskPolling() {
  if (taskTimer) { clearInterval(taskTimer); taskTimer = null }
}

async function pollTasks() {
  if (!props.hostId) return
  const entries = (Object.entries(composeTasks.value) as [string, any][]).filter(([, t]) => t?.task_id && !t.done)
  if (entries.length === 0) { stopTaskPolling(); return }
  for (const [key, task] of entries) {
    try {
      const data: any = await dockerApi.getComposeTask(props.hostId, task.task_id)
      const merged = { ...task, ...data }
      composeTasks.value = { ...composeTasks.value, [key]: merged }
      if (activeTask.value?.task_id === task.task_id) activeTask.value = merged
      if (data.done) handleTaskDone(key, merged)
    } catch {
      // 单次失败（网络抖动）忽略；连续失败多半是后端重启导致任务表丢失
      task._pollFailures = (task._pollFailures || 0) + 1
      if (task._pollFailures >= 5) {
        const lost = {
          ...task, done: true, success: false, status: 'failed',
          error: '任务状态已丢失（后端可能重启），请刷新列表确认实际结果',
        }
        composeTasks.value = { ...composeTasks.value, [key]: lost }
        if (activeTask.value?.task_id === task.task_id) activeTask.value = lost
        handleTaskDone(key, lost)
      }
    }
  }
  if (!Object.values(composeTasks.value).some((t: any) => t?.task_id && !t.done)) stopTaskPolling()
}

function handleTaskDone(key: string, task: any) {
  if (task._notified) return
  task._notified = true
  composeTasks.value = { ...composeTasks.value, [key]: task }
  const name = task.is_bulk ? '批量任务' : (task.project || key)
  if (task.success) success(`${name} ${ACTION_LABELS[task.action] || ''}完成`)
  else if (task.status === 'cancelled') info(`${name} 已终止`)
  else showError(`${name} 失败：${task.error || '未知错误'}`)
  loadComposeProjects()
}

function openTaskDialog(key: string) {
  const task = composeTasks.value[key]
  if (!task) return
  activeTask.value = task
  showTaskDialog.value = true
  if (!task.done) startTaskPolling()
}

async function cancelActiveTask() {
  const task = activeTask.value
  if (!task || !props.hostId || !task.task_id) return
  cancelingTask.value = true
  try {
    const res: any = await dockerApi.cancelComposeTask(props.hostId, task.task_id)
    info(res?.message || '已请求终止')
  } catch (err: any) { showError(err.message || '终止请求失败') }
  finally { cancelingTask.value = false }
}

// ========== 项目操作 ==========
async function composeAction(project: any, action: string) {
  if (!props.hostId) return
  const key = project.name
  const running = taskFor(key)
  if (running) {
    // 已有进行中的任务：只重新打开进度面板，不重复发起
    openTaskDialog(key)
    info('该项目已有任务正在执行')
    return
  }
  startingActions.value[key] = true
  try {
    const res: any = await dockerApi.composeProjectAction(props.hostId, project.name, action, project.config_file || project.path)
    const taskId = res?.task_id
    if (!taskId) throw new Error(res?.message || '未返回任务 ID')
    const task = {
      task_id: taskId, project: project.name, action,
      status: 'pending', stage: 'pending',
      items: {}, item_order: [], lines: [], progress: { total: 0, completed: 0 },
      done: false, success: false, error: null,
    }
    composeTasks.value = { ...composeTasks.value, [key]: task }
    activeTask.value = task
    showTaskDialog.value = true
    if (res?.already_running) info(res.message || '该项目已有任务正在执行')
    startTaskPolling()
  } catch (err: any) { showError(err.message || '操作失败') }
  finally { startingActions.value[key] = false }
}

async function handleBulkComposeAction(action: string) {
  if (!props.hostId) return
  const actionText = action === 'up' ? '启动/更新' : '停止'
  const ok = await confirm({ title: `批量${actionText}`, content: `确定要${actionText}当前主机下的所有 Compose 项目吗？`, confirmColor: 'warning' })
  if (!ok) return
  if (taskFor(BULK_KEY)) { openTaskDialog(BULK_KEY); return }
  startingActions.value[BULK_KEY] = true
  try {
    const res: any = await dockerApi.composeBulkAction(props.hostId, { action })
    const taskId = res?.task_id
    if (!taskId) throw new Error(res?.message || '未返回任务 ID')
    const task = {
      task_id: taskId, project: '全部项目', action, is_bulk: true,
      status: 'pending', stage: action === 'up' ? 'creating' : 'stopping',
      items: {}, item_order: [], lines: [], progress: { total: res?.total || 0, completed: 0 },
      done: false, success: false, error: null,
    }
    composeTasks.value = { ...composeTasks.value, [BULK_KEY]: task }
    activeTask.value = task
    showTaskDialog.value = true
    if (res?.already_running) info(res.message || '批量任务已在执行')
    startTaskPolling()
  } catch { showError('操作失败') }
  finally { startingActions.value[BULK_KEY] = false }
}

async function handleDeleteComposeProject(project: any) {
  if (!props.hostId) return
  const ok = await confirm({ title: '移除项目', content: `确定要从视图中移除项目 ${project.name} 吗？`, confirmColor: 'error' })
  if (!ok) return
  try { await dockerApi.deleteComposeProject(props.hostId, project.name, project.config_file || project.path); success('项目已移除'); loadComposeProjects() }
  catch (err: any) { showError('操作失败: ' + (err.message || '未知错误')) }
}

async function createBackupTask(project: any) {
  if (!props.hostId) return
  const ok = await confirm({ title: '创建备份任务', content: `确定要为项目 ${project.name} 创建一个自动备份任务吗？`, confirmColor: 'info' })
  if (!ok) return
  try {
    await dockerApi.createComposeBackupTask(props.hostId, project.name, { path: project.config_file || project.path })
    success('备份任务已创建，可前往「数据备份管理」进行详细配置')
  } catch (err: any) { showError('创建失败: ' + (err.message || '未知错误')) }
}

// ========== 新建/编辑 ==========
const showComposeModal = ref(false)
const isEditingProject = ref(false)
const currentProject = ref({ name: '', content: '', path: '' })
const baseSavePath = ref('/opt/docker-compose')
const yamlError = ref<string | null>(null)

const storageKey = computed(() => `lens_last_path_${props.hostId}`)
const finalSavePath = computed(() => {
  const base = baseSavePath.value.replace(/\/+$/, '')
  const name = currentProject.value.name.trim() || 'project_name'
  return `${base}/${name}/docker-compose.yml`
})

// Vuetify v-textarea 的 auto-grow 在程序化赋值后不会自动重算高度，
// 需要在弹窗打开后手动触发一次内容变更来让 auto-grow 生效
function triggerAutoGrow() {
  nextTick(() => {
    const content = currentProject.value.content
    currentProject.value = { ...currentProject.value, content: content + ' ' }
    nextTick(() => {
      currentProject.value = { ...currentProject.value, content }
    })
  })
}

function handleCreateProject() {
  currentProject.value = { name: '', content: 'version: "3.8"\nservices:\n  app:\n    image: ', path: '' }
  isEditingProject.value = false; yamlError.value = null
  const saved = localStorage.getItem(storageKey.value)
  if (saved) baseSavePath.value = saved
  showComposeModal.value = true
  triggerAutoGrow()
}

async function editProject(project: any) {
  if (!props.hostId) return
  try {
    const res = await dockerApi.getComposeProject(props.hostId, project.name, project.config_file || project.path)
    currentProject.value = { ...res, path: project.config_file || project.path }
    isEditingProject.value = true; yamlError.value = null; showComposeModal.value = true
    triggerAutoGrow()
  } catch { showError('加载项目失败') }
}

async function saveProject() {
  if (!props.hostId) return
  if (!currentProject.value.name.trim()) { showError('请输入项目名称'); return }
  if (yamlError.value) { showError('请修正 YAML 错误后再保存'); return }
  const savePath = isEditingProject.value ? currentProject.value.path : finalSavePath.value
  try {
    await dockerApi.createComposeProject(props.hostId, { name: currentProject.value.name, content: currentProject.value.content }, savePath)
    success('保存成功')
    if (!isEditingProject.value) localStorage.setItem(storageKey.value, baseSavePath.value)
    showComposeModal.value = false; loadComposeProjects()
  } catch { showError('保存失败') }
}

function handleYamlInput() { yamlError.value = null }

function formatComposeStatus(status: string) {
  if (!status) return '未知'
  const map: Record<string, string> = { running: '运行中', exited: '已停止', restarting: '重启中', paused: '已暂停', created: '已创建', unknown: '未知' }
  const match = status.match(/^([a-z]+)\(?(\d*)\)?$/i)
  if (match) { const key = match[1].toLowerCase(); const count = match[2]; const text = map[key] || key; return count ? `${text}(${count})` : text }
  return status
}

const hasRunningTask = computed(() => Object.values(composeTasks.value).some((t: any) => t?.task_id && !t.done))

onUnmounted(() => { stopTaskPolling() })

defineExpose({ loadComposeProjects })
</script>

<template>
  <div>
    <div class="control-row mb-4">
      <v-btn prepend-icon="mdi-plus" color="primary" variant="tonal" size="small" @click="handleCreateProject">新建项目</v-btn>
      <v-text-field v-model="composeSearchQuery" prepend-inner-icon="mdi-magnify" placeholder="搜索项目..." variant="outlined" density="compact" hide-details clearable class="flex-grow-0" style="max-width:300px" />
      <v-spacer />
      <v-btn-group density="compact">
        <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" color="info" @click="loadComposeProjects" :loading="loadingCompose">刷新</v-btn>
        <v-btn prepend-icon="mdi-play" variant="tonal" size="small" color="success" :loading="startingActions[BULK_KEY]" @click="handleBulkComposeAction('up')">全部启动</v-btn>
        <v-btn prepend-icon="mdi-stop" variant="tonal" size="small" color="error" :loading="startingActions[BULK_KEY]" @click="handleBulkComposeAction('down')">全部停止</v-btn>
      </v-btn-group>
    </div>

    <v-progress-linear v-if="loadingCompose" indeterminate color="primary" class="mb-4" />

    <!-- 批量任务进行中的常驻提示条 -->
    <v-alert v-if="bulkTask" type="info" variant="tonal" density="compact" class="mb-4" prominent>
      <div class="d-flex align-center ga-2">
        <v-progress-circular size="16" width="2" indeterminate color="info" />
        <span class="text-body-2">批量{{ ACTION_LABELS[bulkTask.action] }}任务进行中：{{ taskStageText(bulkTask) }} {{ taskProgressText(bulkTask) }}</span>
        <v-spacer />
        <v-btn size="small" variant="text" @click="openTaskDialog(BULK_KEY)">查看进度</v-btn>
      </div>
    </v-alert>

    <v-row v-if="!loadingCompose && filteredComposeProjects.length === 0">
      <v-col cols="12" class="text-center py-12 text-medium-emphasis">
        <v-icon size="64" color="grey" class="mb-4">mdi-file-document-outline</v-icon>
        <div>暂无 Compose 项目</div>
      </v-col>
    </v-row>

    <div v-if="filteredComposeProjects.length" class="card-grid">
      <v-card
        v-for="project in filteredComposeProjects"
        :key="project.name"
        class="status-card liquid-glass-card"
        :class="{ 'is-running': project.status?.includes('running') }"
        rounded="lg"
      >
        <!-- 卡片头部 -->
        <div class="card-header pa-4 pb-2">
          <div class="card-title">
            <v-icon start color="primary" size="20">mdi-file-document-outline</v-icon>
            <span class="text-subtitle-2 font-weight-bold">{{ project.name }}</span>
            <v-chip v-if="project.type === 'scanned' || project.type === 'remembered'" size="x-small" variant="tonal" color="info">已记忆</v-chip>
            <v-chip v-else size="x-small" variant="outlined" color="warning">探测到</v-chip>
          </div>
          <v-chip :color="project.status?.includes('running') ? 'success' : 'grey'" size="small" variant="tonal" label>
            {{ formatComposeStatus(project.status) }}
          </v-chip>
        </div>

        <!-- 信息行 -->
        <div class="card-info card-info--stacked px-4 pb-2">
          <div class="info-item">
            <span class="info-label">路径</span>
            <span class="font-mono text-caption text-medium-emphasis text-truncate">{{ project.config_file || project.path }}</span>
          </div>
        </div>

        <!-- 任务进行中：卡内实时进度 -->
        <div v-if="taskFor(project.name)" class="px-4 pb-2">
          <div class="d-flex align-center ga-2 mb-1">
            <v-progress-circular size="14" width="2" indeterminate color="primary" />
            <span class="text-caption">{{ ACTION_LABELS[taskFor(project.name)?.action || ''] }} · {{ taskStageText(taskFor(project.name)) }}</span>
            <span class="text-caption text-medium-emphasis">{{ taskProgressText(taskFor(project.name)) }}</span>
            <v-spacer />
            <v-btn size="x-small" variant="text" color="primary" @click="openTaskDialog(project.name)">查看进度</v-btn>
          </div>
          <v-progress-linear indeterminate color="primary" height="4" rounded />
        </div>

        <!-- 操作按钮 -->
        <v-divider class="mt-2" />
        <div class="d-flex flex-wrap ga-2 pa-3">
          <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-play" :loading="startingActions[project.name]" @click="composeAction(project, 'up')">启动/更新</v-btn>
          <v-btn size="small" color="warning" variant="tonal" prepend-icon="mdi-download" :loading="startingActions[project.name]" @click="composeAction(project, 'pull')">拉取</v-btn>
          <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-stop" :loading="startingActions[project.name]" @click="composeAction(project, 'down')">停止</v-btn>
          <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="editProject(project)">编辑</v-btn>
          <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" @click="handleDeleteComposeProject(project)">删除</v-btn>
          <v-btn size="small" color="info" variant="tonal" prepend-icon="mdi-backup-restore" @click="createBackupTask(project)">备份</v-btn>
        </div>
      </v-card>
    </div>

    <!-- Compose 任务进度对话框 -->
    <GlassDialog
      v-model="showTaskDialog"
      :max-width="680"
      icon="mdi-progress-wrench"
      :title="'Compose ' + (ACTION_LABELS[activeTask?.action] || '任务') + ' — ' + (activeTask?.project || '')"
      cancel-text="关闭"
    >
      <template v-if="activeTask">
        <div class="d-flex align-center ga-2 mb-3">
          <v-chip
            :color="activeTask.success ? 'success' : activeTask.done ? (activeTask.status === 'cancelled' ? 'warning' : 'error') : 'info'"
            size="small" variant="tonal" label
          >
            {{ taskStageText(activeTask) }}
          </v-chip>
          <span class="text-caption text-medium-emphasis">{{ taskProgressText(activeTask) }}</span>
          <v-spacer />
          <v-btn v-if="!activeTask.done" size="small" color="error" variant="tonal" prepend-icon="mdi-stop" :loading="cancelingTask" @click="cancelActiveTask">终止</v-btn>
        </div>

        <v-progress-linear v-if="!activeTask.done" indeterminate color="primary" height="6" rounded class="mb-3" />
        <v-progress-linear v-else :model-value="100" :color="activeTask.success ? 'success' : (activeTask.status === 'cancelled' ? 'warning' : 'error')" height="6" rounded class="mb-3" />

        <!-- 条目进度（Container / Image / Network 或批量中的项目） -->
        <div v-if="activeTaskItems.length" class="mb-3">
          <div
            v-for="item in activeTaskItems"
            :key="item.key"
            class="d-flex align-center ga-2 text-caption mb-1"
          >
            <v-icon size="14" :color="itemColorMap[item.status] || 'grey'">
              {{ item.status === 'error' || item.status === 'failed' ? 'mdi-alert-circle-outline' : (['done', 'started', 'pulled', 'created', 'running', 'up-to-date', 'restarted', 'skipped'].includes(item.status) ? 'mdi-check-circle-outline' : 'mdi-circle-slice-4') }}
            </v-icon>
            <span v-if="item.kind" class="text-medium-emphasis">{{ item.kind }}</span>
            <span class="font-mono">{{ item.name }}</span>
            <v-spacer />
            <span :class="`text-${itemColorMap[item.status] || 'medium-emphasis'}`">{{ item.status_text || item.status }}</span>
          </div>
        </div>

        <v-alert v-if="activeTask.done && activeTask.error" type="error" variant="tonal" density="compact" class="mb-3">{{ activeTask.error }}</v-alert>
        <pre v-if="activeTaskLines.length" class="code-block code-block--flat">{{ activeTaskLines.join('\n') }}</pre>
      </template>
    </GlassDialog>

    <!-- Compose 编辑/新建弹窗 -->
    <GlassDialog v-model="showComposeModal" :max-width="800"
      :icon="'mdi-file-document-edit-outline'"
      :title="isEditingProject ? '编辑项目: ' + currentProject.name : '新建 Compose 项目'"
    >
      <v-text-field v-model="currentProject.name" label="项目名称" variant="outlined" density="compact" placeholder="例如: my-awesome-app" :disabled="isEditingProject" class="mb-3" />
      <template v-if="!isEditingProject">
        <v-text-field v-model="baseSavePath" label="基础保存路径" variant="outlined" density="compact" placeholder="选择存放项目的根目录" class="mb-3" />
        <div class="mb-3"><span class="text-body-2 text-medium-emphasis">完整保存路径：</span><code class="text-body-2">{{ finalSavePath }}</code></div>
      </template>
      <v-textarea v-model="currentProject.content" label="YAML 内容" variant="outlined" placeholder="在此输入 docker-compose.yml 内容" auto-grow rows="12" class="yaml-editor" :error-messages="yamlError ? [yamlError] : []" hide-details="auto" @update:model-value="handleYamlInput" />

      <template #actions>
        <v-btn color="primary" variant="tonal" prepend-icon="mdi-content-save-outline" @click="saveProject" :disabled="!!yamlError">保存项目</v-btn>
      </template>
    </GlassDialog>
  </div>
</template>
