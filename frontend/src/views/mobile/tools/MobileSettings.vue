<template>
  <div class="mobile-settings">
    <div class="page-header">
      <h1 class="page-title">{{ pageTitle.SETTINGS }}</h1>
      <p class="page-desc">配置系统参数与偏好</p>
    </div>

    <n-card class="servers-card" :bordered="false" :title="pageTitle.SERVER_SETTINGS">
      <n-space vertical>
        <div v-if="servers.length === 0" class="empty-state">
          <n-empty :description="messageText.NO_SERVERS" />
        </div>
        <div v-else class="server-list">
          <div v-for="server in servers" :key="server.id" class="server-item">
            <div class="server-info">
              <div class="server-name">{{ server.name }}</div>
              <div class="server-url">{{ server.url }}</div>
            </div>
            <div class="server-actions">
              <n-tag v-if="server.id === activeServerId" :type="tagTypes.SUCCESS" :size="buttonSizes.SMALL" round>
                {{ statusText.ACTIVE }}
              </n-tag>
              <n-button v-else :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.PRIMARY" @click="handleActivate(server.id)">
                {{ buttonText.ACTIVATE }}
              </n-button>
              <n-popconfirm @positive-click="handleDelete(server.id)" :positive-text="buttonText.CONFIRM_DELETE" :negative-text="buttonText.CANCEL">
                <template #trigger>
                  <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.ERROR">
                    {{ buttonText.DELETE }}
                  </n-button>
                </template>
                {{ messageText.DELETE_CONFIRM }}
              </n-popconfirm>
            </div>
          </div>
        </div>
        <n-button block :type="buttonTypes.PRIMARY" secondary @click="showAddServerModal = true">
          {{ buttonText.ADD }}{{ formLabel.SERVER }}
        </n-button>
      </n-space>
    </n-card>

    <n-card class="api-card" :bordered="false" :title="pageTitle.API_SETTINGS">
      <n-space vertical>
        <n-form-item label="TMDB API Key">
          <n-input v-model:value="settings.tmdb_api_key" type="password" show-password-on="click" placeholder="The Movie Database V3 Key" />
        </n-form-item>
        <n-form-item label="Bangumi API Token">
          <n-input v-model:value="settings.bangumi_token" type="password" show-password-on="click" placeholder="Bangumi API Token" />
        </n-form-item>
        <n-button block :type="buttonTypes.PRIMARY" @click="saveSettings" :loading="saving">
          {{ buttonText.SAVE }}{{ formLabel.CONFIG }}
        </n-button>
      </n-space>
    </n-card>

    <n-card class="appearance-card" :bordered="false" :title="pageTitle.APPEARANCE_SETTINGS">
      <n-space vertical>
        <div class="setting-item">
          <span class="setting-label">{{ formLabel.THEME }}</span>
          <n-radio-group v-model:value="settings.theme" @update:value="saveSettings">
            <n-radio v-for="option in themeOptions" :key="option.value" :value="option.value">{{ option.label }}</n-radio>
          </n-radio-group>
        </div>
        <div class="setting-item">
          <span class="setting-label">{{ formLabel.LANGUAGE }}</span>
          <n-select v-model:value="settings.language" :options="languageOptions" @update:value="saveSettings" />
        </div>
      </n-space>
    </n-card>

    <n-card class="system-card" :bordered="false" :title="pageTitle.SYSTEM_INFO">
      <n-space vertical>
        <div class="info-item">
          <span class="info-label">{{ formLabel.VERSION }}</span>
          <span class="info-value">{{ version }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ formLabel.BUILD_TIME }}</span>
          <span class="info-value">{{ buildTime }}</span>
        </div>
        <n-button block :type="buttonTypes.INFO" secondary @click="checkUpdate">
          检查更新
        </n-button>
      </n-space>
    </n-card>

    <n-card class="data-card" :bordered="false" :title="pageTitle.DATA_MANAGEMENT">
      <n-space vertical>
        <input 
          type="file" 
          ref="fileInputRef" 
          style="display: none" 
          accept=".json,.yaml,.yml"
          @change="handleImport"
        />
        <n-button block :type="buttonTypes.WARNING" secondary @click="exportData">
          {{ buttonText.EXPORT }}{{ formLabel.DATA }}
        </n-button>
        <n-button block :type="buttonTypes.INFO" secondary @click="triggerImport">
          {{ buttonText.IMPORT }}{{ formLabel.DATA }}
        </n-button>
        <n-button block :type="buttonTypes.ERROR" secondary @click="clearCache">
          {{ buttonText.CLEAR }}{{ formLabel.CACHE }}
        </n-button>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddServerModal" preset="card" :title="buttonText.ADD + formLabel.SERVER" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" :size="formSizes.SMALL">
        <n-form-item :label="formLabel.SERVER_NAME">
          <n-input v-model:value="newServer.name" :placeholder="placeholder.SERVER_NAME" />
        </n-form-item>
        <n-form-item :label="formLabel.SERVER_URL">
          <n-input v-model:value="newServer.url" :placeholder="placeholder.SERVER_URL" />
        </n-form-item>
        <n-form-item :label="formLabel.API_KEY">
          <n-input v-model:value="newServer.api_key" type="password" show-password-on="click" placeholder="Emby API Key" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddServerModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="addServer" :loading="saving">{{ buttonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NTag, NRadioGroup, NRadio, NSelect, NIcon, NPopconfirm } from 'naive-ui'
import { DeleteOutlineOutlined as DeleteIcon } from '@vicons/material'
import { useMessage } from 'naive-ui'
import { serverApi } from '@/api/server'
import { configApi } from '@/api/config'
import { fetchServers, servers, activeServerId, activateServer } from '@/store/serverStore'
import {
  ButtonTypes,
  ButtonSizes,
  TagTypes,
  FormSizes,
  ButtonText,
  StatusText,
  MessageText,
  PageTitle,
  ThemeOptions,
  LanguageOptions,
} from '../constants'

const message = useMessage()
const showAddServerModal = ref(false)
const saving = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const tagTypes = TagTypes
const formSizes = FormSizes
const buttonText = ButtonText
const statusText = StatusText
const messageText = MessageText
const pageTitle = PageTitle
const themeOptions = ThemeOptions
const languageOptions = LanguageOptions

// 表单标签常量
const formLabel = {
  SERVER: '服务器',
  CONFIG: '配置',
  DATA: '数据',
  CACHE: '缓存',
  SERVER_NAME: '服务器名称',
  SERVER_URL: '服务器地址',
  API_KEY: 'API 密钥',
  THEME: '主题模式',
  LANGUAGE: '语言',
  VERSION: '版本',
  BUILD_TIME: '构建时间',
}

// 占位符
const placeholder = {
  SERVER_NAME: '例如：主服务器',
  SERVER_URL: 'http://192.168.1.1:8096',
}

const settings = reactive({
  tmdb_api_key: '',
  bangumi_token: '',
  theme: 'auto',
  language: 'zh-CN'
})

const newServer = ref({
  name: '',
  url: '',
  api_key: ''
})

const version = ref('1.0.0')
const buildTime = ref('2024-01-01')

const fetchCurrent = async () => {
  await fetchServers()
  try {
    const res: any = await serverApi.getCurrent()
    const data = res
    if (data) {
      settings.tmdb_api_key = data.tmdb_api_key || ''
      settings.bangumi_token = data.bangumi_api_token || ''
    }
  } catch (e) {
    console.error('Failed to load global config:', e)
  }
}

const addServer = async () => {
  if (!newServer.value.name || !newServer.value.url) {
    message.warning('请填写完整的服务器信息')
    return
  }
  saving.value = true
  try {
    await serverApi.createServer({
      name: newServer.value.name,
      url: newServer.value.url,
      api_key: newServer.value.api_key
    })
    message.success(messageText.ADD_SUCCESS)
    showAddServerModal.value = false
    newServer.value = { name: '', url: '', api_key: '' }
    await fetchCurrent()
  } catch (e: any) {
    message.error(messageText.ADD_FAILED + ': ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    saving.value = false
  }
}

const handleActivate = async (serverId: string) => {
  const success = await activateServer(serverId)
  if (success) {
    message.success('已切换当前激活服务器')
    await fetchCurrent()
  } else {
    message.error('切换失败')
  }
}

const handleDelete = async (serverId: string) => {
  try {
    await serverApi.deleteServer(serverId)
    message.success(messageText.DELETE_SUCCESS)
    await fetchCurrent()
  } catch (e: any) {
    message.error(messageText.DELETE_FAILED + ': ' + (e.response?.data?.detail || '未知错误'))
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await configApi.saveGlobal({
      tmdb_api_key: settings.tmdb_api_key,
      bangumi_api_token: settings.bangumi_token
    })
    message.success(messageText.SETTINGS_SAVED)
  } catch (e: any) {
    message.error(messageText.SAVE_FAILED + ': ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    saving.value = false
  }
}

const checkUpdate = () => {
  message.info('已是最新版本')
}

const exportData = () => {
  window.open('/api/system/config/export', '_blank')
}

const triggerImport = () => {
  fileInputRef.value?.click()
}

const handleImport = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) return
  
  const file = input.files[0]
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    await configApi.importConfig(formData)
    message.success('配置导入成功，页面将刷新以应用更改')
    setTimeout(() => location.reload(), 1500)
  } catch (e: any) {
    message.error(messageText.IMPORT_FAILED + ': ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    input.value = ''
  }
}

const clearCache = () => {
  localStorage.clear()
  message.success(messageText.CLEAR_SUCCESS)
}

onMounted(fetchCurrent)
</script>

<style scoped>
.mobile-settings {
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

.servers-card,
.api-card,
.appearance-card,
.system-card,
.data-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.server-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 12px;
}

.server-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.server-info {
  flex: 1;
}

.server-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.server-url {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.server-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.setting-item,
.info-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.setting-item:last-child,
.info-item:last-child {
  border-bottom: none;
}

.setting-label,
.info-label {
  font-size: 14px;
  color: var(--text-color);
}

.info-value {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
}
</style>
