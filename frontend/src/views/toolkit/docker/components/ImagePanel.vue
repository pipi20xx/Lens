<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification, useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError, info, warning } = useNotification()
const { confirm } = useConfirm()

const props = defineProps<{
  active: boolean
  hostId: string | null
}>()

// ========== 自动加载 ==========
const loaded = ref(false)
watch([() => props.active, () => props.hostId], ([active, hostId]) => {
  if (active && hostId) { loadImages(); loaded.value = true }
})
onMounted(() => { if (props.active && props.hostId) { loadImages(); loaded.value = true } })

// ========== 镜像列表 ==========
interface DockerImage {
  id: string
  full_id: string
  tags: string[]
  repo_tag: string
  size: string
  created: string
  in_use: boolean
  used_by: string[]
  dangling: boolean
}

const images = ref<DockerImage[]>([])
const searchQuery = ref('')
const loading = ref(false)
const loadingActions = ref<Record<string, boolean>>({})

const imgKey = (img: DockerImage) => img.full_id || img.id
const shortId = (id: string) => (id || '').replace('sha256:', '').slice(0, 12)

const filteredImages = computed(() => {
  if (!searchQuery.value) return images.value
  const q = searchQuery.value.toLowerCase()
  return images.value.filter((img) =>
    img.repo_tag?.toLowerCase().includes(q) ||
    shortId(img.full_id || img.id).includes(q) ||
    img.used_by?.some((n: string) => n.toLowerCase().includes(q))
  )
})

async function loadImages() {
  if (!props.hostId) return
  try {
    loading.value = true
    const data = await dockerApi.getImages(props.hostId)
    images.value = Array.isArray(data) ? data : []
  } catch { showError('加载镜像列表失败') }
  finally { loading.value = false }
}

// ========== 删除 ==========
async function handleRemove(img: DockerImage) {
  const content = img.in_use
    ? `镜像 "${img.repo_tag}" 正在被容器使用（${img.used_by.join('、')}）。强制删除可能导致相关容器无法重建，确定继续吗？`
    : `确定要删除镜像 "${img.repo_tag}" 吗？此操作不可撤销。`
  const ok = await confirm({ title: '确认删除镜像', content, confirmColor: 'error' })
  if (!ok) return
  const key = imgKey(img)
  loadingActions.value[key] = true
  try {
    await dockerApi.removeImage(props.hostId!, key, img.in_use)
    success(`镜像 ${img.repo_tag} 已删除`)
    loadImages()
  } catch (err: any) { showError(err.message || '删除失败') }
  finally { loadingActions.value[key] = false }
}

// ========== 清理 ==========
async function handlePrune(allUnused: boolean) {
  if (!props.hostId) return
  const ok = await confirm({
    title: allUnused ? '确认清理未使用镜像' : '确认清理悬空镜像',
    content: allUnused
      ? '将删除所有未被任何容器使用的镜像（docker image prune -a -f），此操作不可撤销。'
      : '将删除所有悬空镜像，即无标签的中间层镜像（docker image prune -f）。',
    confirmColor: 'warning',
  })
  if (!ok) return
  loadingActions.value['__prune'] = true
  try {
    const res: any = await dockerApi.pruneImages(props.hostId, true, allUnused)
    info(res?.message || '清理任务已启动，完成后将通过系统通知告知')
    setTimeout(() => loadImages(), 5000)
  } catch { showError('清理失败') }
  finally { loadingActions.value['__prune'] = false }
}

