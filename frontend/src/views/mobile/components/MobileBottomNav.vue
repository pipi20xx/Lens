<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  HomeOutlined as HomeIcon,
  AppsOutlined as AppsIcon,
  PersonOutlined as PersonIcon
} from '@vicons/material'
import { BottomNavItems } from '../constants'

const route = useRoute()
const router = useRouter()

// 使用常量并添加图标
const navItems = [
  { name: BottomNavItems[0].name, path: BottomNavItems[0].path, icon: HomeIcon },
  { name: BottomNavItems[1].name, path: BottomNavItems[1].path, icon: AppsIcon },
  { name: BottomNavItems[2].name, path: BottomNavItems[2].path, icon: PersonIcon },
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
