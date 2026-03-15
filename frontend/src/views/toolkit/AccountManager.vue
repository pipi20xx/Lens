<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text>
          <n-text type="primary">账号安全管理</n-text>
        </n-h2>
        <n-text depth="3">
          维护管理员凭据及多因素认证设置，确保系统访问安全。
        </n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：主要配置区 -->
        <n-gi span="24 m:16">
          <n-space vertical size="large">
            <n-grid :x-gap="12" :y-gap="12" :cols="2" item-responsive responsive="screen">
              <!-- 1. 密码修改 -->
              <n-gi span="2 m:1">
                <n-card title="修改管理员密码" size="small" segmented style="height: 100%" content-style="display: flex; flex-direction: column; justify-content: space-between;">
                  <n-form size="medium">
                    <n-form-item label="旧密码">
                      <n-input v-model:value="pwdForm.old_password" type="password" show-password-on="click" placeholder="请输入当前密码" />
                    </n-form-item>
                    <n-form-item label="新密码">
                      <n-input v-model:value="pwdForm.new_password" type="password" show-password-on="click" placeholder="请输入新密码" />
                    </n-form-item>
                  </n-form>
                  <div style="margin-top: 16px">
                    <n-button type="primary" block @click="handleChangePassword">
                      <template #icon><n-icon><LockIcon /></n-icon></template>
                      确认修改密码
                    </n-button>
                  </div>
                </n-card>
              </n-gi>

              <!-- 2. 2FA 设置 -->
              <n-gi span="2 m:1">
                <n-card title="双重验证 (2FA)" size="small" segmented style="height: 100%" content-style="display: flex; flex-direction: column; justify-content: space-between;">
                  <n-space vertical size="large">
                    <n-alert 
                      :type="authInfo.is_otp_enabled ? 'success' : 'warning'" 
                      :title="authInfo.is_otp_enabled ? '已开启安全保护' : '未开启保护'"
                    >
                      {{ authInfo.is_otp_enabled ? '登录时需要输入动态验证码。' : '建议开启以防止密码泄露。' }}
                    </n-alert>
                    
                    <!-- 未开启状态 -->
                    <div v-if="!authInfo.is_otp_enabled && otpSetup.qr_code" style="display: flex; flex-direction: column; align-items: center;">
                      <div style="background: white; padding: 8px; border-radius: 8px; margin-bottom: 16px;">
                        <img :src="otpSetup.qr_code" style="width: 140px; display: block;" />
                      </div>
                      <n-input-group>
                        <n-input v-model:value="otpSetup.code" placeholder="6 位验证码" maxlength="6" />
                        <n-button type="primary" @click="enableOtp">
                          <template #icon><n-icon><LinkIcon /></n-icon></template>
                          绑定
                        </n-button>
                      </n-input-group>
                      <n-button text @click="otpSetup.qr_code = ''" style="margin-top: 10px;">
                        <template #icon><n-icon><BackIcon /></n-icon></template>
                        返回
                      </n-button>
                    </div>
                  </n-space>

                  <div style="margin-top: 16px">
                    <!-- 未开启状态的初始按钮 -->
                    <div v-if="!authInfo.is_otp_enabled && !otpSetup.qr_code">
                      <n-button block type="primary" @click="setupOtp">
                        <template #icon><n-icon><SecurityIcon /></n-icon></template>
                        开始设置 2FA
                      </n-button>
                    </div>
                    
                    <!-- 已开启状态的按钮 -->
                    <n-button 
                      v-if="authInfo.is_otp_enabled" 
                      block 
                      @click="disableOtp" 
                      type="error" 
                      secondary
                    >
                      <template #icon><n-icon><ShieldOffIcon /></n-icon></template>
                      停用双重验证 (2FA)
                    </n-button>
                  </div>
                </n-card>
              </n-gi>
            </n-grid>

            <!-- 3. 会话管理 -->
            <n-gi span="24">
              <SessionManager />
            </n-gi>
          </n-space>
        </n-gi>

        <!-- 右侧：说明与技巧 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <n-card title="安全建议" size="small" segmented>
              <n-text depth="3" style="font-size: 13px">
                1. <b>定期更换密码</b>：建议每 3-6 个月更换一次管理员密码。<br/>
                2. <b>启用 2FA</b>：即使密码泄露，二次验证也能拦截非法登录。<br/>
                3. <b>保护 Token</b>：API Token 拥有系统所有权限，请妥善保管，不要泄露给他人。
              </n-text>
            </n-card>

            <n-card title="2FA 绑定说明" size="small" segmented>
              <n-text depth="3" style="font-size: 13px">
                请确保您的移动设备上安装了支持 TOTP 的验证器应用，例如：<br/>
                - Google Authenticator<br/>
                - Microsoft Authenticator<br/>
                - Authy / Bitwarden<br/><br/>
                扫描左侧生成的二维码即可完成绑定。
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { 
  NSpace, NH2, NText, NCard, NForm, NFormItem, 
  NInput, NButton, NGrid, NGi, NAlert, NInputGroup, NSwitch, NThing, NIcon
} from 'naive-ui'
import {
  LockOutlined as LockIcon,
  SecurityOutlined as SecurityIcon,
  LinkOutlined as LinkIcon,
  ArrowBackOutlined as BackIcon,
  ShieldMoonOutlined as ShieldOffIcon,
  SaveOutlined as SaveIcon
} from '@vicons/material'

// 导入提取的逻辑
import { useAuthManager } from './auth/hooks/useAuthManager'
import SessionManager from './auth/SessionManager.vue'

const { 
  pwdForm, authInfo, otpSetup,
  loadAuthInfo, setupOtp, enableOtp, disableOtp, handleChangePassword 
} = useAuthManager()

onMounted(() => {
  loadAuthInfo()
})
</script>

<style scoped>
</style>