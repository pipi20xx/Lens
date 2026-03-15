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
import Settings from '../Settings.vue'
// import DedupeManager from '../toolkit/DedupeManager.vue' // 有语法错误，暂时禁用
import TypeManager from '../toolkit/TypeManager.vue'
import LockManager from '../toolkit/LockManager.vue'
import AutoTagsManager from '../toolkit/autotags/AutoTagsManager.vue'
import ActorManager from '../toolkit/ActorManager.vue'
import EmbyItemQuery from '../toolkit/EmbyItemQuery.vue'
import TmdbReverseLookup from '../toolkit/TmdbReverseLookup.vue'
import TmdbIdSearch from '../toolkit/TmdbIdSearch.vue'
import ImageBuilder from '../toolkit/ImageBuilder.vue'
import PostgresManager from '../toolkit/PostgresManager.vue'
import BackupManager from '../toolkit/BackupManager.vue'
import WebhookReceiver from '../toolkit/WebhookReceiver.vue'
import AccountManager from '../toolkit/AccountManager.vue'
import ExternalControl from '../toolkit/ExternalControl.vue'
import PlaybackReport from '../toolkit/playback-report/PlaybackReport.vue'
import EmbyScheduledTasks from '../toolkit/emby-tasks/EmbyScheduledTasks.vue'

// 导入移动端实验室组件
import MobileTmdbLab from './tools/MobileTmdbLab.vue'
import MobileBangumiLab from './tools/MobileBangumiLab.vue'
import MobileAILab from './tools/MobileAILab.vue'
import MobileActorLab from './tools/MobileActorLab.vue'
import MobileActorManager from './tools/MobileActorManager.vue'
import MobileMetadataLocker from './tools/MobileMetadataLocker.vue'
import MobileCleanupTools from './tools/MobileCleanupTools.vue'
import MobileTypeManager from './tools/MobileTypeManager.vue'
import MobileTmdbIdSearch from './tools/MobileTmdbIdSearch.vue'
import MobileTmdbReverseLookup from './tools/MobileTmdbReverseLookup.vue'
import MobileEmbyItemQuery from './tools/MobileEmbyItemQuery.vue'
import MobilePlaybackReport from './tools/MobilePlaybackReport.vue'
import MobileEmbyUsers from './tools/MobileEmbyUsers.vue'
import MobileEmbyLibraries from './tools/MobileEmbyLibraries.vue'
import MobileEmbyScheduledTasks from './tools/MobileEmbyScheduledTasks.vue'
import MobileTerminalManager from './tools/MobileTerminalManager.vue'
import MobileDockerManager from './tools/MobileDockerManager.vue'
import MobileImageBuilder from './tools/MobileImageBuilder.vue'
import MobilePostgresManager from './tools/MobilePostgresManager.vue'
import MobileBackupManager from './tools/MobileBackupManager.vue'
import MobileWebhookReceiver from './tools/MobileWebhookReceiver.vue'
import MobileNotificationManager from './tools/MobileNotificationManager.vue'
import MobileAccountManager from './tools/MobileAccountManager.vue'
import MobileExternalControl from './tools/MobileExternalControl.vue'
import MobileSiteNav from './tools/MobileSiteNav.vue'
import MobileBookmarkManager from './tools/MobileBookmarkManager.vue'
import MobileAutoTagsManager from './tools/MobileAutoTagsManager.vue'
import MobileSettings from './tools/MobileSettings.vue'
import MobileDedupe from './tools/MobileDedupe.vue'

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
    case 'sitenav': return MobileSiteNav
    case 'bookmarks': return MobileBookmarkManager
    case 'terminal': return MobileTerminalManager
    case 'docker': return MobileDockerManager
    case 'emby': return MobileEmbyLibraries
    case 'emby-users': return MobileEmbyUsers
    case 'cleanup': return MobileCleanupTools
    case 'notifications': return MobileNotificationManager
    case 'tmdb':
    case 'tmdb-lab': return MobileTmdbLab
    case 'settings': return MobileSettings
    case 'type-manager': return MobileTypeManager
    case 'lock': return MobileMetadataLocker
    case 'autotags': return MobileAutoTagsManager
    case 'actor-manager': return MobileActorManager
    case 'item-query': return MobileEmbyItemQuery
    case 'tmdb-lookup': return MobileTmdbReverseLookup
    case 'tmdb-search': return MobileTmdbIdSearch
    case 'bangumi-lab': return MobileBangumiLab
    case 'ai-lab': return MobileAILab
    case 'actor-lab': return MobileActorLab
    case 'image-builder': return MobileImageBuilder
    case 'postgres': return MobilePostgresManager
    case 'backup': return MobileBackupManager
    case 'webhook': return MobileWebhookReceiver
    case 'account': return MobileAccountManager
    case 'external-control': return MobileExternalControl
    case 'reports': return MobilePlaybackReport
    case 'tasks': return MobileEmbyScheduledTasks
    case 'dedupe': return MobileDedupe
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
