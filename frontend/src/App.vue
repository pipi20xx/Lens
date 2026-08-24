<script setup lang="ts">
import { watch, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import { useThemeStore, useSystemStore } from '@/stores'
import DefaultLayout from '@/layouts/DefaultLayout.vue'

const route = useRoute()
const theme = useTheme()
const themeStore = useThemeStore()
const systemStore = useSystemStore()

// 判断当前路由是否为独立全屏页面（不带 DefaultLayout）
const isStandalone = computed(() => route.meta.standalone === true)

// 同步主题：light → Vuetify light；dark/acg → Vuetify dark
function applyTheme(appTheme: 'light' | 'dark' | 'acg') {
  const vuetifyThemeName = appTheme === 'light' ? 'light' : 'dark'
  if (typeof theme.change === 'function') {
    theme.change(vuetifyThemeName)
  } else {
    theme.global.name.value = vuetifyThemeName
  }

  // ACG 玻璃 class 管理
  const html = document.documentElement
  if (appTheme === 'acg') {
    html.classList.add('glass-theme-acg')
  } else {
    html.classList.remove('glass-theme-acg')
  }
}

applyTheme(themeStore.appTheme)

watch(() => themeStore.appTheme, (val) => {
  applyTheme(val)
})

// 启动 WebSocket 连接
onMounted(() => {
  systemStore.connect()
})
</script>

<template>
  <router-view v-if="isStandalone" />
  <DefaultLayout v-else />
</template>
