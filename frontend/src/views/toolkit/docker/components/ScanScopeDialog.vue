<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import { useDockerHost } from '../composables/useDockerHost'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()
const { currentHost, fetchHosts } = useDockerHost()

const showDialog = defineModel<boolean>({ default: false })
const newPath = ref('')
const saving = ref(false)

const scanPaths = computed(() =>
  (currentHost.value?.compose_scan_paths || '').split(',').map((p: string) => p.trim()).filter(Boolean)
)

watch(showDialog, (val) => { if (val) newPath.value = '' })

async function persistPaths(paths: string[]) {
  if (!currentHost.value) return
  saving.value = true
  try {
    currentHost.value.compose_scan_paths = paths.join(',')
    await dockerApi.updateHost(currentHost.value.id, currentHost.value)
    await fetchHosts()
    return true
  } catch (err: any) {
    showError(err?.message || '保存失败')
    await fetchHosts()
    return false
  } finally { saving.value = false }
}

async function addPath() {
  const path = newPath.value.trim()
  if (!path) return
  if (scanPaths.value.includes(path)) { showError('该路径已存在'); return }
  if (await persistPaths([...scanPaths.value, path])) { success('扫描路径已添加'); newPath.value = '' }
}

async function removePath(path: string) {
  const ok = await confirm({ title: '删除扫描路径', content: `确定不再扫描 ${path} 吗？删除后需重新扫描才能发现该路径下的项目。`, confirmColor: 'error' })
  if (!ok) return
  if (await persistPaths(scanPaths.value.filter(p => p !== path))) success('扫描路径已删除')
}
</script>

<template>
  <GlassDialog v-model="showDialog" :max-width="520" icon="mdi-folder-multiple-outline" title="Compose 扫描范围" cancel-text="关闭">
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      仅扫描以下路径下的 Docker Compose 项目；未配置时将只探测运行中的项目。
    </v-alert>

    <div class="d-flex align-center ga-2 mb-4">
      <v-text-field
        v-model="newPath"
        label="添加扫描路径"
        variant="outlined"
        density="compact"
        placeholder="/vol1/docker/projects"
        hide-details
        class="flex-grow-1"
        @keyup.enter="addPath"
      />
      <v-btn color="primary" variant="flat" prepend-icon="mdi-plus" :disabled="!newPath.trim()" @click="addPath">添加</v-btn>
    </div>

    <div v-if="scanPaths.length" class="d-flex flex-column ga-2">
      <v-card v-for="path in scanPaths" :key="path" rounded="lg" variant="tonal" class="list-card pa-3">
        <div class="d-flex align-center justify-space-between w-100">
          <span class="text-body-2 text-break">{{ path }}</span>
          <v-btn icon="mdi-close" size="x-small" variant="text" color="error" :loading="saving" @click="removePath(path)" />
        </div>
      </v-card>
    </div>
    <div v-else class="text-center text-caption text-medium-emphasis py-4">
      暂未配置扫描路径
    </div>
  </GlassDialog>
</template>
