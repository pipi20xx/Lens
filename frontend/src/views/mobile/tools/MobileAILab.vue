<template>
  <div class="mobile-ai-lab">
    <!-- 页面标题 -->
    <div class="lab-header">
      <h1 class="lab-title">AI 实验室</h1>
      <p class="lab-desc">配置 OpenAI 兼容模型，利用大语言模型辅助元数据处理</p>
    </div>

    <!-- 设置面板 -->
    <n-card class="config-card" :bordered="false">
      <template #header>
        <div class="card-header">
          <n-icon size="20" color="#10b981"><SettingsIcon /></n-icon>
          <span>AI 设置</span>
        </div>
      </template>
      <n-form label-placement="top" class="mobile-form">
        <n-form-item label="服务商">
          <n-select
            v-model:value="config.provider"
            :options="providerOptions"
            @update:value="handleProviderChange"
            size="large"
          />
        </n-form-item>
        <n-form-item label="API Key" v-if="config.provider === 'openai'">
          <n-input
            type="password"
            v-model:value="config.api_key"
            placeholder="sk-..."
            show-password-on="click"
            size="large"
          />
        </n-form-item>
        <n-form-item label="Base URL">
          <n-input
            v-model:value="config.base_url"
            placeholder="https://api.openai.com/v1"
            size="large"
          />
        </n-form-item>
        <n-form-item label="Model Name">
          <n-input
            v-model:value="config.model"
            placeholder="gpt-3.5-turbo"
            size="large"
          />
        </n-form-item>
        <n-form-item>
          <n-space align="center">
            <n-switch v-model:value="config.ai_use_proxy" />
            <span class="switch-label">使用系统内置 HTTP 代理</span>
          </n-space>
        </n-form-item>
        <n-button type="primary" @click="saveConfig" :loading="saving" block size="large">
          <template #icon><n-icon><SaveIcon /></n-icon></template>
          保存配置
        </n-button>
      </n-form>
    </n-card>

    <!-- 对话区域 -->
    <n-card class="chat-card" :bordered="false">
      <template #header>
        <div class="card-header">
          <n-icon size="20" color="#705df2"><ChatIcon /></n-icon>
          <span>AI 对话</span>
          <n-button
            v-if="messages.length > 0"
            size="small"
            secondary
            type="error"
            @click="clearHistory"
            class="clear-btn"
          >
            清空
          </n-button>
        </div>
      </template>

      <!-- 消息列表 -->
      <div class="chat-window" ref="chatWindow">
        <div v-if="messages.length === 0" class="empty-state">
          <n-empty description="开始一次新的对话吧" />
        </div>

        <div
          v-for="(msg, index) in messages"
          :key="index"
          :class="['message-bubble', msg.role]"
        >
          <div class="message-avatar">
            <n-avatar v-if="msg.role === 'assistant'" size="small" color="#705df2">AI</n-avatar>
            <n-avatar v-else size="small" color="#10b981">我</n-avatar>
          </div>
          <div class="message-content">
            <div class="text" v-html="formatMessage(msg.content)"></div>
          </div>
        </div>

        <div v-if="loading" class="message-bubble assistant">
          <div class="message-avatar">
            <n-avatar size="small" color="#705df2">AI</n-avatar>
          </div>
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <n-input
          type="textarea"
          v-model:value="userInput"
          :autosize="{ minRows: 2, maxRows: 4 }"
          placeholder="输入你的问题..."
          @keydown.enter.prevent="sendMessage"
          :disabled="loading"
          class="chat-input"
        />
        <n-button
          type="primary"
          circle
          size="large"
          @click="sendMessage"
          :loading="loading"
          class="send-btn"
        >
          <template #icon><n-icon><SendIcon /></n-icon></template>
        </n-button>
      </div>
    </n-card>

    <!-- 关于说明 -->
    <n-card class="about-card" :bordered="false">
      <template #header>
        <div class="card-header">
          <n-icon size="20" color="#f59e0b"><InfoIcon /></n-icon>
          <span>关于 AI 实验室</span>
        </div>
      </template>
      <div class="about-content">
        <p>这是一个独立的 AI 功能演示模块。</p>
        <p>您可以在此配置 OpenAI 兼容的 API 服务，并在上方进行对话测试。</p>
        <p><b>核心能力：</b></p>
        <ul>
          <li>支持自定义 API Endpoint 与模型名</li>
          <li>支持系统提示词定制</li>
          <li>实时语义理解与上下文对话</li>
        </ul>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import {
  useMessage, NCard, NEmpty, NInput, NButton, NIcon,
  NForm, NFormItem, NSelect, NSwitch, NAvatar
} from 'naive-ui'
import {
  SendOutlined as SendIcon,
  SaveOutlined as SaveIcon,
  SettingsOutlined as SettingsIcon,
  ChatBubbleOutlined as ChatIcon,
  InfoOutlined as InfoIcon
} from '@vicons/material'
import { aiApi } from '@/api/ai'

