<template>
  <div class="mobile-dedupe">
    <div class="page-header">
      <h1 class="page-title">媒体查重与智能清理</h1>
      <p class="page-desc">扫描、分析并清理您的媒体库重复项</p>
    </div>

    <n-card class="action-card" :bordered="false">
      <n-space vertical>
        <n-button 
          :type="buttonTypes.PRIMARY" 
          :size="buttonSizes.MEDIUM"
          @click="syncMedia" 
          :loading="syncing"
          secondary
          block
        >
          {{ buttonText.SYNC }}
        </n-button>
        <n-button 
          :type="buttonTypes.SUCCESS" 
          :size="buttonSizes.MEDIUM"
          @click="fetchDuplicates" 
          secondary
          block
        >
          {{ buttonText.SEARCH }}
        </n-button>
        <n-button 
          :type="buttonTypes.INFO" 
          :size="buttonSizes.MEDIUM"
          @click="showConfig = true" 
          secondary
          block
        >
          {{ buttonText.RULES_SETTINGS }}
        </n-button>
      </n-space>
    </n-card>

    <div v-if="syncing" class="sync-progress">
      <n-icon size="20"><SyncIcon /></n-icon>
      <span>正在从 Emby 获取全量媒体数据并更新本地索引，请稍候...</span>
    </div>

    <div v-if="duplicateGroups.length > 0" class="stats-section">
      <n-card class="stat-card" :bordered="false">
        <div class="stat-label">{{ statText.DUPLICATE_GROUPS }}</div>
        <div class="stat-value">{{ duplicateGroups.length }}</div>
      </n-card>
      <n-card class="stat-card" :bordered="false">
        <div class="stat-label">{{ statText.SUGGESTED_DELETE }}</div>
        <div class="stat-value">{{ suggestedCount }}</div>
      </n-card>
      <n-card class="stat-card" :bordered="false">
        <div class="stat-label">{{ statText.SELECTED_ITEMS }}</div>
        <div class="stat-value">{{ selectedIds.length }}</div>
      </n-card>
    </div>

    <div v-if="duplicateGroups.length > 0" class="toolbar">
      <n-space vertical style="width: 100%">
        <n-button :type="buttonTypes.WARNING" :size="buttonSizes.MEDIUM" secondary @click="autoSelect" :loading="loading" block>
          {{ buttonText.SMART_ANALYZE }}
        </n-button>
        <n-button :type="buttonTypes.PRIMARY" :size="buttonSizes.MEDIUM" secondary @click="selectedIds = []" block>
          {{ buttonText.CANCEL_SELECT }}
        </n-button>
        <n-button 
          :type="buttonTypes.ERROR"
          :size="buttonSizes.MEDIUM"
          secondary
          @click="confirmDelete" 
          :disabled="selectedIds.length === 0"
          block
        >
          {{ buttonText.DELETE }} ({{ selectedIds.length }})
        </n-button>
      </n-space>
    </div>

    <div v-if="duplicateGroups.length > 0" class="groups-list">
      <n-card 
        v-for="group in duplicateGroups" 
        :key="group.tmdb_id" 
        class="group-card"
        :bordered="false"
      >
        <template #header>
          <div class="group-header">
            <div class="group-title">
              <span class="tmdb-id">TMDB ID: {{ group.tmdb_id }}</span>
              <span class="item-name">{{ group.items[0].name }}</span>
            </div>
            <n-tag :size="buttonSizes.TINY" round :bordered="false">{{ group.items.length }} {{ tagText.COPY }}</n-tag>
          </div>
        </template>
        
        <div class="items-container">
          <div 
            v-for="item in group.items" 
            :key="item.emby_id" 
            class="item-row"
            :class="{'selected': selectedIds.includes(item.emby_id)}"
          >
            <div class="item-checkbox">
              <input 
                type="checkbox" 
                :checked="selectedIds.includes(item.emby_id)"
                @change="toggleSelect(item.emby_id)"
                class="checkbox"
              />
            </div>
            <div class="item-details">
              <div class="item-name">{{ item.name }}</div>
              <div class="item-path">{{ item.path }}</div>
              <div class="item-meta">
                <span class="meta-item">{{ item.type }}</span>
                <n-tag :size="buttonSizes.TINY" :bordered="false">{{ item.display_title }}</n-tag>
                <span class="meta-item">{{ item.video_codec }}</span>
                <n-tag 
                  v-if="item.video_range && item.video_range !== 'SDR'" 
                  :size="buttonSizes.TINY" 
                  :type="tagTypes.WARNING" 
                  :bordered="false"
                >
                  {{ item.video_range }}
                </n-tag>
                <span v-else class="meta-item">{{ item.video_range }}</span>
              </div>
            </div>
          </div>
        </div>
      </n-card>
    </div>

    <div v-else-if="!syncing" class="empty-state">
      <n-icon size="64"><CopyIcon /></n-icon>
      <p>{{ emptyText.NO_DUPLICATES }}</p>
      <p class="empty-hint">{{ emptyText.CLICK_TO_START }}</p>
    </div>

    <n-modal 
      v-model:show="showConfig" 
      preset="card" 
      :title="modalTitle.RULES_CONFIG" 
      style="width: 90vw; max-width: 600px"
    >
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="formLabel.DISPLAY_TITLE">
          <template #label>
            <span>{{ formLabel.DISPLAY_TITLE }} <span class="label-hint">{{ formHint.DISPLAY_TITLE }}</span></span>
          </template>
          <n-input v-model:value="configForm.display_title" :placeholder="placeholder.DISPLAY_TITLE" />
        </n-form-item>
        
        <n-form-item :label="formLabel.VIDEO_CODEC">
          <template #label>
            <span>{{ formLabel.VIDEO_CODEC }} <span class="label-hint">{{ formHint.VIDEO_CODEC }}</span></span>
          </template>
          <n-input v-model:value="configForm.video_codec" :placeholder="placeholder.VIDEO_CODEC" />
        </n-form-item>
        
        <n-form-item :label="formLabel.VIDEO_RANGE">
          <template #label>
            <span>{{ formLabel.VIDEO_RANGE }} <span class="label-hint">{{ formHint.VIDEO_RANGE }}</span></span>
          </template>
          <n-input v-model:value="configForm.video_range" :placeholder="placeholder.VIDEO_RANGE" />
        </n-form-item>
        
        <n-form-item :label="formLabel.TIE_BREAKER">
          <n-select
            v-model:value="configForm.tie_breaker"
            :options="tieBreakerOptions"
          />
        </n-form-item>
        
        <n-form-item :label="formLabel.EXCLUDE_PATHS">
          <n-input
            v-model:value="configForm.exclude_paths"
            type="textarea"
            :placeholder="placeholder.EXCLUDE_PATHS"
            :autosize="{ minRows: 4, maxRows: 8 }"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showConfig = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveConfig" :loading="loading">{{ buttonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NIcon, NTag, NSpace, NModal, NForm, NFormItem, NInput, NSelect, useMessage } from 'naive-ui'
