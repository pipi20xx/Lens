<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import DesktopViewWrapper from './components/DesktopViewWrapper.vue'

// 导入桌面组件
import SiteNav from '../toolkit/sitenav/SiteNav.vue'
import BookmarkManager from '../toolkit/BookmarkManager.vue'
import TerminalManager from '../toolkit/terminal/TerminalManager.vue'
import DockerManager from '../toolkit/DockerManager.vue'
import EmbyLibraries from '../EmbyLibraries.vue'
import EmbyUsers from '../EmbyUsers.vue'
import CleanupTools from '../toolkit/CleanupTools.vue'
import NotificationManager from '../toolkit/NotificationManager.vue'
import TmdbLab from '../toolkit/TmdbLab.vue'
import Settings from '../Settings.vue'
// import DedupeManager from '../toolkit/DedupeManager.vue' // 有语法错误，暂时禁用
import TypeManager from '../toolkit/TypeManager.vue'
import LockManager from '../toolkit/LockManager.vue'
import AutoTagsManager from '../toolkit/autotags/AutoTagsManager.vue'
import ActorManager from '../toolkit/ActorManager.vue'
import EmbyItemQuery from '../toolkit/EmbyItemQuery.vue'
import TmdbReverseLookup from '../toolkit/TmdbReverseLookup.vue'
import TmdbIdSearch from '../toolkit/TmdbIdSearch.vue'
import BangumiLab from '../toolkit/BangumiLab.vue'
import AILab from '../toolkit/AILab.vue'
import ActorLab from '../toolkit/ActorLab.vue'
import ImageBuilder from '../toolkit/ImageBuilder.vue'
import PostgresManager from '../toolkit/PostgresManager.vue'
import BackupManager from '../toolkit/BackupManager.vue'
import WebhookReceiver from '../toolkit/WebhookReceiver.vue'
import AccountManager from '../toolkit/AccountManager.vue'
import ExternalControl from '../toolkit/ExternalControl.vue'
import PlaybackReport from '../toolkit/playback-report/PlaybackReport.vue'
import EmbyScheduledTasks from '../toolkit/emby-tasks/EmbyScheduledTasks.vue'

const route = useRoute()

// 工具名称映射
const toolNames: Record<string, string> = {
  'sitenav': '站点导航页',
  'bookmarks': '书签管理',
  'terminal': '终端管理',
  'docker': 'Docker 容器管理',
  'emby': 'Emby 媒体库管理',
  'cleanup': '媒体净化清理',
  'notifications': '通知消息中心',
  'tmdb': 'TMDB 实验中心',
  'tmdb-lab': 'TMDB 实验中心',
  'settings': '系统设置',
  'dedupe': '重复项清理',
  'type-manager': '类型映射管理',
  'lock': '元数据锁定器',
  'autotags': '自动标签助手',
  'actor-manager': '演员信息维护',
  'item-query': '项目元数据查询',
  'tmdb-lookup': '剧集 TMDB 反查',
  'tmdb-search': 'TMDB ID 深度搜索',
  'bangumi-lab': 'Bangumi 实验室',
  'ai-lab': 'AI 实验室',
  'actor-lab': 'TMDB 演员实验室',
  'image-builder': '镜像构建与推送',
  'postgres': 'PostgreSQL 管理',
  'backup': '数据备份管理',
  'webhook': 'Webhook 接收器',
  'account': '账号安全管理',
  'external-control': '外部控制体系',
  'reports': '播放统计报表',
  'tasks': 'Emby 任务计划',
}

// 当前工具名称
const currentToolName = computed(() => {
  const toolKey = route.params.tool as string
  return toolNames[toolKey] || '工具'
})

// 当前工具组件
const currentToolComponent = computed(() => {
  const toolKey = route.params.tool as string
  switch (toolKey) {
    case 'sitenav': return SiteNav
    case 'bookmarks': return BookmarkManager
    case 'terminal': return TerminalManager
    case 'docker': return DockerManager
    case 'emby': return EmbyLibraries
    case 'emby-users': return EmbyUsers
    case 'cleanup': return CleanupTools
    case 'notifications': return NotificationManager
    case 'tmdb':
    case 'tmdb-lab': return TmdbLab
    case 'settings': return Settings
    // case 'dedupe': return DedupeManager // 有语法错误，暂时禁用
    case 'type-manager': return TypeManager
    case 'lock': return LockManager
    case 'autotags': return AutoTagsManager
    case 'actor-manager': return ActorManager
    case 'item-query': return EmbyItemQuery
    case 'tmdb-lookup': return TmdbReverseLookup
    case 'tmdb-search': return TmdbIdSearch
    case 'bangumi-lab': return BangumiLab
    case 'ai-lab': return AILab
    case 'actor-lab': return ActorLab
    case 'image-builder': return ImageBuilder
    case 'postgres': return PostgresManager
    case 'backup': return BackupManager
    case 'webhook': return WebhookReceiver
    case 'account': return AccountManager
    case 'external-control': return ExternalControl
    case 'reports': return PlaybackReport
    case 'tasks': return EmbyScheduledTasks
    default: return null
  }
})
</script>

<template>
  <DesktopViewWrapper :title="currentToolName">
    <component :is="currentToolComponent" v-if="currentToolComponent" />
    <div v-else class="not-found">
      <p>工具未找到</p>
    </div>
  </DesktopViewWrapper>
</template>

<style scoped>
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: rgba(255, 255, 255, 0.5);
}
</style>
