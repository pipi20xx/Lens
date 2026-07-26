<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { pgsqlApi } from '@/api/pgsql'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError, info } = useNotification()
const { confirm } = useConfirm()

// ========== 主机选择 ==========
const hosts = ref<any[]>([])
const selectedHostId = ref<string | null>(null)
const hostLoading = ref(false)

const LS_HOST_KEY = 'pgsql_selected_host'

const hostOptions = computed(() => hosts.value.map(h => ({ label: h.name, value: h.id })))
const selectedHost = computed(() => hosts.value.find(h => h.id === selectedHostId.value))

async function fetchHosts() {
  try {
    hostLoading.value = true
    const data = await pgsqlApi.getHosts()
    hosts.value = Array.isArray(data) ? data : []
    if (hosts.value.length > 0) {
      const saved = localStorage.getItem(LS_HOST_KEY)
      if (saved && hosts.value.some(h => h.id === saved)) {
        selectedHostId.value = saved
      } else if (!selectedHostId.value) {
        selectedHostId.value = hosts.value[0].id
      }
    }
  } catch {
    showError('加载主机列表失败')
  } finally {
    hostLoading.value = false
  }
}

watch(selectedHostId, (val) => {
  if (val) localStorage.setItem(LS_HOST_KEY, val)
})

// ========== Tab 管理 ==========
const activeTab = ref('data')

// ========== 主机管理弹窗 ==========
const showHostManagerDialog = ref(false)
const showHostEditDialog = ref(false)
const editingHostId = ref<string | null>(null)
const hostForm = ref<any>({
  name: '', host: 'localhost', port: 5432, username: 'postgres', password: '', database: 'postgres'
})
const hostTesting = ref(false)

function openAddHost() {
  editingHostId.value = null
  hostForm.value = { name: '', host: 'localhost', port: 5432, username: 'postgres', password: '', database: 'postgres' }
  showHostEditDialog.value = true
}

function openEditHost(row: any) {
  editingHostId.value = row.id
  hostForm.value = { name: row.name, host: row.host, port: row.port, username: row.username, password: row.password, database: row.database }
  showHostEditDialog.value = true
}

async function testHostConnection() {
  hostTesting.value = true
  try {
    const config = { host: hostForm.value.host, port: hostForm.value.port, username: hostForm.value.username, password: hostForm.value.password, database: hostForm.value.database }
    const res = await pgsqlApi.testConnection(config)
    if (res?.success) success('测试成功: ' + (res.version || ''))
    else showError('失败: ' + (res?.message || '未知错误'))
  } catch {
    showError('请求出错')
  } finally {
    hostTesting.value = false
  }
}

async function saveHost() {
  if (!hostForm.value.name) return showError('请输入名称')
  try {
    const config = { host: hostForm.value.host, port: hostForm.value.port, username: hostForm.value.username, password: hostForm.value.password, database: hostForm.value.database }
    if (editingHostId.value) {
      await pgsqlApi.updateHost(editingHostId.value, config, hostForm.value.name)
      success('已更新')
    } else {
      await pgsqlApi.addHost(config, hostForm.value.name)
      success('已添加')
    }
    showHostEditDialog.value = false
    fetchHosts()
  } catch {
    showError('保存失败')
  }
}

async function deleteHost(id: string) {
  const ok = await confirm({ title: '确认移除', content: '确定要移除该数据库主机配置吗？', confirmColor: 'error' })
  if (!ok) return
  try {
    await pgsqlApi.deleteHost(id)
    info('已移除')
    fetchHosts()
  } catch {
    showError('移除失败')
  }
}

// ========== 数据浏览器 ==========
const dbList = ref<string[]>([])
const currentDb = ref<string | null>(null)
const tableList = ref<string[]>([])
const selectedTable = ref<string | null>(null)
const tableData = ref<any[]>([])
const tableColumns = ref<any[]>([])
const tableLoading = ref(false)

const dbOptions = computed(() => dbList.value.map(db => ({ label: db, value: db })))

const pagination = ref({ page: 1, pageSize: 50, total: 0 })

const activeConfig = computed(() => {
  if (!selectedHost.value || !currentDb.value) return null
  return { ...selectedHost.value, database: currentDb.value }
})

async function fetchDatabases() {
  if (!selectedHost.value) return
  try {
    const data = await pgsqlApi.getDatabases(selectedHost.value)
    dbList.value = Array.isArray(data) ? data.map((db: any) => db.name) : []
    if (!currentDb.value && dbList.value.length > 0) {
      if (dbList.value.includes(selectedHost.value.database)) {
        currentDb.value = selectedHost.value.database
      } else {
        currentDb.value = dbList.value[0]
      }
      fetchTables()
    }
  } catch {
    showError('加载数据库列表失败')
  }
}

