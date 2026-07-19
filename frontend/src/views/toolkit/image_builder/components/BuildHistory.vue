<template>
  <n-modal v-model:show="show" preset="card" :title="`构建历史 - ${projectName}`" style="width: 800px">
    <!-- 构建历史卡片列表：一行一个 -->
    <n-spin :show="loading">
      <div v-if="tasks.length" class="history-list">
        <div
          v-for="row in tasks"
          :key="row.id"
          class="history-card"
        >
          <!-- 卡片头部：状态标签 + Tag -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="history-tag">{{ row.tag || '-' }}</n-text>
            </div>
            <n-tag
              size="small"
              :type="getStatusConfig(row.status).type"
              ghost
            >{{ getStatusConfig(row.status).label }}</n-tag>
          </div>

          <!-- 执行时间 -->
          <div class="card-desc">
            <n-text depth="3" class="desc-text">执行时间: {{ formatDate(row.created_at) }}</n-text>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <n-button
              size="small"
              @click="viewLog(row.id)"
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
    
    <!-- 内层日志查看器 -->
    <n-modal v-model:show="showLog" preset="card" title="详细日志" style="width: 90%; max-width: 1200px; height: 96vh;">
      <div class="log-container-wrapper">
        <div class="log-container">
          <pre>{{ currentLog }}</pre>
        </div>
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
import { NModal, NButton, NSpace, NTag, NSpin, NEmpty, NText, useMessage, useDialog } from 'naive-ui'
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
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
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
/* 卡片列表：一行一个卡片 */
.history-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
  max-height: 400px;
  overflow-y: auto;
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

.history-tag {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

/* 描述 */
.card-desc {
  min-width: 0;
}

.desc-text {
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

/* 日志容器 */
.log-container-wrapper {
  height: calc(96vh - 180px); /* 减去 Header, Footer 和 Padding 的高度 */
  overflow: hidden;
}

.log-container {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  height: 100%;
  overflow-y: auto;
  font-family: monospace;
  white-space: pre-wrap;
  border: 1px solid rgba(255, 255, 255, 0.1);
}
</style>