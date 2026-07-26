<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { notificationApi } from '@/api/notification'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const activeTab = ref('bots')
const settings = ref<any>({ enabled: false, bots: [] })
const loading = ref(false)

// ========== 可订阅事件定义 ==========
const EVENT_GROUPS = [
  {
    group: '账户安全',
    icon: 'mdi-shield-lock-outline',
    events: [
      { value: 'auth.login', label: '用户登录' },
    ]
  },
  {
    group: '数据备份',
    icon: 'mdi-backup-restore',
    events: [
      { value: 'backup.success', label: '备份成功' },
      { value: 'backup.failed', label: '备份失败' },
    ]
  },
  {
    group: 'Docker 容器',
    icon: 'mdi-docker',
    events: [
      { value: 'docker.container_action', label: '容器操作' },
      { value: 'docker.cleanup', label: '资源清理' },
      { value: 'docker.auto_update', label: '自动更新' },
      { value: 'docker.host_action', label: '主机操作' },
    ]
  },
  {
    group: '自动标签',
    icon: 'mdi-tag-multiple-outline',
    events: [
      { value: 'autotag.match', label: '标签匹配' },
      { value: 'autotag.task_done', label: '标签任务完成' },
      { value: 'autotag.clear_done', label: '标签清除完成' },
    ]
  },
  {
    group: '类型工具',
    icon: 'mdi-format-list-bulleted',
    events: [
      { value: 'toolkit.genre_mapper', label: '类型映射完成' },
    ]
  },
  {
    group: '镜像构建',
    icon: 'mdi-cube-outline',
    events: [
      { value: 'image_builder.setup_progress', label: '构建进度' },
      { value: 'image_builder.task_completed', label: '构建完成' },
    ]
  },
]

// 所有事件的 flat 列表（用于 "全部订阅" 等）
const ALL_EVENTS = EVENT_GROUPS.flatMap(g => g.events.map(e => e.value))

// 事件名 → 中文标签映射
const EVENT_LABEL_MAP: Record<string, string> = {}
for (const g of EVENT_GROUPS) {
  for (const e of g.events) {
    EVENT_LABEL_MAP[e.value] = e.label
  }
}

