<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import GlassDialog from '@/components/common/GlassDialog.vue'

const props = defineProps<{
  modelValue: boolean
  config: any
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [val: boolean]
  save: [config: any]
}>()

const activeTab = ref('rules')

const form = reactive({
  display_title: '',
  video_codec: '',
  video_range: '',
})
const tieBreaker = ref('small_id')
const excludeText = ref('')

// 根据内容动态计算行数，确保打开时默认显示全部内容
// auto-grow 仅在用户手动输入时触发重算，程序化赋值时不会生效
const excludeRows = computed(() => {
  const text = excludeText.value || ''
  if (!text) return 4
  const lines = text.split('\n')
  let totalLines = 0
  for (const line of lines) {
    totalLines += Math.max(1, Math.ceil(line.length / 50))
  }
  return Math.max(4, Math.min(totalLines + 1, 30))
})

// 弹窗打开时同步外部配置到内部表单
watch(() => props.modelValue, (val) => {
  if (val) {
    const cfg = props.config || {}
    const vw = cfg.rules?.values_weight || {}
    form.display_title = (vw.display_title || []).join(', ')
    form.video_codec = (vw.video_codec || []).join(', ')
    form.video_range = (vw.video_range || []).join(', ')
    tieBreaker.value = cfg.rules?.tie_breaker || 'small_id'
    excludeText.value = (cfg.exclude_paths || []).join('\n')
  }
})

function handleSave() {
  const configToSave = JSON.parse(JSON.stringify(props.config || {}))
  configToSave.rules = configToSave.rules || {}
  configToSave.rules.values_weight = {
    display_title: form.display_title.split(',').map(s => s.trim().toLowerCase()).filter(s => s),
    video_codec: form.video_codec.split(',').map(s => s.trim().toLowerCase()).filter(s => s),
    video_range: form.video_range.split(',').map(s => s.trim().toLowerCase()).filter(s => s),
  }
  configToSave.rules.tie_breaker = tieBreaker.value
  configToSave.exclude_paths = excludeText.value.split('\n').map(s => s.trim()).filter(s => s)
  emit('save', configToSave)
}
</script>

<template>
  <GlassDialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :max-width="600"
    icon="mdi-cog-outline"
    title="智能选中与排除规则配置"
  >
    <v-tabs v-model="activeTab" density="compact" color="primary" class="mb-4">
      <v-tab value="rules">
        <v-icon size="16" class="mr-1">mdi-scale-balance</v-icon>评分权重
      </v-tab>
      <v-tab value="exclude">
        <v-icon size="16" class="mr-1">mdi-shield-check-outline</v-icon>白名单排除
      </v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- 评分权重 -->
      <v-window-item value="rules">
        <v-alert type="info" variant="tonal" density="compact" class="mb-4">
          <strong>优先级逻辑：</strong>从上到下权重递减。同一行内，排在前面的关键词优先级更高。<br />
          所有输入项均不区分大小写（系统会自动处理）。
        </v-alert>

        <v-text-field v-model="form.display_title" label="媒体规格 (DisplayTitle)" variant="outlined" density="compact"
          hint="如: 4k, 2160p, 1080p" persistent-hint class="mb-3" />
        <v-text-field v-model="form.video_codec" label="视频编码 (Codec)" variant="outlined" density="compact"
          hint="如: hevc, h265, h264, av1" persistent-hint class="mb-3" />
        <v-text-field v-model="form.video_range" label="动态范围 (VideoRange)" variant="outlined" density="compact"
          hint="如: dolbyvision, hdr, sdr" persistent-hint class="mb-3" />

        <v-select v-model="tieBreaker" :items="[
          { title: '保留较小的 Emby ID (旧文件优先)', value: 'small_id' },
          { title: '保留较大的 Emby ID (新文件优先)', value: 'large_id' }
        ]" label="平局决策 (当评分完全一致时)" variant="outlined" density="compact" />
      </v-window-item>

      <!-- 白名单排除 -->
      <v-window-item value="exclude">
        <v-textarea v-model="excludeText" label="白名单关键词 (路径包含即保留)" variant="outlined" density="compact"
          placeholder="每行一个关键词或路径片段 (不区分大小写)&#10;只要完整路径中包含该词，文件就会被保护。&#10;&#10;例如：&#10;2023&#10;Feature&#10;/vol1/Anime/Protected"
          :rows="excludeRows" auto-grow />
      </v-window-item>
    </v-window>

    <template #actions>
      <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" :loading="loading" @click="handleSave">
        保存并应用
      </v-btn>
    </template>
  </GlassDialog>
</template>
