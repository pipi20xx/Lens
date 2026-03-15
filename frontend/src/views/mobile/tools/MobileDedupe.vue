<template>
  <div class="mobile-dedupe">
    <div class="page-header">
      <h1 class="page-title">重复项清理</h1>
      <p class="page-desc">扫描、分析并清理您的媒体库重复项</p>
    </div>

    <n-card class="search-card" :bordered="false">
      <n-space vertical>
        <n-input 
          v-model:value="searchName" 
          placeholder="搜索名称或 ID..." 
          @keypress.enter="loadItems"
        >
          <template #prefix>
            <n-icon><SearchIcon /></n-icon>
          </template>
        </n-input>
        <n-button type="primary" block @click="loadItems" :loading="loading">
          <template #icon><n-icon><SearchIcon /></n-icon></template>
          执行搜索
        </n-button>
        <n-checkbox v-model:checked="showOnlyDuplicates" @update:checked="toggleDuplicateMode">
          仅显示重复项
        </n-checkbox>
      </n-space>
    </n-card>

    <n-card class="action-card" :bordered="false">
      <n-space vertical>
        <n-button type="warning" block secondary @click="handleAutoSelect" :loading="loading">
          <template #icon><n-icon><AutoIcon /></n-icon></template>
          执行分析
        </n-button>
        <n-button type="primary" block secondary @click="showConfig = true">
          <template #icon><n-icon><SettingsIcon /></n-icon></template>
          规则设置
        </n-button>
        <n-button type="primary" block secondary :loading="syncing" @click="syncMedia">
          <template #icon><n-icon><SyncIcon /></n-icon></template>
          执行同步
        </n-button>
        <n-button 
          v-if="selectedIds.length > 0" 
          type="error" 
          block 
          secondary 
          @click="showConfirm = true"
        >
          <template #icon><n-icon><DeleteIcon /></n-icon></template>
          执行删除 ({{ selectedIds.length }})
        </n-button>
      </n-space>
    </n-card>

    <n-card class="list-card" :bordered="false" title="媒体项目列表">
      <n-spin :show="loading">
        <div class="items-list">
          <div 
            v-for="item in items" 
            :key="item.id"
            class="item-card"
            :class="{ 'has-children': item.hasChildren }"
          >
            <div class="item-header" @click="toggleExpand(item)">
              <n-checkbox 
                :checked="selectedIds.includes(item.id)"
                @update:checked="(checked) => toggleSelect(item.id, checked)"
                @click.stop
              />
              <div class="item-info">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-meta">{{ item.type }} | {{ item.id }}</div>
              </div>
              <n-icon v-if="item.hasChildren" class="expand-icon">
                <ChevronRightIcon />
              </n-icon>
            </div>
            <div v-if="item.expanded && item.children" class="item-children">
              <div 
                v-for="child in item.children"
                :key="child.id"
                class="child-item"
              >
                <n-checkbox 
                  :checked="selectedIds.includes(child.id)"
                  @update:checked="(checked) => toggleSelect(child.id, checked)"
                />
                <div class="child-info">
                  <div class="child-name">{{ child.name }}</div>
                  <div class="child-meta">{{ child.type }} | {{ child.id }}</div>
                </div>
              </div>
            </div>
          </div>
          <div v-if="items.length === 0 && !loading" class="empty-state">
            <p>暂无数据</p>
          </div>
        </div>
      </n-spin>
    </n-card>

    <DedupeConfigModal v-model:show="showConfig" :config="dedupeConfig" @save="handleConfigSave" />

    <DedupeConfirmModal
      v-model:show="showConfirm"
      :items="confirmItems"
      @confirm="handleBulkDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { NCard, NButton, NIcon, NInput, NCheckbox, NSpace, NSpin, useMessage } from 'naive-ui'
import { 
  SearchOutlined as SearchIcon, 
  SettingsOutlined as SettingsIcon, 
  AutoFixHighOutlined as AutoIcon,
  SyncOutlined as SyncIcon,
  DeleteOutlined as DeleteIcon,
  ChevronRightOutlined as ChevronRightIcon
} from '@vicons/material'

import { useDedupe } from '../../toolkit/dedupe/useDedupe'
import DedupeConfigModal from '../../toolkit/dedupe/DedupeConfigModal.vue'
import DedupeConfirmModal from '../../toolkit/dedupe/DedupeConfirmModal.vue'

const message = useMessage()
const {
  loading, syncing, searchName, showOnlyDuplicates, items, selectedIds, suggestedItems, dedupeConfig,
  loadItems, onLoadChildren, toggleDuplicateMode, syncMedia, autoSelect, deleteItems, loadConfig, saveDedupeConfig
} = useDedupe()

const showConfig = ref(false)
const showConfirm = ref(false)

const confirmItems = computed(() => {
  if (suggestedItems.value.length > 0 && selectedIds.value.length === suggestedItems.value.length) {
    return suggestedItems.value
  }
  return items.value.filter(i => selectedIds.value.includes(i.id))
})

onMounted(async () => {
  await loadConfig()
  loadItems()
})

const toggleExpand = async (item: any) => {
  if (item.hasChildren && !item.children) {
    await onLoadChildren(item)
  }
  item.expanded = !item.expanded
}

const toggleSelect = (id: string, checked: boolean) => {
  if (checked) {
    if (!selectedIds.value.includes(id)) {
      selectedIds.value.push(id)
    }
  } else {
    selectedIds.value = selectedIds.value.filter(i => i !== id)
  }
}

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
  const msgInstance = message.loading(`正在启动后台清理任务，共 ${count} 个项目...`, { duration: 3000 })
  
  showConfirm.value = false
  const idsToDelete = [...selectedIds.value]
  selectedIds.value = []
  suggestedItems.value = []

  deleteItems(idsToDelete).then(success => {
    msgInstance.destroy()
    if (success) {
      message.success('后台清理指令已全部下发，请检查日志查看最终结果')
    }
  })
}
</script>

<style scoped>
.mobile-dedupe {
  padding: 16px;
  padding-bottom: 32px;
  background: var(--app-bg-color);
  min-height: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color);
  margin: 0 0 8px 0;
}

.page-desc {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.search-card,
.action-card,
.list-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.items-list {
  max-height: 60vh;
  overflow-y: auto;
}

.item-card {
  background: var(--app-bg-color);
  border-radius: 12px;
  margin-bottom: 8px;
  overflow: hidden;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  cursor: pointer;
}

.item-header:active {
  background: rgba(255, 255, 255, 0.05);
}

.item-info {
  flex: 1;
}

.item-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.item-meta {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.expand-icon {
  color: var(--text-color);
  opacity: 0.4;
  transition: transform 0.2s;
}

.item-card.has-children .expand-icon {
  transform: rotate(90deg);
}

.item-children {
  padding: 0 12px 12px 12px;
}

.child-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  margin-top: 8px;
}

.child-info {
  flex: 1;
}

.child-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.child-meta {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-color);
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
}
</style>
