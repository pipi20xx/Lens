<template>
  <div class="maintenance-panel">
    <n-grid :cols="2" :x-gap="12" :y-gap="12">
      <n-gi :span="2">
        <n-card title="Docker Daemon 配置" size="small">
          <template #header-extra>
            <n-space align="center">
              <n-button size="tiny" quaternary type="primary" @click="openRawEdit">
                直接编辑 JSON
              </n-button>
              <n-text  type="warning" style="font-size: 12px">
                <n-icon><ExclamationTriangleIcon /></n-icon> 需要 Root 权限的 SSH 账户
              </n-text>
            </n-space>
          </template>

          <n-alert type="info" size="small" style="margin-bottom: 16px" :show-icon="true">
            该配置将直接修改远程主机的 <n-text code>/etc/docker/daemon.json</n-text> 文件。保存前建议确保了解配置项的含义。
          </n-alert>
          
          <n-form label-placement="top" :disabled="loading.daemon">
            <n-grid :cols="2" :x-gap="24">
              <n-gi>
                <n-form-item label="镜像加速器 (Registry Mirrors)">
                  <n-input
                    v-model:value="daemonForm.mirrors"
                    type="textarea"
                    placeholder="每行一个 URL，例如: https://docker.fnnas.com"
                    :autosize="{ minRows: 3 }"
                  />
                </n-form-item>
                <n-form-item label="私有仓库 (Insecure Registries)">
                  <n-input
                    v-model:value="daemonForm.insecure"
                    type="textarea"
                    placeholder="每行一个地址，例如: 192.168.50.12:6100"
                    :autosize="{ minRows: 3 }"
                  />
                </n-form-item>
                
                <n-space vertical style="border: 1px solid #333; padding: 12px; border-radius: 4px">
                  <n-space align="center" justify="space-between">
                    <n-space align="center" size="small">
                      <n-text strong>代理设置 (Proxies)</n-text>
                      <n-tag size="tiny" :type="daemonForm.proxyEnabled ? 'success' : 'default'">
                        {{ daemonForm.proxyEnabled ? '已启用' : '已禁用' }}
                      </n-tag>
                    </n-space>
                    <n-switch v-model:value="daemonForm.proxyEnabled" size="small" />
                  </n-space>
                  
                  <template v-if="daemonForm.proxyEnabled">
                    <n-alert type="warning" size="small" :show-icon="false">
                      注意：Docker 守护进程通常仅支持 HTTP/HTTPS 协议代理，暂不支持 SOCKS5。
                    </n-alert>
                    <n-grid :cols="4" :x-gap="8">
                      <n-gi :span="3">
                        <n-form-item label="服务器地址" size="small">
                          <n-input v-model:value="daemonForm.proxyHost" placeholder="例如: 192.168.50.66" />
                        </n-form-item>
                      </n-gi>
                      <n-gi>
                        <n-form-item label="端口" size="small">
                          <n-input v-model:value="daemonForm.proxyPort" placeholder="7890" />
                        </n-form-item>
                      </n-gi>
                    </n-grid>
                    <n-grid :cols="2" :x-gap="8">
                      <n-gi>
                        <n-form-item label="用户名 (可选)" size="small">
                          <n-input v-model:value="daemonForm.proxyUser" placeholder="可选" />
                        </n-form-item>
                      </n-gi>
                      <n-gi>
                        <n-form-item label="密码 (可选)" size="small">
                          <n-input v-model:value="daemonForm.proxyPass" type="password" show-password-on="click" placeholder="可选" />
                        </n-form-item>
                      </n-gi>
                    </n-grid>
                    <n-form-item label="无需代理地址 (No Proxy)" size="small">
                      <n-input v-model:value="daemonForm.noProxy" placeholder="localhost,127.0.0.1" />
                    </n-form-item>
                  </template>
                </n-space>
              </n-gi>
              <n-gi>
                <n-grid :cols="2" :x-gap="12">
                  <n-gi>
                    <n-form-item label="日志单文件大小">
                      <n-input v-model:value="daemonForm.logSize" placeholder="例如: 100m" />
                    </n-form-item>
                  </n-gi>
                  <n-gi>
                    <n-form-item label="日志保留份数">
                      <n-input-number v-model:value="daemonForm.logFiles" :min="1" style="width: 100%" />
                    </n-form-item>
                  </n-gi>
                </n-grid>
                <n-space vertical>
                  <n-checkbox v-model:checked="daemonForm.liveRestore">
                    开启 Live Restore (守护进程重启时不停止容器)
                  </n-checkbox>
                  <n-alert type="info" size="small" :show-icon="false">
                    保存时将自动备份旧配置至本地 data 目录及远程 .bak 文件。
                  </n-alert>
                  <n-space align="center">
                    <n-checkbox v-model:checked="daemonForm.shouldRestart">
                      保存后重启 Docker 服务 (会导致容器短暂中断)
                    </n-checkbox>
                  </n-space>
                </n-space>
              </n-gi>
            </n-grid>
            <n-space justify="end" style="margin-top: 12px">
              <n-button type="primary" :loading="loading.daemon" @click="handleSaveDaemonConfig">
                保存并应用配置
              </n-button>
            </n-space>
          </n-form>
        </n-card>
      </n-gi>

      <n-gi :span="2">
        <n-card title="Docker 资源清理" size="small">
          <template #header-extra>
            <n-text type="warning" style="font-size: 12px">
              <n-icon><ExclamationTriangleIcon /></n-icon> 勾选项越多，清理越彻底，请谨慎选择
            </n-text>
          </template>
          <n-space vertical size="large">
            <n-text>勾选需要清理的资源类型，点击下方按钮将根据勾选项组合命令一次性执行。</n-text>

            <n-space vertical>
              <!-- 镜像类 -->
              <div class="prune-group">
                <n-text strong depth="2">镜像 (Images)</n-text>
                <n-space item-style="display: flex; align-items: center; margin-left: 8px">
                  <n-checkbox v-model:checked="pruneOptions.images_dangling" :disabled="pruneOptions.images_unused">
                    清理未标签镜像 (Dangling)
                    <n-text depth="3" style="margin-left: 6px; font-size: 12px">— docker image prune -f</n-text>
                  </n-checkbox>
                  <n-checkbox v-model:checked="pruneOptions.images_unused">
                    清理所有未使用镜像 (Unused)
                    <n-text depth="3" style="margin-left: 6px; font-size: 12px">— docker image prune -a -f</n-text>
                  </n-checkbox>
                </n-space>
                <n-alert type="info" size="small" :show-icon="false" style="margin-left: 8px">
                  勾选「所有未使用镜像」时已包含未标签镜像，将自动禁用上方的 Dangling 选项。
                </n-alert>
              </div>

              <!-- 构建缓存 -->
              <div class="prune-group">
                <n-text strong depth="2">构建缓存 (Build Cache)</n-text>
                <n-space item-style="display: flex; align-items: center; margin-left: 8px">
                  <n-checkbox v-model:checked="pruneOptions.build_cache">
                    清理 BuildKit / Buildx 构建缓存
                    <n-text depth="3" style="margin-left: 6px; font-size: 12px">— docker builder prune -f</n-text>
                  </n-checkbox>
                </n-space>
              </div>

              <!-- 容器 -->
              <div class="prune-group">
                <n-text strong depth="2">容器 (Containers)</n-text>
                <n-space item-style="display: flex; align-items: center; margin-left: 8px">
                  <n-checkbox v-model:checked="pruneOptions.containers">
                    清理所有停止状态的容器
                    <n-text depth="3" style="margin-left: 6px; font-size: 12px">— docker container prune -f</n-text>
                  </n-checkbox>
                </n-space>
              </div>

              <!-- 网络 -->
              <div class="prune-group">
                <n-text strong depth="2">网络 (Networks)</n-text>
                <n-space item-style="display: flex; align-items: center; margin-left: 8px">
                  <n-checkbox v-model:checked="pruneOptions.networks">
                    清理未被容器使用的网络
                    <n-text depth="3" style="margin-left: 6px; font-size: 12px">— docker network prune -f</n-text>
                  </n-checkbox>
                </n-space>
              </div>
            </n-space>

            <!-- 将执行的命令预览 -->
            <div v-if="previewCommand" class="cmd-preview">
              <n-text depth="3" style="font-size: 12px; margin-bottom: 4px; display: block">将要执行的命令：</n-text>
              <code>{{ previewCommand }}</code>
            </div>

            <n-space align="center" justify="space-between">
              <n-text depth="3" style="font-size: 12px">
                共勾选 {{ selectedCount }} 项
              </n-text>
              <n-button type="error" :loading="loading.prune" :disabled="!selectedCount" @click="handlePruneAll">
                开始清理
              </n-button>
            </n-space>
          </n-space>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- 结果弹窗 -->
    <n-modal v-model:show="showResult" preset="dialog" title="清理结果" style="width: 600px">
      <template #default>
        <div style="background: #1e1e1e; color: #adadad; padding: 10px; font-family: monospace; border-radius: 4px; overflow: auto; max-height: 400px; white-space: pre-wrap;">
          {{ resultOutput }}
        </div>
      </template>
    </n-modal>

    <!-- 原生 JSON 编辑弹窗 -->
    <n-modal v-model:show="showRawModal" preset="card" title="直接编辑 daemon.json" style="width: 800px">
      <n-space vertical size="large">
        <n-alert type="warning" size="small">
          警告：直接编辑 JSON 可能会导致 Docker 无法启动。系统将会在保存前验证 JSON 格式并自动创建备份。
        </n-alert>
        <n-input
          v-model:value="rawJsonContent"
          type="textarea"
          placeholder="{ ... }"
          :autosize="{ minRows: 15, maxRows: 25 }"
          style="font-family: monospace"
          @input="validateRawJson"
        />
        <n-text v-if="rawJsonError" type="error" style="font-size: 12px">{{ rawJsonError }}</n-text>
        
        <n-space align="center">
          <n-checkbox v-model:checked="daemonForm.shouldRestart">
            保存后重启 Docker 服务
          </n-checkbox>
        </n-space>
      </n-space>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showRawModal = false">
            取消
          </n-button>
          <n-button type="primary" :disabled="!!rawJsonError" @click="handleSaveRawJson" :loading="loading.daemon">
            保存原始配置
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, h } from 'vue'
import { NGrid, NGi, NCard, NSpace, NText, NCheckbox, NSwitch, NButton, NModal, NForm, NFormItem, NInput, NInputNumber, NAlert, NIcon, useMessage, useDialog, NTag } from 'naive-ui'
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import axios from 'axios'

