<template>
  <div class="mobile-backup-manager">
    <div class="page-header">
      <h1 class="page-title">数据备份管理</h1>
      <p class="page-desc">支持多模式增量备份，内置针对云盘、SSD 及 HDD 的传输优化逻辑</p>
    </div>

    <MobileBackupTaskPanel 
      ref="taskPanelRef"
      @add="handleAddTask"
      @edit="handleEditTask"
      @run="handleRunTask"
      @view-history="handleViewHistory"
    />

    <MobileBackupHistoryPanel ref="historyPanelRef" />

    <MobileBackupTaskEditModal 
      v-model:show="showEditModal"
      :task="editTask"
      @save="saveTask"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMessage } from 'naive-ui'
import axios from 'axios'

import MobileBackupTaskPanel from './MobileBackupTaskPanel.vue'
import MobileBackupHistoryPanel from './MobileBackupHistoryPanel.vue'
import MobileBackupTaskEditModal from './MobileBackupTaskEditModal.vue'

const message = useMessage()
const taskPanelRef = ref()
const historyPanelRef = ref()

const showEditModal = ref(false)
const editTask = ref<any>({})

const handleAddTask = () => {
  editTask.value = {
    name: '',
    mode: '7z',
    storage_type: 'ssd',
    sync_strategy: 'mirror',
    src_path: '/data',
    dst_path: '/backup',
    compression_level: 6,
    password: '',
    enabled: true,
    schedule_type: 'cron',
    schedule_value: '0 3 * * *',
    ignore_patterns: []
  }
  showEditModal.value = true
}

const handleEditTask = (task: any) => {
  editTask.value = { ...task }
  showEditModal.value = true
}

const saveTask = async () => {
  try {
    await axios.post('/api/backup/tasks', editTask.value)
    message.success('任务已保存')
    showEditModal.value = false
    await taskPanelRef.value?.fetchTasks()
  } catch (e: any) {
    message.error('保存失败: ' + (e.response?.data?.detail || e.message))
  }
}

const handleRunTask = async (task: any) => {
  try {
    await axios.post(`/api/backup/tasks/${task.id}/run`)
    message.success('任务已启动')
    await historyPanelRef.value?.fetchHistory()
  } catch (e: any) {
    message.error('启动失败: ' + (e.response?.data?.detail || e.message))
  }
}

const handleViewHistory = (task: any) => {
  message.info('查看历史记录功能开发中')
}
</script>

<style scoped>
.mobile-backup-manager {
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
</style>
