<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  items: any[]
  selectedIds: string[]
  loading: boolean
}>()

const emit = defineEmits<{
  'toggle-select': [id: string]
  'select-all': []
  'load-children': [row: any]
}>()

const typeMap: any = { Movie: '电影', Series: '剧集', Season: '季', Episode: '集' }
const colorMap: any = { Movie: 'success', Series: 'info', Season: 'warning', Episode: 'default' }

function formatEpisode(item: any) {
  const raw = item.raw_data || {}
  const s = raw.ParentIndexNumber
  const e = raw.IndexNumber
  if (s !== undefined && e !== undefined) return `S${String(s).padStart(2, '0')}E${String(e).padStart(2, '0')}`
  return '未知编号'
}

const allSelected = computed(() => {
  return props.items.length > 0 && props.items.every((i: any) => props.selectedIds.includes(i.id))
})

function getIcon(type: string) {
  if (type === 'Series') return 'mdi-television-classic'
  if (type === 'Season') return 'mdi-folder-outline'
  if (type === 'Episode') return 'mdi-file-outline'
  return 'mdi-movie-open-outline'
}

function getDisplayName(item: any) {
  if (item.item_type === 'Season') {
    return `第 ${String(item.raw_data?.IndexNumber || 0).padStart(2, '0')} 季`
  }
  if (item.item_type === 'Episode') {
    return `${formatEpisode(item)} - ${item.name}`
  }
  return item.name
}

function canExpand(type: string) {
  return type === 'Series' || type === 'Season'
}
</script>

