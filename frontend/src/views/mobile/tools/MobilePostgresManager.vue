<template>
  <div class="mobile-postgres-manager">
    <div class="page-header">
      <h1 class="page-title">PostgreSQL 管理</h1>
      <p class="page-desc">管理 PostgreSQL 数据库连接与查询</p>
    </div>

    <n-card class="connection-card" :bordered="false" title="连接配置">
      <n-space vertical>
        <n-select
          v-model:value="selectedHostId"
          :options="hostOptions"
          placeholder="选择数据库实例"
          @update:value="handleHostChange"
        />
        <n-button block type="primary" secondary @click="showHostModal = true">
          <template #icon><n-icon><ServerIcon /></n-icon></template>
          管理主机
        </n-button>
        <n-button block secondary @click="refreshAll" :disabled="!selectedHost" :loading="refreshing">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          全部刷新
        </n-button>
      </n-space>
    </n-card>

    <n-card v-if="selectedHost" class="tabs-card" :bordered="false">
      <n-tabs v-model:value="activeTab" type="segment" animated>
        <n-tab-pane name="data" tab="数据浏览器">
          <div v-if="selectedHost" class="data-browser">
            <n-space vertical>
              <n-input
                v-model:value="query"
                type="textarea"
                placeholder="SELECT * FROM table_name LIMIT 10;"
                :rows="4"
              />
              <n-button block type="primary" :loading="querying" @click="executeQuery">
                <template #icon><n-icon><PlayIcon /></n-icon></template>
                执行查询
              </n-button>
              <div v-if="queryResult.length > 0" class="result-content">
                <div class="result-header">查询结果 ({{ queryResult.length }} 行)</div>
                <div class="result-table">
                  <div v-for="(row, index) in queryResult" :key="index" class="result-row">
                    <div v-for="(value, key) in row" :key="key" class="result-cell">
                      {{ value }}
                    </div>
                  </div>
                </div>
              </div>
            </n-space>
          </div>
          <div v-else class="empty-state">
            <n-empty description="请先选择数据库实例" />
          </div>
        </n-tab-pane>

        <n-tab-pane name="databases" tab="数据库列表">
          <div v-if="databases.length > 0" class="database-list">
            <div v-for="db in databases" :key="db.name" class="database-item">
              <div class="database-name">{{ db.name }}</div>
              <div class="database-size">{{ db.size }}</div>
            </div>
          </div>
          <div v-else class="empty-state">
            <n-empty description="暂无数据库" />
          </div>
        </n-tab-pane>

        <n-tab-pane name="users" tab="用户列表">
          <div v-if="users.length > 0" class="user-list">
            <div v-for="user in users" :key="user.name" class="user-item">
              <div class="user-name">{{ user.name }}</div>
              <div class="user-roles">{{ user.roles.join(', ') }}</div>
            </div>
          </div>
          <div v-else class="empty-state">
            <n-empty description="暂无用户" />
          </div>
        </n-tab-pane>

        <n-tab-pane name="backup" tab="备份与恢复">
          <n-space vertical>
            <n-button block type="primary" @click="createBackup">
              <template #icon><n-icon><BackupIcon /></n-icon></template>
              创建备份
            </n-button>
            <n-button block secondary @click="triggerRestoreInput">
              <template #icon><n-icon><RestoreIcon /></n-icon></template>
              恢复备份
              <input 
                type="file" 
                ref="restoreInputRef" 
                style="display: none" 
                accept=".sql,.backup" 
                @change="handleRestore"
              />
            </n-button>
            <div v-if="backups.length > 0" class="backup-list">
              <div v-for="backup in backups" :key="backup.id" class="backup-item">
                <div class="backup-info">
                  <div class="backup-name">{{ backup.name }}</div>
                  <div class="backup-date">{{ backup.date }}</div>
                  <div class="backup-size">{{ backup.size }}</div>
                </div>
                <n-button size="small" secondary type="error" @click="deleteBackup(backup.id)">
                  删除
                </n-button>
              </div>
            </div>
            <div v-else class="empty-state">
              <n-empty description="暂无备份" />
            </div>
          </n-space>
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- 主机管理弹窗 -->
    <n-modal v-model:show="showHostModal" preset="card" title="管理主机" style="width: 90vw; max-width: 400px">
      <n-space vertical>
        <n-button block type="primary" @click="openAddHostModal">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          添加主机
        </n-button>
        <div v-if="hosts.length > 0" class="host-list">
          <div v-for="host in hosts" :key="host.id" class="host-item">
            <div class="host-info">
              <div class="host-name">{{ host.name }}</div>
              <div class="host-host">{{ host.host }}:{{ host.port }}</div>
            </div>
            <div class="host-actions">
              <n-button size="small" secondary @click="openEditHostModal(host)">
                <template #icon><n-icon><EditIcon /></n-icon></template>
                编辑
              </n-button>
              <n-popconfirm @positive-click="handleDeleteHost(host.id)" positive-text="确认" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    <template #icon><n-icon><DeleteIcon /></n-icon></template>
                    删除
                  </n-button>
                </template>
                确定删除此主机？
              </n-popconfirm>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <n-empty description="暂无主机" />
        </div>
      </n-space>
    </n-modal>

    <!-- 主机编辑弹窗 -->
    <n-modal v-model:show="showHostEditModal" preset="card" :title="editHostMode ? '编辑主机' : '添加主机'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="主机名称">
          <n-input v-model:value="hostForm.name" placeholder="例如: 生产数据库" />
        </n-form-item>
        <n-form-item label="主机地址">
          <n-input v-model:value="hostForm.host" placeholder="localhost" />
        </n-form-item>
        <n-form-item label="端口">
          <n-input-number v-model:value="hostForm.port" placeholder="5432" />
        </n-form-item>
        <n-form-item label="数据库名">
          <n-input v-model:value="hostForm.database" placeholder="postgres" />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input v-model:value="hostForm.username" placeholder="postgres" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="hostForm.password" type="password" show-password-on="click" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showHostEditModal = false">取消</n-button>
          <n-button type="primary" @click="saveHost" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NCard, NButton, NSpace, NFormItem, NInput, NInputNumber, NIcon, NTabs, NTabPane, NEmpty, NModal, NForm, NSelect, NPopconfirm } from 'naive-ui'
