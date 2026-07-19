import { ref } from 'vue'
import axios from 'axios'
import { useMessage, useDialog } from 'naive-ui'

export function useDedupe() {
  const message = useMessage()
  const dialog = useDialog()

  const loading = ref(false)
  const syncing = ref(false)
  const analyzing = ref(false)
  const searchName = ref('')
  const showOnlyDuplicates = ref(false)
  const items = ref<any[]>([])
  const selectedIds = ref<string[]>([])
  const suggestedItems = ref<any[]>([]) // 专门存储智能选中的结果对象
  
  const dedupeConfig = ref<any>({ 
    rules: { priority_order: [], values_weight: {}, tie_breaker: 'small_id' }, 
    exclude_paths: [] 
  })

  const loadConfig = async () => {
    try {
      const res = await axios.get('/api/dedupe/config')
      if (res.data && res.data.rules) dedupeConfig.value = res.data
    } catch (e) {}
  }

  const saveDedupeConfig = async () => {
    try {
      await axios.post('/api/dedupe/config', dedupeConfig.value)
      message.success('规则已保存')
      return true
    } catch (e) { return false }
  }

  const processItems = (data: any[]) => {
    return data.map(i => ({
      ...i,
      isLeaf: i.item_type !== 'Series' && i.item_type !== 'Season'
    }))
  }

  const loadItems = async () => {
    loading.value = true
    selectedIds.value = []
    try {
      const res = await axios.get('/api/dedupe/items', { params: { query_text: searchName.value } })
      items.value = processItems(Array.isArray(res.data) ? res.data : [])
    } catch (e) {
      items.value = []
      message.error('加载列表失败')
    } finally {
      loading.value = false
    }
  }

  const onLoadChildren = async (row: any) => {
    try {
      const res = await axios.get('/api/dedupe/items', { params: { parent_id: row.id } })
      row.children = processItems(Array.isArray(res.data) ? res.data : [])
    } catch (e) {}
  }

  const toggleDuplicateMode = async (val: boolean) => {
    if (val) {
      loading.value = true
      selectedIds.value = []
      try {
        const res = await axios.get('/api/dedupe/duplicates')
        // 后端现在直接返回平铺的重复项列表
        items.value = processItems(Array.isArray(res.data) ? res.data : [])
      } catch (e) {
        items.value = []
        message.error('加载重复项失败')
      } finally {
        loading.value = false
      }
    } else {
      loadItems()
    }
  }

  const syncMedia = async () => {
    if (syncing.value) return
    
    try {
      syncing.value = true
      message.info('同步任务已在后台启动，完成后将自动刷新列表', { duration: 3000 })
      
      // 1. 发起触发请求 (后端会立即返回 sync_started)
      await axios.post('/api/dedupe/sync')
      
      // 2. 静默轮询状态，仅用于完成后刷新 + 提示
      const poll = setInterval(async () => {
        try {
          const statusRes = await axios.get('/api/dedupe/sync/status')
          const { is_syncing, progress } = statusRes.data
          
          if (!is_syncing) {
            clearInterval(poll)
            syncing.value = false
            message.success('Emby 媒体库同步已完成，列表已自动刷新')
            
            // 同步完成后刷新视图
            if (showOnlyDuplicates.value) {
              toggleDuplicateMode(true)
            } else {
              loadItems()
            }
          }
          // 静默忽略 progress，不打扰用户
        } catch (e) {
          clearInterval(poll)
          syncing.value = false
          // 轮询出错不弹窗，避免无意义的错误反馈
        }
      }, 2000) // 每 2 秒轮询一次
      
    } catch (e) {
      syncing.value = false
      message.error('启动同步任务失败')
    }
  }

  // --- 智能选中重构 ---
  const autoSelect = async () => {
    analyzing.value = true
    // 不设置 loading，避免遮罩整个表格
    try {
      // 不传任何参数，让后端全库扫描
      // 同步阻塞接口，覆盖全局 20s 超时为永不超时，避免大库分析被误判失败
      const res = await axios.post('/api/dedupe/smart-select', null, { timeout: 0 })
      const data = Array.isArray(res.data) ? res.data : []
      suggestedItems.value = data
      selectedIds.value = data.map((i: any) => i.id)
      
      if (data.length === 0) {
        message.info('未发现符合规则的可清理项目')
      }
      return data
    } catch (e) {
      suggestedItems.value = []
      message.error('算法执行失败')
      return []
    } finally {
      analyzing.value = false
    }
  }

  const deleteItems = async (ids: string[]) => {
    try {
      const res = await axios.delete('/api/dedupe/items', { data: { item_ids: ids } })
      message.success(`成功删除 ${res.data.success} 个项目`)
      selectedIds.value = []
      showOnlyDuplicates.value ? toggleDuplicateMode(true) : loadItems()
      return true
    } catch (e) {
      message.error('删除失败')
      return false
    }
  }

  return {
    loading, syncing, analyzing, searchName, showOnlyDuplicates, items, selectedIds, suggestedItems, dedupeConfig,
    loadItems, onLoadChildren, toggleDuplicateMode, syncMedia, autoSelect, deleteItems, loadConfig, saveDedupeConfig
  }
}