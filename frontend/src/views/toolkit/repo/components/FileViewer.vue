<script setup lang="ts">
/**
 * 右侧文件正文 / 编辑器。
 * 保存只写工作区，不自动 git add —— 改完去「变更」页确认再提交。
 */
import { computed, nextTick, ref, watch } from 'vue'
import { repoManagerApi, type RepoFileContent } from '@/api/repoManager'
import { useConfirm, useNotification } from '@/composables'

const props = defineProps<{
  repoPath: string
  file: string
  /** 从搜索结果打开时，滚到这一行 */
  focusLine?: number
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
  await nextTick()
  scrollToLine(props.focusLine)
}

/** 阅读态滚到指定行（行高与 .code 的 line-height 一致） */
function scrollToLine(line?: number) {
  if (!line || line < 1) return
  const body = preRef.value?.parentElement
  if (!body) return
  body.scrollTop = Math.max(0, (line - 1) * 18.6 - body.clientHeight / 3)
}

watch(
  () => props.focusLine,
  (line) => {
    if (line) nextTick(() => scrollToLine(line))
  }
)

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
  const mod = event.ctrlKey || event.metaKey
  const key = event.key.toLowerCase()
  if (mod && key === 's') {
    event.preventDefault()
    save()
    return
  }
  if (mod && key === 'f') {
    event.preventDefault()
    openFind(false)
    return
  }
  if (mod && key === 'h') {
    event.preventDefault()
    openFind(true)
    return
  }
  if (event.key === 'Escape' && findOpen.value) {
    event.preventDefault()
    closeFind()
  }
}

// ---------------- 查找 / 替换（VSCode 风格浮层） ----------------
const findOpen = ref(false)
const replaceOpen = ref(false)
const findQuery = ref('')
const replaceWith = ref('')
const caseSensitive = ref(false)
const wholeWord = ref(false)
const useRegex = ref(false)
const matchIndex = ref(0)
const MAX_MATCHES = 5000

const findInput = ref<HTMLInputElement | null>(null)
const replaceInput = ref<HTMLInputElement | null>(null)
const preRef = ref<HTMLElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)

/** 被搜索的文本：编辑时是草稿，阅读时是文件内容 */
const activeText = computed(() => (editing.value ? draft.value : content.value?.content ?? ''))

const regexInvalid = computed(() => {
  if (!useRegex.value || !findQuery.value) return false
  try {
    new RegExp(findQuery.value)
    return false
  } catch {
    return true
  }
})

interface Hit {
  start: number
  end: number
}

function isWordChar(ch: string): boolean {
  return /[A-Za-z0-9_]/.test(ch)
}

/** 命中位置：支持 大小写 / 全字 / 正则 三种开关 */
const hits = computed<Hit[]>(() => {
  const query = findQuery.value
  const text = activeText.value
  if (!query || !text) return []
  const out: Hit[] = []

  if (useRegex.value) {
    let re: RegExp
    try {
      re = new RegExp(query, caseSensitive.value ? 'g' : 'gi')
    } catch {
      return []
    }
    let m: RegExpExecArray | null
    while ((m = re.exec(text)) && out.length < MAX_MATCHES) {
      if (m[0] === '') {
        re.lastIndex += 1
        continue
      }
      out.push({ start: m.index, end: m.index + m[0].length })
    }
    return out
  }

  const haystack = caseSensitive.value ? text : text.toLowerCase()
  const needle = caseSensitive.value ? query : query.toLowerCase()
  let index = haystack.indexOf(needle)
  while (index !== -1 && out.length < MAX_MATCHES) {
    const end = index + needle.length
    const boundaryOk =
      !wholeWord.value ||
      ((index === 0 || !isWordChar(text[index - 1])) &&
        (end >= text.length || !isWordChar(text[end])))
    if (boundaryOk) out.push({ start: index, end })
    index = haystack.indexOf(needle, Math.max(index + 1, end))
  }
  return out
})

const countText = computed(() => {
  if (!findQuery.value) return ''
  if (regexInvalid.value) return '正则无效'
  if (!hits.value.length) return '无结果'
  const current = Math.min(matchIndex.value, hits.value.length - 1) + 1
  const suffix = hits.value.length >= MAX_MATCHES ? '+' : ''
  return `${current} / ${hits.value.length}${suffix}`
})