import { DnsOutlined as ServerIcon, RefreshOutlined as RefreshIcon, PlayArrowOutlined as PlayIcon, AddOutlined as AddIcon, EditOutlined as EditIcon, DeleteOutlineOutlined as DeleteIcon, BackupOutlined as BackupIcon, RestoreOutlined as RestoreIcon } from '@vicons/material'
import { pgsqlApi } from '@/api/pgsql'
import { useMessage } from 'naive-ui'

const message = useMessage()
const activeTab = ref('data')
const refreshing = ref(false)
const querying = ref(false)
const saving = ref(false)
const query = ref('')
const queryResult = ref<any[]>([])

const hosts = ref<any[]>([])
const selectedHostId = ref<number | null>(null)
const selectedHost = computed(() => hosts.value.find(h => h.id === selectedHostId.value))

const showHostModal = ref(false)
const showHostEditModal = ref(false)
const editHostMode = ref(false)

const hostForm = ref({
  name: '',
  host: 'localhost',
  port: 5432,
  database: 'postgres',
  username: 'postgres',
  password: ''
})

const databases = ref<any[]>([])
const users = ref<any[]>([])
const backups = ref<any[]>([])

const restoreInputRef = ref<HTMLInputElement | null>(null)

const hostOptions = computed(() => {
  return hosts.value.map(h => ({ label: h.name, value: h.id }))
})

const handleHostChange = () => {
  if (selectedHost.value) {
    fetchDatabases()
    fetchUsers()
    fetchBackups()
  }
}

const fetchHosts = async () => {
  try {
    hosts.value = await pgsqlApi.getHosts()
  } catch (e: any) {
    message.error('获取主机列表失败: ' + (e.message || '未知错误'))
  }
}

const fetchDatabases = async () => {
  if (!selectedHost.value) return
  try {
    databases.value = await pgsqlApi.getDatabases(selectedHost.value)
  } catch (e: any) {
    message.error('获取数据库列表失败: ' + (e.message || '未知错误'))
  }
}

