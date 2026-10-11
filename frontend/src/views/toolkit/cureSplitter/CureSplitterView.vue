<script setup lang="ts">
/**
 * 番剧分季拆分（CureTMDb 拆分逻辑）
 * 输入 TMDB ID → 读取分季定义（规则表/TVDB/Bangumi）→ 拆分重灌 → 渲染词 + 剧集组
 * 集成配置（TMDB/TVDB/Bangumi Key、代理、Gitea、SYTMDB）在「设置 → 第三方 API 集成」维护
 */
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import {
  cureSplitterApi,
  type LogEntry,
  type SplitResult,
} from '@/api/cureSplitter'
import { configApi } from '@/api/config'
import { useNotification } from '@/composables'
import { useClipboard } from '@/composables'

const { success, error: showError, warning, info } = useNotification()
const { copy: copyToClipboard } = useClipboard()

const saved = localStorage.getItem('lens_cure_splitter')
const savedState = saved ? JSON.parse(saved) : {}

const tmdbId = ref(savedState.tmdb_id || '')
const running = ref(false)
const pushing = ref(false)
const taskId = ref('')
const logs = ref<LogEntry[]>([])
const result = ref<SplitResult | null>(null)
const activeTab = ref('logs')
const logBoxRef = ref<HTMLElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

const runParams = reactive({
  language: savedState.language || 'zh-CN',
  source: savedState.source || 'https://raw.githubusercontent.com/wikrin/CureTMDb/main/tv.json',
  use_source: savedState.use_source ?? false,
  priority: savedState.priority || 'tvdb, bangumi',
  force_reference: savedState.force_reference ?? false,
})

const priorityOptions = ['tvdb, bangumi', 'bangumi, tvdb', '仅 tvdb', '仅 bangumi']

// 仓库推送：Gitea / GitHub 两套独立配置（在系统设置维护），路径按目标分别记忆
type RepoProvider = 'gitea' | 'github'
const pushProvider = ref<RepoProvider>((savedState.push_provider as RepoProvider) || 'gitea')
const providerFilePaths = reactive<Record<RepoProvider, string>>({
  gitea: savedState.gitea_file_path || '',
  github: savedState.github_file_path || '',
})
const giteaFilePath = ref(providerFilePaths[pushProvider.value] || '')
const giteaEntries = ref<{ path: string; type: string }[]>([])
const conflictDialog = reactive({ show: false, info: '' })
const pathLabel = computed(() =>
  `渲染词文件路径（${pushProvider.value === 'github' ? 'GitHub' : 'Gitea'} 仓库内）`)
// 渲染词可编辑：生成结果载入后可直接修改，推送/复制/导出均使用编辑后的文本
const renderWordsEdit = ref('')
const renderWordsEdited = computed(() => renderWordsEdit.value !== (result.value?.render_words ?? ''))

function resetRenderWords() {
  renderWordsEdit.value = result.value?.render_words || ''
}

// 下拉项用纯字符串（v-combobox 对对象项的选中行为不可靠）：
// 目录显示为「📁 路径/」，value 即该字符串，选中后由 cleanPath 还原真实路径
const giteaItems = computed(() =>
  giteaEntries.value.map((e) => {
    if (e.type !== 'dir') return e.path
    const name = e.path.split('/').pop() || e.path
    return `📁 ${name}/`
  }),
)

/** 还原真实路径：去掉下拉项的 📁 前缀，兼容非字符串输入 */
function cleanPath(v: unknown): string {
  if (typeof v !== 'string') return ''
  return v.trim().replace(/^📁\s*/, '')
}

/**
 * 由当前路径推导要列出的目录：
 * - 路径以 / 结尾 → 正在浏览该目录，列出其内部
 * - 文件路径 → 列出其所在目录
 * - 空 → 仓库根目录
 */
function listDirFor(cur: string): string {
  const v = cleanPath(cur)
  if (v.endsWith('/')) return v.replace(/\/+$/, '')
  if (!v) return ''
  return v.includes('/') ? v.slice(0, v.lastIndexOf('/')) : ''
}

