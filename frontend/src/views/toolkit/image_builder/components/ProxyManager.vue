<template>
  <div class="proxy-manager">
    <n-card title="构建代理设置" size="small">
      <template #header-extra>
        <n-button size="small" type="primary" @click="openModal()">
          添加代理
        </n-button>
      </template>
      <n-text depth="3">配置 HTTP/HTTPS 代理，用于在构建过程中加速下载基础镜像或依赖包。</n-text>
      <div style="margin-top: 12px">
        <!-- 代理卡片列表：一行一个 -->
        <div v-if="proxies.length" class="proxy-list">
          <div
            v-for="row in proxies"
            :key="row.id"
            class="proxy-card"
          >
            <!-- 卡片头部：名称 -->
            <div class="card-header">
              <div class="card-title">
                <n-text strong class="proxy-name text-truncate">{{ row.name }}</n-text>
              </div>
              <n-tag v-if="row.username" size="small" type="info" ghost>已鉴权</n-tag>
            </div>

            <!-- 代理地址 -->
            <div class="card-desc">
              <n-text depth="3" class="desc-text">{{ row.url }}</n-text>
            </div>

            <!-- 操作按钮 -->
            <div class="card-actions">
              <n-button
                size="small"
                @click="openModal(row)"
              >
                编辑
              </n-button>
              <n-button
                size="small"
                type="error"
                ghost
                @click="deleteProxy(row.id)"
              >
                删除
              </n-button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <n-empty
          v-else
          description="暂无代理配置"
          style="padding: 40px 0"
        />
      </div>
    </n-card>

    <n-modal v-model:show="showModal" preset="card" :title="editMode ? '编辑代理' : '添加代理'" style="width: 450px">
      <n-form :model="form" label-placement="left" label-width="100">
        <n-form-item label="名称">
          <n-input v-model:value="form.name" placeholder="例如: Clash" />
        </n-form-item>
        <n-form-item label="代理地址">
          <n-input v-model:value="form.url" placeholder="例如: http://192.168.1.5:7890" />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" placeholder="可选" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="form.password" type="password" show-password-on="click" placeholder="可选" />
        </n-form-item>
        <n-space justify="end">
          <n-button @click="showModal = false">
            取消
          </n-button>
          <n-button type="primary" @click="saveProxy">
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
  NInput, NSpace, NText, useMessage, useDialog, NTag, NEmpty
} from 'naive-ui'
import axios from 'axios'

const message = useMessage()
const dialog = useDialog()

const proxies = ref([])
const showModal = ref(false)
const editMode = ref(false)
const currentProxyId = ref('')

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
  } catch (e) {}
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
  try {
    if (editMode.value) {
      await axios.put(`/api/image-builder/proxies/${currentProxyId.value}`, form.value)
    } else {
      await axios.post('/api/image-builder/proxies', form.value)
    }
    message.success('已保存')
    showModal.value = false
    fetchProxies()
  } catch (e) {
    message.error('保存失败')
  }
}

const deleteProxy = async (id: string) => {
  dialog.warning({
    title: '确认删除',
    content: '删除代理设置可能影响关联项目的镜像构建，是否继续？',
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await axios.delete(`/api/image-builder/proxies/${id}`)
        fetchProxies()
      } catch (e) {}
    }
  })
}

onMounted(fetchProxies)
</script>

<style scoped>
/* 卡片列表：一行一个卡片 */
.proxy-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm, 0.5rem);
}

.proxy-card {
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

.proxy-card:hover {
  border-color: rgba(64, 128, 240, 0.75);
  box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.3));
}

.proxy-card:active {
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

.proxy-name {
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