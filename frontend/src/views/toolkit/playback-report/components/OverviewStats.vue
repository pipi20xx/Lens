<template>
  <n-grid :x-gap="12" :y-gap="12" :cols="4" item-responsive responsive="screen">
    <n-gi v-for="stat in statItems" :key="stat.title" span="4 m:2 l:1">
      <n-card bordered size="small" hoverable class="stat-card">
        <n-statistic :label="stat.title">
          <template #prefix>
            <n-icon :color="stat.color">
              <component :is="stat.icon" />
            </n-icon>
          </template>
          <template #default>
            <n-number-animation :from="0" :to="stat.value" />
          </template>
          <template #suffix>
            <span class="unit-text">{{ stat.unit }}</span>
          </template>
        </n-statistic>
      </n-card>
    </n-gi>
  </n-grid>
</template>

<script setup lang="ts">
import { computed, markRaw } from 'vue'
import { NGrid, NGi, NCard, NStatistic, NIcon, NNumberAnimation } from 'naive-ui'
import {
  ClockIcon,
  DevicePhoneMobileIcon,
  PlayIcon,
  UsersIcon
} from '@heroicons/vue/24/outline'
const props = defineProps<{
  stats: {
    totalPlay: number
    totalDuration: number
    userCount: number
    deviceCount: number
  }
}>()

const statItems = computed(() => [
  {
    title: '累计播放次数',
    value: props.stats.totalPlay,
    icon: markRaw(PlayIcon),
    color: 'var(--primary-color)',
    unit: '次'
  },
  {
    title: '累计播放时长',
    value: props.stats.totalDuration,
    icon: markRaw(ClockIcon),
    color: '#18a058',
    unit: '分钟'
  },
  {
    title: '累计活跃用户',
    value: props.stats.userCount,
    icon: markRaw(UsersIcon),
    color: '#f0a020',
    unit: '人'
  },
  {
    title: '覆盖设备终端',
    value: props.stats.deviceCount,
    icon: markRaw(DevicePhoneMobileIcon),
    color: '#d03050',
    unit: '台'
  }
])
</script>

<style scoped>
.stat-card {
  height: 100%;
}
.unit-text {
  font-size: 14px;
  margin-left: 4px;
  opacity: 0.6;
}
:deep(.n-statistic .n-statistic__label) {
  font-weight: 500;
}
:deep(.n-statistic .n-statistic-value__content) {
  font-weight: bold;
}
</style>