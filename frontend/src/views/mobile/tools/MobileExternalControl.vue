<template>
  <div class="mobile-external-control">
    <div class="page-header">
      <h1 class="page-title">外部控制体系</h1>
      <p class="page-desc">管理 API 认证、安全审计及自动化对接配置</p>
    </div>

    <n-card class="token-card" :bordered="false" title="API Token">
      <n-space vertical>
        <div class="token-display">
          <n-input
            v-model:value="config.api_token"
            :type="showFullToken ? 'text' : 'password'"
            show-password-on="click"
            placeholder="尚未设置 Token"
            readonly
            @click="showFullToken = !showFullToken"
            class="token-input"
          />
        </div>
        <div class="token-actions">
          <n-button block :type="buttonTypes.PRIMARY" secondary @click="copyToken" :disabled="!config.api_token">
            {{ buttonText.COPY }}
          </n-button>
          <n-button block secondary @click="generateNewToken">
            {{ buttonText.REGENERATE }}
          </n-button>
        </div>
        <n-alert :type="buttonTypes.INFO" :size="buttonSizes.TINY">
          Token 用于外部系统通过 /api 接口与本系统交互，拥有系统所有接口的操作权限。
        </n-alert>
      </n-space>
    </n-card>

    <n-card class="audit-card" :bordered="false" title="审计策略">
      <n-space vertical>
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-label">开启全局审计</div>
            <div class="setting-desc">记录所有 API 请求的方法、路径及状态码</div>
          </div>
          <MobileSwitch v-model="config.audit_enabled" @update:model-value="saveSettings" />
        </div>
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-label">Payload 捕获</div>
            <div class="setting-desc">自动脱敏并存储请求 Body 内容</div>
          </div>
          <MobileSwitch :value="config.audit_enabled" disabled />
        </div>
      </n-space>
    </n-card>

    <n-card class="logs-card" :bordered="false" title="访问日志">
      <div v-if="auditLogs.length === 0" class="empty-state">
        <n-empty :description="messageText.EMPTY_DATA" />
      </div>
      <div v-else class="log-list">
        <div v-for="log in auditLogs" :key="log.id" class="log-item" @click="viewLogDetail(log)">
          <div class="log-header">
            <n-tag :type="log.method === 'GET' ? tagTypes.SUCCESS : tagTypes.INFO" :size="buttonSizes.SMALL">
              {{ log.method }}
            </n-tag>
            <n-tag :type="log.status_code < 400 ? tagTypes.SUCCESS : tagTypes.ERROR" :size="buttonSizes.SMALL">
              {{ log.status_code }}
            </n-tag>
          </div>
          <div class="log-path">{{ log.path }}</div>
          <div class="log-meta">
            <span>{{ formatDate(log.timestamp) }}</span>
            <span>{{ log.client_ip }}</span>
            <span>{{ log.process_time.toFixed(1) }}ms</span>
          </div>
        </div>
      </div>
    </n-card>

    <n-modal v-model:show="showLogDetail" preset="card" title="请求详情" style="width: 90vw; max-width: 600px">
      <div class="detail-wrapper">
        <n-code :code="currentPayload" language="json" word-wrap />
      </div>
      <template #action>
        <n-button :type="buttonTypes.PRIMARY" @click="showLogDetail = false">
          {{ buttonText.CLOSE }}
        </n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NInput, NTag, NAlert, NCode, useMessage } from 'naive-ui'
import { systemApi } from '@/api/system'
import MobileSwitch from '../components/MobileSwitch.vue'
import {
  ButtonTypes,
  ButtonSizes,
  TagTypes,
  ButtonText,
  MessageText,
} from '../constants'

const message = useMessage()

const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const tagTypes = TagTypes
const buttonText = ButtonText
const messageText = MessageText

const config = ref({
  api_token: '',
  audit_enabled: false
})

const auditLogs = ref<any[]>([])
const showFullToken = ref(false)
const showLogDetail = ref(false)
const currentPayload = ref('')
const loadingLogs = ref(false)

const loadConfig = async () => {
  try {
    const data: any = await systemApi.getConfig()
    config.value.api_token = data.api_token || ''
    config.value.audit_enabled = data.audit_enabled === 'true' || data.audit_enabled === true
  } catch (err) {
    message.error(messageText.OPERATION_FAILED)
  }
}

const loadAuditLogs = async () => {
  loadingLogs.value = true
  try {
    const data: any = await systemApi.getAuditLogs({ page: 1, page_size: 50 })
    auditLogs.value = data.items || []
  } catch (err) {
    message.error(messageText.OPERATION_FAILED)
  } finally {
    loadingLogs.value = false
  }
}

const saveSettings = async () => {
  try {
    await systemApi.saveConfig([
      { key: 'audit_enabled', value: String(config.value.audit_enabled) }
    ])
    message.success(messageText.SETTINGS_SAVED)
  } catch (err) {
    message.error(messageText.SAVE_FAILED)
  }
}

const copyToken = () => {
  navigator.clipboard.writeText(config.value.api_token)
  message.success(messageText.COPY_SUCCESS)
}

const generateNewToken = async () => {
  try {
    const data: any = await systemApi.generateToken()
    config.value.api_token = data.token
    await systemApi.saveConfig([{ key: 'api_token', value: data.token }])
    message.success('Token 已重新生成')
  } catch (err) {
    message.error('生成失败')
  }
}

const viewLogDetail = (log: any) => {
  try {
    currentPayload.value = JSON.stringify(JSON.parse(log.payload || '{}'), null, 2)
  } catch {
    currentPayload.value = log.payload || '无数据'
  }
  showLogDetail.value = true
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

onMounted(() => {
  loadConfig()
  loadAuditLogs()
})
</script>

<style scoped>
.mobile-external-control {
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

.token-card,
.audit-card,
.logs-card {
  margin-bottom: 12px;
}

.token-display {
  margin-bottom: 12px;
}

.token-input {
  cursor: pointer;
}

.token-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
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

.empty-state {
  padding: 24px 0;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.log-item {
  padding: 12px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
  cursor: pointer;
}

.log-header {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.log-path {
  font-size: 14px;
  color: var(--text-color);
  margin-bottom: 8px;
  word-break: break-all;
}

.log-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.detail-wrapper {
  background-color: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  max-height: 400px;
  overflow-y: auto;
}
</style>
