<template>
  <div class="mobile-account-manager">
    <div class="page-header">
      <h1 class="page-title">账号安全管理</h1>
      <p class="page-desc">维护管理员凭据及多因素认证设置，确保系统访问安全</p>
    </div>

    <n-card class="password-card" :bordered="false" title="修改管理员密码">
      <n-space vertical>
        <n-form-item :label="formLabel.OLD_PASSWORD">
          <n-input v-model:value="pwdForm.old_password" type="password" show-password-on="click" :placeholder="placeholder.OLD_PASSWORD" />
        </n-form-item>
        <n-form-item :label="formLabel.NEW_PASSWORD">
          <n-input v-model:value="pwdForm.new_password" type="password" show-password-on="click" :placeholder="placeholder.NEW_PASSWORD" />
        </n-form-item>
        <n-button block :type="buttonTypes.PRIMARY" :loading="changingPassword" @click="handleChangePassword">
          {{ buttonText.CONFIRM_CHANGE_PASSWORD }}
        </n-button>
      </n-space>
    </n-card>

    <n-card class="twofa-card" :bordered="false" title="双重验证 (2FA)">
      <n-space vertical>
        <n-alert :type="authInfo.is_otp_enabled ? tagTypes.SUCCESS : tagTypes.WARNING" :size="buttonSizes.TINY">
          {{ authInfo.is_otp_enabled ? '已开启安全保护，登录时需要输入动态验证码' : '未开启保护，建议开启以防止密码泄露' }}
        </n-alert>
        
        <div v-if="!authInfo.is_otp_enabled && otpSetup.qr_code" class="otp-setup">
          <div class="qr-code-wrapper">
            <img :src="otpSetup.qr_code" class="qr-code" />
          </div>
          <n-input v-model:value="otpSetup.code" :placeholder="placeholder.VERIFICATION_CODE" maxlength="6" />
          <n-space>
            <n-button secondary @click="otpSetup.qr_code = ''">{{ buttonText.BACK }}</n-button>
            <n-button :type="buttonTypes.PRIMARY" @click="enableOtp">{{ buttonText.BIND }}</n-button>
          </n-space>
        </div>

        <div v-if="!authInfo.is_otp_enabled && !otpSetup.qr_code">
          <n-button block :type="buttonTypes.PRIMARY" @click="setupOtp">
            {{ buttonText.START_SETUP_2FA }}
          </n-button>
        </div>
        
        <n-button 
          v-if="authInfo.is_otp_enabled" 
          block 
          :type="buttonTypes.ERROR" 
          secondary
          @click="disableOtp"
        >
          {{ buttonText.DISABLE_2FA }}
        </n-button>
      </n-space>
    </n-card>

    <n-card class="sessions-card" :bordered="false" title="会话管理">
      <n-space vertical>
        <n-alert :type="buttonTypes.INFO" :size="buttonSizes.TINY">
          管理您的登录会话，查看所有已登录的设备并踢出可疑设备
        </n-alert>

        <n-space justify="space-between" align="center">
          <n-text depth="3">共 {{ sessions.length }} 个活跃会话</n-text>
          <n-button 
            v-if="sessions.length > 1" 
            :type="buttonTypes.ERROR" 
            :size="buttonSizes.SMALL" 
            @click="handleRevokeAll"
          >
            {{ buttonText.REVOKE_ALL }}
          </n-button>
        </n-space>

        <n-spin :show="loadingSessions">
          <div v-if="sessions.length === 0" class="empty-state">
            <n-empty :description="messageText.EMPTY_DATA" />
          </div>
          <div v-else class="session-list">
            <div v-for="session in sessions" :key="session.session_id" class="session-item">
              <div class="session-header">
                <div class="session-device">
                  <n-icon :size="20" :color="session.is_current ? '#18a058' : '#909399'">
                    <component :is="session.is_current ? CheckCircleIcon : DeviceIcon" />
                  </n-icon>
                  <n-text strong>{{ session.device_info }}</n-text>
                  <n-tag v-if="session.is_current" :type="tagTypes.SUCCESS" :size="buttonSizes.TINY">当前会话</n-tag>
                </div>
              </div>
              <div class="session-details">
                <div class="session-detail-item">
                  <n-icon :component="TimeIcon" :size="14" />
                  <span>{{ session.expires_text }}</span>
                </div>
                <div class="session-detail-item">
                  <n-icon :component="LocationIcon" :size="14" />
                  <span>IP: {{ session.ip_address }}</span>
                </div>
                <div class="session-detail-item">
                  <n-icon :component="CalendarIcon" :size="14" />
                  <span>{{ session.login_time }}</span>
                </div>
              </div>
              <div v-if="!session.is_current" class="session-actions">
                <n-button :type="buttonTypes.ERROR" :size="buttonSizes.SMALL" secondary @click="handleRevokeSession(session.session_id)">
                  {{ buttonText.REVOKE }}
                </n-button>
              </div>
            </div>
          </div>
        </n-spin>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NFormItem, NInput, NTag, NAlert, NSpin, NEmpty, NText, NIcon, h } from 'naive-ui'
