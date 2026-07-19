<template>
  <div class="compose-panel">
    <!-- 顶部工具栏 -->
    <div class="toolbar-row" v-if="hostId">
      <div class="toolbar-left">
        <n-button type="primary" @click="handleCreateProject">
          新建项目
        </n-button>
        <n-input
          v-model:value="searchQuery"
          placeholder="搜索项目名称或路径..."
          clearable
          class="search-input"
        >
          <template #prefix>
            <n-icon><SearchIcon /></n-icon>
          </template>
        </n-input>
      </div>
      <n-button-group>
        <n-button type="info" ghost @click="fetchProjects(true)" :loading="loading">
          刷新
        </n-button>
        <n-button type="success" secondary @click="handleBulkAction('up')">
          全部启动/更新
        </n-button>
        <n-button type="error" secondary @click="handleBulkAction('down')">
          全部停止
        </n-button>
      </n-button-group>
    </div>

    <!-- 卡片网格 -->
    <n-spin :show="loading">
      <div v-if="filteredProjects.length" class="project-grid">
        <div
          v-for="row in filteredProjects"
          :key="row.name"
          class="project-card"
          :class="{ 'is-running': row.status?.includes('running') }"
        >
          <!-- 卡片头部：名称 + 状态 -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="project-name text-truncate">{{ row.name }}</n-text>
              <n-button
                v-if="row.type === 'detected'"
                size="tiny"
                circle
                quaternary
                @click="pinProject(row)"
                title="记忆项目路径"
              >
                <template #icon><n-icon><PushPinIcon /></n-icon></template>
              </n-button>
            </div>
            <n-tag
              :type="row.status?.includes('running') ? 'success' : 'default'"
              size="small"
              round
            >
              {{ formatStatus(row.status) }}
            </n-tag>
          </div>

          <!-- 类型标签 -->
          <div class="card-tags">
            <n-tag
              :type="row.type === 'scanned' ? 'info' : 'warning'"
              size="tiny"
              quaternary
            >
              {{ row.type === 'scanned' ? '已记忆' : '探测到' }}
            </n-tag>
          </div>

          <!-- 配置文件路径 -->
          <div class="card-path">
            <n-text depth="3" class="path-text text-clamp-2">{{ row.config_file || row.path }}</n-text>
            <n-button
              size="tiny"
              quaternary
              circle
              @click="emit('browse-path', row.path)"
              title="浏览路径"
            >
              <template #icon><n-icon><FolderIcon /></n-icon></template>
            </n-button>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <n-button
              size="small"
              type="primary"
              secondary
              :loading="loadingActions[row.name]"
              @click="runComposeAction(row, 'up')"
            >
              启动/更新
            </n-button>
            <n-button
              size="small"
              type="warning"
              secondary
              :loading="loadingActions[row.name]"
              @click="runComposeAction(row, 'pull')"
            >
              拉取
            </n-button>
            <n-button
              size="small"
              type="error"
              secondary
              :loading="loadingActions[row.name]"
              @click="runComposeAction(row, 'down')"
            >
              停止
            </n-button>
            <n-button
              size="small"
              secondary
              @click="editProject(row)"
            >
              编辑
            </n-button>
            <n-button
              size="small"
              type="error"
              secondary
              @click="deleteProject(row)"
            >
              删除
            </n-button>
            <n-button
              size="small"
              type="info"
              quaternary
              @click="createBackupTask(row)"
            >
              备份
            </n-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-else-if="!loading"
        description="暂无 Compose 项目"
        style="padding: 60px 0"
      />
    </n-spin>

    <!-- Compose 编辑/新建弹窗 -->
    <n-modal v-model:show="showComposeModal" preset="card" :title="isEditingProject ? '编辑项目: ' + currentProject.name : '新建 Compose 项目'" style="width: 800px">
      <n-form :model="currentProject" label-placement="left" label-width="100">
        <n-form-item label="项目名称">
          <n-input v-model:value="currentProject.name" placeholder="例如: my-awesome-app" :disabled="isEditingProject" />
        </n-form-item>

        <!-- 新建项目时的路径管理 -->
        <template v-if="!isEditingProject">
          <n-form-item label="基础保存路径">
            <n-input-group>
              <n-input v-model:value="baseSavePath" placeholder="选择存放项目的根目录" />
              <n-button type="primary" ghost @click="pickBasePath">
                选择
              </n-button>
            </n-input-group>
          </n-form-item>
          <n-form-item label="完整保存路径">
            <n-text depth="3" code style="word-break: break-all">
              {{ finalSavePath }}
            </n-text>
          </n-form-item>
        </template>

        <n-form-item label="YAML 内容" :feedback="yamlError" :validation-status="yamlError ? 'error' : undefined">
          <n-input
            v-model:value="currentProject.content"
            type="textarea"
            placeholder="在此输入 docker-compose.yml 内容"
            :autosize="{ minRows: 12, maxRows: 20 }"
            style="font-family: monospace"
            @input="handleYamlInput"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showComposeModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="saveProject" :disabled="!!yamlError">
            保存项目
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 命令行输出弹窗 -->
    <n-modal v-model:show="showCommandResult" preset="dialog" title="操作结果" style="width: 600px">
      <template #default>
        <div style="background: rgba(0, 0, 0, 0.3); color: var(--text-color); padding: 12px; font-family: 'Fira Code', 'JetBrains Mono', monospace; border-radius: 4px; overflow: auto; max-height: 400px; font-size: 12px;">
          <div v-if="commandResult.stdout"><b style="color: var(--primary-color)">STDOUT:</b><br>{{ commandResult.stdout }}</div>
          <div v-if="commandResult.stderr" style="margin-top: 10px"><b style="color: #f0a020">STDERR:</b><br>{{ commandResult.stderr }}</div>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, h } from 'vue'
