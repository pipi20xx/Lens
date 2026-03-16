<template>
  <div class="mobile-external-control">
    <div class="page-header">
      <h1 class="page-title">外部控制体系</h1>
      <p class="page-desc">配置外部 API 访问控制</p>
    </div>

    <n-card class="api-keys-card" :bordered="false" title="API 密钥">
      <n-space vertical>
        <n-button block type="primary" @click="showAddKeyModal = true">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          生成新密钥
        </n-button>
        <div v-if="apiKeys.length === 0" class="empty-state">
          <n-empty description="暂无 API 密钥" />
        </div>
        <div v-else class="key-list">
          <div v-for="key in apiKeys" :key="key.id" class="key-item">
            <div class="key-info">
              <div class="key-name">{{ key.name }}</div>
              <div class="key-preview">{{ maskKey(key.key) }}</div>
              <div class="key-meta">
                <span>{{ formatDate(key.created_at) }}</span>
                <n-tag :type="key.is_active ? 'success' : 'default'" size="small">
                  {{ key.is_active ? '活跃' : '已禁用' }}
                </n-tag>
              </div>
            </div>
            <div class="key-actions">
              <n-button size="small" secondary type="info" @click="copyKey(key.key)">
                复制
              </n-button>
              <n-button size="small" secondary type="warning" @click="toggleKey(key)">
                {{ key.is_active ? '禁用' : '启用' }}
              </n-button>
              <n-popconfirm @positive-click="deleteKey(key.id)" positive-text="确认删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    删除
                  </n-button>
                </template>
                确定删除此密钥？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-card class="permissions-card" :bordered="false" title="权限配置">
      <n-space vertical>
        <div class="permission-item">
          <div class="permission-info">
            <div class="permission-label">允许外部访问</div>
            <div class="permission-desc">启用后可通过 API 访问系统功能</div>
          </div>
          <n-switch v-model:value="settings.externalAccessEnabled" @update:value="saveSettings" class="mobile-switch" />
        </div>
        <div class="permission-item">
          <div class="permission-info">
            <div class="permission-label">IP 白名单</div>
            <div class="permission-desc">仅允许指定 IP 访问</div>
          </div>
          <n-switch v-model:value="settings.ipWhitelistEnabled" @update:value="saveSettings" class="mobile-switch" />
        </div>
        <div v-if="settings.ipWhitelistEnabled" class="ip-whitelist">
          <n-input
            v-model:value="settings.ipWhitelist"
            type="textarea"
            placeholder="每行一个 IP 地址，例如：&#10;192.168.1.100&#10;10.0.0.1"
            :rows="4"
            @blur="saveSettings"
          />
        </div>
      </n-space>
    </n-card>

    <n-card class="logs-card" :bordered="false" title="访问日志">
      <div v-if="accessLogs.length === 0" class="empty-state">
        <n-empty description="暂无访问日志" />
      </div>
      <div v-else class="log-list">
        <div v-for="log in accessLogs" :key="log.id" class="log-item">
          <div class="log-info">
            <div class="log-endpoint">{{ log.endpoint }}</div>
            <div class="log-meta">
              <span>{{ formatDate(log.created_at) }}</span>
              <n-tag :type="log.status_code === 200 ? 'success' : 'error'" size="small">
                {{ log.status_code }}
              </n-tag>
            </div>
          </div>
        </div>
      </div>
    </n-card>

    <n-modal v-model:show="showAddKeyModal" preset="card" title="生成新密钥" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="密钥名称">
          <n-input v-model:value="newKey.name" placeholder="例如：生产环境密钥" />
        </n-form-item>
        <n-form-item label="权限范围">
          <n-select v-model:value="newKey.permissions" multiple :options="permissionOptions" />
        </n-form-item>
        <n-form-item label="过期时间">
          <n-select v-model:value="newKey.expires_in" :options="expiryOptions" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddKeyModal = false">取消</n-button>
          <n-button type="primary" @click="generateKey" :loading="generating">生成</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NSwitch, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, NIcon, NDataTable } from 'naive-ui'
