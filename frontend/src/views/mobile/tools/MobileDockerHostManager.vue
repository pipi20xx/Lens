<template>
  <n-modal :show="show" @update:show="emit('update:show', $event)" preset="card" title="主机管理" style="width: 90vw; max-width: 600px">
    <div class="mobile-docker-host-manager">
      <n-space vertical>
        <n-button type="primary" size="small" @click="handleAddHost">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          添加主机
        </n-button>

        <div v-if="hosts.length === 0" class="empty-state">
          <n-empty description="暂无主机" size="small" />
        </div>

        <div v-else class="host-list">
          <div v-for="host in hosts" :key="host.id" class="host-item">
            <div class="host-header">
              <div class="host-name">
                <n-text strong>{{ host.name }}</n-text>
                <n-tag size="tiny" type="warning">SSH</n-tag>
                <n-tag v-if="host.is_local" size="tiny" type="success">宿主机</n-tag>
              </div>
              <n-space>
                <n-button size="tiny" secondary @click="testConnection(host.id)" :loading="testingId === host.id">
                  <template #icon><n-icon><TestIcon /></n-icon></template>
                  测试
                </n-button>
                <n-button size="tiny" secondary @click="handleEditHost(host)">
                  <template #icon><n-icon><EditIcon /></n-icon></template>
                  编辑
                </n-button>
                <n-popconfirm @positive-click="() => deleteHost(host.id)" positive-text="确认" negative-text="取消">
                  <template #trigger>
                    <n-button size="tiny" secondary type="error">
                      <template #icon><n-icon><DeleteIcon /></n-icon></template>
                    </n-button>
                  </template>
                  确认删除？
                </n-popconfirm>
              </n-space>
            </div>

            <div class="host-info">
              <div class="info-row">
                <n-icon size="14"><ServerIcon /></n-icon>
                <span>{{ host.ssh_host }}:{{ host.ssh_port }}</span>
              </div>
              <div class="info-row">
                <n-icon size="14"><UserIcon /></n-icon>
                <span>{{ host.ssh_user }}</span>
              </div>
              <div v-if="host.compose_scan_paths" class="info-row">
                <n-icon size="14"><FolderIcon /></n-icon>
                <span>{{ host.compose_scan_paths }}</span>
              </div>
            </div>
          </div>
        </div>
      </n-space>
    </div>

    <n-modal v-model:show="showEditModal" preset="card" :title="editHostForm.id ? '编辑主机' : '添加主机'" style="width: 90vw; max-width: 500px">
      <n-form label-placement="top" size="small">
        <n-form-item label="名称" required>
          <n-input v-model:value="editHostForm.name" placeholder="例如: 生产服务器" />
        </n-form-item>
        <n-form-item label="SSH 地址" required>
          <n-input v-model:value="editHostForm.ssh_host" placeholder="127.0.0.1" />
        </n-form-item>
        <n-form-item label="SSH 端口" required>
          <n-input-number v-model:value="editHostForm.ssh_port" :min="1" :max="65535" style="width: 100%" />
        </n-form-item>
        <n-form-item label="SSH 用户" required>
          <n-input v-model:value="editHostForm.ssh_user" placeholder="root" />
        </n-form-item>
        <n-form-item label="SSH 密码" required>
          <n-input v-model:value="editHostForm.ssh_pass" type="password" show-password-on="click" />
        </n-form-item>
        <n-form-item label="宿主机标记">
          <n-space align="center">
            <n-switch v-model:value="editHostForm.is_local" class="mobile-switch" />
            <n-text depth="3" style="font-size: 12px">标记为此 Lens 容器所在的物理宿主机</n-text>
          </n-space>
        </n-form-item>
        <n-form-item label="扫描路径">
          <n-input 
            v-model:value="editHostForm.compose_scan_paths" 
            type="textarea" 
            placeholder="逗号分隔，例如: /opt/docker-compose,/root/projects"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showEditModal = false">取消</n-button>
          <n-button type="primary" @click="saveHost" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </n-modal>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { 
  NSpace, NButton, NTag, NIcon, NText, NModal, NForm, NFormItem, 
  NInput, NInputNumber, NSwitch, NEmpty, NPopconfirm, useMessage 
} from 'naive-ui'
import {
  AddOutlined as AddIcon,
  SensorsOutlined as TestIcon,
  EditOutlined as EditIcon,
  DeleteOutlined as DeleteIcon,
  DnsOutlined as ServerIcon,
  PersonOutlined as UserIcon,
  FolderOutlined as FolderIcon
} from '@vicons/material'
import axios from 'axios'

const props = defineProps<{
  hosts: any[]
  show: boolean
}>()

const emit = defineEmits(['refresh', 'update:show'])

const message = useMessage()
const showEditModal = ref(false)
const editHostForm = ref<any>({})
const testingId = ref('')
const saving = ref(false)

const handleAddHost = () => { 
  editHostForm.value = { 
    type: 'ssh', 
    ssh_port: 22, 
    ssh_user: 'root',
    compose_scan_paths: ''
  }; 
  showEditModal.value = true 
}

const handleEditHost = (h: any) => { 
  editHostForm.value = { ...h }; 
  showEditModal.value = true 
}

const saveHost = async () => {
  if (!editHostForm.value.name || !editHostForm.value.ssh_host || !editHostForm.value.ssh_user || !editHostForm.value.ssh_pass) {
    message.warning('请填写完整的主机信息')
    return
  }
  saving.value = true
  try {
    if (editHostForm.value.id) {
      await axios.put(`/api/docker/hosts/${editHostForm.value.id}`, editHostForm.value)
      message.success('主机配置已更新')
    } else {
      await axios.post('/api/docker/hosts', editHostForm.value)
      message.success('新主机已添加')
    }
    showEditModal.value = false
    emit('refresh')
  } catch (e: any) {
    message.error('保存失败: ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    saving.value = false
  }
}

const deleteHost = async (id: string) => {
  try {
    await axios.delete(`/api/docker/hosts/${id}`)
    message.success('主机已删除')
    emit('refresh')
  } catch (e: any) {
    message.error('删除失败: ' + (e.response?.data?.detail || '未知错误'))
  }
}

const testConnection = async (id: string) => {
  testingId.value = id
  try {
    const res = await axios.post(`/api/docker/${id}/test`)
    if (res.data.status === 'ok') {
      message.success('连接正常')
    } else {
      message.error('连接失败')
    }
  } catch (e: any) {
    message.error('测试失败: ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    testingId.value = ''
  }
}
</script>

<style scoped>
.mobile-docker-host-manager {
  padding: 12px 0;
}

.empty-state {
  padding: 40px 0;
}

.host-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.host-item {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
}

.host-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.host-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 500;
}

.host-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.7;
}
</style>
