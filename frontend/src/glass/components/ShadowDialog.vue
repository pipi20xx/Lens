<script setup lang="ts">
/**
 * ShadowDialog — 阴影切换对话框
 *
 * 参考 BorderRadiusDialog 的结构，提供 5 种阴影预设。
 * 切换后立即生效并持久化，不受白天/夜晚模式影响。
 */
import { computed, ref, watch } from 'vue'
import { useThemeCustomizer, type ThemeCustomizerShadow } from '@/glass/host/useThemeCustomizer'
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
const { settings, setShadow } = useThemeCustomizer()

const currentShadow = computed(() => settings.value.shadow)

const visible = computed({
  get: () => props.modelValue,
  set: (value) => {
    emit('update:modelValue', value)
    if (!value) emit('close')
  },
})

interface ShadowOption {
  value: ThemeCustomizerShadow
  label: string
  hint: string
  icon: string
  /** 预览方块的阴影 CSS */
  previewShadow: string
}

const shadowOptions: ShadowOption[] = [
  {
    value: 'none',
    label: '无阴影',
    hint: '所有组件无投影',
    icon: 'mdi-square-outline',
    previewShadow: 'none',
  },
  {
    value: 'subtle',
    label: '轻微',
    hint: '极淡投影，几乎不可见',
    icon: 'mdi-square-rounded-outline',
    previewShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
  },
  {
    value: 'default',
    label: '默认',
    hint: '保持各主题原生阴影',
    icon: 'mdi-square-rounded',
    previewShadow: '0 2px 8px rgba(0, 0, 0, 0.12)',
  },
  {
    value: 'prominent',
    label: '明显',
    hint: '清晰的深度层次感',
    icon: 'mdi-square-rounded',
    previewShadow: '0 6px 18px rgba(0, 0, 0, 0.22)',
  },
  {
    value: 'dramatic',
    label: '夸张',
    hint: '强烈的悬浮投影效果',
    icon: 'mdi-cube-outline',
    previewShadow: '0 12px 32px rgba(0, 0, 0, 0.35)',
  },
]

/** 用于自定义滑块的映射（0=none, 1=subtle, 2=default, 3=prominent, 4=dramatic） */
const shadowSliderValue = ref(2)

watch(
  () => props.modelValue,
  (value) => {
    if (value) {
      const idx = shadowOptions.findIndex(o => o.value === currentShadow.value)
      shadowSliderValue.value = idx >= 0 ? idx : 2
    }
  },
  { immediate: true },
)

function selectShadow(value: ThemeCustomizerShadow) {
  setShadow(value)
  const idx = shadowOptions.findIndex(o => o.value === value)
  if (idx >= 0) shadowSliderValue.value = idx
}

function onSliderChange(value: number) {
  const option = shadowOptions[value]
  if (option) selectShadow(option.value)
}

