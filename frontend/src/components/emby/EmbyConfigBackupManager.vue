<script setup lang="ts">
import { ref, watch } from 'vue'
import { embyBackupApi } from '@/api/embyBackup'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const props = defineProps<{
  category: 'users' | 'libraries'
  serverId?: string
}>()

const emit = defineEmits(['restored'])
const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const showModal = ref(false)
const loading = ref(false)
const restoringAll = ref(false)
const backups = ref<any[]>([])

async function loadBackups() {
  loading.value = true
  try {
    const res = await embyBackupApi.list(props.category, props.serverId)
    backups.value = Array.isArray(res) ? res : []
  } catch {
    showError('加载备份列表失败')
  } finally {
    loading.value = false
  }
}

async function handleRestore(filename: string) {
  const ok = await confirm({ title: '还原确认', content: '确定要将此配置还原到服务器吗？当前设置将被覆盖。' })
  if (!ok) return
  try {
    await embyBackupApi.restore(props.category, filename, props.serverId)
    success('配置还原成功')
    emit('restored')
    showModal.value = false
  } catch { showError('还原失败') }
}

async function handleDelete(filename: string) {
  const ok = await confirm({ title: '删除确认', content: '确定删除此备份文件吗？', confirmColor: 'error' })
  if (!ok) return
  try {
    await embyBackupApi.delete(props.category, filename)
    success('备份已删除')
    loadBackups()
  } catch { showError('删除失败') }
}

async function handleRestoreAll() {
  const ok = await confirm({ title: '一键还原', content: '确定要将所有配置还原吗？系统将为每个用户/媒体库选取最新的一份备份进行恢复。' })
  if (!ok) return
  restoringAll.value = true
  try {
    const res: any = await embyBackupApi.restoreAll(props.category, props.serverId)
    success(`成功还原 ${res?.count ?? ''} 项最新配置`)
    emit('restored')
    showModal.value = false
  } catch { showError('还原失败') }
  finally { restoringAll.value = false }
}

async function handleClearAll() {
  const ok = await confirm({ title: '清空确认', content: '确定要删除当前分类下的所有备份文件吗？此操作不可撤销。', confirmColor: 'error' })
  if (!ok) return
  try {
    await embyBackupApi.clear(props.category)
    success('所有备份已清空')
    loadBackups()
  } catch { showError('清空失败') }
}

watch(showModal, (val) => {
  if (val) loadBackups()
})
</script>

<template>
  <v-btn variant="tonal" color="info" size="small" prepend-icon="mdi-history" @click="showModal = true">
    配置备份管理
  </v-btn>

  <v-dialog v-model="showModal" max-width="750" scrollable>
    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start>mdi-history</v-icon>
        配置备份历史
        <v-spacer />
        <v-btn variant="tonal" color="warning" size="x-small" prepend-icon="mdi-restore" :loading="restoringAll" :disabled="!backups.length" @click="handleRestoreAll">一键还原最新备份</v-btn>
        <v-btn variant="tonal" color="error" size="x-small" prepend-icon="mdi-delete-sweep-outline" class="ml-2" :disabled="!backups.length" @click="handleClearAll">清空所有备份</v-btn>
      </v-card-title>
      <v-divider />

      <v-alert variant="tonal" type="info" density="compact" class="ma-4 mb-0" rounded="lg">
        备份将保存当前选定对象的完整原始 JSON 配置。还原操作将直接覆盖服务器上的现有设置，请谨慎操作。
      </v-alert>

      <v-card-text class="pa-4">
        <div v-if="loading" class="text-center py-4"><v-progress-circular indeterminate color="primary" /></div>
        <div v-else-if="!backups.length" class="text-center py-8 text-medium-emphasis">暂无备份数据</div>
        <v-table v-else class="bg-transparent" density="compact">
          <thead><tr><th>备份名称</th><th>备份时间</th><th class="text-right">操作</th></tr></thead>
          <tbody>
            <tr v-for="b in backups" :key="b.filename">
              <td class="font-weight-medium">{{ b.filename?.split('_20')[0] }}</td>
              <td class="text-medium-emphasis">{{ b.mtime ? new Date(b.mtime * 1000).toLocaleString() : '-' }}</td>
              <td class="text-right">
                <v-btn size="x-small" variant="tonal" color="warning" prepend-icon="mdi-restore" @click="handleRestore(b.filename)" class="mr-1">还原</v-btn>
                <v-btn size="x-small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="handleDelete(b.filename)">删除</v-btn>
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>
