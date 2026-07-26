<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { toolkitApi } from '@/api/toolkit'
import { useNotification } from '@/composables'
import SecretField from '@/components/common/SecretField.vue'

const { success, error: showError } = useNotification()

// ========== AI 配置模块 ==========
const config = ref({
  provider: 'openai',
  api_key: '',
  base_url: 'https://api.openai.com/v1',
  model: 'gpt-3.5-turbo',
  use_proxy: false,
})
const saving = ref(false)

const providerOptions = [
  { title: 'OpenAI (官方或代理)', value: 'openai' },
  { title: 'Ollama (本地部署)', value: 'ollama' },
]

function handleProviderChange() {
  if (config.value.provider === 'ollama') {
    config.value.base_url = 'http://localhost:11434/v1'
    config.value.model = 'llama3'
    config.value.api_key = ''
  } else {
    config.value.base_url = 'https://api.openai.com/v1'
    config.value.model = 'gpt-3.5-turbo'
  }
}

async function loadConfig() {
  try {
    const data: any = await toolkitApi.aiLab.getConfig()
    if (data) config.value = { ...config.value, ...data }
  } catch { /* ignore */ }
}

async function saveConfig() {
  saving.value = true
  try {
    // 后端 AIConfig 只有4个字段，use_proxy 需要单独保存
    await toolkitApi.aiLab.saveConfig({
      provider: config.value.provider,
      api_key: config.value.api_key,
      base_url: config.value.base_url,
      model: config.value.model,
    })
    // 单独保存 use_proxy 配置
    try {
      const { configApi } = await import('@/api/config')
      await configApi.saveSystemConfig([
        { key: 'ai_use_proxy', value: config.value.use_proxy, description: 'AI 使用代理' },
      ])
    } catch { /* ignore */ }
    success('配置已保存')
  } catch { showError('保存失败') }
  finally { saving.value = false }
}

// ========== AI 对话模块 ==========
const messages = ref<{ role: string; content: string }[]>([])
const userInput = ref('')
const chatLoading = ref(false)
const chatWindow = ref<HTMLElement | null>(null)

const getAuthHeaders = () => {
  const token = localStorage.getItem('lens_access_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function scrollToBottom() {
  await nextTick()
  if (chatWindow.value) chatWindow.value.scrollTop = chatWindow.value.scrollHeight
}

async function sendMessage() {
  if (!userInput.value.trim() || chatLoading.value) return
  const userMsg = userInput.value.trim()
  messages.value.push({ role: 'user', content: userMsg })
  userInput.value = ''
  chatLoading.value = true
  scrollToBottom()

  try {
    const context = messages.value.map(m => ({ role: m.role, content: m.content }))

    // 使用 fetch 获取流式响应
    const response = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ messages: context }),
    })

    if (!response.ok) throw new Error('Network error')
    if (!response.body) throw new Error('No response body')

    const assistantMsg = { role: 'assistant', content: '' }
    messages.value.push(assistantMsg)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value, { stream: true })
      assistantMsg.content += text
      scrollToBottom()
    }
  } catch (e) {
    showError('发送失败: ' + String(e))
    messages.value.push({ role: 'assistant', content: '[Error: Request Failed]' })
  } finally {
    chatLoading.value = false
    scrollToBottom()
  }
}

function handleEnter(e: KeyboardEvent) {
  if (e.ctrlKey) { e.preventDefault(); sendMessage() }
}

function clearHistory() { messages.value = [] }

