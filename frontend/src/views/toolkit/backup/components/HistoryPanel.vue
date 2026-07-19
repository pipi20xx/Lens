<template>
  <n-card size="small" segmented title="执行历史">
    <template #header-extra>
      <n-button size="small" @click="fetchHistory">
        刷新
      </n-button>
    </template>

    <n-spin :show="loading">
      <div v-if="history.length" class="history-list">
        <div
          v-for="row in history"
          :key="row.id"
          class="history-card"
          :class="`is-${row.status}`"
        >
          <!-- 卡片头部：任务名 + 状态 -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="task-name text-truncate">{{ row.task_name }}</n-text>
            </div>
            <n-tag
              :type="statusType(row.status)"
              size="small"
              round
            >
              {{ statusLabels[row.status] || row.status }}
            </n-tag>
          </div>

          <!-- 信息行 -->
          <div class="card-info">
            <div class="info-item">
              <span class="info-label">时间</span>
              <n-text depth="3" style="font-size: 12px">{{ formatTime(row.start_time) }}</n-text>
            </div>
            <div class="info-item">
              <span class="info-label">大小</span>
              <n-text depth="3" style="font-size: 12px">{{ row.size.toFixed(2) }} MB</n-text>
            </div>
          </div>

          <!-- 消息 -->
          <div class="card-message" v-if="row.message">
            <n-text depth="3" class="message-text text-clamp-2">{{ row.message }}</n-text>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-else-if="!loading"
        description="暂无执行历史"
        style="padding: 60px 0"
      />
    </n-spin>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { NCard, NTag, NButton, NText, NSpin, NEmpty } from 'naive-ui'
import axios from 'axios'

const history = ref([])
const loading = ref(false)
let timer: any = null

const statusLabels = { success: '成功', running: '进行中...', failed: '失败' }

const statusType = (status: string) => {
  if (status === 'success') return 'success'
  if (status === 'running') return 'info'
  return 'error'
}

const formatTime = (time: string) => {
  return new Date(time).toLocaleString()
}

const fetchHistory = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const res = await axios.get('/api/backup/history')
    history.value = res.data

    // 如果有任务正在运行，启动/继续轮询
    const hasRunning = res.data.some((item: any) => item.status === 'running')
    if (hasRunning) {
      startPolling()
    } else {
      stopPolling()
    }
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

defineExpose({ fetchHistory })

onMounted(() => {
  fetchHistory()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
/* 历史列表：一行一个卡片 */
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
  transition: border-color var(--transition-normal), box-shadow var(--transition-normal);
  position: relative;
  overflow: hidden;
}

.history-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: transparent;
  transition: background var(--transition-normal);
}

.history-card.is-success::before {
  background: var(--color-success, #10B981);
}

.history-card.is-running::before {
  background: var(--color-info, #3B82F6);
}

.history-card.is-failed::before {
  background: var(--color-error, #EF4444);
}

.history-card:hover {
  border-color: rgba(64, 128, 240, 0.75);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.task-name {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

/* 信息行 */
.card-info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  font-size: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.info-label {
  color: var(--text-color, #fff);
  opacity: 0.5;
  font-size: 11px;
  flex-shrink: 0;
}

/* 消息 */
.card-message {
  padding-top: 4px;
  border-top: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
}

.message-text {
  font-size: 12px;
  line-height: 1.5;
  word-break: break-all;
}
</style>
