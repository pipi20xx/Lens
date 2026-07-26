<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { authApi } from '@/api/auth'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const activeTab = ref('profile')
const profile = ref<any>({})
const sessions = ref<any[]>([])
const loading = ref(false)

// 2FA
const twoFactorSetup = ref<any>(null)
const twoFactorCode = ref('')

// 改密码
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' })

async function loadProfile() {
  try {
    loading.value = true
    profile.value = await authApi.getMe()
  } catch {
    showError('加载用户信息失败')
  } finally {
    loading.value = false
  }
}

async function loadSessions() {
  try {
    const data = await authApi.getSessions()
    // 后端返回 { sessions: [...] }，需要取 .sessions
    sessions.value = Array.isArray(data) ? data : (data?.sessions || [])
  } catch {
    showError('加载会话列表失败')
  }
}

async function changePassword() {
  if (!passwordForm.value.old_password) { showError('请输入当前密码'); return }
  if (!passwordForm.value.new_password) { showError('请输入新密码'); return }
  if (passwordForm.value.new_password.length < 6) { showError('新密码至少 6 位'); return }
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    showError('两次密码不一致')
    return
  }
  const ok = await confirm({
    title: '确认修改密码',
    content: '修改密码后，所有其他设备的登录会话将被撤销，需要重新登录。当前设备不受影响。',
    confirmColor: 'warning'
  })
  if (!ok) return
  try {
    await authApi.changePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
    })
    success('密码已修改，其他设备的会话已撤销')
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (err: any) {
    showError(err.message || '修改失败')
  }
}

async function setup2fa() {
  try {
    twoFactorSetup.value = await authApi.get2faSetup()
  } catch {
    showError('获取 2FA 设置失败')
  }
}

async function enable2fa() {
  if (!twoFactorCode.value.trim()) { showError('请输入验证码'); return }
  try {
    await authApi.enable2fa(twoFactorCode.value)
    success('2FA 已启用')
    twoFactorSetup.value = null
    twoFactorCode.value = ''
    loadProfile()
  } catch {
    showError('启用 2FA 失败，请检查验证码是否正确')
  }
}

async function disable2fa() {
  const ok = await confirm({
    title: '禁用 2FA',
    content: '禁用双因素认证将降低账户安全性。确定要禁用吗？',
    confirmColor: 'error'
  })
  if (!ok) return
  try {
    await authApi.disable2fa()
    success('2FA 已禁用')
    loadProfile()
  } catch {
    showError('禁用 2FA 失败')
  }
}

async function revokeSession(session: any) {
  // 后端需要 session_id 字符串，不是数据库主键 id
  const sessionId = session.session_id
  if (!sessionId) { showError('会话信息异常'); return }
  const ok = await confirm({ title: '撤销会话', content: '确定要撤销此设备的登录会话吗？', confirmColor: 'error' })
  if (!ok) return
  try {
    await authApi.revokeSession(sessionId)
    success('会话已撤销')
    loadSessions()
  } catch {
    showError('撤销失败')
  }
}

async function revokeAllSessions() {
  const ok = await confirm({
    title: '撤销所有其他会话',
    content: '此操作将撤销除当前设备外的所有登录会话，其他设备需要重新登录。',
    confirmColor: 'error'
  })
  if (!ok) return
  try {
    await authApi.revokeAllSessions()
    success('所有其他会话已撤销')
    loadSessions()
  } catch {
    showError('撤销失败')
  }
}

function formatTime(dt: string) {
  if (!dt) return '-'
  try {
    const d = new Date(dt)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return dt
  }
}

