<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { notificationApi } from '@/api/notification'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const activeTab = ref('bots')
const settings = ref<any>({ enabled: false })
const bots = ref<any[]>([])
const loading = ref(false)

// ========== 加载 ==========
async function loadSettings() {
  try {
    settings.value = await notificationApi.getSettings() || { enabled: false }
  } catch { /* ignore */ }
}

async function loadBots() {
  try {
    loading.value = true
    bots.value = settings.value?.bots || []
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  try {
    await notificationApi.saveSettings(settings.value)
    success('通知设置已保存')
    loadSettings()
  } catch {
    showError('保存设置失败')
  }
}

// ========== Bot 管理 ==========
const showBotDialog = ref(false)
const editingBotId = ref<string | null>(null)
const botForm = ref<any>({ name: '', type: 'telegram', token: '', chat_id: '', enabled: true, is_interactive: false })

function openAddBot() {
  editingBotId.value = null
  botForm.value = { name: '', type: 'telegram', token: '', chat_id: '', enabled: true, is_interactive: false }
  showBotDialog.value = true
}

function openEditBot(bot: any) {
  editingBotId.value = bot.id
  botForm.value = { ...bot }
  showBotDialog.value = true
}

async function saveBot() {
  try {
    if (editingBotId.value) {
      await notificationApi.updateBot(editingBotId.value, botForm.value)
    } else {
      await notificationApi.addBot(botForm.value)
    }
    success('Bot 已保存')
    showBotDialog.value = false
    loadSettings()
  } catch {
    showError('保存失败')
  }
}

async function deleteBot(id: string) {
  const ok = await confirm({ title: '删除 Bot', content: '确定要删除此通知 Bot 吗？', confirmColor: 'error' })
  if (!ok) return
  try {
    await notificationApi.deleteBot(id)
    success('Bot 已删除')
    loadSettings()
  } catch {
    showError('删除失败')
  }
}

async function testBot(id: string) {
  try {
    await notificationApi.testBot({ bot_id: id, message: '🔔 Lens 测试通知' })
    success('测试消息已发送')
  } catch {
    showError('发送失败')
  }
}

onMounted(() => { loadSettings().then(loadBots) })
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-bell-outline</v-icon>
      通知中心设置
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">配置多平台推送通道，实现系统备份、任务执行及安全审计的实时通知。</p>

    <v-tabs v-model="activeTab" class="mb-4">
      <v-tab value="bots"><v-icon start>mdi-robot-outline</v-icon> Bot 管理</v-tab>
      <v-tab value="settings"><v-icon start>mdi-tune-vertical</v-icon> 通知设置</v-tab>
    </v-tabs>

    <v-window v-model="activeTab">
      <!-- Bot 管理 -->
      <v-window-item value="bots">
        <div class="d-flex justify-end mb-4">
          <v-btn prepend-icon="mdi-plus" variant="tonal" size="small" @click="openAddBot">添加 Bot</v-btn>
        </div>

        <v-row>
          <v-col v-for="bot in (settings.bots || [])" :key="bot.id" cols="12" sm="6" md="4">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="d-flex align-center pa-4 pb-2">
                <v-icon start :color="bot.enabled ? 'success' : 'grey'">mdi-robot-outline</v-icon>
                <span class="text-subtitle-2 font-weight-bold">{{ bot.name }}</span>
                <v-spacer />
                <v-chip :color="bot.enabled ? 'success' : 'grey'" size="x-small" variant="tonal">
                  {{ bot.enabled ? '启用' : '停用' }}
                </v-chip>
              </v-card-title>
              <v-card-text class="px-4 pb-2">
                <div class="text-body-2 mb-1"><span class="text-medium-emphasis">类型：</span>{{ bot.type }}</div>
                <div class="text-body-2"><span class="text-medium-emphasis">Chat ID：</span>{{ bot.chat_id || '-' }}</div>
              </v-card-text>
              <v-divider />
              <div class="d-flex flex-wrap ga-2 pa-4 pt-3">
                <v-btn size="small" color="info" variant="tonal" @click="testBot(bot.id)">测试</v-btn>
                <v-btn size="small" variant="tonal" @click="openEditBot(bot)">编辑</v-btn>
                <v-btn size="small" color="error" variant="tonal" @click="deleteBot(bot.id)">删除</v-btn>
              </div>
            </v-card>
          </v-col>
        </v-row>

        <div v-if="!settings.bots?.length" class="text-center py-12 text-medium-emphasis">
          <v-icon size="64" color="grey" class="mb-4">mdi-robot-outline</v-icon>
          <div>暂无通知 Bot</div>
        </div>
      </v-window-item>

      <!-- 通知设置 -->
      <v-window-item value="settings">
        <v-card class="liquid-glass-card" rounded="xl" max-width="600">
          <v-card-text class="pa-6">
            <v-switch v-model="settings.enabled" label="启用通知系统" density="compact" color="primary" class="mb-4" />
            <v-btn color="primary" variant="flat" @click="saveSettings">保存设置</v-btn>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Bot 编辑对话框 -->
    <v-dialog v-model="showBotDialog" max-width="500">
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-robot-outline</v-icon>
          {{ editingBotId ? '编辑 Bot' : '添加 Bot' }}
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-text-field v-model="botForm.name" label="名称" variant="outlined" density="compact" class="mb-3" />
          <v-select v-model="botForm.type" :items="[{ title: 'Telegram', value: 'telegram' }]" label="类型" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="botForm.token" label="Bot Token" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="botForm.chat_id" label="Chat ID" variant="outlined" density="compact" class="mb-3" />
          <v-switch v-model="botForm.enabled" label="启用" density="compact" color="primary" class="mb-2" />
          <v-switch v-model="botForm.is_interactive" label="交互模式 (监听消息)" density="compact" color="primary" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="text" @click="showBotDialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" @click="saveBot">保存</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>
