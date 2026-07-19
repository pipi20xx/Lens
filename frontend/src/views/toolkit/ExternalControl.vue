<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text>
          <n-text type="primary">外部控制体系</n-text>
        </n-h2>
        <n-text depth="3">管理 API 认证、安全审计及自动化对接配置，为外部脚本和第三方应用提供能力支撑。</n-text>
      </div>

      <n-tabs v-model:value="activeTab" type="line" animated>
        <!-- 1. API 密钥 -->
        <n-tab-pane name="api_key" tab="API 密钥">
          <div style="padding-top: 16px;">
            <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
              <n-gi span="24 m:16">
                <n-card title="令牌管理" size="small" segmented>
                  <n-space vertical size="large">
                    <n-form-item label="当前生效的 API Token">
                      <n-input-group>
                        <n-input 
                          v-model:value="config.api_token" 
                          :type="showFullToken ? 'text' : 'password'"
                          show-password-on="click" 
                          placeholder="尚未设置 Token"
                          readonly
                          @click="showFullToken = !showFullToken"
                          style="cursor: pointer"
                        />
                        <n-button type="primary" secondary @click="copyToken" :disabled="!config.api_token">
                          复制数据
                        </n-button>
                        <n-button secondary @click="generateNewToken">
                          重新生成
                        </n-button>
                      </n-input-group>
                    </n-form-item>
                    <n-text depth="3">
                      注意：更改 Token 后，所有已对接的外部应用（如自动化脚本、Webhook 触发器）需要同步更新。
                    </n-text>
                  </n-space>
                </n-card>
              </n-gi>
              <n-gi span="24 m:8">
                <n-card title="安全说明" size="small" segmented>
                  <n-alert title="Token 安全性" type="info" :bordered="false">
                    API Token 用于外部系统通过 /api 接口与本系统交互。
                  </n-alert>
                  <n-text depth="3" style="font-size: 13px; margin-top: 12px; display: block;">
                    1. <b>权限等同管理员</b>：Token 拥有系统所有接口的操作权限。<br/>
                    2. <b>加密存储</b>：Token 在数据库中加密存储，无法反向解密。<br/>
                    3. <b>泄露处理</b>：如果怀疑 Token 泄露，请立即点击“重新生成”。
                  </n-text>
                </n-card>
              </n-gi>
            </n-grid>
          </div>
        </n-tab-pane>

        <!-- 2. 安全设置 -->
        <n-tab-pane name="settings" tab="安全设置">
          <div style="padding-top: 16px;">
            <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
              <n-gi span="24 m:16">
                <n-card title="审计策略" size="small" segmented style="height: 100%">
                  <n-space vertical>
                    <div class="setting-item">
                      <n-thing title="开启全局审计" description="记录所有 API 请求的方法、路径及状态码" />
                      <n-switch v-model:value="config.audit_enabled" @update:value="saveSettings" />
                    </div>
                    <n-divider />
                    <div class="setting-item">
                      <n-thing title="Payload 捕获" description="自动脱敏并存储请求 Body 内容" />
                      <n-switch :value="config.audit_enabled" disabled />
                    </div>
                  </n-space>
                </n-card>
              </n-gi>
              <n-gi span="24 m:8">
                <n-card title="设置说明" size="small" segmented>
                  <n-text depth="3" style="font-size: 13px">
                    <b>审计日志：</b>开启审计会产生少量的数据库写入开销，但对于回溯系统操作和定位自动化对接问题非常有帮助。
                  </n-text>
                </n-card>
              </n-gi>
            </n-grid>
          </div>
        </n-tab-pane>

        <!-- 3. 访问日志 -->
        <n-tab-pane name="logs" tab="访问日志">
          <div style="padding-top: 16px;">
            <n-card title="审计日志记录" size="small" segmented>
              <n-data-table
                remote
                ref="table"
                :columns="columns"
                :data="auditLogs"
                :loading="loadingLogs"
                :pagination="pagination"
                :row-key="row => row.id"
                @update:page="handlePageChange"
                @update:page-size="handlePageSizeChange"
                size="small"
                :single-line="false"
              />
            </n-card>
          </div>
        </n-tab-pane>

        <!-- 4. API 文档 -->
        <n-tab-pane name="docs" tab="API 文档">
          <div class="docs-wrapper">
            <iframe
              ref="docsIframe"
              :key="`${currentMode}-${config.api_token}`"
              :src="`/api/system/docs?theme=${currentMode}&token=${config.api_token}`"
              frameborder="0"
              class="docs-iframe"
              @load="initIframeMonitor"
              scrolling="no"
            ></iframe>
          </div>
        </n-tab-pane>
      </n-tabs>
    </n-space>

    <!-- Log Detail Modal -->
    <n-modal v-model:show="showLogDetail" preset="card" title="请求详情 (Payload)" style="width: 800px">
      <div class="detail-wrapper">
        <n-code :code="currentPayload" language="json" word-wrap />
      </div>
      <template #footer>
        <n-space justify="end">
          <n-button type="primary" @click="showLogDetail = false">
            关闭详情
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h, watch, nextTick } from 'vue'
import { 
  useMessage, NSpace, NH2, NText, NTabs, NTabPane, NCard, NAlert,
  NFormItem, NInput, NInputGroup, NButton, NGrid, NGi, NThing, NSwitch, NDivider,
  NDataTable, NTag, NCode, NModal, NIcon
} from 'naive-ui'
// 导入提取的逻辑
import { useExternalControl } from './externalControl/hooks/useExternalControl'
import { useTheme } from '@/hooks/useTheme'

