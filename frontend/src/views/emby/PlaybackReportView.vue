<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { playbackReportApi } from '@/api/playbackReport'
import { useNotification } from '@/composables'

const { error: showError } = useNotification()

const loading = ref(false)
const days = ref(28)
let timer: ReturnType<typeof setInterval> | null = null

const dayOptions = [
  { title: '最近一周', value: 7 },
  { title: '最近双周', value: 14 },
  { title: '最近一月', value: 28 },
  { title: '最近一季', value: 90 },
  { title: '所有数据', value: 3650 },
]

// 数据存储
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

// 图片 URL 缓存
const urlCache = new Map<string, string>()

function getImageUrl(input: any, type: string = 'item') {
  if (!input) return ''
  const cacheKey = typeof input === 'object'
    ? `${input.id || input.guid || input.searchName || input.label}-${type}`
    : `${input}-${type}`
  if (urlCache.has(cacheKey)) return urlCache.get(cacheKey)!

  let url = ''
  if (type === 'user') {
    const userId = typeof input === 'object' ? (input.id || input.UserId || input.user_id) : input
    url = `/api/playback-report/image-proxy?item_id=${userId}&type=user`
  } else {
    const id = input.guid || input.id || input.ItemId || input.item_id || ''
    const name = input.searchName || input.label || input.Name || input.item_name || ''
    const itemType = input.type === 'Movie' ? 'Movie' : 'Series'

    if (id && String(id).length > 15) {
      url = `/api/playback-report/image-proxy?item_id=${id}&type=item`
    } else if (name && name !== 'undefined') {
      url = `/api/playback-report/image-proxy?name=${encodeURIComponent(name)}&type=${itemType}`
    } else if (id) {
      url = `/api/playback-report/image-proxy?item_id=${id}&type=item`
    }
  }
  urlCache.set(cacheKey, url)
  return url
}

// 统计数据
const stats = computed(() => {
  const totalPlay = reports.users.reduce((acc, cur) => acc + (Number(cur.count) || 0), 0)
  const totalDuration = reports.users.reduce((acc, cur) => acc + (Number(cur.time) || 0), 0)
  return {
    totalPlay,
    totalDuration: Math.round(totalDuration / 60),
    userCount: reports.users.length,
    deviceCount: reports.devices.length
  }
})

// 用户排行带徽章
const usersWithBadges = computed(() => {
  const maxTime = Math.max(...reports.users.map(u => Number(u.time) || 1))
  return reports.users.map((user, index) => {
    const badges: { text: string; color: string }[] = []
    const time = Number(user.time) || 0
    if (index === 0) badges.push({ text: '头号玩家', color: '#f0a020' })
    if (time > 36000) badges.push({ text: '肝帝', color: '#ff4d4f' })
    return { ...user, badges, avatar: getImageUrl(user.id, 'user'), percent: maxTime > 0 ? (time / maxTime) * 100 : 0, rank: index + 1 }
  })
})

// 高峰时段
const peakHour = computed(() => {
  let max = -1
  let hour = ''
  for (let i = 0; i < 24; i++) {
    const val = reports.hourly[`Hour-${i}`] || 0
    if (val > max) {
      max = val
      hour = String(i).padStart(2, '0')
    }
  }
  return max > 0 ? hour : null
})

// 格式化时长
function formatDuration(seconds: number) {
  const s = Number(seconds) || 0
  if (s < 3600) return `${Math.round(s / 60)}m`
  return `${(s / 3600).toFixed(1)}h`
}

// 获取排行颜色
function getRankColor(rank: number) {
  if (rank === 1) return '#f0a020'
  if (rank === 2) return '#c0c0c0'
  if (rank === 3) return '#b87333'
  return 'rgb(var(--v-theme-primary))'
}

// 获取默认头像 SVG
function getUserAvatar(user: any) {
  if (user.avatar && user.avatar !== 'null' && user.avatar !== 'undefined') {
    return user.avatar
  }
  const rank = user.rank
  const colorMap: Record<number, string> = { 1: '#f0a020', 2: '#c0c0c0', 3: '#b87333' }
  const mainColor = colorMap[rank] || '#444'
  const iconColor = (rank >= 1 && rank <= 3) ? '#ffffff' : '#888'
  const svg = `<svg viewBox="0 0 128 128" xmlns="http://www.w3.org/2000/svg"><circle cx="64" cy="64" r="64" fill="${mainColor}"/><path d="M64 30c11 0 20 9 20 20s-9 20-20 20-20-9-20-20 9-20 20-20zm0 45c20 0 38 12 44 30H20c6-18 24-30 44-30z" fill="${iconColor}"/></svg>`
  return `data:image/svg+xml;base64,${btoa(svg)}`
}

