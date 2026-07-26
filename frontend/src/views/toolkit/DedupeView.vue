<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError, info } = useNotification()
const { confirm } = useConfirm()

const loading = ref(false)
const syncing = ref(false)
const analyzing = ref(false)
const searchName = ref('')
const showOnlyDuplicates = ref(false)
const items = ref<any[]>([])
const selectedIds = ref<string[]>([])
const suggestedItems = ref<any[]>([])

// ========== 配置 ==========
const dedupeConfig = ref<any>({
  rules: { priority_order: [], values_weight: {}, tie_breaker: 'small_id' },
  exclude_paths: []
})
const showConfigDialog = ref(false)
const showConfirmDialog = ref(false)

// 配置表单
const configForm = ref({
  display_title: '',
  video_codec: '',
  video_range: ''
})
const configTieBreaker = ref('small_id')
const excludeText = ref('')

async function loadConfig() {
  try {
    const data = await toolkitApi.dedupe.getConfig()
    if (data?.rules) dedupeConfig.value = data
  } catch { /* ignore */ }
}

function openConfigDialog() {
  const vw = dedupeConfig.value.rules?.values_weight || {}
  configForm.value.display_title = (vw.display_title || []).join(', ')
  configForm.value.video_codec = (vw.video_codec || []).join(', ')
  configForm.value.video_range = (vw.video_range || []).join(', ')
  configTieBreaker.value = dedupeConfig.value.rules?.tie_breaker || 'small_id'
  excludeText.value = (dedupeConfig.value.exclude_paths || []).join('\n')
  showConfigDialog.value = true
}

async function saveConfig() {
  try {
    const configToSave = JSON.parse(JSON.stringify(dedupeConfig.value))
    configToSave.rules.values_weight = {
      display_title: configForm.value.display_title.split(',').map((s: string) => s.trim().toLowerCase()).filter((s: string) => s),
      video_codec: configForm.value.video_codec.split(',').map((s: string) => s.trim().toLowerCase()).filter((s: string) => s),
      video_range: configForm.value.video_range.split(',').map((s: string) => s.trim().toLowerCase()).filter((s: string) => s)
    }
    configToSave.rules.tie_breaker = configTieBreaker.value
    configToSave.exclude_paths = excludeText.value.split('\n').map((s: string) => s.trim()).filter((s: string) => s)
    await toolkitApi.dedupe.saveConfig(configToSave)
    dedupeConfig.value = configToSave
    success('规则已保存')
    showConfigDialog.value = false
  } catch {
    showError('保存配置失败')
  }
}

// ========== 列表与操作 ==========
function processItems(data: any[]) {
  return data.map((i: any) => ({
    ...i,
    isLeaf: i.item_type !== 'Series' && i.item_type !== 'Season'
  }))
}

async function loadItems() {
  loading.value = true
  selectedIds.value = []
  try {
    const data = await toolkitApi.dedupe.getItems({ query_text: searchName.value })
    items.value = processItems(Array.isArray(data) ? data : [])
  } catch {
    items.value = []
    showError('加载列表失败')
  } finally {
    loading.value = false
  }
}

async function toggleDuplicateMode() {
  showOnlyDuplicates.value = !showOnlyDuplicates.value
  if (showOnlyDuplicates.value) {
    loading.value = true
    selectedIds.value = []
    try {
      const data = await toolkitApi.dedupe.getDuplicates()
      items.value = processItems(Array.isArray(data) ? data : [])
    } catch {
      items.value = []
      showError('加载重复项失败')
    } finally {
      loading.value = false
    }
  } else {
    loadItems()
  }
}

async function syncMedia() {
  if (syncing.value) return
  try {
    syncing.value = true
    info('同步任务已在后台启动，完成后将自动刷新列表')
    await toolkitApi.dedupe.syncMedia()
    // 轮询状态
    const poll = setInterval(async () => {
      try {
        const status = await toolkitApi.dedupe.getSyncStatus()
        if (!status?.is_syncing) {
          clearInterval(poll)
          syncing.value = false
          success('Emby 媒体库同步已完成，列表已自动刷新')
          showOnlyDuplicates.value ? toggleDuplicateMode() : loadItems()
        }
      } catch {
        clearInterval(poll)
        syncing.value = false
      }
    }, 2000)
  } catch {
    syncing.value = false
    showError('启动同步任务失败')
  }
}

async function autoSelect() {
  analyzing.value = true
  try {
    const data = await toolkitApi.dedupe.smartSelect()
    const results = Array.isArray(data) ? data : []
    suggestedItems.value = results
    selectedIds.value = results.map((i: any) => i.id)
    if (results.length === 0) {
      info('未发现符合规则的可清理项目')
    }
  } catch {
    suggestedItems.value = []
    showError('算法执行失败')
  } finally {
    analyzing.value = false
  }
}

