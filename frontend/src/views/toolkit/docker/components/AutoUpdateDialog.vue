<script setup lang="ts">
import { ref } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()

const showDialog = defineModel<boolean>({ default: false })
const savingAutoUpdate = ref(false)
const autoUpdateSettings = ref({ enabled: false, type: 'cron', value: '03:00' })
const intervalParts = ref({ d: 0, h: 0, m: 0 })

async function loadSettings() {
  try {
    const data = await dockerApi.getAutoUpdateSettings()
    autoUpdateSettings.value = { enabled: data?.enabled ?? false, type: data?.type ?? 'cron', value: data?.value ?? '03:00' }
    if (data?.type === 'interval') {
      const totalMin = parseInt(data?.value) || 0
      intervalParts.value = { d: Math.floor(totalMin / 1440), h: Math.floor((totalMin % 1440) / 60), m: totalMin % 60 }
    }
  } catch { /* ignore */ }
}

async function saveAutoUpdateSettings() {
  savingAutoUpdate.value = true
  try {
    let value = autoUpdateSettings.value.value
    if (autoUpdateSettings.value.type === 'interval') {
      value = String((intervalParts.value.d * 1440) + (intervalParts.value.h * 60) + intervalParts.value.m)
    }
    await dockerApi.saveAutoUpdateSettings({ enabled: autoUpdateSettings.value.enabled, type: autoUpdateSettings.value.type, value })
    success('自动更新设置已保存')
    showDialog.value = false
  } catch { showError('保存失败') }
  finally { savingAutoUpdate.value = false }
}

// 打开时自动加载
import { watch } from 'vue'
watch(showDialog, (val) => { if (val) loadSettings() })
</script>

<template>
  <GlassDialog v-model="showDialog" :max-width="450" icon="mdi-timer-outline" title="自动更新全局设置">
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">此处设置将决定系统何时执行镜像检查。开启后，仅会对在容器列表中手动勾选了「自动更新」标记的容器生效。</v-alert>
    <v-switch v-model="autoUpdateSettings.enabled" label="启用全局调度" density="compact" color="primary" class="mb-3" />
    <v-select v-model="autoUpdateSettings.type" :items="[{title: '每日定时 (Cron)', value: 'cron'}, {title: '固定间隔 (Interval)', value: 'interval'}]" label="执行模式" variant="outlined" density="compact" class="mb-3" />
    <template v-if="autoUpdateSettings.type === 'cron'">
      <v-text-field v-model="autoUpdateSettings.value" label="执行时间 (每天)" variant="outlined" density="compact" type="time" hint="每天此时间点自动开始检查" persistent-hint />
    </template>
    <template v-if="autoUpdateSettings.type === 'interval'">
      <v-row dense>
        <v-col cols="4"><v-text-field v-model.number="intervalParts.d" label="天" variant="outlined" density="compact" type="number" :min="0" /></v-col>
        <v-col cols="4"><v-text-field v-model.number="intervalParts.h" label="时" variant="outlined" density="compact" type="number" :min="0" :max="23" /></v-col>
        <v-col cols="4"><v-text-field v-model.number="intervalParts.m" label="分" variant="outlined" density="compact" type="number" :min="0" :max="59" /></v-col>
      </v-row>
      <span class="text-caption text-medium-emphasis">当前合计: {{ (intervalParts.d * 1440) + (intervalParts.h * 60) + intervalParts.m }} 分钟</span>
    </template>

    <template #actions>
      <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveAutoUpdateSettings" :loading="savingAutoUpdate">保存并生效</v-btn>
    </template>
  </GlassDialog>
</template>
