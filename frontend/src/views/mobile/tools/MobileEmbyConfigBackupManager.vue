<template>
  <div class="mobile-backup-manager">
    <n-button 
      size="small" 
      strong
      secondary 
      type="info"
      block
      @click="showModal = true"
    >
      <template #icon><n-icon><HistoryIcon /></n-icon></template>
      配置备份管理
    </n-button>

    <n-modal v-model:show="showModal" preset="card" title="配置备份历史" style="width: 95vw; max-width: 500px" :bordered="false">
      <template #header-extra>
        <n-space vertical :size="8">
          <n-popconfirm @positive-click="handleRestoreAll" positive-text="确定还原" negative-text="取消">
            <template #trigger>
              <n-button 
                size="tiny" 
                type="warning" 
                strong
                secondary 
                :disabled="backups.length === 0" 
                :loading="restoringAll"
                block
              >
                <template #icon><n-icon><RestoreIcon /></n-icon></template>
                一键还原最新备份
              </n-button>
            </template>
            确定要将所有配置还原吗？
          </n-popconfirm>
          <n-popconfirm @positive-click="handleClearAll" positive-text="确定清空" negative-text="取消">
            <template #trigger>
              <n-button 
                size="tiny" 
                type="error" 
                strong
                secondary
                :disabled="backups.length === 0"
                block
              >
                <template #icon><n-icon><ClearIcon /></n-icon></template>
                清空所有备份
              </n-button>
            </template>
            确定要删除所有备份文件吗？
          </n-popconfirm>
        </n-space>
      </template>
      
      <n-space vertical size="large">
        <n-alert type="info" size="small">
          备份将保存当前选定对象的完整原始 JSON 配置。还原操作将直接覆盖服务器上的现有设置，请谨慎操作。
        </n-alert>
        
        <div v-if="backups.length === 0" class="empty-state">
          <n-empty description="暂无备份" />
        </div>
        <div v-else class="backup-list">
          <div v-for="backup in backups" :key="backup.filename" class="backup-item">
            <div class="backup-info">
              <div class="backup-name">{{ backup.filename.split('_20')[0] }}</div>
              <div class="backup-time">{{ new Date(backup.mtime * 1000).toLocaleString() }}</div>
            </div>
            <div class="backup-actions">
              <n-popconfirm @positive-click="handleRestore(backup.filename)" positive-text="确认还原" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="warning">
                    <template #icon><n-icon><RestoreIcon /></n-icon></template>
                    还原
                  </n-button>
                </template>
                确定要将此配置还原到服务器吗？
              </n-popconfirm>
              <n-popconfirm @positive-click="handleDelete(backup.filename)" positive-text="删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    <template #icon><n-icon><DeleteIcon /></n-icon></template>
                    删除
                  </n-button>
                </template>
                确定删除此备份文件吗？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NButton, NSpace, NPopconfirm, useMessage, NIcon, NModal, NAlert, NEmpty } from 'naive-ui'
import { listEmbyBackups, restoreEmbyBackup, deleteEmbyBackup, clearEmbyBackups, restoreAllEmbyBackups } from '@/api/embyBackup'
import { 
  RestoreOutlined as RestoreIcon,
  DeleteOutlined as DeleteIcon,
  CleaningServicesOutlined as ClearIcon,
  HistoryOutlined as HistoryIcon 
} from '@vicons/material'

const props = defineProps<{
  category: 'users' | 'libraries'
  serverId: string
}>()

const emit = defineEmits(['restored'])
const message = useMessage()
const showModal = ref(false)
const restoringAll = ref(false)
const backups = ref<any[]>([])

const loadBackups = async () => {
  try {
    const res = await listEmbyBackups(props.category)
    backups.value = res as any
  } catch (e) {
    console.error(e)
  }
}

const handleRestore = async (filename: string) => {
  try {
    await restoreEmbyBackup(props.category, filename, props.serverId)
    message.success('配置还原成功')
    emit('restored')
    showModal.value = false
  } catch (e) {
    console.error(e)
  }
}

const handleDelete = async (filename: string) => {
  try {
    await deleteEmbyBackup(props.category, filename)
    message.success('备份已删除')
    loadBackups()
  } catch (e) {
    console.error(e)
  }
}

const handleClearAll = async () => {
  try {
    await clearEmbyBackups(props.category)
    message.success('所有备份已清空')
    loadBackups()
  } catch (e) {
    console.error(e)
  }
}

const handleRestoreAll = async () => {
  restoringAll.value = true
  try {
    const res: any = await restoreAllEmbyBackups(props.category, props.serverId)
    message.success(`成功还原 ${res.count} 项最新配置`)
    emit('restored')
    showModal.value = false
  } catch (e) {
    console.error(e)
  } finally {
    restoringAll.value = false
  }
}

watch(showModal, (val) => {
  if (val) loadBackups()
})
</script>

<style scoped>
.mobile-backup-manager {
  width: 100%;
}

.empty-state {
  padding: 24px 0;
}

.backup-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.backup-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.backup-info {
  margin-bottom: 8px;
}

.backup-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.backup-time {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.backup-actions {
  display: flex;
  gap: 8px;
}
</style>
