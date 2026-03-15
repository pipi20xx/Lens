<template>
  <div class="mobile-image-builder">
    <div class="page-header">
      <h1 class="page-title">镜像构建与推送</h1>
      <p class="page-desc">构建 Docker 镜像并推送到仓库</p>
    </div>

    <n-card class="build-card" :bordered="false" title="构建配置">
      <n-space vertical>
        <n-form-item label="镜像名称">
          <n-input v-model:value="config.imageName" placeholder="myapp:latest" />
        </n-form-item>
        <n-form-item label="Dockerfile 路径">
          <n-input v-model:value="config.dockerfilePath" placeholder="/path/to/Dockerfile" />
        </n-form-item>
        <n-form-item label="构建上下文">
          <n-input v-model:value="config.contextPath" placeholder="/path/to/context" />
        </n-form-item>
        <n-form-item label="目标仓库">
          <n-input v-model:value="config.registry" placeholder="registry.example.com" />
        </n-form-item>
        <n-button block type="primary" :loading="building" @click="startBuild">
          <template #icon><n-icon><BuildIcon /></n-icon></template>
          开始构建
        </n-button>
      </n-space>
    </n-card>

    <n-card v-if="buildLogs" class="logs-card" :bordered="false" title="构建日志">
      <div class="logs-content">
        <div v-for="(log, index) in buildLogs" :key="index" class="log-line">
          {{ log }}
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NCard, NButton, NSpace, NFormItem, NInput, NIcon } from 'naive-ui'
import { BuildOutlined as BuildIcon } from '@vicons/material'
import { imageBuilderApi } from '@/api/imageBuilder'
import { useMessage } from 'naive-ui'

const message = useMessage()
const building = ref(false)
const buildLogs = ref<string[]>([])

const config = ref({
  imageName: '',
  dockerfilePath: '',
  contextPath: '',
  registry: ''
})

const startBuild = async () => {
  if (!config.value.imageName || !config.value.dockerfilePath) {
    message.warning('请填写完整的构建配置')
    return
  }
  building.value = true
  buildLogs.value = []
  try {
    const project = {
      name: config.value.imageName,
      dockerfile_path: config.value.dockerfilePath,
      context_path: config.value.contextPath || config.value.dockerfilePath,
      registry: config.value.registry
    }
    const res = await imageBuilderApi.addProject(project)
    await imageBuilderApi.buildProject(res.id, { tag: 'latest' })
    message.success('镜像构建已启动')
  } catch (e) {
    message.error('构建失败')
  } finally {
    building.value = false
  }
}
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

.build-card,
.logs-card {
  margin-bottom: 12px;
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