// ========== 导出镜像 ==========
async function handleExport(img: DockerImage) {
  if (!props.hostId) return
  const key = imgKey(img)
  loadingActions.value[key] = true
  try {
    const base = img.dangling ? shortId(key) : img.repo_tag.replace(/\//g, '_').replace(/:/g, '_')
    await dockerApi.exportImage(props.hostId, key, `${base}.tar`)
    success(`镜像 ${img.repo_tag} 导出完成`)
  } catch (err: any) { showError(err.message || '导出失败') }
  finally { loadingActions.value[key] = false }
}

// ========== 导入镜像 ==========
const showLoadDialog = ref(false)
const loadFile = ref<File | null>(null)
const loadSubmitting = ref(false)
const loadResult = ref<string[]>([])
const loadError = ref('')

function openLoadDialog() {
  loadFile.value = null
  loadResult.value = []
  loadError.value = ''
  showLoadDialog.value = true
}

async function submitLoad() {
  if (!props.hostId) return
  if (!loadFile.value) { warning('请选择镜像 tar 文件'); return }
  loadSubmitting.value = true
  loadError.value = ''
  try {
    const res: any = await dockerApi.loadImage(props.hostId, loadFile.value)
    loadResult.value = (res?.result || [])
      .map((r: any) => (typeof r === 'string' ? r : r.stream || JSON.stringify(r)))
      .filter(Boolean)
    success(res?.message || '镜像导入完成')
    loadImages()
  } catch (err: any) { loadError.value = err.message || '导入失败' }
  finally { loadSubmitting.value = false }
}

// ========== 打标签 ==========
const showTagDialog = ref(false)
const tagForm = ref({ key: '', name: '', repo: '', tag: 'latest' })

function openTagDialog(img: DockerImage) {
  const repo = img.repo_tag.includes(':') ? img.repo_tag.split(':')[0] : img.repo_tag
  tagForm.value = { key: imgKey(img), name: img.repo_tag, repo: repo === '<none>' ? '' : repo, tag: 'latest' }
  showTagDialog.value = true
}

async function saveTag() {
  if (!props.hostId) return
  const repo = tagForm.value.repo.trim()
  if (!repo) { warning('请输入仓库名称'); return }
  loadingActions.value[tagForm.value.key] = true
  try {
    const tag = tagForm.value.tag.trim() || 'latest'
    await dockerApi.tagImage(props.hostId, tagForm.value.key, repo, tag)
    success(`已为 ${tagForm.value.name} 打标签 ${repo}:${tag}`)
    showTagDialog.value = false
    loadImages()
  } catch (err: any) { showError(err.message || '打标签失败') }
  finally { loadingActions.value[tagForm.value.key] = false }
}

// ========== 详情 ==========
const showDetailDialog = ref(false)
const detailName = ref('')
const detailContent = ref('')
const loadingDetail = ref(false)

async function showDetail(img: DockerImage) {
  if (!props.hostId) return
  detailName.value = img.repo_tag
  detailContent.value = ''
  showDetailDialog.value = true
  loadingDetail.value = true
  try {
    const data = await dockerApi.getImageDetail(props.hostId, imgKey(img))
    detailContent.value = JSON.stringify(data, null, 2)
  } catch (err: any) { detailContent.value = err.message || '加载详情失败' }
  finally { loadingDetail.value = false }
}

// ========== 拉取镜像 ==========
const showPullDialog = ref(false)
const pullImageRef = ref('')
const pullSubmitting = ref(false)
const pullTask = ref<any>(null)
let pullTimer: ReturnType<typeof setInterval> | null = null

function openPullDialog() {
  pullImageRef.value = ''
  pullTask.value = null
  showPullDialog.value = true
}

async function startPull() {
  if (!props.hostId) return
  const imageRef = pullImageRef.value.trim()
  if (!imageRef) { warning('请输入镜像名称，例如 nginx:latest'); return }
  pullSubmitting.value = true
  try {
    const res: any = await dockerApi.pullImage(props.hostId, imageRef)
    pullTask.value = { task_id: res.task_id, image: imageRef, status: 'pending', lines: [], layers: {}, done: false, success: false, error: null }
    startPullPolling()
  } catch (err: any) { showError(err.message || '启动拉取失败') }
  finally { pullSubmitting.value = false }
}

function startPullPolling() {
  stopPullPolling()
  pullTimer = setInterval(pollPullProgress, 1000)
  pollPullProgress()
}

async function pollPullProgress() {
  const task = pullTask.value
  if (!task || !props.hostId) return
  try {
    const data: any = await dockerApi.getPullProgress(props.hostId, task.task_id)
    pullTask.value = { ...task, ...data }
    if (data.done) {
      stopPullPolling()
      if (data.success) {
        success(`镜像 ${data.image} 拉取成功`)
        loadImages()
      } else {
        showError(`镜像 ${data.image} 拉取失败：${data.error || '未知错误'}`)
      }
    }
  } catch { /* 单次轮询失败忽略，等待下一轮 */ }
}

function stopPullPolling() {
  if (pullTimer) { clearInterval(pullTimer); pullTimer = null }
}

onUnmounted(() => stopPullPolling())

const pullLines = computed(() => (pullTask.value?.lines || []).slice(-12))
const pullLayerList = computed(() =>
  Object.entries(pullTask.value?.layers || {}).map(([id, l]: [string, any]) => ({ id, ...l }))
)

defineExpose({ loadImages })
</script>

<template>
  <div>
    <div class="control-row mb-4">
      <v-text-field v-model="searchQuery" prepend-inner-icon="mdi-magnify" placeholder="搜索镜像名、ID 或容器..." variant="outlined" density="compact" hide-details clearable class="flex-grow-0" style="max-width:360px" />
      <v-spacer />
      <v-menu>
        <template #activator="{ props: menuProps }">
          <v-btn v-bind="menuProps" prepend-icon="mdi-delete-sweep" variant="tonal" size="small" color="warning" :loading="!!loadingActions['__prune']">清理镜像</v-btn>
        </template>
        <v-list>
          <v-list-item prepend-icon="mdi-eraser" title="清理悬空镜像" subtitle="删除无标签的中间层镜像" @click="handlePrune(false)" />
          <v-list-item prepend-icon="mdi-delete-empty-outline" title="清理未使用镜像" subtitle="删除所有未被容器使用的镜像" @click="handlePrune(true)" />
        </v-list>
      </v-menu>
      <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" color="info" @click="loadImages" :loading="loading">刷新</v-btn>
      <v-btn prepend-icon="mdi-download" variant="tonal" size="small" color="primary" @click="openPullDialog">拉取镜像</v-btn>
      <v-btn prepend-icon="mdi-upload" variant="tonal" size="small" color="primary" @click="openLoadDialog">导入镜像</v-btn>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-row v-if="!loading && filteredImages.length === 0">
      <v-col cols="12" class="text-center py-12 text-medium-emphasis">
        <v-icon size="64" color="grey" class="mb-4">mdi-layers-triple-outline</v-icon>
        <div>暂无镜像</div>
      </v-col>
    </v-row>

    <div v-if="filteredImages.length" class="task-list">
      <v-card
        v-for="img in filteredImages"
        :key="imgKey(img)"
        class="status-card liquid-glass-card"
        rounded="lg"
      >
        <!-- 卡片头部 -->
        <div class="card-header pa-4 pb-2">
          <div class="card-title">
            <v-icon start color="primary" size="20">mdi-layers-triple-outline</v-icon>
            <span class="font-mono text-subtitle-2 font-weight-bold text-truncate">{{ img.repo_tag }}</span>
          </div>
          <div class="d-flex ga-2">
            <v-chip v-if="img.dangling" size="small" color="warning" variant="tonal" label>悬空</v-chip>
            <v-chip v-if="img.in_use" size="small" color="success" variant="tonal" label>使用中</v-chip>
            <v-chip v-else size="small" color="grey" variant="tonal" label>未使用</v-chip>
          </div>
        </div>

        <!-- 信息行 -->
        <div class="card-info px-4 pb-2">
          <div class="info-item">
            <span class="info-label">镜像ID</span>
            <span class="font-mono text-caption text-medium-emphasis">{{ shortId(img.full_id || img.id) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">大小</span>
            <span class="text-caption">{{ img.size || '--' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">创建</span>
            <span class="text-caption">{{ img.created || '--' }}</span>
          </div>
          <div v-if="img.used_by?.length" class="info-item">
            <span class="info-label">使用容器</span>
            <v-chip v-for="name in img.used_by" :key="name" size="x-small" variant="tonal" color="primary">{{ name }}</v-chip>
          </div>
        </div>

        <!-- 操作按钮 -->
        <v-divider class="mt-2" />
        <div class="d-flex flex-wrap ga-2 pa-3">
          <v-btn size="small" color="info" variant="tonal" @click="showDetail(img)"><v-icon start>mdi-information-outline</v-icon> 详情</v-btn>
          <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-tag-outline" @click="openTagDialog(img)">打标签</v-btn>
          <v-btn size="small" color="success" variant="tonal" prepend-icon="mdi-export" :loading="!!loadingActions[imgKey(img)]" @click="handleExport(img)">导出</v-btn>
          <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" :loading="!!loadingActions[imgKey(img)]" @click="handleRemove(img)">删除</v-btn>
        </div>
      </v-card>
    </div>

    <!-- 拉取镜像对话框 -->
    <GlassDialog v-model="showPullDialog" :max-width="560" icon="mdi-download" title="拉取镜像" :cancel-text="pullTask ? '关闭' : '取消'">
      <template v-if="!pullTask">
        <v-text-field v-model="pullImageRef" label="镜像名称" placeholder="例如 nginx:latest、ghcr.io/xxx/app:v1" variant="outlined" density="compact" prepend-inner-icon="mdi-docker" hide-details class="mb-2" @keyup.enter="startPull" />
        <div class="text-caption text-medium-emphasis">将在后台拉取镜像，可随时关闭本窗口，完成后会通过系统通知告知。</div>
      </template>
      <template v-else>
        <div class="d-flex align-center ga-2 mb-3">
          <span class="font-mono text-body-2 text-truncate">{{ pullTask.image }}</span>
          <v-spacer />
          <v-chip :color="pullTask.success ? 'success' : pullTask.done ? 'error' : 'info'" size="small" variant="tonal" label>
            {{ pullTask.status === 'pending' ? '等待中' : pullTask.status === 'running' ? '拉取中' : pullTask.success ? '成功' : '失败' }}
          </v-chip>
        </div>
        <v-progress-linear v-if="!pullTask.done" indeterminate color="primary" class="mb-3" />
        <template v-if="pullLayerList.length && !pullTask.done">
          <div v-for="layer in pullLayerList" :key="layer.id" class="d-flex justify-space-between text-caption text-medium-emphasis font-mono mb-1">
            <span>{{ layer.id }} {{ layer.status }}</span>
            <span>{{ layer.progress }}</span>
          </div>
        </template>
        <v-alert v-if="pullTask.done && pullTask.error" type="error" variant="tonal" density="compact" class="mb-3">{{ pullTask.error }}</v-alert>
        <pre v-if="pullLines.length" class="code-block code-block--flat">{{ pullLines.join('\n') }}</pre>
      </template>
      <template #actions>
        <v-btn v-if="!pullTask" color="primary" variant="flat" prepend-icon="mdi-download" :loading="pullSubmitting" :disabled="!pullImageRef.trim()" @click="startPull">开始拉取</v-btn>
        <v-btn v-else-if="pullTask.done" color="primary" variant="tonal" prepend-icon="mdi-plus" @click="pullTask = null; pullImageRef = ''">继续拉取</v-btn>
      </template>
    </GlassDialog>

    <!-- 导入镜像对话框 -->
    <GlassDialog v-model="showLoadDialog" :max-width="560" icon="mdi-upload" title="导入镜像" cancel-text="取消">
      <v-file-input
        v-model="loadFile"
        label="镜像 tar 文件"
        placeholder="选择 docker save 导出的镜像文件"
        prepend-inner-icon="mdi-file-outline"
        prepend-icon=""
        variant="outlined"
        density="compact"
        accept=".tar,.tar.gz,.tgz"
        show-size
        :disabled="loadSubmitting"
        class="mb-2"
      />
      <div class="text-caption text-medium-emphasis mb-3">将文件通过 docker load 导入当前主机，镜像名称以 tar 包内为准，大文件上传与导入可能需要一些时间。</div>
      <template v-if="loadSubmitting">
        <v-progress-linear indeterminate color="primary" class="mb-3" />
        <div class="text-caption text-medium-emphasis text-center">正在上传并导入，请耐心等待...</div>
      </template>
      <v-alert v-if="loadError" type="error" variant="tonal" density="compact" class="mb-3">{{ loadError }}</v-alert>
      <template v-if="loadResult.length">
        <v-divider class="mb-3" />
        <div class="text-subtitle-2 mb-2">导入结果</div>
        <pre class="code-block code-block--flat">{{ loadResult.join('\n') }}</pre>
      </template>
      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-upload" :loading="loadSubmitting" :disabled="!loadFile" @click="submitLoad">开始导入</v-btn>
      </template>
    </GlassDialog>

    <!-- 打标签对话框 -->
    <GlassDialog v-model="showTagDialog" :max-width="440" icon="mdi-tag-outline" :title="'打标签 — ' + tagForm.name">
      <v-text-field v-model="tagForm.repo" label="仓库名称" placeholder="例如 myrepo/myapp" variant="outlined" density="compact" class="mb-3" />
      <v-text-field v-model="tagForm.tag" label="标签" placeholder="latest" variant="outlined" density="compact" hide-details />
      <div class="text-caption text-medium-emphasis mt-3">等效命令：docker tag {{ shortId(tagForm.key) }} {{ tagForm.repo || '?' }}:{{ tagForm.tag || 'latest' }}</div>
      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-tag-outline" @click="saveTag">确认打标签</v-btn>
      </template>
    </GlassDialog>

    <!-- 详情对话框 -->
    <GlassDialog v-model="showDetailDialog" :max-width="900" icon="mdi-information-outline" :title="'详情 — ' + detailName" cancel-text="关闭">
      <v-progress-linear v-if="loadingDetail" indeterminate color="primary" />
      <pre class="code-block code-block--flat">{{ detailContent }}</pre>
    </GlassDialog>
  </div>
</template>
