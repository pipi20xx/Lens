<script setup lang="ts">
/**
 * 仓库文件树（左侧资源管理器）。
 *
 * 用「扁平可见行 + 展开状态表」而不是递归组件：
 * 渲染可控、能一键全收，也不会因为深层递归拖慢列表。
 * 子目录仍然是点开时才请求的（懒加载），大仓库不会一次拉爆。
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { repoManagerApi, type RepoEntry } from '@/api/repoManager'
import { useNotification } from '@/composables'
import { fileIcon } from '../fileIcons'

const props = defineProps<{
  repoPath: string
  selected: string
}>()

const emit = defineEmits<{
  (e: 'select', path: string): void
}>()

const { error: showError } = useNotification()

const rootEntries = ref<RepoEntry[]>([])
const rootLoading = ref(false)
const rootTruncated = ref(false)

const childrenMap = reactive<Record<string, RepoEntry[]>>({})
const expanded = reactive<Record<string, boolean>>({})
const loadingPaths = reactive<Record<string, boolean>>({})
const truncatedMap = reactive<Record<string, boolean>>({})

interface Row {
  entry: RepoEntry
  depth: number
}

/** 把「展开的目录」摊平成一维可见行 */
const rows = computed<Row[]>(() => {
  const out: Row[] = []
  const walk = (entries: RepoEntry[], depth: number) => {
    for (const entry of entries) {
      out.push({ entry, depth })
      if (entry.type === 'dir' && expanded[entry.path]) {
        const kids = childrenMap[entry.path]
        if (kids) walk(kids, depth + 1)
      }
    }
  }
  walk(rootEntries.value, 0)
  return out
})

async function loadDir(dir: string, isRoot = false) {
  if (loadingPaths[dir]) return
  loadingPaths[dir] = true
  if (isRoot) rootLoading.value = true
  try {
    const res = await repoManagerApi.listFiles(props.repoPath, dir)
    const list = res.entries || []
    if (isRoot) {
      rootEntries.value = list
      rootTruncated.value = !!res.truncated
    } else {
      childrenMap[dir] = list
      truncatedMap[dir] = !!res.truncated
    }
  } catch (e: any) {
    showError(e.message || '读取目录失败')
    if (isRoot) rootEntries.value = []
  } finally {
    loadingPaths[dir] = false
    if (isRoot) rootLoading.value = false
  }
}

async function toggle(entry: RepoEntry) {
  if (entry.type !== 'dir') {
    emit('select', entry.path)
    return
  }
  const next = !expanded[entry.path]
  expanded[entry.path] = next
  if (next && !childrenMap[entry.path]) await loadDir(entry.path)
}

function collapseAll() {
  for (const key of Object.keys(expanded)) expanded[key] = false
}

function reset() {
  rootEntries.value = []
  rootTruncated.value = false
  for (const key of Object.keys(childrenMap)) delete childrenMap[key]
  for (const key of Object.keys(expanded)) delete expanded[key]
  for (const key of Object.keys(truncatedMap)) delete truncatedMap[key]
}

watch(
  () => props.repoPath,
  () => {
    reset()
    loadDir('', true)
  }
)

onMounted(() => loadDir('', true))

defineExpose({
  refresh: () => loadDir('', true),
  collapseAll,
})
</script>

<template>
  <div class="tree">
    <v-progress-linear v-if="rootLoading" indeterminate />

    <div
      v-for="row in rows"
      :key="row.entry.path"
      class="node"
      :class="{ active: selected === row.entry.path, dir: row.entry.type === 'dir' }"
      :style="{ paddingLeft: `${row.depth * 14 + 6}px` }"
      @click="toggle(row.entry)"
    >
      <v-icon v-if="row.entry.type === 'dir'" size="16" class="chevron">
        {{ expanded[row.entry.path] ? 'mdi-chevron-down' : 'mdi-chevron-right' }}
      </v-icon>
      <span v-else class="chevron-spacer" />
      <v-icon size="15" :color="row.entry.type === 'dir' ? 'primary' : undefined">
        {{ fileIcon(row.entry.name, row.entry.type) }}
      </v-icon>
      <span class="name">{{ row.entry.name }}</span>
      <span v-if="loadingPaths[row.entry.path]" class="mini-loading">…</span>
    </div>

    <div v-if="!rootLoading && !rootEntries.length" class="hint">空仓库</div>
    <div v-if="rootTruncated" class="hint">条目过多，仅显示前部分</div>
  </div>
</template>

<style scoped>
.tree {
  padding: 4px 2px;
}
.node {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 22px;
  padding-right: 8px;
  font-size: 12.5px;
  cursor: pointer;
  border-radius: 4px;
  user-select: none;
}
.node:hover {
  background: rgba(var(--v-theme-primary), 0.08);
}
.node.active {
  background: rgba(var(--v-theme-primary), 0.16);
  color: rgb(var(--v-theme-primary));
  font-weight: 500;
}
.chevron {
  opacity: 0.7;
}
.chevron-spacer {
  width: 16px;
  flex: 0 0 16px;
}
.name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mini-loading {
  font-size: 11px;
  opacity: 0.5;
}
.hint {
  font-size: 12px;
  padding: 8px 6px;
  opacity: 0.45;
}
</style>
