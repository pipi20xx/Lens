<script setup lang="ts">
import { 
  NModal, 
  NCard, 
  NSpace, 
  NButton,
  NIcon,
  NTag,
  NSwitch,
  NPopconfirm,
  NTooltip,
  NText,
  useMessage
} from 'naive-ui'
import {
  ArrowRightIcon,
  ArrowTopRightOnSquareIcon,
  Bars3Icon,
  MapPinIcon,
  TrashIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'
import draggable from 'vuedraggable'

import GroupCard from './menu-manager/GroupCard.vue'
import { useMenuEditor } from './menu-manager/useMenuEditor'
import { saveMenuLayoutToBackend, isHeaderSticky } from '../store/navigationStore'
import { watch, ref } from 'vue'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits(['update:show'])
const message = useMessage()
const isSaving = ref(false)

const {
  menuLayout,
  unallocatedItems,
  editingGroupIndex,
  addNewGroup,
  removeGroup,
  removeItemFromGroup,
  refreshUnallocated,
  addItemAsPrimary,
  resetToDefault
} = useMenuEditor()

// 监听布局变化，更新功能池
watch(menuLayout, () => {
  refreshUnallocated()
}, { deep: true })

const handleSaveAndClose = async () => {
  isSaving.value = true
  try {
    await saveMenuLayoutToBackend(menuLayout.value)
    message.success('菜单布局保存成功')
    emit('update:show', false)
  } catch (err) {
    message.error('保存布局失败，请检查网络连接')
  } finally {
    isSaving.value = false
  }
}

const handleClose = () => {
  emit('update:show', false)
}
</script>

<template>
  <n-modal :show="show" @update:show="handleClose" transform-origin="center">
    <n-card
      class="menu-manager-card"
      title="导航布局管理"
      bordered
      size="medium"
      content-style="padding: 0;"
    >
      <template #header-extra>
        <n-button quaternary circle size="small" @click="handleClose" title="关闭">
          <template #icon><n-icon><XMarkIcon /></n-icon></template>
        </n-button>
      </template>
      <div class="editor-container">
        <!-- 左侧：功能池 -->
        <div class="pool-container">
          <div class="section-header">
            <div class="section-title">未分配功能</div>
            <div class="section-desc">可直接拖拽或点击快速添加</div>
          </div>
          
          <div class="pool-scroll-wrapper native-scroll">
              <draggable
                v-model="unallocatedItems"
                :group="{ name: 'menu-items', pull: 'clone', put: false }"
                :sort="false"
                :clone="el => el.key"
                item-key="key"
                class="pool-list"
              >
                <template #item="{ element }">
                  <div class="pool-item">
                    <n-space align="center" justify="space-between" :wrap="false" style="width: 100%">
                      <n-space align="center" :size="8" :wrap="false" style="overflow: hidden; flex: 1;">
                        <n-icon class="drag-handle-icon" :size="18"><Bars3Icon /></n-icon>
                        <span class="pool-label">{{ element.label }}</span>
                      </n-space>
                      
                      <n-popconfirm 
                        @positive-click="addItemAsPrimary(element)"
                        positive-text="确认添加"
                        negative-text="取消"
                      >
                        <template #trigger>
                          <n-tooltip trigger="hover" placement="top">
                            <template #trigger>
                              <n-button 
                                quaternary 
                                circle 
                                size="tiny" 
                                type="primary" 
                                class="quick-add-btn"
                                @click.stop
                              >
                                <template #icon><n-icon><ArrowRightIcon /></n-icon></template>
                              </n-button>
                            </template>
                            快速设为一级菜单
                          </n-tooltip>
                        </template>
                        确定要将此功能直接添加为独立的一级菜单项吗？
                      </n-popconfirm>
                    </n-space>
                  </div>
                </template>
              </draggable>
              <div v-if="unallocatedItems.length === 0" class="pool-empty">
                所有功能已分配
              </div>
          </div>
        </div>

        <!-- 右侧：结构编辑器 -->
        <div class="structure-editor">
          <div class="editor-header">
            <div class="header-left">
              <div class="section-title">当前布局结构</div>
              <div class="section-desc">支持嵌套拖拽排序</div>
            </div>
            <n-space>
              <n-popconfirm 
                @positive-click="resetToDefault"
                positive-text="确认重置"
                negative-text="取消"
              >
                <template #trigger>
                  <n-button quaternary size="small" type="warning">
                    恢复默认布局
                  </n-button>
                </template>
                确定要放弃当前所有自定义改动，恢复到系统默认布局吗？
              </n-popconfirm>

              <n-button type="primary" secondary size="small" @click="addNewGroup">
                添加新分类容器
              </n-button>
            </n-space>
          </div>

          <div class="editor-scroll-wrapper native-scroll">
              <div class="editor-content-wrapper">
                <draggable
                  v-model="menuLayout"
                  :group="{ name: 'primary-groups', put: ['menu-items'] }"
                  item-key="key"
                  handle=".primary-drag-handle"
                  class="primary-list"
                  ghost-class="ghost-node"
                  animation="200"
                  @change="onPoolToPrimary"
                >
                  <template #item="{ element, index }">
                    <div class="primary-node-outer">
                      <GroupCard 
                        v-if="element.type === 'group'"
                        :group="element"
                        :gIdx="index"
                        :isEditing="editingGroupIndex === index"
                        @removeGroup="removeGroup"
                        @removeItem="removeItemFromGroup"
                        @startEdit="(idx) => editingGroupIndex = idx"
                        @stopEdit="editingGroupIndex = null"
                      />

                      <div 
                        v-else
                        class="primary-item-node"
                      >
                        <n-space align="center" justify="space-between" style="width: 100%">
                          <n-space align="center" :size="12">
                            <n-icon class="primary-drag-handle"><Bars3Icon /></n-icon>
                            <n-switch v-model:value="element.visible" size="small" />
                            <div class="item-content-styled">
                              <n-icon :size="18"><ArrowTopRightOnSquareIcon /></n-icon>
                              <span class="item-label-text">{{ element.label }}</span>
                            </div>
                          </n-space>
                          
                          <n-popconfirm 
                            @positive-click="removeGroup(index)"
                            positive-text="确认移出"
                            negative-text="取消"
                          >
                            <template #trigger>
                              <n-button quaternary circle size="small" type="error">
                                <template #icon><n-icon><TrashIcon /></n-icon></template>
                              </n-button>
                            </template>
                            确定要将此项从一级菜单中移出吗？
                          </n-popconfirm>
                        </n-space>
                      </div>
                    </div>
                  </template>
                </draggable>
                
                <div v-if="menuLayout.length === 0" class="empty-layout">
                  <div class="empty-text">布局为空</div>
                  <div class="empty-subtext">请从左侧拖入功能或添加新分类</div>
                </div>
              </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="modal-footer">
          <n-space justify="space-between" align="center" style="width: 100%;">
            <!-- 体验增强开关 -->
            <n-space align="center" :size="20">
              <div class="footer-setting-item">
                <n-icon :size="18" style="margin-right: 8px;"><MapPinIcon /></n-icon>
                <n-text style="margin-right: 8px;">导航栏吸顶显示</n-text>
                <n-switch v-model:value="isHeaderSticky" size="small" />
              </div>
            </n-space>

            <n-space align="center">
              <n-text depth="3" size="small" style="margin-right: 12px;" class="footer-hint-text">提示：更改会实时自动同步至云端配置</n-text>
              <n-button 
                type="primary" 
                size="large" 
                style="min-width: 200px;" 
                :loading="isSaving"
                @click="handleSaveAndClose"
              >
                完成并保存布局
              </n-button>
            </n-space>
          </n-space>
        </div>
      </template>
    </n-card>
  </n-modal>
</template>

<style scoped>
.menu-manager-card {
  width: 90vw;
  max-width: 1400px;
}

.editor-container {
  display: flex;
  background-color: transparent;
}

.pool-container {
  width: 320px;
  border-right: 1px solid var(--border-color);
  background-color: transparent;
  flex-shrink: 0;
}

.pool-scroll-wrapper, .editor-scroll-wrapper {
  /* 不限制高度，内容自然撑开，由浏览器页面滚动 */
}

.section-header {
  padding: 16px 24px;
  box-sizing: border-box;
  background-color: transparent;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.section-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--primary-color);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.section-desc {
  font-size: 11px;
  color: var(--text-color);
  opacity: 0.3;
  margin-top: 4px;
}

.pool-list {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pool-empty { 
  padding: 60px 20px; 
  text-align: center; 
  color: var(--text-color); 
  opacity: 0.15; 
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.pool-empty::before {
  content: '✓';
  font-size: 32px;
  font-weight: 200;
}

.pool-item {
  padding: 10px 16px;
  background-color: var(--hover-bg);
  border-radius: 10px;
  border: 1px solid var(--border-color);
  cursor: grab;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.pool-item:hover {
  background-color: rgba(var(--primary-color-rgb), 0.1);
  border-color: var(--primary-color);
  transform: translateX(4px);
}

.quick-add-btn { opacity: 0; transition: all 0.2s; }
.pool-item:hover .quick-add-btn { opacity: 1; }

.structure-editor {
  flex: 1;
}

.editor-header {
  padding: 16px 24px;
  box-sizing: border-box;
  background-color: transparent;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
}

.editor-content-wrapper {
  padding: 24px;
  box-sizing: border-box;
}

.primary-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 60px;
}

.primary-item-node {
  padding: 10px 16px !important;
  background-color: var(--hover-bg) !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 10px !important;
  transition: all 0.2s;
}
.primary-item-node:hover {
  border-color: var(--primary-color);
  background-color: rgba(var(--primary-color-rgb), 0.1);
}

.item-content-styled {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-color);
}

.item-label-text {
  font-size: 14px;
  font-weight: 500;
}
.primary-drag-handle { color: var(--text-color); opacity: 0.2; cursor: grab; font-size: 22px; }
.primary-drag-handle:hover { color: var(--primary-color); opacity: 1; }

/* ============================================
   移动端适配 (≤768px)
   - 左右分栏 → 纵向堆叠
   - hover 专属交互 → 常驻显示
   - footer → 纵向堆叠
   ============================================ */
@media (max-width: 768px) {
  /* 左右分栏改为纵向堆叠 */
  .editor-container {
    flex-direction: column !important;
  }

  /* 功能池全宽，纵向排列 */
  .pool-container {
    width: 100% !important;
    flex-shrink: 0;
    border-right: none !important;
    border-bottom: 1px solid var(--border-color);
  }

  /* 区块头部允许内容换行 */
  .section-header,
  .editor-header {
    padding: 12px 16px !important;
  }

  /* 编辑器头部按钮行换行 */
  .editor-header {
    flex-wrap: wrap;
    gap: 8px;
  }

  /* 列表内边距收紧 */
  .pool-list,
  .editor-content-wrapper {
    padding: 12px !important;
  }

  /* 快速添加按钮：移动端无 hover，常驻可见 */
  .quick-add-btn {
    opacity: 1 !important;
  }

  /* 禁用 hover 位移效果（触屏无意义且影响拖拽） */
  .pool-item:hover {
    transform: none;
  }

  /* footer 纵向堆叠 */
  .modal-footer :deep(.n-space),
  .modal-footer .n-space {
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 12px !important;
    width: 100% !important;
  }

  .footer-setting-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }

  /* 保存按钮全宽 */
  .modal-footer .n-button--primary-type {
    width: 100% !important;
    min-width: 0 !important;
  }

  /* 隐藏提示文字（移动端空间有限） */
  .modal-footer .footer-hint-text {
    display: none !important;
  }
}
</style>