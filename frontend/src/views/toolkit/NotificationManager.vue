<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <!-- 页面标题区 -->
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">通知中心设置</n-text></n-h2>
        <n-text depth="3">配置多平台推送通道，实现系统备份、任务执行及安全审计的实时通知。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：主要配置区 -->
        <n-gi span="24 m:16">
          <n-space vertical size="large">
            <!-- 1. 全局开关 -->
            <n-card title="系统通知总开关" size="small" segmented>
              <template #header-extra>
                <n-switch v-model:value="settings.enabled" @update:value="saveSettings" />
              </template>
              <n-text depth="3">
                开启后，系统将根据下方各机器人的配置，在特定事件发生时发送通知。
              </n-text>
            </n-card>

            <!-- 2. 机器人列表 -->
            <n-card title="推送通道 (Bots) 列表" size="small" segmented>
              <template #header-extra>
                <n-button type="primary" size="small" @click="handleAddBot">
                  添加新机器人
                </n-button>
              </template>

              <div v-if="settings.bots?.length" class="bot-grid">
                <div
                  v-for="bot in settings.bots"
                  :key="bot.id"
                  class="bot-card"
                  :class="{ 'disabled': !bot.enabled }"
                >
                  <div class="bot-card-header">
                    <div class="bot-name" :title="bot.name">{{ bot.name }}</div>
                    <n-tag
                      :type="bot.enabled ? 'success' : 'default'"
                      size="small"
                      round
                      quaternary
                    >
                      {{ bot.enabled ? '运行中' : '已停用' }}
                    </n-tag>
                  </div>

                  <div class="bot-events">
                    <n-text depth="3" class="events-label">订阅事件</n-text>
                    <n-space v-if="bot.subscribed_events?.length" size="small">
                      <n-tag
                        v-for="ev in bot.subscribed_events"
                        :key="ev"
                        size="tiny"
                        type="info"
                        quaternary
                      >
                        {{ ev }}
                      </n-tag>
                    </n-space>
                    <n-text v-else depth="3" style="font-size: 12px">未订阅任何事件</n-text>
                  </div>

                  <div class="bot-actions">
                    <n-button size="tiny" type="info" secondary @click="handleTestBot(bot.id)">
                      测试
                    </n-button>
                    <n-button size="tiny" secondary @click="handleEditBot(bot)">
                      编辑
                    </n-button>
                    <n-popconfirm
                      @positive-click="handleDeleteBot(bot.id)"
                      positive-text="确认"
                      negative-text="取消"
                    >
                      <template #trigger>
                        <n-button size="tiny" type="error" secondary>
                          删除
                        </n-button>
                      </template>
                      确定删除该机器人吗？
                    </n-popconfirm>
                  </div>
                </div>
              </div>
              <n-empty
                v-else
                description="尚未配置任何机器人"
                style="padding: 30px"
              />
            </n-card>
          </n-space>
        </n-gi>

        <!-- 右侧：辅助信息区 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <n-card title="配置指南" size="small" segmented>
              <n-alert type="info" :bordered="false" style="margin-bottom: 12px">
                Lens 支持多机器人并行推送。
              </n-alert>
              <n-text depth="3" style="font-size: 13px">
                <b>多实例逻辑：</b><br/>
                你可以为不同级别的通知配置不同的机器人。例如：<br/>
                1. <b>核心监控</b>：专门订阅系统备份、升级通知。<br/>
                2. <b>任务详情</b>：专门接收打标签、重复项扫描的任务日志。
              </n-text>
            </n-card>

            <n-card title="关于交互模式" size="small" segmented>
              <n-text depth="3" style="font-size: 13px">
                <b>Telegram 交互：</b><br/>
                开启交互模式后，你可以通过 Telegram 机器人直接执行 Lens 的部分控制命令（如重启 Docker 容器）。<br/><br/>
                <n-text type="warning"><b>安全提示：</b></n-text><br/>
                开启交互模式时，请务必在授权 ID 列表中填写您自己的 Telegram 用户 ID，否则任何人都可以通过机器人控制您的系统。
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>
    </n-space>

    <!-- 机器人编辑弹窗 -->
    <n-modal v-model:show="showEditModal" preset="card" :title="editingBot.id ? '编辑机器人' : '添加机器人'" style="width: 600px">
      <n-form
        ref="formRef"
        :model="editingBot"
        label-placement="left"
        label-width="100"
        require-mark-placement="right-asterisk"
        size="small"
      >
        <n-form-item label="名称" path="name">
          <n-input v-model:value="editingBot.name" placeholder="例如：Lens 备份助手" />
        </n-form-item>
        <n-form-item label="类型" path="type">
          <n-select v-model:value="editingBot.type" :options="typeOptions" disabled />
        </n-form-item>
        <n-form-item label="Bot Token" path="token">
          <n-input v-model:value="editingBot.token" type="password" show-password-on="click" placeholder="Telegram Bot API Token" />
        </n-form-item>
        <n-form-item label="Chat ID" path="chat_id">
          <n-input v-model:value="editingBot.chat_id" placeholder="接收通知的 Chat ID" />
        </n-form-item>
        <n-form-item label="订阅事件" path="subscribed_events">
          <n-select
            v-model:value="editingBot.subscribed_events"
            multiple
            filterable
            tag
            :options="eventOptions"
            placeholder="请选择要订阅的事件"
          />
        </n-form-item>
        <n-form-item label="开启交互">
          <n-space vertical style="width: 100%">
            <n-switch v-model:value="editingBot.is_interactive" />
            <n-alert v-if="editingBot.is_interactive" type="warning" size="small">
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
          <n-switch v-model:value="editingBot.enabled" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button size="small" @click="showEditModal = false">
            取消
          </n-button>
          <n-button size="small" type="primary" :loading="saving" @click="handleSaveBot">
            确定保存
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 测试消息弹窗 -->
    <n-modal v-model:show="showTestModal" preset="dialog" title="发送测试消息" positive-text="发送" negative-text="取消" @positive-click="sendTestMessage">
      <n-input v-model:value="testMessage" type="textarea" placeholder="输入测试内容..." />
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { 
  NButton, NSpace, NTag, NPopconfirm, NCard, NSwitch, NAlert, NModal, NForm, 
  NFormItem, NInput, NSelect, NH2, NText, NGrid, NGi, NEmpty, useMessage 
} from 'naive-ui'
// 导入提取的逻辑
import { useNotificationManager } from './notification/hooks/useNotificationManager'
import { NOTIFICATION_EVENTS } from '@/constants/events'

