<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { terminalApi } from '@/api/terminal'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'
import SecretField from '@/components/common/SecretField.vue'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const props = defineProps<{ activeHostId: number | string }>()
const emit = defineEmits<{ select: [host: any] }>()

const hosts = ref<any[]>([])
const showHostDialog = ref(false)
const editingId = ref<number | null>(null)
const hostForm = ref({
  name: '',
  host: '',
  port: 22,
  username: 'root',
  auth_type: 'password',
  password: '',
  private_key: '',
  private_key_password: '',
})

async function fetchHosts() {
  try {
    const data = await terminalApi.getHosts()
    hosts.value = Array.isArray(data) ? data : []
  } catch {
    showError('加载主机列表失败')
  }
}

function handleSelect(host: any) {
  emit('select', { ...host })
}

function openAddDialog() {
  editingId.value = null
  hostForm.value = {
    name: '',
    host: '',
    port: 22,
    username: 'root',
    auth_type: 'password',
    password: '',
    private_key: '',
    private_key_password: '',
  }
  showHostDialog.value = true
}

function openEditDialog(host: any) {
  editingId.value = host.id
  hostForm.value = {
    name: host.name || '',
    host: host.host || '',
    port: host.port || 22,
    username: host.username || 'root',
    auth_type: host.auth_type || 'password',
    password: host.password || '',
    private_key: host.private_key || '',
    private_key_password: host.private_key_password || '',
  }
  showHostDialog.value = true
}

async function saveHost() {
  try {
    if (editingId.value) {
      await terminalApi.updateHost(editingId.value, hostForm.value)
      success('主机已更新')
    } else {
      await terminalApi.createHost(hostForm.value)
      success('主机已添加')
    }
    showHostDialog.value = false
    fetchHosts()
  } catch {
    showError('保存主机失败')
  }
}

async function deleteHost(id: number) {
  const ok = await confirm({ title: '删除主机', content: '确定要删除此主机吗？此操作不可撤销。', confirmColor: 'error' })
  if (!ok) return
  try {
    await terminalApi.deleteHost(id)
    success('主机已删除')
    fetchHosts()
  } catch {
    showError('删除主机失败')
  }
}

onMounted(fetchHosts)
defineExpose({ fetchHosts })
</script>

<template>
  <div class="host-panel">
    <div class="panel-header d-flex align-center justify-space-between px-4 py-3">
      <span class="text-subtitle-2 font-weight-bold">主机列表</span>
      <v-btn icon="mdi-plus" variant="text" size="small" density="compact" @click="openAddDialog" />
    </div>
    <v-divider />

    <div class="host-list px-2 py-2">
      <!-- 本地 Shell -->
      <div
        class="host-item d-flex align-center px-3 py-2 mb-1 rounded-lg cursor-pointer"
        :class="{ 'active': activeHostId === 0 }"
        @click="handleSelect({ id: 0, name: '本地 Shell' })"
      >
        <v-icon size="18" class="mr-3">mdi-monitor</v-icon>
        <span class="text-body-2" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">本地 Shell</span>
      </div>

      <!-- 远程主机 -->
      <div
        v-for="h in hosts"
        :key="h.id"
        class="host-item d-flex align-center px-3 py-2 mb-1 rounded-lg cursor-pointer"
        :class="{ 'active': activeHostId === h.id }"
        @click="handleSelect(h)"
      >
        <v-icon size="18" class="mr-3">mdi-server</v-icon>
        <span class="text-body-2 flex-grow-1" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap" :title="h.host">{{ h.name }}</span>
        <div class="host-actions d-flex ga-1">
          <v-btn icon="mdi-pencil-outline" variant="text" size="x-small" density="compact" @click.stop="openEditDialog(h)" />
          <v-btn icon="mdi-delete-outline" variant="text" size="x-small" density="compact" color="error" @click.stop="deleteHost(h.id)" />
        </div>
      </div>
    </div>

    <!-- 主机配置弹窗 -->
    <GlassDialog v-model="showHostDialog" :max-width="480"
      icon="mdi-server" :title="editingId ? '编辑主机' : '新增主机'"
    >
      <v-text-field v-model="hostForm.name" label="名称" variant="outlined" density="compact" placeholder="例如：我的服务器" class="mb-3" />
      <div class="d-flex ga-2 mb-3">
        <v-text-field v-model="hostForm.host" label="连接地址" variant="outlined" density="compact" placeholder="IP/域名" class="flex-grow-1" />
        <v-text-field v-model="hostForm.port" label="端口" type="number" variant="outlined" density="compact" style="max-width:100px" />
      </div>
      <v-text-field v-model="hostForm.username" label="登录用户" variant="outlined" density="compact" placeholder="root" class="mb-3" />
      <v-select
        v-model="hostForm.auth_type"
        :items="[{ title: '密码认证', value: 'password' }, { title: '密钥认证', value: 'key' }]"
        label="认证方式" variant="outlined" density="compact" class="mb-3"
      />
      <template v-if="hostForm.auth_type === 'password'">
        <SecretField v-model="hostForm.password" label="登录密码" :show-copy="false" class="mb-3" />
      </template>
      <template v-else>
        <v-textarea v-model="hostForm.private_key" label="私钥内容" variant="outlined" density="compact" rows="3" placeholder="-----BEGIN RSA PRIVATE KEY-----" class="mb-3" />
        <SecretField v-model="hostForm.private_key_password" label="私钥密码" :show-copy="false" placeholder="可选，若私钥已加密请填写" class="mb-3" />
      </template>

      <template #actions>
        <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveHost">保存配置</v-btn>
      </template>
    </GlassDialog>
  </div>
</template>

<style scoped>
.host-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.host-item {
  transition: background 0.2s, color 0.2s;
}
.host-item:hover {
  background: rgba(255, 255, 255, 0.05);
}
.host-item.active {
  background: rgb(var(--v-theme-primary));
  color: #fff;
}
.host-item.active :deep(.v-icon) {
  color: #fff;
}
.host-actions {
  opacity: 0;
  transition: opacity 0.2s;
}
.host-item:hover .host-actions {
  opacity: 1;
}
.host-item.active .host-actions {
  opacity: 1;
}
</style>
