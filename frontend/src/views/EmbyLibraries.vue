<template>
  <div class="emby-libraries-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">Emby 媒体库管理</n-text></n-h2>
        <n-text depth="3">管理您的 Emby 媒体库、路径配置及刮削策略。</n-text>
      </div>

      <n-alert title="高危操作警告" type="error" bordered>
        <template #icon>⚠️</template>
        本模块主要用于<strong>新服务器的媒体库极速初始化</strong>。通过直接推送 JSON 配置实现设置恢复。<br/>
        在生产环境服务器上进行删除、修改路径等操作具有极高风险，可能导致媒体库索引损坏或元数据丢失。<strong>非必要请勿操作，后果自负。</strong>
      </n-alert>

      <n-card size="small" segmented :bordered="false" class="main-card">
        <template #header>
          <n-space align="center">
            <n-button 
              strong 
              secondary 
              type="primary" 
              size="small" 
              @click="loadLibraries" 
              :loading="loading"
            >
              刷新媒体库列表
            </n-button>
            <n-button 
              strong 
              secondary 
              type="warning" 
              size="small" 
              @click="handleBackupAll" 
              :loading="backingUpAll"
            >
              一键备份所有媒体库
            </n-button>
            <EmbyConfigBackupManager category="libraries" :server-id="activeServerId" @restored="loadLibraries" />
          </n-space>
        </template>
        <template #header-extra>
          <n-button 
            type="primary" 
            size="small" 
            @click="showAddModal = true"
          >
            新增媒体库
          </n-button>
        </template>

        <n-data-table
          :columns="columns"
          :data="libraries"
          :loading="loading"
          size="small"
          :bordered="false"
        />
      </n-card>
    </n-space>

    <!-- 新增媒体库模态框 -->
    <n-modal v-model:show="showAddModal" preset="card" title="新增媒体库" style="width: 500px" :bordered="false">
      <n-form label-placement="left" label-width="100" size="small">
        <n-form-item label="显示名称">
          <n-input v-model:value="newLib.name" placeholder="例如：电影" />
        </n-form-item>
        <n-form-item label="内容类型">
          <n-select v-model:value="newLib.type" :options="collectionTypeOptions" />
        </n-form-item>
        <n-form-item label="文件夹路径">
          <n-input v-model:value="newLib.path" placeholder="服务器绝对路径" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button strong secondary @click="showAddModal = false">
            取消
          </n-button>
          <n-button type="primary" strong secondary @click="handleAddLibrary" :loading="adding">
            创建媒体库
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 引用拆分后的编辑模态框 -->
    <LibraryEditModal 
      v-model:show="showEditModal"
      :library="editingLib"
      :server-id="activeServerId"
      @saved="loadLibraries"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive, h } from 'vue'
import { NButton, NSpace, NTag, NPopconfirm, useMessage, NIcon, NInput, NSelect, NCard, NDataTable, NModal, NForm, NFormItem, NAlert, NText } from 'naive-ui'
import { 
  listEmbyLibraries, 
  addEmbyLibrary, 
  removeEmbyLibrary 
} from '@/api/embyLibraries'
import { createEmbyBackup, createAllEmbyBackups } from '@/api/embyBackup'
import { servers, activeServerId, fetchServers } from '@/store/serverStore'
import LibraryEditModal from './emby-library/LibraryEditModal.vue'
import EmbyConfigBackupManager from '@/components/EmbyConfigBackupManager.vue'
import { 
  RefreshOutlined as RefreshIcon,
  BackupOutlined as BackupIcon,
  SettingsOutlined as EditIcon,
  DeleteOutlined as DeleteIcon,
  LibraryAddOutlined as LibAddIcon,
  CheckOutlined as CheckIcon,
  CloseOutlined as CloseIcon
} from '@vicons/material'

const message = useMessage()
const loading = ref(false)
const adding = ref(false)
const backingUpAll = ref(false)
const libraries = ref<any[]>([])

const showAddModal = ref(false)
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

const showEditModal = ref(false)
const editingLib = ref<any>(null)

const columns = [
  { title: '名称', key: 'Name' },
  { 
    title: '类型', 
    key: 'CollectionType', 
    render: (row: any) => h(NTag, { type: 'info', size: 'small', round: true, quaternary: true }, { default: () => row.CollectionType }) 
  },
  { 
    title: 'ID', 
    key: 'Id', 
    render: (row: any) => h('code', { style: 'font-size: 12px; opacity: 0.6' }, row.Id) 
  },
  {
    title: '操作',
    key: 'actions',
    render(row: any) {
      return h(NSpace, null, {
        default: () => [
          h(NButton, { 
            size: 'tiny', 
            strong: true,
            secondary: true, 
            type: 'info',
            onClick: () => openEdit(row) 
          }, { 
            default: () => '设置',
            icon: () => h(NIcon, null, { default: () => h(EditIcon) })
          }),
          h(NButton, { 
            size: 'tiny', 
            strong: true,
            secondary: true, 
            type: 'warning',
            onClick: () => handleDirectBackup(row) 
          }, { 
            default: () => '备份',
            icon: () => h(NIcon, null, { default: () => h(BackupIcon) })
          }),
          h(NPopconfirm, {
            onPositiveClick: () => handleRemoveLibrary(row.Name, row.Id),
            positiveText: '确认移除',
            negativeText: '取消'
          }, {
            trigger: () => h(NButton, { 
              size: 'tiny', 
              strong: true,
              secondary: true, 
              type: 'error'
            }, { 
              default: () => '移除',
              icon: () => h(NIcon, null, { default: () => h(DeleteIcon) })
            }),
            default: () => `确定移除媒体库 ${row.Name}？`
          })
        ]
      })
    }
  }
]

const loadLibraries = async () => {
  if (!activeServerId.value) return
  loading.value = true
  try {
    const res = await listEmbyLibraries(activeServerId.value)
    libraries.value = res as any
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleAddLibrary = async () => {
  if (!newLib.name) return
  adding.value = true
  try {
    await addEmbyLibrary(newLib.name, newLib.type, newLib.path, activeServerId.value)
    message.success('媒体库创建指令已发送')
    showAddModal.value = false
    loadLibraries()
  } catch (e) {
    console.error(e)
  } finally {
    adding.value = false
  }
}

const handleBackupAll = async () => {
  backingUpAll.value = true
  try {
    const res: any = await createAllEmbyBackups('libraries', activeServerId.value)
    message.success(`成功备份 ${res.count} 个媒体库配置`)
  } catch (e) {
    console.error(e)
  } finally {
    backingUpAll.value = false
  }
}

const handleRemoveLibrary = async (name: string, id: string) => {
  try {
    await removeEmbyLibrary(name, id, activeServerId.value)
    message.success('移除指令已发送')
    loadLibraries()
  } catch (e) {
    console.error(e)
  }
}

const handleDirectBackup = async (lib: any) => {
  try {
    await createEmbyBackup('libraries', lib.Id, lib.Name, activeServerId.value)
    message.success(`媒体库 ${lib.Name} 备份成功`)
  } catch (e) {
    console.error(e)
  }
}

const openEdit = (lib: any) => {
  editingLib.value = lib
  showEditModal.value = true
}

onMounted(async () => {
  if (!servers.value.length) {
    await fetchServers()
  }
  loadLibraries()
})
</script>

<style scoped>
.emby-libraries-container { padding: 10px; }
.page-header { margin-bottom: 20px; }
.main-card { margin-top: 12px; }
</style>