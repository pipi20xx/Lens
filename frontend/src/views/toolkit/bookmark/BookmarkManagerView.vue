<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { bookmarksApi } from '@/api/bookmarks'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError, warning } = useNotification()
const { confirm } = useConfirm()

// ========== 数据层 ==========
interface Bookmark {
  id: string
  title: string
  type: 'file' | 'folder'
  url?: string
  icon?: string
  parent_id?: string
  order: number
  children?: Bookmark[]
}

const bookmarks = ref<Bookmark[]>([])
const loading = ref(false)
const searchQuery = ref('')

async function loadBookmarks() {
  try {
    loading.value = true
    const data = await bookmarksApi.getBookmarks(true)
    bookmarks.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载书签失败')
  } finally {
    loading.value = false
  }
}

// ========== 导航层 ==========
const currentFolder = ref<Bookmark | null>(null)
const selectedFolderId = ref<string | null>(null)

const currentItems = computed(() => {
  const rawData = Array.isArray(bookmarks.value) ? bookmarks.value : []
  if (searchQuery.value.trim()) return searchBookmarks(rawData, searchQuery.value.trim())
  if (currentFolder.value) return currentFolder.value.children || []
  return rawData
})

function searchBookmarks(items: Bookmark[], query: string): Bookmark[] {
  let result: Bookmark[] = []
  const q = query.toLowerCase()
  for (const item of items) {
    if (item.title.toLowerCase().includes(q) || (item.url && item.url.toLowerCase().includes(q))) result.push(item)
    if (item.children) result = result.concat(searchBookmarks(item.children, query))
  }
  return result
}

function findItemById(list: Bookmark[], id: string): Bookmark | null {
  for (const item of list) {
    if (item.id === id) return item
    if (item.children) {
      const found = findItemById(item.children, id)
      if (found) return found
    }
  }
  return null
}

function resolvePath(parentId: string | null): string {
  if (!parentId || parentId === 'root') return '根目录'
  const item = findItemById(bookmarks.value, parentId)
  return item ? item.title : '未知文件夹'
}

// 扁平化所有文件夹（用于左侧树形导航）
const flattenedFolders = computed<Bookmark[]>(() => {
  const result: Bookmark[] = []
  const traverse = (items: Bookmark[]) => {
    if (!Array.isArray(items)) return
    for (const item of items) {
      if (item.type === 'folder') {
        result.push(item)
        if (item.children) traverse(item.children)
      }
    }
  }
  traverse(bookmarks.value)
  return result
})

function enterFolder(folder: Bookmark) {
  currentFolder.value = folder
  selectedFolderId.value = folder.id
}

function goToRoot() {
  currentFolder.value = null
  selectedFolderId.value = null
}

function goUp() {
  if (!currentFolder.value?.parent_id) { goToRoot(); return }
  const parent = findItemById(bookmarks.value, currentFolder.value.parent_id)
  if (parent) enterFolder(parent)
  else goToRoot()
}

const breadcrumbPath = computed(() => {
  const parts: { title: string; id: string | null }[] = [{ title: '我的书签', id: null }]
  if (!currentFolder.value) return parts
  const path: string[] = []
  let node: Bookmark | null = currentFolder.value
  while (node) {
    path.unshift(node.title)
    node = node.parent_id ? findItemById(bookmarks.value, node.parent_id) : null
  }
  path.forEach((t, i) => parts.push({ title: t, id: i === path.length - 1 ? currentFolder.value!.id : null }))
  return parts
})

// ========== 选中 & 拖拽 ==========
const selectedItemIds = ref<Set<string>>(new Set())

function toggleSelect(item: Bookmark, e: MouseEvent) {
  if (e.ctrlKey || e.metaKey) {
    if (selectedItemIds.value.has(item.id)) selectedItemIds.value.delete(item.id)
    else selectedItemIds.value.add(item.id)
  } else {
    selectedItemIds.value.clear()
    selectedItemIds.value.add(item.id)
  }
}

