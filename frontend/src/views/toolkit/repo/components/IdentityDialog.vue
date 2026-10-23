<script setup lang="ts">
/**
 * 单个仓库的提交者身份。
 * git 的身份属于「这次提交」，存在每个仓库自己的 .git/config 里，
 * 所以这里改的只影响当前仓库；档案（GitHub/Gitea）只是快捷填充。
 */
import { computed, ref, watch } from 'vue'
import GlassDialog from '@/components/common/GlassDialog.vue'
import { repoManagerApi, type RepoIdentity } from '@/api/repoManager'
import { useConfirm, useNotification } from '@/composables'

const props = defineProps<{
  modelValue: boolean
  path: string
  repoName?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'updated', data: RepoIdentity): void
}>()

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()

const show = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val),
})

const loading = ref(false)
const saving = ref(false)
const data = ref<RepoIdentity | null>(null)
const name = ref('')
const email = ref('')

const sourceLabel = computed(() => {
  switch (data.value?.source) {
    case 'repo':
      return '本仓库已单独设置'
    case 'git-global':
      return '来自容器内 git 全局配置'
    case 'settings':
      return '来自设置里的兜底身份'
    default:
      return '尚未设置（git 会拒绝提交）'
  }
})

const providerLabel = (provider: string) => {
  if (provider === 'github') return 'GitHub'
  if (provider === 'gitea') return 'Gitea'
  return '通用'
}

async function load() {
  loading.value = true
  try {
    const res = await repoManagerApi.identity(props.path)
    data.value = res
    name.value = res.local.name || ''
    email.value = res.local.email || ''
  } catch (e: any) {
    showError(e.message || '读取身份失败')
  } finally {
    loading.value = false
  }
}

function useProfile(id: string) {
  const profile = data.value?.identities.find((i) => i.id === id)
  if (!profile) return
  name.value = profile.name
  email.value = profile.email
}

async function save() {
  saving.value = true
  try {
    const res = await repoManagerApi.applyIdentity(props.path, {
      name: name.value.trim(),
      email: email.value.trim(),
    })
    success(res.message || '已保存')
    emit('updated', res)
    show.value = false
  } catch (e: any) {
    showError(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function clearLocal() {
  const ok = await confirm({
    title: '清除本仓库身份',
    content: '将移除该仓库 .git/config 里的 user.name / user.email，回落到上层配置（设置兜底或 git 全局）。',
    confirmText: '清除',
    confirmColor: 'warning',
  })
  if (!ok) return
  saving.value = true
  try {
    const res = await repoManagerApi.applyIdentity(props.path, { name: '', email: '' })
    success(res.message || '已清除')
    emit('updated', res)
    show.value = false
  } catch (e: any) {
    showError(e.message || '清除失败')
  } finally {
    saving.value = false
  }
}

watch(show, (visible) => {
  if (visible) load()
})
</script>

<template>
  <GlassDialog v-model="show" :max-width="560" icon="mdi-account-edit-outline">
    <template #title>
      提交者身份
      <v-chip v-if="repoName" size="x-small" variant="tonal" class="ml-2">{{ repoName }}</v-chip>
    </template>

    <v-progress-linear v-if="loading" indeterminate class="mb-3" />

    <v-alert
      :type="data?.source === 'none' ? 'warning' : 'info'"
      variant="tonal"
      density="compact"
      class="mb-4"
    >
      <div class="text-body-2">
        当前生效：
        <b v-if="data?.display.name">{{ data.display.name }} &lt;{{ data.display.email }}&gt;</b>
        <b v-else>未配置</b>
      </div>
      <div class="text-caption mt-1">{{ sourceLabel }}</div>
    </v-alert>

    <!-- 身份档案快捷填充 -->
    <template v-if="data?.identities.length">
      <div class="text-subtitle-2 mb-2">从身份档案填充</div>
      <div class="d-flex flex-wrap ga-2 mb-4">
        <v-chip
          v-for="profile in data.identities"
          :key="profile.id"
          size="small"
          variant="tonal"
          :color="name === profile.name && email === profile.email ? 'primary' : undefined"
          @click="useProfile(profile.id)"
        >
          {{ profile.label }}
          <span class="text-caption ml-1">{{ providerLabel(profile.provider) }}</span>
        </v-chip>
      </div>
    </template>
    <v-alert v-else type="info" variant="text" density="compact" class="mb-2">
      还没有身份档案。可在「仓库管理设置」里为 GitHub / Gitea 各建一个，之后克隆会自动套用。
    </v-alert>

    <v-text-field
      v-model="name"
      label="提交者姓名 (user.name)"
      density="compact"
      variant="outlined"
      hide-details
      class="mb-3"
    />
    <v-text-field
      v-model="email"
      label="提交者邮箱 (user.email)"
      density="compact"
      variant="outlined"
      hide-details
      class="mb-2"
    />
    <div class="text-caption">
      写入该仓库的 <code>.git/config</code>，只影响这一个仓库。
    </div>

    <template #actions>
      <v-btn
        v-if="data?.local.name"
        variant="tonal"
        color="error"
        prepend-icon="mdi-account-remove-outline"
        :loading="saving"
        @click="clearLocal"
      >
        清除本仓库身份
      </v-btn>
      <v-btn color="primary" variant="tonal" prepend-icon="mdi-content-save-outline" :loading="saving" @click="save">保存</v-btn>
    </template>
  </GlassDialog>
</template>
