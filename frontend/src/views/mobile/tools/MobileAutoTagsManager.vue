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
          <n-switch v-model:value="webhookConfig.enabled" @update:value="saveWebhookConfig" />
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
        <n-form v-if="webhookConfig.enabled" label-placement="top" size="small">
          <n-form-item label="安全密钥">
            <n-input v-model:value="webhookConfig.secret_token" @blur="saveWebhookConfig" placeholder="自定义 Token" />
          </n-form-item>
          <n-form-item label="写入模式">
            <n-select v-model:value="webhookConfig.write_mode" @update:value="saveWebhookConfig" :options="[
              { label: '合并现有标签', value: 'merge' },
              { label: '覆盖所有标签', value: 'overwrite' }
            ]" />
          </n-form-item>
          <n-form-item label="自动化状态">
            <n-checkbox v-model:checked="webhookConfig.automation_enabled" @update:checked="saveWebhookConfig">
              接收到 item.added 事件时自动执行规则比对
            </n-checkbox>
          </n-form-item>
          <n-form-item label="处理延迟(秒)">
            <n-input-number v-model:value="webhookConfig.delay_seconds" @blur="saveWebhookConfig" :min="0" :max="3600" />
          </n-form-item>
        </n-form>
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
        <div v-else class="rule-list" @dragover.prevent @drop="onDrop">
          <div v-for="(rule, index) in rules" :key="index" class="rule-item-wrapper">
            <MobileRuleCard 
              :rule="rule" 
              :index="index"
              @edit="editRule(index)"
              @delete="deleteRule(index)"
              @drag-start="onDragStart"
              @drag-enter="onDragEnter"
            />
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
        <n-button block type="warning" secondary @click="testWrite" :loading="testing">
          <template #icon><n-icon><TestIcon /></n-icon></template>
          测试写入
        </n-button>
        <n-button block type="error" secondary @click="clearAllTags">
          <template #icon><n-icon><ClearIcon /></n-icon></template>
          清空所有标签
        </n-button>
        <n-button block secondary @click="showClearSpecificModal = true">
          <template #icon><n-icon><FilterIcon /></n-icon></template>
          清空特定标签
        </n-button>
      </n-space>
    </n-card>

    <n-modal v-model:show="showAddRuleModal" preset="card" :title="editingRule.id !== null ? '编辑规则' : '添加规则'" style="width: 95vw; max-width: 500px">
      <MobileRuleEditorModal 
        v-model:show="showAddRuleModal"
        :rule="editingRule"
        :is-new="editingRule.id === null"
        @confirm="saveRule"
      />
    </n-modal>

    <n-modal v-model:show="showClearSpecificModal" preset="card" title="清空特定标签" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="选择标签">
          <n-dynamic-tags v-model:value="clearSpecificTags" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showClearSpecificModal = false">取消</n-button>
          <n-button type="error" @click="handleClearSpecific">清空</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { NCard, NButton, NSpace, NSwitch, NInput, NAlert, NEmpty, NModal, NIcon, NSelect, NCheckbox, NInputNumber, NDynamicTags, NForm, NFormItem } from 'naive-ui'
import { AddOutlined as AddIcon, PlayArrowOutlined as PlayIcon, DeleteOutlineOutlined as ClearIcon, ScienceOutlined as TestIcon, FilterListOutlined as FilterIcon } from '@vicons/material'
import { useMessage } from 'naive-ui'
import { useAutoTags } from '../../toolkit/autotags/useAutoTags'
import MobileRuleEditorModal from './MobileRuleEditorModal.vue'
import MobileRuleCard from './MobileRuleCard.vue'
import axios from 'axios'

const message = useMessage()
const { rules, fetchRules, saveRules, startTask, clearAll, clearSpecific, testWrite: testWriteApi } = useAutoTags()

const webhookConfig = ref({
  enabled: false,
  secret_token: '',
  write_mode: 'merge',
  automation_enabled: true,
  delay_seconds: 10
})
const showAddRuleModal = ref(false)
const showClearSpecificModal = ref(false)
const running = ref(false)
const saving = ref(false)
const testing = ref(false)
const draggedIndex = ref<number | null>(null)

const editingRule = ref({
  id: null as number | null,
  name: '',
  tag: '',
  item_type: 'all',
  match_all_conditions: false,
  is_negative_match: false,
  conditions: { countries: [], genres: [], years_text: '' }
})

const clearSpecificTags = ref<string[]>([])

const webhookUrl = computed(() => {
  const baseUrl = window.location.origin
  return `${baseUrl}/api/autotags/webhook?token=${webhookConfig.value.secret_token}`
})

const copyWebhookUrl = () => {
  navigator.clipboard.writeText(webhookUrl.value)
  message.success('URL 已复制到剪贴板')
}

