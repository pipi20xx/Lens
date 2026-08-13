import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import { visualizer } from 'rollup-plugin-visualizer'
import viteCompression from 'vite-plugin-compression'
import AutoImport from 'unplugin-auto-import/vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => {
  const isAnalyze = mode === 'analyze'

  return {
    base: '/',
    plugins: [
      vue(),
      vuetify({
        autoImport: true,
        styles: {
          configFile: 'src/styles/settings.scss',
        },
      }),
      AutoImport({
        imports: ['vue', 'vue-router', 'pinia', '@vueuse/core'],
        dts: 'src/auto-imports.d.ts',
      }),
      viteCompression({ verbose: true, disable: false, threshold: 10240, algorithm: 'gzip', ext: '.gz' }),
      viteCompression({ verbose: true, disable: false, threshold: 10240, algorithm: 'brotliCompress', ext: '.br' }),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico', 'favicon-32x32.png', 'apple-touch-icon.png', 'favicon.svg'],
        manifest: {
          name: 'Lens',
          short_name: 'Lens',
          description: 'Lens - 一个强大的导航和管理工具',
          theme_color: '#a855f7',
          background_color: '#0a0a1a',
          display: 'standalone',
          orientation: 'portrait',
          scope: '/',
          start_url: '/',
          icons: [
            { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
            { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
            { src: '/pwa-maskable-192x192.png', sizes: '192x192', type: 'image/png', purpose: 'maskable' },
            { src: '/pwa-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg,woff,woff2}'],
          runtimeCaching: [
            {
              urlPattern: /\/api\//i,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'api-cache',
                expiration: {
                  maxEntries: 100,
                  maxAgeSeconds: 60 * 60 * 24 * 7,
                },
                cacheableResponse: {
                  statuses: [0, 200],
                },
              },
            },
          ],
        },
      }),
      isAnalyze && visualizer({ open: true, gzipSize: true, filename: 'dist/stats.html' }),
    ],
    define: {
      __APP_VERSION__: JSON.stringify('3.0.4'),
    },
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 3000,
      watch: {
        // Docker 绑定挂载下 inotify 事件无法跨文件系统边界传递，
        // 必须启用轮询模式才能触发 HMR 热更新。
        // 本地裸机开发时性能影响可忽略，生产构建不涉及此配置。
        usePolling: true,
        interval: 100,
      },
      proxy: {
        '/api': { target: 'http://backend:6565', changeOrigin: true, ws: true },
        '/ws': { target: 'ws://backend:6565', ws: true, changeOrigin: true },
        '/nav_icons': { target: 'http://backend:6565', changeOrigin: true },
        '/nav_backgrounds': { target: 'http://backend:6565', changeOrigin: true },
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/vuetify') || id.includes('node_modules/.vite/deps/vuetify')) return 'vuetify'
            if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router') || id.includes('node_modules/pinia')) return 'vue-vendor'
          },
        },
      },
      minify: true,
      cssMinify: false,
    },
  }
})
