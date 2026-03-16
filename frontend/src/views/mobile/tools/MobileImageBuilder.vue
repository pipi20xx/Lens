<template>
  <div class="mobile-image-builder">
    <div class="page-header">
      <h1 class="page-title">镜像构建与推送</h1>
      <p class="page-desc">模块化管理 Docker 镜像构建项目，支持多平台构建、自动推送及代理加速</p>
    </div>

    <n-card class="tabs-card" :bordered="false">
      <n-tabs v-model:value="activeTab" type="segment" animated>
        <n-tab-pane name="projects" tab="项目管理">
          <mobile-image-project-list />
        </n-tab-pane>
        <n-tab-pane name="registries" tab="仓库管理">
          <mobile-image-registry-manager />
        </n-tab-pane>
        <n-tab-pane name="proxies" tab="代理设置">
          <mobile-image-proxy-manager />
        </n-tab-pane>
        <n-tab-pane name="system" tab="环境监测">
          <mobile-image-system-info />
        </n-tab-pane>
      </n-tabs>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NCard, NTabs, NTabPane } from 'naive-ui'
import MobileImageProjectList from './MobileImageProjectList.vue'
import MobileImageRegistryManager from './MobileImageRegistryManager.vue'
import MobileImageProxyManager from './MobileImageProxyManager.vue'
import MobileImageSystemInfo from './MobileImageSystemInfo.vue'

const activeTab = ref('projects')
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

.tabs-card {
  margin-bottom: 12px;
}
</style>