<template>
  <v-card class="liquid-glass-card" rounded="xl">
    <v-table density="compact" class="dedupe-table">
      <thead>
        <tr>
          <th style="width:40px">
            <v-checkbox :model-value="allSelected" @update:model-value="emit('select-all')"
              density="compact" hide-details />
          </th>
          <th style="width:28px"></th>
          <th>媒体名称 / 路径</th>
          <th style="width:80px">类型</th>
          <th style="width:220px">规格 / 编码</th>
          <th style="width:120px">Emby ID</th>
          <th style="width:100px">TMDB</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!loading && !items.length">
          <td colspan="7" class="text-center py-8 text-medium-emphasis">暂无数据</td>
        </tr>

        <template v-for="item in items" :key="item.id">
          <!-- 主行 -->
          <tr :class="{ 'dup-row': item.is_duplicate }">
            <td>
              <v-checkbox :model-value="selectedIds.includes(item.id)"
                @update:model-value="emit('toggle-select', item.id)" density="compact" hide-details />
            </td>
            <td>
              <v-btn v-if="canExpand(item.item_type)" icon variant="text" size="x-small"
                @click="emit('load-children', item)">
                <v-icon size="16">{{ item.expanded ? 'mdi-chevron-down' : 'mdi-chevron-right' }}</v-icon>
              </v-btn>
            </td>
            <td>
              <div class="d-flex align-center ga-1">
                <v-icon size="16" :color="colorMap[item.item_type] || 'grey'">{{ getIcon(item.item_type) }}</v-icon>
                <span class="row-name" :class="{ 'text-warning': item.is_duplicate }">
                  {{ getDisplayName(item) }}
                </span>
              </div>
              <div class="row-path">{{ item.path }}</div>
            </td>
            <td>
              <v-chip size="x-small" variant="tonal" :color="colorMap[item.item_type] || 'default'">
                {{ typeMap[item.item_type] || item.item_type }}
              </v-chip>
            </td>
            <td>
              <template v-if="item.item_type !== 'Series' && item.item_type !== 'Season'">
                <v-chip v-if="item.display_title && item.display_title !== 'N/A'" size="x-small" variant="tonal" color="info" class="mr-1">
                  {{ item.display_title }}
                </v-chip>
                <v-chip v-if="item.video_codec" size="x-small" variant="tonal" class="mr-1">{{ item.video_codec }}</v-chip>
                <v-chip v-if="item.video_range" size="x-small" variant="tonal"
                  :color="item.video_range === 'SDR' ? 'default' : 'error'">{{ item.video_range }}</v-chip>
              </template>
              <span v-else class="text-medium-emphasis">-</span>
            </td>
            <td class="row-id">{{ item.id }}</td>
            <td class="row-id">{{ item.tmdb_id || '-' }}</td>
          </tr>

          <!-- 第二层子项 (Season under Series) -->
          <template v-if="item.expanded && item.children?.length">
            <template v-for="child in item.children" :key="child.id">
              <tr :class="{ 'dup-row': child.is_duplicate }" class="child-row">
                <td>
                  <v-checkbox :model-value="selectedIds.includes(child.id)"
                    @update:model-value="emit('toggle-select', child.id)" density="compact" hide-details />
                </td>
                <td>
                  <v-btn v-if="canExpand(child.item_type)" icon variant="text" size="x-small"
                    @click="emit('load-children', child)">
                    <v-icon size="16">{{ child.expanded ? 'mdi-chevron-down' : 'mdi-chevron-right' }}</v-icon>
                  </v-btn>
                </td>
                <td style="padding-left:28px">
                  <div class="d-flex align-center ga-1">
                    <v-icon size="14" :color="colorMap[child.item_type] || 'grey'">{{ getIcon(child.item_type) }}</v-icon>
                    <span class="row-name sub-name">{{ getDisplayName(child) }}</span>
                  </div>
                  <div class="row-path">{{ child.path }}</div>
                </td>
                <td>
                  <v-chip size="x-small" variant="tonal" :color="colorMap[child.item_type] || 'default'">
                    {{ typeMap[child.item_type] || child.item_type }}
                  </v-chip>
                </td>
                <td>
                  <v-chip v-if="child.display_title && child.display_title !== 'N/A'" size="x-small" variant="tonal" color="info" class="mr-1">
                    {{ child.display_title }}
                  </v-chip>
                  <v-chip v-if="child.video_codec" size="x-small" variant="tonal">{{ child.video_codec }}</v-chip>
                </td>
                <td class="row-id">{{ child.id }}</td>
                <td class="row-id">{{ child.tmdb_id || '-' }}</td>
              </tr>

              <!-- 第三层子项 (Episode under Season) -->
              <template v-if="child.expanded && child.children?.length">
                <tr v-for="grandchild in child.children" :key="grandchild.id"
                  :class="{ 'dup-row': grandchild.is_duplicate }" class="grandchild-row">
                  <td>
                    <v-checkbox :model-value="selectedIds.includes(grandchild.id)"
                      @update:model-value="emit('toggle-select', grandchild.id)" density="compact" hide-details />
                  </td>
                  <td></td>
                  <td style="padding-left:56px">
                    <div class="d-flex align-center ga-1">
                      <v-icon size="12" :color="colorMap[grandchild.item_type] || 'grey'">{{ getIcon(grandchild.item_type) }}</v-icon>
                      <span class="row-name sub-name">{{ getDisplayName(grandchild) }}</span>
                    </div>
                    <div class="row-path" style="padding-left:20px">{{ grandchild.path }}</div>
                  </td>
                  <td>
                    <v-chip size="x-small" variant="tonal" :color="colorMap[grandchild.item_type] || 'default'">
                      {{ typeMap[grandchild.item_type] || grandchild.item_type }}
                    </v-chip>
                  </td>
                  <td>
                    <v-chip v-if="grandchild.display_title && grandchild.display_title !== 'N/A'" size="x-small" variant="tonal" color="info" class="mr-1">
                      {{ grandchild.display_title }}
                    </v-chip>
                    <v-chip v-if="grandchild.video_codec" size="x-small" variant="tonal">{{ grandchild.video_codec }}</v-chip>
                    <v-chip v-if="grandchild.video_range" size="x-small" variant="tonal"
                      :color="grandchild.video_range === 'SDR' ? 'default' : 'error'">{{ grandchild.video_range }}</v-chip>
                  </td>
                  <td class="row-id">{{ grandchild.id }}</td>
                  <td class="row-id">{{ grandchild.tmdb_id || '-' }}</td>
                </tr>
              </template>

              <tr v-if="child.expanded && child.childrenLoaded && !child.children?.length">
                <td colspan="7" class="text-center py-2 text-caption text-medium-emphasis">无子项</td>
              </tr>
            </template>
          </template>

          <tr v-if="item.expanded && item.childrenLoaded && !item.children?.length">
            <td colspan="7" class="text-center py-2 text-caption text-medium-emphasis">无子项</td>
          </tr>
        </template>
      </tbody>
    </v-table>
  </v-card>
</template>

<style scoped>
/* 表头文字 */
.dedupe-table :deep(thead th) {
  color: rgba(var(--v-theme-on-surface), 0.857) !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.12) !important;
}

/* 单元格基础颜色 */
.dedupe-table :deep(td) {
  color: rgba(var(--v-theme-on-surface), 0.9) !important;
  border-bottom: 1px solid rgba(var(--v-theme-on-surface), 0.06) !important;
}

/* 重复项行高亮 */
.dup-row {
  background: rgba(244, 67, 54, 0.08) !important;
}
.dup-row:hover {
  background: rgba(244, 67, 54, 0.14) !important;
}

/* 子项行缩进 */
.child-row { opacity: 0.95; }
.grandchild-row { opacity: 0.9; }

/* 名称 */
.row-name {
  font-weight: 500;
  font-size: 14px;
  color: rgba(var(--v-theme-on-surface), 0.95);
}
.sub-name {
  font-size: 13px;
}

/* 路径 */
.row-path {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 10px;
  color: rgba(var(--v-theme-on-surface), 0.857);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 500px;
}

/* ID 列 */
.row-id {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: rgba(var(--v-theme-on-surface), 0.857);
}

/* 行 hover */
.dedupe-table :deep(tbody tr:not(.dup-row):hover) {
  background: rgba(var(--v-theme-on-surface), 0.06) !important;
}
</style>
