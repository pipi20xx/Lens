<template>
  <div class="basic-info-tab">
    <n-form label-placement="left" label-width="200" size="small">
      <n-form-item label="显示名称">
        <n-input :value="modelValue.Name" @update:value="(val) => updateRoot('Name', val)" />
      </n-form-item>
      
      <n-form-item label="内容类型">
        <n-tag type="info">{{ modelValue.CollectionType }}</n-tag>
      </n-form-item>

      <n-divider title-placement="left">语言与国家</n-divider>
      <n-form-item label="元数据语言 (PreferredMetadataLanguage)">
        <n-input :value="modelValue.LibraryOptions?.PreferredMetadataLanguage" @update:value="(val) => updateLibOpt('PreferredMetadataLanguage', val)" placeholder="zh" />
      </n-form-item>
      <n-form-item label="图片语言 (PreferredImageLanguage)">
        <n-input :value="modelValue.LibraryOptions?.PreferredImageLanguage" @update:value="(val) => updateLibOpt('PreferredImageLanguage', val)" placeholder="zh" />
      </n-form-item>
      <n-form-item label="国家代码 (MetadataCountryCode)">
        <n-input :value="modelValue.LibraryOptions?.MetadataCountryCode" @update:value="(val) => updateLibOpt('MetadataCountryCode', val)" placeholder="CN" />
      </n-form-item>
      
import { 
  AddOutlined as AddIcon
} from '@vicons/material'

// ... (props, emit, refs, etc.)

      <n-divider title-placement="left">媒体路径</n-divider>
      <n-dynamic-input
        v-model:value="localPaths"
        placeholder="请输入路径"
        @update:value="handlePathsChange"
      >
        <template #create-button-default>
          <n-button strong secondary type="primary" size="small">
            添加路径
          </n-button>
        </template>
      </n-dynamic-input>

      <n-divider title-placement="left">刮削设置</n-divider>
      <n-form-item label="本地元数据读取器 (NFO)">
        <n-checkbox-group :value="readerOrder" @update:value="handleReaderChange">
          <n-space>
            <n-checkbox value="Nfo">Nfo</n-checkbox>
            <n-checkbox value="Emby Xml">Emby Xml</n-checkbox>
          </n-space>
        </n-checkbox-group>
      </n-form-item>
    </n-form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: any
}>()

const emit = defineEmits(['update:modelValue'])

// 使用本地 ref 管理路径，解决 n-dynamic-input 响应问题
const localPaths = ref<string[]>([])

// 同步初始化
watch(() => props.modelValue.LibraryOptions?.PathInfos, (newVal) => {
  const paths = (newVal || []).map((p: any) => p.Path)
  // 只有当长度或内容不一致时才更新，防止输入时的干扰
  if (JSON.stringify(paths) !== JSON.stringify(localPaths.value)) {
    localPaths.value = paths
  }
}, { immediate: true })

const readerOrder = computed(() => {
  const disabled = props.modelValue.LibraryOptions?.DisabledLocalMetadataReaders || []
  const all = ["Nfo", "Emby Xml"]
  return all.filter(r => !disabled.includes(r))
})

const updateRoot = (key: string, val: any) => {
  const data = { ...props.modelValue }
  data[key] = val
  emit('update:modelValue', data)
}

const updateLibOpt = (key: string, val: any) => {
  const data = JSON.parse(JSON.stringify(props.modelValue))
  if (!data.LibraryOptions) data.LibraryOptions = {}
  data.LibraryOptions[key] = val
  emit('update:modelValue', data)
}

const handlePathsChange = (paths: string[]) => {
  const data = JSON.parse(JSON.stringify(props.modelValue))
  if (!data.LibraryOptions) data.LibraryOptions = {}
  // 过滤掉空路径并映射为 PathInfos 对象
  data.LibraryOptions.PathInfos = paths.map(p => ({ Path: p }))
  emit('update:modelValue', data)
}

const handleReaderChange = (val: string[]) => {
  const data = JSON.parse(JSON.stringify(props.modelValue))
  if (!data.LibraryOptions) data.LibraryOptions = {}
  const all = ["Nfo", "Emby Xml"]
  data.LibraryOptions.DisabledLocalMetadataReaders = all.filter(r => !val.includes(r))
  data.LibraryOptions.LocalMetadataReaderOrder = val
  emit('update:modelValue', data)
}
</script>