<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

// ========== 规则管理 ==========
const rules = ref<any[]>([])
const loading = ref(false)

async function fetchRules() {
  loading.value = true
  try {
    const data = await toolkitApi.autotags.getRules()
    rules.value = Array.isArray(data) ? data : []
  } catch {
    rules.value = []
  } finally {
    loading.value = false
  }
}

async function saveRules(newRules: any[]) {
  try {
    await toolkitApi.autotags.saveRules(newRules)
    success('规则已持久化')
    rules.value = newRules
    return true
  } catch {
    showError('保存规则失败')
    return false
  }
}

// ========== Webhook 配置 ==========
const whConfig = reactive({
  enabled: true,
  secret_token: '',
  automation_enabled: true,
  delay_seconds: 10,
  write_mode: 'merge'
})

const webhookUrl = computed(() => {
  const base = window.location.origin
  return `${base}/api/autotags/webhook/${whConfig.secret_token}`
})

async function loadWebhookConfig() {
  try {
    const data = await toolkitApi.autotags.getWebhookConfig()
    if (data) Object.assign(whConfig, data)
  } catch { /* ignore */ }
}

async function saveWH() {
  try {
    await toolkitApi.autotags.saveWebhookConfig(whConfig)
    success('Webhook 配置已更新')
  } catch {
    showError('保存 Webhook 配置失败')
  }
}

function copyUrl() {
  navigator.clipboard.writeText(webhookUrl.value).then(() => {
    success('URL 已成功复制到剪贴板')
  }).catch(() => {
    showError('复制失败，请手动选取')
  })
}

// ========== 规则编辑 ==========
const showEditor = ref(false)
const isNew = ref(false)
const editingIndex = ref(-1)
const editingRule = ref<any>({})

const COUNTRY_OPTIONS = [
  { title: "爱尔兰", value: "IE" }, { title: "澳大利亚", value: "AU" },
  { title: "巴西", value: "BR" }, { title: "比利时", value: "BE" },
  { title: "波兰", value: "PL" }, { title: "丹麦", value: "DK" },
  { title: "德国", value: "DE" }, { title: "俄罗斯", value: "RU" },
  { title: "法国", value: "FR" }, { title: "韩国", value: "KR" },
  { title: "荷兰", value: "NL" }, { title: "加拿大", value: "CA" },
  { title: "美国", value: "US" }, { title: "墨西哥", value: "MX" },
  { title: "挪威", value: "NO" }, { title: "日本", value: "JP" },
  { title: "瑞典", value: "SE" }, { title: "沙特阿拉伯", value: "SA" },
  { title: "泰国", value: "TH" }, { title: "西班牙", value: "ES" },
  { title: "意大利", value: "IT" }, { title: "印度", value: "IN" },
  { title: "英国", value: "GB" }, { title: "中国澳门", value: "MO" },
  { title: "中国大陆", value: "CN" }, { title: "中国台湾", value: "TW" },
  { title: "中国香港", value: "HK" }
]

const GENRE_OPTIONS = [
  { title: "爱情", value: "10749" }, { title: "电视电影", value: "10770" },
  { title: "动画", value: "16" }, { title: "动作", value: "28" },
  { title: "动作冒险", value: "10759" }, { title: "儿童", value: "10762" },
  { title: "犯罪", value: "80" }, { title: "肥皂剧", value: "10766" },
  { title: "纪录片", value: "99" }, { title: "家庭", value: "10751" },
  { title: "惊悚", value: "53" }, { title: "剧情", value: "18" },
  { title: "科幻", value: "878" }, { title: "科幻奇幻", value: "10765" },
  { title: "恐怖", value: "27" }, { title: "历史", value: "36" },
  { title: "冒险", value: "12" }, { title: "奇幻", value: "14" },
  { title: "脱口秀", value: "10767" }, { title: "西部", value: "37" },
  { title: "喜剧", value: "35" }, { title: "新闻", value: "10763" },
  { title: "悬疑", value: "9648" }, { title: "音乐", value: "10402" },
  { title: "战争", value: "10752" }, { title: "战争政治", value: "10768" },
  { title: "真人秀", value: "10764" }
]

const ITEM_TYPE_OPTIONS = [
  { title: '全部', value: 'all' },
  { title: '仅电影', value: 'movie' },
  { title: '仅剧集', value: 'series' }
]

function prepareNewRule() {
  isNew.value = true
  editingRule.value = {
    name: '', tag: '', item_type: 'all', match_all_conditions: false, is_negative_match: false,
    conditions: { countries: [], genres: [], years_text: '' }
  }
  showEditor.value = true
}

