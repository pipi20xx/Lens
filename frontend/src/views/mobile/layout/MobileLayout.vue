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

<style>
/* 引入手机端全局样式 */
@import '../styles/index.css';
</style>

<style scoped>
.mobile-layout {
  width: 100vw;
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--app-bg-color);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  z-index: 100;
  transition: background-color 0.3s ease;
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
  padding-bottom: calc(var(--mobile-nav-height) + var(--mobile-safe-bottom));
}
</style>
