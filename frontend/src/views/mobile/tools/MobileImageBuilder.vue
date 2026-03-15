<template>
  <div class="mobile-image-builder">
    <div class="page-header">
      <h1 class="page-title">镜像构建与推送</h1>
      <p class="page-desc">构建 Docker 镜像并推送到仓库</p>
    </div>

    <n-card class="tabs-card" :bordered="false">
      <n-tabs v-model:value="activeTab" type="segment" animated>
        <n-tab-pane name="projects" tab="项目管理">
          <n-space vertical>
            <n-space>
              <n-button type="primary" @click="openCreateModal">
                <template #icon><n-icon><AddIcon /></n-icon></template>
                新建项目
              </n-button>
              <n-button @click="fetchProjects">
                <template #icon><n-icon><RefreshIcon /></n-icon></template>
                刷新
              </n-button>
            </n-space>
            <div v-if="projects.length === 0" class="empty-state">
              <n-empty description="暂无项目" />
            </div>
            <div v-else class="project-list">
              <div v-for="project in projects" :key="project.id" class="project-item">
                <div class="project-info">
                  <div class="project-name">{{ project.name }}</div>
                  <div class="project-detail">本地: {{ project.local_image_name }}</div>
                  <div class="project-detail">远程: {{ project.repo_image_name }}</div>
                  <div class="project-platforms">
                    <n-tag v-for="platform in project.platforms" :key="platform" size="tiny">
                      {{ platform }}
                    </n-tag>
                  </div>
                </div>
                <div class="project-actions">
                  <n-button size="small" type="primary" @click="startBuild(project)">
                    <template #icon><n-icon><BuildIcon /></n-icon></template>
                    构建
                  </n-button>
                  <n-button size="small" secondary @click="openEditModal(project)">
                    <template #icon><n-icon><EditIcon /></n-icon></template>
                    编辑
                  </n-button>
                  <n-popconfirm @positive-click="handleDeleteProject(project.id)" positive-text="确认" negative-text="取消">
                    <template #trigger>
                      <n-button size="small" secondary type="error">
                        <template #icon><n-icon><DeleteIcon /></n-icon></template>
                        删除
                      </n-button>
                    </template>
                    确定删除此项目？
                  </n-popconfirm>
                </div>
              </div>
            </div>
          </n-space>
        </n-tab-pane>

        <n-tab-pane name="registries" tab="仓库管理">
          <n-space vertical>
            <n-button type="primary" @click="openRegistryModal">
              <template #icon><n-icon><AddIcon /></n-icon></template>
              添加仓库
            </n-button>
            <div v-if="registries.length === 0" class="empty-state">
              <n-empty description="暂无仓库" />
            </div>
            <div v-else class="registry-list">
              <div v-for="registry in registries" :key="registry.id" class="registry-item">
                <div class="registry-info">
                  <div class="registry-name">{{ registry.name }}</div>
                  <div class="registry-url">{{ registry.url }}</div>
                </div>
                <div class="registry-actions">
                  <n-button size="small" secondary @click="openEditRegistryModal(registry)">
                    <template #icon><n-icon><EditIcon /></n-icon></template>
                    编辑
                  </n-button>
                  <n-popconfirm @positive-click="handleDeleteRegistry(registry.id)" positive-text="确认" negative-text="取消">
                    <template #trigger>
                      <n-button size="small" secondary type="error">
                        <template #icon><n-icon><DeleteIcon /></n-icon></template>
                        删除
                      </n-button>
                    </template>
                    确定删除此仓库？
                  </n-popconfirm>
                </div>
              </div>
            </div>
          </n-space>
        </n-tab-pane>

        <n-tab-pane name="proxies" tab="代理设置">
          <n-space vertical>
            <n-button type="primary" @click="openProxyModal">
              <template #icon><n-icon><AddIcon /></n-icon></template>
              添加代理
            </n-button>
            <div v-if="proxies.length === 0" class="empty-state">
              <n-empty description="暂无代理" />
            </div>
            <div v-else class="proxy-list">
              <div v-for="proxy in proxies" :key="proxy.id" class="proxy-item">
                <div class="proxy-info">
                  <div class="proxy-name">{{ proxy.name }}</div>
                  <div class="proxy-url">{{ proxy.url }}</div>
                </div>
                <div class="proxy-actions">
                  <n-button size="small" secondary @click="openEditProxyModal(proxy)">
                    <template #icon><n-icon><EditIcon /></n-icon></template>
                    编辑
                  </n-button>
                  <n-popconfirm @positive-click="handleDeleteProxy(proxy.id)" positive-text="确认" negative-text="取消">
                    <template #trigger>
                      <n-button size="small" secondary type="error">
                        <template #icon><n-icon><DeleteIcon /></n-icon></template>
                        删除
                      </n-button>
                    </template>
                    确定删除此代理？
                  </n-popconfirm>
                </div>
              </div>
            </div>
          </n-space>
        </n-tab-pane>

        <n-tab-pane name="system" tab="环境监测">
          <n-space vertical>
            <n-card title="系统信息" :bordered="false">
              <n-descriptions label-placement="left" :column="1" size="small">
                <n-descriptions-item label="Docker 版本">
                  <n-tag type="info">v20.10.0</n-tag>
                </n-descriptions-item>
                <n-descriptions-item label="Buildx 版本">
                  <n-tag type="success">v0.11.0</n-tag>
                </n-descriptions-item>
                <n-descriptions-item label="支持平台">
                  <n-space>
                    <n-tag size="small">linux/amd64</n-tag>
                    <n-tag size="small">linux/arm64</n-tag>
                    <n-tag size="small">linux/arm/v7</n-tag>
                  </n-space>
                </n-descriptions-item>
              </n-descriptions>
            </n-card>
          </n-space>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <n-card v-if="buildLogs.length > 0" class="logs-card" :bordered="false" title="构建日志">
      <div class="logs-content">
        <div v-for="(log, index) in buildLogs" :key="index" class="log-line">
          {{ log }}
        </div>
      </div>
    </n-card>

    <!-- 项目编辑弹窗 -->
    <n-modal v-model:show="showProjectModal" preset="card" :title="editMode ? '编辑项目' : '新建项目'" style="width: 90vw; max-width: 500px">
      <n-form label-placement="top" size="small">
        <n-form-item label="项目名称">
          <n-input v-model:value="projectForm.name" placeholder="例如: My App" />
        </n-form-item>
        <n-form-item label="构建上下文">
          <n-input v-model:value="projectForm.build_context" placeholder="/root/my-app" />
        </n-form-item>
        <n-form-item label="Dockerfile 路径">
          <n-input v-model:value="projectForm.dockerfile_path" placeholder="Dockerfile" />
        </n-form-item>
        <n-form-item label="本地镜像名">
          <n-input v-model:value="projectForm.local_image_name" placeholder="my-app" />
        </n-form-item>
        <n-form-item label="远程镜像名">
          <n-input v-model:value="projectForm.repo_image_name" placeholder="username/my-app" />
        </n-form-item>
        <n-form-item label="目标平台">
          <n-checkbox-group v-model:value="selectedPlatforms">
            <n-space item-style="display: flex;">
              <n-checkbox value="linux/amd64" label="amd64" />
              <n-checkbox value="linux/arm64" label="arm64" />
              <n-checkbox value="linux/arm/v7" label="arm/v7" />
            </n-space>
          </n-checkbox-group>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showProjectModal = false">取消</n-button>
          <n-button type="primary" @click="saveProject" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 仓库编辑弹窗 -->
    <n-modal v-model:show="showRegistryModal" preset="card" :title="editRegistryMode ? '编辑仓库' : '添加仓库'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="仓库名称">
          <n-input v-model:value="registryForm.name" placeholder="Docker Hub" />
        </n-form-item>
        <n-form-item label="仓库地址">
          <n-input v-model:value="registryForm.url" placeholder="https://registry-1.docker.io" />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input v-model:value="registryForm.username" placeholder="username" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="registryForm.password" type="password" show-password-on="click" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showRegistryModal = false">取消</n-button>
          <n-button type="primary" @click="saveRegistry" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 代理编辑弹窗 -->
    <n-modal v-model:show="showProxyModal" preset="card" :title="editProxyMode ? '编辑代理' : '添加代理'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="代理名称">
          <n-input v-model:value="proxyForm.name" placeholder="本地代理" />
        </n-form-item>
        <n-form-item label="代理地址">
          <n-input v-model:value="proxyForm.url" placeholder="http://127.0.0.1:7890" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showProxyModal = false">取消</n-button>
          <n-button type="primary" @click="saveProxy" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NFormItem, NInput, NInputNumber, NIcon, NTabs, NTabPane, NEmpty, NModal, NForm, NTag, NCheckboxGroup, NCheckbox, NDescriptions, NDescriptionsItem, NPopconfirm } from 'naive-ui'
