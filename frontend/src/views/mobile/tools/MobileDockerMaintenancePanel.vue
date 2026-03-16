<template>
  <div class="mobile-docker-maintenance-panel">
    <n-space vertical>
      <n-card title="Docker Daemon 配置" size="small" :bordered="false">
        <template #header-extra>
          <n-button size="tiny" quaternary type="primary" @click="openRawEdit" :loading="loading.daemon">
            <template #icon><n-icon><CodeIcon /></n-icon></template>
            编辑 JSON
          </n-button>
        </template>

        <n-alert type="info" size="small" style="margin-bottom: 12px">
          该配置将直接修改远程主机的 /etc/docker/daemon.json 文件
        </n-alert>
        
        <n-form label-placement="top" size="small" :disabled="loading.daemon">
          <n-form-item label="镜像加速器">
            <n-input
              v-model:value="daemonForm.mirrors"
              type="textarea"
              placeholder="每行一个 URL"
              :autosize="{ minRows: 2 }"
            />
          </n-form-item>
          
          <n-form-item label="私有仓库">
            <n-input
              v-model:value="daemonForm.insecure"
              type="textarea"
              placeholder="每行一个地址"
              :autosize="{ minRows: 2 }"
            />
          </n-form-item>
          
          <div class="proxy-section">
            <n-space align="center" justify="space-between">
              <n-space align="center" size="small">
                <n-text strong style="font-size: 14px">代理设置</n-text>
                <n-tag size="tiny" :type="daemonForm.proxyEnabled ? 'success' : 'default'">
                  {{ daemonForm.proxyEnabled ? '已启用' : '已禁用' }}
                </n-tag>
              </n-space>
              <n-switch v-model:value="daemonForm.proxyEnabled" size="small" class="mobile-switch" />
            </n-space>
            
            <template v-if="daemonForm.proxyEnabled">
              <n-alert type="warning" size="tiny" style="margin-top: 8px">
                仅支持 HTTP/HTTPS 协议代理
              </n-alert>
              <n-form-item label="服务器地址" style="margin-top: 8px">
                <n-input v-model:value="daemonForm.proxyHost" placeholder="例如: 192.168.50.66" />
              </n-form-item>
              <n-form-item label="端口">
                <n-input v-model:value="daemonForm.proxyPort" placeholder="7890" />
              </n-form-item>
              <n-form-item label="无需代理地址">
                <n-input v-model:value="daemonForm.noProxy" placeholder="localhost,127.0.0.1" />
              </n-form-item>
            </template>
          </div>
          
          <n-grid :cols="2" :x-gap="8" style="margin-top: 8px">
            <n-gi>
              <n-form-item label="日志大小">
                <n-input v-model:value="daemonForm.logSize" placeholder="100m" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item label="日志份数">
                <n-input-number v-model:value="daemonForm.logFiles" :min="1" style="width: 100%" />
              </n-form-item>
            </n-gi>
          </n-grid>
          
          <n-space vertical style="margin-top: 8px">
            <n-checkbox v-model:checked="daemonForm.liveRestore" size="small">
              开启 Live Restore
            </n-checkbox>
            <n-checkbox v-model:checked="daemonForm.shouldRestart" size="small">
              保存后重启 Docker 服务
            </n-checkbox>
          </n-space>
        </n-form>
        
        <n-button 
          type="primary" 
          block 
          :loading="loading.daemon" 
          @click="handleSaveDaemonConfig"
          style="margin-top: 12px"
        >
          <template #icon><n-icon><SaveIcon /></n-icon></template>
          保存配置
        </n-button>
      </n-card>

      <n-card title="镜像清理" size="small" :bordered="false">
        <n-space vertical>
          <n-text depth="3" style="font-size: 12px">清理无用的 Docker 镜像以释放磁盘空间</n-text>
          <n-space vertical item-style="display: flex; align-items: center">
            <n-checkbox v-model:checked="imageOptions.dangling" size="small">
              清理未标签镜像
            </n-checkbox>
            <n-checkbox v-model:checked="imageOptions.all" size="small">
              清理所有未使用镜像
            </n-checkbox>
          </n-space>
          <n-button 
            type="primary" 
            secondary 
            block 
            :loading="loading.images" 
            @click="handlePruneImages"
          >
            <template #icon><n-icon><DeleteIcon /></n-icon></template>
            开始清理镜像
          </n-button>
        </n-space>
      </n-card>

      <n-card title="构建缓存清理" size="small" :bordered="false">
        <n-space vertical>
          <n-text depth="3" style="font-size: 12px">清理 Docker Buildx 或 BuildKit 的构建缓存</n-text>
          <n-button 
            type="warning" 
            secondary 
            block 
            :loading="loading.cache" 
            @click="handlePruneCache"
          >
            <template #icon><n-icon><DeleteIcon /></n-icon></template>
            开始清理构建缓存
          </n-button>
        </n-space>
      </n-card>

      <n-card title="容器清理" size="small" :bordered="false">
        <n-space vertical>
          <n-text depth="3" style="font-size: 12px">清理所有处于停止状态的 Docker 容器</n-text>
          <n-button 
            type="error" 
            secondary 
            block 
            :loading="loading.containers" 
            @click="handlePruneContainers"
          >
            <template #icon><n-icon><DeleteIcon /></n-icon></template>
            开始清理停止的容器
          </n-button>
        </n-space>
      </n-card>
    </n-space>

    <n-modal v-model:show="showResult" preset="dialog" title="清理结果" style="width: 90%">
      <template #default>
        <div style="background: #1e1e1e; color: #adadad; padding: 10px; font-family: monospace; border-radius: 4px; overflow: auto; max-height: 300px; white-space: pre-wrap; font-size: 12px;">
          {{ resultOutput }}
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="showRawModal" preset="card" title="编辑 daemon.json" style="width: 90%">
      <n-space vertical size="large">
        <n-alert type="warning" size="small">
          警告：直接编辑 JSON 可能会导致 Docker 无法启动
        </n-alert>
        <n-input
          v-model:value="rawJsonContent"
          type="textarea"
          placeholder="{ ... }"
          :autosize="{ minRows: 10, maxRows: 20 }"
          style="font-family: monospace; font-size: 12px"
          @input="validateRawJson"
        />
        <n-text v-if="rawJsonError" type="error" style="font-size: 12px">{{ rawJsonError }}</n-text>
        
        <n-space align="center">
          <n-checkbox v-model:checked="daemonForm.shouldRestart" size="small">
            保存后重启 Docker 服务
          </n-checkbox>
        </n-space>
      </n-space>
      <template #footer>
        <n-space justify="end">
          <n-button size="small" @click="showRawModal = false">
            取消
          </n-button>
          <n-button 
            type="primary" 
            size="small" 
            :disabled="!!rawJsonError" 
            @click="handleSaveRawJson" 
            :loading="loading.daemon"
          >
            保存
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NSpace, NCard, NText, NCheckbox, NSwitch, NButton, NModal, NForm, NFormItem, NInput, NInputNumber, NAlert, NIcon, NGrid, NGi, NTag, useMessage, useDialog } from 'naive-ui'
import { 
  CodeOutlined as CodeIcon,
  SaveOutlined as SaveIcon,
  DeleteOutlined as DeleteIcon
} from '@vicons/material'
import axios from 'axios'