const message = useMessage()
const { currentMode } = useTheme()

const {
  config, auditLogs, loadingLogs, pagination, showLogDetail, currentPayload, activeTab,
  loadConfig, saveSettings, generateNewToken, copyToken, fetchLogs, handlePageChange, handlePageSizeChange
} = useExternalControl()

const renderIcon = (icon: any) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const docsIframe = ref<HTMLIFrameElement | null>(null)

// 核心：高度监视器
const initIframeMonitor = () => {
  const iframe = docsIframe.value
  if (!iframe || !iframe.contentWindow) return
  const updateHeight = () => {
    try {
      const doc = iframe.contentWindow?.document
      if (doc) {
        const height = Math.max(doc.body.scrollHeight, doc.documentElement.scrollHeight)
        iframe.style.height = (height + 50) + 'px'
      }
    } catch (e) {
      iframe.style.height = '2000px'
    }
  }
  updateHeight()
  try {
    const observer = new MutationObserver(updateHeight)
    observer.observe(iframe.contentWindow.document.body, { attributes: true, childList: true, subtree: true })
  } catch (e) {
    setInterval(updateHeight, 1000)
  }
}

watch(activeTab, (val) => {
  if (val === 'docs') { nextTick(() => initIframeMonitor()) }
})

const columns = [
  { title: '时间', key: 'timestamp', width: 180, render: (row: any) => new Date(row.timestamp).toLocaleString() },
  { title: '方法', key: 'method', width: 80, render: (row: any) => h(NTag, { type: row.method === 'GET' ? 'success' : 'info', size: 'small', quaternary: true }, { default: () => row.method }) },
  { title: '路径', key: 'path', ellipsis: true },
  { title: '状态', key: 'status_code', width: 80, render: (row: any) => h(NTag, { type: row.status_code < 400 ? 'success' : 'error', size: 'small', quaternary: true }, { default: () => row.status_code }) },
  { title: '来源 IP', key: 'client_ip', width: 130 },
  { title: '耗时', key: 'process_time', width: 100, render: (row: any) => `${row.process_time.toFixed(1)}ms` },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row: any) => {
      return h(NButton, {
        size: 'tiny', secondary: true, disabled: !row.payload,
        onClick: () => {
          try { currentPayload.value = JSON.stringify(JSON.parse(row.payload), null, 2) } 
          catch { currentPayload.value = row.payload || '' }
          showLogDetail.value = true
        }
      }, { default: () => '查看详情' })
    }
  }
]

// 注入 pagination 的前缀渲染逻辑
pagination.prefix = (info: any) => h('span', { style: 'font-size: 12px; opacity: 0.6;' }, `共 ${info.itemCount} 条记录`)

onMounted(() => { loadConfig(); fetchLogs() })
</script>

<style scoped>
.setting-item { display: flex; justify-content: space-between; align-items: center; }

.docs-wrapper {
  margin-top: 16px;
  width: 100%;
}

.docs-iframe {
  width: 100%;
  min-height: 800px;
  border: none;
  display: block;
  overflow: hidden;
}

.detail-wrapper {
  background-color: rgba(0, 0, 0, 0.3);
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}

/* 彻底移除 Naive UI 内部的高度和滚动封印 */
:deep(.n-tabs-content) { height: auto !important; }
:deep(.n-tab-pane) { height: auto !important; overflow: visible !important; }
</style>