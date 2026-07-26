<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { dockerApi } from '@/api/docker'
import { useNotification } from '@/composables'

const { success, error: showError } = useNotification()

const props = defineProps<{
  active: boolean
  hostId: string | null
}>()

// ========== 自动加载 ==========
watch([() => props.active, () => props.hostId], ([active, hostId]) => {
  if (active && hostId) loadSystemInfo()
})
onMounted(() => { if (props.active && props.hostId) loadSystemInfo() })

// ========== 环境信息 ==========
const systemInfo = ref({ docker: '', compose: '', os: '', status: '' })
const systemInfoLoading = ref(false)
const installing = ref(false)
const actionLoading = ref<string | null>(null)

async function loadSystemInfo() {
  if (!props.hostId) return
  systemInfoLoading.value = true
  try {
    const data = await dockerApi.getSystemInfo(props.hostId)
    systemInfo.value = data || { docker: '', compose: '', os: '', status: '' }
  } catch { /* ignore */ }
  finally { systemInfoLoading.value = false }
}

async function handleServiceAction(action: string) {
  if (!props.hostId) return
  actionLoading.value = action
  try {
    const res = await dockerApi.serviceAction(props.hostId, action)
    if (res?.success) success(`服务已尝试${action === 'start' ? '启动' : action === 'stop' ? '停止' : '重启'}`)
    else showError('操作失败')
    setTimeout(loadSystemInfo, 1000)
  } catch { showError('请求失败') }
  finally { actionLoading.value = null }
}

// ========== 修复/安装 ==========
const showRepairModal = ref(false)
const showResultModal = ref(false)
const resultOutput = ref('')
const repairForm = ref({ useMirror: true, proxy: '' })

async function handleRepair() {
  if (!props.hostId) return
  showRepairModal.value = false; installing.value = true
  try {
    const res = await dockerApi.installEnv(props.hostId, repairForm.value.useMirror, repairForm.value.proxy)
    resultOutput.value = res?.stdout || res?.stderr || '安装已完成。'
    showResultModal.value = true
    if (res?.success) success('环境任务执行完毕')
    else showError('安装过程中出现错误')
    loadSystemInfo()
  } catch (err: any) { showError('请求失败: ' + (err.message || '')) }
  finally { installing.value = false }
}

defineExpose({ loadSystemInfo })
</script>

<template>
  <div>
    <v-card class="liquid-glass-card" rounded="xl">
      <v-card-title class="d-flex align-center pa-4">
        <v-icon start>mdi-information-outline</v-icon> 环境检测
        <v-spacer />
        <v-btn size="small" variant="tonal" color="warning" prepend-icon="mdi-wrench-outline" @click="showRepairModal = true" :loading="installing" class="mr-2">一键修复/安装</v-btn>
        <v-btn size="small" variant="tonal" prepend-icon="mdi-refresh" @click="loadSystemInfo" :loading="systemInfoLoading">重新检测</v-btn>
      </v-card-title>
      <v-divider />
      <v-progress-linear v-if="systemInfoLoading" indeterminate color="primary" class="ma-4" />
      <v-card-text v-else class="pa-4">
        <v-row>
          <v-col cols="12" sm="6">
            <v-card variant="outlined" rounded="lg" class="pa-3">
              <div class="text-caption text-medium-emphasis mb-1">Docker 版本</div>
              <v-chip :color="systemInfo.docker === '未安装' ? 'error' : 'success'" size="small" variant="tonal">{{ systemInfo.docker || '-' }}</v-chip>
            </v-card>
          </v-col>
          <v-col cols="12" sm="6">
            <v-card variant="outlined" rounded="lg" class="pa-3">
              <div class="text-caption text-medium-emphasis mb-1">Compose 版本</div>
              <v-chip :color="systemInfo.compose === '未安装' ? 'error' : 'success'" size="small" variant="tonal">{{ systemInfo.compose || '-' }}</v-chip>
            </v-card>
          </v-col>
          <v-col cols="12" sm="6">
            <v-card variant="outlined" rounded="lg" class="pa-3">
              <div class="text-caption text-medium-emphasis mb-1">服务状态</div>
              <div class="d-flex align-center ga-2">
                <v-chip :color="systemInfo.status === 'active' ? 'success' : 'error'" size="small" variant="tonal">{{ systemInfo.status === 'active' ? '运行中' : systemInfo.status === 'inactive' ? '已停止' : '未知' }}</v-chip>
                <v-btn-group density="compact" size="small">
                  <v-btn v-if="systemInfo.status !== 'active'" variant="tonal" color="success" prepend-icon="mdi-play" :loading="actionLoading === 'start'" @click="handleServiceAction('start')">启动</v-btn>
                  <v-btn v-if="systemInfo.status === 'active'" variant="tonal" color="error" prepend-icon="mdi-stop" :loading="actionLoading === 'stop'" @click="handleServiceAction('stop')">停止</v-btn>
                  <v-btn variant="tonal" color="warning" prepend-icon="mdi-restart" :loading="actionLoading === 'restart'" @click="handleServiceAction('restart')">重启</v-btn>
                </v-btn-group>
              </div>
            </v-card>
          </v-col>
          <v-col cols="12" sm="6">
            <v-card variant="outlined" rounded="lg" class="pa-3">
              <div class="text-caption text-medium-emphasis mb-1">操作系统</div>
              <span class="text-body-2">{{ systemInfo.os || '-' }}</span>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <v-alert v-if="installing" type="warning" variant="tonal" class="mt-4" title="正在安装环境" text="正在远程主机上下载并安装 Docker 及 Docker Compose，这通常需要 1-3 分钟，请耐心等待..." />
    <v-alert type="info" variant="tonal" class="mt-4" title="环境说明">本页面显示的是远程 Docker 主机的实时环境状态。如果 Docker 或 Compose 未安装，您可以使用「一键修复」功能尝试自动安装。</v-alert>

    <!-- 修复/安装配置弹窗 -->
    <v-dialog v-model="showRepairModal" max-width="450" scrollable>
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4"><v-icon start>mdi-wrench-outline</v-icon> 环境修复/安装配置</v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <v-switch v-model="repairForm.useMirror" label="使用国内镜像" density="compact" color="primary" hint="开启后使用阿里云镜像安装，国内环境建议开启" persistent-hint class="mb-3" />
          <v-text-field v-model="repairForm.proxy" label="安装代理" variant="outlined" density="compact" placeholder="例如: http://192.168.1.10:7890" hint="仅在安装过程中生效。留空则不使用代理。" persistent-hint class="mb-3" />
          <v-alert type="warning" variant="tonal" density="compact" text="此操作将修改远程主机的系统组件。" />
        </v-card-text>
        <v-divider />
        <div class="d-flex justify-end ga-2 pa-4">
          <v-btn variant="tonal" color="grey" prepend-icon="mdi-close" @click="showRepairModal = false">取消</v-btn>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-wrench-outline" @click="handleRepair" :loading="installing">开始执行</v-btn>
        </div>
      </v-card>
    </v-dialog>

    <!-- 安装结果弹窗 -->
    <v-dialog v-model="showResultModal" max-width="600" scrollable>
      <v-card class="liquid-glass-card" rounded="xl">
        <v-card-title class="pa-4"><v-icon start>mdi-text-box-outline</v-icon> 安装结果</v-card-title>
        <v-divider />
        <v-card-text class="pa-4">
          <pre class="code-block">{{ resultOutput }}</pre>
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>
