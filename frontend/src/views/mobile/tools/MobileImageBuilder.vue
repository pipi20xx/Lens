<template>
  <div class="mobile-image-builder">
    <div class="page-header">
      <h1 class="page-title">镜像构建与推送</h1>
      <p class="page-desc">模块化管理 Docker 镜像构建项目，支持多平台构建、自动推送及代理加速</p>
    </div>

    <n-card class="tabs-card" :bordered="false">
      <MobileTabs v-model="activeTab" :tabs="tabs">
        <template #projects>
          <mobile-image-project-list />
        </template>
        <template #registries>
          <mobile-image-registry-manager />
        </template>
        <template #proxies>
          <mobile-image-proxy-manager />
        </template>
        <template #system>
          <mobile-image-system-info />
        </template>
      </MobileTabs>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NCard } from 'naive-ui'
import MobileImageProjectList from './MobileImageProjectList.vue'
import MobileImageRegistryManager from './MobileImageRegistryManager.vue'
import MobileImageProxyManager from './MobileImageProxyManager.vue'
import MobileImageSystemInfo from './MobileImageSystemInfo.vue'
import MobileTabs from '../components/MobileTabs.vue'

const activeTab = ref('projects')

const tabs = [
  { name: 'projects', label: '项目列表' },
  { name: 'registries', label: '仓库管理' },
  { name: 'proxies', label: '代理设置' },
  { name: 'system', label: '系统信息' },
]
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
