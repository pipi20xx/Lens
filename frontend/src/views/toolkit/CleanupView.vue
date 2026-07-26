<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { serverApi } from '@/api/server'
import { useNotification } from '@/composables'

const { success, error: showError, warning } = useNotification()

const loading = ref(false)
const libOptions = ref<any[]>([])

const savedCommon = localStorage.getItem('lens_cleanup_common')
const common = reactive(savedCommon ? JSON.parse(savedCommon) : {
  lib_names: [] as string[],
  dry_run: true
})

watch(common, (val) => {
  localStorage.setItem('lens_cleanup_common', JSON.stringify(val))
}, { deep: true })

const peopleItemTypes = ref(['Movie', 'Series'])

async function fetchLibraries() {
  try {
    const data = await serverApi.getLibraries()
    libOptions.value = Array.isArray(data) ? data : []
  } catch { /* ignore */ }
}

onMounted(fetchLibraries)

async function handleAction(endpoint: string) {
  if (common.lib_names.length === 0) {
    warning('请至少指定一个媒体库')
    return
  }
  loading.value = true
  try {
    const payload: any = {
      lib_names: common.lib_names,
      dry_run: common.dry_run
    }
    if (endpoint === 'people_remover') {
      payload.item_types = peopleItemTypes.value
    }
    const res = await toolkitApi.executeAction(endpoint, payload)
    success(`任务完成：处理项目数 ${res?.processed_count ?? 0} [${common.dry_run ? '预览' : '实调'}]`)
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
      <v-icon start>mdi-broom</v-icon>
      媒体净化清理
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">支持指定媒体库与媒体类型，执行演职员移除或剧集类型重置，保持媒体库整洁。</p>

    <v-row>
      <!-- 左侧：主要功能区 -->
      <v-col cols="12" md="7">
        <!-- 全局配置 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-tune</v-icon>
            通用执行参数
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-select v-model="common.lib_names" :items="libOptions" item-title="label" item-value="value" multiple chips closable-chips
              label="目标媒体库" variant="outlined" density="compact" placeholder="自动拉取媒体库列表中..." class="mb-3" />
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
          <!-- 演职员信息清空 -->
          <v-col cols="12" sm="6">
            <v-card class="liquid-glass-card" rounded="xl" style="height:100%;display:flex;flex-direction:column">
              <v-card-title class="pa-4 text-subtitle-2">
                <v-icon start size="18">mdi-account-remove-outline</v-icon>
                演职员信息清空
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <p class="text-caption text-medium-emphasis mb-3">操作媒体类型：</p>
                <div class="d-flex ga-3">
                  <v-checkbox v-model="peopleItemTypes" value="Movie" label="电影" density="compact" hide-details />
                  <v-checkbox v-model="peopleItemTypes" value="Series" label="剧集" density="compact" hide-details />
                </div>
              </v-card-text>
              <v-divider />
              <div class="pa-4">
                <v-btn block color="error" variant="tonal" @click="handleAction('people_remover')" :loading="loading">
                  执行清空演职员
                </v-btn>
              </div>
            </v-card>
          </v-col>

          <!-- 集类型重置 -->
          <v-col cols="12" sm="6">
            <v-card class="liquid-glass-card" rounded="xl" style="height:100%;display:flex;flex-direction:column">
              <v-card-title class="pa-4 text-subtitle-2">
                <v-icon start size="18">mdi-refresh</v-icon>
                集类型(Episode)重置
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <p class="text-caption text-medium-emphasis">扫描指定媒体库中的所有剧集，清除"集"层级的 Genres 标签。</p>
              </v-card-text>
              <v-divider />
              <div class="pa-4">
                <v-btn block color="primary" variant="tonal" @click="handleAction('episode_deleter')" :loading="loading">
                  执行修复重置
                </v-btn>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-col>

      <!-- 右侧：说明区 -->
      <v-col cols="12" md="5">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-help-circle-outline</v-icon>
            工具说明
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p class="mb-2"><strong>演职员清空：</strong></p>
            <p class="mb-3">主要用于清理因刮削器错误导致的冗余演职员列表，清空后建议在 Emby 中重新识别。</p>
            <p class="mb-2"><strong>集类型重置：</strong></p>
            <p>修复某些剧集的"单集"被错误打上"剧集类型"标签的问题。</p>
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-lightbulb-outline</v-icon>
            操作技巧
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p>建议搭配"实时日志"使用。在执行大规模清理前，请务必确认"目标媒体库"选择正确。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
