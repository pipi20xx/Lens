<script setup lang="ts">
/**
 * GlassDialog — Glass 模块专用的弹窗基础组件
 *
 * 封装了 Liquid Glass 风格的 v-dialog + v-card 结构，
 * 统一标题栏、分割线、内容区、操作栏的样式与行为。
 *
 * 布局：顶部标题栏固定 + 中间内容区滚动 + 底部操作栏固定
 * - scrollable=true（默认）：内容超出时由 v-card-text 独立滚动，
 *   标题栏和操作栏始终保持固定不动
 * - scrollable=false：弹窗不滚动，适合内含 textarea 等自带滚动的场景
 * - 标题栏提供关闭按钮（dismiss），底部提供取消按钮（cancel）
 * - 可通过 actions 插槽自定义额外按钮
 */
const props = withDefaults(defineProps<{
  modelValue: boolean
  maxWidth?: string | number
  title?: string
  icon?: string
  scrollable?: boolean
  cancelText?: string
  cancelVisible?: boolean
}>(), {
  maxWidth: 600,
  scrollable: true,
  cancelText: '取消',
  cancelVisible: true,
})

const emit = defineEmits<{
  'update:modelValue': [val: boolean]
  cancel: []
  dismiss: []
}>()

function handleCancel() {
  emit('cancel')
  emit('update:modelValue', false)
}

function handleDismiss() {
  emit('dismiss')
  emit('update:modelValue', false)
}
</script>

<template>
  <v-dialog
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :max-width="maxWidth"
    :scrollable="scrollable"
  >
    <v-card class="liquid-glass-card glass-dialog-card" :class="{ 'glass-dialog-card--scrollable': scrollable }" rounded="xl">
      <!-- 标题栏（固定） -->
      <v-card-title v-if="title || $slots.title" class="glass-dialog-header pa-4 d-flex align-center">
        <v-icon v-if="icon" start>{{ icon }}</v-icon>
        <slot name="title">{{ title }}</slot>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" size="small" @click="handleDismiss" />
      </v-card-title>

      <v-divider v-if="title || $slots.title" />

      <!-- 内容区（滚动） -->
      <v-card-text class="glass-dialog-body pa-4">
        <slot />
      </v-card-text>

      <!-- 操作栏（固定） -->
      <template v-if="$slots.actions || cancelVisible">
        <v-divider />
        <div class="glass-dialog-footer d-flex justify-end ga-2 pa-4">
          <v-btn
            v-if="cancelVisible"
            variant="tonal"
            color="grey"
            prepend-icon="mdi-close"
            @click="handleCancel"
          >
            {{ cancelText }}
          </v-btn>
          <slot name="actions" />
        </div>
      </template>
    </v-card>
  </v-dialog>
</template>

<style scoped>
/* 确保弹窗卡片使用 flex column 布局，
   顶部标题栏和底部操作栏固定，中间内容区滚动 */
.glass-dialog-card {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 48px);
  overflow: hidden;
}

/* 标题栏 — 不收缩、不滚动 */
.glass-dialog-header {
  flex-shrink: 0;
}

/* 内容区 — 填充剩余空间
   scrollable 模式下独立滚动，非 scrollable 模式下不滚动（由 textarea 等自带滚动） */
.glass-dialog-body {
  flex: 1 1 auto;
  min-height: 0;
}
.glass-dialog-card--scrollable .glass-dialog-body {
  overflow-y: auto;
}

/* 操作栏 — 不收缩、不滚动 */
.glass-dialog-footer {
  flex-shrink: 0;
}
</style>
