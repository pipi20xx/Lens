<template>
  <div class="mobile-image-project-list">
    <n-space vertical>
      <n-space justify="space-between" align="center">
        <n-button type="primary" size="small" @click="openCreateModal">
          新建项目
        </n-button>
        <n-space>
          <n-button size="small" secondary @click="fetchProjects">
            刷新
          </n-button>
          <n-button size="small" secondary type="error" @click="handleClearAllLogs">
            清空记录
          </n-button>
        </n-space>
      </n-space>

      <div v-if="projects.length === 0" class="empty-state">
        <n-empty description="暂无项目" size="small" />
      </div>

      <div v-else class="project-list">
        <div v-for="project in projects" :key="project.id" class="project-item">
          <div class="project-header">
            <div class="project-name">{{ project.name }}</div>
            <n-space>
              <n-button size="tiny" secondary type="info" @click="openHistory(project)">
                历史
              </n-button>
              <n-button size="tiny" secondary @click="openEditModal(project)">
                编辑
              </n-button>
              <n-popconfirm @positive-click="() => deleteProject(project)" positive-text="确认" negative-text="取消">
                <template #trigger>
                  <n-button size="tiny" secondary type="error">
                    删除
                  </n-button>
                </template>
                确认删除？
              </n-popconfirm>
            </n-space>
          </div>

          <div class="project-info">
            <div class="info-row">
              <n-icon size="14"><ServerIcon /></n-icon>
              <span>主机: {{ getHostName(project.host_id) }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><ImageIcon /></n-icon>
              <span>本地: {{ project.local_image_name }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><CloudIcon /></n-icon>
              <span>远程: {{ project.repo_image_name }}</span>
            </div>
            <div v-if="getRegistryName(project.registry_id)" class="info-row">
              <n-icon size="14"><RegistryIcon /></n-icon>
              <span>仓库: {{ getRegistryName(project.registry_id) }}</span>
            </div>
            <div v-if="getProxyName(project.proxy_id)" class="info-row">
              <n-icon size="14"><ProxyIcon /></n-icon>
              <span>代理: {{ getProxyName(project.proxy_id) }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><FolderIcon /></n-icon>
              <span>上下文: {{ project.build_context }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><FileIcon /></n-icon>
              <span>Dockerfile: {{ project.dockerfile_path }}</span>
            </div>
          </div>

          <div class="project-platforms">
            <n-tag v-for="platform in getPlatforms(project.platforms)" :key="platform" size="tiny" type="info" ghost>
              {{ platform }}
            </n-tag>
          </div>

          <div class="project-build">
            <n-input-group>
              <n-input 
                v-model:value="projectTags[project.id]" 
                placeholder="Tag" 
                size="small" 
                style="width: 80px"
              />
              <n-button 
                size="small" 
                type="primary" 
                @click="startBuild(project)"
                :loading="buildingProjectId === project.id"
              >
                构建
              </n-button>
            </n-input-group>
          </div>

          <div v-if="project.no_cache || !project.auto_cleanup" class="project-options">
            <n-tag v-if="project.no_cache" size="tiny" type="warning" ghost>禁用缓存</n-tag>
            <n-tag v-if="!project.auto_cleanup" size="tiny" type="warning" ghost>不清理镜像</n-tag>
          </div>
        </div>
      </div>
    </n-space>

    <n-modal v-model:show="showModal" preset="card" :title="editMode ? '编辑项目' : '新建项目'" style="width: 90vw; max-width: 500px">
      <n-form label-placement="top" size="small">
        <n-form-item label="项目名称" required>
          <n-input v-model:value="form.name" placeholder="例如: My App" />
        </n-form-item>
        <n-form-item label="构建主机">
          <n-select v-model:value="form.host_id" :options="hostOptions" placeholder="选择执行构建的服务器" />
        </n-form-item>
        <n-form-item label="构建上下文" required>
          <n-input v-model:value="form.build_context" placeholder="宿主机目录, 例如: /root/my-app" />
        </n-form-item>
        <n-form-item label="Dockerfile 路径" required>
          <n-input v-model:value="form.dockerfile_path" placeholder="相对于上下文的路径, 例如: Dockerfile" />
        </n-form-item>
        <n-form-item label="本地镜像名" required>
          <n-input v-model:value="form.local_image_name" placeholder="例如: my-app" />
        </n-form-item>
        <n-form-item label="远程镜像名" required>
          <n-input v-model:value="form.repo_image_name" placeholder="例如: username/my-app" />
        </n-form-item>
        <n-form-item label="目标平台">
          <n-checkbox-group v-model:value="selectedPlatforms">
            <n-space item-style="display: flex;">
              <n-checkbox value="linux/amd64" label="amd64" />
              <n-checkbox value="linux/arm64" label="arm64" />
              <n-checkbox value="linux/arm/v7" label="arm/v7" />
              <n-checkbox value="linux/arm/v6" label="arm/v6" />
              <n-checkbox value="linux/386" label="386" />
            </n-space>
          </n-checkbox-group>
        </n-form-item>
        <n-form-item label="目标仓库">
          <n-select v-model:value="form.registry_id" :options="registryOptions" clearable placeholder="选择推送仓库 (选填)" />
        </n-form-item>
        <n-form-item label="构建代理">
          <n-select v-model:value="form.proxy_id" :options="proxyOptions" clearable placeholder="选择代理 (选填)" />
        </n-form-item>
        <n-form-item label="构建选项">
          <n-space vertical>
            <n-checkbox v-model:checked="form.no_cache">禁用缓存</n-checkbox>
            <n-checkbox v-model:checked="form.auto_cleanup">自动清理本地镜像</n-checkbox>
          </n-space>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="saveProject" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <mobile-build-history 
      v-model:show="showHistory" 
      :project-id="selectedProjectId" 
      :project-name="selectedProjectName" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { 
  NSpace, NButton, NModal, NForm, NFormItem, NInput, NSelect,
  NCheckbox, NInputGroup, NIcon, NTag, NCheckboxGroup, NEmpty, NPopconfirm, useMessage, useDialog 
} from 'naive-ui'
import {
  DnsOutlined as ServerIcon,
  Cloud,
  Vpn
} from '@vicons/material'
import { imageBuilderApi } from '@/api/imageBuilder'
import MobileBuildHistory from './MobileBuildHistory.vue'
import { useImageBuilder } from '@/views/toolkit/image_builder/hooks/useImageBuilder'

const message = useMessage()
const dialog = useDialog()

const {
  projects, registries, hostOptions, proxyOptions, registryOptions, loading, projectTags,
  fetchProjects, fetchOptions, directBuild, handleClearAllLogs, deleteProject: performDelete
} = useImageBuilder()

const showModal = ref(false)
const editMode = ref(false)
const currentProjectId = ref('')
const selectedPlatforms = ref<string[]>(['linux/amd64'])
const saving = ref(false)
const buildingProjectId = ref('')

const showHistory = ref(false)
const selectedProjectId = ref('')
const selectedProjectName = ref('')

const form = ref({
  name: '', host_id: null, build_context: '', dockerfile_path: 'Dockerfile',
  local_image_name: '', repo_image_name: '', platforms: 'linux/amd64',
  registry_id: null, proxy_id: null, no_cache: false, auto_cleanup: true
})

const getHostName = (hostId: any) => {
  const host = hostOptions.value.find(h => h.value === hostId)
  return host ? host.label : '本地'
}

const getRegistryName = (registryId: any) => {
  const reg = registries.value.find((r: any) => r.id === registryId)
  return reg ? reg.name : ''
}

const getProxyName = (proxyId: any) => {
  const proxy = proxyOptions.value.find(p => p.value === proxyId)
  return proxy ? proxy.label : ''
}

const getPlatforms = (platformsStr: string) => {
  return platformsStr ? platformsStr.split(',') : ['linux/amd64']
}

const openCreateModal = () => {
  editMode.value = false
  selectedPlatforms.value = ['linux/amd64']
  form.value = {
    name: '', 
    host_id: hostOptions.value.length > 0 ? hostOptions.value[0].value : 'local',
    build_context: '', 
    dockerfile_path: 'Dockerfile', 
    local_image_name: '', 
    repo_image_name: '',
    platforms: 'linux/amd64', 
    registry_id: null, 
    proxy_id: null, 
    no_cache: false, 
    auto_cleanup: true
  }
  showModal.value = true
}

const openEditModal = (row: any) => {
  editMode.value = true
  currentProjectId.value = row.id
  form.value = { ...row }
  selectedPlatforms.value = row.platforms ? row.platforms.split(',') : ['linux/amd64']
  showModal.value = true
}

const saveProject = async () => {
  if (!form.value.name || !form.value.build_context || !form.value.dockerfile_path) {
    message.warning('请填写完整的项目信息')
    return
  }
  saving.value = true
  try {
    form.value.platforms = selectedPlatforms.value.join(',')
    if (editMode.value) {
      await imageBuilderApi.updateProject(currentProjectId.value, form.value)
      message.success('项目更新成功')
    } else {
      await imageBuilderApi.addProject(form.value)
      message.success('项目创建成功')
    }
    showModal.value = false
    fetchProjects()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const deleteProject = (row: any) => {
  performDelete(row, () => fetchProjects())
}

const startBuild = async (project: any) => {
  buildingProjectId.value = project.id
  try {
    const tag = projectTags[project.id] || 'latest'
    await directBuild(project, tag)
  } finally {
    buildingProjectId.value = ''
  }
}

const openHistory = (project: any) => {
  selectedProjectId.value = project.id
  selectedProjectName.value = project.name
  showHistory.value = true
}

onMounted(() => { 
  fetchProjects()
  fetchOptions()
})
</script>

<style scoped>
.mobile-image-project-list {
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
  background: var(--card-color);
  border: 1px solid #3B82F6;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 12px;
}

.project-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.project-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.project-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.7;
}

.project-platforms {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.project-build {
  margin-bottom: 8px;
}

.project-options {
  display: flex;
  gap: 4px;
}
</style>
