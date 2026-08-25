import { createApp } from 'vue'
import { createPinia } from 'pinia'
import vuetify from './plugins/vuetify'
import App from './App.vue'
import router from './router'
import { glassI18n } from '@/glass/host/i18n'

// 全局样式
import '@/styles/global.css'
import '@/styles/tokens.css'

const app = createApp(App)

app.use(createPinia())
app.use(vuetify)
app.use(router)
app.use(glassI18n)

app.mount('#app')
