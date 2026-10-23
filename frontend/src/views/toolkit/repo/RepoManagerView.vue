<script setup lang="ts">
/**
 * 代码仓库管理（工具 → 代码仓库）
 *
 * 定位：只管 git，不做 IDE —— 扫描服务器上的工作副本，暂存 / 提交 / 推送 / 拉取 / 克隆。
 * 所有 git 操作都在后端以子进程执行，前端只负责展示与触发。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import {
  repoManagerApi,
  type BranchItem,
  type CommitItem,
  type IdentityProfile,
  type RepoFile,
  type RepoIdentity,
  type RepoStatus,
  type RepoSummary,
} from '@/api/repoManager'
import { useConfirm, useNotification } from '@/composables'
import CloneDialog from './components/CloneDialog.vue'
import DiffViewer from './components/DiffViewer.vue'
import FileTree from './components/FileTree.vue'
import FileViewer from './components/FileViewer.vue'
import IdentityDialog from './components/IdentityDialog.vue'
import RepoSelect from './components/RepoSelect.vue'
import RepoSettingsDialog from './components/RepoSettingsDialog.vue'

const { success, error: showError, warning } = useNotification()
const { confirm } = useConfirm()
const route = useRoute()
// ---------------- 状态 ----------------
const repos = ref<RepoSummary[]>([])
const roots = ref<string[]>([])
const listLoading = ref(false)
const selected = ref('')
const status = ref<RepoStatus | null>(null)
const statusLoading = ref(false)
const activeTab = ref<'changes' | 'history' | 'branches' | 'files'>('changes')

const commits = ref<CommitItem[]>([])
const branches = ref<BranchItem[]>([])
const logLoading = ref(false)

const commitMessage = ref('')
const amend = ref(false)
const busy = ref('')

const diffText = ref('')
const diffFile = ref('')
const diffLoading = ref(false)

const cloneDialog = ref(false)
const settingsDialog = ref(false)
const identityDialog = ref(false)
const identityInfo = ref<RepoIdentity | null>(null)
const identityProfiles = ref<IdentityProfile[]>([])
const cloneDir = ref('/vol1/1000/NVME/repos')

const newBranchName = ref('')
const treeRef = ref<InstanceType<typeof FileTree> | null>(null)
const viewerRef = ref<InstanceType<typeof FileViewer> | null>(null)
const previewFile = ref('')
const fileDirty = ref(false)
const fetchJob = ref<{ progress: number; phase: string; status: string; result: any } | null>(null)
let timer: number | undefined
let fetchTimer: number | undefined
let preferredPath = ''

// ---------------- 派生 ----------------
const current = computed<RepoSummary>(
  () =>
    repos.value.find((r) => r.path === selected.value) || {
      path: '',
      name: '',
      ok: true,
      branch: '',
      detached: false,
      upstream: '',
      ahead: 0,
      behind: 0,
      counts: { staged: 0, unstaged: 0, untracked: 0, conflict: 0 },
      dirty: false,
      pinned: false,
    }
)
const hasCurrent = computed(() => !!selected.value && repos.value.some((r) => r.path === selected.value))

const stagedFiles = computed(() => status.value?.files.filter((f) => f.staged) || [])
const unstagedFiles = computed(
  () => status.value?.files.filter((f) => f.unstaged && f.kind === 'change') || []
)
const untrackedFiles = computed(() => status.value?.files.filter((f) => f.kind === 'untracked') || [])
const conflictFiles = computed(() => status.value?.files.filter((f) => f.kind === 'conflict') || [])

const hasChanges = computed(() => {
  const c = status.value?.counts
  return !!c && c.staged + c.unstaged + c.untracked + c.conflict > 0
})

const canCommit = computed(
  () => !busy.value && (!!status.value?.counts.staged || amend.value) && commitMessage.value.trim().length > 0
)

// ---------------- 数据加载 ----------------
async function loadRepos(force = false, silent = false) {
  if (!silent) listLoading.value = true
  try {
    const res = await repoManagerApi.listRepos(force)
    repos.value = res.repos || []
    roots.value = res.roots || []
    if (!selected.value && repos.value.length) {
      selected.value =
        preferredPath && repos.value.some((r) => r.path === preferredPath)
          ? preferredPath
          : repos.value[0].path
    } else if (selected.value && !repos.value.some((r) => r.path === selected.value)) {
      status.value = null
      selected.value = ''
    }
  } catch (e: any) {
    if (!silent) showError(e.message || '读取仓库列表失败')
  } finally {
    if (!silent) listLoading.value = false
  }
}

async function loadStatus(silent = false) {
  if (!selected.value) return
  if (!silent) statusLoading.value = true
  try {
    status.value = await repoManagerApi.status(selected.value)
    // 文件被处理掉后清空 diff 面板
    if (diffFile.value && !status.value.files.some((f) => f.path === diffFile.value)) {
      diffFile.value = ''
      diffText.value = ''
    }
  } catch (e: any) {
    if (!silent) showError(e.message || '读取仓库状态失败')
  } finally {
    if (!silent) statusLoading.value = false
  }
}

async function loadBranches() {
  if (!selected.value) return
  try {
    const res = await repoManagerApi.branches(selected.value)
    branches.value = res.branches || []
  } catch {
    branches.value = []
  }
}

async function loadLog() {
  if (!selected.value) return
  logLoading.value = true
  try {
    const res = await repoManagerApi.log(selected.value, 60)
    commits.value = res.commits || []
  } catch {
    commits.value = []
  } finally {
    logLoading.value = false
  }
}

async function loadIdentity() {
  if (!selected.value) return
  try {
    identityInfo.value = await repoManagerApi.identity(selected.value)
  } catch {
    identityInfo.value = null
  }
}

function onRepoSwitch(path: string) {
  status.value = null
  commits.value = []
  branches.value = []
  diffFile.value = ''
  diffText.value = ''
  commitMessage.value = ''
  amend.value = false
  identityInfo.value = null
  previewFile.value = ''
  fileDirty.value = false
  if (!path) return
  loadStatus()
  loadBranches()
  loadLog()
  loadIdentity()
}

// 下拉里切换仓库时统一切换上下文
watch(selected, (path) => onRepoSwitch(path))

async function refreshAll(silent = false) {
  await loadStatus(silent)
  await loadRepos(!silent, silent)
  await loadBranches()
  await loadIdentity()
}

/** 工具栏「刷新」：状态 + 列表 + 分支 + 身份 + 目录树，一次全刷新 */
async function refreshEverything() {
  await refreshAll()
  refreshTree()
}