// 数据获取
async function fetchAllData(showLoading = true) {
  if (showLoading) loading.value = true
  try {
    urlCache.clear()
    const [activityRes, moviesRes, tvRes, deviceRes, userRes, hourlyRes] = await Promise.all([
      playbackReportApi.getPlaylist(days.value),
      playbackReportApi.getReport('MoviesReport', days.value),
      playbackReportApi.getReport('TvShowsReport', days.value),
      playbackReportApi.getReport('DeviceName/BreakdownReport', days.value),
      playbackReportApi.getReport('UserId/BreakdownReport', days.value),
      playbackReportApi.getReport('HourlyReport', days.value)
    ])

    const isOk = (res: any) => Array.isArray(res) && !res.error
    const sortByCount = (a: any, b: any) => (Number(b.count) || 0) - (Number(a.count) || 0)

    if (isOk(activityRes)) {
      summary.user_activity = (activityRes as any[]).map(i => ({
        ...i,
        id: i.item_id || i.ItemId || i.id,
        label: i.item_name || i.label || i.Name,
        type: i.item_type || i.ItemType || i.type
      }))
    }

    reports.movies = isOk(moviesRes) ? [...moviesRes].map(i => ({ ...i, type: 'Movie' })).sort(sortByCount) : []
    reports.tvShows = isOk(tvRes) ? [...tvRes].map(i => ({ ...i, type: 'Series' })).sort(sortByCount) : []
    reports.devices = isOk(deviceRes) ? deviceRes : []
    reports.users = isOk(userRes) ? [...userRes].map(u => ({ ...u, id: u.UserId || u.id })).sort(sortByCount) : []
    reports.hourly = (hourlyRes && !hourlyRes.error) ? hourlyRes : {}

  } catch {
    if (showLoading) showError('同步失败')
  } finally {
    if (showLoading) loading.value = false
  }
}

onMounted(() => {
  fetchAllData()
})

onUnmounted(() => {
  if (timer) { clearInterval(timer); timer = null }
})
</script>

