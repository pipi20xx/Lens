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
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <div class="d-flex align-center justify-space-between flex-wrap ga-3 pa-4">
        <div class="d-flex align-center ga-2">
          <v-icon color="primary">mdi-clipboard-list-outline</v-icon>
          <span class="text-subtitle-2 font-weight-bold">计划任务</span>
          <v-chip size="x-small" variant="tonal">{{ tasks.filter(t => !t.IsHidden).length }}</v-chip>
        </div>
        <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="fetchTasks(true)" :loading="loading">刷新</v-btn>
      </div>
    </v-card>

    <!-- 加载中 -->
    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <!-- 空状态 -->
    <div v-else-if="!tasks.filter(t => !t.IsHidden).length" class="text-center py-12 text-medium-emphasis">
      <v-icon size="64" color="grey" class="mb-4">mdi-clipboard-text-off-outline</v-icon>
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

        <div class="card-grid">
          <v-card
            v-for="task in group"
            :key="task.Id"
            class="status-card liquid-glass-card"
            :class="{ 'running-card': task.State === 'Running' }"
            rounded="lg"
          >
            <!-- 卡片头部：名称 + 运行/停止 -->
            <div class="card-header pa-4 pb-2">
              <div class="card-title">
                <v-icon start :color="getCategoryColor(category)" size="20">{{ getCategoryIcon(category) }}</v-icon>
                <span class="text-subtitle-2 font-weight-bold text-truncate">{{ task.Name }}</span>
                <v-chip v-if="task.State === 'Running'" size="x-small" color="success" variant="tonal" class="ml-1">运行中</v-chip>
              </div>
              <v-btn
                v-if="task.State !== 'Running'"
                icon="mdi-play"
                variant="tonal"
                size="small"
                color="primary"
                title="立即运行"
                @click="runTask(task.Id)"
              />
              <v-btn
                v-else
                icon="mdi-stop"
                variant="tonal"
                size="small"
                color="error"
                title="停止任务"
                @click="stopTask(task.Id)"
              />
            </div>

            <!-- 信息行：字段恒定渲染，保证同一排卡片行高对齐 -->
            <div class="card-info card-info--stacked px-4 pb-2">
              <div class="info-item">
                <span class="info-label">上次运行</span>
                <span class="text-caption text-medium-emphasis">{{ formatTaskDate(task.LastExecutionResult?.EndTimeUtc) }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">说明</span>
                <span class="text-caption text-medium-emphasis text-truncate-3" :title="task.Description || ''">{{ task.Description || '暂无任务描述' }}</span>
              </div>
            </div>

            <!-- 运行进度 -->
            <template v-if="task.State === 'Running'">
              <v-divider class="mt-2" />
              <div class="pa-3">
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
              </div>
            </template>
          </v-card>
        </div>
      </div>
    </div>
  </v-container>
</template>

