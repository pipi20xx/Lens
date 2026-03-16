<template>
  <n-card size="small" :bordered="false" title="备份任务">
    <n-space vertical>
      <n-space justify="space-between">
        <n-text type="primary" style="font-weight: 600">任务列表</n-text>
        <n-space>
          <n-button size="small" secondary @click="fetchTasks">
            <template #icon><n-icon><RefreshIcon /></n-icon></template>
            刷新
          </n-button>
          <n-button size="small" type="primary" @click="$emit('add')">
            <template #icon><n-icon><AddIcon /></n-icon></template>
            新增
          </n-button>
        </n-space>
      </n-space>
      
      <div v-if="loading" class="loading-state">
        <n-spin size="medium" />
      </div>
      
      <div v-else-if="tasks.length === 0" class="empty-state">
        <n-empty description="暂无备份任务" />
      </div>
      
      <div v-else class="task-list">
        <div v-for="task in tasks" :key="task.id" class="task-item">
          <div class="task-header">
            <div class="task-name">
              {{ task.name }}
              <n-tag v-if="task.host_id && task.host_id !== 'local'" size="tiny" type="warning" round>
                远程
              </n-tag>
            </div>
            <n-switch
              :value="task.enabled"
              @update:value="(val) => handleToggleEnable(task, val)"
              size="small"
              class="mobile-switch"
            />
          </div>
          
          <div class="task-info">
            <div class="info-row">
              <n-icon size="14"><ModeIcon /></n-icon>
              <span>{{ getModeLabel(task.mode) }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><StorageIcon /></n-icon>
              <span>{{ getStorageLabel(task.storage_type) }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><ScheduleIcon /></n-icon>
              <span>{{ formatSchedule(task) }}</span>
            </div>
          </div>
          
          <div class="task-actions">
            <n-button size="small" secondary type="primary" @click="$emit('run', task)">
              <template #icon><n-icon><PlayIcon /></n-icon></template>
              执行
            </n-button>
            <n-button size="small" secondary @click="$emit('view-history', task)">
              <template #icon><n-icon><HistoryIcon /></n-icon></template>
              历史
            </n-button>
            <n-button size="small" secondary @click="$emit('edit', task)">
              <template #icon><n-icon><EditIcon /></n-icon></template>
              编辑
            </n-button>
            <n-popconfirm @positive-click="() => handleDelete(task)">
              <template #trigger>
                <n-button size="small" secondary type="error">
                  <template #icon><n-icon><DeleteIcon /></n-icon></template>
                </n-button>
              </template>
              确认删除任务？
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { ref, h } from 'vue'
import { NCard, NSpace, NButton, NTag, NIcon, NText, NEmpty, NSwitch, NSpin, NPopconfirm, useMessage, useDialog } from 'naive-ui'
import {
  AddOutlined as AddIcon,
  RefreshOutlined as RefreshIcon,
  PlayArrowOutlined as PlayIcon,
  HistoryOutlined as HistoryIcon,
  EditOutlined as EditIcon,
  DeleteOutlined as DeleteIcon,
  BackupOutlined as ModeIcon,
  StorageOutlined as StorageIcon,
  ScheduleOutlined as ScheduleIcon
} from '@vicons/material'
import axios from 'axios'

const emit = defineEmits(['add', 'edit', 'run', 'view-history'])
const message = useMessage()
const dialog = useDialog()

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
    message.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

const handleToggleEnable = async (task: any, enabled: boolean) => {
  try {
    await axios.post('/api/backup/tasks', { ...task, enabled })
    message.success(enabled ? '任务已启用' : '任务已禁用')
    await fetchTasks()
  } catch (e) {
    message.error('操作失败')
  }
}

const handleDelete = (task: any) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除任务 "${task.name}" 吗？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/backup/tasks/${task.id}`)
        message.success('已删除')
        await fetchTasks()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

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
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
  transition: all 0.2s ease;
}

.task-item:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--n-primary-color);
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
