<template>
  <n-layout has-sider class="browser-layout" style="height: calc(100vh - 300px); min-height: 500px;" bordered>
    <n-layout-sider
      bordered
      :collapse-mode="isMobile ? 'transform' : 'width'"
      :collapsed-width="isMobile ? 0 : 48"
      :width="240"
      v-model:collapsed="siderCollapsed"
      :show-trigger="!isMobile"
      :position="isMobile ? 'absolute' : 'static'"
      class="browser-sider"
    >
      <div style="padding: 12px; border-bottom: 1px solid var(--border-color)">
        <n-space vertical size="small">
          <n-select
            v-model:value="currentDb"
            :options="dbOptions"
            placeholder="切换数据库"
            size="small"
            @update:value="handleDbChange"
          />
          <n-button block size="tiny" ghost @click="fetchTables">
            刷新表列表
          </n-button>
        </n-space>
      </div>
      <n-menu
        v-model:value="selectedTable"
        :options="tableMenuOptions"
        :indent="18"
        @update:value="handleTableChange"
      />
    </n-layout-sider>

    <!-- 移动端遮罩：sider 展开时点击关闭 -->
    <div v-if="isMobile && !siderCollapsed" class="sider-mask" @click="siderCollapsed = true"></div>

    <n-layout-content content-style="padding: 16px; display: flex; flex-direction: column;">
      <!-- 移动端:表列表触发按钮 -->
      <div v-if="isMobile" class="mobile-table-trigger">
        <n-button size="small" block secondary @click="siderCollapsed = false">
          <template #icon><n-icon :component="TableCellsIcon" /></template>
          {{ currentDb ? `${currentDb} / ${selectedTable || '选择表'}` : '选择数据库' }}
        </n-button>
      </div>

      <div v-if="!selectedTable" class="empty-state">
        <n-empty :description="currentDb ? '该库下没有发现公有表，或请从左侧选择' : '请先在上方选择一个数据库'" />
      </div>
      <div v-else style="flex: 1; display: flex; flex-direction: column; min-height: 0;">
        <n-space justify="space-between" align="center" :wrap="true" :size="8" style="margin-bottom: 12px">
          <n-space align="center" :wrap="true" :size="8">
            <n-icon size="20"><TableCellsIcon /></n-icon>
            <n-text strong style="font-size: 16px">{{ selectedTable }}</n-text>
            <n-tag size="small" type="info">{{ pagination.itemCount }} 条记录</n-tag>
          </n-space>
          <n-button size="small" @click="fetchTableData" :loading="loading">
            刷新数据
          </n-button>
        </n-space>
        <n-data-table
          flex-height remote
          :columns="columns"
          :data="tableData"
          :loading="loading"
          :pagination="pagination"
          :scroll-x="1200"
          style="flex: 1"
        />
      </div>
    </n-layout-content>
  </n-layout>

  <DataValueViewerModal
    v-model:show="showViewer"
    :title="viewerTitle"
    :value="viewerValue"
  />
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, h } from 'vue'
import { NLayout, NLayoutSider, NLayoutContent, NMenu, NDataTable, NEmpty, NSpace, NIcon, NText, NTag, NButton, NSelect, NEllipsis, useMessage } from 'naive-ui'
import { TableCellsIcon } from '@heroicons/vue/24/outline'
import axios from 'axios'
import DataValueViewerModal from './DataValueViewerModal.vue'
import { usePWA } from '@/composables/usePWA'

const { isMobile } = usePWA()

const props = defineProps<{ host: any }>()
const message = useMessage()

// 移动端 sider 默认折叠
const siderCollapsed = ref(false)
watch(isMobile, (mobile) => { siderCollapsed.value = mobile }, { immediate: true })

