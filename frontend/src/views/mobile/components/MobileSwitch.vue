<template>
  <div 
    class="mobile-switch-custom"
    :class="{ active: modelValue }"
    @click="toggle"
  >
    <div class="switch-track">
      <div class="switch-thumb"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  modelValue: boolean
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const toggle = () => {
  emit('update:modelValue', !props.modelValue)
}
</script>

<style scoped>
.mobile-switch-custom {
  cursor: pointer;
  user-select: none;
  transition: all 0.3s ease;
}

.switch-track {
  width: 50px;
  height: 28px;
  background-color: #9ca3af;
  border-radius: 14px;
  position: relative;
  transition: background-color 0.3s ease;
}

.mobile-switch-custom.active .switch-track {
  background-color: var(--primary-color, #7c3aed);
}

.switch-thumb {
  width: 24px;
  height: 24px;
  background-color: #ffffff;
  border-radius: 50%;
  position: absolute;
  top: 2px;
  left: 2px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: transform 0.3s ease;
}

.mobile-switch-custom.active .switch-thumb {
  transform: translateX(22px);
}
</style>
