<template>
  <div class="project-list">
    <n-space vertical>
      <n-space justify="space-between">
        <n-button type="primary" @click="openCreateModal">
          新建项目
        </n-button>
        <n-space>
          <n-button @click="fetchProjects">
            刷新列表
          </n-button>
          <n-button type="error" ghost @click="handleClearAllLogs">
            清空所有记录
          </n-button>
        </n-space>
      </n-space>

      <!-- 项目卡片列表：一行一个 -->
      <n-spin :show="loading">
        <div v-if="projects.length" class="project-list-cards">
          <div
            v-for="row in projects"
            :key="row.id"
            class="project-card"
          >
            <!-- 卡片头部：项目名称 + 目标仓库 -->
            <div class="card-header">
              <div class="card-title">
                <n-text strong class="project-name text-truncate">{{ row.name }}</n-text>
              </div>
              <n-tag v-if="getRegistry(row.registry_id)" size="small" type="warning" ghost>
                {{ getRegistry(row.registry_id).name }}
              </n-tag>
              <n-tag v-else size="small" type="default" ghost>默认仓库</n-tag>
            </div>

            <!-- 远程镜像名 -->
            <div class="card-desc">
              <n-text depth="3" class="desc-text">远程镜像: {{ row.repo_image_name }}</n-text>
            </div>

            <!-- 平台标签 -->
            <div class="card-platforms">
              <n-tag
                v-for="p in splitPlatforms(row.platforms)"
                :key="p"
                size="small"
                type="info"
                ghost
              >{{ p }}</n-tag>
            </div>

            <!-- 构建区：Tag 输入 + 立即构建 -->
            <div class="card-build">
              <n-input-group>
                <n-input
                  v-model:value="projectTags[row.id]"
                  size="small"
                  placeholder="Tag"
                  style="width: 120px; flex: 0 0 auto"
                />
                <n-button
                  size="small"
                  type="primary"
                  @click="directBuild(row)"
                >
                  立即构建
                </n-button>
              </n-input-group>
            </div>

            <!-- 操作按钮 -->
            <div class="card-actions">
              <n-button
                size="small"
                @click="openHistory(row)"
              >
                查看历史
              </n-button>
              <n-button
                size="small"
                type="info"
                ghost
                @click="openEditModal(row)"
              >
                修改
              </n-button>
              <n-button
                size="small"
                type="error"
                ghost
                @click="deleteProject(row)"
              >
                删除
              </n-button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <n-empty
          v-else-if="!loading"
          description="暂无项目"
          style="padding: 60px 0"
        />
      </n-spin>
    </n-space>

    <!-- 项目编辑弹窗 -->
    <n-modal v-model:show="showModal" preset="card" :title="editMode ? '编辑项目' : '新建项目'" style="width: 600px">
      <n-form :model="form" label-placement="left" label-width="120" ref="formRef">
        <n-form-item label="项目名称" path="name" required>
          <n-input v-model:value="form.name" placeholder="例如: My App" />
        </n-form-item>
        <n-form-item label="构建主机" path="host_id">
          <n-select v-model:value="form.host_id" :options="hostOptions" placeholder="选择执行构建的服务器" />
        </n-form-item>
        <n-form-item label="构建上下文" path="build_context" required>
          <n-input v-model:value="form.build_context" placeholder="宿主机目录, 例如: /root/my-app" />
        </n-form-item>
        <n-form-item label="Dockerfile 路径" path="dockerfile_path" required>
          <n-input v-model:value="form.dockerfile_path" placeholder="相对于上下文的路径, 例如: Dockerfile" />
        </n-form-item>
        <n-form-item label="本地镜像名" path="local_image_name" required>
          <n-input v-model:value="form.local_image_name" placeholder="例如: my-app" />
        </n-form-item>
        <n-form-item label="远程镜像名" path="repo_image_name" required>
          <n-input v-model:value="form.repo_image_name" placeholder="例如: username/my-app" />
        </n-form-item>
        <n-form-item label="目标平台" path="platforms">
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
        <n-form-item label="目标仓库" path="registry_id">
          <n-select v-model:value="form.registry_id" :options="registryOptions" clearable placeholder="选择推送仓库 (选填)" />
        </n-form-item>
        <n-form-item label="构建代理" path="proxy_id">
          <n-select v-model:value="form.proxy_id" :options="proxyOptions" clearable placeholder="选择代理 (选填)" />
        </n-form-item>
        <n-form-item label="构建选项">
          <n-space>
            <n-checkbox v-model:checked="form.no_cache">禁用缓存</n-checkbox>
            <n-checkbox v-model:checked="form.auto_cleanup">自动清理本地镜像</n-checkbox>
          </n-space>
        </n-form-item>

        <n-space justify="end">
          <n-button @click="showModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="saveProject">
            保存项目
          </n-button>
        </n-space>
      </n-form>
    </n-modal>

    <!-- 历史记录组件 -->
    <build-history 
      v-model:show="showHistory" 
      :project-id="selectedProjectId" 
      :project-name="selectedProjectName" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NSpace, NButton, NModal, NForm, NFormItem, NInput, NSelect,
  NCheckbox, useMessage, useDialog, NTag, NCheckboxGroup, NInputGroup, NSpin, NEmpty, NText
} from 'naive-ui'
import { imageBuilderApi } from '@/api/imageBuilder'
import BuildHistory from './BuildHistory.vue'

