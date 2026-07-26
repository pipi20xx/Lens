<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { serverApi } from '@/api/server'
import { configApi } from '@/api/config'
import { systemApi } from '@/api/system'
import { useNotification, useClipboard } from '@/composables'
import GlassDialog from '@/components/common/GlassDialog.vue'
import SecretField from '@/components/common/SecretField.vue'

const { success, error: showError } = useNotification()
const { copy: copyToClipboard } = useClipboard()
const activeTab = ref('general')
const loading = ref(true)
const savingGlobal = ref(false)
const savingSystem = ref(false)

// ========== 服务器列表 (来自 /api/server/list) ==========
const serverList = ref<any[]>([])
const activeServerId = ref('')

// ========== 全局配置 (来自 /api/server/current) ==========
// 旧前端: serverApi.getCurrent() 返回的是 config.json 全部内容 + 激活服务器合并
const globalConfig = ref<any>({
  tmdb_api_key: '',
  bangumi_api_token: '',
  proxy: { enabled: false, url: '', exclude_emby: true },
  session_never_expire: false,
})

// ========== 数据库系统配置 (来自 /api/system/config) ==========
// api_token, auth_enabled, audit_enabled 等存数据库
const systemConfig = ref<any>({
  api_token: '',
  auth_enabled: true,
  audit_enabled: false,
})

// ========== 服务器编辑 ==========
const showAddServerDialog = ref(false)
const serverForm = ref({ id: '', name: '', url: '', api_key: '', username: '', password: '' })
const editingServerId = ref<string | null>(null)

// ========== 版本 ==========
const versionInfo = ref<any>(null)

/**
 * 加载所有配置
 * 对齐旧前端逻辑:
 * 1. serverApi.getServers() -> /api/server/list -> 获取服务器列表 + active_id
 * 2. serverApi.getCurrent() -> /api/server/current -> 获取全局配置(tmdb_api_key/proxy等)
 * 3. configApi.getSystemConfig() -> /api/system/config -> 获取数据库配置(api_token/auth_enabled等)
 */