const props = defineProps({
  hostId: String | null
})

const message = useMessage()
const dialog = useDialog()
const loading = ref({ images: false, cache: false, containers: false, daemon: false })
const showResult = ref(false)
const showRawModal = ref(false)
const rawJsonContent = ref('')
const rawJsonError = ref<string | null>(null)
const resultOutput = ref('')

const imageOptions = ref({
  dangling: true,
  all: false
})

const daemonForm = ref({
  mirrors: '',
  insecure: '',
  logSize: '100m',
  logFiles: 5,
  liveRestore: true,
  shouldRestart: false,
  proxyEnabled: false,
  proxyHost: '',
  proxyPort: '',
  proxyUser: '',
  proxyPass: '',
  noProxy: 'localhost,127.0.0.1'
})

const rawDaemonConfig = ref<any>({})

const fetchDaemonConfig = async () => {
  if (!props.hostId) return
  loading.value.daemon = true
  try {
    const res = await axios.get(`/api/docker/${props.hostId}/daemon-config`)
    rawDaemonConfig.value = res.data
    
    daemonForm.value.mirrors = (res.data['registry-mirrors'] || []).join('\n')
    daemonForm.value.insecure = (res.data['insecure-registries'] || []).join('\n')
    daemonForm.value.logSize = res.data['log-opts']?.['max-size'] || '100m'
    daemonForm.value.logFiles = parseInt(res.data['log-opts']?.['max-file'] || '5')
    daemonForm.value.liveRestore = res.data['live-restore'] ?? true
    
    const proxies = res.data['proxies'] || {}
    const httpProxy = proxies['http-proxy'] || ''
    daemonForm.value.noProxy = proxies['no-proxy'] || 'localhost,127.0.0.1'
    
    if (httpProxy) {
      daemonForm.value.proxyEnabled = true
      try {
        const url = new URL(httpProxy)
        daemonForm.value.proxyHost = url.hostname
        daemonForm.value.proxyPort = url.port
        daemonForm.value.proxyUser = decodeURIComponent(url.username)
        daemonForm.value.proxyPass = decodeURIComponent(url.password)
      } catch (e) {
        daemonForm.value.proxyHost = httpProxy
      }
    } else {
      daemonForm.value.proxyEnabled = false
    }
  } catch (e) {
    message.error('无法读取 Daemon 配置')
  } finally {
    loading.value.daemon = false
  }
}

watch(() => props.hostId, fetchDaemonConfig, { immediate: true })

const openRawEdit = async () => {
  if (!props.hostId) return
  loading.value.daemon = true
  try {
    const res = await axios.get(`/api/docker/${props.hostId}/daemon-config/raw`)
    rawJsonContent.value = res.data.content
    rawJsonError.value = null
    showRawModal.value = true
  } catch (e) {
    message.error('无法读取原始配置')
  } finally {
    loading.value.daemon = false
  }
}