import { 
  SyncOutlined as SyncIcon,
  SearchOutlined as SearchIcon,
  DeleteOutlined as DeleteIcon,
  ScienceOutlined as LabIcon,
  ClearOutlined as ClearIcon,
  ContentCopyOutlined as CopyIcon,
  SettingsOutlined as SettingsIcon
} from '@vicons/material'
import axios from 'axios'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  TagTypes,
  TagText,
  StatText,
  EmptyText,
  ModalTitle,
  FormLabel,
  Placeholder,
  FormHint,
} from '../constants'

const message = useMessage()

const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const tagTypes = TagTypes
const tagText = TagText
const statText = StatText
const emptyText = EmptyText
const modalTitle = ModalTitle
const formLabel = FormLabel
const placeholder = Placeholder
const formHint = FormHint

const syncing = ref(false)
const loading = ref(false)
const showConfig = ref(false)
const duplicateGroups = ref<any[]>([])
const selectedIds = ref<string[]>([])
const suggestedCount = ref(0)
const configForm = ref<any>({
  display_title: '',
  video_codec: '',
  video_range: '',
  tie_breaker: 'small_id',
  exclude_paths: ''
})

const tieBreakerOptions = [
  { label: '保留较小的 Emby ID (旧文件优先)', value: 'small_id' },
  { label: '保留较大的 Emby ID (新文件优先)', value: 'large_id' }
]

const fetchDuplicates = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/dedupe/duplicates')
    duplicateGroups.value = res.data || []
    selectedIds.value = []
    suggestedCount.value = 0
  } catch (error) {
    message.error(messageText.FETCH_FAILED)
  } finally {
    loading.value = false
  }
}

const syncMedia = async () => {
  if (!confirm(messageText.SYNC_CONFIRM)) return
  syncing.value = true
  try {
    await axios.post('/api/dedupe/sync', { item_types: ['Movie', 'Series'] })
    message.success(messageText.SYNC_SUCCESS)
    await fetchDuplicates()
  } catch (error) {
    message.error(messageText.SYNC_FAILED)
  } finally {
    syncing.value = false
  }
}

const autoSelect = async () => {
  if (duplicateGroups.value.length === 0) return
  
  loading.value = true
  const allItems = duplicateGroups.value.flatMap(g => g.items)
  try {
    const res = await axios.post('/api/dedupe/smart-select', { items: allItems })
    selectedIds.value = res.data.to_delete || []
    suggestedCount.value = selectedIds.length
  } catch (error) {
    message.error(messageText.SMART_SELECT_FAILED)
  } finally {
    loading.value = false
  }
}