interface NotificationBot {
  id: string
  name: string
  type: string
  token: string
  chat_id: string
  enabled: boolean
  subscribed_events: string[]
  is_interactive: boolean
  allowed_user_ids: string[]
}

const {
  settings, showEditModal, showTestModal, saving, testMessage, editingBot,
  fetchSettings, saveSettings, handleAddBot, handleEditBot, handleSaveBot, handleDeleteBot, handleTestBot, sendTestMessage
} = useNotificationManager()

const typeOptions = [
  { label: 'Telegram', value: 'telegram' }
]

const eventOptions = NOTIFICATION_EVENTS

onMounted(fetchSettings)
</script>

<style scoped>
/* 推送通道卡片列表 */
.bot-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.bot-card {
  display: flex;
  flex-direction: column;
  padding: 12px 14px;
  background: var(--info-item-bg, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--info-item-border, rgba(255, 255, 255, 0.08));
  border-radius: 6px;
  transition: border-color 200ms ease, background 200ms ease;
}

.bot-card:hover {
  border-color: rgba(64, 128, 240, 0.3);
}

.bot-card.disabled {
  opacity: 0.7;
}

.bot-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.bot-name {
  font-size: 14px;
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bot-events {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
  min-width: 0;
}

.bot-events .events-label {
  font-size: 12px;
}

.bot-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: auto;
}

/* ============== 移动端适配 ============== */
@media (max-width: 767px) {
  .bot-grid {
    grid-template-columns: 1fr;
  }
}

/* 超窄屏 (≤380px) 兼容 */
@media (max-width: 380px) {
  .bot-card {
    padding: 10px 12px;
  }

  .bot-actions {
    flex-wrap: nowrap;
  }
  .bot-actions :deep(.n-button) {
    flex: 1 1 0;
    margin: 0 !important;
  }
}
</style>