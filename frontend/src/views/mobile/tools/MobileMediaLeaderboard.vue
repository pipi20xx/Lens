<template>
  <div class="mobile-media-leaderboard">
    <MobileTabs v-model="activeTab" :tabs="tabs">
      <template #movies>
        <div v-if="movies.length === 0" class="empty-state">
          <n-empty description="暂无电影数据" />
        </div>
        <div v-else class="media-list">
          <div v-for="(item, index) in movies.slice(0, 10)" :key="item.id || index" class="media-item">
            <div class="media-rank" :class="{ 'top-3': index < 3 }">
              <span v-if="index === 0" class="rank-icon">👑</span>
              <span v-else-if="index === 1" class="rank-icon">🥈</span>
              <span v-else-if="index === 2" class="rank-icon">🥉</span>
              <span v-else class="rank-number">{{ index + 1 }}</span>
            </div>
            
            <div class="media-poster">
              <img :src="getImageUrl(item)" onerror="this.src='/favicon.svg'" />
            </div>
            
            <div class="media-info">
              <div class="media-name" :title="item.label">{{ item.label }}</div>
              <div class="media-stats">
                <span class="play-count">{{ item.count }} 次播放</span>
                <span v-if="item.year" class="year">{{ item.year }}</span>
              </div>
              <div v-if="item.rating" class="rating">
                {{ item.rating.toFixed(1) }}
              </div>
            </div>
          </div>
        </div>
      </template>
      
      <template #tv>
        <div v-if="tvShows.length === 0" class="empty-state">
          <n-empty description="暂无剧集数据" />
        </div>
        <div v-else class="media-list">
          <div v-for="(item, index) in tvShows.slice(0, 10)" :key="item.id || index" class="media-item">
            <div class="media-rank" :class="{ 'top-3': index < 3 }">
              <span v-if="index === 0" class="rank-icon">👑</span>
              <span v-else-if="index === 1" class="rank-icon">🥈</span>
              <span v-else-if="index === 2" class="rank-icon">🥉</span>
              <span v-else class="rank-number">{{ index + 1 }}</span>
            </div>
            
            <div class="media-poster">
              <img :src="getImageUrl(item)" onerror="this.src='/favicon.svg'" />
            </div>
            
            <div class="media-info">
              <div class="media-name" :title="item.label">{{ item.label }}</div>
              <div class="media-stats">
                <span class="play-count">{{ item.count }} 次播放</span>
                <span v-if="item.year" class="year">{{ item.year }}</span>
              </div>
              <div v-if="item.rating" class="rating">
                {{ item.rating.toFixed(1) }}
              </div>
            </div>
          </div>
        </div>
      </template>
    </MobileTabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NEmpty } from 'naive-ui'
import MobileTabs from '../components/MobileTabs.vue'
const props = defineProps<{
  movies: any[]
  tvShows: any[]
  getImageUrl: (item: any) => string
}>()

const activeTab = ref('movies')

const tabs = [
  { name: 'movies', label: '电影' },
  { name: 'tv', label: '剧集' },
]
</script>

<style scoped>
.mobile-media-leaderboard {
  width: 100%;
}

.empty-state {
  padding: 40px 0;
}

.media-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.media-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.04);
  transition: all 0.2s ease;
}

.media-item:hover {
  background: rgba(255, 255, 255, 0.04);
  transform: translateX(4px);
  border-color: var(--n-primary-color);
}

.media-rank {
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

.media-poster {
  width: 60px;
  height: 90px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.1);
}

.media-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.media-name {
  font-size: 14px;
  font-weight: bold;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.media-stats {
  font-size: 12px;
  color: var(--text-color-3);
  display: flex;
  align-items: center;
  gap: 8px;
}

.play-count {
  color: var(--n-primary-color);
  font-weight: bold;
}

.year {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.rating {
  font-size: 12px;
  color: var(--text-color-3);
  display: flex;
  align-items: center;
  gap: 2px;
}
</style>
