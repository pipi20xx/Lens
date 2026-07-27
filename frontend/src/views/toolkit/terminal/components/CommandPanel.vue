<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { terminalApi } from '@/api/terminal'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const emit = defineEmits<{ send: [cmd: string, autoEnter: boolean] }>()

const commands = ref<any[]>([])
const autoEnter = ref(false)
const showCmdDialog = ref(false)
const editingId = ref<number | null>(null)
const cmdForm = ref({ title: '', command: '' })
const dragIndex = ref<number | null>(null)

async function fetchCommands() {
  try {
    const data = await terminalApi.getCommands()
    commands.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载命令列表失败')
  }
}

function openAddDialog() {
  editingId.value = null
  cmdForm.value = { title: '', command: '' }
  showCmdDialog.value = true
}

function openEditDialog(cmd: any) {
  editingId.value = cmd.id
  cmdForm.value = { title: cmd.title || '', command: cmd.command || '' }
  showCmdDialog.value = true
}

async function saveCommand() {
  try {
    await terminalApi.saveCommand({ id: editingId.value, ...cmdForm.value })
    success(editingId.value ? '命令已更新' : '命令已添加')
    showCmdDialog.value = false
    fetchCommands()
  } catch {
    showError('保存命令失败')
  }
}

async function deleteCommand(id: number) {
  const ok = await confirm({ title: '删除命令', content: '确定要删除此快速命令吗？', confirmColor: 'error' })
  if (!ok) return
  try {
    await terminalApi.deleteCommand(id)
    success('命令已删除')
    fetchCommands()
  } catch {
    showError('删除命令失败')
  }
}

async function saveOrder() {
  try {
    const ids = commands.value.map((c) => c.id)
    await terminalApi.reorderCommands(ids)
  } catch {
    /* ignore */
  }
}

function onDragStart(index: number) {
  dragIndex.value = index
}

function onDragOver(e: DragEvent, index: number) {
  e.preventDefault()
  if (dragIndex.value === null || dragIndex.value === index) return
  const list = [...commands.value]
  const item = list.splice(dragIndex.value, 1)[0]
  list.splice(index, 0, item)
  commands.value = list
  dragIndex.value = index
}

function onDragEnd() {
  dragIndex.value = null
  saveOrder()
}

onMounted(fetchCommands)
</script>

<template>
  <div class="command-panel">
    <div class="panel-header d-flex align-center justify-space-between px-4 py-3">
      <span class="text-subtitle-2 font-weight-bold">快速命令</span>
      <v-btn icon="mdi-plus" variant="text" size="small" density="compact" color="primary" @click="openAddDialog" />
    </div>
    <v-divider />

    <div class="px-4 py-2">
      <v-checkbox v-model="autoEnter" label="点击即执行" density="compact" hide-details color="primary" />
    </div>
    <v-divider />

    <div class="command-list px-3 py-2" style="flex:1;overflow-y:auto">
      <div
        v-for="(cmd, index) in commands"
        :key="cmd.id"
        class="command-card mb-2 pa-3 rounded-lg cursor-pointer"
        :style="{ opacity: dragIndex === index ? 0.5 : 1 }"
        draggable="true"
        @dragstart="onDragStart(index)"
        @dragover="onDragOver($event, index)"
        @dragend="onDragEnd"
        @click="emit('send', cmd.command, autoEnter)"
      >
        <div class="d-flex align-center justify-space-between mb-1">
          <div class="d-flex align-center ga-1" style="min-width:0;flex:1">
            <v-icon size="14" class="drag-handle" style="cursor:grab;opacity:0.3">mdi-drag-vertical</v-icon>
            <span class="text-body-2 font-weight-medium" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ cmd.title }}</span>
          </div>
          <div class="d-flex ga-1">
            <v-btn icon="mdi-pencil-outline" variant="text" size="x-small" density="compact" color="warning" @click.stop="openEditDialog(cmd)" />
            <v-btn icon="mdi-delete-outline" variant="text" size="x-small" density="compact" color="error" @click.stop="deleteCommand(cmd.id)" />
          </div>
        </div>
        <div class="font-mono text-caption text-medium-emphasis" style="font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ cmd.command }}</div>
      </div>

      <div v-if="commands.length === 0" class="text-center py-6 text-medium-emphasis text-body-2">
        <v-icon size="32" color="grey" class="mb-2">mdi-flash-outline</v-icon>
        <div>暂无快速命令</div>
      </div>
    </div>

    <GlassDialog v-model="showCmdDialog" :max-width="420"
      icon="mdi-flash" :title="editingId ? '编辑命令' : '新建命令'"
    >
      <v-text-field v-model="cmdForm.title" label="标题" variant="outlined" density="compact" placeholder="例如：查看日志" class="mb-3" />
      <v-textarea v-model="cmdForm.command" label="命令" variant="outlined" density="compact" rows="3" placeholder="tail -f /app/logs/app.log" />

      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveCommand">保存</v-btn>
      </template>
    </GlassDialog>
  </div>
</template>

<style scoped>
.command-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.command-card {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  transition: border-color 0.2s, background 0.2s;
}
.command-card:hover {
  border-color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-on-surface), 0.03);
}
.drag-handle:hover {
  opacity: 1 !important;
  color: rgb(var(--v-theme-primary));
}
.drag-handle:active {
  cursor: grabbing;
}
</style>