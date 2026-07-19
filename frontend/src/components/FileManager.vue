<template>
  <div class="file-manager" @contextmenu.prevent="handleGlobalContextMenu">
    <!-- 工具栏 -->
    <div class="fm-toolbar">
      <n-space justify="space-between" align="center" style="width: 100%">
        <n-space align="center">
          <n-button-group size="small">
            <n-button @click="browse(getParentPath(currentPath))" :disabled="currentPath === '/'">
            </n-button>
            <n-button @click="browse(currentPath)">
            </n-button>
          </n-button-group>
          
          <n-breadcrumb separator=">">
            <n-breadcrumb-item @click="browse('/')">根目录</n-breadcrumb-item>
            <n-breadcrumb-item v-for="(part, index) in pathParts" :key="index" @click="jumpTo(index)">
              {{ part }}
            </n-breadcrumb-item>
          </n-breadcrumb>
        </n-space>

        <n-space>
          <n-button size="small" type="success" secondary @click="triggerUpload">
            上传文件
          </n-button>
          <n-button size="small" type="primary" secondary @click="showMkdirModal = true">
            新建文件夹
          </n-button>
          <n-button size="small" type="info" secondary @click="showMkfileModal = true">
            新建文件
          </n-button>
        </n-space>
      </n-space>
    </div>

    <!-- 隐藏的上传控件 -->
    <input 
      type="file" 
      multiple 
      ref="fileInputRef" 
      style="display: none" 
      @change="onFileChange" 
    />

    <!-- 内容列表 -->
    <div class="fm-content" @click="selectedPath = null">
      <n-spin :show="loading">
        <n-list hoverable bordered class="file-list">
          <n-list-item v-if="currentPath !== '/'" @dblclick="browse(getParentPath(currentPath))" class="file-item">
            <template #prefix><n-icon size="24" color="#8c8c8c"><FolderIcon /></n-icon></template>
            <n-text depth="3">.. (返回上级)</n-text>
          </n-list-item>

          <n-list-item 
            v-for="item in items" 
            :key="item.path" 
            :class="{ 'is-selected': selectedPath === item.path }"
            class="file-item"
            @click.stop="selectItem(item)"
            @dblclick="handleDoubleClick(item)"
            @contextmenu.stop="handleItemContextMenu($event, item)"
          >
            <template #prefix>
              <n-icon size="24" :color="item.is_dir ? '#fadb14' : '#8c8c8c'">
                <folder-icon v-if="item.is_dir" />
                <file-icon v-else />
              </n-icon>
            </template>
            
            <div class="item-info">
              <n-text :strong="item.is_dir" class="item-name">{{ item.name }}</n-text>
              <div class="item-meta">
                <span v-if="!item.is_dir" class="meta-size">{{ formatSize(item.size) }}</span>
                <span v-if="item.mode" class="meta-mode">{{ item.mode }}</span>
                <span v-if="item.mtime" class="meta-time">{{ formatTime(item.mtime) }}</span>
              </div>
            </div>
            
            <template #suffix>
              <div class="item-actions">
                <slot name="actions" :item="item"></slot>
              </div>
            </template>
          </n-list-item>
        </n-list>
      </n-spin>
    </div>

    <!-- 右键菜单 -->
    <n-dropdown
      placement="bottom-start"
      trigger="manual"
      :x="contextMenuX"
      :y="contextMenuY"
      :show="showContextMenu"
      :options="contextMenuOptions"
      @clickoutside="showContextMenu = false"
      @select="onContextMenuSelect"
    />

    <!-- 弹窗组件 -->
    <PermissionModal 
      v-model:show="showPermissionModal" 
      :item="activeItem" 
      :host-id="hostId" 
      :provider="provider"
      @success="browse(currentPath)"
    />

    <EditorModal 
      v-model:show="showEditor" 
      :item="activeItem" 
      :host-id="hostId" 
      :provider="provider" 
    />

    <!-- 弹窗：新建文件夹 -->
    <n-modal v-model:show="showMkdirModal" preset="dialog" title="新建文件夹" positive-text="创建" negative-text="取消" @positive-click="onMkdir">
      <n-input v-model:value="newDirName" placeholder="文件夹名称" @keypress.enter="onMkdir" />
    </n-modal>

    <!-- 弹窗：新建文件 -->
    <n-modal v-model:show="showMkfileModal" preset="dialog" title="新建文件" positive-text="创建" negative-text="取消" @positive-click="onMkfile">
      <n-input v-model:value="newFileName" placeholder="文件名称" @keypress.enter="onMkfile" />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, h, onMounted, nextTick, computed } from 'vue'
