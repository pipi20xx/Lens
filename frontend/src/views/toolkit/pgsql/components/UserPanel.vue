<template>
  <div class="user-panel">
    <!-- 工具栏 -->
    <div class="toolbar-row">
      <n-button type="primary" @click="showCreateModal = true">
        创建用户
      </n-button>
      <n-button @click="fetchUsers" :loading="loading">
        刷新
      </n-button>
    </div>

    <!-- 卡片列表 -->
    <n-spin :show="loading">
      <div v-if="userList.length" class="user-list">
        <div
          v-for="row in userList"
          :key="row.username"
          class="user-card"
          :class="{ 'is-super': row.is_superuser, 'is-login': row.can_login && !row.is_superuser }"
        >
          <!-- 卡片头部：用户名 + 登录状态 -->
          <div class="card-header">
            <div class="card-title">
              <n-text strong class="username text-truncate">{{ row.username }}</n-text>
              <n-tag v-if="row.is_superuser" type="error" size="tiny" quaternary>超级用户</n-tag>
            </div>
            <n-tag
              :type="row.can_login ? 'success' : 'default'"
              size="small"
              round
            >
              {{ row.can_login ? '可登录' : '不可登录' }}
            </n-tag>
          </div>

          <!-- 权限标签 -->
          <div class="card-perms" v-if="getPermTags(row).length">
            <n-tag
              v-for="perm in getPermTags(row)"
              :key="perm.label"
              :type="perm.type"
              size="tiny"
              quaternary
            >
              {{ perm.label }}
            </n-tag>
          </div>

          <!-- 连接限制 -->
          <div class="card-info" v-if="row.connection_limit !== undefined && row.connection_limit !== null">
            <span class="info-label">连接限制</span>
            <n-text depth="3" style="font-size: 12px">
              {{ row.connection_limit === -1 ? '无限制' : row.connection_limit }}
            </n-text>
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
              @click="handleDrop(row.username)"
            >
              删除
            </n-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <n-empty
        v-else-if="!loading"
        description="暂无用户"
        style="padding: 60px 0"
      />
    </n-spin>

    <!-- 创建模态框 -->
    <n-modal v-model:show="showCreateModal" preset="card" title="创建数据库用户/角色" style="width: 550px">
      <n-form label-placement="left" label-width="120">
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
        <n-grid :cols="2" :x-gap="12">
          <n-gi><n-checkbox v-model:checked="form.can_login">允许登录 (LOGIN)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="form.is_superuser">超级用户 (SUPERUSER)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="form.can_create_db">创建数据库 (CREATEDB)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="form.can_create_role">创建角色 (CREATEROLE)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="form.inherit">继承权限 (INHERIT)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="form.replication">流复制 (REPLICATION)</n-checkbox></n-gi>
          <n-gi :span="2"><n-checkbox v-model:checked="form.bypass_rls">绕过 RLS (BYPASSRLS)</n-checkbox></n-gi>
        </n-grid>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showCreateModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="handleCreate" :loading="creating">
            创建角色
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 编辑模态框 -->
    <n-modal v-model:show="showEditModal" preset="card" :title="`编辑数据库用户: ${editingUser?.username}`" style="width: 550px">
      <n-form label-placement="left" label-width="120">
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
        <n-grid :cols="2" :x-gap="12">
          <n-gi><n-checkbox v-model:checked="editForm.can_login">允许登录 (LOGIN)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="editForm.is_superuser">超级用户 (SUPERUSER)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="editForm.can_create_db">创建数据库 (CREATEDB)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="editForm.can_create_role">创建角色 (CREATEROLE)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="editForm.inherit">继承权限 (INHERIT)</n-checkbox></n-gi>
          <n-gi><n-checkbox v-model:checked="editForm.replication">流复制 (REPLICATION)</n-checkbox></n-gi>
          <n-gi :span="2"><n-checkbox v-model:checked="editForm.bypass_rls">绕过 RLS (BYPASSRLS)</n-checkbox></n-gi>
        </n-grid>
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
import { ref, watch, reactive } from 'vue'
import { NSpace, NButton, NModal, NForm, NFormItem, NInput, NCheckbox, NDatePicker, NInputNumber, NGrid, NGi, NDivider, NSpin, NEmpty, NText, NTag, useMessage, useDialog } from 'naive-ui'
import axios from 'axios'

const props = defineProps<{ host: any }>()
const message = useMessage()
const dialog = useDialog()

const userList = ref<any[]>([])
const loading = ref(false)

// 创建逻辑
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

// 编辑逻辑
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

// 辅助函数：获取权限标签
const getPermTags = (row: any) => {
  const tags: { label: string; type: string }[] = []
  if (row.is_superuser) tags.push({ label: 'SUPERUSER', type: 'error' })
  if (row.can_create_db) tags.push({ label: 'CREATEDB', type: 'info' })
  if (row.can_create_role) tags.push({ label: 'CREATEROLE', type: 'info' })
  if (row.replication) tags.push({ label: 'REPLICATION', type: 'warning' })
  if (row.bypass_rls) tags.push({ label: 'BYPASSRLS', type: 'warning' })
  if (row.inherit) tags.push({ label: 'INHERIT', type: 'default' })
  return tags
}

const fetchUsers = async () => {
  if (!props.host) return
  loading.value = true
  try {
    const res = await axios.post('/api/pgsql/users', props.host)
    userList.value = res.data
  } catch (e) {}
  finally { loading.value = false }
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
  } catch (e: any) { message.error('更新失败') }
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
    message.success('创建角色成功')
    showCreateModal.value = false
    Object.assign(form, { username: '', password: '', can_login: true, is_superuser: false, can_create_db: false, can_create_role: false, inherit: true, replication: false, bypass_rls: false, connection_limit: -1 })
    fetchUsers()
  } catch (e: any) { message.error('失败: ' + (e.response?.data?.detail || e.message)) }
  finally { creating.value = false }
}

const handleDrop = (username: string) => {
  dialog.warning({
    title: '删除角色',
    content: `确定要删除角色 "${username}" 吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/pgsql/users/${username}`, { data: props.host })
        message.success('已删除')
        fetchUsers()
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

watch(() => props.host, fetchUsers, { immediate: true })
defineExpose({ refresh: fetchUsers })
</script>

<style scoped>
.user-panel {
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
.user-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.user-card {
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

.user-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 3px;
  background: transparent;
  transition: background var(--transition-normal, 250ms ease);
}

.user-card.is-super::before {
  background: var(--color-error, #EF4444);
}

.user-card.is-login::before {
  background: var(--color-success, #10B981);
}

.user-card:hover {
  border-color: rgba(64, 128, 240, 0.75);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.user-card:active {
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

.username {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

/* 权限标签 */
.card-perms {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* 信息行 */
.card-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
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
