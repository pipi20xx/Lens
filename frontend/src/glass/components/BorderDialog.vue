<script setup lang="ts">
/**
 * BorderDialog — 边框切换对话框
 *
 * 参考 ShadowDialog 的结构，提供 5 种边框预设。
 * 切换后立即生效并持久化，不受白天/夜晚模式影响。
 */
import { computed, ref, watch } from 'vue'
import { useThemeCustomizer, type ThemeCustomizerBorder } from '@/glass/host/useThemeCustomizer'
import { useDisplay } from 'vuetify'

const props = withDefaults(
  defineProps<{
    modelValue?: boolean
  }>(),
  {
    modelValue: true,
  },
)

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'update:modelValue', value: boolean): void
}>()

const display = useDisplay()
const { settings, setBorder } = useThemeCustomizer()

const currentBorder = computed(() => settings.value.border)

const visible = computed({
  get: () => props.modelValue,
  set: (value) => {
    emit('update:modelValue', value)
    if (!value) emit('close')
  },
})

interface BorderOption {
  value: ThemeCustomizerBorder
  label: string
  hint: string
  icon: string
  /** 预览方块的边框 CSS */
  previewBorder: string
}

const borderOptions: BorderOption[] = [
  {
    value: 'none',
    label: '无边框',
    hint: '所有组件无边框描边',
    icon: 'mdi-square-outline',
    previewBorder: 'none',
  },
  {
    value: 'subtle',
    label: '轻微',
    hint: '极淡描边，几乎不可见',
    icon: 'mdi-square-rounded-outline',
    previewBorder: '1px solid rgba(var(--v-theme-on-surface), 0.06)',
  },
  {
    value: 'default',
    label: '默认',
    hint: '保持各主题原生边框',
    icon: 'mdi-square-rounded',
    previewBorder: '1px solid rgba(var(--v-theme-on-surface), 0.12)',
  },
  {
    value: 'prominent',
    label: '明显',
    hint: '清晰的边框层次感',
    icon: 'mdi-square-rounded',
    previewBorder: '1px solid rgba(var(--v-theme-on-surface), 0.2)',
  },
  {
    value: 'dramatic',
    label: '强边框',
    hint: '粗线描边，高对比度',
    icon: 'mdi-cube-outline',
    previewBorder: '2px solid rgba(var(--v-theme-on-surface), 0.3)',
  },
]

/** 用于自定义滑块的映射（0=none, 1=subtle, 2=default, 3=prominent, 4=dramatic） */
const borderSliderValue = ref(2)

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      const idx = borderOptions.findIndex(o => o.value === currentBorder.value)
      borderSliderValue.value = idx >= 0 ? idx : 2
    }
  },
  { immediate: true },
)

function selectBorder(value: ThemeCustomizerBorder) {
  setBorder(value)
  const idx = borderOptions.findIndex(o => o.value === value)
  if (idx >= 0) borderSliderValue.value = idx
}

function onSliderChange(value: number) {
  const option = borderOptions[value]
  if (option) selectBorder(option.value)
}

const currentOption = computed(() => borderOptions.find(o => o.value === currentBorder.value) ?? borderOptions[2])
</script>

