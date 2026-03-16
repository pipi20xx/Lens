<template>
  <div class="mobile-activity-heatmap">
    <div class="heatmap-container">
      <div class="heatmap-bars">
        <div 
          v-for="hour in 24" 
          :key="hour" 
          class="bar-item"
          @mouseenter="showTooltip = hour - 1"
          @mouseleave="showTooltip = null"
        >
          <div 
            class="bar" 
            :style="{ 
              height: getBarHeight(hour - 1) + '%',
              background: getBarColor(hour - 1)
            }"
          ></div>
          <div class="bar-label">{{ hour - 1 }}</div>
        </div>
      </div>
    </div>
    
    <div v-if="showTooltip !== null" class="tooltip">
      <div class="tooltip-time">{{ showTooltip }}:00 - {{ showTooltip }}:59</div>
      <div class="tooltip-count">{{ hourlyData[`Hour-${showTooltip}`] || 0 }} 次播放</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  hourlyData: Record<string, number>
}>()

const showTooltip = ref<number | null>(null)

const maxValue = computed(() => {
  let max = 0
  for (let i = 0; i < 24; i++) {
    const val = props.hourlyData[`Hour-${i}`] || 0
    if (val > max) max = val
  }
  return max
})

const getBarHeight = (hour: number) => {
  const value = props.hourlyData[`Hour-${hour}`] || 0
  if (maxValue.value === 0) return 0
  return (value / maxValue.value) * 100
}

const getBarColor = (hour: number) => {
  const value = props.hourlyData[`Hour-${hour}`] || 0
  if (value === 0) return 'rgba(255, 255, 255, 0.1)'
  
  const ratio = value / maxValue.value
  if (ratio > 0.7) return 'linear-gradient(to top, #18a058, #36ad6a)'
  if (ratio > 0.4) return 'linear-gradient(to top, #2080f0, #40a9ff)'
  if (ratio > 0.2) return 'linear-gradient(to top, #f0a020, #f5a623)'
  return 'linear-gradient(to top, #d03050, #de576d)'
}
</script>

<style scoped>
.mobile-activity-heatmap {
  position: relative;
  padding: 16px 0;
}

.heatmap-container {
  width: 100%;
  height: 180px;
}

.heatmap-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  height: 100%;
  padding: 0 4px;
}

.bar-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  margin: 0 2px;
  position: relative;
}

.bar {
  width: 100%;
  min-height: 4px;
  border-radius: 4px 4px 0 0;
  transition: all 0.3s ease;
  cursor: pointer;
}

.bar-item:hover .bar {
  filter: brightness(1.2);
  transform: scaleX(1.1);
}

.bar-label {
  margin-top: 8px;
  font-size: 10px;
  color: var(--text-color-3);
  text-align: center;
}

.tooltip {
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.9);
  color: white;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  z-index: 10;
  pointer-events: none;
  white-space: nowrap;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.tooltip-time {
  color: var(--text-color-3);
  margin-bottom: 4px;
}

.tooltip-count {
  font-weight: bold;
  color: var(--n-primary-color);
}
</style>