function handleItemClick(item: Bookmark) {
  if (item.type === 'folder') enterFolder(item)
  else if (item.url) window.open(item.url, '_blank')
}

// ========== 拖拽排序 ==========
const dragId = ref<string | null>(null)

function onDragStart(e: DragEvent, id: string) {
  dragId.value = id
  if (e.dataTransfer) { e.dataTransfer.setData('text/plain', id); e.dataTransfer.effectAllowed = 'move' }
}

function onDragEnter(targetId: string) {
  if (!dragId.value || dragId.value === targetId) return
  const list = currentItems.value
  const fromIdx = list.findIndex(i => i.id === dragId.value)
  const toIdx = list.findIndex(i => i.id === targetId)
  if (fromIdx !== -1 && toIdx !== -1) {
    const [moved] = list.splice(fromIdx, 1)
    list.splice(toIdx, 0, moved)
  }
}

async function onDragEnd() {
  if (dragId.value) {
    const list = currentItems.value
    const pId = currentFolder.value?.id || null
    try {
      await bookmarksApi.reorderBookmarks(list.map(i => i.id), pId)
    } catch { /* ignore */ }
  }
  dragId.value = null
}

async function onDropOnFolder(folder: Bookmark) {
  if (!dragId.value || dragId.value === folder.id) return
  const ids = Array.from(selectedItemIds.value)
  if (ids.length === 0) ids.push(dragId.value)
  try {
    await bookmarksApi.reorderBookmarks(ids, folder.id)
    success(`成功移动 ${ids.length} 个项目`)
    await loadBookmarks()
    selectedItemIds.value.clear()
  } catch { showError('移动失败') }
  dragId.value = null
}

// ========== 书签/文件夹编辑弹窗 ==========
const showBookmarkDialog = ref(false)
const editingItem = ref<Bookmark | null>(null)
const bookmarkForm = reactive({ title: '', url: '', icon: '' })

function openAddBookmark() {
  editingItem.value = null
  Object.assign(bookmarkForm, { title: '', url: '', icon: '' })
  showBookmarkDialog.value = true
}

function openEditItem(item: Bookmark) {
  editingItem.value = item
  Object.assign(bookmarkForm, { title: item.title, url: item.url || '', icon: item.icon || '' })
  showBookmarkDialog.value = true
}

async function saveBookmark() {
  try {
    const pId = currentFolder.value?.id || null
    if (editingItem.value) {
      await bookmarksApi.updateBookmark(editingItem.value.id, { ...bookmarkForm, type: 'file' })
      success('书签已更新')
    } else {
      await bookmarksApi.createBookmark({ ...bookmarkForm, type: 'file', parent_id: pId })
      success('书签已创建')
    }
    showBookmarkDialog.value = false
    await loadBookmarks()
  } catch { showError('保存失败') }
}

async function fetchIconForUrl() {
  if (!bookmarkForm.url) return
  try {
    const data = await bookmarksApi.fetchIcon(bookmarkForm.url)
    if ((data as any)?.icon) bookmarkForm.icon = (data as any).icon
  } catch { /* ignore */ }
}

// ========== 文件夹弹窗 ==========
const showFolderDialog = ref(false)
const folderName = ref('')

function openAddFolder() {
  folderName.value = ''
  showFolderDialog.value = true
}

async function saveFolder() {
  if (!folderName.value.trim()) return
  try {
    const pId = currentFolder.value?.id || null
    await bookmarksApi.createBookmark({ title: folderName.value, type: 'folder', parent_id: pId })
    success('文件夹已创建')
    showFolderDialog.value = false
    await loadBookmarks()
  } catch { showError('创建文件夹失败') }
}

// ========== 删除 & 清空 ==========
async function deleteItem(item: Bookmark) {
  const ok = await confirm({ title: '删除确认', content: `确定删除「${item.title}」吗？`, confirmColor: 'error' })
  if (!ok) return
  try { await bookmarksApi.deleteBookmark(item.id); success('已删除'); await loadBookmarks() }
  catch { showError('删除失败') }
}

