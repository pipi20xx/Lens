<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NInputNumber, NSelect, NIcon, NPopconfirm, useMessage
} from 'naive-ui'
import {
  DeleteOutlineOutlined as DeleteIcon
} from '@vicons/material'
import { terminalApi } from '@/api/terminal'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  MessageText,
  EmptyText,
  ConfirmText,
  ModalTitle,
  FormLabel,
  Placeholder,
} from '../constants'

const message = useMessage()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const messageText = MessageText
const emptyText = EmptyText
const confirmText = ConfirmText
const modalTitle = ModalTitle
const formLabel = FormLabel
const placeholder = Placeholder

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
    message.error(messageText.LOAD_HOST_FAILED)
  }
}

const saveHost = async () => {
  if (!newHost.value.name || !newHost.value.host) {
    message.warning(messageText.FILL_HOST_INFO)
    return
  }
  saving.value = true
  try {
    if (newHost.value.id) {
      await terminalApi.updateHost(newHost.value.id, newHost.value)
      message.success(messageText.UPDATE_HOST_SUCCESS)
    } else {
      await terminalApi.createHost(newHost.value)
      message.success(messageText.ADD_HOST_SUCCESS)
    }
    showAddHostModal.value = false
    newHost.value = { id: undefined, name: '', host: '', port: 22, username: '', auth_type: 'password', password: '' }
    await loadHosts()
  } catch (e) {
    message.error(newHost.value.id ? messageText.UPDATE_HOST_FAILED : messageText.ADD_HOST_FAILED)
  } finally {
    saving.value = false
  }
}

const deleteHost = async (id: number) => {
  try {
    await terminalApi.deleteHost(id)
    message.success(messageText.DELETE_HOST_SUCCESS)
    await loadHosts()
  } catch (e) {
    message.error(messageText.DELETE_HOST_FAILED)
  }
}

const editHost = (host: any) => {
  newHost.value = { ...host }
  showAddHostModal.value = true
}

const connectHost = (host: any) => {
  message.info(messageText.TERMINAL_DESKTOP_ONLY)
}

// 快速命令
const loadCommands = async () => {
  try {
    const res = await terminalApi.getCommands()
    commands.value = res as any || []
  } catch (e) {
    message.error(messageText.LOAD_COMMAND_FAILED)
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
    message.warning(messageText.FILL_COMMAND_INFO)
    return
  }
  savingCommand.value = true
  try {
    if (editingCommand.value) {
      await terminalApi.saveCommand({ ...newCommand.value, id: editingCommand.value.id })
    } else {
      await terminalApi.saveCommand(newCommand.value)
    }
    message.success(editingCommand.value ? messageText.UPDATE_COMMAND_SUCCESS : messageText.ADD_COMMAND_SUCCESS)
    showAddCommandModal.value = false
    newCommand.value = { title: '', command: '' }
    editingCommand.value = null
    await loadCommands()
  } catch (e) {
    message.error(messageText.SAVE_COMMAND_FAILED)
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
    message.success(messageText.DELETE_COMMAND_SUCCESS)
    await loadCommands()
  } catch (e) {
    message.error(messageText.DELETE_COMMAND_FAILED)
  }
}

