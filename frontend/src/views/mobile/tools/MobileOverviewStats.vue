<template>
  <div class="mobile-overview-stats">
    <n-grid :cols="2" :x-gap="8" :y-gap="8">
      <n-gi v-for="stat in statItems" :key="stat.title">
        <div class="stat-card">
          <div class="stat-icon" :style="{ color: stat.color }">
            <n-icon :size="24">
              <component :is="stat.icon" />
            </n-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stat.value }}</div>
            <div class="stat-label">{{ stat.title }}</div>
          </div>
        </div>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw } from 'vue'
import { NGrid, NGi, NIcon } from 'naive-ui'
import { 
  PlayArrowOutlined, 
  AccessTimeOutlined, 
  PeopleOutlined, 
  MovieOutlined 
} from '@vicons/material'

const props = defineProps<{
  stats: {
    totalPlays: number
    totalDuration: number
    activeUsers: number
    activeItems: number
  }
}>()

const statItems = computed(() => [
  {
    title: '总播放次数',
    value: props.stats.totalPlays,
    icon: markRaw(PlayArrowOutlined),
    color: '#18a058'
  },
  {
    title: '总播放时长',
    value: formatDuration(props.stats.totalDuration),
    icon: markRaw(AccessTimeOutlined),
    color: '#2080f0'
  },
  {
    title: '活跃用户',
    value: props.stats.activeUsers,
    icon: markRaw(PeopleOutlined),
    color: '#f0a020'
  },
  {
    title: '活跃内容',
    value: props.stats.activeItems,
    icon: markRaw(MovieOutlined),
    color: '#d03050'
  }
])

const formatDuration = (seconds: number) => {
  const s = Number(seconds) || 0
  if (s < 3600) return `${Math.round(s / 60)}m`
  return `${(s / 3600).toFixed(1)}h`
}
</script>

<style scoped>
.mobile-overview-stats {
  width: 100%;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.04);
  transition: all 0.2s ease;
}

.stat-card:hover {
  background: rgba(255, 255, 255, 0.04);
  transform: translateY(-2px);
  border-color: var(--n-primary-color);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 20px;
  font-weight: bold;
  color: var(--text-color);
  line-height: 1.2;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: var(--text-color-3);
  line-height: 1.2;
}
</style>
