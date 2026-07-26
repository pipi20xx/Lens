<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { systemApi } from '@/api/system'
import { useNotification } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()

const activeTab = ref('api_key')
const config = reactive<any>({
  api_token: '',
  auth_enabled: true,
  audit_enabled: false,
})
const showFullToken = ref(false)
const loading = ref(false)
const loadingLogs = ref(false)
const auditLogs = ref<any[]>([])
const showLogDetail = ref(false)
const currentPayload = ref('')
const pagination = reactive({ page: 1, pageSize: 20, itemCount: 0 })

async function loadConfig() {
  try {
    loading.value = true
    const data = await systemApi.getConfig()
    if (data && typeof data === 'object') {
      config.api_token = data.api_token || ''
      config.auth_enabled = data.auth_enabled !== false
      config.audit_enabled = data.audit_enabled === true
    }
  } catch {
    showError('加载配置失败')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  try {
    await systemApi.saveConfig([
      { key: 'auth_enabled', value: config.auth_enabled },
      { key: 'audit_enabled', value: config.audit_enabled },
    ])
    success('设置已保存')
  } catch {
    showError('保存失败')
  }
}

async function generateNewToken() {
  try {
    const data = await systemApi.generateToken()
    config.api_token = data?.token || data?.api_token || ''
    success('Token 已重新生成')
  } catch {
    showError('生成 Token 失败')
  }
}

function copyToken() {
  if (config.api_token) {
    navigator.clipboard.writeText(config.api_token)
    success('Token 已复制到剪贴板')
  }
}

async function fetchLogs() {
  try {
    loadingLogs.value = true
    const data = await systemApi.getAuditLogs({
      page: pagination.page,
      page_size: pagination.pageSize,
    })
    auditLogs.value = data?.items || data || []
    pagination.itemCount = data?.total || auditLogs.value.length
  } catch {
    showError('加载审计日志失败')
  } finally {
    loadingLogs.value = false
  }
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchLogs()
}

function showPayload(row: any) {
  try {
    currentPayload.value = JSON.stringify(JSON.parse(row.payload), null, 2)
  } catch {
    currentPayload.value = row.payload || ''
  }
  showLogDetail.value = true
}

const docsUrl = ref('')

onMounted(() => {
  loadConfig()
  fetchLogs()
  docsUrl.value = systemApi.getDocsUrl(config.api_token)
})
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-shield-lock-outline</v-icon>
      外部控制体系
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">管理 API 认证、安全审计及自动化对接配置，为外部脚本和第三方应用提供能力支撑。</p>

    <v-tabs v-model="activeTab" class="mb-4">
      <v-tab value="api_key"><v-icon start>mdi-key-outline</v-icon> API 密钥</v-tab>
      <v-tab value="settings"><v-icon start>mdi-cog-outline</v-icon> 安全设置</v-tab>
      <v-tab value="logs"><v-icon start>mdi-history</v-icon> 访问日志</v-tab>
      <v-tab value="docs"><v-icon start>mdi-file-document-outline</v-icon> API 文档</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- 1. API 密钥 -->
      <v-window-item value="api_key">
        <v-row>
          <v-col cols="12" md="8">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="pa-4">令牌管理</v-card-title>
              <v-divider />
              <v-card-text class="pa-4">
                <v-text-field
                  v-model="config.api_token"
                  :type="showFullToken ? 'text' : 'password'"
                  :append-inner-icon="showFullToken ? 'mdi-eye-off' : 'mdi-eye'"
                  @click:append-inner="showFullToken = !showFullToken"
                  label="当前生效的 API Token"
                  variant="outlined"
                  readonly
                  class="mb-3"
                />
                <div class="d-flex ga-2">
                  <v-btn color="primary" variant="tonal" prepend-icon="mdi-content-copy" @click="copyToken" :disabled="!config.api_token">复制数据</v-btn>
                  <v-btn variant="tonal" color="warning" prepend-icon="mdi-refresh" @click="generateNewToken">重新生成</v-btn>
                </div>
                <p class="text-caption text-medium-emphasis mt-3">
                  注意：更改 Token 后，所有已对接的外部应用（如自动化脚本、Webhook 触发器）需要同步更新。
                </p>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="pa-4">安全说明</v-card-title>
              <v-divider />
              <v-card-text class="pa-4">
                <v-alert type="info" variant="tonal" class="mb-3" rounded="lg">Token 安全性</v-alert>
                <p class="text-body-2 text-medium-emphasis">
                  1. <b>权限等同管理员</b>：Token 拥有系统所有接口的操作权限。<br/>
                  2. <b>加密存储</b>：Token 在数据库中加密存储，无法反向解密。<br/>
                  3. <b>泄露处理</b>：如果怀疑 Token 泄露，请立即点击"重新生成"。
                </p>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <!-- 2. 安全设置 -->
      <v-window-item value="settings">
        <v-row>
          <v-col cols="12" md="8">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="pa-4">审计策略</v-card-title>
              <v-divider />
              <v-card-text class="pa-4">
                <div class="d-flex align-center justify-space-between mb-4">
                  <div>
                    <div class="text-subtitle-2 font-weight-bold">开启全局审计</div>
                    <div class="text-caption text-medium-emphasis">记录所有 API 请求的方法、路径及状态码</div>
                  </div>
                  <v-switch v-model="config.audit_enabled" @update:model-value="saveSettings" color="primary" density="compact" hide-details />
                </div>
                <v-divider class="mb-4" />
                <div class="d-flex align-center justify-space-between">
                  <div>
                    <div class="text-subtitle-2 font-weight-bold">Payload 捕获</div>
                    <div class="text-caption text-medium-emphasis">自动脱敏并存储请求 Body 内容</div>
                  </div>
                  <v-switch :model-value="config.audit_enabled" disabled density="compact" hide-details />
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="pa-4">设置说明</v-card-title>
              <v-divider />
              <v-card-text class="pa-4">
                <p class="text-body-2 text-medium-emphasis">
                  <b>审计日志：</b>开启审计会产生少量的数据库写入开销，但对于回溯系统操作和定位自动化对接问题非常有帮助。
                </p>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-window-item>

      <!-- 3. 访问日志 -->
      <v-window-item value="logs">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="d-flex align-center pa-4">
            <span>审计日志记录</span>
            <v-spacer />
            <v-btn variant="tonal" color="info" size="small" prepend-icon="mdi-refresh" @click="fetchLogs" :loading="loadingLogs">刷新</v-btn>
          </v-card-title>
          <v-divider />
          <v-table class="bg-transparent">
            <thead>
              <tr><th>时间</th><th>方法</th><th>路径</th><th>状态</th><th>来源 IP</th><th>耗时</th><th class="text-right">操作</th></tr>
            </thead>
            <tbody>
              <tr v-if="!loadingLogs && !auditLogs.length"><td colspan="7" class="text-center py-8 text-medium-emphasis">暂无审计日志</td></tr>
              <tr v-for="row in auditLogs" :key="row.id">
                <td class="text-medium-emphasis" style="font-size:12px">{{ new Date(row.timestamp).toLocaleString() }}</td>
                <td><v-chip :color="row.method === 'GET' ? 'success' : 'info'" size="small" variant="tonal" label>{{ row.method }}</v-chip></td>
                <td class="font-mono" style="font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ row.path }}</td>
                <td><v-chip :color="row.status_code < 400 ? 'success' : 'error'" size="small" variant="tonal" label>{{ row.status_code }}</v-chip></td>
                <td class="font-mono text-medium-emphasis">{{ row.client_ip }}</td>
                <td class="text-medium-emphasis">{{ row.process_time?.toFixed(1) }}ms</td>
                <td class="text-right">
                  <v-btn size="small" variant="tonal" color="info" prepend-icon="mdi-eye-outline" :disabled="!row.payload" @click="showPayload(row)">查看详情</v-btn>
                </td>
              </tr>
            </tbody>
          </v-table>
          <div class="d-flex justify-center pa-4" v-if="pagination.itemCount > pagination.pageSize">
            <v-pagination v-model="pagination.page" :length="Math.ceil(pagination.itemCount / pagination.pageSize)" :total-visible="5" @update:model-value="handlePageChange" />
          </div>
        </v-card>
      </v-window-item>

      <!-- 4. API 文档 -->
      <v-window-item value="docs">
        <v-card class="liquid-glass-card" rounded="xl" style="min-height:600px">
          <iframe
            :src="docsUrl"
            frameborder="0"
            style="width:100%;min-height:600px;border:none;border-radius:12px"
          ></iframe>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Payload 详情对话框 -->
    <GlassDialog v-model="showLogDetail" :max-width="800"
      title="请求详情 (Payload)" cancel-text="关闭详情"
    >
      <pre class="code-block code-block--flat">{{ currentPayload }}</pre>
    </GlassDialog>
  </v-container>
</template>
