<template>
  <!-- 构建历史弹框 -->
  <n-modal v-model:show="show" preset="card" :title="`构建历史 - ${projectName}`" style="width: 800px">
    <n-spin :show="loading">
      <div v-if="tasks.length" class="history-list">
        <div
          v-for="row in tasks"
          :key="row.id"
          class="history-card"
        >
          <!-- 卡片头部：完整镜像地址 + 状态标签 -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="history-image-name text-truncate">{{ row.image_name || row.tag || '-' }}</n-text>
            </div>
            <n-tag
              size="small"
              :type="getStatusConfig(row.status).type"
              ghost
            >{{ getStatusConfig(row.status).label }}</n-tag>
          </div>

          <!-- 构建平台标签 -->
          <div v-if="row.platforms" class="card-platforms">
            <n-tag
              v-for="p in splitPlatforms(row.platforms)"
              :key="p"
              size="small"
              type="info"
              ghost
            >{{ p }}</n-tag>
          </div>

          <!-- 执行信息 -->
          <div class="card-meta">
            <n-text class="meta-text" v-if="row.host_name">🖥️ 构建主机: {{ row.host_name }}</n-text>
            <n-text class="meta-text">⏱️ 开始: {{ formatDate(row.created_at) }}</n-text>
            <n-text class="meta-text" v-if="row.completed_at">🏁 完成: {{ formatDate(row.completed_at) }}</n-text>
            <n-text class="meta-text" v-if="row.completed_at && row.created_at">⚡ 耗时: {{ formatDuration(row.created_at, row.completed_at) }}</n-text>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <n-button
              size="small"
              @click="viewLog(row)"
            >
              查看日志
            </n-button>
            <n-button
              size="small"
              type="error"
              ghost
              @click="deleteLog(row.id)"
            >
              删除
            </n-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-else-if="!loading"
        description="暂无构建历史"
        style="padding: 40px 0"
      />
    </n-spin>
  </n-modal>

  <!-- 日志查看器弹框（独立于历史弹框，避免嵌套层级问题） -->
  <n-modal
    v-model:show="showLog"
    preset="card"
    :title="logModalTitle"
    style="width: 90%; max-width: 1200px;"
  >
    <div class="log-toolbar">
      <n-space align="center" size="small">
        <n-tag v-if="currentTaskStatus" size="small" :type="getStatusConfig(currentTaskStatus).type" ghost>
          {{ getStatusConfig(currentTaskStatus).label }}
        </n-tag>
        <n-text depth="3" class="log-toolbar-hint">
          <span v-if="logLoading">正在加载日志...</span>
          <span v-else>共 {{ currentLog ? currentLog.split('\n').length : 0 }} 行</span>
        </n-text>
      </n-space>
      <n-space size="small">
        <n-button size="small" :loading="logLoading" @click="refreshLog">
          刷新
        </n-button>
        <n-button size="small" @click="scrollToBottom">
          滚动到底部
        </n-button>
      </n-space>
    </div>
    <div class="log-container-wrapper">
      <n-spin :show="logLoading">
        <div ref="logContainerRef" class="log-container">
          <pre>{{ currentLog || '暂无日志内容' }}</pre>
        </div>
      </n-spin>
    </div>
    <template #footer>
      <n-space justify="end">
        <n-button type="primary" @click="showLog = false">
          关闭
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { NModal, NButton, NSpace, NTag, NSpin, NEmpty, NText, useMessage, useDialog } from 'naive-ui'
import axios from 'axios'

const props = defineProps<{
  show: boolean
  projectId: string
  projectName: string
}>()

const emit = defineEmits(['update:show'])

const show = ref(false)
const tasks = ref<any[]>([])
const loading = ref(false)

// 日志查看相关状态
const showLog = ref(false)
const logLoading = ref(false)
const currentLog = ref('')
const currentTaskId = ref('')
const currentTaskStatus = ref('')
const logContainerRef = ref<HTMLElement | null>(null)

const message = useMessage()
const dialog = useDialog()

// 日志弹框标题
const logModalTitle = computed(() => {
  return currentTaskId.value ? `构建日志` : '详细日志'
})

