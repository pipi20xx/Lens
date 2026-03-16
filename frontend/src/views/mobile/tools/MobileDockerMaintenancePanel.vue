<template>
  <div class="mobile-docker-maintenance-panel">
    <n-space vertical>
      <n-card :title="cardTitle.DAEMON_CONFIG" :size="buttonSizes.SMALL" :bordered="false">
        <template #header-extra>
          <n-button :size="buttonSizes.MEDIUM" quaternary :type="buttonTypes.PRIMARY" @click="openRawEdit" :loading="loading.daemon">
            {{ buttonText.EDIT_JSON }}
          </n-button>
        </template>

        <n-alert :type="tagTypes.INFO" :size="buttonSizes.SMALL" style="margin-bottom: 12px">
          {{ alertText.DAEMON_CONFIG_TIP }}
        </n-alert>
        
        <n-form label-placement="top" :size="buttonSizes.SMALL" :disabled="loading.daemon">
          <n-form-item :label="formLabel.MIRROR_ACCELERATOR">
            <n-input
              v-model:value="daemonForm.mirrors"
              type="textarea"
              :placeholder="placeholder.ONE_PER_LINE"
              :autosize="{ minRows: 2 }"
            />
          </n-form-item>
          
          <n-form-item :label="formLabel.PRIVATE_REGISTRY">
            <n-input
              v-model:value="daemonForm.insecure"
              type="textarea"
              :placeholder="placeholder.ONE_PER_LINE"
              :autosize="{ minRows: 2 }"
            />
          </n-form-item>
          
          <div class="setting-item">
            <span class="setting-label">{{ formLabel.PROXY_SETTINGS }}</span>
            <MobileSwitch v-model="daemonForm.proxyEnabled" />
          </div>
          
          <template v-if="daemonForm.proxyEnabled">
            <n-alert :type="tagTypes.WARNING" :size="buttonSizes.TINY" style="margin-top: 8px">
              {{ alertText.PROXY_ONLY_HTTP }}
            </n-alert>
            <n-form-item :label="formLabel.SERVER_ADDRESS" style="margin-top: 8px">
              <n-input v-model:value="daemonForm.proxyHost" :placeholder="placeholder.PROXY_HOST_EXAMPLE" />
            </n-form-item>
            <n-form-item :label="formLabel.PORT">
              <n-input v-model:value="daemonForm.proxyPort" :placeholder="placeholder.PORT" />
            </n-form-item>
            <n-form-item :label="formLabel.NO_PROXY_ADDRESSES">
              <n-input v-model:value="daemonForm.noProxy" :placeholder="placeholder.NO_PROXY_EXAMPLE" />
            </n-form-item>
          </template>
          
          <n-grid :cols="2" :x-gap="8" style="margin-top: 8px">
            <n-gi>
              <n-form-item :label="formLabel.LOG_SIZE">
                <n-input v-model:value="daemonForm.logSize" :placeholder="placeholder.LOG_SIZE" />
              </n-form-item>
            </n-gi>
            <n-gi>
              <n-form-item :label="formLabel.LOG_FILES">
                <n-input-number v-model:value="daemonForm.logFiles" :min="1" style="width: 100%" />
              </n-form-item>
            </n-gi>
          </n-grid>
          
          <n-space vertical style="margin-top: 8px">
            <n-checkbox v-model:checked="daemonForm.liveRestore" :size="buttonSizes.SMALL">
              {{ formLabel.ENABLE_LIVE_RESTORE }}
            </n-checkbox>
            <n-checkbox v-model:checked="daemonForm.shouldRestart" :size="buttonSizes.SMALL">
              {{ formLabel.RESTART_AFTER_SAVE }}
            </n-checkbox>
          </n-space>
        </n-form>
        
        <n-button 
          :type="buttonTypes.PRIMARY" 
          block 
          :loading="loading.daemon" 
          @click="handleSaveDaemonConfig"
          style="margin-top: 12px"
        >
          {{ buttonText.SAVE_CONFIG }}
        </n-button>
      </n-card>

      <n-card :title="cardTitle.IMAGE_CLEANUP" :size="buttonSizes.SMALL" :bordered="false">
        <n-space vertical>
          <n-text depth="3" style="font-size: 12px">{{ alertText.IMAGE_CLEANUP_TIP }}</n-text>
          <n-space vertical item-style="display: flex; align-items: center">
            <n-checkbox v-model:checked="imageOptions.dangling" :size="buttonSizes.SMALL">
              {{ formLabel.CLEAN_UNTAGGED_IMAGES }}
            </n-checkbox>
            <n-checkbox v-model:checked="imageOptions.all" :size="buttonSizes.SMALL">
              {{ formLabel.CLEAN_ALL_UNUSED_IMAGES }}
            </n-checkbox>
          </n-space>
          <n-button 
            :type="buttonTypes.PRIMARY" 
            secondary 
            block 
            :loading="loading.images" 
            @click="handlePruneImages"
          >
            {{ buttonText.START_CLEANUP_IMAGES }}
          </n-button>
        </n-space>
      </n-card>

      <n-card :title="cardTitle.CACHE_CLEANUP" :size="buttonSizes.SMALL" :bordered="false">
        <n-space vertical>
          <n-text depth="3" style="font-size: 12px">{{ alertText.CACHE_CLEANUP_TIP }}</n-text>
          <n-button 
            :type="buttonTypes.WARNING" 
            secondary 
            block 
            :loading="loading.cache" 
            @click="handlePruneCache"
          >
            {{ buttonText.START_CLEANUP_CACHE }}
          </n-button>
        </n-space>
      </n-card>

      <n-card :title="cardTitle.CONTAINER_CLEANUP" :size="buttonSizes.SMALL" :bordered="false">
        <n-space vertical>
          <n-text depth="3" style="font-size: 12px">{{ alertText.CONTAINER_CLEANUP_TIP }}</n-text>
          <n-button 
            :type="buttonTypes.ERROR" 
            secondary 
            block 
            :loading="loading.containers" 
            @click="handlePruneContainers"
          >
            {{ buttonText.START_CLEANUP_CONTAINERS }}
          </n-button>
        </n-space>
      </n-card>
    </n-space>

    <n-modal v-model:show="showResult" preset="dialog" :title="modalTitle.CLEANUP_RESULT" style="width: 90%">
      <template #default>
        <div style="background: #1e1e1e; color: #adadad; padding: 10px; font-family: monospace; border-radius: 4px; overflow: auto; max-height: 300px; white-space: pre-wrap; font-size: 12px;">
          {{ resultOutput }}
        </div>
      </template>
    </n-modal>

    <n-modal v-model:show="showRawModal" preset="card" :title="modalTitle.EDIT_DAEMON_JSON" style="width: 90%">
      <n-space vertical size="large">
        <n-alert :type="tagTypes.WARNING" :size="buttonSizes.SMALL">
          {{ alertText.EDIT_JSON_WARNING }}
        </n-alert>
        <n-input
          v-model:value="rawJsonContent"
          type="textarea"
          :placeholder="placeholder.JSON_PLACEHOLDER"
          :autosize="{ minRows: 10, maxRows: 20 }"
          style="font-family: monospace; font-size: 12px"
          @input="validateRawJson"
        />
        <n-text v-if="rawJsonError" :type="tagTypes.ERROR" style="font-size: 12px">{{ rawJsonError }}</n-text>
        
        <n-space align="center">
          <n-checkbox v-model:checked="daemonForm.shouldRestart" :size="buttonSizes.SMALL">
            {{ formLabel.RESTART_AFTER_SAVE }}
          </n-checkbox>
        </n-space>
      </n-space>
      <template #footer>
        <n-space justify="end">
          <n-button :size="buttonSizes.MEDIUM" @click="showRawModal = false">
            {{ buttonText.CANCEL }}
          </n-button>
          <n-button 
            :type="buttonTypes.PRIMARY" 
            :size="buttonSizes.MEDIUM" 
            :disabled="!!rawJsonError" 
            @click="handleSaveRawJson" 
            :loading="loading.daemon"
          >
            {{ buttonText.SAVE }}
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NSpace, NCard, NText, NCheckbox, NButton, NModal, NForm, NFormItem, NInput, NInputNumber, NAlert, NIcon, NGrid, NGi, NTag, useMessage, useDialog } from 'naive-ui'
import axios from 'axios'
import MobileSwitch from '../components/MobileSwitch.vue'
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
  AlertText,
} from '../constants'

