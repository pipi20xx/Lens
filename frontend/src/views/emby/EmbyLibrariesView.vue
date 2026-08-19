<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { listEmbyLibraries, addEmbyLibrary, removeEmbyLibrary, updateEmbyLibrary } from '@/api/embyLibraries'
import { embyBackupApi } from '@/api/embyBackup'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import EmbyConfigBackupManager from '@/components/emby/EmbyConfigBackupManager.vue'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const libraries = ref<any[]>([])
const loading = ref(true)
const backingUpAll = ref(false)

// 新增媒体库弹窗
const showAddDialog = ref(false)
const addForm = reactive({ name: '', type: 'movies', path: '' })
const adding = ref(false)

const libraryTypeOptions = [
  { title: '电影 (movies)', value: 'movies' },
  { title: '电视剧 (tvshows)', value: 'tvshows' },
  { title: '音乐 (music)', value: 'music' },
  { title: '书籍 (books)', value: 'books' },
  { title: '家庭视频 (homevideos)', value: 'homevideos' },
  { title: '混合内容 (mixed)', value: 'mixed' },
]

// 编辑媒体库弹窗
const showEditDialog = ref(false)
const editingLib = ref<any>(null)
const localData = ref<any>({})
const jsonRaw = ref('')
const savingLib = ref(false)
const backingUp = ref(false)
const activeEditTab = ref('basic')

async function loadLibraries() {
  try {
    loading.value = true
    const res = await listEmbyLibraries()
    libraries.value = Array.isArray(res) ? res : []
  } catch {
    showError('加载媒体库列表失败')
  } finally {
    loading.value = false
  }
}

async function backupAll() {
  backingUpAll.value = true
  try {
    const res: any = await embyBackupApi.createAll('libraries')
    success(`成功备份 ${res?.count ?? ''} 个媒体库配置`)
  } catch { showError('备份失败') }
  finally { backingUpAll.value = false }
}

async function handleDirectBackup(lib: any) {
  try {
    await embyBackupApi.create('libraries', lib.Id, lib.Name)
    success(`媒体库 ${lib.Name} 备份成功`)
  } catch { showError('备份失败') }
}

async function removeLibrary(id: string, name: string) {
  const ok = await confirm({ title: '移除媒体库', content: `确定要移除媒体库 "${name}" 吗？此操作极高风险！`, confirmColor: 'error' })
  if (!ok) return
  try {
    await removeEmbyLibrary(name, id)
    success('媒体库已移除')
    loadLibraries()
  } catch { showError('移除失败') }
}

async function addLibrary() {
  if (!addForm.name.trim()) return
  adding.value = true
  try {
    await addEmbyLibrary(addForm.name.trim(), addForm.type, addForm.path)
    success('媒体库已添加')
    showAddDialog.value = false
    addForm.name = ''
    addForm.type = 'movies'
    addForm.path = ''
    loadLibraries()
  } catch { showError('添加失败') }
  finally { adding.value = false }
}

// 打开编辑弹窗
function openEdit(lib: any) {
  editingLib.value = lib
  localData.value = JSON.parse(JSON.stringify(lib))
  if (!localData.value.LibraryOptions) localData.value.LibraryOptions = {}
  if (!localData.value.LibraryOptions.PathInfos) localData.value.LibraryOptions.PathInfos = []
  if (!localData.value.LibraryOptions.TypeOptions) localData.value.LibraryOptions.TypeOptions = []
  jsonRaw.value = JSON.stringify(localData.value, null, 2)
  activeEditTab.value = 'basic'
  showEditDialog.value = true
}

// JSON 输入同步
function handleJsonInput(value: string) {
  try {
    const parsed = JSON.parse(value)
    localData.value = parsed
  } catch { /* ignore */ }
}

// 编辑弹窗内备份
async function handleBackup() {
  if (!editingLib.value) return
  backingUp.value = true
  try {
    await embyBackupApi.create('libraries', editingLib.value.Id, editingLib.value.Name)
    success('当前媒体库配置已备份')
  } catch { showError('备份失败') }
  finally { backingUp.value = false }
}

