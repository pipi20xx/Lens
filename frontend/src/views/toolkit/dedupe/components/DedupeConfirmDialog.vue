<script setup lang="ts">
import { computed } from 'vue'
import GlassDialog from '@/components/common/GlassDialog.vue'

const props = defineProps<{
  modelValue: boolean
  items: any[]
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [val: boolean]
  confirm: []
}>()

const typeMap: Record<string, string> = { Movie: '电影', Series: '剧集', Season: '季', Episode: '单集' }
const typeColorMap: Record<string, string> = { Movie: 'success', Series: 'info', Season: 'warning', Episode: 'default' }
const typeIconMap: Record<string, string> = {
  Movie: 'mdi-movie-open-outline',
  Series: 'mdi-television-classic',
  Season: 'mdi-folder-outline',
  Episode: 'mdi-file-outline',
}

function formatEpisode(item: any) {
  const raw = item.raw_data || {}
  const s = raw.ParentIndexNumber ?? item.season_num
  const e = raw.IndexNumber ?? item.episode_num
  if (s !== undefined && e !== undefined) return `S${String(s).padStart(2, '0')}E${String(e).padStart(2, '0')}`
  return '未知编号'
}

// 按类型汇总
const typeStats = computed(() => {
  const stats: Record<string, number> = {}
  for (const item of props.items) {
    const t = item.item_type || 'Unknown'
    stats[t] = (stats[t] || 0) + 1
  }
  return stats
})
</script>

<template>
  <GlassDialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :max-width="860"
    :cancel-visible="false"
  >
    <template #title>
      <v-icon start color="error" size="26">mdi-alert-rhombus-outline</v-icon>
      <span class="text-h6 font-weight-bold">待清理媒体清单</span>
      <v-spacer />
      <v-chip size="small" variant="tonal" color="error" prepend-icon="mdi-delete-clock-outline">
        共 {{ items.length }} 项
      </v-chip>
    </template>

    <!-- 警告条 -->
    <v-alert type="warning" variant="tonal" density="comfortable" class="mb-4" rounded="lg">
      <div class="d-flex align-center ga-2">
        <v-icon size="18">mdi-shield-alert-outline</v-icon>
        <span class="text-body-2">
          以下文件将被从磁盘中<strong>永久删除</strong>，此操作不可撤销。请仔细核对后再确认。
        </span>
      </div>
    </v-alert>

    <!-- 类型汇总 -->
    <div class="d-flex ga-2 flex-wrap mb-4">
      <v-chip
        v-for="(count, type) in typeStats"
        :key="type"
        size="small"
        variant="tonal"
        :color="typeColorMap[type] || 'grey'"
        prepend-icon="mdi-counter"
      >
        {{ typeMap[type] || type }}: {{ count }}
      </v-chip>
    </div>

    <!-- 清单列表 -->
    <div class="confirm-list">
      <div
        v-for="(item, idx) in items"
        :key="item.id"
        class="confirm-item"
      >
        <!-- 序号 + 类型图标 -->
        <div class="item-index">
          <v-icon size="18" :color="typeColorMap[item.item_type] || 'grey'">
            {{ typeIconMap[item.item_type] || 'mdi-file-question-outline' }}
          </v-icon>
          <span class="item-num">{{ idx + 1 }}</span>
        </div>

        <!-- 主体信息 -->
        <div class="item-body">
          <div class="d-flex align-center ga-2 flex-wrap">
            <span class="item-name">{{ item.name }}</span>
            <v-chip size="x-small" variant="tonal" :color="typeColorMap[item.item_type] || 'default'">
              {{ typeMap[item.item_type] || item.item_type }}
            </v-chip>
            <v-chip
              v-if="item.item_type === 'Episode'"
              size="x-small" variant="tonal" color="info"
            >
              {{ formatEpisode(item) }}
            </v-chip>
            <v-chip
              v-if="item.display_title && item.display_title !== 'N/A'"
              size="x-small" variant="tonal" color="primary"
            >
              {{ item.display_title }}
            </v-chip>
            <v-chip v-if="item.video_codec" size="x-small" variant="tonal">
              {{ item.video_codec }}
            </v-chip>
            <v-chip
              v-if="item.video_range"
              size="x-small" variant="tonal"
              :color="item.video_range === 'SDR' ? 'default' : 'error'"
            >
              {{ item.video_range }}
            </v-chip>
          </div>
          <div class="item-path">{{ item.path }}</div>
        </div>

        <!-- Emby ID -->
        <div class="item-id">
          <span class="id-label">Emby ID</span>
          <span class="id-value">{{ item.id }}</span>
        </div>
      </div>
    </div>

    <template #actions>
      <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="emit('update:modelValue', false)">取消</v-btn>
      <v-btn
        color="error"
        variant="flat"
        prepend-icon="mdi-delete-forever-outline"
        :loading="loading"
        @click="emit('confirm')"
      >
        确认永久删除 ({{ items.length }})
      </v-btn>
    </template>
  </GlassDialog>
</template>

<style scoped>
/* 清单容器 */
.confirm-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* 单项卡片 */
.confirm-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.04);
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  transition: background 0.2s ease;
}
.confirm-item:hover {
  background: rgba(var(--v-theme-on-surface), 0.07);
}

/* 左侧序号/图标 */
.item-index {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 32px;
  padding-top: 2px;
}
.item-num {
  font-size: 11px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.4);
}

/* 主体 */
.item-body {
  flex: 1;
  min-width: 0;
}
.item-name {
  font-size: 14px;
  font-weight: 600;
  color: rgba(var(--v-theme-on-surface), 0.95);
  word-break: break-word;
}
.item-path {
  margin-top: 4px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.4);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 右侧 ID */
.item-id {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  min-width: 80px;
  padding-top: 2px;
}
.id-label {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgba(var(--v-theme-on-surface), 0.3);
}
.id-value {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.5);
}

/* 自定义滚动条 */
.v-card-text::-webkit-scrollbar {
  width: 6px;
}
.v-card-text::-webkit-scrollbar-track {
  background: transparent;
}
.v-card-text::-webkit-scrollbar-thumb {
  background: rgba(var(--v-theme-on-surface), 0.15);
  border-radius: 3px;
}
.v-card-text::-webkit-scrollbar-thumb:hover {
  background: rgba(var(--v-theme-on-surface), 0.25);
}
</style>