async function fetchTables() {
  if (!activeConfig.value) return
  try {
    const data = await pgsqlApi.getTables(activeConfig.value)
    tableList.value = data?.tables || []
    if (tableList.value.length === 0) info('该库下未发现公有表')
  } catch {
    showError('加载表列表失败')
  }
}

async function fetchTableData() {
  if (!selectedTable.value || !activeConfig.value) return
  tableLoading.value = true
  try {
    const data = await pgsqlApi.getTableData(activeConfig.value, {
      table_name: selectedTable.value,
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    })
    tableColumns.value = (data?.columns || []).map((col: any) => ({
      title: col.name,
      key: col.name,
      width: 150,
    }))
    tableData.value = data?.rows || []
    pagination.value.total = data?.total || 0
  } catch {
    showError('加载数据失败')
  } finally {
    tableLoading.value = false
  }
}

function handleDbChange() {
  selectedTable.value = null
  tableList.value = []
  tableData.value = []
  fetchTables()
}

function handleTableSelect(table: string) {
  selectedTable.value = table
  pagination.value.page = 1
  fetchTableData()
}

// 数据值查看器
const showViewerDialog = ref(false)
const viewerTitle = ref('')
const viewerValue = ref<any>(null)

function openViewer(title: string, val: any) {
  viewerTitle.value = title
  viewerValue.value = val
  showViewerDialog.value = true
}

const formattedViewerContent = computed(() => {
  const val = viewerValue.value
  if (val === null) return 'NULL'
  if (typeof val === 'object') return JSON.stringify(val, null, 2)
  if (typeof val === 'string') {
    try {
      if ((val.startsWith('{') && val.endsWith('}')) || (val.startsWith('[') && val.endsWith(']'))) {
        return JSON.stringify(JSON.parse(val), null, 2)
      }
    } catch { /* ignore */ }
    return val
  }
  return String(val)
})

async function copyViewerContent() {
  try {
    await navigator.clipboard.writeText(formattedViewerContent.value)
    success('已复制到剪贴板')
  } catch {
    showError('复制失败')
  }
}

// ========== 数据库列表 Tab ==========
const dbInfoList = ref<any[]>([])
const dbInfoLoading = ref(false)

async function fetchDbInfoList() {
  if (!selectedHost.value) return
  dbInfoLoading.value = true
  try {
    const data = await pgsqlApi.getDatabases(selectedHost.value)
    dbInfoList.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载数据库列表失败')
  } finally {
    dbInfoLoading.value = false
  }
}

// 创建数据库
const showCreateDbDialog = ref(false)
const newDbName = ref('')
const newDbOwner = ref<string | null>(null)
const creatingDb = ref(false)
const dbUserList = ref<any[]>([])
const dbUserOptions = computed(() => dbUserList.value.map(u => ({ label: u.username, value: u.username })))

async function fetchDbUsers() {
  if (!selectedHost.value) return
  try {
    const data = await pgsqlApi.getUsers(selectedHost.value)
    dbUserList.value = Array.isArray(data) ? data : []
  } catch { /* ignore */ }
}

function openCreateDb() {
  newDbName.value = ''
  newDbOwner.value = null
  showCreateDbDialog.value = true
  fetchDbUsers()
}

async function createDatabase() {
  if (!newDbName.value || !selectedHost.value) return
  creatingDb.value = true
  try {
    await pgsqlApi.createDatabase(selectedHost.value, { dbname: newDbName.value, owner: newDbOwner.value || undefined })
    success('创建成功')
    showCreateDbDialog.value = false
    fetchDbInfoList()
    fetchDatabases()
  } catch {
    showError('创建失败')
  } finally {
    creatingDb.value = false
  }
}

// 编辑数据库
const showEditDbDialog = ref(false)
const editingDb = ref<any>(null)
const editDbForm = ref({ owner: '', description: '' })
const updatingDb = ref(false)

function openEditDb(row: any) {
  editingDb.value = row
  editDbForm.value = { owner: row.owner || '', description: row.description || '' }
  showEditDbDialog.value = true
  fetchDbUsers()
}

async function updateDatabase() {
  if (!editingDb.value || !selectedHost.value) return
  updatingDb.value = true
  try {
    await pgsqlApi.updateDatabase(editingDb.value.name, selectedHost.value, { owner: editDbForm.value.owner, description: editDbForm.value.description })
    success('更新成功')
    showEditDbDialog.value = false
    fetchDbInfoList()
  } catch {
    showError('更新失败')
  } finally {
    updatingDb.value = false
  }
}

