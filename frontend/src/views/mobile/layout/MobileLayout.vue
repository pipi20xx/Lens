<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import MobileBottomNav from '../components/MobileBottomNav.vue'

const route = useRoute()

// 判断是否显示底部导航
const showBottomNav = computed(() => {
  // 在登录页等页面不显示底部导航
  const hiddenPaths = ['/mobile/login']
  return !hiddenPaths.includes(route.path)
})
</script>

<template>
  <div class="mobile-layout">
    <!-- 主内容区域 -->
    <main class="mobile-main" :class="{ 'has-bottom-nav': showBottomNav }">
      <router-view />
    </main>
    
    <!-- 底部导航 -->
    <MobileBottomNav v-if="showBottomNav" />
  </div>
</template>

<style scoped>
.mobile-layout {
  width: 100vw;
  min-height: 100vh;
  min-height: 100dvh;
  background: #1e1e22;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  z-index: 100;
}

.mobile-main {
  flex: 1;
  width: 100%;
  padding: 0;
  box-sizing: border-box;
  overflow-x: hidden;
  overflow-y: auto;
}

.mobile-main.has-bottom-nav {
  padding-bottom: calc(64px + env(safe-area-inset-bottom));
}
</style>
