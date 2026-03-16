<template>
  <div class="mobile-notification-manager">
    <div class="page-header">
      <h1 class="page-title">通知消息中心</h1>
      <p class="page-desc">配置通知推送通道</p>
    </div>

    <n-card class="switch-card" :bordered="false" title="全局设置">
      <div class="setting-item">
        <span class="setting-label">启用通知</span>
        <MobileSwitch v-model="settings.enabled" @update:model-value="saveSettings" />
      </div>
    </n-card>

    <n-card class="bots-card" :bordered="false" title="推送通道">
      <n-space vertical>
        <n-button block :type="buttonTypes.PRIMARY" @click="showAddBotModal = true">
          {{ buttonText.ADD }}机器人
        </n-button>
        <div v-if="settings.bots.length === 0" class="empty-state">
          <n-empty :description="messageText.EMPTY_DATA" />
        </div>
        <div v-else class="bot-list">
          <div v-for="bot in settings.bots" :key="bot.id" class="bot-item">
            <div class="bot-header">
              <div class="bot-name">
                <n-text strong>{{ bot.name }}</n-text>
                <n-tag :type="bot.enabled ? tagTypes.SUCCESS : tagTypes.DEFAULT" :size="buttonSizes.TINY" round>
                  {{ bot.enabled ? statusText.RUNNING : statusText.DISABLED }}
                </n-tag>
              </div>
              <MobileSwitch v-model="bot.enabled" @update:model-value="saveSettings" />
            </div>
            
            <div class="bot-info">
              <div class="bot-type">{{ bot.type }}</div>
              <div v-if="bot.is_interactive" class="bot-interactive">
                <n-tag :type="tagTypes.WARNING" :size="buttonSizes.TINY">交互模式</n-tag>
              </div>
              <div class="bot-events">
                <n-tag v-for="event in bot.subscribed_events" :key="event" :size="buttonSizes.SMALL" :type="tagTypes.INFO">
                  {{ event }}
                </n-tag>
              </div>
            </div>
            
            <div class="bot-actions">
              <n-button :size="buttonSizes.MEDIUM" secondary :type="buttonTypes.INFO" @click="testBot(bot.id)">
                {{ buttonText.TEST }}
              </n-button>
              <n-button :size="buttonSizes.MEDIUM" secondary @click="editBot(bot)">
                {{ buttonText.EDIT }}
              </n-button>
              <n-popconfirm @positive-click="() => deleteBot(bot.id)" :positive-text="buttonText.CONFIRM_DELETE" :negative-text="buttonText.CANCEL">
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
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddBotModal" preset="card" :title="editingBot.id ? buttonText.EDIT + '机器人' : buttonText.ADD + '机器人'" style="width: 90vw; max-width: 500px">
      <n-form label-placement="top" :size="formSizes.SMALL">
        <n-form-item :label="formLabel.NAME">
          <n-input v-model:value="editingBot.name" :placeholder="placeholder.BOT_NAME" />
        </n-form-item>
        <n-form-item :label="formLabel.TYPE">
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
        <n-form-item label="开启交互">
          <n-space vertical style="width: 100%">
            <MobileSwitch v-model="editingBot.is_interactive" />
            <n-alert v-if="editingBot.is_interactive" :type="buttonTypes.WARNING" :size="buttonSizes.TINY">
              开启后，你可以通过 Telegram 直接操控 Docker。请务必配置下方的授权用户 ID。
            </n-alert>
          </n-space>
        </n-form-item>
        <n-form-item v-if="editingBot.is_interactive" label="授权用户 ID">
          <n-select
            v-model:value="editingBot.allowed_user_ids"
            multiple
            filterable
            tag
            placeholder="输入你的 Telegram User ID 并回车"
          />
        </n-form-item>
        <n-form-item label="是否启用">
          <MobileSwitch v-model="editingBot.enabled" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddBotModal = false">{{ buttonText.CANCEL }}</n-button>
          <n-button :type="buttonTypes.PRIMARY" @click="saveBot" :loading="saving">{{ buttonText.SAVE }}</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showTestModal" preset="dialog" title="发送测试消息" :positive-text="buttonText.SEND" :negative-text="buttonText.CANCEL" @positive-click="sendTestMessage">
      <n-input v-model:value="testMessage" type="textarea" placeholder="输入测试内容..." />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NButton, NSpace, NEmpty, NModal, NForm, NFormItem, NInput, NSelect, NTag, NPopconfirm, NText, NAlert, useMessage } from 'naive-ui'
