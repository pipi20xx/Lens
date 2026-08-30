<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useNotification } from '@/composables'
import { useDockerHost } from './composables/useDockerHost'
import ContainerPanel from './components/ContainerPanel.vue'
import ImagePanel from './components/ImagePanel.vue'
import ComposePanel from './components/ComposePanel.vue'
import SystemPanel from './components/SystemPanel.vue'
import MaintenancePanel from './components/MaintenancePanel.vue'
import FileBrowserPanel from './components/FileBrowserPanel.vue'
import HostManagerDialog from './components/HostManagerDialog.vue'
import AutoUpdateDialog from './components/AutoUpdateDialog.vue'
import ScanScopeDialog from './components/ScanScopeDialog.vue'

const { success } = useNotification()
const { selectedHostId, currentHost, hostOptions, fetchHosts } = useDockerHost()

const activeTab = ref('containers')
const showHostManager = ref(false)
const showAutoUpdate = ref(false)
const showScanScope = ref(false)

const scanPathCount = computed(() =>
  (currentHost.value?.compose_scan_paths || '').split(',').map((p: string) => p.trim()).filter(Boolean).length
)

// 各 Tab 是否激活（传递给子组件，由子组件自行监听加载）
const containersActive = computed(() => activeTab.value === 'containers')
const imagesActive = computed(() => activeTab.value === 'images')
const composeActive = computed(() => activeTab.value === 'compose')
const systemActive = computed(() => activeTab.value === 'system')
const maintenanceActive = computed(() => activeTab.value === 'maintenance')
const filesActive = computed(() => activeTab.value === 'files')

// 子组件 ref，用于 refreshAll
const containerPanel = ref<InstanceType<typeof ContainerPanel> | null>(null)
const imagePanel = ref<InstanceType<typeof ImagePanel> | null>(null)
const composePanel = ref<InstanceType<typeof ComposePanel> | null>(null)
const systemPanel = ref<InstanceType<typeof SystemPanel> | null>(null)
const maintenancePanel = ref<InstanceType<typeof MaintenancePanel> | null>(null)
const fileBrowserPanel = ref<InstanceType<typeof FileBrowserPanel> | null>(null)

async function refreshAll() {
  await fetchHosts()
  containerPanel.value?.loadContainers()
  imagePanel.value?.loadImages()
  composePanel.value?.loadComposeProjects()
  systemPanel.value?.loadSystemInfo()
  maintenancePanel.value?.loadDaemonConfig()
  success('全部刷新完成')
}

onMounted(() => { fetchHosts() })
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2"><v-icon start>mdi-docker</v-icon> Docker 容器与项目管理</h1>
    <p class="text-body-2 text-medium-emphasis mb-4">统一管理多台远程主机的 Docker 容器及 Docker Compose 项目，支持一键部署与日志回溯。</p>

    <!-- 主机选择 & 管理 -->
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <div class="d-flex align-center pa-4 ga-3 flex-wrap">
        <v-select v-model="selectedHostId" :items="hostOptions" item-title="title" item-value="value" label="选择 Docker 主机" variant="outlined" density="compact" hide-details style="max-width:260px" prepend-inner-icon="mdi-server" />
        <v-btn prepend-icon="mdi-cog-outline" variant="tonal" color="primary" size="small" @click="showHostManager = true">管理主机</v-btn>

        <template v-if="selectedHostId">
          <v-btn prepend-icon="mdi-folder-multiple-outline" variant="tonal" color="info" size="small" @click="showScanScope = true">
            扫描范围 ({{ scanPathCount }})
          </v-btn>
          <span v-if="!scanPathCount" class="text-caption text-medium-emphasis">未配置，仅探测运行中项目</span>
        </template>

        <v-spacer />
        <v-btn prepend-icon="mdi-timer-outline" variant="tonal" size="small" color="warning" @click="showAutoUpdate = true">计划设置</v-btn>
        <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="refreshAll">全部刷新</v-btn>
      </div>
    </v-card>

    <v-tabs v-model="activeTab" class="mb-4" color="primary">
      <v-tab value="containers"><v-icon start>mdi-package-variant-closed</v-icon> 容器管理</v-tab>
      <v-tab value="images"><v-icon start>mdi-layers-triple-outline</v-icon> 镜像管理</v-tab>
      <v-tab value="compose"><v-icon start>mdi-file-document-outline</v-icon> Compose 管理</v-tab>
      <v-tab value="system"><v-icon start>mdi-information-outline</v-icon> 环境检测</v-tab>
      <v-tab value="maintenance"><v-icon start>mdi-wrench-outline</v-icon> 配置</v-tab>
      <v-tab value="files"><v-icon start>mdi-folder-outline</v-icon> 主机文件</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <v-window-item value="containers">
        <ContainerPanel ref="containerPanel" :active="containersActive" :host-id="selectedHostId" />
      </v-window-item>
      <v-window-item value="images">
        <ImagePanel ref="imagePanel" :active="imagesActive" :host-id="selectedHostId" />
      </v-window-item>
      <v-window-item value="compose">
        <ComposePanel ref="composePanel" :active="composeActive" :host-id="selectedHostId" />
      </v-window-item>
      <v-window-item value="system">
        <SystemPanel ref="systemPanel" :active="systemActive" :host-id="selectedHostId" />
      </v-window-item>
      <v-window-item value="maintenance">
        <MaintenancePanel ref="maintenancePanel" :active="maintenanceActive" :host-id="selectedHostId" />
      </v-window-item>
      <v-window-item value="files">
        <FileBrowserPanel ref="fileBrowserPanel" :active="filesActive" :host-id="selectedHostId" />
      </v-window-item>
    </v-window>

    <!-- 全局弹窗 -->
    <HostManagerDialog v-model="showHostManager" />
    <AutoUpdateDialog v-model="showAutoUpdate" />
    <ScanScopeDialog v-model="showScanScope" />
  </v-container>
</template>