async function dropDatabase(dbName: string) {
  if (!selectedHost.value) return
  const ok = await confirm({
    title: '危险操作',
    content: `确定要永久删除数据库 "${dbName}" 吗？系统将强制终止活跃连接。`,
    confirmColor: 'error', confirmText: '确认删除'
  })
  if (!ok) return
  try {
    await pgsqlApi.dropDatabase(dbName, selectedHost.value)
    success('已删除')
    fetchDbInfoList()
    fetchDatabases()
  } catch {
    showError('删除失败')
  }
}

// ========== 用户列表 Tab ==========
const userList = ref<any[]>([])
const userLoading = ref(false)

async function fetchUsers() {
  if (!selectedHost.value) return
  userLoading.value = true
  try {
    const data = await pgsqlApi.getUsers(selectedHost.value)
    userList.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载用户列表失败')
  } finally {
    userLoading.value = false
  }
}

function getPermTags(row: any) {
  const tags: { label: string; color: string }[] = []
  if (row.is_superuser) tags.push({ label: 'SUPERUSER', color: 'error' })
  if (row.can_create_db) tags.push({ label: 'CREATEDB', color: 'info' })
  if (row.can_create_role) tags.push({ label: 'CREATEROLE', color: 'info' })
  if (row.replication) tags.push({ label: 'REPLICATION', color: 'warning' })
  if (row.bypass_rls) tags.push({ label: 'BYPASSRLS', color: 'warning' })
  if (row.inherit) tags.push({ label: 'INHERIT', color: 'grey' })
  return tags
}

// 创建用户
const showCreateUserDialog = ref(false)
const creatingUser = ref(false)
const userForm = ref<any>({
  username: '', password: '', can_login: true, is_superuser: false,
  can_create_db: false, can_create_role: false, inherit: true,
  replication: false, bypass_rls: false, connection_limit: -1
})

function openCreateUser() {
  userForm.value = { username: '', password: '', can_login: true, is_superuser: false, can_create_db: false, can_create_role: false, inherit: true, replication: false, bypass_rls: false, connection_limit: -1 }
  showCreateUserDialog.value = true
}

async function createUser() {
  if (!userForm.value.username || !selectedHost.value) return
  creatingUser.value = true
  try {
    await pgsqlApi.createUser(selectedHost.value, userForm.value)
    success('创建角色成功')
    showCreateUserDialog.value = false
    fetchUsers()
  } catch {
    showError('创建失败')
  } finally {
    creatingUser.value = false
  }
}

// 编辑用户
const showEditUserDialog = ref(false)
const updatingUser = ref(false)
const editingUser = ref<any>(null)
const editUserForm = ref<any>({
  password: '', can_login: true, is_superuser: false, can_create_db: false,
  can_create_role: false, inherit: true, replication: false, bypass_rls: false,
  connection_limit: -1, valid_until: null
})

function openEditUser(row: any) {
  editingUser.value = row
  editUserForm.value = {
    password: '', can_login: row.can_login, is_superuser: row.is_superuser,
    can_create_db: row.can_create_db, can_create_role: row.can_create_role,
    inherit: row.inherit, replication: row.replication, bypass_rls: row.bypass_rls,
    connection_limit: row.connection_limit, valid_until: row.valid_until
  }
  showEditUserDialog.value = true
}

async function updateUser() {
  if (!editingUser.value || !selectedHost.value) return
  updatingUser.value = true
  try {
    await pgsqlApi.updateUser(editingUser.value.username, selectedHost.value, { ...editUserForm.value, password: editUserForm.value.password || null })
    success('更新成功')
    showEditUserDialog.value = false
    fetchUsers()
  } catch {
    showError('更新失败')
  } finally {
    updatingUser.value = false
  }
}

async function dropUser(username: string) {
  if (!selectedHost.value) return
  const ok = await confirm({ title: '删除角色', content: `确定要删除角色 "${username}" 吗？`, confirmColor: 'error' })
  if (!ok) return
  try {
    await pgsqlApi.dropUser(username, selectedHost.value)
    success('已删除')
    fetchUsers()
  } catch {
    showError('删除失败')
  }
}

// ========== 备份与恢复 Tab ==========
const backupList = ref<any[]>([])
const backupLoading = ref(false)

async function fetchBackups() {
  backupLoading.value = true
  try {
    const data = await pgsqlApi.getBackups()
    backupList.value = Array.isArray(data) ? data : []
  } catch {
    showError('获取备份列表失败')
  } finally {
    backupLoading.value = false
  }
}

