<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { embyTasksApi } from '@/api/embyTasks'
import { useNotification } from '@/composables'

const { success, error: showError } = useNotification()

const tasks = ref<any[]>([])
const loading = ref(true)
let timer: ReturnType<typeof setInterval> | null = null

// 分类分组
const groupedTasks = computed(() => {
  const visible = tasks.value.filter(t => !t.IsHidden)
  const groups: Record<string, any[]> = {}
  visible.forEach(task => {
    const cat = task.Category || 'Other'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(task)
  })
  return groups
})

// 分类颜色
function getCategoryColor(category: string) {
  const colors: Record<string, string> = {
    'Library': 'primary',
    'System': 'warning',
    'Media': 'success',
    'Maintenance': 'error',
    'Danmu': 'purple',
    'Bangumi': 'pink',
  }
  return colors[category] || 'grey'
}

// 分类图标
function getCategoryIcon(category: string) {
  const icons: Record<string, string> = {
    'Library': 'mdi-database-outline',
    'System': 'mdi-cog-outline',
    'Media': 'mdi-play-circle-outline',
    'Maintenance': 'mdi-wrench-outline',
    'Danmu': 'mdi-comment-text-outline',
    'Bangumi': 'mdi-star-outline',
  }
  return icons[category] || 'mdi-help-circle-outline'
}

// 上次运行时间格式化
function formatTaskDate(dateStr: string) {
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
  } catch {
    return '未知'
  }
}

async function fetchTasks(showLoading = false) {
  if (showLoading) loading.value = true
  try {
    const res = await embyTasksApi.list()
    if (Array.isArray(res)) {
      tasks.value = res
    }
  } catch {
    if (showLoading) showError('加载任务列表失败')
  } finally {
    if (showLoading) loading.value = false
  }
}

async function runTask(id: string) {
  try {
    await embyTasksApi.run(id)
    success('任务已启动')
    fetchTasks()
  } catch { showError('启动任务失败') }
}

async function stopTask(id: string) {
  try {
    await embyTasksApi.stop(id)
    success('已发送停止指令')
    fetchTasks()
  } catch { showError('停止任务失败') }
}

onMounted(() => {
  fetchTasks(true)
  // 每5秒自动刷新（静默）
  timer = setInterval(() => fetchTasks(false), 5000)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-clock-outline</v-icon>
      Emby 任务计划
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">查看并管理 Emby 服务器的计划任务与维护操作。</p>

    <!-- 工具栏 -->
    <div class="d-flex align-center mb-4">
      <v-spacer />
      <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" @click="fetchTasks(true)" :loading="loading">刷新</v-btn>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="text-center py-8"><v-progress-circular indeterminate color="primary" /></div>

    <!-- 空状态 -->
    <div v-else-if="!tasks.filter(t => !t.IsHidden).length" class="text-center py-8 text-medium-emphasis">
      <v-icon size="48" color="grey" class="mb-2">mdi-clipboard-text-off-outline</v-icon>
      <div>未发现计划任务</div>
    </div>

    <!-- 分类分组任务卡片 -->
    <div v-else>
      <div v-for="(group, category) in groupedTasks" :key="category" class="mb-6">
        <div class="d-flex align-center mb-3">
          <v-icon :color="getCategoryColor(category)" class="mr-2">{{ getCategoryIcon(category) }}</v-icon>
          <span class="text-subtitle-2 font-weight-bold text-uppercase" style="letter-spacing: 1px">{{ category }}</span>
          <v-chip size="x-small" variant="tonal" class="ml-2">{{ group.length }}</v-chip>
        </div>

        <v-row>
          <v-col v-for="task in group" :key="task.Id" cols="12" sm="6" md="4">
            <v-card
              variant="outlined"
              rounded="lg"
              class="pa-4 task-card"
              :class="{ 'running-card': task.State === 'Running' }"
            >
              <!-- 卡片头部 -->
              <div class="d-flex align-center mb-2">
                <v-icon :color="getCategoryColor(category)" class="mr-2" size="20">{{ getCategoryIcon(category) }}</v-icon>
                <span class="text-subtitle-2 font-weight-bold flex-grow-1">{{ task.Name }}</span>
                <!-- 运行/停止按钮 -->
                <v-btn
                  v-if="task.State !== 'Running'"
                  icon
                  variant="tonal"
                  size="x-small"
                  color="primary"
                  @click="runTask(task.Id)"
                >
                  <v-icon>mdi-play</v-icon>
                </v-btn>
                <v-btn
                  v-else
                  icon
                  variant="tonal"
                  size="x-small"
                  color="error"
                  @click="stopTask(task.Id)"
                >
                  <v-icon>mdi-stop</v-icon>
                </v-btn>
              </div>

              <!-- 描述 -->
              <div class="text-caption text-medium-emphasis mb-3" style="min-height: 32px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                {{ task.Description || '暂无任务描述' }}
              </div>

              <!-- 状态区域 -->
              <div style="min-height: 32px">
                <template v-if="task.State === 'Running'">
                  <div class="d-flex justify-space-between align-center mb-1">
                    <span class="text-caption text-success font-weight-bold">正在运行</span>
                    <span class="text-caption text-success">{{ task.CurrentProgressPercentage?.toFixed(1) }}%</span>
                  </div>
                  <v-progress-linear
                    :model-value="task.CurrentProgressPercentage || 0"
                    color="success"
                    height="4"
                    rounded
                    stream
                  />
                </template>
                <template v-else>
                  <div class="d-flex justify-space-between align-center">
                    <span class="text-caption text-medium-emphasis">上次运行时间</span>
                    <span class="text-caption">{{ formatTaskDate(task.LastExecutionResult?.EndTimeUtc) }}</span>
                  </div>
                </template>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </div>
    </div>
  </v-container>
</template>

<style scoped>
.task-card {
  transition: all 0.2s ease;
}
.task-card:hover {
  transform: translateY(-2px);
}
.running-card {
  border-color: rgb(var(--v-theme-success)) !important;
  background: rgba(var(--v-theme-success), 0.04);
}
</style>