const props = defineProps({
  hostId: String | null
})

const message = useMessage()
const dialog = useDialog()

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
const alertText = AlertText

const loading = ref({ images: false, cache: false, containers: false, daemon: false })
const showResult = ref(false)
const showRawModal = ref(false)
const rawJsonContent = ref('')
const rawJsonError = ref<string | null>(null)
const resultOutput = ref('')

const imageOptions = ref({
  dangling: true,
  all: false
})

const daemonForm = ref({
  mirrors: '',
  insecure: '',
  logSize: '100m',
  logFiles: 5,
  liveRestore: true,
  shouldRestart: false,
  proxyEnabled: false,
  proxyHost: '',
  proxyPort: '',
  proxyUser: '',
  proxyPass: '',
  noProxy: 'localhost,127.0.0.1'
})

const rawDaemonConfig = ref<any>({})

const fetchDaemonConfig = async () => {
  if (!props.hostId) return
  loading.value.daemon = true
  try {
    const res = await axios.get(`/api/docker/${props.hostId}/daemon-config`)
    rawDaemonConfig.value = res.data
    
    daemonForm.value.mirrors = (res.data['registry-mirrors'] || []).join('\n')
    daemonForm.value.insecure = (res.data['insecure-registries'] || []).join('\n')
    daemonForm.value.logSize = res.data['log-opts']?.['max-size'] || '100m'
    daemonForm.value.logFiles = parseInt(res.data['log-opts']?.['max-file'] || '5')
    daemonForm.value.liveRestore = res.data['live-restore'] ?? true
    
    const proxies = res.data['proxies'] || {}
    const httpProxy = proxies['http-proxy'] || ''
    daemonForm.value.noProxy = proxies['no-proxy'] || 'localhost,127.0.0.1'
    
    if (httpProxy) {
      daemonForm.value.proxyEnabled = true
      try {
        const url = new URL(httpProxy)
        daemonForm.value.proxyHost = url.hostname
        daemonForm.value.proxyPort = url.port
        daemonForm.value.proxyUser = decodeURIComponent(url.username)
        daemonForm.value.proxyPass = decodeURIComponent(url.password)
      } catch (e) {
        daemonForm.value.proxyHost = httpProxy
      }
    } else {
      daemonForm.value.proxyEnabled = false
    }
  } catch (e) {
    message.error(messageText.READ_DAEMON_CONFIG_FAILED)
  } finally {
    loading.value.daemon = false
  }
}

