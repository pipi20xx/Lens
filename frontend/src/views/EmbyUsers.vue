<template>
  <div class="emby-users-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">Emby 用户管理</n-text></n-h2>
        <n-text depth="3">管理您的 Emby 服务器用户、权限策略及密码。</n-text>
      </div>

      <n-alert title="高危操作警告" type="error" bordered>
        <template #icon>⚠️</template>
        本模块功能涉及 Emby 数据库底层权限策略的强制写入。<strong>非必要请勿使用！</strong><br/>
        建议仅在<strong>新建/初始化 Emby 服务器</strong>时用于快速迁移配置。误操作可能导致 Emby 用户数据库损坏或权限丢失，由此产生的后果请自行承担。
      </n-alert>

      <n-card size="small" segmented :bordered="false" class="main-card">
        <template #header>
          <n-space align="center">
            <n-button
              strong
              secondary
              type="primary"
              size="small"
              @click="loadUsers"
              :loading="loading"
            >
              刷新用户列表
            </n-button>
            <n-button
              strong
              secondary
              type="warning"
              size="small"
              @click="handleBackupAll"
              :loading="backingUpAll"
            >
              一键备份所有用户
            </n-button>
            <EmbyConfigBackupManager category="users" :server-id="activeServerId" @restored="loadUsers" />
          </n-space>
        </template>
        <template #header-extra>
          <n-input-group>
            <n-input v-model:value="newUserName" placeholder="新用户名" size="small" @keyup.enter="handleCreateUser" style="width: 150px" />
            <n-button type="primary" size="small" @click="handleCreateUser" :loading="creating">
              新增用户
            </n-button>
          </n-input-group>
        </template>

        <!-- 用户卡片列表：一行一个 -->
        <n-spin :show="loading">
          <div v-if="users.length" class="user-list">
            <div
              v-for="row in users"
              :key="row.Id"
              class="user-card"
            >
              <!-- 卡片头部：用户名 + 状态标签 -->
              <div class="card-header">
                <div class="card-title">
                  <n-text strong class="user-name text-truncate">{{ row.Name }}</n-text>
                </div>
                <n-space :size="4" class="card-tags">
                  <n-tag v-if="row.Policy?.IsDisabled" type="error" size="small" round quaternary>禁用</n-tag>
                  <n-tag v-if="row.Policy?.IsAdministrator" type="warning" size="small" round quaternary>管理员</n-tag>
                  <n-tag v-if="row.Policy?.IsHidden" type="default" size="small" round quaternary>隐藏</n-tag>
                  <n-tag
                    v-if="!row.Policy?.IsDisabled && !row.Policy?.IsAdministrator && !row.Policy?.IsHidden"
                    type="success"
                    size="small"
                    round
                    quaternary
                  >正常</n-tag>
                </n-space>
              </div>

              <!-- 用户 ID -->
              <div class="card-desc">
                <n-text depth="3" class="desc-text">
                  ID: <code class="user-id-code">{{ row.Id }}</code>
                </n-text>
              </div>

              <!-- 操作按钮 -->
              <div class="card-actions">
                <n-button
                  size="small"
                  type="info"
                  secondary
                  strong
                  @click="openEdit(row)"
                >
                  设置
                </n-button>
                <n-button
                  size="small"
                  type="warning"
                  secondary
                  strong
                  @click="handleDirectBackup(row)"
                >
                  备份
                </n-button>
                <n-popconfirm
                  @positive-click="handleDeleteUser(row.Id)"
                  positive-text="确认删除"
                  negative-text="取消"
                >
                  <template #trigger>
                    <n-button
                      size="small"
                      type="error"
                      secondary
                      strong
                    >
                      删除
                    </n-button>
                  </template>
                  确定删除用户 {{ row.Name }}？
                </n-popconfirm>
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
      </n-card>
    </n-space>

    <!-- 用户设置模态框 -->
    <n-modal
      v-model:show="showEditModal"
      preset="card"
      :title="'设置: ' + editingUser?.Name"
      style="width: 800px"
      :bordered="false"
      segmented
    >
      <n-tabs type="line" animated>
        <n-tab-pane name="account" tab="账户与访问">
          <n-form label-placement="left" label-width="260" size="small">
            <n-form-item label="禁用此账户 (IsDisabled)">
              <n-switch v-model:value="policy.IsDisabled" />
            </n-form-item>
            <n-form-item label="管理员权限 (IsAdministrator)">
              <n-switch v-model:value="policy.IsAdministrator" />
            </n-form-item>
            <n-form-item label="在登录界面隐藏该用户 (IsHidden)">
              <n-switch v-model:value="policy.IsHidden" />
            </n-form-item>
            <n-form-item label="远程访问时隐藏 (IsHiddenRemotely)">
              <n-switch v-model:value="policy.IsHiddenRemotely" />
            </n-form-item>
            <n-form-item label="从不使用的设备中隐藏 (IsHiddenFromUnusedDevices)">
              <n-switch v-model:value="policy.IsHiddenFromUnusedDevices" />
            </n-form-item>
            <n-form-item label="允许远程访问 (EnableRemoteAccess)">
              <n-switch v-model:value="policy.EnableRemoteAccess" />
            </n-form-item>
            <n-form-item label="同时播放数量限制 (SimultaneousStreamLimit)">
              <n-input-number v-model:value="policy.SimultaneousStreamLimit" :min="0" />
              <template #feedback>0 为无限制</template>
            </n-form-item>
            <n-form-item label="远程客户端比特率限制 (RemoteClientBitrateLimit)">
              <n-input-number v-model:value="policy.RemoteClientBitrateLimit" :min="0" :step="1000000" />
              <template #feedback>单位: bps (0 为无限制)</template>
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <n-tab-pane name="playback" tab="播放与转码">
          <n-form label-placement="left" label-width="260" size="small">
            <n-form-item label="允许媒体播放 (EnableMediaPlayback)">
              <n-switch v-model:value="policy.EnableMediaPlayback" />
            </n-form-item>
            <n-form-item label="允许音频转码 (EnableAudioPlaybackTranscoding)">
              <n-switch v-model:value="policy.EnableAudioPlaybackTranscoding" />
            </n-form-item>
            <n-form-item label="允许视频转码 (EnableVideoPlaybackTranscoding)">
              <n-switch v-model:value="policy.EnableVideoPlaybackTranscoding" />
            </n-form-item>
            <n-form-item label="允许播放封装转换 (EnablePlaybackRemuxing)">
              <n-switch v-model:value="policy.EnablePlaybackRemuxing" />
            </n-form-item>
            <n-form-item label="允许媒体转换 (EnableMediaConversion)">
              <n-switch v-model:value="policy.EnableMediaConversion" />
            </n-form-item>
            <n-form-item label="允许同步转码 (EnableSyncTranscoding)">
              <n-switch v-model:value="policy.EnableSyncTranscoding" />
            </n-form-item>
            <n-form-item label="自动远程质量 (AutoRemoteQuality)">
              <n-input-number v-model:value="policy.AutoRemoteQuality" :min="0" />
              <template #feedback>单位: Mbps</template>
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <n-tab-pane name="features" tab="功能权限">
          <n-form label-placement="left" label-width="260" size="small">
            <n-divider title-placement="left">文件与下载</n-divider>
            <n-form-item label="允许删除媒体 (EnableContentDeletion)">
              <n-switch v-model:value="policy.EnableContentDeletion" />
            </n-form-item>
            <n-form-item label="允许下载媒体 (EnableContentDownloading)">
              <n-switch v-model:value="policy.EnableContentDownloading" />
            </n-form-item>
            <n-form-item label="允许下载字幕 (EnableSubtitleDownloading)">
              <n-switch v-model:value="policy.EnableSubtitleDownloading" />
            </n-form-item>
            <n-form-item label="允许管理字幕 (EnableSubtitleManagement)">
              <n-switch v-model:value="policy.EnableSubtitleManagement" />
            </n-form-item>
            <n-form-item label="允许相机上传 (AllowCameraUpload)">
              <n-switch v-model:value="policy.AllowCameraUpload" />
            </n-form-item>

            <n-divider title-placement="left">社交与远程控制</n-divider>
            <n-form-item label="允许公开分享内容 (EnablePublicSharing)">
              <n-switch v-model:value="policy.EnablePublicSharing" />
            </n-form-item>
            <n-form-item label="允许远程控制其他用户 (EnableRemoteControlOfOtherUsers)">
              <n-switch v-model:value="policy.EnableRemoteControlOfOtherUsers" />
            </n-form-item>
            <n-form-item label="允许控制共享设备 (EnableSharedDeviceControl)">
              <n-switch v-model:value="policy.EnableSharedDeviceControl" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <n-tab-pane name="library" tab="媒体库范围">
          <n-form label-placement="left" label-width="260" size="small">
            <n-divider title-placement="left">访问范围</n-divider>
            <n-form-item label="允许访问所有媒体库 (EnableAllFolders)">
              <n-switch v-model:value="policy.EnableAllFolders" />
            </n-form-item>
            <n-form-item label="允许访问所有频道 (EnableAllChannels)">
              <n-switch v-model:value="policy.EnableAllChannels" />
            </n-form-item>
            <n-form-item label="允许在所有设备上登录 (EnableAllDevices)">
              <n-switch v-model:value="policy.EnableAllDevices" />
            </n-form-item>
            
            <n-divider title-placement="left">直播电视</n-divider>
            <n-form-item label="允许观看直播电视 (EnableLiveTvAccess)">
              <n-switch v-model:value="policy.EnableLiveTvAccess" />
            </n-form-item>
            <n-form-item label="允许管理直播电视 (EnableLiveTvManagement)">
              <n-switch v-model:value="policy.EnableLiveTvManagement" />
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <n-tab-pane name="password" tab="修改密码">
          <n-form label-placement="left" label-width="100" size="small">
            <n-form-item label="新密码">
              <n-input v-model:value="newPassword" type="password" show-password-on="click" placeholder="留空则不修改" />
            </n-form-item>
            <n-form-item>
              <n-button type="warning" secondary strong @click="handleUpdatePassword" :disabled="!newPassword">
                单独更新密码
              </n-button>
            </n-form-item>
          </n-form>
        </n-tab-pane>

        <n-tab-pane name="json" tab="原始数据 (JSON)">
          <n-space vertical>
            <n-alert type="info" size="small">
              高级操作：您可以直接编辑下方的原始 JSON 数据。请确保格式正确，非法 JSON 将无法保存。
            </n-alert>
            <n-input
              v-model:value="jsonRaw"
              type="textarea"
              :autosize="{ minRows: 15, maxRows: 25 }"
              placeholder="请输入有效的 Policy JSON"
              style="font-family: monospace"
              @update:value="handleJsonInput"
            />
          </n-space>
        </n-tab-pane>
      </n-tabs>

      <template #action>
        <n-space justify="end">
          <n-button strong secondary @click="showEditModal = false">
            取消
          </n-button>
          <n-button type="warning" secondary strong @click="handleBackup" :loading="backingUp">
            备份当前配置
          </n-button>
          <n-button type="primary" strong @click="handleSavePolicy" :loading="savingPolicy">
            保存设置
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NSpace, NTag, NPopconfirm, useMessage, NInput, NInputGroup, NCard, NModal, NTabs, NTabPane, NForm, NFormItem, NSwitch, NInputNumber, NDivider, NAlert, NText, NSpin, NEmpty } from 'naive-ui'
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
import EmbyConfigBackupManager from '@/components/EmbyConfigBackupManager.vue'

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

