<template>
  <div class="mobile-pgsql-user-panel">
    <n-space vertical>
      <n-space justify="space-between" align="center">
        <n-button type="primary" size="small" @click="showCreateModal = true">
          创建用户
        </n-button>
        <n-button size="small" secondary @click="fetchUsers" :loading="loading">
          刷新
        </n-button>
      </n-space>

      <div v-if="userList.length === 0" class="empty-state">
        <n-empty description="暂无用户" size="small" />
      </div>

      <div v-else class="user-list">
        <div v-for="user in userList" :key="user.username" class="user-item">
          <div class="user-header">
            <div class="user-name">{{ user.username }}</div>
            <n-space>
              <n-button size="tiny" secondary type="info" @click="openEditModal(user)">
                编辑
              </n-button>
              <n-popconfirm @positive-click="() => handleDrop(user.username)" positive-text="确认" negative-text="取消">
                <template #trigger>
                  <n-button size="tiny" secondary type="error">
                    删除
                  </n-button>
                </template>
                确认删除？
              </n-popconfirm>
            </n-space>
          </div>
          <div class="user-info">
            <div class="info-row">
              <span>允许登录: {{ user.can_login ? '是' : '否' }}</span>
            </div>
            <div v-if="user.is_superuser" class="info-row">
              <span>超级用户</span>
            </div>
            <div v-if="user.can_create_db" class="info-row">
              <span>可创建数据库</span>
            </div>
          </div>
        </div>
      </div>
    </n-space>

    <n-modal v-model:show="showCreateModal" preset="card" title="创建数据库用户/角色" style="width: 90vw; max-width: 450px">
      <n-form label-placement="top" size="small">
        <n-form-item label="用户名/角色名">
          <n-input v-model:value="form.username" placeholder="请输入名称" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="form.password" type="password" placeholder="请输入密码" />
        </n-form-item>
        <n-form-item label="连接限制">
          <n-input-number v-model:value="form.connection_limit" :min="-1" style="width: 100%" />
          <template #feedback>输入 -1 表示无限制</template>
        </n-form-item>
        <n-divider title-placement="left">权限设置</n-divider>
        <n-space vertical>
          <n-checkbox v-model:checked="form.can_login">允许登录 (LOGIN)</n-checkbox>
          <n-checkbox v-model:checked="form.is_superuser">超级用户 (SUPERUSER)</n-checkbox>
          <n-checkbox v-model:checked="form.can_create_db">创建数据库 (CREATEDB)</n-checkbox>
          <n-checkbox v-model:checked="form.can_create_role">创建角色 (CREATEROLE)</n-checkbox>
          <n-checkbox v-model:checked="form.inherit">继承权限 (INHERIT)</n-checkbox>
          <n-checkbox v-model:checked="form.replication">流复制 (REPLICATION)</n-checkbox>
          <n-checkbox v-model:checked="form.bypass_rls">绕过 RLS (BYPASSRLS)</n-checkbox>
        </n-space>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button secondary @click="showCreateModal = false">取消</n-button>
          <n-button type="primary" @click="handleCreate" :loading="creating">创建</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showEditModal" preset="card" :title="`编辑用户: ${editingUser?.username}`" style="width: 90vw; max-width: 450px">
      <n-form label-placement="top" size="small">
        <n-form-item label="重置密码">
          <n-input v-model:value="editForm.password" type="password" placeholder="留空则不修改" />
        </n-form-item>
        <n-form-item label="到期时间">
          <n-date-picker v-model:formatted-value="editForm.valid_until" value-format="yyyy-MM-dd HH:mm:ss" type="datetime" clearable style="width: 100%" />
        </n-form-item>
        <n-form-item label="连接限制">
          <n-input-number v-model:value="editForm.connection_limit" :min="-1" style="width: 100%" />
        </n-form-item>
        <n-divider title-placement="left">权限设置</n-divider>
        <n-space vertical>
          <n-checkbox v-model:checked="editForm.can_login">允许登录 (LOGIN)</n-checkbox>
          <n-checkbox v-model:checked="editForm.is_superuser">超级用户 (SUPERUSER)</n-checkbox>
          <n-checkbox v-model:checked="editForm.can_create_db">创建数据库 (CREATEDB)</n-checkbox>
          <n-checkbox v-model:checked="editForm.can_create_role">创建角色 (CREATEROLE)</n-checkbox>
          <n-checkbox v-model:checked="editForm.inherit">继承权限 (INHERIT)</n-checkbox>
          <n-checkbox v-model:checked="editForm.replication">流复制 (REPLICATION)</n-checkbox>
          <n-checkbox v-model:checked="editForm.bypass_rls">绕过 RLS (BYPASSRLS)</n-checkbox>
        </n-space>
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
import { ref, watch, reactive } from 'vue'
import { NSpace, NButton, NModal, NForm, NFormItem, NInput, NCheckbox, NDatePicker, NInputNumber, NDivider, NEmpty, NPopconfirm, useMessage, useDialog } from 'naive-ui'
import axios from 'axios'

