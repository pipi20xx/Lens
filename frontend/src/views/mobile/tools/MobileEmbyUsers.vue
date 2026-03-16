<template>
  <div class="mobile-emby-users">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">Emby 用户管理</h1>
      <p class="page-desc">管理您的 Emby 服务器用户、权限策略及密码</p>
    </div>

    <!-- 高危警告 -->
    <n-alert title="高危操作警告" type="error" :bordered="false" class="warning-alert">
      本模块功能涉及 Emby 数据库底层权限策略的强制写入。<strong>非必要请勿使用！</strong>
    </n-alert>

    <!-- 操作按钮 -->
    <n-card class="action-card" :bordered="false">
      <n-space vertical>
        <n-button block type="primary" secondary :loading="loading" @click="loadUsers">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          刷新用户列表
        </n-button>
        <n-button block type="warning" secondary :loading="backingUpAll" @click="handleBackupAll">
          <template #icon><n-icon><BackupIcon /></n-icon></template>
          一键备份所有用户
        </n-button>
        <MobileEmbyConfigBackupManager category="users" :server-id="activeServerId" @restored="loadUsers" />
      </n-space>
    </n-card>

    <!-- 新增用户 -->
    <n-card class="add-card" :bordered="false" title="新增用户">
      <n-space>
        <n-input v-model:value="newUserName" placeholder="新用户名" @keyup.enter="handleCreateUser" />
        <n-button type="primary" :loading="creating" @click="handleCreateUser">
          <template #icon><n-icon><UserAddIcon /></n-icon></template>
          创建
        </n-button>
      </n-space>
    </n-card>

    <!-- 用户列表 -->
    <n-card class="users-card" :bordered="false" title="用户列表">
      <div v-if="users.length === 0" class="empty-state">
        <n-empty description="暂无用户" />
      </div>
      <div v-else class="user-list">
        <div v-for="user in users" :key="user.Id" class="user-item">
          <div class="user-info">
            <div class="user-name">{{ user.Name }}</div>
            <div class="user-tags">
              <n-tag v-if="user.Policy?.IsDisabled" type="error" size="tiny" round>禁用</n-tag>
              <n-tag v-if="user.Policy?.IsAdministrator" type="warning" size="tiny" round>管理员</n-tag>
              <n-tag v-if="user.Policy?.IsHidden" type="default" size="tiny" round>隐藏</n-tag>
              <n-tag v-if="!user.Policy?.IsDisabled && !user.Policy?.IsAdministrator" type="success" size="tiny" round>正常</n-tag>
            </div>
          </div>
          <div class="user-actions">
            <n-button size="small" secondary type="info" @click="openEdit(user)">
              <template #icon><n-icon><EditIcon /></n-icon></template>
              设置
            </n-button>
            <n-button size="small" secondary type="warning" @click="handleDirectBackup(user)">
              <template #icon><n-icon><BackupIcon /></n-icon></template>
              备份
            </n-button>
            <n-popconfirm @positive-click="handleDeleteUser(user.Id)" positive-text="确认删除" negative-text="取消">
              <template #trigger>
                <n-button size="small" secondary type="error">
                  <template #icon><n-icon><DeleteIcon /></n-icon></template>
                  删除
                </n-button>
              </template>
              确定删除用户 {{ user.Name }}？
            </n-popconfirm>
          </div>
        </div>
      </div>
    </n-card>

    <!-- 用户设置模态框 -->
    <n-modal v-model:show="showEditModal" preset="card" :title="'设置: ' + editingUser?.Name" style="width: 95vw; max-width: 600px">
      <n-tabs type="segment" size="small">
        <n-tab-pane name="account" tab="账户">
          <n-space vertical class="settings-section">
            <div class="setting-item">
              <span class="setting-label">禁用此账户</span>
              <n-switch v-model:value="policy.IsDisabled" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">管理员权限</span>
              <n-switch v-model:value="policy.IsAdministrator" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">在登录界面隐藏</span>
              <n-switch v-model:value="policy.IsHidden" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">在远程访问时隐藏</span>
              <n-switch v-model:value="policy.IsHiddenRemotely" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许远程访问</span>
              <n-switch v-model:value="policy.EnableRemoteAccess" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">同时播放限制</span>
              <n-input-number v-model:value="policy.SimultaneousStreamLimit" :min="0" size="small" style="width: 100px" />
            </div>
            <div class="setting-item">
              <span class="setting-label">远程客户端比特率限制</span>
              <n-input-number v-model:value="policy.RemoteClientBitrateLimit" :min="0" :step="1000000" size="small" style="width: 150px" />
            </div>
          </n-space>
        </n-tab-pane>
        <n-tab-pane name="playback" tab="播放">
          <n-space vertical class="settings-section">
            <div class="setting-item">
              <span class="setting-label">允许媒体播放</span>
              <n-switch v-model:value="policy.EnableMediaPlayback" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许音频转码</span>
              <n-switch v-model:value="policy.EnableAudioPlaybackTranscoding" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许视频转码</span>
              <n-switch v-model:value="policy.EnableVideoPlaybackTranscoding" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许播放封装转换</span>
              <n-switch v-model:value="policy.EnablePlaybackRemuxing" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许媒体转换</span>
              <n-switch v-model:value="policy.EnableMediaConversion" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许同步转码</span>
              <n-switch v-model:value="policy.EnableSyncTranscoding" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">自动远程质量</span>
              <n-input-number v-model:value="policy.AutoRemoteQuality" :min="0" size="small" style="width: 100px" />
            </div>
          </n-space>
        </n-tab-pane>
        <n-tab-pane name="features" tab="功能">
          <n-space vertical class="settings-section">
            <div class="setting-item">
              <span class="setting-label">允许删除媒体</span>
              <n-switch v-model:value="policy.EnableContentDeletion" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许下载媒体</span>
              <n-switch v-model:value="policy.EnableContentDownloading" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许下载字幕</span>
              <n-switch v-model:value="policy.EnableSubtitleDownloading" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许管理字幕</span>
              <n-switch v-model:value="policy.EnableSubtitleManagement" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许公开分享</span>
              <n-switch v-model:value="policy.EnablePublicSharing" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许远程控制其他用户</span>
              <n-switch v-model:value="policy.EnableRemoteControlOfOtherUsers" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许控制共享设备</span>
              <n-switch v-model:value="policy.EnableSharedDeviceControl" class="mobile-switch" />
            </div>
          </n-space>
        </n-tab-pane>
        <n-tab-pane name="library" tab="媒体库">
          <n-space vertical class="settings-section">
            <div class="setting-item">
              <span class="setting-label">允许访问所有媒体库</span>
              <n-switch v-model:value="policy.EnableAllFolders" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许访问所有频道</span>
              <n-switch v-model:value="policy.EnableAllChannels" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许在所有设备上登录</span>
              <n-switch v-model:value="policy.EnableAllDevices" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许观看直播电视</span>
              <n-switch v-model:value="policy.EnableLiveTvAccess" class="mobile-switch" />
            </div>
            <div class="setting-item">
              <span class="setting-label">允许管理直播电视</span>
              <n-switch v-model:value="policy.EnableLiveTvManagement" class="mobile-switch" />
            </div>
          </n-space>
        </n-tab-pane>
        <n-tab-pane name="password" tab="密码">
          <n-space vertical class="settings-section">
            <n-input v-model:value="newPassword" type="password" show-password-on="click" placeholder="输入新密码" />
            <n-button type="warning" secondary block :disabled="!newPassword" @click="handleUpdatePassword">
              <template #icon><n-icon><EditIcon /></n-icon></template>
              更新密码
            </n-button>
          </n-space>
        </n-tab-pane>
        <n-tab-pane name="json" tab="JSON">
          <n-space vertical>
            <n-alert type="info" size="small">
              高级操作：您可以直接编辑下方的原始 JSON 数据。请确保格式正确，非法 JSON 将无法保存。
            </n-alert>
            <n-input
              v-model:value="jsonRaw"
              type="textarea"
              :autosize="{ minRows: 10, maxRows: 20 }"
              placeholder="请输入有效的 Policy JSON"
              style="font-family: monospace; font-size: 12px"
              @update:value="handleJsonInput"
            />
          </n-space>
        </n-tab-pane>
      </n-tabs>
      <template #action>
        <n-space vertical style="width: 100%">
          <n-space justify="end">
            <n-button strong secondary @click="showEditModal = false">取消</n-button>
            <n-button type="warning" secondary strong @click="handleBackup" :loading="backingUp">
              <template #icon><n-icon><BackupIcon /></n-icon></template>
              备份当前配置
            </n-button>
            <n-button type="primary" strong secondary :loading="savingPolicy" @click="handleSavePolicy">
              <template #icon><n-icon><SaveIcon /></n-icon></template>
              保存设置
            </n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  NButton, NSpace, NTag, NPopconfirm, useMessage, NIcon, 
  NInput, NCard, NModal, NTabs, NTabPane, NSwitch, 
  NInputNumber, NAlert, NEmpty 
} from 'naive-ui'
import { 
  listEmbyUsers, 
  createEmbyUser, 
  deleteEmbyUser, 
  getEmbyUserInfo, 
  updateEmbyUserPolicy,
  updateEmbyUserPassword
} from '@/api/embyUsers'
import { createEmbyBackup, createAllEmbyBackups } from '@/api/embyBackup'
import { servers, activeServerId, fetchServers } from '@/store/serverStore'
import MobileEmbyConfigBackupManager from './MobileEmbyConfigBackupManager.vue'
import { 
  RefreshOutlined as RefreshIcon,
  BackupOutlined as BackupIcon,
  SettingsOutlined as EditIcon,
  DeleteOutlined as DeleteIcon,
  PersonAddOutlined as UserAddIcon,
  SaveOutlined as SaveIcon
} from '@vicons/material'