const saveWebhookConfig = async () => {
  try {
    await axios.post('/api/autotags/webhook-config', webhookConfig.value)
    message.success('Webhook 配置已更新')
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  }
}

const loadWebhookConfig = async () => {
  try {
    const res = await axios.get('/api/autotags/webhook-config')
    Object.assign(webhookConfig.value, res.data)
  } catch (e: any) {
    console.error('加载 webhook 配置失败:', e)
  }
}

const editRule = (index: number) => {
  const rule = rules.value[index]
  editingRule.value = { 
    ...rule, 
    id: index,
    conditions: { ...rule.conditions }
  }
  showAddRuleModal.value = true
}

const saveRule = async () => {
  if (!editingRule.value.name || !editingRule.value.tag) {
    message.warning('请填写完整的规则信息')
    return
  }
  saving.value = true
  try {
    const newRules = [...rules.value]
    if (editingRule.value.id !== null) {
      newRules[editingRule.value.id] = { 
        name: editingRule.value.name,
        tag: editingRule.value.tag,
        item_type: editingRule.value.item_type,
        match_all_conditions: editingRule.value.match_all_conditions,
        is_negative_match: editingRule.value.is_negative_match,
        conditions: editingRule.value.conditions
      }
    } else {
      newRules.push({
        name: editingRule.value.name,
        tag: editingRule.value.tag,
        item_type: editingRule.value.item_type,
        match_all_conditions: editingRule.value.match_all_conditions,
        is_negative_match: editingRule.value.is_negative_match,
        conditions: editingRule.value.conditions
      })
    }
    await saveRules(newRules)
    message.success('规则保存成功')
    showAddRuleModal.value = false
    editingRule.value = { 
      id: null, 
      name: '', 
      tag: '', 
      item_type: 'all',
      match_all_conditions: false,
      is_negative_match: false,
      conditions: { countries: [], genres: [], years_text: '' }
    }
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const deleteRule = async (index: number) => {
  try {
    const newRules = [...rules.value]
    newRules.splice(index, 1)
    await saveRules(newRules)
    message.success('规则已删除')
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

const runAllRules = async () => {
  running.value = true
  try {
    await startTask({ all: true })
    message.success('所有规则已执行')
  } catch (e: any) {
    message.error('执行失败: ' + (e.message || '未知错误'))
  } finally {
    running.value = false
  }
}

const clearAllTags = async () => {
  try {
    await clearAll()
    message.success('所有标签已清空')
  } catch (e: any) {
    message.error('清空失败: ' + (e.message || '未知错误'))
  }
}

const testWrite = async () => {
  testing.value = true
  try {
    await testWriteApi()
    message.success('测试写入成功')
  } catch (e: any) {
    message.error('测试写入失败: ' + (e.message || '未知错误'))
  } finally {
    testing.value = false
  }
}

const handleClearSpecific = async () => {
  if (clearSpecificTags.value.length === 0) {
    message.warning('请选择要清空的标签')
    return
  }
  try {
    await clearSpecific(clearSpecificTags.value)
    message.success('指定标签已清空')
    showClearSpecificModal.value = false
    clearSpecificTags.value = []
  } catch (e: any) {
    message.error('清空失败: ' + (e.message || '未知错误'))
  }
}

const onDragStart = (index: number) => { 
  draggedIndex.value = index 
}

const onDragEnter = (index: number) => {
  if (draggedIndex.value === null || draggedIndex.value === index) return
  const newRules = [...rules.value]
  const item = newRules.splice(draggedIndex.value, 1)[0]
  newRules.splice(index, 0, item)
  rules.value = newRules
  draggedIndex.value = index
}

const onDrop = async () => { 
  draggedIndex.value = null
  await saveRules(rules.value)
}

onMounted(() => {
  fetchRules()
  loadWebhookConfig()
})
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
  margin-bottom: 16px;
}

.webhook-card :deep(.n-card__content) {
  padding: 16px;
}

.webhook-card :deep(.n-form-item) {
  margin-bottom: 16px;
}

.webhook-card :deep(.n-form-item-label) {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 8px;
}

.webhook-card :deep(.n-input),
.webhook-card :deep(.n-input-number),
.webhook-card :deep(.n-select) {
  width: 100%;
}

.webhook-card :deep(.n-checkbox) {
  font-size: 13px;
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.switch-label {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.webhook-url {
  margin-bottom: 16px;
}

.webhook-url :deep(.n-input) {
  font-size: 13px;
}

.webhook-url :deep(.n-input__input-el) {
  color: var(--text-color-2);
}

.empty-state {
  padding: 24px 0;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rule-item-wrapper {
  transition: all 0.2s ease;
}

.rule-item-wrapper.is-dragging {
  opacity: 0.5;
  transform: scale(0.98);
}

.rule-item-wrapper.drag-over {
  border-top: 2px solid var(--n-primary-color);
}

</style>