const handleJsonInput = (value: string) => {
  try {
    const parsed = JSON.parse(value)
    policy.value = parsed
  } catch (e) { }
}

const handleDeleteUser = async (id: string) => {
  try {
    await deleteEmbyUser(id, activeServerId.value)
    message.success('删除成功')
    loadUsers()
  } catch (e) {
    console.error(e)
  }
}

const loadUsers = async () => {
  if (!activeServerId.value) return
  loading.value = true
  try {
    const res = await listEmbyUsers(activeServerId.value)
    users.value = res as any
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const handleCreateUser = async () => {
  if (!newUserName.value) return
  creating.value = true
  try {
    await createEmbyUser(newUserName.value, activeServerId.value)
    message.success('创建成功')
    newUserName.value = ''
    loadUsers()
  } catch (e) {
    console.error(e)
  } finally {
    creating.value = false
  }
}

const handleBackupAll = async () => {
  backingUpAll.value = true
  try {
    const res: any = await createAllEmbyBackups('users', activeServerId.value)
    message.success(`成功备份 ${res.count} 个用户配置`)
  } catch (e) {
    console.error(e)
  } finally {
    backingUpAll.value = false
  }
}

const handleDirectBackup = async (user: any) => {
  try {
    await createEmbyBackup('users', user.Id, user.Name, activeServerId.value)
    message.success(`用户 ${user.Name} 备份成功`)
  } catch (e) {
    console.error(e)
  }
}

const handleBackup = async () => {
  if (!editingUser.value) return
  backingUp.value = true
  try {
    await createEmbyBackup('users', editingUser.value.Id, editingUser.value.Name, activeServerId.value)
    message.success('当前配置已备份')
  } catch (e) {
    console.error(e)
  } finally {
    backingUp.value = false
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
  } catch (e) {
    console.error(e)
  }
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
    message.success('设置已保存')
    showEditModal.value = false
    loadUsers()
  } catch (e) {
    console.error(e)
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
  } catch (e) {
    console.error(e)
  }
}

onMounted(async () => {
  if (!servers.value.length) {
    await fetchServers()
  }
  loadUsers()
})
</script>

<style scoped>
.emby-users-container { padding: 10px; }
.page-header { margin-bottom: 20px; }
.main-card { margin-top: 12px; }

/* 卡片列表：一行一个卡片 */
.user-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
  margin-top: 4px;
}

.user-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  background: var(--card-bg-color, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
  transition: border-color var(--transition-normal, 250ms ease),
              box-shadow var(--transition-normal, 250ms ease),
              transform var(--transition-fast, 150ms ease);
  position: relative;
  overflow: hidden;
}

.user-card:hover {
  border-color: var(--border-medium, rgba(255, 255, 255, 0.12));
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
  flex-wrap: wrap;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.user-name {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

.card-tags {
  flex-shrink: 0;
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

.user-id-code {
  font-size: 11px;
  opacity: 0.6;
  font-family: monospace;
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