// 输入变化持久化，下次进入自动恢复
watch([tmdbId, runParams, pushProvider, providerFilePaths], () => {
  localStorage.setItem('lens_cure_splitter', JSON.stringify({
    tmdb_id: tmdbId.value,
    ...runParams,
    push_provider: pushProvider.value,
    gitea_file_path: providerFilePaths.gitea,
    github_file_path: providerFilePaths.github,
  }))
}, { deep: true })

const logCount = computed(() => logs.value.length)

const mapRows = computed(() =>
  (result.value?.episode_rows || []).map((r) => ({
    season: `S${String(r.season).padStart(2, '0')}`,
    episode: `E${String(r.episode).padStart(2, '0')}`,
    org_season: `S${String(r.org_season ?? 0).padStart(2, '0')}`,
    org_episode: r.org_episode != null ? `E${String(r.org_episode).padStart(2, '0')}` : '—',
    type: r.type,
    air_date: r.air_date || '—',
    name: r.name || '',
  })),
)

const definitionRows = computed(() => result.value?.definition_rows || [])
const seasonRows = computed(() => result.value?.season_rows || [])

const definitionHeaders = [
  { title: '季号', key: 'season_number', sortable: true },
  { title: '季名称', key: 'name' },
  { title: '定义集数', key: 'episode_count', sortable: true },
  { title: 'include 定义', key: 'include_desc' },
]
const seasonHeaders = [
  { title: '虚拟季号', key: 'season_number', sortable: true },
  { title: '季名称', key: 'name' },
  { title: '集数', key: 'episode_count', sortable: true },
  { title: '首播日期', key: 'air_date' },
]
const mapHeaders = [
  { title: '虚拟季', key: 'season' },
  { title: '虚拟集', key: 'episode' },
  { title: '原始季', key: 'org_season' },
  { title: '原始集', key: 'org_episode' },
  { title: '类型', key: 'type' },
  { title: '播出日期', key: 'air_date' },
  { title: '标题', key: 'name' },
]

// ── 拆分任务 ──────────────────────────────────────────────

function appendLog(level: string, message: string) {
  logs.value.push({
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    level,
    message,
  })
  scrollToLog()
}

