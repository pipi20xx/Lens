<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { useSystemStore } from '@/stores'

const systemStore = useSystemStore()
const logContainer = ref<HTMLElement>()

const levelColors: Record<string, string> = {
  INFO: '#4ecdc4',
  WARNING: '#FFB74D',
  ERROR: '#EF5350',
  CRITICAL: '#F48FB1',
  DEBUG: 'rgba(255,255,255,0.4)',
  SUCCESS: '#81C784',
}

const filterOptions = [
  { title: '全部', value: 'all' },
  { title: 'INFO', value: 'INFO' },
  { title: 'WARNING', value: 'WARNING' },
  { title: 'ERROR', value: 'ERROR' },
]

const autoScroll = ref(true)

watch(() => systemStore.filteredLogs.length, async () => {
  if (autoScroll.value) {
    await nextTick()
    logContainer.value?.scrollTo({ top: logContainer.value.scrollHeight })
  }
})

function clearLogs() {
  systemStore.clearLogs()
}
</script>

<template>
  <v-dialog v-model="systemStore.showLogModal" max-width="900" scrollable>
    <v-card rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start>mdi-card-text-outline</v-icon>
        系统日志
        <v-spacer />
        <v-btn-toggle v-model="systemStore.logFilter" density="compact" variant="tonal" rounded="lg" class="mr-2">
          <v-btn v-for="opt in filterOptions" :key="opt.value" :value="opt.value" size="small">
            {{ opt.title }}
          </v-btn>
        </v-btn-toggle>
        <v-btn variant="text" size="small" icon="mdi-delete-outline" @click="clearLogs" />
        <v-btn variant="text" size="small" icon="mdi-close" @click="systemStore.showLogModal = false" />
      </v-card-title>
      <v-divider />
      <div ref="logContainer" class="log-terminal" style="height: 500px;">
        <div
          v-for="(entry, i) in systemStore.filteredLogs"
          :key="i"
          class="log-entry"
          :class="{ 'log-entry--error': entry.level === 'ERROR', 'log-entry--warn': entry.level === 'WARNING' }"
        >
          <span class="log-entry__time">{{ entry.time }}</span>
          <span class="log-entry__level" :data-level="entry.level.toLowerCase()" :style="{ color: levelColors[entry.level] || '#4ecdc4' }">
            {{ entry.level }}
          </span>
          <span class="log-entry__msg">{{ entry.message }}</span>
        </div>
        <div v-if="!systemStore.filteredLogs.length" class="text-center pa-8 text-medium-emphasis">
          暂无日志
        </div>
      </div>
    </v-card>
  </v-dialog>
</template>
