<template>
  <div class="mobile-image-proxy-manager">
    <n-space vertical>
      <n-space justify="space-between" align="center">
        <n-button type="primary" size="small" @click="openModal">
          添加代理
        </n-button>
        <n-text depth="3" style="font-size: 12px">
          配置 HTTP/HTTPS 代理，用于加速下载
        </n-text>
      </n-space>

      <div v-if="proxies.length === 0" class="empty-state">
        <n-empty description="暂无代理" size="small" />
      </div>

      <div v-else class="proxy-list">
        <div v-for="proxy in proxies" :key="proxy.id" class="proxy-item">
          <div class="proxy-header">
            <div class="proxy-name">{{ proxy.name }}</div>
            <n-space>
              <n-button size="tiny" secondary @click="openModal(proxy)">
                编辑
              </n-button>
              <n-popconfirm @positive-click="() => deleteProxy(proxy.id)" positive-text="确认" negative-text="取消">
                <template #trigger>
                  <n-button size="tiny" secondary type="error">
                    </n-button>
                </template>
                确认删除？
              </n-popconfirm>
            </n-space>
          </div>

          <div class="proxy-info">
            <div class="info-row">
              <n-icon size="14"><UrlIcon /></n-icon>
              <span>{{ proxy.url }}</span>
            </div>
            <div v-if="proxy.username" class="info-row">
              <n-icon size="14"><UserIcon /></n-icon>
              <span>用户名: {{ proxy.username }}</span>
            </div>
          </div>
        </div>
      </div>
    </n-space>

    <n-modal v-model:show="showModal" preset="card" :title="editMode ? '编辑代理' : '添加代理'" style="width: 90vw; max-width: 400px">
      <n-form label-placement="top" size="small">
        <n-form-item label="名称" required>
          <n-input v-model:value="form.name" placeholder="例如: Clash" />
        </n-form-item>
        <n-form-item label="代理地址" required>
          <n-input v-model:value="form.url" placeholder="例如: http://192.168.1.5:7890" />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" placeholder="可选" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="可选" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space justify="end">
          <n-button secondary @click="showModal = false">取消</n-button>
          <n-button type="primary" @click="saveProxy" :loading="saving">保存</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { 
  NSpace, NButton, NModal, NForm, NFormItem, 
  NInput, NIcon, NEmpty, NText, NPopconfirm, useMessage, useDialog 
} from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const dialog = useDialog()

const proxies = ref([])
const showModal = ref(false)
const editMode = ref(false)
const currentProxyId = ref('')
const saving = ref(false)

const form = ref({
  name: '',
  url: '',
  username: '',
  password: ''
})

const fetchProxies = async () => {
  try {
    const res = await axios.get('/api/image-builder/proxies')
    proxies.value = res.data
  } catch (e: any) {
    message.error('获取代理列表失败: ' + (e.message || '未知错误'))
  }
}

const openModal = (row: any = null) => {
  if (row) {
    editMode.value = true
    currentProxyId.value = row.id
    form.value = { ...row }
  } else {
    editMode.value = false
    form.value = { name: '', url: '', username: '', password: '' }
  }
  showModal.value = true
}

const saveProxy = async () => {
  if (!form.value.name || !form.value.url) {
    message.warning('请填写完整的代理信息')
    return
  }
  saving.value = true
  try {
    if (editMode.value) {
      await axios.put(`/api/image-builder/proxies/${currentProxyId.value}`, form.value)
      message.success('代理更新成功')
    } else {
      await axios.post('/api/image-builder/proxies', form.value)
      message.success('代理添加成功')
    }
    showModal.value = false
    fetchProxies()
  } catch (e: any) {
    message.error('保存失败: ' + (e.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

const deleteProxy = async (id: string) => {
  try {
    await axios.delete(`/api/image-builder/proxies/${id}`)
    message.success('代理已删除')
    fetchProxies()
  } catch (e: any) {
    message.error('删除失败: ' + (e.message || '未知错误'))
  }
}

onMounted(fetchProxies)
</script>

<style scoped>
.mobile-image-proxy-manager {
  padding: 12px 0;
}

.empty-state {
  padding: 40px 0;
}

.proxy-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.proxy-item {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
}

.proxy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.proxy-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-color);
}

.proxy-info {
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
