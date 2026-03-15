<template>
  <div class="mobile-type-manager">
    <div class="page-header">
      <h1 class="page-title">类型与标签管理</h1>
      <p class="page-desc">类型映射、移除及批量新增</p>
    </div>

    <n-card class="config-card" :bordered="false" title="执行参数">
      <n-space vertical>
        <n-form-item label="目标媒体库">
          <n-select 
            v-model:value="common.lib_names" 
            multiple 
            filterable 
            :options="libOptions"
            placeholder="选择媒体库" 
          />
        </n-form-item>
        <div class="mode-row">
          <n-radio-group v-model:value="common.dry_run" size="large">
            <n-radio-button :value="true">预览模式</n-radio-button>
            <n-radio-button :value="false">实调模式</n-radio-button>
          </n-radio-group>
        </div>
      </n-space>
    </n-card>

    <n-card class="action-card" :bordered="false" title="类型操作">
      <n-space vertical>
        <!-- 类型映射 -->
        <n-card size="small" :bordered="false" class="tool-card">
          <div class="tool-title">类型映射</div>
          <n-space vertical>
            <n-input v-model:value="forms.map.old" placeholder="旧类型名" />
            <n-input v-model:value="forms.map.new_name" placeholder="新类型名" />
            <n-input v-model:value="forms.map.new_id" placeholder="新 ID (可选)" />
          </n-space>
          <n-button 
            block 
            type="primary" 
            secondary 
            :loading="loading"
            @click="runMapper"
            style="margin-top: 12px"
          >
            <template #icon><n-icon><MapIcon /></n-icon></template>
            执行映射
          </n-button>
        </n-card>

        <!-- 类型移除 -->
        <n-card size="small" :bordered="false" class="tool-card">
          <div class="tool-title">类型移除</div>
          <n-input v-model:value="forms.remove.tag" placeholder="要移除的标签名 (留空则清空所有)" />
          <n-button 
            block 
            type="error" 
            secondary 
            :loading="loading"
            @click="runRemover"
            style="margin-top: 12px"
          >
            <template #icon><n-icon><DeleteIcon /></n-icon></template>
            执行移除
          </n-button>
        </n-card>

        <!-- 类型新增 -->
        <n-card size="small" :bordered="false" class="tool-card">
          <div class="tool-title">类型新增</div>
          <n-space vertical>
            <n-input v-model:value="forms.add.name" placeholder="新增类型名" />
            <n-input v-model:value="forms.add.id" placeholder="新增 ID (可选)" />
          </n-space>
          <n-button 
            block 
            type="success" 
            secondary 
            :loading="loading"
            @click="runAdder"
            style="margin-top: 12px"
          >
            <template #icon><n-icon><AddIcon /></n-icon></template>
            执行新增
          </n-button>
        </n-card>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { 
  useMessage, NCard, NButton, NSelect, NRadioGroup, NRadioButton, 
  NInput, NIcon, NSpace
} from 'naive-ui'
import {
  SyncAltOutlined as MapIcon,
  DeleteSweepOutlined as DeleteIcon,
  AddCircleOutlineOutlined as AddIcon
} from '@vicons/material'
import axios from 'axios'

const message = useMessage()
const loading = ref(false)
const libOptions = ref([])

const common = reactive({
  lib_names: JSON.parse(localStorage.getItem('lens_toolkit_common') || '{"lib_names":[]}').lib_names,
  dry_run: true
})

watch(common, (val) => {
  localStorage.setItem('lens_toolkit_common', JSON.stringify(val))
}, { deep: true })

const fetchLibraries = async () => {
  try {
    const res = await axios.get('/api/server/libraries')
    libOptions.value = res.data
  } catch (e) {}
}

onMounted(fetchLibraries)

const forms = reactive({
  map: { old: '', new_name: '', new_id: '' },
  remove: { tag: '' },
  add: { name: '', id: '' }
})

const runMapper = async () => {
  if (common.lib_names.length === 0) { message.warning('请选择媒体库'); return; }
  if (!forms.map.old || !forms.map.new_name) { message.warning('请填写映射规则'); return; }
  
  loading.value = true
  try {
    const payload = {
      ...common,
      genre_mappings: [{
        old: forms.map.old,
        new_name: forms.map.new_name,
        new_id: forms.map.new_id || null
      }]
    }
    const res = await axios.post('/api/toolkit/mapper', payload)
    message.success(`映射完成：共处理 ${res.data.processed_count} 个项目`)
  } catch (e) {
    message.error('映射请求失败')
  } finally {
    loading.value = false
  }
}

const runRemover = async () => {
  if (common.lib_names.length === 0) { message.warning('请选择媒体库'); return; }
  loading.value = true
  try {
    const payload = {
      ...common,
      genres_to_remove: forms.remove.tag ? [forms.remove.tag] : []
    }
    const res = await axios.post('/api/toolkit/remover', payload)
    message.success(`移除完成：共清理 ${res.data.processed_count} 个项目`)
  } catch (e) { message.error('请求失败') }
  finally { loading.value = false }
}

const runAdder = async () => {
  if (common.lib_names.length === 0) { message.warning('请选择媒体库'); return; }
  loading.value = true
  try {
    const payload = {
      ...common,
      genre_to_add_name: forms.add.name,
      genre_to_add_id: forms.add.id || null
    }
    const res = await axios.post('/api/toolkit/genre_adder', payload)
    message.success(`新增完成：共影响 ${res.data.processed_count} 个项目`)
  } catch (e) { message.error('请求失败') }
  finally { loading.value = false }
}
</script>

<style scoped>
.mobile-type-manager {
  padding: 16px;
  padding-bottom: 32px;
  background: var(--app-bg-color);
  min-height: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color);
  margin: 0 0 8px 0;
}

.page-desc {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.config-card,
.action-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.tool-card {
  background: var(--app-bg-color);
  border-radius: 12px;
}

.tool-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
  margin-bottom: 12px;
}

.mode-row {
  padding: 12px 0;
}
</style>
