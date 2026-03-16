<template>
  <div class="mobile-actor-manager">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">演员信息维护</h1>
      <p class="page-desc">检索并修改 Emby 库内的演员元数据</p>
    </div>

    <!-- 搜索区域 -->
    <n-card class="search-card" :bordered="false">
      <n-tabs v-model:value="activeTab" type="segment">
        <n-tab-pane name="search" tab="搜索演员">
          <n-space vertical class="search-form">
            <n-radio-group v-model:value="embyMode">
              <n-radio-button value="name">按名称</n-radio-button>
              <n-radio-button value="id">按 ID</n-radio-button>
            </n-radio-group>
            <n-input 
              v-model:value="embyQuery" 
              :placeholder="embyMode === 'id' ? '输入 TMDB ID' : '输入姓名关键字'"
              size="large"
              @keyup.enter="handleEmbySearch"
            />
            <n-button 
              type="primary" 
              size="large" 
              block 
              :loading="embyLoading"
              @click="handleEmbySearch"
            >
              搜索
            </n-button>
          </n-space>

          <!-- 搜索结果 -->
          <div v-if="embyResults.length > 0" class="results-list">
            <n-divider>搜索结果 ({{ embyResults.length }})</n-divider>
            <div 
              v-for="person in embyResults" 
              :key="person.Id"
              class="actor-item"
              :class="{ 'selected': selectedEmby?.Id === person.Id }"
              @click="selectActor(person)"
            >
              <n-avatar round size="large" :src="getEmbyAvatar(person)" />
              <div class="actor-info">
                <div class="actor-name">{{ person.Name }}</div>
                <n-space size="small">
                  <n-tag size="tiny" round>ID: {{ person.Id }}</n-tag>
                  <n-tag v-if="person.ProviderIds?.Tmdb" size="tiny" type="info" round>
                    TMDB: {{ person.ProviderIds.Tmdb }}
                  </n-tag>
                </n-space>
              </div>
              <n-button secondary circle size="small" @click.stop="showJson(person)">
                </n-button>
            </div>
          </div>
          <n-empty v-else-if="!embyLoading && hasSearched" description="未找到结果" />
        </n-tab-pane>

        <n-tab-pane name="edit" tab="编辑资料" :disabled="!selectedEmby">
          <div v-if="selectedEmby" class="edit-section">
            <div class="selected-actor">
              <n-avatar round size="huge" :src="getEmbyAvatar(selectedEmby)" />
              <div class="selected-name">{{ selectedEmby.Name }}</div>
              <n-tag size="small" round>Emby ID: {{ selectedEmby.Id }}</n-tag>
            </div>

            <n-divider>修改姓名</n-divider>
            <n-input v-model:value="editName" placeholder="新姓名" size="large" />
            <n-button 
              type="primary" 
              size="large" 
              block 
              :loading="nameLoading"
              @click="handleUpdateName"
            >
              执行修改
            </n-button>

            <n-divider>操作指南</n-divider>
            <n-alert type="info" :bordered="false">
              用于修复刮削器导致的译名不统一或错别字。修改后将即时同步至 Emby。
            </n-alert>
          </div>
          <n-empty v-else description="请先选择一名演员" />
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- JSON 弹窗 -->
    <n-modal v-model:show="jsonModal.show" preset="card" style="width: 90vw; max-width: 600px" title="演员原始元数据">
      <div class="json-wrapper">
        <n-code :code="JSON.stringify(jsonModal.data, null, 2)" language="json" word-wrap />
      </div>
      <template #footer>
        <n-button block type="primary" secondary @click="copyRawJson">
          复制数据
        </n-button>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { 
  useMessage, NSpace, NCard, NInput, NButton, NAvatar, 
  NTag, NEmpty, NCode, NSelect, NModal, NIcon, NTabs, NTabPane,
  NRadioGroup, NRadioButton, NDivider, NAlert
} from 'naive-ui'
// 导入提取的逻辑
import { useActorSearch } from '../../toolkit/actor/hooks/useActorSearch'
import { useActorSync } from '../../toolkit/actor/hooks/useActorSync'

const message = useMessage()
const activeTab = ref('search')
const hasSearched = ref(false)

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

const selectActor = (person: any) => {
  selectedEmby.value = person
  activeTab.value = 'edit'
}

const showJson = (item: any) => { 
  jsonModal.data = item
  jsonModal.show = true
}

const copyRawJson = () => {
  const text = JSON.stringify(jsonModal.data, null, 2)
  navigator.clipboard.writeText(text).then(() => {
    message.success('已复制到剪贴板')
  }).catch(() => {
    message.error('复制失败')
  })
}

const getEmbyAvatar = (person: any) => {
  if (!person.PrimaryImageTag) return ''
  return `/api/system/img-proxy?id=${person.Id}&tag=${person.PrimaryImageTag}` 
}
</script>

<style scoped>
.mobile-actor-manager {
  padding: 16px;
  padding-bottom: 32px;
  background: var(--app-bg-color);
  min-height: 100%;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-color);
  margin: 0 0 8px 0;
}

.page-desc {
  font-size: 14px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.search-card {
  background: var(--card-bg-color);
  border-radius: 16px;
}

.search-form {
  padding: 16px 0;
}

.results-list {
  margin-top: 16px;
}

.actor-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--app-bg-color);
  border-radius: 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.actor-item.selected {
  background: rgba(var(--primary-color-rgb), 0.1);
  border-left: 4px solid var(--primary-color);
}

.actor-item:active {
  transform: scale(0.98);
}

.actor-info {
  flex: 1;
  min-width: 0;
}

.actor-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 4px;
}

.edit-section {
  padding: 16px 0;
}

.selected-actor {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: var(--app-bg-color);
  border-radius: 16px;
  margin-bottom: 16px;
}

.selected-name {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
}

.json-wrapper {
  background: var(--app-bg-color);
  padding: 12px;
  border-radius: 8px;
  max-height: 50vh;
  overflow-y: auto;
}
</style>
