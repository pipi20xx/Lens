<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError, warning } = useNotification()
const { confirm } = useConfirm()

const props = defineProps<{
  active: boolean
  hostId: string | null
}>()

// ========== 自动加载 ==========
watch([() => props.active, () => props.hostId], ([active, hostId]) => {
  if (active && hostId) loadDaemonConfig()
})
onMounted(() => { if (props.active && props.hostId) loadDaemonConfig() })

// ========== 资源清理 ==========
const pruneLoading = ref(false)
const pruneOptions = ref({ images_dangling: false, images_unused: false, build_cache: false, containers: false, networks: false })

const selectedPruneCount = computed(() => {
  const o = pruneOptions.value
  let count = 0
  if (o.images_unused) count += 1; else if (o.images_dangling) count += 1
  if (o.build_cache) count += 1; if (o.containers) count += 1; if (o.networks) count += 1
  return count
})

const previewPruneCommand = computed(() => {
  const o = pruneOptions.value; const parts: string[] = []
  if (o.images_unused) parts.push('docker image prune -a -f')
  else if (o.images_dangling) parts.push('docker image prune -f')
  if (o.build_cache) parts.push('docker builder prune -f')
  if (o.containers) parts.push('docker container prune -f')
  if (o.networks) parts.push('docker network prune -f')
  return parts.join(' && ')
})

async function handlePrune() {
  if (!props.hostId) return
  if (!selectedPruneCount.value) { warning('请至少选择一个清理选项'); return }
  const ok = await confirm({ title: '确认执行资源清理', content: `此操作将根据勾选项组合命令一次性执行。将执行命令：${previewPruneCommand.value}`, confirmColor: 'error' })
  if (!ok) return
  pruneLoading.value = true
  try { const res = await dockerApi.pruneAll(props.hostId, pruneOptions.value); success(res?.message || '清理任务已启动') }
  catch { showError('清理失败') }
  finally { pruneLoading.value = false }
}

// ========== Daemon 配置 ==========
const daemonForm = ref({ mirrors: '', insecure: '', logSize: '100m', logFiles: 5, liveRestore: true, shouldRestart: false, proxyEnabled: false, proxyHost: '', proxyPort: '', proxyUser: '', proxyPass: '', noProxy: 'localhost,127.0.0.1' })
const rawDaemonConfig = ref<any>({})
const daemonLoading = ref(false)
const showRawModal = ref(false)
const rawJsonContent = ref('')
const rawJsonError = ref<string | null>(null)

async function loadDaemonConfig() {
  if (!props.hostId) return
  daemonLoading.value = true
  try {
    const res: any = await dockerApi.getDaemonConfig(props.hostId)
    rawDaemonConfig.value = res || {}
    const r = res || {}
    daemonForm.value.mirrors = (r['registry-mirrors'] || []).join('\n')
    daemonForm.value.insecure = (r['insecure-registries'] || []).join('\n')
    daemonForm.value.logSize = r['log-opts']?.['max-size'] || '100m'
    daemonForm.value.logFiles = parseInt(r['log-opts']?.['max-file'] || '5')
    daemonForm.value.liveRestore = r['live-restore'] ?? true
    const proxies = r['proxies'] || {}; const httpProxy = proxies['http-proxy'] || ''
    daemonForm.value.noProxy = proxies['no-proxy'] || 'localhost,127.0.0.1'
    if (httpProxy) {
      daemonForm.value.proxyEnabled = true
      try {
        const url = new URL(httpProxy)
        daemonForm.value.proxyHost = url.hostname
        daemonForm.value.proxyPort = url.port
        daemonForm.value.proxyUser = decodeURIComponent(url.username)
        daemonForm.value.proxyPass = decodeURIComponent(url.password)
      } catch { daemonForm.value.proxyHost = httpProxy }
    } else { daemonForm.value.proxyEnabled = false }
  } catch { showError('无法读取 Daemon 配置') }
  finally { daemonLoading.value = false }
}

async function openRawEdit() {
  if (!props.hostId) return
  daemonLoading.value = true
  try {
    const res = await dockerApi.getDaemonConfigRaw(props.hostId)
    rawJsonContent.value = res?.content || ''; rawJsonError.value = null; showRawModal.value = true
  } catch { showError('无法读取原始配置') }
  finally { daemonLoading.value = false }
}

function validateRawJson(val: string) {
  if (!val.trim()) { rawJsonError.value = '内容不能为空'; return }
  try { JSON.parse(val); rawJsonError.value = null } catch { rawJsonError.value = '无效的 JSON 格式' }
}