// 保存编辑
async function handleSaveLib() {
  try {
    const dataToSave = JSON.parse(jsonRaw.value)
    savingLib.value = true
    await updateEmbyLibrary(dataToSave)
    success('设置已保存')
    showEditDialog.value = false
    loadLibraries()
  } catch {
    showError('JSON 格式错误或保存失败')
  } finally {
    savingLib.value = false
  }
}

// 同步 localData -> jsonRaw
watch(localData, (newVal) => {
  const currentJson = JSON.stringify(newVal, null, 2)
  if (currentJson !== jsonRaw.value) {
    jsonRaw.value = currentJson
  }
}, { deep: true })

function getLibraryIcon(type: string) {
  const icons: Record<string, string> = { movies: 'mdi-filmstrip', tvshows: 'mdi-television-classic', music: 'mdi-music', books: 'mdi-book-open-variant', homevideos: 'mdi-video-vintage', mixed: 'mdi-folder-multiple' }
  return icons[type] || 'mdi-folder'
}

// === 元数据下载器 & 图片下载参数 ===
const METADATA_FETCHERS: Record<string, string[]> = {
  Movie: ['TheMovieDb', 'The Open Movie Database', 'TheTVDB'],
  Series: ['TheMovieDb', 'The Open Movie Database', 'TheTVDB'],
  Season: ['TheMovieDb', 'TheTVDB'],
  Episode: ['TheMovieDb', 'The Open Movie Database', 'TheTVDB'],
}

const IMAGE_FETCHERS: Record<string, string[]> = {
  Movie: ['TheMovieDb', 'TheTVDB', 'FanArt', 'The Open Movie Database', 'Image Capture'],
  Series: ['TheMovieDb', 'The Open Movie Database', 'FanArt', 'TheTVDB'],
  Season: ['TheMovieDb', 'FanArt', 'TheTVDB'],
  Episode: ['TheMovieDb', 'TheTVDB', 'The Open Movie Database', 'Image Capture'],
}

const IMAGE_OPTS_FILTER: Record<string, string[]> = {
  Movie: ['Primary', 'Art', 'Banner', 'Disc', 'Logo', 'Thumb', 'Backdrop'],
  Series: ['Primary', 'Art', 'Banner', 'Logo', 'Thumb', 'Backdrop'],
  Season: ['Primary', 'Banner', 'Thumb'],
  Episode: [],
}

const TYPE_LABELS: Record<string, string> = {
  Movie: '电影 (Movie)',
  Series: '剧集 (Series)',
  Season: '季 (Season)',
  Episode: '集 (Episode)',
}

const activeTypes = computed(() => {
  const contentType = localData.value?.LibraryOptions?.ContentType || localData.value?.CollectionType
  if (contentType === 'tvshows') return ['Series', 'Season', 'Episode']
  if (contentType === 'movies') return ['Movie']
  return ['Movie', 'Series', 'Season', 'Episode']
})

function getTypeOption(typeKey: string) {
  const options = localData.value?.LibraryOptions?.TypeOptions || []
  return options.find((o: any) => o.Type === typeKey) || { Type: typeKey, MetadataFetchers: [], ImageFetchers: [], ImageOptions: [] }
}

function getAvailableMetadataFetchers(typeKey: string) {
  return METADATA_FETCHERS[typeKey] || []
}

function getAvailableImageFetchers(typeKey: string) {
  return IMAGE_FETCHERS[typeKey] || []
}

function getAllowedImages(typeKey: string) {
  return IMAGE_OPTS_FILTER[typeKey] || []
}

function isImageEnabled(typeKey: string, imgType: string) {
  const typeOpt = getTypeOption(typeKey)
  const imgOpt = typeOpt.ImageOptions?.find((i: any) => i.Type === imgType)
  return imgOpt ? imgOpt.Limit > 0 : false
}

