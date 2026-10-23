<script setup lang="ts">
/**
 * 全局通知宿主（Vuetify snackbar）。
 *
 * 为什么要单独抽成一个组件：`useNotification()` 用的是模块级共享 state，
 * 但必须有地方把它渲染出来。之前 snackbar 只写在 DefaultLayout 里，
 * 而登录页 / 站点导航这类 `meta.standalone` 路由不套 DefaultLayout，
 * 于是这些页面里调用 error()/success() 只会改 state、屏幕上什么都不会出现
 * （典型症状：登录页输错密码没有任何提示）。
 *
 * 现在把它做成可复用组件：DefaultLayout 放一个，standalone 页面自己放一个。
 */
import { useNotification } from '@/composables'

const { state } = useNotification()
</script>

<template>
  <v-snackbar
    v-model="state.show"
    :color="state.color"
    :timeout="state.timeout"
    location="top right"
  >
    <div v-if="state.title" class="font-weight-bold mb-1">{{ state.title }}</div>
    {{ state.message }}
    <template #actions>
      <v-btn variant="text" icon="mdi-close" size="small" @click="state.show = false" />
    </template>
  </v-snackbar>
</template>