function escapeHtml(text: string): string {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

/** 阅读态高亮：所有命中包 <mark>，当前命中额外加类（内容全部转义，v-html 安全） */
const previewHtml = computed<string>(() => {
  const text = content.value?.content ?? ''
  const list = hits.value
  if (editing.value || !findQuery.value || !list.length) return escapeHtml(text)

  const current = Math.min(matchIndex.value, list.length - 1)
  const parts: string[] = []
  let last = 0
  list.forEach((hit, i) => {
    parts.push(escapeHtml(text.slice(last, hit.start)))
    const cls = i === current ? 'hit hit-current' : 'hit'
    parts.push(`<mark class="${cls}">${escapeHtml(text.slice(hit.start, hit.end))}</mark>`)
    last = hit.end
  })
  parts.push(escapeHtml(text.slice(last)))
  return parts.join('')
})

function openFind(withReplace = false) {
  if (!content.value || content.value.binary) return
  findOpen.value = true
  if (withReplace && editing.value) replaceOpen.value = true
  nextTick(() => {
    const el = withReplace && editing.value ? replaceInput.value : findInput.value
    el?.focus()
    el?.select()
  })
}

function closeFind() {
  findOpen.value = false
  replaceOpen.value = false
  matchIndex.value = 0
}

function scrollToOffset(offset: number) {
  const el = textareaRef.value
  if (!el) return
  const lineHeight = 18.6
  const line = draft.value.slice(0, offset).split('\n').length - 1
  const y = line * lineHeight
  if (y < el.scrollTop || y > el.scrollTop + el.clientHeight - lineHeight * 2) {
    el.scrollTop = Math.max(0, y - el.clientHeight / 2)
  }
}

function selectMatch(index: number, focus = true) {
  const total = hits.value.length
  if (!total) return
  const i = ((index % total) + total) % total
  matchIndex.value = i
  const hit = hits.value[i]

  if (editing.value) {
    const el = textareaRef.value
    if (!el) return
    if (focus) el.focus()
    el.setSelectionRange(hit.start, hit.end)
    scrollToOffset(hit.start)
    return
  }

  const marks = preRef.value?.querySelectorAll('mark.hit')
  const target = marks?.[i] as HTMLElement | undefined
  target?.scrollIntoView({ block: 'center' })
}

function nextMatch(reverse = false) {
  if (!hits.value.length) return
  selectMatch(matchIndex.value + (reverse ? -1 : 1))
}

function replaceOne() {
  if (!editing.value || !hits.value.length) return
  const hit = hits.value[Math.min(matchIndex.value, hits.value.length - 1)]
  draft.value = draft.value.slice(0, hit.start) + replaceWith.value + draft.value.slice(hit.end)
  nextTick(() => selectMatch(matchIndex.value))
}

function replaceAll() {
  if (!editing.value) return
  const total = hits.value.length
  if (!total) return
  const text = draft.value
  if (useRegex.value) {
    const re = new RegExp(findQuery.value, caseSensitive.value ? 'g' : 'gi')
    // 正则模式支持 $1 分组引用
    draft.value = text.replace(re, replaceWith.value)
  } else {
    const query = findQuery.value
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const re = new RegExp(escaped, caseSensitive.value ? 'g' : 'gi')
    // 字面量模式按原样插入，避免 $ 被当成分组引用
    draft.value = text.replace(re, () => replaceWith.value)
  }
  matchIndex.value = 0
  success(`已替换 ${total} 处`)
}

// 搜索条件变化后自动定位第一个命中（不抢焦点，否则没法继续输入）
watch([findQuery, caseSensitive, wholeWord, useRegex], () => {
  matchIndex.value = 0
  nextTick(() => {
    if (hits.value.length) selectMatch(0, false)
  })
})

// 切换文件时收起浮层
watch(
  () => props.file,
  () => {
    closeFind()
    findQuery.value = ''
    replaceWith.value = ''
  }
)

defineExpose({ confirmLeave, reload: load })
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
            variant="text"
            prepend-icon="mdi-magnify"
            title="查找（Ctrl+F）"
            @click="openFind(false)"
          >
            查找
          </v-btn>
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
          <v-btn
            size="x-small"
            variant="text"
            prepend-icon="mdi-magnify"
            title="查找 / 替换（Ctrl+F / Ctrl+H）"
            @click="openFind(false)"
          >
            查找
          </v-btn>
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

      <div class="body-wrap">
        <!-- VSCode 风格查找 / 替换浮层 -->
        <div v-if="findOpen" class="find-widget" @keydown.esc.stop.prevent="closeFind">
          <div class="find-row">
            <v-icon size="14" class="find-icon">mdi-magnify</v-icon>
            <input
              ref="findInput"
              v-model="findQuery"
              class="find-field"
              :class="{ invalid: regexInvalid }"
              placeholder="查找"
              spellcheck="false"
              @keydown.enter.prevent="nextMatch($event.shiftKey)"
            />
            <span class="find-count" :class="{ empty: findQuery && !hits.length }">
              {{ countText }}
            </span>
            <button
              class="find-toggle"
              title="上一个（Shift+Enter）"
              :disabled="!hits.length"
              @click="nextMatch(true)"
            >
              <v-icon size="14">mdi-chevron-up</v-icon>
            </button>
            <button
              class="find-toggle"
              title="下一个（Enter）"
              :disabled="!hits.length"
              @click="nextMatch(false)"
            >
              <v-icon size="14">mdi-chevron-down</v-icon>
            </button>
            <button
              class="find-toggle"
              :class="{ on: caseSensitive }"
              title="区分大小写"
              @click="caseSensitive = !caseSensitive"
            >
              Aa
            </button>
            <button
              class="find-toggle"
              :class="{ on: wholeWord }"
              title="全字匹配"
              @click="wholeWord = !wholeWord"
            >
              ab
            </button>
            <button
              class="find-toggle"
              :class="{ on: useRegex }"
              title="使用正则表达式"
              @click="useRegex = !useRegex"
            >
              .*
            </button>
            <button
              v-if="editing"
              class="find-toggle"
              :class="{ on: replaceOpen }"
              title="切换替换"
              @click="replaceOpen = !replaceOpen"
            >
              <v-icon size="14">
                {{ replaceOpen ? 'mdi-chevron-up' : 'mdi-chevron-down' }}
              </v-icon>
            </button>
            <button class="find-toggle" title="关闭（Esc）" @click="closeFind">
              <v-icon size="14">mdi-close</v-icon>
            </button>
          </div>

          <div v-if="editing && replaceOpen" class="find-row replace-row">
            <v-icon size="14" class="find-icon">mdi-swap-horizontal</v-icon>
            <input
              ref="replaceInput"
              v-model="replaceWith"
              class="find-field"
              placeholder="替换"
              spellcheck="false"
              @keydown.enter.prevent="replaceOne"
            />
            <button class="find-action" :disabled="!hits.length" @click="replaceOne">
              替换
            </button>
            <button class="find-action" :disabled="!hits.length" @click="replaceAll">
              全部替换
            </button>
          </div>
        </div>

        <div class="body">
          <textarea
            v-if="editing"
            ref="textareaRef"
            v-model="draft"
            class="editor"
            spellcheck="false"
            wrap="off"
            @keydown="onEditorKeydown"
          />
          <pre v-else ref="preRef" class="code" v-html="previewHtml"></pre>
          <div v-if="content.truncated && !editing" class="tip">
            文件超过 400KB，仅显示前半部分（编辑前请先在本地处理）
          </div>
          <div v-else-if="editing" class="tip">
            保存只写入工作区，不会自动 git add；改完到「变更」页确认后提交。Ctrl/⌘ + S 可保存。
          </div>
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
.body-wrap {
  position: relative;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
/* ---------- VSCode 风格查找 / 替换浮层 ---------- */
.find-widget {
  position: absolute;
  top: 6px;
  right: 18px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 4px 5px;
  border-radius: 6px;
  border: 1px solid rgba(var(--v-border-color), 0.7);
  background: rgba(var(--v-theme-surface), 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.28);
}
.find-row {
  display: flex;
  align-items: center;
  gap: 2px;
}
.find-icon {
  opacity: 0.55;
  margin: 0 2px 0 4px;
}
.find-field {
  width: 170px;
  height: 24px;
  padding: 0 6px;
  border: 1px solid rgba(var(--v-border-color), 0.7);
  border-radius: 4px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  outline: none;
}
.find-field::placeholder {
  color: rgba(var(--v-theme-on-surface), 0.5);
}
.find-field:focus {
  border-color: rgb(var(--v-theme-primary));
}
.find-field.invalid {
  border-color: rgb(var(--v-theme-error));
}
.find-count {
  min-width: 54px;
  padding: 0 6px;
  font-size: 11px;
  text-align: right;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}
.find-count.empty {
  color: rgb(var(--v-theme-error));
}
.find-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-size: 11px;
  line-height: 1;
  cursor: pointer;
}
.find-toggle:hover:not(:disabled) {
  background: rgba(var(--v-theme-primary), 0.14);
}
.find-toggle.on {
  background: rgba(var(--v-theme-primary), 0.24);
  color: rgb(var(--v-theme-primary));
}
.find-toggle:disabled {
  opacity: 0.35;
  cursor: default;
}
.find-action {
  height: 24px;
  padding: 0 8px;
  border: 1px solid rgba(var(--v-border-color), 0.7);
  border-radius: 4px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-size: 12px;
  cursor: pointer;
}
.find-action:hover:not(:disabled) {
  background: rgba(var(--v-theme-primary), 0.14);
}
.find-action:disabled {
  opacity: 0.4;
  cursor: default;
}
.replace-row {
  margin-top: 1px;
}
/* v-html 注入的命中高亮 */
.code :deep(mark.hit) {
  background: rgba(var(--v-theme-primary), 0.26);
  color: inherit;
  border-radius: 2px;
}
.code :deep(mark.hit-current) {
  background: rgba(var(--v-theme-primary), 0.55);
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
  flex-shrink: 0;
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
