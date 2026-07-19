<template>
  <n-modal
    :show="show"
    @update:show="(val) => $emit('update:show', val)"
    preset="card"
    :title="'配置媒体库: ' + library?.Name"
    style="width: 1000px"
    :bordered="false"
    segmented
  >
    <n-tabs type="line" animated>
      <n-tab-pane name="basic" tab="基础信息">
        <BasicInfoTab v-model="localData" />
      </n-tab-pane>

      <n-tab-pane name="metadata-fetchers" tab="元数据下载器">
        <MetadataFetchersTab v-model="localData" />
      </n-tab-pane>

      <n-tab-pane name="image-settings" tab="图片下载与参数">
        <ImageSettingsTab v-model="localData" />
      </n-tab-pane>

      <n-tab-pane name="features" tab="功能开关">
        <FeatureSwitchesTab v-model="localData" />
      </n-tab-pane>

      <n-tab-pane name="json" tab="原始数据 (JSON)">
        <n-space vertical>
          <n-alert type="info" size="small">
            高级操作：您可以直接编辑下方的原始 JSON 数据进行高级配置。
          </n-alert>
          <n-input
            v-model:value="jsonRaw"
            type="textarea"
            :autosize="{ minRows: 15, maxRows: 25 }"
            style="font-family: monospace"
            @update:value="handleJsonInput"
          />
        </n-space>
      </n-tab-pane>
    </n-tabs>

    <template #action>
      <n-space justify="end">
        <n-button 
          strong 
          secondary 
          @click="$emit('update:show', false)"
        >
          取消
        </n-button>
        <n-button 
          type="warning" 
          secondary 
          strong 
          @click="handleBackup" 
          :loading="backingUp"
        >
          备份当前配置
        </n-button>
        <n-button 
          type="primary" 
          strong 
          @click="handleSave" 
          :loading="loading"
        >
          保存设置
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useMessage, NIcon, NButton, NSpace, NAlert, NInput, NTabs, NTabPane, NModal } from 'naive-ui'
import BasicInfoTab from './tabs/BasicInfoTab.vue'
import MetadataFetchersTab from './tabs/MetadataFetchersTab.vue'
import ImageSettingsTab from './tabs/ImageSettingsTab.vue'
import FeatureSwitchesTab from './tabs/FeatureSwitchesTab.vue'
import { updateEmbyLibrary } from '@/api/embyLibraries'
import { createEmbyBackup } from '@/api/embyBackup'
const props = defineProps<{
  show: boolean
  library: any
  serverId: string
}>()

const emit = defineEmits(['update:show', 'saved'])
const message = useMessage()
const loading = ref(false)
const backingUp = ref(false)
const localData = ref<any>({ LibraryOptions: {} })
const jsonRaw = ref('')

watch(() => props.library, (newVal) => {
  if (newVal) {
    localData.value = JSON.parse(JSON.stringify(newVal))
    if (!localData.value.LibraryOptions) localData.value.LibraryOptions = {}
    jsonRaw.value = JSON.stringify(localData.value, null, 2)
  }
}, { immediate: true })

watch(localData, (newVal) => {
  const currentJson = JSON.stringify(newVal, null, 2)
  if (currentJson !== jsonRaw.value) {
    jsonRaw.value = currentJson
  }
}, { deep: true })

const handleJsonInput = (value: string) => {
  try {
    const parsed = JSON.parse(value)
    localData.value = parsed
  } catch (e) { }
}

const handleBackup = async () => {
  if (!props.library) return
  backingUp.value = true
  try {
    await createEmbyBackup('libraries', props.library.Id, props.library.Name, props.serverId)
    message.success('当前媒体库配置已备份')
  } catch (e) {
    console.error(e)
  } finally {
    backingUp.value = false
  }
}

const handleSave = async () => {
  try {
    const dataToSave = JSON.parse(jsonRaw.value)
    loading.value = true
    await updateEmbyLibrary(dataToSave, props.serverId)
    message.success('设置已保存')
    emit('saved')
    emit('update:show', false)
  } catch (e) {
    message.error('JSON 格式错误或保存失败')
  } finally {
    loading.value = false
  }
}
</script>