async function loadAll() {
  loading.value = true
  try {
    const [serverRes, currentRes, sysRes] = await Promise.all([
      serverApi.getServers(),      // /api/server/list
      serverApi.getCurrent(),      // /api/server/current
      configApi.getSystemConfig(), // /api/system/config
    ])

    // 1. 服务器列表
    const sData: any = serverRes || {}
    serverList.value = sData.servers || sData.emby_servers || []
    activeServerId.value = sData.active_id || ''

    // 2. 全局配置 (config.json 内容)
    const cfg: any = currentRes || {}
    globalConfig.value = {
      tmdb_api_key: cfg.tmdb_api_key || '',
      bangumi_api_token: cfg.bangumi_api_token || '',
      proxy: {
        enabled: cfg.proxy?.enabled ?? false,
        url: cfg.proxy?.url || '',
        exclude_emby: cfg.proxy?.exclude_emby ?? true,
      },
      session_never_expire: !!cfg.session_never_expire,
    }

    // 3. 数据库系统配置
    const sc: any = sysRes || {}
    systemConfig.value = {
      api_token: sc.api_token || '',
      auth_enabled: sc.auth_enabled !== false,
      audit_enabled: !!sc.audit_enabled,
    }
  } catch (e: any) {
    console.error('加载配置失败:', e)
    showError('加载配置失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// ========== 服务器管理 ==========
function openAddServer() {
  editingServerId.value = null
  serverForm.value = { id: '', name: '', url: '', api_key: '', username: '', password: '' }
  showAddServerDialog.value = true
}

function openEditServer(server: any) {
  editingServerId.value = server.id
  serverForm.value = { ...server }
  showAddServerDialog.value = true
}

async function saveServer() {
  try {
    // /api/server/save - 后端会自动处理新增/更新
    await serverApi.saveGlobal(serverForm.value)
    success('服务器配置已保存')
    showAddServerDialog.value = false
    loadAll()
  } catch (err: any) {
    showError(err.message || '保存失败')
  }
}

async function deleteServer(id: string) {
  try {
    await serverApi.deleteServer(id)
    success('服务器已删除')
    loadAll()
  } catch { showError('删除失败') }
}

async function activateServer(id: string) {
  try {
    await serverApi.activateServer(id)
    success('已切换激活服务器')
    loadAll()
  } catch { showError('切换失败') }
}

async function testConnection() {
  try {
    const res = await serverApi.testConnection({
      url: serverForm.value.url,
      api_key: serverForm.value.api_key,
    })
    if (res?.message) success(res.message)
    else success('连接成功')
  } catch (err: any) {
    showError(err.message || '连接失败')
  }
}

// ========== 全局配置保存 (config.json -> /api/server/save) ==========
async function handleSaveGlobal() {
  savingGlobal.value = true
  try {
    await serverApi.saveGlobal(globalConfig.value)
    success('全局配置已保存')
    await loadAll()
  } catch { showError('保存失败') }
  finally { savingGlobal.value = false }
}

// ========== 数据库系统配置保存 (/api/system/config) ==========
async function handleSaveSystem() {
  savingSystem.value = true
  try {
    const configs = [
      { key: 'api_token', value: systemConfig.value.api_token, description: 'API Token' },
      { key: 'auth_enabled', value: systemConfig.value.auth_enabled, description: '启用登录认证' },
      { key: 'audit_enabled', value: systemConfig.value.audit_enabled, description: '启用审计日志' },
    ]
    await configApi.saveSystemConfig(configs)
    success('系统配置已保存')
    await loadAll()
  } catch { showError('保存失败') }
  finally { savingSystem.value = false }
}

// ========== API Token ==========
async function generateToken() {
  try {
    const res = await systemApi.generateToken()
    systemConfig.value.api_token = res.token
    // 保存到数据库
    await configApi.saveSystemConfig([
      { key: 'api_token', value: res.token, description: 'API Token' },
    ])
    success('Token 已生成并保存')
  } catch { showError('生成 Token 失败') }
}

// ========== 配置导入导出 ==========
function exportConfig() {
  window.open('/api/system/config/export', '_blank')
}

async function importConfig(event: Event) {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  const formData = new FormData()
  formData.append('file', input.files[0])
  try {
    await configApi.importConfig(formData)
    success('配置已导入，页面将刷新以应用更改')
    setTimeout(() => location.reload(), 1500)
  } catch (err: any) {
    showError(err.message || '导入失败')
  }
}

// ========== 版本 ==========
async function checkVersion() {
  try {
    versionInfo.value = await systemApi.getVersion()
  } catch { /* ignore */ }
}

async function upgradeSystem() {
  try {
    const res = await systemApi.upgrade()
    success(res?.message || '升级任务已启动')
  } catch (err: any) {
    showError(err.message || '升级失败')
  }
}

function copyText(text: string) {
  copyToClipboard(text)
}

onMounted(loadAll)
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 font-weight-bold mb-2">
      <v-icon start>mdi-cog-outline</v-icon>
      系统集成配置
    </h1>
    <p class="text-body-2 text-medium-emphasis mb-6">统一管理您的 Emby 核心凭据与第三方扩展 API 密钥。</p>

    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <v-row>
      <!-- 左侧：核心配置 -->
      <v-col cols="12" md="8">
        <v-tabs v-model="activeTab" class="mb-4">
          <v-tab value="general"><v-icon start>mdi-server-outline</v-icon> Emby 服务端管理</v-tab>
          <v-tab value="api"><v-icon start>mdi-key-outline</v-icon> 第三方 API 集成</v-tab>
          <v-tab value="proxy"><v-icon start>mdi-vpn</v-icon> 网络代理设置</v-tab>
          <v-tab value="session"><v-icon start>mdi-shield-lock-outline</v-icon> 会话与安全</v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
          <!-- ====== Emby 服务端管理 ====== -->
          <v-window-item value="general">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="d-flex align-center pa-4">
                <v-icon start>mdi-server-outline</v-icon>
                Emby 服务端管理
                <v-spacer />
                <v-btn prepend-icon="mdi-plus" variant="tonal" color="primary" size="small" @click="openAddServer">添加服务器</v-btn>
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4">
                <div v-if="!serverList.length" class="text-center py-8 text-medium-emphasis">
                  <v-icon size="48" color="grey" class="mb-2">mdi-server-off</v-icon>
                  <div>暂无服务器配置</div>
                </div>
                <v-row v-else>
                  <v-col v-for="server in serverList" :key="server.id" cols="12" sm="6">
                    <v-card variant="outlined" rounded="lg" class="pa-3"
                      :style="server.id === activeServerId ? 'border-color:rgb(var(--v-theme-primary));background:rgba(var(--v-theme-primary),0.04)' : ''">
                      <div class="d-flex align-center mb-2">
                        <span class="text-subtitle-2 font-weight-bold text-truncate">{{ server.name || server.url }}</span>
                        <v-spacer />
                        <v-chip v-if="server.id === activeServerId" size="x-small" color="success" variant="tonal">当前激活</v-chip>
                        <v-chip v-else size="x-small" variant="tonal">闲置</v-chip>
                      </div>
                      <div class="text-caption text-medium-emphasis font-mono mb-3">{{ server.url }}</div>
                      <div class="d-flex flex-wrap ga-2">
                        <v-btn size="x-small" variant="tonal" color="secondary" prepend-icon="mdi-cog-outline" @click="openEditServer(server)">配置</v-btn>
                        <v-btn v-if="server.id !== activeServerId" size="x-small" color="primary" variant="tonal" prepend-icon="mdi-check-circle-outline" @click="activateServer(server.id)">激活</v-btn>
                        <v-btn size="x-small" color="error" variant="tonal" prepend-icon="mdi-delete-outline" @click="deleteServer(server.id)">删除</v-btn>
                      </div>
                    </v-card>
                  </v-col>
                </v-row>
              </v-card-text>
            </v-card>
          </v-window-item>

          <!-- ====== 第三方 API 集成 ====== -->
          <v-window-item value="api">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="pa-4">
                <v-icon start>mdi-key-outline</v-icon>
                第三方 API 扩展集成
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4">
                <SecretField v-model="globalConfig.tmdb_api_key" label="TMDB API Key"
                  class="mb-3"
                  hint="The Movie Database V3 Key" persistent-hint />
                <SecretField v-model="globalConfig.bangumi_api_token" label="Bangumi API Token"
                  class="mb-3"
                  hint="Bangumi Access Token" persistent-hint />
              </v-card-text>
              <v-divider />
              <div class="d-flex justify-end pa-4">
                <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" :loading="savingGlobal" @click="handleSaveGlobal">保存 API 配置</v-btn>
              </div>
            </v-card>
          </v-window-item>

          <!-- ====== 网络代理设置 ====== -->
          <v-window-item value="proxy">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="pa-4">
                <v-icon start>mdi-vpn</v-icon>
                网络代理设置
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4">
                <v-row class="mb-3">
                  <v-col cols="6">
                    <v-switch v-model="globalConfig.proxy.enabled" label="启用全局代理" density="compact" color="primary" />
                  </v-col>
                  <v-col cols="6">
                    <v-switch v-model="globalConfig.proxy.exclude_emby" label="排除 Emby 服务器" density="compact" color="primary" />
                  </v-col>
                </v-row>
                <v-text-field v-model="globalConfig.proxy.url" label="代理服务器地址 (Proxy URL)" variant="outlined" density="compact"
                  placeholder="http://127.0.0.1:7890" :disabled="!globalConfig.proxy.enabled" />
              </v-card-text>
              <v-divider />
              <div class="d-flex justify-end pa-4">
                <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" :loading="savingGlobal" @click="handleSaveGlobal">保存代理配置</v-btn>
              </div>
            </v-card>
          </v-window-item>

          <!-- ====== 会话与安全 ====== -->
          <v-window-item value="session">
            <v-card class="liquid-glass-card" rounded="xl">
              <v-card-title class="pa-4">
                <v-icon start>mdi-shield-lock-outline</v-icon>
                会话管理
              </v-card-title>
              <v-divider />
              <v-card-text class="pa-4">
                <v-switch v-model="globalConfig.session_never_expire" label="会话永不过期" density="compact" color="primary" class="mb-2" />
                <p class="text-caption text-medium-emphasis">
                  开启后，登录会话将不会自动过期，直到用户主动登出或被管理员踢出。<br />
                  关闭后，会话将在 24 小时后自动过期。
                </p>
                <v-divider class="my-4" />
                <v-row>
                  <v-col cols="6">
                    <v-switch v-model="systemConfig.auth_enabled" label="启用登录认证" density="compact" color="primary"
                      hint="关闭后任何人都可以访问系统" persistent-hint />
                  </v-col>
                  <v-col cols="6">
                    <v-switch v-model="systemConfig.audit_enabled" label="启用审计日志" density="compact" color="primary" />
                  </v-col>
                </v-row>
              </v-card-text>
              <v-divider />
              <div class="d-flex justify-end pa-4">
                <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" :loading="savingSystem" @click="handleSaveSystem">保存会话与安全配置</v-btn>
              </div>
            </v-card>
          </v-window-item>
        </v-window>
      </v-col>

      <!-- 右侧：维护与提示 -->
      <v-col cols="12" md="4">
        <!-- 数据备份与迁移 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start size="20">mdi-database-export-outline</v-icon>
            数据备份与迁移
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <p class="text-body-2 text-medium-emphasis mb-4">您可以导出当前的全局配置文件 (config.json) 进行备份，或在迁移环境时导入旧配置。</p>
            <div class="d-flex flex-column ga-2">
              <v-btn block variant="tonal" color="info" @click="exportConfig" prepend-icon="mdi-download">导出 config.json</v-btn>
              <v-btn block color="primary" variant="tonal" @click="($refs.fileInput as any).click()" prepend-icon="mdi-upload">导入备份文件</v-btn>
              <input ref="fileInput" type="file" accept=".json" style="display:none" @change="importConfig" />
            </div>
          </v-card-text>
        </v-card>

        <!-- 版本与升级 -->
        <v-card class="liquid-glass-card mb-4" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start size="20">mdi-update</v-icon>
            版本与升级
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4">
            <v-btn block variant="tonal" color="info" @click="checkVersion" prepend-icon="mdi-refresh" class="mb-3">检查更新</v-btn>
            <template v-if="versionInfo">
              <div class="text-body-2 mb-1"><span class="text-medium-emphasis">当前版本：</span><span class="font-weight-bold">{{ versionInfo.current }}</span></div>
              <div class="text-body-2 mb-2"><span class="text-medium-emphasis">最新版本：</span><span class="font-weight-bold">{{ versionInfo.latest }}</span></div>
              <v-alert v-if="versionInfo.has_update" variant="tonal" type="info" density="compact" class="mb-3" rounded="lg">发现新版本！</v-alert>
              <v-btn v-if="versionInfo.has_update" block color="primary" variant="flat" @click="upgradeSystem" prepend-icon="mdi-arrow-up-bold-circle-outline">一键升级</v-btn>
            </template>
            <div v-else class="text-caption text-medium-emphasis">点击"检查更新"获取版本信息</div>
          </v-card-text>
        </v-card>

        <!-- 配置贴士 -->
        <v-card class="liquid-glass-card" rounded="xl">
          <v-card-title class="pa-4">
            <v-icon start size="20">mdi-lightbulb-outline</v-icon>
            配置贴士
          </v-card-title>
          <v-divider />
          <v-card-text class="pa-4 text-body-2" style="line-height:1.8">
            <div class="mb-2">• <b>TMDB</b>：元数据抓取的核心，建议配置 V3 Key。</div>
            <div class="mb-2">• <b>代理</b>：如果您无法连接外网，请在此配置 HTTP/SOCKS 代理。</div>
            <div>• <b>多服务器</b>：Lens 支持多实例管理，您可以随时切换当前激活的服务器。</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 服务器编辑对话框 -->
    <GlassDialog v-model="showAddServerDialog" :max-width="520" icon="mdi-server" :title="editingServerId ? '编辑服务器' : '添加服务器'">
  <v-text-field v-model="serverForm.name" label="名称" variant="outlined" density="compact" class="mb-3" />
          <v-text-field v-model="serverForm.url" label="Emby 地址" variant="outlined" density="compact"
            hint="如 http://192.168.1.100:8096" persistent-hint class="mb-3" />
          <SecretField v-model="serverForm.api_key" label="API Key" class="mb-3" />
          <v-text-field v-model="serverForm.username" label="用户名 (用于登录)" variant="outlined" density="compact" class="mb-3" />
          <SecretField v-model="serverForm.password" label="密码" class="mb-3" />
  <template #actions>
    <v-btn variant="text" prepend-icon="mdi-lan-connect" @click="testConnection">测试连接</v-btn>
    <v-btn color="primary" variant="flat" prepend-icon="mdi-content-save-outline" @click="saveServer">保存</v-btn>
  </template>
</GlassDialog>
  </v-container>
</template>

