<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <!-- 页面标题区 -->
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">演员信息维护</n-text></n-h2>
        <n-text depth="3">检索并修改 Emby 库内的演员元数据，支持姓名更正与原始数据审计。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：Emby 库内检索 -->
        <n-gi span="24 m:16">
          <n-card title="Emby 演员库检索" size="small" segmented>
            <n-input-group>
              <n-select v-model:value="embyMode" :options="searchModes" style="width: 110px" />
              <n-input v-model:value="embyQuery" :placeholder="embyMode === 'id' ? '输入 TMDB ID' : '输入姓名关键字'" @keyup.enter="handleEmbySearch" />
              <n-button type="primary" secondary @click="handleEmbySearch" :loading="embyLoading">
                执行搜索
              </n-button>
            </n-input-group>

            <n-scrollbar style="max-height: 600px; margin-top: 12px">
              <n-list v-if="embyResults.length > 0" hoverable clickable>
                <n-list-item 
                  v-for="person in embyResults" 
                  :key="person.Id" 
                  :class="{ 'selected-item': selectedEmby?.Id === person.Id }"
                  @click="selectedEmby = person"
                >
                  <template #prefix>
                    <n-avatar round size="large" :src="getEmbyAvatar(person)" />
                  </template>
                  <n-thing :title="person.Name">
                    <template #description>
                      <n-space>
                        <n-tag size="tiny" tertiary round>EMBY ID: {{ person.Id }}</n-tag>
                        <n-tag v-if="person.ProviderIds?.Tmdb" size="tiny" type="info" quaternary round>TMDB ID: {{ person.ProviderIds.Tmdb }}</n-tag>
                      </n-space>
                    </template>
                  </n-thing>
                  <template #suffix>
                    <n-button secondary circle size="tiny" type="primary" @click.stop="showJson(person)">
                      <template #icon><n-icon color="var(--primary-color)"><CodeIcon /></n-icon></template>
                    </n-button>
                  </template>
                </n-list-item>
              </n-list>
              <n-empty v-else description="请输入姓名并点击搜索" />
            </n-scrollbar>
          </n-card>
        </n-gi>

        <!-- 右侧：信息维护与操作 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <n-card title="资料修改" size="small" segmented>
              <div v-if="selectedEmby">
                <n-descriptions label-placement="top" :column="1">
                  <n-descriptions-item label="显示姓名 (修改后即时同步至 Emby)">
                    <n-input-group>
                      <n-input v-model:value="editName" placeholder="新姓名" />
                      <n-button type="primary" @click="handleUpdateName" :loading="nameLoading">
                        执行修改
                      </n-button>
                    </n-input-group>
                  </n-descriptions-item>
                </n-descriptions>
                <n-text depth="3" style="font-size: 12px; margin-top: 12px; display: block;">
                  选中左侧列表项后即可在此进行编辑。
                </n-text>
              </div>
              <n-empty v-else description="请先在左侧选择一名演员" size="small" />
            </n-card>

            <n-card title="操作指南" size="small" segmented>
              <n-text depth="3" style="font-size: 13px">
                1. <b>姓名修正</b>：用于修复刮削器导致的译名不统一或错别字。<br/>
                2. <b>元数据审计</b>：点击右侧代码图标可查看该演员在 Emby 中的全量原始 JSON 数据。<br/>
                3. <b>头像同步</b>：如果您需要从 TMDB 强制拉取最新头像，请使用“演员实验室”功能。
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>

      <!-- JSON 弹窗 -->
      <n-modal v-model:show="jsonModal.show" preset="card" style="width: 800px" title="演员原始元数据 (Raw JSON)">
        <div class="json-code-wrapper">
          <n-code :code="JSON.stringify(jsonModal.data, null, 2)" language="json" word-wrap />
        </div>
        <template #footer>
          <n-button block type="primary" secondary @click="copyRawJson">
            复制数据
          </n-button>
        </template>
      </n-modal>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { 
  useMessage, NSpace, NH2, NText, NCard, NInput, NButton, NInputGroup, 
  NList, NListItem, NAvatar, NThing, NScrollbar, NEmpty, NGi, NGrid, 
  NDescriptions, NDescriptionsItem, NCode, NTag, NSelect, NModal, NIcon 
} from 'naive-ui'
import { 
  TerminalOutlined as CodeIcon,
  SearchOutlined as SearchIcon,
  SaveOutlined as SaveIcon,
  ContentCopyOutlined as CopyIcon
} from '@vicons/material'

// 导入提取的逻辑
import { useActorSearch } from './actor/hooks/useActorSearch'
import { useActorSync } from './actor/hooks/useActorSync'

const message = useMessage()
const searchModes = [{ label: '按名称', value: 'name' }, { label: '按 ID', value: 'id' }]

// 1. 搜索逻辑
const { 
  embyMode, embyQuery, embyLoading, embyResults,
  handleEmbySearch 
} = useActorSearch()

// 2. 状态管理
const selectedEmby = ref<any>(null)
const editName = ref('')
const jsonModal = reactive({ show: false, data: {} as any })

watch(selectedEmby, (val) => { if (val) editName.value = val.Name })

// 3. 同步逻辑
const { 
  nameLoading, 
  handleUpdateName: updateName 
} = useActorSync(() => handleEmbySearch())

const handleUpdateName = () => updateName(selectedEmby.value, editName.value)

const showJson = (item: any) => { jsonModal.data = item; jsonModal.show = true; }
const copyRawJson = () => {
  const text = JSON.stringify(jsonModal.data, null, 2)
  const textArea = document.createElement("textarea")
  textArea.value = text; document.body.appendChild(textArea); textArea.select()
  document.execCommand('copy'); document.body.removeChild(textArea)
  message.success('已复制到剪贴板')
}

const getEmbyAvatar = (person: any) => {
  if (!person.PrimaryImageTag) return ''
  return `/api/system/img-proxy?id=${person.Id}&tag=${person.PrimaryImageTag}` 
}
</script>

<style scoped>
.selected-item { 
  background-color: rgba(var(--primary-color-rgb), 0.1) !important; 
  border-left: 4px solid var(--primary-color); 
}

.json-code-wrapper { 
  background: var(--card-bg-color); 
  padding: 16px; 
  border-radius: 8px; 
  max-height: 60vh; 
  overflow-y: auto; 
  border: 1px solid var(--border-color); 
}
</style>