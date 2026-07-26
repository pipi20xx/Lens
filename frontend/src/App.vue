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

// 同步主题
function applyTheme(isDark: boolean) {
  const themeName = isDark ? 'dark' : 'light'
  if (typeof theme.change === 'function') {
    theme.change(themeName)
  } else {
    theme.global.name.value = themeName
  }
}

applyTheme(themeStore.isDarkMode)

watch(() => themeStore.isDarkMode, (val) => {
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
