<template>
  <div class="mobile-emby-libraries">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">Emby 媒体库管理</h1>
      <p class="page-desc">管理您的 Emby 媒体库、路径配置及刮削策略</p>
    </div>

    <!-- 高危警告 -->
    <n-alert :title="alertText.HIGH_RISK_WARNING" :type="tagTypes.ERROR" :bordered="false" class="warning-alert">
      本模块主要用于<strong>新服务器的媒体库极速初始化</strong>。生产环境操作具有极高风险！
    </n-alert>

    <!-- 操作按钮 -->
    <n-card class="action-card" :bordered="false">
      <n-space vertical>
        <n-button block :type="buttonTypes.PRIMARY" secondary :loading="loading" @click="loadLibraries">
          {{ buttonText.REFRESH_LIBRARY_LIST }}
        </n-button>
        <n-button block :type="buttonTypes.WARNING" secondary :loading="backingUpAll" @click="handleBackupAll">
          {{ buttonText.BACKUP_ALL_LIBRARIES }}
        </n-button>
        <MobileEmbyConfigBackupManager category="libraries" :server-id="activeServerId" @restored="loadLibraries" />
        <n-button block :type="buttonTypes.PRIMARY" @click="showAddModal = true">
          {{ buttonText.ADD_LIBRARY }}
        </n-button>
      </n-space>
    </n-card>

    <!-- 媒体库列表 -->
    <n-card class="libraries-card" :bordered="false" :title="cardTitle.LIBRARY_LIST">
      <div v-if="libraries.length === 0" class="empty-state">
        <n-empty :description="emptyText.NO_LIBRARY" />
      </div>
      <div v-else class="library-list">
        <div v-for="lib in libraries" :key="lib.Id" class="library-item">
          <div class="library-info">
            <div class="library-name">{{ lib.Name }}</div>
            <div class="library-meta">
              <n-tag :type="tagTypes.INFO" size="tiny" round>{{ lib.CollectionType || '未知' }}</n-tag>
              <code class="library-id">{{ lib.Id?.slice(0, 8) }}...</code>
            </div>
            <div v-if="lib.Path" class="library-path">{{ lib.Path }}</div>
          </div>
          <div class="library-actions">
            <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.INFO" @click="openEdit(lib)">
              {{ buttonText.SETTINGS }}
            </n-button>
            <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.WARNING" @click="handleDirectBackup(lib)">
              {{ buttonText.BACKUP }}
            </n-button>
            <n-popconfirm @positive-click="handleRemoveLibrary(lib.Name, lib.Id)" :positive-text="confirmText.CONFIRM_REMOVE" :negative-text="confirmText.CANCEL">
              <template #trigger>
                <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
                  {{ buttonText.REMOVE }}
                </n-button>
              </template>
              确定移除媒体库 {{ lib.Name }}？
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 新增媒体库模态框 -->
    <n-modal v-model:show="showAddModal" preset="card" :title="modalTitle.ADD_LIBRARY" style="width: 90vw; max-width: 400px">
      <n-space vertical>
        <n-form-item :label="formLabel.DISPLAY_NAME">
          <n-input v-model:value="newLib.name" :placeholder="placeholder.EXAMPLE_MOVIE" />
        </n-form-item>
        <n-form-item :label="formLabel.CONTENT_TYPE">
          <n-select v-model:value="newLib.type" :options="collectionTypeOptions" />
        </n-form-item>
        <n-form-item :label="formLabel.FOLDER_PATH">
          <n-input v-model:value="newLib.path" :placeholder="placeholder.SERVER_ABSOLUTE_PATH" />
        </n-form-item>
      </n-space>
      <template #action>
        <n-space justify="end">
          <n-button strong secondary @click="showAddModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" strong secondary :loading="adding" @click="handleAddLibrary">
            {{ buttonText.CREATE_LIBRARY }}
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑媒体库模态框 -->
    <MobileLibraryEditModal 
      v-model:show="showEditModal"
      :library="editingLib"
      :server-id="activeServerId"
      @saved="loadLibraries"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { 
  NButton, NSpace, NTag, NPopconfirm, useMessage, NIcon, 
  NInput, NSelect, NCard, NModal, NFormItem, 
  NInputNumber, NDivider, NAlert, NEmpty 
} from 'naive-ui'
import { 
  listEmbyLibraries, 
  addEmbyLibrary, 
  removeEmbyLibrary
} from '@/api/embyLibraries'
import { createEmbyBackup, createAllEmbyBackups } from '@/api/embyBackup'
import { servers, activeServerId, fetchServers } from '@/store/serverStore'
import MobileLibraryEditModal from './MobileLibraryEditModal.vue'
import MobileEmbyConfigBackupManager from './MobileEmbyConfigBackupManager.vue'
import {
  BackupOutlined as BackupIcon,
  Library
} from '@vicons/material'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  TagTypes,
  MessageText,
} from '../constants'

