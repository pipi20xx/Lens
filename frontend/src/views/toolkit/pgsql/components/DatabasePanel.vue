<template>
  <div class="database-panel">
    <!-- 工具栏 -->
    <div class="toolbar-row">
      <n-button type="primary" @click="showCreateModal = true">
        创建数据库
      </n-button>
      <n-button @click="fetchDatabases" :loading="loading">
        刷新
      </n-button>
    </div>

    <!-- 卡片列表 -->
    <n-spin :show="loading">
      <div v-if="dbList.length" class="db-list">
        <div
          v-for="row in dbList"
          :key="row.name"
          class="db-card"
        >
          <!-- 卡片头部：库名 + 所有者 -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="db-name text-truncate">{{ row.name }}</n-text>
            </div>
            <n-tag size="small" quaternary type="info">{{ row.owner }}</n-tag>
          </div>

          <!-- 描述 -->
          <div class="card-desc" v-if="row.description">
            <n-text depth="3" class="desc-text text-clamp-2">{{ row.description }}</n-text>
          </div>
          <div class="card-desc" v-else>
            <n-text depth="3" style="font-size: 11px; opacity: 0.5">无描述</n-text>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <n-button
              size="small"
              type="info"
              secondary
              @click="openEditModal(row)"
            >
              编辑
            </n-button>
            <n-button
              size="small"
              type="error"
              secondary
              @click="handleDrop(row.name)"
            >
              删除
            </n-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-else-if="!loading"
        description="暂无数据库"
        style="padding: 60px 0"
      />
    </n-spin>

    <!-- 创建模态框 -->
    <n-modal v-model:show="showCreateModal" preset="card" title="创建数据库" style="width: 450px">
      <n-form label-placement="left" label-width="100">
        <n-form-item label="数据库名称">
          <n-input v-model:value="newDbName" placeholder="请输入库名" />
        </n-form-item>
        <n-form-item label="所有者">
          <n-select v-model:value="newDbOwner" :options="userOptions" placeholder="选择所有者 (可选)" clearable />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreateModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="handleCreate" :loading="creating">
            立即创建
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑模态框 -->
    <n-modal v-model:show="showEditModal" preset="card" :title="`编辑数据库: ${editingDb?.name}`" style="width: 500px">
      <n-form label-placement="left" label-width="100">
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
          <n-button @click="showEditModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="handleUpdate" :loading="updating">
            保存修改
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive, computed } from 'vue'
import { NSpace, NButton, NModal, NForm, NFormItem, NInput, NSelect, NSpin, NEmpty, NText, NTag, useMessage, useDialog } from 'naive-ui'
import request from '@/utils/request'

const props = defineProps<{ host: any }>()
const message = useMessage()
const dialog = useDialog()

const dbList = ref<any[]>([])
const userList = ref<any[]>([])
const loading = ref(false)

// 创建逻辑
const showCreateModal = ref(false)
const newDbName = ref('')
const newDbOwner = ref<string | null>(null)
const creating = ref(false)

// 监听创建弹窗打开，刷新用户列表
watch(showCreateModal, (val) => {
  if (val) fetchUsers()
})

// 编辑逻辑
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
    const res = await request.post('/api/pgsql/databases', props.host)
    dbList.value = (res as any) || []
  } catch (e) {}
  finally { loading.value = false }
}

const fetchUsers = async () => {
  if (!props.host) return
  try {
    const res = await request.post('/api/pgsql/users', props.host)
    userList.value = (res as any) || []
  } catch (e) {}
}

const openEditModal = (row: any) => {
  editingDb.value = row
  editForm.owner = row.owner
  editForm.description = row.description || ''
  showEditModal.value = true
  fetchUsers() // 弹出时同步刷新用户列表以供选择
}

const handleUpdate = async () => {
  if (!editingDb.value) return
  updating.value = true
  try {
    await request({
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
    // message.error 由 request.ts 处理
  } finally { updating.value = false }
}

const handleCreate = async () => {
  if (!newDbName.value) return
  creating.value = true
  try {
    await request.post('/api/pgsql/databases/create', {
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
    //
  } finally { creating.value = false }
}

const handleDrop = (name: string) => {
  dialog.error({
    title: '危险操作',
    content: `确定要永久删除数据库 "${name}" 吗？系统将强制终止活跃连接。`,
    positiveText: '确认删除',
    onPositiveClick: async () => {
      try {
        await request.delete(`/api/pgsql/databases/${name}`, { data: props.host })
        message.success('已删除')
        fetchDatabases()
      } catch (e: any) {
        //
      }
    }
  })
}

watch(() => props.host, fetchDatabases, { immediate: true })
defineExpose({ refresh: fetchDatabases })
</script>

<style scoped>
.database-panel {
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

/* 卡片列表：一行一个卡片 */
.db-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.db-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  background: var(--card-bg-color, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
  transition: border-color var(--transition-normal, 250ms ease), box-shadow var(--transition-normal, 250ms ease), transform var(--transition-fast, 150ms ease);
  position: relative;
  overflow: hidden;
}

.db-card:hover {
  border-color: var(--border-medium, rgba(255, 255, 255, 0.12));
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.db-card:active {
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

.db-name {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

/* 描述 */
.card-desc {
  min-width: 0;
}

.desc-text {
  font-size: 12px;
  line-height: 1.5;
  word-break: break-all;
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
