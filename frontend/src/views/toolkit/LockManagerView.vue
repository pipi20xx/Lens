<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { serverApi } from '@/api/server'
import { useNotification } from '@/composables'

const { success, error: showError, warning } = useNotification()

const loading = ref(false)
const libOptions = ref<any[]>([])

const savedCommon = localStorage.getItem('lens_lock_common')
const common = reactive(savedCommon ? JSON.parse(savedCommon) : {
  lib_names: [] as string[],
  dry_run: true
})

watch(common, (val) => {
  localStorage.setItem('lens_lock_common', JSON.stringify(val))
}, { deep: true })

const selectedTypes = ref(['Movie', 'Series', 'Season', 'Episode'])

async function fetchLibraries() {
  try {
    const data = await serverApi.getLibraries()
    libOptions.value = Array.isArray(data) ? data : []
  } catch { /* ignore */ }
}

onMounted(fetchLibraries)

async function handleAction(endpoint: string) {
  if (common.lib_names.length === 0) {
    warning('请选择媒体库')
    return
  }
  loading.value = true
  try {
    const payload = {
      ...common,
      item_types: selectedTypes.value
    }
    const res = await toolkitApi.executeAction(endpoint, payload)
    success(`任务完成: ${res?.message ?? '完成'} (处理数: ${res?.processed_count ?? 0})`)
  } catch {
    showError('接口请求失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-lock-outline</v-icon>
      元数据锁定器
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">严格区分 Emby 的"主锁 (LockData)"与"小锁 (LockedFields)"维度的操作逻辑。</p>

    <v-row>
      <!-- 左侧：主要操作区 -->
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
            <v-switch v-model="common.dry_run" color="primary" density="compact" hide-details class="mb-3">
              <template #label>
                <span class="text-body-2">执行模式：</span>
                <v-chip size="small" :color="common.dry_run ? 'info' : 'error'" variant="tonal" class="ml-2">
                  {{ common.dry_run ? '预览模式' : '实调模式' }}
                </v-chip>
              </template>
            </v-switch>
            <div class="d-flex ga-3 flex-wrap">
              <v-checkbox v-model="selectedTypes" value="Movie" label="电影" density="compact" hide-details />
              <v-checkbox v-model="selectedTypes" value="Series" label="剧集 (Series)" density="compact" hide-details />
              <v-checkbox v-model="selectedTypes" value="Season" label="季 (Season)" density="compact" hide-details />
              <v-checkbox v-model="selectedTypes" value="Episode" label="集 (Episode)" density="compact" hide-details />
            </div>
          </v-card-text>
        </v-card>

        <!-- 功能工具区 -->
        <v-row>
          <!-- 元数据字段全解锁 -->
          <v-col cols="12" sm="4">
            <v-card class="liquid-glass-card" rounded="xl" style="height:100%;display:flex;flex-direction:column" color="error">
              <v-card-title class="pa-4 text-subtitle-2">
                <v-icon start size="18">mdi-lock-open-variant-outline</v-icon>
                元数据字段全解锁
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <p class="text-caption text-medium-emphasis">
                  <strong>[深度释放]</strong><br />
                  逻辑：清空 LockedFields 列表 (小锁) <strong>并</strong> 设置 LockData = false (主锁)。
                </p>
              </v-card-text>
              <v-divider />
              <div class="pa-4">
                <v-btn block color="error" variant="tonal" @click="handleAction('metadata_field_unlocker')" :loading="loading">
                  执行字段解锁
                </v-btn>
              </div>
            </v-card>
          </v-col>

          <!-- 项目整体锁定 -->
          <v-col cols="12" sm="4">
            <v-card class="liquid-glass-card" rounded="xl" style="height:100%;display:flex;flex-direction:column" color="info">
              <v-card-title class="pa-4 text-subtitle-2">
                <v-icon start size="18">mdi-lock-outline</v-icon>
                项目整体锁定
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <p class="text-caption text-medium-emphasis">
                  <strong>[主锁保护]</strong><br />
                  逻辑：仅设置 LockData = true。保护整体元数据，但不修改各字段锁定状态。
                </p>
              </v-card-text>
              <v-divider />
              <div class="pa-4">
                <v-btn block color="info" variant="tonal" @click="handleAction('item_locker')" :loading="loading">
                  执行全局锁定
                </v-btn>
              </div>
            </v-card>
          </v-col>

          <!-- 项目深度全解锁 -->
          <v-col cols="12" sm="4">
            <v-card class="liquid-glass-card" rounded="xl" style="height:100%;display:flex;flex-direction:column" color="success">
              <v-card-title class="pa-4 text-subtitle-2">
                <v-icon start size="18">mdi-lock-open-outline</v-icon>
                项目深度全解锁
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4 flex-grow-1">
                <p class="text-caption text-medium-emphasis">
                  <strong>[彻底释放]</strong><br />
                  逻辑：主锁、小锁一起解除 (LockData=false + 列表清空)。
                </p>
              </v-card-text>
              <v-divider />
              <div class="pa-4">
                <v-btn block color="success" variant="tonal" @click="handleAction('item_unlocker')" :loading="loading">
                  执行深度解锁
                </v-btn>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-col>

      <!-- 右侧：辅助信息区 -->
      <v-col cols="12" md="5">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-help-circle-outline</v-icon>
            概念区分
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p class="mb-2"><strong>主锁 (LockData):</strong></p>
            <p class="mb-3">Emby 控制面板中"将此项目锁定以防意外更改"的总开关。</p>
            <p class="mb-2"><strong>小锁 (LockedFields):</strong></p>
            <p>各具体字段（标题、简介、海报等）的细粒度锁定列表。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
