<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listEmbyUsers, createEmbyUser, deleteEmbyUser, getEmbyUserInfo, updateEmbyUserPolicy, updateEmbyUserPassword } from '@/api/embyUsers'
import { embyBackupApi } from '@/api/embyBackup'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import EmbyConfigBackupManager from '@/components/emby/EmbyConfigBackupManager.vue'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const users = ref<any[]>([])
const loading = ref(true)
const creating = ref(false)
const backingUpAll = ref(false)
const newUserName = ref('')

// 用户设置弹窗
const showEditModal = ref(false)
const editingUser = ref<any>(null)
const policy = ref<any>({})
const jsonRaw = ref('')
const newPassword = ref('')
const savingPolicy = ref(false)
const backingUp = ref(false)
const activeEditTab = ref('account')

async function loadUsers() {
  try {
    loading.value = true
    const res = await listEmbyUsers()
    users.value = Array.isArray(res) ? res : []
  } catch {
    showError('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function handleCreateUser() {
  if (!newUserName.value.trim()) return
  creating.value = true
  try {
    await createEmbyUser(newUserName.value.trim())
    success('用户已创建')
    newUserName.value = ''
    loadUsers()
  } catch { showError('创建失败') }
  finally { creating.value = false }
}

async function handleBackupAll() {
  backingUpAll.value = true
  try {
    const res: any = await embyBackupApi.createAll('users')
    success(`成功备份 ${res?.count ?? ''} 个用户配置`)
  } catch { showError('备份失败') }
  finally { backingUpAll.value = false }
}

async function handleDirectBackup(user: any) {
  try {
    await embyBackupApi.create('users', user.Id, user.Name)
    success(`用户 ${user.Name} 备份成功`)
  } catch { showError('备份失败') }
}

async function handleBackup() {
  if (!editingUser.value) return
  backingUp.value = true
  try {
    await embyBackupApi.create('users', editingUser.value.Id, editingUser.value.Name)
    success('当前配置已备份')
  } catch { showError('备份失败') }
  finally { backingUp.value = false }
}

async function deleteUser(id: string, name: string) {
  const ok = await confirm({ title: '删除用户', content: `确定要删除用户 "${name}" 吗？此操作不可恢复。`, confirmColor: 'error' })
  if (!ok) return
  try {
    await deleteEmbyUser(id)
    success('用户已删除')
    loadUsers()
  } catch { showError('删除失败') }
}

async function openEdit(user: any) {
  editingUser.value = user
  newPassword.value = ''
  try {
    const info: any = await getEmbyUserInfo(user.Id)
    policy.value = info?.Policy || {}
    jsonRaw.value = JSON.stringify(policy.value, null, 2)
    activeEditTab.value = 'account'
    showEditModal.value = true
  } catch {
    showError('获取用户详情失败')
  }
}

function handleJsonInput(value: string) {
  try {
    const parsed = JSON.parse(value)
    policy.value = parsed
  } catch { /* ignore */ }
}

async function handleSavePolicy() {
  if (!editingUser.value) return
  try {
    policy.value = JSON.parse(jsonRaw.value)
  } catch {
    showError('JSON 格式非法，请检查后再试')
    return
  }
  savingPolicy.value = true
  try {
    await updateEmbyUserPolicy(editingUser.value.Id, policy.value)
    success('设置已保存')
    showEditModal.value = false
    loadUsers()
  } catch { showError('保存失败') }
  finally { savingPolicy.value = false }
}

async function handleUpdatePassword() {
  if (!editingUser.value || !newPassword.value) return
  try {
    await updateEmbyUserPassword(editingUser.value.Id, newPassword.value)
    success('密码已更新')
    newPassword.value = ''
  } catch { showError('密码更新失败') }
}

onMounted(loadUsers)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-account-group-outline</v-icon>
      Emby 用户管理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-4">管理您的 Emby 服务器用户、权限策略及密码。</p>

    <!-- 高危警告 -->
    <v-alert variant="tonal" type="error" density="compact" class="mb-4" rounded="lg">
      <strong>高危操作警告：</strong>本模块功能涉及 Emby 数据库底层权限策略的强制写入。<strong>非必要请勿使用！</strong>建议仅在<strong>新建/初始化 Emby 服务器</strong>时用于快速迁移配置。误操作可能导致 Emby 用户数据库损坏或权限丢失，由此产生的后果请自行承担。
    </v-alert>

    <!-- 工具栏 -->
    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center flex-wrap pa-4">
        <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" @click="loadUsers" :loading="loading" class="mr-2">刷新用户列表</v-btn>
        <v-btn prepend-icon="mdi-backup-restore" variant="tonal" color="warning" size="small" @click="handleBackupAll" :loading="backingUpAll" class="mr-2">一键备份所有用户</v-btn>
        <EmbyConfigBackupManager category="users" @restored="loadUsers" />
        <v-spacer />
        <div class="d-flex ga-2">
          <v-text-field v-model="newUserName" placeholder="新用户名" variant="outlined" density="compact" hide-details style="width:150px"
            @keydown.enter="handleCreateUser" />
          <v-btn color="primary" variant="flat" size="small" @click="handleCreateUser" :loading="creating">新增用户</v-btn>
        </div>
      </v-card-title>
      <v-divider />

      <!-- 用户卡片列表 -->
      <v-card-text class="pa-4">
        <div v-if="loading" class="text-center py-8"><v-progress-circular indeterminate color="primary" /></div>
        <div v-else-if="!users.length" class="text-center py-8 text-medium-emphasis">
          <v-icon size="48" color="grey" class="mb-2">mdi-account-off-outline</v-icon>
          <div>暂无用户数据</div>
        </div>
        <div v-else>
          <v-row>
            <v-col v-for="user in users" :key="user.Id" cols="12">
              <v-card variant="outlined" rounded="lg" class="pa-4">
                <div class="d-flex align-center flex-wrap">
                  <!-- 用户名与状态标签 -->
                  <div class="d-flex align-center flex-grow-1 mb-2 mb-sm-0" style="min-width:200px">
                    <v-avatar color="primary" variant="tonal" size="40" rounded="xl" class="mr-3">
                      <v-icon icon="mdi-account" size="20" />
                    </v-avatar>
                    <div>
                      <div class="text-subtitle-2 font-weight-bold">{{ user.Name }}</div>
                      <div class="text-caption text-medium-emphasis font-mono">ID: {{ user.Id }}</div>
                    </div>
                  </div>

                  <!-- 状态标签 -->
                  <div class="d-flex flex-wrap ga-1 mb-2 mb-sm-0">
                    <v-chip v-if="user.Policy?.IsDisabled" size="x-small" color="error" variant="tonal">禁用</v-chip>
                    <v-chip v-if="user.Policy?.IsAdministrator" size="x-small" color="warning" variant="tonal">管理员</v-chip>
                    <v-chip v-if="user.Policy?.IsHidden" size="x-small" variant="tonal">隐藏</v-chip>
                    <v-chip v-if="!user.Policy?.IsDisabled && !user.Policy?.IsAdministrator && !user.Policy?.IsHidden" size="x-small" color="success" variant="tonal">正常</v-chip>
                  </div>

                  <!-- 最近活动 -->
                  <div class="text-caption text-medium-emphasis mx-4" style="min-width:120px">
                    {{ user.LastActivityDate ? new Date(user.LastActivityDate).toLocaleString() : '从未登录' }}
                  </div>

                  <!-- 操作按钮 -->
                  <div class="d-flex flex-wrap ga-1">
                    <v-btn size="x-small" variant="tonal" color="info" @click="openEdit(user)">设置</v-btn>
                    <v-btn size="x-small" variant="tonal" color="warning" @click="handleDirectBackup(user)">备份</v-btn>
                    <v-btn size="x-small" color="error" variant="tonal" @click="deleteUser(user.Id, user.Name)">删除</v-btn>
                  </div>
                </div>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </v-card-text>
    </v-card>

    <!-- 用户设置弹窗 -->
    <v-dialog v-model="showEditModal" max-width="900" scrollable>
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-account-cog-outline</v-icon>
          设置: {{ editingUser?.Name }}
        </v-card-title>
        <v-divider />

        <v-tabs v-model="activeEditTab" class="px-4">
          <v-tab value="account">账户与访问</v-tab>
          <v-tab value="playback">播放与转码</v-tab>
          <v-tab value="features">功能权限</v-tab>
          <v-tab value="library">媒体库范围</v-tab>
          <v-tab value="password">修改密码</v-tab>
          <v-tab value="json">原始数据 (JSON)</v-tab>
        </v-tabs>
        <v-divider />

        <v-card-text class="pa-4" style="max-height: 60vh; overflow-y: auto;">
          <v-window v-model="activeEditTab">
            <!-- 账户与访问 -->
            <v-window-item value="account">
              <v-switch v-model="policy.IsDisabled" label="禁用此账户 (IsDisabled)" density="compact" color="error" class="mb-2" />
              <v-switch v-model="policy.IsAdministrator" label="管理员权限 (IsAdministrator)" density="compact" color="warning" class="mb-2" />
              <v-switch v-model="policy.IsHidden" label="在登录界面隐藏该用户 (IsHidden)" density="compact" class="mb-2" />
              <v-switch v-model="policy.IsHiddenRemotely" label="远程访问时隐藏 (IsHiddenRemotely)" density="compact" class="mb-2" />
              <v-switch v-model="policy.IsHiddenFromUnusedDevices" label="从不使用的设备中隐藏 (IsHiddenFromUnusedDevices)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableRemoteAccess" label="允许远程访问 (EnableRemoteAccess)" density="compact" color="success" class="mb-2" />
              <v-text-field v-model="policy.SimultaneousStreamLimit" label="同时播放数量限制 (SimultaneousStreamLimit)" type="number" variant="outlined" density="compact" hint="0 为无限制" persistent-hint class="mb-2" />
              <v-text-field v-model="policy.RemoteClientBitrateLimit" label="远程客户端比特率限制 (RemoteClientBitrateLimit)" type="number" variant="outlined" density="compact" hint="单位: bps (0 为无限制)" persistent-hint class="mb-2" />
            </v-window-item>

            <!-- 播放与转码 -->
            <v-window-item value="playback">
              <v-switch v-model="policy.EnableMediaPlayback" label="允许媒体播放 (EnableMediaPlayback)" density="compact" color="success" class="mb-2" />
              <v-switch v-model="policy.EnableAudioPlaybackTranscoding" label="允许音频转码 (EnableAudioPlaybackTranscoding)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableVideoPlaybackTranscoding" label="允许视频转码 (EnableVideoPlaybackTranscoding)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnablePlaybackRemuxing" label="允许播放封装转换 (EnablePlaybackRemuxing)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableMediaConversion" label="允许媒体转换 (EnableMediaConversion)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableSyncTranscoding" label="允许同步转码 (EnableSyncTranscoding)" density="compact" class="mb-2" />
              <v-text-field v-model="policy.AutoRemoteQuality" label="自动远程质量 (AutoRemoteQuality)" type="number" variant="outlined" density="compact" hint="单位: Mbps" persistent-hint class="mb-2" />
            </v-window-item>

            <!-- 功能权限 -->
            <v-window-item value="features">
              <div class="text-subtitle-2 font-weight-bold mb-2">文件与下载</div>
              <v-switch v-model="policy.EnableContentDeletion" label="允许删除媒体 (EnableContentDeletion)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableContentDownloading" label="允许下载媒体 (EnableContentDownloading)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableSubtitleDownloading" label="允许下载字幕 (EnableSubtitleDownloading)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableSubtitleManagement" label="允许管理字幕 (EnableSubtitleManagement)" density="compact" class="mb-2" />
              <v-switch v-model="policy.AllowCameraUpload" label="允许相机上传 (AllowCameraUpload)" density="compact" class="mb-2" />

              <v-divider class="my-3" />
              <div class="text-subtitle-2 font-weight-bold mb-2">社交与远程控制</div>
              <v-switch v-model="policy.EnablePublicSharing" label="允许公开分享内容 (EnablePublicSharing)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableRemoteControlOfOtherUsers" label="允许远程控制其他用户 (EnableRemoteControlOfOtherUsers)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableSharedDeviceControl" label="允许控制共享设备 (EnableSharedDeviceControl)" density="compact" class="mb-2" />
            </v-window-item>

            <!-- 媒体库范围 -->
            <v-window-item value="library">
              <div class="text-subtitle-2 font-weight-bold mb-2">访问范围</div>
              <v-switch v-model="policy.EnableAllFolders" label="允许访问所有媒体库 (EnableAllFolders)" density="compact" color="success" class="mb-2" />
              <v-switch v-model="policy.EnableAllChannels" label="允许访问所有频道 (EnableAllChannels)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableAllDevices" label="允许在所有设备上登录 (EnableAllDevices)" density="compact" class="mb-2" />

              <v-divider class="my-3" />
              <div class="text-subtitle-2 font-weight-bold mb-2">直播电视</div>
              <v-switch v-model="policy.EnableLiveTvAccess" label="允许观看直播电视 (EnableLiveTvAccess)" density="compact" class="mb-2" />
              <v-switch v-model="policy.EnableLiveTvManagement" label="允许管理直播电视 (EnableLiveTvManagement)" density="compact" class="mb-2" />
            </v-window-item>

            <!-- 修改密码 -->
            <v-window-item value="password">
              <v-text-field v-model="newPassword" label="新密码" type="password" variant="outlined" density="compact" hint="留空则不修改" persistent-hint class="mb-3" />
              <v-btn color="warning" variant="flat" size="small" @click="handleUpdatePassword" :disabled="!newPassword">单独更新密码</v-btn>
            </v-window-item>

            <!-- 原始数据 (JSON) -->
            <v-window-item value="json">
              <v-alert variant="tonal" type="info" density="compact" class="mb-3" rounded="lg">
                高级操作：您可以直接编辑下方的原始 JSON 数据。请确保格式正确，非法 JSON 将无法保存。
              </v-alert>
              <v-textarea v-model="jsonRaw" variant="outlined" rows="18" style="font-family: monospace" @update:model-value="handleJsonInput" />
            </v-window-item>
          </v-window>
        </v-card-text>

        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="text" @click="showEditModal = false">取消</v-btn>
          <v-btn variant="tonal" color="warning" @click="handleBackup" :loading="backingUp">备份当前配置</v-btn>
          <v-btn color="primary" variant="flat" @click="handleSavePolicy" :loading="savingPolicy">保存设置</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>