async function deleteSelected() {
  const count = selectedItemIds.value.size
  if (count === 0) return
  const ok = await confirm({ title: '批量删除', content: `确定删除选中的 ${count} 个项目吗？`, confirmColor: 'error' })
  if (!ok) return
  try {
    for (const id of Array.from(selectedItemIds.value)) await bookmarksApi.deleteBookmark(id)
    success(`已删除 ${count} 个项目`)
    selectedItemIds.value.clear()
    await loadBookmarks()
  } catch { showError('部分删除失败') }
}

async function clearAll() {
  const ok = await confirm({ title: '危险操作', content: '确定要清空所有书签吗？此操作无法撤销。', confirmColor: 'error' })
  if (!ok) return
  try { await bookmarksApi.clearBookmarks(); success('已全部清空'); goToRoot(); await loadBookmarks() }
  catch { showError('清空失败') }
}

// ========== 导入/导出 ==========
const importInput = ref<HTMLInputElement | null>(null)

function triggerImport() { importInput.value?.click() }

async function handleImportHtml(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  try {
    const res = await bookmarksApi.importHtml(file) as any
    success(`成功导入 ${res.count || 0} 个项目`)
    await loadBookmarks()
  } catch { showError('导入失败') }
  finally { (e.target as HTMLInputElement).value = '' }
}

function handleExport() { bookmarksApi.exportBookmarks() }

// ========== 体检中心 ==========
const showHealthDialog = ref(false)
const healthTab = ref('duplicate')

// 重复检测
const duplicates = ref<any[]>([])
const loadingDuplicates = ref(false)

async function scanDuplicates() {
  loadingDuplicates.value = true
  try { duplicates.value = (await bookmarksApi.findDuplicates()) as any[] || [] }
  catch { showError('扫描重复失败') }
  finally { loadingDuplicates.value = false }
}

async function mergeDuplicate(group: any, keepId: string) {
  try {
    for (const item of group.items) {
      if (item.id !== keepId) await bookmarksApi.deleteBookmark(item.id)
    }
    duplicates.value = duplicates.value.filter(g => g.url !== group.url)
    success('合并成功')
    await loadBookmarks()
  } catch { showError('合并失败') }
}

async function mergeAllDuplicates() {
  if (duplicates.value.length === 0) return
  const totalToDelete = duplicates.value.reduce((acc, g) => acc + (g.count - 1), 0)
  const ok = await confirm({ title: '批量合并', content: `确定合并所有重复组？将清理 ${totalToDelete} 个重复项。`, confirmColor: 'warning' })
  if (!ok) return
  try {
    let count = 0
    for (const group of duplicates.value) {
      const keepId = group.items[0].id
      for (const item of group.items) {
        if (item.id !== keepId) { try { await bookmarksApi.deleteBookmark(item.id); count++ } catch {} }
      }
    }
    duplicates.value = []
    success(`成功清理 ${count} 个重复项`)
    await loadBookmarks()
  } catch { showError('合并异常') }
}

// 无效链接诊断
const healthResults = ref<any[]>([])
const healthProgress = ref(0)
const isScanningHealth = ref(false)

async function scanHealth() {
  if (isScanningHealth.value) return
  isScanningHealth.value = true
  healthProgress.value = 0
  healthResults.value = []

  const allFiles: Bookmark[] = []
  const traverse = (items: Bookmark[]) => {
    for (const item of items) {
      if (item.type === 'file' && item.url) allFiles.push(item)
      if (item.children) traverse(item.children)
    }
  }
  traverse(bookmarks.value)

  const total = allFiles.length
  if (total === 0) { isScanningHealth.value = false; return }

  const BATCH_SIZE = 10
  for (let i = 0; i < total; i += BATCH_SIZE) {
    if (!isScanningHealth.value) break
    const batch = allFiles.slice(i, i + BATCH_SIZE)
    const urls = batch.map(b => b.url!)
    try {
      const res = await bookmarksApi.checkHealth(urls) as any
      for (const item of batch) {
        const status = res[item.url]
        if (status !== 200) healthResults.value.push({ ...item, statusCode: status })
      }
    } catch {}
    healthProgress.value = Math.min(100, Math.round(((i + BATCH_SIZE) / total) * 100))
  }
  healthProgress.value = 100
  isScanningHealth.value = false
}

