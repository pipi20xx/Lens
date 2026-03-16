<template>
  <div class="mobile-playback-report">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">播放统计报表</h1>
      <p class="page-desc">实时洞察媒体库播放趋势、活跃用户与内容热度</p>
    </div>

    <!-- 时间范围选择 -->
    <n-card class="filter-card" :bordered="false">
      <n-space justify="space-between" align="center">
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
    </n-card>

    <!-- 核心指标 -->
    <n-card class="stats-card" :bordered="false" title="核心指标">
      <MobileOverviewStats :stats="stats" />
    </n-card>

    <!-- 活跃用户排行榜 -->
    <n-card class="leaderboard-card" :bordered="false" title="活跃用户排行榜">
      <MobileUserLeaderboard :users="usersWithBadges" />
    </n-card>

    <!-- 最近播放活动 -->
    <n-card class="activity-card" :bordered="false" title="最近播放活动">
      <div v-if="summary.user_activity.length === 0" class="empty-state">
        <n-empty description="暂无活动" />
      </div>
      <div v-else class="activity-list">
        <div v-for="(activity, index) in summary.user_activity.slice(0, 10)" :key="index" class="activity-item">
          <div class="activity-poster">
            <img :src="getImageUrl(activity)" onerror="this.src='/favicon.svg'" />
          </div>
          <div class="activity-info">
            <div class="activity-name">{{ activity.label }}</div>
            <div class="activity-user">
              <n-icon size="12"><PeopleOutlined /></n-icon>
              {{ activity.user_name || activity.UserName }}
            </div>
            <div class="activity-time">{{ activity.DateCreated?.split(' ')[0] || activity.date }}</div>
          </div>
          <div class="activity-badge" :class="{ 'is-live': !activity.duration }">
            {{ activity.duration ? Math.round(activity.duration / 60) + 'm' : 'LIVE' }}
          </div>
        </div>
      </div>
    </n-card>

    <!-- 内容热度排行 -->
    <n-card class="media-card" :bordered="false" title="内容热度排行">
      <MobileMediaLeaderboard :movies="reports.movies" :tv-shows="reports.tvShows" :get-image-url="getImageUrl" />
    </n-card>

    <!-- 24小时播放热度 -->
    <n-card class="heatmap-card" :bordered="false" title="24小时播放热度">
      <MobileActivityHeatmap :hourly-data="reports.hourly" />
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { 
  NCard, NButton, NSelect, NEmpty, 
  NSpace, NIcon 
} from 'naive-ui'
import { 
  RefreshOutlined, PeopleOutlined 
} from '@vicons/material'
import { playbackReportApi } from '@/api/playbackReport'
import { useMessage } from 'naive-ui'
import request from '@/utils/request'
import MobileOverviewStats from './MobileOverviewStats.vue'
import MobileActivityHeatmap from './MobileActivityHeatmap.vue'
import MobileUserLeaderboard from './MobileUserLeaderboard.vue'
import MobileMediaLeaderboard from './MobileMediaLeaderboard.vue'

const message = useMessage()
const loading = ref(false)
const days = ref(28)
let timer: any = null

const dayOptions = [
  { label: '最近7天', value: 7 },
  { label: '最近14天', value: 14 },
  { label: '最近28天', value: 28 },
  { label: '最近90天', value: 90 }
]

const summary = reactive({
  user_activity: [] as any[],
  type_filters: [] as any[]
})

const reports = reactive({
  movies: [] as any[],
  tvShows: [] as any[],
  devices: [] as any[],
  users: [] as any[],
  hourly: {} as Record<string, number>
})

const stats = computed(() => {
  const totalPlays = reports.users.reduce((sum, u) => sum + (u.play_count || u.playCount || 0), 0)
  const totalDuration = reports.users.reduce((sum, u) => sum + (u.total_duration || u.totalDuration || 0), 0)
  const activeUsers = reports.users.length
  const activeItems = reports.movies.length + reports.tvShows.length
  return { totalPlays, totalDuration, activeUsers, activeItems }
})

const usersWithBadges = computed(() => {
  return reports.users.map((user, index) => ({
    ...user,
    label: user.name || user.user_name || user.UserName,
    count: user.play_count || user.playCount || 0,
    time: user.total_duration || user.totalDuration || 0,
    rank: index + 1,
    badges: []
  }))
})

const urlCache = new Map<string, string>()

const getImageUrl = (input: any, type: string = 'item') => {
  if (!input) return '/favicon.svg'
  const cacheKey = typeof input === 'object' 
    ? `${input.id || input.guid || input.searchName || input.label}-${type}`
    : `${input}-${type}`
  if (urlCache.has(cacheKey)) return urlCache.get(cacheKey)!

  let url = ''
  if (type === 'user') {
    const userId = typeof input === 'object' ? (input.id || input.UserId || input.user_id || input.userId) : input
    if (!userId || userId === 'undefined') return '/favicon.svg'
    url = `/api/playback-report/image-proxy?item_id=${userId}&type=user`
  } else {
    const id = input.guid || input.id || input.ItemId || input.item_id || ''
    // 关键：优先使用干净的搜索名称，避免使用带 S01E01 的装饰名称
    const name = input.searchName || input.label || input.Name || input.item_name || ''
    const itemType = input.type === 'Movie' ? 'Movie' : 'Series'

    if (id && String(id).length > 15) {
      url = `/api/playback-report/image-proxy?item_id=${id}&type=item`
    } else if (name && name !== 'undefined' && !name.includes(' - s') && !name.includes(' - S')) {
      url = `/api/playback-report/image-proxy?name=${encodeURIComponent(name)}&type=${itemType}`
    } else if (id) {
      url = `/api/playback-report/image-proxy?item_id=${id}&type=item`
    } else {
      return '/favicon.svg'
    }
  }
  urlCache.set(cacheKey, url)
  return url
}

