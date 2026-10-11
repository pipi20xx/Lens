<script setup lang="ts">
/**
 * 识别词生成器
 * 粘贴文件名 → 提取标题锚点（可手动修正） → 生成 MoviePilot 自定义识别词规则
 * 核心算法在后端 /api/recognition-words/generate，此处只做参数与展示
 */
import { ref, reactive, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { recognitionWordsApi, type AnchorRow, type GenerateResult } from '@/api/recognitionWords'
import { useNotification } from '@/composables'
import { useClipboard } from '@/composables'

const { success, error: showError, warning } = useNotification()
const { copy: copyToClipboard } = useClipboard()

const inputText = ref('')
const autoAnchor = ref(true)
const rows = ref<AnchorRow[]>([])
const result = ref<GenerateResult | null>(null)
const generating = ref(false)
// 输出可编辑：手动修改后暂停自动覆盖（改动文件名或点"还原"恢复自动生成）
const outputText = ref('')
const outputEdited = ref(false)

function onOutputEdit(v: string) {
  outputText.value = v
  outputEdited.value = v !== (result.value?.rules_text ?? '')
}

function resetOutput() {
  outputEdited.value = false
  outputText.value = result.value?.rules_text || ''
}

const saved = localStorage.getItem('lens_recognition_words')
const params = reactive(saved ? JSON.parse(saved) : {
  tmdbid: 'xxxx',
  mtype: 'tv',
  season: 'x',
  loose: true,
  boundary: false,
  keep_group: false,
  date_comment: true,
})

watch(params, (val) => {
  localStorage.setItem('lens_recognition_words', JSON.stringify(val))
}, { deep: true })

let timer: ReturnType<typeof setTimeout> | null = null
function scheduleGenerate(keepAnchors: boolean) {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => generate(keepAnchors), 400)
}

async function generate(keepAnchors = false) {
  const filenames = inputText.value.split('\n').map((s) => s.trim()).filter(Boolean)
  if (filenames.length === 0) {
    rows.value = []
    result.value = null
    outputText.value = ''
    outputEdited.value = false
    return
  }
  const payload: any = { filenames, ...params }
  // 手动修正过锚点（或参数变化）时带上现有锚点，避免覆盖用户编辑
  if (keepAnchors && rows.value.length === filenames.length) {
    payload.anchors = rows.value.map((r) => r.anchor)
  }
  generating.value = true
  try {
    const res = await recognitionWordsApi.generate(payload)
    rows.value = res.rows
    result.value = res
    // 手动改过输出时不覆盖（自动生成已暂停），还原或改文件名后恢复
    if (!outputEdited.value) outputText.value = res.rules_text
  } catch (e: any) {
    showError('生成失败: ' + (e.message || '未知错误'))
  } finally {
    generating.value = false
  }
}

watch(inputText, () => {
  // 文件名列表变化 = 重新生成意图，恢复自动生成
  outputEdited.value = false
  scheduleGenerate(false)
})
watch(params, () => scheduleGenerate(true))

watch(autoAnchor, (checked) => {
  // 重新开启：强制按当前文件名重建锚点（覆盖手动修改）；关闭则保留现状
  scheduleGenerate(!checked)
})

function onAnchorEdit(row: AnchorRow, value: string) {
  row.anchor = value
  row.valid = false
  if (autoAnchor.value) autoAnchor.value = false
  scheduleGenerate(true)
}

function copyAll() {
  const text = outputText.value.trim()
  if (!text) { warning('当前没有可复制的内容'); return }
  copyToClipboard(text)
  success('识别词已复制到剪贴板')
}

function copyRow(row: AnchorRow) {
  if (!row.rule) { warning('该行没有规则（锚点为空或重复）'); return }
  copyToClipboard(row.rule)
  success('规则已复制')
}

const anchorListRef = ref<HTMLElement | null>(null)
function scrollToAnchors() {
  nextTick(() => anchorListRef.value?.scrollTo({ top: 0 }))
}

onMounted(() => {
  if (inputText.value) generate(false)
})

onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-regex</v-icon>
      识别词生成器
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">
      粘贴一个或多个文件名，自动提取标题锚点并生成自定义识别词规则；tmdbid / 季号需人工填写。
    </p>

    <v-row>
      <!-- 左侧：输入与锚点 -->
      <v-col cols="12" md="7">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-file-document-edit-outline</v-icon>
            文件名（每行一个，支持完整路径）
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-textarea
              v-model="inputText"
              :rows="6"
              auto-grow
              variant="outlined" density="compact"
              placeholder="[ANi] 桃源暗鬼：日光·華嚴瀑布篇 - 01 [1080P][Baha][WEB-DL][AAC AVC][CHT].mp4"
              hide-details
            />
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4 d-flex align-center">
            <v-icon start>mdi-anchor</v-icon>
            锚点
            <v-switch
              v-model="autoAnchor" color="primary" density="compact" hide-details
              label="自动生成" class="ml-4"
            />
            <v-spacer />
            <v-icon v-if="generating" icon="mdi-loading mdi-spin" size="18" color="primary" />
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-0">
            <div v-if="rows.length === 0" class="pa-4 text-body-2 text-medium-emphasis">
              暂无锚点，请先在上方输入文件名。
            </div>
            <div v-else ref="anchorListRef" style="max-height: 380px; overflow-y: auto">
              <div
                v-for="(row, i) in rows" :key="i"
                class="px-4 py-2"
                :class="{ 'border-b': i < rows.length - 1 }"
              >
                <div class="text-caption text-medium-emphasis text-truncate mb-1">
                  {{ row.filename }}
                </div>
                <div class="d-flex align-center">
                  <v-text-field
                    :model-value="row.anchor"
                    @update:model-value="(v: string) => onAnchorEdit(row, v)"
                    variant="outlined" density="compact" hide-details
                    placeholder="锚点为空"
                    :error="!row.valid && !!row.anchor"
                  />
                  <v-tooltip text="该锚点过短，可能误伤其他文件" location="top">
                    <template #activator="{ props: tipProps }">
                      <v-icon
                        v-if="!row.valid && !!row.anchor"
                        v-bind="tipProps" icon="mdi-alert-outline" color="warning" size="20" class="ml-2 flex-shrink-0"
                      />
                    </template>
                  </v-tooltip>
                  <v-tooltip text="复制该条规则" location="top">
                    <template #activator="{ props: tipProps }">
                      <v-icon
                        v-bind="tipProps" icon="mdi-content-copy" size="20" class="ml-2 cursor-pointer flex-shrink-0"
                        @click="copyRow(row)"
                      />
                    </template>
                  </v-tooltip>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧：参数与结果 -->
      <v-col cols="12" md="5">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-tune</v-icon>
            规则参数
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-select
              v-model="params.loose"
              :items="[{ title: '宽松模式（推荐）', value: true }, { title: '绝对模式', value: false }]"
              item-title="title" item-value="value"
              label="匹配模式" variant="outlined" density="compact" class="mb-3" hide-details
            />
            <v-text-field v-model="params.tmdbid" label="tmdbid" variant="outlined" density="compact" class="mb-3" hide-details />
            <v-select
              v-model="params.mtype"
              :items="['tv', 'movie']"
              label="type" variant="outlined" density="compact" class="mb-3" hide-details
            />
            <v-text-field v-model="params.season" label="s（季号）" variant="outlined" density="compact" class="mb-1" hide-details />
            <v-switch v-model="params.boundary" color="primary" density="compact" hide-details>
              <template #label>
                <span class="text-body-2">词边界包裹 (?i)\b...\b</span>
              </template>
            </v-switch>
            <v-switch v-model="params.date_comment" color="primary" density="compact" hide-details>
              <template #label>
                <span class="text-body-2">首行添加生成日期注释</span>
              </template>
            </v-switch>
            <v-switch v-model="params.keep_group" color="primary" density="compact" hide-details>
              <template #label>
                <span class="text-body-2">锚点保留字幕组前缀（如 [ANi]）</span>
              </template>
            </v-switch>
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4 d-flex align-center">
            <v-icon start>mdi-text-box-check-outline</v-icon>
            生成的识别词
            <v-btn
              v-if="outputEdited"
              size="small" variant="text" prepend-icon="mdi-restore" class="ml-2"
              @click="resetOutput"
            >
              还原
            </v-btn>
            <v-spacer />
            <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-content-copy" @click="copyAll">
              复制全部
            </v-btn>
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-textarea
              :model-value="outputText"
              @update:model-value="onOutputEdit"
              :rows="8" auto-grow
              variant="outlined" density="compact"
              placeholder="生成的识别词会出现在这里（可直接编辑后再复制）"
              class="monospace-text"
              hide-details
            />
            <v-alert
              v-if="outputEdited"
              type="info" variant="tonal" density="compact" class="mt-3"
            >
              识别词已手动修改，自动生成已暂停（改动文件名列表或点击"还原"可恢复）。
            </v-alert>
            <v-alert
              v-for="(w, i) in result?.warnings || []" :key="'w' + i"
              type="warning" variant="tonal" density="compact" class="mt-3"
            >
              {{ w }}
            </v-alert>
            <p v-if="result?.hint" class="text-body-2 text-success mt-3 mb-0">{{ result.hint }}</p>
            <p class="text-caption text-medium-emphasis mt-2 mb-0">
              规则可直接粘贴到 MoviePilot 等工具的自定义识别词；# 开头行为注释，不参与匹配。
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.monospace-text :deep(textarea) {
  font-family: Consolas, 'Courier New', monospace;
}
.border-b {
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.08);
}
</style>