function formatSize(bytes: number) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString()
}

// 创建备份弹窗
const showCreateBackupDialog = ref(false)
const selectedDbToBackup = ref<string | null>(null)
const backupDbOptions = computed(() => dbInfoList.value.map(db => ({ label: db.name, value: db.name })))
const actionLoading = ref(false)

function openCreateBackup() {
  selectedDbToBackup.value = null
  showCreateBackupDialog.value = true
  fetchDbInfoList()
}

async function createBackup() {
  if (!selectedDbToBackup.value || !selectedHost.value) return
  actionLoading.value = true
  try {
    await pgsqlApi.createBackup(selectedHost.value, { dbname: selectedDbToBackup.value })
    success('备份创建成功')
    showCreateBackupDialog.value = false
    fetchBackups()
  } catch {
    showError('备份失败')
  } finally {
    actionLoading.value = false
  }
}

// 还原备份弹窗
const showRestoreDialog = ref(false)
const selectedBackup = ref<any>(null)
const selectedDbToRestore = ref<string | null>(null)

function openRestoreModal(row: any) {
  selectedBackup.value = row
  selectedDbToRestore.value = row.db_name !== 'unknown' ? row.db_name : null
  showRestoreDialog.value = true
  fetchDbInfoList()
}

async function restoreBackup() {
  if (!selectedBackup.value || !selectedDbToRestore.value || !selectedHost.value) return
  actionLoading.value = true
  try {
    await pgsqlApi.restoreBackup(selectedBackup.value.filename, selectedHost.value, selectedDbToRestore.value)
    success('数据库还原成功')
    showRestoreDialog.value = false
  } catch {
    showError('还原失败')
  } finally {
    actionLoading.value = false
  }
}

async function deleteBackup(filename: string) {
  const ok = await confirm({ title: '确认删除', content: `确定要删除备份文件 ${filename} 吗？此操作不可撤销。`, confirmColor: 'error' })
  if (!ok) return
  try {
    await pgsqlApi.deleteBackup(filename)
    success('已删除备份')
    fetchBackups()
  } catch {
    showError('删除失败')
  }
}

// ========== 刷新全部 ==========
const refreshing = ref(false)

async function refreshAll() {
  if (!selectedHost.value) return
  refreshing.value = true
  await Promise.all([fetchDatabases(), fetchDbInfoList(), fetchUsers(), fetchBackups()])
  refreshing.value = false
}

// ========== 监听主机切换 ==========
watch(selectedHost, () => {
  currentDb.value = null
  selectedTable.value = null
  dbList.value = []
  tableList.value = []
  tableData.value = []
  fetchDatabases()
  fetchDbInfoList()
  fetchUsers()
  fetchBackups()
})