function openEditor(index: number) {
  isNew.value = false
  editingIndex.value = index
  editingRule.value = JSON.parse(JSON.stringify(rules.value[index]))
  showEditor.value = true
}

async function onRuleSave(rule: any) {
  const newRules = [...rules.value]
  if (isNew.value) newRules.push(rule)
  else newRules[editingIndex.value] = rule
  if (await saveRules(newRules)) showEditor.value = false
}

async function handleDeleteRule(index: number) {
  const ok = await confirm({ title: '删除规则', content: '确认删除此规则？', confirmColor: 'error' })
  if (!ok) return
  const newRules = [...rules.value]
  newRules.splice(index, 1)
  await saveRules(newRules)
}

// ========== 拖拽排序 ==========
const draggedIndex = ref<number | null>(null)

function onDragStart(index: number) {
  draggedIndex.value = index
}

function onDragEnter(index: number) {
  if (draggedIndex.value === null || draggedIndex.value === index) return
  const newRules = [...rules.value]
  const item = newRules.splice(draggedIndex.value, 1)[0]
  newRules.splice(index, 0, item)
  rules.value = newRules
  draggedIndex.value = index
}

async function onDrop() {
  draggedIndex.value = null
  await saveRules(rules.value)
}

// ========== 任务面板 ==========
const taskForm = reactive({
  mode: 'merge',
  library_type: 'all',
  use_custom: false,
  custom_tags_text: ''
})

async function startTask() {
  const ok = await confirm({
    title: '确认启动任务',
    content: '任务将在后台执行，每一项媒体都会调用 TMDB 进行精准元数据匹配。确认开始？'
  })
  if (!ok) return
  const customTags = taskForm.use_custom
    ? taskForm.custom_tags_text.split(',').map(t => t.trim()).filter(t => t)
    : null
  try {
    await toolkitApi.autotags.execute({
      mode: taskForm.mode,
      library_type: taskForm.library_type,
      custom_tags: customTags
    })
    success('后台任务已排队')
  } catch {
    showError('启动失败')
  }
}

// ========== 维护面板 ==========
const testId = ref('')
const testTag = ref('测试')

async function testWrite() {
  if (!testId.value.trim()) {
    showError('请输入 Emby ID')
    return
  }
  try {
    const res = await toolkitApi.autotags.testWrite(testId.value.trim(), testTag.value)
    if (res?.success !== false) success('写入指令已发送')
    else showError('写入测试失败')
  } catch {
    showError('写入测试失败')
  }
}

async function clearAll() {
  const ok = await confirm({
    title: '危险：清空所有标签',
    content: '此操作将永久移除库中所有电影/剧集的标签。确认执行？',
    confirmColor: 'error'
  })
  if (!ok) return
  try {
    await toolkitApi.autotags.clearAll()
    success('清空任务已启动')
  } catch {
    showError('启动失败')
  }
}

async function clearSpecific() {
  const ok = await confirm({
    title: '移除特定标签',
    content: '请输入要移除的标签名（多个用逗号分隔）：',
    confirmColor: 'warning'
  })
  if (!ok) return
  // 简化：直接使用 prompt 风格的确认
  try {
    await toolkitApi.autotags.clearSpecific({ tags: [] })
    success('清除任务已启动')
  } catch {
    showError('启动失败')
  }
}

// ========== 规则卡片辅助 ==========
function getTypeLabel(type: string) {
  const map: any = { all: '全部', movie: '仅电影', series: '仅剧集' }
  return map[type] || '全部'
}

function getSummaryText(rule: any) {
  const c = rule.conditions
  const parts = []
  if (c.countries?.length) parts.push(`地区: ${c.countries.join('/')}`)
  if (c.genres?.length) parts.push(`流派: ${c.genres.join('/')}`)
  if (c.years_text) parts.push(`年份: ${c.years_text}`)
  return parts.join(' | ') || '无限制条件'
}

