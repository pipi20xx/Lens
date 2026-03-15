<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  HomeOutlined as HomeIcon,
  AppsOutlined as AppsIcon,
  SettingsOutlined as SettingsIcon,
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
.mobile-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: rgba(30, 30, 34, 0.95);
  backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding-bottom: env(safe-area-inset-bottom);
  z-index: 1000;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 16px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 12px;
}

.nav-item:active {
  transform: scale(0.95);
}

.nav-item.active {
  color: #705df2;
}

.nav-label {
  font-size: 11px;
  font-weight: 500;
}
</style>