import { notificationApi } from '@/api/notification'
import { NOTIFICATION_EVENTS } from '@/constants/events'
import MobileSwitch from '../components/MobileSwitch.vue'
import {
  ButtonTypes,
  ButtonSizes,
  TagTypes,
  FormSizes,
  ButtonText,
  StatusText,
  MessageText,
} from '../constants'

const message = useMessage()

// 使用常量
const buttonTypes = ButtonTypes
const buttonSizes = ButtonSizes
const tagTypes = TagTypes
const formSizes = FormSizes
const buttonText = ButtonText
const statusText = StatusText
const messageText = MessageText

// 表单标签
const formLabel = {
  NAME: '名称',
  TYPE: '类型',
}

// 占位符
const placeholder = {
  BOT_NAME: '例如：Lens 备份助手',
}

const settings = ref({
  enabled: true,
  bots: []
})
const showAddBotModal = ref(false)
const showTestModal = ref(false)
const saving = ref(false)
const testMessage = ref('')
const editingBot = ref({
  id: null,
  name: '',
  type: 'telegram',
  token: '',
  chat_id: '',
  subscribed_events: [],
  is_interactive: false,
  allowed_user_ids: [],
  enabled: true
})

const typeOptions = [
  { label: 'Telegram', value: 'telegram' }
]

const eventOptions = NOTIFICATION_EVENTS

const loadSettings = async () => {
  try {
    const res = await notificationApi.getSettings()
    settings.value = res as any || { enabled: true, bots: [] }
  } catch (e) {
    message.error(messageText.OPERATION_FAILED)
  }
}

const saveSettings = async () => {
  try {
    await notificationApi.saveSettings(settings.value)
    message.success(messageText.SETTINGS_SAVED)
  } catch (e) {
    message.error(messageText.SAVE_FAILED)
  }
}

const saveBot = async () => {
  if (!editingBot.value.name || !editingBot.value.token) {
    message.warning('请填写完整的机器人信息')
    return
  }
  saving.value = true
  try {
    if (editingBot.value.id) {
      await notificationApi.updateBot(editingBot.value.id, editingBot.value)
    } else {
      await notificationApi.addBot(editingBot.value)
    }
    await saveSettings()
    showAddBotModal.value = false
    editingBot.value = { id: null, name: '', type: 'telegram', token: '', chat_id: '', subscribed_events: [], is_interactive: false, allowed_user_ids: [], enabled: true }
  } catch (e) {
    message.error(messageText.ADD_FAILED)
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
    message.error(messageText.DELETE_FAILED)
  }
}

const testBot = async (id: string) => {
  testMessage.value = '这是一条测试消息'
  showTestModal.value = true
}

const sendTestMessage = async () => {
  try {
    await notificationApi.sendTestMessage(testMessage.value)
    message.success(messageText.SEND_SUCCESS)
    showTestModal.value = false
  } catch (e) {
    message.error(messageText.SEND_FAILED)
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

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
  margin-bottom: 12px;
}

.setting-label {
  font-size: 15px;
  color: var(--text-color);
  font-weight: 500;
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
  background: var(--card-color);
  border: 1px solid #7c3aed;
  border-radius: 12px;
}

.bot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.bot-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.bot-info {
  margin-bottom: 8px;
}

.bot-type {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 4px;
}

.bot-interactive {
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
