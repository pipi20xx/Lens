<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">类型与标签管理</n-text></n-h2>
        <n-text depth="3">提供类型映射、一键移除及批量新增功能，深度优化媒体库标签结构。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：主要功能区 -->
        <n-gi span="24 m:16">
          <n-space vertical size="large">
            <!-- 1. 通用执行参数 -->
            <n-card title="通用执行参数" size="small" segmented>
              <n-form label-placement="left" label-width="120">
                <n-form-item label="目标媒体库">
                  <n-select 
                    v-model:value="common.lib_names" 
                    multiple 
                    filterable 
                    :options="libOptions"
                    placeholder="请选择要操作的媒体库" 
                  />
                </n-form-item>
                <n-form-item label="执行模式">
                  <n-switch v-model:value="common.dry_run">
                    <template #checked>预览模式</template>
                    <template #unchecked>实调模式</template>
                  </n-switch>
                </n-form-item>
              </n-form>
            </n-card>

            <!-- 2. 原子工具卡片 -->
            <n-grid :cols="3" :x-gap="12" :y-gap="12" item-responsive responsive="screen">
              <n-gi span="3 m:1">
                <n-card title="类型映射" size="small" style="height: 100%" content-style="display: flex; flex-direction: column; justify-content: space-between;">
                  <n-space vertical :size="8">
                    <n-input v-model:value="forms.map.old" placeholder="旧类型名" size="small" />
                    <n-input v-model:value="forms.map.new_name" placeholder="新类型名" size="small" />
                    <n-input v-model:value="forms.map.new_id" placeholder="新 ID (可选)" size="small" />
                  </n-space>
                  <div style="margin-top: 16px">
                    <n-button block type="primary" secondary @click="runMapper" :loading="loading">
                      执行映射
                    </n-button>
                  </div>
                </n-card>
              </n-gi>

              <n-gi span="3 m:1">
                <n-card title="类型移除" size="small" style="height: 100%" content-style="display: flex; flex-direction: column; justify-content: space-between;">
                  <n-space vertical :size="8">
                    <n-input v-model:value="forms.remove.tag" placeholder="要移除的标签名" size="small" />
                    <n-text depth="3" style="font-size: 12px">留空则清空该库所有类型标签。</n-text>
                  </n-space>
                  <div style="margin-top: 16px">
                    <n-button block type="error" secondary @click="runRemover" :loading="loading">
                      执行移除
                    </n-button>
                  </div>
                </n-card>
              </n-gi>

              <n-gi span="3 m:1">
                <n-card title="类型新增" size="small" style="height: 100%" content-style="display: flex; flex-direction: column; justify-content: space-between;">
                  <n-space vertical :size="8">
                    <n-input v-model:value="forms.add.name" placeholder="新增类型名" size="small" />
                    <n-input v-model:value="forms.add.id" placeholder="新增 ID (可选)" size="small" />
                  </n-space>
                  <div style="margin-top: 16px">
                    <n-button block type="success" secondary @click="runAdder" :loading="loading">
                      执行新增
                    </n-button>
                  </div>
                </n-card>
              </n-gi>
            </n-grid>
          </n-space>
        </n-gi>

        <!-- 右侧：说明区 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <n-card title="操作提示" size="small" segmented>
              <n-alert type="info" :bordered="false">
                点击按钮后，建议打开实时日志窗口查看详细执行进度。
              </n-alert>
              <n-text depth="3" style="font-size: 13px; margin-top: 12px; display: block;">
                <b>逻辑说明：</b><br/>
                此工具不仅修改项目的 Tags 属性，还会同步处理底层的 GenreItems 对象，确保在 Emby 各级界面中生效。
              </n-text>
            </n-card>

            <n-card title="预览模式" size="small" segmented>
              <n-text depth="3" style="font-size: 13px">
                建议先在“预览模式”下运行，查看日志中模拟的处理结果，确认无误后再切换到“实调模式”执行物理写入。
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { 
  useMessage, NSpace, NH2, NText, NCard, NButton, NGrid, NGi, 
  NSwitch, NForm, NFormItem, NSelect, NInput, NAlert, NIcon 
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
    message.success(`映射任务完成：共处理 ${res.data.processed_count} 个项目 [${common.dry_run ? '预览' : '实调'}]`)
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
    message.success(`移除任务完成：共清理 ${res.data.processed_count} 个项目 [${common.dry_run ? '预览' : '实调'}]`)
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
    message.success(`新增任务完成：共影响 ${res.data.processed_count} 个项目 [${common.dry_run ? '预览' : '实调'}]`)
  } catch (e) { message.error('请求失败') }
  finally { loading.value = false }
}
</script>

<style scoped>
</style>