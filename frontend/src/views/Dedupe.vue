<template>
  <div class="dedupe-layout">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">Emby 媒体管理与去重</n-text></n-h2>
        <n-text depth="3">扫描、分析并清理您的媒体库重复项，支持基于文件名与元数据的智能匹配。</n-text>
      </div>

      <n-card embedded :bordered="false" size="small" class="dedupe-toolbar">
        <n-space justify="space-between" align="center" :wrap="true" :size="[12, 8]">
          <n-space align="center" :size="12" :wrap="true">
            <n-input-group class="search-group">
              <n-input v-model:value="searchName" placeholder="搜索名称或 ID..." @keypress.enter="loadItems" />
              <n-button type="primary" secondary @click="loadItems">
                执行搜索
              </n-button>
            </n-input-group>
            <n-checkbox v-model:checked="showOnlyDuplicates" @update:checked="toggleDuplicateMode">
              仅显示重复项
            </n-checkbox>
          </n-space>

          <n-space :size="8" :wrap="true">
            <n-button type="warning" secondary size="small" @click="handleAutoSelect">
              执行分析
            </n-button>
            <n-button type="primary" secondary size="small" @click="showConfig = true">
              规则设置
            </n-button>
            <n-button type="primary" secondary size="small" :loading="syncing" @click="syncMedia">
              执行同步
            </n-button>
            <n-button v-if="selectedIds.length > 0" type="error" secondary size="small" @click="showConfirm = true">
              执行删除 ({{ selectedIds.length }})
            </n-button>
          </n-space>
        </n-space>
      </n-card>

      <n-card :bordered="false" content-style="padding: 0">
        <n-data-table
          remote :columns="columns" :data="items" :loading="loading" :row-key="row => row.id"
          v-model:checked-row-keys="selectedIds" :pagination="false" size="small"
          :max-height="isMobile ? 'calc(100vh - 12rem)' : 'calc(100vh - 15rem)'"
          :scroll-x="isMobile ? 520 : 0"
          virtual-scroll :cascade="false" @load="onLoadChildren"
        />
      </n-card>
    </n-space>

    <DedupeConfigModal v-model:show="showConfig" :config="dedupeConfig" @save="handleConfigSave" />

    <!-- 弹窗清单现在显示 suggestedItems -->
    <DedupeConfirmModal
      v-model:show="showConfirm"
      :items="confirmItems"
      @confirm="handleBulkDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NCard, NSpace, NButton, NIcon, NInput, NInputGroup, NCheckbox, NDataTable, NH2, NText, useMessage } from 'naive-ui'
import { getColumns } from './toolkit/dedupe/columns'
import { useDedupe } from './toolkit/dedupe/useDedupe'
import DedupeConfigModal from './toolkit/dedupe/DedupeConfigModal.vue'
import DedupeConfirmModal from './toolkit/dedupe/DedupeConfirmModal.vue'
import { usePWA } from '@/composables/usePWA'

const { isMobile } = usePWA()
const message = useMessage()
const {
  loading, syncing, searchName, showOnlyDuplicates, items, selectedIds, suggestedItems, dedupeConfig,
  loadItems, onLoadChildren, toggleDuplicateMode, syncMedia, autoSelect, deleteItems, loadConfig, saveDedupeConfig
} = useDedupe()

// 移动端隐藏 Emby ID / TMDB 列，并缩小名称、规格列宽，配合水平滚动
const columns = computed(() => {
  const cols = getColumns()
  if (isMobile.value) {
    return cols
      .filter((c: any) => c.key !== 'id' && c.key !== 'tmdb_id')
      .map((c: any) => {
        if (c.key === 'name') return { ...c, width: 200 }
        if (c.key === 'specs') return { ...c, width: 170 }
        return c
      })
  }
  return cols
})
const showConfig = ref(false)
const showConfirm = ref(false)

// 如果是智能分析出来的，显示 suggestedItems，否则显示手动勾选的
const confirmItems = computed(() => {
  if (suggestedItems.value.length > 0 && selectedIds.value.length === suggestedItems.value.length) {
    return suggestedItems.value
  }
  // 手动勾选时，从当前页面列表找对象
  return items.value.filter(i => selectedIds.value.includes(i.id))
})

onMounted(async () => {
  await loadConfig()
  loadItems()
})

const handleAutoSelect = async () => {
  const res = await autoSelect()
  if (res.length > 0) {
    showConfirm.value = true
  }
}

const handleConfigSave = async (newConfig: any) => {
  dedupeConfig.value = newConfig
  if (await saveDedupeConfig()) showConfig.value = false
}

const handleBulkDelete = () => {
  const count = selectedIds.value.length
  // 1. 立即给用户反馈
  const msgInstance = message.loading(`正在启动后台清理任务，共 ${count} 个项目...`, { duration: 3000 })
  
  // 2. 立即关闭弹窗并重置状态，释放 UI
  showConfirm.value = false
  const idsToDelete = [...selectedIds.value] // 备份 ID 列表
  selectedIds.value = []
  suggestedItems.value = []

  // 3. 静默执行请求
  deleteItems(idsToDelete).then(success => {
    msgInstance.destroy()
    if (success) {
      message.success('后台清理指令已全部下发，请检查日志查看最终结果')
    }
  })
}
</script>

<style scoped>
.dedupe-layout {
  width: 100%;
}
:deep(.n-h2 .n-text--primary-type) {
  color: var(--primary-color);
}
:deep(.n-data-table-tr--with-children) {
  background-color: rgba(255, 255, 255, 0.02);
}
:deep(.n-data-table .n-data-table-td--selection) {
  color: var(--primary-color);
}

/* 搜索组：桌面端固定宽度，移动端自适应 */
.search-group {
  width: 20rem;
  flex-shrink: 0;
}

@media (max-width: 767px) {
  /* 搜索组移动端全宽，输入框弹性填充 */
  .search-group {
    width: 100%;
    flex: 1 1 100%;
  }
  .search-group :deep(.n-input) {
    flex: 1;
    min-width: 0;
    width: auto !important;
  }
  /* 工具栏内边距缩减 */
  .dedupe-toolbar :deep(.n-card__content) {
    padding: 8px !important;
  }
}
</style>