<template>
  <div class="mobile-image-registry-manager">
    <MobileTabs v-model="activeTab" :tabs="tabs">
      <template #registries>
        <n-space vertical>
          <n-button type="primary" size="small" @click="openRegistryModal">
            添加仓库
          </n-button>

          <div v-if="registries.length === 0" class="empty-state">
            <n-empty description="暂无仓库" size="small" />
          </div>

          <div v-else class="registry-list">
            <div v-for="registry in registries" :key="registry.id" class="registry-item">
              <div class="registry-header">
                <div class="registry-name">{{ registry.name }}</div>
                <n-space>
                  <n-button size="tiny" secondary type="info" @click="testRegistry(registry)" :loading="testingId === registry.id">
                    测试
                  </n-button>
                  <n-button size="tiny" secondary @click="openRegistryModal(registry)">
                    编辑
                  </n-button>
                  <n-popconfirm @positive-click="() => deleteRegistry(registry.id)" positive-text="确认" negative-text="取消">
                    <template #trigger>
                      <n-button size="tiny" secondary type="error">
                        </n-button>
                    </template>
                    确认删除？
                  </n-popconfirm>
                </n-space>
              </div>

              <div class="registry-info">
                <div class="info-row">
                  <span>{{ registry.is_https ? 'https://' : 'http://' }}{{ registry.url }}</span>
                </div>
                <div v-if="getCredentialName(registry.credential_id)" class="info-row">
                  <span>凭据: {{ getCredentialName(registry.credential_id) }}</span>
                </div>
              </div>
            </div>
          </div>
        </n-space>
      </template>

      <template #credentials>
        <n-space vertical>
          <n-button type="primary" size="small" @click="openCredModal">
            添加凭据
          </n-button>

          <div v-if="credentials.length === 0" class="empty-state">
            <n-empty description="暂无凭据" size="small" />
          </div>

          <div v-else class="credential-list">
            <div v-for="cred in credentials" :key="cred.id" class="credential-item">
              <div class="credential-header">
                <div class="credential-name">{{ cred.name }}</div>
                <n-space>
                  <n-button size="tiny" secondary @click="openCredModal(cred)">
                    编辑
                  </n-button>
                  <n-popconfirm @positive-click="() => deleteCredential(cred.id)" positive-text="确认" negative-text="取消">
                    <template #trigger>
                      <n-button size="tiny" secondary type="error">
                        </n-button>
                    </template>
                    确认删除？
                  </n-popconfirm>
                </n-space>
              </div>

              <div class="credential-info">
                <div class="info-row">
                  <n-icon size="14"><UserIcon /></n-icon>
                  <span>用户名: {{ cred.username }}</span>
                </div>
              </div>
            </div>
          </div>
        </n-space>
      </template>
    </MobileTabs>

    <n-modal v-model:show="showRegistryModal" preset="card" :title="editRegistryMode ? '编辑仓库' : '添加仓库'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="名称" required>
          <n-input v-model:value="registryForm.name" placeholder="例如: Docker Hub" />
        </n-form-item>
        <n-form-item label="URL" required>
          <n-input v-model:value="registryForm.url" placeholder="例如: docker.io" />
        </n-form-item>
        <n-form-item label="HTTPS">
          <n-switch v-model:value="registryForm.is_https" class="mobile-switch" />
        </n-form-item>
        <n-form-item label="关联凭据">
          <n-select v-model:value="registryForm.credential_id" :options="credOptions" clearable placeholder="选择凭据 (选填)" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showRegistryModal = false">取消</n-button>
          <n-button type="primary" @click="saveRegistry" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>

    <n-modal v-model:show="showCredModal" preset="card" :title="editCredMode ? '编辑凭据' : '添加凭据'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="名称" required>
          <n-input v-model:value="credForm.name" placeholder="例如: my-docker-hub-login" />
        </n-form-item>
        <n-form-item label="用户名" required>
          <n-input v-model:value="credForm.username" placeholder="username" />
        </n-form-item>
        <n-form-item label="密码/Token" required>
          <n-input v-model:value="credForm.password" type="password" show-password-on="click" placeholder="请输入密码或仓库 Token" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showCredModal = false">取消</n-button>
          <n-button type="primary" @click="saveCredential" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { 
  NSpace, NButton, NModal, NForm, NFormItem, 
  NInput, NSelect, NSwitch, NIcon, NEmpty, NPopconfirm, useMessage, useDialog 
} from 'naive-ui'
import {
  SensorsOutlined as TestIcon,
  Vpn
} from '@vicons/material'
import axios from 'axios'
import MobileTabs from '../components/MobileTabs.vue'