async function handleSaveDaemonConfig() {
  if (!props.hostId) return
  const ok = await confirm({
    title: '确认保存并应用',
    content: daemonForm.value.shouldRestart ? '保存配置后将立即重启远程 Docker 服务。' : '配置将保存并备份，需要手动重启 Docker 服务后才能生效。',
    confirmColor: 'warning'
  })
  if (!ok) return
  const newConfig = { ...rawDaemonConfig.value }
  newConfig['registry-mirrors'] = daemonForm.value.mirrors.split('\n').map((i: string) => i.trim()).filter(Boolean)
  newConfig['insecure-registries'] = daemonForm.value.insecure.split('\n').map((i: string) => i.trim()).filter(Boolean)
  newConfig['log-driver'] = 'json-file'
  newConfig['log-opts'] = { 'max-size': daemonForm.value.logSize, 'max-file': daemonForm.value.logFiles.toString() }
  newConfig['live-restore'] = daemonForm.value.liveRestore
  if (daemonForm.value.proxyEnabled && daemonForm.value.proxyHost) {
    let auth = ''
    if (daemonForm.value.proxyUser) auth = `${encodeURIComponent(daemonForm.value.proxyUser)}:${encodeURIComponent(daemonForm.value.proxyPass)}@`
    const port = daemonForm.value.proxyPort ? `:${daemonForm.value.proxyPort}` : ''
    const host = daemonForm.value.proxyHost.includes('://') ? daemonForm.value.proxyHost.split('://')[1] : daemonForm.value.proxyHost
    const proxyUrl = `http://${auth}${host}${port}`
    newConfig['proxies'] = { 'http-proxy': proxyUrl, 'https-proxy': proxyUrl, 'no-proxy': daemonForm.value.noProxy }
  } else { delete newConfig['proxies'] }
  daemonLoading.value = true
  try { const res = await dockerApi.saveDaemonConfig(props.hostId, newConfig, daemonForm.value.shouldRestart); success(res?.message || '配置已保存'); loadDaemonConfig() }
  catch (err: any) { showError(err.message || '保存失败') }
  finally { daemonLoading.value = false }
}

async function handleSaveRawJson() {
  if (!props.hostId || rawJsonError.value) return
  const ok = await confirm({ title: '确认保存原始配置', content: '此操作将修改远程主机的 /etc/docker/daemon.json 文件。', confirmColor: 'warning' })
  if (!ok) return
  daemonLoading.value = true
  try {
    const res = await dockerApi.saveDaemonConfigRaw(props.hostId, rawJsonContent.value, daemonForm.value.shouldRestart)
    success(res?.message || '配置已保存'); showRawModal.value = false; loadDaemonConfig()
  } catch (err: any) { showError(err.message || '保存失败') }
  finally { daemonLoading.value = false }
}

defineExpose({ loadDaemonConfig })
</script>

