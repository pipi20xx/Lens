<template>
  <n-modal :show="show" @update:show="$emit('update:show', $event)" preset="card" title="选择路径" style="width: 500px">
    <n-breadcrumb style="margin-bottom: 12px">
      <n-breadcrumb-item v-for="(part, index) in pathParts" :key="index" @click="jumpToPath(index)">
        {{ part || '/' }}
      </n-breadcrumb-item>
    </n-breadcrumb>
    <n-list hoverable clickable size="small" style="max-height: 400px; overflow-y: auto">
      <n-list-item v-if="currentPath !== '/'" @click="goUp">
        <template #prefix>📁</template>
        .. (返回上级)
      </n-list-item>
      <n-list-item v-for="item in browserItems" :key="item.path" @click="handleBrowserClick(item)">
        <template #prefix>{{ item.is_dir ? '📁' : '📄' }}</template>
        {{ item.name }}
        <template #suffix v-if="!item.is_dir">
          {{ (item.size / 1024 / 1024).toFixed(2) }} MB
        </template>
      </n-list-item>
    </n-list>
    <template #footer>
      <n-space justify="space-between" align="center">
        <n-text depth="3" style="word-break: break-all; max-width: 300px">{{ currentPath }}</n-text>
        <n-button type="primary" @click="confirmPath">
          确认选择
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { 
  NModal, NBreadcrumb, NBreadcrumbItem, NList, NListItem, NSpace, NText, NButton, NIcon, useMessage 
} from 'naive-ui'
import { CheckCircleOutlined as CheckIcon } from '@vicons/material'
import axios from 'axios'

const props = defineProps<{
  show: boolean
  initialPath?: string
}>()

const emit = defineEmits(['update:show', 'select'])
const message = useMessage()

const currentPath = ref(props.initialPath || '/')
const browserItems = ref([])
const pathParts = computed(() => currentPath.value.split('/').filter(Boolean))

const fetchBrowserItems = async () => {
  try {
    const res = await axios.get(`/api/backup/path-browser?path=${encodeURIComponent(currentPath.value)}`)
    browserItems.value = res.data.items
  } catch (e) {
    message.error('无法读取目录')
  }
}

const handleBrowserClick = (item) => {
  if (item.is_dir) {
    currentPath.value = item.path
    fetchBrowserItems()
  }
}

const goUp = () => {
  const parts = currentPath.value.split('/').filter(Boolean)
  parts.pop()
  currentPath.value = '/' + (parts.join('/') || '')
  if (currentPath.value === '//') currentPath.value = '/'
  fetchBrowserItems()
}

const jumpToPath = (index) => {
  const parts = pathParts.value.slice(0, index + 1)
  currentPath.value = '/' + parts.join('/')
  fetchBrowserItems()
}

const confirmPath = () => {
  emit('select', currentPath.value)
  emit('update:show', false)
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    currentPath.value = props.initialPath || '/'
    fetchBrowserItems()
  }
})
</script>