const message = useMessage()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const tagTypes = TagTypes
const messageText = MessageText

// 额外的文本常量
const alertText = {
  HIGH_RISK_WARNING: '高危操作警告',
}

const cardTitle = {
  LIBRARY_LIST: '媒体库列表',
}

const emptyText = {
  NO_LIBRARY: '暂无媒体库',
}

const modalTitle = {
  ADD_LIBRARY: '新增媒体库',
}

const formLabel = {
  DISPLAY_NAME: '显示名称',
  CONTENT_TYPE: '内容类型',
  FOLDER_PATH: '文件夹路径',
}

const placeholder = {
  EXAMPLE_MOVIE: '例如：电影',
  SERVER_ABSOLUTE_PATH: '服务器绝对路径',
}

const confirmText = {
  CONFIRM_REMOVE: '确认移除',
  CANCEL: '取消',
}

const loading = ref(false)
const adding = ref(false)
const backingUpAll = ref(false)
const libraries = ref<any[]>([])

const showAddModal = ref(false)
const showEditModal = ref(false)
const editingLib = ref<any>({})

const newLib = reactive({
  name: '',
  type: 'movies',
  path: ''
})

const collectionTypeOptions = [
  { label: '电影', value: 'movies' },
  { label: '电视节目', value: 'tvshows' },
  { label: '音乐', value: 'music' },
  { label: '混合内容', value: 'mixed' }
]

const loadLibraries = async () => {
  if (!activeServerId.value) {
    await fetchServers()
  }
  if (!activeServerId.value) {
    message.error(messageText.CONFIG_SERVER_FIRST)
    return
  }
  loading.value = true
  try {
    const res = await listEmbyLibraries(activeServerId.value)
    libraries.value = res as any || []
  } catch (e: any) {
    message.error(e.response?.data?.detail || messageText.LOAD_LIBRARY_FAILED)
  } finally {
    loading.value = false
  }
}

const handleAddLibrary = async () => {
  if (!newLib.name.trim()) {
    message.warning(messageText.ENTER_LIBRARY_NAME)
    return
  }
  adding.value = true
  try {
    await addEmbyLibrary(newLib.name.trim(), newLib.type, newLib.path.trim() || undefined, activeServerId.value)
    message.success(messageText.CREATE_LIBRARY_SUCCESS)
    newLib.name = ''
    newLib.path = ''
    showAddModal.value = false
    await loadLibraries()
  } catch (e: any) {
    message.error(e.response?.data?.detail || messageText.CREATE_LIBRARY_FAILED)
  } finally {
    adding.value = false
  }
}

const openEdit = (lib: any) => {
  editingLib.value = { ...lib }
  showEditModal.value = true
}

const handleRemoveLibrary = async (name: string, id: string) => {
  try {
    await removeEmbyLibrary(name, id, activeServerId.value)
    message.success(messageText.REMOVE_LIBRARY_SUCCESS)
    await loadLibraries()
  } catch (e: any) {
    message.error(e.response?.data?.detail || messageText.REMOVE_LIBRARY_FAILED)
  }
}

const handleDirectBackup = async (lib: any) => {
  try {
    await createEmbyBackup('libraries', lib.Id, activeServerId.value)
    message.success(`媒体库 ${lib.Name} 已备份`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || messageText.BACKUP_FAILED)
  }
}

const handleBackupAll = async () => {
  backingUpAll.value = true
  try {
    await createAllEmbyBackups('libraries', activeServerId.value)
    message.success(messageText.BACKUP_ALL_SUCCESS)
  } catch (e: any) {
    message.error(e.response?.data?.detail || messageText.BACKUP_FAILED)
  } finally {
    backingUpAll.value = false
  }
}

onMounted(() => {
  loadLibraries()
})
</script>

<style scoped>
.mobile-emby-libraries {
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

.warning-alert {
  margin-bottom: 12px;
}

.action-card,
.libraries-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.library-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.library-item {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
  margin-bottom: 12px;
}

.library-info {
  margin-bottom: 8px;
}

.library-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.library-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.library-id {
  font-size: 11px;
  color: var(--text-color);
  opacity: 0.5;
  background: var(--border-color);
  padding: 2px 6px;
  border-radius: 4px;
}

.library-path {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  word-break: break-all;
}

.library-actions {
  display: flex;
  gap: 8px;
}
</style>