import { authApi } from '@/api/auth'
import { useMessage } from 'naive-ui'
import {
  ButtonTypes,
  ButtonSizes,
  TagTypes,
  ButtonText,
  MessageText,
} from '../constants'
import {
  CheckCircleOutlined as CheckCircleIcon,
  DevicesOutlined as DeviceIcon,
  AccessTimeOutlined as TimeIcon,
  LocationOnOutlined as LocationIcon,
  EventOutlined as CalendarIcon,
  ExitToAppOutlined as LogoutIcon
} from '@vicons/material'

const message = useMessage()

const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const tagTypes = TagTypes
const buttonText = ButtonText
const messageText = MessageText

const formLabel = {
  OLD_PASSWORD: '旧密码',
  NEW_PASSWORD: '新密码',
}

const placeholder = {
  OLD_PASSWORD: '请输入当前密码',
  NEW_PASSWORD: '请输入新密码',
  VERIFICATION_CODE: '6 位验证码',
}

const pwdForm = ref({
  old_password: '',
  new_password: ''
})
const authInfo = ref({
  is_otp_enabled: false
})
const otpSetup = ref({
  qr_code: '',
  code: ''
})
const changingPassword = ref(false)
const sessions = ref<any[]>([])
const loadingSessions = ref(false)

const loadAuthInfo = async () => {
  try {
    const data: any = await authApi.getMe()
    authInfo.value.is_otp_enabled = data.is_otp_enabled || false
  } catch (e) {
    message.error(messageText.LOAD_FAILED)
  }
}

const handleChangePassword = async () => {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    message.warning('请填写完整的密码信息')
    return
  }
  changingPassword.value = true
  try {
    await authApi.changePassword(pwdForm.value)
    message.success(messageText.UPDATE_SUCCESS)
    pwdForm.value = { old_password: '', new_password: '' }
  } catch (e: any) {
    message.error(messageText.UPDATE_FAILED + ': ' + (e.response?.data?.detail || e.message))
  } finally {
    changingPassword.value = false
  }
}

const setupOtp = async () => {
  try {
    const data: any = await authApi.setup2fa()
    otpSetup.value.qr_code = data.qr_code
  } catch (e) {
    message.error(messageText.OPERATION_FAILED)
  }
}

const enableOtp = async () => {
  if (!otpSetup.value.code) {
    message.warning('请输入验证码')
    return
  }
  try {
    await authApi.enable2fa(otpSetup.value.code)
    message.success('双重验证已开启')
    otpSetup.value = { qr_code: '', code: '' }
    await loadAuthInfo()
  } catch (e) {
    message.error(messageText.OPERATION_FAILED)
  }
}

const disableOtp = async () => {
  try {
    await authApi.disable2fa()
    message.success('双重验证已关闭')
    await loadAuthInfo()
  } catch (e) {
    message.error(messageText.OPERATION_FAILED)
  }
}

const loadSessions = async () => {
  loadingSessions.value = true
  try {
    const data: any = await authApi.getSessions()
    sessions.value = data.sessions || []
  } catch (error) {
    message.error('加载会话列表失败')
  } finally {
    loadingSessions.value = false
  }
}

const handleRevokeSession = async (sessionId: string) => {
  try {
    await authApi.revokeSession(sessionId)
    message.success('设备已踢出')
    await loadSessions()
  } catch (error) {
    message.error('踢出设备失败')
  }
}

const handleRevokeAll = async () => {
  try {
    await authApi.revokeAllSessions()
    message.success('所有其他设备已踢出')
    await loadSessions()
  } catch (error) {
    message.error('操作失败')
  }
}

onMounted(() => {
  loadAuthInfo()
  loadSessions()
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

.password-card,
.twofa-card,
.sessions-card {
  margin-bottom: 12px;
}

.otp-setup {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.qr-code-wrapper {
  background: white;
  padding: 8px;
  border-radius: 8px;
}

.qr-code {
  width: 140px;
  display: block;
}

.empty-state {
  padding: 24px 0;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.session-item {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #3B82F6;
  border-radius: 12px;
}

.session-header {
  margin-bottom: 8px;
}

.session-device {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.session-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.session-detail-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.session-actions {
  display: flex;
  gap: 8px;
}
</style>
