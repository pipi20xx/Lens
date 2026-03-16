<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NIcon, NPopconfirm, useMessage
} from 'naive-ui'
import {
  AddOutlined as AddIcon,
  TerminalOutlined as TerminalIcon,
  EditOutlined as EditIcon,
  DeleteOutlineOutlined as DeleteIcon
} from '@vicons/material'
import { terminalApi } from '@/api/terminal'

const message = useMessage()

// 主机列表
const hosts = ref<any[]>([])
const commands = ref<any[]>([])
const showAddHostModal = ref(false)
const showAddCommandModal = ref(false)
const saving = ref(false)

const newHost = ref({
  id: undefined as number | undefined,
  name: '',
  host: '',
  port: 22,
  username: '',
  auth_type: 'password',
  password: ''
})

const authTypeOptions = [
  { label: '密码认证', value: 'password' },
  { label: 'SSH 密钥', value: 'key' }
]

const loadHosts = async () => {
  try {
    const res = await terminalApi.getHosts()
    hosts.value = res as any || []
  } catch (e) {
    message.error('加载主机列表失败')
  }
}

const saveHost = async () => {
  if (!newHost.value.name || !newHost.value.host) {
    message.warning('请填写完整的主机信息')
    return
  }
  saving.value = true
  try {
    if (newHost.value.id) {
      await terminalApi.updateHost(newHost.value.id, newHost.value)
      message.success('主机更新成功')
    } else {
      await terminalApi.createHost(newHost.value)
      message.success('主机添加成功')
    }
    showAddHostModal.value = false
    newHost.value = { id: undefined, name: '', host: '', port: 22, username: '', auth_type: 'password', password: '' }
    await loadHosts()
  } catch (e) {
    message.error(newHost.value.id ? '更新主机失败' : '添加主机失败')
  } finally {
    saving.value = false
  }
}

const deleteHost = async (id: number) => {
  try {
    await terminalApi.deleteHost(id)
    message.success('主机已删除')
    await loadHosts()
  } catch (e) {
    message.error('删除主机失败')
  }
}

const editHost = (host: any) => {
  newHost.value = { ...host }
  showAddHostModal.value = true
}

const connectHost = (host: any) => {
  message.info('终端连接功能请在桌面端使用')
}

// 快速命令
const loadCommands = async () => {
  try {
    const res = await terminalApi.getCommands()
    commands.value = res as any || []
  } catch (e) {
    message.error('加载命令列表失败')
  }
}

const editingCommand = ref<any>(null)
const newCommand = ref({
  title: '',
  command: ''
})
const savingCommand = ref(false)

const saveCommand = async () => {
  if (!newCommand.value.title || !newCommand.value.command) {
    message.warning('请填写完整的命令信息')
    return
  }
  savingCommand.value = true
  try {
    if (editingCommand.value) {
      await terminalApi.saveCommand({ ...newCommand.value, id: editingCommand.value.id })
    } else {
      await terminalApi.saveCommand(newCommand.value)
    }
    message.success(editingCommand.value ? '命令更新成功' : '命令添加成功')
    showAddCommandModal.value = false
    newCommand.value = { title: '', command: '' }
    editingCommand.value = null
    await loadCommands()
  } catch (e) {
    message.error('保存命令失败')
  } finally {
    savingCommand.value = false
  }
}

const editCommand = (cmd: any) => {
  editingCommand.value = cmd
  newCommand.value = { title: cmd.title, command: cmd.command }
  showAddCommandModal.value = true
}

const deleteCommand = async (id: number) => {
  try {
    await terminalApi.deleteCommand(id)
    message.success('命令已删除')
    await loadCommands()
  } catch (e) {
    message.error('删除命令失败')
  }
}

const sendCommand = (cmd: any) => {
  message.info('命令执行功能请在桌面端使用')
}

onMounted(() => {
  loadHosts()
  loadCommands()
})
</script>

