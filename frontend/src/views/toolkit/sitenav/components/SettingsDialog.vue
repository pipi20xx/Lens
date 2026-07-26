<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Category } from '../composables/useSiteNav'
import GlassDialog from '@/components/common/GlassDialog.vue'

const props = defineProps<{
  modelValue: boolean
  settings: Record<string, any>
  categories: Category[]
  wallpaperLoading: boolean
  baseRandomApiUrl: string
}>()

const emit = defineEmits<{
  'update:modelValue': [val: boolean]
  'update:settings': [patch: Record<string, any>]
  'reset-settings': []
  'upload-bg': [file: File]
  'refresh-wallpaper': []
  'save-wallpaper': []
  'add-category': [name: string, icon: string]
  'delete-category': [id: number]
  'reorder-categories': [ids: number[]]
  'update-category': [id: number, name: string, icon: string]
  'export': []
  'import': [file: File]
}>()

const activeTab = ref('appearance')
const bgInput = ref<HTMLInputElement | null>(null)
const importInput = ref<HTMLInputElement | null>(null)

// 本地设置副本，实时同步
const local = ref<Record<string, any>>({})
watch(() => props.settings, (val) => { local.value = { ...val } }, { immediate: true, deep: true })

function update(key: string, val: any) {
  local.value[key] = val
  emit('update:settings', { [key]: val })
}

function onBgUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) emit('upload-bg', file)
  ;(e.target as HTMLInputElement).value = ''
}

function onImportFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) emit('import', file)
  ;(e.target as HTMLInputElement).value = ''
}

// === 分类管理 ===
const newCatName = ref('')
const newCatIcon = ref('')
const editingCatId = ref<number | null>(null)
const editingCatName = ref('')
const editingCatIcon = ref('')
const dragCatId = ref<number | null>(null)
const dragOverCatId = ref<number | null>(null)

function handleAddCategory() {
  if (!newCatName.value) return
  emit('add-category', newCatName.value, newCatIcon.value)
  newCatName.value = ''
  newCatIcon.value = ''
}

function startEditCat(cat: Category) {
  editingCatId.value = cat.id
  editingCatName.value = cat.name
  editingCatIcon.value = cat.icon || ''
}

function saveEditCat() {
  if (editingCatId.value !== null && editingCatName.value) {
    emit('update-category', editingCatId.value, editingCatName.value, editingCatIcon.value)
    editingCatId.value = null
  }
}

function onCatDragStart(id: number) { dragCatId.value = id }
function onCatDragEnter(id: number) {
  if (id !== dragCatId.value) dragOverCatId.value = id
}
function onCatDragEnd() {
  if (dragCatId.value !== null && dragOverCatId.value !== null) {
    const newCats = [...props.categories]
    const fromIndex = newCats.findIndex(c => c.id === dragCatId.value)
    const toIndex = newCats.findIndex(c => c.id === dragOverCatId.value)
    if (fromIndex !== -1 && toIndex !== -1) {
      const [removed] = newCats.splice(fromIndex, 1)
      newCats.splice(toIndex, 0, removed)
      emit('reorder-categories', newCats.map(c => c.id))
    }
  }
  dragCatId.value = dragOverCatId.value = null
}

function isEmoji(str: string) {
  if (!str) return false
  if (str.includes('/') || str.includes('.')) return false
  return /\p{Emoji}/u.test(str) && str.length <= 4
}

const sizeOptions = [
  { title: '全部填充 (Cover)', value: 'cover' },
  { title: '完整显示 (Contain)', value: 'contain' },
  { title: '强制拉伸 (Stretch)', value: '100% 100%' },
]
</script>

