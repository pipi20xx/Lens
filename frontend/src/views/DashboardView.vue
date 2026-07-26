<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { systemApi } from '@/api/system'
import { useNotification } from '@/composables'

const router = useRouter()
const { success, error: showError } = useNotification()

const upgrading = ref(false)
const loading = ref(true)
const stats = ref<any>({})

const versionInfo = ref({
  current: 'v0.0.0',
  latest: 'v0.0.0',
  has_update: false,
  docker_hub: 'https://hub.docker.com/r/pipi20xx/lens',
})

async function fetchVersion() {
  try {
    const data: any = await systemApi.getVersion()
    if (data) versionInfo.value = { ...versionInfo.value, ...data }
  } catch { /* ignore */ }
}

async function fetchStats() {
  try {
    const res = await systemApi.getStats()
    stats.value = res || {}
  } catch { /* ignore */ }
  finally { loading.value = false }
}

async function handleUpgrade() {
  upgrading.value = true
  try {
    const res: any = await systemApi.upgrade()
    success(res?.message || '升级任务已启动')
    setTimeout(() => window.location.reload(), 20000)
  } catch (e: any) {
    showError(e?.response?.data?.detail || '启动升级失败')
    upgrading.value = false
  }
}

function navigateTo(path: string) { router.push(path) }

onMounted(() => { fetchVersion(); fetchStats() })

const statCards = [
  { title: 'Emby 用户', icon: 'mdi-account-group-outline', key: 'user_count', color: 'primary' },
  { title: '媒体库', icon: 'mdi-folder-multiple-outline', key: 'library_count', color: 'secondary' },
  { title: 'Docker 容器', icon: 'mdi-docker', key: 'container_count', color: 'success' },
  { title: '今日播放', icon: 'mdi-play-circle-outline', key: 'today_plays', color: 'warning' },
]

const quickLinks = [
  { title: 'Emby 用户管理', icon: 'mdi-account-group-outline', to: '/emby/users', desc: '管理 Emby 服务器用户' },
  { title: 'Docker 管理', icon: 'mdi-docker', to: '/toolkit/docker-manager', desc: '容器状态与操作' },
  { title: '播放报告', icon: 'mdi-chart-bar', to: '/emby/playback-report', desc: '查看播放统计' },
  { title: '站点导航', icon: 'mdi-compass-outline', to: '/toolkit/site-nav', desc: '自定义站点导航页' },
  { title: '备份管理', icon: 'mdi-backup-restore', to: '/toolkit/backup-manager', desc: '系统与数据备份' },
  { title: '系统设置', icon: 'mdi-cog-outline', to: '/settings', desc: '全局系统配置' },
]
</script>

