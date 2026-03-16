<template>
  <div class="mobile-pgsql-database-panel">
    <n-space vertical>
      <n-space justify="space-between" align="center">
        <n-button type="primary" size="small" @click="showCreateModal = true">
          创建数据库
        </n-button>
        <n-button size="small" secondary @click="fetchDatabases" :loading="loading">
          刷新
        </n-button>
      </n-space>

      <div v-if="dbList.length === 0" class="empty-state">
        <n-empty description="暂无数据库" size="small" />
      </div>

      <div v-else class="database-list">
        <div v-for="db in dbList" :key="db.name" class="database-item">
          <div class="database-header">
            <div class="database-name">{{ db.name }}</div>
            <n-space>
              <n-button size="tiny" secondary type="info" @click="openEditModal(db)">
                </n-button>
              <n-popconfirm @positive-click="() => handleDrop(db.name)" positive-text="确认" negative-text="取消">
                <template #trigger>
                  <n-button size="tiny" secondary type="error">
                    </n-button>
                </template>
                确认删除？
              </n-popconfirm>
            </n-space>
          </div>
          <div class="database-info">
            <div class="info-row">
              <n-icon size="14"><UserIcon /></n-icon>
              <span>所有者: {{ db.owner }}</span>
            </div>
            <div v-if="db.description" class="info-row">
              <n-icon size="14"><DescIcon /></n-icon>
              <span>{{ db.description }}</span>
            </div>
          </div>
        </div>
      </div>
    </n-space>

    <n-modal v-model:show="showCreateModal" preset="card" title="创建数据库" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="数据库名称">
          <n-input v-model:value="newDbName" placeholder="请输入库名" />
        </n-form-item>
        <n-form-item label="所有者">
          <n-select v-model:value="newDbOwner" :options="userOptions" placeholder="选择所有者 (可选)" clearable />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button secondary @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" @click="handleCreate" :loading="creating">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showEditModal" preset="card" :title="`编辑数据库: ${editingDb?.name}`" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="所有者">
          <n-select v-model:value="editForm.owner" :options="userOptions" placeholder="选择新所有者" />
        </n-form-item>
        <n-form-item label="备注/描述">
          <n-input
            v-model:value="editForm.description"
            type="textarea"
            placeholder="为数据库添加描述信息..."
            :autosize="{ minRows: 3 }"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button secondary @click="showEditModal = false">取消</n-button>
          <n-button type="primary" @click="handleUpdate" :loading="updating">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive, computed } from 'vue'
import { NSpace, NButton, NModal, NForm, NFormItem, NInput, NSelect, NIcon, NEmpty, NPopconfirm, useMessage, useDialog } from 'naive-ui'
import axios from 'axios'

const props = defineProps<{ host: any }>()
const message = useMessage()
const dialog = useDialog()

const dbList = ref<any[]>([])
const userList = ref<any[]>([])
const loading = ref(false)

const showCreateModal = ref(false)
const newDbName = ref('')
const newDbOwner = ref<string | null>(null)
const creating = ref(false)

const showEditModal = ref(false)
const updating = ref(false)
const editingDb = ref<any>(null)
const editForm = reactive({
  owner: '',
  description: ''
})

const userOptions = computed(() => userList.value.map(u => ({ label: u.username, value: u.username })))

const fetchDatabases = async () => {
  if (!props.host) return
  loading.value = true
  try {
    console.log('Fetching databases with host:', props.host)
    const res = await axios.post('/api/pgsql/databases', props.host)
    console.log('Databases response:', res.data)
    dbList.value = res.data || []
  } catch (e: any) {
    console.error('Error fetching databases:', e)
    message.error('获取数据库列表失败: ' + (e.response?.data?.detail || e.message))
  } finally { loading.value = false }
}

const fetchUsers = async () => {
  if (!props.host) return
  try {
    const res = await axios.post('/api/pgsql/users', props.host)
    userList.value = res.data || []
  } catch (e) {}
}

watch(showCreateModal, (val) => {
  if (val) fetchUsers()
})

const openEditModal = (row: any) => {
  editingDb.value = row
  editForm.owner = row.owner
  editForm.description = row.description || ''
  showEditModal.value = true
  fetchUsers()
}

const handleUpdate = async () => {
  if (!editingDb.value) return
  updating.value = true
  try {
    await axios({
      method: 'patch',
      url: `/api/pgsql/databases/${editingDb.value.name}`,
      data: {
        config: props.host,
        req: { owner: editForm.owner, description: editForm.description }
      }
    })
    message.success('更新成功')
    showEditModal.value = false
    fetchDatabases()
  } catch (e: any) {
    message.error('更新失败')
  } finally { updating.value = false }
}

const handleCreate = async () => {
  if (!newDbName.value) return
  creating.value = true
  try {
    await axios.post('/api/pgsql/databases/create', {
      config: props.host,
      req: { 
        dbname: newDbName.value,
        owner: newDbOwner.value
      }
    })
    message.success('创建成功')
    showCreateModal.value = false
    newDbName.value = ''
    newDbOwner.value = null
    fetchDatabases()
  } catch (e: any) {
    message.error('创建失败')
  } finally { creating.value = false }
}

const handleDrop = async (name: string) => {
  try {
    await axios.delete(`/api/pgsql/databases/${name}`, { data: props.host })
    message.success('已删除')
    fetchDatabases()
  } catch (e: any) {
    message.error('删除失败')
  }
}

watch(() => props.host, fetchDatabases, { immediate: true })
defineExpose({ refresh: fetchDatabases })
</script>

<style scoped>
.mobile-pgsql-database-panel {
  padding: 12px 0;
}

.empty-state {
  padding: 40px 0;
}

.database-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.database-item {
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.database-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.database-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
}

.database-info {
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
