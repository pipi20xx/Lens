<template>
  <div class="user-pulse-leaderboard">
    <!-- 领奖台 (Top 3) -->
    <div class="podium-container">
      <div v-for="user in podiumUsers" :key="user.id" class="podium-item" :class="'rank-' + user.rank">
        <div class="avatar-wrapper">
          <div class="rank-crown" v-if="user.rank === 1">👑</div>
          <div class="glow-ring"></div>
          <n-avatar
            round
            :size="user.rank === 1 ? 90 : 70"
            :src="getUserAvatar(user)"
            fallback-src="/favicon.svg"
            class="user-avatar"
          />
          <div class="rank-badge">{{ user.rank }}</div>
        </div>
        <div class="user-name" :title="user.label">{{ user.label }}</div>
        <div class="user-stats">
          <span class="count">{{ user.count }}次</span>
          <span class="divider">/</span>
          <span class="time">{{ formatDuration(user.time) }}</span>
        </div>
        <div class="badge-row">
          <div 
            v-for="badge in user.badges" 
            :key="badge.text" 
            class="achievement-chip" 
            :style="{ backgroundColor: badge.color + '15', color: badge.color }"
          >
            <n-icon><component :is="markRaw(badge.icon)" /></n-icon>
            {{ badge.text }}
          </div>
        </div>
      </div>
    </div>

    <!-- 列表区 (4-10) -->
    <div class="list-container">
      <div v-for="user in listUsers" :key="user.id" class="user-list-row">
        <div class="rank-num">#{{ user.rank }}</div>
        <n-avatar
          round
          size="medium"
          :src="getUserAvatar(user)"
          fallback-src="/favicon.svg"
        />
        <div class="main-info">
          <div class="name-line">
            <span class="name" :title="user.label">{{ user.label }}</span>
            <div class="mini-badges">
              <span v-for="badge in user.badges" :key="badge.text" :style="{ color: badge.color }">
                <n-icon><component :is="markRaw(badge.icon)" /></n-icon>
              </span>
            </div>
          </div>
          <!-- 活跃度进度条 -->
          <div class="progress-track">
            <div 
              class="progress-bar" 
              :style="{ width: user.percent + '%', backgroundColor: getRankColor(user.rank) }"
            ></div>
          </div>
        </div>
        <div class="data-info">
          <div class="val">{{ user.count }} <small>回</small></div>
          <div class="sub">{{ formatDuration(user.time) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw } from 'vue'
import { NAvatar, NIcon } from 'naive-ui'
import { 
  PeopleOutlined, 
  EmojiEventsOutlined, 
  LocalFireDepartmentOutlined, 
  HomeOutlined, 
  AutoAwesomeOutlined,
  NightsStayOutlined
} from '@vicons/material'

const props = defineProps<{
  users: any[]
}>()

const podiumUsers = computed(() => {
  const top3 = props.users.slice(0, 3)
  const result = []
  if (top3[1]) result.push(top3[1])
  if (top3[0]) result.push(top3[0])
  if (top3[2]) result.push(top3[2])
  return result
})

const listUsers = computed(() => props.users.slice(3, 10))

const getUserAvatar = (user: any) => {
  if (user.avatar && user.avatar !== 'null' && user.avatar !== 'undefined') {
    return user.avatar
  }
  
  const rank = user.rank
  const colorMap: Record<number, string> = {
    1: '#f0a020', // 金
    2: '#c0c0c0', // 银
    3: '#b87333'  // 铜
  }
  
  const mainColor = colorMap[rank] || '#444' // 其他默认深灰
  const iconColor = (rank >= 1 && rank <= 3) ? '#ffffff' : '#888'
  
  // 生成一个简单的 SVG 默认头像 (Base64)
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

const getRankColor = (rank: number) => {
  if (rank === 1) return '#f0a020'
  if (rank === 2) return '#c0c0c0'
  if (rank === 3) return '#b87333'
  return 'var(--primary-color)'
}
</script>

<style scoped>
.user-pulse-leaderboard {
  padding: 10px 0;
}

/* 领奖台样式 */
.podium-container {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 24px;
  margin-bottom: 40px;
  padding-top: 20px;
}

.podium-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  transition: transform 0.3s ease;
  width: 140px;
}
.podium-item:hover { transform: translateY(-5px); }

.avatar-wrapper {
  position: relative;
  margin-bottom: 12px;
}

.rank-1 { order: 2; margin-top: -20px; }
.rank-2 { order: 1; }
.rank-3 { order: 3; }

.rank-crown {
  position: absolute;
  top: -20px;
  left: 50%;
  transform: translateX(-50%) rotate(-10deg);
  font-size: 24px;
  z-index: 10;
  filter: drop-shadow(0 0 8px rgba(240, 160, 32, 0.6));
}

.glow-ring {
  position: absolute;
  top: -4px;
  left: -4px;
  right: -4px;
  bottom: -4px;
  border-radius: 50%;
  border: 2px solid transparent;
}
.rank-1 .glow-ring { border-color: #f0a020; box-shadow: 0 0 15px rgba(240, 160, 32, 0.3); }
.rank-2 .glow-ring { border-color: #c0c0c0; }
.rank-3 .glow-ring { border-color: #b87333; }

.rank-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 24px;
  height: 24px;
  background: #333;
  color: var(--text-color);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
  border: 2px solid var(--card-color);
}
.rank-1 .rank-badge { background: #f0a020; color: #000; }

.user-name {
  font-size: 15px;
  font-weight: bold;
  color: var(--text-color);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  width: 100%;
  text-align: center;
}

.user-stats {
  font-size: 12px;
  color: var(--text-color-3);
  margin-bottom: 10px;
}
.user-stats .count { color: var(--primary-color); font-weight: bold; }

.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
}

.achievement-chip {
  padding: 1px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 3px;
}

/* 列表样式 */
.list-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-list-row {
  background: var(--hover-bg);
  padding: 10px 16px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid var(--border-color);
  transition: all 0.2s;
}
.user-list-row:hover {
  background: var(--hover-bg);
  transform: translateX(4px);
  border-color: var(--primary-color);
}

.rank-num {
  font-size: 13px;
  font-weight: 900;
  font-style: italic;
  color: var(--text-color-3);
  width: 28px;
}

.main-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.name-line {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.name-line .name { 
  font-weight: bold; font-size: 14px; color: var(--text-color); 
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}
.mini-badges { display: flex; gap: 4px; font-size: 12px; }

.progress-track {
  height: 4px;
  background: var(--hover-bg);
  border-radius: 2px;
  width: 100%;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  border-radius: 2px;
  transition: width 1s ease-out;
}

.data-info {
  text-align: right;
}
.data-info .val { font-size: 14px; font-weight: bold; color: var(--text-color); }
.data-info .val small { font-size: 10px; color: var(--text-color-3); }
.data-info .sub { font-size: 11px; color: var(--text-color-3); }
</style>