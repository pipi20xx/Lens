<template>
  <div class="emby-tasks-container">
    <n-space vertical size="large">
      <!-- 页面标题 -->
      <div class="page-header">
        <n-space align="center" justify="space-between">
          <div>
            <n-h2 prefix="bar" align-text>
              <n-text type="primary">Emby 任务计划中心</n-text>
            </n-h2>
            <n-text depth="3">查看并管理 Emby 服务器的计划任务与维护操作。</n-text>
          </div>
          <n-button 
            quaternary 
            circle 
            type="primary" 
            :loading="loading" 
            @click="fetchTasks(true)"
          >
            <template #icon>
              <n-icon><ArrowPathIcon /></n-icon>
            </template>
          </n-button>
        </n-space>
      </div>

      <!-- 任务列表数据展示 -->
      <div v-if="tasks.length > 0" class="task-groups-wrapper">
        <n-space vertical size="large">
          <div v-for="(group, category) in groupedTasks" :key="category" class="category-section">
            <n-divider title-placement="left">
              <n-text depth="2" strong style="text-transform: uppercase; letter-spacing: 1px;">
                {{ category }}
              </n-text>
            </n-divider>

            <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
              <n-gi v-for="task in group" :key="task.Id" span="24 m:12 l:8">
                <n-card 
                  size="small" 
                  hoverable 
                  :class="{ 'running-card': task.State === 'Running' }"
                  class="task-card"
                >
                  <template #header>
                    <n-space align="center" :size="8">
                      <n-icon 
                        size="22" 
                        :style="{ color: getCategoryColor(task.Category) }"
                      >
                        <component :is="getTaskIcon(task.Category)" />
                      </n-icon>
                      <n-text strong style="font-size: 14px">{{ task.Name }}</n-text>
                    </n-space>
                  </template>

                  <template #header-extra>
                    <n-button
                      v-if="task.State !== 'Running'"
                      quaternary
                      circle
                      size="small"
                      type="primary"
                      @click="handleRun(task.Id)"
                    >
                      <template #icon><n-icon><PlayIcon /></n-icon></template>
                    </n-button>
                    <n-button
                      v-else
                      quaternary
                      circle
                      size="small"
                      type="error"
                      @click="handleStop(task.Id)"
                    >
                      <template #icon><n-icon><StopCircleIcon /></n-icon></template>
                    </n-button>
                  </template>

                  <n-space vertical size="small">
                    <n-text depth="3" class="task-desc">
                      {{ task.Description || '暂无任务描述' }}
                    </n-text>

                    <div class="status-area">
                      <template v-if="task.State === 'Running'">
                        <n-space vertical :size="4">
                          <n-space justify="space-between">
                            <n-text type="success" strong style="font-size: 12px">正在运行</n-text>
                            <n-text type="success" style="font-size: 12px">{{ task.CurrentProgressPercentage?.toFixed(1) }}%</n-text>
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
                        <n-space justify="space-between" align="center">
                          <n-text depth="3" style="font-size: 12px">上次运行时间</n-text>
                          <n-text depth="2" style="font-size: 12px">
                            {{ formatTaskDate(task.LastExecutionResult?.EndTimeUtc) }}
                          </n-text>
                        </n-space>
                      </template>
                    </div>
                  </n-space>
                </n-card>
              </n-gi>
            </n-grid>
          </div>
        </n-space>
      </div>

      <!-- 空状态 -->
      <n-empty v-else-if="!loading" description="未发现计划任务" style="margin-top: 100px" />
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, markRaw } from 'vue'
import { 
  NSpace, NIcon, NButton, NProgress, useMessage, NH2, NText, 
  NDivider, NGrid, NGi, NCard, NEmpty 
} from 'naive-ui'
import {
  ArrowPathIcon,
  CircleStackIcon,
  Cog6ToothIcon,
  PlayIcon,
  QuestionMarkCircleIcon,
  StopCircleIcon,
  SwatchIcon,
  WrenchIcon
} from '@heroicons/vue/24/outline'
import { embyTasksApi } from '@/api/embyTasks'

const message = useMessage()
const tasks = ref<any[]>([])
const loading = ref(false)
let timer: any = null

// 分组逻辑
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
  } finally {
    if (showLoading) loading.value = false
  }
}

const handleRun = async (id: string) => {
  try {
    await embyTasksApi.run(id)
    message.success('任务已启动')
    fetchTasks()
  } catch (err) {
    message.error('启动失败')
  }
}

const handleStop = async (id: string) => {
  try {
    await embyTasksApi.stop(id)
    message.warning('已发送停止指令')
    fetchTasks()
  } catch (err) {
    message.error('停止失败')
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
    'Library': markRaw(CircleStackIcon),
    'System': markRaw(Cog6ToothIcon),
    'Media': markRaw(SwatchIcon),
    'Maintenance': markRaw(WrenchIcon),
    'Danmu': markRaw(SwatchIcon),
    'Bangumi': markRaw(WrenchIcon)
  }
  return icons[category] || markRaw(QuestionMarkCircleIcon)
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
    return '未知'
  }
}

onMounted(() => {
  fetchTasks(true)
  timer = setInterval(() => fetchTasks(false), 5000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.emby-tasks-container {
  padding: 10px;
}

.page-header {
  margin-bottom: 20px;
}

.task-card {
  height: 100%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
}

.task-card:hover {
  transform: translateY(-2px);
  border-color: var(--primary-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.running-card {
  border-color: var(--success-color);
  background-color: rgba(24, 160, 88, 0.05);
}

.task-desc {
  font-size: 12px;
  height: 36px;
  line-height: 18px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.status-area {
  margin-top: 8px;
  min-height: 32px;
}
</style>