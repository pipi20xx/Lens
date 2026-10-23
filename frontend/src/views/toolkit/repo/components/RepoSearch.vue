<script setup lang="ts">
/**
 * 仓库级搜索：同时搜「文件名」和「文件内容」，结果按文件分组。
 * 内容搜索走后端 git grep（遵循 .gitignore，含未跟踪文件，自动跳过二进制）。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { repoManagerApi, type RepoSearchResult } from '@/api/repoManager'
import { useConfirm, useNotification } from '@/composables'

const props = defineProps<{ repoPath: string }>()

const emit = defineEmits<{
  (e: 'open', file: string, line: number): void
  (e: 'searching', value: boolean): void
  (e: 'replaced', files: string[]): void
}>()

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const query = ref('')
const replacement = ref('')
const caseSensitive = ref(false)
const wholeWord = ref(false)
const useRegex = ref(false)
const replaceOpen = ref(false)
const replacing = ref(false)
const loading = ref(false)
const result = ref<RepoSearchResult | null>(null)
const errorText = ref('')
let timer: number | undefined

const searching = computed(() => query.value.trim().length > 0)

/** 按文件分组的内容命中 */
const grouped = computed(() => {
  const map = new Map<string, { line: number; text: string }[]>()
  for (const item of result.value?.matches || []) {
    if (!map.has(item.file)) map.set(item.file, [])
    map.get(item.file)!.push({ line: item.line, text: item.text })
  }
  return Array.from(map.entries()).map(([file, lines]) => ({ file, lines }))
})

const summary = computed(() => {
  if (!result.value) return ''
  const files = result.value.files.length
  const hits = result.value.matches.length
  return `${files} 个文件名 · ${hits} 处内容`
})

function schedule() {
  emit('searching', searching.value)
  if (timer !== undefined) window.clearTimeout(timer)
  if (!searching.value) {
    result.value = null
    errorText.value = ''
    return
  }
  timer = window.setTimeout(run, 300)
}

async function run() {
  if (!searching.value) return
  loading.value = true
  errorText.value = ''
  try {
    result.value = await repoManagerApi.search(props.repoPath, query.value.trim(), {
      case: caseSensitive.value,
      whole: wholeWord.value,
      regex: useRegex.value,
    })
  } catch (e: any) {
    errorText.value = e.message || '搜索失败'
    result.value = null
  } finally {
    loading.value = false
  }
}

watch([query, caseSensitive, wholeWord, useRegex], schedule)

// 换仓库时清空
watch(
  () => props.repoPath,
  () => {
    query.value = ''
    result.value = null
    errorText.value = ''
    emit('searching', false)
  }
)

onBeforeUnmount(() => {
  if (timer !== undefined) window.clearTimeout(timer)
})

/** 跨文件替换：file 为空表示全仓库 */
async function doReplace(file = '') {
  if (!searching.value || replacing.value) return
  const fileHits = file
    ? grouped.value.find((g) => g.file === file)?.lines.length || 0
    : 0
  const totalHits = file ? fileHits : result.value?.matches.length || 0
  if (!totalHits) return

  const ok = await confirm({
    title: file ? '替换此文件中的匹配' : '全部替换',
    content: file
      ? `将把 ${file} 里的 ${totalHits} 处「${query.value}」替换为「${replacement.value}」。会直接写入工作区文件，不会自动提交。`
      : `将把 ${totalHits} 处「${query.value}」替换为「${replacement.value}」，涉及 ${grouped.value.length} 个文件。会直接写入工作区文件，不会自动提交。`,
    confirmText: '替换',
    confirmColor: 'warning',
  })
  if (!ok) return

  replacing.value = true
  try {
    const res = await repoManagerApi.replace(props.repoPath, {
      query: query.value.trim(),
      replacement: replacement.value,
      case: caseSensitive.value,
      whole: wholeWord.value,
      regex: useRegex.value,
      file,
    })
    if (res.replacements > 0) {
      success(`已替换 ${res.files} 个文件，共 ${res.replacements} 处`)
      emit('replaced', res.details.map((item) => item.file))
    } else {
      success('没有可替换的内容')
    }
    await run()
  } catch (e: any) {
    showError(e.message || '替换失败')
  } finally {
    replacing.value = false
  }
}

defineExpose({ clear: () => (query.value = '') })
</script>

