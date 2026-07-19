<template>
  <n-card title="会话管理" size="small" segmented>
    <n-space vertical size="large">
      <n-alert type="info" title="管理您的登录会话">
        查看所有已登录的设备并踢出可疑设备。
      </n-alert>

      <n-space justify="space-between" align="center">
        <n-text depth="3">共 {{ sessions.length }} 个活跃会话</n-text>
        <n-button 
          v-if="sessions.length > 1" 
          type="error" 
          size="small" 
          @click="handleRevokeAll"
        >
          踢出所有其他设备
        </n-button>
      </n-space>

      <n-alert v-if="neverExpire" type="warning" size="small">
        已开启会话永不过期，所有会话将不会自动过期。
      </n-alert>

      <n-spin :show="loading">
        <n-list hoverable clickable>
          <n-list-item v-for="session in sessions" :key="session.session_id">
            <template #prefix>
              <n-icon size="24" :color="session.is_current ? '#18a058' : '#909399'">
                <component :is="session.is_current ? CheckCircleIcon : DevicePhoneMobileIcon" />
              </n-icon>
            </template>
            <n-thing>
              <template #header>
                <n-space align="center">
                  <n-text strong>{{ session.device_info }}</n-text>
                  <n-tag v-if="session.is_current" type="success" size="small">当前会话</n-tag>
                </n-space>
              </template>
              <template #description>
                <n-space vertical size="small">
                  <n-text depth="3" style="font-size: 12px">
                    <n-icon :component="ClockIcon" style="vertical-align: middle; margin-right: 4px;" />
                    {{ session.expires_text }}
                  </n-text>
                  <n-text depth="3" style="font-size: 12px">
                    <n-icon :component="MapPinIcon" style="vertical-align: middle; margin-right: 4px;" />
                    IP: {{ session.ip_address }}
                  </n-text>
                  <n-text depth="3" style="font-size: 12px">
                    <n-icon :component="ArrowPathIcon" style="vertical-align: middle; margin-right: 4px;" />
                    UA: {{ session.user_agent }}
                  </n-text>
                  <n-text depth="3" style="font-size: 12px">
                    <n-icon :component="CalendarIcon" style="vertical-align: middle; margin-right: 4px;" />
                    登录时间: {{ session.login_time }}
                  </n-text>
                </n-space>
              </template>
              <template #footer>
                <n-button 
                  v-if="!session.is_current" 
                  type="error" 
                  size="small" 
                  secondary
                  @click="handleRevokeSession(session.session_id)"
                >
                  踢出设备
                </n-button>
              </template>
            </n-thing>
          </n-list-item>
        </n-list>
        <n-empty v-if="!loading && sessions.length === 0" description="暂无活跃会话" />
      </n-spin>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useMessage } from 'naive-ui'
import { authApi } from '@/api/auth'
import {
  NCard, NSpace, NAlert, NButton, NIcon, NList, NListItem,
  NThing, NText, NTag, NSpin, NEmpty
} from 'naive-ui'
import {
  ArrowPathIcon,
  CalendarIcon,
  CheckCircleIcon,
  ClockIcon,
  DevicePhoneMobileIcon,
  MapPinIcon
} from '@heroicons/vue/24/outline'
const message = useMessage()
const loading = ref(false)
const sessions = ref<any[]>([])
const neverExpire = ref(false)

const loadSessions = async () => {
  loading.value = true
  try {
    const data: any = await authApi.getSessions()
    sessions.value = data.sessions || []
    
    // 获取会话永不过期配置
    const configData: any = await authApi.getSessionConfig()
    neverExpire.value = configData.session_never_expire || false
  } catch (error) {
    message.error('加载会话列表失败')
  } finally {
    loading.value = false
  }
}

const handleRevokeSession = async (sessionId: string) => {
  try {
    await authApi.revokeSession(sessionId)
    message.success('设备已踢出')
    await loadSessions()
  } catch (error) {
    message.error('踢出设备失败')
  }
}

const handleRevokeAll = async () => {
  try {
    await authApi.revokeAllSessions()
    message.success('所有其他设备已踢出')
    await loadSessions()
  } catch (error) {
    message.error('操作失败')
  }
}

onMounted(() => {
  loadSessions()
})
</script>
