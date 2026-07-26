<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { bookmarksApi } from '@/api/bookmarks'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const bookmarks = ref<any[]>([])
const loading = ref(false)
const searchQuery = ref('')

async function loadBookmarks() {
  try {
    loading.value = true
    const data = await bookmarksApi.getBookmarks()
    bookmarks.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载书签失败')
  } finally {
    loading.value = false
  }
}

const showBookmarkDialog = ref(false)
const editingBookmarkId = ref<string | null>(null)
const bookmarkForm = ref<any>({ title: '', url: '', description: '', category: '', icon: '' })

function openAddBookmark() {
  editingBookmarkId.value = null
  bookmarkForm.value = { title: '', url: '', description: '', category: '', icon: '' }
  showBookmarkDialog.value = true
}

function openEditBookmark(bm: any) {
  editingBookmarkId.value = bm.id
  bookmarkForm.value = { ...bm }
  showBookmarkDialog.value = true
}

async function saveBookmark() {
  try {
    if (editingBookmarkId.value) { await bookmarksApi.updateBookmark(editingBookmarkId.value, bookmarkForm.value) }
    else { await bookmarksApi.createBookmark(bookmarkForm.value) }
    success('书签已保存')
    showBookmarkDialog.value = false
    loadBookmarks()
  } catch { showError('保存失败') }
}

async function deleteBookmark(id: string) {
  const ok = await confirm({ title: '删除书签', content: '确定要删除此书签吗？', confirmColor: 'error' })
  if (!ok) return
  try { await bookmarksApi.deleteBookmark(id); success('已删除'); loadBookmarks() }
  catch { showError('删除失败') }
}

onMounted(loadBookmarks)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-bookmark-outline</v-icon>
      书签管理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">管理浏览器书签与常用链接，支持分类与搜索。</p>

    <div class="d-flex ga-3 mb-4">
      <v-text-field v-model="searchQuery" prepend-inner-icon="mdi-magnify" placeholder="搜索书签..."
        variant="outlined" density="compact" hide-details clearable style="max-width:260px" />
      <v-btn prepend-icon="mdi-plus" variant="tonal" color="primary" size="small" @click="openAddBookmark">添加书签</v-btn>
      <v-spacer />
      <v-btn variant="tonal" color="info" size="small" @click="loadBookmarks" :loading="loading" prepend-icon="mdi-refresh">刷新</v-btn>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-card class="liquid-glass-card" rounded="xl">
      <v-table class="bg-transparent">
        <thead><tr><th>标题</th><th>URL</th><th>分类</th><th class="text-right">操作</th></tr></thead>
        <tbody>
          <tr v-if="!loading && !bookmarks.length"><td colspan="4" class="text-center py-8 text-medium-emphasis">暂无书签</td></tr>
          <tr v-for="bm in bookmarks.filter(b => !searchQuery || b.title?.toLowerCase().includes(searchQuery.toLowerCase()))" :key="bm.id">
            <td class="font-weight-medium">{{ bm.title }}</td>
            <td><a :href="bm.url" target="_blank" class="text-decoration-none font-mono" style="font-size:12px">{{ bm.url }}</a></td>
            <td><v-chip v-if="bm.category" size="small" variant="tonal">{{ bm.category }}</v-chip><span v-else class="text-medium-emphasis">-</span></td>
            <td class="text-right">
              <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="openEditBookmark(bm)" class="mr-1">编辑</v-btn>
              <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" @click="deleteBookmark(bm.id)">删除</v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <v-dialog v-model="showBookmarkDialog" max-width="500" scrollable>
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4"><v-icon start>mdi-bookmark-outline</v-icon>{{ editingBookmarkId ? '编辑书签' : '添加书签' }}</v-card-title>
        <v-divider />
        <v-card-text class="pa-4" style="max-height:65vh;overflow-y:auto">
          <v-text-field v-model="bookmarkForm.title" label="标题" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="bookmarkForm.url" label="URL" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="bookmarkForm.description" label="描述" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="bookmarkForm.category" label="分类" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="bookmarkForm.icon" label="图标 URL" variant="outlined" density="compact" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showBookmarkDialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveBookmark">保存</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>
