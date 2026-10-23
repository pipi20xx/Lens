<script setup lang="ts">
/**
 * 仓库管理设置：允许扫描的根目录（安全白名单）、克隆落地目录、提交者身份档案。
 * 两个路径字段都支持「浏览」直接挑文件夹，不用手打绝对路径。
 */
import { computed, ref, watch } from 'vue'
import GlassDialog from '@/components/common/GlassDialog.vue'
import { repoManagerApi, type IdentityProfile, type RepoSettings } from '@/api/repoManager'
import { useNotification } from '@/composables'
import DirectoryPicker from './DirectoryPicker.vue'

const props = defineProps<{ modelValue: boolean }>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'saved'): void
}>()

const { success, error: showError, warning } = useNotification()

const show = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val),
})

const loading = ref(false)
const saving = ref(false)
const roots = ref<string[]>([])
const cloneDir = ref('')
const scanDepth = ref(3)
const authorName = ref('')
const authorEmail = ref('')
const identities = ref<IdentityProfile[]>([])

const pickerOpen = ref(false)
const pickerTarget = ref<'roots' | 'clone_dir'>('roots')
const pickerInitial = ref('')

const providerOptions = [
  { title: 'GitHub', value: 'github' },
  { title: 'Gitea', value: 'gitea' },
  { title: '通用', value: '' },
]

function addIdentity(kind: 'github' | 'gitea' = 'github') {
  identities.value.push({
    id: '',
    label: kind === 'github' ? 'GitHub' : 'Gitea',
    provider: kind,
    name: '',
    email: '',
  })
}

function removeIdentity(index: number) {
  identities.value.splice(index, 1)
}

async function load() {
  loading.value = true
  try {
    const res = await repoManagerApi.getSettings()
    const settings: RepoSettings = res.settings
    roots.value = [...(settings.roots || [])]
    cloneDir.value = settings.clone_dir || ''
    scanDepth.value = settings.scan_depth || 3
    authorName.value = settings.author_name || ''
    authorEmail.value = settings.author_email || ''
    identities.value = (settings.identities || []).map((item) => ({ ...item }))
  } catch (e: any) {
    showError(e.message || '读取设置失败')
  } finally {
    loading.value = false
  }
}

function openPicker(target: 'roots' | 'clone_dir') {
  pickerTarget.value = target
  pickerInitial.value = target === 'roots' ? cloneDir.value || roots.value[0] || '' : cloneDir.value
  pickerOpen.value = true
}

function onPicked(path: string) {
  if (pickerTarget.value === 'clone_dir') {
    cloneDir.value = path
    return
  }
  if (roots.value.includes(path)) {
    warning('该目录已在列表中')
    return
  }
  roots.value.push(path)
}

function removeRoot(index: number) {
  roots.value.splice(index, 1)
}

