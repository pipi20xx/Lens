<template>
  <n-modal 
    :show="show" 
    @update:show="$emit('update:show', $event)" 
    preset="card" 
    :title="`${label.BACKUP_HISTORY}: ${taskName || label.LOADING}`" 
    style="width: 95vw; max-width: 600px"
  >
    <n-spin :show="loading">
      <div v-if="history.length === 0" class="empty-state">
        <n-empty :description="messageText.EMPTY_DATA" />
      </div>
      <div v-else class="history-list">
        <div v-for="item in history" :key="item.id" class="history-item">
          <div class="history-header">
            <n-tag :type="getStatusType(item.status)" :size="buttonSizes.SMALL">
              {{ getStatusLabel(item.status) }}
            </n-tag>
            <n-text depth="3" style="font-size: 12px">
              {{ formatDate(item.start_time) }}
            </n-text>
          </div>
          <div class="history-info">
            <div class="info-row">
              <span class="info-label">{{ label.SIZE }}:</span>
              <span class="info-value">{{ item.size.toFixed(2) }} MB</span>
            </div>
            <div class="info-row">
              <span class="info-label">{{ label.MESSAGE }}:</span>
              <span class="info-value">{{ item.message || '-' }}</span>
            </div>
          </div>
          <div v-if="item.status === 'success'" class="history-actions">
            <n-button 
              block 
              :type="buttonTypes.WARNING" 
              secondary 
              @click="handleRestore(item)"
            >
              {{ buttonText.RESTORE }}
            </n-button>
          </div>
        </div>
      </div>
    </n-spin>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NModal, NSpin, NEmpty, NTag, NText, NButton, useMessage, useDialog } from 'naive-ui'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  MessageText,
  Label,
} from '../constants'
import axios from 'axios'

const props = defineProps<{
  show: boolean
  taskId: string
  taskName: string
}>()

const emit = defineEmits(['update:show'])

const message = useMessage()
const dialog = useDialog()

const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const messageText = MessageText
const label = Label

const history = ref([])
const loading = ref(false)

const getStatusType = (status: string) => {
  if (status === 'success') return 'success'
  if (status === 'running') return 'info'
  return 'error'
}

const getStatusLabel = (status: string) => {
  const labels = { success: '成功', running: '运行中', failed: '失败' }
  return labels[status] || status
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

const fetchHistory = async () => {
  if (!props.taskId) return
  loading.value = true
  try {
    const res = await axios.get(`/api/backup/history?task_id=${props.taskId}`)
    history.value = res.data
  } catch (e) {
    message.error(messageText.LOAD_FAILED)
  } finally {
    loading.value = false
  }
}

const handleRestore = (row: any) => {
  const restoreMode = ref('overwrite')

  dialog.warning({
    title: '确认还原',
    content: () => {
      return `
        <div>
          <p>警告：还原操作将影响源目录 "${props.taskName}"。</p>
          <p style="margin-bottom: 12px; color: #d03050; font-weight: bold;">请选择还原模式：</p>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            <label>
              <input type="radio" value="overwrite" v-model="restoreMode.value" />
              覆盖还原 (保留目录中已有但备份中没有的文件)
            </label>
            <label>
              <input type="radio" value="clear" v-model="restoreMode.value" />
              清空还原 (还原前删除目标目录下所有内容)
            </label>
          </div>
        </div>
      `
    },
    positiveText: '确认执行',
    negativeText: '取消',
    onPositiveClick: () => {
      axios.post(`/api/backup/history/${row.id}/restore?clear_dst=${restoreMode.value === 'clear'}`)
        .then(() => {
          message.info('还原任务已在后台启动，请关注系统日志或稍后刷新历史')
          setTimeout(fetchHistory, 1000)
        })
        .catch(e => {
          message.error('启动还原失败: ' + (e.response?.data?.detail || '未知错误'))
        })
    }
  })
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    history.value = []
    fetchHistory()
  }
})
</script>

<style scoped>
.empty-state {
  padding: 40px 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.history-info {
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 13px;
}

.info-label {
  color: var(--text-color);
  opacity: 0.6;
}

.info-value {
  color: var(--text-color);
  font-weight: 500;
}

.history-actions {
  margin-top: 8px;
}
</style>
