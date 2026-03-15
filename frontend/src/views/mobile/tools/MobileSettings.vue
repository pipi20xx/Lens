<template>
  <div class="mobile-settings">
    <div class="page-header">
      <h1 class="page-title">系统设置</h1>
      <p class="page-desc">配置系统参数与偏好</p>
    </div>

    <n-card class="servers-card" :bordered="false" title="Emby 服务器">
      <n-space vertical>
        <div v-if="servers.length === 0" class="empty-state">
          <n-empty description="暂无服务器配置" />
        </div>
        <div v-else class="server-list">
          <div v-for="server in servers" :key="server.id" class="server-item">
            <div class="server-info">
              <div class="server-name">{{ server.name }}</div>
              <div class="server-url">{{ server.url }}</div>
            </div>
            <n-tag v-if="server.id === activeServerId" type="success" size="small" round>
              已激活
            </n-tag>
          </div>
        </div>
        <n-button block type="primary" secondary @click="showAddServerModal = true">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          添加服务器
        </n-button>
      </n-space>
    </n-card>

    <n-card class="api-card" :bordered="false" title="API 配置">
      <n-space vertical>
        <n-form-item label="TMDB API Key">
          <n-input v-model:value="settings.tmdb_api_key" type="password" show-password-on="click" placeholder="The Movie Database V3 Key" />
        </n-form-item>
        <n-form-item label="Bangumi API Token">
          <n-input v-model:value="settings.bangumi_token" type="password" show-password-on="click" placeholder="Bangumi API Token" />
        </n-form-item>
        <n-button block type="primary" @click="saveSettings" :loading="saving">
          保存配置
        </n-button>
      </n-space>
    </n-card>

    <n-card class="appearance-card" :bordered="false" title="外观设置">
      <n-space vertical>
        <div class="setting-item">
          <span class="setting-label">主题模式</span>
          <n-radio-group v-model:value="settings.theme" @update:value="saveSettings">
            <n-radio value="light">浅色</n-radio>
            <n-radio value="dark">深色</n-radio>
            <n-radio value="auto">自动</n-radio>
          </n-radio-group>
        </div>
        <div class="setting-item">
          <span class="setting-label">语言</span>
          <n-select v-model:value="settings.language" :options="languageOptions" @update:value="saveSettings" />
        </div>
      </n-space>
    </n-card>

    <n-card class="system-card" :bordered="false" title="系统信息">
      <n-space vertical>
        <div class="info-item">
          <span class="info-label">版本</span>
          <span class="info-value">{{ version }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">构建时间</span>
          <span class="info-value">{{ buildTime }}</span>
        </div>
        <n-button block type="info" secondary @click="checkUpdate">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          检查更新
        </n-button>
      </n-space>
    </n-card>

    <n-card class="data-card" :bordered="false" title="数据管理">
      <n-space vertical>
        <n-button block type="warning" secondary @click="exportData">
          <template #icon><n-icon><DownloadIcon /></n-icon></template>
          导出数据
        </n-button>
        <n-button block type="info" secondary @click="importData">
          <template #icon><n-icon><UploadIcon /></n-icon></template>
          导入数据
        </n-button>
        <n-button block type="error" secondary @click="clearCache">
          <template #icon><n-icon><DeleteIcon /></n-icon></template>
          清除缓存
        </n-button>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddServerModal" preset="card" title="添加服务器" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="服务器名称">
          <n-input v-model:value="newServer.name" placeholder="例如：主服务器" />
        </n-form-item>
        <n-form-item label="服务器地址">
          <n-input v-model:value="newServer.url" placeholder="http://192.168.1.1:8096" />
        </n-form-item>
        <n-form-item label="API 密钥">
          <n-input v-model:value="newServer.api_key" type="password" show-password-on="click" placeholder="Emby API Key" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddServerModal = false">取消</n-button>
          <n-button type="primary" @click="addServer" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NTag, NRadioGroup, NRadio, NSelect, NIcon } from 'naive-ui'
import { AddOutlined as AddIcon, RefreshOutlined as RefreshIcon, DownloadOutlined as DownloadIcon, UploadOutlined as UploadIcon, DeleteOutlineOutlined as DeleteIcon } from '@vicons/material'
import { useMessage } from 'naive-ui'

const message = useMessage()
const servers = ref<any[]>([])
const activeServerId = ref<number | null>(null)
const showAddServerModal = ref(false)
const saving = ref(false)

const settings = ref({
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

const version = '1.0.0'
const buildTime = '2024-01-01'

const languageOptions = [
  { label: '简体中文', value: 'zh-CN' },
  { label: 'English', value: 'en-US' }
]

const addServer = () => {
  if (!newServer.value.name || !newServer.value.url) {
    message.warning('请填写完整的服务器信息')
    return
  }
  saving.value = true
  setTimeout(() => {
    servers.value.push({
      id: Date.now(),
      ...newServer.value
    })
    if (!activeServerId.value) {
      activeServerId.value = servers.value[0].id
    }
    message.success('服务器添加成功')
    showAddServerModal.value = false
    newServer.value = { name: '', url: '', api_key: '' }
    saving.value = false
  }, 500)
}

const saveSettings = () => {
  saving.value = true
  setTimeout(() => {
    message.success('设置已保存')
    saving.value = false
  }, 500)
}

const checkUpdate = () => {
  message.info('已是最新版本')
}

const exportData = () => {
  message.info('请在桌面端导出数据')
}

const importData = () => {
  message.info('请在桌面端导入数据')
}

const clearCache = () => {
  message.success('缓存已清除')
}

servers.value = [
  { id: 1, name: '主服务器', url: 'http://192.168.1.1:8096' }
]
activeServerId.value = 1
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
