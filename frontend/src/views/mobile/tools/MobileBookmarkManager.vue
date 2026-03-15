<template>
  <div class="mobile-bookmark-manager">
    <div class="page-header">
      <h1 class="page-title">书签管理</h1>
      <p class="page-desc">管理浏览器书签</p>
    </div>

    <n-card class="search-card" :bordered="false">
      <n-input v-model:value="searchQuery" placeholder="搜索书签..." clearable>
        <template #prefix>
          <n-icon><SearchIcon /></n-icon>
        </template>
      </n-input>
    </n-card>

    <n-card class="bookmarks-card" :bordered="false" title="书签列表">
      <n-space vertical>
        <n-space vertical>
          <n-button block type="primary" @click="showAddBookmarkModal = true">
            <template #icon><n-icon><AddIcon /></n-icon></template>
            添加书签
          </n-button>
          <n-button block secondary type="primary" @click="handleAIAnalyze">
            <template #icon><n-icon><LabIcon /></n-icon></template>
            AI 智能整理
          </n-button>
          <n-button block secondary @click="showHealthModal = true">
            <template #icon><n-icon><HealthIcon /></n-icon></template>
            体检中心
          </n-button>
          <n-button block secondary @click="triggerFileInput">
            <template #icon><n-icon><ImportIcon /></n-icon></template>
            导入书签
            <input 
              type="file" 
              ref="fileInputRef" 
              style="display: none" 
              accept=".html,.htm" 
              @change="onFileChange"
            />
          </n-button>
          <n-button block secondary @click="handleExport">
            <template #icon><n-icon><ExportIcon /></n-icon></template>
            导出书签
          </n-button>
          <n-button block secondary type="error" @click="handleClearAll">
            <template #icon><n-icon><ClearIcon /></n-icon></template>
            清空所有书签
          </n-button>
        </n-space>
        <div v-if="filteredBookmarks.length === 0" class="empty-state">
          <n-empty description="暂无书签" />
        </div>
        <div v-else class="bookmark-list">
          <div v-for="bookmark in filteredBookmarks" :key="bookmark.id" class="bookmark-item" @click="openBookmark(bookmark)">
            <div class="bookmark-info">
              <div class="bookmark-title">{{ bookmark.title }}</div>
              <div class="bookmark-url">{{ bookmark.url }}</div>
              <div v-if="bookmark.folder" class="bookmark-folder">
                <n-tag size="small" type="info">{{ bookmark.folder }}</n-tag>
              </div>
            </div>
            <div class="bookmark-actions">
              <n-button size="small" secondary type="warning" @click.stop="editBookmark(bookmark)">
                编辑
              </n-button>
              <n-popconfirm @positive-click="handleDeleteBookmark(bookmark.id)" positive-text="确认删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error" @click.stop>
                    删除
                  </n-button>
                </template>
                确定删除此书签？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-card class="folders-card" :bordered="false" title="文件夹">
      <n-space vertical>
        <n-button block type="primary" secondary @click="showAddFolderModal = true">
          <template #icon><n-icon><FolderAddIcon /></n-icon></template>
          新建文件夹
        </n-button>
        <div v-if="folders.length === 0" class="empty-state">
          <n-empty description="暂无文件夹" />
        </div>
        <div v-else class="folder-list">
          <div v-for="folder in folders" :key="folder.id" class="folder-item">
            <div class="folder-info">
              <div class="folder-name">{{ folder.name }}</div>
              <div class="folder-count">{{ folder.count }} 个书签</div>
            </div>
            <n-popconfirm @positive-click="handleDeleteFolder(folder.id)" positive-text="确认删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    删除
                  </n-button>
                </template>
                确定删除此文件夹？其中的书签也会被删除。
              </n-popconfirm>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddBookmarkModal" preset="card" :title="editingBookmark.id ? '编辑书签' : '添加书签'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="标题">
          <n-input v-model:value="editingBookmark.title" placeholder="书签标题" />
        </n-form-item>
        <n-form-item label="URL">
          <n-input v-model:value="editingBookmark.url" placeholder="https://example.com" />
        </n-form-item>
        <n-form-item label="文件夹">
          <n-select v-model:value="editingBookmark.folder" :options="folderOptions" clearable />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddBookmarkModal = false">取消</n-button>
          <n-button type="primary" @click="saveBookmark" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showAddFolderModal" preset="card" title="新建文件夹" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="文件夹名称">
          <n-input v-model:value="newFolder.name" placeholder="文件夹名称" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddFolderModal = false">取消</n-button>
          <n-button type="primary" @click="saveFolder" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showHealthModal" preset="card" title="体检中心" style="width: 90vw; max-width: 500px">
      <n-tabs v-model:value="healthActiveTab" type="line" animated>
        <n-tab-pane name="duplicates" tab="重复项检测">
          <n-space vertical>
            <n-button block type="primary" @click="scanDuplicates" :loading="loadingDuplicates">
              <template #icon><n-icon><SearchIcon /></n-icon></template>
              扫描重复项
            </n-button>
            <div v-if="duplicates.length > 0" class="duplicates-list">
              <n-divider>重复项 ({{ duplicates.length }} 组)</n-divider>
              <div v-for="group in duplicates" :key="group.url" class="duplicate-group">
                <div class="duplicate-url">{{ group.url }}</div>
                <div class="duplicate-items">
                  <div v-for="item in group.items" :key="item.id" class="duplicate-item">
                    {{ item.title }}
                  </div>
                </div>
                <n-space :size="8">
                  <n-button size="small" type="primary" @click="handleMergeDuplicate(group)">
                    合并
                  </n-button>
                  <n-button size="small" type="error" @click="handleDeleteAllInGroup(group)">
                    删除全部
                  </n-button>
                </n-space>
              </div>
            </div>
            <div v-else-if="!loadingDuplicates" class="empty-state">
              <n-empty description="暂无重复项" />
            </div>
          </n-space>
        </n-tab-pane>
        <n-tab-pane name="health" tab="死链检测">
          <n-space vertical>
            <n-button block type="primary" @click="scanHealth" :disabled="isScanningHealth">
              <template #icon><n-icon><SearchIcon /></n-icon></template>
              开始检测
            </n-button>
            <n-button v-if="isScanningHealth" block secondary @click="stopScanHealth">
              停止检测
            </n-button>
            <div v-if="isScanningHealth">
              <n-progress type="line" :percentage="healthProgress" />
              <div class="scan-status">正在检测... {{ healthProgress }}%</div>
            </div>
            <div v-if="healthResults.length > 0" class="health-results">
              <n-divider>失效链接 ({{ healthResults.length }} 个)</n-divider>
              <div v-for="result in healthResults" :key="result.bookmark.id" class="health-item">
                <div class="health-title">{{ result.bookmark.title }}</div>
                <div class="health-url">{{ result.bookmark.url }}</div>
                <n-button size="small" type="error" @click="handleDeleteDead(result)">
                  删除
                </n-button>
              </div>
              <n-button block type="error" @click="handleDeleteBatchDead">
                批量删除失效链接
              </n-button>
            </div>
            <div v-else-if="!isScanningHealth" class="empty-state">
              <n-empty description="暂无失效链接" />
            </div>
          </n-space>
        </n-tab-pane>
      </n-tabs>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, NIcon, NTabs, NTabPane, NProgress, NAlert, NDivider } from 'naive-ui'
