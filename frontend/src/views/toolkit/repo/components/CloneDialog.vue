<script setup lang="ts">
/**
 * 克隆仓库：支持手动填地址，或直接从已配置的 GitHub / Gitea 账号里挑。
 * 克隆是长任务，走后端异步 job + 轮询，避免 HTTP 请求挂住。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import GlassDialog from '@/components/common/GlassDialog.vue'
import { repoManagerApi, type IdentityProfile, type RemoteRepo, type JobState } from '@/api/repoManager'
import { useNotification } from '@/composables'
import DirectoryPicker from './DirectoryPicker.vue'

const props = defineProps<{
  modelValue: boolean
  cloneDir: string
  identities?: IdentityProfile[]
  /** 设置里保存的克隆代理默认值 */
  cloneProxy?: 'auto' | 'on' | 'off'
  /** 「系统设置 → 网络代理」里配置的代理地址，仅用于提示 */
  proxyUrl?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'cloned', path: string): void
}>()

const { success, error: showError } = useNotification()

const show = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val),
})

const tab = ref<'url' | 'github' | 'gitea'>('url')
const url = ref('')
const name = ref('')
const targetDir = ref('')
const pickerOpen = ref(false)
const identityId = ref('')
const provider = ref<'github' | 'gitea'>('github')
const proxyMode = ref<'auto' | 'on' | 'off'>('auto')

const remoteRepos = ref<RemoteRepo[]>([])
const remoteLoading = ref(false)
const remoteError = ref('')
const search = ref('')

const job = ref<JobState | null>(null)
const starting = ref(false)
let timer: number | undefined

const filteredRemote = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return remoteRepos.value
  return remoteRepos.value.filter(
    (r) =>
      r.full_name.toLowerCase().includes(q) ||
      (r.description || '').toLowerCase().includes(q)
  )
})

const running = computed(() => job.value?.status === 'running')
const finished = computed(() => job.value?.status === 'done')
const failed = computed(() => job.value?.status === 'failed')

const proxyOptions = [
  { title: '跟随容器环境（默认）', value: 'auto' },
  { title: '强制走代理', value: 'on' },
  { title: '强制直连（忽略环境代理）', value: 'off' },
]

const proxyHint = computed(() => {
  if (proxyMode.value === 'auto') {
    return '不干预：容器/宿主里配了 HTTP_PROXY 就跟着走，没配就直连。'
  }
  if (proxyMode.value === 'off') {
    return '强制直连：会清空 http_proxy / https_proxy，避免被容器环境悄悄带进代理。'
  }
  if (!props.proxyUrl) {
    return '还没有代理地址：请先到「系统设置 → 网络代理」填写并保存。'
  }
  return `将通过 ${props.proxyUrl} 克隆（SSH 地址不受影响）。`
})

const identityOptions = computed(() => {
  const options = [
    { title: '按来源自动匹配（GitHub 仓库用 GitHub 身份）', value: '' },
  ]
  for (const profile of props.identities || []) {
    const providerTag = profile.provider === 'github' ? 'GitHub' : profile.provider === 'gitea' ? 'Gitea' : '通用'
    options.push({
      title: `${profile.label}（${providerTag}）<${profile.email}>`,
      value: profile.id,
    })
  }
  return options
})

function stopPolling() {
  if (timer !== undefined) {
    window.clearInterval(timer)
    timer = undefined
  }
}

async function poll(jobId: string) {
  try {
    const state = await repoManagerApi.job(jobId)
    job.value = state
    if (state.status !== 'running') {
      stopPolling()
      if (state.status === 'done') {
        success('克隆完成')
        const path = state.result?.path || ''
        if (path) emit('cloned', path)
      } else {
        showError(state.error || '克隆失败')
      }
    }
  } catch (e: any) {
    stopPolling()
    showError(e.message || '查询克隆进度失败')
  }
}

async function loadRemote(kind: 'github' | 'gitea') {
  provider.value = kind
  remoteLoading.value = true
  remoteError.value = ''
  try {
    const res = await repoManagerApi.remoteRepos(kind)
    remoteRepos.value = res.repos || []
  } catch (e: any) {
    remoteRepos.value = []
    remoteError.value = e.message || '读取仓库列表失败'
  } finally {
    remoteLoading.value = false
  }
}

function pick(item: RemoteRepo) {
  url.value = item.clone_url || item.ssh_url
  name.value = item.name || ''
}

async function startClone() {
  const target = url.value.trim()
  if (!target) {
    showError('请填写仓库地址')
    return
  }
  starting.value = true
  job.value = null
  try {
    const res = await repoManagerApi.clone(
      target,
      name.value.trim(),
      tab.value === 'url' ? '' : tab.value,
      targetDir.value.trim(),
      identityId.value,
      proxyMode.value
    )
    job.value = {
      id: res.job_id,
      kind: 'clone',
      status: 'running',
      progress: 0,
      phase: '准备中',
      lines: [],
      result: null,
      error: '',
    }
    stopPolling()
    timer = window.setInterval(() => poll(res.job_id), 700)
  } catch (e: any) {
    showError(e.message || '无法启动克隆')
  } finally {
    starting.value = false
  }
}

function reset() {
  stopPolling()
  job.value = null
  url.value = ''
  name.value = ''
  search.value = ''
  targetDir.value = props.cloneDir
  identityId.value = ''
  proxyMode.value = props.cloneProxy || 'auto'
}

