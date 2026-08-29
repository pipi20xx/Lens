<script setup lang="ts">
/**
 * HDIconPicker — HD-Icons 在线图标库选择器
 *
 * 从后端 /api/toolkit/navigation/hd-icons 获取图标列表，
 * 支持按风格（圆角/圆形/SVG）筛选和关键词搜索。
 * 数据来源: GitHub xushier/HD-Icons
 */
import { ref, computed, watch } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import GlassDialog from '@/components/common/GlassDialog.vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [val: boolean]
  select: [url: string]
}>()

const loading = ref(false)
const searchText = ref('')
const selectedStyle = ref('border-radius')
const iconData = ref<{ name: string; url: string }[]>([])

const styles = [
  { title: '圆角 (Border Radius)', value: 'border-radius' },
  { title: '圆形 (Circle)', value: 'circle' },
  { title: '矢量 (SVG)', value: 'svg' },
]

async function fetchIcons() {
  loading.value = true
  try {
    const data: any = await toolkitApi.getHdIcons()
    iconData.value = data.icons || []
  } catch (e) {
    console.error('Failed to fetch HD-Icons:', e)
  } finally {
    loading.value = false
  }
}

const filteredIcons = computed(() => {
  const styleMatch = iconData.value.filter(item => item.url.includes(`/${selectedStyle.value}/`))
  if (!searchText.value) return styleMatch
  const kw = searchText.value.toLowerCase()
  return styleMatch.filter(item => item.name.toLowerCase().includes(kw))
})

function handleSelect(url: string) {
  emit('select', url)
  emit('update:modelValue', false)
}

function onStyleChange() {
  searchText.value = ''
}

// 弹窗打开时加载数据
watch(() => props.modelValue, (val) => {
  if (val && iconData.value.length === 0) {
    fetchIcons()
  }
})
</script>

<template>
  <GlassDialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :max-width="820"
    icon="mdi-shape-outline"
    title="HD-Icons 图标库"
    cancel-text="关闭"
    :scrollable="true"
  >
    <!-- 工具栏 -->
    <div class="d-flex align-center ga-3 mb-4 flex-wrap">
      <v-select
        v-model="selectedStyle"
        :items="styles"
        item-title="title"
        item-value="value"
        density="compact"
        variant="outlined"
        hide-details
        style="max-width: 220px"
        @update:model-value="onStyleChange"
      />
      <v-text-field
        v-model="searchText"
        density="compact"
        variant="outlined"
        hide-details
        prepend-inner-icon="mdi-magnify"
        placeholder="搜索图标名称 (英文)..."
        style="max-width: 300px"
        clearable
      />
      <span class="text-caption text-medium-emphasis ml-auto">
        已加载 {{ iconData.length }} 个图标
      </span>
    </div>

    <!-- 图标网格 -->
    <div class="icon-grid-wrapper">
      <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-2" />
      <div v-if="!loading && filteredIcons.length === 0" class="text-center pa-8 text-medium-emphasis">
        <v-icon size="48" class="mb-2">mdi-emoticon-sad-outline</v-icon>
        <div>未找到匹配图标</div>
      </div>
      <div v-else class="icon-grid">
        <div
          v-for="item in filteredIcons"
          :key="item.url"
          class="icon-card"
          @click="handleSelect(item.url)"
        >
          <div class="icon-img-box">
            <img :src="item.url" loading="lazy" />
          </div>
          <div class="icon-name">{{ item.name }}</div>
        </div>
      </div>
    </div>

    <template #actions>
      <span class="text-caption text-medium-emphasis mr-auto">
        图标数据来自 GitHub: xushier/HD-Icons
      </span>
    </template>
  </GlassDialog>
</template>

<style scoped>
/* 图标网格 — 由弹窗统一滚动，不设独立滚动条 */
.icon-grid-wrapper {
  min-height: 300px;
  padding: 4px;
}

.icon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 10px;
}

.icon-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 6px;
  border-radius: 10px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  cursor: pointer;
  transition: all 0.2s ease;
}

.icon-card:hover {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.08);
  transform: translateY(-2px);
}

.icon-img-box {
  width: 44px;
  height: 44px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-img-box img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.icon-name {
  font-size: 11px;
  text-align: center;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgb(var(--v-theme-on-surface));
}
</style>