const message = useMessage()

// 配置
const config = ref({
  provider: 'openai',
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  model: 'gpt-3.5-turbo',
  ai_use_proxy: false
})
const saving = ref(false)

const providerOptions = [
  { label: 'OpenAI (官方或代理)', value: 'openai' },
  { label: 'Ollama (本地部署)', value: 'ollama' }
]

const handleProviderChange = (val: string) => {
  if (val === 'ollama') {
    config.value.base_url = 'http://localhost:11434/v1'
    config.value.model = 'llama3'
    config.value.api_key = ''
  } else {
    config.value.base_url = 'https://api.openai.com/v1'
    config.value.model = 'gpt-3.5-turbo'
  }
}

const loadConfig = async () => {
  try {
    const res: any = await aiApi.getConfig()
    if (res) {
      config.value = { ...config.value, ...res }
    }
  } catch (e) {
    console.error(e)
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    await aiApi.saveConfig(config.value)
    message.success('配置已保存')
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 对话
const messages = ref<{ role: string; content: string }[]>([])
const userInput = ref('')
const loading = ref(false)
const chatWindow = ref<HTMLElement | null>(null)

const formatMessage = (text: string) => {
  if (!text) return ''
  return text.replace(/\n/g, '<br>')
}

const clearHistory = () => {
  messages.value = []
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatWindow.value) {
    chatWindow.value.scrollTop = chatWindow.value.scrollHeight
  }
}

const sendMessage = async () => {
  const text = userInput.value.trim()
  if (!text || loading.value) return

  messages.value.push({ role: 'user', content: text })
  userInput.value = ''
  loading.value = true
  await scrollToBottom()

  try {
    const response = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('lens_access_token') || ''}`
      },
      body: JSON.stringify({
        messages: messages.value,
        stream: false
      })
    })

    if (!response.ok) {
      throw new Error('请求失败')
    }

    const data = await response.json()
    messages.value.push({
      role: 'assistant',
      content: data.content || '无响应内容'
    })
  } catch (error) {
    message.error('发送失败，请检查配置')
    messages.value.push({
      role: 'assistant',
      content: '抱歉，请求处理失败。请检查 AI 配置是否正确。'
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

onMounted(loadConfig)
</script>

<style scoped>
.mobile-ai-lab {
  padding: 16px;
  padding-bottom: 32px;
  background: var(--app-bg-color);
  min-height: 100%;
}

.lab-header {
  margin-bottom: 20px;
}

.lab-title {
  font-size: 24px;
  font-weight: 700;
  color: #10b981;
  margin: 0 0 8px 0;
}

.lab-desc {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.7;
  margin: 0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-color);
}

.clear-btn {
  margin-left: auto;
}

/* 配置卡片 */
.config-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.mobile-form {
  padding: 8px 0;
}

.switch-label {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.7;
}

/* 对话卡片 */
.chat-card {
  background: var(--card-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.chat-window {
  height: 300px;
  overflow-y: auto;
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 12px;
  margin-bottom: 12px;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.message-bubble {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.message-bubble.user {
  flex-direction: row-reverse;
}

.message-content {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.5;
}

.message-bubble.assistant .message-content {
  background: rgba(112, 93, 242, 0.2);
  color: var(--text-color);
  border-bottom-left-radius: 4px;
}

.message-bubble.user .message-content {
  background: rgba(16, 185, 129, 0.2);
  color: var(--text-color);
  border-bottom-right-radius: 4px;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 12px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: var(--text-color);
  opacity: 0.5;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-10px); }
}

/* 输入区域 */
.input-area {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
}

.send-btn {
  flex-shrink: 0;
}

/* 关于卡片 */
.about-card {
  background: var(--card-bg-color);
  border-radius: 16px;
}

.about-content {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.7;
  line-height: 1.8;
}

.about-content p {
  margin: 0 0 8px 0;
}

.about-content ul {
  margin: 8px 0;
  padding-left: 20px;
}

.about-content li {
  margin-bottom: 4px;
}
</style>