// ---------------- 暂存 / 提交 ----------------
async function fileAction(file: RepoFile, action: 'stage' | 'unstage' | 'discard') {
  if (action === 'discard') {
    const ok = await confirm({
      title: '丢弃改动',
      content: `确定丢弃 ${file.path} 的工作区改动？此操作不可撤销。`,
      confirmText: '丢弃',
      confirmColor: 'error',
    })
    if (!ok) return
  }
  busy.value = action
  try {
    await repoManagerApi.stage(selected.value, action, [file.path])
    await refreshAll()
  } catch (e: any) {
    showError(e.message || '操作失败')
  } finally {
    busy.value = ''
  }
}

async function bulkAction(action: 'stage' | 'unstage' | 'discard', paths: string[]) {
  if (!paths.length) return
  if (action === 'discard') {
    const ok = await confirm({
      title: '丢弃全部改动',
      content: `确定丢弃这 ${paths.length} 个文件的工作区改动？此操作不可撤销。`,
      confirmText: '全部丢弃',
      confirmColor: 'error',
    })
    if (!ok) return
  }
  busy.value = action
  try {
    await repoManagerApi.stage(selected.value, action, paths)
    await refreshAll()
  } catch (e: any) {
    showError(e.message || '操作失败')
  } finally {
    busy.value = ''
  }
}

async function doCommit() {
  if (!canCommit.value) return
  busy.value = 'commit'
  try {
    const res = await repoManagerApi.commit(selected.value, commitMessage.value.trim(), amend.value)
    success(`已提交 ${res.commit ? res.commit.slice(0, 7) : ''}`)
    commitMessage.value = ''
    amend.value = false
    await refreshAll()
    await loadLog()
  } catch (e: any) {
    showError(e.message || '提交失败')
  } finally {
    busy.value = ''
  }
}

// ---------------- 远端同步 ----------------
async function doPush() {
  if (!hasCurrent.value) return
  const setUpstream = !current.value.upstream
  busy.value = 'push'
  try {
    const res = await repoManagerApi.push(selected.value, setUpstream, false)
    success(res.detail || '已推送')
    await refreshAll()
  } catch (e: any) {
    showError(e.message || '推送失败')
  } finally {
    busy.value = ''
  }
}

