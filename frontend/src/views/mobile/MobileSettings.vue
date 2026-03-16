<template>
  <div class="mobile-settings">
    <div class="page-header">
      <h1 class="page-title">系统集成配置</h1>
      <p class="page-desc">统一管理您的 Emby 核心凭据与第三方扩展 API 密钥</p>
    </div>

    <!-- Emby 服务端管理 -->
    <n-card class="servers-card" :bordered="false" title="Emby 服务端管理">
      <n-space vertical>
        <n-button block :type="buttonTypes.PRIMARY" @click="openAddModal">
          {{ buttonText.ADD_SERVER }}
        </n-button>
        <div v-if="servers.length === 0" class="empty-state">
          <n-empty :description="messageText.NO_SERVERS" />
        </div>
        <div v-else class="server-list">
          <div v-for="s in servers" :key="s.id" class="server-item" :class="{ active: s.id === activeServerId }">
            <div class="server-info">
              <div class="server-name">{{ s.name }}</div>
              <div class="server-url">{{ s.url }}</div>
              <div class="server-status">
                <n-tag v-if="s.id === activeServerId" :type="tagTypes.SUCCESS" :size="buttonSizes.TINY">
                  {{ statusText.ACTIVE }}
                </n-tag>
                <n-tag v-else :type="tagTypes.DEFAULT" :size="buttonSizes.TINY">
                  {{ statusText.INACTIVE }}
                </n-tag>
              </div>
            </div>
            <div class="server-actions">
              <n-button :size="buttonSizes.MEDIUM" secondary @click="openEditModal(s)">
                {{ buttonText.CONFIG }}
              </n-button>
              <n-button v-if="s.id !== activeServerId" :size="buttonSizes.MEDIUM" :type="buttonTypes.PRIMARY" secondary @click="handleActivate(s.id)">
                {{ buttonText.ACTIVATE }}
              </n-button>
              <n-popconfirm @positive-click="() => handleDelete(s.id)" :positive-text="buttonText.CONFIRM" :negative-text="buttonText.CANCEL">
                <template #trigger>
                  <n-button :size="buttonSizes.MEDIUM" :type="buttonTypes.ERROR" secondary>
                    {{ buttonText.DELETE }}
                  </n-button>
                </template>
                {{ messageText.DELETE_CONFIRM }}
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <!-- 第三方 API 扩展集成 -->
    <n-card class="api-card" :bordered="false" title="第三方 API 扩展集成">
      <n-space vertical>
        <div class="api-item">
          <div class="api-label">TMDB API Key</div>
          <n-input-group>
            <n-input v-model:value="globalConfig.tmdb_api_key" type="password" show-password-on="click" placeholder="The Movie Database V3 Key" />
            <n-button secondary @click="handleCopy(globalConfig.tmdb_api_key)">
              {{ buttonText.COPY }}
            </n-button>
          </n-input-group>
        </div>
        <div class="api-item">
          <div class="api-label">Bangumi API Token</div>
          <n-input-group>
            <n-input v-model:value="globalConfig.bangumi_api_token" type="password" show-password-on="click" placeholder="Bangumi Access Token" />
            <n-button secondary @click="handleCopy(globalConfig.bangumi_api_token)">
              {{ buttonText.COPY }}
            </n-button>
          </n-input-group>
        </div>
        <n-button block :type="buttonTypes.PRIMARY" :loading="savingGlobal" @click="handleSaveGlobal">
          {{ buttonText.SAVE_API_CONFIG }}
        </n-button>
      </n-space>
    </n-card>

    <!-- 网络代理设置 -->
    <n-card class="proxy-card" :bordered="false" title="网络代理设置">
      <n-space vertical>
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-label">启用全局代理</div>
            <div class="setting-desc">启用后所有网络请求将通过代理服务器</div>
          </div>
          <MobileSwitch v-model="globalConfig.proxy.enabled" />
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-label">排除 Emby 服务器</div>
            <div class="setting-desc">Emby 服务器直连，不经过代理</div>
          </div>
          <MobileSwitch v-model="globalConfig.proxy.exclude_emby" />
        </div>
        <div v-if="globalConfig.proxy.enabled" class="proxy-url">
          <div class="setting-label">代理服务器地址</div>
          <n-input v-model:value="globalConfig.proxy.url" placeholder="http://127.0.0.1:7890" />
        </div>
        <n-button block :type="buttonTypes.PRIMARY" :loading="savingGlobal" @click="handleSaveGlobal">
          {{ buttonText.SAVE_PROXY_CONFIG }}
        </n-button>
      </n-space>
    </n-card>

    <!-- 会话管理 -->
    <n-card class="session-card" :bordered="false" title="会话管理">
      <n-space vertical>
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-label">会话永不过期</div>
            <div class="setting-desc">开启后，登录会话将不会自动过期，直到用户主动登出或被管理员踢出。关闭后，会话将在 24 小时后自动过期。</div>
          </div>
          <MobileSwitch v-model="globalConfig.session_never_expire" />
        </div>
        <n-button block :type="buttonTypes.PRIMARY" :loading="savingGlobal" @click="handleSaveGlobal">
          {{ buttonText.SAVE_SESSION_CONFIG }}
        </n-button>
      </n-space>
    </n-card>

    <!-- 数据备份与迁移 -->
    <n-card class="backup-card" :bordered="false" title="数据备份与迁移">
      <n-space vertical>
        <n-text depth="3" style="font-size: 13px">
          您可以导出当前的全局配置文件 (config.json) 进行备份，或在迁移环境时导入旧配置。
        </n-text>
        <n-button block secondary @click="handleExportConfig">
          {{ buttonText.EXPORT_CONFIG }}
        </n-button>
        <n-button block :type="buttonTypes.PRIMARY" ghost @click="triggerImportConfig">
          {{ buttonText.IMPORT_BACKUP }}
        </n-button>
        <input 
          type="file" 
          ref="fileInputRef" 
          style="display: none" 
          accept=".json" 
          @change="handleImportConfig" 
        />
      </n-space>
    </n-card>

    <!-- 配置贴士 -->
    <n-card class="tips-card" :bordered="false" title="配置贴士">
      <n-space vertical>
        <div class="tip-item">
          <div class="tip-label">TMDB</div>
          <div class="tip-desc">元数据抓取的核心，建议配置 V3 Key。</div>
        </div>
        <div class="tip-item">
          <div class="tip-label">代理</div>
          <div class="tip-desc">如果您无法连接外网，请在此配置 HTTP/SOCKS 代理。</div>
        </div>
        <div class="tip-item">
          <div class="tip-label">多服务器</div>
          <div class="tip-desc">Lens 支持多实例管理，您可以随时切换当前激活的服务器。</div>
        </div>
      </n-space>
    </n-card>

    <!-- 服务器配置弹窗 -->
    <n-modal v-model:show="showServerModal" preset="card" :title="editingServer ? buttonText.EDIT_SERVER : buttonText.ADD_SERVER" style="width: 90vw; max-width: 500px">
      <n-form label-placement="top" :size="formSizes.SMALL">
        <n-form-item :label="formLabel.SERVER_NAME">
          <n-input v-model:value="serverForm.name" :placeholder="placeholder.SERVER_NAME" />
        </n-form-item>
        <n-form-item :label="formLabel.SERVER_URL">
          <n-input v-model:value="serverForm.url" :placeholder="placeholder.SERVER_URL" />
        </n-form-item>
        <n-form-item :label="formLabel.API_KEY">
          <n-input v-model:value="serverForm.api_key" type="password" show-password-on="click" :placeholder="placeholder.API_KEY" />
        </n-form-item>
        <n-form-item :label="formLabel.USER_ID">
          <n-input v-model:value="serverForm.user_id" :placeholder="placeholder.USER_ID" />
        </n-form-item>
        
        <n-divider />
        
        <div class="auth-section-title">身份认证 (增强功能)</div>
        
        <n-form-item :label="formLabel.EMBY_USERNAME">
          <n-input v-model:value="serverForm.username" :placeholder="placeholder.EMBY_USERNAME" />
        </n-form-item>
        <n-form-item :label="formLabel.EMBY_PASSWORD">
          <n-input v-model:value="serverForm.password" type="password" show-password-on="click" :placeholder="placeholder.EMBY_PASSWORD" />
        </n-form-item>
        <n-form-item :label="formLabel.SESSION_TOKEN">
          <n-input v-model:value="serverForm.session_token" disabled :placeholder="placeholder.SESSION_TOKEN" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space vertical style="width: 100%">
          <n-button block secondary @click="handleTest" :loading="testing">
            {{ buttonText.TEST_CONNECTION }}
          </n-button>
          <n-button block :type="buttonTypes.INFO" secondary @click="handleLogin" :loading="loggingIn">
            {{ buttonText.LOGIN_AUTH }}
          </n-button>
          <n-space>
            <n-button secondary @click="showServerModal = false">{{ buttonText.CANCEL }}</n-button>
            <n-button :type="buttonTypes.PRIMARY" @click="saveServer" :loading="savingServer">{{ buttonText.SAVE }}</n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NTag, NPopconfirm, NText, NInputGroup, NDivider, useMessage } from 'naive-ui'
