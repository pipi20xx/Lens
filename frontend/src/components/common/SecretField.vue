<script setup lang="ts">
/**
 * 统一密钥/密码输入组件
 *
 * 特性：
 * - 密码可见性切换（眼睛图标）
 * - 可选复制按钮
 * - 支持 readonly / disabled / hint 等 v-text-field 全部属性
 */
import { ref } from 'vue'
import { useClipboard } from '@/composables'

const props = withDefaults(defineProps<{
  modelValue: string
  label?: string
  hint?: string
  persistentHint?: boolean
  readonly?: boolean
  disabled?: boolean
  density?: 'compact' | 'comfortable' | 'default'
  variant?: string
  class?: string
  showCopy?: boolean
  placeholder?: string
  prependInnerIcon?: string
  autocomplete?: string
}>(), {
  showCopy: true,
  density: 'compact',
  variant: 'outlined',
})

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const visible = ref(false)
const { copy: copyToClipboard } = useClipboard()

// ── Slot 透传 ──
const slots = defineSlots()
</script>

<template>
  <v-text-field
    :model-value="modelValue"
    @update:model-value="emit('update:modelValue', $event)"
    :label="label"
    :hint="hint"
    :persistent-hint="persistentHint"
    :readonly="readonly"
    :disabled="disabled"
    :density="density"
    :variant="variant"
    :class="props.class"
    :placeholder="placeholder"
    :prepend-inner-icon="prependInnerIcon"
    :autocomplete="autocomplete"
    :type="visible ? 'text' : 'password'"
  >
    <!-- 输入框内部末尾图标：可见性切换 + 复制 -->
    <template #append-inner>
      <v-icon
        :icon="visible ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
        @click="visible = !visible"
        class="cursor-pointer"
        size="20"
      />
      <v-tooltip v-if="showCopy" text="复制" location="top">
        <template #activator="{ props: tipProps }">
          <v-icon
            v-bind="tipProps"
            icon="mdi-content-copy"
            @click="copyToClipboard(modelValue)"
            class="cursor-pointer ml-1"
            size="20"
          />
        </template>
      </v-tooltip>
      <slot name="append-inner" />
    </template>
  </v-text-field>
</template>