// ========== 加载 ==========
async function loadSettings() {
  try {
    loading.value = true
    const data = await notificationApi.getSettings()
    settings.value = data || { enabled: false, bots: [] }
    if (!settings.value.bots) settings.value.bots = []
  } catch {
    showError('加载通知设置失败')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  try {
    const payload = {
      enabled: settings.value.enabled,
      bots: (settings.value.bots || []).map((b: any) => ({
        id: b.id || '',
        name: b.name || '',
        type: b.type || 'telegram',
        token: b.token || '',
        chat_id: b.chat_id || '',
        enabled: b.enabled !== false,
        is_interactive: b.is_interactive || false,
        subscribed_events: b.subscribed_events || [],
        allowed_user_ids: b.allowed_user_ids || [],
      }))
    }
    await notificationApi.saveSettings(payload)
    success('通知设置已保存')
    loadSettings()
  } catch {
    showError('保存设置失败')
  }
}

// ========== Bot 管理 ==========
const showBotDialog = ref(false)
const editingBotId = ref<string | null>(null)
const botForm = ref<any>({
  id: '', name: '', type: 'telegram', token: '', chat_id: '',
  enabled: true, is_interactive: false, subscribed_events: ['*'],
  allowed_user_ids: []
})

const typeOptions = [
  { title: 'Telegram', value: 'telegram' },
]

function openAddBot() {
  editingBotId.value = null
  botForm.value = {
    id: '', name: '', type: 'telegram', token: '', chat_id: '',
    enabled: true, is_interactive: false, subscribed_events: ['*'],
    allowed_user_ids: []
  }
  showBotDialog.value = true
}

function openEditBot(bot: any) {
  editingBotId.value = bot.id
  botForm.value = { ...bot }
  // 确保 subscribed_events 始终是数组
  if (!Array.isArray(botForm.value.subscribed_events)) botForm.value.subscribed_events = []
  if (!Array.isArray(botForm.value.allowed_user_ids)) botForm.value.allowed_user_ids = []
  showBotDialog.value = true
}

async function saveBot() {
  try {
    if (!botForm.value.name?.trim()) { showError('请输入 Bot 名称'); return }
    if (!botForm.value.token?.trim()) { showError('请输入 Bot Token'); return }
    if (!botForm.value.chat_id?.trim()) { showError('请输入 Chat ID'); return }
    if (!botForm.value.subscribed_events?.length) {
      showError('请至少选择一个订阅事件');
      return
    }

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

async function toggleBotEnabled(bot: any) {
  try {
    await notificationApi.updateBot(bot.id, { ...bot, enabled: bot.enabled })
    success(bot.enabled ? 'Bot 已启用' : 'Bot 已停用')
    loadSettings()
  } catch {
    showError('操作失败')
  }
}

// 订阅事件快捷操作
function selectAllEvents() {
  botForm.value.subscribed_events = [...ALL_EVENTS]
}

function clearAllEvents() {
  botForm.value.subscribed_events = []
}

function selectAllInGroup(group: typeof EVENT_GROUPS[0]) {
  const groupEvents = group.events.map(e => e.value)
  const current = new Set(botForm.value.subscribed_events || [])
  for (const e of groupEvents) current.add(e)
  botForm.value.subscribed_events = [...current]
}

function isGroupFullySelected(group: typeof EVENT_GROUPS[0]): boolean {
  const events = botForm.value.subscribed_events || []
  return group.events.every(e => events.includes(e.value))
}

function getBotEventSummary(bot: any): string {
  const events = bot.subscribed_events || []
  if (events.includes('*')) return '全部事件'
  if (events.length === 0) return '未订阅'
  if (events.length <= 3) return events.map((e: string) => EVENT_LABEL_MAP[e] || e).join('、')
  return `${events.length} 个事件`
}

onMounted(loadSettings)
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
          <v-btn prepend-icon="mdi-plus" variant="tonal" color="primary" size="small" @click="openAddBot">添加 Bot</v-btn>
        </div>

        <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

        <v-row>
          <v-col v-for="bot in (settings.bots || [])" :key="bot.id" cols="12" sm="6">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="d-flex align-center pa-4 pb-2">
                <v-icon start :color="bot.enabled ? 'success' : 'grey'">mdi-robot-outline</v-icon>
                <span class="text-subtitle-2 font-weight-bold">{{ bot.name }}</span>
                <v-spacer />
                <v-switch :model-value="bot.enabled" @update:model-value="() => { bot.enabled = !bot.enabled; toggleBotEnabled(bot) }" density="compact" hide-details color="success" />
              </v-card-title>
              <v-card-text class="px-4 pb-2">
                <div class="text-body-2 mb-1"><span class="text-medium-emphasis">类型：</span>{{ bot.type }}</div>
                <div class="text-body-2 mb-1"><span class="text-medium-emphasis">Chat ID：</span>{{ bot.chat_id || '-' }}</div>
                <div class="text-body-2 mb-1">
                  <span class="text-medium-emphasis">订阅：</span>
                  <v-chip size="x-small" variant="tonal" :color="(bot.subscribed_events || []).length ? 'primary' : 'grey'">
                    {{ getBotEventSummary(bot) }}
                  </v-chip>
                </div>
                <div v-if="bot.is_interactive" class="mt-1">
                  <v-chip size="x-small" variant="tonal" color="info">交互模式</v-chip>
                </div>
              </v-card-text>
              <v-divider />
              <div class="d-flex flex-wrap ga-2 pa-4 pt-3">
                <v-btn size="small" color="info" variant="tonal" prepend-icon="mdi-send-outline" @click="testBot(bot.id)">测试</v-btn>
                <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-pencil-outline" @click="openEditBot(bot)">编辑</v-btn>
                <v-btn size="small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" @click="deleteBot(bot.id)">删除</v-btn>
              </div>
            </v-card>
          </v-col>
        </v-row>

        <div v-if="!loading && !settings.bots?.length" class="text-center py-12 text-medium-emphasis">
          <v-icon size="64" color="grey" class="mb-4">mdi-robot-outline</v-icon>
          <div>暂无通知 Bot</div>
          <div class="text-caption mt-2">点击右上角「添加 Bot」创建第一个通知通道</div>
        </div>
      </v-window-item>

      <!-- 通知设置 -->
      <v-window-item value="settings">
        <v-card class="liquid-glass-card" rounded="xl" max-width="600">
          <v-card-text class="pa-6">
            <div class="d-flex align-center justify-space-between mb-4">
              <div>
                <div class="text-subtitle-2 font-weight-bold">启用通知系统</div>
                <div class="text-caption text-medium-emphasis">开启后，系统事件将通过已配置的 Bot 推送通知</div>
              </div>
              <v-switch v-model="settings.enabled" density="compact" color="primary" hide-details />
            </div>
            <v-divider class="mb-4" />
            <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveSettings">保存设置</v-btn>
          </v-card-text>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- Bot 编辑对话框 -->
    <v-dialog v-model="showBotDialog" max-width="640" scrollable>
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4">
          <v-icon start>mdi-robot-outline</v-icon>
          {{ editingBotId ? '编辑 Bot' : '添加 Bot' }}
        </v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <!-- 基本信息 -->
          <v-text-field v-model="botForm.name" label="名称" variant="outlined" density="compact" placeholder="例如: 我的 Telegram Bot" class="mb-3" />
          <v-select v-model="botForm.type" :items="typeOptions" label="类型" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="botForm.token" label="Bot Token" variant="outlined" density="compact" placeholder="例如: 123456:ABC-DEF..." class="mb-3" />
          <v-text-field v-model="botForm.chat_id" label="Chat ID" variant="outlined" density="compact" placeholder="接收通知的聊天 ID" class="mb-3" />

          <v-divider class="my-4" />

          <!-- 订阅事件 -->
          <div class="text-subtitle-2 font-weight-bold mb-2">
            <v-icon start size="18">mdi-bell-ring-outline</v-icon>
            订阅事件
          </div>
          <p class="text-caption text-medium-emphasis mb-3">选择此 Bot 需要接收通知的事件类型。只有订阅的事件才会推送。</p>

          <div class="d-flex ga-2 mb-3">
            <v-btn size="x-small" variant="tonal" color="primary" prepend-icon="mdi-select-all" @click="selectAllEvents">全选</v-btn>
            <v-btn size="x-small" variant="tonal" color="error" prepend-icon="mdi-close-circle-outline" @click="clearAllEvents">清空</v-btn>
          </div>

          <div v-for="group in EVENT_GROUPS" :key="group.group" class="mb-3">
            <div class="d-flex align-center mb-1">
              <v-icon start size="16" class="mr-1">{{ group.icon }}</v-icon>
              <span class="text-body-2 font-weight-medium">{{ group.group }}</span>
              <v-btn size="x-small" variant="text" prepend-icon="mdi-select-all" class="ml-auto" @click="selectAllInGroup(group)">
                {{ isGroupFullySelected(group) ? '✓' : '全选' }}
              </v-btn>
            </div>
            <div class="d-flex flex-wrap ga-2 ml-6">
              <v-checkbox
                v-for="evt in group.events"
                :key="evt.value"
                v-model="botForm.subscribed_events"
                :value="evt.value"
                :label="evt.label"
                density="compact"
                hide-details
                color="primary"
              />
            </div>
          </div>

          <v-divider class="my-4" />

          <!-- 交互模式 -->
          <div class="d-flex align-center justify-space-between mb-2">
            <div>
              <div class="text-body-2 font-weight-medium">交互模式</div>
              <div class="text-caption text-medium-emphasis">允许通过 Telegram 消息执行操作（如查询状态、触发备份）</div>
            </div>
            <v-switch v-model="botForm.is_interactive" density="compact" color="primary" hide-details />
          </div>

          <template v-if="botForm.is_interactive">
            <v-text-field
              v-model="botForm.allowed_user_ids"
              label="允许交互的 TG 用户 ID"
              variant="outlined"
              density="compact"
              placeholder="多个 ID 用英文逗号分隔，如: 123456,789012"
              hint="只有这些用户 ID 才能通过 Bot 执行操作，留空则所有人可操作"
              persistent-hint
              class="mt-2"
            />
          </template>

          <v-divider class="my-4" />

          <!-- 启用开关 -->
          <v-switch v-model="botForm.enabled" label="启用此 Bot" density="compact" color="primary" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showBotDialog = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveBot">保存</v-btn>
        </div>
      </v-card>
    </v-dialog>
  </v-container>
</template>