const message = useMessage()
const loading = ref(false)
const creating = ref(false)
const backingUp = ref(false)
const backingUpAll = ref(false)
const users = ref<any[]>([])
const newUserName = ref('')

const showEditModal = ref(false)
const editingUser = ref<any>(null)
const policy = ref<any>({})
const jsonRaw = ref('')
const newPassword = ref('')
const savingPolicy = ref(false)

const loadUsers = async () => {
  if (!activeServerId.value) {
    await fetchServers()
  }
  if (!activeServerId.value) {
    message.error('请先配置 Emby 服务器')
    return
  }
  loading.value = true
  try {
    const res = await listEmbyUsers(activeServerId.value)
    users.value = res as any || []
  } catch (e: any) {
    message.error(e.response?.data?.detail || '加载用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleCreateUser = async () => {
  if (!newUserName.value.trim()) {
    message.warning('请输入用户名')
    return
  }
  creating.value = true
  try {
    await createEmbyUser(newUserName.value.trim(), activeServerId.value)
    message.success('用户创建成功')
    newUserName.value = ''
    await loadUsers()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建用户失败')
  } finally {
    creating.value = false
  }
}

const handleDeleteUser = async (userId: string) => {
  try {
    await deleteEmbyUser(userId, activeServerId.value)
    message.success('用户已删除')
    await loadUsers()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除用户失败')
  }
}

const openEdit = async (user: any) => {
  editingUser.value = user
  newPassword.value = ''
  try {
    const info = await getEmbyUserInfo(user.Id, activeServerId.value) as any
    policy.value = info.Policy || {}
    jsonRaw.value = JSON.stringify(policy.value, null, 2)
    showEditModal.value = true
  } catch (e: any) {
    message.error(e.response?.data?.detail || '获取用户信息失败')
  }
}

const handleJsonInput = (value: string) => {
  try {
    const parsed = JSON.parse(value)
    policy.value = parsed
  } catch (e) { }
}

const handleSavePolicy = async () => {
  if (!editingUser.value) return
  try {
    policy.value = JSON.parse(jsonRaw.value)
  } catch (e) {
    message.error('JSON 格式非法，请检查后再试')
    return
  }
  savingPolicy.value = true
  try {
    await updateEmbyUserPolicy(editingUser.value.Id, policy.value, activeServerId.value)
    message.success('用户策略已更新')
    await loadUsers()
    showEditModal.value = false
  } catch (e: any) {
    message.error(e.response?.data?.detail || '更新策略失败')
  } finally {
    savingPolicy.value = false
  }
}

const handleUpdatePassword = async () => {
  if (!editingUser.value || !newPassword.value) return
  try {
    await updateEmbyUserPassword(editingUser.value.Id, newPassword.value, activeServerId.value)
    message.success('密码已更新')
    newPassword.value = ''
  } catch (e: any) {
    message.error(e.response?.data?.detail || '更新密码失败')
  }
}

const handleDirectBackup = async (user: any) => {
  backingUp.value = true
  try {
    await createEmbyBackup('users', user.Id, activeServerId.value)
    message.success(`用户 ${user.Name} 已备份`)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '备份失败')
  } finally {
    backingUp.value = false
  }
}

const handleBackup = async () => {
  if (!editingUser.value) return
  backingUp.value = true
  try {
    await createEmbyBackup('users', editingUser.value.Id, activeServerId.value)
    message.success('当前配置已备份')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '备份失败')
  } finally {
    backingUp.value = false
  }
}

const handleBackupAll = async () => {
  backingUpAll.value = true
  try {
    await createAllEmbyBackups('users', activeServerId.value)
    message.success('所有用户已备份')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '备份失败')
  } finally {
    backingUpAll.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.mobile-emby-users {
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

.warning-alert {
  margin-bottom: 12px;
}

.action-card,
.add-card,
.users-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.user-info {
  margin-bottom: 8px;
}

.user-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.user-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.user-actions {
  display: flex;
  gap: 8px;
}

.settings-section {
  padding: 16px 0;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  font-size: 14px;
  color: var(--text-color);
}
</style>
