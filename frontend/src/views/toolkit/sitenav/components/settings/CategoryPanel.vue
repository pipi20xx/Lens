<script setup lang="ts">
import { ref } from 'vue'
import { 
  NSpace, NInput, NInputGroup, NButton, NDivider, NIcon, NText, 
  NPopconfirm, NScrollbar, NPopover
} from 'naive-ui'
import { 
  DragIndicatorOutlined as DragIcon,
  DeleteOutlined as DeleteIcon,
  AddOutlined as AddIcon,
  EditOutlined as EditIcon,
  CheckOutlined as SaveIcon,
  InsertEmoticonOutlined as EmojiIcon,
  ImageOutlined as ImageIcon
} from '@vicons/material'
import HDIconPicker from '../HDIconPicker.vue'

// 常用 Emoji 预设
const COMMON_EMOJIS = [
  '🏠', '🎬', '📺', '🎮', '📥', '🛠️', '⚙️', '📊', '🌐', '📁', 
  '🔍', '📚', '🎵', '📸', '🎨', '🛡️', '⚡', '☁️', '📱', '💻'
]

export interface Category {
  id: number
  name: string
  icon?: string
  order?: number
}

const props = defineProps<{
  categories: Category[]
}>()

const emit = defineEmits(['add', 'delete', 'reorder', 'update'])

const newCatName = ref('')
const newCatIcon = ref('')
const editingId = ref<number | null>(null)
const editingName = ref('')
const editingIcon = ref('')
const showIconPicker = ref(false)
const pickingFor = ref<'new' | 'edit'>('new')
const dragItem = ref<number | null>(null)
const dragOverItem = ref<number | null>(null)

const openPicker = (type: 'new' | 'edit') => {
  pickingFor.value = type
  showIconPicker.value = true
}

const handleIconSelect = (url: string) => {
  if (pickingFor.value === 'new') {
    newCatIcon.value = url
  } else {
    editingIcon.value = url
  }
}

const selectEmoji = (emoji: string, type: 'new' | 'edit') => {
  if (type === 'new') {
    newCatIcon.value = emoji
  } else {
    editingIcon.value = emoji
  }
}

const isEmoji = (str: string) => {
  if (!str) return false
  if (str.includes('/') || str.includes('.')) return false
  return /\p{Emoji}/u.test(str) && str.length <= 4
}

const handleAdd = () => {
  if (!newCatName.value) return
  emit('add', newCatName.value, newCatIcon.value)
  newCatName.value = ''
  newCatIcon.value = ''
}

const startEdit = (cat: Category) => {
  editingId.value = cat.id
  editingName.value = cat.name
  editingIcon.value = cat.icon || ''
}

const saveEdit = () => {
  if (editingId.value && editingName.value) {
    emit('update', editingId.value, editingName.value, editingIcon.value)
    editingId.value = null
  }
}

const onDragStart = (id: number) => { dragItem.value = id }
const onDragEnter = (id: number) => { if (id !== dragItem.value) dragOverItem.value = id }
const onDragEnd = () => {
  if (dragItem.value !== null && dragOverItem.value !== null) {
    const newCats = [...props.categories]
    const fromIndex = newCats.findIndex(c => c.id === dragItem.value)
    const toIndex = newCats.findIndex(c => c.id === dragOverItem.value)
    if (fromIndex !== -1 && toIndex !== -1) {
      const [removed] = newCats.splice(fromIndex, 1)
      newCats.splice(toIndex, 0, removed)
      emit('reorder', newCats.map(c => c.id))
    }
  }
  dragItem.value = dragOverItem.value = null
}
</script>

