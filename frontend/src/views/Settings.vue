<template>
  <div class="toolkit-container">
    <n-space vertical size="large">
      <div class="page-header">
        <n-h2 prefix="bar" align-text><n-text type="primary">系统集成配置</n-text></n-h2>
        <n-text >统一管理您的 Emby 核心凭据与第三方扩展 API 密钥。</n-text>
      </div>

      <n-grid :x-gap="12" :y-gap="12" :cols="24" item-responsive responsive="screen">
        <!-- 左侧：核心凭据管理 -->
        <n-gi span="24 m:16">
          <n-space vertical size="large">
            <!-- 1. Emby 服务端管理 -->
            <n-card title="Emby 服务端管理" size="small" segmented>
              <template #header-extra>
                <n-button type="primary" size="small" @click="openAddModal">
                  添加服务器
                </n-button>
              </template>

              <n-empty
                v-if="servers.length === 0"
                description="暂无服务器配置"
                style="padding: 30px"
              />
              <div v-else class="server-grid">
                <div
                  v-for="s in servers"
                  :key="s.id"
                  class="server-card"
                  :class="{ 'active': s.id === activeServerId }"
                >
                  <div class="server-card-header">
                    <div class="server-name" :title="s.name">
                      {{ s.name }}
                    </div>
                    <n-tag
                      v-if="s.id === activeServerId"
                      type="success"
                      size="small"
                      round
                      quaternary
                    >
                      当前激活
                    </n-tag>
                    <n-tag v-else size="small" round quaternary>闲置</n-tag>
                  </div>

                  <div class="server-url">
                    <n-text depth="3" class="url-label">服务器地址</n-text>
                    <n-text class="url-value" :title="s.url">{{ s.url }}</n-text>
                  </div>

                  <div class="server-actions">
                    <n-button size="tiny" secondary @click="openEditModal(s)">
                      配置
                    </n-button>
                    <n-button
                      v-if="s.id !== activeServerId"
                      size="tiny"
                      type="primary"
                      secondary
                      @click="handleActivate(s.id)"
                    >
                      激活
                    </n-button>
                    <n-popconfirm
                      @positive-click="handleDelete(s.id)"
                      positive-text="确认"
                      negative-text="取消"
                    >
                      <template #trigger>
                        <n-button size="tiny" type="error" quaternary>
                          删除
                        </n-button>
                      </template>
                      确定删除？
                    </n-popconfirm>
                  </div>
                </div>
              </div>
            </n-card>

            <!-- 2. 全局 API 服务集成 -->
            <n-card title="第三方 API 扩展集成" size="small" segmented>
              <n-form label-placement="left" label-width="140" size="small">
                <n-form-item label="TMDB API Key">
                  <n-input-group>
                    <n-input v-model:value="globalConfig.tmdb_api_key" type="password" show-password-on="click" placeholder="The Movie Database V3 Key" />
                    <n-button secondary @click="handleCopy(globalConfig.tmdb_api_key)">
                      复制
                    </n-button>
                  </n-input-group>
                </n-form-item>
                <n-form-item label="Bangumi API Token">
                  <n-input-group>
                    <n-input v-model:value="globalConfig.bangumi_api_token" type="password" show-password-on="click" placeholder="Bangumi Access Token" />
                    <n-button secondary @click="handleCopy(globalConfig.bangumi_api_token)">
                      复制
                    </n-button>
                  </n-input-group>
                </n-form-item>
              </n-form>
              <template #action>
                <n-space justify="end">
                  <n-button type="primary" size="small" @click="handleSaveGlobal" :loading="savingGlobal">
                    保存 API 配置
                  </n-button>
                </n-space>
              </template>
            </n-card>

            <!-- 3. HTTP 代理配置 -->
            <n-card title="网络代理设置" size="small" segmented>
              <n-form label-placement="top" size="small">
                <n-grid :cols="2" :x-gap="24">
                  <n-form-item-gi label="启用全局代理">
                    <n-switch v-model:value="globalConfig.proxy.enabled" />
                  </n-form-item-gi>
                  <n-form-item-gi label="排除 Emby 服务器">
                    <n-switch v-model:value="globalConfig.proxy.exclude_emby" />
                  </n-form-item-gi>
                  <n-form-item-gi span="2" label="代理服务器地址 (Proxy URL)">
                    <n-input v-model:value="globalConfig.proxy.url" placeholder="http://127.0.0.1:7890" :disabled="!globalConfig.proxy.enabled" />
                  </n-form-item-gi>
                </n-grid>
              </n-form>
              <template #action>
                <n-space justify="end">
                  <n-button type="primary" size="small" @click="handleSaveGlobal" :loading="savingGlobal">
                    保存代理配置
                  </n-button>
                </n-space>
              </template>
            </n-card>

            <!-- 4. 会话管理配置 -->
            <n-card title="会话管理" size="small" segmented>
              <n-form label-placement="left" label-width="140" size="small">
                <n-form-item label="会话永不过期">
                  <n-space vertical>
                    <n-switch v-model:value="globalConfig.session_never_expire" />
                    <n-text  style="font-size: 12px">
                      开启后，登录会话将不会自动过期，直到用户主动登出或被管理员踢出。
                      <br>关闭后，会话将在 24 小时后自动过期。
                    </n-text>
                  </n-space>
                </n-form-item>
              </n-form>
              <template #action>
                <n-space justify="end">
                  <n-button type="primary" size="small" @click="handleSaveGlobal" :loading="savingGlobal">
                    保存会话配置
                  </n-button>
                </n-space>
              </template>
            </n-card>
          </n-space>
        </n-gi>

        <!-- 右侧：维护与提示 -->
        <n-gi span="24 m:8">
          <n-space vertical size="large">
            <!-- 5. 配置备份与恢复 -->
            <n-card title="数据备份与迁移" size="small" segmented>
              <n-text  style="font-size: 13px; display: block; margin-bottom: 16px;">
                您可以导出当前的全局配置文件 (config.json) 进行备份，或在迁移环境时导入旧配置。
              </n-text>
              <n-space vertical>
                <n-button block secondary @click="handleExportConfig">
                  导出 config.json
                </n-button>
                <n-button block type="primary" ghost @click="triggerImportConfig">
                  导入备份文件
                </n-button>
                <input 
                  type="file" 
                  ref="fileInputRef" 
                  style="display: none" 
                  accept=".json" 
                  @change="handleImportConfig" 
                />
              </n-space>
            </n-card>

            <n-card title="配置贴士" size="small" segmented>
              <n-text  style="font-size: 13px; line-height: 1.8">
                <div style="margin-bottom: 8px">• <b>TMDB</b>：元数据抓取的核心，建议配置 V3 Key。</div>
                <div style="margin-bottom: 8px">• <b>代理</b>：如果您无法连接外网，请在此配置 HTTP/SOCKS 代理。</div>
                <div>• <b>多服务器</b>：Lens 支持多实例管理，您可以随时切换当前激活的服务器。</div>
              </n-text>
            </n-card>
          </n-space>
        </n-gi>
      </n-grid>
    </n-space>

    <!-- 抽离出的服务器配置弹窗 -->
    <EmbyServerModal 
      v-model:show="showServerModal" 
      :server-data="editingServer" 
      @on-success="fetchCurrent"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { 
  useMessage, NSpace, NH2, NText, NCard, NTag, 
  NForm, NGrid, NFormItemGi, NInput, NSwitch, NCode, 
  NButton, NFormItem, NEmpty, NPopconfirm, NDivider
} from 'naive-ui'
import { servers, activeServerId } from '../store/serverStore'
import { copyElementContent, copyText } from '../utils/clipboard'
import EmbyServerModal from '../components/EmbyServerModal.vue'