import { systemApi } from '@/api/system'
import { servers, activeServerId } from '@/store/serverStore'
import MobileSwitch from './components/MobileSwitch.vue'
import {
  ButtonTypes,
  ButtonSizes,
  TagTypes,
  FormSizes,
  ButtonText,
  StatusText,
  MessageText,
} from './constants'
import axios from 'axios'

const message = useMessage()

const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const tagTypes = TagTypes
const formSizes = FormSizes
const buttonText = ButtonText
const statusText = StatusText
const messageText = MessageText

const formLabel = {
  SERVER_NAME: '服务器名称',
  SERVER_URL: '服务器地址',
  API_KEY: 'API 密钥',
  USER_ID: '用户 ID',
  EMBY_USERNAME: 'Emby 用户名',
  EMBY_PASSWORD: 'Emby 密码',
  SESSION_TOKEN: '会话令牌',
}

const placeholder = {
  SERVER_NAME: '例如：我的 Emby 服务器',
  SERVER_URL: 'http://localhost:8096',
  API_KEY: '请输入 API 密钥',
  USER_ID: '可选，由系统自动识别',
  EMBY_USERNAME: '管理员用户名',
  EMBY_PASSWORD: '请输入密码',
  SESSION_TOKEN: '登录后自动填充',
}

const globalConfig = ref({
  tmdb_api_key: '',
  bangumi_api_token: '',
  proxy: {
    enabled: false,
    exclude_emby: false,
    url: ''
  },
  session_never_expire: false
})