const validateRawJson = (val: string) => {
  if (!val.trim()) {
    rawJsonError.value = '内容不能为空'
    return
  }
  try {
    JSON.parse(val)
    rawJsonError.value = null
  } catch (e: any) {
    rawJsonError.value = '无效的 JSON 格式'
  }
}

const handleSaveRawJson = () => {
  if (rawJsonError.value) return
  
  dialog.warning({
    title: '确认保存',
    content: daemonForm.value.shouldRestart 
      ? '保存后将重启 Docker 服务，会导致容器短暂中断' 
      : '配置将保存，需要手动重启 Docker 服务后才能生效',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      loading.value.daemon = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/daemon-config/raw`, {
          content: rawJsonContent.value,
          restart: daemonForm.value.shouldRestart
        })
        message.success(res.data.message)
        showRawModal.value = false
        fetchDaemonConfig()
      } catch (e: any) {
        message.error(e.response?.data?.detail || '保存失败')
      } finally {
        loading.value.daemon = false
      }
    }
  })
}

const handleSaveDaemonConfig = async () => {
  if (!props.hostId) return
  const newConfig = { ...rawDaemonConfig.value }
  newConfig['registry-mirrors'] = daemonForm.value.mirrors.split('\n').map(i => i.trim()).filter(i => i)
  newConfig['insecure-registries'] = daemonForm.value.insecure.split('\n').map(i => i.trim()).filter(i => i)
  newConfig['log-driver'] = 'json-file'
  newConfig['log-opts'] = {
    'max-size': daemonForm.value.logSize,
    'max-file': daemonForm.value.logFiles.toString()
  }
  newConfig['live-restore'] = daemonForm.value.liveRestore
  
  if (daemonForm.value.proxyEnabled && daemonForm.value.proxyHost) {
    let auth = ''
    if (daemonForm.value.proxyUser) {
      auth = `${encodeURIComponent(daemonForm.value.proxyUser)}:${encodeURIComponent(daemonForm.value.proxyPass)}@`
    }
    const port = daemonForm.value.proxyPort ? `:${daemonForm.value.proxyPort}` : ''
    const host = daemonForm.value.proxyHost.includes('://') ? daemonForm.value.proxyHost.split('://')[1] : daemonForm.value.proxyHost
    const proxyUrl = `http://${auth}${host}${port}`
    newConfig['proxies'] = {
      'http-proxy': proxyUrl,
      'https-proxy': proxyUrl,
      'no-proxy': daemonForm.value.noProxy
    }
  } else {
    delete newConfig['proxies']
  }

  dialog.warning({
    title: '确认保存',
    content: daemonForm.value.shouldRestart 
      ? '保存后将重启 Docker 服务，会导致容器短暂中断' 
      : '配置将保存，需要手动重启 Docker 服务后才能生效',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      loading.value.daemon = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/daemon-config`, {
          config: newConfig,
          restart: daemonForm.value.shouldRestart
        })
        message.success(res.data.message)
        if (daemonForm.value.shouldRestart && res.data.restart_result) {
          resultOutput.value = res.data.restart_result.stdout || res.data.restart_result.stderr || '服务已尝试重启'
          showResult.value = true
        }
        fetchDaemonConfig()
      } catch (e) {
        message.error(e.response?.data?.detail || '保存失败')
      } finally {
        loading.value.daemon = false
      }
    }
  })
}

const handlePruneImages = async () => {
  if (!props.hostId) return
  if (!imageOptions.value.dangling && !imageOptions.value.all) {
    message.warning('请至少选择一个清理选项')
    return
  }

  dialog.warning({
    title: '确认清理镜像',
    content: '此操作将永久删除满足条件的本地镜像',
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      loading.value.images = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune-images`, {
          dangling: imageOptions.value.dangling,
          all_unused: imageOptions.value.all
        })
        message.success(res.data.message || '镜像清理任务已启动')
      } catch (e) { message.error('请求失败') }
      finally { loading.value.images = false }
    }
  })
}

const handlePruneCache = async () => {
  if (!props.hostId) return
  dialog.warning({
    title: '确认清理构建缓存',
    content: '此操作将清理所有未使用的构建缓存',
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      loading.value.cache = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune-cache`)
        message.success(res.data.message || '缓存清理任务已启动')
      } catch (e) { message.error('请求失败') }
      finally { loading.value.cache = false }
    }
  })
}

const handlePruneContainers = async () => {
  if (!props.hostId) return
  dialog.warning({
    title: '确认清理容器',
    content: '此操作将永久删除所有处于停止状态的容器',
    positiveText: '确认',
    negativeText: '取消',
    onPositiveClick: async () => {
      loading.value.containers = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune-containers`)
        message.success(res.data.message || '容器清理任务已启动')
      } catch (e) { message.error('请求失败') }
      finally { loading.value.containers = false }
    }
  })
}
</script>

<style scoped>
.mobile-docker-maintenance-panel {
  padding: 8px;
}

.proxy-section {
  background: rgba(24, 160, 88, 0.05);
  border: 1px solid rgba(24, 160, 88, 0.2);
  border-radius: 6px;
  padding: 12px;
  margin-top: 8px;
}
</style>