// 导入提取的逻辑
import { useImageBuilder } from '../hooks/useImageBuilder'

const message = useMessage()
const dialog = useDialog()

const {
  projects, registries, hostOptions, proxyOptions, registryOptions, loading, projectTags,
  fetchProjects, fetchOptions, directBuild, handleClearAllLogs, deleteProject: performDelete
} = useImageBuilder()

// 辅助函数：获取仓库信息
const getRegistry = (id: string) => {
  return registries.value.find((r: any) => r.id === id)
}

// 辅助函数：拆分平台字符串
const splitPlatforms = (platforms: string) => {
  return (platforms || '').split(',').filter((p: string) => p)
}

const showModal = ref(false)
const editMode = ref(false)
const currentProjectId = ref('')
const selectedPlatforms = ref(['linux/amd64'])

const showHistory = ref(false)
const selectedProjectId = ref('')
const selectedProjectName = ref('')

const form = ref({
  name: '', host_id: null, build_context: '', dockerfile_path: 'Dockerfile',
  local_image_name: '', repo_image_name: '', platforms: 'linux/amd64',
  registry_id: null, proxy_id: null, no_cache: false, auto_cleanup: true
})

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
  form.value.platforms = selectedPlatforms.value.join(',')
  try {
    if (editMode.value) { await imageBuilderApi.updateProject(currentProjectId.value, form.value) }
    else { await imageBuilderApi.addProject(form.value) }
    message.success('保存成功')
    showModal.value = false
    fetchProjects()
  } catch (e) { message.error('保存失败') }
}

const deleteProject = (row: any) => {
  performDelete(row, () => fetchProjects())
}

const openHistory = (row: any) => {
  selectedProjectId.value = row.id
  selectedProjectName.value = row.name
  showHistory.value = true
}

onMounted(() => { fetchProjects(); fetchOptions() })
</script>

<style scoped>
/* 卡片列表：一行一个卡片 */
.project-list-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.project-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  background: var(--card-bg-color, rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(64, 128, 240, 0.4);
  transition: border-color var(--transition-normal, 250ms ease),
              box-shadow var(--transition-normal, 250ms ease),
              transform var(--transition-fast, 150ms ease);
  position: relative;
  overflow: hidden;
}

.project-card:hover {
  border-color: rgba(64, 128, 240, 0.75);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.project-card:active {
  transform: scale(0.99);
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.project-name {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

/* 描述 */
.card-desc {
  min-width: 0;
}

.desc-text {
  font-size: 12px;
  line-height: 1.5;
  word-break: break-all;
}

/* 平台标签 */
.card-platforms {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* 构建区 */
.card-build {
  padding-top: 6px;
}

/* 操作按钮 */
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
}

.card-actions .n-button {
  flex: 1 1 auto;
  min-width: 56px;
}

/* 移动端适配 */
@media (max-width: 767px) {
  .card-actions .n-button {
    flex: 1 1 calc(33.333% - 4px);
    min-width: 0;
  }
}

@media (max-width: 380px) {
  .card-actions .n-button {
    flex: 1 1 100%;
  }
}
</style>