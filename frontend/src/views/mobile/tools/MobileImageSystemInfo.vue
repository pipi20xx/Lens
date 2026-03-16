<template>
  <div class="mobile-image-system-info">
    <n-space vertical>
      <n-card title="主机选择" size="small" :bordered="false">
        <n-space vertical>
          <n-select 
            v-model:value="selectedHostId" 
            :options="hostOptions" 
            placeholder="选择监测主机"
            size="small"
            @update:value="fetchInfo"
          />
          <n-space justify="space-between">
            <n-text v-if="info.platforms.length > 0" type="success" style="font-size: 12px">
              多架构环境就绪
            </n-text>
            <n-text v-else-if="info.docker_version !== 'Unknown'" type="warning" style="font-size: 12px">
              基础 Docker 就绪
            </n-text>
            <n-button size="tiny" secondary @click="fetchInfo" :loading="loading">
              <template #icon><n-icon><RefreshIcon /></n-icon></template>
              刷新
            </n-button>
          </n-space>
        </n-space>
      </n-card>

      <n-card title="Docker 服务" size="small" :bordered="false">
        <n-descriptions label-placement="left" :column="1" size="small">
          <n-descriptions-item label="Docker 版本">
            <n-space align="center">
              <n-text strong>{{ info.docker_version }}</n-text>
              <n-tag v-if="info.docker_version !== 'Unknown'" type="success" size="tiny">运行中</n-tag>
            </n-space>
          </n-descriptions-item>
          <n-descriptions-item label="Buildx 引擎">
            <n-space align="center">
              <n-text strong>{{ info.buildx_version }}</n-text>
              <n-tag v-if="info.buildx_version !== 'Not Found'" type="success" size="tiny">就绪</n-tag>
            </n-space>
          </n-descriptions-item>
        </n-descriptions>
      </n-card>

      <n-card title="多架构支持" size="small" :bordered="false">
        <div v-if="info.platforms.length" class="platforms-container">
          <n-tag v-for="plat in info.platforms" :key="plat" type="info" size="small" ghost>
            {{ plat }}
          </n-tag>
        </div>
        <n-empty v-else description="未检测到多架构支持" size="small" />
      </n-card>

      <n-card title="构建器列表" size="small" :bordered="false">
        <div v-if="info.builders && info.builders.length" class="builders-container">
          <div v-for="(builder, index) in info.builders" :key="index" class="builder-item">
            {{ builder }}
          </div>
        </div>
        <n-empty v-else description="未发现活跃构建器" size="small" />
      </n-card>

      <n-card title="环境初始化" size="small" :bordered="false">
        <n-space vertical>
          <n-form-item label="绑定代理" label-placement="top" size="small">
            <n-select 
              v-model:value="selectedProxyId" 
              :options="proxyOptions" 
              placeholder="不使用代理" 
              clearable 
              size="small"
            />
          </n-form-item>
          <n-button 
            type="warning" 
            secondary 
            block 
            @click="handleRepair" 
            :loading="fixing"
            size="small"
          >
            <template #icon><n-icon><RepairIcon /></n-icon></template>
            初始化/修复构建环境
          </n-button>
        </n-space>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NCard, NDescriptions, NDescriptionsItem, NText, NSpace, NButton, 
  NEmpty, NSelect, NTag, NIcon, NFormItem, useMessage, useDialog
} from 'naive-ui'
import {
  CheckCircleOutlined as CheckIcon,
  BuildCircleOutlined as RepairIcon,
  RefreshOutlined as RefreshIcon
} from '@vicons/material'
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
  } catch (e: any) {
    message.error('获取主机列表失败: ' + (e.message || '未知错误'))
  }
}

const fetchInfo = async () => {
  if (!selectedHostId.value) return
  loading.value = true
  try {
    const res = await axios.get('/api/image-builder/system-info', {
      params: { host_id: selectedHostId.value }
    })
    info.value = res.data
  } catch (e: any) {
    message.error('获取系统信息失败: ' + (e.message || '未知错误'))
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
      } catch (e: any) {
        message.error('请求失败: ' + (e.message || '未知错误'))
      } finally {
        fixing.value = false
      }
    }
  })
}

onMounted(fetchHosts)
</script>

<style scoped>
.mobile-image-system-info {
  padding: 12px 0;
}

.platforms-container {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.builders-container {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
}

.builder-item {
  font-family: monospace;
  font-size: 12px;
  color: var(--text-color);
  padding: 4px 0;
  white-space: pre-wrap;
}
</style>
