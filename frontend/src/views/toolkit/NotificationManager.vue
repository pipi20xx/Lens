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

              <n-data-table
                :columns="columns"
                :data="settings.bots"
                :bordered="false"
                size="small"
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
import { onMounted, h } from 'vue'
import { 
  NButton, NSpace, NTag, NPopconfirm, NCard, NSwitch, NAlert, NDataTable, NModal, NForm, 
  NFormItem, NInput, NSelect, NH2, NText, NGrid, NGi, DataTableColumns, useMessage, NIcon 
} from 'naive-ui'
import { 
  AddOutlined as AddIcon,
  SendOutlined as TestIcon,
  EditOutlined as EditIcon,
  DeleteOutlined as DeleteIcon,
  SaveOutlined as SaveIcon,
  CloseOutlined as CloseIcon
} from '@vicons/material'

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

const renderIcon = (icon: any) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const columns: DataTableColumns<NotificationBot> = [
  { title: '机器人名称', key: 'name' },
  { 
    title: '状态', 
    key: 'enabled',
    width: 100,
    render(row) {
      return h(NTag, { type: row.enabled ? 'success' : 'default', size: 'small', round: true, quaternary: true }, { default: () => row.enabled ? '运行中' : '已停用' })
    }
  },
  {
    title: '订阅事件',
    key: 'subscribed_events',
    render(row) {
      return h(NSpace, { size: 'small' }, {
        default: () => row.subscribed_events.map(ev => h(NTag, { size: 'tiny', bordered: false, type: 'info', quaternary: true }, { default: () => ev }))
      })
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 240,
    render(row) {
      return h(NSpace, { justify: 'end' }, {
        default: () => [
          h(NButton, { 
            size: 'tiny', 
            type: 'info',
            secondary: true, 
            onClick: () => handleTestBot(row.id) 
          }, { 
            default: () => '测试' 
          }),
          h(NButton, { 
            size: 'tiny', 
            secondary: true,
            onClick: () => handleEditBot(row) 
          }, { 
            default: () => '编辑' 
          }),
          h(NPopconfirm, { onPositiveClick: () => handleDeleteBot(row.id) }, {
            trigger: () => h(NButton, { 
              size: 'tiny', 
              type: 'error', 
              secondary: true 
            }, { 
              default: () => '删除' 
            }),
            default: () => '确定删除该机器人吗？'
          })
        ]
      })
    }
  }
]

onMounted(fetchSettings)
</script>

<style scoped>
</style>