function getImageOptionValue(typeKey: string, imgType: string, field: 'Limit' | 'MinWidth') {
  const typeOpt = getTypeOption(typeKey)
  const imgOpt = typeOpt.ImageOptions?.find((i: any) => i.Type === imgType)
  if (imgOpt) return imgOpt[field]
  return field === 'Limit' ? 1 : 0
}

function toggleMetadataFetcher(typeKey: string, fetcher: string) {
  const typeOpt = getTypeOption(typeKey)
  const current: string[] = typeOpt.MetadataFetchers || []
  const idx = current.indexOf(fetcher)
  if (idx >= 0) current.splice(idx, 1)
  else current.push(fetcher)
  updateTypeOption(typeKey, 'MetadataFetchers', current)
}

function toggleImageFetcher(typeKey: string, fetcher: string) {
  const typeOpt = getTypeOption(typeKey)
  const current: string[] = typeOpt.ImageFetchers || []
  const idx = current.indexOf(fetcher)
  if (idx >= 0) current.splice(idx, 1)
  else current.push(fetcher)
  updateTypeOption(typeKey, 'ImageFetchers', current)
}

function handleImageToggle(typeKey: string, imgType: string, enabled: boolean) {
  updateImageOption(typeKey, imgType, 'Limit', enabled ? 1 : 0)
}

function updateTypeOption(typeKey: string, key: string, value: any) {
  const data = JSON.parse(JSON.stringify(localData.value))
  if (!data.LibraryOptions) data.LibraryOptions = {}
  if (!data.LibraryOptions.TypeOptions) data.LibraryOptions.TypeOptions = []
  let typeOpt = data.LibraryOptions.TypeOptions.find((o: any) => o.Type === typeKey)
  if (!typeOpt) {
    typeOpt = { Type: typeKey, MetadataFetchers: [], ImageFetchers: [], ImageOptions: [] }
    data.LibraryOptions.TypeOptions.push(typeOpt)
  }
  typeOpt[key] = value
  localData.value = data
}

function updateImageOption(typeKey: string, imgType: string, field: string, value: any) {
  const data = JSON.parse(JSON.stringify(localData.value))
  if (!data.LibraryOptions) data.LibraryOptions = {}
  if (!data.LibraryOptions.TypeOptions) data.LibraryOptions.TypeOptions = []
  let typeOpt = data.LibraryOptions.TypeOptions.find((o: any) => o.Type === typeKey)
  if (!typeOpt) {
    typeOpt = { Type: typeKey, MetadataFetchers: [], ImageFetchers: [], ImageOptions: [] }
    data.LibraryOptions.TypeOptions.push(typeOpt)
  }
  if (!typeOpt.ImageOptions) typeOpt.ImageOptions = []
  let imgOpt = typeOpt.ImageOptions.find((i: any) => i.Type === imgType)
  if (!imgOpt) {
    imgOpt = { Type: imgType, Limit: 0, MinWidth: 0 }
    typeOpt.ImageOptions.push(imgOpt)
  }
  imgOpt[field] = value
  localData.value = data
}

// === 本地元数据读取器 (NFO) ===
const localReaderOrder = computed(() => {
  const disabled = localData.value?.LibraryOptions?.DisabledLocalMetadataReaders || []
  const all = ['Nfo', 'Emby Xml']
  return all.filter(r => !disabled.includes(r))
})

function toggleLocalReader(reader: string) {
  const data = JSON.parse(JSON.stringify(localData.value))
  if (!data.LibraryOptions) data.LibraryOptions = {}
  const disabled: string[] = data.LibraryOptions.DisabledLocalMetadataReaders || []
  const order: string[] = data.LibraryOptions.LocalMetadataReaderOrder || []
  const idx = disabled.indexOf(reader)
  if (idx >= 0) {
    disabled.splice(idx, 1)
    if (!order.includes(reader)) order.push(reader)
  } else {
    disabled.push(reader)
    const oi = order.indexOf(reader)
    if (oi >= 0) order.splice(oi, 1)
  }
  data.LibraryOptions.DisabledLocalMetadataReaders = disabled
  data.LibraryOptions.LocalMetadataReaderOrder = order
  localData.value = data
}

