<template>
  <div class="dashboard-page">
    <n-space vertical size="large">
      <!-- 页面标题区 -->
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">项目概览</n-text></n-h2>
        <n-text depth="3">Lens - 专注于 Emby 媒体库自动化管理与开发者工具箱的集成平台。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：项目介绍 -->
        <n-gi span="24 m:16">
          <n-card title="关于 Lens (Project Introduction)" segmented>
            <div class="intro-content">
              <n-p>
                Lens 是一款专为媒体发烧友和开发者打造的开源管理平台。它不仅是一个 Emby 的辅助工具，更是一个集成了自动化运维、元数据抓取、网络开发工具和系统监控的综合性 Workstation。
              </n-p>
              
              <n-h3 prefix="bar">核心特性 (Key Features)</n-h3>
              <n-ul>
                <n-li>
                  <n-text strong>智能媒体去重 (Dedupe Ultimate):</n-text>
                  基于 TMDB ID 与画质特征的深度比对引擎，支持安全拦截、内容互补识别及白名单路径保护。
                </n-li>
                <n-li>
                  <n-text strong>自动化标签系统 (Auto-Tagging):</n-text>
                  通过规则引擎自动分析媒体属性，一键同步至 Emby，极大提升搜索与分拣体验。
                </n-li>
                <n-li>
                  <n-text strong>开发者实验室 (Lab Center):</n-text>
                  深度集成 TMDB、Bangumi 等元数据 API 的探测工具，支持演员池全量生成与原名自动匹配。
                </n-li>
                <n-li>
                  <n-text strong>全栈运维工具 (DevOps Toolkit):</n-text>
                  内置 Docker 容器管理、多主机 SSH 终端、PostgreSQL 备份还原以及多介质同步方案。
                </n-li>
              </n-ul>

              <n-h3 prefix="bar">项目愿景 (Vision)</n-h3>
              <n-blockquote>
                "Make Media Management Invisible."
                <br />
                旨在通过高度自动化的手段，让用户告别繁琐的元数据纠偏，将精力集中在享受媒体内容本身。
              </n-blockquote>
            </div>
            
            <template #footer>
              <n-space>
                <n-button quaternary type="primary" tag="a" href="https://github.com/pipi20xx/Lens" target="_blank">
                  GitHub 源码
                </n-button>
                <n-button quaternary type="info" tag="a" href="https://github.com/pipi20xx/Lens/issues" target="_blank">
                  提交反馈 (Issues)
                </n-button>
              </n-space>
            </template>
          </n-card>
        </n-gi>

        <!-- 右侧：系统信息区 -->
        <n-gi span="24 m:8">
          <n-card title="系统状态监控" segmented size="small">
            <n-list size="small">
              <n-list-item>
                <n-space justify="space-between">
                  <n-text depth="3">运行版本 (Current)</n-text>
                  <n-space :size="4" align="center">
                    <n-tag size="small" type="primary" quaternary>{{ versionInfo.current }}</n-tag>
                    <n-tag v-if="!versionInfo.has_update" size="small" type="success" quaternary>Latest</n-tag>
                    <n-tag v-else size="small" type="error" quaternary>Update Avail.</n-tag>
                  </n-space>
                </n-space>
              </n-list-item>
              <n-list-item>
                <n-space justify="space-between" align="center">
                  <n-text depth="3">远端构建 (DockerHub)</n-text>
                  <n-space :size="8" align="center">
                    <n-text style="font-size: 13px; font-family: monospace">{{ versionInfo.latest }}</n-text>
                    <n-button 
                      v-if="versionInfo.docker_hub"
                      text 
                      tag="a" 
                      :href="versionInfo.docker_hub" 
                      target="_blank" 
                      type="primary"
                    >
                      <n-icon size="16"><DockerIcon /></n-icon>
                    </n-button>
                  </n-space>
                </n-space>
              </n-list-item>
              <n-list-item>
                <n-space justify="space-between">
                  <n-text depth="3">运行环境 (Env)</n-text>
                  <n-tag size="small" type="info" quaternary>Lens Core v2</n-tag>
                </n-space>
              </n-list-item>
            </n-list>
            
            <n-alert v-if="versionInfo.has_update" type="warning" size="small" :bordered="false" style="margin-top: 12px">
              检测到新版本 {{ versionInfo.latest }}，请及时更新。
            </n-alert>

            <template #footer>
              <n-space vertical>
                <n-button 
                  v-if="versionInfo.has_update" 
                  block 
                  size="small" 
                  type="warning" 
                  :loading="upgrading"
                  @click="handleUpgrade"
                >
                  {{ upgrading ? '正在执行更新任务...' : '立即执行系统升级' }}
                </n-button>
                <n-button block size="small" type="primary" secondary @click="navigateTo('SettingsView')">
                  配置中心
                </n-button>
              </n-space>
            </template>
          </n-card>
        </n-gi>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  NSpace, NGrid, NGi, NCard, NIcon, NText, 
  NH2, NH3, NP, NUl, NLi, NBlockquote,
  NList, NListItem, NTag, NButton, NAlert, useMessage
} from 'naive-ui'
import axios from 'axios'
import {
  CodeOutlined as CodeIcon,
  BugReportOutlined as BugIcon,
  DnsRound as DockerIcon,
  SettingsOutlined as SettingsIcon,
  SystemUpdateAltOutlined as UpgradeIcon
} from '@vicons/material'
import { currentViewKey } from '../store/navigationStore'

const message = useMessage()
const upgrading = ref(false)

const versionInfo = ref({
  current: 'v2.5.8',
  latest: 'v2.5.8',
  has_update: false,
  docker_hub: 'https://hub.docker.com/r/pipi20xx/lens'
})

const handleUpgrade = async () => {
  upgrading.value = true
  try {
    const res = await axios.post('/api/system/upgrade')
    message.success(res.data.message, { duration: 10000 })
    setTimeout(() => {
      window.location.reload()
    }, 20000)
  } catch (e: any) {
    message.error(e.response?.data?.detail || '启动升级失败')
    upgrading.value = false
  }
}

const navigateTo = (key: string) => {
  currentViewKey.value = key
}

const fetchVersion = async () => {
  try {
    const res = await axios.get('/api/system/version')
    if (res.data) {
      versionInfo.value = res.data
    }
  } catch (e) {
    console.error('Failed to fetch version:', e)
  }
}

onMounted(() => {
  fetchVersion()
})
</script>

<style scoped>
.dashboard-page {
  width: 100%;
}
:deep(.n-list-item) {
  padding: 8px 0 !important;
}
.intro-content {
  line-height: 1.6;
}
.n-h3 {
  margin-top: 24px !important;
  margin-bottom: 12px !important;
}
</style>
