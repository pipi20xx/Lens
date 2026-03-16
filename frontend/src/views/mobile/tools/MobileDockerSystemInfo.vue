<template>
  <div class="mobile-docker-system-info">
    <n-space vertical>
      <n-card :title="cardTitle.ENV_CHECK" :size="buttonSizes.SMALL" :bordered="false">
        <template #header-extra>
          <n-space>
            <n-button 
              :type="buttonTypes.WARNING" 
              size="tiny" 
              secondary 
              @click="showRepairModal = true" 
              :loading="installing"
            >
              {{ buttonText.REPAIR }}
            </n-button>
            <n-button size="tiny" secondary @click="fetchInfo" :loading="loading">
              {{ buttonText.REFRESH }}
            </n-button>
          </n-space>
        </template>

        <n-skeleton v-if="loading" text :repeat="4" />

        <n-space v-else vertical>
          <div class="info-item">
            <div class="info-label">{{ label.DOCKER_VERSION }}</div>
            <n-tag :type="info.docker === '未安装' ? tagTypes.ERROR : tagTypes.SUCCESS" :size="buttonSizes.SMALL">
              {{ info.docker }}
            </n-tag>
          </div>

          <div class="info-item">
            <div class="info-label">{{ label.COMPOSE_VERSION }}</div>
            <n-tag :type="info.compose === '未安装' ? tagTypes.ERROR : tagTypes.SUCCESS" :size="buttonSizes.SMALL">
              {{ info.compose }}
            </n-tag>
          </div>

          <div class="info-item">
            <div class="info-label">{{ label.SERVICE_STATUS }}</div>
            <n-space align="center">
              <n-badge 
                :value="info.status === 'active' ? statusText.RUNNING : (info.status === 'inactive' ? statusText.STOPPED : statusText.UNKNOWN)" 
                :type="info.status === 'active' ? tagTypes.SUCCESS : tagTypes.ERROR" 
              />
              <n-button-group :size="buttonSizes.MEDIUM">
                <n-button 
                  v-if="info.status !== 'active'" 
                  :type="buttonTypes.SUCCESS" 
                  ghost 
                  @click="handleServiceAction('start')"
                  :loading="actionLoading === 'start'"
                >
                  {{ buttonText.START }}
                </n-button>
                <n-button 
                  v-if="info.status === 'active'" 
                  :type="buttonTypes.ERROR" 
                  ghost 
                  @click="handleServiceAction('stop')"
                  :loading="actionLoading === 'stop'"
                >
                  {{ buttonText.STOP }}
                </n-button>
                <n-button 
                  :type="buttonTypes.WARNING" 
                  ghost 
                  @click="handleServiceAction('restart')"
                  :loading="actionLoading === 'restart'"
                >
                  {{ buttonText.RESTART }}
                </n-button>
              </n-button-group>
            </n-space>
          </div>

          <div class="info-item">
            <div class="info-label">{{ label.OS }}</div>
            <n-text depth="3" style="font-size: 12px">{{ info.os }}</n-text>
          </div>
        </n-space>
      </n-card>

      <n-alert :type="tagTypes.INFO" :size="buttonSizes.SMALL">
        {{ alertText.ENV_CHECK_TIP }}
      </n-alert>
    </n-space>

    <n-modal v-model:show="showRepairModal" preset="card" :title="modalTitle.ENV_REPAIR_CONFIG" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="buttonSizes.SMALL">
        <n-form-item :label="formLabel.USE_MIRROR">
          <n-switch v-model:value="repairForm.useMirror" class="mobile-switch" />
        </n-form-item>
        <n-form-item :label="formLabel.PROXY">
          <n-input v-model:value="repairForm.proxy" :placeholder="placeholder.PROXY_EXAMPLE" />
        </n-form-item>
        <n-alert :type="tagTypes.WARNING" :size="buttonSizes.SMALL">
          {{ alertText.REPAIR_WARNING }}
        </n-alert>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showRepairModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="handleRepair" :loading="installing">{{ buttonText.START_EXECUTE }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showResult" preset="dialog" :title="modalTitle.INSTALL_RESULT" style="width: 90vw; max-width: 600px">
      <div class="result-container">
        {{ resultOutput }}
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { 
  NSpace, NCard, NTag, NBadge, NSkeleton, NButton, NIcon, 
  NAlert, NModal, useMessage, NForm, NFormItem, NInput, NSwitch, NButtonGroup, NText 
} from 'naive-ui'
import axios from 'axios'
import {
  ButtonTypes,
  ButtonSizes,
  ButtonText,
  TagTypes,
  StatusText,
  MessageText,
  ModalTitle,
  FormLabel,
  Placeholder,
  CardTitle,
  Label,
  AlertText,
} from '../constants'

const props = defineProps<{ hostId: string | null }>()
const message = useMessage()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const buttonText = ButtonText
const tagTypes = TagTypes
const statusText = StatusText
const messageText = MessageText
const modalTitle = ModalTitle
const formLabel = FormLabel
const placeholder = Placeholder
const cardTitle = CardTitle
const label = Label
const alertText = AlertText

const loading = ref(false)
const installing = ref(false)
const actionLoading = ref<string | null>(null)
const showRepairModal = ref(false)
const showResult = ref(false)
const resultOutput = ref('')

const repairForm = reactive({
  useMirror: true,
  proxy: ''
})

const info = ref({
  docker: '',
  compose: '',
  os: '',
  status: ''
})

const handleServiceAction = async (action: string) => {
  if (!props.hostId) return
  actionLoading.value = action
  try {
    const res = await axios.post(`/api/docker/${props.hostId}/service-action`, { action })
    if (res.data.success) {
      message.success(messageText.SERVICE_ACTION_SUCCESS.replace('{action}', action === 'start' ? '启动' : action === 'stop' ? '停止' : '重启'))
    } else {
      message.error(messageText.OPERATION_FAILED + ': ' + res.data.stderr)
    }
    setTimeout(fetchInfo, 1000)
  } catch (e: any) {
    message.error(messageText.REQUEST_FAILED + ': ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    actionLoading.value = null
  }
}

const fetchInfo = async () => {
  if (!props.hostId) return
  loading.value = true
  try {
    const res = await axios.get(`/api/docker/${props.hostId}/system-info`)
    info.value = res.data
  } catch (e: any) {
    message.error(messageText.GET_SYSTEM_INFO_FAILED + ': ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    loading.value = false
  }
}

const handleRepair = async () => {
  showRepairModal.value = false
  installing.value = true
  try {
    const res = await axios.post(`/api/docker/${props.hostId}/install-env`, { 
      use_mirror: repairForm.useMirror,
      proxy: repairForm.proxy
    })
    resultOutput.value = res.data.stdout || res.data.stderr || '安装已完成。'
    showResult.value = true
    if (res.data.success) message.success(messageText.ENV_TASK_COMPLETED)
  } catch (e: any) {
    message.error(messageText.INSTALL_FAILED + ': ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    installing.value = false
    fetchInfo()
  }
}

watch(() => props.hostId, fetchInfo, { immediate: true })
</script>

<style scoped>
.mobile-docker-system-info {
  padding: 12px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 14px;
  color: var(--text-color);
}

.result-container {
  background: #1e1e1e;
  color: #adadad;
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 12px;
  white-space: pre-wrap;
  max-height: 400px;
  overflow: auto;
}
</style>
