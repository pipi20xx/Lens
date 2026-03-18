<template>
  <div class="pulse-activity-card">
    <div class="card-header">
      <div class="title-group">
        <n-icon size="22" color="#0078d4"><TimelineOutlined /></n-icon>
        <span class="title">24小时播放热度脉冲</span>
      </div>
      <div class="peak-info" v-if="peakHour">
        高峰时段: <span class="highlight">{{ peakHour }}:00</span>
      </div>
    </div>
    <div class="chart-container">
      <v-chart class="chart" :option="chartOption" autoresize />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NIcon } from 'naive-ui'
import { TimelineOutlined } from '@vicons/material'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent])

const props = defineProps<{
  hourlyData: Record<string, number>
}>()

const peakHour = computed(() => {
  let max = -1
  let hour = ''
  for (let i = 0; i < 24; i++) {
    const val = props.hourlyData[`Hour-${i}`] || 0
    if (val > max) {
      max = val
      hour = String(i).padStart(2, '0')
    }
  }
  return max > 0 ? hour : null
})

const chartOption = computed(() => {
  const hours = Array.from({ length: 24 }, (_, i) => `${i}h`)
  const data = Array.from({ length: 24 }, (_, i) => props.hourlyData[`Hour-${i}`] || 0)

  return {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(16, 16, 20, 0.9)',
      borderColor: 'rgba(59, 130, 246, 0.1)',
      textStyle: { color: 'var(--text-color)' },
      formatter: (params: any) => {
        const p = params[0]
        return `<div style="padding: 4px">
          <div style="color: #888; font-size: 12px; margin-bottom: 4px">${p.name}:00 - ${p.name.replace('h', '')}:59</div>
          <div style="font-weight: bold; color: var(--primary-color)">播放次数: ${p.value}</div>
        </div>`
      }
    },
    grid: {
      top: '10%',
      bottom: '10%',
      left: '3%',
      right: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: hours,
      boundaryGap: false,
      axisLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.1)' } },
      axisTick: { show: false },
      axisLabel: { color: '#666', fontSize: 11, interval: 2 }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(59, 130, 246, 0.03)', type: 'dashed' } },
      axisLabel: { color: '#666', fontSize: 11 }
    },
    series: [
      {
        name: '播放热度',
        type: 'line',
        smooth: 0.4, // 极其平滑
        showSymbol: false,
        data: data,
        lineStyle: {
          width: 4,
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: '#0078d4' },
              { offset: 1, color: '#00bcf2' }
            ]
          },
          shadowBlur: 10,
          shadowColor: 'rgba(0, 120, 212, 0.5)'
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(0, 120, 212, 0.2)' },
              { offset: 1, color: 'transparent' }
            ]
          }
        },
        emphasis: {
          scale: true,
          itemStyle: {
            color: 'var(--text-color)',
            borderColor: 'var(--primary-color)',
            borderWidth: 3
          }
        }
      }
    ]
  }
})
</script>

<style scoped>
.pulse-activity-card {
  width: 100%;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}
.title {
  font-size: 18px;
  font-weight: bold;
  color: var(--text-color);
}
.peak-info {
  font-size: 12px;
  color: #666;
  background: var(--hover-bg);
  padding: 4px 12px;
  border-radius: 20px;
}
.highlight {
  color: var(--primary-color);
  font-weight: bold;
}
.chart-container {
  height: 240px;
}
.chart {
  width: 100%;
  height: 100%;
}
</style>