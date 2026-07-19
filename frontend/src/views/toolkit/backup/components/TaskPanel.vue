<template>
  <n-card size="small" segmented title="备份任务">
    <template #header-extra>
      <n-space>
        <n-button type="primary" size="small" @click="$emit('add')">
          新增任务
        </n-button>
        <n-button size="small" @click="fetchTasks">
          刷新
        </n-button>
      </n-space>
    </template>

    <n-spin :show="loading">
      <div v-if="tasks.length" class="task-list">
        <div
          v-for="row in tasks"
          :key="row.id"
          class="task-card"
          :class="{ 'is-auto': row.enabled }"
        >
          <!-- 卡片头部：任务名称 + 自动运行状态 -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="task-name text-truncate">{{ row.name }}</n-text>
              <n-tag
                v-if="row.host_id && row.host_id !== 'local'"
                type="warning"
                size="tiny"
                quaternary
              >
                远程
              </n-tag>
            </div>
            <n-tag
              :type="row.enabled ? 'success' : 'default'"
              size="small"
              round
            >
              {{ row.enabled ? '自动计划中' : '仅手动' }}
            </n-tag>
          </div>

          <!-- 信息行 -->
          <div class="card-info">
            <div class="info-item">
              <span class="info-label">模式</span>
              <n-tag type="info" size="tiny" quaternary>{{ row.mode }}</n-tag>
            </div>
            <div class="info-item">
              <span class="info-label">介质</span>
              <n-text depth="3" style="font-size: 12px">{{ storageLabels[row.storage_type] || 'SSD' }}</n-text>
            </div>
            <div class="info-item" v-if="row.enabled">
              <span class="info-label">计划</span>
              <n-text depth="3" style="font-size: 12px">{{ formatSchedule(row) }}</n-text>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <n-button
              size="small"
              type="primary"
              secondary
              @click="$emit('run', row)"
            >
              执行
            </n-button>
            <n-button
              size="small"
              secondary
              @click="$emit('view-history', row)"
            >
              历史
            </n-button>
            <n-button
              size="small"
              secondary
              @click="$emit('edit', row)"
            >
              编辑
            </n-button>
            <n-button
              size="small"
              type="error"
              ghost
              @click="handleDeleteTask(row)"
            >
              删除
            </n-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-else-if="!loading"
        description="暂无备份任务"
        style="padding: 60px 0"
      />
    </n-spin>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NSpace, NButton, NTag, NText, NSpin, NEmpty, useMessage, useDialog } from 'naive-ui'
import axios from 'axios'

const emit = defineEmits(['add', 'edit', 'run', 'view-history'])
const message = useMessage()
const dialog = useDialog()

const tasks = ref([])
const loading = ref(false)

const storageLabels = { ssd: 'SSD', hdd: 'HDD', cloud: '云盘' }

const formatSchedule = (row: any) => {
  if (!row.enabled) return '-'

  if (row.schedule_type === 'interval') {
    const min = parseInt(row.schedule_value)
    if (min % 1440 === 0) return `每隔 ${min / 1440} 天`
    if (min % 60 === 0) return `每隔 ${min / 60} 小时`
    return `每隔 ${min} 分钟`
  }

  if (row.schedule_type === 'cron') {
    const cron = row.schedule_value || ''
    const dailyMatch = cron.match(/^(\d+)\s+(\d+)\s+\*\s+\*\s+\*$/)
    if (dailyMatch) {
      const m = dailyMatch[1].padStart(2, '0')
      const h = dailyMatch[2].padStart(2, '0')
      return `每天 ${h}:${m}`
    }
    return cron
  }
  return row.schedule_value
}

const fetchTasks = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/backup/tasks')
    tasks.value = res.data
  } finally {
    loading.value = false
  }
}

const handleDeleteTask = (row) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除任务 "${row.name}" 吗？`,
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      await axios.delete(`/api/backup/tasks/${row.id}`)
      message.success('已删除')
      fetchTasks()
    }
  })
}

defineExpose({ fetchTasks })

onMounted(fetchTasks)
</script>

<style scoped>
/* 任务列表：一行一个卡片 */
.task-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.task-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 10px;
  background: var(--card-bg-color, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
  transition: border-color var(--transition-normal), box-shadow var(--transition-normal), transform var(--transition-fast);
  position: relative;
  overflow: hidden;
}

.task-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: transparent;
  transition: background var(--transition-normal);
}

.task-card.is-auto::before {
  background: var(--color-success, #10B981);
}

.task-card:hover {
  border-color: var(--border-medium, rgba(255, 255, 255, 0.12));
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.task-card:active {
  transform: scale(0.99);
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
</style>
