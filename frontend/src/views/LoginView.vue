<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables'
import { useNotification } from '@/composables'
import SecretField from '@/components/common/SecretField.vue'

const { formValue, loading, handleLogin } = useAuth()
const { error: showError } = useNotification()

async function onSubmit() {
  try {
    await handleLogin()
  } catch (err: any) {
    showError(err.message || '登录失败')
  }
}
</script>

<template>
  <v-app class="login-app">
    <v-main>
      <v-container fluid class="fill-height d-flex align-center justify-center">
        <v-card class="glass-card login-glass-panel pa-8" max-width="420" width="100%">
          <!-- 标题 -->
          <div class="text-center mb-6">
            <v-avatar class="liquid-avatar mb-4" size="64" rounded="xl">
              <div class="app-logo app-logo--login" role="img" aria-label="Lens" />
            </v-avatar>
            <h1 class="text-h5 font-weight-bold">LENS</h1>
            <p class="text-body-2 text-medium-emphasis mt-1">导航与管理工具</p>
          </div>

          <!-- 表单 -->
          <v-form @submit.prevent="onSubmit">
            <v-text-field
              v-model="formValue.username"
              label="用户名"
              prepend-inner-icon="mdi-account"
              autocomplete="username"
              class="mb-3"
            />
            <SecretField
              v-model="formValue.password"
              label="密码"
              prepend-inner-icon="mdi-lock"
              density="default"
              :show-copy="false"
              autocomplete="current-password"
              class="mb-4"
            />
            <v-btn
              type="submit"
              :loading="loading"
              block
              variant="tonal"
              color="primary"
              size="large"
              rounded="xl"
            >
              登 录
            </v-btn>
          </v-form>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<style scoped>
.app-logo {
  width: 40px;
  height: 40px;
  -webkit-mask: url('/favicon.svg') center / contain no-repeat;
  mask: url('/favicon.svg') center / contain no-repeat;
  background-color: rgb(var(--v-theme-primary));
}

/* 登录页输入框 — 在玻璃面板上增加微底色，提升可读性 */
:deep(.v-field--variant-outlined .v-field__outline) {
  --v-field-border-opacity: 0.5 !important;
}

:deep(.v-field--variant-outlined.v-field--focused .v-field__outline) {
  --v-field-border-opacity: 1 !important;
}
</style>
