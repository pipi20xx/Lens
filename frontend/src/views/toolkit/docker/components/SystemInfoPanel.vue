<template>
  <div class="system-info-panel">
    <n-grid :cols="2" :x-gap="12" :y-gap="12">
      <n-gi :span="2">
        <n-card title="环境检测" size="small">
          <template #header-extra>
            <div class="header-actions">
              <n-button 
                type="warning" size="tiny" secondary 
                @click="showRepairModal = true" 
                :loading="installing"
              >
                一键修复/安装
              </n-button>
              <n-button size="tiny" quaternary @click="fetchInfo" :loading="loading">
                重新检测
              </n-button>
            </div>
          </template>
          
          <n-skeleton v-if="loading" text :repeat="4" />
          <div v-else class="info-grid">
            <div class="info-item">
              <div class="info-label">Docker 版本</div>
              <div class="info-value">
                <n-tag :type="info.docker === '未安装' ? 'error' : 'success'" size="small">
                  {{ info.docker }}
                </n-tag>
              </div>
            </div>
            <div class="info-item">
              <div class="info-label">Compose 版本</div>
              <div class="info-value">
                <n-tag :type="info.compose === '未安装' ? 'error' : 'success'" size="small">
                  {{ info.compose }}
                </n-tag>
              </div>
            </div>
            <div class="info-item">
              <div class="info-label">服务状态</div>
              <div class="info-value">
                <n-badge 
                  :value="info.status === 'active' ? '运行中' : (info.status === 'inactive' ? '已停止' : '未知')" 
                  :type="info.status === 'active' ? 'success' : 'error'" 
                />
                <n-button-group size="tiny" class="service-actions">
                  <n-button 
                    v-if="info.status !== 'active'" 
                    type="success" ghost 
                    @click="handleServiceAction('start')"
                    :loading="actionLoading === 'start'"
                  >
                    启动
                  </n-button>
                  <n-button 
                    v-if="info.status === 'active'" 
                    type="error" ghost 
                    @click="handleServiceAction('stop')"
                    :loading="actionLoading === 'stop'"
                  >
                    停止
                  </n-button>
                  <n-button 
                    type="warning" ghost 
                    @click="handleServiceAction('restart')"
                    :loading="actionLoading === 'restart'"
                  >
                    重启
                  </n-button>
                </n-button-group>
              </div>
            </div>
            <div class="info-item">
              <div class="info-label">操作系统</div>
              <div class="info-value">
                {{ info.os }}
              </div>
            </div>
          </div>
        </n-card>
      </n-gi>

      <n-gi :span="2" v-if="installing">
        <n-alert title="正在安装环境" type="warning">
          正在远程主机上下载并安装 Docker 及 Docker Compose，这通常需要 1-3 分钟，请耐心等待...
        </n-alert>
      </n-gi>
      
      <n-gi :span="2">
        <n-alert title="环境说明" type="info">
          本页面显示的是远程 Docker 主机的实时环境状态。如果 Docker 或 Compose 未安装，您可以使用“一键修复”功能尝试自动安装。
        </n-alert>
      </n-gi>
    </n-grid>

    <!-- 修复配置弹窗 -->
    <n-modal v-model:show="showRepairModal" preset="card" title="环境修复/安装配置" style="width: 450px">
      <n-form label-placement="left" label-width="100">
        <n-form-item label="使用国内镜像">
          <n-switch v-model:value="repairForm.useMirror" />
          <template #feedback>开启后使用阿里云镜像安装，国内环境建议开启</template>
        </n-form-item>
        <n-form-item label="安装代理">
          <n-input v-model:value="repairForm.proxy" placeholder="例如: http://192.168.1.10:7890" />
          <template #feedback>仅在安装过程中生效。留空则不使用代理。</template>
        </n-form-item>
        <n-alert type="warning" size="small">
          此操作将修改远程主机的系统组件。如果主机已有 Docker 运行，执行此操作可能会尝试更新或重置配置。
        </n-alert>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showRepairModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="handleRepair" :loading="installing">
            开始执行
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- 安装结果弹窗 -->
    <n-modal v-model:show="showResult" preset="dialog" title="安装结果" style="width: 600px">
      <template #default>
        <div style="background: #1e1e1e; color: #adadad; padding: 10px; font-family: monospace; border-radius: 4px; overflow: auto; max-height: 400px; white-space: pre-wrap;">
          {{ resultOutput }}
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, reactive } from 'vue'
import { NGrid, NGi, NCard, NTag, NBadge, NSkeleton, NButton, NAlert, NSpace, NModal, useMessage, useDialog, NForm, NFormItem, NInput, NSwitch, NButtonGroup } from 'naive-ui'
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
    message.error('请求失败')
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
  } catch (e) {
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
    message.error('请求失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    installing.value = false
  }
}

watch(() => props.hostId, fetchInfo, { immediate: true })
</script>

<style scoped>
/* 头部操作区 */
.header-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* 信息卡片网格 */
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.info-item {
  padding: 10px 12px;
  background: var(--info-item-bg, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--info-item-border, rgba(255, 255, 255, 0.08));
  border-radius: 6px;
  transition: border-color 200ms ease, background 200ms ease;
}

.info-item:hover {
  border-color: rgba(64, 128, 240, 0.4);
  background: rgba(64, 128, 240, 0.05);
}

.info-label {
  font-size: 12px;
  opacity: 0.65;
  margin-bottom: 6px;
  font-weight: 500;
}

.info-value {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.service-actions {
  margin-left: 4px;
}

/* ============== 移动端适配 ============== */
@media (max-width: 767px) {
  /* 信息网格变单列 */
  .info-grid {
    grid-template-columns: 1fr;
  }

  /* 头部操作区按钮垂直堆叠 */
  .header-actions {
    flex-direction: column;
    align-items: stretch;
    gap: 4px;
  }
  .header-actions :deep(.n-button) {
    width: 100%;
    margin: 0 !important;
  }
}

/* 超窄屏 (≤380px) 兼容 */
@media (max-width: 380px) {
  .info-item {
    padding: 8px 10px;
  }
  .info-label {
    font-size: 11px;
  }
  /* 超窄屏下服务状态按钮也变宽 */
  .service-actions :deep(.n-button) {
    flex: 1 1 0;
  }
}
</style>