<template>
  <VDialog
    v-model="visible"
    width="100%"
    max-width="32rem"
    scrollable
    :fullscreen="display.smAndDown.value"
  >
    <VCard>
      <VCardTitle class="d-flex align-center pa-4">
        <VIcon icon="mdi-border-all-variant" class="me-2" />
        边框
        <VSpacer />
        <VBtn
          icon
          variant="text"
          size="small"
          aria-label="关闭"
          @click.stop="visible = false"
        >
          <VIcon icon="mdi-close" />
        </VBtn>
      </VCardTitle>
      <VDivider />

      <VCardText class="border-dialog__body">
        <!-- 预设选项 -->
        <section>
          <h3 class="border-dialog__label">边框强度</h3>
          <div class="border-dialog__grid">
            <button
              v-for="option in borderOptions"
              :key="option.value"
              type="button"
              class="border-dialog__option"
              :class="{ 'border-dialog__option--active': currentBorder === option.value }"
              @click="selectBorder(option.value)"
            >
              <div
                class="border-dialog__preview"
                :style="{ border: option.previewBorder }"
              >
                <VIcon :icon="option.icon" size="20" />
              </div>
              <span class="border-dialog__option-label">{{ option.label }}</span>
            </button>
          </div>
          <p class="border-dialog__hint">
            点击预设即可切换边框强度。边框设置不会因深色/浅色模式切换而改变。
          </p>
        </section>

        <!-- 滑块调整 -->
        <section>
          <div class="border-dialog__slider-header">
            <h3 class="border-dialog__label">快速调整</h3>
            <span class="border-dialog__current-value">{{ currentOption.label }}</span>
          </div>
          <div class="border-dialog__slider-wrapper">
            <VSlider
              v-model="borderSliderValue"
              :min="0"
              :max="4"
              :step="1"
              color="primary"
              show-ticks
              thumb-label
              @update:model-value="onSliderChange"
            >
              <template #thumb-label="{ modelValue }">
                {{ borderOptions[modelValue]?.label ?? '' }}
              </template>
            </VSlider>
          </div>
          <div class="border-dialog__tick-labels">
            <span
              v-for="option in borderOptions"
              :key="option.value"
              class="border-dialog__tick-label"
            >{{ option.label }}</span>
          </div>
        </section>

        <!-- 当前选中预览 -->
        <section class="border-dialog__current">
          <div
            class="border-dialog__current-preview"
            :style="{ border: currentOption.previewBorder }"
          />
          <div class="border-dialog__current-info">
            <span class="border-dialog__current-label">当前边框</span>
            <span class="border-dialog__current-text">{{ currentOption.label }}</span>
            <span class="border-dialog__current-hint">{{ currentOption.hint }}</span>
          </div>
        </section>
      </VCardText>

      <VDivider />
      <VCardActions class="border-dialog__actions justify-center">
        <VBtn
          :slim="false"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-check"
          @click="visible = false"
        >
          完成
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped lang="scss">
.border-dialog__body {
  display: grid;
  align-content: start;
  gap: 24px;
  grid-auto-rows: max-content;
  padding: 20px 24px 24px;
}

.border-dialog__actions {
  flex: none;
  padding: 16px 24px;
}

.border-dialog__label {
  margin: 0 0 10px;
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.4;
}

.border-dialog__hint {
  margin: 8px 0 0;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.75rem;
  line-height: 1.45;
}

.border-dialog__grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.border-dialog__option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px 4px;
  border: 2px solid transparent;
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.03);
  cursor: pointer;
  outline: none;
  transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;

  &:hover {
    background: rgba(var(--v-theme-on-surface), 0.06);
    transform: translateY(-2px);
  }

  &--active {
    border-color: rgb(var(--v-theme-primary));
    background: rgba(var(--v-theme-primary), 0.08);
  }
}

.border-dialog__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  block-size: 40px;
  inline-size: 40px;
  background: rgba(var(--v-theme-on-surface), 0.05);
  border-radius: 8px;
  transition: border 0.2s ease;
}

.border-dialog__option-label {
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  font-size: 0.75rem;
  font-weight: 500;
  text-align: center;
}

.border-dialog__slider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  .border-dialog__label {
    margin-block-end: 0;
  }
}

.border-dialog__current-value {
  color: rgb(var(--v-theme-primary));
  font-size: 0.8125rem;
  font-weight: 600;
}

.border-dialog__slider-wrapper {
  margin-block-start: 8px;
  padding-inline: 8px;
}

.border-dialog__tick-labels {
  display: flex;
  justify-content: space-between;
  margin-block-start: -4px;
  padding-inline: 8px;
}

.border-dialog__tick-label {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.625rem;
  text-align: center;
  flex: 1;

  &:first-child {
    text-align: left;
  }

  &:last-child {
    text-align: right;
  }
}

.border-dialog__current {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.035);
}

.border-dialog__current-preview {
  block-size: 48px;
  inline-size: 48px;
  background: rgba(var(--v-theme-primary), 0.1);
  border-radius: 10px;
  flex-shrink: 0;
  transition: border 0.2s ease;
}

.border-dialog__current-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.border-dialog__current-label {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.75rem;
}

.border-dialog__current-text {
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  font-size: 0.9rem;
  font-weight: 600;
}

.border-dialog__current-hint {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.6875rem;
}
</style>