// === 功能开关配置项 ===
const scanOptions = [
  { label: '启用实时监控 (EnableRealtimeMonitor)', key: 'EnableRealtimeMonitor' },
  { label: '提取章节图片 (EnableChapterImageExtraction)', key: 'EnableChapterImageExtraction' },
  { label: '库扫描期间提取章节图 (ExtractChapterImagesDuringLibraryScan)', key: 'ExtractChapterImagesDuringLibraryScan' },
  { label: '启用标记检测 (EnableMarkerDetection)', key: 'EnableMarkerDetection' },
  { label: '库扫描期间检测标记 (EnableMarkerDetectionDuringLibraryScan)', key: 'EnableMarkerDetectionDuringLibraryScan' },
  { label: '忽略隐藏文件和文件夹 (IgnoreHiddenFiles)', key: 'IgnoreHiddenFiles' },
  { label: '启用压缩媒体文件读取 (EnableArchiveMediaFiles)', key: 'EnableArchiveMediaFiles' },
]

const saveOptions = [
  { label: '将媒体元数据保存到媒体文件夹 (SaveLocalMetadata)', key: 'SaveLocalMetadata' },
  { label: '将元数据文件设为隐藏 (SaveMetadataHidden)', key: 'SaveMetadataHidden' },
  { label: '在本地保存缩略图集 (SaveLocalThumbnailSets)', key: 'SaveLocalThumbnailSets' },
  { label: '将歌词保存到媒体文件夹 (SaveLyricsWithMedia)', key: 'SaveLyricsWithMedia' },
  { label: '将字幕保存到媒体文件夹 (SaveSubtitlesWithMedia)', key: 'SaveSubtitlesWithMedia' },
  { label: '启用本地图片缓存 (CacheImages)', key: 'CacheImages' },
  { label: '提前下载图像 (DownloadImagesInAdvance)', key: 'DownloadImagesInAdvance' },
]

const otherOptions = [
  { label: '启用按文件多版本合并 (EnableMultiVersionByFiles)', key: 'EnableMultiVersionByFiles' },
  { label: '启用按元数据多版本合并 (EnableMultiVersionByMetadata)', key: 'EnableMultiVersionByMetadata' },
  { label: '允许刮削互联网元数据 (EnableInternetProviders)', key: 'EnableInternetProviders' },
  { label: '优先使用内嵌标题 (EnableEmbeddedTitles)', key: 'EnableEmbeddedTitles' },
  { label: '从搜索结果中排除此库 (ExcludeFromSearch)', key: 'ExcludeFromSearch' },
  { label: '启用照片支持 (EnablePhotos)', key: 'EnablePhotos' },
  { label: '启用 .plexignore 支持 (EnablePlexIgnore)', key: 'EnablePlexIgnore' },
]

const movieOptions = [
  { label: '自动导入电影合集 (ImportCollections)', key: 'ImportCollections' },
  { label: '启用多分段项目合并 (EnableMultiPartItems)', key: 'EnableMultiPartItems' },
  { label: '允许成人元数据 (EnableAdultMetadata)', key: 'EnableAdultMetadata' },
]

const seriesOptions = [
  { label: '自动将剧集分组 (EnableAutomaticSeriesGrouping)', key: 'EnableAutomaticSeriesGrouping' },
  { label: '合并顶级文件夹内容 (MergeTopLevelFolders)', key: 'MergeTopLevelFolders' },
  { label: '折叠单项目录 (CollapseSingleItemFolders)', key: 'CollapseSingleItemFolders' },
  { label: '强制折叠单项目录 (ForceCollapseSingleItemFolders)', key: 'ForceCollapseSingleItemFolders' },
]

const isMovie = computed(() => (localData.value?.CollectionType || localData.value?.LibraryOptions?.ContentType) === 'movies')
const isSeries = computed(() => (localData.value?.CollectionType || localData.value?.LibraryOptions?.ContentType) === 'tvshows')

function getLibOption(key: string) {
  return !!localData.value?.LibraryOptions?.[key]
}

