<template>
  <div class="mobile-emby-libraries">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">Emby 媒体库管理</h1>
      <p class="page-desc">管理您的 Emby 媒体库、路径配置及刮削策略</p>
    </div>

    <!-- 高危警告 -->
    <n-alert title="高危操作警告" type="error" :bordered="false" class="warning-alert">
      本模块主要用于<strong>新服务器的媒体库极速初始化</strong>。生产环境操作具有极高风险！
    </n-alert>

    <!-- 操作按钮 -->
    <n-card class="action-card" :bordered="false">
      <n-space vertical>
        <n-button block type="primary" secondary :loading="loading" @click="loadLibraries">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          刷新媒体库列表
        </n-button>
        <n-button block type="warning" secondary :loading="backingUpAll" @click="handleBackupAll">
          <template #icon><n-icon><BackupIcon /></n-icon></template>
          一键备份所有媒体库
        </n-button>
        <MobileEmbyConfigBackupManager category="libraries" :server-id="activeServerId" @restored="loadLibraries" />
        <n-button block type="primary" @click="showAddModal = true">
          <template #icon><n-icon><LibAddIcon /></n-icon></template>
          新增媒体库
        </n-button>
      </n-space>
    </n-card>

    <!-- 媒体库列表 -->
    <n-card class="libraries-card" :bordered="false" title="媒体库列表">
      <div v-if="libraries.length === 0" class="empty-state">
        <n-empty description="暂无媒体库" />
      </div>
      <div v-else class="library-list">
        <div v-for="lib in libraries" :key="lib.Id" class="library-item">
          <div class="library-info">
            <div class="library-name">{{ lib.Name }}</div>
            <div class="library-meta">
              <n-tag type="info" size="tiny" round>{{ lib.CollectionType || '未知' }}</n-tag>
              <code class="library-id">{{ lib.Id?.slice(0, 8) }}...</code>
            </div>
            <div v-if="lib.Path" class="library-path">{{ lib.Path }}</div>
          </div>
          <div class="library-actions">
            <n-button size="small" secondary type="info" @click="openEdit(lib)">
              <template #icon><n-icon><EditIcon /></n-icon></template>
              设置
            </n-button>
            <n-button size="small" secondary type="warning" @click="handleDirectBackup(lib)">
              <template #icon><n-icon><BackupIcon /></n-icon></template>
              备份
            </n-button>
            <n-popconfirm @positive-click="handleRemoveLibrary(lib.Name, lib.Id)" positive-text="确认移除" negative-text="取消">
              <template #trigger>
                <n-button size="small" secondary type="error">
                  <template #icon><n-icon><DeleteIcon /></n-icon></template>
                  移除
                </n-button>
              </template>
              确定移除媒体库 {{ lib.Name }}？
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 新增媒体库模态框 -->
    <n-modal v-model:show="showAddModal" preset="card" title="新增媒体库" style="width: 90vw; max-width: 400px">
      <n-space vertical>
        <n-form-item label="显示名称">
          <n-input v-model:value="newLib.name" placeholder="例如：电影" />
        </n-form-item>
        <n-form-item label="内容类型">
          <n-select v-model:value="newLib.type" :options="collectionTypeOptions" />
        </n-form-item>
        <n-form-item label="文件夹路径">
          <n-input v-model:value="newLib.path" placeholder="服务器绝对路径" />
        </n-form-item>
      </n-space>
      <template #action>
        <n-space justify="end">
          <n-button strong secondary @click="showAddModal = false">取消</n-button>
          <n-button type="primary" strong secondary :loading="adding" @click="handleAddLibrary">
            创建媒体库
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
  RefreshOutlined as RefreshIcon,
  BackupOutlined as BackupIcon,
  SettingsOutlined as EditIcon,
  DeleteOutlined as DeleteIcon,
  LibraryAddOutlined as LibAddIcon
} from '@vicons/material'

const message = useMessage()
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
    message.error('请先配置 Emby 服务器')
    return
  }
  loading.value = true
  try {
    const res = await listEmbyLibraries(activeServerId.value)
    libraries.value = res as any || []
  } catch (e: any) {
    message.error(e.response?.data?.detail || '加载媒体库列表失败')
  } finally {
    loading.value = false
  }
}

const handleAddLibrary = async () => {
  if (!newLib.name.trim()) {
    message.warning('请输入媒体库名称')
    return
  }
  adding.value = true
  try {
    await addEmbyLibrary(newLib.name.trim(), newLib.type, newLib.path.trim() || undefined, activeServerId.value)
    message.success('媒体库创建成功')
    newLib.name = ''
    newLib.path = ''
    showAddModal.value = false
    await loadLibraries()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建媒体库失败')
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
    message.success('媒体库已移除')
    await loadLibraries()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '移除媒体库失败')
  }
}

const handleDirectBackup = async (lib: any) => {
  try {
    await createEmbyBackup('libraries', lib.Id, activeServerId.value)
    message.success(`媒体库 ${lib.Name} 已备份`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '备份失败')
  }
}

const handleBackupAll = async () => {
  backingUpAll.value = true
  try {
    await createAllEmbyBackups('libraries', activeServerId.value)
    message.success('所有媒体库已备份')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '备份失败')
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
  background: var(--app-bg-color);
  border-radius: 8px;
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