import { AddOutlined as AddIcon, SearchOutlined as SearchIcon, CreateNewFolderOutlined as FolderAddIcon, ScienceOutlined as LabIcon, MedicalServicesOutlined as HealthIcon, FileDownloadOutlined as ImportIcon, FileUploadOutlined as ExportIcon, DeleteSweepOutlined as ClearIcon } from '@vicons/material'
import { useMessage } from 'naive-ui'
import { useBookmark } from '../../toolkit/sitenav/useBookmark'

const message = useMessage()
const { 
  bookmarks, 
  loading, 
  fetchBookmarks, 
  addBookmark, 
  updateBookmark, 
  deleteBookmark: deleteBookmarkApi,
  exportBookmarks,
  clearBookmarks
} = useBookmark()

const searchQuery = ref('')
const showAddBookmarkModal = ref(false)
const showAddFolderModal = ref(false)
const showHealthModal = ref(false)
const saving = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const healthActiveTab = ref('duplicates')
const duplicates = ref<any[]>([])
const loadingDuplicates = ref(false)
const healthResults = ref<any[]>([])
const healthProgress = ref(0)
const isScanningHealth = ref(false)

const editingBookmark = ref({
  id: null as string | null,
  title: '',
  url: '',
  parent_id: null as string | null
})

const newFolder = ref({
  name: ''
})

