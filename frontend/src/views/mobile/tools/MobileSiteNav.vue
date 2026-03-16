<template>
  <div class="mobile-site-nav">
    <div class="page-header">
      <h1 class="page-title">{{ PageTitle.SITE_NAV }}</h1>
      <p class="page-desc">{{ ButtonText.QUICK_ACCESS_SITES }}</p>
    </div>

    <n-card class="categories-card" :bordered="false" :title="ButtonText.CATEGORY">
      <n-space vertical>
        <div v-for="category in categories" :key="category.id" class="category-item">
          <div class="category-header" @click="toggleCategory(category.id)">
            <div class="category-name">{{ category.name }}</div>
            <n-space :size="4">
              <n-button :size="buttonSizes.TINY" secondary circle @click.stop="editCategory(category)">
                <template #icon><n-icon :component="EditIcon" /></template>
              </n-button>
              <n-button :size="buttonSizes.TINY" secondary :type="buttonTypes.ERROR" circle @click.stop="handleDeleteCategory(category)">
                <template #icon><n-icon :component="DeleteIcon" /></template>
              </n-button>
              <n-icon :component="isExpanded(category.id) ? ExpandLessIcon : ExpandMoreIcon" />
            </n-space>
          </div>
          <div v-if="isExpanded(category.id)" class="category-sites">
            <div v-for="site in getSitesByCategory(category.id)" :key="site.id" class="site-item" @click="openSite(site)">
              <div class="site-icon">
                <img v-if="site.icon" :src="site.icon" :alt="site.name" />
                <n-icon v-else :component="LinkIcon" />
              </div>
              <div class="site-name">{{ site.name }}</div>
              <n-space :size="4" class="site-actions">
                <n-button :size="buttonSizes.TINY" secondary circle @click.stop="editSite(site)">
                  <template #icon><n-icon :component="EditIcon" /></template>
                </n-button>
                <n-button :size="buttonSizes.TINY" secondary :type="buttonTypes.ERROR" circle @click.stop="handleDeleteSite(site)">
                  <template #icon><n-icon :component="DeleteIcon" /></template>
                </n-button>
              </n-space>
            </div>
            <div v-if="!getSitesByCategory(category.id).length" class="empty-sites">
              {{ MessageText.NO_SITES }}
            </div>
          </div>
        </div>
        <div v-if="categories.length === 0" class="empty-state">
          <n-empty :description="MessageText.NO_CATEGORY" />
        </div>
      </n-space>
    </n-card>

    <n-card class="quick-actions-card" :bordered="false" :title="ButtonText.QUICK_ACTIONS">
      <n-space vertical>
        <n-button block secondary @click="showAddSiteModal = true">
          {{ ButtonText.ADD_SITE }}
        </n-button>
        <n-button block secondary @click="showAddCategoryModal = true">
          {{ ButtonText.ADD_CATEGORY }}
        </n-button>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddSiteModal" preset="card" :title="editingSite ? ModalTitle.EDIT_SITE : ModalTitle.ADD_SITE" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="FormLabel.SITE_NAME">
          <n-input v-model:value="newSite.name" :placeholder="Placeholder.SITE_NAME" />
        </n-form-item>
        <n-form-item :label="FormLabel.SITE_URL">
          <n-input v-model:value="newSite.url" :placeholder="Placeholder.SITE_URL" />
        </n-form-item>
        <n-form-item :label="FormLabel.CATEGORY">
          <n-select v-model:value="newSite.category_id" :options="categoryOptions" />
        </n-form-item>
        <n-form-item :label="FormLabel.ICON_URL">
          <n-input v-model:value="newSite.icon" :placeholder="Placeholder.ICON_URL" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="closeSiteModal">{{ ButtonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveSite" :loading="saving">{{ ButtonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showAddCategoryModal" preset="card" :title="ModalTitle.ADD_CATEGORY" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="FormLabel.CATEGORY_NAME">
          <n-input v-model:value="newCategory.name" :placeholder="Placeholder.CATEGORY_NAME" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="closeCategoryModal">{{ ButtonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveCategory" :loading="saving">{{ ButtonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showEditCategoryModal" preset="card" :title="ModalTitle.EDIT_CATEGORY" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="FormLabel.CATEGORY_NAME">
          <n-input v-model:value="newCategory.name" :placeholder="Placeholder.CATEGORY_NAME" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="closeCategoryModal">{{ ButtonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveCategory" :loading="saving">{{ ButtonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NIcon } from 'naive-ui'
import {
  CreateNew,
  DeleteOutlineOutlined as DeleteIcon,
  EditOutlined as EditIcon,
  ExpandLessOutlined as ExpandLessIcon,
  ExpandMoreOutlined as ExpandMoreIcon,
  LinkOutlined as LinkIcon
} from '@vicons/material'
import { useMessage } from 'naive-ui'
import { useSiteNav } from '../../toolkit/sitenav/useSiteNav'
import {
  ButtonText,
  PageTitle,
  ModalTitle,
  FormLabel,
  Placeholder,
  MessageText,
  ButtonTypes,
  ButtonSizes,
} from '../constants'

const message = useMessage()
const { 
  sites, 
  categories, 
  loading, 
  fetchSites, 
  fetchCategories,
  addSite,
  addCategory,
  updateSite,
  deleteSite,
  updateCategory,
  deleteCategory
} = useSiteNav()

const buttonSizes = ButtonSizes
const buttonTypes = ButtonTypes

const showAddSiteModal = ref(false)
const showAddCategoryModal = ref(false)
const showEditCategoryModal = ref(false)
const saving = ref(false)

const newSite = ref({
  name: '',
  url: '',
  category_id: null as number | null,
  icon: ''
})

const newCategory = ref({
  name: ''
})

const editingSite = ref<any>(null)
const editingCategory = ref<any>(null)

const expandedCategories = ref<Set<number>>(new Set())

const categoryOptions = computed(() => {
  return categories.value.map(c => ({ label: c.name, value: c.id }))
})

const getSitesByCategory = (categoryId: number) => {
  return sites.value.filter(s => s.category_id === categoryId)
}

const toggleCategory = (categoryId: number) => {
  if (expandedCategories.value.has(categoryId)) {
    expandedCategories.value.delete(categoryId)
  } else {
    expandedCategories.value.add(categoryId)
  }
}

const isExpanded = (categoryId: number) => {
  return expandedCategories.value.has(categoryId)
}

const openSite = (site: any) => {
  window.open(site.url, '_blank')
}

const closeSiteModal = () => {
  showAddSiteModal.value = false
  editingSite.value = null
  newSite.value = { name: '', url: '', category_id: null, icon: '' }
}

const closeCategoryModal = () => {
  showAddCategoryModal.value = false
  showEditCategoryModal.value = false
  editingCategory.value = null
  newCategory.value = { name: '' }
}

const editSite = (site: any) => {
  editingSite.value = site
  newSite.value = {
    name: site.title || site.name,
    url: site.url,
    category_id: site.category_id,
    icon: site.icon || ''
  }
  showAddSiteModal.value = true
}

const handleDeleteSite = async (site: any) => {
  try {
    await deleteSite(site.id)
    message.success(MessageText.SITE_DELETED)
    await fetchSites()
  } catch (e: any) {
    message.error(MessageText.DELETE_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const editCategory = (category: any) => {
  editingCategory.value = category
  newCategory.value = {
    name: category.name
  }
  showEditCategoryModal.value = true
}

const handleDeleteCategory = async (category: any) => {
  try {
    await deleteCategory(category.id)
    message.success(MessageText.CATEGORY_DELETED)
    await fetchCategories()
    await fetchSites()
  } catch (e: any) {
    message.error(MessageText.DELETE_FAILED + ': ' + (e.message || '未知错误'))
  }
}

const saveSite = async () => {
  if (!newSite.value.name || !newSite.value.url) {
    message.warning(MessageText.FILL_SITE_INFO)
    return
  }
  saving.value = true
  try {
    if (editingSite.value) {
      await updateSite(editingSite.value.id, {
        title: newSite.value.name,
        url: newSite.value.url,
        category_id: newSite.value.category_id || undefined,
        icon: newSite.value.icon || undefined
      })
      message.success(MessageText.SITE_UPDATED)
    } else {
      await addSite({
        title: newSite.value.name,
        url: newSite.value.url,
        category_id: newSite.value.category_id || undefined,
        icon: newSite.value.icon || undefined
      })
      message.success(MessageText.SITE_ADDED)
    }
    showAddSiteModal.value = false
    editingSite.value = null
    newSite.value = { name: '', url: '', category_id: null, icon: '' }
    await fetchSites()
  } catch (e: any) {
    message.error(MessageText.SAVE_FAILED + ': ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const saveCategory = async () => {
  if (!newCategory.value.name) {
    message.warning(MessageText.FILL_CATEGORY_NAME)
    return
  }
  saving.value = true
  try {
    if (editingCategory.value) {
      await updateCategory(editingCategory.value.id, {
        name: newCategory.value.name
      })
      message.success(MessageText.CATEGORY_UPDATED)
    } else {
      await addCategory({
        name: newCategory.value.name
      })
      message.success(MessageText.CATEGORY_ADDED)
    }
    showAddCategoryModal.value = false
    showEditCategoryModal.value = false
    editingCategory.value = null
    newCategory.value = { name: '' }
    await fetchCategories()
  } catch (e: any) {
    message.error(MessageText.SAVE_FAILED + ': ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await fetchCategories()
  await fetchSites()
  // 默认展开第一个分类
  if (categories.value.length > 0) {
    expandedCategories.value.add(categories.value[0].id)
  }
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
  position: relative;
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
  flex: 1;
}

.site-actions {
  flex-shrink: 0;
}

.empty-sites,
.empty-state {
  padding: 24px 0;
  text-align: center;
  color: var(--text-color);
  opacity: 0.6;
}
</style>
