<template>
  <div class="mobile-webhook-receiver">
    <div class="page-header">
      <h1 class="page-title">Webhook 接收器</h1>
      <p class="page-desc">管理 Webhook 端点与事件处理</p>
    </div>

    <n-card class="endpoints-card" :bordered="false" title="端点列表">
      <n-space vertical>
        <n-button block type="primary" @click="showAddModal = true">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          添加端点
        </n-button>
        <div v-if="endpoints.length === 0" class="empty-state">
          <n-empty description="暂无 Webhook 端点" />
        </div>
        <div v-else class="endpoint-list">
          <div v-for="endpoint in endpoints" :key="endpoint.id" class="endpoint-item">
            <div class="endpoint-info">
              <div class="endpoint-name">{{ endpoint.name }}</div>
              <div class="endpoint-url">{{ endpoint.url }}</div>
              <div class="endpoint-events">
                <n-tag v-for="event in endpoint.events" :key="event" size="small" type="info">
                  {{ event }}
                </n-tag>
              </div>
            </div>
            <div class="endpoint-actions">
              <n-button size="small" secondary type="warning" @click="editEndpoint(endpoint)">
                编辑
              </n-button>
              <n-popconfirm @positive-click="deleteEndpoint(endpoint.id)" positive-text="确认删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    删除
                  </n-button>
                </template>
                确定删除此端点？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-card class="logs-card" :bordered="false" title="最近调用日志">
      <div v-if="logs.length === 0" class="empty-state">
        <n-empty description="暂无调用日志" />
      </div>
      <div v-else class="log-list">
        <div v-for="log in logs" :key="log.id" class="log-item">
          <div class="log-info">
            <div class="log-endpoint">{{ log.endpoint_name }}</div>
            <div class="log-time">{{ formatDate(log.created_at) }}</div>
            <n-tag :type="log.status === 'success' ? 'success' : 'error'" size="small">
              {{ log.status }}
            </n-tag>
          </div>
        </div>
      </div>
    </n-card>

    <n-modal v-model:show="showAddModal" preset="card" title="添加端点" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="名称">
          <n-input v-model:value="newEndpoint.name" placeholder="端点名称" />
        </n-form-item>
        <n-form-item label="URL 路径">
          <n-input v-model:value="newEndpoint.url" placeholder="/webhook/myhook" />
        </n-form-item>
        <n-form-item label="事件类型">
          <n-select v-model:value="newEndpoint.events" multiple :options="eventOptions" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddModal = false">取消</n-button>
          <n-button type="primary" @click="saveEndpoint" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, NIcon } from 'naive-ui'
import { AddOutlined as AddIcon } from '@vicons/material'
import { webhookApi } from '@/api/webhook'
import { useMessage } from 'naive-ui'

const message = useMessage()
const endpoints = ref<any[]>([])
const logs = ref<any[]>([])
const showAddModal = ref(false)
const saving = ref(false)

const newEndpoint = ref({
  name: '',
  url: '',
  events: []
})

const eventOptions = [
  { label: '备份完成', value: 'backup_completed' },
  { label: '任务完成', value: 'task_completed' },
  { label: '系统告警', value: 'system_alert' },
  { label: '用户登录', value: 'user_login' }
]

const loadEndpoints = async () => {
  message.info('请在桌面端配置 Webhook')
}

const loadLogs = async () => {
  try {
    const res = await webhookApi.getLogs()
    logs.value = res as any || []
  } catch (e) {
    message.error('加载日志失败')
  }
}

const saveEndpoint = () => {
  message.info('请在桌面端配置 Webhook')
}

const editEndpoint = (endpoint: any) => {
  message.info('请在桌面端配置 Webhook')
}

const deleteEndpoint = (id: string) => {
  message.info('请在桌面端配置 Webhook')
}

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString()
}

onMounted(() => {
  loadEndpoints()
  loadLogs()
})
</script>

<style scoped>
.mobile-webhook-receiver {
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

.endpoints-card,
.logs-card {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.endpoint-list,
.log-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.endpoint-item,
.log-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.endpoint-info,
.log-info {
  margin-bottom: 8px;
}

.endpoint-name,
.log-endpoint {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.endpoint-url,
.log-time {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 4px;
}

.endpoint-events {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.endpoint-actions {
  display: flex;
  gap: 8px;
}

.log-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