import { BuildOutlined as BuildIcon, AddOutlined as AddIcon, RefreshOutlined as RefreshIcon, EditOutlined as EditIcon, DeleteOutlineOutlined as DeleteIcon } from '@vicons/material'
import { imageBuilderApi } from '@/api/imageBuilder'
import { useMessage } from 'naive-ui'

const message = useMessage()
const activeTab = ref('projects')
const building = ref(false)
const saving = ref(false)
const buildLogs = ref<string[]>([])

const projects = ref<any[]>([])
const registries = ref<any[]>([])
const proxies = ref<any[]>([])

const showProjectModal = ref(false)
const showRegistryModal = ref(false)
const showProxyModal = ref(false)

const editMode = ref(false)
const editRegistryMode = ref(false)
const editProxyMode = ref(false)

const selectedPlatforms = ref<string[]>(['linux/amd64'])

const projectForm = ref({
  name: '',
  build_context: '',
  dockerfile_path: '',
  local_image_name: '',
  repo_image_name: '',
  platforms: ['linux/amd64']
})

const registryForm = ref({
  name: '',
  url: '',
  username: '',
  password: ''
})

const proxyForm = ref({
  name: '',
  url: ''
})

const fetchProjects = async () => {
  try {
    projects.value = await imageBuilderApi.getProjects()
  } catch (e: any) {
    message.error('获取项目列表失败: ' + (e.message || '未知错误'))
  }
}

