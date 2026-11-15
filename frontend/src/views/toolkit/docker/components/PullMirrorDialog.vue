<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()

const showDialog = defineModel<boolean>({ default: false })
const saving = ref(false)
const enabled = ref(true)
const mirrorsText = ref('')

const mirrors = computed(() =>
  mirrorsText.value
    .split('\n')
    .map((m) => m.trim())
    .filter((m) => m && !m.startsWith('#'))
)

async function loadSettings() {
  try {
    const data: any = await dockerApi.getPullMirrorSettings()
    enabled.value = data?.enabled ?? true
    mirrorsText.value = (data?.mirrors || []).join('\n')
  } catch { /* ignore */ }
}

async function saveSettings() {
  saving.value = true
  try {
    await dockerApi.savePullMirrorSettings({ enabled: enabled.value, mirrors: mirrors.value })
    success('拉取加速源设置已保存')
    showDialog.value = false
  } catch { showError('保存失败') }
  finally { saving.value = false }
}

watch(showDialog, (val) => { if (val) loadSettings() })
</script>

<template>
  <GlassDialog v-model="showDialog" :max-width="520" icon="mdi-rocket-launch-outline" title="拉取镜像加速源">
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      点击「更新」时可在弹窗中临时选择下方加速源；仅对 Docker Hub 镜像生效（如 nginx、pipi20xx/lens），ghcr.io / lscr.io 等第三方仓库不受影响。
    </v-alert>
    <v-switch v-model="enabled" label="启用加速源选项" density="compact" color="primary" class="mb-3" />
    <v-textarea
      v-model="mirrorsText"
      label="加速源地址（每行一个）"
      placeholder="docker.m.daocloud.io&#10;docker.1panel.live&#10;docker.fnnas.com&#10;dockerproxy.net"
      variant="outlined"
      density="compact"
      rows="5"
      hint="可带 https:// 前缀（会自动去除），# 开头视为注释"
      persistent-hint
    />
    <template #actions>
      <v-btn color="primary" variant="tonal" prepend-icon="mdi-content-save-outline" @click="saveSettings" :loading="saving">保存</v-btn>
    </template>
  </GlassDialog>
</template>
