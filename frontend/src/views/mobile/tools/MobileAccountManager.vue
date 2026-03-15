<template>
  <div class="mobile-account-manager">
    <div class="page-header">
      <h1 class="page-title">账号安全管理</h1>
      <p class="page-desc">管理系统用户与安全设置</p>
    </div>

    <n-card class="profile-card" :bordered="false" title="当前用户">
      <div class="profile-info">
        <div class="profile-avatar">
          <n-avatar round :size="60" :src="user.avatar || '/favicon.svg'" />
        </div>
        <div class="profile-details">
          <div class="profile-name">{{ user.username }}</div>
          <div class="profile-email">{{ user.email }}</div>
          <div class="profile-role">
            <n-tag :type="user.role === 'admin' ? 'warning' : 'info'" size="small">
              {{ user.role === 'admin' ? '管理员' : '普通用户' }}
            </n-tag>
          </div>
        </div>
      </div>
    </n-card>

    <n-card class="password-card" :bordered="false" title="修改密码">
      <n-space vertical>
        <n-form-item label="当前密码">
          <n-input v-model:value="passwordForm.oldPassword" type="password" show-password-on="click" placeholder="请输入当前密码" />
        </n-form-item>
        <n-form-item label="新密码">
          <n-input v-model:value="passwordForm.newPassword" type="password" show-password-on="click" placeholder="请输入新密码" />
        </n-form-item>
        <n-form-item label="确认密码">
          <n-input v-model:value="passwordForm.confirmPassword" type="password" show-password-on="click" placeholder="请再次输入新密码" />
        </n-form-item>
        <n-button block type="primary" :loading="changingPassword" @click="changePassword">
          修改密码
        </n-button>
      </n-space>
    </n-card>

    <n-card class="security-card" :bordered="false" title="安全设置">
      <n-space vertical>
        <div class="security-item">
          <div class="security-info">
            <div class="security-label">两步验证</div>
            <div class="security-desc">启用后登录需要验证码</div>
          </div>
          <n-switch v-model:value="securitySettings.twoFactorEnabled" @update:value="toggleTwoFactor" />
        </div>
        <div class="security-item">
          <div class="security-info">
            <div class="security-label">登录通知</div>
            <div class="security-desc">新设备登录时发送通知</div>
          </div>
          <n-switch v-model:value="securitySettings.loginNotification" @update:value="saveSecuritySettings" />
        </div>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NFormItem, NInput, NSwitch, NTag, NAvatar } from 'naive-ui'
import { accountApi } from '@/api/account'
import { useMessage } from 'naive-ui'

const message = useMessage()
const user = ref({
  username: '',
  email: '',
  role: '',
  avatar: ''
})
const changingPassword = ref(false)
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})
const securitySettings = ref({
  twoFactorEnabled: false,
  loginNotification: true
})

const loadProfile = async () => {
  try {
    const res = await accountApi.getUsers()
    const users = res.data as any || []
    user.value = users[0] || { username: '', email: '', role: '', avatar: '' }
  } catch (e) {
    message.error('加载用户信息失败')
  }
}

const loadSecuritySettings = () => {
  message.info('请在桌面端配置安全设置')
}

const changePassword = () => {
  message.info('请在桌面端修改密码')
}

const toggleTwoFactor = () => {
  message.info('请在桌面端配置两步验证')
}

const saveSecuritySettings = () => {
  message.info('请在桌面端配置安全设置')
}

onMounted(() => {
  loadProfile()
  loadSecuritySettings()
})
</script>

<style scoped>
.mobile-account-manager {
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

.profile-card,
.password-card,
.security-card {
  margin-bottom: 12px;
}

.profile-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.profile-avatar {
  flex-shrink: 0;
}

.profile-details {
  flex: 1;
}

.profile-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 4px;
}

.profile-email {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 8px;
}

.security-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.security-item:last-child {
  border-bottom: none;
}

.security-info {
  flex: 1;
}

.security-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.security-desc {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}
</style>
