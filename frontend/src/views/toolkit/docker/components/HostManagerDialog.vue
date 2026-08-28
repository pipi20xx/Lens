<script setup lang="ts">
import { ref } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import { useDockerHost } from '../composables/useDockerHost'
import GlassDialog from '@/components/common/GlassDialog.vue'
import SecretField from '@/components/common/SecretField.vue'

const { success, error: showError, info } = useNotification()
const { confirm } = useConfirm()
const { hosts, fetchHosts, currentHost } = useDockerHost()

const showHostManagerDialog = defineModel<boolean>({ default: false })
const showHostEditDialog = ref(false)
const hostForm = ref({ name: '', type: 'ssh', ssh_host: '', ssh_port: 22, ssh_user: 'root', ssh_pass: '', is_local: false, compose_scan_paths: '' })
const editingHostId = ref<string | null>(null)

function openAddHost() {
  editingHostId.value = null
  hostForm.value = { name: '', type: 'ssh', ssh_host: '', ssh_port: 22, ssh_user: 'root', ssh_pass: '', is_local: false, compose_scan_paths: '' }
  showHostEditDialog.value = true
}

function openEditHost(host: any) {
  editingHostId.value = host.id
  hostForm.value = { ...host }
  showHostEditDialog.value = true
}

async function saveHost() {
  try {
    if (editingHostId.value) { await dockerApi.updateHost(editingHostId.value, hostForm.value); success('主机已更新') }
    else { await dockerApi.addHost(hostForm.value); success('主机已添加') }
    showHostEditDialog.value = false
    fetchHosts()
  } catch (err: any) { showError(err.message || '保存失败') }
}

async function deleteHost(id: string) {
  const ok = await confirm({ title: '删除主机', content: '确定要删除此主机吗？', confirmColor: 'error' })
  if (!ok) return
  try { await dockerApi.deleteHost(id); success('主机已删除'); fetchHosts() } catch { showError('删除失败') }
}

async function testConnection(hostId: string) {
  try { const res = await dockerApi.testConnection(hostId); info(res?.status === 'ok' ? '连接正常' : '连接失败') }
  catch { showError('连接失败') }
}

function removeScanPath(path: string) {
  if (!currentHost.value) return
  const paths = (currentHost.value.compose_scan_paths || '').split(',').map((i: string) => i.trim()).filter((i: string) => i && i !== path)
  currentHost.value.compose_scan_paths = paths.join(',')
  dockerApi.updateHost(currentHost.value.id, currentHost.value)
  fetchHosts()
}
</script>

<template>
  <!-- 主机管理列表对话框 -->
  <GlassDialog v-model="showHostManagerDialog" :max-width="700" icon="mdi-server" title="Docker 主机管理" cancel-text="关闭">
    <v-btn prepend-icon="mdi-plus" color="primary" variant="tonal" block @click="openAddHost" class="mb-4">添加新主机</v-btn>
    <div v-if="hosts.length" class="d-flex flex-column ga-2">
      <v-card v-for="host in hosts" :key="host.id" rounded="lg" variant="tonal" class="list-card pa-3">
        <div class="d-flex align-center justify-space-between w-100">
          <div class="d-flex align-center ga-2">
            <span class="font-weight-bold">{{ host.name }}</span>
            <v-chip size="x-small" variant="tonal" color="warning">SSH 远程</v-chip>
            <v-chip v-if="host.is_local" size="x-small" variant="tonal" color="success">宿主机</v-chip>
          </div>
          <div class="d-flex ga-1">
            <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-lan-connect" @click="testConnection(host.id)">测试</v-btn>
            <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="openEditHost(host)">编辑</v-btn>
            <v-btn size="small" variant="tonal" color="error" prepend-icon="mdi-delete-outline" @click="deleteHost(host.id)">删除</v-btn>
          </div>
        </div>
      </v-card>
    </div>

  </GlassDialog>

  <!-- 添加/编辑主机对话框 -->
  <GlassDialog v-model="showHostEditDialog" :max-width="520" icon="mdi-server"
    :title="editingHostId ? '编辑主机' : '添加主机'"
  >
    <v-text-field v-model="hostForm.name" label="主机名称" variant="outlined" density="compact" class="mb-3" />
    <v-select v-model="hostForm.type" :items="[{title: '远程 Docker (SSH)', value: 'ssh'}]" label="连接类型" variant="outlined" density="compact" class="mb-3" />
    <v-text-field v-model="hostForm.ssh_host" label="SSH 地址" variant="outlined" density="compact" placeholder="127.0.0.1" class="mb-3" />
    <v-text-field v-model="hostForm.ssh_port" label="SSH 端口" type="number" variant="outlined" density="compact" class="mb-3" />
    <v-text-field v-model="hostForm.ssh_user" label="SSH 用户名" variant="outlined" density="compact" class="mb-3" />
    <SecretField v-model="hostForm.ssh_pass" label="SSH 密码" :show-copy="false" class="mb-3" />
    <v-switch v-model="hostForm.is_local" label="标记为宿主机" density="compact" color="primary" hint="标记为此 Lens 容器所在的物理宿主机" persistent-hint class="mb-3" />
    <v-textarea v-model="hostForm.compose_scan_paths" label="Compose 扫描路径" variant="outlined" density="compact" hint="逗号分隔多个路径" persistent-hint rows="2" auto-grow />

    <template #actions>
      <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveHost">保存</v-btn>
    </template>
  </GlassDialog>
</template>
