<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { systemApi } from '@/api/system'
import { useNotification } from '@/composables'

const { error: showError } = useNotification()
const stats = ref<any>({})
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await systemApi.getStats()
    stats.value = res
  } catch (err: any) {
    showError('加载统计信息失败')
  } finally {
    loading.value = false
  }
})

const statCards = [
  { title: 'Emby 用户', icon: 'mdi-account-group-outline', key: 'user_count', color: 'primary' },
  { title: '媒体库', icon: 'mdi-folder-multiple-outline', key: 'library_count', color: 'accent' },
  { title: 'Docker 容器', icon: 'mdi-docker', key: 'container_count', color: 'success' },
  { title: '今日播放', icon: 'mdi-play-circle-outline', key: 'today_plays', color: 'warning' },
]
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-6">
      <v-icon start>mdi-view-dashboard-outline</v-icon>
      管理仪表盘
    </h1>

    <!-- 统计卡片 -->
    <v-row class="mb-6">
      <v-col v-for="card in statCards" :key="card.key" cols="12" sm="6" md="3">
        <v-card class="liquid-glass-card pa-6" rounded="xl">
          <div class="d-flex align-center mb-3">
            <v-avatar :color="card.color" variant="tonal" size="48" rounded="xl" class="mr-4">
              <v-icon :icon="card.icon" size="24" />
            </v-avatar>
            <div>
              <div class="text-caption text-medium-emphasis">{{ card.title }}</div>
              <div class="text-h4 font-weight-bold">
                <v-skeleton-loader v-if="loading" type="text" width="60" />
                <template v-else>{{ stats[card.key] ?? '-' }}</template>
              </div>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- 快速入口 -->
    <h2 class="text-h6 font-weight-bold mb-4">
      <v-icon start>mdi-lightning-bolt-outline</v-icon>
      快速入口
    </h2>

    <v-row>
      <v-col v-for="item in [
        { title: 'Emby 用户管理', icon: 'mdi-account-group-outline', to: '/emby/users', desc: '管理 Emby 服务器用户' },
        { title: 'Docker 管理', icon: 'mdi-docker', to: '/toolkit/docker-manager', desc: '容器状态与操作' },
        { title: '播放报告', icon: 'mdi-chart-bar', to: '/emby/playback-report', desc: '查看播放统计' },
        { title: '站点导航', icon: 'mdi-compass-outline', to: '/toolkit/site-nav', desc: '自定义站点导航页' },
        { title: '备份管理', icon: 'mdi-backup-restore', to: '/toolkit/backup-manager', desc: '系统与数据备份' },
        { title: '系统设置', icon: 'mdi-cog-outline', to: '/settings', desc: '全局系统配置' },
      ]" :key="item.to" cols="12" sm="6" md="4">
        <v-card class="liquid-glass-card" :to="item.to" link rounded="xl">
          <v-card-title class="d-flex align-center pa-4">
            <v-avatar color="primary" variant="tonal" size="40" rounded="xl" class="mr-3">
              <v-icon :icon="item.icon" size="20" />
            </v-avatar>
            <div>
              <div class="text-subtitle-1 font-weight-bold">{{ item.title }}</div>
              <div class="text-caption text-medium-emphasis">{{ item.desc }}</div>
            </div>
          </v-card-title>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
