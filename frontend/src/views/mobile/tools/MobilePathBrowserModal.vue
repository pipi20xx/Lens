<template>
  <n-modal 
    :show="show" 
    @update:show="$emit('update:show', $event)" 
    preset="card" 
    :title="label.SELECT_PATH" 
    style="width: 95vw; max-width: 500px"
  >
    <n-spin :show="loading">
      <div class="path-browser">
        <div class="current-path">
          <n-text depth="3" style="font-size: 12px; margin-bottom: 4px;">{{ label.CURRENT_PATH }}:</n-text>
          <div class="path-display">{{ currentPath }}</div>
        </div>

        <div class="path-actions">
          <n-button size="small" secondary @click="goUp" :disabled="currentPath === '/'">
            {{ buttonText.GO_UP }}
          </n-button>
          <n-button size="small" secondary @click="goHome">
            {{ buttonText.GO_HOME }}
          </n-button>
        </div>

        <div v-if="items.length === 0" class="empty-state">
          <n-empty :description="messageText.EMPTY_DATA" />
        </div>

        <div v-else class="file-list">
          <div 
            v-for="item in items" 
            :key="item.name" 
            class="file-item"
            @click="handleItemClick(item)"
          >
            <div class="file-icon">
              <n-icon :size="24" :color="item.is_dir ? '#7c3aed' : '#909399'">
                <component :is="item.is_dir ? FolderIcon : FileIcon" />
              </n-icon>
            </div>
            <div class="file-info">
              <div class="file-name">{{ item.name }}</div>
              <div v-if="!item.is_dir" class="file-size">{{ formatSize(item.size) }}</div>
            </div>
          </div>
        </div>
      </div>
    </n-spin>

    <template #footer>
      <n-space justify="end">
        <n-button @click="$emit('update:show', false)">
          {{ buttonText.CANCEL }}
        </n-button>
        <n-button :type="buttonTypes.PRIMARY" @click="handleSelect">
          {{ buttonText.SELECT }}
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { NModal, NSpin, NEmpty, NText, NButton, NSpace, NIcon, useMessage } from 'naive-ui'
import {
  FolderOpenOutlined as FolderIcon,
  DescriptionOutlined as FileIcon
} from '@vicons/material'
import {
  ButtonTypes,
  ButtonText,
  MessageText,
  Label,
} from '../constants'
import axios from 'axios'

const props = defineProps<{
  show: boolean
  initialPath?: string
}>()

const emit = defineEmits(['update:show', 'select'])

const message = useMessage()

const buttonTypes = ButtonTypes
const buttonText = ButtonText
const messageText = MessageText
const label = Label

const currentPath = ref('/')
const items = ref<any[]>([])
const loading = ref(false)

const formatSize = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

const fetchItems = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/backup/browse', { params: { path: currentPath.value } })
    items.value = res.data || []
  } catch (e) {
    message.error(messageText.LOAD_FAILED)
    items.value = []
  } finally {
    loading.value = false
  }
}

const goUp = () => {
  if (currentPath.value === '/') return
  const parts = currentPath.value.split('/').filter(p => p)
  parts.pop()
  currentPath.value = '/' + parts.join('/')
  fetchItems()
}

const goHome = () => {
  currentPath.value = '/'
  fetchItems()
}

const handleItemClick = (item: any) => {
  if (item.is_dir) {
    currentPath.value = currentPath.value === '/' 
      ? '/' + item.name 
      : currentPath.value + '/' + item.name
    fetchItems()
  }
}

const handleSelect = () => {
  emit('select', currentPath.value)
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    currentPath.value = props.initialPath || '/'
    fetchItems()
  }
})
</script>

<style scoped>
.path-browser {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.current-path {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 8px;
}

.path-display {
  font-family: monospace;
  font-size: 14px;
  word-break: break-all;
  color: var(--text-color);
}

.path-actions {
  display: flex;
  gap: 8px;
}

.empty-state {
  padding: 40px 0;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.file-item:hover {
  background-color: var(--modal-color);
}

.file-icon {
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  word-break: break-all;
}

.file-size {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-top: 2px;
}
</style>
