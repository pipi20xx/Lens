<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { embyTasksApi } from '@/api/embyTasks'
import { useNotification } from '@/composables'

const { success, error: showError } = useNotification()
const tasks = ref<any[]>([])
const loading = ref(true)

async function loadTasks() {
  try {
    loading.value = true
    const res = await embyTasksApi.getTasks()
    tasks.value = Array.isArray(res) ? res : []
  } catch { showError('加载任务列表失败') }
  finally { loading.value = false }
}

async function runTask(id: string) {
  try {
    await embyTasksApi.runTask(id)
    success('任务已触发')
  } catch { showError('触发任务失败') }
}

onMounted(loadTasks)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-6">
      <v-icon start>mdi-clock-outline</v-icon>
      Emby 定时任务
    </h1>
    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <span>任务列表</span>
        <v-spacer />
        <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" @click="loadTasks" :loading="loading">刷新</v-btn>
      </v-card-title>
      <v-divider />
      <v-table class="bg-transparent">
        <thead><tr><th>任务名称</th><th>状态</th><th class="text-right">操作</th></tr></thead>
        <tbody>
          <tr v-if="loading"><td colspan="3" class="text-center py-8"><v-progress-circular indeterminate color="primary" /></td></tr>
          <tr v-else-if="!tasks.length"><td colspan="3" class="text-center py-8 text-medium-emphasis">暂无数据</td></tr>
          <tr v-for="task in tasks" :key="task.Id">
            <td class="font-weight-medium">{{ task.Name }}</td>
            <td><v-chip size="small" variant="tonal" label>{{ task.State || '-' }}</v-chip></td>
            <td class="text-right"><v-btn prepend-icon="mdi-play" variant="tonal" size="small" @click="runTask(task.Id)">执行</v-btn></td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>
</template>