onMounted(() => { loadProfile(); loadSessions() })
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-shield-account-outline</v-icon>
      账户安全
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">管理登录密码、双因素认证及活跃会话。</p>

    <v-tabs v-model="activeTab" class="mb-4">
      <v-tab value="profile"><v-icon start>mdi-account-outline</v-icon> 个人信息</v-tab>
      <v-tab value="password"><v-icon start>mdi-lock-outline</v-icon> 修改密码</v-tab>
      <v-tab value="2fa"><v-icon start>mdi-two-factor-authentication</v-icon> 双因素认证</v-tab>
      <v-tab value="sessions"><v-icon start>mdi-devices</v-icon> 会话管理</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- 个人信息 -->
      <v-window-item value="profile">
        <v-card class="liquid-glass-card" rounded="xl" max-width="600">
          <v-card-text class="pa-6">
            <div class="d-flex align-center mb-4">
              <v-avatar color="primary" size="64" rounded="xl" class="mr-4">
                <v-icon icon="mdi-account" size="32" />
              </v-avatar>
              <div>
                <div class="text-h6 font-weight-bold">{{ profile.username || '-' }}</div>
                <div class="text-body-2 text-medium-emphasis">管理员</div>
              </div>
            </div>
            <v-divider class="mb-4" />
            <div class="text-body-2 mb-2">
              <v-icon start size="18">mdi-clock-outline</v-icon>
              上次登录：{{ formatTime(profile.last_login) || '-' }}
            </div>
            <div class="text-body-2">
              <v-icon start size="18">mdi-shield-check</v-icon>
              2FA 状态：
              <v-chip :color="profile.is_otp_enabled ? 'success' : 'grey'" size="small" variant="tonal">
                {{ profile.is_otp_enabled ? '已启用' : '未启用' }}
              </v-chip>
            </div>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- 修改密码 -->
      <v-window-item value="password">
        <v-card class="liquid-glass-card" rounded="xl" max-width="500">
          <v-card-text class="pa-6">
            <v-text-field v-model="passwordForm.old_password" label="当前密码" type="password" variant="outlined" class="mb-3" />
            <v-text-field v-model="passwordForm.new_password" label="新密码" type="password" variant="outlined" hint="至少 6 位字符" persistent-hint class="mb-3" />
            <v-text-field v-model="passwordForm.confirm_password" label="确认新密码" type="password" variant="outlined" class="mb-4" />
            <v-btn color="primary" variant="flat" block prepend-icon="mdi-lock-outline" @click="changePassword">修改密码</v-btn>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- 2FA -->
      <v-window-item value="2fa">
        <v-card class="liquid-glass-card" rounded="xl" max-width="500">
          <v-card-text class="pa-6">
            <template v-if="!twoFactorSetup">
              <p class="text-body-1 mb-4">双因素认证 (2FA) 为您的账户增加额外的安全保护，登录时除密码外还需输入动态验证码。</p>
              <v-btn v-if="!profile.is_otp_enabled" color="primary" variant="flat" prepend-icon="mdi-shield-key-outline" @click="setup2fa">设置 2FA</v-btn>
              <template v-else>
                <v-alert type="success" variant="tonal" class="mb-4" rounded="lg">2FA 已启用，您的账户受到额外保护。</v-alert>
                <v-btn color="error" variant="tonal" prepend-icon="mdi-shield-off-outline" @click="disable2fa">禁用 2FA</v-btn>
              </template>
            </template>
            <template v-else>
              <p class="text-body-2 mb-3">请使用认证器 App（如 Google Authenticator、Microsoft Authenticator）扫描以下二维码：</p>
              <div class="text-center mb-3">
                <img :src="twoFactorSetup.qr_code" alt="2FA QR Code" style="max-width:200px;border-radius:8px" />
                <div class="font-mono text-caption pa-2 mt-2 rounded" style="background:rgba(0,0,0,0.2)">
                  密钥：{{ twoFactorSetup.secret }}
                </div>
              </div>
              <v-alert type="info" variant="tonal" density="compact" class="mb-3">
                请妥善保存密钥，更换设备时可用其恢复 2FA 配置。
              </v-alert>
              <v-text-field v-model="twoFactorCode" label="输入 6 位验证码" variant="outlined" maxlength="6" placeholder="000000" class="mb-3" />
              <div class="d-flex ga-2">
                <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="twoFactorSetup = null; twoFactorCode = ''">取消</v-btn>
                <v-btn color="primary" variant="flat" prepend-icon="mdi-check-circle-outline" @click="enable2fa" :disabled="!twoFactorCode">启用</v-btn>
              </div>
            </template>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- 会话管理 -->
      <v-window-item value="sessions">
        <div class="d-flex justify-end mb-4">
          <v-btn color="error" variant="tonal" size="small" prepend-icon="mdi-logout" @click="revokeAllSessions">撤销所有其他会话</v-btn>
        </div>

        <div v-if="sessions.length === 0" class="text-center py-12 text-medium-emphasis">
          <v-icon size="64" color="grey" class="mb-4">mdi-devices</v-icon>
          <div>暂无活跃会话</div>
        </div>

        <div v-else class="d-flex flex-column ga-3">
          <v-card v-for="session in sessions" :key="session.session_id || session.id" class="liquid-glass-card" rounded="lg">
            <div class="pa-4">
              <div class="d-flex align-center mb-2">
                <v-icon start :color="session.is_current ? 'success' : 'default'" class="mr-2">
                  {{ session.is_current ? 'mdi-laptop' : 'mdi-monitor' }}
                </v-icon>
                <span class="text-subtitle-2 font-weight-bold">{{ session.device_info || session.user_agent || '-' }}</span>
                <v-spacer />
                <v-chip v-if="session.is_current" size="x-small" variant="tonal" color="success">当前设备</v-chip>
                <v-btn v-else size="small" variant="tonal" color="error" prepend-icon="mdi-cancel" @click="revokeSession(session)">撤销</v-btn>
              </div>
              <div class="d-flex flex-wrap ga-4 text-caption text-medium-emphasis">
                <span><v-icon size="14">mdi-ip-network</v-icon> {{ session.ip_address || '-' }}</span>
                <span><v-icon size="14">mdi-clock-outline</v-icon> 登录：{{ session.login_time || '-' }}</span>
                <span><v-icon size="14">mdi-update</v-icon> 活动：{{ session.last_activity || '-' }}</span>
                <span v-if="session.expires_text"><v-icon size="14">mdi-timer-sand</v-icon> {{ session.expires_text }}</span>
              </div>
            </div>
          </v-card>
        </div>
      </v-window-item>
    </v-window>
  </v-container>
</template>
