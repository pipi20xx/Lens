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
        <n-button block type="primary" @click="showAddBookmarkModal = true">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          添加书签
        </n-button>
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
              <n-popconfirm @positive-click="deleteBookmark(bookmark.id)" positive-text="确认删除" negative-text="取消">
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
            <n-button size="small" secondary type="error" @click="deleteFolder(folder.id)">
              删除
            </n-button>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, NIcon } from 'naive-ui'
import { AddOutlined as AddIcon, SearchOutlined as SearchIcon, CreateNewFolderOutlined as FolderAddIcon } from '@vicons/material'
import { useMessage } from 'naive-ui'

const message = useMessage()
const bookmarks = ref<any[]>([])
const folders = ref<any[]>([])
const searchQuery = ref('')
const showAddBookmarkModal = ref(false)
const showAddFolderModal = ref(false)
const saving = ref(false)

const editingBookmark = ref({
  id: null,
  title: '',
  url: '',
  folder: ''
})

const newFolder = ref({
  name: ''
})

const filteredBookmarks = computed(() => {
  if (!searchQuery.value) return bookmarks.value
  const query = searchQuery.value.toLowerCase()
  return bookmarks.value.filter(b => 
    b.title.toLowerCase().includes(query) || 
    b.url.toLowerCase().includes(query)
  )
})

const folderOptions = computed(() => {
  return folders.value.map(f => ({ label: f.name, value: f.name }))
})

const openBookmark = (bookmark: any) => {
  window.open(bookmark.url, '_blank')
}

const editBookmark = (bookmark: any) => {
  editingBookmark.value = { ...bookmark }
  showAddBookmarkModal.value = true
}

const saveBookmark = () => {
  if (!editingBookmark.value.title || !editingBookmark.value.url) {
    message.warning('请填写完整的书签信息')
    return
  }
  saving.value = true
  setTimeout(() => {
    if (editingBookmark.value.id) {
      const index = bookmarks.value.findIndex(b => b.id === editingBookmark.value.id)
      if (index !== -1) {
        bookmarks.value[index] = { ...editingBookmark.value }
      }
    } else {
      bookmarks.value.push({
        id: Date.now(),
        ...editingBookmark.value
      })
    }
    message.success('书签保存成功')
    showAddBookmarkModal.value = false
    editingBookmark.value = { id: null, title: '', url: '', folder: '' }
    saving.value = false
  }, 500)
}

const deleteBookmark = (id: number) => {
  bookmarks.value = bookmarks.value.filter(b => b.id !== id)
  message.success('书签已删除')
}

const saveFolder = () => {
  if (!newFolder.value.name) {
    message.warning('请填写文件夹名称')
    return
  }
  saving.value = true
  setTimeout(() => {
    folders.value.push({
      id: Date.now(),
      name: newFolder.value.name,
      count: 0
    })
    message.success('文件夹创建成功')
    showAddFolderModal.value = false
    newFolder.value = { name: '' }
    saving.value = false
  }, 500)
}

const deleteFolder = (id: number) => {
  folders.value = folders.value.filter(f => f.id !== id)
  message.success('文件夹已删除')
}

bookmarks.value = [
  { id: 1, title: 'Google', url: 'https://www.google.com', folder: '常用' },
  { id: 2, title: 'GitHub', url: 'https://github.com', folder: '开发' },
  { id: 3, title: 'Stack Overflow', url: 'https://stackoverflow.com', folder: '开发' }
]

folders.value = [
  { id: 1, name: '常用', count: 1 },
  { id: 2, name: '开发', count: 2 }
]
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
</style>
