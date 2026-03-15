<template>
  <div class="mobile-postgres-manager">
    <div class="page-header">
      <h1 class="page-title">PostgreSQL 管理</h1>
      <p class="page-desc">管理 PostgreSQL 数据库连接与查询</p>
    </div>

    <n-card class="connection-card" :bordered="false" title="连接配置">
      <n-space vertical>
        <n-form-item label="主机地址">
          <n-input v-model:value="config.host" placeholder="localhost" />
        </n-form-item>
        <n-form-item label="端口">
          <n-input-number v-model:value="config.port" placeholder="5432" />
        </n-form-item>
        <n-form-item label="数据库名">
          <n-input v-model:value="config.database" placeholder="postgres" />
        </n-form-item>
        <n-form-item label="用户名">
          <n-input v-model:value="config.username" placeholder="postgres" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input v-model:value="config.password" type="password" show-password-on="click" />
        </n-form-item>
        <n-button block type="primary" :loading="connecting" @click="connect">
          <template #icon><n-icon><ConnectIcon /></n-icon></template>
          连接数据库
        </n-button>
      </n-space>
    </n-card>

    <n-card class="query-card" :bordered="false" title="SQL 查询">
      <n-space vertical>
        <n-input
          v-model:value="query"
          type="textarea"
          placeholder="SELECT * FROM table_name LIMIT 10;"
          :rows="4"
        />
        <n-button block type="primary" :loading="querying" @click="executeQuery" :disabled="!connected">
          <template #icon><n-icon><PlayIcon /></n-icon></template>
          执行查询
        </n-button>
        <div v-if="queryResult" class="result-content">
          <div class="result-header">查询结果 ({{ queryResult.length }} 行)</div>
          <div class="result-table">
            <div v-for="(row, index) in queryResult" :key="index" class="result-row">
              <div v-for="(value, key) in row" :key="key" class="result-cell">
                {{ value }}
              </div>
            </div>
          </div>
        </div>
      </n-space>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NCard, NButton, NSpace, NFormItem, NInput, NInputNumber, NIcon } from 'naive-ui'
import { LinkOutlined as ConnectIcon, PlayArrowOutlined as PlayIcon } from '@vicons/material'
import { pgsqlApi } from '@/api/pgsql'
import { useMessage } from 'naive-ui'

const message = useMessage()
const connecting = ref(false)
const querying = ref(false)
const connected = ref(false)
const query = ref('')
const queryResult = ref<any[]>([])

const config = ref({
  host: 'localhost',
  port: 5432,
  database: 'postgres',
  username: 'postgres',
  password: ''
})

const connect = async () => {
  if (!config.value.host || !config.value.database) {
    message.warning('请填写完整的连接信息')
    return
  }
  connecting.value = true
  try {
    const res = await pgsqlApi.getDatabases(config.value)
    connected.value = true
    message.success('数据库连接成功')
    queryResult.value = res as any || []
  } catch (e) {
    message.error('数据库连接失败')
    connected.value = false
  } finally {
    connecting.value = false
  }
}

const executeQuery = () => {
  message.info('请在桌面端使用查询功能')
}
</script>

<style scoped>
.mobile-postgres-manager {
  padding: 16px;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-color);
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-color);
  opacity: 0.6;
  margin: 0;
}

.connection-card,
.query-card {
  margin-bottom: 12px;
}

.result-content {
  margin-top: 12px;
}

.result-header {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color);
  margin-bottom: 8px;
}

.result-table {
  background: var(--app-bg-color);
  border-radius: 8px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.result-row {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}

.result-cell {
  flex: 1;
  padding: 8px;
  font-size: 12px;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
