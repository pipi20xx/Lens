<template>
  <div class="mobile-site-nav">
    <div class="page-header">
      <h1 class="page-title">站点导航</h1>
      <p class="page-desc">快速访问常用站点</p>
    </div>

    <n-card class="categories-card" :bordered="false" title="分类">
      <n-space vertical>
        <div v-for="category in categories" :key="category.id" class="category-item">
          <div class="category-header" @click="toggleCategory(category.id)">
            <div class="category-name">{{ category.name }}</div>
            <n-icon :component="category.expanded ? ExpandLessIcon : ExpandMoreIcon" />
          </div>
          <div v-if="category.expanded" class="category-sites">
            <div v-for="site in getSitesByCategory(category.id)" :key="site.id" class="site-item" @click="openSite(site)">
              <div class="site-icon">
                <img v-if="site.icon" :src="site.icon" :alt="site.name" />
                <n-icon v-else :component="LinkIcon" />
              </div>
              <div class="site-name">{{ site.name }}</div>
            </div>
            <div v-if="!getSitesByCategory(category.id).length" class="empty-sites">
              暂无站点
            </div>
          </div>
        </div>
        <div v-if="categories.length === 0" class="empty-state">
          <n-empty description="暂无分类" />
        </div>
      </n-space>
    </n-card>

    <n-card class="quick-actions-card" :bordered="false" title="快捷操作">
      <n-space vertical>
        <n-button block secondary @click="showAddSiteModal = true">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          添加站点
        </n-button>
        <n-button block secondary @click="showAddCategoryModal = true">
          <template #icon><n-icon><FolderAddIcon /></n-icon></template>
          添加分类
        </n-button>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddSiteModal" preset="card" title="添加站点" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="站点名称">
          <n-input v-model:value="newSite.name" placeholder="站点名称" />
        </n-form-item>
        <n-form-item label="站点 URL">
          <n-input v-model:value="newSite.url" placeholder="https://example.com" />
        </n-form-item>
        <n-form-item label="分类">
          <n-select v-model:value="newSite.category_id" :options="categoryOptions" />
        </n-form-item>
        <n-form-item label="图标 URL">
          <n-input v-model:value="newSite.icon" placeholder="https://example.com/icon.png" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddSiteModal = false">取消</n-button>
          <n-button type="primary" @click="saveSite" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showAddCategoryModal" preset="card" title="添加分类" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="分类名称">
          <n-input v-model:value="newCategory.name" placeholder="分类名称" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddCategoryModal = false">取消</n-button>
          <n-button type="primary" @click="saveCategory" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NIcon } from 'naive-ui'
import { AddOutlined as AddIcon, CreateNewFolderOutlined as FolderAddIcon, LinkOutlined as LinkIcon, ExpandLessOutlined as ExpandLessIcon, ExpandMoreOutlined as ExpandMoreIcon } from '@vicons/material'
import { useMessage } from 'naive-ui'

const message = useMessage()
const categories = ref<any[]>([])
const sites = ref<any[]>([])
const showAddSiteModal = ref(false)
const showAddCategoryModal = ref(false)
const saving = ref(false)

const newSite = ref({
  name: '',
  url: '',
  category_id: null,
  icon: ''
})

const newCategory = ref({
  name: ''
})

const categoryOptions = computed(() => {
  return categories.value.map(c => ({ label: c.name, value: c.id }))
})

const getSitesByCategory = (categoryId: number) => {
  return sites.value.filter(s => s.category_id === categoryId)
}

const toggleCategory = (categoryId: number) => {
  const category = categories.value.find(c => c.id === categoryId)
  if (category) {
    category.expanded = !category.expanded
  }
}

const openSite = (site: any) => {
  window.open(site.url, '_blank')
}

const saveSite = () => {
  if (!newSite.value.name || !newSite.value.url) {
    message.warning('请填写完整的站点信息')
    return
  }
  saving.value = true
  setTimeout(() => {
    sites.value.push({
      id: Date.now(),
      ...newSite.value
    })
    message.success('站点添加成功')
    showAddSiteModal.value = false
    newSite.value = { name: '', url: '', category_id: null, icon: '' }
    saving.value = false
  }, 500)
}

const saveCategory = () => {
  if (!newCategory.value.name) {
    message.warning('请填写分类名称')
    return
  }
  saving.value = true
  setTimeout(() => {
    categories.value.push({
      id: Date.now(),
      name: newCategory.value.name,
      expanded: false
    })
    message.success('分类添加成功')
    showAddCategoryModal.value = false
    newCategory.value = { name: '' }
    saving.value = false
  }, 500)
}

onMounted(() => {
  categories.value = [
    { id: 1, name: '常用工具', expanded: true },
    { id: 2, name: '娱乐', expanded: false },
    { id: 3, name: '工作', expanded: false }
  ]
  sites.value = [
    { id: 1, name: 'Google', url: 'https://www.google.com', category_id: 1, icon: '' },
    { id: 2, name: 'GitHub', url: 'https://github.com', category_id: 1, icon: '' }
  ]
})
</script>

<style scoped>
.mobile-site-nav {
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

.categories-card,
.quick-actions-card {
  margin-bottom: 12px;
}

.category-item {
  margin-bottom: 8px;
}

.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
  cursor: pointer;
}

.category-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.category-sites {
  margin-top: 8px;
  padding-left: 12px;
}

.site-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: var(--app-bg-color);
  border-radius: 8px;
  margin-bottom: 6px;
  cursor: pointer;
}

.site-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: var(--card-color);
}

.site-icon img {
  width: 24px;
  height: 24px;
  border-radius: 4px;
}

.site-name {
  font-size: 14px;
  color: var(--text-color);
}

.empty-sites,
.empty-state {
  padding: 24px 0;
  text-align: center;
  color: var(--text-color);
  opacity: 0.6;
}
</style>
