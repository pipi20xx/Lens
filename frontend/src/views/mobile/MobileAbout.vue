<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  ArrowBackOutlined as BackIcon,
  CodeOutlined as GitHubIcon,
  LanguageOutlined as WebIcon,
  ArticleOutlined as DocIcon,
  ChevronRightOutlined as ChevronRightIcon
} from '@vicons/material'

const router = useRouter()

const features = [
  'Emby 媒体库管理',
  '播放统计报表',
  'TMDB 元数据查询',
  'Docker 容器管理',
  'PostgreSQL 管理',
  '数据备份与恢复',
  'Webhook 接收器',
  'AI 智能助手',
]

const links = [
  { name: 'GitHub 仓库', icon: GitHubIcon, url: 'https://github.com/lens/lens' },
  { name: '官方文档', icon: DocIcon, url: 'https://docs.lens.app' },
  { name: '官方网站', icon: WebIcon, url: 'https://lens.app' },
]

const goBack = () => {
  router.back()
}
</script>

<template>
  <div class="mobile-about">
    <!-- 头部 -->
    <header class="about-header">
      <div class="back-btn" @click="goBack">
        <n-icon size="24" :component="BackIcon" />
      </div>
      <h1 class="page-title">关于 Lens</h1>
      <div class="placeholder"></div>
    </header>

    <!-- 应用信息 -->
    <section class="app-info-section">
      <img src="/favicon.svg" alt="Lens" class="app-logo" />
      <h2 class="app-name">Lens</h2>
      <div class="app-version">v{{ __APP_VERSION__ }}</div>
      <p class="app-description">现代化的媒体服务器管理工具</p>
    </section>

    <!-- 功能列表 -->
    <section class="features-section">
      <h3 class="section-title">核心功能</h3>
      <div class="features-list">
        <div v-for="feature in features" :key="feature" class="feature-item">
          <div class="feature-dot"></div>
          <span>{{ feature }}</span>
        </div>
      </div>
    </section>

    <!-- 链接列表 -->
    <section class="links-section">
      <div class="links-list">
        <a
          v-for="link in links"
          :key="link.name"
          :href="link.url"
          target="_blank"
          class="link-item"
        >
          <div class="link-icon">
            <n-icon size="20" :component="link.icon" />
          </div>
          <span class="link-name">{{ link.name }}</span>
          <n-icon size="18" :component="ChevronRightIcon" class="arrow-icon" />
        </a>
      </div>
    </section>

    <!-- 版权信息 -->
    <footer class="copyright">
      <p>© 2024 Lens. All rights reserved.</p>
      <p>Made with ❤️ for media lovers</p>
    </footer>
  </div>
</template>

<style scoped>
.mobile-about {
  min-height: 100vh;
  background: var(--app-bg-color);
  padding-bottom: calc(24px + env(safe-area-inset-bottom));
  transition: background-color 0.3s ease;
}

/* 头部 */
.about-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: calc(12px + env(safe-area-inset-top));
  background: var(--card-bg-color);
  border-bottom: 1px solid var(--border-color);
}

.back-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.back-btn:active {
  background: var(--hover-bg);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0;
}

.placeholder {
  width: 40px;
}

/* 应用信息 */
.app-info-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 32px 20px;
  text-align: center;
}

.app-logo {
  width: 80px;
  height: 80px;
  margin-bottom: 16px;
}

.app-name {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color);
  margin-bottom: 4px;
}

.app-version {
  font-size: 14px;
  color: var(--primary-color);
  font-weight: 500;
  margin-bottom: 8px;
}

.app-description {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 功能列表 */
.features-section {
  padding: 0 20px;
  margin-bottom: 28px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 14px;
}

.features-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--card-bg-color);
  border-radius: 10px;
  font-size: 13px;
  color: var(--text-color);
  border: 1px solid var(--border-color);
}

.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-color);
  flex-shrink: 0;
}

/* 链接列表 */
.links-section {
  padding: 0 20px;
  margin-bottom: 32px;
}

.links-list {
  background: var(--card-bg-color);
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.link-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  text-decoration: none;
  border-bottom: 1px solid var(--border-color);
  transition: all 0.2s ease;
}

.link-item:last-child {
  border-bottom: none;
}

.link-item:active {
  background: var(--hover-bg);
}

.link-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: var(--primary-color);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.link-name {
  flex: 1;
  font-size: 15px;
  color: var(--text-color);
}

.arrow-icon {
  color: var(--text-secondary);
}

/* 版权信息 */
.copyright {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.8;
}

.copyright p {
  margin: 0;
}
</style>