async function deleteSelected() {
  if (!selectedIds.value.length) return
  showConfirmDialog.value = true
}

async function confirmDelete() {
  try {
    const res = await toolkitApi.dedupe.deleteItems(selectedIds.value)
    success(`成功删除 ${res?.success ?? selectedIds.value.length} 个项目`)
    selectedIds.value = []
    showConfirmDialog.value = false
    showOnlyDuplicates.value ? toggleDuplicateMode() : loadItems()
  } catch {
    showError('删除失败')
  }
}

function toggleSelect(id: string) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function selectAll() {
  if (selectedIds.value.length === items.value.length) {
    selectedIds.value = []
  } else {
    selectedIds.value = items.value.map((i: any) => i.id || i.item_id)
  }
}

function formatEpisode(item: any) {
  const raw = item.raw_data || {}
  const s = raw.ParentIndexNumber
  const e = raw.IndexNumber
  if (s !== undefined && e !== undefined) return `S${String(s).padStart(2, '0')}E${String(e).padStart(2, '0')}`
  return '未知编号'
}

const typeMap: any = { Movie: '电影', Series: '剧集', Season: '季', Episode: '集' }
const colorMap: any = { Movie: 'success', Series: 'info', Season: 'warning', Episode: 'default' }

onMounted(() => {
  loadItems()
  loadConfig()
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-content-duplicate</v-icon>
      重复项清理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">扫描、分析并清理您的媒体库重复项，支持基于文件名与元数据的智能匹配。</p>

    <!-- 工具栏 -->
    <div class="d-flex ga-2 flex-wrap mb-4 align-center">
      <v-text-field v-model="searchName" prepend-inner-icon="mdi-magnify" placeholder="搜索名称..."
        variant="outlined" density="compact" hide-details clearable style="max-width:240px"
        @keydown.enter="loadItems" @click:clear="loadItems" />
      <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="loadItems" :loading="loading">刷新</v-btn>
      <v-btn prepend-icon="mdi-cloud-sync-outline" variant="tonal" color="info" size="small" @click="syncMedia" :loading="syncing">同步库</v-btn>
      <v-btn prepend-icon="mdi-auto-fix" variant="tonal" size="small" color="primary" @click="autoSelect" :loading="analyzing">智能选中</v-btn>
      <v-btn variant="tonal" size="small" :color="showOnlyDuplicates ? 'warning' : 'default'" :prepend-icon="showOnlyDuplicates ? 'mdi-filter' : 'mdi-filter-outline'" @click="toggleDuplicateMode">
        {{ showOnlyDuplicates ? '显示全部' : '仅重复项' }}
      </v-btn>
      <v-btn prepend-icon="mdi-cog-outline" variant="tonal" color="secondary" size="small" @click="openConfigDialog">规则配置</v-btn>
      <v-spacer />
      <v-btn v-if="selectedIds.length" prepend-icon="mdi-delete-outline" variant="flat" color="error" size="small"
        @click="deleteSelected">删除选中 ({{ selectedIds.length }})</v-btn>
    </div>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <!-- 列表 -->
    <v-card class="liquid-glass-card" rounded="xl">
      <v-table class="bg-transparent">
        <thead>
          <tr>
            <th style="width:40px">
              <v-checkbox :model-value="selectedIds.length === items.length && items.length > 0"
                @update:model-value="selectAll" density="compact" hide-details />
            </th>
            <th>媒体名称 / 路径</th>
            <th>类型</th>
            <th>规格 / 编码</th>
            <th>Emby ID</th>
            <th>TMDB</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!loading && !items.length"><td colspan="6" class="text-center py-8 text-medium-emphasis">暂无数据</td></tr>
          <tr v-for="item in items" :key="item.id || item.item_id"
            :class="{ 'bg-error': item.is_duplicate }">
            <td>
              <v-checkbox :model-value="selectedIds.includes(item.id || item.item_id)"
                @update:model-value="toggleSelect(item.id || item.item_id)" density="compact" hide-details />
            </td>
            <td>
              <div class="font-weight-medium" :class="{ 'text-warning': item.is_duplicate }">
                <template v-if="item.item_type === 'Episode'">
                  {{ formatEpisode(item) }} - {{ item.name }}
                </template>
                <template v-else-if="item.item_type === 'Season'">
                  第 {{ String(item.raw_data?.IndexNumber || 0).padStart(2, '0') }} 季
                </template>
                <template v-else>{{ item.name }}</template>
              </div>
              <div class="text-caption text-medium-emphasis font-mono" style="font-size:10px;opacity:0.5">{{ item.path }}</div>
            </td>
            <td>
              <v-chip size="x-small" variant="tonal" :color="colorMap[item.item_type] || 'default'">
                {{ typeMap[item.item_type] || item.item_type }}
              </v-chip>
            </td>
            <td>
              <template v-if="item.item_type !== 'Series' && item.item_type !== 'Season'">
                <v-chip v-if="item.display_title && item.display_title !== 'N/A'" size="x-small" variant="tonal" color="info" class="mr-1">{{ item.display_title }}</v-chip>
                <v-chip v-if="item.video_codec" size="x-small" variant="tonal" class="mr-1">{{ item.video_codec }}</v-chip>
                <v-chip v-if="item.video_range" size="x-small" variant="tonal" :color="item.video_range === 'SDR' ? 'default' : 'error'">{{ item.video_range }}</v-chip>
              </template>
              <span v-else class="text-medium-emphasis">-</span>
            </td>
            <td class="font-mono text-caption text-medium-emphasis">{{ item.id }}</td>
            <td class="text-caption text-medium-emphasis">{{ item.tmdb_id || '-' }}</td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- 配置弹窗 -->
    <v-dialog v-model="showConfigDialog" max-width="600" scrollable>
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-cog-outline</v-icon>
          智能选中与排除规则配置
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4" style="max-height:65vh;overflow-y:auto">
          <v-tabs class="mb-4">
            <v-tab>评分权重</v-tab>
            <v-tab>白名单排除</v-tab>
          </v-tabs>

          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            <strong>优先级逻辑：</strong>从上到下权重递减。同一行内，排在前面的关键词优先级更高。<br />
            所有输入项均不区分大小写（系统会自动处理）。
          </v-alert>

          <v-text-field v-model="configForm.display_title" label="媒体规格 (DisplayTitle)" variant="outlined" density="compact"
            hint="如: 4k, 2160p, 1080p" persistent-hint class="mb-3" />
          <v-text-field v-model="configForm.video_codec" label="视频编码 (Codec)" variant="outlined" density="compact"
            hint="如: hevc, h265, h264, av1" persistent-hint class="mb-3" />
          <v-text-field v-model="configForm.video_range" label="动态范围 (VideoRange)" variant="outlined" density="compact"
            hint="如: dolbyvision, hdr, sdr" persistent-hint class="mb-3" />

          <v-select v-model="configTieBreaker" :items="[
            { title: '保留较小的 Emby ID (旧文件优先)', value: 'small_id' },
            { title: '保留较大的 Emby ID (新文件优先)', value: 'large_id' }
          ]" label="平局决策 (当评分完全一致时)" variant="outlined" density="compact" class="mb-4" />

          <v-textarea v-model="excludeText" label="白名单关键词 (路径包含即保留)" variant="outlined" density="compact"
            placeholder="每行一个关键词或路径片段 (不区分大小写)&#10;只要完整路径中包含该词，文件就会被保护。"
            :rows="6" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showConfigDialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveConfig" :loading="loading">保存并应用</v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- 确认删除弹窗 -->
    <v-dialog v-model="showConfirmDialog" max-width="900">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="d-flex align-center pa-4">
          <v-icon start color="warning">mdi-alert-outline</v-icon>
          待清理媒体清单
          <v-spacer />
          <v-chip size="small" variant="tonal" color="warning">共选中 {{ selectedIds.length }} 个项目</v-chip>
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
            请仔细核对以下列表。点击下方的"确认并永久删除"后，这些文件将从磁盘中彻底移除。
          </v-alert>
          <div style="max-height:500px;overflow-y:auto">
            <v-table density="compact" class="bg-transparent">
              <thead>
                <tr><th>媒体名称 / 编号</th><th>规格</th><th>物理路径</th></tr>
              </thead>
              <tbody>
                <tr v-for="item in suggestedItems.filter((i: any) => selectedIds.includes(i.id))" :key="item.id">
                  <td>
                    <div class="font-weight-bold">{{ item.name }}</div>
                    <v-chip v-if="item.item_type === 'Episode'" size="x-small" variant="tonal" color="info">{{ formatEpisode(item) }}</v-chip>
                    <v-chip v-else-if="item.item_type === 'Series'" size="x-small" variant="tonal" color="warning">剧集本体</v-chip>
                  </td>
                  <td>
                    <v-chip v-if="item.display_title" size="x-small" variant="tonal" color="primary">{{ item.display_title }}</v-chip>
                    <div class="text-caption text-medium-emphasis">{{ item.video_codec }}</div>
                  </td>
                  <td class="font-mono text-caption text-medium-emphasis" style="font-size:10px">{{ item.path }}</td>
                </tr>
              </tbody>
            </v-table>
          </div>
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-arrow-left" @click="showConfirmDialog = false">点错了，返回</v-btn>
          <v-btn color="error" variant="flat" prepend-icon="mdi-delete-outline" @click="confirmDelete">
            确认并永久删除 ({{ selectedIds.length }} 项)
          </v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>