import {
  NSpace, NButton, NButtonGroup, NTag, NIcon, NText,
  NModal, NForm, NFormItem, NInput, NInputGroup, NCheckbox, NSpin, NEmpty, useMessage, useDialog
} from 'naive-ui'
import {
  PushPinOutlined as PushPinIcon,
  FolderOutlined as FolderIcon,
  SearchOutlined as SearchIcon
} from '@vicons/material'
import axios from 'axios'
import yaml from 'js-yaml'
import { useDockerStore } from '@/store/dockerStore'

const props = defineProps({
  hostId: { type: String, default: null },
  hosts: { type: Array, default: [] },
  pickedPath: { type: String, default: '' }
})

const emit = defineEmits(['refresh-containers', 'refresh-hosts', 'browse-path', 'request-pick-path'])

const message = useMessage()
const dialog = useDialog()
const dockerStore = useDockerStore()

const projects = computed(() => (dockerStore.projects[props.hostId || ''] || []).sort((a: any, b: any) => a.name.localeCompare(b.name)))
const loading = computed(() => dockerStore.loading[`projects_${props.hostId}`] || false)

const loadingActions = ref<Record<string, boolean>>({})
const searchQuery = ref('')

const filteredProjects = computed(() => {
  const data = projects.value
  if (!searchQuery.value) return data
  const query = searchQuery.value.toLowerCase()
  return data.filter((p: any) =>
    p.name.toLowerCase().includes(query) ||
    (p.config_file || p.path || '').toLowerCase().includes(query)
  )
})

const showComposeModal = ref(false)
const showCommandResult = ref(false)
const commandResult = ref({ stdout: '', stderr: '' })
const currentProject = ref({ name: '', content: '', path: '' })
const isEditingProject = ref(false)
const yamlError = ref<string | null>(null)

const translateYamlError = (e: any) => {
  const reason = e.reason || ''
  const map: Record<string, string> = {
    'can not read a block mapping entry; a multiline key may not be an implicit key': '无法读取块映射条目；可能是缩进错误或缺少冒号',
    'bad indentation of a mapping entry': '映射条目缩进错误',
    'duplicated mapping key': '存在重复的键名',
    'end of the stream or a document separator is expected': '期望流结束或文档分隔符，请检查缩进',
    'incomplete explicit mapping pair': '不完整的显式映射对',
    'unknown tag': '未知的标签',
    'missed comma between flow collection entries': '流集合条目之间缺少逗号',
  }

  let msg = map[reason] || reason || 'YAML 格式错误'
  if (e.mark) {
    msg += ` (行 ${e.mark.line + 1}, 列 ${e.mark.column + 1})`
  }
  return msg
}