async function doForcePush() {
  const ok = await confirm({
    title: '强制推送',
    content: '将用本地提交覆盖远端分支（--force-with-lease）。如果他人已推送新提交，请先拉取。确定继续？',
    confirmText: '强制推送',
    confirmColor: 'warning',
  })
  if (!ok) return
  busy.value = 'push'
  try {
    const res = await repoManagerApi.push(selected.value, false, true)
    success(res.detail || '已强制推送')
    await refreshAll()
  } catch (e: any) {
    showError(e.message || '推送失败')
  } finally {
    busy.value = ''
  }
}

async function doPull(rebase = false) {
  busy.value = 'pull'
  try {
    const res = await repoManagerApi.pull(selected.value, rebase)
    success(res.detail || '已更新')
    await refreshAll()
    await loadLog()
  } catch (e: any) {
    showError(e.message || '拉取失败')
  } finally {
    busy.value = ''
  }
}

async function doFetch() {
  busy.value = 'fetch'
  try {
    await repoManagerApi.fetch(selected.value)
    success('已获取远端最新状态')
    await refreshAll()
  } catch (e: any) {
    showError(e.message || 'fetch 失败')
  } finally {
    busy.value = ''
  }
}

function stopFetchPolling() {
  if (fetchTimer !== undefined) {
    window.clearInterval(fetchTimer)
    fetchTimer = undefined
  }
}

async function fetchAll() {
  if (!repos.value.length) {
    warning('还没有任何仓库可以 fetch')
    return
  }
  const ok = await confirm({
    title: '全部 fetch',
    content:
      `将对 ${repos.value.length} 个仓库逐个执行 git fetch --prune。\n\n` +
      '它只更新「远端分支的最新位置」，不会改动工作区文件，也不会自动合并。' +
      '跑完后就能直接看出哪些仓库落后、哪些有未推送提交。',
    confirmText: '开始 fetch',
  })
  if (!ok) return

  try {
    const res = await repoManagerApi.fetchAll()
    fetchJob.value = { progress: 0, phase: '准备中', status: 'running', result: null }
    stopFetchPolling()
    fetchTimer = window.setInterval(async () => {
      try {
        const state = await repoManagerApi.job(res.job_id)
        fetchJob.value = {
          progress: state.progress,
          phase: state.phase || '',
          status: state.status,
          result: state.result,
        }
        if (state.status === 'running') return

        stopFetchPolling()
        if (state.status === 'done') {
          const result = state.result || {}
          success(`fetch 完成：成功 ${result.ok ?? 0} 个，失败 ${result.failed ?? 0} 个`)
          await loadRepos(true, true)
        } else {
          showError(state.error || 'fetch 失败')
        }
        window.setTimeout(() => {
          fetchJob.value = null
        }, 4000)
      } catch {
        stopFetchPolling()
      }
    }, 1200)
  } catch (e: any) {
    showError(e.message || '无法启动批量拉取')
  }
}

// ---------------- 冲突 ----------------
async function resolveConflict(file: RepoFile, strategy: 'ours' | 'theirs') {
  try {
    await repoManagerApi.resolve(selected.value, file.path, strategy)
    success(strategy === 'ours' ? '已保留本地版本' : '已保留远端版本')
    await refreshAll()
  } catch (e: any) {
    showError(e.message || '解决冲突失败')
  }
}

// ---------------- 分支 ----------------
async function switchBranch(name: string) {
  if (!name || name === current.value?.branch) return
  busy.value = 'branch'
  try {
    await repoManagerApi.switchBranch(selected.value, name)
    success(`已切换到 ${name}`)
    await refreshAll()
    await loadLog()
  } catch (e: any) {
    showError(e.message || '切换分支失败')
  } finally {
    busy.value = ''
  }
}

async function createBranch() {
  const name = newBranchName.value.trim()
  if (!name) return
  busy.value = 'branch'
  try {
    await repoManagerApi.createBranch(selected.value, name, true)
    success(`已创建并切换到 ${name}`)
    newBranchName.value = ''
    await refreshAll()
  } catch (e: any) {
    showError(e.message || '创建分支失败')
  } finally {
    busy.value = ''
  }
}

