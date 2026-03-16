<template>
  <div class="mobile-tabs">
    <div class="tabs-header">
      <div 
        v-for="tab in tabs" 
        :key="tab.name"
        class="tab-item"
        :class="{ active: activeTab === tab.name }"
        @click="handleTabClick(tab.name)"
      >
        {{ tab.label }}
      </div>
    </div>
    <div class="tabs-content">
      <slot :name="activeTab"></slot>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Tab {
  name: string
  label: string
}

interface Props {
  tabs: Tab[]
  modelValue: string
}

interface Emits {
  (e: 'update:modelValue', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const activeTab = computed(() => props.modelValue)

const handleTabClick = (name: string) => {
  emit('update:modelValue', name)
}
</script>

<style scoped>
.mobile-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.tabs-header {
  display: flex;
  gap: 8px;
  padding: 8px;
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  border-bottom: 1px solid var(--border-color);
}

.tabs-header::-webkit-scrollbar {
  display: none;
}

.tab-item {
  flex-shrink: 0;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  background: var(--app-bg-color);
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.tab-item.active {
  background: var(--primary-color, #7c3aed);
  color: white;
}

.tabs-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}
</style>