const renderIcon = (icon: any) => {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const dbList = ref<string[]>([])
const currentDb = ref<string | null>(null)
const selectedTable = ref<string | null>(null)
const tableList = ref<string[]>([])
const tableData = ref<any[]>([])
const columns = ref<any[]>([])
const loading = ref(false)

const showViewer = ref(false)
const viewerTitle = ref('')
const viewerValue = ref<any>(null)

const openViewer = (title: string, val: any) => {
  viewerTitle.value = title
  viewerValue.value = val
  showViewer.value = true
}

// 计算属性：将主机配置与当前选中的库合并
const activeConfig = computed(() => {
  if (!props.host || !currentDb.value) return null
  return { ...props.host, database: currentDb.value }
})

const dbOptions = computed(() => dbList.value.map(db => ({ label: db, value: db })))

const pagination = reactive({
  page: 1,
  pageSize: 50,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [20, 50, 100],
  onChange: (page: number) => {
    pagination.page = page
    fetchTableData()
  }
})

const tableMenuOptions = computed(() => {
  return tableList.value.map(t => ({
    label: t,
    key: t,
    icon: () => h(NIcon, null, { default: () => h(TableCellsIcon) })
  }))
})

// 1. 获取该实例下的所有数据库
const fetchDatabases = async () => {
  if (!props.host) return
  try {
    const res = await axios.post('/api/pgsql/databases', props.host)
    // 后端返回的是对象数组
    dbList.value = res.data.map((db: any) => db.name)
    
    // 初始化数据库选中
    if (!currentDb.value && dbList.value.length > 0) {
      if (dbList.value.includes(props.host.database)) {
        currentDb.value = props.host.database
      } else {
        currentDb.value = dbList.value[0]
      }
      fetchTables()
    }
  } catch (e: any) {
    message.error('加载数据库列表失败')
  }
}

// 2. 获取选中库下的表
const fetchTables = async () => {
  if (!activeConfig.value) return
  try {
    const res = await axios.post('/api/pgsql/tables', activeConfig.value)
    tableList.value = res.data.tables
    if (tableList.value.length === 0) {
      message.info('该库下未发现公有表')
    }
  } catch (e: any) {
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
      key: col.name,
      width: 150,
      render(row: any) {
        const val = row[col.name]
        if (val === null) return h(NText, { depth: 3, style: 'font-style: italic' }, { default: () => 'NULL' })

        const isObject = typeof val === 'object'
        const isLongText = typeof val === 'string' && val.length > 80

        if (isObject || isLongText) {
          return h(
            NButton,
            {
              size: 'tiny',
              type: 'primary',
              secondary: true,
              block: true,
              onClick: () => openViewer(col.name, val)
            },
            { 
              default: () => isObject ? '查看 JSON' : '查看详情'
            }
          )
        }

        return h(
          NEllipsis,
          { style: 'cursor: pointer;', onClick: () => openViewer(col.name, val) },
          { default: () => String(val) }
        )
      }
    }))
    tableData.value = res.data.rows
    pagination.itemCount = res.data.total
  } catch (e: any) {
    message.error('加载数据失败')
  }
  finally { loading.value = false }
}

const handleDbChange = () => {
  selectedTable.value = null
  tableList.value = []
  tableData.value = []
  fetchTables()
}

const handleTableChange = (val: string) => {
  selectedTable.value = val
  pagination.page = 1
  fetchTableData()
}

watch(() => props.host, () => {
  currentDb.value = null
  selectedTable.value = null
  dbList.value = []
  tableList.value = []
  fetchDatabases()
}, { immediate: true })

defineExpose({ refresh: fetchDatabases })
</script>

<style scoped>
.empty-state { height: 100%; display: flex; align-items: center; justify-content: center; }

/* n-layout 设 position: relative，作为 absolute sider 和遮罩的定位参考 */
.browser-layout {
  position: relative;
}

/* 移动端 sider 浮层：高于 content */
.browser-sider {
  z-index: 101;
}
/* 遮罩层：sider 展开时覆盖 content，点击关闭 */
.sider-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 100;
}
.mobile-table-trigger {
  margin-bottom: 12px;
  flex-shrink: 0;
}

@media (max-width: 767px) {
  /* content 内边距缩减 */
  :deep(.n-layout-content .n-layout-content__content) {
    padding: 8px !important;
  }
  /* n-data-table 字体稍缩 */
  :deep(.n-data-table .n-data-table-th),
  :deep(.n-data-table .n-data-table-td) {
    font-size: 12px;
  }
}
</style>