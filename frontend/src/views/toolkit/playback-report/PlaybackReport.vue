<template>
  <div class="playback-report-container">
    <n-space vertical size="large">
      <!-- 页面标题区 -->
      <div class="page-header">
        <n-space align="center" justify="space-between">
          <div>
            <n-h2 prefix="bar" align-text>
              <n-text type="primary">播放统计报表</n-text>
            </n-h2>
            <n-text depth="3">实时洞察媒体库播放趋势、活跃用户与内容热度。</n-text>
          </div>
          <n-space align="center">
            <n-select 
              v-model:value="days" 
              :options="dayOptions" 
              style="width: 140px" 
              size="small"
              @update:value="fetchAllData" 
            />
            <n-button 
              strong 
              secondary 
              circle 
              type="primary" 
              :loading="loading" 
              @click="fetchAllData"
            >
              <template #icon>
                <n-icon><RefreshOutlined /></n-icon>
              </template>
            </n-button>
          </n-space>
        </n-space>
      </div>

      <!-- 第一行：核心指标 -->
      <OverviewStats :stats="stats" />

      <!-- 第二行：用户排行 (左) + 最近播放 (右) -->
      <n-grid :cols="24" :x-gap="12" :y-gap="12" item-responsive responsive="screen">
        <n-gi span="24 m:16">
          <n-card title="活跃用户排行榜" segmented size="small" class="report-card">
            <UserLeaderboard :users="usersWithBadges" />
          </n-card>
        </n-gi>
        <n-gi span="24 m:8">
          <n-card title="最近播放活动" segmented size="small" class="report-card">
            <n-scrollbar style="height: 600px">
              <div class="activity-list">
                <div v-for="(activity, index) in summary.user_activity.slice(0, 20)" :key="index" class="activity-item">
                  <div class="activity-poster">
                    <img 
                      :src="getImageUrl(activity)" 
                      class="mini-poster-img"
                      onerror="this.src='/favicon.svg'"
                    />
                  </div>
                  <div class="activity-info">
                    <div class="name-text" :title="activity.label">{{ activity.label }}</div>
                    <n-space :size="8" align="center">
                      <n-icon size="14" color="var(--primary-color)"><PeopleOutlined /></n-icon>
                      <n-text depth="2" style="font-size: 12px">{{ activity.user_name || activity.UserName }}</n-text>
                    </n-space>
                    <n-text depth="3" style="font-size: 11px">{{ activity.DateCreated?.split(' ')[0] || activity.date }}</n-text>
                  </div>
                  <div class="activity-badge" :class="{ 'is-live': !activity.duration }">
                    {{ activity.duration ? Math.round(activity.duration / 60) + 'm' : 'LIVE' }}
                  </div>
                </div>
              </div>
            </n-scrollbar>
          </n-card>
        </n-gi>
      </n-grid>

      <!-- 第三行：媒体排行 -->
      <n-card title="内容热度排行" segmented size="small" class="report-card">
        <MediaLeaderboard :movies="reports.movies" :tv-shows="reports.tvShows" :get-image-url="getImageUrl" />
      </n-card>

      <!-- 第四行：播放热度脉冲 -->
      <n-card title="24小时播放热度分布" segmented size="small" class="report-card">
        <ActivityHeatmap :hourly-data="reports.hourly" />
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { 
  NSpace, NIcon, NButton, NSelect, NGrid, NGi, NScrollbar, 
  NH2, NText, NCard 
} from 'naive-ui'
import { 
  RefreshOutlined, HistoryOutlined, PeopleOutlined 
} from '@vicons/material'
import { usePlaybackReport } from './usePlaybackReport'

import OverviewStats from './components/OverviewStats.vue'
import ActivityHeatmap from './components/ActivityHeatmap.vue'
import UserLeaderboard from './components/UserLeaderboard.vue'
import MediaLeaderboard from './components/MediaLeaderboard.vue'

const { loading, days, reports, stats, usersWithBadges, summary, fetchAllData, getImageUrl } = usePlaybackReport()

const dayOptions = [
  { label: '最近一周', value: 7 },
  { label: '最近双周', value: 14 },
  { label: '最近一月', value: 28 },
  { label: '最近一季', value: 90 },
  { label: '所有数据', value: 3650 }
]
</script>

<style scoped>
.playback-report-container {
  padding: 10px;
}

.page-header {
  margin-bottom: 20px;
}

.report-card {
  height: 100%;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  border-radius: 8px;
  background: var(--hover-bg);
  border: 1px solid var(--border-color);
  transition: all 0.2s ease;
}

.activity-item:hover {
  background: var(--hover-bg);
  transform: translateX(4px);
  border-color: var(--primary-color);
}

.activity-poster {
  width: 36px;
  height: 54px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.mini-poster-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.activity-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.name-text {
  font-weight: bold;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-badge {
  padding: 2px 8px;
  border-radius:4px;
  font-size: 10px;
  font-weight: bold;
  background: var(--hover-bg);
  color: var(--text-color-3);
}

.activity-badge.is-live {
  background: rgba(24, 160, 88, 0.15);
  color: #18a058;
}
</style>