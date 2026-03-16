<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  HomeOutlined as HomeIcon,
  AppsOutlined as AppsIcon,
  PersonOutlined as PersonIcon
} from '@vicons/material'

const route = useRoute()
const router = useRouter()

const navItems = [
  { name: '首页', path: '/mobile/home', icon: HomeIcon },
  { name: '工具', path: '/mobile/tools', icon: AppsIcon },
  { name: '我的', path: '/mobile/profile', icon: PersonIcon },
]

const activePath = computed(() => route.path)

const navigateTo = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="mobile-bottom-nav">
    <div
      v-for="item in navItems"
      :key="item.path"
      class="nav-item"
      :class="{ active: activePath === item.path || activePath.startsWith(item.path + '/') }"
      @click="navigateTo(item.path)"
    >
      <n-icon size="24" :component="item.icon" />
      <span class="nav-label">{{ item.name }}</span>
    </div>
  </div>
</template>

<style scoped>
/* 样式已迁移至 ../styles/index.css */
</style>