<template>
  <v-container fluid class="pa-6">
    <!-- 页面标题 -->
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-view-dashboard-outline</v-icon>
      项目概览
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">Lens - 专注于 Emby 媒体库自动化管理与开发者工具箱的集成平台。</p>

    <v-row>
      <!-- 左侧：项目介绍 -->
      <v-col cols="12" md="8">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start color="primary">mdi-information-outline</v-icon>
            关于 Lens (Project Introduction)
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4" style="line-height:1.8">
            <p class="text-body-1 mb-4">
              Lens 是一款专为媒体发烧友和开发者打造的开源管理平台。它不仅是一个 Emby 的辅助工具，更是一个集成了自动化运维、元数据抓取、网络开发工具和系统监控的综合性 Workstation。
            </p>

            <h3 class="text-subtitle-1 font-weight-bold mb-3 mt-6" style="color:rgb(var(--v-theme-primary))">
              <v-icon start size="20" color="primary">mdi-star-outline</v-icon>
              核心特性 (Key Features)
            </h3>

            <v-list density="compact" class="bg-transparent">
              <v-list-item>
                <v-list-item-title><span class="font-weight-bold">智能媒体去重 (Dedupe Ultimate):</span> 基于 TMDB ID 与画质特征的深度比对引擎，支持安全拦截、内容互补识别及白名单路径保护。</v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-title><span class="font-weight-bold">自动化标签系统 (Auto-Tagging):</span> 通过规则引擎自动分析媒体属性，一键同步至 Emby，极大提升搜索与分拣体验。</v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-title><span class="font-weight-bold">开发者实验室 (Lab Center):</span> 深度集成 TMDB、Bangumi 等元数据 API 的探测工具，支持演员池全量生成与原名自动匹配。</v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-title><span class="font-weight-bold">全栈运维工具 (DevOps Toolkit):</span> 内置 Docker 容器管理、多主机 SSH 终端、PostgreSQL 备份还原以及多介质同步方案。</v-list-item-title>
              </v-list-item>
            </v-list>

            <h3 class="text-subtitle-1 font-weight-bold mb-3 mt-6" style="color:rgb(var(--v-theme-primary))">
              <v-icon start size="20" color="primary">mdi-eye-outline</v-icon>
              项目愿景 (Vision)
            </h3>
            <v-alert variant="tonal" color="primary" rounded="lg" class="mb-4">
              <em>"Make Media Management Invisible."</em><br />
              旨在通过高度自动化的手段，让用户告别繁琐的元数据纠偏，将精力集中在享受媒体内容本身。
            </v-alert>
          </v-card-text>
          <v-divider />
          <div class="d-flex ga-2 pa-4">
            <v-btn variant="tonal" color="primary" href="https://github.com/pipi20xx/Lens" target="_blank">GitHub 源码</v-btn>
            <v-btn variant="tonal" color="info" href="https://github.com/pipi20xx/Lens/issues" target="_blank">提交反馈 (Issues)</v-btn>
          </div>
        </v-card>
      </v-col>

      <!-- 右侧：系统状态 -->
      <v-col cols="12" md="4">
        <!-- 系统状态监控 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start size="20">mdi-monitor-dashboard</v-icon>
            系统状态监控
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-table density="compact" class="bg-transparent">
              <tbody>
                <tr>
                  <td class="text-medium-emphasis">运行版本 (Current)</td>
                  <td class="text-right">
                    <v-chip size="small" color="primary" variant="tonal">{{ versionInfo.current }}</v-chip>
                    <v-chip v-if="!versionInfo.has_update" size="small" color="success" variant="tonal" class="ml-1">Latest</v-chip>
                    <v-chip v-else size="small" color="error" variant="tonal" class="ml-1">Update Avail.</v-chip>
                  </td>
                </tr>
                <tr>
                  <td class="text-medium-emphasis">远端构建 (DockerHub)</td>
                  <td class="text-right">
                    <span class="font-mono text-body-2">{{ versionInfo.latest }}</span>
                    <v-btn v-if="versionInfo.docker_hub" icon variant="tonal" size="x-small" class="ml-1" :href="versionInfo.docker_hub" target="_blank">
                      <v-icon size="14">mdi-docker</v-icon>
                    </v-btn>
                  </td>
                </tr>
                <tr>
                  <td class="text-medium-emphasis">运行环境 (Env)</td>
                  <td class="text-right"><v-chip size="small" color="info" variant="tonal">Lens Core v2</v-chip></td>
                </tr>
              </tbody>
            </v-table>

            <v-alert v-if="versionInfo.has_update" variant="tonal" type="warning" density="compact" class="mt-3" rounded="lg">
              检测到新版本 {{ versionInfo.latest }}，请及时更新。
            </v-alert>
          </v-card-text>
          <v-divider />
          <div class="pa-4 d-flex flex-column ga-2">
            <v-btn v-if="versionInfo.has_update" block color="warning" variant="flat" :loading="upgrading" @click="handleUpgrade">
              {{ upgrading ? '正在执行更新任务...' : '立即执行系统升级' }}
            </v-btn>
            <v-btn block color="primary" variant="tonal" @click="navigateTo('/settings')">配置中心</v-btn>
          </div>
        </v-card>

        <!-- 统计卡片 -->
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start size="20">mdi-chart-box-outline</v-icon>
            数据概览
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-row>
              <v-col v-for="card in statCards" :key="card.key" cols="6">
                <div class="text-center">
                  <v-avatar :color="card.color" variant="tonal" size="40" rounded="xl" class="mb-2">
                    <v-icon :icon="card.icon" size="20" />
                  </v-avatar>
                  <div class="text-h5 font-weight-bold">
                    <v-skeleton-loader v-if="loading" type="text" width="40" class="mx-auto" />
                    <template v-else>{{ stats[card.key] ?? '-' }}</template>
                  </div>
                  <div class="text-caption text-medium-emphasis">{{ card.title }}</div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 快速入口 -->
    <h2 class="text-h6 font-weight-bold mt-6 mb-4">
      <v-icon start>mdi-lightning-bolt-outline</v-icon>
      快速入口
    </h2>
    <v-row>
      <v-col v-for="item in quickLinks" :key="item.to" cols="12" sm="6" md="4">
        <v-card class="liquid-glass-card" link rounded="xl" @click="navigateTo(item.to)">
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
