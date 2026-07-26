<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { authApi } from '@/api/auth'
import { useNotification } from '@/composables'

const { success, error: showError } = useNotification()

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
    sessions.value = await authApi.getSessions() || []
  } catch {
    showError('加载会话列表失败')
  }
}

async function changePassword() {
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    showError('两次密码不一致')
    return
  }
  try {
    await authApi.changePassword({
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
    })
    success('密码已修改')
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
  try {
    await authApi.enable2fa(twoFactorCode.value)
    success('2FA 已启用')
    twoFactorSetup.value = null
    loadProfile()
  } catch {
    showError('启用 2FA 失败')
  }
}

async function disable2fa() {
  try {
    await authApi.disable2fa()
    success('2FA 已禁用')
    loadProfile()
  } catch {
    showError('禁用 2FA 失败')
  }
}

async function revokeSession(id: string) {
  try {
    await authApi.revokeSession(id)
    success('会话已撤销')
    loadSessions()
  } catch {
    showError('撤销失败')
  }
}

async function revokeAllSessions() {
  try {
    await authApi.revokeAllSessions()
    success('所有其他会话已撤销')
    loadSessions()
  } catch {
    showError('撤销失败')
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
              创建时间：{{ profile.created_at || '-' }}
            </div>
            <div class="text-body-2">
              <v-icon start size="18">mdi-shield-check</v-icon>
              2FA 状态：
              <v-chip :color="profile.twofa_enabled ? 'success' : 'grey'" size="small" variant="tonal">
                {{ profile.twofa_enabled ? '已启用' : '未启用' }}
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
            <v-text-field v-model="passwordForm.new_password" label="新密码" type="password" variant="outlined" class="mb-3" />
            <v-text-field v-model="passwordForm.confirm_password" label="确认新密码" type="password" variant="outlined" class="mb-4" />
            <v-btn color="primary" variant="flat" block @click="changePassword">修改密码</v-btn>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- 2FA -->
      <v-window-item value="2fa">
        <v-card class="liquid-glass-card" rounded="xl" max-width="500">
          <v-card-text class="pa-6">
            <template v-if="!twoFactorSetup">
              <p class="text-body-1 mb-4">双因素认证 (2FA) 为您的账户增加额外的安全保护。</p>
              <v-btn v-if="!profile.twofa_enabled" color="primary" variant="flat" @click="setup2fa">设置 2FA</v-btn>
              <template v-else>
                <v-alert type="success" variant="tonal" class="mb-4" rounded="lg">2FA 已启用</v-alert>
                <v-btn color="error" variant="tonal" @click="disable2fa">禁用 2FA</v-btn>
              </template>
            </template>
            <template v-else>
              <p class="text-body-2 mb-3">请使用认证器 App 扫描以下二维码：</p>
              <div class="text-center mb-3">
                <img :src="twoFactorSetup.qr_code_url" alt="2FA QR Code" style="max-width:200px" v-if="twoFactorSetup.qr_code_url" />
                <div class="font-mono text-caption pa-2 rounded" style="background:rgba(0,0,0,0.2)">
                  {{ twoFactorSetup.secret }}
                </div>
              </div>
              <v-text-field v-model="twoFactorCode" label="输入验证码" variant="outlined" class="mb-3" />
              <v-btn color="primary" variant="flat" @click="enable2fa" :disabled="!twoFactorCode">启用</v-btn>
            </template>
          </v-card-text>
        </v-card>
      </v-window-item>

      <!-- 会话管理 -->
      <v-window-item value="sessions">
        <div class="d-flex justify-end mb-4">
          <v-btn color="error" variant="tonal" size="small" @click="revokeAllSessions">撤销所有其他会话</v-btn>
        </div>
        <v-card class="liquid-glass-card" rounded="xl">
          <v-table class="bg-transparent">
            <thead>
              <tr><th>设备</th><th>IP 地址</th><th>最后活动</th><th class="text-right">操作</th></tr>
            </thead>
            <tbody>
              <tr v-for="session in sessions" :key="session.id">
                <td class="font-weight-medium">{{ session.device_info || session.user_agent || '-' }}</td>
                <td class="text-medium-emphasis font-mono">{{ session.ip_address || '-' }}</td>
                <td class="text-medium-emphasis">{{ session.last_activity || '-' }}</td>
                <td class="text-right">
                  <v-btn size="small" variant="tonal" color="error" @click="revokeSession(session.id)">撤销</v-btn>
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-window-item>
    </v-window>
  </v-container>
</template>
