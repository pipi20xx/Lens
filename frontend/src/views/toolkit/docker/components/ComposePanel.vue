<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError, info } = useNotification()
const { confirm } = useConfirm()

const props = defineProps<{
  active: boolean
  hostId: string | null
}>()

// ========== 自动加载 ==========
watch([() => props.active, () => props.hostId], ([active, hostId]) => {
  if (active && hostId) loadComposeProjects()
})
onMounted(() => { if (props.active && props.hostId) loadComposeProjects() })

// ========== 列表 ==========
const composeProjects = ref<any[]>([])
const loadingCompose = ref(false)
const composeSearchQuery = ref('')
const loadingActions = ref<Record<string, boolean>>({})

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

// ========== 项目操作 ==========
async function composeAction(projectName: string, action: string, projectPath?: string) {
  if (!props.hostId) return
  loadingActions.value[projectName] = true
  try {
    await dockerApi.composeProjectAction(props.hostId, projectName, action, projectPath)
    success(`${action} 已触发`)
    setTimeout(() => loadComposeProjects(), 3000)
  } catch (err: any) { showError(err.message || '操作失败') }
  finally { loadingActions.value[projectName] = false }
}

async function handleBulkComposeAction(action: string) {
  if (!props.hostId) return
  const actionText = action === 'up' ? '启动/更新' : '停止'
  const ok = await confirm({ title: `批量${actionText}`, content: `确定要${actionText}当前主机下的所有 Compose 项目吗？`, confirmColor: 'warning' })
  if (!ok) return
  try {
    await dockerApi.composeBulkAction(props.hostId, { action })
    success(`批量${actionText}指令已发送`)
    loadComposeProjects()
  } catch { showError('操作失败') }
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

function handleCreateProject() {
  currentProject.value = { name: '', content: 'version: "3.8"\nservices:\n  app:\n    image: ', path: '' }
  isEditingProject.value = false; yamlError.value = null
  const saved = localStorage.getItem(storageKey.value)
  if (saved) baseSavePath.value = saved
  showComposeModal.value = true
}

async function editProject(project: any) {
  if (!props.hostId) return
  try {
    const res = await dockerApi.getComposeProject(props.hostId, project.name, project.config_file || project.path)
    currentProject.value = { ...res, path: project.config_file || project.path }
    isEditingProject.value = true; yamlError.value = null; showComposeModal.value = true
  } catch { showError('加载项目失败') }
}

async function saveProject() {
  if (!props.hostId) return
  if (!currentProject.value.name.trim()) { showError('请输入项目名称'); return }
  if (yamlError.value) { showError('请修正 YAML 错误后再保存'); return }
  try {
    await dockerApi.createComposeProject(props.hostId, { name: currentProject.value.name, content: currentProject.value.content })
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

defineExpose({ loadComposeProjects })
</script>

<template>
  <div>
    <div class="d-flex ga-3 mb-4 flex-wrap">
      <v-btn prepend-icon="mdi-plus" color="primary" variant="tonal" size="small" @click="handleCreateProject">新建项目</v-btn>
      <v-text-field v-model="composeSearchQuery" prepend-inner-icon="mdi-magnify" placeholder="搜索项目..." variant="outlined" density="compact" hide-details clearable style="max-width:300px" />
      <v-spacer />
      <v-btn-group density="compact">
        <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="loadComposeProjects" :loading="loadingCompose">刷新</v-btn>
        <v-btn prepend-icon="mdi-play" variant="tonal" size="small" color="success" @click="handleBulkComposeAction('up')">全部启动</v-btn>
        <v-btn prepend-icon="mdi-stop" variant="tonal" size="small" color="error" @click="handleBulkComposeAction('down')">全部停止</v-btn>
      </v-btn-group>
    </div>

    <v-progress-linear v-if="loadingCompose" indeterminate color="primary" class="mb-4" />

    <v-row v-if="!loadingCompose && filteredComposeProjects.length === 0">
      <v-col cols="12" class="text-center py-12 text-medium-emphasis">
        <v-icon size="64" color="grey" class="mb-4">mdi-file-document-outline</v-icon>
        <div>暂无 Compose 项目</div>
      </v-col>
    </v-row>

    <div class="d-flex flex-column ga-3">
      <v-card v-for="project in filteredComposeProjects" :key="project.name" class="status-card liquid-glass-card" rounded="lg" :class="{'is-running': project.status?.includes('running')}">
        <div class="pa-4">
          <div class="d-flex align-center mb-1">
            <div class="d-flex align-center ga-1 flex-grow-1" style="min-width:0">
              <span class="text-subtitle-2 font-weight-bold">{{ project.name }}</span>
              <v-chip v-if="project.type === 'scanned'" size="x-small" variant="tonal" color="info">已记忆</v-chip>
              <v-chip v-else size="x-small" variant="outlined" color="warning">探测到</v-chip>
            </div>
            <v-chip :color="project.status?.includes('running') ? 'success' : 'grey'" size="small" variant="tonal" label>{{ formatComposeStatus(project.status) }}</v-chip>
          </div>
          <div class="text-caption text-medium-emphasis font-mono mb-2" style="opacity:0.6;word-break:break-all;font-size:11px">{{ project.config_file || project.path }}</div>
          <v-divider class="my-2" />
          <div class="d-flex flex-wrap ga-2">
            <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-play" :loading="loadingActions[project.name]" @click="composeAction(project.name, 'up', project.config_file || project.path)">启动/更新</v-btn>
            <v-btn size="small" color="warning" variant="tonal" prepend-icon="mdi-download" :loading="loadingActions[project.name]" @click="composeAction(project.name, 'pull', project.config_file || project.path)">拉取</v-btn>
            <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-stop" :loading="loadingActions[project.name]" @click="composeAction(project.name, 'down', project.config_file || project.path)">停止</v-btn>
            <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="editProject(project)">编辑</v-btn>
            <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" @click="handleDeleteComposeProject(project)">删除</v-btn>
            <v-btn size="small" color="info" variant="tonal" prepend-icon="mdi-backup-restore" @click="createBackupTask(project)">备份</v-btn>
          </div>
        </div>
      </v-card>
    </div>

    <!-- Compose 编辑/新建弹窗 -->
    <v-dialog v-model="showComposeModal" max-width="800">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-file-document-edit-outline</v-icon>
          {{ isEditingProject ? '编辑项目: ' + currentProject.name : '新建 Compose 项目' }}
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-text-field v-model="currentProject.name" label="项目名称" variant="outlined" density="compact" placeholder="例如: my-awesome-app" :disabled="isEditingProject" class="mb-3" />
          <template v-if="!isEditingProject">
            <v-text-field v-model="baseSavePath" label="基础保存路径" variant="outlined" density="compact" placeholder="选择存放项目的根目录" class="mb-3" />
            <div class="mb-3"><span class="text-body-2 text-medium-emphasis">完整保存路径：</span><code class="text-body-2">{{ finalSavePath }}</code></div>
          </template>
          <v-textarea v-model="currentProject.content" label="YAML 内容" variant="outlined" placeholder="在此输入 docker-compose.yml 内容" rows="14" style="font-family:'Fira Code','JetBrains Mono',monospace" :error-messages="yamlError ? [yamlError] : []" @update:model-value="handleYamlInput" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showComposeModal = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveProject" :disabled="!!yamlError">保存项目</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

