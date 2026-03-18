<template>
  <n-modal :show="show" @update:show="emit('update:show', $event)" preset="card" :title="modalTitle.HOST_MANAGE" style="width: 90vw; max-width: 600px">
    <div class="mobile-docker-host-manager">
      <n-space vertical>
        <n-button :type="buttonTypes.PRIMARY" :size="buttonSizes.MEDIUM" @click="handleAddHost">
          {{ buttonText.ADD_HOST }}
        </n-button>

        <div v-if="hosts.length === 0" class="empty-state">
          <n-empty :description="emptyText.NO_HOST" :size="buttonSizes.SMALL" />
        </div>

        <div v-else class="host-list">
          <div v-for="host in hosts" :key="host.id" class="host-item">
            <div class="host-header">
              <div class="host-name">
                <n-text strong>{{ host.name }}</n-text>
                <n-tag :size="buttonSizes.TINY" :type="tagTypes.WARNING">SSH</n-tag>
                <n-tag v-if="host.is_local" :size="buttonSizes.TINY" :type="tagTypes.SUCCESS">{{ tagText.HOST }}</n-tag>
              </div>
              <n-space>
                <n-button :size="buttonSizes.MEDIUM" secondary @click="testConnection(host.id)" :loading="testingId === host.id">
                  {{ buttonText.TEST }}
                </n-button>
                <n-button :size="buttonSizes.MEDIUM" secondary @click="handleEditHost(host)">
                  {{ buttonText.EDIT }}
                </n-button>
                <n-popconfirm @positive-click="() => deleteHost(host.id)" :positive-text="confirmText.CONFIRM" :negative-text="confirmText.CANCEL">
                  <template #trigger>
                    <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
                      {{ buttonText.DELETE }}
                    </n-button>
                  </template>
                  {{ confirmText.DELETE_CONFIRM }}
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
            </div>
          </div>
        </div>
      </n-space>
    </div>
  </n-modal>

  <n-modal v-model:show="showEditModal" preset="card" :title="editHostForm.id ? modalTitle.EDIT_HOST : modalTitle.ADD_HOST" style="width: 90vw; max-width: 500px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="formLabel.NAME" required>
          <n-input v-model:value="editHostForm.name" :placeholder="placeholder.HOST_NAME_EXAMPLE" />
        </n-form-item>
        <n-form-item :label="formLabel.SSH_ADDRESS" required>
          <n-input v-model:value="editHostForm.ssh_host" :placeholder="placeholder.SSH_HOST" />
        </n-form-item>
        <n-form-item :label="formLabel.SSH_PORT" required>
          <n-input-number v-model:value="editHostForm.ssh_port" :min="1" :max="65535" style="width: 100%" />
        </n-form-item>
        <n-form-item :label="formLabel.SSH_USER" required>
          <n-input v-model:value="editHostForm.ssh_user" :placeholder="placeholder.SSH_USER" />
        </n-form-item>
        <n-form-item :label="formLabel.SSH_PASSWORD" required>
          <n-input v-model:value="editHostForm.ssh_pass" type="password" show-password-on="click" />
        </n-form-item>
        <n-form-item :label="formLabel.HOST_MARK">
          <n-space align="center">
            <MobileSwitch
              :model-value="editHostForm.is_local"
              @update:model-value="(val) => editHostForm.is_local = val"
            />
            <n-text depth="3" style="font-size: 12px">{{ formLabel.HOST_MARK_TIP }}</n-text>
          </n-space>
        </n-form-item>
        <n-form-item :label="formLabel.SCAN_PATHS">
          <n-input 
            v-model:value="editHostForm.compose_scan_paths" 
            type="textarea" 
            :placeholder="placeholder.SCAN_PATHS_EXAMPLE"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showEditModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveHost" :loading="saving">{{ buttonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { 
  NSpace, NButton, NTag, NIcon, NText, NModal, NForm, NFormItem, 
  NInput, NInputNumber, NEmpty, NPopconfirm, useMessage 
} from 'naive-ui'
import {
  SensorsOutlined as TestIcon,
  DnsOutlined as ServerIcon,
  PersonOutlineOutlined as UserIcon
} from '@vicons/material'
import axios from 'axios'
import MobileSwitch from '../components/MobileSwitch.vue'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  TagTypes,
  TagText,
  MessageText,
  ModalTitle,
  FormLabel,
  Placeholder,
  ConfirmText,
  EmptyText,
} from '../constants'

const props = defineProps<{
  hosts: any[]
  show: boolean
}>()

const emit = defineEmits(['refresh', 'update:show'])

const message = useMessage()

const show = ref(props.show)

watch(() => props.show, (val) => {
  show.value = val
})

watch(() => show.value, (val) => {
  emit('update:show', val)
})

watch(() => props.hosts, (val) => {
  console.log('hosts updated:', val)
}, { immediate: true })

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const tagTypes = TagTypes
const tagText = TagText
const messageText = MessageText
const modalTitle = ModalTitle
const formLabel = FormLabel
const placeholder = Placeholder
const confirmText = ConfirmText
const emptyText = EmptyText

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
    message.warning(messageText.COMPLETE_HOST_INFO)
    return
  }
  saving.value = true
  try {
    if (editHostForm.value.id) {
      await axios.put(`/api/docker/hosts/${editHostForm.value.id}`, editHostForm.value)
      message.success(messageText.HOST_CONFIG_UPDATED)
    } else {
      await axios.post('/api/docker/hosts', editHostForm.value)
      message.success(messageText.NEW_HOST_ADDED)
    }
    showEditModal.value = false
    emit('refresh')
  } catch (e: any) {
    message.error(messageText.SAVE_FAILED + ': ' + (e.response?.data?.detail || messageText.UNKNOWN_ERROR))
  } finally {
    saving.value = false
  }
}

const deleteHost = async (id: string) => {
  try {
    await axios.delete(`/api/docker/hosts/${id}`)
    message.success(messageText.HOST_DELETED)
    emit('refresh')
  } catch (e: any) {
    message.error(messageText.DELETE_FAILED + ': ' + (e.response?.data?.detail || messageText.UNKNOWN_ERROR))
  }
}

const testConnection = async (id: string) => {
  testingId.value = id
  try {
    const res = await axios.post(`/api/docker/${id}/test`)
    if (res.data.status === 'ok') {
      message.success(messageText.CONNECTION_NORMAL)
    } else {
      message.error(messageText.CONNECTION_FAILED)
    }
  } catch (e: any) {
    message.error(messageText.TEST_FAILED + ': ' + (e.response?.data?.detail || messageText.UNKNOWN_ERROR))
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
  background: var(--card-color);
  border: 1px solid #3B82F6;
  border-radius: 12px;
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