const fetchRegistries = async () => {
  try {
    registries.value = await imageBuilderApi.getRegistries()
  } catch (e: any) {
    message.error('获取仓库列表失败: ' + (e.message || '未知错误'))
  }
}

const fetchProxies = async () => {
  try {
    proxies.value = await imageBuilderApi.getProxies()
  } catch (e: any) {
    message.error('获取代理列表失败: ' + (e.message || '未知错误'))
  }
}

const openCreateModal = () => {
  editMode.value = false
  projectForm.value = {
    name: '',
    build_context: '',
    dockerfile_path: '',
    local_image_name: '',
    repo_image_name: '',
    platforms: ['linux/amd64']
  }
  selectedPlatforms.value = ['linux/amd64']
  showProjectModal.value = true
}

const openEditModal = (project: any) => {
  editMode.value = true
  projectForm.value = {
    name: project.name,
    build_context: project.build_context,
    dockerfile_path: project.dockerfile_path,
    local_image_name: project.local_image_name,
    repo_image_name: project.repo_image_name,
    platforms: project.platforms || ['linux/amd64']
  }
  selectedPlatforms.value = project.platforms || ['linux/amd64']
  showProjectModal.value = true
}

const saveProject = async () => {
  if (!projectForm.value.name || !projectForm.value.build_context || !projectForm.value.dockerfile_path) {
    message.warning('请填写完整的项目信息')
    return
  }
  saving.value = true
  try {
    const data = {
      ...projectForm.value,
      platforms: selectedPlatforms.value
    }
    if (editMode.value) {
      await imageBuilderApi.updateProject(projectForm.value.id, data)
      message.success('项目更新成功')
    } else {
      await imageBuilderApi.addProject(data)
      message.success('项目创建成功')
    }
    showProjectModal.value = false
    await fetchProjects()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleDeleteProject = async (id: string) => {
  try {
    await imageBuilderApi.deleteProject(id)
    message.success('项目已删除')
    await fetchProjects()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

const startBuild = async (project: any) => {
  building.value = true
  buildLogs.value = []
  try {
    await imageBuilderApi.buildProject(project.id, { tag: 'latest' })
    message.success('镜像构建已启动')
    buildLogs.value = ['构建已启动...']
  } catch (e: any) {
    message.error('构建失败')
    buildLogs.value = ['构建失败: ' + (e.message || '未知错误')]
  } finally {
    building.value = false
  }
}

const openRegistryModal = () => {
  editRegistryMode.value = false
  registryForm.value = { name: '', url: '', username: '', password: '' }
  showRegistryModal.value = true
}

const openEditRegistryModal = (registry: any) => {
  editRegistryMode.value = true
  registryForm.value = { ...registry }
  showRegistryModal.value = true
}

const saveRegistry = async () => {
  if (!registryForm.value.name || !registryForm.value.url) {
    message.warning('请填写完整的仓库信息')
    return
  }
  saving.value = true
  try {
    if (editRegistryMode.value) {
      await imageBuilderApi.updateProject(registryForm.value.id, registryForm.value)
      message.success('仓库更新成功')
    } else {
      await imageBuilderApi.addProject(registryForm.value)
      message.success('仓库添加成功')
    }
    showRegistryModal.value = false
    await fetchRegistries()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleDeleteRegistry = async (id: string) => {
  try {
    await imageBuilderApi.deleteProject(id)
    message.success('仓库已删除')
    await fetchRegistries()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

const openProxyModal = () => {
  editProxyMode.value = false
  proxyForm.value = { name: '', url: '' }
  showProxyModal.value = true
}

const openEditProxyModal = (proxy: any) => {
  editProxyMode.value = true
  proxyForm.value = { ...proxy }
  showProxyModal.value = true
}

const saveProxy = async () => {
  if (!proxyForm.value.name || !proxyForm.value.url) {
    message.warning('请填写完整的代理信息')
    return
  }
  saving.value = true
  try {
    if (editProxyMode.value) {
      await imageBuilderApi.updateProject(proxyForm.value.id, proxyForm.value)
      message.success('代理更新成功')
    } else {
      await imageBuilderApi.addProject(proxyForm.value)
      message.success('代理添加成功')
    }
    showProxyModal.value = false
    await fetchProxies()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleDeleteProxy = async (id: string) => {
  try {
    await imageBuilderApi.deleteProject(id)
    message.success('代理已删除')
    await fetchProxies()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

onMounted(() => {
  fetchProjects()
  fetchRegistries()
  fetchProxies()
})
</script>

<style scoped>
.mobile-image-builder {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.tabs-card,
.logs-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 40px 0;
}

.project-list,
.registry-list,
.proxy-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.project-item,
.registry-item,
.proxy-item {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
}

.project-info,
.registry-info,
.proxy-info {
  margin-bottom: 8px;
}

.project-name,
.registry-name,
.proxy-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.project-detail,
.registry-url,
.proxy-url {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 2px;
}

.project-platforms {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.project-actions,
.registry-actions,
.proxy-actions {
  display: flex;
  gap: 8px;
}

.logs-content {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.log-line {
  font-size: 12px;
  color: var(--text-color);
  font-family: monospace;
  padding: 2px 0;
  white-space: pre-wrap;
}
</style>