// 辅助函数：状态映射
const getStatusConfig = (status: string) => {
  const statusMap: Record<string, { label: string, type: 'success' | 'error' | 'info' | 'warning' }> = {
    'SUCCESS': { label: '成功', type: 'success' },
    'FAILED': { label: '失败', type: 'error' },
    'PENDING': { label: '处理中', type: 'info' }
  }
  return statusMap[status] || { label: status, type: 'info' }
}

// 辅助函数：日期格式化
const formatDate = (createdAt: string) => {
  if (!createdAt) return '-'
  const date = new Date(createdAt)
  return date.toLocaleString('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
}

// 辅助函数：耗时格式化
const formatDuration = (start: string, end: string) => {
  const startTime = new Date(start).getTime()
  const endTime = new Date(end).getTime()
  if (isNaN(startTime) || isNaN(endTime) || endTime < startTime) return '-'
  const seconds = Math.floor((endTime - startTime) / 1000)
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  const remainSeconds = seconds % 60
  if (minutes < 60) return `${minutes}分${remainSeconds}秒`
  const hours = Math.floor(minutes / 60)
  const remainMinutes = minutes % 60
  return `${hours}小时${remainMinutes}分${remainSeconds}秒`
}

// 辅助函数：拆分平台字符串
const splitPlatforms = (platforms: string) => {
  return (platforms || '').split(',').filter((p: string) => p.trim())
}

// 滚动日志到底部（使用 scrollIntoView 适配浏览器原生滚动）
const scrollToBottom = () => {
  nextTick(() => {
    if (logContainerRef.value) {
      logContainerRef.value.scrollIntoView({ behavior: 'smooth', block: 'end' })
    }
  })
}

watch(() => props.show, (val) => {
  show.value = val
  if (val) fetchHistory()
})

watch(show, (val) => {
  emit('update:show', val)
})

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

// 查看日志：传入整行数据，记录任务状态用于展示
const viewLog = async (row: any) => {
  currentTaskId.value = row.id
  currentTaskStatus.value = row.status || ''
  showLog.value = true
  await fetchLog()
}

// 拉取日志内容
const fetchLog = async () => {
  if (!currentTaskId.value) return
  logLoading.value = true
  try {
    const res = await axios.get(`/api/image-builder/tasks/${currentTaskId.value}/log`)
    currentLog.value = res.data.content || ''
    // 日志加载后自动滚动到底部（最新输出）
    scrollToBottom()
  } catch (e) {
    message.error('读取日志失败')
  } finally {
    logLoading.value = false
  }
}

// 刷新日志（对正在构建中的任务特别有用）
const refreshLog = () => {
  fetchLog()
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
/* 卡片列表：一行一个卡片
   不限制高度，内容自然撑开，超出由浏览器滚动条处理 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.history-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  background: var(--card-bg-color, rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(64, 128, 240, 0.4);
  transition: border-color var(--transition-normal, 250ms ease),
              box-shadow var(--transition-normal, 250ms ease),
              transform var(--transition-fast, 150ms ease);
  position: relative;
  overflow: hidden;
}

.history-card:hover {
  border-color: rgba(64, 128, 240, 0.75);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.history-card:active {
  transform: scale(0.99);
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.history-image-name {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

.text-truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 平台标签 */
.card-platforms {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* 元信息 */
.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  min-width: 0;
}

.meta-text {
  font-size: 12px;
  line-height: 1.5;
  word-break: break-all;
}

/* 操作按钮 */
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
}

.card-actions .n-button {
  flex: 1 1 auto;
  min-width: 56px;
}

/* 移动端适配 */
@media (max-width: 767px) {
  .card-actions .n-button {
    flex: 1 1 calc(50% - 3px);
    min-width: 0;
  }
}

@media (max-width: 380px) {
  .card-actions .n-button {
    flex: 1 1 100%;
  }
}

/* 日志工具栏 */
.log-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.log-toolbar-hint {
  font-size: 12px;
}

/* 日志容器：不限制高度，内容自然撑开，超出由浏览器滚动条处理 */
.log-container-wrapper {
  overflow: visible;
}

.log-container {
  background: var(--code-bg-color, #1e1e1e);
  color: var(--text-color, #d4d4d4);
  padding: 12px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.1));
}

.log-container pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}
</style>