<template>
  <div class="mobile-terminal-manager">
    <div class="page-header">
      <h1 class="page-title">终端管理</h1>
      <p class="page-desc">管理远程终端主机与连接会话</p>
    </div>

    <n-card class="hosts-card" :bordered="false" title="主机列表">
      <n-space vertical>
        <n-button block type="primary" @click="showAddHostModal = true">
          <template #icon>
            <n-icon><AddIcon /></n-icon>
          </template>
          添加主机
        </n-button>
        <div v-if="hosts.length === 0" class="empty-state">
          <n-empty description="暂无主机配置" />
        </div>
        <div v-else class="host-list">
          <div v-for="host in hosts" :key="host.id" class="host-item">
            <div class="host-info">
              <div class="host-name">{{ host.name }}</div>
              <div class="host-detail">{{ host.username }}@{{ host.host }}:{{ host.port }}</div>
            </div>
            <div class="host-actions">
              <n-button size="small" secondary type="info" @click="connectHost(host)">
                <template #icon>
                  <n-icon><TerminalIcon /></n-icon>
                </template>
                连接
              </n-button>
              <n-button size="small" secondary type="warning" @click="editHost(host)">
                <template #icon>
                  <n-icon><EditIcon /></n-icon>
                </template>
                编辑
              </n-button>
              <n-popconfirm @positive-click="deleteHost(host.id)" positive-text="确认删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    <template #icon>
                      <n-icon><DeleteIcon /></n-icon>
                    </template>
                    删除
                  </n-button>
                </template>
                确定删除主机 {{ host.name }}？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-card class="commands-card" :bordered="false" title="快速命令">
      <n-space vertical>
        <n-button block type="primary" secondary @click="showAddCommandModal = true; editingCommand = null; newCommand = { title: '', command: '' }">
          <template #icon>
            <n-icon><AddIcon /></n-icon>
          </template>
          添加命令
        </n-button>
        <div v-if="commands.length === 0" class="empty-state">
          <n-empty description="暂无快速命令" />
        </div>
        <div v-else class="command-list">
          <div v-for="cmd in commands" :key="cmd.id" class="command-item">
            <div class="command-info" @click="sendCommand(cmd)">
              <div class="command-name">{{ cmd.title }}</div>
              <div class="command-preview">{{ cmd.command }}</div>
            </div>
            <div class="command-actions">
              <n-button size="small" secondary type="warning" @click="editCommand(cmd)">
                <template #icon>
                  <n-icon><EditIcon /></n-icon>
                </template>
              </n-button>
              <n-popconfirm @positive-click="deleteCommand(cmd.id)" positive-text="确认删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    <template #icon>
                      <n-icon><DeleteIcon /></n-icon>
                    </template>
                  </n-button>
                </template>
                确定删除此命令？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddHostModal" preset="card" :title="newHost.id ? '编辑主机' : '添加主机'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="名称">
          <n-input v-model:value="newHost.name" placeholder="主机名称" />
        </n-form-item>
        <n-form-item label="主机地址">
          <n-input v-model:value="newHost.host" placeholder="192.168.1.1" />
        </n-form-item>
        <n-form-item label="端口">
          <n-input-number v-model:value="newHost.port" placeholder="22" />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input v-model:value="newHost.username" placeholder="root" />
        </n-form-item>
        <n-form-item label="认证方式">
          <n-select v-model:value="newHost.auth_type" :options="authTypeOptions" />
        </n-form-item>
        <n-form-item v-if="newHost.auth_type === 'password'" label="密码">
          <n-input v-model:value="newHost.password" type="password" show-password-on="click" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddHostModal = false">取消</n-button>
          <n-button type="primary" @click="saveHost" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showAddCommandModal" preset="card" :title="editingCommand ? '编辑命令' : '添加命令'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="命令名称">
          <n-input v-model:value="newCommand.title" placeholder="例如：查看日志" />
        </n-form-item>
        <n-form-item label="命令内容">
          <n-input v-model:value="newCommand.command" type="textarea" :rows="3" placeholder="例如：tail -f /var/log/syslog" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddCommandModal = false">取消</n-button>
          <n-button type="primary" @click="saveCommand" :loading="savingCommand">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<style scoped>
.mobile-terminal-manager {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.hosts-card,
.commands-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.host-list,
.command-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.host-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.host-info {
  margin-bottom: 8px;
}

.host-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.host-detail {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.host-actions {
  display: flex;
  gap: 8px;
}

.command-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.command-info {
  flex: 1;
  cursor: pointer;
}

.command-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.command-preview {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  font-family: monospace;
}

.command-actions {
  display: flex;
  gap: 8px;
}
</style>