const showServerModal = ref(false)
const editingServer = ref<any>(null)
const savingServer = ref(false)
const savingGlobal = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)
const testing = ref(false)
const loggingIn = ref(false)

const serverForm = ref({
  id: '',
  name: '',
  url: '',
  api_key: '',
  user_id: '',
  username: '',
  password: '',
  session_token: '',
  emby_id: ''
})

const fetchCurrent = async () => {
  try {
    const data: any = await systemApi.getConfig()
    globalConfig.value.tmdb_api_key = data.tmdb_api_key || ''
    globalConfig.value.bangumi_api_token = data.bangumi_api_token || ''
    globalConfig.value.proxy = data.proxy || { enabled: false, exclude_emby: false, url: '' }
    globalConfig.value.session_never_expire = data.session_never_expire || false
  } catch (e) {
    message.error(messageText.LOAD_FAILED)
  }
}

const handleSaveGlobal = async () => {
  savingGlobal.value = true
  try {
    await systemApi.saveConfig([
      { key: 'tmdb_api_key', value: globalConfig.value.tmdb_api_key },
      { key: 'bangumi_api_token', value: globalConfig.value.bangumi_api_token },
      { key: 'proxy', value: JSON.stringify(globalConfig.value.proxy) },
      { key: 'session_never_expire', value: String(globalConfig.value.session_never_expire) }
    ])
    message.success(messageText.SAVE_SUCCESS)
  } catch (e) {
    message.error(messageText.SAVE_FAILED)
  } finally {
    savingGlobal.value = false
  }
}

const openAddModal = () => {
  editingServer.value = null
  serverForm.value = { 
    id: '', 
    name: '新服务器', 
    url: '', 
    api_key: '', 
    user_id: '', 
    username: '', 
    password: '', 
    session_token: '', 
    emby_id: '' 
  }
  showServerModal.value = true
}

