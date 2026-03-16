<template>
  <div class="mobile-pgsql-table-browser">
    <n-space vertical>
      <n-card size="small" :bordered="false" title="数据库选择">
        <n-select
          v-model:value="currentDb"
          :options="dbOptions"
          placeholder="切换数据库"
          @update:value="handleDbChange"
        />
        <n-button block size="small" secondary style="margin-top: 8px" @click="fetchTables">
          <template #icon><n-icon><RefreshIcon /></n-icon></template>
          刷新表列表
        </n-button>
      </n-card>

      <n-card v-if="tableList.length > 0" size="small" :bordered="false" title="表列表">
        <div class="table-list">
          <div 
            v-for="table in tableList" 
            :key="table" 
            class="table-item"
            :class="{ active: selectedTable === table }"
            @click="handleTableChange(table)"
          >
            <n-icon size="16"><TableIcon /></n-icon>
            <span>{{ table }}</span>
          </div>
        </div>
      </n-card>

      <n-card v-if="selectedTable" size="small" :bordered="false">
        <template #header>
          <n-space justify="space-between" align="center">
            <n-space align="center">
              <n-icon size="18"><TableIcon /></n-icon>
              <n-text strong style="font-size: 15px">{{ selectedTable }}</n-text>
            </n-space>
            <n-button size="small" secondary @click="fetchTableData" :loading="loading">
              <template #icon><n-icon><RefreshIcon /></n-icon></template>
              刷新
            </n-button>
          </n-space>
        </template>
        
        <n-space vertical>
          <n-text depth="3" style="font-size: 12px">共 {{ pagination.itemCount }} 条记录</n-text>
          <div class="data-table">
            <div v-if="tableData.length === 0" class="empty-state">
              <n-empty description="暂无数据" size="small" />
            </div>
            <div v-else>
              <div class="table-header">
                <div v-for="col in columns" :key="col.key" class="table-cell header-cell">
                  {{ col.title }}
                </div>
              </div>
              <div v-for="(row, index) in tableData" :key="index" class="table-row">
                <div v-for="col in columns" :key="col.key" class="table-cell">
                  {{ row[col.key] }}
                </div>
              </div>
            </div>
          </div>
          
          <n-pagination
            v-model:page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :page-count="Math.ceil(pagination.itemCount / pagination.pageSize)"
            :page-sizes="[10, 20, 50]"
            show-size-picker
            @update:page="fetchTableData"
            @update:page-size="handlePageSizeChange"
          />
        </n-space>
      </n-card>

      <div v-if="!selectedTable" class="empty-state">
        <n-empty :description="currentDb ? '请从上方选择一个表' : '请先选择数据库'" />
      </div>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { NCard, NSpace, NSelect, NButton, NIcon, NText, NEmpty, NPagination, useMessage } from 'naive-ui'
import { 
  TableChartOutlined as TableIcon, 
  RefreshOutlined as RefreshIcon
} from '@vicons/material'
import axios from 'axios'

const props = defineProps<{ host: any }>()
const message = useMessage()

const dbList = ref<string[]>([])
const currentDb = ref<string | null>(null)
const selectedTable = ref<string | null>(null)
const tableList = ref<string[]>([])
const tableData = ref<any[]>([])
const columns = ref<any[]>([])
const loading = ref(false)

const activeConfig = computed(() => {
  if (!props.host || !currentDb.value) return null
  return { ...props.host, database: currentDb.value }
})

const dbOptions = computed(() => dbList.value.map(db => ({ label: db, value: db })))

const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0
})

const fetchDatabases = async () => {
  if (!props.host) return
  try {
    console.log('Fetching databases with host:', props.host)
    const res = await axios.post('/api/pgsql/databases', props.host)
    console.log('Databases response:', res.data)
    dbList.value = res.data.map((db: any) => db.name)
    
    if (!currentDb.value && dbList.value.length > 0) {
      if (dbList.value.includes(props.host.database)) {
        currentDb.value = props.host.database
      } else {
        currentDb.value = dbList.value[0]
      }
      fetchTables()
    }
  } catch (e: any) {
    console.error('Error fetching databases:', e)
    message.error('加载数据库列表失败: ' + (e.response?.data?.detail || e.message))
  }
}

const fetchTables = async () => {
  if (!activeConfig.value) return
  try {
    console.log('Fetching tables with config:', activeConfig.value)
    const res = await axios.post('/api/pgsql/tables', activeConfig.value)
    console.log('Tables response:', res.data)
    tableList.value = res.data.tables
    if (tableList.value.length === 0) {
      message.info('该库下未发现公有表')
    }
  } catch (e: any) {
    console.error('Error fetching tables:', e)
    message.error('加载表列表失败: ' + (e.response?.data?.detail || e.message))
  }
}

const fetchTableData = async () => {
  if (!selectedTable.value || !activeConfig.value) return
  loading.value = true
  try {
    const res = await axios.post('/api/pgsql/data', {
      config: activeConfig.value,
      params: {
        table_name: selectedTable.value,
        page: pagination.page,
        page_size: pagination.pageSize
      }
    })
    columns.value = res.data.columns.map((col: any) => ({
      title: col.name,
      key: col.name
    }))
    tableData.value = res.data.rows
    pagination.itemCount = res.data.total
  } catch (e: any) {
    message.error('加载数据失败')
  } finally { 
    loading.value = false 
  }
}

const handleDbChange = () => {
  selectedTable.value = null
  tableList.value = []
  tableData.value = []
  fetchTables()
}

const handleTableChange = (table: string) => {
  selectedTable.value = table
  pagination.page = 1
  fetchTableData()
}

const handlePageSizeChange = () => {
  pagination.page = 1
  fetchTableData()
}

watch(() => props.host, (newHost) => {
  if (newHost) {
    currentDb.value = null
    selectedTable.value = null
    dbList.value = []
    tableList.value = []
    fetchDatabases()
  }
}, { immediate: true })

defineExpose({ refresh: fetchDatabases })
</script>

<style scoped>
.mobile-pgsql-table-browser {
  padding: 12px 0;
}

.table-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.table-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.04);
  cursor: pointer;
  transition: all 0.2s ease;
}

.table-item:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--n-primary-color);
}

.table-item.active {
  background: rgba(24, 160, 88, 0.1);
  border-color: var(--n-primary-color);
}

.data-table {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 6px;
}

.table-header {
  display: flex;
  background: rgba(255, 255, 255, 0.04);
  position: sticky;
  top: 0;
  z-index: 1;
}

.header-cell {
  padding: 8px;
  font-weight: 600;
  font-size: 12px;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.table-row {
  display: flex;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.table-row:last-child {
  border-bottom: none;
}

.table-cell {
  flex: 1;
  padding: 8px;
  font-size: 12px;
  color: var(--text-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.empty-state {
  padding: 40px 0;
}
</style>
