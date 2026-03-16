<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import { ArrowBackOutlined as BackIcon } from '@vicons/material'

const router = useRouter()

const props = defineProps<{
  title: string
}>()

const goBack = () => {
  router.back()
}
</script>

<template>
  <div class="desktop-view-wrapper">
    <!-- 移动端头部 -->
    <header class="mobile-header">
      <div class="back-btn" @click="goBack">
        <n-icon size="24"><BackIcon /></n-icon>
      </div>
      <h1 class="page-title">{{ title }}</h1>
      <div class="placeholder"></div>
    </header>

    <!-- 桌面组件容器 -->
    <div class="desktop-content">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.desktop-view-wrapper {
  width: 100vw;
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--app-bg-color, #1e1e22);
  display: flex;
  flex-direction: column;
}

.mobile-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: calc(12px + env(safe-area-inset-top));
  background: var(--sidebar-bg-color, rgba(255, 255, 255, 0.02));
  border-bottom: 1px solid var(--border-color, rgba(255, 255, 255, 0.05));
  flex-shrink: 0;
}

.back-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-color, rgba(255, 255, 255, 0.7));
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.back-btn:active {
  background: rgba(255, 255, 255, 0.08);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color, rgba(255, 255, 255, 0.95));
  margin: 0;
}

.placeholder {
  width: 40px;
}

.desktop-content {
  flex: 1;
  overflow: visible;
  padding: 16px;
  position: relative;
}

/* 适配桌面组件在移动端的显示 */
.desktop-content :deep(*) {
  max-width: 100%;
}

.desktop-content :deep(.n-card) {
  margin-bottom: 16px;
}

.desktop-content :deep(.n-button) {
  white-space: nowrap;
}

.desktop-content :deep(.n-data-table) {
  font-size: 14px;
}

.desktop-content :deep(.n-data-table .n-data-table-th),
.desktop-content :deep(.n-data-table .n-data-table-td) {
  padding: 8px 12px;
}

/* 修复 aria-hidden 警告 */
.desktop-content :deep([aria-hidden="true"]) {
  display: none !important;
}
</style>

<style>
/* 全局 Switch 样式 - 非 scoped 确保覆盖 naive-ui */
.mobile-switch .n-switch__rail {
  background-color: #9ca3af !important;
}

.mobile-switch.n-switch--active .n-switch__rail {
  background-color: var(--primary-color) !important;
}
</style>
