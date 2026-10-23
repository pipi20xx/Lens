<script setup lang="ts">
/**
 * 目录选择器：给「仓库根目录」和「克隆落地目录」挑文件夹用。
 * 只列子目录，隐藏点目录；顺手标出哪些目录本身就是 git 仓库。
 */
import { computed, ref, watch } from 'vue'
import GlassDialog from '@/components/common/GlassDialog.vue'
import { repoManagerApi } from '@/api/repoManager'

interface BrowseEntry {
  name: string
  path: string
  is_git: boolean
  in_roots: boolean
}

const props = defineProps<{
  modelValue: boolean
  initialPath?: string
  title?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'picked', path: string): void
}>()

const show = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val),
})

const loading = ref(false)
const current = ref('')
const parent = ref('')
const entries = ref<BrowseEntry[]>([])
const shortcuts = ref<{ label: string; path: string }[]>([])
const pathInput = ref('')
const error = ref('')
const isGit = ref(false)

async function load(path: string) {
  loading.value = true
  error.value = ''
  try {
    const res = await repoManagerApi.browse(path || '')
    current.value = res.path
    pathInput.value = res.path
    parent.value = res.parent
    entries.value = res.entries || []
    shortcuts.value = res.shortcuts || []
    isGit.value = !!res.is_git
  } catch (e: any) {
    error.value = e.message || '读取目录失败'
  } finally {
    loading.value = false
  }
}

function pick(path: string) {
  emit('picked', path)
  show.value = false
}

watch(show, (visible) => {
  if (visible) load(props.initialPath || '')
})
</script>

<template>
  <GlassDialog
    v-model="show"
    :max-width="720"
    :title="title || '选择目录'"
    icon="mdi-folder-search-outline"
  >
    <!-- 快捷入口 -->
    <div v-if="shortcuts.length" class="d-flex flex-wrap ga-2 mb-4">
      <v-chip
        v-for="item in shortcuts"
        :key="item.path"
        size="small"
        variant="tonal"
        :color="item.path === current ? 'primary' : undefined"
        @click="load(item.path)"
      >
        {{ item.label }}
      </v-chip>
    </div>

    <!-- 路径栏 -->
    <div class="d-flex ga-3 align-center mb-4">
      <v-btn
        size="small"
        variant="tonal"
        color="info"
        icon="mdi-arrow-up"
        :disabled="!parent"
        title="上一级"
        @click="load(parent)"
      />
      <v-text-field
        v-model="pathInput"
        density="compact"
        variant="outlined"
        hide-details
        placeholder="/vol1/1000/NVME"
        @keyup.enter="load(pathInput)"
      />
      <v-btn size="small" variant="tonal" color="primary" @click="load(pathInput)">前往</v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-3">
      {{ error }}
    </v-alert>

    <v-progress-linear v-if="loading" indeterminate class="mb-2" />

    <v-list density="compact" class="dir-list">
      <v-list-item v-if="!loading && !entries.length">
        <v-list-item-title class="text-caption">
          该目录下没有子目录（可以直接选择此目录）
        </v-list-item-title>
      </v-list-item>
      <v-list-item v-for="entry in entries" :key="entry.path" @click="load(entry.path)">
        <template #prepend>
          <v-icon :color="entry.is_git ? 'primary' : undefined">
            {{ entry.is_git ? 'mdi-folder-git-outline' : 'mdi-folder-outline' }}
          </v-icon>
        </template>
        <v-list-item-title class="d-flex align-center ga-2">
          <span class="text-truncate">{{ entry.name }}</span>
          <v-chip v-if="entry.is_git" size="x-small" color="primary" variant="tonal">
            git 仓库
          </v-chip>
        </v-list-item-title>
        <template #append>
          <v-icon size="16">mdi-chevron-right</v-icon>
        </template>
      </v-list-item>
    </v-list>

    <div class="text-caption current-path mt-3">
      {{ current }}
      <v-chip v-if="isGit" size="x-small" color="primary" variant="tonal" class="ml-1">
        本身是 git 仓库
      </v-chip>
    </div>

    <template #actions>
      <v-btn color="primary" variant="tonal" :disabled="!current" @click="pick(current)">
        选择此目录
      </v-btn>
    </template>
  </GlassDialog>
</template>

<style scoped>
.dir-list {
  max-height: 42vh;
  overflow: auto;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
.current-path {
  opacity: 0.7;
  word-break: break-all;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}
</style>
