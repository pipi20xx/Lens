<template>
  <div class="mobile-notification-manager">
    <div class="page-header">
      <h1 class="page-title">通知消息中心</h1>
      <p class="page-desc">配置通知推送通道</p>
    </div>

    <n-card class="switch-card" :bordered="false" title="全局设置">
      <div class="switch-row">
        <span class="switch-label">启用通知</span>
        <n-switch v-model:value="settings.enabled" @update:value="saveSettings" />
      </div>
    </n-card>

    <n-card class="bots-card" :bordered="false" title="推送通道">
      <n-space vertical>
        <n-button block type="primary" @click="showAddBotModal = true">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          添加机器人
        </n-button>
        <div v-if="settings.bots.length === 0" class="empty-state">
          <n-empty description="暂无推送通道" />
        </div>
        <div v-else class="bot-list">
          <div v-for="bot in settings.bots" :key="bot.id" class="bot-item">
            <div class="bot-info">
              <div class="bot-name">{{ bot.name }}</div>
              <div class="bot-type">{{ bot.type }}</div>
              <div class="bot-events">
                <n-tag v-for="event in bot.subscribed_events" :key="event" size="small" type="info">
                  {{ event }}
                </n-tag>
              </div>
            </div>
            <div class="bot-actions">
              <n-button size="small" secondary type="info" @click="editBot(bot)">
                编辑
              </n-button>
              <n-popconfirm @positive-click="deleteBot(bot.id)" positive-text="确认删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    删除
                  </n-button>
                </template>
                确定删除此通道？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddBotModal" preset="card" :title="editingBot.id ? '编辑机器人' : '添加机器人'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="名称">
          <n-input v-model:value="editingBot.name" placeholder="例如：Lens 备份助手" />
        </n-form-item>
        <n-form-item label="类型">
          <n-select v-model:value="editingBot.type" :options="typeOptions" />
        </n-form-item>
        <n-form-item label="Bot Token">
          <n-input v-model:value="editingBot.token" type="password" show-password-on="click" placeholder="Telegram Bot API Token" />
        </n-form-item>
        <n-form-item label="Chat ID">
          <n-input v-model:value="editingBot.chat_id" placeholder="接收通知的 Chat ID" />
        </n-form-item>
        <n-form-item label="订阅事件">
          <n-select v-model:value="editingBot.subscribed_events" multiple :options="eventOptions" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddBotModal = false">取消</n-button>
          <n-button type="primary" @click="saveBot" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NSwitch, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, NIcon } from 'naive-ui'
import { AddOutlined as AddIcon } from '@vicons/material'
import { notificationApi } from '@/api/notification'
import { useMessage } from 'naive-ui'

const message = useMessage()
const settings = ref({
  enabled: true,
  bots: []
})
const showAddBotModal = ref(false)
const saving = ref(false)
const editingBot = ref({
  id: null,
  name: '',
  type: 'telegram',
  token: '',
  chat_id: '',
  subscribed_events: []
})

const typeOptions = [
  { label: 'Telegram', value: 'telegram' },
  { label: '企业微信', value: 'wechat' },
  { label: '钉钉', value: 'dingtalk' }
]

const eventOptions = [
  { label: '备份完成', value: 'backup_completed' },
  { label: '任务完成', value: 'task_completed' },
  { label: '系统告警', value: 'system_alert' },
  { label: '用户登录', value: 'user_login' }
]

const loadSettings = async () => {
  try {
    const res = await notificationApi.getSettings()
    settings.value = res as any || { enabled: true, bots: [] }
  } catch (e) {
    message.error('加载设置失败')
  }
}

const saveSettings = async () => {
  try {
    await notificationApi.saveSettings(settings.value)
    message.success('设置已保存')
  } catch (e) {
    message.error('保存设置失败')
  }
}

const saveBot = async () => {
  if (!editingBot.name || !editingBot.token) {
    message.warning('请填写完整的机器人信息')
    return
  }
  saving.value = true
  try {
    if (editingBot.id) {
      await notificationApi.updateBot(editingBot.id, editingBot)
    } else {
      await notificationApi.addBot(editingBot)
    }
    await saveSettings()
    showAddBotModal.value = false
    editingBot.value = { id: null, name: '', type: 'telegram', token: '', chat_id: '', subscribed_events: [] }
  } catch (e) {
    message.error('保存机器人失败')
  } finally {
    saving.value = false
  }
}

const editBot = (bot: any) => {
  editingBot.value = { ...bot }
  showAddBotModal.value = true
}

const deleteBot = async (id: number) => {
  try {
    await notificationApi.deleteBot(String(id))
    await saveSettings()
  } catch (e) {
    message.error('删除机器人失败')
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.mobile-notification-manager {
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

.switch-card,
.bots-card {
  margin-bottom: 12px;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.switch-label {
  font-size: 14px;
  color: var(--text-color);
}

.empty-state {
  padding: 24px 0;
}

.bot-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bot-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.bot-info {
  margin-bottom: 8px;
}

.bot-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.bot-type {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 4px;
}

.bot-events {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.bot-actions {
  display: flex;
  gap: 8px;
}
</style>