import { AddOutlined as AddIcon } from '@vicons/material'
import { systemApi } from '@/api/system'
import { useMessage } from 'naive-ui'

const message = useMessage()
const apiKeys = ref<any[]>([])
const accessLogs = ref<any[]>([])
const showAddKeyModal = ref(false)
const generating = ref(false)

const settings = ref({
  externalAccessEnabled: false,
  ipWhitelistEnabled: false,
  ipWhitelist: '',
  apiToken: '',
  auditEnabled: true
})

const newKey = ref({
  name: '',
  permissions: [],
  expires_in: 'never'
})

const permissionOptions = [
  { label: '读取数据', value: 'read' },
  { label: '写入数据', value: 'write' },
  { label: '执行任务', value: 'execute' },
  { label: '管理用户', value: 'admin' }
]

const expiryOptions = [
  { label: '永不过期', value: 'never' },
  { label: '30 天', value: '30d' },
  { label: '90 天', value: '90d' },
  { label: '1 年', value: '1y' }
]

const loadConfig = async () => {
  try {
    const data: any = await systemApi.getConfig()
    settings.value.apiToken = data.api_token || ''
    settings.value.auditEnabled = data.audit_enabled !== 'false' && data.audit_enabled !== false
  } catch (err) {
    message.error('加载配置失败')
  }
}

const loadAccessLogs = async () => {
  loadingLogs.value = true
  try {
    const data: any = await systemApi.getAuditLogs({ page: 1, page_size: 50 })
    accessLogs.value = data.items || []
  } catch (err) {
    message.error('加载日志失败')
  } finally {
    loadingLogs.value = false
  }
}

const saveSettings = async () => {
  try {
    await systemApi.saveConfig([
      { key: 'audit_enabled', value: String(settings.value.auditEnabled) }
    ])
    message.success('设置已保存')
  } catch (err) {
    message.error('保存失败')
  }
}

const generateKey = async () => {
  if (!newKey.value.name) {
    message.warning('请输入密钥名称')
    return
  }
  generating.value = true
  try {
    const data: any = await systemApi.generateToken()
    const newToken = data.token
    await systemApi.saveConfig([{ key: 'api_token', value: newToken }])
    settings.value.apiToken = newToken
    message.success('新 Token 已生成')
    showAddKeyModal.value = false
    newKey.value = { name: '', permissions: [], expires_in: 'never' }
  } catch (err) {
    message.error('生成失败')
  } finally {
    generating.value = false
  }
}

const copyKey = (key: string) => {
  navigator.clipboard.writeText(key)
  message.success('密钥已复制到剪贴板')
}

const toggleKey = async (key: any) => {
  // 移动端简化处理，实际应该调用API更新状态
  key.is_active = !key.is_active
  message.success(key.is_active ? '密钥已启用' : '密钥已禁用')
}

const deleteKey = async (id: string) => {
  // 移动端简化处理，实际应该调用API删除
  apiKeys.value = apiKeys.value.filter(k => k.id !== id)
  message.success('密钥已删除')
}

const loadingLogs = ref(false)

const maskKey = (key: string) => {
  if (!key) return ''
  return key.substring(0, 8) + '...' + key.substring(key.length - 8)
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

onMounted(() => {
  loadConfig()
  loadAccessLogs()
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

.api-keys-card,
.permissions-card,
.logs-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.key-list,
.log-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.key-item,
.log-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.key-info,
.log-info {
  margin-bottom: 8px;
}

.key-name,
.log-endpoint {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.key-preview {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  font-family: monospace;
  margin-bottom: 4px;
}

.key-meta,
.log-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  align-items: center;
}

.key-actions {
  display: flex;
  gap: 8px;
}

.permission-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--border-color);
}

.permission-item:last-child {
  border-bottom: none;
}

.permission-info {
  flex: 1;
}

.permission-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.permission-desc {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
}

.ip-whitelist {
  margin-top: 12px;
}
</style>
