<template>
  <div class="registry-manager">
    <n-space vertical :size="16">
      <!-- 仓库配置卡片区块 -->
      <n-card title="仓库配置" size="small">
        <template #header-extra>
          <n-button size="small" type="primary" @click="openRegistryModal()">
            添加仓库
          </n-button>
        </template>
        <n-spin :show="false">
          <div v-if="registries.length" class="reg-list">
            <div
              v-for="row in registries"
              :key="row.id"
              class="reg-card"
            >
              <!-- 卡片头部：名称 + URL -->
              <div class="card-header">
                <div class="card-title">
                  <n-text strong class="reg-name text-truncate">{{ row.name }}</n-text>
                </div>
                <n-tag v-if="row.is_https" size="small" type="success" ghost>HTTPS</n-tag>
                <n-tag v-else size="small" type="warning" ghost>HTTP</n-tag>
              </div>

              <!-- URL -->
              <div class="card-desc">
                <n-text  class="desc-text">{{ row.url }}</n-text>
              </div>

              <!-- 操作按钮 -->
              <div class="card-actions">
                <n-button
                  size="small"
                  type="info"
                  ghost
                  :loading="testingId === row.id"
                  @click="testRegistry(row)"
                >
                  测试
                </n-button>
                <n-button
                  size="small"
                  @click="openRegistryModal(row)"
                >
                  编辑
                </n-button>
                <n-button
                  size="small"
                  type="error"
                  ghost
                  @click="deleteRegistry(row.id)"
                >
                  删除
                </n-button>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <n-empty
            v-else
            description="暂无仓库配置"
            style="padding: 40px 0"
          />
        </n-spin>
      </n-card>

      <!-- 凭据管理卡片区块 -->
      <n-card title="凭据管理" size="small">
        <template #header-extra>
          <n-button size="small" type="primary" @click="openCredModal()">
            添加凭据
          </n-button>
        </template>
        <div v-if="credentials.length" class="cred-list">
          <div
            v-for="row in credentials"
            :key="row.id"
            class="cred-card"
          >
            <!-- 卡片头部：名称 + 用户名 -->
            <div class="card-header">
              <div class="card-title">
                <n-text strong class="cred-name text-truncate">{{ row.name }}</n-text>
              </div>
              <n-tag size="small" type="info" ghost>{{ row.username }}</n-tag>
            </div>

            <!-- 操作按钮 -->
            <div class="card-actions">
              <n-button
                size="small"
                @click="openCredModal(row)"
              >
                编辑
              </n-button>
              <n-button
                size="small"
                type="error"
                ghost
                @click="deleteCredential(row.id)"
              >
                删除
              </n-button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <n-empty
          v-else
          description="暂无凭据"
          style="padding: 40px 0"
        />
      </n-card>
    </n-space>

    <!-- Registry Modal -->
    <n-modal v-model:show="showRegistryModal" preset="card" :title="editRegistryMode ? '编辑仓库' : '添加仓库'" style="width: 450px">
      <n-form :model="registryForm" label-placement="left" label-width="100">
        <n-form-item label="名称">
          <n-input v-model:value="registryForm.name" placeholder="例如: Docker Hub" />
        </n-form-item>
        <n-form-item label="URL">
          <n-input v-model:value="registryForm.url" placeholder="例如: docker.io" />
        </n-form-item>
        <n-form-item label="HTTPS">
          <n-switch v-model:value="registryForm.is_https" />
        </n-form-item>
        <n-form-item label="关联凭据">
          <n-select v-model:value="registryForm.credential_id" :options="credOptions" clearable />
        </n-form-item>
        <n-space justify="end">
          <n-button @click="showRegistryModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="saveRegistry">
            保存
          </n-button>
        </n-space>
      </n-form>
    </n-modal>

    <!-- Credential Modal -->
    <n-modal v-model:show="showCredModal" preset="card" :title="editCredMode ? '编辑凭据' : '添加凭据'" style="width: 600px">
      <n-form :model="credForm" label-placement="left" label-width="120">
        <n-form-item label="名称">
          <n-input v-model:value="credForm.name" placeholder="例如: my-docker-hub-login" />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input v-model:value="credForm.username" />
        </n-form-item>
        <n-form-item label="密码/Token">
          <n-input v-model:value="credForm.password" placeholder="请输入密码或仓库 Token" />
        </n-form-item>
        <n-space justify="end">
          <n-button @click="showCredModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="saveCredential">
            保存
          </n-button>
        </n-space>
      </n-form>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  NCard, NButton, NModal, NForm, NFormItem,
  NInput, NSelect, NSwitch, NSpace, useMessage, useDialog, NTag, NSpin, NEmpty, NText
} from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const dialog = useDialog()

