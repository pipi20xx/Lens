<script setup lang="ts">
import { useRouter } from 'vue-router'
import DesktopViewWrapper from './components/DesktopViewWrapper.vue'
import Settings from '../Settings.vue'

const router = useRouter()
</script>

<template>
  <DesktopViewWrapper title="系统设置">
    <Settings />
  </DesktopViewWrapper>
</template>
