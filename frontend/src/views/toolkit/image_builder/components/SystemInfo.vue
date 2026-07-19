<template>
  <div class="system-info">
    <n-space vertical size="large">
      <n-card size="small">
        <div class="host-bar">
          <n-space align="center" class="host-select-wrap">
            <n-text class="host-label">选择监测主机:</n-text>
            <n-select v-model:value="selectedHostId" :options="hostOptions" class="host-select" @update:value="fetchInfo" />
          </n-space>
          <n-tag v-if="info.platforms.length > 0" type="success" size="large" round class="status-tag">
            <template #icon>
              <n-icon><CheckCircleIcon /></n-icon>
            </template>
            多架构环境就绪
          </n-tag>
          <n-tag v-else-if="info.docker_version !== 'Unknown'" type="warning" size="large" round class="status-tag">
            基础 Docker 就绪
          </n-tag>
        </div>
      </n-card>

      <n-grid :cols="2" :x-gap="12" :y-gap="12">
        <n-gi :span="2">
          <n-card title="Docker 服务状态" size="small">
            <template #header-extra>
              <n-button size="tiny" quaternary @click="fetchInfo" :loading="loading">
                重新检测
              </n-button>
            </template>
            <div class="info-grid">
              <div class="info-item">
                <div class="info-label">Docker 版本</div>
                <div class="info-value">
                  <n-text strong>{{ info.docker_version }}</n-text>
                  <n-tag v-if="info.docker_version !== 'Unknown'" type="success" size="small">运行中</n-tag>
                </div>
              </div>
              <div class="info-item">
                <div class="info-label">Buildx 构建引擎</div>
                <div class="info-value">
                  <n-text strong>{{ info.buildx_version }}</n-text>
                  <n-tag v-if="info.buildx_version !== 'Not Found'" type="success" size="small">就绪</n-tag>
                </div>
              </div>
            </div>
          </n-card>
        </n-gi>
        <n-gi :span="2">
          <n-card title="多架构构建支持" size="small">
            <template #header-extra>
              <n-text v-if="info.platforms.length" type="success">多架构环境已就绪</n-text>
            </template>
            <n-space v-if="info.platforms.length">
              <n-tag v-for="plat in info.platforms" :key="plat" type="info" size="small" ghost>
                {{ plat }}
              </n-tag>
            </n-space>
            <n-empty v-else description="未检测到多架构支持" />
          </n-card>
        </n-gi>
        <n-gi :span="2">
          <n-card title="Buildx 构建器列表 (Builders)" size="small">
            <div class="code-block">
              <pre v-if="info.builders && info.builders.length">{{ info.builders.join('\n') }}</pre>
              <n-empty v-else description="未发现活跃构建器" />
            </div>
          </n-card>
        </n-gi>
      </n-grid>
      <div class="footer-actions">
        <n-space vertical size="small" align="center" class="footer-proxy">
          <n-text class="proxy-label">初始化环境时绑定代理:</n-text>
          <n-select v-model:value="selectedProxyId" :options="proxyOptions" placeholder="不使用代理" clearable class="proxy-select" size="small" />
        </n-space>
        <n-space justify="center" size="large" class="footer-buttons">
          <n-button @click="fetchInfo" :loading="loading" secondary type="primary">
            手动刷新环境状态
          </n-button>
          <n-button @click="handleRepair" :loading="fixing" type="warning" ghost>
            一键初始化/修复构建环境
          </n-button>
        </n-space>
      </div>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NGrid, NGi, NCard,
  NText, NSpace, NButton, NEmpty, NSelect, NTag, NIcon, useMessage, useDialog
} from 'naive-ui'
import { CheckCircleIcon } from '@heroicons/vue/24/outline'
import axios from 'axios'

const message = useMessage()
const dialog = useDialog()

const info = ref({
  docker_version: 'Unknown',
  buildx_version: 'Not Found',
  builders: [],
  platforms: []
})
const loading = ref(false)
const fixing = ref(false)
const selectedHostId = ref(null)
const hostOptions = ref([])
const proxyOptions = ref([])
const selectedProxyId = ref(null)

