<script setup lang="ts">
/**
 * 仓库选择下拉（仓库管理页 / 文件浏览页共用）。
 * 展示分支、干净/有改动/不可用状态，以及领先/落后提交数。
 */
import { computed } from 'vue'
import type { RepoSummary } from '@/api/repoManager'

const props = defineProps<{
  modelValue: string
  repos: RepoSummary[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

interface RepoOption {
  path: string
  name: string
  subtitle: string
  color: string
  ahead: number
  behind: number
}

const options = computed<RepoOption[]>(() =>
  props.repos.map((repo) => ({
    path: repo.path,
    name: repo.name,
    subtitle: repo.ok ? repo.branch : repo.error || '不可用',
    color: !repo.ok ? 'error' : repo.dirty ? 'warning' : 'success',
    ahead: repo.ahead,
    behind: repo.behind,
  }))
)

const value = computed({
  get: () => props.modelValue,
  set: (val: string) => emit('update:modelValue', val),
})

/** 兼容取值：不同版本可能给 ListItem 包装（.raw），也可能直接给裸数据 */
function opt(item: any): RepoOption {
  return (item?.raw ?? item ?? {}) as RepoOption
}

function filterRepo(_title: string, query: string, item: any): boolean {
  const q = (query || '').trim().toLowerCase()
  if (!q) return true
  const raw = item?.raw ?? item ?? {}
  return (
    String(raw.name || '').toLowerCase().includes(q) ||
    String(raw.path || '').toLowerCase().includes(q)
  )
}
</script>

<template>
  <v-autocomplete
    v-model="value"
    :items="options"
    item-title="name"
    item-value="path"
    :custom-filter="filterRepo"
    label="选择仓库"
    density="compact"
    variant="outlined"
    hide-details
    prepend-inner-icon="mdi-source-repository"
    no-data-text="没有匹配的仓库"
    class="repo-select"
  >
    <template #item="{ props: itemProps, item }">
      <v-list-item v-bind="itemProps" :subtitle="opt(item).subtitle">
        <template #title>{{ opt(item).name }}</template>
        <template #prepend>
          <v-icon size="14" :color="opt(item).color">mdi-circle</v-icon>
        </template>
        <template #append>
          <v-chip v-if="opt(item).ahead" size="x-small" color="warning" variant="tonal">
            ↑{{ opt(item).ahead }}
          </v-chip>
          <v-chip
            v-if="opt(item).behind"
            size="x-small"
            color="info"
            variant="tonal"
            class="ml-1"
          >
            ↓{{ opt(item).behind }}
          </v-chip>
        </template>
      </v-list-item>
    </template>
  </v-autocomplete>
</template>

<style scoped>
.repo-select {
  min-width: 240px;
  max-width: 380px;
  flex: 0 1 320px;
}
</style>
