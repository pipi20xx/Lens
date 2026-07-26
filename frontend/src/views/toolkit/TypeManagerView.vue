<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { serverApi } from '@/api/server'
import { useNotification } from '@/composables'

const { success, error: showError, warning } = useNotification()

const loading = ref(false)
const libOptions = ref<any[]>([])

const savedCommon = localStorage.getItem('lens_toolkit_common')
const common = reactive(savedCommon ? JSON.parse(savedCommon) : {
  lib_names: [] as string[],
  dry_run: true
})

watch(common, (val) => {
  localStorage.setItem('lens_toolkit_common', JSON.stringify(val))
}, { deep: true })

const forms = reactive({
  map: { old: '', new_name: '', new_id: '' },
  remove: { tag: '' },
  add: { name: '', id: '' }
})

async function fetchLibraries() {
  try {
    const data = await serverApi.getLibraries()
    libOptions.value = Array.isArray(data) ? data : []
  } catch { /* ignore */ }
}

onMounted(fetchLibraries)

async function runMapper() {
  if (common.lib_names.length === 0) { warning('请选择媒体库'); return }
  if (!forms.map.old || !forms.map.new_name) { warning('请填写映射规则'); return }
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
    const res = await toolkitApi.mapper(payload)
    success(`映射任务完成：共处理 ${res?.processed_count ?? 0} 个项目 [${common.dry_run ? '预览' : '实调'}]`)
  } catch {
    showError('映射请求失败')
  } finally {
    loading.value = false
  }
}

async function runRemover() {
  if (common.lib_names.length === 0) { warning('请选择媒体库'); return }
  loading.value = true
  try {
    const payload = {
      ...common,
      genres_to_remove: forms.remove.tag ? [forms.remove.tag] : []
    }
    const res = await toolkitApi.genreRemover(payload)
    success(`移除任务完成：共清理 ${res?.processed_count ?? 0} 个项目 [${common.dry_run ? '预览' : '实调'}]`)
  } catch {
    showError('请求失败')
  } finally {
    loading.value = false
  }
}

async function runAdder() {
  if (common.lib_names.length === 0) { warning('请选择媒体库'); return }
  loading.value = true
  try {
    const payload = {
      ...common,
      genre_to_add_name: forms.add.name,
      genre_to_add_id: forms.add.id || null
    }
    const res = await toolkitApi.genreAdder(payload)
    success(`新增任务完成：共影响 ${res?.processed_count ?? 0} 个项目 [${common.dry_run ? '预览' : '实调'}]`)
  } catch {
    showError('请求失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-format-list-bulleted-type</v-icon>
      类型映射管理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">提供类型映射、一键移除及批量新增功能，深度优化媒体库标签结构。</p>

    <v-row>
      <!-- 左侧：主要功能区 -->
      <v-col cols="12" md="7">
        <!-- 通用执行参数 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-tune</v-icon>
            通用执行参数
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-select v-model="common.lib_names" :items="libOptions" item-title="label" item-value="value" multiple chips closable-chips
              label="目标媒体库" variant="outlined" density="compact" placeholder="请选择要操作的媒体库" class="mb-3" />
            <v-switch v-model="common.dry_run" color="primary" density="compact" hide-details>
              <template #label>
                <span class="text-body-2">执行模式：</span>
                <v-chip size="small" :color="common.dry_run ? 'info' : 'error'" variant="tonal" class="ml-2">
                  {{ common.dry_run ? '预览模式' : '实调模式' }}
                </v-chip>
              </template>
            </v-switch>
          </v-card-text>
        </v-card>

        <!-- 原子工具卡片 -->
        <v-row>
          <!-- 类型映射 -->
          <v-col cols="12" sm="4">
            <v-card class="liquid-glass-card" rounded="xl" style="height:100%;display:flex;flex-direction:column">
              <v-card-title class="pa-4 text-subtitle-2">
                <v-icon start size="18">mdi-swap-horizontal</v-icon>
                类型映射
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <v-text-field v-model="forms.map.old" label="旧类型名" variant="outlined" density="compact" hide-details class="mb-2" />
                <v-text-field v-model="forms.map.new_name" label="新类型名" variant="outlined" density="compact" hide-details class="mb-2" />
                <v-text-field v-model="forms.map.new_id" label="新 ID (可选)" variant="outlined" density="compact" hide-details />
              </v-card-text>
              <v-divider />
              <div class="pa-4">
                <v-btn block color="primary" variant="tonal" @click="runMapper" :loading="loading">执行映射</v-btn>
              </div>
            </v-card>
          </v-col>

          <!-- 类型移除 -->
          <v-col cols="12" sm="4">
            <v-card class="liquid-glass-card" rounded="xl" style="height:100%;display:flex;flex-direction:column">
              <v-card-title class="pa-4 text-subtitle-2">
                <v-icon start size="18">mdi-minus-circle-outline</v-icon>
                类型移除
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <v-text-field v-model="forms.remove.tag" label="要移除的标签名" variant="outlined" density="compact" hide-details class="mb-2" />
                <p class="text-caption text-medium-emphasis">留空则清空该库所有类型标签。</p>
              </v-card-text>
              <v-divider />
              <div class="pa-4">
                <v-btn block color="error" variant="tonal" @click="runRemover" :loading="loading">执行移除</v-btn>
              </div>
            </v-card>
          </v-col>

          <!-- 类型新增 -->
          <v-col cols="12" sm="4">
            <v-card class="liquid-glass-card" rounded="xl" style="height:100%;display:flex;flex-direction:column">
              <v-card-title class="pa-4 text-subtitle-2">
                <v-icon start size="18">mdi-plus-circle-outline</v-icon>
                类型新增
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <v-text-field v-model="forms.add.name" label="新增类型名" variant="outlined" density="compact" hide-details class="mb-2" />
                <v-text-field v-model="forms.add.id" label="新增 ID (可选)" variant="outlined" density="compact" hide-details />
              </v-card-text>
              <v-divider />
              <div class="pa-4">
                <v-btn block color="success" variant="tonal" @click="runAdder" :loading="loading">执行新增</v-btn>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-col>

      <!-- 右侧：说明区 -->
      <v-col cols="12" md="5">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-information-outline</v-icon>
            操作提示
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <v-alert type="info" variant="tonal" density="compact" class="mb-3">
              点击按钮后，建议打开实时日志窗口查看详细执行进度。
            </v-alert>
            <p><strong>逻辑说明：</strong></p>
            <p>此工具不仅修改项目的 Tags 属性，还会同步处理底层的 GenreItems 对象，确保在 Emby 各级界面中生效。</p>
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-eye-outline</v-icon>
            预览模式
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p>建议先在"预览模式"下运行，查看日志中模拟的处理结果，确认无误后再切换到"实调模式"执行物理写入。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