const toggleSelect = (id: string) => {
  const index = selectedIds.value.indexOf(id)
  if (index > -1) {
    selectedIds.value.splice(index, 1)
  } else {
    selectedIds.value.push(id)
  }
}

const loadConfig = async () => {
  try {
    const res = await axios.get('/api/dedupe/config')
    if (res.data && res.data.rules) {
      const config = res.data
      configForm.value = {
        display_title: (config.rules.values_weight?.display_title || []).join(', '),
        video_codec: (config.rules.values_weight?.video_codec || []).join(', '),
        video_range: (config.rules.values_weight?.video_range || []).join(', '),
        tie_breaker: config.rules.tie_breaker || 'small_id',
        exclude_paths: (config.exclude_paths || []).join('\n')
      }
    }
  } catch (e) {
    console.error('加载配置失败', e)
  }
}

const saveConfig = async () => {
  loading.value = true
  try {
    const config = {
      rules: {
        values_weight: {
          display_title: configForm.value.display_title.split(',').map(s => s.trim().toLowerCase()).filter(s => s),
          video_codec: configForm.value.video_codec.split(',').map(s => s.trim().toLowerCase()).filter(s => s),
          video_range: configForm.value.video_range.split(',').map(s => s.trim().toLowerCase()).filter(s => s)
        },
        tie_breaker: configForm.value.tie_breaker
      },
      exclude_paths: configForm.value.exclude_paths.split('\n').map(s => s.trim()).filter(s => s)
    }
    await axios.post('/api/dedupe/config', config)
    message.success(messageText.CONFIG_SAVED)
    showConfig.value = false
  } catch (e) {
    message.error(messageText.SAVE_FAILED)
  } finally {
    loading.value = false
  }
}

const confirmDelete = async () => {
  if (!confirm(messageText.DELETE_CONFIRM.replace('{count}', selectedIds.value.length.toString()))) return
  
  try {
    const res = await axios.delete('/api/dedupe/items', { data: { item_ids: selectedIds.value } })
    message.success(messageText.DELETE_SUCCESS.replace('{success}', res.data.success).replace('{total}', res.data.total))
    await fetchDuplicates()
  } catch (error) {
    message.error(messageText.DELETE_FAILED)
  }
}

onMounted(() => {
  loadConfig()
  fetchDuplicates()
})

const messageText = {
  FETCH_FAILED: '获取重复项失败',
  SYNC_CONFIRM: '全量同步可能需要一些时间（取决于媒体库大小），确定开始吗？',
  SYNC_SUCCESS: '同步完成',
  SYNC_FAILED: '同步失败',
  SMART_SELECT_FAILED: '智能选中算法执行失败',
  DELETE_CONFIRM: '确定要永久删除选中的 {count} 个项目吗？此操作无法撤销，文件将从磁盘移除。',
  DELETE_SUCCESS: '清理完成: 成功 {success}, 失败 {total}',
  DELETE_FAILED: '删除请求执行失败',
  CONFIG_SAVED: '规则已保存',
  SAVE_FAILED: '保存失败'
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

.action-card {
  background: var(--card-color);
  border-radius: 12px;
  margin-bottom: 16px;
}

.sync-progress {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  margin-bottom: 16px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 12px;
  color: #60a5fa;
  font-size: 14px;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat-card {
  background: var(--card-color);
  border-radius: 12px;
  padding: 12px;
  text-align: center;
  border-left: 4px solid #3B82F6;
}

.stat-label {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color);
}

.toolbar {
  background: var(--card-color);
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 16px;
}

.groups-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.group-card {
  background: var(--card-color);
  border: 1px solid #3B82F6;
  border-radius: 12px;
  overflow: hidden;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.group-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tmdb-id {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.item-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color);
}

.items-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(59, 130, 246, 0.05);
  border-radius: 8px;
  transition: background 0.2s;
}

.item-row.selected {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.item-checkbox {
  padding-top: 2px;
}

.checkbox {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.item-details {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
  word-break: break-all;
}

.item-path {
  font-size: 11px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 8px;
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.meta-item {
  font-size: 11px;
  color: var(--text-color);
  opacity: 0.7;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  background: var(--card-color);
  border-radius: 12px;
  border: 2px dashed rgba(255, 255, 255, 0.1);
  color: var(--text-color);
  opacity: 0.5;
}

.empty-state .n-icon {
  margin-bottom: 16px;
  opacity: 0.3;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.empty-hint {
  font-size: 12px;
  margin-top: 8px;
  opacity: 0.7;
}

.label-hint {
  opacity: 0.6;
  font-weight: normal;
  font-size: 12px;
}
</style>
