<script setup lang="ts">
import { useRouter } from 'vue-router'
import { NIcon } from 'naive-ui'
import {
  ArrowBackOutlined as BackIcon,
  GitHubIcon,
  LanguageOutlined as WebIcon,
  EmailOutlined as EmailIcon
} from '@vicons/material'

const router = useRouter()

const goBack = () => {
  router.back()
}

const appInfo = {
  name: 'Lens',
  version: 'v2.5.6',
  description: '一个强大的媒体服务器管理工具',
  author: 'Lens Team',
  github: 'https://github.com/lens/lens',
  website: 'https://lens.app',
  email: 'support@lens.app'
}

const features = [
  'Emby 媒体库管理',
  'Docker 容器管理',
  '智能文件清理',
  '站点导航与书签',
  '通知推送服务',
  'TMDB 元数据工具'
]
</script>

<template>
  <div class="mobile-about">
    <!-- 头部 -->
    <header class="about-header">
      <div class="back-btn" @click="goBack">
        <n-icon size="24"><BackIcon /></n-icon>
      </div>
      <h1 class="page-title">关于</h1>
      <div class="placeholder"></div>
    </header>

    <!-- 应用信息 -->
    <div class="app-info-section">
      <div class="app-logo">
        <svg width="80" height="80" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <linearGradient id="lens_grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#705df2;stop-opacity:1" />
              <stop offset="100%" style="stop-color:#bb86fc;stop-opacity:1" />
            </linearGradient>
          </defs>
          <circle cx="100" cy="100" r="85" fill="none" stroke="url(#lens_grad)" stroke-width="15" />
          <circle cx="100" cy="100" r="55" fill="none" stroke="url(#lens_grad)" stroke-width="6" stroke-dasharray="20 10" opacity="0.6" />
          <circle cx="100" cy="100" r="25" fill="url(#lens_grad)" />
          <path d="M60 60 A60 60 0 0 1 140 60" fill="none" stroke="white" stroke-width="8" stroke-linecap="round" opacity="0.3" />
        </svg>
      </div>
      <div class="app-name">{{ appInfo.name }}</div>
      <div class="app-version">{{ appInfo.version }}</div>
      <div class="app-description">{{ appInfo.description }}</div>
    </div>

    <!-- 功能列表 -->
    <div class="features-section">
      <div class="section-title">主要功能</div>
      <div class="features-list">
        <div v-for="feature in features" :key="feature" class="feature-item">
          <div class="feature-dot"></div>
          <span>{{ feature }}</span>
        </div>
      </div>
    </div>

    <!-- 链接列表 -->
    <div class="links-section">
      <div class="section-title">联系我们</div>
      <div class="links-list">
        <a class="link-item" :href="appInfo.github" target="_blank">
          <div class="link-icon">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
          </div>
          <span class="link-name">GitHub</span>
          <n-icon size="16" class="arrow-icon"><ChevronRightIcon /></n-icon>
        </a>
        <a class="link-item" :href="appInfo.website" target="_blank">
          <div class="link-icon">
            <n-icon size="18"><WebIcon /></n-icon>
          </div>
          <span class="link-name">官方网站</span>
          <n-icon size="16" class="arrow-icon"><ChevronRightIcon /></n-icon>
        </a>
        <a class="link-item" :href="`mailto:${appInfo.email}`">
          <div class="link-icon">
            <n-icon size="18"><EmailIcon /></n-icon>
          </div>
          <span class="link-name">联系我们</span>
          <n-icon size="16" class="arrow-icon"><ChevronRightIcon /></n-icon>
        </a>
      </div>
    </div>

    <!-- 版权信息 -->
    <div class="copyright">
      <p>© 2024 Lens Team. All rights reserved.</p>
      <p>Made with ❤️ for media lovers</p>
    </div>
  </div>
</template>

<script lang="ts">
import { ChevronRightOutlined as ChevronRightIcon } from '@vicons/material'
export { ChevronRightIcon }
</script>

<style scoped>
.mobile-about {
  min-height: 100vh;
  background: #1e1e22;
  padding-bottom: calc(24px + env(safe-area-inset-bottom));
}

/* 头部 */
.about-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  padding-top: calc(12px + env(safe-area-inset-top));
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.back-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.back-btn:active {
  background: rgba(255, 255, 255, 0.08);
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.95);
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
  color: rgba(255, 255, 255, 0.95);
  margin-bottom: 4px;
}

.app-version {
  font-size: 14px;
  color: #705df2;
  font-weight: 500;
  margin-bottom: 8px;
}

.app-description {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
}

/* 功能列表 */
.features-section {
  padding: 0 20px;
  margin-bottom: 28px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.4);
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
  background: rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
}

.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #705df2;
  flex-shrink: 0;
}

/* 链接列表 */
.links-section {
  padding: 0 20px;
  margin-bottom: 32px;
}

.links-list {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 16px;
  overflow: hidden;
}

.link-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  text-decoration: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  transition: all 0.2s ease;
}

.link-item:last-child {
  border-bottom: none;
}

.link-item:active {
  background: rgba(255, 255, 255, 0.06);
}

.link-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(112, 93, 242, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #705df2;
}

.link-name {
  flex: 1;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.9);
}

.arrow-icon {
  color: rgba(255, 255, 255, 0.3);
}

/* 版权信息 */
.copyright {
  text-align: center;
  padding: 20px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
  line-height: 1.8;
}

.copyright p {
  margin: 0;
}
</style>