async function save() {
  if (!roots.value.length) {
    showError('至少需要一个仓库根目录')
    return
  }
  saving.value = true
  try {
    await repoManagerApi.saveSettings({
      roots: roots.value,
      clone_dir: cloneDir.value.trim(),
      scan_depth: Number(scanDepth.value) || 3,
      author_name: authorName.value.trim(),
      author_email: authorEmail.value.trim(),
      identities: identities.value.filter((i) => i.name.trim() && i.email.trim()),
    })
    success('设置已保存')
    emit('saved')
    show.value = false
  } catch (e: any) {
    showError(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

watch(show, (visible) => {
  if (visible) load()
})
</script>

<template>
  <GlassDialog v-model="show" :max-width="680" title="仓库管理设置" icon="mdi-cog-outline">
    <v-progress-linear v-if="loading" indeterminate class="mb-3" />

    <!-- 允许的根目录 -->
    <div class="d-flex align-center ga-3 mb-1">
      <span class="text-subtitle-2">允许管理的仓库根目录</span>
      <v-btn
        size="small"
        variant="tonal"
        color="primary"
        prepend-icon="mdi-folder-search-outline"
        @click="openPicker('roots')"
      >
        浏览添加
      </v-btn>
    </div>
    <div class="text-caption mb-2">
      只扫描这些目录下的 git 仓库，同时作为安全白名单 —— 范围外的路径一律拒绝操作。
    </div>
    <div class="root-list mb-4">
      <div v-if="!roots.length" class="text-caption pa-2">
        还没有添加任何目录
      </div>
      <div v-for="(root, index) in roots" :key="root" class="root-row">
        <v-icon size="16" color="primary">mdi-folder-outline</v-icon>
        <span class="root-path">{{ root }}</span>
        <v-spacer />
        <v-btn
          icon="mdi-close"
          variant="text"
          size="x-small"
          density="compact"
          color="error"
          title="移除"
          @click="removeRoot(index)"
        />
      </div>
    </div>

    <!-- 克隆落地目录 -->
    <div class="text-subtitle-2 mb-1">克隆落地目录</div>
    <div class="d-flex ga-3 align-center mb-1">
      <v-text-field
        v-model="cloneDir"
        density="compact"
        variant="outlined"
        hide-details
        placeholder="/vol1/1000/NVME/repos"
      />
      <v-btn
        size="small"
        variant="tonal"
        color="info"
        prepend-icon="mdi-folder-search-outline"
        @click="openPicker('clone_dir')"
      >
        浏览
      </v-btn>
    </div>
    <div class="text-caption mb-4">
      「克隆仓库」默认落在这里，必须位于上面的某个根目录之内。
    </div>

    <!-- 扫描深度 -->
    <v-text-field
      v-model.number="scanDepth"
      type="number"
      label="扫描深度"
      variant="outlined"
      density="compact"
      hide-details="auto"
      class="mb-4"
      hint="相对根目录递归查找 .git 的层数，目录很多时不要设太大"
      persistent-hint
    />

    <!-- 提交者身份档案 -->
    <div class="d-flex align-center flex-wrap ga-3 mb-1">
      <span class="text-subtitle-2">提交者身份档案</span>
      <v-btn size="small" variant="tonal" color="primary" prepend-icon="mdi-plus" @click="addIdentity('github')">
        GitHub
      </v-btn>
      <v-btn size="small" variant="tonal" color="secondary" prepend-icon="mdi-plus" @click="addIdentity('gitea')">
        Gitea
      </v-btn>
    </div>
    <div class="text-caption mb-2">
      给每个远端账号各建一个。克隆仓库时会按来源自动套用对应身份，之后也能在仓库页单独改。
    </div>

    <div v-if="!identities.length" class="text-caption pa-2 mb-3">
      还没有身份档案
    </div>
    <div v-for="(ident, index) in identities" :key="index" class="identity-card mb-2">
      <div class="d-flex ga-3 align-center">
        <v-text-field
          v-model="ident.label"
          label="名称"
          density="compact"
          variant="outlined"
          hide-details
        />
        <v-select
          v-model="ident.provider"
          :items="providerOptions"
          item-title="title"
          item-value="value"
          label="对应"
          density="compact"
          variant="outlined"
          hide-details
          style="max-width: 140px"
        />
        <v-btn
          icon="mdi-delete-outline"
          variant="text"
          size="x-small"
          density="compact"
          color="error"
          title="删除"
          @click="removeIdentity(index)"
        />
      </div>
      <div class="d-flex ga-3 align-center mt-3">
        <v-text-field
          v-model="ident.name"
          label="提交者姓名 user.name"
          density="compact"
          variant="outlined"
          hide-details
        />
        <v-text-field
          v-model="ident.email"
          label="提交者邮箱 user.email"
          density="compact"
          variant="outlined"
          hide-details
        />
      </div>
    </div>

    <!-- 兜底身份 -->
    <div class="text-subtitle-2 mt-4 mb-2">兜底身份（可选）</div>
    <v-row dense>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model="authorName"
          label="提交者姓名"
          variant="outlined"
          density="compact"
          hide-details
        />
      </v-col>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model="authorEmail"
          label="提交者邮箱"
          variant="outlined"
          density="compact"
          hide-details
        />
      </v-col>
    </v-row>
    <div class="text-caption mt-2">
      优先级：仓库自己的 <code>.git/config</code> → 容器内 git 全局配置 → 这里的兜底。
    </div>

    <DirectoryPicker
      v-model="pickerOpen"
      :initial-path="pickerInitial"
      :title="pickerTarget === 'roots' ? '选择仓库根目录' : '选择克隆落地目录'"
      @picked="onPicked"
    />

    <template #actions>
      <v-btn color="primary" variant="tonal" :loading="saving" @click="save">保存</v-btn>
    </template>
  </GlassDialog>
</template>

<style scoped>
.root-list {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  overflow: hidden;
}
.root-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  font-size: 12.5px;
}
.root-row + .root-row {
  border-top: 1px solid rgba(var(--v-border-color), 0.4);
}
.root-path {
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.identity-card {
  padding: 10px;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
}
</style>