const handleYamlInput = (value: string) => {
  if (!value) {
    yamlError.value = null
    return
  }

  try {
    yaml.load(value)
    yamlError.value = null
  } catch (e: any) {
    yamlError.value = translateYamlError(e)
  }
}

// 状态本地化
const statusMap: Record<string, string> = {
  'running': '运行中',
  'exited': '已停止',
  'restarting': '重启中',
  'paused': '已暂停',
  'created': '已创建',
  'unknown': '未知'
}

const formatStatus = (status: string) => {
  if (!status) return '未知'
  const match = status.match(/^([a-z]+)\(?(\d*)\)?$/i)
  if (match) {
    const key = match[1].toLowerCase()
    const count = match[2]
    const text = statusMap[key] || key
    return count ? `${text}(${count})` : text
  }
  return status
}

const fetchProjects = async (force = false) => {
  if (!props.hostId) return
  await dockerStore.fetchProjects(props.hostId, force)
}

const createBackupTask = (p: any) => {
  dialog.info({
    title: '创建备份任务',
    content: `确定要为项目 ${p.name} 创建一个自动备份任务吗？该任务将定期备份整个项目文件夹并拉取到 Lens 本地服务器。`,
    positiveText: '确认创建',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.post(`/api/docker/compose/${props.hostId}/projects/${p.name}/create-backup-task`, {
          path: p.config_file || p.path
        })
        message.success('备份任务已创建，可前往"数据备份管理"进行详细配置')
      } catch (e: any) {
        message.error('创建失败: ' + (e.response?.data?.detail || '未知错误'))
      }
    }
  })
}

// 路径记忆逻辑
const baseSavePath = ref('/opt/docker-compose')
const storageKey = computed(() => `lens_last_path_${props.hostId}`)

const loadLastPath = () => {
  const saved = localStorage.getItem(storageKey.value)
  if (saved) baseSavePath.value = saved
}

const finalSavePath = computed(() => {
  const base = baseSavePath.value.replace(/\/+$/, '')
  const name = currentProject.value.name.trim() || 'project_name'
  return `${base}/${name}/docker-compose.yml`
})

watch(() => props.hostId, () => {
  fetchProjects()
  loadLastPath()
}, { immediate: true })

// 监听外部传回的路径
watch(() => props.pickedPath, (val) => {
  if (val && showComposeModal.value && !isEditingProject.value) {
    baseSavePath.value = val
  }
})

const handleBulkAction = (action: string) => {
  const actionText = action === 'up' ? '启动/更新' : '停止'
  dialog.warning({
    title: `批量${actionText}`,
    content: `确定要${actionText}当前主机下的所有 Compose 项目吗？这可能会消耗较多系统资源并导致服务短暂中断。`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      const m = message.loading(`正在批量${actionText}所有项目...`, { duration: 0 })
      try {
        await axios.post(`/api/docker/compose/${props.hostId}/projects/bulk-action`, { action })
        message.success(`批量${actionText}指令已发送`)
        fetchProjects(true)
        emit('refresh-containers')
      } catch (e) {
        message.error('操作失败')
      } finally {
        m.destroy()
      }
    }
  })
}

const handleCreateProject = () => {
  currentProject.value = {
    name: '',
    content: `version: "3.8"\nservices:\n  app:\n    image: `,
    path: ''
  }
  isEditingProject.value = false
  yamlError.value = null
  loadLastPath()
  showComposeModal.value = true
  handleYamlInput(currentProject.value.content)
}

const pickBasePath = () => {
  emit('request-pick-path', baseSavePath.value)
}

const editProject = async (p: any) => {
  const res = await axios.get(`/api/docker/compose/${props.hostId}/projects/${p.name}`, {
    params: { path: p.config_file || p.path }
  })
  currentProject.value = { ...res.data, path: p.config_file || p.path }
  isEditingProject.value = true
  yamlError.value = null
  showComposeModal.value = true
  handleYamlInput(currentProject.value.content)
}