onMounted(fetchHosts)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-database-outline</v-icon>
      PostgreSQL 数据库管理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">直连 PostgreSQL 数据库，支持数据表浏览、SQL 调试及库级备份还原操作。</p>

    <!-- 主机选择 + 管理按钮 -->
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <div class="d-flex align-center justify-space-between flex-wrap ga-3 pa-4">
        <div class="d-flex align-center ga-3">
          <v-select v-model="selectedHostId" :items="hostOptions" item-title="label" item-value="value"
            label="选择数据库实例" variant="outlined" density="compact" hide-details style="max-width:260px"
            @update:model-value="fetchHosts" />
          <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-cog-outline" @click="showHostManagerDialog = true">
            管理主机
          </v-btn>
        </div>
        <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh" :loading="refreshing" :disabled="!selectedHost" @click="refreshAll">
          全部刷新
        </v-btn>
      </div>
    </v-card>

    <v-tabs v-model="activeTab" class="mb-4" color="primary">
      <v-tab value="data"><v-icon start>mdi-table</v-icon> 数据浏览器</v-tab>
      <v-tab value="databases"><v-icon start>mdi-database-outline</v-icon> 数据库列表</v-tab>
      <v-tab value="users"><v-icon start>mdi-account-group-outline</v-icon> 用户列表</v-tab>
      <v-tab value="backup"><v-icon start>mdi-backup-restore</v-icon> 备份与恢复</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">

      <!-- ==================== 数据浏览器 ==================== -->
      <v-window-item value="data">
        <div v-if="!selectedHost" class="text-center py-12 text-medium-emphasis">请先选择一个数据库实例</div>
        <template v-else>
          <div class="d-flex ga-4" style="min-height:500px">
            <!-- 左侧：数据库+表列表 -->
            <v-card class="liquid-glass-card" rounded="xl" style="flex:0 0 240px;min-width:200px">
              <div class="pa-3" style="border-bottom:1px solid rgba(255,255,255,0.06)">
                <v-select v-model="currentDb" :items="dbOptions" item-title="label" item-value="value"
                  density="compact" variant="outlined" label="切换数据库" hide-details
                  @update:model-value="handleDbChange" />
                <v-btn block size="x-small" variant="tonal" color="info" prepend-icon="mdi-refresh" class="mt-2" @click="fetchTables">刷新表列表</v-btn>
              </div>
              <div class="pa-2" style="max-height:500px;overflow-y:auto">
                <div v-for="t in tableList" :key="t" @click="handleTableSelect(t)"
                  class="d-flex align-center ga-2 pa-2 rounded-lg cursor-pointer"
                  :class="selectedTable === t ? 'bg-primary bg-opacity-15' : ''"
                  style="cursor:pointer;transition:background .15s">
                  <v-icon size="16" color="primary">mdi-table</v-icon>
                  <span class="text-body-2" :class="selectedTable === t ? 'font-weight-bold' : ''">{{ t }}</span>
                </div>
                <div v-if="!tableList.length && currentDb" class="text-center py-4 text-medium-emphasis text-caption">
                  该库下没有发现公有表
                </div>
              </div>
            </v-card>

            <!-- 右侧：数据表格 -->
            <v-card class="liquid-glass-card flex-grow-1" rounded="xl">
              <div v-if="!selectedTable" class="text-center py-12 text-medium-emphasis">
                {{ currentDb ? '请从左侧选择一个表' : '请先选择一个数据库' }}
              </div>
              <template v-else>
                <div class="d-flex align-center justify-space-between pa-4 pb-2">
                  <div class="d-flex align-center ga-2">
                    <v-icon color="primary">mdi-table</v-icon>
                    <span class="text-subtitle-2 font-weight-bold">{{ selectedTable }}</span>
                    <v-chip size="small" color="info" variant="tonal">{{ pagination.total }} 条记录</v-chip>
                  </div>
                  <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh" :loading="tableLoading" @click="fetchTableData">刷新数据</v-btn>
                </div>
                <v-divider />
                <div style="overflow-x:auto">
                  <v-table density="compact" class="bg-transparent">
                    <thead>
                      <tr>
                        <th v-for="col in tableColumns" :key="col.key">{{ col.title }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-if="tableLoading"><td :colspan="tableColumns.length" class="text-center py-8"><v-progress-circular indeterminate color="primary" size="small" /></td></tr>
                      <tr v-else-if="!tableData.length"><td :colspan="tableColumns.length" class="text-center py-8 text-medium-emphasis">暂无数据</td></tr>
                      <tr v-for="(row, idx) in tableData" :key="idx">
                        <td v-for="col in tableColumns" :key="col.key" style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
                          <template v-if="row[col.key] === null">
                            <span class="text-medium-emphasis font-italic">NULL</span>
                          </template>
                          <template v-else-if="typeof row[col.key] === 'object'">
                            <v-btn size="x-small" color="primary" variant="tonal" prepend-icon="mdi-code-block-braces" @click="openViewer(col.key, row[col.key])">查看 JSON</v-btn>
                          </template>
                          <template v-else-if="typeof row[col.key] === 'string' && row[col.key].length > 80">
                            <v-btn size="x-small" color="primary" variant="tonal" prepend-icon="mdi-eye-outline" @click="openViewer(col.key, row[col.key])">查看详情</v-btn>
                          </template>
                          <template v-else>
                            <span style="cursor:pointer" @click="openViewer(col.key, row[col.key])">{{ row[col.key] }}</span>
                          </template>
                        </td>
                      </tr>
                    </tbody>
                  </v-table>
                </div>
                <!-- 分页 -->
                <v-divider />
                <div class="d-flex align-center justify-center pa-3 ga-2">
                  <v-btn size="x-small" variant="tonal" color="secondary" prepend-icon="mdi-chevron-left" :disabled="pagination.page <= 1" @click="pagination.page--; fetchTableData()">上一页</v-btn>
                  <span class="text-caption text-medium-emphasis">第 {{ pagination.page }} 页</span>
                  <v-btn size="x-small" variant="tonal" color="secondary" prepend-icon="mdi-chevron-right" :disabled="pagination.page * pagination.pageSize >= pagination.total" @click="pagination.page++; fetchTableData()">下一页</v-btn>
                </div>
              </template>
            </v-card>
          </div>
        </template>
      </v-window-item>

      <!-- ==================== 数据库列表 ==================== -->
      <v-window-item value="databases">
        <div v-if="!selectedHost" class="text-center py-12 text-medium-emphasis">请先选择一个数据库实例</div>
        <template v-else>
          <div class="d-flex justify-space-between mb-4">
            <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" @click="openCreateDb">创建数据库</v-btn>
            <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh" :loading="dbInfoLoading" @click="fetchDbInfoList">刷新</v-btn>
          </div>

          <v-progress-linear v-if="dbInfoLoading" indeterminate color="primary" class="mb-4" />

          <div v-if="dbInfoList.length" class="d-flex flex-column ga-3">
            <v-card v-for="db in dbInfoList" :key="db.name" variant="outlined" rounded="lg" class="pa-3">
              <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-1">
                <span class="font-weight-bold">{{ db.name }}</span>
                <v-chip size="small" color="info" variant="tonal">{{ db.owner }}</v-chip>
              </div>
              <div class="text-body-2 text-medium-emphasis mb-2" style="font-size:12px">
                {{ db.description || '无描述' }}
              </div>
              <v-divider class="mb-2" />
              <div class="d-flex flex-wrap ga-2">
                <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-pencil-outline" @click="openEditDb(db)">编辑</v-btn>
                <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="dropDatabase(db.name)">删除</v-btn>
              </div>
            </v-card>
          </div>
          <div v-else-if="!dbInfoLoading" class="text-center py-12 text-medium-emphasis">暂无数据库</div>
        </template>
      </v-window-item>

      <!-- ==================== 用户列表 ==================== -->
      <v-window-item value="users">
        <div v-if="!selectedHost" class="text-center py-12 text-medium-emphasis">请先选择一个数据库实例</div>
        <template v-else>
          <div class="d-flex justify-space-between mb-4">
            <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" @click="openCreateUser">创建用户</v-btn>
            <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh" :loading="userLoading" @click="fetchUsers">刷新</v-btn>
          </div>

          <v-progress-linear v-if="userLoading" indeterminate color="primary" class="mb-4" />

          <div v-if="userList.length" class="d-flex flex-column ga-3">
            <v-card v-for="row in userList" :key="row.username" variant="outlined" rounded="lg" class="pa-3"
              style="border-left:3px solid" :style="{ borderLeftColor: row.is_superuser ? '#EF4444' : row.can_login ? '#10B981' : 'transparent' }">
              <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-1">
                <div class="d-flex align-center ga-2">
                  <span class="font-weight-bold">{{ row.username }}</span>
                  <v-chip v-if="row.is_superuser" size="x-small" color="error" variant="tonal">超级用户</v-chip>
                </div>
                <v-chip :color="row.can_login ? 'success' : 'grey'" size="small" variant="tonal">
                  {{ row.can_login ? '可登录' : '不可登录' }}
                </v-chip>
              </div>

              <!-- 权限标签 -->
              <div v-if="getPermTags(row).length" class="d-flex flex-wrap ga-1 mb-2">
                <v-chip v-for="perm in getPermTags(row)" :key="perm.label" size="x-small" :color="perm.color" variant="tonal">{{ perm.label }}</v-chip>
              </div>

              <div v-if="row.connection_limit !== undefined && row.connection_limit !== null" class="text-caption text-medium-emphasis mb-2">
                连接限制: {{ row.connection_limit === -1 ? '无限制' : row.connection_limit }}
              </div>

              <v-divider class="mb-2" />
              <div class="d-flex flex-wrap ga-2">
                <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-pencil-outline" @click="openEditUser(row)">编辑</v-btn>
                <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="dropUser(row.username)">删除</v-btn>
              </div>
            </v-card>
          </div>
          <div v-else-if="!userLoading" class="text-center py-12 text-medium-emphasis">暂无用户</div>
        </template>
      </v-window-item>

      <!-- ==================== 备份与恢复 ==================== -->
      <v-window-item value="backup">
        <div class="d-flex flex-wrap justify-space-between align-center ga-3 mb-4">
          <div class="d-flex ga-2">
            <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" :disabled="!selectedHost" @click="openCreateBackup">创建新备份</v-btn>
            <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh" :loading="backupLoading" @click="fetchBackups">刷新</v-btn>
          </div>
          <v-chip size="small" variant="tonal" color="info">备份文件存储在 data/backups/pg 目录下</v-chip>
        </div>

        <v-progress-linear v-if="backupLoading" indeterminate color="primary" class="mb-4" />

        <div v-if="backupList.length" class="d-flex flex-column ga-3">
          <v-card v-for="row in backupList" :key="row.filename" variant="outlined" rounded="lg" class="pa-3"
            style="border-left:3px solid #3B82F6">
            <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-1">
              <span class="font-weight-bold font-mono" style="font-size:13px">{{ row.filename }}</span>
              <v-chip size="small" color="info" variant="tonal">{{ row.db_name }}</v-chip>
            </div>
            <div class="d-flex flex-wrap ga-4 text-caption text-medium-emphasis mb-2">
              <span>大小: {{ formatSize(row.size) }}</span>
              <span>创建时间: {{ formatDate(row.created_at) }}</span>
            </div>
            <v-divider class="mb-2" />
            <div class="d-flex flex-wrap ga-2">
              <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-restore" @click="openRestoreModal(row)">还原</v-btn>
              <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="deleteBackup(row.filename)">删除</v-btn>
            </div>
          </v-card>
        </div>
        <div v-else-if="!backupLoading" class="text-center py-12 text-medium-emphasis">暂无备份文件</div>
      </v-window-item>
    </v-window>

    <!-- ==================== 管理主机弹窗 ==================== -->
    <GlassDialog v-model="showHostManagerDialog" :max-width="650" icon="mdi-server-outline" title="管理 PostgreSQL 主机" :cancel-visible="false">
      <div class="d-flex justify-space-between mb-4">
        <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-plus" @click="openAddHost">添加新主机</v-btn>
        <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-refresh" @click="fetchHosts">刷新</v-btn>
      </div>
      <v-table density="compact" class="bg-transparent">
        <thead><tr><th>名称</th><th>地址</th><th class="text-right">操作</th></tr></thead>
        <tbody>
          <tr v-for="h in hosts" :key="h.id">
            <td class="font-weight-medium">{{ h.name }}</td>
            <td class="text-medium-emphasis font-mono" style="font-size:12px">{{ h.host }}:{{ h.port }}</td>
            <td class="text-right">
              <v-btn size="x-small" variant="tonal" color="primary" prepend-icon="mdi-pencil-outline" @click="openEditHost(h)">编辑</v-btn>
              <v-btn size="x-small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" class="ml-1" @click="deleteHost(h.id)">移除</v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </GlassDialog>

    <!-- ==================== 添加/编辑主机弹窗 ==================== -->
    <GlassDialog v-model="showHostEditDialog" :max-width="500" :title="editingHostId ? '编辑数据库主机' : '配置数据库主机'">
  <v-text-field v-model="hostForm.name" label="显示名称" variant="outlined" density="compact"
            hint="例如: 生产环境库" persistent-hint class="mb-3" />
          <v-row class="mb-3">
            <v-col cols="8">
              <v-text-field v-model="hostForm.host" label="主机" variant="outlined" density="compact" hint="localhost" persistent-hint />
            </v-col>
            <v-col cols="4">
              <v-text-field v-model="hostForm.port" label="端口" type="number" variant="outlined" density="compact" />
            </v-col>
          </v-row>
          <v-text-field v-model="hostForm.username" label="用户名" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="hostForm.password" label="密码" type="password" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="hostForm.database" label="默认数据库" variant="outlined" density="compact" />
  <template #actions>
    <v-btn color="warning" variant="tonal" prepend-icon="mdi-lan-connect" :loading="hostTesting" @click="testHostConnection">测试连接</v-btn>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveHost">{{ editingHostId ? '保存修改' : '保存主机' }}</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 数据值查看器弹窗 ==================== -->
<GlassDialog v-model="showViewerDialog" :max-width="1000" :cancel-visible="false">
      <template #title>
        <v-icon start>mdi-eye-outline</v-icon>
        查看: {{ viewerTitle }}
        <v-spacer />
        <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-content-copy" @click="copyViewerContent">复制内容</v-btn>
      </template>
      <pre class="code-block code-block--flat">{{ formattedViewerContent }}</pre>
    </GlassDialog>

    <!-- ==================== 创建数据库弹窗 ==================== -->
    <GlassDialog v-model="showCreateDbDialog" :max-width="450" title="创建数据库">
  <v-text-field v-model="newDbName" label="数据库名称" variant="outlined" density="compact" class="mb-3" />
          <v-select v-model="newDbOwner" :items="dbUserOptions" item-title="label" item-value="value"
            label="所有者" variant="outlined" density="compact" clearable hint="选择所有者 (可选)" persistent-hint />
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-plus" :loading="creatingDb" @click="createDatabase">立即创建</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 编辑数据库弹窗 ==================== -->
    <GlassDialog v-model="showEditDbDialog" :max-width="500" :title="'编辑数据库:' + (editingDb?.name)">
  <v-select v-model="editDbForm.owner" :items="dbUserOptions" item-title="label" item-value="value"
            label="所有者" variant="outlined" density="compact" class="mb-3" />
          <v-textarea v-model="editDbForm.description" label="备注/描述" variant="outlined" density="compact"
            rows="3" hint="为数据库添加描述信息..." persistent-hint />
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" :loading="updatingDb" @click="updateDatabase">保存修改</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 创建用户弹窗 ==================== -->
    <GlassDialog v-model="showCreateUserDialog" :max-width="550" title="创建数据库用户/角色">
  <v-text-field v-model="userForm.username" label="用户名/角色名" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="userForm.password" label="密码" type="password" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="userForm.connection_limit" label="连接限制" type="number" variant="outlined" density="compact"
            hint="输入 -1 表示无限制" persistent-hint class="mb-3" />

          <div class="text-subtitle-2 mb-2">权限设置</div>
          <v-row>
            <v-col cols="6"><v-switch v-model="userForm.can_login" label="允许登录 (LOGIN)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="userForm.is_superuser" label="超级用户 (SUPERUSER)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="userForm.can_create_db" label="创建数据库 (CREATEDB)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="userForm.can_create_role" label="创建角色 (CREATEROLE)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="userForm.inherit" label="继承权限 (INHERIT)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="userForm.replication" label="流复制 (REPLICATION)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="12"><v-switch v-model="userForm.bypass_rls" label="绕过 RLS (BYPASSRLS)" density="compact" color="primary" hide-details /></v-col>
          </v-row>
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-plus" :loading="creatingUser" @click="createUser">创建角色</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 编辑用户弹窗 ==================== -->
    <GlassDialog v-model="showEditUserDialog" :max-width="550" :title="'编辑数据库用户:' + (editingUser?.username)">
  <v-text-field v-model="editUserForm.password" label="重置密码" type="password" variant="outlined" density="compact"
            hint="留空则不修改" persistent-hint class="mb-3" />
          <v-text-field v-model="editUserForm.connection_limit" label="连接限制" type="number" variant="outlined" density="compact"
            hint="输入 -1 表示无限制" persistent-hint class="mb-3" />

          <div class="text-subtitle-2 mb-2">权限设置</div>
          <v-row>
            <v-col cols="6"><v-switch v-model="editUserForm.can_login" label="允许登录 (LOGIN)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="editUserForm.is_superuser" label="超级用户 (SUPERUSER)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="editUserForm.can_create_db" label="创建数据库 (CREATEDB)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="editUserForm.can_create_role" label="创建角色 (CREATEROLE)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="editUserForm.inherit" label="继承权限 (INHERIT)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="6"><v-switch v-model="editUserForm.replication" label="流复制 (REPLICATION)" density="compact" color="primary" hide-details /></v-col>
            <v-col cols="12"><v-switch v-model="editUserForm.bypass_rls" label="绕过 RLS (BYPASSRLS)" density="compact" color="primary" hide-details /></v-col>
          </v-row>
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" :loading="updatingUser" @click="updateUser">保存修改</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 创建备份弹窗 ==================== -->
    <GlassDialog v-model="showCreateBackupDialog" :max-width="450" title="创建数据库备份">
  <v-select v-model="selectedDbToBackup" :items="backupDbOptions" item-title="label" item-value="value"
            label="选择数据库" variant="outlined" density="compact" hint="请选择要备份的数据库" persistent-hint class="mb-3" />
          <div class="text-caption text-medium-emphasis">提示：备份将使用 pg_dump 生成 .bak 文件（自定义格式），支持高效还原。</div>
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-backup-restore" :loading="actionLoading" @click="createBackup">开始备份</v-btn>
  </template>
</GlassDialog>

    <!-- ==================== 还原备份弹窗 ==================== -->
    <GlassDialog v-model="showRestoreDialog" :max-width="450" :title="'还原备份:' + (selectedBackup?.filename)">
  <v-select v-model="selectedDbToRestore" :items="backupDbOptions" item-title="label" item-value="value"
            label="目标数据库" variant="outlined" density="compact" hint="选择要还原到的目标数据库" persistent-hint class="mb-3" />
          <v-alert type="warning" variant="tonal" density="compact" class="mb-2">
            还原操作将执行以下步骤：<br />
            1. 强制断开目标数据库的所有连接。<br />
            2. 删除并重新创建该数据库。<br />
            3. 从备份文件恢复数据。<br />
            所有当前数据将被覆盖！
          </v-alert>
  <template #actions>
    <v-btn color="error" variant="flat" prepend-icon="mdi-restore" :loading="actionLoading" @click="restoreBackup">确认还原</v-btn>
  </template>
</GlassDialog>
  </v-container>
</template>