// ---------------- diff ----------------
async function openDiff(file: RepoFile) {
  diffFile.value = file.path
  diffLoading.value = true
  diffText.value = ''
  const stagedOnly = file.staged && !file.unstaged
  try {
    const res = await repoManagerApi.diff(
      selected.value,
      file.path,
      stagedOnly,
      file.kind === 'untracked'
    )
    diffText.value = res.diff || ''
  } catch (e: any) {
    showError(e.message || '读取 diff 失败')
  } finally {
    diffLoading.value = false
  }
}

// ---------------- 克隆 ----------------
async function onCloned(path: string) {
  await loadRepos(true)
  if (path) selected.value = path
  cloneDialog.value = false
}

async function onSettingsSaved() {
  await loadSettingsHint()
  await loadRepos(true)
}

function refreshTree() {
  treeRef.value?.refresh()
}

/** 点树里的文件：先确认未保存改动，再切到「文件」标签 */
async function onTreeSelect(path: string) {
  const ok = (await viewerRef.value?.confirmLeave?.()) ?? true
  if (!ok) return
  previewFile.value = path
  activeTab.value = 'files'
}
// ---------------- 工具 ----------------
function iconOf(file: RepoFile): string {
  if (file.kind === 'untracked') return 'mdi-plus-circle-outline'
  if (file.kind === 'conflict') return 'mdi-alert-circle-outline'
  if (file.kind === 'rename') return 'mdi-swap-horizontal'
  switch (file.xy.replace(/[^A-Z]/g, '')[0]) {
    case 'A':
      return 'mdi-plus-box-outline'
    case 'D':
      return 'mdi-minus-box-outline'
    case 'R':
      return 'mdi-swap-horizontal'
    default:
      return 'mdi-file-edit-outline'
  }
}

function colorOf(file: RepoFile): string {
  if (file.kind === 'untracked') return 'success'
  if (file.kind === 'conflict') return 'error'
  if (file.staged) return 'primary'
  return 'warning'
}

async function loadSettingsHint() {
  try {
    const res = await repoManagerApi.getSettings()
    cloneDir.value = res.settings.clone_dir || cloneDir.value
    identityProfiles.value = res.settings.identities || []
  } catch {
    /* 读不到就用默认提示 */
  }
}

onMounted(async () => {
  preferredPath = String(route.query.path || '')
  await loadSettingsHint()
  await loadRepos(true)
  timer = window.setInterval(() => {
    if (!busy.value) loadStatus(true)
  }, 12000)
})