const saveProject = async () => {
  if (!currentProject.value.name.trim()) {
    message.error('请输入项目名称')
    return
  }

  const savePath = isEditingProject.value ? currentProject.value.path : finalSavePath.value

  try {
    await axios.post(`/api/docker/compose/${props.hostId}/projects`,
      { name: currentProject.value.name, content: currentProject.value.content },
      { params: { path: savePath } }
    )
    message.success('保存成功')

    // 记忆路径
    if (!isEditingProject.value) {
      localStorage.setItem(storageKey.value, baseSavePath.value)
    }

    showComposeModal.value = false
    fetchProjects(true)
    // 自动扫描新路径
    if (!isEditingProject.value) pinProject({ path: savePath.substring(0, savePath.lastIndexOf('/')) })
  } catch (e) {
    message.error('保存失败')
  }
}

const deleteProject = (p: any) => {
  const deleteFiles = ref(false)

  dialog.error({
    title: '移除项目',
    content: () => h('div', null, [
      h('p', null, `确定要从视图中移除项目 ${p.name} 吗？`),
      h(NCheckbox, {
        checked: deleteFiles.value,
        'onUpdate:checked': (val: boolean) => deleteFiles.value = val,
        style: 'margin-top: 10px; color: #ff4d4f'
      }, { default: () => '同时彻底删除磁盘上的文件夹及 YML 文件' })
    ]),
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/docker/compose/${props.hostId}/projects/${p.name}`, {
          params: {
            path: p.config_file || p.path,
            delete_files: deleteFiles.value
          }
        })
        message.success(deleteFiles.value ? '项目及文件已删除' : '项目已从视图移除')
        fetchProjects(true)
      } catch (e) {
        message.error('操作失败: ' + ((e as any).response?.data?.detail || '未知错误'))
      }
    }
  })
}

const runComposeAction = async (p: any, action: string) => {
  loadingActions.value[p.name] = true
  try {
    const res = await axios.post(`/api/docker/compose/${props.hostId}/projects/${p.name}/action`, { action, path: p.config_file || p.path })

    if (res.data.success) {
      const noise = ['Started', 'Stopped', 'Stopping', 'Removing', 'Removed', 'Network', 'default']
      const stderr = res.data.stderr || ''
      const isNoise = noise.some(n => stderr.includes(n))

      const hasRealOutput = res.data.stdout?.trim() || (stderr.trim() && !isNoise)

      if (!hasRealOutput) {
        message.success('操作成功')
      } else {
        commandResult.value = { stdout: res.data.stdout, stderr: res.data.stderr }
        showCommandResult.value = true
      }
    } else {
      commandResult.value = { stdout: res.data.stdout, stderr: res.data.stderr }
      showCommandResult.value = true
      message.error('操作异常')
    }
    emit('refresh-containers')
  } catch (e) {
    message.error('请求失败')
  } finally {
    loadingActions.value[p.name] = false
    fetchProjects(true)
  }
}

const pinProject = async (p: any) => {
  const currentHost = props.hosts.find(h => h.id === props.hostId)
  if (!currentHost) return
  const path = p.path.substring(0, p.path.lastIndexOf('/'))
  const pathList = (currentHost.compose_scan_paths || '').split(',').map((i: string) => i.trim()).filter((i: string) => i)
  if (!pathList.includes(path)) {
    pathList.push(path)
    currentHost.compose_scan_paths = pathList.join(',')
    await axios.put(`/api/docker/hosts/${props.hostId}`, currentHost)
    message.success('项目路径已记忆')
    fetchProjects(true)
    emit('refresh-hosts')
  }
}

defineExpose({ refresh: fetchProjects })
</script>

<style scoped>
.compose-panel {
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
  flex: 1;
  min-width: 0;
}

.search-input {
  width: 250px;
  flex-shrink: 1;
  min-width: 180px;
}

/* 卡片网格：统一一行一个卡片 */
.project-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
  margin-top: 4px;
}

.project-card {
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

.project-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: transparent;
  transition: background var(--transition-normal);
}

.project-card.is-running::before {
  background: var(--color-success, #10B981);
}

.project-card:hover {
  border-color: var(--border-medium, rgba(255, 255, 255, 0.12));
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.project-card:active {
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

.project-name {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

.card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

/* 路径行 */
.card-path {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
}

.path-text {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  opacity: 0.6;
  line-height: 1.5;
  word-break: break-all;
}

/* 操作按钮 */
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
}

.card-actions .n-button {
  flex: 1 1 auto;
  min-width: 56px;
}

/* 移动端适配 */
@media (max-width: 767px) {
  .toolbar-row {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input {
    width: 100%;
  }

  .project-card {
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
