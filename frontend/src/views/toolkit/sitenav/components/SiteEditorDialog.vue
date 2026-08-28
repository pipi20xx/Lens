<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Category, SiteItem } from '../composables/useSiteNav'
import GlassDialog from '@/components/common/GlassDialog.vue'
import HDIconPicker from './HDIconPicker.vue'
import { navigationApi } from '@/api/navigation'
import { useNotification } from '@/composables'

const props = defineProps<{
  modelValue: boolean
  editingSite: Partial<SiteItem> | null
  categories: Category[]
  fetchingIcon: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [val: boolean]
  save: []
  fetchIcon: []
  'update:editingSite': [val: Partial<SiteItem>]
}>()

const { success, error: showError } = useNotification()

// 本地表单副本
const form = ref<any>({})

watch(() => props.editingSite, (val) => {
  if (val) form.value = { ...val }
}, { immediate: true, deep: true })

function updateField(field: string, value: any) {
  form.value[field] = value
  emit('update:editingSite', { ...form.value })
}

const isEditing = ref(false)
watch(() => props.editingSite, (val) => {
  isEditing.value = !!val?.id
}, { immediate: true })

// ========== HD-Icons 图标库 ==========
const showHDIconPicker = ref(false)

function handleHDIconSelect(url: string) {
  updateField('icon', url)
}

// ========== 本地图标上传 ==========
const uploadingIcon = ref(false)

async function handleUploadIcon(file: File) {
  if (!file) return
  uploadingIcon.value = true
  try {
    const data: any = await navigationApi.uploadIcon(file)
    if (data?.icon) {
      updateField('icon', data.icon)
      success('图标上传成功')
    }
  } catch (e: any) {
    showError(e?.message || '图标上传失败')
  } finally {
    uploadingIcon.value = false
  }
}

function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (target.files && target.files[0]) {
    handleUploadIcon(target.files[0])
    target.value = '' // 重置，允许重复上传同一文件
  }
}

// ========== Emoji 判断 ==========
function isEmoji(str: string) {
  if (!str) return false
  if (str.includes('/') || str.includes('.')) return false
  return /\p{Emoji}/u.test(str) && str.length <= 4
}

// ========== 文件输入 ref ==========
const fileInput = ref<HTMLInputElement | null>(null)
</script>

<template>
  <GlassDialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :max-width="520"
    :icon="isEditing ? 'mdi-pencil' : 'mdi-plus'"
    :title="isEditing ? '编辑站点' : '添加站点'"
  >
    <v-text-field
      :model-value="form.url"
      @update:model-value="updateField('url', $event)"
      label="访问链接" variant="outlined" density="compact" class="mb-3"
      placeholder="https://..."
    >
      <template #append>
        <v-btn size="small" variant="tonal" color="info" :loading="fetchingIcon" height="40" @click="emit('fetchIcon')">
          获取图标
        </v-btn>
      </template>
    </v-text-field>
    <v-text-field
      :model-value="form.title"
      @update:model-value="updateField('title', $event)"
      label="站点名称" variant="outlined" density="compact" class="mb-3"
    />
    <v-select
      :model-value="form.category_id"
      @update:model-value="updateField('category_id', $event)"
      :items="categories.map(c => ({ title: c.name, value: c.id }))"
      label="所属分类" variant="outlined" density="compact" class="mb-3"
    />

    <!-- 图标地址 + 预览 + 上传 + 图标库 -->
    <div class="mb-3">
      <div class="d-flex align-center ga-2 mb-2">
        <v-text-field
          :model-value="form.icon"
          @update:model-value="updateField('icon', $event)"
          label="图标 URL 或 Emoji" variant="outlined" density="compact" hide-details
          placeholder="可填图片地址或 emoji 表情"
        />
        <!-- 图标预览 -->
        <div class="icon-preview">
          <template v-if="form.icon">
            <span v-if="isEmoji(form.icon)" class="preview-emoji">{{ form.icon }}</span>
            <img v-else :src="form.icon" class="preview-img" />
          </template>
          <v-icon v-else size="20" color="grey">mdi-web</v-icon>
        </div>
      </div>

      <!-- 上传 + 图标库按钮 -->
      <div class="d-flex ga-2">
        <v-btn
          variant="tonal" color="info" size="small" prepend-icon="mdi-upload"
          :loading="uploadingIcon"
          @click="fileInput?.click()"
        >
          上传本地图标
        </v-btn>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display: none"
          @change="onFileChange"
        />
        <v-btn
          variant="tonal" color="primary" size="small" prepend-icon="mdi-shape-outline"
          @click="showHDIconPicker = true"
        >
          HD-Icons 图标库
        </v-btn>
      </div>
    </div>

    <v-text-field
      :model-value="form.description"
      @update:model-value="updateField('description', $event)"
      label="站点描述" variant="outlined" density="compact" class="mb-3"
    />
    <v-text-field
      :model-value="form.order"
      @update:model-value="updateField('order', $event)"
      label="排序" type="number" variant="outlined" density="compact"
    />
    <template #actions>
      <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="emit('save')">保存</v-btn>
    </template>
  </GlassDialog>

  <!-- HD-Icons 图标库选择器 -->
  <HDIconPicker
    v-model="showHDIconPicker"
    @select="handleHDIconSelect"
  />
</template>

<style scoped>
.icon-preview {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 10px;
  background: rgba(var(--v-theme-on-surface), 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.preview-emoji {
  font-size: 22px;
  line-height: 1;
}
</style>
