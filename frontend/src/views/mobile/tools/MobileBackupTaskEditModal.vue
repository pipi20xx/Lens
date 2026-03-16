<template>
  <n-modal 
    :show="show" 
    @update:show="$emit('update:show', $event)" 
    preset="card" 
    :title="task.id ? '编辑备份任务' : '新增备份任务'" 
    style="width: 95vw; max-width: 500px"
  >
    <n-form :model="task" label-placement="top" size="small">
      <n-form-item label="任务名称">
        <n-input v-model:value="task.name" placeholder="例如：数据库每日备份" />
      </n-form-item>
      
      <n-form-item label="备份模式">
        <n-select v-model:value="task.mode" :options="modeOptions" />
      </n-form-item>
      
      <n-form-item label="存储介质" v-if="task.mode !== 'pgsql'">
        <n-select v-model:value="task.storage_type" :options="storageOptions" />
      </n-form-item>
      
      <n-form-item label="同步策略" v-if="task.mode === 'sync'">
        <n-select v-model:value="task.sync_strategy" :options="syncOptions" />
      </n-form-item>
      
      <n-form-item label="源路径" v-if="task.mode !== 'pgsql'">
        <n-input v-model:value="task.src_path" placeholder="/app/data" />
      </n-form-item>
      
      <n-form-item label="目标目录">
        <n-input v-model:value="task.dst_path" placeholder="/backup" />
      </n-form-item>
      
      <n-form-item label="压缩强度" v-if="task.mode === '7z'">
        <n-slider v-model:value="task.compression_level" :min="1" :max="9" :step="1" />
        <n-text depth="3" style="margin-left: 12px">等级 {{ task.compression_level }}</n-text>
      </n-form-item>
      
      <n-form-item label="加密密码" v-if="task.mode === '7z'">
        <n-input v-model:value="task.password" type="password" show-password-on="click" placeholder="可选" />
      </n-form-item>
      
      <n-divider title-placement="left">自动化运行计划</n-divider>
      
      <n-form-item label="启用定时备份">
        <n-switch v-model:value="task.enabled" />
      </n-form-item>
      
      <template v-if="task.enabled">
        <n-form-item label="运行频率">
          <n-select v-model:value="simpleScheduleMode" :options="scheduleOptions" />
        </n-form-item>
        
        <n-form-item label="执行时间" v-if="simpleScheduleMode === 'daily'">
          <n-time-picker v-model:formatted-value="dailyTime" format="HH:mm" />
        </n-form-item>
        
        <n-form-item label="间隔时间" v-if="simpleScheduleMode === 'interval'">
          <n-input-number v-model:value="intervalValue" :min="1" style="width: 120px" />
          <n-select v-model:value="intervalUnit" :options="unitOptions" style="width: 100px; margin-left: 8px" />
        </n-form-item>
        
        <n-form-item label="Cron 表达式" v-if="simpleScheduleMode === 'cron'">
          <n-input v-model:value="task.schedule_value" placeholder="0 3 * * *" />
        </n-form-item>
      </template>
      
      <n-form-item label="忽略模式" v-if="task.mode !== 'pgsql'">
        <n-space vertical :size="8" style="width: 100%">
          <n-space :size="4">
            <n-text depth="3" style="font-size: 12px; margin-right: 4px">常用预设:</n-text>
            <n-tag 
              v-for="p in presetPatterns" 
              :key="p" 
              size="small" 
              round 
              checkable 
              :checked="task.ignore_patterns.includes(p)"
              @update:checked="(val) => handleTogglePattern(p, val)"
              style="cursor: pointer"
            >
              {{ p }}
            </n-tag>
          </n-space>
          <n-dynamic-input v-model:value="task.ignore_patterns" placeholder="例如：*.log" />
        </n-space>
      </n-form-item>
    </n-form>
    
    <template #footer>
      <n-space vertical style="width: 100%">
        <n-space justify="end">
          <n-button @click="$emit('update:show', false)">
            取消
          </n-button>
          <n-button type="primary" @click="handleSave">
            保存
          </n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { 
  NModal, NForm, NFormItem, NInput, NSelect, NSlider, 
  NText, NDynamicInput, NSpace, NDivider, NSwitch, 
  NTimePicker, NInputNumber, NTag 
} from 'naive-ui'

const props = defineProps<{
  show: boolean
  task: any
}>()

const emit = defineEmits(['update:show', 'save'])

const simpleScheduleMode = ref('daily')
const dailyTime = ref('03:00')
const intervalValue = ref(1)
const intervalUnit = ref(60)

const modeOptions = [
  { label: '7z 压缩', value: '7z' },
  { label: 'Tar.gz 打包', value: 'tar' },
  { label: 'Sync 同步', value: 'sync' },
  { label: 'PostgreSQL 备份', value: 'pgsql' }
]

const storageOptions = [
  { label: 'SSD (高性能)', value: 'ssd' },
  { label: 'HDD (机械硬盘)', value: 'hdd' },
  { label: '云盘', value: 'cloud' }
]

const syncOptions = [
  { label: '镜像模式 (完全一致)', value: 'mirror' },
  { label: '增量模式 (只增不删)', value: 'incremental' }
]

const scheduleOptions = [
  { label: '每天固定时间', value: 'daily' },
  { label: '固定间隔频率', value: 'interval' },
  { label: '自定义 Cron', value: 'cron' }
]

const unitOptions = [
  { label: '分钟', value: 1 },
  { label: '小时', value: 60 },
  { label: '天', value: 1440 }
]

const presetPatterns = [
  '__pycache__', '*.pyc', '.git', 'node_modules', 'target', 
  '.vscode', '.idea', 'dist', 'build', '*.log', '.DS_Store'
]

const handleTogglePattern = (pattern: string, checked: boolean) => {
  const patterns = [...props.task.ignore_patterns]
  if (checked) {
    if (!patterns.includes(pattern)) {
      patterns.push(pattern)
    }
  } else {
    const index = patterns.indexOf(pattern)
    if (index > -1) {
      patterns.splice(index, 1)
    }
  }
  props.task.ignore_patterns = patterns
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    if (props.task.schedule_type === 'cron') {
      const cron = props.task.schedule_value || ''
      const dailyMatch = cron.match(/^(\d+)\s+(\d+)\s+\*\s+\*\s+\*$/)
      if (dailyMatch) {
        simpleScheduleMode.value = 'daily'
        const m = dailyMatch[1].padStart(2, '0')
        const h = dailyMatch[2].padStart(2, '0')
        dailyTime.value = `${h}:${m}`
      } else {
        simpleScheduleMode.value = 'cron'
      }
    } else if (props.task.schedule_type === 'interval') {
      simpleScheduleMode.value = 'interval'
      const totalMin = parseInt(props.task.schedule_value) || 60
      if (totalMin % 1440 === 0) {
        intervalUnit.value = 1440
        intervalValue.value = totalMin / 1440
      } else if (totalMin % 60 === 0) {
        intervalUnit.value = 60
        intervalValue.value = totalMin / 60
      } else {
        intervalUnit.value = 1
        intervalValue.value = totalMin
      }
    }
  }
})

const handleSave = () => {
  if (simpleScheduleMode.value === 'daily') {
    const [h, m] = dailyTime.value.split(':').map(x => parseInt(x))
    props.task.schedule_type = 'cron'
    props.task.schedule_value = `${m} ${h} * * *`
  } else if (simpleScheduleMode.value === 'interval') {
    props.task.schedule_type = 'interval'
    props.task.schedule_value = String(intervalValue.value * intervalUnit.value)
  }
  emit('save')
}
</script>
