<template>
  <div class="mobile-user-leaderboard">
    <div v-if="users.length === 0" class="empty-state">
      <n-empty description="暂无用户数据" />
    </div>
    <div v-else class="user-list">
      <div v-for="(user, index) in users.slice(0, 10)" :key="user.id || index" class="user-item">
        <div class="user-rank" :class="{ 'top-3': index < 3 }">
          <span v-if="index === 0" class="rank-icon">👑</span>
          <span v-else-if="index === 1" class="rank-icon">🥈</span>
          <span v-else-if="index === 2" class="rank-icon">🥉</span>
          <span v-else class="rank-number">{{ index + 1 }}</span>
        </div>
        
        <div class="user-avatar">
          <img :src="getUserAvatar(user)" onerror="this.src='/favicon.svg'" />
        </div>
        
        <div class="user-info">
          <div class="user-name" :title="user.label">{{ user.label }}</div>
          <div class="user-stats">
            <span class="play-count">{{ user.count }} 次播放</span>
            <span class="divider">·</span>
            <span class="duration">{{ formatDuration(user.time) }}</span>
          </div>
          <div v-if="user.badges && user.badges.length > 0" class="badges">
            <span v-for="badge in user.badges.slice(0, 3)" :key="badge.text" class="badge" :style="{ color: badge.color }">
              <n-icon :size="12"><component :is="markRaw(badge.icon)" /></n-icon>
              {{ badge.text }}
            </span>
          </div>
        </div>
        
        <div class="user-progress">
          <div 
            class="progress-bar" 
            :style="{ 
              width: getProgressWidth(user.count) + '%',
              background: getProgressColor(index)
            }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw } from 'vue'
import { NIcon, NEmpty } from 'naive-ui'

const props = defineProps<{
  users: any[]
}>()

const maxCount = computed(() => {
  if (props.users.length === 0) return 1
  return Math.max(...props.users.map(u => u.count || 0))
})

const getUserAvatar = (user: any) => {
  if (user.avatar && user.avatar !== 'null' && user.avatar !== 'undefined') {
    return user.avatar
  }
  
  const rank = props.users.findIndex(u => u.id === user.id) + 1
  const colorMap: Record<number, string> = {
    1: '#f0a020',
    2: '#c0c0c0',
    3: '#b87333'
  }
  
  const mainColor = colorMap[rank] || '#444'
  const iconColor = (rank >= 1 && rank <= 3) ? '#ffffff' : '#888'
  
  const svg = `
    <svg viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg">
      <circle cx="64" cy="64" r="64" fill="${mainColor}"/>
      <path d="M64 30c11 0 20 9 20 20s-9 20-20 20-20-9-20-20 9-20 20-20zm0 45c20 0 38 12 44 30H20c6-18 24-30 44-30z" fill="${iconColor}"/>
    </svg>
  `.trim()
  
  return `data:image/svg+xml;base64,${btoa(svg)}`
}

const formatDuration = (seconds: number) => {
  const s = Number(seconds) || 0
  if (s < 3600) return `${Math.round(s / 60)}m`
  return `${(s / 3600).toFixed(1)}h`
}

const getProgressWidth = (count: number) => {
  if (maxCount.value === 0) return 0
  return (count / maxCount.value) * 100
}

const getProgressColor = (index: number) => {
  if (index === 0) return '#f0a020'
  if (index === 1) return '#c0c0c0'
  if (index === 2) return '#b87333'
  return 'var(--n-primary-color)'
}
</script>

<style scoped>
.mobile-user-leaderboard {
  width: 100%;
}

.empty-state {
  padding: 40px 0;
}

.user-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.04);
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.user-item:hover {
  background: rgba(255, 255, 255, 0.04);
  transform: translateX(4px);
  border-color: var(--n-primary-color);
}

.user-rank {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.rank-icon {
  font-size: 24px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
}

.rank-number {
  font-size: 16px;
  font-weight: 900;
  font-style: italic;
  color: var(--text-color-3);
}

.top-3 .rank-number {
  display: none;
}

.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.1);
}

.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 15px;
  font-weight: bold;
  color: var(--text-color);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-stats {
  font-size: 12px;
  color: var(--text-color-3);
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
}

.play-count {
  color: var(--n-primary-color);
  font-weight: bold;
}

.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.badge {
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
}

.user-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: rgba(255, 255, 255, 0.05);
}

.progress-bar {
  height: 100%;
  transition: width 0.5s ease;
  border-radius: 0 2px 2px 0;
}
</style>
