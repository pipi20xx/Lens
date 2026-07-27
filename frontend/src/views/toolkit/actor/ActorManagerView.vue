<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { actorsApi } from '@/api/actors'
import { useNotification, useClipboard } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'

const { success, error: showError } = useNotification()
const { copy: copyToClipboard } = useClipboard()

// ========== 搜索相关 ==========
const embyMode = ref('name')
const embyQuery = ref('')
const embyLoading = ref(false)
const embyResults = ref<any[]>([])
const searchModes = [
  { title: '按名称', value: 'name' },
  { title: '按 ID', value: 'id' }
]

async function handleEmbySearch() {
  if (!embyQuery.value.trim()) return
  embyLoading.value = true
  try {
    const data = await actorsApi.searchEmby(embyQuery.value.trim())
    const res = data as any
    embyResults.value = Array.isArray(res) ? res : (res?.results || [])
  } catch {
    showError('搜索失败')
  } finally {
    embyLoading.value = false
  }
}

// ========== 选中状态与编辑 ==========
const selectedEmby = ref<any>(null)
const editName = ref('')
const nameLoading = ref(false)
const jsonModal = reactive({ show: false, data: {} as any })

watch(selectedEmby, (val) => {
  if (val) editName.value = val.Name
})

async function handleUpdateName() {
  if (!selectedEmby.value || !editName.value.trim()) return
  nameLoading.value = true
  try {
    await actorsApi.updateName(selectedEmby.value.Id, editName.value.trim())
    selectedEmby.value.Name = editName.value.trim()
    success('姓名已更新')
  } catch {
    showError('更新失败')
  } finally {
    nameLoading.value = false
  }
}

function showJson(item: any) {
  jsonModal.data = item
  jsonModal.show = true
}

function copyRawJson() {
  copyToClipboard(JSON.stringify(jsonModal.data, null, 2))
}

function getEmbyAvatar(person: any) {
  if (!person.PrimaryImageTag) return ''
  return `/api/system/img-proxy?id=${person.Id}&tag=${person.PrimaryImageTag}`
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-account-star-outline</v-icon>
      Emby 演员信息维护
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">检索并修改 Emby 库内的演员元数据，支持姓名更正与原始数据审计。</p>

    <v-row>
      <!-- 左侧：Emby 库内检索 -->
      <v-col cols="12" md="7">
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-magnify</v-icon>
            Emby 演员库检索
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div class="d-flex align-center ga-3 mb-4">
              <v-select v-model="embyMode" :items="searchModes" variant="outlined" density="compact"
                hide-details style="max-width:120px" />
              <v-text-field v-model="embyQuery"
                :placeholder="embyMode === 'id' ? '输入 TMDB ID' : '输入姓名关键字'"
                prepend-inner-icon="mdi-magnify" variant="outlined" density="compact" hide-details clearable
                @keydown.enter="handleEmbySearch" />
              <v-btn color="primary" variant="tonal" prepend-icon="mdi-magnify" @click="handleEmbySearch" :loading="embyLoading">执行搜索</v-btn>
            </div>

            <div style="max-height:600px;overflow-y:auto">
              <template v-if="embyResults.length > 0">
                <v-card v-for="person in embyResults" :key="person.Id"
                  @click="selectedEmby = person"
                  rounded="lg" variant="tonal" class="list-card pa-3 mb-2 cursor-pointer"
                  :class="{ 'selected-item': selectedEmby?.Id === person.Id }">
                  <div class="d-flex align-center ga-3">
                    <v-avatar size="40" rounded="lg">
                      <v-img v-if="getEmbyAvatar(person)" :src="getEmbyAvatar(person)" />
                      <v-icon v-else icon="mdi-account" />
                    </v-avatar>
                    <div class="flex-grow-1" style="min-width:0">
                      <div class="font-weight-bold text-body-2">{{ person.Name }}</div>
                      <div class="d-flex ga-2 mt-1">
                        <v-chip size="x-small" variant="tonal">EMBY ID: {{ person.Id }}</v-chip>
                        <v-chip v-if="person.ProviderIds?.Tmdb" size="x-small" variant="tonal" color="info">TMDB ID: {{ person.ProviderIds.Tmdb }}</v-chip>
                      </div>
                    </div>
                    <v-btn icon variant="tonal" size="small" @click.stop="showJson(person)">
                      <v-icon size="18" color="primary">mdi-code-block-braces</v-icon>
                    </v-btn>
                  </div>
                </v-card>
              </template>
              <div v-else class="text-center py-8 text-medium-emphasis">请输入姓名并点击搜索</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- 右侧：信息维护与操作 -->
      <v-col cols="12" md="5">
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-pencil-outline</v-icon>
            资料修改
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <div v-if="selectedEmby">
              <p class="text-caption text-medium-emphasis mb-2">显示姓名 (修改后即时同步至 Emby)</p>
              <div class="d-flex align-center ga-3">
                <v-text-field v-model="editName" placeholder="新姓名" variant="outlined" density="compact" hide-details />
                <v-btn color="primary" variant="flat" prepend-icon="mdi-pencil-outline" @click="handleUpdateName" :loading="nameLoading">执行修改</v-btn>
              </div>
              <p class="text-caption text-medium-emphasis mt-3">选中左侧列表项后即可在此进行编辑。</p>
            </div>
            <div v-else class="text-center py-6 text-medium-emphasis">
              <v-icon size="48" color="grey" class="mb-2">mdi-account-star-outline</v-icon>
              <p>请先在左侧选择一名演员</p>
            </div>
          </v-card-text>
        </v-card>

        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start>mdi-help-circle-outline</v-icon>
            操作指南
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2 text-medium-emphasis">
            <p class="mb-2">1. <strong>姓名修正</strong>：用于修复刮削器导致的译名不统一或错别字。</p>
            <p class="mb-2">2. <strong>元数据审计</strong>：点击右侧文档图标可查看该演员在 Emby 中的全量原始 JSON 数据。</p>
            <p>3. <strong>头像同步</strong>：如果您需要从 TMDB 强制拉取最新头像，请使用"演员实验室"功能。</p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

<!-- JSON 弹窗 -->
<GlassDialog v-model="jsonModal.show" :max-width="800"
  icon="mdi-code-block-braces" title="演员原始元数据 (Raw JSON)" cancel-text="关闭"
>
  <pre class="code-block code-block--flat">{{ JSON.stringify(jsonModal.data, null, 2) }}</pre>
  <template #actions>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-copy" @click="copyRawJson">复制数据</v-btn>
  </template>
</GlassDialog>
  </v-container>
</template>

