<template>
  <div class="mobile-bookmark-manager">
    <div class="page-header">
      <h1 class="page-title">书签管理</h1>
      <p class="page-desc">管理浏览器书签</p>
    </div>

    <n-card class="search-card" :bordered="false">
      <n-input v-model:value="searchQuery" :placeholder="placeholder.SEARCH_BOOKMARK" clearable>
        <template #prefix>
          <n-icon><SearchIcon /></n-icon>
        </template>
      </n-input>
    </n-card>

    <n-card class="bookmarks-card" :bordered="false" title="书签列表">
      <n-space vertical>
        <n-space vertical>
          <n-button block :type="buttonTypes.PRIMARY" @click="showAddBookmarkModal = true">
            {{ buttonText.ADD_BOOKMARK }}
          </n-button>
          <n-button block secondary :type="buttonTypes.PRIMARY" @click="handleAIAnalyze">
            {{ buttonText.AI_ANALYZE }}
          </n-button>
          <n-button block secondary @click="showHealthModal = true">
            {{ buttonText.HEALTH_CENTER }}
          </n-button>
          <n-button block secondary @click="triggerFileInput">
            {{ buttonText.IMPORT_BOOKMARKS }}
            <input 
              type="file" 
              ref="fileInputRef" 
              style="display: none" 
              accept=".html,.htm" 
              @change="onFileChange"
            />
          </n-button>
          <n-button block secondary @click="handleExport">
            {{ buttonText.EXPORT_BOOKMARKS }}
          </n-button>
          <n-button block secondary :type="buttonTypes.ERROR" @click="handleClearAll">
            {{ buttonText.CLEAR_ALL_BOOKMARKS }}
          </n-button>
        </n-space>
        <div v-if="filteredBookmarks.length === 0" class="empty-state">
          <n-empty :description="emptyText.NO_BOOKMARKS" />
        </div>
        <div v-else class="bookmark-list">
          <div v-for="bookmark in filteredBookmarks" :key="bookmark.id" class="bookmark-item" @click="openBookmark(bookmark)">
            <div class="bookmark-info">
              <div class="bookmark-title">{{ bookmark.title }}</div>
              <div class="bookmark-url">{{ bookmark.url }}</div>
              <div v-if="bookmark.folder" class="bookmark-folder">
                <n-tag :size="buttonSizes.SMALL" :type="tagTypes.INFO">{{ bookmark.folder }}</n-tag>
              </div>
            </div>
            <div class="bookmark-actions">
              <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.WARNING" @click.stop="editBookmark(bookmark)">
                {{ buttonText.EDIT }}
              </n-button>
              <n-popconfirm @positive-click="handleDeleteBookmark(bookmark.id)" :positive-text="confirmText.CONFIRM_DELETE" :negative-text="confirmText.CANCEL">
                <template #trigger>
                  <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR" @click.stop>
                    {{ buttonText.DELETE }}
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
        <n-button block :type="buttonTypes.PRIMARY" secondary @click="showAddFolderModal = true">
          {{ buttonText.CREATE_FOLDER }}
        </n-button>
        <div v-if="folders.length === 0" class="empty-state">
          <n-empty :description="emptyText.NO_FOLDERS" />
        </div>
        <div v-else class="folder-list">
          <div v-for="folder in folders" :key="folder.id" class="folder-item">
            <div class="folder-info">
              <div class="folder-name">{{ folder.name }}</div>
              <div class="folder-count">{{ folder.count }} 个书签</div>
            </div>
            <n-popconfirm @positive-click="handleDeleteFolder(folder.id)" :positive-text="confirmText.CONFIRM_DELETE" :negative-text="confirmText.CANCEL">
                <template #trigger>
                  <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
                    {{ buttonText.DELETE }}
                  </n-button>
                </template>
                确定删除此文件夹？其中的书签也会被删除。
              </n-popconfirm>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddBookmarkModal" preset="card" :title="editingBookmark.id ? modalTitle.EDIT_BOOKMARK : modalTitle.ADD_BOOKMARK" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="formLabel.TITLE">
          <n-input v-model:value="editingBookmark.title" :placeholder="placeholder.BOOKMARK_TITLE" />
        </n-form-item>
        <n-form-item :label="formLabel.URL">
          <n-input v-model:value="editingBookmark.url" :placeholder="placeholder.BOOKMARK_URL" />
        </n-form-item>
        <n-form-item :label="formLabel.FOLDER">
          <n-select v-model:value="editingBookmark.folder" :options="folderOptions" clearable />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddBookmarkModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveBookmark" :loading="saving">{{ buttonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showAddFolderModal" preset="card" :title="modalTitle.CREATE_FOLDER" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="formLabel.FOLDER_NAME">
          <n-input v-model:value="newFolder.name" :placeholder="placeholder.FOLDER_NAME" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddFolderModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveFolder" :loading="saving">{{ buttonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showHealthModal" preset="card" :title="modalTitle.HEALTH_CENTER" style="width: 90vw; max-width: 500px">
      <n-tabs v-model:value="healthActiveTab" type="line" animated>
        <n-tab-pane name="duplicates" :tab="tabText.DUPLICATE_CHECK">
          <n-space vertical>
            <n-button block :type="buttonTypes.PRIMARY" @click="scanDuplicates" :loading="loadingDuplicates">
              {{ buttonText.SCAN_DUPLICATES }}
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
                  <n-button :size="buttonSizes.MEDIUM" :type="buttonTypes.PRIMARY" @click="handleMergeDuplicate(group)">
                    {{ buttonText.MERGE }}
                  </n-button>
                  <n-button :size="buttonSizes.MEDIUM" :type="buttonTypes.ERROR" @click="handleDeleteAllInGroup(group)">
                    {{ buttonText.DELETE_ALL }}
                  </n-button>
                </n-space>
              </div>
            </div>
            <div v-else-if="!loadingDuplicates" class="empty-state">
              <n-empty :description="emptyText.NO_DUPLICATES" />
            </div>
          </n-space>
        </n-tab-pane>
        <n-tab-pane name="health" :tab="tabText.DEAD_LINK_CHECK">
          <n-space vertical>
            <n-button block :type="buttonTypes.PRIMARY" @click="scanHealth" :disabled="isScanningHealth">
              {{ buttonText.START_SCAN }}
            </n-button>
            <n-button v-if="isScanningHealth" block secondary @click="stopScanHealth">
              {{ buttonText.STOP_SCAN }}
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
                <n-button :size="buttonSizes.MEDIUM" :type="buttonTypes.ERROR" @click="handleDeleteDead(result)">
                  {{ buttonText.DELETE }}
                </n-button>
              </div>
              <n-button block :type="buttonTypes.ERROR" @click="handleDeleteBatchDead">
                {{ buttonText.BATCH_DELETE_DEAD }}
              </n-button>
            </div>
            <div v-else-if="!isScanningHealth" class="empty-state">
              <n-empty :description="emptyText.NO_DEAD_LINKS" />
            </div>
          </n-space>
        </n-tab-pane>
      </n-tabs>
    </n-modal>

    <!-- AI 智能整理弹窗 -->
    <n-modal v-model:show="showAiModal" preset="card" :title="modalTitle.AI_SUGGESTIONS" style="width: 95vw; max-width: 500px">
      <n-space vertical>
        <n-alert type="info" :show-icon="false">
          AI 分析发现 {{ aiSuggestions.length }} 条整理建议
        </n-alert>
        <div v-for="(suggestion, index) in aiSuggestions" :key="index" class="ai-suggestion-item">
          <div class="suggestion-header">
            <n-tag :type="tagTypes.WARNING" :size="buttonSizes.SMALL">{{ suggestion.action }}</n-tag>
          </div>
          <div class="suggestion-detail">
            <div v-if="suggestion.bookmark_title">书签: {{ suggestion.bookmark_title }}</div>
            <div v-if="suggestion.folder_name">目标文件夹: {{ suggestion.folder_name }}</div>
            <div v-if="suggestion.reason" class="suggestion-reason">{{ suggestion.reason }}</div>
          </div>
          <n-button :size="buttonSizes.MEDIUM" :type="buttonTypes.PRIMARY" @click="applyAiSuggestion(suggestion)">
            {{ buttonText.APPLY }}
          </n-button>
        </div>
        <n-space justify="end" style="margin-top: 16px;">
          <n-button secondary @click="showAiModal = false">{{ buttonText.CLOSE }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="applyAllSuggestions">{{ buttonText.APPLY_ALL }}</n-button>
        </n-space>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, NIcon, NTabs, NTabPane, NProgress, NAlert, NDivider } from 'naive-ui'
