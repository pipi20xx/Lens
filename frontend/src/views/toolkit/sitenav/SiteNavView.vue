<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { navigationApi } from '@/api/navigation'
import { useNotification } from '@/composables'

const { success, error: showError } = useNotification()

const sites = ref<any[]>([])
const categories = ref<any[]>([])
const loading = ref(false)
const searchQuery = ref('')
const selectedCategory = ref<string | null>(null)

const filteredSites = computed(() => {
  let list = sites.value
  if (selectedCategory.value) {
    list = list.filter(s => s.category_id === selectedCategory.value || s.category_name === selectedCategory.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(s => s.name?.toLowerCase().includes(q) || s.url?.toLowerCase().includes(q))
  }
  return list
})

async function loadAll() {
  try {
    loading.value = true
    const [sitesData, catsData] = await Promise.all([navigationApi.getSites(), navigationApi.getCategories()])
    sites.value = Array.isArray(sitesData) ? sitesData : []
    categories.value = Array.isArray(catsData) ? catsData : []
  } catch {
    showError('加载站点数据失败')
  } finally {
    loading.value = false
  }
}

const showSiteDialog = ref(false)
const editingSiteId = ref<string | null>(null)
const siteForm = ref<any>({ name: '', url: '', description: '', icon: '', category_id: '', sort_order: 0 })

function openAddSite() {
  editingSiteId.value = null
  siteForm.value = { name: '', url: '', description: '', icon: '', category_id: selectedCategory.value || '', sort_order: 0 }
  showSiteDialog.value = true
}

function openEditSite(site: any) {
  editingSiteId.value = site.id
  siteForm.value = { ...site }
  showSiteDialog.value = true
}

async function saveSite() {
  try {
    if (editingSiteId.value) { await navigationApi.updateSite(editingSiteId.value, siteForm.value) }
    else { await navigationApi.createSite(siteForm.value) }
    success('站点已保存')
    showSiteDialog.value = false
    loadAll()
  } catch { showError('保存失败') }
}

async function deleteSite(id: string) {
  try { await navigationApi.deleteSite(id); success('已删除'); loadAll() }
  catch { showError('删除失败') }
}

const showCategoryDialog = ref(false)
const editingCategoryId = ref<string | null>(null)
const categoryForm = ref<any>({ name: '', icon: '', sort_order: 0, description: '' })

function openAddCategory() {
  editingCategoryId.value = null
  categoryForm.value = { name: '', icon: '', sort_order: 0, description: '' }
  showCategoryDialog.value = true
}

function openEditCategory(cat: any) {
  editingCategoryId.value = cat.id
  categoryForm.value = { ...cat }
  showCategoryDialog.value = true
}

async function saveCategory() {
  try {
    if (editingCategoryId.value) { await navigationApi.updateCategory(editingCategoryId.value, categoryForm.value) }
    else { await navigationApi.createCategory(categoryForm.value) }
    success('分类已保存')
    showCategoryDialog.value = false
    loadAll()
  } catch { showError('保存失败') }
}

async function deleteCategory(id: string) {
  try { await navigationApi.deleteCategory(id); success('已删除'); loadAll() }
  catch { showError('删除失败') }
}

onMounted(loadAll)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-compass-outline</v-icon>
      站点导航
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">自定义站点导航页，按分类管理常用服务入口，支持图标与描述配置。</p>

    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <div class="d-flex align-center pa-4 ga-3 flex-wrap">
        <v-text-field v-model="searchQuery" prepend-inner-icon="mdi-magnify" placeholder="搜索站点..."
          variant="outlined" density="compact" hide-details clearable style="max-width:260px" />
        <v-btn prepend-icon="mdi-plus" variant="tonal" color="primary" size="small" @click="openAddSite">添加站点</v-btn>
        <v-btn prepend-icon="mdi-folder-plus-outline" variant="tonal" color="primary" size="small" @click="openAddCategory">添加分类</v-btn>
        <v-spacer />
        <v-btn variant="tonal" color="info" size="small" @click="loadAll" :loading="loading" prepend-icon="mdi-refresh">刷新</v-btn>
      </div>
    </v-card>

    <div class="d-flex flex-wrap ga-2 mb-4">
      <v-chip :variant="!selectedCategory ? 'flat' : 'tonal'" color="primary" @click="selectedCategory = null" style="cursor:pointer">
        全部 ({{ sites.length }})
      </v-chip>
      <v-chip v-for="cat in categories" :key="cat.id"
        :variant="selectedCategory === cat.id ? 'flat' : 'tonal'" color="primary"
        @click="selectedCategory = selectedCategory === cat.id ? null : cat.id" style="cursor:pointer">
        <v-icon start size="16">{{ cat.icon || 'mdi-folder-outline' }}</v-icon>
        {{ cat.name }}
        <v-btn icon size="x-small" variant="text" class="ml-1" @click.stop="openEditCategory(cat)"><v-icon size="12">mdi-pencil</v-icon></v-btn>
        <v-btn icon size="x-small" variant="text" color="error" @click.stop="deleteCategory(cat.id)"><v-icon size="12">mdi-close</v-icon></v-btn>
      </v-chip>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-row>
      <v-col v-for="site in filteredSites" :key="site.id" cols="6" sm="4" md="3" lg="2">
        <v-card class="liquid-glass-card text-center" rounded="xl" :href="site.url" target="_blank" link>
          <v-card-text class="pa-4">
            <v-avatar :color="site.icon ? 'transparent' : 'primary'" variant="tonal" size="56" rounded="xl" class="mb-3">
              <v-img v-if="site.icon" :src="site.icon" />
              <v-icon v-else icon="mdi-web" size="28" />
            </v-avatar>
            <div class="text-subtitle-2 font-weight-bold text-truncate">{{ site.name }}</div>
            <div class="text-caption text-medium-emphasis text-truncate" v-if="site.description">{{ site.description }}</div>
          </v-card-text>
          <v-divider />
          <div class="d-flex justify-center ga-1 pa-2">
            <v-btn size="small" variant="text" icon="mdi-pencil" @click.prevent="openEditSite(site)" />
            <v-btn size="small" variant="text" icon="mdi-delete-outline" color="error" @click.prevent="deleteSite(site.id)" />
          </div>
        </v-card>
      </v-col>
    </v-row>

    <div v-if="!loading && filteredSites.length === 0" class="text-center py-12 text-medium-emphasis">
      <v-icon size="64" color="grey" class="mb-4">mdi-compass-outline</v-icon>
      <div>暂无站点</div>
    </div>

    <v-dialog v-model="showSiteDialog" max-width="500">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4"><v-icon start>mdi-web</v-icon>{{ editingSiteId ? '编辑站点' : '添加站点' }}</v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-text-field v-model="siteForm.name" label="站点名称" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="siteForm.url" label="URL" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="siteForm.icon" label="图标 URL" variant="outlined" density="compact" hint="留空自动获取 favicon" persistent-hint class="mb-3" />
          <v-text-field v-model="siteForm.description" label="描述" variant="outlined" density="compact" class="mb-3" />
          <v-select v-model="siteForm.category_id" :items="categories.map(c => ({ title: c.name, value: c.id }))" label="分类" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="siteForm.sort_order" label="排序" type="number" variant="outlined" density="compact" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showSiteDialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveSite">保存</v-btn>
        </div>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showCategoryDialog" max-width="400">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4"><v-icon start>mdi-folder-outline</v-icon>{{ editingCategoryId ? '编辑分类' : '添加分类' }}</v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-text-field v-model="categoryForm.name" label="分类名称" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="categoryForm.icon" label="图标" variant="outlined" density="compact" hint="如 mdi-folder-outline" persistent-hint class="mb-3" />
          <v-text-field v-model="categoryForm.sort_order" label="排序" type="number" variant="outlined" density="compact" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showCategoryDialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveCategory">保存</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>