function setLibOption(key: string, val: boolean) {
  const data = JSON.parse(JSON.stringify(localData.value))
  if (!data.LibraryOptions) data.LibraryOptions = {}
  data.LibraryOptions[key] = val
  localData.value = data
}

// === JSON 编辑器动态行数 ===
const jsonRows = computed(() => {
  const text = jsonRaw.value || ''
  if (!text) return 10
  const lines = text.split('\n').length
  return Math.max(10, Math.min(lines + 1, 30))
})

onMounted(loadLibraries)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-folder-multiple-outline</v-icon>
      Emby 媒体库管理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-4">管理您的 Emby 媒体库、路径配置及刮削策略。</p>

    <!-- 高危警告 -->
    <v-alert variant="tonal" type="error" density="compact" class="mb-4" rounded="lg">
      <strong>高危操作警告：</strong>本模块主要用于<strong>新服务器的媒体库极速初始化</strong>。通过直接推送 JSON 配置实现设置恢复。在生产环境服务器上进行删除、修改路径等操作具有极高风险，可能导致媒体库索引损坏或元数据丢失。<strong>非必要请勿操作，后果自负。</strong>
    </v-alert>

    <!-- 工具栏 -->
    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center flex-wrap pa-4">
        <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="loadLibraries" :loading="loading" class="mr-2">刷新媒体库列表</v-btn>
        <v-btn prepend-icon="mdi-backup-restore" variant="tonal" color="warning" size="small" @click="backupAll" :loading="backingUpAll" class="mr-2">一键备份所有媒体库</v-btn>
        <EmbyConfigBackupManager category="libraries" @restored="loadLibraries" />
        <v-spacer />
        <v-btn prepend-icon="mdi-plus" color="primary" variant="flat" size="small" @click="showAddDialog = true">新增媒体库</v-btn>
      </v-card-title>
      <v-divider />

      <v-card-text class="pa-4">
        <div v-if="loading" class="text-center py-8"><v-progress-circular indeterminate color="primary" /></div>
        <div v-else-if="!libraries.length" class="text-center py-8 text-medium-emphasis">
          <v-icon size="48" color="grey" class="mb-2">mdi-folder-off-outline</v-icon>
          <div>暂无媒体库数据</div>
        </div>
        <div v-else>
          <v-row>
            <v-col v-for="lib in libraries" :key="lib.ItemId || lib.Id" cols="12">
              <v-card variant="outlined" rounded="lg" class="pa-4">
                <div class="d-flex align-center flex-wrap">
                  <v-avatar :color="lib.CollectionType === 'movies' ? 'primary' : lib.CollectionType === 'tvshows' ? 'info' : 'accent'" variant="tonal" size="40" rounded="xl" class="mr-3">
                    <v-icon :icon="getLibraryIcon(lib.CollectionType || lib.Type)" size="20" />
                  </v-avatar>
                  <div class="flex-grow-1" style="min-width:200px">
                    <div class="text-subtitle-2 font-weight-bold">{{ lib.Name }}</div>
                    <div class="text-caption text-medium-emphasis font-mono">ID: {{ lib.Id }}</div>
                  </div>
                  <!-- 类型标签 -->
                  <v-chip size="x-small" variant="tonal" color="info" class="mr-3">{{ lib.CollectionType || lib.Type || '未知类型' }}</v-chip>
                  <!-- 路径信息 -->
                  <div class="flex-grow-1 mx-4" style="min-width:200px">
                    <div v-if="lib.LibraryOptions?.PathInfos?.length">
                      <div v-for="pi in lib.LibraryOptions.PathInfos.slice(0, 2)" :key="pi.Path" class="text-caption font-mono text-medium-emphasis text-truncate">{{ pi.Path }}</div>
                      <div v-if="lib.LibraryOptions.PathInfos.length > 2" class="text-caption text-medium-emphasis">+{{ lib.LibraryOptions.PathInfos.length - 2 }} 更多路径</div>
                    </div>
                    <div v-else-if="lib.PathInfo?.length">
                      <div v-for="pi in lib.PathInfo.slice(0, 2)" :key="pi.Path" class="text-caption font-mono text-medium-emphasis text-truncate">{{ pi.Path }}</div>
                      <div v-if="lib.PathInfo.length > 2" class="text-caption text-medium-emphasis">+{{ lib.PathInfo.length - 2 }} 更多路径</div>
                    </div>
                    <div v-else class="text-caption text-medium-emphasis">{{ lib.Path || '无路径' }}</div>
                  </div>
                  <!-- 操作 -->
                  <div class="d-flex flex-wrap ga-1">
                    <v-btn size="x-small" variant="tonal" color="info" prepend-icon="mdi-cog-outline" @click="openEdit(lib)">设置</v-btn>
                    <v-btn size="x-small" variant="tonal" color="warning" prepend-icon="mdi-backup-restore" @click="handleDirectBackup(lib)">备份</v-btn>
                    <v-btn size="x-small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" @click="removeLibrary(lib.Id, lib.Name)">移除</v-btn>
                  </div>
                </div>
              </v-card>
            </v-col>
          </v-row>
        </div>
      </v-card-text>
    </v-card>

    <!-- 新增媒体库弹窗 -->
    <GlassDialog v-model="showAddDialog" :max-width="550" icon="mdi-folder-plus-outline" title="新增媒体库">
      <v-text-field v-model="addForm.name" label="显示名称" variant="outlined" density="compact" class="mb-3" />
      <v-select v-model="addForm.type" :items="libraryTypeOptions" label="内容类型" variant="outlined" density="compact" class="mb-3" />
      <v-text-field v-model="addForm.path" label="文件夹路径" variant="outlined" density="compact" hint="服务器绝对路径" persistent-hint />
      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-plus" @click="addLibrary" :loading="adding">创建媒体库</v-btn>
      </template>
    </GlassDialog>

    <!-- 编辑媒体库弹窗 -->
    <GlassDialog v-model="showEditDialog" :max-width="1000" icon="mdi-folder-cog-outline" :title="'配置媒体库: ' + (editingLib?.Name)">
      <v-tabs v-model="activeEditTab" density="compact" color="primary" class="mb-4">
        <v-tab value="basic"><v-icon start>mdi-information-outline</v-icon> 基础信息</v-tab>
        <v-tab value="metadata"><v-icon start>mdi-database-search-outline</v-icon> 元数据下载器</v-tab>
        <v-tab value="images"><v-icon start>mdi-image-multiple-outline</v-icon> 图片下载与参数</v-tab>
        <v-tab value="features"><v-icon start>mdi-toggle-switch-outline</v-icon> 功能开关</v-tab>
        <v-tab value="json"><v-icon start>mdi-code-block-braces</v-icon> 原始数据</v-tab>
      </v-tabs>

      <v-window v-model="activeEditTab">
        <!-- 基础信息 -->
        <v-window-item value="basic">
          <v-text-field v-model="localData.Name" label="显示名称" variant="outlined" density="compact" class="mb-3" />
          <v-text-field :model-value="localData.CollectionType" label="内容类型" variant="outlined" density="compact" readonly class="mb-3" />

          <div class="text-subtitle-2 font-weight-bold mb-2">语言与国家</div>
          <v-text-field v-model="localData.LibraryOptions.PreferredMetadataLanguage" label="元数据语言 (PreferredMetadataLanguage)" variant="outlined" density="compact" placeholder="zh" class="mb-2" />
          <v-text-field v-model="localData.LibraryOptions.PreferredImageLanguage" label="图片语言 (PreferredImageLanguage)" variant="outlined" density="compact" placeholder="zh" class="mb-2" />
          <v-text-field v-model="localData.LibraryOptions.MetadataCountryCode" label="国家代码 (MetadataCountryCode)" variant="outlined" density="compact" placeholder="CN" class="mb-2" />

          <v-divider class="my-3" />
          <div class="text-subtitle-2 font-weight-bold mb-2">媒体路径</div>
          <div v-for="(pi, index) in localData.LibraryOptions.PathInfos" :key="index" class="d-flex ga-2 mb-2">
            <v-text-field v-model="localData.LibraryOptions.PathInfos[index].Path" :label="'路径 ' + (index + 1)" variant="outlined" density="compact" class="flex-grow-1" />
            <v-btn v-if="localData.LibraryOptions.PathInfos.length > 1" icon variant="text" size="small" color="error" @click="localData.LibraryOptions.PathInfos.splice(index, 1)">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>
          <v-btn size="small" variant="tonal" color="primary" @click="localData.LibraryOptions.PathInfos.push({ Path: '' })" prepend-icon="mdi-plus" class="mb-4">添加路径</v-btn>

          <v-divider class="my-3" />
          <div class="text-subtitle-2 font-weight-bold mb-2">刮削设置</div>
          <div class="text-caption text-medium-emphasis mb-2">本地元数据读取器 (NFO)</div>
          <v-checkbox
            v-for="reader in ['Nfo', 'Emby Xml']"
            :key="reader"
            :model-value="localReaderOrder.includes(reader)"
            :label="reader"
            density="compact"
            hide-details
            @update:model-value="toggleLocalReader(reader)"
          />
        </v-window-item>

        <!-- 元数据下载器 -->
        <v-window-item value="metadata">
          <v-alert variant="tonal" type="info" density="compact" class="mb-3" rounded="lg">
            请选择各媒体类型所使用的元数据刮削器。
          </v-alert>
          <v-expansion-panels variant="accordion" multiple>
            <v-expansion-panel v-for="typeKey in activeTypes" :key="typeKey">
              <v-expansion-panel-title>{{ TYPE_LABELS[typeKey] || typeKey }}</v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="text-caption text-medium-emphasis mb-2">元数据下载器 (MetadataFetchers)</div>
                <v-checkbox
                  v-for="fetcher in getAvailableMetadataFetchers(typeKey)"
                  :key="fetcher"
                  :model-value="getTypeOption(typeKey).MetadataFetchers?.includes(fetcher)"
                  :label="fetcher"
                  density="compact"
                  hide-details
                  @update:model-value="toggleMetadataFetcher(typeKey, fetcher)"
                />
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-window-item>

        <!-- 图片下载与参数 -->
        <v-window-item value="images">
          <v-alert variant="tonal" type="info" density="compact" class="mb-3" rounded="lg">
            配置各媒体类型所使用的图片下载器及图片参数。开启开关后可设置下载数量与最小宽度。
          </v-alert>
          <v-expansion-panels variant="accordion" multiple>
            <v-expansion-panel v-for="typeKey in activeTypes" :key="typeKey">
              <v-expansion-panel-title>{{ TYPE_LABELS[typeKey] || typeKey }}</v-expansion-panel-title>
              <v-expansion-panel-text>
                <div class="text-caption text-medium-emphasis mb-2">图片下载器 (ImageFetchers)</div>
                <v-checkbox
                  v-for="fetcher in getAvailableImageFetchers(typeKey)"
                  :key="fetcher"
                  :model-value="getTypeOption(typeKey).ImageFetchers?.includes(fetcher)"
                  :label="fetcher"
                  density="compact"
                  hide-details
                  class="mb-1"
                  @update:model-value="toggleImageFetcher(typeKey, fetcher)"
                />

                <template v-if="getAllowedImages(typeKey).length">
                  <v-divider class="my-3" />
                  <div class="text-caption font-weight-bold mb-2">图片参数配置 (ImageOptions)</div>
                  <v-card v-for="imgType in getAllowedImages(typeKey)" :key="imgType" variant="outlined" rounded="lg" class="mb-2 pa-3">
                    <div class="d-flex align-center justify-space-between flex-wrap ga-2">
                      <div class="d-flex align-center ga-2">
                        <v-switch
                          :model-value="isImageEnabled(typeKey, imgType)"
                          density="compact"
                          hide-details
                          color="primary"
                          @update:model-value="handleImageToggle(typeKey, imgType, $event)"
                        />
                        <span class="text-body-2 font-weight-medium">{{ imgType }}</span>
                      </div>
                      <div v-if="isImageEnabled(typeKey, imgType)" class="d-flex align-center ga-3">
                        <v-text-field
                          :model-value="getImageOptionValue(typeKey, imgType, 'Limit')"
                          label="数量"
                          type="number"
                          variant="outlined"
                          density="compact"
                          hide-details
                          style="max-width:90px"
                          @update:model-value="updateImageOption(typeKey, imgType, 'Limit', Number($event))"
                        />
                        <v-text-field
                          :model-value="getImageOptionValue(typeKey, imgType, 'MinWidth')"
                          label="最小宽度"
                          type="number"
                          variant="outlined"
                          density="compact"
                          hide-details
                          style="max-width:110px"
                          @update:model-value="updateImageOption(typeKey, imgType, 'MinWidth', Number($event))"
                        />
                      </div>
                    </div>
                  </v-card>
                </template>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-window-item>

        <!-- 功能开关 -->
        <v-window-item value="features">
          <div class="text-subtitle-2 font-weight-bold mb-2">核心扫描与监控</div>
          <v-row>
            <v-col v-for="opt in scanOptions" :key="opt.key" cols="12" sm="6">
              <v-switch :model-value="getLibOption(opt.key)" @update:model-value="setLibOption(opt.key, $event)" :label="opt.label" density="compact" hide-details color="primary" />
            </v-col>
          </v-row>

          <v-divider class="my-3" />
          <div class="text-subtitle-2 font-weight-bold mb-2">元数据与保存设置</div>
          <v-row>
            <v-col v-for="opt in saveOptions" :key="opt.key" cols="12" sm="6">
              <v-switch :model-value="getLibOption(opt.key)" @update:model-value="setLibOption(opt.key, $event)" :label="opt.label" density="compact" hide-details color="primary" />
            </v-col>
          </v-row>

          <v-divider class="my-3" />
          <div class="text-subtitle-2 font-weight-bold mb-2">高级播放与刮削控制</div>
          <v-row>
            <v-col v-for="opt in otherOptions" :key="opt.key" cols="12" sm="6">
              <v-switch :model-value="getLibOption(opt.key)" @update:model-value="setLibOption(opt.key, $event)" :label="opt.label" density="compact" hide-details color="primary" />
            </v-col>
          </v-row>

          <template v-if="isMovie">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 font-weight-bold mb-2">电影库专属选项</div>
            <v-row>
              <v-col v-for="opt in movieOptions" :key="opt.key" cols="12" sm="6">
                <v-switch :model-value="getLibOption(opt.key)" @update:model-value="setLibOption(opt.key, $event)" :label="opt.label" density="compact" hide-details color="primary" />
              </v-col>
            </v-row>
          </template>

          <template v-if="isSeries">
            <v-divider class="my-3" />
            <div class="text-subtitle-2 font-weight-bold mb-2">电视节目库专属选项</div>
            <v-row>
              <v-col v-for="opt in seriesOptions" :key="opt.key" cols="12" sm="6">
                <v-switch :model-value="getLibOption(opt.key)" @update:model-value="setLibOption(opt.key, $event)" :label="opt.label" density="compact" hide-details color="primary" />
              </v-col>
            </v-row>
          </template>
        </v-window-item>

        <!-- 原始数据 (JSON) -->
        <v-window-item value="json">
          <v-alert variant="tonal" type="info" density="compact" class="mb-3" rounded="lg">
            高级操作：您可以直接编辑下方的原始 JSON 数据进行高级配置。
          </v-alert>
          <v-textarea v-model="jsonRaw" variant="outlined" :rows="jsonRows" class="yaml-editor" @update:model-value="handleJsonInput" />
        </v-window-item>
      </v-window>

      <template #actions>
        <v-btn variant="tonal" color="warning" prepend-icon="mdi-backup-restore" @click="handleBackup" :loading="backingUp">备份当前配置</v-btn>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="handleSaveLib" :loading="savingLib">保存设置</v-btn>
      </template>
    </GlassDialog>
  </v-container>
</template>