<template>
  <GlassDialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :max-width="600"
    icon="mdi-cog-outline"
    title="高级设置 - 站点导航"
    cancel-text="关闭"
  >
    <v-tabs v-model="activeTab" density="compact" color="primary">
      <v-tab value="appearance">
        <v-icon size="16" class="mr-1">mdi-palette-outline</v-icon>外观设置
      </v-tab>
      <v-tab value="categories">
        <v-icon size="16" class="mr-1">mdi-view-grid-outline</v-icon>分类管理
      </v-tab>
      <v-tab value="data">
        <v-icon size="16" class="mr-1">mdi-database-outline</v-icon>数据管理
      </v-tab>
    </v-tabs>
    <v-divider class="mb-2" />

    <!-- ===== 外观设置 ===== -->
    <div v-show="activeTab === 'appearance'">
      <!-- 背景资源 -->
      <div class="settings-section-title">背景资源</div>
          <v-radio-group
            :model-value="local.wallpaper_mode"
            @update:model-value="update('wallpaper_mode', $event)"
            inline density="compact" class="mb-3"
          >
            <v-radio value="custom" label="自定义上传" />
            <v-radio value="bing" label="必应每日壁纸" />
            <v-radio value="unsplash" label="Unsplash 随机" />
          </v-radio-group>

          <!-- 自定义上传 -->
          <template v-if="local.wallpaper_mode === 'custom'">
            <div class="d-flex align-center ga-2 mb-3">
              <v-text-field
                :model-value="local.background_url"
                @update:model-value="update('background_url', $event)"
                label="背景图 URL" variant="outlined" density="compact" hide-details
              />
              <v-btn variant="tonal" size="small" prepend-icon="mdi-upload" @click="bgInput?.click()">上传</v-btn>
              <v-btn v-if="local.background_url" variant="tonal" size="small" color="error" @click="update('background_url', '')">移除</v-btn>
              <input ref="bgInput" type="file" accept="image/*" style="display:none" @change="onBgUpload" />
            </div>
          </template>

          <!-- Unsplash 随机 -->
          <template v-if="local.wallpaper_mode === 'unsplash'">
            <div class="text-caption text-medium-emphasis mb-2">从高质量随机库获取摄影或动漫作品</div>
            <v-select
              :model-value="local.wallpaper_type"
              @update:model-value="update('wallpaper_type', $event)"
              :items="[{ title: '二次元 / 动漫', value: 'anime' }, { title: '自然风景', value: 'scenery' }, { title: '极简 / 抽象', value: 'minimalist' }, { title: '纯随机 (摄影)', value: 'random' }]"
              label="壁纸风格" variant="outlined" density="compact" class="mb-3"
            />
            <v-select
              :model-value="local.wallpaper_resolution"
              @update:model-value="update('wallpaper_resolution', $event)"
              :items="[{ title: '1080P Full HD', value: '1920x1080' }, { title: '2K Quad HD', value: '2560x1440' }, { title: '4K Ultra HD', value: '3840x2160' }]"
              label="壁纸分辨率" variant="outlined" density="compact" class="mb-3"
            />
            <div class="d-flex ga-2 mb-3">
              <v-btn variant="tonal" color="primary" :loading="wallpaperLoading" @click="emit('refresh-wallpaper')">换一张</v-btn>
              <v-btn variant="tonal" color="info" @click="emit('save-wallpaper')">设为固定背景</v-btn>
            </div>
          </template>

          <!-- 必应壁纸 -->
          <template v-if="local.wallpaper_mode === 'bing'">
            <div class="text-caption text-medium-emphasis mb-2">已启用必应每日壁纸。可自定义地区和历史日期。</div>
            <v-btn variant="tonal" color="info" size="small" class="mb-3" @click="emit('save-wallpaper')">固化当前必应壁纸</v-btn>
            <v-select
              :model-value="local.bing_mkt"
              @update:model-value="update('bing_mkt', $event)"
              :items="[{ title: '中国 (zh-CN)', value: 'zh-CN' }, { title: '美国 (en-US)', value: 'en-US' }, { title: '日本 (ja-JP)', value: 'ja-JP' }, { title: '德国 (de-DE)', value: 'de-DE' }, { title: '英国 (en-GB)', value: 'en-GB' }]"
              label="壁纸地区 (Market)" variant="outlined" density="compact" class="mb-3"
            />
            <div class="mb-2 text-caption">{{ local.bing_index === 0 ? '今天' : local.bing_index + ' 天前' }}</div>
            <v-slider
              :model-value="local.bing_index"
              @update:model-value="update('bing_index', $event)"
              :min="0" :max="7" :step="1" thumb-label class="mb-3"
            />
            <v-radio-group
              :model-value="local.bing_resolution"
              @update:model-value="update('bing_resolution', $event)"
              inline density="compact" class="mb-3"
            >
              <v-radio value="1920x1080" label="1080P" />
              <v-radio value="UHD" label="4K UHD" />
            </v-radio-group>
            <v-switch
              :model-value="local.show_wallpaper_info"
              @update:model-value="update('show_wallpaper_info', $event)"
              label="显示壁纸故事信息" color="primary" hide-details density="compact" class="mb-3"
            />
          </template>

          <v-divider class="mb-4" />

          <!-- 背景样式 -->
          <div class="settings-section-title">背景样式</div>
          <v-switch
            :model-value="local.enable_background_color"
            @update:model-value="update('enable_background_color', $event)"
            label="启用背景底色" color="primary" hide-details density="compact" class="mb-3"
          />
          <template v-if="local.enable_background_color">
            <v-text-field
              :model-value="local.background_color"
              @update:model-value="update('background_color', $event)"
              label="背景底色" variant="outlined" density="compact" type="color" class="mb-3"
            />
          </template>

          <template v-if="local.background_url || local.wallpaper_mode !== 'custom'">
            <v-switch
              :model-value="local.enable_hd_mode"
              @update:model-value="update('enable_hd_mode', $event)"
              label="高清背景模式" color="primary" hide-details density="compact" class="mb-3"
            />
            <template v-if="!local.enable_hd_mode">
              <v-select
                :model-value="local.background_size"
                @update:model-value="update('background_size', $event)"
                :items="sizeOptions"
                label="填充模式" variant="outlined" density="compact" class="mb-3"
              />
              <div class="mb-1 text-caption">背景透明度: {{ Math.round((local.background_opacity || 0) * 100) }}%</div>
              <v-slider :model-value="local.background_opacity" @update:model-value="update('background_opacity', $event)"
                :min="0" :max="1" :step="0.01" thumb-label class="mb-3" />
              <div class="mb-1 text-caption">背景模糊度: {{ local.background_blur || 0 }}px</div>
              <v-slider :model-value="local.background_blur" @update:model-value="update('background_blur', $event)"
                :min="0" :max="20" :step="1" thumb-label class="mb-3" />
            </template>
          </template>

          <v-divider class="mb-4" />

          <!-- 内容组件 -->
          <div class="settings-section-title">内容组件</div>
          <v-switch
            :model-value="local.show_clock"
            @update:model-value="update('show_clock', $event)"
            label="显示数字时钟" color="primary" hide-details density="compact" class="mb-3"
          />
          <v-text-field v-if="local.show_clock"
            :model-value="local.clock_text_color"
            @update:model-value="update('clock_text_color', $event)"
            label="时钟文字颜色" variant="outlined" density="compact" type="color" class="mb-3"
          />
          <v-switch
            :model-value="local.show_hitokoto"
            @update:model-value="update('show_hitokoto', $event)"
            label="显示「每日一言」" color="primary" hide-details density="compact" class="mb-3"
          />
          <template v-if="local.show_hitokoto">
            <v-text-field
              :model-value="local.hitokoto_background"
              @update:model-value="update('hitokoto_background', $event)"
              label="一言背景色" variant="outlined" density="compact" class="mb-3"
            />
            <v-text-field
              :model-value="local.hitokoto_text_color"
              @update:model-value="update('hitokoto_text_color', $event)"
              label="一言文字颜色" variant="outlined" density="compact" type="color" class="mb-3"
            />
            <v-text-field
              :model-value="local.hitokoto_from_color"
              @update:model-value="update('hitokoto_from_color', $event)"
              label="一言来源颜色" variant="outlined" density="compact" class="mb-3"
            />
          </template>
          <v-text-field
            :model-value="local.page_title"
            @update:model-value="update('page_title', $event)"
            label="主标题" variant="outlined" density="compact" placeholder="站点导航" class="mb-3"
          />
          <v-text-field
            :model-value="local.header_text_color"
            @update:model-value="update('header_text_color', $event)"
            label="主标题颜色" variant="outlined" density="compact" type="color" class="mb-3"
          />
          <v-textarea
            :model-value="local.page_subtitle"
            @update:model-value="update('page_subtitle', $event)"
            label="副标题 (提示文字)" variant="outlined" density="compact"
            :rows="2" auto-grow class="mb-3"
          />
          <v-text-field
            :model-value="local.header_subtitle_color"
            @update:model-value="update('header_subtitle_color', $event)"
            label="副标题颜色" variant="outlined" density="compact" class="mb-3"
          />

          <v-divider class="mb-4" />

          <!-- 布局调整 -->
          <div class="settings-section-title">布局调整</div>
          <div class="mb-1 text-caption">主标题对齐方式</div>
          <v-radio-group :model-value="local.header_alignment" @update:model-value="update('header_alignment', $event)"
            inline density="compact" class="mb-3">
            <v-radio value="left" label="左对齐" />
            <v-radio value="center" label="居中" />
            <v-radio value="right" label="右对齐" />
          </v-radio-group>
          <div class="mb-1 text-caption">分类标题对齐方式</div>
          <v-radio-group :model-value="local.category_alignment" @update:model-value="update('category_alignment', $event)"
            inline density="compact" class="mb-3">
            <v-radio value="left" label="左对齐" />
            <v-radio value="center" label="居中" />
            <v-radio value="right" label="右对齐" />
          </v-radio-group>
          <v-switch :model-value="local.show_category_line" @update:model-value="update('show_category_line', $event)"
            label="显示分类装饰线" color="primary" hide-details density="compact" class="mb-3" />
          <div class="mb-1 text-caption">页面内容宽度: {{ local.content_max_width }}%</div>
          <v-slider :model-value="local.content_max_width" @update:model-value="update('content_max_width', $event)"
            :min="30" :max="100" :step="1" thumb-label class="mb-3" />
          <div class="mb-1 text-caption">标题顶部边距 (MT): {{ local.header_margin_top }}px</div>
          <v-slider :model-value="local.header_margin_top" @update:model-value="update('header_margin_top', $event)"
            :min="0" :max="200" :step="1" thumb-label class="mb-3" />
          <div class="mb-1 text-caption">标题行间距: {{ local.header_item_spacing }}px</div>
          <v-slider :model-value="local.header_item_spacing" @update:model-value="update('header_item_spacing', $event)"
            :min="0" :max="50" :step="1" thumb-label class="mb-3" />
          <div class="mb-1 text-caption">标题底部边距 (MB): {{ local.header_margin_bottom }}px</div>
          <v-slider :model-value="local.header_margin_bottom" @update:model-value="update('header_margin_bottom', $event)"
            :min="0" :max="100" :step="1" thumb-label class="mb-3" />

          <v-divider class="mb-4" />

          <!-- 卡片风格 -->
          <div class="settings-section-title">卡片风格</div>
          <v-radio-group :model-value="local.card_style" @update:model-value="update('card_style', $event)"
            inline density="compact" class="mb-3">
            <v-radio value="glass" label="毛玻璃" />
            <v-radio value="liquid" label="水玻璃" />
            <v-radio value="pure" label="极简" />
          </v-radio-group>

          <v-divider class="mb-4" />

          <!-- 卡片高级样式 -->
          <div class="settings-section-title">卡片高级样式</div>
          <v-text-field :model-value="local.card_background" @update:model-value="update('card_background', $event)"
            label="卡片背景色" variant="outlined" density="compact" class="mb-3" />
          <v-text-field :model-value="local.card_border_color" @update:model-value="update('card_border_color', $event)"
            label="卡片边框色" variant="outlined" density="compact" class="mb-3" />
          <div class="mb-1 text-caption">卡片模糊度: {{ local.card_blur }}px</div>
          <v-slider :model-value="local.card_blur" @update:model-value="update('card_blur', $event)"
            :min="0" :max="30" :step="1" thumb-label class="mb-3" />
          <v-text-field :model-value="local.text_color" @update:model-value="update('text_color', $event)"
            label="标题文字色" variant="outlined" density="compact" type="color" class="mb-3" />
          <v-text-field :model-value="local.text_description_color" @update:model-value="update('text_description_color', $event)"
            label="描述文字色" variant="outlined" density="compact" class="mb-3" />
          <v-text-field :model-value="local.category_title_color" @update:model-value="update('category_title_color', $event)"
            label="分类标题色" variant="outlined" density="compact" type="color" class="mb-3" />

          <v-btn block variant="text" color="warning" class="mt-2" @click="emit('reset-settings')">
            恢复默认样式
          </v-btn>
        </div>

      <!-- 分类管理 ===== -->
      <div v-show="activeTab === 'categories'">
          <div class="settings-section-title mb-3">添加新分类</div>
          <div class="d-flex ga-2 mb-4">
            <v-text-field v-model="newCatIcon" placeholder="图标/Emoji" variant="outlined" density="compact"
              style="max-width:120px" hide-details />
            <v-text-field v-model="newCatName" placeholder="新分类名称" variant="outlined" density="compact"
              hide-details @keyup.enter="handleAddCategory" />
            <v-btn color="primary" variant="flat" @click="handleAddCategory">添加</v-btn>
          </div>

          <v-divider class="mb-4" />
          <div class="text-caption text-medium-emphasis mb-3">已有分类（可拖拽排序 / 点图标编辑）</div>

          <div class="category-list">
            <div
              v-for="cat in categories"
              :key="cat.id"
              class="category-item"
              :class="{ 'is-dragging': dragCatId === cat.id, 'is-drag-over': dragOverCatId === cat.id }"
              draggable="true"
              @dragstart="onCatDragStart(cat.id)"
              @dragover.prevent
              @dragenter="onCatDragEnter(cat.id)"
              @dragend="onCatDragEnd"
            >
              <v-icon size="16" class="drag-handle">mdi-drag</v-icon>

              <div class="cat-content">
                <template v-if="editingCatId === cat.id">
                  <div class="d-flex ga-1 align-center">
                    <v-text-field v-model="editingCatIcon" placeholder="图标" variant="outlined" density="compact"
                      hide-details style="max-width:80px" />
                    <v-text-field v-model="editingCatName" placeholder="名称" variant="outlined" density="compact"
                      hide-details @keyup.enter="saveEditCat" />
                    <v-btn size="small" color="primary" variant="flat" @click="saveEditCat">保存</v-btn>
                  </div>
                </template>
                <template v-else>
                  <div class="cat-display">
                    <span v-if="cat.icon && isEmoji(cat.icon)" class="cat-icon-emoji">{{ cat.icon }}</span>
                    <img v-else-if="cat.icon" :src="cat.icon" class="cat-icon-img" />
                    <span class="cat-name">{{ cat.name }}</span>
                  </div>
                  <v-btn icon variant="text" size="x-small" @click="startEditCat(cat)">
                    <v-icon size="14">mdi-pencil</v-icon>
                  </v-btn>
                </template>
              </div>

              <v-btn v-if="editingCatId !== cat.id" icon variant="text" size="x-small" color="error"
                @click="emit('delete-category', cat.id)">
                <v-icon size="14">mdi-delete</v-icon>
              </v-btn>
            </div>
          </div>
        </div>

      <!-- 数据管理 ===== -->
      <div v-show="activeTab === 'data'">
          <div class="text-caption text-medium-emphasis mb-4">配置备份与恢复（包含分类、站点及本地图标文件）</div>

          <v-card variant="outlined" class="mb-4" rounded="lg">
            <v-card-title class="text-subtitle-2 pa-3">导出配置</v-card-title>
            <v-card-text class="pa-3 pt-0">
              <div class="text-body-2 text-medium-emphasis mb-3">将当前所有导航数据导出为 .zip 压缩包，方便迁移到其他服务器。</div>
              <v-btn variant="tonal" prepend-icon="mdi-download" @click="emit('export')">生成并下载全量备份</v-btn>
            </v-card-text>
          </v-card>

          <v-card variant="outlined" rounded="lg">
            <v-card-title class="text-subtitle-2 pa-3">导入配置</v-card-title>
            <v-card-text class="pa-3 pt-0">
              <div class="text-body-2 text-warning mb-3">注意：导入备份将覆盖当前所有导航设置，请谨慎操作。</div>
              <v-btn variant="tonal" color="info" prepend-icon="mdi-upload" @click="importInput?.click()">
                上传备份文件恢复
              </v-btn>
              <input ref="importInput" type="file" accept=".zip" style="display:none" @change="onImportFile" />
            </v-card-text>
          </v-card>
        </div>
  </GlassDialog>
</template>

<style scoped>
.settings-section-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 12px;
  color: rgba(var(--v-theme-on-surface), 0.9);
}
.category-list { display: flex; flex-direction: column; gap: 8px; }
.category-item {
  display: flex; align-items: center; padding: 10px 12px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px; transition: all 0.2s; gap: 8px;
}
.category-item:hover { background: rgba(var(--v-theme-on-surface), 0.05); }
.drag-handle { cursor: grab; opacity: 0.5; }
.cat-content { flex: 1; display: flex; align-items: center; gap: 8px; }
.cat-display { display: flex; align-items: center; gap: 8px; flex: 1; }
.cat-icon-emoji { font-size: 18px; }
.cat-icon-img { width: 16px; height: 16px; object-fit: contain; }
.cat-name { font-weight: 500; font-size: 14px; }
.is-dragging { opacity: 0.4; border-style: dashed; }
.is-drag-over { border: 2px solid rgb(var(--v-theme-primary)); transform: scale(1.01); }
</style>
