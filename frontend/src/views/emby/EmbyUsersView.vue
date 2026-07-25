<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { embyUsersApi } from '@/api/embyUsers'
import { useNotification } from '@/composables'
import { useConfirm } from '@/composables'

const { success, error: showError } = useNotification()
const { confirm } = useConfirm()
const users = ref<any[]>([])
const loading = ref(true)

async function loadUsers() {
  try {
    loading.value = true
    const res = await embyUsersApi.getUsers()
    users.value = Array.isArray(res) ? res : []
  } catch (err: any) {
    showError('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

async function deleteUser(id: string, name: string) {
  const ok = await confirm({ title: '删除用户', content: `确定要删除用户 "${name}" 吗？`, confirmColor: 'error' })
  if (!ok) return
  try {
    await embyUsersApi.deleteUser(id)
    success('用户已删除')
    loadUsers()
  } catch (err: any) {
    showError('删除失败')
  }
}

onMounted(loadUsers)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-6">
      <v-icon start>mdi-account-group-outline</v-icon>
      Emby 用户管理
    </h1>

    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <span>用户列表</span>
        <v-spacer />
        <v-btn prepend-icon="mdi-refresh" variant="tonal" size="small" @click="loadUsers" :loading="loading">
          刷新
        </v-btn>
      </v-card-title>

      <v-divider />

      <v-table class="bg-transparent">
        <thead>
          <tr>
            <th>用户名</th>
            <th>状态</th>
            <th>管理员</th>
            <th>最近活动</th>
            <th class="text-right">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="5" class="text-center py-8"><v-progress-circular indeterminate color="primary" /></td>
          </tr>
          <tr v-else-if="!users.length">
            <td colspan="5" class="text-center py-8 text-medium-emphasis">暂无用户数据</td>
          </tr>
          <tr v-for="user in users" :key="user.Id">
            <td class="font-weight-medium">{{ user.Name }}</td>
            <td>
              <v-chip :color="user.IsDisabled ? 'error' : 'success'" size="small" variant="tonal" label>
                {{ user.IsDisabled ? '已禁用' : '正常' }}
              </v-chip>
            </td>
            <td>
              <v-icon v-if="user.IsAdmin" color="warning" size="small">mdi-shield-check</v-icon>
              <span v-else class="text-medium-emphasis">-</span>
            </td>
            <td class="text-medium-emphasis">{{ user.LastActivityDate || '-' }}</td>
            <td class="text-right">
              <v-btn icon="mdi-delete-outline" variant="text" size="small" color="error" @click="deleteUser(user.Id, user.Name)" />
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>
</template>
