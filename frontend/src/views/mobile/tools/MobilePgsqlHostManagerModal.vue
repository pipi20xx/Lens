<template>
  <n-modal 
    :show="show" 
    @update:show="$emit('update:show', $event)" 
    preset="card" 
    title="管理 PostgreSQL 主机" 
    style="width: 95vw; max-width: 500px"
  >
    <n-space vertical>
      <n-button block type="primary" @click="handleAdd">
        添加新主机
      </n-button>
      <n-button block secondary @click="fetchHosts">
        刷新
      </n-button>

      <div v-if="hosts.length === 0" class="empty-state">
        <n-empty description="暂无主机" size="small" />
      </div>

      <div v-else class="host-list">
        <div v-for="host in hosts" :key="host.id" class="host-item">
          <div class="host-header">
            <div class="host-name">{{ host.name }}</div>
            <n-space>
              <n-button size="tiny" secondary type="info" @click="handleEdit(host)">
                </n-button>
              <n-popconfirm @positive-click="() => handleDelete(host.id)" positive-text="确认" negative-text="取消">
                <template #trigger>
                  <n-button size="tiny" secondary type="error">
                    </n-button>
                </template>
                确认删除？
              </n-popconfirm>
            </n-space>
          </div>
          <div class="host-info">
            <div class="info-row">
              <n-icon size="14"><ServerIcon /></n-icon>
              <span>{{ host.host }}:{{ host.port }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><UserIcon /></n-icon>
              <span>{{ host.username }}</span>
            </div>
            <div class="info-row">
              <n-icon size="14"><DbIcon /></n-icon>
              <span>{{ host.database }}</span>
            </div>
          </div>
        </div>
      </div>
    </n-space>

    <n-modal 
      v-model:show="showAdd" 
      preset="card" 
      :title="editingHostId ? '编辑数据库主机' : '配置数据库主机'" 
      style="width: 95vw; max-width: 400px"
    >
      <n-form label-placement="top" size="small">
        <n-form-item label="显示名称">
          <n-input v-model:value="form.name" placeholder="例如: 生产环境库" />
        </n-form-item>
        <n-form-item label="主机">
          <n-input v-model:value="form.host" placeholder="localhost" />
        </n-form-item>
        <n-form-item label="端口">
          <n-input-number v-model:value="form.port" :show-button="false" style="width: 100%" />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input v-model:value="form.username" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="form.password" type="password" />
        </n-form-item>
        <n-form-item label="默认数据库">
          <n-input v-model:value="form.database" />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space vertical style="width: 100%">
          <n-button block type="warning" @click="handleTest" :loading="testing">
            测试连接
          </n-button>
          <n-space justify="end">
            <n-button secondary @click="showAdd = false">取消</n-button>
            <n-button type="primary" @click="handleSave">
              {{ editingHostId ? '保存修改' : '保存主机' }}
            </n-button>
          </n-space>
        </n-space>
      </template>
    </n-modal>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { NModal, NSpace, NButton, NForm, NFormItem, NInput, NInputNumber, NIcon, NEmpty, NPopconfirm, useMessage, useDialog } from 'naive-ui'
import {
  DnsOutlined as ServerIcon,
  SensorsOutlined as TestIcon
} from '@vicons/material'
import request from '@/utils/request'

defineProps<{ show: boolean }>()
const emit = defineEmits(['update:show', 'refresh'])

const message = useMessage()
const dialog = useDialog()

const hosts = ref<any[]>([])
const showAdd = ref(false)
const testing = ref(false)
const editingHostId = ref<string | null>(null)

const form = reactive({
  name: '',
  host: 'localhost',
  port: 5432,
  username: 'postgres',
  password: '',
  database: 'postgres'
})

const resetForm = () => {
  form.name = ''
  form.host = 'localhost'
  form.port = 5432
  form.username = 'postgres'
  form.password = ''
  form.database = 'postgres'
  editingHostId.value = null
}

const fetchHosts = async () => {
  try {
    const res = await request.get('/api/pgsql/hosts')
    hosts.value = (res as any) || []
  } catch (e) {}
}

const handleAdd = () => {
  resetForm()
  showAdd.value = true
}

const handleEdit = (row: any) => {
  editingHostId.value = row.id
  form.name = row.name
  form.host = row.host
  form.port = row.port
  form.username = row.username
  form.password = row.password
  form.database = row.database
  showAdd.value = true
}

const handleTest = async () => {
  testing.value = true
  try {
    const res: any = await request.post('/api/pgsql/test', form)
    if (res.success) message.success('测试成功: ' + res.version)
    else message.error('失败: ' + res.message)
  } catch (e: any) { message.error('请求出错') }
  finally { testing.value = false }
}

const handleSave = async () => {
  if (!form.name) return message.warning('请输入名称')
  try {
    if (editingHostId.value) {
      await request.put(`/api/pgsql/hosts/${editingHostId.value}`, form, { params: { name: form.name } })
      message.success('已更新')
    } else {
      await request.post('/api/pgsql/hosts', form, { params: { name: form.name } })
      message.success('已添加')
    }
    showAdd.value = false
    fetchHosts()
    emit('refresh')
  } catch (e) {}
}

const handleDelete = async (id: string) => {
  try {
    await request.delete(`/api/pgsql/hosts/${id}`)
    fetchHosts()
    emit('refresh')
    message.info('已移除')
  } catch (e) {
    message.error('移除失败')
  }
}

onMounted(fetchHosts)
</script>

<style scoped>
.empty-state {
  padding: 40px 0;
}

.host-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.host-item {
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.host-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.host-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-color);
}

.host-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-color-3);
}
</style>