<template>
  <v-container fluid class="pa-6">
    <!-- 页面标题区 -->
    <div class="d-flex align-center justify-space-between mb-4 flex-wrap">
      <div>
        <h1 class="text-h5 font-weight-bold mb-1">
          <v-icon start>mdi-chart-bar</v-icon>
          播放统计报表
        </h1>
        <p class="text-body-2 text-medium-emphasis">实时洞察媒体库播放趋势、活跃用户与内容热度。</p>
      </div>
      <div class="d-flex ga-2 align-center">
        <v-select v-model="days" :items="dayOptions" item-title="title" item-value="value" variant="outlined" density="compact" hide-details style="width:150px" @update:model-value="fetchAllData" />
        <v-btn icon variant="tonal" size="small" @click="fetchAllData" :loading="loading">
          <v-icon>mdi-refresh</v-icon>
        </v-btn>
      </div>
    </div>

    <!-- 第一行：核心指标 -->
    <v-row class="mb-6">
      <v-col v-for="stat in [
        { title: '累计播放次数', value: stats.totalPlay, icon: 'mdi-play-circle-outline', color: 'primary', unit: '次' },
        { title: '累计播放时长', value: stats.totalDuration, icon: 'mdi-clock-outline', color: 'success', unit: '分钟' },
        { title: '累计活跃用户', value: stats.userCount, icon: 'mdi-account-group-outline', color: 'warning', unit: '人' },
        { title: '覆盖设备终端', value: stats.deviceCount, icon: 'mdi-monitor-cellphone', color: 'error', unit: '台' },
      ]" :key="stat.title" cols="12" sm="6" md="3">
        <v-card class="liquid-glass-card pa-4" rounded="xl">
          <v-avatar :color="stat.color" variant="tonal" size="44" rounded="xl" class="mb-2">
            <v-icon :icon="stat.icon" size="22" />
          </v-avatar>
          <div class="text-caption text-medium-emphasis">{{ stat.title }}</div>
          <div class="text-h5 font-weight-bold">{{ stat.value }} <small class="text-caption text-medium-emphasis">{{ stat.unit }}</small></div>
        </v-card>
      </v-col>
    </v-row>

    <!-- 第二行：用户排行 (左) + 最近播放 (右) -->
    <v-row class="mb-6">
      <v-col cols="12" md="7">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-trophy-outline</v-icon>
            活跃用户排行榜
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div v-if="!usersWithBadges.length" class="text-center py-8 text-medium-emphasis">暂无数据</div>
            <template v-else>
              <!-- 领奖台 (Top 3) -->
              <div class="d-flex justify-center align-end ga-4 mb-6 pt-4">
                <div v-for="user in usersWithBadges.slice(0, 3)" :key="user.id"
                  class="d-flex flex-column align-center podium-item"
                  :style="{ order: user.rank === 1 ? 2 : user.rank === 2 ? 1 : 3 }"
                >
                  <div class="position-relative mb-3">
                    <div v-if="user.rank === 1" class="text-h4" style="position:absolute;top:-24px;left:50%;transform:translateX(-50%)">👑</div>
                    <v-avatar :size="user.rank === 1 ? 72 : 56" rounded="xl">
                      <v-img :src="getUserAvatar(user)" />
                    </v-avatar>
                    <v-chip size="x-small" :color="user.rank === 1 ? 'warning' : 'grey'" variant="flat" style="position:absolute;bottom:-4px;right:-4px">{{ user.rank }}</v-chip>
                  </div>
                  <div class="text-subtitle-2 font-weight-bold text-center" style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ user.label }}</div>
                  <div class="text-caption text-medium-emphasis">{{ user.count }}次 / {{ formatDuration(user.time) }}</div>
                  <div class="d-flex ga-1 mt-1">
                    <v-chip v-for="badge in user.badges" :key="badge.text" size="x-small" variant="tonal" :style="{ color: badge.color }">{{ badge.text }}</v-chip>
                  </div>
                </div>
              </div>

              <!-- 列表区 (4-10) -->
              <div class="d-flex flex-column ga-2">
                <div v-for="user in usersWithBadges.slice(3, 10)" :key="user.id"
                  class="d-flex align-center ga-3 pa-2 rounded-lg"
                  style="border: 1px solid rgba(var(--v-theme-on-surface), 0.08); transition: all 0.2s"
                >
                  <span class="text-caption font-weight-bold text-medium-emphasis" style="width:28px">#{{ user.rank }}</span>
                  <v-avatar size="32" rounded="xl">
                    <v-img :src="getUserAvatar(user)" />
                  </v-avatar>
                  <div class="flex-grow-1">
                    <div class="text-body-2 font-weight-bold">{{ user.label }}</div>
                    <div style="height:4px;border-radius:2px;background:rgba(var(--v-theme-on-surface),0.06);overflow:hidden">
                      <div :style="{ width: user.percent + '%', height: '100%', borderRadius: '2px', backgroundColor: getRankColor(user.rank) }" />
                    </div>
                  </div>
                  <div class="text-right">
                    <div class="text-body-2 font-weight-bold">{{ user.count }} <small class="text-caption">回</small></div>
                    <div class="text-caption text-medium-emphasis">{{ formatDuration(user.time) }}</div>
                  </div>
                </div>
              </div>
            </template>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="5">
        <v-card class="liquid-glass-card" rounded="xl" style="height:100%">
          <v-card-title class="pa-4">
            <v-icon start>mdi-history</v-icon>
            最近播放活动
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4" style="max-height:600px;overflow-y:auto">
            <div v-if="!summary.user_activity.length" class="text-center py-8 text-medium-emphasis">暂无播放活动</div>
            <div v-else class="d-flex flex-column ga-2">
              <div v-for="(activity, index) in summary.user_activity.slice(0, 20)" :key="index"
                class="d-flex align-center ga-3 pa-2 rounded-lg"
                style="border: 1px solid rgba(var(--v-theme-on-surface), 0.06); transition: all 0.2s"
              >
                <!-- 海报缩略图 -->
                <div style="width:36px;height:54px;flex-shrink:0;border-radius:4px;overflow:hidden;background:#222">
                  <img :src="getImageUrl(activity)" style="width:100%;height:100%;object-fit:cover" @error="($event.target as HTMLImageElement).src='/favicon.svg'" />
                </div>
                <!-- 信息 -->
                <div class="flex-grow-1" style="min-width:0">
                  <div class="text-body-2 font-weight-bold" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{{ activity.label }}</div>
                  <div class="text-caption text-medium-emphasis">
                    <v-icon size="12">mdi-account-outline</v-icon> {{ activity.user_name || activity.UserName }}
                  </div>
                  <div class="text-caption text-medium-emphasis">{{ activity.DateCreated?.split(' ')[0] || activity.date }}</div>
                </div>
                <!-- 时长标签 -->
                <v-chip size="x-small" :color="activity.duration ? 'default' : 'success'" variant="tonal">
                  {{ activity.duration ? Math.round(activity.duration / 60) + 'm' : 'LIVE' }}
                </v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 第三行：内容热度排行 -->
    <v-card class="liquid-glass-card mb-6" rounded="xl">
      <v-card-title class="pa-4">
        <v-icon start>mdi-fire</v-icon>
        内容热度排行
      </v-card-title>
      <v-divider />

      <!-- 电影排行 -->
      <v-card-text class="pa-4">
        <div class="text-subtitle-2 font-weight-bold mb-3">
          <v-icon start size="18">mdi-filmstrip</v-icon>
          热门电影排行
        </div>
        <div v-if="!reports.movies.length" class="text-center py-4 text-medium-emphasis">暂无电影数据</div>
        <div v-else class="d-flex ga-4 overflow-x-auto pb-4" style="scrollbar-width:none">
          <div v-for="(item, index) in reports.movies.slice(0, 10)" :key="item.id || index"
            class="flex-shrink-0" style="width:130px;transition:all 0.3s"
            @mouseenter="($event.currentTarget as HTMLElement).style.transform='translateY(-8px)'"
            @mouseleave="($event.currentTarget as HTMLElement).style.transform='none'"
          >
            <div class="position-relative" style="width:130px;height:195px;border-radius:12px;overflow:hidden;background:#222">
              <img :src="getImageUrl(item)" style="width:100%;height:100%;object-fit:cover" @error="($event.target as HTMLImageElement).src='/favicon.svg'" />
              <div style="position:absolute;bottom:0;left:0;right:0;padding:12px 4px 6px;background:linear-gradient(transparent,rgba(59,130,246,0.9));text-align:center">
                <span class="text-caption font-weight-bold text-white">{{ item.count }} 次播放</span>
              </div>
              <div v-if="index < 3" style="position:absolute;top:4px;right:4px;font-size:20px">
                {{ index === 0 ? '👑' : index === 1 ? '🥈' : '🥉' }}
              </div>
            </div>
            <div class="text-caption font-weight-bold mt-2 text-center" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ item.label }}</div>
          </div>
        </div>
      </v-card-text>

      <v-divider />

      <!-- 剧集排行 -->
      <v-card-text class="pa-4">
        <div class="text-subtitle-2 font-weight-bold mb-3">
          <v-icon start size="18">mdi-television-classic</v-icon>
          热门剧集排行
        </div>
        <div v-if="!reports.tvShows.length" class="text-center py-4 text-medium-emphasis">暂无剧集数据</div>
        <div v-else class="d-flex ga-4 overflow-x-auto pb-4" style="scrollbar-width:none">
          <div v-for="(item, index) in reports.tvShows.slice(0, 10)" :key="item.id || index"
            class="flex-shrink-0" style="width:130px;transition:all 0.3s"
            @mouseenter="($event.currentTarget as HTMLElement).style.transform='translateY(-8px)'"
            @mouseleave="($event.currentTarget as HTMLElement).style.transform='none'"
          >
            <div class="position-relative" style="width:130px;height:195px;border-radius:12px;overflow:hidden;background:#222">
              <img :src="getImageUrl(item)" style="width:100%;height:100%;object-fit:cover" @error="($event.target as HTMLImageElement).src='/favicon.svg'" />
              <div style="position:absolute;bottom:0;left:0;right:0;padding:12px 4px 6px;background:linear-gradient(transparent,rgba(59,130,246,0.9));text-align:center">
                <span class="text-caption font-weight-bold text-white">{{ item.count }} 次播放</span>
              </div>
              <div v-if="index < 3" style="position:absolute;top:4px;right:4px;font-size:20px">
                {{ index === 0 ? '👑' : index === 1 ? '🥈' : '🥉' }}
              </div>
            </div>
            <div class="text-caption font-weight-bold mt-2 text-center" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ item.label }}</div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- 第四行：24小时播放热度分布 -->
    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start>mdi-chart-bell-curve-cumulative</v-icon>
        24小时播放热度分布
        <v-spacer />
        <div v-if="peakHour" class="text-caption text-medium-emphasis">
          高峰时段: <strong class="text-primary">{{ peakHour }}:00</strong>
        </div>
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-4">
        <div v-if="!Object.keys(reports.hourly).length" class="text-center py-8 text-medium-emphasis">暂无热度数据</div>
        <div v-else class="d-flex align-end ga-1" style="height:200px">
          <div v-for="i in 24" :key="i" class="flex-grow-1 d-flex flex-column align-center" style="min-width:0">
            <div class="flex-grow-1 d-flex align-end" style="width:100%">
              <div
                :style="{
                  width: '100%',
                  minHeight: '4px',
                  height: Math.max(4, ((reports.hourly[`Hour-${i-1}`] || 0) / Math.max(...Array.from({length:24}, (_, j) => reports.hourly[`Hour-${j}`] || 1))) * 180) + 'px',
                  background: `linear-gradient(to top, rgb(var(--v-theme-primary)), rgba(var(--v-theme-primary), 0.6))`,
                  borderRadius: '4px 4px 0 0',
                  transition: 'height 0.5s ease'
                }"
              />
            </div>
            <span class="text-caption text-medium-emphasis" style="font-size:9px">{{ i - 1 }}h</span>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </v-container>
</template>

