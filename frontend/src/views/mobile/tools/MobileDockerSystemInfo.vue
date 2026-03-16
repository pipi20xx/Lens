<template>
  <div class="mobile-docker-system-info">
    <n-space vertical>
      <n-card title="环境检测" size="small" :bordered="false">
        <template #header-extra>
          <n-space>
            <n-button 
              type="warning" 
              size="tiny" 
              secondary 
              @click="showRepairModal = true" 
              :loading="installing"
            >
              <template #icon><n-icon><RepairIcon /></n-icon></template>
              修复
            </n-button>
            <n-button size="tiny" secondary @click="fetchInfo" :loading="loading">
              <template #icon><n-icon><RefreshIcon /></n-icon></template>
              刷新
            </n-button>
          </n-space>
        </template>

        <n-skeleton v-if="loading" text :repeat="4" />

        <n-space v-else vertical>
          <div class="info-item">
            <div class="info-label">Docker 版本</div>
            <n-tag :type="info.docker === '未安装' ? 'error' : 'success'" size="small">
              {{ info.docker }}
            </n-tag>
          </div>

          <div class="info-item">
            <div class="info-label">Compose 版本</div>
            <n-tag :type="info.compose === '未安装' ? 'error' : 'success'" size="small">
              {{ info.compose }}
            </n-tag>
          </div>

          <div class="info-item">
            <div class="info-label">服务状态</div>
            <n-space align="center">
              <n-badge 
                :value="info.status === 'active' ? '运行中' : (info.status === 'inactive' ? '已停止' : '未知')" 
                :type="info.status === 'active' ? 'success' : 'error'" 
              />
              <n-button-group size="tiny">
                <n-button 
                  v-if="info.status !== 'active'" 
                  type="success" 
                  ghost 
                  @click="handleServiceAction('start')"
                  :loading="actionLoading === 'start'"
                >
                  <template #icon><n-icon><StartIcon /></n-icon></template>
                  启动
                </n-button>
                <n-button 
                  v-if="info.status === 'active'" 
                  type="error" 
                  ghost 
                  @click="handleServiceAction('stop')"
                  :loading="actionLoading === 'stop'"
                >
                  <template #icon><n-icon><StopIcon /></n-icon></template>
                  停止
                </n-button>
                <n-button 
                  type="warning" 
                  ghost 
                  @click="handleServiceAction('restart')"
                  :loading="actionLoading === 'restart'"
                >
                  <template #icon><n-icon><RecreateIcon /></n-icon></template>
                  重启
                </n-button>
              </n-button-group>
            </n-space>
          </div>

          <div class="info-item">
            <div class="info-label">操作系统</div>
            <n-text depth="3" style="font-size: 12px">{{ info.os }}</n-text>
          </div>
        </n-space>
      </n-card>

      <n-alert type="info" size="small">
        本页面显示的是远程 Docker 主机的实时环境状态。如果 Docker 或 Compose 未安装，您可以使用"修复"功能尝试自动安装。
      </n-alert>
    </n-space>

    <n-modal v-model:show="showRepairModal" preset="card" title="环境修复/安装配置" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="使用国内镜像">
          <n-switch v-model:value="repairForm.useMirror" />
        </n-form-item>
        <n-form-item label="安装代理">
          <n-input v-model:value="repairForm.proxy" placeholder="例如: http://192.168.1.10:7890" />
        </n-form-item>
        <n-alert type="warning" size="small">
          此操作将修改远程主机的系统组件。如果主机已有 Docker 运行，执行此操作可能会尝试更新或重置配置。
        </n-alert>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showRepairModal = false">取消</n-button>
          <n-button type="primary" @click="handleRepair" :loading="installing">开始执行</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showResult" preset="dialog" title="安装结果" style="width: 90vw; max-width: 600px">
      <div class="result-container">
        {{ resultOutput }}
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { 
  NSpace, NCard, NTag, NBadge, NSkeleton, NButton, NIcon, 
  NAlert, NModal, useMessage, NForm, NFormItem, NInput, NSwitch, NButtonGroup, NText 
} from 'naive-ui'
import { 
  RefreshOutlined as RefreshIcon,
  BuildOutlined as RepairIcon,
  PlayArrowOutlined as StartIcon,
  StopOutlined as StopIcon,
  AutorenewOutlined as RecreateIcon
} from '@vicons/material'
import axios from 'axios'

const props = defineProps<{ hostId: string | null }>()
const message = useMessage()

const loading = ref(false)
const installing = ref(false)
const actionLoading = ref<string | null>(null)
const showRepairModal = ref(false)
const showResult = ref(false)
const resultOutput = ref('')

const repairForm = reactive({
  useMirror: true,
  proxy: ''
})

const info = ref({
  docker: '',
  compose: '',
  os: '',
  status: ''
})

const handleServiceAction = async (action: string) => {
  if (!props.hostId) return
  actionLoading.value = action
  try {
    const res = await axios.post(`/api/docker/${props.hostId}/service-action`, { action })
    if (res.data.success) {
      message.success(`服务已尝试${action === 'start' ? '启动' : action === 'stop' ? '停止' : '重启'}`)
    } else {
      message.error('操作失败: ' + res.data.stderr)
    }
    setTimeout(fetchInfo, 1000)
  } catch (e: any) {
    message.error('请求失败: ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    actionLoading.value = null
  }
}

const fetchInfo = async () => {
  if (!props.hostId) return
  loading.value = true
  try {
    const res = await axios.get(`/api/docker/${props.hostId}/system-info`)
    info.value = res.data
  } catch (e: any) {
    message.error('获取系统信息失败: ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    loading.value = false
  }
}

const handleRepair = async () => {
  showRepairModal.value = false
  installing.value = true
  try {
    const res = await axios.post(`/api/docker/${props.hostId}/install-env`, { 
      use_mirror: repairForm.useMirror,
      proxy: repairForm.proxy
    })
    resultOutput.value = res.data.stdout || res.data.stderr || '安装已完成。'
    showResult.value = true
    if (res.data.success) message.success('环境任务执行完毕')
    else message.error('安装过程中出现错误')
    fetchInfo()
  } catch (e: any) {
    message.error('请求失败: ' + (e.response?.data?.detail || '未知错误'))
  } finally {
    installing.value = false
  }
}

watch(() => props.hostId, fetchInfo, { immediate: true })
</script>

<style scoped>
.mobile-docker-system-info {
  padding: 12px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 14px;
  color: var(--text-color);
  font-weight: 500;
}

.result-container {
  background: #1e1e1e;
  color: #adadad;
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  border-radius: 4px;
  overflow: auto;
  max-height: 400px;
  white-space: pre-wrap;
}
</style>