<template>
  <div>
    <!-- Daemon 配置 -->
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start>mdi-cog-outline</v-icon> Docker Daemon 配置
        <v-spacer />
        <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-code-json" @click="openRawEdit" class="mr-2">直接编辑 JSON</v-btn>
        <span class="text-caption text-warning"><v-icon size="14">mdi-alert-outline</v-icon> 需要 Root 权限的 SSH 账户</span>
      </v-card-title>
      <v-divider />
      <v-alert type="info" variant="tonal" density="compact" class="ma-4 mb-0" text="该配置将直接修改远程主机的 /etc/docker/daemon.json 文件。保存前建议确保了解配置项的含义。" />

      <v-card-text class="pa-4" v-if="!daemonLoading">
        <v-row>
          <v-col cols="12" sm="6">
            <v-textarea v-model="daemonForm.mirrors" label="镜像加速器 (Registry Mirrors)" variant="outlined" density="compact" rows="3" hint="每行一个 URL" persistent-hint class="mb-3" />
            <v-textarea v-model="daemonForm.insecure" label="私有仓库 (Insecure Registries)" variant="outlined" density="compact" rows="3" hint="每行一个地址" persistent-hint class="mb-3" />

            <v-card variant="outlined" class="pa-3">
              <div class="d-flex align-center justify-space-between mb-2">
                <div class="d-flex align-center ga-2">
                  <span class="text-subtitle-2">代理设置 (Proxies)</span>
                  <v-chip :color="daemonForm.proxyEnabled ? 'success' : 'default'" size="x-small" variant="tonal">{{ daemonForm.proxyEnabled ? '已启用' : '已禁用' }}</v-chip>
                </div>
                <v-switch v-model="daemonForm.proxyEnabled" density="compact" hide-details color="primary" />
              </div>
              <template v-if="daemonForm.proxyEnabled">
                <v-alert type="warning" variant="tonal" density="compact" class="mb-3" text="Docker 守护进程通常仅支持 HTTP/HTTPS 协议代理，暂不支持 SOCKS5。" />
                <v-row dense>
                  <v-col cols="8"><v-text-field v-model="daemonForm.proxyHost" label="服务器地址" variant="outlined" density="compact" placeholder="192.168.50.66" /></v-col>
                  <v-col cols="4"><v-text-field v-model="daemonForm.proxyPort" label="端口" variant="outlined" density="compact" placeholder="7890" /></v-col>
                  <v-col cols="6"><v-text-field v-model="daemonForm.proxyUser" label="用户名 (可选)" variant="outlined" density="compact" /></v-col>
                  <v-col cols="6"><v-text-field v-model="daemonForm.proxyPass" label="密码 (可选)" variant="outlined" density="compact" type="password" /></v-col>
                  <v-col cols="12"><v-text-field v-model="daemonForm.noProxy" label="无需代理地址 (No Proxy)" variant="outlined" density="compact" placeholder="localhost,127.0.0.1" /></v-col>
                </v-row>
              </template>
            </v-card>
          </v-col>

          <v-col cols="12" sm="6">
            <v-row dense>
              <v-col cols="6"><v-text-field v-model="daemonForm.logSize" label="日志单文件大小" variant="outlined" density="compact" placeholder="100m" /></v-col>
              <v-col cols="6"><v-text-field v-model.number="daemonForm.logFiles" label="日志保留份数" variant="outlined" density="compact" type="number" :min="1" /></v-col>
            </v-row>
            <v-checkbox v-model="daemonForm.liveRestore" density="compact" hide-details label="开启 Live Restore (守护进程重启时不停止容器)" class="mb-2" />
            <v-alert type="info" variant="tonal" density="compact" class="mb-3" text="保存时将自动备份旧配置至本地 data 目录及远程 .bak 文件。" />
            <v-checkbox v-model="daemonForm.shouldRestart" density="compact" hide-details label="保存后重启 Docker 服务 (会导致容器短暂中断)" class="mb-4" />
            <div class="d-flex justify-end">
              <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" :loading="daemonLoading" @click="handleSaveDaemonConfig">保存并应用配置</v-btn>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-text v-else class="pa-4 text-center"><v-progress-circular indeterminate color="primary" /></v-card-text>
    </v-card>

    <!-- 资源清理 -->
    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start>mdi-broom</v-icon> Docker 资源清理
        <v-spacer />
        <span class="text-caption text-warning"><v-icon size="14">mdi-alert-outline</v-icon> 勾选项越多，清理越彻底，请谨慎选择</span>
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-4">
        <p class="text-body-2 text-medium-emphasis mb-4">勾选需要清理的资源类型，点击下方按钮将根据勾选项组合命令一次性执行。</p>

        <div class="prune-group mb-3">
          <div class="text-subtitle-2 mb-2">镜像 (Images)</div>
          <v-checkbox v-model="pruneOptions.images_dangling" density="compact" hide-details :disabled="pruneOptions.images_unused" label="清理未标签镜像 (Dangling) — docker image prune -f" class="ml-4" />
          <v-checkbox v-model="pruneOptions.images_unused" density="compact" hide-details label="清理所有未使用镜像 (Unused) — docker image prune -a -f" class="ml-4" />
          <v-alert v-if="pruneOptions.images_unused" type="info" variant="tonal" density="compact" class="ml-4 mt-1" text="勾选「所有未使用镜像」时已包含未标签镜像。" />
        </div>
        <div class="prune-group mb-3">
          <div class="text-subtitle-2 mb-2">构建缓存 (Build Cache)</div>
          <v-checkbox v-model="pruneOptions.build_cache" density="compact" hide-details label="清理 BuildKit / Buildx 构建缓存 — docker builder prune -f" class="ml-4" />
        </div>
        <div class="prune-group mb-3">
          <div class="text-subtitle-2 mb-2">容器 (Containers)</div>
          <v-checkbox v-model="pruneOptions.containers" density="compact" hide-details label="清理所有停止状态的容器 — docker container prune -f" class="ml-4" />
        </div>
        <div class="prune-group mb-3">
          <div class="text-subtitle-2 mb-2">网络 (Networks)</div>
          <v-checkbox v-model="pruneOptions.networks" density="compact" hide-details label="清理未被容器使用的网络 — docker network prune -f" class="ml-4" />
        </div>

        <div v-if="previewPruneCommand" class="code-block mb-4">
          <span class="text-caption text-medium-emphasis" style="font-size:12px">将要执行的命令：</span>
          <code>{{ previewPruneCommand }}</code>
        </div>
        <div class="d-flex align-center justify-space-between">
          <span class="text-caption text-medium-emphasis">共勾选 {{ selectedPruneCount }} 项</span>
          <v-btn color="error" variant="flat" :loading="pruneLoading" :disabled="!selectedPruneCount" @click="handlePrune" prepend-icon="mdi-delete-sweep-outline">开始清理</v-btn>
        </div>
      </v-card-text>
    </v-card>

    <!-- 原始 JSON 编辑弹窗 -->
    <v-dialog v-model="showRawModal" max-width="800">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4"><v-icon start>mdi-code-json</v-icon> 直接编辑 daemon.json</v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-alert type="warning" variant="tonal" density="compact" class="mb-3" text="警告：直接编辑 JSON 可能会导致 Docker 无法启动。系统将会在保存前验证 JSON 格式并自动创建备份。" />
          <v-textarea v-model="rawJsonContent" variant="outlined" rows="18" style="font-family:'Fira Code','JetBrains Mono',monospace" :error-messages="rawJsonError ? [rawJsonError] : []" @update:model-value="validateRawJson" />
          <v-checkbox v-model="daemonForm.shouldRestart" density="compact" hide-details label="保存后重启 Docker 服务" class="mt-3" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showRawModal = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="handleSaveRawJson" :disabled="!!rawJsonError" :loading="daemonLoading">保存原始配置</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </div>
</template>