onMounted(() => {
  fetchRules()
  loadWebhookConfig()
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-tag-multiple-outline</v-icon>
      自动标签助手
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">基于规则全自动维护 Emby 媒体标签。支持实时 Webhook 联动自动化。</p>

    <v-row>
      <!-- 左侧：规则与核心配置 -->
      <v-col cols="12" md="7">
        <!-- Webhook 实时自动化配置面板 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon start>mdi-webhook</v-icon>
            Webhook 实时自动化
            <v-spacer />
            <v-switch v-model="whConfig.enabled" @update:model-value="saveWH" density="compact" hide-details color="primary" />
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div class="d-flex ga-3 mb-3 align-center">
              <v-text-field :model-value="webhookUrl" label="Webhook URL" variant="outlined" density="compact" readonly hide-details />
              <v-btn color="primary" variant="tonal" @click="copyUrl" size="small">复制 URL</v-btn>
            </div>

            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              在 Emby 后台添加此 URL，选择 <strong>application/json</strong> 类型，并勾选 <strong>"已添加新媒体"</strong> 事件。
            </v-alert>

            <v-row>
              <v-col cols="12" sm="6">
                <v-text-field v-model="whConfig.secret_token" label="安全密钥" variant="outlined" density="compact"
                  placeholder="自定义 Token" @blur="saveWH" hide-details />
              </v-col>
              <v-col cols="12" sm="6">
                <v-select v-model="whConfig.write_mode" :items="[
                  { title: '合并现有标签', value: 'merge' },
                  { title: '覆盖所有标签', value: 'overwrite' }
                ]" label="写入模式" variant="outlined" density="compact" @update:model-value="saveWH" hide-details />
              </v-col>
            </v-row>

            <v-checkbox v-model="whConfig.automation_enabled" @update:model-value="saveWH" density="compact" hide-details class="mt-2">
              <template #label>
                <span class="text-body-2">接收到 item.added 事件时自动执行规则比对</span>
              </template>
            </v-checkbox>
          </v-card-text>
        </v-card>

        <!-- 规则列表 -->
        <div class="d-flex align-center justify-space-between mb-3">
          <div class="d-flex align-center ga-2">
            <span class="text-subtitle-2 font-weight-bold">打标签规则列表</span>
            <span class="text-caption text-medium-emphasis">按住 ⠿ 拖拽调整顺序</span>
          </div>
          <v-btn type="primary" size="small" variant="tonal" @click="prepareNewRule" prepend-icon="mdi-plus">添加新规则</v-btn>
        </div>

        <div class="rules-grid" @dragover.prevent @drop="onDrop">
          <v-card v-for="(rule, index) in rules" :key="index"
            class="liquid-glass-card rule-card mb-3" rounded="lg"
            :class="{ 'is-dragging': draggedIndex === index }"
            draggable="true"
            @dragstart="onDragStart(index)"
            @dragenter="onDragEnter(index)"
            @click="openEditor(index)">
            <v-card-title class="d-flex align-center pa-3 text-subtitle-2">
              <v-icon start size="16" class="drag-handle mr-2">mdi-drag</v-icon>
              {{ rule.name }}
              <v-spacer />
              <v-btn icon variant="text" size="x-small" color="error" @click.stop="handleDeleteRule(index)">
                <v-icon size="16">mdi-delete-outline</v-icon>
              </v-btn>
            </v-card-title>
            <v-card-text class="pa-3 pt-0">
              <div class="d-flex align-center ga-2 mb-1">
                <v-chip size="small" variant="tonal" color="primary">{{ rule.tag }}</v-chip>
                <span class="text-caption text-medium-emphasis">[{{ getTypeLabel(rule.item_type) }}]</span>
              </div>
              <p class="text-caption text-medium-emphasis mb-0">{{ getSummaryText(rule) }}</p>
            </v-card-text>
          </v-card>

          <div v-if="!rules.length" class="text-center py-8 text-medium-emphasis">
            <v-icon size="48" color="grey" class="mb-2">mdi-tag-off-outline</v-icon>
            <p>尚未配置任何规则</p>
          </div>
        </div>
      </v-col>

      <!-- 右侧：控制与工具 -->
      <v-col cols="12" md="5">
        <!-- 任务面板 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-play-circle-outline</v-icon>
            一键打标签任务
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <p class="text-caption text-medium-emphasis mb-3">此功能将遍历媒体库，应用预设规则或自定义标签</p>

            <v-radio-group v-model="taskForm.mode" density="compact" hide-details class="mb-2">
              <template #label><span class="text-body-2">写入模式:</span></template>
              <v-radio value="merge" label="合并现有标签" />
              <v-radio value="overwrite" label="覆盖所有标签" />
            </v-radio-group>

            <v-radio-group v-model="taskForm.library_type" density="compact" hide-details class="mb-3">
              <template #label><span class="text-body-2">库类型:</span></template>
              <v-radio value="all" label="全库媒体" />
              <v-radio value="favorite" label="仅收藏项" />
            </v-radio-group>

            <v-checkbox v-model="taskForm.use_custom" density="compact" hide-details class="mb-2">
              <template #label><span class="text-body-2">使用固定标签内容 (不走自动匹配规则)</span></template>
            </v-checkbox>
            <v-text-field v-if="taskForm.use_custom" v-model="taskForm.custom_tags_text"
              placeholder="请输入标签名，多个用英文逗号分隔" variant="outlined" density="compact" hide-details class="mb-3" />

            <v-btn color="primary" variant="flat" block @click="startTask">执行打标签任务</v-btn>
          </v-card-text>
        </v-card>

        <!-- 维护面板 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-wrench-outline</v-icon>
            辅助维护工具
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div class="d-flex ga-2 mb-4">
              <v-btn size="small" variant="tonal" color="warning" @click="clearSpecific">清除指定标签</v-btn>
              <v-btn size="small" variant="tonal" color="error" @click="clearAll">清空所有标签</v-btn>
            </div>

            <v-divider class="mb-4" />

            <p class="text-caption text-medium-emphasis mb-2">写入测试 (手动验证权限与解锁逻辑)</p>
            <div class="d-flex ga-2">
              <v-text-field v-model="testId" placeholder="Emby ID" variant="outlined" density="compact" hide-details style="max-width:120px" />
              <v-text-field v-model="testTag" placeholder="标签名" variant="outlined" density="compact" hide-details />
              <v-btn size="small" color="primary" variant="tonal" @click="testWrite">执行写入测试</v-btn>
            </div>
          </v-card-text>
        </v-card>

        <!-- 处理参数 -->
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-timer-outline</v-icon>
            处理参数
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-text-field v-model.number="whConfig.delay_seconds" label="处理延迟(秒)" variant="outlined" density="compact"
              type="number" min="0" max="3600" @blur="saveWH" hide-details class="mb-2" />
            <p class="text-caption text-medium-emphasis">延迟处理是为了等待 Emby 完成元数据刮削，确保标签匹配时各项属性已就绪。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 规则编辑弹窗 -->
    <v-dialog v-model="showEditor" max-width="650">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-tag-multiple-outline</v-icon>
          {{ isNew ? '添加新规则' : '编辑规则' }}
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-text-field v-model="editingRule.name" label="规则名称" variant="outlined" density="compact"
            placeholder="起个名字方便识别" class="mb-3" />
          <v-text-field v-model="editingRule.tag" label="生成的标签" variant="outlined" density="compact"
            placeholder="Emby 中将要显示的标签名" class="mb-3" />

          <v-select v-model="editingRule.conditions.countries" :items="COUNTRY_OPTIONS" multiple chips closable-chips
            label="国家/地区" variant="outlined" density="compact"
            placeholder="满足其中任一国家即可" class="mb-3" />

          <v-select v-model="editingRule.conditions.genres" :items="GENRE_OPTIONS" multiple chips closable-chips
            label="流派类型" variant="outlined" density="compact"
            placeholder="满足其中任一流派即可" class="mb-3" />

          <v-text-field v-model="editingRule.conditions.years_text" label="作用于年份" variant="outlined" density="compact"
            placeholder="例如: 2020, 2022 2024 或 1999-2020" class="mb-3" />

          <v-radio-group v-model="editingRule.item_type" density="compact" hide-details class="mb-3">
            <template #label><span class="text-body-2">作用对象:</span></template>
            <v-radio v-for="opt in ITEM_TYPE_OPTIONS" :key="opt.value" :value="opt.value" :label="opt.title" />
          </v-radio-group>

          <v-checkbox v-model="editingRule.match_all_conditions" density="compact" hide-details class="mb-1">
            <template #label><span class="text-body-2">严格匹配所有条件 (国家/地区和流派必须全部命中)</span></template>
          </v-checkbox>
          <v-checkbox v-model="editingRule.is_negative_match" density="compact" hide-details>
            <template #label><span class="text-body-2">负向匹配 (满足条件的项目将被排除，不满足才生效)</span></template>
          </v-checkbox>
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="text" @click="showEditor = false">取消</v-btn>
          <v-btn color="primary" variant="flat" @click="onRuleSave(editingRule)">保存规则</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<style scoped>
.rules-grid {
  min-height: 100px;
}

.rule-card {
  cursor: grab;
  transition: all 0.2s ease;
  border: 1px solid transparent;
}

.rule-card:active {
  cursor: grabbing;
}

.rule-card:hover {
  border-color: rgb(var(--v-theme-primary));
  transform: translateY(-2px);
}

.rule-card.is-dragging {
  opacity: 0.5;
  border: 1px dashed rgb(var(--v-theme-primary));
}

.drag-handle {
  cursor: grab;
  color: #666;
}

.drag-handle:hover {
  color: rgb(var(--v-theme-primary));
}
</style>