const registries = ref([])
const credentials = ref([])
const showRegistryModal = ref(false)
const showCredModal = ref(false)
const editRegistryMode = ref(false)
const editCredMode = ref(false)
const currentRegistryId = ref('')
const currentCredId = ref('')
const testingId = ref('')

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

const credOptions = ref([])

const fetchData = async () => {
  try {
    const [regRes, credRes] = await Promise.all([
      axios.get('/api/image-builder/registries'),
      axios.get('/api/image-builder/credentials')
    ])
    registries.value = regRes.data
    credentials.value = credRes.data
    credOptions.value = credentials.value.map((c: any) => ({ label: c.name, value: c.id }))
  } catch (e) {}
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
  try {
    if (editRegistryMode.value) {
      await axios.put(`/api/image-builder/registries/${currentRegistryId.value}`, registryForm.value)
    } else {
      await axios.post('/api/image-builder/registries', registryForm.value)
    }
    message.success('已保存')
    showRegistryModal.value = false
    fetchData()
  } catch (e) {
    message.error('保存失败')
  }
}

const saveCredential = async () => {
  try {
    if (editCredMode.value) {
      await axios.put(`/api/image-builder/credentials/${currentCredId.value}`, credForm.value)
    } else {
      await axios.post('/api/image-builder/credentials', credForm.value)
    }
    message.success('已保存')
    showCredModal.value = false
    fetchData()
  } catch (e) {
    message.error('保存失败')
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
  } catch (e) {
    message.error('测试请求失败')
  } finally {
    testingId.value = ''
  }
}

const deleteRegistry = async (id: string) => {
  dialog.warning({
    title: '确认删除',
    content: '删除仓库配置可能导致关联的构建任务失败，是否继续？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/image-builder/registries/${id}`)
        fetchData()
      } catch (e) {}
    }
  })
}

const deleteCredential = async (id: string) => {
  dialog.warning({
    title: '确认删除',
    content: '删除凭据将导致所有使用该凭据的仓库无法登录，是否继续？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/image-builder/credentials/${id}`)
        fetchData()
      } catch (e) {}
    }
  })
}

onMounted(fetchData)
</script>

<style scoped>
/* 卡片列表：一行一个卡片 */
.reg-list,
.cred-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.reg-card,
.cred-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 10px;
  background: var(--card-bg-color, rgba(255, 255, 255, 0.03));
  border: 1px solid rgba(64, 128, 240, 0.4);
  transition: border-color var(--transition-normal, 250ms ease),
              box-shadow var(--transition-normal, 250ms ease),
              transform var(--transition-fast, 150ms ease);
  position: relative;
  overflow: hidden;
}

.reg-card:hover,
.cred-card:hover {
  border-color: rgba(64, 128, 240, 0.75);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.reg-card:active,
.cred-card:active {
  transform: scale(0.99);
}

/* 卡片头部 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.reg-name,
.cred-name {
  font-size: var(--text-md, 0.9375rem);
  max-width: 100%;
}

/* 描述 */
.card-desc {
  min-width: 0;
}

.desc-text {
  font-size: 12px;
  line-height: 1.5;
  word-break: break-all;
}

/* 操作按钮 */
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light, rgba(255, 255, 255, 0.06));
}

.card-actions .n-button {
  flex: 1 1 auto;
  min-width: 56px;
}

/* 移动端适配 */
@media (max-width: 767px) {
  .card-actions .n-button {
    flex: 1 1 calc(50% - 3px);
    min-width: 0;
  }
}

@media (max-width: 380px) {
  .card-actions .n-button {
    flex: 1 1 100%;
  }
}
</style>