<template>
  <div class="tab-content">
    <n-space vertical size="large">
      <div class="add-section">
        <n-text depth="3" style="font-size: 12px; margin-bottom: 8px; display: block;">添加新分类</n-text>
        <n-input-group>
          <!-- Emoji 快速选择 -->
          <n-popover trigger="click" placement="bottom-start" style="padding: 12px">
            <template #trigger>
              <n-button secondary type="info">
                <template #icon><n-icon><EmojiIcon /></n-icon></template>
              </n-button>
            </template>
            <div class="emoji-picker-grid">
              <span v-for="e in COMMON_EMOJIS" :key="e" class="emoji-item" @click="selectEmoji(e, 'new')">{{ e }}</span>
              <n-button size="tiny" quaternary type="primary" @click="openPicker('new')" style="margin-top: 8px">
                图标库
              </n-button>
            </div>
          </n-popover>
          
          <n-input v-model:value="newCatIcon" placeholder="图标/Emoji" style="width: 120px" />
          <n-input v-model:value="newCatName" placeholder="新分类名称" @keyup.enter="handleAdd" />
          <n-button type="primary" @click="handleAdd">
            <template #icon><n-icon><AddIcon /></n-icon></template>
            添加
          </n-button>
        </n-input-group>
      </div>

      <n-divider title-placement="left" style="margin: 4px 0">已有分类 (可上下拖拽排序/点图标改名)</n-divider>
      
      <n-scrollbar style="max-height: 350px; padding-right: 12px;">
        <div class="category-list">
          <div 
            v-for="cat in categories" 
            :key="cat.id"
            class="category-item"
            :class="{ 'is-dragging': dragItem === cat.id, 'is-drag-over': dragOverItem === cat.id }"
            draggable="true"
            @dragstart="onDragStart(cat.id)"
            @dragover.prevent
            @dragenter="onDragEnter(cat.id)"
            @dragend="onDragEnd"
          >
            <div class="drag-handle"><n-icon><DragIcon /></n-icon></div>
            
            <div class="cat-content">
              <template v-if="editingId === cat.id">
                <n-input-group>
                  <n-popover trigger="click" placement="bottom-start" style="padding: 12px">
                    <template #trigger>
                      <n-button size="small" secondary type="info">
                        <template #icon><n-icon><EmojiIcon /></n-icon></template>
                      </n-button>
                    </template>
                    <div class="emoji-picker-grid">
                      <span v-for="e in COMMON_EMOJIS" :key="e" class="emoji-item" @click="selectEmoji(e, 'edit')">{{ e }}</span>
                      <n-button size="tiny" quaternary type="primary" @click="openPicker('edit')" style="margin-top: 8px">
                        图标库
                      </n-button>
                    </div>
                  </n-popover>
                  <n-input size="small" v-model:value="editingIcon" placeholder="图标" style="width: 100px" />
                  <n-input size="small" v-model:value="editingName" @keyup.enter="saveEdit" />
                  <n-button size="small" type="primary" @click="saveEdit">
                    <template #icon><n-icon><SaveIcon /></n-icon></template>
                  </n-button>
                </n-input-group>
              </template>
              <template v-else>
                <div class="cat-display">
                  <span v-if="cat.icon" class="cat-icon-preview">
                    <span v-if="isEmoji(cat.icon)">{{ cat.icon }}</span>
                    <img v-else :src="cat.icon" style="width: 16px; height: 16px; object-fit: contain" />
                  </span>
                  <span class="cat-name">{{ cat.name }}</span>
                </div>
                <n-button quaternary circle size="tiny" @click="startEdit(cat)" class="edit-btn">
                  <template #icon><n-icon><EditIcon /></n-icon></template>
                </n-button>
              </template>
            </div>

            <div class="cat-actions" v-if="editingId !== cat.id">
              <n-popconfirm @positive-click="emit('delete', cat.id)">
                <template #trigger>
                  <n-button quaternary circle size="small" type="error">
                    <template #icon><n-icon><DeleteIcon /></n-icon></template>
                  </n-button>
                </template>
                确定删除该分类吗？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-scrollbar>
    </n-space>

    <!-- 图标选择器弹窗 -->
    <HDIconPicker v-model:show="showIconPicker" @select="handleIconSelect" />
  </div>
</template>

<style scoped>
.tab-content { padding: 12px 4px; min-height: 300px; }
.category-list { display: flex; flex-direction: column; gap: 8px; }
.category-item {
  display: flex; align-items: center; padding: 10px 12px;
  background: var(--n-card-color); border: 1px solid var(--n-border-color);
  border-radius: 8px; transition: all 0.2s;
}
.category-item:hover { background: var(--n-hover-color); border-color: var(--primary-color); }
.drag-handle { cursor: grab; margin-right: 12px; color: var(--n-text-color-3); }
.cat-content { flex: 1; display: flex; align-items: center; gap: 8px; }
.cat-display { display: flex; align-items: center; gap: 8px; flex: 1; }
.cat-icon-preview { font-size: 16px; display: flex; align-items: center; }
.cat-name { font-weight: 500; }
.edit-btn { opacity: 0.6; transition: opacity 0.2s; }
.category-item:hover .edit-btn { opacity: 1; }
.edit-btn:hover { opacity: 1 !important; }
.is-dragging { opacity: 0.4; border-style: dashed; }
.is-drag-over { border: 2px solid var(--primary-color); transform: scale(1.01); }

.emoji-picker-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
  width: 200px; /* 稍微加宽一点，防止挤压 */
  padding: 4px;
}
.emoji-item {
  font-size: 19px; /* 微调字号 */
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px; /* 增大底框 */
  height: 34px;
  border-radius: 6px;
  transition: all 0.2s ease;
  background: var(--n-hover-color);
  overflow: hidden; /* 强制拦截溢出 */
  line-height: 1;
}
.emoji-item:hover {
  background: var(--n-color-primary-pressed);
  transform: scale(1.1);
  z-index: 1;
}
</style>