<template>
  <n-modal v-model:show="show" preset="card" :title="'文件管理器: Docker 主机'" style="width: 90vw; max-width: 1100px">
    <FileManager 
      :host-id="hostId" 
      :provider="dockerProvider" 
      :initial-path="initialPath"
    >
      <template #actions="{ item }">
        <template v-if="item.is_dir">
          <n-button 
            v-if="isSelected(item.path)"
            size="small" type="error" quaternary @click.stop="$emit('remove', item.path)"
          >
            取消扫描
          </n-button>
          <n-button 
            v-else
            size="small" type="primary" quaternary @click.stop="$emit('select', item.path)"
          >
            设为扫描路径
          </n-button>

          <n-button size="small" type="info" quaternary @click.stop="createBackup(item)">
            设为SSH备份
          </n-button>
        </template>
      </template>
    </FileManager>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { NModal, NButton, NIcon, useMessage, useDialog } from 'naive-ui'
import { 
  ManageSearchOutlined as ScanIcon,
  CloudUploadOutlined as BackupIcon,
  CancelOutlined as CancelIcon
} from '@vicons/material'
import axios from 'axios'
import FileManager from '@/components/FileManager.vue'

const props = defineProps<{
  show: boolean
  hostId: string
  selectedPaths: string[]
  initialPath?: string
}>()

const emit = defineEmits(['update:show', 'select', 'remove'])

const message = useMessage()
const dialog = useDialog()
const show = ref(props.show)

watch(() => props.show, (val) => show.value = val)
watch(() => show.value, (val) => emit('update:show', val))

const isSelected = (path: string) => props.selectedPaths.includes(path)

const createBackup = (item: any) => {
  dialog.info({
    title: '创建 SSH 备份',
    content: `确定要为文件夹 ${item.name} 创建一个 SSH 自动备份任务吗？`,
    positiveText: '确认创建',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.post(`/api/docker/compose/${props.hostId}/create-folder-backup`, { 
          path: item.path 
        })
        message.success('备份任务已创建')
      } catch (e: any) {
        message.error('创建失败: ' + (e.response?.data?.detail || '未知错误'))
      }
    }
  })
}

// Docker 专用的 Provider 适配
const dockerProvider = reactive({
  ls: async (hostId: string, path: string) => {
    const res = await axios.get(`/api/docker/compose/${hostId}/ls`, { params: { path } })
    return res.data
  },
  read: async (hostId: string, path: string) => {
    const res = await axios.get(`/api/docker/compose/${hostId}/projects/file`, {
      params: { path: path, name: 'temp' }
    })
    return res.data
  },
  write: async (hostId: string, path: string, content: string) => {
    return await axios.post(`/api/docker/compose/${hostId}/projects`, { name: 'temp', content }, { params: { path } })
  },
  action: async (hostId: string, action: string, path: string, target?: string) => {
    // Docker 模式下，借用 chmod 接口实现 mkdir 和 delete
    if (action === 'mkdir') {
        return await axios.post(`/api/docker/compose/${hostId}/chmod`, { path, mode: '755' }) 
    }
    if (action === 'delete') {
        return await axios.post(`/api/docker/compose/${hostId}/chmod`, { path, action: 'delete' })
    }
    if (action === 'rename' || action === 'move' || action === 'copy') {
        // 目前后端 docker_compose.py 尚未实现 mv/cp 命令，提示不支持
        message.warning(`Docker 模式暂不支持 ${action} 操作`)
        return true
    }
    return true
  },
  chmod: async (hostId: string, data: any) => {
    const res = await axios.post(`/api/docker/compose/${hostId}/chmod`, data)
    return res.data
  }
})
</script>