function stopScanHealth() { isScanningHealth.value = false }

async function deleteDead(id: string) {
  try {
    await bookmarksApi.deleteBookmark(id)
    healthResults.value = healthResults.value.filter(h => h.id !== id)
    success('已删除')
    await loadBookmarks()
  } catch { showError('删除失败') }
}

async function deleteBatchDead(statusCodes: number[]) {
  const targets = healthResults.value.filter(h => statusCodes.includes(h.statusCode))
  if (targets.length === 0) { warning('没有符合条件的书签'); return }
  const ok = await confirm({ title: '批量清理', content: `确定清理 ${targets.length} 个无效书签吗？`, confirmColor: 'warning' })
  if (!ok) return
  try {
    let count = 0
    for (const t of targets) { try { await bookmarksApi.deleteBookmark(t.id); count++ } catch {} }
    healthResults.value = healthResults.value.filter(h => !statusCodes.includes(h.statusCode))
    success(`成功清理 ${count} 个无效书签`)
    await loadBookmarks()
  } catch { showError('清理失败') }
}

// ========== AI 整理 ==========
const isOrganizing = ref(false)

async function handleAIAnalyze() {
  if (isOrganizing.value) return
  const ok = await confirm({ title: 'AI 整理书签', content: 'AI 将自动对当前目录下的书签进行分类整理。确认启动？' })
  if (!ok) return
  isOrganizing.value = true
  const folderId = currentFolder.value?.id || null
  try {
    const token = localStorage.getItem('lens_access_token')
    const response = await fetch('/api/bookmarks/ai-auto-organize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({ folder_id: folderId })
    })
    if (!response.ok) throw new Error('请求失败')
    const reader = response.body?.getReader()
    if (reader) {
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        decoder.decode(value)
      }
    }
    success('AI 整理已完成')
    await loadBookmarks()
  } catch (err: any) {
    showError('AI 整理异常: ' + (err.message || '未知错误'))
  } finally {
    isOrganizing.value = false
  }
}