const fetchHosts = async () => {
  try {
    const [hRes, pRes] = await Promise.all([
      axios.get('/api/docker/hosts'),
      axios.get('/api/image-builder/proxies')
    ])
    hostOptions.value = hRes.data.map((h: any) => ({ label: h.name, value: h.id }))
    proxyOptions.value = pRes.data.map((p: any) => ({ label: p.name, value: p.id }))
    
    if (hostOptions.value.length > 0 && !selectedHostId.value) {
      selectedHostId.value = hostOptions.value[0].value
      fetchInfo()
    }
  } catch (e) {}
}

const fetchInfo = async () => {
  if (!selectedHostId.value) return
  loading.value = true
  try {
    const res = await axios.get('/api/image-builder/system-info', {
      params: { host_id: selectedHostId.value }
    })
    info.value = res.data
  } catch (e) {
    info.value = { docker_version: 'Unknown', buildx_version: 'Not Found', builders: [], platforms: [] }
  } finally {
    loading.value = false
  }
}

const handleRepair = () => {
  dialog.info({
    title: '初始化构建环境',
    content: '该操作将为远程主机安装 QEMU 仿真支持并配置专用 Buildx 构建器，以实现跨平台（如 ARM64）构建。是否继续？',
    positiveText: '立即开始',
    negativeText: '取消',
    onPositiveClick: async () => {
      fixing.value = true
      try {
        const res = await axios.post('/api/image-builder/setup-env', { 
          host_id: selectedHostId.value,
          proxy_id: selectedProxyId.value
        })
        if (res.data.success) {
          if (res.data.async) {
            message.info(res.data.message || '环境初始化任务已在后台启动，请留意系统通知进度')
          } else {
            message.success('构建环境初始化成功')
            fetchInfo()
          }
        } else {
          message.error('初始化失败: ' + res.data.message)
        }
      } catch (e) {
        message.error('请求失败')
      } finally {
        fixing.value = false
      }
    }
  })
}

onMounted(fetchHosts)
</script>

<style scoped>
/* 顶部主机选择栏 */
.host-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.host-select-wrap {
  flex: 0 0 auto;
  min-width: 0;
}

.host-label {
  white-space: nowrap;
}

.host-select {
  width: 220px;
}

.status-tag {
  flex-shrink: 0;
}

/* Docker 服务状态：信息卡片网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.info-item {
  padding: 10px 12px;
  background: var(--info-item-bg, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--info-item-border, rgba(255, 255, 255, 0.08));
  border-radius: 6px;
  transition: border-color 200ms ease, background 200ms ease;
}

.info-item:hover {
  border-color: rgba(64, 128, 240, 0.4);
  background: rgba(64, 128, 240, 0.05);
}

.info-label {
  font-size: 12px;
  opacity: 0.65;
  margin-bottom: 6px;
  font-weight: 500;
}

.info-value {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}

/* 底部操作区 */
.footer-actions {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.footer-proxy {
  width: 100%;
  justify-content: center;
}

.proxy-label {
  opacity: 0.8;
  white-space: nowrap;
}

.proxy-select {
  width: 200px;
}

.footer-buttons {
  flex-wrap: wrap;
  justify-content: center;
}

/* 代码块 */
.code-block {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  overflow-x: auto;
}
pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}

/* ============== 移动端适配 ============== */
@media (max-width: 767px) {
  /* 顶部主机选择栏：select 占满整行 */
  .host-bar {
    flex-direction: column;
    align-items: stretch;
  }
  .host-select-wrap {
    width: 100%;
    flex-wrap: wrap;
  }
  .host-select {
    width: 100% !important;
  }
  .status-tag {
    align-self: flex-start;
  }

  /* Docker 服务状态：移动端单列展示 */
  .info-grid {
    grid-template-columns: 1fr;
  }

  /* 底部代理选择框占满整行 */
  .proxy-select {
    width: 100% !important;
  }
  .footer-proxy {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  /* 底部按钮：每个按钮占整行 */
  .footer-buttons {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }
  .footer-buttons :deep(.n-button) {
    width: 100%;
    margin: 0 !important;
  }
}

/* 超窄屏 (≤380px) 兼容 */
@media (max-width: 380px) {
  .info-item {
    padding: 8px 10px;
  }
  .info-label {
    font-size: 11px;
  }
}
</style>