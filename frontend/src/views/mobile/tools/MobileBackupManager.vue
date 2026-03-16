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
      @browse="openBrowser"
    />

    <MobileBackupHistoryModal 
      v-model:show="showHistoryModal"
      :task-id="historyTaskId"
      :task-name="historyTaskName"
    />

    <MobilePathBrowserModal 
      v-model:show="showBrowser"
      :initial-path="browserInitialPath"
      @select="handlePathSelect"
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
import MobileBackupHistoryModal from './MobileBackupHistoryModal.vue'
import MobilePathBrowserModal from './MobilePathBrowserModal.vue'
import {
  ButtonText,
  MessageText,
} from '../constants'

const message = useMessage()

// 使用常量
const buttonText = ButtonText
const messageText = MessageText

const taskPanelRef = ref()
const historyPanelRef = ref()

const showEditModal = ref(false)
const editTask = ref<any>({})
const showHistoryModal = ref(false)
const historyTaskId = ref('')
const historyTaskName = ref('')
const showBrowser = ref(false)
const browserTarget = ref<'src' | 'dst'>('src')
const browserInitialPath = ref('/')

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
    ignore_patterns: [],
    host_id: 'local'
  }
  showEditModal.value = true
}

const handleEditTask = (task: any) => {
  editTask.value = JSON.parse(JSON.stringify(task))
  showEditModal.value = true
}

const saveTask = async () => {
  try {
    if (editTask.value.id) {
      await axios.put(`/api/backup/tasks/${editTask.value.id}`, editTask.value)
    } else {
      await axios.post('/api/backup/tasks', editTask.value)
    }
    message.success(messageText.SAVE_SUCCESS)
    showEditModal.value = false
    resetEditTask()
    await taskPanelRef.value?.fetchTasks()
  } catch (e: any) {
    message.error(messageText.SAVE_FAILED + ': ' + (e.response?.data?.detail || e.message))
  }
}

const resetEditTask = () => {
  editTask.value = {}
}

const handleRunTask = async (task: any) => {
  try {
    await axios.post(`/api/backup/tasks/${task.id}/run`)
    message.success(buttonText.RUN + messageText.SUCCESS)
    await historyPanelRef.value?.fetchHistory()
  } catch (e: any) {
    message.error(buttonText.RUN + messageText.FAILED + ': ' + (e.response?.data?.detail || e.message))
  }
}

const handleViewHistory = (task: any) => {
  historyTaskId.value = task.id
  historyTaskName.value = task.name
  showHistoryModal.value = true
}

const openBrowser = (target: 'src' | 'dst') => {
  browserTarget.value = target
  browserInitialPath.value = '/'
  showBrowser.value = true
}

const handlePathSelect = (path: string) => {
  if (browserTarget.value === 'src') {
    editTask.value.src_path = path
  } else {
    editTask.value.dst_path = path
  }
  showBrowser.value = false
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