// 解析项目 ID 并获取额外信息
const resolveItemsByIds = async (items: any[]) => {
  if (!items.length) return items
  const itemIds = items.map(i => i.id || i.ItemId || i.item_id).filter(id => id).join(',')
  if (!itemIds) return items

  try {
    const embyItems = await request.get('/api/server/items', { params: { ids: itemIds } }) as any[]
    if (!Array.isArray(embyItems)) return items
    
    return items.map(item => {
      const originalId = String(item.id || item.ItemId || item.item_id)
      const extra = embyItems.find(i => String(i.Id) === originalId || i.Name === (item.label || item.item_name))
      
      if (extra) {
        const isEpisode = extra.Type === 'Episode'
        const seriesName = extra.SeriesName || extra.Name
        const fullLabel = isEpisode ? `${seriesName} - ${extra.Name}` : extra.Name
        const searchName = isEpisode ? seriesName : extra.Name
        
        return {
          ...item,
          guid: extra.Id,
          id: extra.Id,
          label: fullLabel,
          searchName: searchName
        }
      }
      return item
    })
  } catch (e) {
    return items
  }
}

const formatDuration = (seconds: number) => {
  if (!seconds) return '0h'
  const hours = Math.floor(seconds / 3600)
  if (hours < 1) return Math.floor(seconds / 60) + 'm'
  if (hours < 24) return hours + 'h'
  return Math.floor(hours / 24) + 'd'
}

const fetchAllData = async () => {
  loading.value = true
  try {
    const [activityRes, moviesRes, tvRes, deviceRes, userRes, hourlyRes] = await Promise.all([
      playbackReportApi.getPlaylist(days.value),
      playbackReportApi.getReport('MoviesReport', days.value),
      playbackReportApi.getReport('TvShowsReport', days.value),
      playbackReportApi.getReport('DeviceName/BreakdownReport', days.value),
      playbackReportApi.getReport('UserId/BreakdownReport', days.value),
      playbackReportApi.getReport('HourlyReport', days.value)
    ])

    // API 返回的是 axios response，需要取 .data
    const activityData = (activityRes as any)?.data || activityRes
    const moviesData = (moviesRes as any)?.data || moviesRes
    const tvData = (tvRes as any)?.data || tvRes
    const deviceData = (deviceRes as any)?.data || deviceRes
    const userData = (userRes as any)?.data || userRes
    const hourlyData = (hourlyRes as any)?.data || hourlyRes

    const isOk = (res: any) => Array.isArray(res) && !res.error

    if (isOk(activityData)) {
      const rawActivities = activityData.map((i: any) => ({
        ...i,
        id: i.item_id || i.ItemId || i.id,
        label: i.item_name || i.label || i.Name,
        type: i.item_type || i.ItemType || i.type,
        user_name: i.user_name || i.UserName,
        duration: i.duration || i.Duration
      }))
      summary.user_activity = await resolveItemsByIds(rawActivities)
    } else {
      summary.user_activity = []
    }

    const rawMovies = isOk(moviesData) ? moviesData.map((i: any) => ({ ...i, type: 'Movie' })) : []
    const rawTv = isOk(tvData) ? tvData.map((i: any) => ({ ...i, type: 'Series' })) : []
    
    reports.movies = await resolveItemsByIds(rawMovies)
    reports.tvShows = await resolveItemsByIds(rawTv)
    reports.devices = isOk(deviceData) ? deviceData : []
    reports.users = isOk(userData) ? userData.map((u: any) => ({ ...u, id: u.UserId || u.id })) : []
    reports.hourly = (hourlyData && !hourlyData.error) ? hourlyData : {}
  } catch (err) {
    console.error('Failed to fetch playback report:', err)
    message.error('数据加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchAllData()
  timer = setInterval(fetchAllData, 60000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.mobile-playback-report {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.filter-card,
.stats-card,
.leaderboard-card,
.activity-card,
.media-card,
.heatmap-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
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
  background: var(--app-bg-color);
  border-radius: 8px;
}

.activity-poster {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.activity-poster img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.activity-info {
  flex: 1;
  min-width: 0;
}

.activity-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-user,
.activity-time {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-top: 2px;
}

.activity-user {
  display: flex;
  align-items: center;
  gap: 4px;
}

.activity-badge {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  background: var(--primary-color);
  border-radius: 10px;
}

.activity-badge.is-live {
  background: #d03050;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