// 将书签列表扁平化并添加文件夹信息
const flatBookmarks = computed(() => {
  const result: any[] = []
  const flatten = (items: any[], folderName = '') => {
    items.forEach(item => {
      if (item.type === 'folder') {
        flatten(item.children || [], item.title)
      } else {
        result.push({
          ...item,
          folder: folderName
        })
      }
    })
  }
  flatten(bookmarks.value)
  return result
})

const filteredBookmarks = computed(() => {
  if (!searchQuery.value) return flatBookmarks.value
  const query = searchQuery.value.toLowerCase()
  return flatBookmarks.value.filter(b => 
    b.title?.toLowerCase().includes(query) || 
    b.url?.toLowerCase().includes(query)
  )
})

// 获取文件夹列表
const folders = computed(() => {
  const folderList: any[] = []
  const countBookmarks = (items: any[]): number => {
    let count = 0
    items.forEach(item => {
      if (item.type === 'folder') {
        count += countBookmarks(item.children || [])
      } else {
        count++
      }
    })
    return count
  }
  
  const findFolders = (items: any[]) => {
    items.forEach(item => {
      if (item.type === 'folder') {
        folderList.push({
          id: item.id,
          name: item.title,
          count: countBookmarks(item.children || [])
        })
        findFolders(item.children || [])
      }
    })
  }
  findFolders(bookmarks.value)
  return folderList
})

const folderOptions = computed(() => {
  return folders.value.map(f => ({ label: f.name, value: f.id }))
})

const openBookmark = (bookmark: any) => {
  if (bookmark.url) {
    window.open(bookmark.url, '_blank')
  }
}

const editBookmark = (bookmark: any) => {
  editingBookmark.value = { 
    id: bookmark.id,
    title: bookmark.title,
    url: bookmark.url || '',
    parent_id: bookmark.parent_id || null
  }
  showAddBookmarkModal.value = true
}