const props = defineProps<{ host: any }>()
const message = useMessage()
const dialog = useDialog()

const userList = ref<any[]>([])
const loading = ref(false)

const creating = ref(false)
const showCreateModal = ref(false)
const form = reactive({
  username: '',
  password: '',
  can_login: true,
  is_superuser: false,
  can_create_db: false,
  can_create_role: false,
  inherit: true,
  replication: false,
  bypass_rls: false,
  connection_limit: -1
})

const showEditModal = ref(false)
const updating = ref(false)
const editingUser = ref<any>(null)
const editForm = reactive({
  password: '',
  can_login: true,
  is_superuser: false,
  can_create_db: false,
  can_create_role: false,
  inherit: true,
  replication: false,
  bypass_rls: false,
  connection_limit: -1,
  valid_until: null as string | null
})

const fetchUsers = async () => {
  if (!props.host) return
  loading.value = true
  try {
    console.log('Fetching users with host:', props.host)
    const res = await axios.post('/api/pgsql/users', props.host)
    console.log('Users response:', res.data)
    userList.value = res.data
  } catch (e: any) {
    console.error('Error fetching users:', e)
    message.error('获取用户列表失败: ' + (e.response?.data?.detail || e.message))
  } finally { loading.value = false }
}

const openEditModal = (row: any) => {
  editingUser.value = row
  editForm.password = ''
  editForm.can_login = row.can_login
  editForm.is_superuser = row.is_superuser
  editForm.can_create_db = row.can_create_db
  editForm.can_create_role = row.can_create_role
  editForm.inherit = row.inherit
  editForm.replication = row.replication
  editForm.bypass_rls = row.bypass_rls
  editForm.connection_limit = row.connection_limit
  editForm.valid_until = row.valid_until
  showEditModal.value = true
}

const handleUpdate = async () => {
  if (!editingUser.value) return
  updating.value = true
  try {
    await axios({
      method: 'patch',
      url: `/api/pgsql/users/${editingUser.value.username}`,
      data: {
        config: props.host,
        req: { ...editForm, password: editForm.password || null }
      }
    })
    message.success('更新成功')
    showEditModal.value = false
    fetchUsers()
  } catch (e: any) { 
    message.error('更新失败') 
  }
  finally { updating.value = false }
}

const handleCreate = async () => {
  if (!form.username) return
  creating.value = true
  try {
    await axios.post('/api/pgsql/users/create', {
      config: props.host,
      req: form
    })
    message.success('创建成功')
    showCreateModal.value = false
    Object.assign(form, { username: '', password: '', can_login: true, is_superuser: false, can_create_db: false, can_create_role: false, inherit: true, replication: false, bypass_rls: false, connection_limit: -1 })
    fetchUsers()
  } catch (e: any) { 
    message.error('创建失败') 
  }
  finally { creating.value = false }
}

const handleDrop = async (username: string) => {
  try {
    await axios.delete(`/api/pgsql/users/${username}`, { data: props.host })
    message.success('已删除')
    fetchUsers()
  } catch (e) {
    message.error('删除失败')
  }
}

watch(() => props.host, fetchUsers, { immediate: true })
defineExpose({ refresh: fetchUsers })
</script>

<style scoped>
.mobile-pgsql-user-panel {
  padding: 12px 0;
}

.empty-state {
  padding: 40px 0;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-item {
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.user-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.user-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
}

.user-info {
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
