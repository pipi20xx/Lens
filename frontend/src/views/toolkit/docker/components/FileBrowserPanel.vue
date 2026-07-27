<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { filesApi } from '@/api/files'
import { downloadFile } from '@/api/client'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import { useDockerHost } from '../composables/useDockerHost'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError, info, warning } = useNotification()
const { confirm } = useConfirm()
const { currentHost } = useDockerHost()

const props = defineProps<{
  active: boolean
  hostId: string | null
}>()

// ========== 自动加载 ==========
const loaded = ref(false)
watch([() => props.active, () => props.hostId], ([active, hostId]) => {
  if (active && hostId) { browse(currentPath.value); loaded.value = true }
})
onMounted(() => { if (props.active && props.hostId) { browse(currentPath.value); loaded.value = true } })

// ========== 文件列表状态 ==========
interface FileItem {
  name: string
  path: string
  is_dir: boolean
  size?: number
  mtime?: number
  mode?: string
}

const loading = ref(false)
const items = ref<FileItem[]>([])
const currentPath = ref('/')
const selectedPath = ref<string | null>(null)
const pathParts = computed(() => currentPath.value.split('/').filter(p => p))

// ========== 浏览 ==========
async function browse(path: string) {
  if (!props.hostId) { warning('请先选择 Docker 主机'); return }
  loading.value = true
  selectedPath.value = null
  try {
    const res: any = await filesApi.ls(props.hostId, path)
    currentPath.value = res.current_path || path
    items.value = res.items || []
  } catch (e: any) {
    showError('加载目录失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

function jumpTo(index: number) {
  const target = '/' + pathParts.value.slice(0, index + 1).join('/')
  browse(target)
}

function getParentPath(path: string): string {
  if (path === '/') return '/'
  const p = path.replace(/\/$/, '')
  return p.substring(0, p.lastIndexOf('/')) || '/'
}

function goUp() { browse(getParentPath(currentPath.value)) }

function selectItem(item: FileItem) {
  selectedPath.value = selectedPath.value === item.path ? null : item.path
}

function handleDoubleClick(item: FileItem) {
  if (item.is_dir) browse(item.path)
  else openEditor(item)
}

// ========== 文件编辑器 ==========
const showEditor = ref(false)
const editorItem = ref<FileItem | null>(null)
const editorContent = ref('')
const editorLoading = ref(false)
const editorSaving = ref(false)

async function openEditor(item: FileItem) {
  editorItem.value = item
  showEditor.value = true
  editorLoading.value = true
  editorContent.value = ''
  try {
    const res: any = await filesApi.read(props.hostId!, item.path)
    editorContent.value = res.content ?? ''
  } catch (e: any) {
    showError('读取文件失败: ' + (e.message || ''))
  } finally {
    editorLoading.value = false
  }
}

async function saveEditor() {
  if (!props.hostId || !editorItem.value) return
  editorSaving.value = true
  try {
    await filesApi.write(props.hostId, editorItem.value.path, editorContent.value)
    success('文件已保存')
    showEditor.value = false
    browse(currentPath.value)
  } catch (e: any) {
    showError('保存失败: ' + (e.message || ''))
  } finally {
    editorSaving.value = false
  }
}

// ========== 权限修改 ==========
const showPermission = ref(false)
const permItem = ref<FileItem | null>(null)
const permForm = ref({ mode: '0755', owner: '', group: '', recursive: false })
const permMatrix = ref({
  owner: { read: true, write: true, execute: true },
  group: { read: true, write: false, execute: true },
  public: { read: true, write: false, execute: true },
})
const permSubmitting = ref(false)

function openPermission(item: FileItem) {
  permItem.value = item
  const mode = item.mode || (item.is_dir ? '0755' : '0644')
  const m = mode.startsWith('0') ? mode : '0' + mode
  permForm.value.mode = m
  const parse = (char: string) => {
    const n = parseInt(char)
    return { read: !!(n & 4), write: !!(n & 2), execute: !!(n & 1) }
  }
  const code = m.slice(-3)
  permMatrix.value.owner = parse(code[0])
  permMatrix.value.group = parse(code[1])
  permMatrix.value.public = parse(code[2])
  showPermission.value = true
}

function calcPermMode() {
  const getVal = (role: 'owner' | 'group' | 'public') => {
    let val = 0
    if (permMatrix.value[role].read) val += 4
    if (permMatrix.value[role].write) val += 2
    if (permMatrix.value[role].execute) val += 1
    return val
  }
  permForm.value.mode = `0${getVal('owner')}${getVal('group')}${getVal('public')}`
}

async function submitPermission() {
  if (!props.hostId || !permItem.value) return
  permSubmitting.value = true
  try {
    await filesApi.chmod(props.hostId, {
      path: permItem.value.path,
      mode: permForm.value.mode.slice(-3),
      owner: permForm.value.owner,
      group: permForm.value.group,
      recursive: permForm.value.recursive,
    })
    success('权限已更新')
    showPermission.value = false
    browse(currentPath.value)
  } catch (e: any) {
    showError('权限更新失败: ' + (e.message || ''))
  } finally {
    permSubmitting.value = false
  }
}

// ========== 新建文件夹/文件 ==========
const showMkdir = ref(false)
const showMkfile = ref(false)
const newName = ref('')

async function doMkdir() {
  if (!props.hostId || !newName.value.trim()) return
  const target = (currentPath.value.endsWith('/') ? currentPath.value : currentPath.value + '/') + newName.value.trim()
  try {
    await filesApi.action(props.hostId, 'mkdir', target)
    success('文件夹已创建')
    newName.value = ''
    showMkdir.value = false
    browse(currentPath.value)
  } catch (e: any) {
    showError('创建失败: ' + (e.message || ''))
  }
}

async function doMkfile() {
  if (!props.hostId || !newName.value.trim()) return
  const target = (currentPath.value.endsWith('/') ? currentPath.value : currentPath.value + '/') + newName.value.trim()
  try {
    await filesApi.write(props.hostId, target, '')
    success('文件已创建')
    newName.value = ''
    showMkfile.value = false
    browse(currentPath.value)
  } catch (e: any) {
    showError('创建失败: ' + (e.message || ''))
  }
}

// ========== 上传 ==========
const fileInputRef = ref<HTMLInputElement | null>(null)
const uploading = ref(false)

function triggerUpload() { fileInputRef.value?.click() }

async function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  if (!target.files?.length || !props.hostId) return
  uploading.value = true
  try {
    await filesApi.upload(props.hostId, currentPath.value, Array.from(target.files))
    success('上传成功')
    browse(currentPath.value)
  } catch (e: any) {
    showError('上传失败: ' + (e.message || ''))
  } finally {
    uploading.value = false
    target.value = ''
  }
}

// ========== 下载 ==========
async function handleDownload(item: FileItem) {
  if (item.is_dir) { warning('暂不支持下载文件夹'); return }
  if (!props.hostId) return
  try {
    await downloadFile(`/api/files/${props.hostId}/download?path=${encodeURIComponent(item.path)}`, item.name)
    success('下载已开始')
  } catch (e: any) {
    showError('下载失败: ' + (e.message || ''))
  }
}

// ========== 删除 ==========
async function handleDelete(item: FileItem) {
  const ok = await confirm({
    title: '确认删除',
    content: `确定要删除 "${item.name}" 吗？此操作不可撤销。`,
    confirmColor: 'error',
  })
  if (!ok || !props.hostId) return
  try {
    await filesApi.action(props.hostId, 'delete', item.path)
    success('已删除')
    browse(currentPath.value)
  } catch (e: any) {
    showError('删除失败: ' + (e.message || ''))
  }
}

// ========== 重命名 ==========
const showRename = ref(false)
const renameItem = ref<FileItem | null>(null)
const renameNewName = ref('')

function openRename(item: FileItem) {
  renameItem.value = item
  renameNewName.value = item.name
  showRename.value = true
}

async function doRename() {
  if (!props.hostId || !renameItem.value || !renameNewName.value.trim()) return
  const target = getParentPath(renameItem.value.path) + '/' + renameNewName.value.trim()
  try {
    await filesApi.action(props.hostId, 'rename', renameItem.value.path, target)
    success('重命名成功')
    showRename.value = false
    browse(currentPath.value)
  } catch (e: any) {
    showError('重命名失败: ' + (e.message || ''))
  }
}

// ========== 复制路径 ==========
function copyPath(item: FileItem) {
  navigator.clipboard.writeText(item.path).then(
    () => success(`已复制: ${item.path}`),
    () => showError('复制失败')
  )
}

// ========== 右键菜单 ==========
const contextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const contextMenuItem = ref<FileItem | null>(null)

function handleContextMenu(e: MouseEvent, item: FileItem) {
  e.preventDefault()
  e.stopPropagation()
  contextMenuItem.value = item
  selectedPath.value = item.path
  contextMenuX.value = e.clientX
  contextMenuY.value = e.clientY
  nextTick(() => { contextMenu.value = true })
}

function handleContextMenuAction(key: string) {
  contextMenu.value = false
  const item = contextMenuItem.value
  if (!item) return
  if (key === 'open') handleDoubleClick(item)
  else if (key === 'edit') openEditor(item)
  else if (key === 'rename') openRename(item)
  else if (key === 'delete') handleDelete(item)
  else if (key === 'chmod') openPermission(item)
  else if (key === 'download') handleDownload(item)
  else if (key === 'copyPath') copyPath(item)
}

// ========== 格式化 ==========
function formatSize(bytes?: number) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatTime(ts?: number) {
  if (!ts) return ''
  const d = new Date(ts * 1000)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<template>
  <div v-if="!hostId" class="text-center py-8 text-medium-emphasis">
    <v-icon size="48" class="mb-2">mdi-folder-off-outline</v-icon>
    <div>请先选择一个 Docker 主机</div>
  </div>

  <div v-else>
    <!-- 工具栏 -->
    <v-card class="liquid-glass-card mb-4" rounded="xl">
      <div class="d-flex align-center pa-3 ga-2 flex-wrap">
        <!-- 返回上级 + 刷新 -->
        <v-btn icon variant="tonal" size="small" :disabled="currentPath === '/'" @click="goUp">
          <v-icon>mdi-arrow-up</v-icon>
        </v-btn>
        <v-btn icon variant="tonal" size="small" color="info" :loading="loading" @click="browse(currentPath)">
          <v-icon>mdi-refresh</v-icon>
        </v-btn>

        <!-- 面包屑 -->
        <v-breadcrumbs density="compact" class="pa-0 flex-grow-1" style="min-width: 0">
          <template #default>
            <v-breadcrumbs-item @click="browse('/')">根目录</v-breadcrumbs-item>
            <template v-for="(part, idx) in pathParts" :key="idx">
              <v-breadcrumbs-divider>/</v-breadcrumbs-divider>
              <v-breadcrumbs-item @click="jumpTo(idx)">{{ part }}</v-breadcrumbs-item>
            </template>
          </template>
        </v-breadcrumbs>

        <!-- 操作按钮 -->
        <v-btn variant="tonal" color="success" size="small" prepend-icon="mdi-upload" :loading="uploading" @click="triggerUpload">上传</v-btn>
        <v-btn variant="tonal" color="primary" size="small" prepend-icon="mdi-folder-plus-outline" @click="showMkdir = true; newName = ''">新建文件夹</v-btn>
        <v-btn variant="tonal" color="info" size="small" prepend-icon="mdi-file-plus-outline" @click="showMkfile = true; newName = ''">新建文件</v-btn>
      </div>
    </v-card>

    <input ref="fileInputRef" type="file" multiple style="display: none" @change="onFileChange" />

    <!-- 文件列表 -->
    <v-card class="liquid-glass-card" rounded="xl">
      <v-progress-linear v-if="loading" indeterminate color="primary" height="2" />

      <div v-if="!loading && items.length === 0" class="text-center py-8 text-medium-emphasis">
        <v-icon size="48" class="mb-2">mdi-folder-open-outline</v-icon>
        <div>空目录</div>
      </div>

      <v-list v-else density="compact" class="py-1">
        <!-- 返回上级 -->
        <v-list-item v-if="currentPath !== '/'" @click="goUp" class="rounded-lg mx-2">
          <template #prepend>
            <v-icon color="grey">mdi-folder-upload-outline</v-icon>
          </template>
          <v-list-item-title class="text-medium-emphasis">.. (返回上级)</v-list-item-title>
        </v-list-item>

        <v-list-item
          v-for="item in items"
          :key="item.path"
          :active="selectedPath === item.path"
          @click="selectItem(item)"
          @dblclick="handleDoubleClick(item)"
          @contextmenu.prevent="handleContextMenu($event, item)"
          class="rounded-lg mx-2 mb-0.5"
        >
          <template #prepend>
            <v-icon :color="item.is_dir ? 'warning' : 'grey'" class="mr-2">
              {{ item.is_dir ? 'mdi-folder' : 'mdi-file-outline' }}
            </v-icon>
          </template>

          <v-list-item-title :class="{ 'font-weight-bold': item.is_dir }">{{ item.name }}</v-list-item-title>
          <v-list-item-subtitle class="d-flex ga-3">
            <span v-if="!item.is_dir">{{ formatSize(item.size) }}</span>
            <span v-if="item.mode" class="font-mono text-caption">{{ item.mode }}</span>
            <span v-if="item.mtime">{{ formatTime(item.mtime) }}</span>
          </v-list-item-subtitle>

          <template #append>
            <div class="d-flex ga-1">
              <v-btn v-if="item.is_dir" icon variant="text" size="x-small" color="primary" @click.stop="browse(item.path)">
                <v-icon size="16">mdi-folder-open-outline</v-icon>
              </v-btn>
              <v-btn v-if="!item.is_dir" icon variant="text" size="x-small" color="info" @click.stop="openEditor(item)">
                <v-icon size="16">mdi-pencil-outline</v-icon>
              </v-btn>
              <v-btn icon variant="text" size="x-small" color="error" @click.stop="handleDelete(item)">
                <v-icon size="16">mdi-delete-outline</v-icon>
              </v-btn>
            </div>
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- 右键菜单 -->
    <v-menu v-model="contextMenu" :target="[contextMenuX, contextMenuY]" absolute>
      <v-list density="compact" rounded="lg">
        <template v-if="contextMenuItem?.is_dir">
          <v-list-item prepend-icon="mdi-folder-open-outline" @click="handleContextMenuAction('open')">打开文件夹</v-list-item>
        </template>
        <template v-else>
          <v-list-item prepend-icon="mdi-pencil-outline" @click="handleContextMenuAction('edit')">编辑文件</v-list-item>
          <v-list-item prepend-icon="mdi-download" @click="handleContextMenuAction('download')">下载文件</v-list-item>
        </template>
        <v-divider />
        <v-list-item prepend-icon="mdi-rename-outline" @click="handleContextMenuAction('rename')">重命名</v-list-item>
        <v-list-item prepend-icon="mdi-content-copy" @click="handleContextMenuAction('copyPath')">复制完整路径</v-list-item>
        <v-list-item prepend-icon="mdi-shield-lock-outline" @click="handleContextMenuAction('chmod')">权限设置</v-list-item>
        <v-divider />
        <v-list-item prepend-icon="mdi-delete-outline" base-color="error" @click="handleContextMenuAction('delete')">删除</v-list-item>
      </v-list>
    </v-menu>

    <!-- 文件编辑器弹窗 -->
    <GlassDialog v-model="showEditor" :max-width="1000" icon="mdi-file-edit-outline" :title="'编辑: ' + (editorItem?.name || '')" :scrollable="false" cancel-text="关闭">
      <v-progress-linear v-if="editorLoading" indeterminate color="primary" class="mb-2" />
      <v-textarea
        v-model="editorContent"
        :loading="editorLoading"
        :disabled="editorLoading"
        auto-grow
        rows="20"
        class="yaml-editor"
        variant="outlined"
        hide-details
      />
      <template #actions>
        <v-btn variant="tonal" color="primary" prepend-icon="mdi-content-save-outline" :loading="editorSaving" @click="saveEditor">保存</v-btn>
      </template>
    </GlassDialog>

    <!-- 权限修改弹窗 -->
    <GlassDialog v-model="showPermission" :max-width="520" icon="mdi-shield-lock-outline" title="权限设置" cancel-text="关闭">
      <div class="text-caption text-medium-emphasis font-mono mb-3">{{ permItem?.path }}</div>

      <v-table density="compact" class="mb-4 rounded-lg" hover>
        <thead>
          <tr><th>对象</th><th>读取</th><th>写入</th><th>执行</th></tr>
        </thead>
        <tbody>
          <tr v-for="role in (['owner', 'group', 'public'] as const)" :key="role">
            <td>{{ role === 'owner' ? '所有者' : role === 'group' ? '用户组' : '公共' }}</td>
            <td><v-checkbox v-model="permMatrix[role].read" density="compact" hide-details @update:model-value="calcPermMode" /></td>
            <td><v-checkbox v-model="permMatrix[role].write" density="compact" hide-details @update:model-value="calcPermMode" /></td>
            <td><v-checkbox v-model="permMatrix[role].execute" density="compact" hide-details @update:model-value="calcPermMode" /></td>
          </tr>
        </tbody>
      </v-table>

      <v-row density="comfortable">
        <v-col cols="6">
          <v-text-field v-model="permForm.mode" label="权限代码" variant="outlined" density="compact" placeholder="0755" hide-details />
        </v-col>
        <v-col cols="6">
          <div class="d-flex ga-1">
            <v-text-field v-model="permForm.owner" label="所有者" variant="outlined" density="compact" placeholder="root" hide-details />
            <span class="align-self-center text-medium-emphasis">:</span>
            <v-text-field v-model="permForm.group" label="用户组" variant="outlined" density="compact" placeholder="root" hide-details />
          </div>
        </v-col>
      </v-row>

      <v-checkbox v-if="permItem?.is_dir" v-model="permForm.recursive" label="递归应用到子项" density="compact" hide-details class="mt-2" />

      <template #actions>
        <v-btn variant="tonal" color="primary" prepend-icon="mdi-check" :loading="permSubmitting" @click="submitPermission">应用</v-btn>
      </template>
    </GlassDialog>

    <!-- 新建文件夹弹窗 -->
    <GlassDialog v-model="showMkdir" :max-width="400" icon="mdi-folder-plus-outline" title="新建文件夹">
      <v-text-field v-model="newName" label="文件夹名称" variant="outlined" density="compact" autofocus @keypress.enter="doMkdir" />
      <template #actions>
        <v-btn variant="tonal" color="primary" prepend-icon="mdi-plus" @click="doMkdir">创建</v-btn>
      </template>
    </GlassDialog>

    <!-- 新建文件弹窗 -->
    <GlassDialog v-model="showMkfile" :max-width="400" icon="mdi-file-plus-outline" title="新建文件">
      <v-text-field v-model="newName" label="文件名称" variant="outlined" density="compact" autofocus @keypress.enter="doMkfile" />
      <template #actions>
        <v-btn variant="tonal" color="primary" prepend-icon="mdi-plus" @click="doMkfile">创建</v-btn>
      </template>
    </GlassDialog>

    <!-- 重命名弹窗 -->
    <GlassDialog v-model="showRename" :max-width="400" icon="mdi-rename-outline" title="重命名">
      <v-text-field v-model="renameNewName" label="新名称" variant="outlined" density="compact" autofocus @keypress.enter="doRename" />
      <template #actions>
        <v-btn variant="tonal" color="primary" prepend-icon="mdi-check" @click="doRename">确定</v-btn>
      </template>
    </GlassDialog>
  </div>
</template>
