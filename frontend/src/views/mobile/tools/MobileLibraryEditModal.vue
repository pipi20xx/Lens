<template>
  <n-modal
    :show="show"
    @update:show="(val) => $emit('update:show', val)"
    preset="card"
    :title="'配置媒体库: ' + library?.Name"
    style="width: 95vw; max-width: 600px"
    :bordered="false"
  >
    <MobileTabs v-model="activeTab" :tabs="tabs">
      <template #basic>
        <BasicInfoTab v-model="localData" />
      </template>

      <template #metadata-fetchers>
        <MetadataFetchersTab v-model="localData" />
      </template>

      <template #image-settings>
        <ImageSettingsTab v-model="localData" />
      </template>

      <template #features>
        <FeatureSwitchesTab v-model="localData" />
      </template>

      <template #json>
        <n-space vertical>
          <n-alert type="info" size="small">
            高级操作：您可以直接编辑下方的原始 JSON 数据进行高级配置。
          </n-alert>
          <n-input
            v-model:value="jsonRaw"
            type="textarea"
            :autosize="{ minRows: 10, maxRows: 20 }"
            style="font-family: monospace; font-size: 12px"
            @update:value="handleJsonInput"
          />
        </n-space>
      </template>
    </MobileTabs>

    <template #action>
      <n-space vertical style="width: 100%">
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
            备份
          </n-button>
          <n-button 
            type="primary" 
            strong 
            @click="handleSave" 
            :loading="loading"
          >
            保存
          </n-button>
        </n-space>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useMessage, NButton, NSpace, NAlert, NInput, NModal } from 'naive-ui'
import BasicInfoTab from '../../emby-library/tabs/BasicInfoTab.vue'
import MetadataFetchersTab from '../../emby-library/tabs/MetadataFetchersTab.vue'
import ImageSettingsTab from '../../emby-library/tabs/ImageSettingsTab.vue'
import FeatureSwitchesTab from '../../emby-library/tabs/FeatureSwitchesTab.vue'
import MobileTabs from '../components/MobileTabs.vue'
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
const activeTab = ref('basic')

const tabs = [
  { name: 'basic', label: '基础信息' },
  { name: 'metadata-fetchers', label: '元数据下载器' },
  { name: 'image-settings', label: '图片设置' },
  { name: 'features', label: '功能开关' },
  { name: 'json', label: 'JSON' },
]

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

<style scoped>
:deep(.n-tab-pane) {
  padding: 12px 0;
}
</style>