const props = defineProps({
  hostId: String | null
})

const message = useMessage()
const dialog = useDialog()
const loading = ref({ daemon: false, prune: false })
const showResult = ref(false)
const showRawModal = ref(false)
const rawJsonContent = ref('')
const rawJsonError = ref<string | null>(null)
const resultOutput = ref('')

const pruneOptions = ref({
  images_dangling: false,
  images_unused: false,
  build_cache: false,
  containers: false,
  networks: false
})

// 已选清理项数量
const selectedCount = computed(() => {
  const o = pruneOptions.value
  // images_unused 勾选时已包含 dangling，dangling 不单独计数
  let count = 0
  if (o.images_unused) count += 1
  else if (o.images_dangling) count += 1
  if (o.build_cache) count += 1
  if (o.containers) count += 1
  if (o.networks) count += 1
  return count
})

// 命令预览：根据勾选项组合出将要执行的命令
const previewCommand = computed(() => {
  const o = pruneOptions.value
  const parts: string[] = []
  if (o.images_unused) parts.push('docker image prune -a -f')
  else if (o.images_dangling) parts.push('docker image prune -f')
  if (o.build_cache) parts.push('docker builder prune -f')
  if (o.containers) parts.push('docker container prune -f')
  if (o.networks) parts.push('docker network prune -f')
  return parts.join(' && ')
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
    title: '确认保存原始配置',
    content: () => h('div', null, [
      h('p', null, daemonForm.value.shouldRestart 
        ? '保存配置后将立即重启远程 Docker 服务，这会导致所有运行中的容器短暂中断。' 
        : '配置将保存并备份，但需要手动重启 Docker 服务后才能生效。'),
      h('p', { style: 'margin-top: 8px; color: #f0a020; font-weight: bold;' }, '注意：此操作将修改远程主机的 /etc/docker/daemon.json 文件。')
    ]),
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
    title: '确认保存并应用',
    content: () => h('div', null, [
      h('p', null, daemonForm.value.shouldRestart 
        ? '保存配置后将立即重启远程 Docker 服务，这会导致所有运行中的容器短暂中断。' 
        : '配置将保存并备份，但需要手动重启 Docker 服务后才能生效。'),
      h('p', { style: 'margin-top: 8px; color: #f0a020; font-weight: bold;' }, '注意：此操作将修改远程主机的 /etc/docker/daemon.json 文件。')
    ]),
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

const handlePruneAll = async () => {
  if (!props.hostId) return
  if (!selectedCount.value) {
    message.warning('请至少选择一个清理选项')
    return
  }

  const cmd = previewCommand.value
  dialog.warning({
    title: '确认执行资源清理',
    content: () => h('div', null, [
      h('p', null, '此操作将根据勾选项组合命令一次性执行，被删除的资源不可恢复。'),
      h('p', { style: 'margin-top: 8px; color: #f0a020; font-weight: bold;' }, `将执行命令：${cmd}`),
      h('p', { style: 'margin-top: 8px; color: #d03050; font-size: 12px;' }, '⚠️ 特别注意：清理「所有未使用镜像」会删除所有未被容器引用的镜像；清理「停止的容器」会丢失其配置；请确认无误后再继续。')
    ]),
    positiveText: '确认清理',
    negativeText: '取消',
    onPositiveClick: async () => {
      loading.value.prune = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune`, {
          images_dangling: pruneOptions.value.images_dangling,
          images_unused: pruneOptions.value.images_unused,
          build_cache: pruneOptions.value.build_cache,
          containers: pruneOptions.value.containers,
          networks: pruneOptions.value.networks
        })
        message.success(res.data.message || '资源清理任务已启动')
      } catch (e) { message.error('请求失败') }
      finally { loading.value.prune = false }
    }
  })
}
</script>

<style scoped>
.prune-group {
  padding: 8px 12px;
  border-left: 3px solid var(--n-border-color, #333);
  background: var(--n-card-color, transparent);
  border-radius: 0 4px 4px 0;
}

.prune-group + .prune-group {
  margin-top: 8px;
}

.cmd-preview {
  padding: 10px 12px;
  background: #1e1e1e;
  border-radius: 4px;
  border: 1px solid #333;
  overflow-x: auto;
}

.cmd-preview code {
  color: #7ec699;
  font-family: 'Fira Code', Consolas, Monaco, monospace;
  font-size: 13px;
  white-space: nowrap;
  display: block;
}

.maintenance-panel :deep(.n-checkbox .n-checkbox__label) {
  display: inline-flex;
  align-items: center;
}
</style>