import { 
  NSpace, NBreadcrumb, NBreadcrumbItem, NList, NListItem, NText, NButton, NButtonGroup,
  NIcon, NInput, NSpin, NModal, NDropdown
} from 'naive-ui'
import {
  ArrowDownTrayIcon,
  ArrowPathIcon,
  ClipboardDocumentIcon,
  DocumentDuplicateIcon,
  DocumentPlusIcon,
  FolderIcon,
  FolderPlusIcon,
  LinkIcon,
  PencilIcon,
  ScissorsIcon,
  ShieldCheckIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'
import { useFileManager } from './file-manager/useFileManager'
import PermissionModal from './file-manager/PermissionModal.vue'
import EditorModal from './file-manager/EditorModal.vue'
import { formatSize, formatTime, getParentPath } from './file-manager/utils'

const props = defineProps<{
  hostId: number | string
  provider: any
  initialPath?: string
}>()

// 所有业务逻辑和状态都从 Composable 中获取
const { 
  loading, items, currentPath, pathParts, selectedPath,
  showPermissionModal, showEditor, showMkdirModal, showMkfileModal, activeItem, newDirName, newFileName,
  clipboard,
  browse, jumpTo, handleAction, openEditor, onMkdir, selectItem, 
  copyPath, handleCopy, handlePaste, createFile, handleUpload, handleDownload
} = useFileManager(props)

const fileInputRef = ref<HTMLInputElement | null>(null)

const triggerUpload = () => {
  fileInputRef.value?.click()
}

const onFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    handleUpload(Array.from(target.files))
    target.value = '' // 清空以便下次触发
  }
}

// 组件内仅保留 UI 交互相关的状态
const showContextMenu = ref(false)
const contextMenuX = ref(0)
const contextMenuY = ref(0)
const menuMode = ref<'item' | 'global'>('item')
const contextMenuItem = ref<any>(null)

const handleDoubleClick = (item: any) => {
  if (item.is_dir) browse(item.path)
  else openEditor(item)
}

const handleItemContextMenu = (e: MouseEvent, item: any) => {
  e.preventDefault()
  showContextMenu.value = false
  selectItem(item)
  menuMode.value = 'item'
  contextMenuItem.value = item
  nextTick(() => {
    contextMenuX.value = e.clientX
    contextMenuY.value = e.clientY
    showContextMenu.value = true
  })
}

const handleGlobalContextMenu = (e: MouseEvent) => {
  e.preventDefault()
  showContextMenu.value = false
  menuMode.value = 'global'
  contextMenuItem.value = null
  nextTick(() => {
    contextMenuX.value = e.clientX
    contextMenuY.value = e.clientY
    showContextMenu.value = true
  })
}

