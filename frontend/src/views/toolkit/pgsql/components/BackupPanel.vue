<template>
  <div class="backup-panel">
    <!-- 工具栏 -->
    <div class="toolbar-row">
      <div class="toolbar-left">
        <n-button type="primary" @click="openCreateModal" :disabled="!host">
          创建新备份
        </n-button>
        <n-button @click="fetchBackups" :loading="loading">
          刷新
        </n-button>
      </div>
      <n-alert type="info" size="small" :show-icon="false" class="storage-hint">
        备份文件存储在 data/backups/pg 目录下
      </n-alert>
    </div>

    <!-- 卡片列表 -->
    <n-spin :show="loading">
      <div v-if="backupList.length" class="backup-list">
        <div
          v-for="row in backupList"
          :key="row.filename"
          class="backup-card"
        >
          <!-- 卡片头部：文件名 + 原数据库 -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="filename text-truncate">{{ row.filename }}</n-text>
            </div>
            <n-tag size="small" type="info" quaternary>{{ row.db_name }}</n-tag>
          </div>

          <!-- 信息行 -->
          <div class="card-info">
            <div class="info-item">
              <span class="info-label">大小</span>
              <n-text depth="3" style="font-size: 12px">{{ formatSize(row.size) }}</n-text>
            </div>
            <div class="info-item">
              <span class="info-label">创建时间</span>
              <n-text depth="3" style="font-size: 12px">{{ formatDate(row.created_at) }}</n-text>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <n-button
              size="small"
              type="warning"
              secondary
              @click="openRestoreModal(row)"
            >
              还原
            </n-button>
            <n-button
              size="small"
              type="error"
              secondary
              @click="handleDelete(row.filename)"
            >
              删除
            </n-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-else-if="!loading"
        description="暂无备份文件"
        style="padding: 60px 0"
      />
    </n-spin>

    <!-- 创建备份模态框 -->
    <n-modal v-model:show="showCreateModal" preset="card" title="创建数据库备份" style="width: 450px">
      <n-form label-placement="left" label-width="100">
        <n-form-item label="选择数据库">
          <n-select
            v-model:value="selectedDbToBackup"
            :options="dbOptions"
            placeholder="请选择要备份的数据库"
          />
        </n-form-item>
        <n-p depth="3">
          提示：备份将使用 pg_dump 生成 .bak 文件（自定义格式），支持高效还原。
        </n-p>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreateModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="handleCreateBackup" :loading="actionLoading">
            开始备份
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 还原备份模态框 -->
    <n-modal v-model:show="showRestoreModal" preset="card" :title="`还原备份: ${selectedBackup?.filename}`" style="width: 450px">
      <n-form label-placement="left" label-width="100">
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
          <n-button @click="showRestoreModal = false">
            取消
          </n-button>
          <n-button type="error" @click="handleRestore" :loading="actionLoading">
            确认还原
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import {
  NSpace, NButton, NModal, NForm, NFormItem, NSelect,
  useMessage, useDialog, NAlert, NP, NSpin, NEmpty, NText, NTag
} from 'naive-ui'
import axios from 'axios'

const props = defineProps<{ host: any }>()
const message = useMessage()
const dialog = useDialog()

const backupList = ref<any[]>([])
const dbList = ref<any[]>([])
const loading = ref(false)
const actionLoading = ref(false)

// 创建备份逻辑
const showCreateModal = ref(false)
const selectedDbToBackup = ref<string | null>(null)

// 还原备份逻辑
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
    }, { timeout: 0 }) // 覆盖全局超时，设置永不超时
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
      timeout: 0 // 覆盖全局超时，设置永不超时
    })
    message.success('数据库还原成功')
    showRestoreModal.value = false
  } catch (e: any) {
    message.error('还原失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    actionLoading.value = false
  }
}

const handleDelete = (filename: string) => {
  dialog.warning({
    title: '确认删除',
    content: `确定要删除备份文件 ${filename} 吗？此操作不可撤销。`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/pgsql/backups/${filename}`)
        message.success('已删除备份')
        fetchBackups()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

watch(() => props.host, () => {
  fetchBackups()
}, { immediate: true })

defineExpose({ refresh: fetchBackups })
</script>

<style scoped>
.backup-panel {
  width: 100%;
}

/* 工具栏 */
.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm, 0.5rem);
  margin-bottom: var(--space-md, 1rem);
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--space-sm, 0.5rem);
  flex-wrap: wrap;
}

.storage-hint {
  flex-shrink: 1;
}

/* 卡片列表：一行一个卡片 */
.backup-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.backup-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  background: var(--card-bg-color, rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(64, 128, 240, 0.4);
  transition: border-color var(--transition-normal, 250ms ease), box-shadow var(--transition-normal, 250ms ease), transform var(--transition-fast, 150ms ease);
  position: relative;
  overflow: hidden;
}

.backup-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: var(--color-info, #3B82F6);
  transition: background var(--transition-normal, 250ms ease);
}

.backup-card:hover {
  border-color: rgba(64, 128, 240, 0.75);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.backup-card:active {
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

.filename {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
  font-family: var(--font-mono, monospace);
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