onBeforeUnmount(() => {
  if (timer !== undefined) window.clearInterval(timer)
  stopFetchPolling()
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-source-branch</v-icon> 代码仓库
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-4">
      管理服务器上的 git 工作副本：查看改动、暂存、提交、推送，也可以一键克隆新仓库。
    </p>

    <!-- 工具栏：仓库选择 + 当前仓库状态 + 全部操作都在这一行 -->
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <div class="d-flex align-center pa-4 ga-2 flex-wrap">
        <RepoSelect v-model="selected" :repos="repos" />

        <template v-if="hasCurrent">
          <v-chip v-if="current.branch" size="small" variant="tonal">
            {{ current.branch }}
          </v-chip>
          <v-chip v-if="current.ahead" size="small" color="warning" variant="tonal">
            ↑{{ current.ahead }}
          </v-chip>
          <v-chip v-if="current.behind" size="small" color="info" variant="tonal">
            ↓{{ current.behind }}
          </v-chip>
          <v-chip
            size="small"
            variant="tonal"
            :color="identityInfo?.source === 'none' ? 'warning' : undefined"
            title="当前仓库使用的提交者身份（点击修改）"
            @click="identityDialog = true"
          >
            <v-icon start size="14">mdi-account-outline</v-icon>
            {{ identityInfo?.display.name || '未设置提交者' }}
          </v-chip>
        </template>

        <v-chip v-if="fetchJob" size="small" color="info" variant="tonal">
          <v-progress-circular
            v-if="fetchJob.status === 'running'"
            indeterminate
            size="12"
            width="2"
            class="mr-1"
          />
          {{ fetchJob.phase || 'fetch 中' }}
          <span v-if="fetchJob.status === 'running'" class="ml-1">{{ fetchJob.progress }}%</span>
        </v-chip>

        <v-spacer />

        <v-btn
          size="small"
          variant="tonal"
          color="info"
          prepend-icon="mdi-refresh"
          :loading="listLoading || statusLoading"
          @click="refreshEverything"
        >
          刷新
        </v-btn>
        <v-btn
          size="small"
          variant="tonal"
          color="info"
          prepend-icon="mdi-download"
          :disabled="!hasCurrent"
          :loading="busy === 'fetch'"
          @click="doFetch"
        >
          fetch
        </v-btn>
        <v-menu>
          <template #activator="{ props: menuProps }">
            <v-btn
              size="small"
              variant="tonal"
              color="info"
              prepend-icon="mdi-arrow-down-bold"
              :disabled="!hasCurrent"
              :loading="busy === 'pull'"
              v-bind="menuProps"
            >
              拉取
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item @click="doPull(false)">
              <v-list-item-title>快进合并（--ff-only）</v-list-item-title>
              <v-list-item-subtitle class="text-caption">无法快进时直接失败，最安全</v-list-item-subtitle>
            </v-list-item>
            <v-list-item @click="doPull(true)">
              <v-list-item-title>变基（--rebase）</v-list-item-title>
              <v-list-item-subtitle class="text-caption">把本地提交接到远端之后</v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-menu>
        <v-btn
          size="small"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-arrow-up-bold"
          :disabled="!hasCurrent"
          :loading="busy === 'push'"
          @click="doPush"
        >
          推送<span v-if="current.ahead"> ({{ current.ahead }})</span>
        </v-btn>
        <v-menu>
          <template #activator="{ props: menuProps }">
            <v-btn size="small" variant="text" prepend-icon="mdi-dots-horizontal" v-bind="menuProps">
              更多
            </v-btn>
          </template>
          <v-list density="compact">
            <v-list-item
              title="全部 fetch"
              subtitle="所有仓库执行 git fetch，不改工作区"
              @click="fetchAll"
            />
            <v-list-item
              title="强制推送"
              subtitle="--force-with-lease"
              :disabled="!hasCurrent"
              @click="doForcePush"
            />
          </v-list>
        </v-menu>
        <v-btn
          size="small"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-source-repository"
          @click="cloneDialog = true"
        >
          克隆仓库
        </v-btn>
        <v-btn
          size="small"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-cog-outline"
          @click="settingsDialog = true"
        >
          设置
        </v-btn>
      </div>
    </v-card>

    <!-- 仓库详情 -->
    <v-card class="liquid-glass-card detail-panel" rounded="xl">
          <template v-if="!hasCurrent">
            <div class="empty-state">
              <v-icon size="56" color="primary" style="opacity: 0.35">mdi-source-repository</v-icon>
              <div class="text-body-2 mt-3">请在上方下拉框中选择一个仓库</div>
              <div class="text-caption mt-1" style="opacity: 0.7">
                扫描根目录：{{ roots.join('、') || '未配置' }}
              </div>
            </div>
          </template>

          <template v-else>
            <section class="main">
            <!-- Tabs -->
            <v-tabs v-model="activeTab" density="compact" color="primary">
              <v-tab value="changes">
                变更
                <v-badge
                  v-if="hasChanges"
                  dot
                  color="warning"
                  inline
                  class="ml-1"
                />
              </v-tab>
              <v-tab value="history">历史</v-tab>
              <v-tab value="branches">分支</v-tab>
              <v-tab value="files">
                文件
                <v-badge v-if="fileDirty" dot color="warning" inline class="ml-1" />
              </v-tab>
            </v-tabs>

            <div class="main-scroll">
              <v-alert
                v-if="!current.ok && current.error"
                type="error"
                variant="tonal"
                density="compact"
                class="ma-3"
              >
                {{ current.error }}
              </v-alert>

              <!-- 变更 -->
              <div v-show="activeTab === 'changes'">
                <div class="pa-3">
                  <div class="changes-grid">
                    <div class="changes-col">
                      <!-- 提交区：只占左边这一列，把宽度让给 diff -->
                      <div class="commit-box mb-3">
                        <v-textarea
                          v-model="commitMessage"
                          density="compact"
                          variant="outlined"
                          rows="2"
                          auto-grow
                          max-rows="5"
                          hide-details
                          placeholder="提交说明（第一行是标题）"
                        />
                        <div class="d-flex align-center flex-wrap ga-2 mt-2">
                          <v-switch
                            v-model="amend"
                            density="compact"
                            hide-details
                            label="修补"
                            color="warning"
                            class="flex-grow-0"
                          />
                          <v-chip size="small" variant="tonal">
                            已暂存 {{ status?.counts.staged || 0 }}
                          </v-chip>
                          <v-chip
                            v-if="status?.counts.unstaged"
                            size="small"
                            variant="tonal"
                            color="warning"
                          >
                            未暂存 {{ status.counts.unstaged }}
                          </v-chip>
                          <v-chip
                            v-if="status?.counts.untracked"
                            size="small"
                            variant="tonal"
                            color="success"
                          >
                            未跟踪 {{ status.counts.untracked }}
                          </v-chip>
                          <v-spacer />
                          <v-btn
                            color="primary"
                            variant="tonal"
                            size="small"
                            prepend-icon="mdi-check"
                            :disabled="!canCommit"
                            :loading="busy === 'commit'"
                            @click="doCommit"
                          >
                            提交
                          </v-btn>
                        </div>
                      </div>

                      <v-progress-linear v-if="statusLoading" indeterminate />

                      <!-- 冲突 -->
                      <template v-if="conflictFiles.length">
                        <div class="group-title error--text">
                          <v-icon size="14" color="error">mdi-alert-circle-outline</v-icon>
                          冲突 {{ conflictFiles.length }}
                        </div>
                        <div v-for="file in conflictFiles" :key="'c-' + file.path" class="file-row">
                          <v-icon size="16" color="error">mdi-file-alert-outline</v-icon>
                          <span class="file-name" @click="openDiff(file)">{{ file.path }}</span>
                          <v-btn size="x-small" variant="text" @click="resolveConflict(file, 'ours')">
                            用我的
                          </v-btn>
                          <v-btn size="x-small" variant="text" @click="resolveConflict(file, 'theirs')">
                            用远端
                          </v-btn>
                        </div>
                      </template>

                      <!-- 已暂存 -->
                      <div class="group-title">
                        <v-icon size="14">mdi-checkbox-marked-outline</v-icon>
                        已暂存 {{ stagedFiles.length }}
                        <v-spacer />
                        <v-btn
                          v-if="stagedFiles.length"
                          size="x-small"
                          variant="text"
                          @click="bulkAction('unstage', stagedFiles.map((f) => f.path))"
                        >
                          全部取消
                        </v-btn>
                      </div>
                      <div v-if="!stagedFiles.length" class="empty-hint">暂存区为空</div>
                      <div v-for="file in stagedFiles" :key="'s-' + file.path" class="file-row">
                        <v-icon size="16" :color="colorOf(file)">{{ iconOf(file) }}</v-icon>
                        <span class="file-name" :class="{ active: diffFile === file.path }" @click="openDiff(file)">
                          {{ file.path }}
                          <span class="file-label">{{ file.label }}</span>
                        </span>
                        <v-btn
                          icon="mdi-minus-box-outline"
                          variant="text"
                          size="x-small"
                          density="compact"
                          color="warning"
                          title="取消暂存"
                          @click.stop="fileAction(file, 'unstage')"
                        />
                      </div>

                      <!-- 未暂存 -->
                      <div class="group-title">
                        <v-icon size="14">mdi-file-edit-outline</v-icon>
                        未暂存 {{ unstagedFiles.length }}
                        <v-spacer />
                        <v-btn
                          v-if="unstagedFiles.length"
                          size="x-small"
                          variant="text"
                          @click="bulkAction('stage', unstagedFiles.map((f) => f.path))"
                        >
                          全部暂存
                        </v-btn>
                      </div>
                      <div v-if="!unstagedFiles.length" class="empty-hint">没有未暂存改动</div>
                      <div v-for="file in unstagedFiles" :key="'u-' + file.path" class="file-row">
                        <v-icon size="16" :color="colorOf(file)">{{ iconOf(file) }}</v-icon>
                        <span class="file-name" :class="{ active: diffFile === file.path }" @click="openDiff(file)">
                          {{ file.path }}
                          <span class="file-label">{{ file.label }}</span>
                        </span>
                        <v-btn
                          icon="mdi-plus-box-outline"
                          variant="text"
                          size="x-small"
                          density="compact"
                          color="success"
                          title="暂存"
                          @click.stop="fileAction(file, 'stage')"
                        />
                        <v-btn
                          icon="mdi-undo-variant"
                          variant="text"
                          size="x-small"
                          density="compact"
                          color="error"
                          title="丢弃改动"
                          @click.stop="fileAction(file, 'discard')"
                        />
                      </div>

                      <!-- 未跟踪 -->
                      <div class="group-title">
                        <v-icon size="14">mdi-plus-circle-outline</v-icon>
                        未跟踪 {{ untrackedFiles.length }}
                        <v-spacer />
                        <v-btn
                          v-if="untrackedFiles.length"
                          size="x-small"
                          variant="text"
                          @click="bulkAction('stage', untrackedFiles.map((f) => f.path))"
                        >
                          全部暂存
                        </v-btn>
                      </div>
                      <div v-if="!untrackedFiles.length" class="empty-hint">没有未跟踪文件</div>
                      <div v-for="file in untrackedFiles" :key="'n-' + file.path" class="file-row">
                        <v-icon size="16" color="success">{{ iconOf(file) }}</v-icon>
                        <span class="file-name" :class="{ active: diffFile === file.path }" @click="openDiff(file)">
                          {{ file.path }}
                        </span>
                        <v-btn
                          icon="mdi-plus-box-outline"
                          variant="text"
                          size="x-small"
                          density="compact"
                          color="success"
                          title="暂存"
                          @click.stop="fileAction(file, 'stage')"
                        />
                        <v-btn
                          icon="mdi-delete-outline"
                          variant="text"
                          size="x-small"
                          density="compact"
                          color="error"
                          title="删除文件"
                          @click.stop="fileAction(file, 'discard')"
                        />
                      </div>
                    </div>

                    <div class="diff-col">
                      <DiffViewer :diff="diffText" :loading="diffLoading" :file="diffFile" />
                    </div>
                  </div>
                </div>
              </div>

              <!-- 历史 -->
              <div v-show="activeTab === 'history'">
                <div class="pa-3">
                  <v-progress-linear v-if="logLoading" indeterminate />
                  <v-alert
                    v-else-if="!commits.length"
                    type="info"
                    variant="text"
                    density="compact"
                  >
                    还没有提交记录。
                  </v-alert>
                  <div v-for="commit in commits" :key="commit.hash" class="commit-row">
                    <v-chip size="x-small" variant="tonal" class="commit-hash">
                      {{ commit.short }}
                    </v-chip>
                    <div class="commit-main">
                      <div class="commit-subject">{{ commit.subject }}</div>
                      <div class="commit-meta">
                        {{ commit.author }} · {{ commit.date }}
                        <v-chip
                          v-for="ref in commit.refs"
                          :key="ref"
                          size="x-small"
                          variant="text"
                          color="primary"
                          class="ml-1"
                        >
                          {{ ref }}
                        </v-chip>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- 分支 -->
              <div v-show="activeTab === 'branches'">
                <div class="pa-3">
                  <div class="d-flex ga-2 mb-3">
                    <v-text-field
                      v-model="newBranchName"
                      density="compact"
                      variant="outlined"
                      label="新分支名"
                      hide-details
                      @keyup.enter="createBranch"
                    />
                    <v-btn
                      variant="tonal"
                      :disabled="!newBranchName.trim()"
                      :loading="busy === 'branch'"
                      @click="createBranch"
                    >
                      创建并切换
                    </v-btn>
                  </div>
                  <div
                    v-for="branch in branches"
                    :key="branch.name"
                    class="branch-row"
                    :class="{ current: branch.current }"
                  >
                    <v-icon size="16" :color="branch.current ? 'primary' : undefined">
                      {{ branch.current ? 'mdi-check-circle' : 'mdi-source-branch' }}
                    </v-icon>
                    <span class="branch-name">{{ branch.name }}</span>
                    <span v-if="branch.upstream" class="branch-upstream">{{ branch.upstream }}</span>
                    <v-spacer />
                    <v-btn
                      v-if="!branch.current"
                      size="x-small"
                      variant="text"
                      @click="switchBranch(branch.name)"
                    >
                      切换
                    </v-btn>
                  </div>
                </div>
              </div>

              <!-- 文件：树 + 内容，只有这个 TAB 才占宽度 -->
              <div v-show="activeTab === 'files'" class="files-pane">
                <div class="files-layout">
                  <div class="files-tree">
                    <div class="tree-head">
                      <v-icon size="14" color="primary">mdi-file-tree-outline</v-icon>
                      <span class="tree-title text-truncate" :title="current.path">
                        {{ current.name }}
                      </span>
                      <v-spacer />
                      <v-btn
                        icon="mdi-refresh"
                        variant="text"
                        size="x-small"
                        density="compact"
                        color="info"
                        title="刷新目录树"
                        @click="refreshTree"
                      />
                    </div>
                    <div class="tree-body">
                      <FileTree
                        ref="treeRef"
                        :repo-path="selected"
                        :selected="previewFile"
                        @select="onTreeSelect"
                      />
                    </div>
                  </div>
                  <FileViewer
                    ref="viewerRef"
                    class="files-viewer"
                    :repo-path="selected"
                    :file="previewFile"
                    @dirty-change="fileDirty = $event"
                  />
                </div>
              </div>
            </div>
            </section>
          </template>
    </v-card>

    <CloneDialog
      v-model="cloneDialog"
      :clone-dir="cloneDir"
      :identities="identityProfiles"
      @cloned="onCloned"
    />
    <RepoSettingsDialog v-model="settingsDialog" @saved="onSettingsSaved" />
    <IdentityDialog
      v-model="identityDialog"
      :path="selected"
      :repo-name="current.name"
      @updated="identityInfo = $event"
    />
  </v-container>
</template>

<style scoped>
.detail-panel {
  /* 整卡高度。宁可让页面轻微滚动，也要保证内容区够大 */
  --panel-h: clamp(640px, calc(100dvh - 260px), 3000px);
  overflow: hidden;
}
/* 主体：TAB + 内容，全宽 */
.main {
  display: flex;
  flex-direction: column;
  height: var(--panel-h);
  min-height: 0;
  min-width: 0;
  --content-h: calc(var(--panel-h) - 60px);
}
.main-scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.commit-box {
  padding: 8px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgba(var(--v-theme-surface-variant), 0.25);
}
.files-pane {
  height: var(--content-h);
  padding: 12px;
}
/* 文件页：树 + 内容，只在这个 TAB 里占宽度 */
.files-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 12px;
  height: 100%;
  min-height: 0;
}
.files-tree {
  display: flex;
  flex-direction: column;
  min-height: 0;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}
.tree-head {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px 2px 10px;
  flex-shrink: 0;
  font-size: 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: rgba(var(--v-theme-surface-variant), 0.4);
}
.tree-title {
  font-weight: 600;
  opacity: 0.8;
}
.tree-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
@media (max-width: 1100px) {
  .files-layout {
    grid-template-columns: 240px 1fr;
  }
}
@media (max-width: 900px) {
  .files-layout {
    grid-template-columns: 1fr;
    grid-template-rows: 40% 1fr;
  }
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 72px 16px;
}
.changes-grid {
  display: grid;
  /* 左列放提交框 + 文件组，尽量压窄，把宽度让给 diff */
  grid-template-columns: minmax(320px, 30%) 1fr;
  gap: 12px;
}
@media (max-width: 960px) {
  .changes-grid {
    grid-template-columns: 1fr;
  }
}
.changes-col {
  max-height: var(--content-h, 56vh);
  overflow: auto;
  padding-right: 4px;
}
.diff-col {
  min-width: 0;
}
.group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 4px 4px;
  opacity: 0.85;
}
.empty-hint {
  font-size: 12px;
  padding: 2px 4px 6px;
  opacity: 0.45;
}
.file-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 12.5px;
}
.file-row:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}
.file-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
  text-align: left;
}
.file-name.active {
  color: rgb(var(--v-theme-primary));
  font-weight: 600;
}
.file-label {
  font-size: 11px;
  opacity: 0.55;
  margin-left: 4px;
}
.commit-row {
  display: flex;
  gap: 10px;
  padding: 8px 4px;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.35);
}
.commit-hash {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  flex: 0 0 auto;
  height: 22px;
}
.commit-main {
  min-width: 0;
}
.commit-subject {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.commit-meta {
  font-size: 11px;
  opacity: 0.55;
  margin-top: 2px;
}
.branch-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
  border-radius: 4px;
  font-size: 13px;
}
.branch-row:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}
.branch-row.current {
  background: rgba(var(--v-theme-primary), 0.12);
}
.branch-name {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}
.branch-upstream {
  font-size: 11px;
  opacity: 0.55;
}
</style>