const contextMenuOptions = computed(() => {
  if (menuMode.value === 'global') {
    return [
      { label: '新建文件夹', key: 'mkdir', icon: () => h(NIcon, null, { default: () => h(FolderPlusIcon) }) },
      { label: '新建文件', key: 'mkfile', icon: () => h(NIcon, null, { default: () => h(DocumentPlusIcon) }) },
      { type: 'divider', key: 'd0' },
      { label: '粘贴', key: 'paste', disabled: !clipboard.path, icon: () => h(NIcon, null, { default: () => h(ClipboardDocumentIcon) }) },
      { label: '刷新', key: 'refresh', icon: () => h(NIcon, null, { default: () => h(ArrowPathIcon) }) },
    ]
  }

  const item = contextMenuItem.value
  if (!item) return []
  
  return [
    { label: item.is_dir ? '打开文件夹' : '编辑文件', key: 'open', icon: () => h(NIcon, null, { default: () => h(item.is_dir ? FolderIcon : PencilIcon) }) },
    { type: 'divider', key: 'd1' },
    { label: '复制', key: 'copy', icon: () => h(NIcon, null, { default: () => h(DocumentDuplicateIcon) }) },
    { label: '剪切', key: 'cut', icon: () => h(NIcon, null, { default: () => h(ScissorsIcon) }) },
    { label: '复制完整路径', key: 'copyPath', icon: () => h(NIcon, null, { default: () => h(LinkIcon) }) },
    { label: '下载文件', key: 'download', disabled: item.is_dir, icon: () => h(NIcon, null, { default: () => h(ArrowDownTrayIcon) }) },
    { type: 'divider', key: 'd2' },
    { label: '重命名', key: 'rename', icon: () => h(NIcon, null, { default: () => h(PencilIcon) }) },
    { label: '权限设置', key: 'chmod', icon: () => h(NIcon, null, { default: () => h(ShieldCheckIcon) }) },
    { type: 'divider', key: 'd3' },
    { label: '删除', key: 'delete', icon: () => h(NIcon, null, { default: () => h(TrashIcon) }) },
  ]
})

const onContextMenuSelect = (key: string) => {
  const item = contextMenuItem.value
  
  if (key === 'copyPath') {
    // 关键：在任何 UI 状态改变（如关闭菜单）之前，立即同步执行复制
    copyPath(item.path)
    showContextMenu.value = false
    return
  }

  showContextMenu.value = false

  if (key === 'open') handleDoubleClick(item)
  else if (key === 'copy') handleCopy(item, 'copy')
  else if (key === 'cut') handleCopy(item, 'cut')
  else if (key === 'download') handleDownload(item)
  else if (key === 'paste') handlePaste()
  else if (key === 'mkdir') showMkdirModal.value = true
  else if (key === 'mkfile') showMkfileModal.value = true
  else if (key === 'refresh') browse(currentPath.value)
  else if (item) handleAction(key, item)
}

const onMkfile = async () => {
  if (await createFile(newFileName.value)) {
    newFileName.value = ''
    showMkfileModal.value = false
  }
}

// 彻底移除冗余的 onMkdir / openEditor 等声明

onMounted(() => browse(currentPath.value))
</script>

<style scoped>
.file-manager { display: flex; flex-direction: column; height: 100%; overflow: hidden; background: var(--app-bg-color); }
.fm-toolbar { padding: 10px 16px; flex-shrink: 0; border-bottom: 1px solid var(--border-color); background: var(--card-bg-color); }
.fm-content { flex: 1; overflow: hidden; position: relative; }
.fm-content :deep(.n-spin),
.fm-content :deep(.n-spin-container),
.fm-content :deep(.n-spin-content) { height: 100%; display: flex; flex-direction: column; }

.file-list { flex: 1; overflow-y: auto !important; height: 100%; padding: 4px 0; }

.file-item { 
  padding: 8px 16px !important; 
  cursor: default; 
  user-select: none;
  transition: background-color 0.2s;
  border: none !important;
  margin: 2px 8px;
  border-radius: 4px;
}

.file-item:hover { background-color: rgba(var(--primary-color-rgb, 100, 100, 100), 0.08) !important; }
.file-item.is-selected { 
  background-color: rgba(var(--primary-color-rgb, 100, 100, 100), 0.15) !important; 
  outline: 1px solid var(--primary-color);
}

.item-info { flex: 1; margin-left: 12px; overflow: hidden; }
.item-name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; color: var(--text-color); }
.item-meta { font-size: 11px; opacity: 0.5; display: flex; gap: 16px; margin-top: 2px; }

.item-actions { display: flex; align-items: center; gap: 8px; }
</style>