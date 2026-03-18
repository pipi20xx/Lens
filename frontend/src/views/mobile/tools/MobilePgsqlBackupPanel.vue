<template>
  <div class="mobile-pgsql-backup-panel">
    <n-space vertical>
      <n-space justify="space-between" align="center">
        <n-button type="primary" size="small" @click="openCreateModal">
          创建备份
        </n-button>
        <n-button size="small" secondary @click="fetchBackups" :loading="loading">
          刷新
        </n-button>
      </n-space>

      <n-alert type="info" size="small" :show-icon="false">
        备份文件存储在 data/backups/pg 目录下
      </n-alert>

      <div v-if="backupList.length === 0" class="empty-state">
        <n-empty description="暂无备份" size="small" />
      </div>

      <div v-else class="backup-list">
        <div v-for="backup in backupList" :key="backup.filename" class="backup-item">
          <div class="backup-header">
            <div class="backup-filename">{{ backup.filename }}</div>
            <n-space>
              <n-button size="tiny" secondary type="warning" @click="openRestoreModal(backup)">
                还原
              </n-button>
              <n-popconfirm @positive-click="() => handleDelete(backup.filename)" positive-text="确认" negative-text="取消">
                <template #trigger>
                  <n-button size="tiny" secondary type="error">
                    删除
                  </n-button>
                </template>
                确认删除？
              </n-popconfirm>
            </n-space>
          </div>
          <div class="backup-info">
            <div class="info-row">
              <n-icon size="14"><DbIcon /></n-icon>
              <span>数据库: {{ backup.db_name }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><SizeIcon /></n-icon>
              <span>大小: {{ formatSize(backup.size) }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><TimeIcon /></n-icon>
              <span>时间: {{ formatDate(backup.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </n-space>

    <n-modal v-model:show="showCreateModal" preset="card" title="创建数据库备份" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="选择数据库">
          <n-select 
            v-model:value="selectedDbToBackup" 
            :options="dbOptions" 
            placeholder="请选择要备份的数据库" 
          />
        </n-form-item>
        <n-text depth="3" style="font-size: 12px">
          提示：备份将使用 pg_dump 生成 .bak 文件（自定义格式），支持高效还原。
        </n-text>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button secondary @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" @click="handleCreateBackup" :loading="actionLoading">开始备份</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showRestoreModal" preset="card" :title="`还原备份: ${selectedBackup?.filename}`" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="目标数据库">
          <n-select 
            v-model:value="selectedDbToRestore" 
            :options="dbOptions" 
            placeholder="选择要还原到的目标数据库" 
          />
        </n-form-item>
        <n-alert type="warning" title="危险警告">
          还原操作将执行以下步骤：
          1. 强制断开目标数据库的所有连接。
          2. 删除并重新创建该数据库。
          3. 从备份文件恢复数据。
          所有当前数据将被覆盖！
        </n-alert>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button secondary @click="showRestoreModal = false">取消</n-button>
          <n-button type="error" @click="handleRestore" :loading="actionLoading">确认还原</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { 
  NSpace, NButton, NModal, NForm, NFormItem, NSelect, 
  NIcon, NAlert, NText, NEmpty, NPopconfirm, useMessage, useDialog 
} from 'naive-ui'
import {
  BackupOutlined as BackupIcon
} from '@vicons/material'
import axios from 'axios'

const props = defineProps<{ host: any }>()
const message = useMessage()
const dialog = useDialog()

const backupList = ref<any[]>([])
const dbList = ref<any[]>([])
const loading = ref(false)
const actionLoading = ref(false)

const showCreateModal = ref(false)
const selectedDbToBackup = ref<string | null>(null)

const showRestoreModal = ref(false)
const selectedBackup = ref<any>(null)
const selectedDbToRestore = ref<string | null>(null)

const dbOptions = computed(() => dbList.value.map(db => ({ label: db.name, value: db.name })))

const formatSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

const fetchBackups = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/pgsql/backups')
    backupList.value = res.data
  } catch (e: any) {
    message.error('获取备份列表失败')
  } finally {
    loading.value = false
  }
}

const fetchDatabases = async () => {
  if (!props.host) return
  try {
    const res = await axios.post('/api/pgsql/databases', props.host)
    dbList.value = res.data
  } catch (e) {}
}

const openCreateModal = () => {
  showCreateModal.value = true
  fetchDatabases()
}

const handleCreateBackup = async () => {
  if (!selectedDbToBackup.value || !props.host) return
  actionLoading.value = true
  try {
    await axios.post('/api/pgsql/backups/create', {
      config: props.host,
      req: { dbname: selectedDbToBackup.value }
    }, { timeout: 0 })
    message.success('备份创建成功')
    showCreateModal.value = false
    fetchBackups()
  } catch (e: any) {
    message.error('备份失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    actionLoading.value = false
  }
}

const openRestoreModal = (row: any) => {
  selectedBackup.value = row
  selectedDbToRestore.value = row.db_name !== 'unknown' ? row.db_name : null
  showRestoreModal.value = true
  fetchDatabases()
}

const handleRestore = async () => {
  if (!selectedBackup.value || !selectedDbToRestore.value || !props.host) return
  
  actionLoading.value = true
  try {
    await axios.post(`/api/pgsql/backups/restore/${selectedBackup.value.filename}`, props.host, {
      params: { dbname: selectedDbToRestore.value },
      timeout: 0
    })
    message.success('数据库还原成功')
    showRestoreModal.value = false
  } catch (e: any) {
    message.error('还原失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    actionLoading.value = false
  }
}

const handleDelete = async (filename: string) => {
  try {
    await axios.delete(`/api/pgsql/backups/${filename}`)
    message.success('已删除备份')
    fetchBackups()
  } catch (e) {
    message.error('删除失败')
  }
}

watch(() => props.host, () => {
  fetchBackups()
}, { immediate: true })

defineExpose({ refresh: fetchBackups })
</script>

<style scoped>
.mobile-pgsql-backup-panel {
  padding: 12px 0;
}

.empty-state {
  padding: 40px 0;
}

.backup-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.backup-item {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #3B82F6;
  border-radius: 12px;
  margin-bottom: 12px;
}

.backup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.backup-filename {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color);
  word-break: break-all;
}

.backup-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color-3);
}
</style>
