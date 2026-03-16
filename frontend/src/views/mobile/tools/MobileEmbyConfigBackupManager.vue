<template>
  <div class="mobile-backup-manager">
    <n-button 
      :size="buttonSizes.MEDIUM" 
      strong
      secondary 
      :type="buttonTypes.INFO"
      block
      @click="showModal = true"
    >
      {{ buttonText.CONFIG_BACKUP_MANAGE }}
    </n-button>

    <n-modal v-model:show="showModal" preset="card" :title="modalTitle.CONFIG_BACKUP_HISTORY" style="width: 95vw; max-width: 500px" :bordered="false">
      <template #header-extra>
        <n-space vertical :size="8">
          <n-popconfirm @positive-click="handleRestoreAll" :positive-text="confirmText.CONFIRM_RESTORE" :negative-text="confirmText.CANCEL">
            <template #trigger>
              <n-button 
                :size="buttonSizes.MEDIUM" 
                :type="buttonTypes.WARNING" 
                strong
                secondary 
                :disabled="backups.length === 0" 
                :loading="restoringAll"
                block
              >
                {{ buttonText.RESTORE_LATEST_BACKUP }}
              </n-button>
            </template>
            确定要将所有配置还原吗？
          </n-popconfirm>
          <n-popconfirm @positive-click="handleClearAll" :positive-text="confirmText.CONFIRM_CLEAR" :negative-text="confirmText.CANCEL">
            <template #trigger>
              <n-button 
                :size="buttonSizes.MEDIUM" 
                :type="buttonTypes.ERROR" 
                strong
                secondary
                :disabled="backups.length === 0"
                block
              >
                {{ buttonText.CLEAR_ALL_BACKUP }}
              </n-button>
            </template>
            确定要删除所有备份文件吗？
          </n-popconfirm>
        </n-space>
      </template>
      
      <n-space vertical size="large">
        <n-alert :type="tagTypes.INFO" size="small">
          备份将保存当前选定对象的完整原始 JSON 配置。还原操作将直接覆盖服务器上的现有设置，请谨慎操作。
        </n-alert>
        
        <div v-if="backups.length === 0" class="empty-state">
          <n-empty :description="emptyText.NO_BACKUP" />
        </div>
        <div v-else class="backup-list">
          <div v-for="backup in backups" :key="backup.filename" class="backup-item">
            <div class="backup-info">
              <div class="backup-name">{{ backup.filename.split('_20')[0] }}</div>
              <div class="backup-time">{{ new Date(backup.mtime * 1000).toLocaleString() }}</div>
            </div>
            <div class="backup-actions">
              <n-popconfirm @positive-click="handleRestore(backup.filename)" :positive-text="confirmText.CONFIRM_RESTORE" :negative-text="confirmText.CANCEL">
                <template #trigger>
                  <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.WARNING">
                    {{ buttonText.RESTORE }}
                  </n-button>
                </template>
                确定要将此配置还原到服务器吗？
              </n-popconfirm>
              <n-popconfirm @positive-click="handleDelete(backup.filename)" :positive-text="confirmText.DELETE" :negative-text="confirmText.CANCEL">
                <template #trigger>
                  <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
                    {{ buttonText.DELETE }}
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
  CleaningServicesOutlined as ClearIcon 
} from '@vicons/material'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  TagTypes,
  MessageText,
} from '../constants'

const props = defineProps<{
  category: 'users' | 'libraries'
  serverId: string
}>()

const emit = defineEmits(['restored'])
const message = useMessage()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const tagTypes = TagTypes
const messageText = MessageText

// 额外的文本常量
const modalTitle = {
  CONFIG_BACKUP_HISTORY: '配置备份历史',
}

const emptyText = {
  NO_BACKUP: '暂无备份',
}

const confirmText = {
  CONFIRM_RESTORE: '确定还原',
  CONFIRM_CLEAR: '确定清空',
  DELETE: '删除',
  CANCEL: '取消',
}

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
    message.success(messageText.RESTORE_SUCCESS)
    emit('restored')
    showModal.value = false
  } catch (e) {
    console.error(e)
  }
}

const handleDelete = async (filename: string) => {
  try {
    await deleteEmbyBackup(props.category, filename)
    message.success(messageText.DELETE_SUCCESS)
    loadBackups()
  } catch (e) {
    console.error(e)
  }
}

const handleClearAll = async () => {
  try {
    await clearEmbyBackups(props.category)
    message.success(messageText.CLEAR_ALL_SUCCESS)
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
</style>
