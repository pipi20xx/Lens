<template>
  <div class="mobile-auto-tags-manager">
    <div class="page-header">
      <h1 class="page-title">自动标签助手</h1>
      <p class="page-desc">基于规则自动维护媒体标签</p>
    </div>

    <n-card class="webhook-card" :bordered="false" title="Webhook 自动化">
      <n-space vertical>
        <div class="switch-row">
          <span class="switch-label">启用 Webhook</span>
          <n-switch v-model:value="webhookConfig.enabled" />
        </div>
        <div v-if="webhookConfig.enabled" class="webhook-url">
          <n-input :value="webhookUrl" readonly>
            <template #suffix>
              <n-button size="tiny" secondary @click="copyWebhookUrl">
                复制
              </n-button>
            </template>
          </n-input>
        </div>
        <n-alert type="info" :bordered="false">
          在 Emby 后台添加此 URL，选择 application/json 类型，并勾选"已添加新媒体"事件。
        </n-alert>
      </n-space>
    </n-card>

    <n-card class="rules-card" :bordered="false" title="规则列表">
      <n-space vertical>
        <n-button block type="primary" @click="showAddRuleModal = true">
          <template #icon><n-icon><AddIcon /></n-icon></template>
          添加规则
        </n-button>
        <div v-if="rules.length === 0" class="empty-state">
          <n-empty description="暂无规则" />
        </div>
        <div v-else class="rule-list">
          <div v-for="(rule, index) in rules" :key="index" class="rule-item">
            <div class="rule-info">
              <div class="rule-name">{{ rule.name }}</div>
              <div class="rule-condition">条件: {{ rule.condition }}</div>
              <div class="rule-tags">
                <n-tag v-for="tag in rule.tags" :key="tag" size="small" type="info">
                  {{ tag }}
                </n-tag>
              </div>
            </div>
            <div class="rule-actions">
              <n-button size="small" secondary type="warning" @click="editRule(index)">
                编辑
              </n-button>
              <n-popconfirm @positive-click="deleteRule(index)" positive-text="确认删除" negative-text="取消">
                <template #trigger>
                  <n-button size="small" secondary type="error">
                    删除
                  </n-button>
                </template>
                确定删除此规则？
              </n-popconfirm>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>

    <n-card class="actions-card" :bordered="false" title="操作">
      <n-space vertical>
        <n-button block type="info" secondary @click="runAllRules" :loading="running">
          <template #icon><n-icon><PlayIcon /></n-icon></template>
          运行所有规则
        </n-button>
        <n-button block type="warning" secondary @click="clearAllTags">
          <template #icon><n-icon><ClearIcon /></n-icon></template>
          清空所有标签
        </n-button>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddRuleModal" preset="card" :title="editingRule.id !== null ? '编辑规则' : '添加规则'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="规则名称">
          <n-input v-model:value="editingRule.name" placeholder="规则名称" />
        </n-form-item>
        <n-form-item label="匹配条件">
          <n-input v-model:value="editingRule.condition" placeholder="例如：类型=电影" />
        </n-form-item>
        <n-form-item label="标签">
          <n-dynamic-tags v-model:value="editingRule.tags" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showAddRuleModal = false">取消</n-button>
          <n-button type="primary" @click="saveRule" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NCard, NButton, NSpace, NSwitch, NInput, NAlert, NEmpty, NModal, NForm, NFormItem, NTag, NPopconfirm, NIcon, NDynamicTags } from 'naive-ui'
import { AddOutlined as AddIcon, PlayArrowOutlined as PlayIcon, DeleteOutlineOutlined as ClearIcon } from '@vicons/material'
import { useMessage } from 'naive-ui'

const message = useMessage()
const rules = ref<any[]>([])
const webhookConfig = ref({
  enabled: false,
  secret_token: ''
})
const showAddRuleModal = ref(false)
const running = ref(false)
const saving = ref(false)

const editingRule = ref({
  id: null,
  name: '',
  condition: '',
  tags: []
})

const webhookUrl = computed(() => {
  const baseUrl = window.location.origin
  return `${baseUrl}/api/autotags/webhook?token=${webhookConfig.value.secret_token}`
})

const copyWebhookUrl = () => {
  navigator.clipboard.writeText(webhookUrl.value)
  message.success('URL 已复制到剪贴板')
}

const editRule = (index: number) => {
  editingRule.value = { ...rules.value[index], id: index }
  showAddRuleModal.value = true
}

const saveRule = () => {
  if (!editingRule.value.name || !editingRule.value.condition) {
    message.warning('请填写完整的规则信息')
    return
  }
  saving.value = true
  setTimeout(() => {
    if (editingRule.value.id !== null) {
      rules.value[editingRule.value.id] = { ...editingRule.value }
    } else {
      rules.value.push({
        id: Date.now(),
        ...editingRule.value
      })
    }
    message.success('规则保存成功')
    showAddRuleModal.value = false
    editingRule.value = { id: null, name: '', condition: '', tags: [] }
    saving.value = false
  }, 500)
}

const deleteRule = (index: number) => {
  rules.value.splice(index, 1)
  message.success('规则已删除')
}

const runAllRules = () => {
  running.value = true
  setTimeout(() => {
    message.success('所有规则已执行')
    running.value = false
  }, 1000)
}

const clearAllTags = () => {
  message.info('请在桌面端执行清空操作')
}

rules.value = [
  { id: 1, name: '电影标签', condition: '类型=电影', tags: ['电影', '高清'] },
  { id: 2, name: '剧集标签', condition: '类型=剧集', tags: ['剧集', '连续剧'] }
]
</script>

<style scoped>
.mobile-auto-tags-manager {
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

.webhook-card,
.rules-card,
.actions-card {
  margin-bottom: 12px;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.switch-label {
  font-size: 14px;
  color: var(--text-color);
}

.webhook-url {
  margin-bottom: 12px;
}

.empty-state {
  padding: 24px 0;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rule-item {
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 8px;
}

.rule-info {
  margin-bottom: 8px;
}

.rule-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.rule-condition {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  margin-bottom: 4px;
}

.rule-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.rule-actions {
  display: flex;
  gap: 8px;
}
</style>
