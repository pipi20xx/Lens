<script setup lang="ts">
/**
 * 仓库文件树（左侧资源管理器）。
 *
 * 用「扁平可见行 + 展开状态表」而不是递归组件：
 * 渲染可控、能一键全收，也不会因为深层递归拖慢列表。
 * 子目录仍然是点开时才请求的（懒加载），大仓库不会一次拉爆。
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { repoManagerApi, type RepoEntry } from '@/api/repoManager'
import { useNotification } from '@/composables'
import { fileIcon } from '../fileIcons'

const props = defineProps<{
  repoPath: string
  selected: string
}>()

const emit = defineEmits<{
  (e: 'select', path: string): void
  (e: 'file-delete', entry: RepoEntry): void
  (e: 'file-copy', entry: RepoEntry): void
  (e: 'file-move', entry: RepoEntry): void
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

// ---------------- 右键菜单（删除 / 复制 / 移动） ----------------
const ctx = reactive({
  show: false,
  x: 0,
  y: 0,
  entry: null as RepoEntry | null,
})

function openCtx(event: MouseEvent, entry: RepoEntry) {
  ctx.entry = entry
  ctx.x = Math.max(4, Math.min(event.clientX, window.innerWidth - 200))
  ctx.y = Math.max(4, Math.min(event.clientY, window.innerHeight - 150))
  ctx.show = true
}

function closeCtx() {
  ctx.show = false
  ctx.entry = null
}

function ctxAction(action: 'delete' | 'copy' | 'move') {
  const entry = ctx.entry
  closeCtx()
  if (!entry) return
  if (action === 'delete') emit('file-delete', entry)
  else if (action === 'copy') emit('file-copy', entry)
  else emit('file-move', entry)
}

function onGlobalKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeCtx()
}

onMounted(() => {
  loadDir('', true)
  window.addEventListener('click', closeCtx)
  window.addEventListener('contextmenu', closeCtx, true)
  window.addEventListener('keydown', onGlobalKeydown)
  window.addEventListener('resize', closeCtx)
  window.addEventListener('scroll', closeCtx, true)
})

onBeforeUnmount(() => {
  window.removeEventListener('click', closeCtx)
  window.removeEventListener('contextmenu', closeCtx, true)
  window.removeEventListener('keydown', onGlobalKeydown)
  window.removeEventListener('resize', closeCtx)
  window.removeEventListener('scroll', closeCtx, true)
})

defineExpose({
  refresh: () => loadDir('', true),
  reload: () => {
    reset()
    loadDir('', true)
  },
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
      @contextmenu.prevent.stop="openCtx($event, row.entry)"
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

    <Teleport to="body">
      <div
        v-if="ctx.show"
        class="ctx-menu"
        :style="{ left: ctx.x + 'px', top: ctx.y + 'px' }"
        @click.stop
      >
        <v-list density="compact">
          <v-list-item prepend-icon="mdi-content-copy" @click="ctxAction('copy')">
            <v-list-item-title>复制到…</v-list-item-title>
          </v-list-item>
          <v-list-item prepend-icon="mdi-folder-move-outline" @click="ctxAction('move')">
            <v-list-item-title>移动到…</v-list-item-title>
          </v-list-item>
          <v-divider />
          <v-list-item prepend-icon="mdi-delete-outline" color="error" @click="ctxAction('delete')">
            <v-list-item-title>删除</v-list-item-title>
          </v-list-item>
        </v-list>
      </div>
    </Teleport>
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
}
.hint {
  font-size: 12px;
  padding: 8px 6px;
}
.ctx-menu {
  position: fixed;
  z-index: 3000;
  min-width: 180px;
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.28);
  overflow: hidden;
}
</style>
