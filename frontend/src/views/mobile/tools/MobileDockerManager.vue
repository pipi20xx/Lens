<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NSpace, NCard, NText, NSelect, NButton, NIcon, NTag, NModal, NForm, NFormItem, NInput, useMessage } from 'naive-ui'
import { DnsOutlined as ServerIcon, RefreshOutlined as RefreshIcon, FolderOutlined as FolderIcon } from '@vicons/material'
import MobileDockerContainerList from './MobileDockerContainerList.vue'
import MobileDockerComposeList from './MobileDockerComposeList.vue'
import MobileDockerSystemInfo from './MobileDockerSystemInfo.vue'
import MobileDockerMaintenancePanel from './MobileDockerMaintenancePanel.vue'
import MobileDockerHostManager from './MobileDockerHostManager.vue'
import { dockerApi } from '@/api/docker'
import MobileTabs from '../components/MobileTabs.vue'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  MessageText,
  TagTypes,
} from '../constants'

const message = useMessage()

const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const messageText = MessageText
const tagTypes = TagTypes

const loading = ref(false)
const selectedHostId = ref<string | null>(null)
const hosts = ref<any[]>([])
const activeTab = ref('containers')

const placeholder = {
  SELECT_HOST: '选择 Docker 主机',
}

const tabs = [
  { name: 'containers', label: '容器' },
  { name: 'compose', label: 'Compose' },
  { name: 'system', label: '系统信息' },
  { name: 'maintenance', label: '维护' },
]
const showHostManager = ref(false)
const showAddPathModal = ref(false)
const newPath = ref('')
const saving = ref(false)

const hostOptions = computed(() => {
  return hosts.value.map(h => ({ label: h.name, value: h.id }))
})

const currentHost = computed(() => {
  return hosts.value.find(h => h.id === selectedHostId.value)
})

const loadHosts = async () => {
  try {
    const res = await dockerApi.getHosts()
    hosts.value = res as any || []
    if (hosts.value.length > 0 && !selectedHostId.value) {
      selectedHostId.value = hosts.value[0].id
    }
  } catch (e) {
    message.error(messageText.LOAD_FAILED)
  }
}

const refreshAll = async () => {
  loading.value = true
  try {
    await loadHosts()
    message.success(messageText.REFRESH_SUCCESS)
  } catch (e) {
    message.error(messageText.REFRESH_FAILED)
  } finally {
    loading.value = false
  }
}

const addScanPath = async () => {
  if (!newPath.value || !selectedHostId.value) {
    message.warning(messageText.PLEASE_INPUT_PATH)
    return
  }
  saving.value = true
  try {
    const host = hosts.value.find(h => h.id === selectedHostId.value)
    if (!host) return
    
    const pathList = (host.compose_scan_paths || '').split(',').map(p => p.trim()).filter(p => p)
    if (!pathList.includes(newPath.value)) {
      pathList.push(newPath.value)
      const updatedHost = { ...host, compose_scan_paths: pathList.join(',') }
      await dockerApi.updateHost(selectedHostId.value, updatedHost)
      message.success(messageText.PATH_ADDED)
      await loadHosts()
      showAddPathModal.value = false
      newPath.value = ''
    } else {
      message.warning(messageText.PATH_EXISTS)
    }
  } catch (e: any) {
    message.error(messageText.SAVE_FAILED + ': ' + (e.response?.data?.detail || messageText.UNKNOWN_ERROR))
  } finally {
    saving.value = false
  }
}

const removeScanPath = async (path: string) => {
  if (!selectedHostId.value) return
  try {
    const host = hosts.value.find(h => h.id === selectedHostId.value)
    if (!host) return
    
    const pathList = (host.compose_scan_paths || '').split(',').map(p => p.trim()).filter(p => p)
    const newList = pathList.filter(p => p !== path)
    const updatedHost = { ...host, compose_scan_paths: newList.join(',') }
    await dockerApi.updateHost(selectedHostId.value, updatedHost)
    message.success(messageText.PATH_REMOVED)
    await loadHosts()
  } catch (e: any) {
    message.error(messageText.SAVE_FAILED + ': ' + (e.response?.data?.detail || messageText.UNKNOWN_ERROR))
  }
}

onMounted(() => {
  loadHosts()
})
</script>

<template>
  <div class="mobile-docker-manager">
    <div class="page-header">
      <h1 class="page-title">Docker 容器管理</h1>
      <p class="page-desc">管理 Docker 容器与 Compose 项目</p>
    </div>

    <n-card class="filter-card" :bordered="false">
      <n-space vertical>
        <n-select 
          v-model:value="selectedHostId" 
          :options="hostOptions" 
          :placeholder="placeholder.SELECT_HOST"
          :size="buttonSizes.MEDIUM"
        />
        
        <div v-if="selectedHostId && currentHost" class="scan-paths-section">
          <div class="scan-label">
            <n-icon size="14"><FolderIcon /></n-icon>
            <span>扫描范围:</span>
          </div>
          <div v-if="currentHost.compose_scan_paths" class="path-tags">
            <n-tag 
              v-for="path in currentHost.compose_scan_paths.split(',').filter(p => p.trim())" 
              :key="path" 
              closable 
              :size="buttonSizes.TINY" 
              :type="tagTypes.INFO"
              @close="removeScanPath(path)"
            >
              {{ path }}
            </n-tag>
          </div>
          <n-text v-else depth="3" style="font-size: 12px">仅探测运行中项目</n-text>
          <n-button :size="buttonSizes.SMALL" secondary @click="showAddPathModal = true">
            {{ buttonText.ADD_PATH }}
          </n-button>
        </div>

        <n-space justify="space-between">
          <n-button :type="buttonTypes.PRIMARY" secondary @click="showHostManager = true" :size="buttonSizes.MEDIUM">
            {{ buttonText.MANAGE_HOST }}
          </n-button>
          <n-button :type="buttonTypes.INFO" secondary @click="refreshAll" :loading="loading" :size="buttonSizes.MEDIUM">
            {{ buttonText.REFRESH }}
          </n-button>
        </n-space>
      </n-space>
    </n-card>

    <n-card class="content-card" :bordered="false">
      <MobileTabs v-model="activeTab" :tabs="tabs">
        <template #containers>
          <MobileDockerContainerList :host-id="selectedHostId" />
        </template>
        <template #compose>
          <MobileDockerComposeList :host-id="selectedHostId" />
        </template>
        <template #system>
          <MobileDockerSystemInfo :host-id="selectedHostId" />
        </template>
        <template #maintenance>
          <MobileDockerMaintenancePanel :host-id="selectedHostId" />
        </template>
      </MobileTabs>
    </n-card>

    <MobileDockerHostManager 
      :show="showHostManager" 
      @update:show="showHostManager = $event"
      :hosts="hosts" 
      @refresh="loadHosts"
    />

    <n-modal v-model:show="showAddPathModal" preset="card" :title="buttonText.ADD_PATH" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item label="扫描路径" required>
          <n-input v-model:value="newPath" :placeholder="'例如: /opt/docker-compose'" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddPathModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="addScanPath" :loading="saving">{{ buttonText.ADD }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.mobile-docker-manager {
  padding: 16px;
  background: var(--app-bg-color);
  min-height: 100vh;
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

.filter-card,
.content-card {
  margin-bottom: 12px;
  background: var(--card-color);
  border-radius: 12px;
}

.scan-paths-section {
  margin: 12px 0;
  padding: 12px;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.scan-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 8px;
}

.path-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
</style>