const openEditModal = (s: any) => {
  editingServer.value = s
  serverForm.value = { 
    id: s.id, 
    name: s.name, 
    url: s.url, 
    api_key: s.api_key, 
    user_id: s.user_id || '', 
    username: s.username || '', 
    password: s.password || '', 
    session_token: s.session_token || '', 
    emby_id: s.emby_id || '' 
  }
  showServerModal.value = true
}

const handleTest = async () => {
  if (!serverForm.value.url || !serverForm.value.api_key) {
    message.warning('请先填写 URL 和 API Key')
    return
  }
  testing.value = true
  try {
    const res = await axios.post('/api/server/test', serverForm.value)
    message.success(`连接成功: ${res.data.server_name || ''}`)
    if (res.data.server_id) serverForm.value.emby_id = res.data.server_id
  } catch (e: any) {
    message.error(e.response?.data?.detail || '连接失败')
  } finally {
    testing.value = false
  }
}

const handleLogin = async () => {
  if (!serverForm.value.username) {
    message.warning('请输入用户名')
    return
  }
  loggingIn.value = true
  try {
    const res = await axios.post('/api/server/login', { server_id: serverForm.value.id || null })
    message.success('登录成功')
    serverForm.value.session_token = res.data.token
  } catch (e: any) {
    message.error(e.response?.data?.detail || '登录失败')
  } finally {
    loggingIn.value = false
  }
}

const saveServer = async () => {
  if (!serverForm.value.name || !serverForm.value.url || !serverForm.value.api_key) {
    message.warning('请填写完整的服务器信息')
    return
  }
  savingServer.value = true
  try {
    await axios.post('/api/server/save', serverForm.value)
    message.success(messageText.SAVE_SUCCESS)
    showServerModal.value = false
    await fetchCurrent()
  } catch (e) {
    message.error(messageText.SAVE_FAILED)
  } finally {
    savingServer.value = false
  }
}

const handleActivate = async (id: number) => {
  try {
    await axios.post(`/api/server/${id}/activate`)
    message.success('服务器已激活')
    await fetchCurrent()
  } catch (e) {
    message.error('激活失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await axios.delete(`/api/server/${id}`)
    message.success(messageText.DELETE_SUCCESS)
    await fetchCurrent()
  } catch (e) {
    message.error(messageText.DELETE_FAILED)
  }
}

const handleCopy = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    message.success(messageText.COPY_SUCCESS)
  } catch (e) {
    message.error('复制失败')
  }
}

const handleExportConfig = async () => {
  try {
    const data: any = await systemApi.getConfig()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'config.json'
    a.click()
    URL.revokeObjectURL(url)
    message.success(messageText.EXPORT_SUCCESS)
  } catch (e) {
    message.error(messageText.EXPORT_FAILED)
  }
}

const triggerImportConfig = () => {
  fileInputRef.value?.click()
}

const handleImportConfig = async (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  try {
    const text = await file.text()
    const config = JSON.parse(text)
    await systemApi.saveConfig(Object.entries(config).map(([key, value]) => ({ key, value: String(value) })))
    message.success(messageText.IMPORT_SUCCESS)
    await fetchCurrent()
  } catch (e) {
    message.error(messageText.IMPORT_FAILED)
  }
  target.value = ''
}

onMounted(() => {
  fetchCurrent()
})
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
.proxy-card,
.session-card,
.backup-card,
.tips-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.server-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.server-item {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
}

.server-item.active {
  background: rgba(124, 58, 237, 0.1);
}

.server-info {
  margin-bottom: 8px;
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
  margin-bottom: 4px;
}

.server-status {
  display: flex;
  gap: 8px;
}

.server-actions {
  display: flex;
  gap: 8px;
}

.api-item {
  margin-bottom: 12px;
}

.api-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 8px;
}

.auth-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-color);
  margin: 16px 0 12px 0;
  padding-left: 8px;
  border-left: 3px solid #7c3aed;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
  margin-bottom: 12px;
}

.setting-info {
  flex: 1;
}

.setting-label {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.setting-desc {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.proxy-url {
  margin-bottom: 12px;
}

.tip-item {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
  margin-bottom: 8px;
}

.tip-label {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.tip-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.8;
}
</style>