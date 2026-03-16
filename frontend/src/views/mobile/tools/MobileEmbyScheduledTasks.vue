<template>
  <div class="mobile-emby-tasks">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">Emby 任务计划中心</h1>
      <p class="page-desc">查看并管理 Emby 服务器的计划任务与维护操作</p>
    </div>

    <!-- 刷新按钮 -->
    <n-card class="action-card" :bordered="false">
      <n-button block :type="buttonTypes.PRIMARY" secondary :loading="loading" @click="fetchTasks(true)">
        {{ buttonText.REFRESH_TASK_LIST }}
      </n-button>
    </n-card>

    <!-- 任务列表 -->
    <div v-if="tasks.length === 0" class="empty-state">
      <n-empty :description="emptyText.NO_TASK" />
    </div>
    <div v-else class="task-groups">
      <div v-for="(group, category) in groupedTasks" :key="category" class="task-group">
        <div class="group-title">{{ category }}</div>
        <div class="task-list">
          <n-card v-for="task in group" :key="task.Id" size="small" :bordered="false" class="task-card" :class="{ 'running': task.State === 'Running' }">
            <div class="task-header">
              <div class="task-icon" :style="{ color: getCategoryColor(task.Category) }">
                <n-icon size="22"><component :is="getTaskIcon(task.Category)" /></n-icon>
              </div>
              <div class="task-title">{{ task.Name }}</div>
              <n-button
                v-if="task.State !== 'Running'"
                quaternary
                circle
                :size="buttonSizes.MEDIUM"
                :type="buttonTypes.PRIMARY"
                @click="handleRun(task.Id)"
              >
                </n-button>
              <n-button
                v-else
                quaternary
                circle
                :size="buttonSizes.MEDIUM"
                :type="buttonTypes.ERROR"
                @click="handleStop(task.Id)"
              >
                </n-button>
            </div>
            <div class="task-desc">{{ task.Description || '暂无任务描述' }}</div>
            <div class="task-status">
              <template v-if="task.State === 'Running'">
                <n-space vertical :size="4">
                  <n-space justify="space-between">
                    <n-text :type="tagTypes.SUCCESS" strong style="font-size: 12px">{{ statusText.RUNNING }}</n-text>
                    <n-text :type="tagTypes.SUCCESS" style="font-size: 12px">{{ task.CurrentProgressPercentage?.toFixed(1) }}%</n-text>
                  </n-space>
                  <n-progress
                    type="line"
                    :percentage="task.CurrentProgressPercentage"
                    :show-indicator="false"
                    status="success"
                    processing
                    size="small"
                  />
                </n-space>
              </template>
              <template v-else>
                <n-space justify="space-between">
                  <n-tag :type="task.State === 'Idle' ? tagTypes.SUCCESS : tagTypes.DEFAULT" size="tiny" round>
                    {{ task.State === 'Idle' ? statusText.IDLE : task.State }}
                  </n-tag>
                  <n-text depth="3" style="font-size: 11px">{{ formatTaskDate(task.LastExecutionResult?.EndTimeUtc) }}</n-text>
                </n-space>
              </template>
            </div>
          </n-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, markRaw } from 'vue'
import { 
  NButton, NCard, NIcon, NProgress, NTag, NText, 
  NSpace, NEmpty 
} from 'naive-ui'
import { 
  RefreshOutlined, PlayArrowFilled, StopFilled,
  StorageOutlined, SettingsSuggestOutlined, PhotoFilterOutlined, 
  BuildCircleOutlined, HelpOutlineOutlined
} from '@vicons/material'
import { embyTasksApi } from '@/api/embyTasks'
import { useMessage } from 'naive-ui'
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
const emptyText = {
  NO_TASK: '暂无任务',
}

const statusText = {
  RUNNING: '正在运行',
  IDLE: '空闲',
}

const tasks = ref<any[]>([])
const loading = ref(false)
let timer: any = null

const groupedTasks = computed(() => {
  if (!tasks.value) return {}
  const visible = tasks.value.filter(t => !t.IsHidden)
  const groups: Record<string, any[]> = {}
  
  visible.forEach(task => {
    const cat = task.Category || 'Other'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(task)
  })
  
  return groups
})

const fetchTasks = async (showLoading = false) => {
  if (showLoading) loading.value = true
  try {
    const res = await embyTasksApi.list()
    if (Array.isArray(res)) {
      tasks.value = res
    }
  } catch (err) {
    console.error('Failed to fetch emby tasks:', err)
    message.error(messageText.LOAD_TASK_FAILED)
  } finally {
    if (showLoading) loading.value = false
  }
}

const handleRun = async (id: string) => {
  try {
    await embyTasksApi.run(id)
    message.success(messageText.TASK_START_SUCCESS)
    fetchTasks()
  } catch (err) {
    message.error(messageText.TASK_START_FAILED)
  }
}

const handleStop = async (id: string) => {
  try {
    await embyTasksApi.stop(id)
    message.warning(messageText.TASK_STOP_WARNING)
    fetchTasks()
  } catch (err) {
    message.error(messageText.TASK_STOP_FAILED)
  }
}

const getCategoryColor = (category: string) => {
  const colors: any = {
    'Library': 'var(--primary-color)',
    'System': '#f0a020',
    'Media': '#18a058',
    'Maintenance': '#d03050',
    'Danmu': '#722ed1',
    'Bangumi': '#ff4d4f'
  }
  return colors[category] || '#888'
}

const getTaskIcon = (category: string) => {
  const icons: any = {
    'Library': markRaw(StorageOutlined),
    'System': markRaw(SettingsSuggestOutlined),
    'Media': markRaw(PhotoFilterOutlined),
    'Maintenance': markRaw(BuildCircleOutlined),
    'Danmu': markRaw(PhotoFilterOutlined),
    'Bangumi': markRaw(BuildCircleOutlined)
  }
  return icons[category] || markRaw(HelpOutlineOutlined)
}

const formatTaskDate = (dateStr: string) => {
  if (!dateStr) return '从未运行'
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    
    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins} 分钟前`
    if (diffHours < 24) return `${diffHours} 小时前`
    return date.toLocaleString()
  } catch (e) {
    return dateStr
  }
}

onMounted(() => {
  fetchTasks(true)
  timer = setInterval(() => fetchTasks(), 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.mobile-emby-tasks {
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

.action-card {
  margin-bottom: 16px;
}

.empty-state {
  padding: 48px 0;
}

.task-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.group-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-color);
  opacity: 0.6;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 8px;
  padding-left: 4px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-card {
  background: var(--app-bg-color);
}

.task-card.running {
  border: 1px solid var(--primary-color);
}

.task-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.task-icon {
  flex-shrink: 0;
}

.task-title {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.task-desc {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 8px;
  line-height: 1.4;
}

.task-status {
  margin-top: 8px;
}
</style>
