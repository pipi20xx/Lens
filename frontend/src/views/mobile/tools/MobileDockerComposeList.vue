<template>
  <div class="mobile-docker-compose-list">
    <n-space vertical>
      <n-space justify="space-between" align="center">
        <n-button type="primary" size="small" @click="handleCreateProject">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          新建项目
        </n-button>
        <n-button size="small" secondary @click="fetchProjects(true)" :loading="loading">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          刷新
        </n-button>
      </n-space>

      <n-input
        v-model:value="searchQuery"
        placeholder="搜索项目名称或路径..."
        clearable
        size="small"
      >
        <template #prefix>
          <n-icon><SearchIcon /></n-icon>
        </template>
      </n-input>

      <div v-if="filteredProjects.length === 0" class="empty-state">
        <n-empty description="暂无项目" size="small" />
      </div>

      <div v-else class="project-list">
        <div v-for="project in filteredProjects" :key="project.name" class="project-item">
          <div class="project-header">
            <div class="project-name">
              <n-text strong>{{ project.name }}</n-text>
              <n-tag :type="project.type === 'scanned' ? 'info' : 'warning'" size="tiny" ghost>
                {{ project.type === 'scanned' ? '已记忆' : '探测到' }}
              </n-tag>
            </div>
            <n-tag :type="project.status?.includes('running') ? 'success' : 'default'" size="small" round>
              {{ formatStatus(project.status) }}
            </n-tag>
          </div>

          <div class="project-info">
            <div class="info-row">
              <n-icon size="14"><FileIcon /></n-icon>
              <n-text depth="3" style="font-size: 12px">{{ project.config_file || project.path }}</n-text>
            </div>
          </div>

          <div class="project-actions">
            <n-button size="tiny" type="primary" secondary @click="runComposeAction(project, 'up')" :loading="loadingActions[project.name]">
              <template #icon><n-icon><StartIcon /></n-icon></template>
              启动
            </n-button>
            <n-button size="tiny" type="warning" secondary @click="runComposeAction(project, 'pull')" :loading="loadingActions[project.name]">
              <template #icon><n-icon><PullIcon /></n-icon></template>
              拉取
            </n-button>
            <n-button size="tiny" type="error" secondary @click="runComposeAction(project, 'down')" :loading="loadingActions[project.name]">
              <template #icon><n-icon><StopIcon /></n-icon></template>
              停止
            </n-button>
            <n-button size="tiny" secondary @click="editProject(project)">
              <template #icon><n-icon><EditIcon /></n-icon></template>
              编辑
            </n-button>
            <n-button size="tiny" type="info" secondary @click="createBackupTask(project)">
              <template #icon><n-icon><BackupIcon /></n-icon></template>
              备份
            </n-button>
            <n-popconfirm @positive-click="() => deleteProject(project)" positive-text="确认" negative-text="取消">
              <template #trigger>
                <n-button size="tiny" secondary type="error">
                  <template #icon><n-icon><DeleteIcon /></n-icon></template>
                </n-button>
              </template>
              确认删除？
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-space>

    <n-modal v-model:show="showComposeModal" preset="card" :title="isEditingProject ? '编辑项目' : '新建项目'" style="width: 90vw; max-width: 600px">
      <n-form label-placement="top" size="small">
        <n-form-item label="项目名称">
          <n-input v-model:value="currentProject.name" placeholder="例如: my-awesome-app" :disabled="isEditingProject" />
        </n-form-item>
        
        <template v-if="!isEditingProject">
          <n-form-item label="基础保存路径">
            <n-input-group>
              <n-input v-model:value="baseSavePath" placeholder="选择存放项目的根目录" />
              <n-button type="primary" ghost @click="pickBasePath">
                <template #icon><n-icon><FolderIcon /></n-icon></template>
                选择
              </n-button>
            </n-input-group>
          </n-form-item>
          <n-form-item label="完整保存路径">
            <n-text depth="3" code style="word-break: break-all; font-size: 12px">
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
            style="font-family: monospace; font-size: 12px"
            @input="handleYamlInput"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showComposeModal = false">取消</n-button>
          <n-button type="primary" @click="saveProject" :disabled="!!yamlError" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { 
  NSpace, NButton, NTag, NIcon, NText, NModal, NForm, NFormItem, 
  NInput, NInputGroup, NEmpty, NPopconfirm, useMessage, useDialog 
} from 'naive-ui'
import { 
  AddOutlined as AddIcon,
  EditOutlined as EditIcon,
  DeleteOutlined as DeleteIcon,
  PlayCircleOutlined as StartIcon,
  StopCircleOutlined as StopIcon,
  CloudDownloadOutlined as PullIcon,
  SearchOutlined as SearchIcon,
  BackupTableRound as BackupIcon,
  AutorenewOutlined as RefreshIcon,
  FolderOutlined as FolderIcon,
  DescriptionOutlined as FileIcon
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
const saving = ref(false)

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
const currentProject = ref({ name: '', content: '', path: '' })
const isEditingProject = ref(false)
const yamlError = ref<string | null>(null)
const baseSavePath = ref('/opt/docker-compose')

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

const fetchProjects = async (force = false) => {
  if (!props.hostId) return
  await dockerStore.fetchProjects(props.hostId, force)
}

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

watch(() => props.pickedPath, (val) => {
  if (val && showComposeModal.value && !isEditingProject.value) {
    baseSavePath.value = val
  }
})

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
  
  saving.value = true
  try {
    await axios.post(`/api/docker/compose/${props.hostId}/projects`, 
      { name: currentProject.value.name, content: currentProject.value.content },
      { params: { path: savePath } }
    )
    message.success('保存成功')
    
    if (!isEditingProject.value) {
      localStorage.setItem(storageKey.value, baseSavePath.value)
    }

    showComposeModal.value = false
    fetchProjects(true) 
  } catch (e: any) {
    message.error('保存失败: ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    saving.value = false
  }
}

const deleteProject = (p: any) => {
  dialog.error({
    title: '移除项目',
    content: `确定要从视图中移除项目 ${p.name} 吗？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/docker/compose/${props.hostId}/projects/${p.name}`, { 
          params: { path: p.config_file || p.path }
        })
        message.success('项目已从视图移除')
        fetchProjects(true)
      } catch (e: any) {
        message.error('操作失败: ' + (e.response?.data?.detail || '未知错误'))
      }
    }
  })
}

const runComposeAction = async (p: any, action: string) => {
  loadingActions.value[p.name] = true
  try {
    const res = await axios.post(`/api/docker/compose/${props.hostId}/projects/${p.name}/action`, { action, path: p.config_file || p.path })
    
    if (res.data.success) {
      message.success('操作成功')
    } else {
      message.error('操作异常')
    }
    emit('refresh-containers')
  } catch (e: any) {
    message.error('请求失败: ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    loadingActions.value[p.name] = false
    fetchProjects(true)
  }
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

defineExpose({ refresh: fetchProjects })
</script>

<style scoped>
.mobile-docker-compose-list {
  padding: 12px 0;
}

.empty-state {
  padding: 40px 0;
}

.project-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.project-item {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.project-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 500;
}

.project-info {
  margin-bottom: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.project-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
