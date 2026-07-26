<script setup lang="ts">
import { ref } from 'vue'
import type { SiteItem } from '../composables/useSiteNav'

const props = defineProps<{
  site: SiteItem
  styleMode?: string
  isDragging?: boolean
}>()

const emit = defineEmits<{
  click: []
  contextmenu: [e: MouseEvent]
  dragstart: []
  dragenter: []
  dragend: []
}>()

const cardRef = ref<HTMLElement | null>(null)
const mouseX = ref(0)
const mouseY = ref(0)

function handleMouseMove(e: MouseEvent) {
  if (!cardRef.value) return
  const rect = cardRef.value.getBoundingClientRect()
  mouseX.value = e.clientX - rect.left
  mouseY.value = e.clientY - rect.top
}

function isEmoji(str: string) {
  if (!str) return false
  if (str.includes('/') || str.includes('.')) return false
  return /\p{Emoji}/u.test(str) && str.length <= 4
}
</script>

<template>
  <div
    ref="cardRef"
    class="site-card"
    :class="[`style-${styleMode || 'glass'}`, { 'is-dragging': isDragging }]"
    :style="{ '--mouse-x': `${mouseX}px`, '--mouse-y': `${mouseY}px` }"
    draggable="true"
    @mousemove="handleMouseMove"
    @dragstart="emit('dragstart')"
    @dragover.prevent
    @dragenter="emit('dragenter')"
    @dragend="emit('dragend')"
    @click="emit('click')"
    @contextmenu="emit('contextmenu', $event)"
  >
    <!-- Spotlight 光效层 -->
    <div class="spotlight"></div>

    <div class="site-icon-wrapper">
      <span v-if="site.icon && isEmoji(site.icon)" class="emoji-icon">{{ site.icon }}</span>
      <img v-else-if="site.icon" :src="site.icon" class="image-icon" loading="lazy" />
      <v-icon v-else size="20" color="rgba(255,255,255,0.6)">mdi-link-variant</v-icon>
    </div>
    <div class="site-info">
      <div class="site-name">{{ site.title }}</div>
      <div v-if="site.description" class="site-desc">{{ site.description }}</div>
    </div>
  </div>
</template>

<style scoped>
.site-card {
  display: flex; align-items: center; padding: 10px 14px;
  height: 64px; width: 100%; max-width: 280px;
  border-radius: 12px; cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  box-sizing: border-box; overflow: hidden;
  position: relative; user-select: none;
}

/* Spotlight 效果 */
.spotlight {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: none; z-index: 0;
  background: radial-gradient(circle at var(--mouse-x) var(--mouse-y), rgba(255,255,255,0.15) 0%, transparent 80%);
  opacity: 0; transition: opacity 0.5s;
}
.site-card:hover .spotlight { opacity: 1; }

/* --- 1. 毛玻璃风格 (Glass) --- */
.site-card.style-glass {
  background: var(--nav-card-bg);
  backdrop-filter: blur(var(--nav-card-blur));
  -webkit-backdrop-filter: blur(var(--nav-card-blur));
  border: 1px solid var(--nav-card-border);
  box-shadow: 0 4px 12px -2px rgba(0,0,0,0.15);
}
.site-card.style-glass:hover {
  border-color: rgba(255,255,255,0.3);
  transform: translateY(-5px) scale(1.02);
  background: rgba(255,255,255,0.18);
  box-shadow: 0 12px 24px -10px rgba(0,0,0,0.4);
}

/* --- 2. 水玻璃风格 (Liquid) --- */
.site-card.style-liquid {
  background: rgba(128,128,128,0.05);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(128,128,128,0.2);
  border-top: 1.5px solid rgba(255,255,255,0.2);
  border-left: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 8px 32px -12px rgba(0,0,0,0.2);
}
.site-card.style-liquid:hover {
  background: rgba(128,128,128,0.1);
  transform: translateY(-8px) scale(1.04);
  box-shadow: 0 20px 40px -15px rgba(0,0,0,0.4), inset 0 0 20px rgba(128,128,128,0.1);
}

/* --- 3. 极简风格 (Pure) --- */
.site-card.style-pure {
  background: transparent;
  backdrop-filter: none;
  border: 1px solid rgba(128,128,128,0.15);
}
.site-card.style-pure:hover {
  background: rgba(128,128,128,0.08);
  border-color: rgba(128,128,128,0.3);
  transform: translateY(-4px);
}

/* 拖拽状态 */
.site-card.is-dragging { opacity: 0.1; transform: scale(0.9); }

/* 图标 */
.site-icon-wrapper {
  width: 44px; height: 44px; display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.1); margin-right: 14px; flex-shrink: 0;
  border-radius: 12px; overflow: hidden;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  box-shadow: 0 4px 10px rgba(0,0,0,0.2); z-index: 1;
  border: 1px solid rgba(255,255,255,0.1);
}
.site-card:hover .site-icon-wrapper {
  transform: scale(1.1) rotate(6deg);
  background: rgba(255,255,255,0.2);
  box-shadow: 0 8px 16px rgba(0,0,0,0.3);
}
.image-icon { width: 100%; height: 100%; object-fit: cover; }
.emoji-icon { font-size: 28px; line-height: 1; }

/* 文字 */
.site-info {
  flex: 1; min-width: 0; text-align: left;
  display: flex; flex-direction: column; justify-content: center;
  z-index: 1; position: relative;
}
.site-name {
  font-size: 14px; font-weight: 600; color: var(--nav-text-color);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  margin-bottom: 2px; transition: color 0.3s;
}
.site-card:hover .site-name { color: #fff; }
.site-desc {
  font-size: 11px; color: var(--nav-text-desc-color);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  opacity: 0.6; transition: all 0.3s;
}
.site-card:hover .site-desc { opacity: 1; }
</style>
