<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { embyLibrariesApi } from '@/api/embyLibraries'
import { useNotification } from '@/composables'

const { error: showError } = useNotification()
const libraries = ref<any[]>([])
const loading = ref(true)

async function loadLibraries() {
  try {
    loading.value = true
    const res = await embyLibrariesApi.getLibraries()
    libraries.value = Array.isArray(res) ? res : []
  } catch (err: any) {
    showError('加载媒体库列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadLibraries)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-6">
      <v-icon start>mdi-folder-multiple-outline</v-icon>
      Emby 媒体库管理
    </h1>

    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <span>媒体库列表</span>
        <v-spacer />
        <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" @click="loadLibraries" :loading="loading">
          刷新
        </v-btn>
      </v-card-title>
      <v-divider />
      <v-table class="bg-transparent">
        <thead>
          <tr><th>名称</th><th>类型</th><th class="text-right">操作</th></tr>
        </thead>
        <tbody>
          <tr v-if="loading"><td colspan="3" class="text-center py-8"><v-progress-circular indeterminate color="primary" /></td></tr>
          <tr v-else-if="!libraries.length"><td colspan="3" class="text-center py-8 text-medium-emphasis">暂无数据</td></tr>
          <tr v-for="lib in libraries" :key="lib.ItemId">
            <td class="font-weight-medium">{{ lib.Name }}</td>
            <td class="text-medium-emphasis">{{ lib.Type }}</td>
            <td class="text-right">
              <v-btn icon="mdi-refresh" variant="text" size="small" @click="embyLibrariesApi.refreshLibrary(lib.ItemId)" />
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>
</template>