import { useMessage } from 'naive-ui'
import { useBookmark } from '../../toolkit/sitenav/useBookmark'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  TagTypes,
  MessageText,
  EmptyText,
  ConfirmText,
  ModalTitle,
  FormLabel,
  Placeholder,
  TabText,
} from '../constants'

const message = useMessage()
const { 
  bookmarks, 
  loading, 
  fetchBookmarks, 
  addBookmark, 
  updateBookmark, 
  deleteBookmark: deleteBookmarkApi,
  exportBookmarks,
  clearBookmarks,
  aiAnalyze,
  aiApply
} = useBookmark()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const tagTypes = TagTypes
const messageText = MessageText
const emptyText = EmptyText
const confirmText = ConfirmText
const modalTitle = ModalTitle
const formLabel = FormLabel
const placeholder = Placeholder
const tabText = TabText

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
    message.warning(messageText.FILL_BOOKMARK_INFO)
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
      message.success(messageText.UPDATE_BOOKMARK_SUCCESS)
    } else {
      await addBookmark({
        title: editingBookmark.value.title,
        url: editingBookmark.value.url,
        type: 'file',
        parent_id: editingBookmark.value.parent_id || undefined
      })
      message.success(messageText.ADD_BOOKMARK_SUCCESS)
    }
    showAddBookmarkModal.value = false
    editingBookmark.value = { id: null, title: '', url: '', parent_id: null }
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error(messageText.SAVE_BOOKMARK_FAILED + ': ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleDeleteBookmark = async (id: string) => {
  try {
    await deleteBookmarkApi(id)
    message.success(messageText.DELETE_BOOKMARK_SUCCESS)
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error(messageText.DELETE_BOOKMARK_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const saveFolder = async () => {
  if (!newFolder.value.name) {
    message.warning(messageText.FILL_FOLDER_NAME)
    return
  }
  saving.value = true
  try {
    await addBookmark({
      title: newFolder.value.name,
      type: 'folder'
    })
    message.success(messageText.CREATE_FOLDER_SUCCESS)
    showAddFolderModal.value = false
    newFolder.value = { name: '' }
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error(messageText.CREATE_FOLDER_FAILED + ': ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleDeleteFolder = async (id: string) => {
  try {
    await deleteBookmarkApi(id)
    message.success(messageText.DELETE_FOLDER_SUCCESS)
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error(messageText.DELETE_FOLDER_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const handleExport = () => {
  exportBookmarks()
}

const handleClearAll = async () => {
  try {
    await clearBookmarks()
    message.success(messageText.CLEAR_BOOKMARKS_SUCCESS)
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error(messageText.CLEAR_BOOKMARKS_FAILED + ': ' + (e.message || '未知错误'))
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
    
    message.success(messageText.IMPORT_BOOKMARKS_SUCCESS.replace('{count}', count.toString()))
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error(messageText.IMPORT_BOOKMARKS_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const aiLoading = ref(false)
const aiSuggestions = ref<any[]>([])
const showAiModal = ref(false)

const handleAIAnalyze = async () => {
  aiLoading.value = true
  try {
    const result = await aiAnalyze()
    if (result.suggestions && result.suggestions.length > 0) {
      aiSuggestions.value = result.suggestions
      showAiModal.value = true
    } else {
      message.info(messageText.AI_ANALYZE_NO_SUGGESTIONS)
    }
  } catch (e: any) {
    message.error(messageText.AI_ANALYZE_FAILED + ': ' + (e.message || '未知错误'))
  } finally {
    aiLoading.value = false
  }
}

const applyAiSuggestion = async (suggestion: any) => {
  try {
    await aiApply([suggestion])
    message.success(messageText.APPLY_SUGGESTION_SUCCESS)
    await fetchBookmarks(true)
    // 从列表中移除已应用的建议
    aiSuggestions.value = aiSuggestions.value.filter(s => s !== suggestion)
    if (aiSuggestions.value.length === 0) {
      showAiModal.value = false
    }
  } catch (e: any) {
    message.error(messageText.APPLY_SUGGESTION_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const applyAllSuggestions = async () => {
  try {
    await aiApply(aiSuggestions.value)
    message.success(messageText.APPLY_ALL_SUGGESTIONS_SUCCESS)
    await fetchBookmarks(true)
    showAiModal.value = false
    aiSuggestions.value = []
  } catch (e: any) {
    message.error(messageText.APPLY_ALL_SUGGESTIONS_FAILED + ': ' + (e.message || '未知错误'))
  }
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
  message.info(messageText.DUPLICATES_FOUND.replace('{count}', duplicates.value.length.toString()))
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
  message.info(messageText.DEAD_LINKS_FOUND.replace('{count}', deadLinks.length.toString()))
}

const stopScanHealth = () => {
  isScanningHealth.value = false
  message.info(messageText.SCAN_STOPPED)
}

const handleDeleteDead = async (result: any) => {
  try {
    await deleteBookmarkApi(result.bookmark.id)
    message.success(messageText.DELETE_BOOKMARK_SUCCESS)
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error(messageText.DELETE_BOOKMARK_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const handleDeleteBatchDead = async () => {
  try {
    for (const result of healthResults.value) {
      await deleteBookmarkApi(result.bookmark.id)
    }
    message.success(messageText.BATCH_DELETE_SUCCESS.replace('{count}', healthResults.value.length.toString()))
    healthResults.value = []
    await fetchBookmarks(true)
  } catch (e: any) {
    message.error(messageText.BATCH_DELETE_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const handleMergeDuplicate = async (group: any) => {
  try {
    const keep = group.items[0]
    for (let i = 1; i < group.items.length; i++) {
      await deleteBookmarkApi(group.items[i].id)
    }
    message.success(messageText.MERGE_DUPLICATES_SUCCESS)
    await fetchBookmarks(true)
    scanDuplicates()
  } catch (e: any) {
    message.error(messageText.MERGE_DUPLICATES_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const handleDeleteAllInGroup = async (group: any) => {
  try {
    for (const item of group.items) {
      await deleteBookmarkApi(item.id)
    }
    message.success(messageText.DELETE_GROUP_SUCCESS)
    await fetchBookmarks(true)
    scanDuplicates()
  } catch (e: any) {
    message.error(messageText.DELETE_GROUP_FAILED + ': ' + (e.message || '未知错误'))
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
