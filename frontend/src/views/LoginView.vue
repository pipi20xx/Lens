<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '@/composables'
import { useNotification } from '@/composables'

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
  <div class="login-container min-h-screen d-flex align-center justify-center">
    <!-- 光晕动画 -->
    <div class="login-light-wells" />

    <v-card class="login-card liquid-glass-card pa-8" width="420" rounded="xl">
      <div class="text-center mb-8">
        <v-avatar class="liquid-avatar mb-4" size="64" rounded="xl">
          <v-icon icon="mdi-eye-outline" size="36" />
        </v-avatar>
        <h1 class="text-h4 font-weight-black liquid-glass-title mb-2">LENS</h1>
        <p class="text-body-2 text-medium-emphasis">导航与管理工具</p>
      </div>

      <v-form @submit.prevent="onSubmit">
        <v-text-field
          v-model="formValue.username"
          label="用户名"
          prepend-inner-icon="mdi-account-outline"
          variant="outlined"
          class="mb-2"
          autocomplete="username"
        />
        <v-text-field
          v-model="formValue.password"
          label="密码"
          type="password"
          prepend-inner-icon="mdi-lock-outline"
          variant="outlined"
          class="mb-6"
          autocomplete="current-password"
        />

        <v-btn
          type="submit"
          :loading="loading"
          block
          color="primary"
          size="large"
          variant="flat"
          rounded="xl"
          class="login-btn"
        >
          登 录
        </v-btn>
      </v-form>
    </v-card>
  </div>
</template>