function scrollToLog() {
  nextTick(() => {
    const el = logBoxRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function startSplit() {
  const id = parseInt(tmdbId.value)
  if (!id || id <= 0) { warning('请输入有效的 TMDB ID（数字）'); return }
  running.value = true
  logs.value = []
  result.value = null
  taskId.value = ''
  activeTab.value = 'logs'
  try {
    const res = await cureSplitterApi.startSplit({ tmdb_id: id, ...runParams })
    taskId.value = res.task_id
    appendLog('INFO', `任务已创建（${res.task_id}），正在拆分…`)
    stopPoll()
    pollTimer = setInterval(poll, 1500)
    await poll()
  } catch (e: any) {
    showError(e.message || '任务创建失败')
    running.value = false
  }
}

async function poll() {
  if (!taskId.value) return
  try {
    const st = await cureSplitterApi.taskStatus(taskId.value)
    logs.value = st.logs
    scrollToLog()
    if (st.status === 'done') {
      stopPoll()
      await loadResult()
    } else if (st.status === 'failed') {
      stopPoll()
      running.value = false
      showError(st.error || '拆分失败，详见日志')
    }
  } catch { /* 轮询失败静默重试 */ }
}

async function loadResult() {
  try {
    const res = await cureSplitterApi.taskResult(taskId.value)
    result.value = res
    renderWordsEdit.value = res.render_words || ''
    running.value = false
    activeTab.value = 'words'
    if (res.split_done) {
      success(`拆分完成：${res.title}（共 ${res.season_rows.length} 个虚拟季）`)
    } else {
      info(`已按 finale 分组生成剧集组/渲染词：${res.title}`)
    }
  } catch (e: any) {
    running.value = false
    showError('获取结果失败: ' + (e.message || '未知错误'))
  }
}

// ── Gitea 推送 ────────────────────────────────────────────

async function refreshGiteaFiles() {
  const dir = listDirFor(giteaFilePath.value)
  try {
    const res = await cureSplitterApi.listGiteaFiles(dir, pushProvider.value)
    giteaEntries.value = res.files || []
    if (!giteaEntries.value.length) {
      info(`目录「${dir || '/'}」下没有内容（或目录不存在）`)
    } else {
      const dirCount = giteaEntries.value.filter((e) => e.type === 'dir').length
      success(dirCount
        ? `已列出 ${giteaEntries.value.length} 项（${dirCount} 个目录，点文件夹可进入）`
        : `已列出 ${giteaEntries.value.length} 个文件`)
    }
  } catch (e: any) {
    showError(e.message || '获取文件列表失败')
  }
}

// 切换推送目标：记住当前路径、切到目标仓库各自的路径，需重新刷新列表
watch(pushProvider, (nv, ov) => {
  providerFilePaths[ov] = cleanPath(giteaFilePath.value)
  giteaFilePath.value = providerFilePaths[nv] || ''
  giteaEntries.value = []
})

// 选中目录项（📁 前缀、以 / 结尾）→ 自动进入该目录刷新列表
watch(giteaFilePath, (v) => {
  providerFilePaths[pushProvider.value] = cleanPath(v)
  if (typeof v === 'string' && cleanPath(v).endsWith('/')) refreshGiteaFiles()
})

async function pushGitea(forceManual = false) {
  const content = renderWordsEdit.value.trim()
  if (!content) { warning('当前没有可推送的渲染词，请先完成一次拆分'); return }
  const path = cleanPath(giteaFilePath.value)
  if (!path) { warning('请先填写或选择渲染词文件路径'); return }
  if (path.endsWith('/')) { warning('推送目标必须是文件，请进入目录后选择具体文件'); return }
  pushing.value = true
  try {
    const res = await cureSplitterApi.pushToGitea({
      task_id: taskId.value,
      file_path: path,
      force_manual: forceManual,
      content: renderWordsEdit.value,
      provider: pushProvider.value,
    })
    if (res.action === 'conflict') {
      conflictDialog.info = res.info || ''
      conflictDialog.show = true
      return
    }
    appendLog('INFO', `Gitea 推送成功: ${res.message || res.action}（提交 ${res.commit?.slice(0, 7) || '未知'}）`)
    success(res.message || '渲染词已推送到 Gitea')
  } catch (e: any) {
    appendLog('ERROR', `Gitea 推送失败: ${e.message || e}`)
    showError(e.message || 'Gitea 推送失败')
  } finally {
    pushing.value = false
  }
}

async function pushSytmdb() {
  if (!result.value?.group_json?.groups?.length) { warning('当前没有可写入的剧集组，请先完成一次拆分'); return }
  pushing.value = true
  try {
    const res = await cureSplitterApi.writeToSytmdb(taskId.value)
    appendLog('INFO', `SYTMDB 写入 TMDB ${res.tmdb_id} 剧集组（${res.groups} 组）: ${res.message}`)
    if (res.ok) success(`剧集组已覆盖写入 SYTMDB（${res.groups} 组）`)
    else warning(`SYTMDB 返回: ${res.message}`)
  } catch (e: any) {
    appendLog('ERROR', `SYTMDB 写入失败: ${e.message || e}`)
    showError(e.message || 'SYTMDB 写入失败')
  } finally {
    pushing.value = false
  }
}

// ── 复制 / 导出 ───────────────────────────────────────────

function downloadText(name: string, text: string, mime = 'text/plain;charset=utf-8') {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function copyWords() {
  const text = renderWordsEdit.value.trim()
  if (!text) { warning('当前没有可复制的渲染词'); return }
  copyToClipboard(text)
  success('渲染词已复制到剪贴板')
}

function exportWords() {
  const text = renderWordsEdit.value.trim()
  if (!text) { warning('当前没有可导出的渲染词'); return }
  downloadText(`render_words_${result.value?.tmdb_id}.txt`, text + '\n')
  success('渲染词 TXT 已导出')
}

function exportMapping() {
  const data = result.value?.mapping_json
  if (!data) { warning('当前没有可导出的映射结果'); return }
  downloadText(`mapping_${result.value?.tmdb_id}.json`, JSON.stringify(data, null, 2), 'application/json')
  success('映射 JSON 已导出')
}

function exportLogic() {
  const data = result.value?.logic_json
  if (!data) { warning('当前没有可导出的逻辑季结果'); return }
  downloadText(`logic_series_${result.value?.tmdb_id}.json`, JSON.stringify(data, null, 2), 'application/json')
  success('完整逻辑 JSON 已导出')
}

function copyMapping() {
  const data = result.value?.mapping_json
  if (!data) { warning('当前没有可复制的映射结果'); return }
  copyToClipboard(JSON.stringify(data, null, 2))
  success('映射 JSON 已复制到剪贴板')
}

const groupJsonText = computed(() =>
  result.value?.group_json ? JSON.stringify(result.value.group_json, null, 2) : '',
)

function copyGroup() {
  if (!groupJsonText.value) { warning('当前没有可复制的剧集组'); return }
  copyToClipboard(groupJsonText.value)
  success('剧集组 JSON 已复制到剪贴板')
}

// ── 初始化 ────────────────────────────────────────────────

onMounted(async () => {
  // 渲染词文件路径默认取系统设置（Gitea / GitHub 各自的集成配置）
  try {
    const cfg: any = await configApi.getCurrent()
    providerFilePaths.gitea = providerFilePaths.gitea || cfg?.gitea?.file_path || ''
    providerFilePaths.github = providerFilePaths.github || cfg?.github?.file_path || ''
    if (!giteaFilePath.value) {
      giteaFilePath.value = providerFilePaths[pushProvider.value] || ''
    }
  } catch { /* ignore */ }
})

onBeforeUnmount(stopPoll)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-television-classic</v-icon>
      番剧分季拆分
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">
      读取分季定义（规则表 → TVDB → Bangumi），仅当 TMDB 某季实际集数超出定义时拆分重灌，产出渲染词与剧集组。
      接口 Key 等集成配置请在「设置 → 第三方 API 集成」维护。
    </p>

    <v-row>
      <!-- 左侧：运行参数 -->
      <v-col cols="12" md="4">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-tune</v-icon>
            运行参数
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-select
              v-model="runParams.priority"
              :items="priorityOptions"
              label="参照优先级" variant="outlined" density="compact" class="mb-3" hide-details
            />
            <v-text-field
              v-model="runParams.language"
              label="TMDB 语言" variant="outlined" density="compact" class="mb-3" hide-details
            />
            <v-text-field
              v-model="runParams.source"
              label="外部分季规则表（URL / 本地 JSON 路径）"
              variant="outlined" density="compact" class="mb-1" hide-details
              :disabled="!runParams.use_source"
            />
            <v-switch v-model="runParams.use_source" color="primary" density="compact" hide-details>
              <template #label>
                <span class="text-body-2">启用外部分季规则表（优先级最高）</span>
              </template>
            </v-switch>
            <p class="text-caption text-medium-emphasis mb-2">
              规则表命中直接作为分季定义；关闭则跳过规则表，按优先级走 TVDB / Bangumi。
            </p>
            <v-switch v-model="runParams.force_reference" color="primary" density="compact" hide-details>
              <template #label>
                <span class="text-body-2">忽略自动参照条件（强制尝试）</span>
              </template>
            </v-switch>
            <p class="text-caption text-medium-emphasis mb-1">
              自动参照默认仅处理"日本动画且有效季数 1~2"的剧集；开启后不满足条件（非日漫 / 有效季数≥3 等）也强制尝试 TVDB / Bangumi。
            </p>
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-information-outline</v-icon>
            拆分流程
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p class="mb-1">1. CureTMDb 规则表命中 → 直接作为分季定义</p>
            <p class="mb-1">2. 否则（日本动画且有效季数 1~2）按优先级尝试 TVDB / Bangumi</p>
            <p class="mb-1">3. 仅当 TMDB 某季实际集数 &gt; 定义集数时才拆分</p>
            <p class="mb-1">4. 拉全原始集 → 同日跨季去重 → 按播出日期摊平</p>
            <p class="mb-1">5. 按定义逐季重灌：集号从 1 重排，切出虚拟季</p>
            <p class="mb-1">6. 生成分季渲染词 + 剧集组 JSON；无需拆分时按季结局(finale)兜底分组</p>
            <p>7. 渲染词页可一键推送到 Gitea：自动替换文件中同 TMDB ID 的 [自动分季] 区块</p>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧：操作与结果 -->
      <v-col cols="12" md="8">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-text class="pa-4 d-flex align-center control-row">
            <v-text-field
              v-model="tmdbId"
              label="TMDB ID"
              placeholder="例如 240411（胆大党）"
              variant="outlined" density="compact"
              max-width="260"
              hide-details
              :disabled="running"
              @keyup.enter="startSplit"
            />
            <v-btn
              color="primary" variant="tonal"
              prepend-icon="mdi-play-circle-outline"
              :loading="running"
              @click="startSplit"
            >
              {{ running ? '拆分中…' : '开始拆分' }}
            </v-btn>
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-tabs v-model="activeTab" class="mb-1">
            <v-tab value="logs"><v-icon start size="18">mdi-text</v-icon>日志</v-tab>
            <v-tab value="definition"><v-icon start size="18">mdi-format-list-numbered</v-icon>分季定义</v-tab>
            <v-tab value="seasons"><v-icon start size="18">mdi-television-box</v-icon>虚拟季</v-tab>
            <v-tab value="mapping"><v-icon start size="18">mdi-swap-vertical</v-icon>逐集映射</v-tab>
            <v-tab value="words"><v-icon start size="18">mdi-text-box-check-outline</v-icon>渲染词</v-tab>
            <v-tab value="group"><v-icon start size="18">mdi-code-json</v-icon>剧集组</v-tab>
          </v-tabs>
          <v-divider />
          <v-window v-model="activeTab">
            <!-- 日志 -->
            <v-window-item value="logs">
              <div ref="logBoxRef" class="log-box pa-4">
                <div v-if="logs.length === 0" class="text-body-2 text-medium-emphasis">暂无日志</div>
                <div v-for="(l, i) in logs" :key="i" class="log-line">
                  <span class="log-time">[{{ l.time }}]</span>
                  <span :class="`log-${l.level}`">[{{ l.level }}]</span>
                  {{ l.message }}
                </div>
              </div>
            </v-window-item>

            <!-- 分季定义 -->
            <v-window-item value="definition">
              <v-data-table
                :headers="definitionHeaders" :items="definitionRows"
                density="compact" class="transparent-table"
                items-per-page-text="每页条数"
                no-data-text="暂无分季定义，请先完成一次拆分"
              />
            </v-window-item>

            <!-- 虚拟季 -->
            <v-window-item value="seasons">
              <v-data-table
                :headers="seasonHeaders" :items="seasonRows"
                density="compact" class="transparent-table"
                items-per-page-text="每页条数"
                no-data-text="暂无虚拟季，请先完成一次拆分"
              />
            </v-window-item>

            <!-- 逐集映射 -->
            <v-window-item value="mapping">
              <v-data-table
                :headers="mapHeaders" :items="mapRows"
                density="compact" class="transparent-table"
                items-per-page-text="每页条数"
                no-data-text="暂无逐集映射，请先完成一次拆分"
              >
                <template #item.name="{ item }">
                  <span class="text-truncate d-inline-block" style="max-width: 260px">{{ item.name }}</span>
                </template>
              </v-data-table>
            </v-window-item>

            <!-- 渲染词 -->
            <v-window-item value="words">
              <div class="pa-4">
                <div class="d-flex align-center mb-3 control-row">
                  <v-select
                    v-model="pushProvider"
                    :items="[{ title: 'Gitea', value: 'gitea' }, { title: 'GitHub', value: 'github' }]"
                    item-title="title" item-value="value"
                    label="推送目标"
                    variant="outlined" density="compact" hide-details
                    style="max-width: 130px; flex-shrink: 0"
                  />
                  <v-combobox
                    v-model="giteaFilePath"
                    :items="giteaItems"
                    :label="pathLabel"
                    variant="outlined" density="compact" hide-details
                    placeholder="anime/animeifre.txt"
                    class="flex-grow-1"
                  />
                  <v-tooltip text="列出当前目录内容，点文件夹可逐级进入" location="top">
                    <template #activator="{ props: tipProps }">
                      <v-btn v-bind="tipProps" icon="mdi-refresh" variant="tonal" size="small" @click="refreshGiteaFiles" />
                    </template>
                  </v-tooltip>
                  <v-btn
                    color="primary" variant="tonal" prepend-icon="mdi-cloud-upload-outline"
                    :loading="pushing" @click="pushGitea(false)"
                  >
                    推送到仓库
                  </v-btn>
                  <v-btn
                    v-if="renderWordsEdited"
                    variant="text" prepend-icon="mdi-restore" size="small"
                    @click="resetRenderWords"
                  >
                    还原
                  </v-btn>
                </div>
                <p class="text-caption text-medium-emphasis mb-2">
                  推送目标可选 Gitea / GitHub（在「设置 → 第三方 API 集成」分别配置，路径各自记忆）；渲染词可直接编辑，修改后的内容用于复制/导出/推送。按头部 TMDB 编号定位：同号 [自动分季] 区块原位替换，无则追加文末。刷新后点 📁 文件夹可逐级进入。
                </p>
                <v-textarea
                  v-model="renderWordsEdit"
                  :rows="12" auto-grow
                  variant="outlined" density="compact" hide-details
                  placeholder="拆分完成后，渲染词会出现在这里（可直接编辑）"
                  class="monospace-text"
                />
              </div>
            </v-window-item>

            <!-- 剧集组 -->
            <v-window-item value="group">
              <div class="pa-4">
                <div class="d-flex align-center mb-3 control-row">
                  <v-btn variant="tonal" prepend-icon="mdi-content-copy" @click="copyGroup">复制剧集组 JSON</v-btn>
                  <v-btn
                    color="primary" variant="tonal" prepend-icon="mdi-database-export-outline"
                    :loading="pushing" @click="pushSytmdb"
                  >
                    写入 SYTMDB（覆盖）
                  </v-btn>
                </div>
                <p class="text-caption text-medium-emphasis mb-2">
                  覆盖写入 SYTMDB /api/tv/{TMDB ID}/episodegroup，文件不存在会先创建；服务地址与 Token 在系统设置维护。
                </p>
                <v-textarea
                  :model-value="groupJsonText"
                  readonly :rows="12" auto-grow
                  variant="outlined" density="compact" hide-details
                  placeholder="剧集组 JSON 会出现在这里"
                  class="monospace-text"
                />
              </div>
            </v-window-item>
          </v-window>
          <v-divider />
          <div class="pa-4 d-flex flex-wrap ga-2">
            <v-btn size="small" variant="tonal" prepend-icon="mdi-content-copy" @click="copyWords">复制渲染词</v-btn>
            <v-btn size="small" variant="tonal" prepend-icon="mdi-file-download-outline" @click="exportWords">导出渲染词 TXT</v-btn>
            <v-btn size="small" variant="tonal" prepend-icon="mdi-code-json" @click="exportMapping">导出映射 JSON</v-btn>
            <v-btn size="small" variant="tonal" prepend-icon="mdi-code-braces" @click="exportLogic">导出完整逻辑 JSON</v-btn>
            <v-btn size="small" variant="tonal" prepend-icon="mdi-clipboard-text-outline" @click="copyMapping">复制映射</v-btn>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- 手动区块冲突确认 -->
    <v-dialog v-model="conflictDialog.show" max-width="460">
      <v-card rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start color="warning">mdi-alert-outline</v-icon>
          发现手动区块
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4 text-body-2">
          该 TMDB ID 已出现在手动维护的区块「{{ conflictDialog.info }}」中（头部没有 [自动分季] 标记）。
          是否用本次拆分结果替换该手动区块？
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-3">
          <v-spacer />
          <v-btn variant="text" @click="conflictDialog.show = false">取消</v-btn>
          <v-btn color="warning" variant="tonal" @click="conflictDialog.show = false; pushGitea(true)">替换并推送</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<style scoped>
.log-box {
  max-height: 520px;
  overflow-y: auto;
  font-family: Consolas, 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.7;
}
.log-time {
  opacity: 0.6;
  margin-right: 6px;
}
.log-INFO { color: inherit; }
.log-WARN { color: #d97706; }
.log-ERROR { color: #ef4444; }
.log-DEBUG { opacity: 0.55; }
.monospace-text :deep(textarea) {
  font-family: Consolas, 'Courier New', monospace;
}
.transparent-table {
  background: transparent;
}
</style>