watch(() => props.hostId, fetchDaemonConfig, { immediate: true })

const openRawEdit = async () => {
  if (!props.hostId) return
  loading.value.daemon = true
  try {
    const res = await axios.get(`/api/docker/${props.hostId}/daemon-config/raw`)
    rawJsonContent.value = res.data.content
    rawJsonError.value = null
    showRawModal.value = true
  } catch (e) {
    message.error(messageText.READ_RAW_CONFIG_FAILED)
  } finally {
    loading.value.daemon = false
  }
}

const validateRawJson = (val: string) => {
  if (!val.trim()) {
    rawJsonError.value = messageText.CONTENT_REQUIRED
    return
  }
  try {
    JSON.parse(val)
    rawJsonError.value = null
  } catch (e: any) {
    rawJsonError.value = messageText.INVALID_JSON
  }
}

const handleSaveRawJson = () => {
  if (rawJsonError.value) return
  
  dialog.warning({
    title: modalTitle.CONFIRM_SAVE,
    content: daemonForm.value.shouldRestart 
      ? messageText.RESTART_WARNING 
      : messageText.MANUAL_RESTART_TIP,
    positiveText: buttonText.CONFIRM,
    negativeText: buttonText.CANCEL,
    onPositiveClick: async () => {
      loading.value.daemon = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/daemon-config/raw`, {
          content: rawJsonContent.value,
          restart: daemonForm.value.shouldRestart
        })
        message.success(res.data.message)
        showRawModal.value = false
        fetchDaemonConfig()
      } catch (e: any) {
        message.error(e.response?.data?.detail || messageText.SAVE_FAILED)
      } finally {
        loading.value.daemon = false
      }
    }
  })
}

const handleSaveDaemonConfig = async () => {
  if (!props.hostId) return
  const newConfig = { ...rawDaemonConfig.value }
  newConfig['registry-mirrors'] = daemonForm.value.mirrors.split('\n').map(i => i.trim()).filter(i => i)
  newConfig['insecure-registries'] = daemonForm.value.insecure.split('\n').map(i => i.trim()).filter(i => i)
  newConfig['log-driver'] = 'json-file'
  newConfig['log-opts'] = {
    'max-size': daemonForm.value.logSize,
    'max-file': daemonForm.value.logFiles.toString()
  }
  newConfig['live-restore'] = daemonForm.value.liveRestore
  
  if (daemonForm.value.proxyEnabled && daemonForm.value.proxyHost) {
    let auth = ''
    if (daemonForm.value.proxyUser) {
      auth = `${encodeURIComponent(daemonForm.value.proxyUser)}:${encodeURIComponent(daemonForm.value.proxyPass)}@`
    }
    const port = daemonForm.value.proxyPort ? `:${daemonForm.value.proxyPort}` : ''
    const host = daemonForm.value.proxyHost.includes('://') ? daemonForm.value.proxyHost.split('://')[1] : daemonForm.value.proxyHost
    const proxyUrl = `http://${auth}${host}${port}`
    newConfig['proxies'] = {
      'http-proxy': proxyUrl,
      'https-proxy': proxyUrl,
      'no-proxy': daemonForm.value.noProxy
    }
  } else {
    delete newConfig['proxies']
  }

  dialog.warning({
    title: modalTitle.CONFIRM_SAVE,
    content: daemonForm.value.shouldRestart 
      ? messageText.RESTART_WARNING 
      : messageText.MANUAL_RESTART_TIP,
    positiveText: buttonText.CONFIRM,
    negativeText: buttonText.CANCEL,
    onPositiveClick: async () => {
      loading.value.daemon = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/daemon-config`, {
          config: newConfig,
          restart: daemonForm.value.shouldRestart
        })
        message.success(res.data.message)
        if (daemonForm.value.shouldRestart && res.data.restart_result) {
          resultOutput.value = res.data.restart_result.stdout || res.data.restart_result.stderr || messageText.SERVICE_RESTART_ATTEMPTED
          showResult.value = true
        }
        fetchDaemonConfig()
      } catch (e) {
        message.error(e.response?.data?.detail || messageText.SAVE_FAILED)
      } finally {
        loading.value.daemon = false
      }
    }
  })
}

const handlePruneImages = async () => {
  if (!props.hostId) return
  if (!imageOptions.value.dangling && !imageOptions.value.all) {
    message.warning(messageText.SELECT_CLEANUP_OPTION)
    return
  }

  dialog.warning({
    title: modalTitle.CONFIRM_CLEANUP_IMAGES,
    content: messageText.CLEANUP_IMAGES_WARNING,
    positiveText: buttonText.CONFIRM,
    negativeText: buttonText.CANCEL,
    onPositiveClick: async () => {
      loading.value.images = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune-images`, {
          dangling: imageOptions.value.dangling,
          all_unused: imageOptions.value.all
        })
        message.success(res.data.message || messageText.IMAGE_CLEANUP_STARTED)
      } catch (e) { message.error(messageText.REQUEST_FAILED) }
      finally { loading.value.images = false }
    }
  })
}

