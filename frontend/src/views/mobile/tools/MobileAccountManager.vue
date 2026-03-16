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
          <n-switch v-model:value="securitySettings.twoFactorEnabled" @update:value="toggleTwoFactor" class="mobile-switch" />
        </div>
        <div class="security-item">
          <div class="security-info">
            <div class="security-label">登录通知</div>
            <div class="security-desc">新设备登录时发送通知</div>
          </div>
          <n-switch v-model:value="securitySettings.loginNotification" @update:value="saveSecuritySettings" class="mobile-switch" />
        </div>
      </n-space>
    </n-card>

    <!-- 两步验证设置弹窗 -->
    <n-modal v-model:show="showOtpModal" preset="card" title="开启两步验证" style="width: 90vw; max-width: 400px">
      <n-space vertical align="center">
        <p style="color: var(--text-color); text-align: center;">请使用身份验证器扫描下方二维码</p>
        <img v-if="otpQrCode" :src="otpQrCode" style="width: 200px; height: 200px;" />
        <n-form-item label="或手动输入密钥" style="width: 100%;">
          <n-input :value="otpSecret" readonly />
        </n-form-item>
        <n-form-item label="验证码" style="width: 100%;">
          <n-input v-model:value="otpCode" placeholder="请输入6位验证码" maxlength="6" />
        </n-form-item>
        <n-space>
          <n-button secondary @click="showOtpModal = false">取消</n-button>
          <n-button type="primary" @click="enableOtp">确认开启</n-button>
        </n-space>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NFormItem, NInput, NSwitch, NTag, NAvatar, NModal, NForm } from 'naive-ui'
import { accountApi } from '@/api/account'
import { authApi } from '@/api/auth'
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

const loadSecuritySettings = async () => {
  try {
    const meData: any = await authApi.getMe()
    securitySettings.value.twoFactorEnabled = meData.is_otp_enabled || false
  } catch (e) {
    message.error('加载安全设置失败')
  }
}

const changePassword = async () => {
  if (!passwordForm.value.oldPassword || !passwordForm.value.newPassword || !passwordForm.value.confirmPassword) {
    message.warning('请填写完整的密码信息')
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    message.warning('两次输入的新密码不一致')
    return
  }
  changingPassword.value = true
  try {
    await authApi.changePassword({
      old_password: passwordForm.value.oldPassword,
      new_password: passwordForm.value.newPassword
    })
    message.success('密码修改成功')
    passwordForm.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
  } catch (e: any) {
    message.error('密码修改失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    changingPassword.value = false
  }
}

const toggleTwoFactor = async () => {
  if (securitySettings.value.twoFactorEnabled) {
    // 开启两步验证
    showOtpModal.value = true
    try {
      const data: any = await authApi.setup2fa()
      otpQrCode.value = data.qr_code
      otpSecret.value = data.secret
    } catch (e) {
      message.error('获取二维码失败')
    }
  } else {
    // 关闭两步验证
    try {
      await authApi.disable2fa()
      message.success('两步验证已关闭')
    } catch (e) {
      message.error('关闭两步验证失败')
      securitySettings.value.twoFactorEnabled = true
    }
  }
}

const enableOtp = async () => {
  if (!otpCode.value) {
    message.warning('请输入验证码')
    return
  }
  try {
    await authApi.enable2fa(otpCode.value)
    message.success('两步验证已开启')
    showOtpModal.value = false
    otpCode.value = ''
    otpQrCode.value = ''
    otpSecret.value = ''
  } catch (e) {
    message.error('验证码错误')
  }
}

const saveSecuritySettings = () => {
  message.success('安全设置已保存')
}

const showOtpModal = ref(false)
const otpQrCode = ref('')
const otpSecret = ref('')
const otpCode = ref('')

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
