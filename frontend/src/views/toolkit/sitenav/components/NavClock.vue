<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

const props = defineProps<{
  textColor?: string
  alignment?: string
}>()

const currentTime = ref(new Date())
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  currentTime.value = new Date()
  timer = setInterval(() => { currentTime.value = new Date() }, 1000)
})
onUnmounted(() => { if (timer) clearInterval(timer) })

const timeStr = computed(() => {
  const h = String(currentTime.value.getHours()).padStart(2, '0')
  const m = String(currentTime.value.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
})

const secondsStr = computed(() => String(currentTime.value.getSeconds()).padStart(2, '0'))

const dateStr = computed(() => {
  return currentTime.value.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', weekday: 'short' })
})

const alignClass = computed(() => {
  if (props.alignment === 'center') return 'align-center'
  if (props.alignment === 'right') return 'align-right'
  return 'align-left'
})
</script>

<template>
  <div class="nav-clock" :class="alignClass">
    <div class="time-wrapper" :style="{ color: textColor || 'var(--nav-clock-text-color, #fff)' }">
      <span class="main-time">{{ timeStr }}</span>
      <span class="seconds">{{ secondsStr }}</span>
    </div>
    <div class="date-wrapper" :style="{ color: textColor || 'var(--nav-clock-text-color, #fff)' }">
      {{ dateStr }}
    </div>
  </div>
</template>

<style scoped>
.nav-clock {
  display: flex;
  flex-direction: column;
  margin-bottom: 8px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  user-select: none;
}
.nav-clock.align-center { align-items: center; }
.nav-clock.align-right { align-items: flex-end; }
.nav-clock.align-left { align-items: flex-start; }

.time-wrapper {
  display: flex;
  align-items: baseline;
  line-height: 1;
}
.main-time {
  font-size: 48px;
  font-weight: 700;
  letter-spacing: -2px;
  text-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
.seconds {
  font-size: 20px;
  margin-left: 6px;
  font-weight: 400;
  opacity: 0.8;
}
.date-wrapper {
  font-size: 14px;
  margin-top: 4px;
  font-weight: 500;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
  opacity: 0.8;
}

@media (max-width: 600px) {
  .main-time { font-size: 36px; }
  .seconds { font-size: 16px; }
}
</style>
