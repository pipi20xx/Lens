import { createApp } from 'vue'
import { createPinia } from 'pinia'
import vuetify from './plugins/vuetify'
import App from './App.vue'
import router from './router'
import { glassI18n } from '@/glass/host/i18n'

// 全局样式 — 四层架构入口（结构 → 令牌 → 视觉 → 主题）
// 第 4 层 ACG 主题由 DefaultLayout.vue 动态加载/卸载
import '@/styles/index.css'

const app = createApp(App)

app.use(createPinia())
app.use(vuetify)
app.use(router)
app.use(glassI18n)

app.mount('#app')