<template>
  <div class="repo-search" :class="{ expanded: searching }">
    <div class="search-box">
      <v-icon size="14" class="icon">mdi-magnify</v-icon>
      <input
        v-model="query"
        class="field"
        :class="{ invalid: !!errorText }"
        placeholder="搜索文件名或内容"
        spellcheck="false"
      />
      <button
        class="toggle"
        :class="{ on: caseSensitive }"
        title="区分大小写"
        @click="caseSensitive = !caseSensitive"
      >
        Aa
      </button>
      <button
        class="toggle"
        :class="{ on: wholeWord }"
        title="全字匹配"
        @click="wholeWord = !wholeWord"
      >
        ab
      </button>
      <button
        class="toggle"
        :class="{ on: useRegex }"
        title="正则表达式"
        @click="useRegex = !useRegex"
      >
        .*
      </button>
      <button
        class="toggle"
        :class="{ on: replaceOpen }"
        title="展开替换"
        @click="replaceOpen = !replaceOpen"
      >
        <v-icon size="14">{{ replaceOpen ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
      </button>
      <button v-if="query" class="toggle" title="清空" @click="query = ''">
        <v-icon size="14">mdi-close</v-icon>
      </button>
    </div>

    <!-- 替换行：和 VSCode 一样在搜索框下面 -->
    <div v-if="replaceOpen" class="search-box replace-box">
      <v-icon size="14" class="icon">mdi-swap-horizontal</v-icon>
      <input
        v-model="replacement"
        class="field"
        placeholder="替换为"
        spellcheck="false"
        @keydown.enter.prevent="doReplace()"
      />
      <button
        class="replace-all"
        :disabled="!result?.matches.length || replacing"
        title="替换全部匹配"
        @click="doReplace()"
      >
        {{ replacing ? '替换中…' : '全部替换' }}
      </button>
    </div>

    <div v-if="searching" class="results">
      <v-progress-linear v-if="loading" indeterminate height="2" />

      <div v-if="errorText" class="state error">{{ errorText }}</div>
      <div v-else-if="!loading && result" class="state">{{ summary }}</div>

      <!-- 文件名 -->
      <template v-if="result?.files.length">
        <div class="group-title">文件名</div>
        <div
          v-for="item in result.files"
          :key="'f-' + item.path"
          class="row file-row"
          :title="item.path"
          @click="emit('open', item.path, 0)"
        >
          <v-icon size="14" color="primary">mdi-file-outline</v-icon>
          <span class="path">{{ item.path }}</span>
        </div>
      </template>

      <!-- 内容 -->
      <template v-if="grouped.length">
        <div class="group-title">内容</div>
        <div v-for="group in grouped" :key="'g-' + group.file" class="file-group">
          <div class="file-head" :title="group.file">
            <v-icon size="14" color="primary">mdi-file-document-outline</v-icon>
            <span class="path">{{ group.file }}</span>
            <span class="badge">{{ group.lines.length }}</span>
            <button
              v-if="replaceOpen"
              class="mini"
              title="替换此文件中的匹配"
              @click.stop="doReplace(group.file)"
            >
              替换
            </button>
          </div>
          <div
            v-for="line in group.lines"
            :key="group.file + ':' + line.line"
            class="row hit-row"
            :title="line.text"
            @click="emit('open', group.file, line.line)"
          >
            <span class="lineno">{{ line.line }}</span>
            <span class="snippet">{{ line.text || ' ' }}</span>
          </div>
        </div>
      </template>

      <div
        v-if="!loading && result && !result.files.length && !result.matches.length"
        class="state"
      >
        没有匹配结果
      </div>
      <div v-if="result?.truncated" class="state">结果过多，仅显示前一部分</div>
    </div>
  </div>
</template>

<style scoped>
.repo-search {
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
/* 有搜索词时占满左栏，结果区自己滚动 */
.repo-search.expanded {
  flex: 1 1 auto;
}
.search-box {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 6px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
.icon {
  opacity: 0.55;
  margin: 0 2px;
}
.field {
  flex: 1;
  min-width: 0;
  height: 24px;
  padding: 0 6px;
  border: 1px solid rgba(var(--v-border-color), 0.7);
  border-radius: 4px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-size: 12px;
  outline: none;
}
.field::placeholder {
  color: rgba(var(--v-theme-on-surface), 0.5);
}
.field:focus {
  border-color: rgb(var(--v-theme-primary));
}
.field.invalid {
  border-color: rgb(var(--v-theme-error));
}
.toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 22px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-size: 10.5px;
  line-height: 1;
  cursor: pointer;
  flex: 0 0 auto;
}
.toggle:hover {
  background: rgba(var(--v-theme-primary), 0.14);
}
.toggle.on {
  background: rgba(var(--v-theme-primary), 0.24);
  color: rgb(var(--v-theme-primary));
}
.results {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding-bottom: 6px;
}
.replace-box {
  gap: 4px;
}
.replace-all {
  height: 22px;
  padding: 0 8px;
  flex: 0 0 auto;
  border: 1px solid rgba(var(--v-border-color), 0.7);
  border-radius: 4px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-size: 11.5px;
  cursor: pointer;
  white-space: nowrap;
}
.replace-all:hover:not(:disabled) {
  background: rgba(var(--v-theme-primary), 0.16);
}
.replace-all:disabled {
  opacity: 0.4;
  cursor: default;
}
.mini {
  height: 18px;
  padding: 0 5px;
  border: 1px solid rgba(var(--v-border-color), 0.7);
  border-radius: 3px;
  background: transparent;
  color: rgb(var(--v-theme-on-surface));
  font-size: 10.5px;
  cursor: pointer;
  flex: 0 0 auto;
}
.mini:hover {
  background: rgba(var(--v-theme-primary), 0.16);
}
.state {
  font-size: 11px;
  padding: 6px 8px;
  color: rgb(var(--v-theme-on-surface));
}
.state.error {
  color: rgb(var(--v-theme-error));
}
.group-title {
  font-size: 11px;
  font-weight: 600;
  padding: 8px 8px 2px;
  color: rgb(var(--v-theme-on-surface));
}
.row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
}
.row:hover {
  background: rgba(var(--v-theme-primary), 0.1);
}
.file-head {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px 2px;
  font-size: 11.5px;
  font-weight: 600;
}
.path {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.badge {
  font-size: 10px;
  padding: 0 4px;
  border-radius: 8px;
  background: rgba(var(--v-theme-primary), 0.2);
  color: rgb(var(--v-theme-primary));
}
.hit-row {
  padding-left: 16px;
}
.lineno {
  flex: 0 0 auto;
  min-width: 26px;
  text-align: right;
  font-size: 10.5px;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  color: rgb(var(--v-theme-primary));
}
.snippet {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: pre;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 11.5px;
}
</style>
