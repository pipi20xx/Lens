<template>
  <n-modal v-model:show="show" preset="card" :title="`构建历史 - ${projectName}`" style="width: 90vw; max-width: 600px">
    <div v-if="tasks.length === 0" class="empty-state">
      <n-empty description="暂无构建记录" size="small" />
    </div>
    
    <div v-else class="history-list">
      <div v-for="task in tasks" :key="task.id" class="history-item">
        <div class="history-header">
          <div class="history-tag">{{ task.tag }}</div>
          <n-tag :type="getStatusType(task.status)" size="small" ghost>
            {{ getStatusLabel(task.status) }}
          </n-tag>
        </div>
        
        <div class="history-time">
          <n-icon size="14"><TimeIcon /></n-icon>
          <span>{{ formatTime(task.created_at) }}</span>
        </div>
        
        <div class="history-actions">
          <n-button size="tiny" secondary @click="viewLog(task.id)">
            日志
          </n-button>
          <n-button size="tiny" secondary type="error" @click="deleteLog(task.id)">
            删除
          </n-button>
        </div>
      </div>
    </div>
    
    <n-modal v-model:show="showLog" preset="card" title="详细日志" style="width: 90vw; max-width: 600px; height: 80vh;">
      <div class="log-container">
        <pre>{{ currentLog }}</pre>
      </div>
      <template #footer>
        <n-space justify="end">
          <n-button type="primary" @click="showLog = false">
            关闭
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NModal, NTag, NButton, NSpace, NIcon, NEmpty, useMessage, useDialog } from 'naive-ui'
import axios from 'axios'

const props = defineProps<{
  show: boolean
  projectId: string
  projectName: string
}>()

const emit = defineEmits(['update:show'])

const show = ref(false)
const tasks = ref([])
const loading = ref(false)
const showLog = ref(false)
const currentLog = ref('')

const message = useMessage()
const dialog = useDialog()

watch(() => props.show, (val) => {
  show.value = val
  if (val) fetchHistory()
})

watch(show, (val) => {
  emit('update:show', val)
})

const getStatusType = (status: string) => {
  const typeMap: Record<string, any> = {
    'SUCCESS': 'success',
    'FAILED': 'error',
    'PENDING': 'info'
  }
  return typeMap[status] || 'default'
}

const getStatusLabel = (status: string) => {
  const labelMap: Record<string, string> = {
    'SUCCESS': '成功',
    'FAILED': '失败',
    'PENDING': '处理中'
  }
  return labelMap[status] || status
}

const formatTime = (timeStr: string) => {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

const fetchHistory = async () => {
  if (!props.projectId) return
  loading.value = true
  try {
    const res = await axios.get(`/api/image-builder/projects/${props.projectId}/tasks`)
    tasks.value = res.data
  } catch (e) {
    message.error('获取历史失败')
  } finally {
    loading.value = false
  }
}

const viewLog = async (taskId: string) => {
  try {
    const res = await axios.get(`/api/image-builder/tasks/${taskId}/log`)
    currentLog.value = res.data.content
    showLog.value = true
  } catch (e) {
    message.error('读取日志失败')
  }
}

const deleteLog = (taskId: string) => {
  dialog.warning({
    title: '确认删除',
    content: '确定要删除这条构建记录吗？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/image-builder/tasks/${taskId}`)
        message.success('已删除')
        fetchHistory()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}
</script>

<style scoped>
.empty-state {
  padding: 40px 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.history-item {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.history-tag {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
}

.history-time {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.7;
  margin-bottom: 8px;
}

.history-actions {
  display: flex;
  gap: 8px;
}

.log-container {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  height: calc(80vh - 180px);
  overflow-y: auto;
  font-family: monospace;
  white-space: pre-wrap;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
</style>