const saveBookmark = async () => {
  if (!editingBookmark.value.title || !editingBookmark.value.url) {
    message.warning('请填写完整的书签信息')
    return
  }
  saving.value = true
  try {
    if (editingBookmark.value.id) {
      await updateBookmark(editingBookmark.value.id, {
        title: editingBookmark.value.title,
        url: editingBookmark.value.url,
        parent_id: editingBookmark.value.parent_id || undefined
      })
      message.success('书签更新成功')
    } else {
      await addBookmark({
        title: editingBookmark.value.title,
        url: editingBookmark.value.url,
        type: 'file',
        parent_id: editingBookmark.value.parent_id || undefined
      })
      message.success('书签添加成功')
    }
    showAddBookmarkModal.value = false
    editingBookmark.value = { id: null, title: '', url: '', parent_id: null }
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleDeleteBookmark = async (id: string) => {
  try {
    await deleteBookmarkApi(id)
    message.success('书签已删除')
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

const saveFolder = async () => {
  if (!newFolder.value.name) {
    message.warning('请填写文件夹名称')
    return
  }
  saving.value = true
  try {
    await addBookmark({
      title: newFolder.value.name,
      type: 'folder'
    })
    message.success('文件夹创建成功')
    showAddFolderModal.value = false
    newFolder.value = { name: '' }
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error('创建失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleDeleteFolder = async (id: string) => {
  try {
    await deleteBookmarkApi(id)
    message.success('文件夹已删除')
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

const handleExport = () => {
  exportBookmarks()
}

const handleClearAll = async () => {
  try {
    await clearBookmarks()
    message.success('所有书签已清空')
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error('清空失败: ' + (e.message || '未知错误'))
  }
}

const triggerFileInput = () => {
  fileInputRef.value?.click()
}

const onFileChange = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  
  try {
    const text = await file.text()
    const parser = new DOMParser()
    const doc = parser.parseFromString(text, 'text/html')
    const links = doc.querySelectorAll('a')
    
    let count = 0
    for (const link of links) {
      const url = link.getAttribute('href')
      const title = link.textContent || url
      if (url) {
        await addBookmark({
          title: title || '未命名书签',
          url: url,
          type: 'file'
        })
        count++
      }
    }
    
    message.success(`成功导入 ${count} 个书签`)
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error('导入失败: ' + (e.message || '未知错误'))
  }
}

const handleAIAnalyze = () => {
  message.info('AI智能整理功能需要后端支持，请在桌面端使用')
}

const scanDuplicates = () => {
  loadingDuplicates.value = true
  duplicates.value = []
  
  const urlMap = new Map<string, any[]>()
  flatBookmarks.value.forEach(bookmark => {
    const url = bookmark.url?.trim()
    if (url) {
      if (!urlMap.has(url)) {
        urlMap.set(url, [])
      }
      urlMap.get(url)!.push(bookmark)
    }
  })
  
  urlMap.forEach((items, url) => {
    if (items.length > 1) {
      duplicates.value.push({
        url: url,
        items: items,
        count: items.length
      })
    }
  })
  
  loadingDuplicates.value = false
  message.info(`发现 ${duplicates.value.length} 组重复书签`)
}

const scanHealth = async () => {
  isScanningHealth.value = true
  healthProgress.value = 0
  healthResults.value = []
  
  const total = flatBookmarks.value.length
  const deadLinks: any[] = []
  
  for (let i = 0; i < total; i++) {
    const bookmark = flatBookmarks.value[i]
    try {
      const response = await fetch(bookmark.url, { method: 'HEAD', mode: 'no-cors' })
      healthResults.value.push({
        bookmark: bookmark,
        status: 'ok',
        message: '链接正常'
      })
    } catch (e) {
      deadLinks.push({
        bookmark: bookmark,
        status: 'dead',
        message: '链接失效'
      })
    }
    healthProgress.value = Math.round(((i + 1) / total) * 100)
  }
  
  healthResults.value = deadLinks
  isScanningHealth.value = false
  message.info(`发现 ${deadLinks.length} 个失效链接`)
}

const stopScanHealth = () => {
  isScanningHealth.value = false
  message.info('扫描已停止')
}

const handleDeleteDead = async (result: any) => {
  try {
    await deleteBookmarkApi(result.bookmark.id)
    message.success('书签已删除')
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

const handleDeleteBatchDead = async () => {
  try {
    for (const result of healthResults.value) {
      await deleteBookmarkApi(result.bookmark.id)
    }
    message.success(`已删除 ${healthResults.value.length} 个失效书签`)
    healthResults.value = []
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error('批量删除失败: ' + (e.message || '未知错误'))
  }
}

const handleMergeDuplicate = async (group: any) => {
  try {
    const keep = group.items[0]
    for (let i = 1; i < group.items.length; i++) {
      await deleteBookmarkApi(group.items[i].id)
    }
    message.success('重复书签已合并')
    await fetchBookmarks(true)
    scanDuplicates()
  } catch (e: any) {
    message.error('合并失败: ' + (e.message || '未知错误'))
  }
}

const handleMergeAllDuplicates = async () => {
  try {
    for (const group of duplicates.value) {
      const keep = group.items[0]
      for (let i = 1; i < group.items.length; i++) {
        await deleteBookmarkApi(group.items[i].id)
      }
    }
    message.success('所有重复书签已合并')
    await fetchBookmarks(true)
    scanDuplicates()
  } catch (e: any) {
    message.error('批量合并失败: ' + (e.message || '未知错误'))
  }
}

const handleDeleteAllInGroup = async (group: any) => {
  try {
    for (const item of group.items) {
      await deleteBookmarkApi(item.id)
    }
    message.success('书签组已删除')
    await fetchBookmarks(true)
    scanDuplicates()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

onMounted(() => {
  fetchBookmarks(true)
})
</script>

<style scoped>
.mobile-bookmark-manager {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.search-card,
.bookmarks-card,
.folders-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.bookmark-list,
.folder-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bookmark-item,
.folder-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.bookmark-info,
.folder-info {
  margin-bottom: 8px;
}

.bookmark-title,
.folder-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.bookmark-url {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 4px;
}

.bookmark-folder {
  margin-bottom: 4px;
}

.folder-count {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.bookmark-actions {
  display: flex;
  gap: 8px;
}

.duplicates-list,
.health-results {
  max-height: 400px;
  overflow-y: auto;
}

.duplicate-group,
.health-item {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.duplicate-url,
.health-url {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 8px;
  word-break: break-all;
}

.duplicate-items {
  margin-bottom: 8px;
}

.duplicate-item {
  font-size: 14px;
  color: var(--text-color);
  padding: 4px 0;
}

.health-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.scan-status {
  text-align: center;
  font-size: 14px;
  color: var(--text-color);
  margin-top: 8px;
}
</style>