const fetchUsers = async () => {
  if (!selectedHost.value) return
  try {
    users.value = await pgsqlApi.getUsers(selectedHost.value)
  } catch (e: any) {
    message.error('获取用户列表失败: ' + (e.message || '未知错误'))
  }
}

const fetchBackups = async () => {
  if (!selectedHost.value) return
  try {
    backups.value = await pgsqlApi.getBackups(selectedHost.value)
  } catch (e: any) {
    message.error('获取备份列表失败: ' + (e.message || '未知错误'))
  }
}

const refreshAll = async () => {
  if (!selectedHost.value) return
  refreshing.value = true
  await Promise.all([
    fetchDatabases(),
    fetchUsers(),
    fetchBackups()
  ])
  refreshing.value = false
}

const executeQuery = async () => {
  if (!selectedHost.value) {
    message.warning('请先选择数据库实例')
    return
  }
  if (!query.value) {
    message.warning('请输入SQL查询语句')
    return
  }
  querying.value = true
  try {
    queryResult.value = await pgsqlApi.executeQuery(selectedHost.value, query.value)
    message.success('查询成功')
  } catch (e: any) {
    message.error('查询失败: ' + (e.message || '未知错误'))
    queryResult.value = []
  } finally {
    querying.value = false
  }
}

const openAddHostModal = () => {
  editHostMode.value = false
  hostForm.value = {
    name: '',
    host: 'localhost',
    port: 5432,
    database: 'postgres',
    username: 'postgres',
    password: ''
  }
  showHostEditModal.value = true
}

const openEditHostModal = (host: any) => {
  editHostMode.value = true
  hostForm.value = { ...host }
  showHostEditModal.value = true
}

const saveHost = async () => {
  if (!hostForm.value.name || !hostForm.value.host) {
    message.warning('请填写完整的主机信息')
    return
  }
  saving.value = true
  try {
    if (editHostMode.value) {
      await pgsqlApi.updateHost(hostForm.value.id, hostForm.value)
      message.success('主机更新成功')
    } else {
      await pgsqlApi.addHost(hostForm.value)
      message.success('主机添加成功')
    }
    showHostEditModal.value = false
    await fetchHosts()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleDeleteHost = async (id: number) => {
  try {
    await pgsqlApi.deleteHost(id)
    message.success('主机已删除')
    await fetchHosts()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

const createBackup = async () => {
  if (!selectedHost.value) return
  try {
    await pgsqlApi.createBackup(selectedHost.value)
    message.success('备份创建成功')
    await fetchBackups()
  } catch (e: any) {
    message.error('创建备份失败: ' + (e.message || '未知错误'))
  }
}

const triggerRestoreInput = () => {
  restoreInputRef.value?.click()
}

const handleRestore = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !selectedHost.value) return
  
  try {
    const text = await file.text()
    await pgsqlApi.restoreBackup(selectedHost.value, text)
    message.success('备份恢复成功')
    await refreshAll()
  } catch (e: any) {
    message.error('恢复备份失败: ' + (e.message || '未知错误'))
  }
}

const deleteBackup = async (id: number) => {
  try {
    await pgsqlApi.deleteBackup(id)
    message.success('备份已删除')
    await fetchBackups()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

onMounted(() => {
  fetchHosts()
})
</script>

<style scoped>
.mobile-postgres-manager {
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

.connection-card,
.tabs-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 40px 0;
}

.data-browser,
.database-list,
.user-list,
.backup-list,
.host-list {
  margin-top: 12px;
}

.database-item,
.user-item,
.backup-item,
.host-item {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}

.database-name,
.user-name,
.backup-name,
.host-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.database-size,
.user-roles,
.backup-date,
.backup-size,
.host-host {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.backup-info,
.host-info {
  margin-bottom: 8px;
}

.host-actions {
  display: flex;
  gap: 8px;
}

.result-content {
  margin-top: 12px;
}

.result-header {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 8px;
}

.result-table {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.result-row {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}

.result-cell {
  flex: 1;
  padding: 8px;
  font-size: 12px;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
