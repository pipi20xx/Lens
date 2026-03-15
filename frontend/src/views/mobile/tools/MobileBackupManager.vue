<template>
  <div class="mobile-backup-manager">
    <div class="page-header">
      <h1 class="page-title">数据备份管理</h1>
      <p class="page-desc">管理系统备份与恢复</p>
    </div>

    <n-card class="action-card" :bordered="false">
      <n-space vertical>
        <n-button block type="primary" :loading="creating" @click="createBackup">
          <template #icon><n-icon><BackupIcon /></n-icon></template>
          创建新备份
        </n-button>
        <n-button block type="info" secondary :loading="loading" @click="loadBackups">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          刷新备份列表
        </n-button>
      </n-space>
    </n-card>

    <n-card class="backups-card" :bordered="false" title="备份列表">
      <div v-if="backups.length === 0" class="empty-state">
        <n-empty description="暂无备份" />
      </div>
      <div v-else class="backup-list">
        <div v-for="backup in backups" :key="backup.id" class="backup-item">
          <div class="backup-info">
            <div class="backup-name">{{ backup.name }}</div>
            <div class="backup-meta">
              <span>{{ backup.type }}</span>
              <span>{{ formatDate(backup.created_at) }}</span>
              <span>{{ formatSize(backup.size) }}</span>
            </div>
          </div>
          <div class="backup-actions">
            <n-button size="small" secondary type="info" @click="restoreBackup(backup)">
              恢复
            </n-button>
            <n-button size="small" secondary type="warning" @click="downloadBackup(backup)">
              下载
            </n-button>
            <n-popconfirm @positive-click="deleteBackup(backup.id)" positive-text="确认删除" negative-text="取消">
              <template #trigger>
                <n-button size="small" secondary type="error">
                  删除
                </n-button>
              </template>
              确定删除此备份？
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 恢复弹窗 -->
    <n-modal v-model:show="showRestoreModal" preset="card" title="恢复备份" style="width: 90vw; max-width: 400px">
      <n-space vertical>
        <p style="color: var(--text-color); margin-bottom: 12px;">
          请选择恢复模式：
        </p>
        <n-radio-group v-model:value="restoreMode">
          <n-space vertical>
            <n-radio value="overwrite">
              覆盖还原（保留已有文件）
            </n-radio>
            <n-radio value="clear">
              清空还原（删除目标目录所有内容）
            </n-radio>
          </n-space>
        </n-radio-group>
        <n-space justify="end" style="margin-top: 16px;">
          <n-button secondary @click="showRestoreModal = false">取消</n-button>
          <n-button type="warning" :loading="restoring" @click="confirmRestore">确认恢复</n-button>
        </n-space>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NPopconfirm, NIcon, NModal, NSelect, NRadio, NRadioGroup } from 'naive-ui'
import { BackupOutlined as BackupIcon, RefreshOutlined as RefreshIcon } from '@vicons/material'
import { backupApi } from '@/api/backup'
import { useMessage } from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const loading = ref(false)
const creating = ref(false)
const backups = ref<any[]>([])

const loadBackups = async () => {
  loading.value = true
  try {
    const res = await backupApi.getTasks()
    backups.value = res as any || []
  } catch (e) {
    message.error('加载备份列表失败')
  } finally {
    loading.value = false
  }
}

const createBackup = async () => {
  creating.value = true
  try {
    const task = {
      name: '手动备份',
      mode: 'full',
      storage_type: 'local',
      sync_strategy: 'once',
      compression_level: 6,
      src_path: '/data',
      dst_path: '/backup',
      enabled: true,
      schedule_type: 'manual',
      schedule_value: '',
      ignore_patterns: [],
      host_id: 'default'
    }
    await backupApi.saveTask(task)
    message.success('备份任务已创建')
    await loadBackups()
  } catch (e) {
    message.error('创建备份失败')
  } finally {
    creating.value = false
  }
}

const restoreBackup = async (backup: any) => {
  // 获取该任务的备份历史
  try {
    const res = await axios.get(`/api/backup/history?task_id=${backup.id}`)
    const history = res.data || []
    if (history.length === 0) {
      message.warning('该任务暂无备份历史')
      return
    }
    // 找到最新的成功备份
    const latestBackup = history.find((h: any) => h.status === 'success')
    if (!latestBackup) {
      message.warning('没有找到成功的备份记录')
      return
    }
    // 打开恢复弹窗
    selectedHistory.value = latestBackup
    showRestoreModal.value = true
  } catch (e: any) {
    message.error('获取备份历史失败: ' + (e.response?.data?.detail || e.message))
  }
}

const confirmRestore = async () => {
  if (!selectedHistory.value) return
  restoring.value = true
  try {
    await axios.post(`/api/backup/history/${selectedHistory.value.id}/restore?clear_dst=${restoreMode.value === 'clear'}`)
    message.success('恢复任务已启动')
    showRestoreModal.value = false
  } catch (e: any) {
    message.error('恢复失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    restoring.value = false
  }
}

const downloadBackup = async (backup: any) => {
  // 获取该任务的备份历史
  try {
    const res = await axios.get(`/api/backup/history?task_id=${backup.id}`)
    const history = res.data || []
    if (history.length === 0) {
      message.warning('该任务暂无备份历史')
      return
    }
    // 找到最新的成功备份
    const latestBackup = history.find((h: any) => h.status === 'success')
    if (!latestBackup) {
      message.warning('没有找到成功的备份记录')
      return
    }
    // 下载文件
    const downloadUrl = `/api/backup/history/${latestBackup.id}/download`
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = `${backup.name}.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    message.success('开始下载备份')
  } catch (e: any) {
    message.error('下载失败: ' + (e.response?.data?.detail || e.message))
  }
}

const showRestoreModal = ref(false)
const selectedHistory = ref<any>(null)
const restoreMode = ref('overwrite')
const restoring = ref(false)

const deleteBackup = async (id: string) => {
  try {
    await backupApi.saveTask({ id, enabled: false })
    message.success('备份已禁用')
    await loadBackups()
  } catch (e) {
    message.error('禁用备份失败')
  }
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

const formatSize = (bytes: number) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

onMounted(() => {
  loadBackups()
})
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

.action-card,
.backups-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.backup-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.backup-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.backup-info {
  margin-bottom: 8px;
}

.backup-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.backup-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.backup-actions {
  display: flex;
  gap: 8px;
}
</style>
