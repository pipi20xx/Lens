<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDedupe } from './composables/useDedupe'
import DedupeTable from './components/DedupeTable.vue'
import DedupeConfigDialog from './components/DedupeConfigDialog.vue'
import DedupeConfirmDialog from './components/DedupeConfirmDialog.vue'

const {
  loading, syncing, analyzing, searchName, showOnlyDuplicates,
  selectedIds, dedupeConfig,
  currentPage, pageSize, totalPages, pagedItems, confirmItems,
  loadItems, loadChildren, toggleDuplicateMode, syncMedia,
  autoSelect, deleteItems, loadConfig, saveConfig,
  toggleSelect, selectAllPage,
} = useDedupe()

const showConfigDialog = ref(false)
const showConfirmDialog = ref(false)
const configSaving = ref(false)
const deleting = ref(false)

async function handleAutoSelect() {
  const results = await autoSelect()
  if (results.length > 0) showConfirmDialog.value = true
}

async function handleSaveConfig(config: any) {
  configSaving.value = true
  const ok = await saveConfig(config)
  configSaving.value = false
  if (ok) showConfigDialog.value = false
}

async function handleConfirmDelete() {
  deleting.value = true
  const ok = await deleteItems([...selectedIds.value])
  deleting.value = false
  if (ok) showConfirmDialog.value = false
}

onMounted(() => {
  loadConfig()
  loadItems()
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-content-duplicate</v-icon>
      Emby 重复项清理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">扫描、分析并清理您的 Emby 媒体库重复项，支持基于文件名与元数据的智能匹配。</p>

    <!-- 工具栏 -->
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <v-card-text class="pa-4">
        <div class="d-flex ga-2 flex-wrap align-center">
          <v-text-field v-model="searchName" prepend-inner-icon="mdi-magnify" placeholder="搜索名称或 ID..."
            variant="outlined" density="compact" hide-details clearable style="max-width:240px"
            @keydown.enter="loadItems" @click:clear="loadItems" />
          <v-btn prepend-icon="mdi-refresh" variant="tonal" color="info" size="small" @click="loadItems" :loading="loading">
            刷新
          </v-btn>
          <v-btn prepend-icon="mdi-cloud-sync-outline" variant="tonal" color="info" size="small"
            @click="syncMedia" :loading="syncing">同步库</v-btn>
          <v-btn prepend-icon="mdi-auto-fix" variant="tonal" size="small" color="primary"
            @click="handleAutoSelect" :loading="analyzing">智能选中</v-btn>
          <v-btn variant="tonal" size="small" :color="showOnlyDuplicates ? 'warning' : 'info'"
            :prepend-icon="showOnlyDuplicates ? 'mdi-filter' : 'mdi-filter-outline'"
            @click="toggleDuplicateMode">
            {{ showOnlyDuplicates ? '显示全部' : '仅重复项' }}
          </v-btn>
          <v-btn prepend-icon="mdi-cog-outline" variant="tonal" color="primary" size="small" @click="showConfigDialog = true">
            规则配置
          </v-btn>
          <v-spacer />
          <v-btn v-if="selectedIds.length" prepend-icon="mdi-delete-outline" variant="flat" color="error" size="small"
            @click="showConfirmDialog = true">
            删除选中 ({{ selectedIds.length }})
          </v-btn>
        </div>
      </v-card-text>
    </v-card>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <!-- 表格 -->
    <DedupeTable
      :items="pagedItems"
      :selected-ids="selectedIds"
      :loading="loading"
      @toggle-select="toggleSelect"
      @select-all="selectAllPage"
      @load-children="loadChildren"
    />

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="d-flex align-center justify-center mt-4 ga-3">
      <v-btn icon variant="text" size="small" :disabled="currentPage <= 1" @click="currentPage--">
        <v-icon>mdi-chevron-left</v-icon>
      </v-btn>
      <span class="text-body-2 text-medium-emphasis">
        第 {{ currentPage }} / {{ totalPages }} 页
      </span>
      <v-btn icon variant="text" size="small" :disabled="currentPage >= totalPages" @click="currentPage++">
        <v-icon>mdi-chevron-right</v-icon>
      </v-btn>
      <v-select v-model="pageSize" :items="[20, 50, 100, 200]" label="每页" variant="outlined" density="compact"
        hide-details style="max-width:100px" @update:model-value="currentPage = 1" />
    </div>

    <!-- 配置弹窗 -->
    <DedupeConfigDialog
      v-model="showConfigDialog"
      :config="dedupeConfig"
      :loading="configSaving"
      @save="handleSaveConfig"
    />

    <!-- 删除确认弹窗 -->
    <DedupeConfirmDialog
      v-model="showConfirmDialog"
      :items="confirmItems"
      :loading="deleting"
      @confirm="handleConfirmDelete"
    />
  </v-container>
</template>
