<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { listEmbyLibraries, addEmbyLibrary, removeEmbyLibrary, updateEmbyLibrary } from '@/api/embyLibraries'
import { embyBackupApi } from '@/api/embyBackup'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import EmbyConfigBackupManager from '@/components/emby/EmbyConfigBackupManager.vue'

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
    <v-dialog v-model="showAddDialog" max-width="550">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-folder-plus-outline</v-icon>
          新增媒体库
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-text-field v-model="addForm.name" label="显示名称" variant="outlined" density="compact" class="mb-3" />
          <v-select v-model="addForm.type" :items="libraryTypeOptions" label="内容类型" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="addForm.path" label="文件夹路径" variant="outlined" density="compact" hint="服务器绝对路径" persistent-hint />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showAddDialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-plus" @click="addLibrary" :loading="adding">创建媒体库</v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- 编辑媒体库弹窗 -->
    <v-dialog v-model="showEditDialog" max-width="1000" scrollable>
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-folder-cog-outline</v-icon>
          配置媒体库: {{ editingLib?.Name }}
        </v-card-title>
        <v-divider />

        <v-tabs v-model="activeEditTab" class="px-4">
          <v-tab value="basic">基础信息</v-tab>
          <v-tab value="features">功能开关</v-tab>
          <v-tab value="json">原始数据 (JSON)</v-tab>
        </v-tabs>
        <v-divider />

        <v-card-text class="pa-4" style="max-height: 60vh; overflow-y: auto;">
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
              <v-btn size="small" variant="tonal" color="primary" @click="localData.LibraryOptions.PathInfos.push({ Path: '' })" prepend-icon="mdi-plus">添加路径</v-btn>
            </v-window-item>

            <!-- 功能开关 -->
            <v-window-item value="features">
              <div class="text-subtitle-2 font-weight-bold mb-2">通用功能</div>
              <v-switch v-model="localData.LibraryOptions.EnableArchiveMediaFiles" label="启用存档媒体文件浏览 (EnableArchiveMediaFiles)" density="compact" class="mb-2" />
              <v-switch v-model="localData.LibraryOptions.EnablePhotos" label="启用照片浏览 (EnablePhotos)" density="compact" class="mb-2" />
              <v-switch v-model="localData.LibraryOptions.EnableRealtimeMonitor" label="启用实时监控 (EnableRealtimeMonitor)" density="compact" class="mb-2" />
              <v-switch v-model="localData.LibraryOptions.EnableLUFSScan" label="启用 LUF 扫描 (EnableLUFSScan)" density="compact" class="mb-2" />

              <v-divider class="my-3" />
              <div v-if="localData.CollectionType === 'movies'" class="text-subtitle-2 font-weight-bold mb-2">电影专属</div>
              <template v-if="localData.CollectionType === 'movies'">
                <v-switch v-model="localData.LibraryOptions.EnableChapterImageExtraction" label="启用章节图片提取 (EnableChapterImageExtraction)" density="compact" class="mb-2" />
                <v-switch v-model="localData.LibraryOptions.ExtractDuringLibraryScan" label="在媒体库扫描时提取 (ExtractDuringLibraryScan)" density="compact" class="mb-2" />
              </template>

              <div v-if="localData.CollectionType === 'tvshows'" class="text-subtitle-2 font-weight-bold mb-2">电视节目专属</div>
              <template v-if="localData.CollectionType === 'tvshows'">
                <v-switch v-model="localData.LibraryOptions.EnableChapterImageExtraction" label="启用章节图片提取 (EnableChapterImageExtraction)" density="compact" class="mb-2" />
                <v-switch v-model="localData.LibraryOptions.ExtractDuringLibraryScan" label="在媒体库扫描时提取 (ExtractDuringLibraryScan)" density="compact" class="mb-2" />
                <v-switch v-model="localData.LibraryOptions.EnableAutomaticSeriesGrouping" label="启用自动系列分组 (EnableAutomaticSeriesGrouping)" density="compact" class="mb-2" />
              </template>
            </v-window-item>

            <!-- 原始数据 (JSON) -->
            <v-window-item value="json">
              <v-alert variant="tonal" type="info" density="compact" class="mb-3" rounded="lg">
                高级操作：您可以直接编辑下方的原始 JSON 数据进行高级配置。
              </v-alert>
              <v-textarea v-model="jsonRaw" variant="outlined" rows="18" style="font-family: monospace" @update:model-value="handleJsonInput" />
            </v-window-item>
          </v-window>
        </v-card-text>

        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showEditDialog = false">取消</v-btn>
          <v-btn variant="tonal" color="warning" prepend-icon="mdi-backup-restore" @click="handleBackup" :loading="backingUp">备份当前配置</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="handleSaveLib" :loading="savingLib">保存设置</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>
