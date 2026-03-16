<template>
  <n-card :size="buttonSizes.SMALL" :bordered="false" :title="cardTitle.EXECUTION_HISTORY">
    <n-space vertical>
      <n-space justify="space-between">
        <n-text :type="tagTypes.PRIMARY" style="font-weight: 600">{{ label.HISTORY_RECORD }}</n-text>
        <n-button :size="buttonSizes.MEDIUM" secondary @click="fetchHistory">
          {{ buttonText.REFRESH }}
        </n-button>
      </n-space>

      <div v-if="loading" class="loading-state">
        <n-spin :size="buttonSizes.MEDIUM" />
      </div>

      <div v-else-if="history.length === 0" class="empty-state">
        <n-empty :description="emptyText.NO_BACKUP_HISTORY" />
      </div>

      <div v-else class="history-list">
        <div v-for="item in history" :key="item.id" class="history-item">
          <div class="history-header">
            <div class="task-name">{{ item.task_name }}</div>
            <n-tag
              :type="getStatusType(item.status)"
              :size="buttonSizes.SMALL"
              round
              :bordered="false"
            >
              {{ getStatusLabel(item.status) }}
            </n-tag>
          </div>

          <div class="history-info">
            <div class="info-row">
              <n-icon size="14"><TimeIcon /></n-icon>
              <span>{{ formatTime(item.start_time) }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><SizeIcon /></n-icon>
              <span>{{ formatSize(item.size) }}</span>
            </div>
          </div>

          <div v-if="item.message" class="history-message">
            <n-text depth="3" style="font-size: 12px">
              {{ item.message }}
            </n-text>
          </div>

          <div v-if="item.status === 'success'" class="history-actions">
            <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.INFO" @click="handleDownload(item)">
              {{ buttonText.DOWNLOAD }}
            </n-button>
            <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.WARNING" @click="handleRestore(item)">
              {{ buttonText.RESTORE }}
            </n-button>
          </div>
        </div>
      </div>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { NCard, NSpace, NButton, NTag, NIcon, NEmpty, NSpin, NText, useMessage } from 'naive-ui'
import axios from 'axios'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  TagTypes,
  MessageText,
  CardTitle,
  Label,
  EmptyText,
} from '../constants'

const message = useMessage()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const tagTypes = TagTypes
const messageText = MessageText
const cardTitle = CardTitle
const label = Label
const emptyText = EmptyText

const history = ref([])
const loading = ref(false)
let timer: any = null

const getStatusType = (status: string) => {
  const types: Record<string, any> = {
    'success': tagTypes.SUCCESS,
    'running': tagTypes.INFO,
    'failed': tagTypes.ERROR
  }
  return types[status] || tagTypes.DEFAULT
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    'success': '成功',
    'running': '进行中',
    'failed': '失败'
  }
  return labels[status] || status
}

const formatTime = (time: string) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

const formatSize = (bytes: number) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

const fetchHistory = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const res = await axios.get('/api/backup/history')
    history.value = res.data

    const hasRunning = res.data.some((item: any) => item.status === 'running')
    if (hasRunning) {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (e) {
    message.error(messageText.LOAD_HISTORY_FAILED)
  } finally {
    loading.value = false
  }
}

const startPolling = () => {
  if (timer) return
  timer = setInterval(() => {
    fetchHistory(true)
  }, 5000)
}

const stopPolling = () => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const handleDownload = (item: any) => {
  const downloadUrl = `/api/backup/history/${item.id}/download`
  const link = document.createElement('a')
  link.href = downloadUrl
  link.download = `${item.task_name}_${item.id}.zip`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  message.success(messageText.START_DOWNLOAD)
}

const handleRestore = (item: any) => {
  message.info(messageText.RESTORE_DEVELOPING)
}

defineExpose({ fetchHistory })

onMounted(() => {
  fetchHistory()
})

onUnmounted(() => {
  stopPolling()
})
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

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
  transition: all 0.2s ease;
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--n-primary-color);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.task-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
}

.history-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color-3);
}

.history-message {
  padding: 8px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 4px;
  margin-bottom: 8px;
}

.history-actions {
  display: flex;
  gap: 8px;
}

.history-actions .n-button {
  flex: 1;
}
</style>