const currentOption = computed(() => shadowOptions.find(o => o.value === currentShadow.value) ?? shadowOptions[2])
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
        <VIcon icon="mdi-box-shadow" class="me-2" />
        阴影
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

      <VCardText class="shadow-dialog__body">
        <!-- 预设选项 -->
        <section>
          <h3 class="shadow-dialog__label">阴影强度</h3>
          <div class="shadow-dialog__grid">
            <button
              v-for="option in shadowOptions"
              :key="option.value"
              type="button"
              class="shadow-dialog__option"
              :class="{ 'shadow-dialog__option--active': currentShadow === option.value }"
              @click="selectShadow(option.value)"
            >
              <div
                class="shadow-dialog__preview"
                :style="{ boxShadow: option.previewShadow }"
              >
                <VIcon :icon="option.icon" size="20" />
              </div>
              <span class="shadow-dialog__option-label">{{ option.label }}</span>
            </button>
          </div>
          <p class="shadow-dialog__hint">
            点击预设即可切换阴影强度。阴影设置不会因深色/浅色模式切换而改变。
          </p>
        </section>

        <!-- 滑块调整 -->
        <section>
          <div class="shadow-dialog__slider-header">
            <h3 class="shadow-dialog__label">快速调整</h3>
            <span class="shadow-dialog__current-value">{{ currentOption.label }}</span>
          </div>
          <div class="shadow-dialog__slider-wrapper">
            <VSlider
              v-model="shadowSliderValue"
              :min="0"
              :max="4"
              :step="1"
              color="primary"
              show-ticks
              thumb-label
              @update:model-value="onSliderChange"
            >
              <template #thumb-label="{ modelValue }">
                {{ shadowOptions[modelValue]?.label ?? '' }}
              </template>
            </VSlider>
          </div>
          <div class="shadow-dialog__tick-labels">
            <span
              v-for="option in shadowOptions"
              :key="option.value"
              class="shadow-dialog__tick-label"
            >{{ option.label }}</span>
          </div>
        </section>

        <!-- 当前选中预览 -->
        <section class="shadow-dialog__current">
          <div
            class="shadow-dialog__current-preview"
            :style="{ boxShadow: currentOption.previewShadow }"
          />
          <div class="shadow-dialog__current-info">
            <span class="shadow-dialog__current-label">当前阴影</span>
            <span class="shadow-dialog__current-text">{{ currentOption.label }}</span>
            <span class="shadow-dialog__current-hint">{{ currentOption.hint }}</span>
          </div>
        </section>
      </VCardText>

      <VDivider />
      <VCardActions class="shadow-dialog__actions justify-center">
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
.shadow-dialog__body {
  display: grid;
  align-content: start;
  gap: 24px;
  grid-auto-rows: max-content;
  padding: 20px 24px 24px;
}

.shadow-dialog__actions {
  flex: none;
  padding: 16px 24px;
}

.shadow-dialog__label {
  margin: 0 0 10px;
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.4;
}

.shadow-dialog__hint {
  margin: 8px 0 0;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.75rem;
  line-height: 1.45;
}

.shadow-dialog__grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
}

.shadow-dialog__option {
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

.shadow-dialog__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  block-size: 40px;
  inline-size: 40px;
  border: 1.5px solid rgba(var(--v-theme-on-surface), 0.2);
  background: rgba(var(--v-theme-on-surface), 0.05);
  border-radius: 8px;
  transition: box-shadow 0.2s ease;
}

.shadow-dialog__option-label {
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  font-size: 0.75rem;
  font-weight: 500;
  text-align: center;
}

.shadow-dialog__slider-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;

  .shadow-dialog__label {
    margin-block-end: 0;
  }
}

.shadow-dialog__current-value {
  color: rgb(var(--v-theme-primary));
  font-size: 0.8125rem;
  font-weight: 600;
}

.shadow-dialog__slider-wrapper {
  margin-block-start: 8px;
  padding-inline: 8px;
}

.shadow-dialog__tick-labels {
  display: flex;
  justify-content: space-between;
  margin-block-start: -4px;
  padding-inline: 8px;
}

.shadow-dialog__tick-label {
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

.shadow-dialog__current {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(var(--v-theme-on-surface), 0.08);
  border-radius: 12px;
  background: rgba(var(--v-theme-on-surface), 0.035);
}

.shadow-dialog__current-preview {
  block-size: 48px;
  inline-size: 48px;
  border: 2px solid rgba(var(--v-theme-on-surface), 0.15);
  background: rgba(var(--v-theme-primary), 0.1);
  border-radius: 10px;
  flex-shrink: 0;
  transition: box-shadow 0.2s ease;
}

.shadow-dialog__current-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.shadow-dialog__current-label {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.75rem;
}

.shadow-dialog__current-text {
  color: rgba(var(--v-theme-on-surface), var(--v-high-emphasis-opacity));
  font-size: 0.9rem;
  font-weight: 600;
}

.shadow-dialog__current-hint {
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
  font-size: 0.6875rem;
}
</style>