onMounted(loadBookmarks)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-bookmark-outline</v-icon>
      书签管理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">管理浏览器书签与常用链接，支持文件夹导航、拖拽排序、重复检测与 AI 整理。</p>

    <!-- 工具栏 -->
    <div class="d-flex flex-wrap ga-2 mb-4 align-center">
      <v-text-field v-model="searchQuery" prepend-inner-icon="mdi-magnify" placeholder="搜索书签..."
        variant="outlined" density="compact" hide-details clearable style="max-width:240px" />
      <v-btn variant="tonal" color="primary" size="small" prepend-icon="mdi-plus" @click="openAddBookmark">添加书签</v-btn>
      <v-btn variant="tonal" color="info" size="small" prepend-icon="mdi-folder-plus-outline" @click="openAddFolder">新建文件夹</v-btn>
      <v-btn variant="tonal" color="success" size="small" prepend-icon="mdi-file-import-outline" @click="triggerImport">导入 HTML</v-btn>
      <v-btn variant="tonal" color="info" size="small" prepend-icon="mdi-file-export-outline" @click="handleExport">导出HTML</v-btn>
      <v-btn variant="tonal" color="warning" size="small" prepend-icon="mdi-stethoscope" @click="showHealthDialog = true">体检中心</v-btn>
      <v-btn variant="tonal" color="deep-purple" size="small" prepend-icon="mdi-robot-outline" :loading="isOrganizing" @click="handleAIAnalyze">AI 整理</v-btn>
      <v-spacer />
      <v-btn v-if="selectedItemIds.size > 0" variant="tonal" color="error" size="small" prepend-icon="mdi-delete-outline" @click="deleteSelected">
        删除选中 ({{ selectedItemIds.size }})
      </v-btn>
      <v-btn variant="tonal" color="info" size="small" :loading="loading" prepend-icon="mdi-refresh" @click="loadBookmarks">刷新</v-btn>
    </div>

    <input ref="importInput" type="file" accept=".html,.htm" style="display:none" @change="handleImportHtml" />

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <!-- 面包屑导航 -->
    <div class="d-flex align-center ga-1 mb-3 flex-wrap">
      <template v-for="(crumb, i) in breadcrumbPath" :key="i">
        <v-btn variant="text" size="small" density="compact" :disabled="!crumb.id && i === breadcrumbPath.length - 1"
          @click="crumb.id ? enterFolder(findItemById(bookmarks, crumb.id)!) : goToRoot()">
          {{ crumb.title }}
        </v-btn>
        <v-icon v-if="i < breadcrumbPath.length - 1" size="14" color="grey">mdi-chevron-right</v-icon>
      </template>
    </div>

    <v-row>
      <!-- 左侧文件夹树 -->
      <v-col cols="12" md="3">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-3 text-subtitle-2">
            <v-icon start size="18">mdi-folder-multiple-outline</v-icon>
            文件夹
          </v-card-title>
          <v-divider />
          <v-list density="compact" class="bg-transparent pa-2" style="max-height:70vh;overflow-y:auto">
            <v-list-item :active="!currentFolder" @click="goToRoot()" class="rounded-lg mb-1">
              <template #prepend><v-icon size="18" class="mr-2">mdi-home-outline</v-icon></template>
              <v-list-item-title class="text-body-2">全部书签</v-list-item-title>
            </v-list-item>
            <template v-for="folder in flattenedFolders" :key="folder.id">
              <v-list-item :active="currentFolder?.id === folder.id" @click="enterFolder(folder)"
                class="rounded-lg mb-1" :style="{ paddingLeft: `${(folder.parent_id ? 16 : 8) + 12}px` }"
                @dragover.prevent @drop.prevent="onDropOnFolder(folder)">
                <template #prepend><v-icon size="18" class="mr-2" color="warning">mdi-folder-outline</v-icon></template>
                <v-list-item-title class="text-body-2 text-truncate">{{ folder.title }}</v-list-item-title>
                <template #append>
                  <v-chip size="x-small" variant="tonal">{{ folder.children?.length || 0 }}</v-chip>
                </template>
              </v-list-item>
            </template>
          </v-list>
        </v-card>
      </v-col>

      <!-- 右侧书签列表 -->
      <v-col cols="12" md="9">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-table class="bg-transparent">
            <thead>
              <tr>
                <th style="width:40px"></th>
                <th>标题</th>
                <th>URL</th>
                <th>所在文件夹</th>
                <th class="text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!loading && currentItems.length === 0">
                <td colspan="5" class="text-center py-8 text-medium-emphasis">
                  <v-icon size="48" color="grey" class="mb-2">mdi-bookmark-off-outline</v-icon>
                  <div>暂无书签</div>
                </td>
              </tr>
              <tr v-for="item in currentItems" :key="item.id"
                :class="{ 'selected-item': selectedItemIds.has(item.id) }"
                draggable="true"
                @dragstart="onDragStart($event, item.id)"
                @dragenter="item.type === 'file' && onDragEnter(item.id)"
                @dragend="onDragEnd"
                @click="toggleSelect(item, $event)"
                @dblclick="handleItemClick(item)"
                style="cursor:pointer">

                <td>
                  <v-icon size="20" :color="item.type === 'folder' ? 'warning' : 'primary'">
                    {{ item.type === 'folder' ? 'mdi-folder-outline' : (item.icon ? 'mdi-web' : 'mdi-bookmark-outline') }}
                  </v-icon>
                </td>
                <td>
                  <div class="d-flex align-center ga-2">
                    <img v-if="item.icon && item.type === 'file'" :src="item.icon" width="16" height="16" class="flex-shrink-0" style="object-fit:contain" />
                    <span class="font-weight-medium">{{ item.title }}</span>
                    <v-chip v-if="item.type === 'folder'" size="x-small" variant="tonal" color="warning">
                      {{ item.children?.length || 0 }} 项
                    </v-chip>
                  </div>
                </td>
                <td>
                  <a v-if="item.url" :href="item.url" target="_blank" class="text-decoration-none font-mono text-medium-emphasis"
                    style="font-size:12px" @click.stop>{{ item.url }}</a>
                  <span v-else class="text-medium-emphasis">-</span>
                </td>
                <td>
                  <v-chip v-if="item.parent_id" size="x-small" variant="tonal">{{ resolvePath(item.parent_id) }}</v-chip>
                  <span v-else class="text-medium-emphasis text-caption">根目录</span>
                </td>
                <td class="text-right">
                  <v-btn icon variant="tonal" size="x-small" color="primary" @click.stop="openEditItem(item)">
                    <v-icon size="14">mdi-pencil-outline</v-icon>
                  </v-btn>
                  <v-btn icon variant="tonal" size="x-small" color="error" class="ml-1" @click.stop="deleteItem(item)">
                    <v-icon size="14">mdi-delete-outline</v-icon>
                  </v-btn>
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-col>
    </v-row>

    <!-- 书签编辑弹窗 -->
    <GlassDialog v-model="showBookmarkDialog" :max-width="520"
      icon="mdi-bookmark-outline" :title="editingItem ? '编辑书签' : '添加书签'"
    >
      <v-text-field v-model="bookmarkForm.title" label="标题" variant="outlined" density="compact" class="mb-3" />
      <v-text-field v-model="bookmarkForm.url" label="URL" variant="outlined" density="compact" class="mb-3" />
      <v-text-field v-model="bookmarkForm.icon" label="图标路径" variant="outlined" density="compact" hint="可留空，也可点击自动获取" persistent-hint>
        <template #append>
          <v-btn size="x-small" variant="tonal" color="info" prepend-icon="mdi-auto-fix" @click="fetchIconForUrl">自动获取</v-btn>
        </template>
      </v-text-field>
      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveBookmark">保存</v-btn>
      </template>
    </GlassDialog>

    <!-- 新建文件夹弹窗 -->
    <GlassDialog v-model="showFolderDialog" :max-width="420"
      icon="mdi-folder-plus-outline" title="新建文件夹"
    >
      <v-text-field v-model="folderName" label="文件夹名称" variant="outlined" density="compact"
        placeholder="请输入文件夹名称" @keydown.enter="saveFolder" />
      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-folder-plus-outline" @click="saveFolder">创建</v-btn>
      </template>
    </GlassDialog>

    <!-- 体检中心弹窗 -->
    <GlassDialog v-model="showHealthDialog" :max-width="900"
      icon="mdi-stethoscope" title="书签体检中心" cancel-text="关闭"
    >
      <v-tabs v-model="healthTab" density="compact">
        <v-tab value="duplicate" size="small">重复检测</v-tab>
        <v-tab value="health" size="small">无效链接诊断</v-tab>
      </v-tabs>
      <v-divider />

      <!-- 重复检测 -->
      <div v-if="healthTab === 'duplicate'" class="pt-4">
        <div class="d-flex ga-2 mb-4">
          <v-btn color="primary" variant="flat" size="small" prepend-icon="mdi-magnify-scan" :loading="loadingDuplicates" @click="scanDuplicates">扫描重复</v-btn>
          <v-btn v-if="duplicates.length > 0" variant="tonal" color="warning" size="small" prepend-icon="mdi-merge" @click="mergeAllDuplicates">自动合并</v-btn>
        </div>

        <div v-if="duplicates.length > 0" class="d-flex flex-column ga-3">
          <v-card v-for="group in duplicates" :key="group.url" variant="outlined" rounded="lg" class="pa-3">
            <div class="d-flex align-center mb-2">
              <div class="flex-grow-1">
                <div class="text-body-2 font-weight-medium">{{ group.items[0]?.title || '无标题' }}</div>
                <div class="text-caption text-medium-emphasis font-mono">{{ group.url }}</div>
              </div>
              <v-chip size="small" variant="tonal" color="warning">{{ group.count }} 处重复</v-chip>
            </div>
            <div class="d-flex flex-column ga-1">
              <div v-for="item in group.items" :key="item.id" class="d-flex align-center justify-space-between pa-2 rounded" style="background:rgba(var(--v-theme-on-surface),0.03)">
                <div class="d-flex align-center ga-2">
                  <v-icon size="16" color="warning">mdi-folder-outline</v-icon>
                  <span class="text-caption">{{ resolvePath(item.parent_id) }}</span>
                </div>
                <v-btn size="x-small" variant="tonal" color="primary" prepend-icon="mdi-check" @click="mergeDuplicate(group, item.id)">保留此项</v-btn>
              </div>
            </div>
          </v-card>
        </div>
        <div v-else class="text-center py-8 text-medium-emphasis">
          <v-icon size="48" color="grey" class="mb-2">mdi-check-circle-outline</v-icon>
          <div>未发现重复书签</div>
        </div>
      </div>

      <!-- 无效链接诊断 -->
      <div v-if="healthTab === 'health'" class="pt-4">
        <div class="d-flex ga-2 mb-4">
          <v-btn v-if="isScanningHealth" color="error" variant="flat" size="small" prepend-icon="mdi-stop" @click="stopScanHealth">停止诊断</v-btn>
          <v-btn v-else color="primary" variant="flat" size="small" prepend-icon="mdi-magnify-scan" @click="scanHealth">开始扫描</v-btn>
          <v-btn v-if="healthResults.some(h => h.statusCode === 404)" variant="tonal" color="warning" size="small" prepend-icon="mdi-delete-sweep-outline" @click="deleteBatchDead([404])">清理 404</v-btn>
        </div>

        <v-progress-linear v-if="isScanningHealth || healthProgress > 0" :model-value="healthProgress" color="primary" class="mb-3" height="4" rounded />

        <div v-if="healthResults.length > 0" class="d-flex flex-column ga-2">
          <div v-for="item in healthResults" :key="item.id" class="d-flex align-center ga-3 pa-3 rounded-lg" style="background:rgba(var(--v-theme-on-surface),0.03)">
            <v-chip size="small" :color="item.statusCode === 0 ? 'warning' : 'error'" variant="tonal">
              {{ item.statusCode === 0 ? 'TIMEOUT' : item.statusCode }}
            </v-chip>
            <div class="flex-grow-1" style="min-width:0">
              <div class="text-body-2 font-weight-medium text-truncate">{{ item.title || '无标题书签' }}</div>
              <div class="text-caption text-medium-emphasis">
                <v-icon size="12">mdi-folder-outline</v-icon> {{ resolvePath(item.parent_id) }}
              </div>
            </div>
            <v-btn icon variant="tonal" size="x-small" color="error" @click="deleteDead(item.id)">
              <v-icon size="14">mdi-delete-outline</v-icon>
            </v-btn>
          </div>
        </div>
        <div v-else class="text-center py-8 text-medium-emphasis">
          <v-icon size="48" color="grey" class="mb-2">mdi-check-circle-outline</v-icon>
          <div>暂无异常书签链接</div>
        </div>
      </div>
    </GlassDialog>
  </v-container>
</template>