const handlePruneCache = async () => {
  if (!props.hostId) return
  dialog.warning({
    title: modalTitle.CONFIRM_CLEANUP_CACHE,
    content: messageText.CLEANUP_CACHE_WARNING,
    positiveText: buttonText.CONFIRM,
    negativeText: buttonText.CANCEL,
    onPositiveClick: async () => {
      loading.value.cache = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune-cache`)
        message.success(res.data.message || messageText.CACHE_CLEANUP_STARTED)
      } catch (e) { message.error(messageText.REQUEST_FAILED) }
      finally { loading.value.cache = false }
    }
  })
}

const handlePruneContainers = async () => {
  if (!props.hostId) return
  dialog.warning({
    title: modalTitle.CONFIRM_CLEANUP_CONTAINERS,
    content: messageText.CLEANUP_CONTAINERS_WARNING,
    positiveText: buttonText.CONFIRM,
    negativeText: buttonText.CANCEL,
    onPositiveClick: async () => {
      loading.value.containers = true
      try {
        const res = await axios.post(`/api/docker/${props.hostId}/prune-containers`)
        message.success(res.data.message || messageText.CONTAINER_CLEANUP_STARTED)
      } catch (e) { message.error(messageText.REQUEST_FAILED) }
      finally { loading.value.containers = false }
    }
  })
}
</script>

<style scoped>
.mobile-docker-maintenance-panel {
  padding: 8px;
}

.proxy-section {
  background: rgba(24, 160, 88, 0.05);
  border: 1px solid rgba(24, 160, 88, 0.2);
  border-radius: 6px;
  padding: 12px;
  margin-top: 8px;
}

.switch-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}
</style>
