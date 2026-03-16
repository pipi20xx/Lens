<template>
  <n-card :size="buttonSizes.SMALL" :bordered="false" title="备份任务">
    <n-space vertical>
      <n-space justify="space-between">
        <n-text :type="tagTypes.PRIMARY" style="font-weight: 600">任务列表</n-text>
        <n-space>
          <n-button :size="buttonSizes.MEDIUM" secondary @click="fetchTasks">
            {{ buttonText.REFRESH }}
          </n-button>
          <n-button :size="buttonSizes.MEDIUM" :type="buttonTypes.PRIMARY" @click="$emit('add')">
            {{ buttonText.ADD }}
          </n-button>
        </n-space>
      </n-space>
      
      <div v-if="loading" class="loading-state">
        <n-spin :size="buttonSizes.MEDIUM" />
      </div>
      
      <div v-else-if="tasks.length === 0" class="empty-state">
        <n-empty :description="messageText.EMPTY_DATA" />
      </div>
      
      <div v-else class="task-list">
        <div v-for="task in tasks" :key="task.id" class="task-item">
          <div class="task-header">
            <div class="task-name">
              {{ task.name }}
              <n-tag v-if="task.host_id && task.host_id !== 'local'" :size="buttonSizes.TINY" :type="tagTypes.WARNING" round>
                远程
              </n-tag>
            </div>
            <n-tag 
              :type="task.enabled ? tagTypes.SUCCESS : tagTypes.DEFAULT" 
              :size="buttonSizes.SMALL" 
              round
            >
              {{ task.enabled ? '自动计划中' : '仅手动' }}
            </n-tag>
          </div>
          
          <div class="task-info">
            <div class="info-row">
              <n-icon :size="14"><ModeIcon /></n-icon>
              <span>{{ getModeLabel(task.mode) }}</span>
            </div>
            <div class="info-row">
              <n-icon :size="14"><StorageIcon /></n-icon>
              <span>{{ getStorageLabel(task.storage_type) }}</span>
            </div>
            <div class="info-row">
              <n-icon :size="14"><ScheduleIcon /></n-icon>
              <span>{{ formatSchedule(task) }}</span>
            </div>
          </div>
          
          <div class="task-actions">
            <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.PRIMARY" @click="$emit('run', task)">
              {{ buttonText.RUN }}
            </n-button>
            <n-button :size="buttonSizes.MEDIUM" secondary @click="$emit('view-history', task)">
              {{ buttonText.HISTORY }}
            </n-button>
            <n-button :size="buttonSizes.MEDIUM" secondary @click="$emit('edit', task)">
              {{ buttonText.EDIT }}
            </n-button>
            <n-popconfirm @positive-click="() => handleDelete(task)" :positive-text="buttonText.CONFIRM_DELETE" :negative-text="buttonText.CANCEL">
              <template #trigger>
                <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
                  {{ buttonText.DELETE }}
                </n-button>
              </template>
              {{ messageText.DELETE_CONFIRM }}
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NSpace, NButton, NTag, NIcon, NText, NEmpty, NSpin, NPopconfirm, useMessage } from 'naive-ui'
import {
  BackupOutlined as ModeIcon,
  StorageOutlined as StorageIcon,
  ScheduleOutlined as ScheduleIcon
} from '@vicons/material'
import axios from 'axios'
import {
  ButtonTypes,
  ButtonSizes,
  TagTypes,
  ButtonText,
  MessageText,
} from '../constants'

const emit = defineEmits(['add', 'edit', 'run', 'view-history'])
const message = useMessage()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const tagTypes = TagTypes
const buttonText = ButtonText
const messageText = MessageText

const tasks = ref([])
const loading = ref(false)

const getModeLabel = (mode: string) => {
  const labels: Record<string, string> = {
    '7z': '7z 压缩',
    'tar': 'Tar.gz 打包',
    'sync': 'Sync 同步',
    'pgsql': 'PostgreSQL 备份'
  }
  return labels[mode] || mode
}

const getStorageLabel = (type: string) => {
  const labels: Record<string, string> = {
    'ssd': 'SSD',
    'hdd': 'HDD',
    'cloud': '云盘'
  }
  return labels[type] || 'SSD'
}

const formatSchedule = (task: any) => {
  if (!task.enabled) return '仅手动'
  
  if (task.schedule_type === 'interval') {
    const min = parseInt(task.schedule_value)
    if (min % 1440 === 0) return `每 ${min / 1440} 天`
    if (min % 60 === 0) return `每 ${min / 60} 小时`
    return `每 ${min} 分钟`
  }
  
  if (task.schedule_type === 'cron') {
    const cron = task.schedule_value || ''
    const dailyMatch = cron.match(/^(\d+)\s+(\d+)\s+\*\s+\*\s+\*$/)
    if (dailyMatch) {
      const m = dailyMatch[1].padStart(2, '0')
      const h = dailyMatch[2].padStart(2, '0')
      return `每天 ${h}:${m}`
    }
    return cron
  }
  return task.schedule_value
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/backup/tasks')
    tasks.value = res.data
  } catch (e) {
    message.error(messageText.LOAD_FAILED)
  } finally {
    loading.value = false
  }
}

const handleDelete = async (task: any) => {
  try {
    await axios.delete(`/api/backup/tasks/${task.id}`)
    message.success(messageText.DELETE_SUCCESS)
    await fetchTasks()
  } catch (e) {
    message.error(messageText.DELETE_FAILED)
  }
}

onMounted(() => {
  fetchTasks()
})

defineExpose({ fetchTasks })
</script>

<style scoped>
.loading-state {
  display: flex;
  justify-content: center;
  padding: 40px 0;
}

.empty-state {
  padding: 40px 0;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
  transition: all 0.2s ease;
}

.task-item:hover {
  border-color: #9f7aea;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color-3);
}

.task-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.task-actions .n-button {
  flex: 1;
  min-width: 60px;
}
</style>