watch(show, (visible) => {
  if (!visible) {
    stopPolling()
    return
  }
  reset()
  if (tab.value !== 'url') loadRemote(tab.value as 'github' | 'gitea')
})

watch(tab, (val) => {
  if (val === 'url') return
  loadRemote(val as 'github' | 'gitea')
})

onBeforeUnmount(stopPolling)
</script>

<template>
  <GlassDialog
    v-model="show"
    :max-width="820"
    title="克隆仓库"
    icon="mdi-source-repository"
    :cancel-text="finished ? '关闭' : '取消'"
  >
    <v-tabs v-model="tab" density="compact" color="primary" class="mb-4">
      <v-tab value="url">手动地址</v-tab>
      <v-tab value="github">从 GitHub 选择</v-tab>
      <v-tab value="gitea">从 Gitea 选择</v-tab>
    </v-tabs>

    <!-- 远端仓库列表 -->
    <div v-if="tab !== 'url'" class="mb-4">
      <v-text-field
        v-model="search"
        density="compact"
        variant="outlined"
        prepend-inner-icon="mdi-magnify"
        label="搜索仓库"
        hide-details
        class="mb-3"
      />
      <div v-if="remoteLoading" class="d-flex align-center ga-2 py-4 justify-center">
        <v-progress-circular indeterminate size="18" width="2" /> 正在读取账号下的仓库…
      </div>
      <v-alert v-else-if="remoteError" type="warning" variant="tonal" density="compact">
        {{ remoteError }}
        <div class="text-caption mt-1">
          请先到「系统设置 → 第三方 API 集成」配置 {{ tab === 'github' ? 'GitHub' : 'Gitea' }} 令牌。
        </div>
      </v-alert>
      <div v-else class="remote-list">
        <v-list density="compact" class="py-0">
          <v-list-item
            v-for="item in filteredRemote"
            :key="item.full_name"
            :active="url === (item.clone_url || item.ssh_url)"
            @click="pick(item)"
          >
            <v-list-item-title class="d-flex align-center ga-2">
              <span class="text-truncate">{{ item.full_name }}</span>
              <v-chip v-if="item.private" size="x-small" variant="tonal">私有</v-chip>
            </v-list-item-title>
            <v-list-item-subtitle v-if="item.description" class="text-caption">
              {{ item.description }}
            </v-list-item-subtitle>
          </v-list-item>
          <v-list-item v-if="!filteredRemote.length">
            <v-list-item-title class="text-caption">没有匹配的仓库</v-list-item-title>
          </v-list-item>
        </v-list>
      </div>
    </div>

    <v-text-field
      v-model="url"
      label="仓库地址"
      density="compact"
      variant="outlined"
      placeholder="https://github.com/owner/repo.git 或 git@github.com:owner/repo.git"
      hide-details
      class="mb-3"
    />
    <v-text-field
      v-model="name"
      label="目标目录名（留空则取仓库名）"
      density="compact"
      variant="outlined"
      hide-details
      class="mb-3"
    />
    <div class="d-flex ga-3 align-center mb-3">
      <v-text-field
        v-model="targetDir"
        label="落地目录"
        density="compact"
        variant="outlined"
        hide-details
        placeholder="/vol1/1000/NVME/repos"
      />
      <v-btn
        size="small"
        variant="tonal"
        color="info"
        prepend-icon="mdi-folder-search-outline"
        @click="pickerOpen = true"
      >
        浏览
      </v-btn>
    </div>
    <v-select
      v-model="identityId"
      :items="identityOptions"
      item-title="title"
      item-value="value"
      label="提交者身份（克隆完成后写入该仓库）"
      density="compact"
      variant="outlined"
      hide-details
    />
    <v-select
      v-model="proxyMode"
      :items="proxyOptions"
      item-title="title"
      item-value="value"
      label="网络代理"
      prepend-inner-icon="mdi-shield-network-outline"
      density="compact"
      variant="outlined"
      class="mt-3"
      hide-details
    />
    <div class="text-caption mt-1">{{ proxyHint }}</div>

    <!-- 进度 -->
    <div v-if="job" class="mt-4">
      <div class="d-flex align-center ga-2 mb-1">
        <v-icon :color="failed ? 'error' : finished ? 'success' : 'primary'" size="18">
          {{ failed ? 'mdi-alert-circle' : finished ? 'mdi-check-circle' : 'mdi-progress-clipboard-check' }}
        </v-icon>
        <span class="text-body-2">{{ job.phase || '处理中' }}</span>
        <v-spacer />
        <span class="text-caption">{{ job.progress }}%</span>
      </div>
      <v-progress-linear
        :model-value="job.progress"
        :color="failed ? 'error' : finished ? 'success' : 'primary'"
        height="6"
        rounded
      />
      <div class="clone-log mt-2">{{ job.lines.join('\n') || '等待输出…' }}</div>
    </div>

    <DirectoryPicker
      v-model="pickerOpen"
      :initial-path="targetDir || cloneDir"
      title="选择克隆落地目录"
      @picked="targetDir = $event"
    />

    <template #actions>
      <v-btn
        color="primary"
        variant="tonal"
        prepend-icon="mdi-download"
        :loading="starting || running"
        :disabled="finished"
        @click="startClone"
      >
        开始克隆
      </v-btn>
    </template>
  </GlassDialog>
</template>

<style scoped>
.remote-list {
  max-height: 240px;
  overflow: auto;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
.clone-log {
  height: 110px;
  overflow: auto;
  padding: 8px;
  border-radius: 8px;
  background: var(--am-surface-bg);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 11px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
