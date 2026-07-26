<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Category, SiteItem } from '../composables/useSiteNav'
import GlassDialog from '@/components/common/GlassDialog.vue'

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
        <v-btn size="x-small" variant="tonal" color="info" :loading="fetchingIcon" @click="emit('fetchIcon')">
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
    <v-text-field
      :model-value="form.icon"
      @update:model-value="updateField('icon', $event)"
      label="图标 URL 或 Emoji" variant="outlined" density="compact"
      hint="可填图片地址或 emoji 表情" persistent-hint class="mb-3"
    />
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
      <v-btn color="primary" variant="flat" @click="emit('save')">保存</v-btn>
    </template>
  </GlassDialog>
</template>