const sendCommand = (cmd: any) => {
  message.info(messageText.COMMAND_DESKTOP_ONLY)
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
        <n-button block :type="buttonTypes.PRIMARY" @click="showAddHostModal = true">
          <template #icon>
            <n-icon><AddIcon /></n-icon>
          </template>
          {{ buttonText.ADD_HOST }}
        </n-button>
        <div v-if="hosts.length === 0" class="empty-state">
          <n-empty :description="emptyText.NO_HOST_CONFIG" />
        </div>
        <div v-else class="host-list">
          <div v-for="host in hosts" :key="host.id" class="host-item">
            <div class="host-info">
              <div class="host-name">{{ host.name }}</div>
              <div class="host-detail">{{ host.username }}@{{ host.host }}:{{ host.port }}</div>
            </div>
            <div class="host-actions">
              <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.INFO" @click="connectHost(host)">
                <template #icon>
                  <n-icon><TerminalIcon /></n-icon>
                </template>
                {{ buttonText.CONNECT }}
              </n-button>
              <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.WARNING" @click="editHost(host)">
                <template #icon>
                  <n-icon><EditIcon /></n-icon>
                </template>
                {{ buttonText.EDIT }}
              </n-button>
              <n-popconfirm @positive-click="deleteHost(host.id)" :positive-text="confirmText.CONFIRM_DELETE" :negative-text="confirmText.CANCEL">
                <template #trigger>
                  <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
                    <template #icon>
                      <n-icon><DeleteIcon /></n-icon>
                    </template>
                    {{ buttonText.DELETE }}
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
        <n-button block :type="buttonTypes.PRIMARY" secondary @click="showAddCommandModal = true; editingCommand = null; newCommand = { title: '', command: '' }">
          <template #icon>
            <n-icon><AddIcon /></n-icon>
          </template>
          {{ buttonText.ADD_COMMAND }}
        </n-button>
        <div v-if="commands.length === 0" class="empty-state">
          <n-empty :description="emptyText.NO_QUICK_COMMAND" />
        </div>
        <div v-else class="command-list">
          <div v-for="cmd in commands" :key="cmd.id" class="command-item">
            <div class="command-info" @click="sendCommand(cmd)">
              <div class="command-name">{{ cmd.title }}</div>
              <div class="command-preview">{{ cmd.command }}</div>
            </div>
            <div class="command-actions">
              <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.WARNING" @click="editCommand(cmd)">
                <template #icon>
                  <n-icon><EditIcon /></n-icon>
                </template>
              </n-button>
              <n-popconfirm @positive-click="deleteCommand(cmd.id)" :positive-text="confirmText.CONFIRM_DELETE" :negative-text="confirmText.CANCEL">
                <template #trigger>
                  <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
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

    <n-modal v-model:show="showAddHostModal" preset="card" :title="newHost.id ? modalTitle.EDIT_HOST : modalTitle.ADD_HOST" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="formLabel.NAME">
          <n-input v-model:value="newHost.name" :placeholder="placeholder.HOST_NAME" />
        </n-form-item>
        <n-form-item :label="formLabel.HOST_ADDRESS">
          <n-input v-model:value="newHost.host" :placeholder="placeholder.HOST_ADDRESS_EXAMPLE" />
        </n-form-item>
        <n-form-item :label="formLabel.PORT">
          <n-input-number v-model:value="newHost.port" :placeholder="placeholder.PORT" />
        </n-form-item>
        <n-form-item :label="formLabel.USERNAME">
          <n-input v-model:value="newHost.username" :placeholder="placeholder.USERNAME" />
        </n-form-item>
        <n-form-item :label="formLabel.AUTH_TYPE">
          <n-select v-model:value="newHost.auth_type" :options="authTypeOptions" />
        </n-form-item>
        <n-form-item v-if="newHost.auth_type === 'password'" :label="formLabel.PASSWORD">
          <n-input v-model:value="newHost.password" type="password" show-password-on="click" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddHostModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveHost" :loading="saving">{{ buttonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showAddCommandModal" preset="card" :title="editingCommand ? modalTitle.EDIT_COMMAND : modalTitle.ADD_COMMAND" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="formLabel.COMMAND_NAME">
          <n-input v-model:value="newCommand.title" :placeholder="placeholder.COMMAND_NAME_EXAMPLE" />
        </n-form-item>
        <n-form-item :label="formLabel.COMMAND_CONTENT">
          <n-input v-model:value="newCommand.command" type="textarea" :rows="3" :placeholder="placeholder.COMMAND_CONTENT_EXAMPLE" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddCommandModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveCommand" :loading="savingCommand">{{ buttonText.SAVE }}</n-button>
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
