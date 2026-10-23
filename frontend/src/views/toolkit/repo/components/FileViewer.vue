<script setup lang="ts">
/**
 * 右侧文件正文 / 编辑器。
 * 保存只写工作区，不自动 git add —— 改完去「变更」页确认再提交。
 */
import { computed, ref, watch } from 'vue'
import { repoManagerApi, type RepoFileContent } from '@/api/repoManager'
import { useConfirm, useNotification } from '@/composables'

const props = defineProps<{
  repoPath: string
  file: string
}>()

const emit = defineEmits<{
  (e: 'dirty-change', value: boolean): void
}>()

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const content = ref<RepoFileContent | null>(null)
const loading = ref(false)
const editing = ref(false)
const draft = ref('')
const saving = ref(false)

const dirty = computed(() => editing.value && draft.value !== (content.value?.content ?? ''))
const canEdit = computed(() => !!content.value && !content.value.binary)

watch(dirty, (value) => emit('dirty-change', value))

function sizeText(bytes: number): string {
  if (!bytes) return '0 B'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`
}

async function load() {
  if (!props.file) {
    content.value = null
    return
  }
  loading.value = true
  content.value = null
  editing.value = false
  draft.value = ''
  try {
    content.value = await repoManagerApi.readFile(props.repoPath, props.file)
  } catch (e: any) {
    showError(e.message || '读取文件失败')
  } finally {
    loading.value = false
  }
}

watch(() => [props.repoPath, props.file], load, { immediate: true })

/** 让调用方在切换文件前先问一句，避免丢失未保存内容 */
async function confirmLeave(): Promise<boolean> {
  if (!dirty.value) return true
  return confirm({
    title: '放弃未保存的修改',
    content: `${props.file} 有未保存的修改，确定放弃？`,
    confirmText: '放弃修改',
    confirmColor: 'warning',
  })
}

function startEdit() {
  if (!canEdit.value) return
  draft.value = content.value?.content ?? ''
  editing.value = true
}

async function cancelEdit() {
  if (!(await confirmLeave())) return
  editing.value = false
  draft.value = ''
}

async function save() {
  if (!props.file || saving.value) return
  saving.value = true
  try {
    const res = await repoManagerApi.saveFile(
      props.repoPath,
      props.file,
      draft.value,
      content.value?.encoding || '',
      content.value?.eol || ''
    )
    if (content.value) {
      content.value.content = draft.value
      content.value.size = res.size
      content.value.encoding = res.encoding
      content.value.eol = res.eol as any
      content.value.truncated = false
    }
    editing.value = false
    success(`已保存 ${props.file}（${sizeText(res.size)}）`)
  } catch (e: any) {
    showError(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function onEditorKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    save()
  }
}

defineExpose({ confirmLeave })
</script>

<template>
  <div class="viewer">
    <div v-if="loading" class="hint">
      <v-progress-circular indeterminate size="18" width="2" class="mr-2" />正在读取…
    </div>
    <div v-else-if="!file" class="hint">从左侧资源管理器选择文件</div>
    <div v-else-if="content?.binary" class="hint">
      二进制文件（{{ sizeText(content.size) }}），无法预览
    </div>
    <template v-else-if="content">
      <div class="bar">
        <span class="text-truncate">{{ content.path }}</span>
        <span v-if="dirty" class="dot" title="有未保存的修改">●</span>
        <v-spacer />
        <span class="meta">
          {{ sizeText(content.size) }}
          <span v-if="content.encoding !== 'utf-8'" class="ml-2">{{ content.encoding }}</span>
          <span v-if="content.eol === 'crlf'" class="ml-2" title="该文件使用 CRLF 换行，保存会原样写回">CRLF</span>
        </span>
        <template v-if="!editing">
          <v-btn
            size="x-small"
            variant="tonal"
            color="primary"
            prepend-icon="mdi-pencil-outline"
            :disabled="!canEdit"
            @click="startEdit"
          >
            编辑
          </v-btn>
        </template>
        <template v-else>
          <v-btn size="x-small" variant="text" @click="cancelEdit">取消</v-btn>
          <v-btn
            size="x-small"
            variant="tonal"
            color="primary"
            prepend-icon="mdi-content-save-outline"
            :loading="saving"
            :disabled="!dirty"
            @click="save"
          >
            保存
          </v-btn>
        </template>
      </div>

      <div class="body">
        <textarea
          v-if="editing"
          v-model="draft"
          class="editor"
          spellcheck="false"
          wrap="off"
          @keydown="onEditorKeydown"
        />
        <pre v-else class="code">{{ content.content }}</pre>
        <div v-if="content.truncated && !editing" class="tip">
          文件超过 400KB，仅显示前半部分（编辑前请先在本地处理）
        </div>
        <div v-else-if="editing" class="tip">
          保存只写入工作区，不会自动 git add；改完到「变更」页确认后提交。Ctrl/⌘ + S 可保存。
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}
.hint {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 32px 12px;
  font-size: 13px;
  opacity: 0.55;
}
.bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  font-size: 12px;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: var(--am-surface-bg);
}
.meta {
  opacity: 0.6;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  white-space: nowrap;
}
.dot {
  color: rgb(var(--v-theme-warning));
  font-size: 10px;
}
.body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: auto;
}
.code {
  margin: 0;
  padding: 8px 10px;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre;
  tab-size: 4;
}
.editor {
  display: block;
  width: 100%;
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 8px 10px;
  border: 0;
  outline: none;
  resize: none;
  background: var(--am-surface-bg);
  color: rgb(var(--v-theme-on-surface));
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
  tab-size: 4;
  white-space: pre;
  overflow: auto;
}
.tip {
  padding: 5px 10px;
  font-size: 11px;
  opacity: 0.6;
  flex-shrink: 0;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
