<script setup lang="ts">
/**
 * 只读 diff 查看器：按行着色，不做编辑（这个页面只管 git，不做 IDE）。
 * 用 div + white-space:pre 逐行渲染，避免 <pre> 里的模板缩进被当成内容。
 */
import { computed } from 'vue'

const props = defineProps<{
  diff: string
  loading?: boolean
  file?: string
  /** 放进 flex 列里时用：撑满剩余高度，而不是固定高 */
  fill?: boolean
}>()

type LineKind = 'add' | 'del' | 'hunk' | 'meta' | 'ctx'

interface DiffLine {
  text: string
  kind: LineKind
}

const lines = computed<DiffLine[]>(() => {
  if (!props.diff) return []
  // CRLF 文件的 patch 每行末尾会带 \r，在 white-space:pre 下会被当成换行 → 行高翻倍
  const normalized = props.diff.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
  return normalized.split('\n').map((text) => {
    let kind: LineKind = 'ctx'
    if (
      text.startsWith('+++') ||
      text.startsWith('---') ||
      text.startsWith('diff ') ||
      text.startsWith('index ') ||
      text.startsWith('new file') ||
      text.startsWith('deleted file')
    ) {
      kind = 'meta'
    } else if (text.startsWith('@@')) {
      kind = 'hunk'
    } else if (text.startsWith('+')) {
      kind = 'add'
    } else if (text.startsWith('-')) {
      kind = 'del'
    }
    return { text, kind }
  })
})

const stats = computed(() => {
  let add = 0
  let del = 0
  for (const line of lines.value) {
    if (line.kind === 'add') add++
    else if (line.kind === 'del') del++
  }
  return { add, del }
})
</script>

<template>
  <div class="diff-shell" :class="{ 'diff-fill': fill }">
    <div v-if="loading" class="diff-hint">
      <v-progress-circular indeterminate size="18" width="2" class="mr-2" />正在读取 diff…
    </div>
    <div v-else-if="!diff" class="diff-hint">选择文件查看具体改动</div>
    <template v-else>
      <div class="diff-bar">
        <span class="text-truncate">{{ file || '全部改动' }}</span>
        <span class="diff-stat">
          <span class="diff-stat-add">+{{ stats.add }}</span>
          <span class="diff-stat-del">-{{ stats.del }}</span>
        </span>
      </div>
      <div class="diff-body">
        <div v-for="(line, idx) in lines" :key="idx" :class="['diff-line', `diff-${line.kind}`]">{{ line.text || ' ' }}</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.diff-shell {
  display: flex;
  flex-direction: column;
  min-height: 160px;
  height: var(--content-h, 58vh);
  max-height: var(--content-h, 58vh);
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
  background: var(--am-surface-bg);
}
.diff-fill {
  height: 100%;
  max-height: none;
  flex: 1;
  min-height: 0;
}
.diff-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 12px;
  font-size: 13px;
  color: rgba(var(--v-theme-on-surface), 0.55);
}
.diff-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  font-size: 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  background: var(--am-surface-bg);
}
.diff-stat {
  margin-left: auto;
  display: flex;
  gap: 8px;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
}
.diff-stat-add { color: #4caf50; }
.diff-stat-del { color: #ef5350; }
.diff-body {
  flex: 1;
  overflow: auto;
  padding: 6px 0;
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: 12px;
  line-height: 1.55;
}
.diff-line {
  white-space: pre;
  padding: 0 10px;
  min-height: 18px;
}
.diff-add { background: rgba(76, 175, 80, 0.14); color: #81c784; }
.diff-del { background: rgba(239, 83, 80, 0.14); color: #e57373; }
.diff-hunk { background: rgba(33, 150, 243, 0.12); color: #64b5f6; }
.diff-meta { color: rgba(var(--v-theme-on-surface), 0.5); }
.diff-ctx { color: rgba(var(--v-theme-on-surface), 0.82); }
</style>
