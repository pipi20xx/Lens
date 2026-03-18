<template>
  <div class="media-pulse-container">
    <div v-for="section in sections" :key="section.title" class="pulse-section">
      <div class="section-title">
        <n-icon :size="24"><component :is="section.icon" /></n-icon>
        <span>{{ section.title }}</span>
      </div>
      
      <div class="pulse-row">
        <div v-for="(item, index) in section.data.slice(0, 10)" :key="item.id || index" class="pulse-item">
          <!-- 背景光晕 -->
          <div class="rank-glow" :class="'glow-' + (index + 1)"></div>
          
          <div class="item-container" :class="'frame-rank-' + (index + 1)">
            <!-- 皇冠与奖章图标 -->
            <div class="top-honor" v-if="index < 3">
              <span v-if="index === 0" class="honor-icon crown">👑</span>
              <span v-if="index === 1" class="honor-icon medal">🥈</span>
              <span v-if="index === 2" class="honor-icon medal">🥉</span>
            </div>

            <!-- 霸气的数字排行 (现在在奖框后方一点) -->
            <div class="big-rank-number" :class="'text-rank-' + (index + 1)">
              {{ index + 1 }}
            </div>

            <!-- 海报主体 (包裹在奖框中) -->
            <div class="main-poster-wrapper">
              <img :src="getImageUrl(item)" class="main-poster" onerror="this.src='/fallback-poster.png'" />
              
              <!-- 播放量标签 (前三名变色) -->
              <div class="play-tag" :class="'tag-rank-' + (index + 1)">
                {{ item.count }} 次播放
              </div>
              
              <!-- 顶部年份评分 -->
              <div class="poster-top-info" v-if="item.year || item.rating">
                <span v-if="item.rating" class="rating-val">⭐{{ item.rating.toFixed(1) }}</span>
                <span v-else-if="item.year">{{ item.year }}</span>
              </div>
            </div>
          </div>
          
          <div class="item-name" :title="item.label">{{ item.label }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { MovieOutlined, LiveTvOutlined } from '@vicons/material'

const props = defineProps<{
  movies: any[]
  tvShows: any[]
  getImageUrl: (item: any) => string
}>()

const sections = computed(() => [
  { title: '热门电影排行', icon: MovieOutlined, data: props.movies },
  { title: '热门剧集排行', icon: LiveTvOutlined, data: props.tvShows }
])
</script>

<style scoped>
.media-pulse-container { display: flex; flex-direction: column; gap: 60px; }
.section-title { display: flex; align-items: center; gap: 12px; font-size: 22px; font-weight: 900; color: var(--text-color); margin-bottom: 30px; padding-left: 10px; border-left: 5px solid var(--primary-color); }

.pulse-row { display: flex; gap: 40px; overflow-x: auto; padding: 40px 10px 30px 50px; scrollbar-width: none; }
.pulse-row::-webkit-scrollbar { display: none; }

.pulse-item { position: relative; flex: 0 0 180px; display: flex; flex-direction: column; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.pulse-item:hover { transform: translateY(-15px) scale(1.05); z-index: 10; }

.item-container { position: relative; width: 160px; height: 240px; border-radius: 16px; }

/* 荣誉图标样式 */
.top-honor {
  position: absolute;
  top: -35px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
  pointer-events: none;
}
.honor-icon { font-size: 36px; filter: drop-shadow(0 0 10px rgba(0,0,0,0.5)); }
.crown { filter: drop-shadow(0 0 15px rgba(240, 160, 32, 0.8)); animation: float 3s ease-in-out infinite; }

/* 前三名专属奖框 */
.frame-rank-1 { border: 3px solid #f0a020; box-shadow: 0 0 25px rgba(240, 160, 32, 0.4); padding: 2px; }
.frame-rank-2 { border: 3px solid #c0c0c0; box-shadow: 0 0 20px rgba(192, 192, 192, 0.3); padding: 2px; }
.frame-rank-3 { border: 3px solid #b87333; box-shadow: 0 0 15px rgba(184, 115, 51, 0.3); padding: 2px; }

/* 超大排名数字 */
.big-rank-number {
  position: absolute;
  left: -55px;
  bottom: -15px;
  font-size: 110px;
  font-weight: 950;
  line-height: 0.8;
  font-style: italic;
  z-index: 5;
  pointer-events: none;
  filter: drop-shadow(4px 4px 10px rgba(0,0,0,0.9));
}

.text-rank-1 { color: #f0a020; -webkit-text-stroke: 1px #ffd700; }
.text-rank-2 { color: #c0c0c0; -webkit-text-stroke: 1px #e8e8e8; }
.text-rank-3 { color: #b87333; -webkit-text-stroke: 1px #cd7f32; }
.text-rank-4, .text-rank-5, .text-rank-6, .text-rank-7, .text-rank-8, .text-rank-9, .text-rank-10 { 
  color: var(--text-color); -webkit-text-stroke: 2px rgba(59,130,246,0.4); 
}

.main-poster-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 12px;
  overflow: hidden;
  background: #18181c;
  z-index: 2;
}

.main-poster { width: 100%; height: 100%; object-fit: cover; }

.play-tag {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  background: linear-gradient(transparent, rgba(59, 130, 246, 0.95));
  color: var(--text-color); font-size: 12px; font-weight: 900; padding: 15px 0 8px;
  text-align: center;
}
.tag-rank-1 { background: linear-gradient(transparent, rgba(240, 160, 32, 0.95)); color: #000; }
.tag-rank-2 { background: linear-gradient(transparent, rgba(192, 192, 192, 0.95)); color: #000; }
.tag-rank-3 { background: linear-gradient(transparent, rgba(184, 115, 51, 0.95)); }

.poster-top-info {
  position: absolute; top: 0; left: 0; right: 0;
  padding: 8px; background: linear-gradient(rgba(0,0,0,0.8), transparent);
  display: flex; justify-content: flex-end; font-size: 12px; color: var(--text-color); font-weight: 900;
}

.rating-val { color: #f0a020; text-shadow: 0 0 5px rgba(240, 160, 32, 0.5); }

.item-name {
  margin-top: 15px; font-size: 14px; font-weight: 800; color: var(--text-color);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  padding: 0 5px; text-align: center;
  width: 160px; margin: 15px auto 0 auto;
}

/* 动画 */
@keyframes float {
  0% { transform: translateX(-50%) translateY(0); }
  50% { transform: translateX(-50%) translateY(-10px); }
  100% { transform: translateX(-50%) translateY(0); }
}

.rank-glow {
  position: absolute; top: 10%; left: 10%; right: 10%; bottom: 10%;
  z-index: 0; filter: blur(50px); opacity: 0; transition: opacity 0.4s;
}
.pulse-item:hover .rank-glow { opacity: 0.5; }
.glow-1 { background: #f0a020; }
.glow-2 { background: #c0c0c0; }
.glow-3 { background: #b87333; }
</style>