const message = useMessage()
const dialog = useDialog()

const activeTab = ref('registries')

const tabs = [
  { name: 'registries', label: '仓库列表' },
  { name: 'credentials', label: '凭据管理' },
]
const registries = ref([])
const credentials = ref([])
const showRegistryModal = ref(false)
const showCredModal = ref(false)
const editRegistryMode = ref(false)
const editCredMode = ref(false)
const currentRegistryId = ref('')
const currentCredId = ref('')
const testingId = ref('')
const saving = ref(false)

const registryForm = ref({
  name: '',
  url: '',
  is_https: true,
  credential_id: null
})

const credForm = ref({
  name: '',
  username: '',
  password: ''
})

const credOptions = computed(() => 
  credentials.value.map((c: any) => ({ label: c.name, value: c.id }))
)

const getCredentialName = (credId: any) => {
  const cred = credentials.value.find((c: any) => c.id === credId)
  return cred ? cred.name : ''
}

const fetchData = async () => {
  try {
    const [regRes, credRes] = await Promise.all([
      axios.get('/api/image-builder/registries'),
      axios.get('/api/image-builder/credentials')
    ])
    registries.value = regRes.data
    credentials.value = credRes.data
  } catch (e) {
    message.error('获取数据失败')
  }
}

const openRegistryModal = (row: any = null) => {
  if (row) {
    editRegistryMode.value = true
    currentRegistryId.value = row.id
    registryForm.value = { ...row }
  } else {
    editRegistryMode.value = false
    registryForm.value = { name: '', url: '', is_https: true, credential_id: null }
  }
  showRegistryModal.value = true
}

const openCredModal = (row: any = null) => {
  if (row) {
    editCredMode.value = true
    currentCredId.value = row.id
    credForm.value = { 
      name: row.name, 
      username: row.username, 
      password: row.encrypted_password || '' 
    }
  } else {
    editCredMode.value = false
    credForm.value = { name: '', username: '', password: '' }
  }
  showCredModal.value = true
}

const saveRegistry = async () => {
  if (!registryForm.value.name || !registryForm.value.url) {
    message.warning('请填写完整的仓库信息')
    return
  }
  saving.value = true
  try {
    if (editRegistryMode.value) {
      await axios.put(`/api/image-builder/registries/${currentRegistryId.value}`, registryForm.value)
      message.success('仓库更新成功')
    } else {
      await axios.post('/api/image-builder/registries', registryForm.value)
      message.success('仓库添加成功')
    }
    showRegistryModal.value = false
    fetchData()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const saveCredential = async () => {
  if (!credForm.value.name || !credForm.value.username || !credForm.value.password) {
    message.warning('请填写完整的凭据信息')
    return
  }
  saving.value = true
  try {
    if (editCredMode.value) {
      await axios.put(`/api/image-builder/credentials/${currentCredId.value}`, credForm.value)
      message.success('凭据更新成功')
    } else {
      await axios.post('/api/image-builder/credentials', credForm.value)
      message.success('凭据添加成功')
    }
    showCredModal.value = false
    fetchData()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const testRegistry = async (row: any) => {
  testingId.value = row.id
  try {
    const res = await axios.post(`/api/image-builder/registries/${row.id}/test`)
    if (res.data.success) {
      message.success(res.data.message)
    } else {
      message.error(res.data.message)
    }
  } catch (e: any) {
    message.error('测试请求失败: ' + (e.message || '未知错误'))
  } finally {
    testingId.value = ''
  }
}

const deleteRegistry = async (id: string) => {
  try {
    await axios.delete(`/api/image-builder/registries/${id}`)
    message.success('仓库已删除')
    fetchData()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

const deleteCredential = async (id: string) => {
  try {
    await axios.delete(`/api/image-builder/credentials/${id}`)
    message.success('凭据已删除')
    fetchData()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

onMounted(fetchData)
</script>

<style scoped>
.mobile-image-registry-manager {
  padding: 12px 0;
}

.empty-state {
  padding: 40px 0;
}

.registry-list,
.credential-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.registry-item,
.credential-item {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
}

.registry-header,
.credential-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.registry-name,
.credential-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.registry-info,
.credential-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.7;
}
</style>