onMounted(loadConfig)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-robot-outline</v-icon>
      AI 实验室
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">配置 OpenAI 兼容模型，利用大语言模型辅助元数据处理与语义分析。</p>

    <v-row>
      <!-- 左侧：AI 对话 -->
      <v-col cols="12" md="8">
        <v-card class="liquid-glass-card" rounded="xl" style="height:75vh;display:flex;flex-direction:column">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon start>mdi-chat-outline</v-icon>
            AI 对话
            <v-spacer />
            <v-btn v-if="messages.length > 0" size="small" variant="tonal" color="error" prepend-icon="mdi-delete-sweep-outline" @click="clearHistory">清空历史</v-btn>
          </v-card-title>
          <v-divider />
          <div ref="chatWindow" class="flex-grow-1 pa-4" style="overflow-y:auto;background:rgba(0,0,0,0.02)">
            <!-- 空状态 -->
            <div v-if="messages.length === 0" class="text-center py-12 text-medium-emphasis">
              <v-icon size="48" color="grey" class="mb-4">mdi-chat-processing-outline</v-icon>
              <div>开始一次新的对话吧</div>
            </div>

            <!-- 消息列表 -->
            <div v-for="(msg, index) in messages" :key="index" class="mb-4" :class="{ 'd-flex justify-end': msg.role === 'user', 'd-flex justify-start': msg.role === 'assistant' }">
              <div :style="{ maxWidth: '80%' }">
                <div class="text-caption text-medium-emphasis mb-1" :class="{ 'text-right': msg.role === 'user' }">{{ msg.role === 'user' ? 'You' : 'AI' }}</div>
                <div class="pa-3 rounded-lg text-body-2" :style="{
                  background: msg.role === 'user' ? 'rgb(var(--v-theme-primary))' : 'rgba(var(--v-theme-surface-variant),0.3)',
                  color: msg.role === 'user' ? 'white' : 'inherit',
                  borderBottomRightRadius: msg.role === 'user' ? '2px' : undefined,
                  borderBottomLeftRadius: msg.role === 'assistant' ? '2px' : undefined,
                }" style="white-space:pre-wrap;line-height:1.5">{{ msg.content }}</div>
              </div>
            </div>

            <!-- 加载指示器 -->
            <div v-if="chatLoading" class="d-flex justify-start mb-4">
              <div class="pa-3 rounded-lg" style="background:rgba(var(--v-theme-surface-variant),0.3)">
                <v-progress-linear indeterminate color="primary" width="3" rounded style="min-width:60px" />
              </div>
            </div>
          </div>

          <!-- 输入区 -->
          <div class="d-flex ga-2 pa-4 align-end">
            <v-textarea v-model="userInput" placeholder="输入你的问题... (Ctrl+Enter 发送)" variant="outlined" density="compact" :rows="2" auto-grow :disabled="chatLoading" @keydown="handleEnter" class="flex-grow-1" hide-details />
            <v-btn color="primary" variant="flat" icon :loading="chatLoading" @click="sendMessage" :disabled="!userInput.trim()">
              <v-icon>mdi-send</v-icon>
            </v-btn>
          </div>
        </v-card>
      </v-col>

      <!-- 右侧：配置与说明 -->
      <v-col cols="12" md="4">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-cog-outline</v-icon>
            AI 设置
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-select v-model="config.provider" :items="providerOptions" label="服务商 (Provider)" variant="outlined" density="compact" class="mb-3" @update:model-value="handleProviderChange" />
            <SecretField v-if="config.provider === 'openai'" v-model="config.api_key" label="API Key" placeholder="sk-..." class="mb-3" :show-copy="false" />
            <v-text-field v-model="config.base_url" label="Base URL" placeholder="https://api.openai.com/v1" variant="outlined" density="compact" class="mb-3" />
            <v-text-field v-model="config.model" label="Model Name" placeholder="gpt-3.5-turbo" variant="outlined" density="compact" class="mb-3" />
            <div class="d-flex align-center mb-4">
              <v-switch v-model="config.use_proxy" density="compact" color="primary" hide-details class="mr-2" />
              <span class="text-body-2 text-medium-emphasis">使用系统内置 HTTP 代理转发请求</span>
            </div>
            <v-btn block color="primary" variant="flat" prepend-icon="mdi-content-save-outline" :loading="saving" @click="saveConfig">执行保存</v-btn>
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-information-outline</v-icon>
            关于 AI 实验室
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p>这是一个独立的 AI 功能演示模块。</p>
            <p>您可以在此配置 OpenAI 兼容的 API 服务，并在左侧进行对话测试。</p>
            <p class="font-weight-bold mt-2">核心能力：</p>
            <ul>
              <li>支持自定义 API Endpoint 与模型名。</li>
              <li>支持系统提示词 (System Prompt) 定制。</li>
              <li>实时语义理解与上下文对话。</li>
            </ul>
            <p class="mt-2">未来此模块的能力将被复用到系统的其他自动化功能中，如剧情简介自动润色、标签语义分类等。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>
