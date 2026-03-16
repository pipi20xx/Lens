<template>
  <n-modal
    :show="show"
    @update:show="$emit('update:show', $event)"
    preset="card"
    :title="task.id ? modalTitle.EDIT_BACKUP_TASK : modalTitle.ADD_BACKUP_TASK"
    style="width: 95vw; max-width: 500px"
  >
    <n-form :model="task" label-placement="top" :size="buttonSizes.SMALL">
      <n-form-item :label="formLabel.TASK_NAME">
        <n-input v-model:value="task.name" :placeholder="placeholder.TASK_NAME_EXAMPLE" />
      </n-form-item>

      <n-form-item :label="formLabel.BACKUP_MODE">
        <n-select v-model:value="task.mode" :options="modeOptions" />
      </n-form-item>

      <n-form-item :label="formLabel.STORAGE_MEDIUM" v-if="task.mode !== 'pgsql'">
        <n-select v-model:value="task.storage_type" :options="storageOptions" />
      </n-form-item>

      <n-form-item :label="formLabel.SYNC_STRATEGY" v-if="task.mode === 'sync'">
        <n-select v-model:value="task.sync_strategy" :options="syncOptions" />
      </n-form-item>

      <n-form-item :label="formLabel.SOURCE_PATH" v-if="task.mode !== 'pgsql'">
        <n-input v-model:value="task.src_path" :placeholder="placeholder.SOURCE_PATH" />
      </n-form-item>

      <n-form-item :label="formLabel.DESTINATION_DIR">
        <n-input v-model:value="task.dst_path" :placeholder="placeholder.DESTINATION_DIR" />
      </n-form-item>

      <n-form-item :label="formLabel.COMPRESSION_LEVEL" v-if="task.mode === '7z'">
        <n-slider v-model:value="task.compression_level" :min="1" :max="9" :step="1" />
        <n-text depth="3" style="margin-left: 12px">{{ label.LEVEL }} {{ task.compression_level }}</n-text>
      </n-form-item>

      <n-form-item :label="formLabel.ENCRYPTION_PASSWORD" v-if="task.mode === '7z'">
        <n-input v-model:value="task.password" type="password" show-password-on="click" :placeholder="placeholder.OPTIONAL" />
      </n-form-item>

      <n-divider title-placement="left">{{ label.AUTO_SCHEDULE }}</n-divider>

      <n-form-item :label="formLabel.ENABLE_SCHEDULE">
        <n-switch v-model:value="task.enabled" class="mobile-switch" />
      </n-form-item>

      <template v-if="task.enabled">
        <n-form-item :label="formLabel.RUN_FREQUENCY">
          <n-select v-model:value="simpleScheduleMode" :options="scheduleOptions" />
        </n-form-item>

        <n-form-item :label="formLabel.EXECUTION_TIME" v-if="simpleScheduleMode === 'daily'">
          <n-time-picker v-model:formatted-value="dailyTime" format="HH:mm" />
        </n-form-item>

        <n-form-item :label="formLabel.INTERVAL_TIME" v-if="simpleScheduleMode === 'interval'">
          <n-input-number v-model:value="intervalValue" :min="1" style="width: 120px" />
          <n-select v-model:value="intervalUnit" :options="unitOptions" style="width: 100px; margin-left: 8px" />
        </n-form-item>

        <n-form-item :label="formLabel.CRON_EXPRESSION" v-if="simpleScheduleMode === 'cron'">
          <n-input v-model:value="task.schedule_value" :placeholder="placeholder.CRON_EXAMPLE" />
        </n-form-item>
      </template>

      <n-form-item :label="formLabel.IGNORE_PATTERN" v-if="task.mode !== 'pgsql'">
        <n-space vertical :size="8" style="width: 100%">
          <n-space :size="4">
            <n-text depth="3" style="font-size: 12px; margin-right: 4px">{{ label.COMMON_PRESETS }}:</n-text>
            <n-tag
              v-for="p in presetPatterns"
              :key="p"
              :size="buttonSizes.SMALL"
              round
              checkable
              :checked="task.ignore_patterns.includes(p)"
              @update:checked="(val) => handleTogglePattern(p, val)"
              style="cursor: pointer"
            >
              {{ p }}
            </n-tag>
          </n-space>
          <n-dynamic-input v-model:value="task.ignore_patterns" :placeholder="placeholder.IGNORE_PATTERN_EXAMPLE" />
        </n-space>
      </n-form-item>
    </n-form>

    <template #footer>
      <n-space vertical style="width: 100%">
        <n-space justify="end">
          <n-button @click="$emit('update:show', false)">
            {{ buttonText.CANCEL }}
          </n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="handleSave">
            {{ buttonText.SAVE }}
          </n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import {
  NModal, NForm, NFormItem, NInput, NSelect, NSlider,
  NText, NDynamicInput, NSpace, NDivider, NSwitch,
  NTimePicker, NInputNumber, NTag
} from 'naive-ui'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  ModalTitle,
  FormLabel,
  Placeholder,
  Label,
} from '../constants'

const props = defineProps<{
  show: boolean
  task: any
}>()

const emit = defineEmits(['update:show', 'save'])

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const modalTitle = ModalTitle
const formLabel = FormLabel
const placeholder = Placeholder
const label = Label

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