// 导入提取的逻辑
import { useSettings } from '../hooks/useSettings'

const message = useMessage()
const { 
  globalConfig, savingGlobal, showServerModal, editingServer, fileInputRef,
  handleExportConfig, triggerImportConfig, handleImportConfig, fetchCurrent, 
  handleActivate, handleDelete, handleSaveGlobal
} = useSettings()

onMounted(fetchCurrent)

const openAddModal = () => {
  editingServer.value = null
  showServerModal.value = true
}

const openEditModal = (s: any) => {
  editingServer.value = s
  showServerModal.value = true
}

const handleCopy = async (text: string) => {
  if (await copyText(text)) {
    message.success('已成功复制到剪贴板')
  } else {
    message.error('复制失败')
  }
}
</script>

<style scoped>
/* Emby 服务端卡片列表 */
.server-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.server-card {
  display: flex;
  flex-direction: column;
  padding: 12px 14px;
  background: var(--info-item-bg, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--info-item-border, rgba(255, 255, 255, 0.08));
  border-radius: 6px;
  transition: border-color 200ms ease, background 200ms ease;
}

.server-card.active {
  border-color: rgba(64, 128, 240, 0.4);
  background: rgba(64, 128, 240, 0.06);
}

.server-card:hover {
  border-color: rgba(64, 128, 240, 0.3);
}

.server-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.server-name {
  font-size: 14px;
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.server-url {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 12px;
  min-width: 0;
}

.server-url .url-label {
  font-size: 12px;
}

.server-url .url-value {
  word-break: break-all;
  font-size: 13px;
}

.server-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: auto;
}

/* ============== 移动端适配 ============== */
@media (max-width: 767px) {
  /* 卡片列表变为单列 */
  .server-grid {
    grid-template-columns: 1fr;
  }
}

/* 超窄屏 (≤380px) 兼容 */
@media (max-width: 380px) {
  .server-card {
    padding: 10px 12px;
  }

  /* 操作按钮撑满宽度，更易点击 */
  .server-actions {
    flex-wrap: nowrap;
  }
  .server-actions :deep(.n-button) {
    flex: 1 1 0;
    margin: 0 !important;
  }
}
</style>
